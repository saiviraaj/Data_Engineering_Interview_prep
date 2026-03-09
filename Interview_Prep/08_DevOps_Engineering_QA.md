# DevOps & Engineering Practices — Exhaustive Interview Q&A

---

**Q1. How did you implement CI/CD for data pipelines in CDM Next?**

Every change to CDM Next went through a four-stage GitHub Actions pipeline before reaching production. Stage one: lint and unit test — flake8 and black for Python, sqlfluff for SQL, pytest for unit tests, and a DagBag import check that verified every DAG parsed without errors. This ran in under two minutes on every PR. Stage two: Terraform plan — an automated plan for any infrastructure changes, published as a PR comment so the reviewer could see exactly what resources would change. Stage three: auto-deploy to staging on merge to the develop branch — Terraform apply in the staging project, DAG files synced to the staging Composer GCS bucket. Stage four: production deployment required two PR approvals and a manual "Approve" click in GitHub Environments, which provided an audit trail of who approved each production deployment. This workflow meant a change in a DAG file could never reach production without being tested, reviewed, and explicitly approved.

---

**Q2. What is Terraform and how do you use it for data infrastructure?**

Terraform is an Infrastructure as Code tool that lets you declare GCP resources in configuration files, plan changes before applying them, and track resource state. For data engineering, the resources I manage in Terraform are: BigQuery datasets and tables (schema, partitioning, clustering, expiration), GCS buckets (lifecycle rules, IAM), service accounts and IAM bindings, Secret Manager secrets, Cloud Composer environments, and VPC Service Control perimeters.

The workflow: write HCL (HashiCorp Configuration Language) declaring desired state, run `terraform plan` to preview changes, review the plan (critical step — never skip), run `terraform apply` to create/modify resources. State is stored in a GCS bucket so the team shares a single source of truth.

In CDM Next, every new application team onboarding triggered a Terraform module instantiation that provisioned: a BigQuery dataset, a dedicated service account, IAM bindings with least privilege, a GCS staging prefix, and a Secret Manager entry for their source credentials. Consistent, auditable, repeatable — no console clicks.

---

**Q3. What is the difference between a Docker image and a container?**

An image is a static, immutable snapshot — a template. It contains the OS layer, Python version, installed packages, and application code, built by running a Dockerfile. An image is built once and pushed to a registry (GCP Artifact Registry).

A container is a running instance of an image. You can run many containers from the same image simultaneously. Containers are isolated processes on the host machine — they share the kernel but have their own filesystem, network, and process space. When a container stops, its writable layer is discarded (unless you use a volume).

For data engineering: our pipeline code is packaged into Docker images. When Airflow triggers a pipeline, it starts a container from that image, the pipeline runs, and the container exits. The image in Artifact Registry is immutable and versioned — you can always roll back to a previous image version if a deployment breaks something.

---

**Q4. How do you handle secrets and credentials in a data pipeline? What are the antipatterns?**

Every credential in CDM Next was stored in Secret Manager — no exceptions. Database passwords, API keys, JDBC connection strings, service account keys (when Workload Identity wasn't available).

Pipeline code fetches secrets at runtime: `secretmanager.access_secret_version()`. The secret value is held in memory for the lifetime of the process and never written to disk, logs, or environment files. We used `@lru_cache` on the fetch function to avoid repeated API calls within a single run.

Antipatterns I've seen and explicitly prevented in CDM Next: hardcoded credentials in DAG files (DAGs are stored in GCS, publicly readable within the project); credentials in environment variables set in Airflow's UI (stored in the metadata database in plaintext in older Airflow versions); logging credentials in error messages (easy to do accidentally when including exception detail). We enforced a bandit security scan in CI that flagged common credential patterns.

The gold standard for GKE and Cloud Run: Workload Identity Federation. The pod/service authenticates as a GCP service account without any key file at all — the workload's identity is bound to the SA via IAM. Nothing to rotate, nothing to leak.

---

**Q5. Explain Docker layer caching and why it matters for data pipeline images.**

Docker builds images layer by layer. Each instruction in a Dockerfile creates a layer. Docker caches layers and only rebuilds from the first changed layer onward. This makes rebuilds fast when only application code changes.

The key principle: order Dockerfile instructions from least-frequently-changed to most-frequently-changed. System packages (apt-get) change very rarely — put them first. Python dependencies (pip install -r requirements.txt) change when a library is upgraded — put them before the application code. Application code changes on every commit — put it last.

Bad order (slow builds):
```
COPY . .                          # copies all code — invalidates cache on every commit
RUN pip install -r requirements.txt  # reinstalls ALL packages every commit
```

Good order (fast builds):
```
COPY requirements.txt .           # only changes when deps change
RUN pip install -r requirements.txt  # cached unless requirements.txt changes
COPY pipelines/ ./pipelines/      # changes on every commit, but layer above is cached
```

In CDM Next with 60+ pipelines, fast Docker builds (30 seconds vs 8 minutes) significantly reduced feedback loop time for developers.

---

**Q6. What is Kubernetes and when would a data engineer need to know it?**

Kubernetes is a container orchestration system that manages running, scaling, and recovering containerised workloads across a cluster of machines. For data engineers, the scenarios where Kubernetes knowledge matters: running batch pipeline jobs as Kubernetes Jobs (instead of Dataflow or Composer), deploying custom ingestion services (API scrapers, CDC consumers) as Deployments, running feature engineering or ML training jobs as Jobs on GPU nodes, and debugging issues with Airflow on GKE (Cloud Composer runs on GKE).

The concepts data engineers use most: `kubectl logs` to see what happened in a pipeline container; `kubectl describe pod` to see why a pod failed to start (image pull failure, insufficient resources, secret not found); `kubectl get jobs` to see the status of batch jobs; resource requests and limits to ensure pipeline containers get the memory they need without evicting other workloads.

In CDM Next, most pipelines ran via Cloud Composer orchestrating BigQuery and Dataflow jobs. But our custom Oracle CDC consumer ran as a Kubernetes Deployment on GKE — it was a long-running process that Composer's task model didn't fit well. I needed to be able to debug pod crashes and rolling update deployments.

---

**Q7. How do you structure Python code for a data pipeline to make it testable?**

Testability requires two principles: pure functions (no hidden state, inputs and outputs are explicit) and dependency injection (don't create dependencies inside functions — pass them in).

Bad (untestable): the function creates its own BigQuery client internally, making it impossible to mock.
```python
def load_to_bq(data):
    client = bigquery.Client()   # can't mock this
    client.insert_rows_json("project.dataset.table", data)
```

Good (testable): dependencies injected, function is pure.
```python
def load_to_bq(data: list, table: str, client: bigquery.Client) -> int:
    errors = client.insert_rows_json(table, data)
    if errors:
        raise LoadError(f"Failed to load {len(errors)} rows: {errors}")
    return len(data)

# In tests:
mock_client = MagicMock()
mock_client.insert_rows_json.return_value = []
result = load_to_bq([{"id": 1}], "project.dataset.table", mock_client)
assert result == 1
mock_client.insert_rows_json.assert_called_once()
```

In CDM Next we structured pipelines as: `Extractor` class (source abstraction), `Transformer` class (pure functions), `Loader` class (target abstraction), and a `Pipeline` orchestrator that wired them together. Each class received its dependencies (BQ client, GCS client, config) via constructor injection. This meant we could test extraction logic against a mock DB, transformation logic without any GCP calls, and loader logic with a mock BQ client — fast, reliable unit tests with zero network calls.

---

**Q8. What is a Terraform module and why do you use them?**

A Terraform module is a reusable, parameterised block of Terraform configuration. Instead of copying the same BQ dataset + IAM + GCS resource definitions for every application team, you write a module once and call it with different parameters.

```hcl
module "finance_team" {
  source      = "./modules/cdm_team_onboarding"
  team_name   = "finance"
  project_id  = var.project_id
  source_type = "teradata"
  data_classification = "confidential"
  team_group  = "finance-analysts@company.com"
}

module "risk_team" {
  source      = "./modules/cdm_team_onboarding"
  team_name   = "risk"
  project_id  = var.project_id
  source_type = "oracle"
  data_classification = "restricted"
  team_group  = "risk-analysts@company.com"
}
```

Each module call creates a consistent set of resources (dataset, SA, IAM, GCS prefix, secret). All 60+ teams in CDM Next were onboarded via this module. New team onboarding was a 15-minute process: add a module block, run `terraform apply`, pipeline infrastructure ready.

Benefits: consistency (all teams get identical resource structure), maintainability (fix a security policy once in the module, applies to all 60+ teams on next apply), code review (infra changes are visible as code diffs, not console screenshots).

---

*End of DevOps & Engineering Practices Q&A*
