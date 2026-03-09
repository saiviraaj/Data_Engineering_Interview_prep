# DevOps & Engineering Practices for Data — Complete Textbook
### CI/CD, Terraform, Docker, Kubernetes, and Production Engineering

---

## CHAPTER 1: CI/CD FOR DATA PIPELINES

### 1.1 Why CI/CD Matters for Data Engineering

Traditional software CI/CD deploys application code. Data engineering CI/CD deploys: pipeline code (DAGs, Spark jobs, Python transforms), infrastructure (BigQuery datasets, GCS buckets, IAM policies via Terraform), configuration (pipeline configs, schema registries), and SQL (DDL for tables, views, stored procedures).

Without CI/CD, a data team manually deploys DAG files, runs Terraform commands from laptops, and has no automated safety net. A typo in a DAG, a wrong IAM policy, or an incorrect table schema reaches production and breaks live pipelines.

### 1.2 CI/CD Pipeline Stages for Data Engineering

```
1. TRIGGER         Push to PR branch or merge to main
       ↓
2. LINT            flake8, black, pylint for Python; sqlfluff for SQL
       ↓
3. UNIT TEST       pytest for Python functions; DAG import tests
       ↓
4. INTEGRATION TEST  BQ/GCS sandbox tests (small datasets)
       ↓
5. TERRAFORM PLAN  Show infra changes — reviewed by engineer
       ↓
6. BUILD           Package Python jobs; build Docker images
       ↓
7. DEPLOY TO DEV   Terraform apply (dev); deploy DAGs to dev Composer
       ↓
8. DEPLOY TO STAGING  Terraform apply (staging); DAGs to staging Composer
       ↓
9. MANUAL APPROVAL  Required for production deployments
       ↓
10. DEPLOY TO PROD  Terraform apply (prod); DAGs to prod Composer
```

### 1.3 GitHub Actions Workflow for Data Pipelines

```yaml
# .github/workflows/pipeline_ci_cd.yml
name: Data Pipeline CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PROJECT_ID: wf-cdm-prod
  GCP_REGION: us-central1
  COMPOSER_BUCKET: gs://wf-composer-dags-prod

jobs:
  lint-and-test:
    name: Lint and Unit Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with: {python-version: '3.11'}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Lint Python (flake8)
        run: flake8 dags/ pipelines/ tests/ --max-line-length=100

      - name: Format check (black)
        run: black --check dags/ pipelines/ tests/

      - name: Lint SQL (sqlfluff)
        run: sqlfluff lint sql/ --dialect bigquery

      - name: Unit tests
        run: pytest tests/unit/ -v --cov=pipelines --cov-report=xml

      - name: DAG import tests
        run: pytest tests/dags/ -v

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with: {files: coverage.xml}

  terraform-plan:
    name: Terraform Plan
    runs-on: ubuntu-latest
    needs: lint-and-test
    steps:
      - uses: actions/checkout@v3

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        with: {terraform_version: 1.6.0}

      - name: Terraform Init
        run: terraform init
        working-directory: terraform/

      - name: Terraform Plan
        run: terraform plan -var="project=$PROJECT_ID" -out=tfplan
        working-directory: terraform/

      - name: Upload plan artifact
        uses: actions/upload-artifact@v3
        with: {name: tfplan, path: terraform/tfplan}

  deploy-prod:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [lint-and-test, terraform-plan]
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://console.cloud.google.com/composer
    steps:
      - uses: actions/checkout@v3

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY_PROD }}

      - name: Download Terraform plan
        uses: actions/download-artifact@v3
        with: {name: tfplan, path: terraform/}

      - name: Terraform Apply
        run: terraform apply tfplan
        working-directory: terraform/

      - name: Deploy DAGs to Composer
        run: |
          gsutil -m cp -r dags/ $COMPOSER_BUCKET/dags/

      - name: Deploy pipeline configs
        run: |
          gsutil -m cp -r configs/ gs://wf-cdm-configs/pipeline-configs/

      - name: Notify Slack
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: "CDM Next deployment to production: ${{ job.status }}"
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### 1.4 Environment Promotion Strategy

```
DEVELOPMENT (wf-cdm-dev)
  Purpose: Engineers develop and test new pipelines
  Data: Anonymised sample (1% of production, synthetic PII)
  Deployment: auto-deploy on every push to feature branch
  Access: all DE team members

STAGING (wf-cdm-staging)
  Purpose: Integration testing, UAT with application teams
  Data: Production-like data (recent 30 days, masked)
  Deployment: auto-deploy on merge to develop branch
  Access: DE team + application team leads

PRODUCTION (wf-cdm-prod)
  Purpose: Live workloads serving 60+ teams
  Data: Full production data
  Deployment: manual approval required, deploy from main branch only
  Access: restricted SA keys; no developer direct access to run jobs
```

---

## CHAPTER 2: TERRAFORM FOR GCP DATA INFRASTRUCTURE

### 2.1 Infrastructure as Code Principles

Infrastructure as Code (IaC) means your GCP resources — BigQuery datasets, GCS buckets, IAM policies, Composer environments — are defined in version-controlled Terraform files, not created manually in the console.

Benefits: reproducibility (dev/staging/prod are identical by construction), auditability (every infra change has a PR, reviewer, and commit), disaster recovery (entire environment can be rebuilt from Terraform state), drift detection (Terraform plan shows any manual changes).

### 2.2 Terraform Project Structure for Data Engineering

```
terraform/
├── main.tf                   # Provider config, backend state
├── variables.tf              # Input variable declarations
├── outputs.tf                # Output values
├── terraform.tfvars          # Variable values per environment
├── modules/
│   ├── bigquery/             # BigQuery datasets, tables, views
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── gcs/                  # GCS buckets and lifecycle rules
│   ├── iam/                  # IAM bindings and service accounts
│   ├── composer/             # Cloud Composer environment
│   └── networking/           # VPC, subnets, VPC SC
└── environments/
    ├── dev/
    ├── staging/
    └── prod/
```

### 2.3 Key Terraform Resources for Data Engineering

```hcl
# BigQuery Dataset
resource "google_bigquery_dataset" "finance_prod" {
  dataset_id  = "finance_prod"
  project     = var.project_id
  location    = var.region
  description = "Production financial data — CDM Next migrated"

  labels = {
    env        = var.environment
    team       = "data-platform"
    domain     = "finance"
    managed_by = "terraform"
  }

  # 7-year default table expiration for regulatory compliance
  default_table_expiration_ms = 220752000000  # 7 years in ms

  access {
    role          = "OWNER"
    user_by_email = "cdm-platform-sa@${var.project_id}.iam.gserviceaccount.com"
  }
  access {
    role           = "READER"
    group_by_email = "finance-analysts@company.com"
  }
}

# BigQuery Table with schema
resource "google_bigquery_table" "orders" {
  dataset_id = google_bigquery_dataset.finance_prod.dataset_id
  table_id   = "orders"
  project    = var.project_id

  description = "Daily customer orders migrated from Teradata FINANCE_DB.ORDERS"

  time_partitioning {
    type  = "DAY"
    field = "order_date"
    expiration_ms = 220752000000  # 7 years
  }

  clustering = ["account_id", "transaction_type"]

  schema = jsonencode([
    {name = "order_id",         type = "STRING",    mode = "REQUIRED"},
    {name = "account_id",       type = "STRING",    mode = "REQUIRED"},
    {name = "order_date",       type = "DATE",      mode = "REQUIRED"},
    {name = "amount",           type = "NUMERIC",   mode = "NULLABLE"},
    {name = "transaction_type", type = "STRING",    mode = "NULLABLE"},
    {name = "status",           type = "STRING",    mode = "NULLABLE"},
    {name = "created_at",       type = "TIMESTAMP", mode = "NULLABLE"}
  ])

  labels = {
    managed_by = "terraform"
    data_classification = "confidential"
  }
}

# GCS Bucket for staging
resource "google_storage_bucket" "cdm_staging" {
  name          = "${var.project_id}-cdm-staging"
  project       = var.project_id
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true   # enforce bucket-level IAM (no ACLs)

  versioning {
    enabled = false  # no versioning for transient staging data
  }

  lifecycle_rule {
    condition { age = 7 }  # delete staging files after 7 days
    action    { type = "Delete" }
  }

  labels = {
    managed_by = "terraform"
    purpose    = "cdm-staging"
  }
}

# Service Account for pipeline
resource "google_service_account" "pipeline_finance" {
  account_id   = "cdm-pipeline-finance"
  display_name = "CDM Finance Migration Pipeline"
  project      = var.project_id
}

# IAM binding: SA can write to staging dataset
resource "google_bigquery_dataset_iam_member" "pipeline_staging_editor" {
  dataset_id = google_bigquery_dataset.finance_staging.dataset_id
  project    = var.project_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.pipeline_finance.email}"
}

# IAM binding: SA can read from source dataset
resource "google_bigquery_dataset_iam_member" "pipeline_source_viewer" {
  dataset_id = google_bigquery_dataset.finance_source.dataset_id
  project    = var.project_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.pipeline_finance.email}"
}

# Secret for DB credentials
resource "google_secret_manager_secret" "teradata_creds" {
  secret_id = "tdprod-finance-credentials"
  project   = var.project_id

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_iam_member" "pipeline_secret_access" {
  secret_id = google_secret_manager_secret.teradata_creds.secret_id
  project   = var.project_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.pipeline_finance.email}"
}
```

### 2.4 Terraform State Management

```hcl
# backend.tf — store state in GCS (not local filesystem)
terraform {
  backend "gcs" {
    bucket = "wf-cdm-terraform-state"
    prefix = "terraform/state/prod"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}
```

```bash
# Key Terraform commands
terraform init          # initialise — download providers, configure backend
terraform plan          # show what will change (always review before apply)
terraform apply         # apply changes (prompted for approval)
terraform apply -auto-approve   # no prompt (use in CI/CD only)
terraform destroy       # destroy all resources (DANGEROUS)
terraform state list    # list all managed resources
terraform state show google_bigquery_dataset.finance_prod  # inspect resource
terraform import google_bigquery_dataset.existing project:dataset  # import existing resource
```

---

## CHAPTER 3: DOCKER FOR DATA ENGINEERING

### 3.1 Why Docker Matters for Data Engineers

Docker packages your code + dependencies + Python version into a portable, reproducible image. The key problem it solves: "it works on my laptop but not in production" — because both environments use the identical image.

For data engineering: Dataflow custom jobs run in Docker containers. Cloud Run ingestion jobs are Docker containers. Spark on Dataproc Serverless can use custom Docker images. Local development environments are Docker-based.

### 3.2 Writing a Dockerfile for a Data Pipeline

```dockerfile
# Dockerfile for a BigQuery ETL pipeline
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies first (Docker layer caching — this layer
# only rebuilds if system deps change, which is rare)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (separate layer from app code —
# rebuilds only when requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code last (most frequently changed layer)
COPY pipelines/ ./pipelines/
COPY configs/ ./configs/

# Non-root user for security (never run data pipelines as root)
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO

# Entry point
ENTRYPOINT ["python", "-m", "pipelines.main"]
CMD ["--help"]
```

```
# requirements.txt for a GCP data pipeline
google-cloud-bigquery==3.13.0
google-cloud-storage==2.13.0
google-cloud-secret-manager==2.19.0
google-cloud-dlp==3.12.0
google-cloud-pubsub==2.19.0
apache-airflow-providers-google==10.11.0
pandas==2.1.4
pyarrow==14.0.1
teradatasql==17.20.0.27    # Teradata JDBC
cx-Oracle==8.3.0           # Oracle client
great-expectations==0.18.8
tenacity==8.2.3
pydantic==2.5.2
```

### 3.3 Docker Compose for Local Development

```yaml
# docker-compose.yml — local dev environment
version: '3.8'

services:
  pipeline:
    build: .
    volumes:
      - ./pipelines:/app/pipelines   # hot-reload code changes
      - ./configs:/app/configs
      - ~/.config/gcloud:/home/appuser/.config/gcloud  # share GCP credentials
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/home/appuser/.config/gcloud/application_default_credentials.json
      - GCP_PROJECT=wf-cdm-dev
      - ENVIRONMENT=development
      - LOG_LEVEL=DEBUG
    command: ["--source=teradata", "--table=CUSTOMER_MASTER", "--dry-run"]

  # Local Airflow for DAG development
  airflow-webserver:
    image: apache/airflow:2.8.0
    ports: ["8080:8080"]
    environment:
      - AIRFLOW__CORE__EXECUTOR=LocalExecutor
      - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres/airflow
    volumes:
      - ./dags:/opt/airflow/dags
    depends_on: [postgres]
    command: webserver

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### 3.4 Building and Pushing to Artifact Registry

```bash
# Authenticate Docker to GCP Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build image with specific tag
docker build -t us-central1-docker.pkg.dev/wf-cdm-prod/cdm-images/pipeline:v1.2.3 .
docker build -t us-central1-docker.pkg.dev/wf-cdm-prod/cdm-images/pipeline:latest .

# Push both tags
docker push us-central1-docker.pkg.dev/wf-cdm-prod/cdm-images/pipeline:v1.2.3
docker push us-central1-docker.pkg.dev/wf-cdm-prod/cdm-images/pipeline:latest

# In CI/CD: build and push in one step
export IMAGE=us-central1-docker.pkg.dev/$PROJECT/cdm-images/pipeline
docker build -t $IMAGE:$GITHUB_SHA -t $IMAGE:latest .
docker push $IMAGE:$GITHUB_SHA
docker push $IMAGE:latest
```

---

## CHAPTER 4: KUBERNETES FOR DATA ENGINEERING

### 4.1 Kubernetes Concepts (What Data Engineers Need)

You don't need to be a Kubernetes expert, but you need to understand enough to deploy and debug data workloads.

```
CLUSTER        A set of machines (nodes) running containerised workloads
NODE           A single machine (VM) in the cluster
POD            Smallest deployable unit — one or more containers
DEPLOYMENT     Manages a set of identical pods; handles restarts, scaling
JOB            Run a pod to completion (not continuously) — batch processing
CRONJOB        Schedule a Job on a cron expression
NAMESPACE      Logical isolation within a cluster (dev, staging, prod)
SERVICE        Stable network endpoint pointing to a set of pods
CONFIGMAP      Non-sensitive config data injected into pods
SECRET         Sensitive data (credentials) injected into pods
                (In GCP: use External Secrets to pull from Secret Manager)
```

### 4.2 Running a Data Pipeline as a Kubernetes Job

```yaml
# k8s/jobs/finance-migration-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: finance-migration-2024-01-15
  namespace: cdm-prod
  labels:
    app: cdm-pipeline
    team: data-platform
    domain: finance
spec:
  backoffLimit: 3           # retry 3 times on failure
  activeDeadlineSeconds: 14400  # 4-hour timeout
  template:
    spec:
      serviceAccountName: cdm-pipeline-sa  # Workload Identity SA
      restartPolicy: OnFailure

      containers:
        - name: migration
          image: us-central1-docker.pkg.dev/wf-cdm-prod/cdm-images/pipeline:v1.2.3
          command: ["python", "-m", "pipelines.migrate"]
          args:
            - "--source=teradata"
            - "--table=FINANCE_DB.CUSTOMER_MASTER"
            - "--date=2024-01-15"

          resources:
            requests:
              cpu: "2"
              memory: "4Gi"
            limits:
              cpu: "4"
              memory: "8Gi"

          env:
            - name: GCP_PROJECT
              value: "wf-cdm-prod"
            - name: ENVIRONMENT
              value: "production"
            - name: LOG_LEVEL
              value: "INFO"

          # Inject secrets from Secret Manager via External Secrets operator
          envFrom:
            - secretRef:
                name: teradata-credentials   # K8s Secret synced from GCP Secret Manager
```

### 4.3 Useful kubectl Commands

```bash
# See pods in a namespace
kubectl get pods -n cdm-prod

# See jobs
kubectl get jobs -n cdm-prod

# Describe a pod (shows events, resource limits, status)
kubectl describe pod finance-migration-xxxxx -n cdm-prod

# Get logs from a pod
kubectl logs finance-migration-xxxxx -n cdm-prod
kubectl logs finance-migration-xxxxx -n cdm-prod --previous  # logs from crashed container

# Execute into a running pod (debugging)
kubectl exec -it finance-migration-xxxxx -n cdm-prod -- /bin/bash

# Delete a failed job and all its pods
kubectl delete job finance-migration-2024-01-15 -n cdm-prod

# Watch pods in real time
kubectl get pods -n cdm-prod --watch

# Check resource usage
kubectl top pods -n cdm-prod
```

---

## CHAPTER 5: SECRET AND CREDENTIAL MANAGEMENT

### 5.1 Secret Manager Integration

```python
from google.cloud import secretmanager
from functools import lru_cache

@lru_cache(maxsize=None)
def get_secret(project_id: str, secret_id: str, version: str = "latest") -> str:
    """Fetch a secret from Secret Manager. Cached to avoid repeated API calls."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


def get_db_connection(project_id: str, secret_id: str):
    """Get DB credentials from Secret Manager and create connection."""
    import json
    creds = json.loads(get_secret(project_id, secret_id))
    return connect_to_db(
        host=creds["host"],
        port=creds["port"],
        database=creds["database"],
        user=creds["user"],
        password=creds["password"]
    )
```

### 5.2 What Never to Do With Secrets

```
NEVER hardcode credentials in code: password = "my-secret-password"
NEVER commit credentials to Git: even in .env files, even in private repos
NEVER log credentials: f"Connecting with {password}" in log messages
NEVER put credentials in Airflow DAG files: they're stored in GCS
NEVER pass credentials as command-line args: visible in process lists
NEVER use shared service account keys: one SA per pipeline
NEVER store secrets in BigQuery: even encrypted columns are queryable by those with access

ALWAYS use Secret Manager for credentials
ALWAYS use Workload Identity for GKE/Cloud Run (no key files at all)
ALWAYS rotate credentials on a schedule
ALWAYS audit secret access (Secret Manager logs all access)
```

---

## CHAPTER 6: MONITORING AND ALERTING INFRASTRUCTURE

### 6.1 Structured Logging

```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    """Produces JSON-structured logs compatible with Cloud Logging."""

    def __init__(self, pipeline_name: str, run_id: str):
        self.pipeline_name = pipeline_name
        self.run_id = run_id
        self._logger = logging.getLogger(pipeline_name)

    def _log(self, level: str, message: str, **kwargs):
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": level,
            "pipeline": self.pipeline_name,
            "run_id": self.run_id,
            "message": message,
            **kwargs
        }
        print(json.dumps(record))  # Cloud Logging picks up stdout as structured JSON

    def info(self, msg: str, **ctx): self._log("INFO", msg, **ctx)
    def warning(self, msg: str, **ctx): self._log("WARNING", msg, **ctx)
    def error(self, msg: str, **ctx): self._log("ERROR", msg, **ctx)


# Usage
log = StructuredLogger("finance_migration", run_id="run-2024-01-15")
log.info("Starting extraction", source_table="CUSTOMER_MASTER", expected_rows=1_234_567)
log.info("Extraction complete", rows_extracted=1_234_210, duration_seconds=342)
log.error("Validation failed", check="row_count", expected=1_234_567,
          actual=1_234_210, diff_pct=0.029)
```

### 6.2 Cloud Monitoring Alerting Policy (Terraform)

```hcl
# Alert when pipeline failure rate exceeds threshold
resource "google_monitoring_alert_policy" "pipeline_failure_alert" {
  display_name = "CDM Pipeline Failure Alert"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Pipeline failure rate > 5%"
    condition_threshold {
      filter          = "resource.type=\"global\" AND metric.type=\"logging.googleapis.com/user/cdm_pipeline_failures\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05
      duration        = "300s"   # alert if > 5% for 5 minutes
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.pagerduty.name,
    google_monitoring_notification_channel.slack.name,
  ]

  alert_strategy {
    auto_close = "86400s"  # auto-close after 24 hours
  }
}
```

---

## CHAPTER 7: CODE QUALITY AND BEST PRACTICES

### 7.1 Python Code Quality Tools

```
flake8          Style and lint: PEP8 compliance, unused imports, undefined names
black           Opinionated formatter: auto-formats code to consistent style
mypy            Static type checking: catches type errors before runtime
pylint          Comprehensive analysis: code smell, naming conventions
isort           Import sorting: consistent import organisation
bandit          Security scanning: finds common security issues
pre-commit      Run all checks automatically before every git commit
```

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks: [{id: black}]

  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks: [{id: flake8, args: [--max-line-length=100]}]

  - repo: https://github.com/PyCQA/isort
    rev: 5.12.0
    hooks: [{id: isort, args: [--profile=black]}]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks: [{id: mypy}]
```

### 7.2 Git Workflow for Data Teams

```
BRANCH STRATEGY (GitFlow adapted):
  main          Production code only. Protected. Requires PR + 2 approvals.
  develop       Integration branch. Auto-deploys to staging on merge.
  feature/*     Individual feature branches. Created from develop.
  hotfix/*      Emergency production fixes. Merged to main AND develop.

COMMIT CONVENTIONS:
  feat: add incremental extraction for Oracle sources
  fix: correct watermark drift in Teradata extractor
  chore: update BigQuery client to 3.13.0
  refactor: extract validation logic into separate module
  test: add unit tests for schema drift detection

PR CHECKLIST:
  □ Unit tests pass
  □ DAG import tests pass
  □ Terraform plan reviewed (if infra changes)
  □ No credentials in code
  □ Audit trail: new pipelines write to pipeline_audit table
  □ Runbook updated if operational procedure changed
```

---

*End of DevOps & Engineering Practices Textbook*
