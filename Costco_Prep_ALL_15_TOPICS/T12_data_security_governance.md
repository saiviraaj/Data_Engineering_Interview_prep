# Topic 12: Data Security & Governance
## Costco Sr. Data Engineer — Exhaustive Interview Textbook

---

## Table of Contents
1. [L1: Core Concepts — IAM, Encryption Basics](#l1-core-concepts)
2. [L2: Deep Technical Understanding](#l2-deep-technical-understanding)
3. [L3: Real-World Scenarios — Enterprise Data Security](#l3-real-world-scenarios)
4. [L4: Hands-On Implementation](#l4-hands-on-implementation)
5. [L5: Edge Cases & Pitfalls](#l5-edge-cases--pitfalls)
6. [L6: Interview Questions — Easy to Very Hard](#l6-interview-questions)

---

## L1: Core Concepts

### 1.1 Why Security Matters for Data Engineers

Data engineers are the custodians of the organization's most sensitive data: member PII, financial transactions, behavioral data, ad spend, competitive intelligence. A data breach caused by misconfigured BigQuery permissions or unmasked PII in a pipeline can result in regulatory fines, legal liability, and reputational damage.

**The security mindset for data engineers**:
- **Defense in depth**: multiple layers of controls, not just one
- **Principle of least privilege**: give the minimum permissions needed, nothing more
- **Data minimization**: don't store what you don't need
- **Fail secure**: when something goes wrong, default to more restrictive, not less
- **Auditability**: every data access should be traceable

---

### 1.2 The Three Pillars of Data Security

**1. Access Control (Who can see what?)**
- Authentication: proving you are who you say you are
- Authorization: controlling what authenticated users can do
- IAM roles, column-level security, row-level security

**2. Data Protection (How is data protected at rest and in transit?)**
- Encryption at rest (storage-level, key management)
- Encryption in transit (TLS)
- Data masking and tokenization

**3. Governance (Are we using data appropriately?)**
- Data lineage: where did this data come from?
- Data catalog: what data do we have and what does it mean?
- Compliance: GDPR, CCPA, HIPAA — specific regulatory requirements
- Audit logging: who accessed what, when, and how

---

### 1.3 Compliance Frameworks — What Data Engineers Must Know

**GDPR (General Data Protection Regulation)** — EU:
- Applies to any data about EU residents (even if company is in US)
- Key requirements: right to erasure, data minimization, purpose limitation, breach notification within 72 hours
- Data engineer implications: must be able to delete ALL records for a user on request, must document data flows, must have legal basis for processing

**CCPA (California Consumer Privacy Act)** — California:
- Similar to GDPR for California residents
- Right to know, right to delete, right to opt-out of sale
- Data engineer implications: must be able to identify and delete all data for a California resident

**PCI DSS** — Payment card data:
- Strict requirements for storing, processing, transmitting card data
- Data engineers should NEVER be storing raw card numbers — use tokenization

**HIPAA** — Health data (less relevant for MarTech, but worth knowing):
- Protected Health Information (PHI) has strict access and audit requirements

---

## L2: Deep Technical Understanding

### 2.1 GCP IAM — Complete Architecture

**IAM hierarchy**:
```
Organization
└── Folders (optional grouping)
    └── Projects
        └── Resources (BigQuery datasets, GCS buckets, etc.)
```

**Principal types**:
- `user:email@domain.com` — individual Google account
- `serviceAccount:name@project.iam.gserviceaccount.com` — application identity
- `group:team@domain.com` — Google Group (preferred for team access)
- `domain:costco.com` — all users in a domain
- `allAuthenticatedUsers` — any Google account (DANGEROUS — avoid)
- `allUsers` — completely public (EXTREMELY DANGEROUS — never use for data)

**IAM policy binding**:
```json
{
  "bindings": [
    {
      "role": "roles/bigquery.dataViewer",
      "members": [
        "group:analysts@costco.com",
        "serviceAccount:looker-sa@costco-prod.iam.gserviceaccount.com"
      ]
    },
    {
      "role": "roles/bigquery.dataEditor",
      "members": [
        "serviceAccount:dbt-pipeline-sa@costco-prod.iam.gserviceaccount.com"
      ]
    }
  ]
}
```

**Key BigQuery IAM roles**:

| Role | Permissions | Use For |
|------|------------|---------|
| `bigquery.admin` | Everything | Platform admins only |
| `bigquery.dataOwner` | Read/write/delete tables + manage access | Dataset owners |
| `bigquery.dataEditor` | Read + write tables | Pipeline service accounts |
| `bigquery.dataViewer` | Read tables | Analysts, BI tools |
| `bigquery.jobUser` | Run queries (must have dataViewer separately) | Query runners |
| `bigquery.user` | Run queries + create jobs | General users |

**Service account best practices**:
```python
# WRONG: pipeline uses your personal credentials
# WRONG: one service account for everything
# CORRECT: dedicated SA per pipeline with minimal permissions

# Example: DBT pipeline SA
# - bigquery.dataViewer on raw dataset (read sources)
# - bigquery.dataEditor on staging dataset (write staging tables)
# - bigquery.dataEditor on marts dataset (write mart tables)
# - storage.objectViewer on raw GCS bucket (read raw files)
# NOTHING ELSE

# Terraform config for least-privilege SA
resource "google_service_account" "dbt_pipeline" {
  account_id   = "dbt-pipeline-sa"
  display_name = "DBT Pipeline Service Account"
}

resource "google_bigquery_dataset_iam_binding" "dbt_staging_editor" {
  dataset_id = "staging"
  role       = "roles/bigquery.dataEditor"
  members    = ["serviceAccount:${google_service_account.dbt_pipeline.email}"]
}
```

---

### 2.2 Column-Level Security in BigQuery

Column-level security restricts access to specific columns — even if a user has table-level access, they can't see masked columns without explicit permission.

```sql
-- Step 1: Create a policy tag taxonomy in Data Catalog
-- Policy tags are hierarchical: PII > Email, PII > Phone, PII > SSN

-- Step 2: Assign policy tags to columns in BigQuery schema
-- Example: dim_members table
CREATE TABLE dim_members (
    member_id       STRING,
    first_name      STRING,
    last_name       STRING,
    -- These columns have policy tags attached:
    email           STRING,         -- tagged: PII/Email
    phone_number    STRING,         -- tagged: PII/Phone
    date_of_birth   DATE,           -- tagged: PII/DOB
    -- Non-PII columns (no tags, accessible to everyone with table access)
    loyalty_tier    STRING,
    zip_code        STRING,
    acquisition_channel STRING
);

-- Step 3: Assign fine-grained reader role to authorized principals
-- Data analysts: can see loyalty_tier, zip_code, acquisition_channel
-- → NOT email, phone, DOB (masked/error if accessed)

-- Data science team: can see hashed email (for ML), but not raw email
-- Marketing automation SA: can see email (to send campaigns)

-- BigQuery enforces: if user doesn't have policy tag permission,
-- the column returns NULL or throws an error

-- Step 4: Create a masked view for analysts
CREATE VIEW dim_members_masked AS
SELECT
    member_id,
    -- PII columns: masked for analysts, but this view shows them masked
    CONCAT(LEFT(email, 2), '***@***.com')   AS email_masked,
    CONCAT('***-***-', RIGHT(phone_number, 4)) AS phone_masked,
    -- Safe columns: accessible as-is
    loyalty_tier,
    zip_code,
    acquisition_channel
FROM dim_members;
-- Grant analysts access to this view, NOT the underlying table
```

---

### 2.3 Row-Level Security in BigQuery

Row-level security restricts which ROWS a user can see, not just columns.

```sql
-- Use case: regional data residency
-- US analysts can only see US member data
-- EU analysts can only see EU member data

-- Step 1: Create row access policy
CREATE ROW ACCESS POLICY us_only_policy
ON dim_members
GRANT TO ('group:us-analysts@costco.com')
FILTER USING (region = 'US');

CREATE ROW ACCESS POLICY eu_only_policy
ON dim_members
GRANT TO ('group:eu-analysts@costco.com')
FILTER USING (region = 'EU');

-- Admin sees all rows (no row access policy applies to them)

-- Use case 2: multi-tenant platform — each team sees only their data
CREATE ROW ACCESS POLICY team_data_isolation
ON mart_campaign_performance
GRANT TO ('serviceAccount:team-martech@project.iam.gserviceaccount.com')
FILTER USING (owning_team = 'martech');

-- Note: row access policies affect ALL queries on the table
-- Even COUNT(*) returns the count of rows the user CAN see
```

---

### 2.4 Data Masking and Tokenization

**Masking**: Replace sensitive data with a non-reversible representation.
```python
import hashlib
import hmac

# One-way hash (not reversible)
def mask_email(email: str, salt: str = "costco-secret-salt") -> str:
    """SHA256 hash of email — useful for matching without exposing email."""
    return hashlib.sha256(f"{salt}:{email.lower().strip()}".encode()).hexdigest()

# Format-preserving masking (keeps structure for testing)
def mask_phone(phone: str) -> str:
    """Keep last 4 digits, mask rest."""
    digits = ''.join(filter(str.isdigit, phone))
    return f"***-***-{digits[-4:]}" if len(digits) >= 4 else "***-***-****"

# For BigQuery: use Cloud DLP for automated PII detection and masking
```

**Tokenization**: Replace sensitive data with a randomly generated token that can be reversed (with the token vault).
```python
# Tokenization: email → token (reversible with vault lookup)
# Used when: need to match records across systems without sharing raw PII
# Example: match purchase_member_id to ad_click_member_id without exposing member_id

# Vault stores: token ↔ real_value mapping
# Pipeline stores: only tokens
# Authorized service can de-tokenize when needed
```

**Cloud DLP** — Google's PII detection and masking service:
```python
from google.cloud import dlp_v2

def scan_and_mask_with_dlp(data: list[dict]) -> list[dict]:
    """
    Use Cloud DLP to:
    1. Auto-detect PII in data
    2. Mask detected PII
    """
    dlp = dlp_v2.DlpServiceClient()

    inspect_config = dlp_v2.InspectConfig(
        info_types=[
            dlp_v2.InfoType(name="EMAIL_ADDRESS"),
            dlp_v2.InfoType(name="PHONE_NUMBER"),
            dlp_v2.InfoType(name="CREDIT_CARD_NUMBER"),
            dlp_v2.InfoType(name="US_SOCIAL_SECURITY_NUMBER"),
        ]
    )

    deidentify_config = dlp_v2.DeidentifyConfig(
        info_type_transformations=dlp_v2.InfoTypeTransformations(
            transformations=[
                dlp_v2.InfoTypeTransformations.InfoTypeTransformation(
                    info_types=[dlp_v2.InfoType(name="EMAIL_ADDRESS")],
                    primitive_transformation=dlp_v2.PrimitiveTransformation(
                        crypto_hash_config=dlp_v2.CryptoHashConfig(
                            crypto_key=dlp_v2.CryptoKey(
                                kms_wrapped=dlp_v2.KmsWrappedCryptoKey(
                                    wrapped_key=b"...",
                                    crypto_key_name="projects/.../cryptoKeyVersions/1"
                                )
                            )
                        )
                    )
                )
            ]
        )
    )

    # DLP deidentifies the content
    response = dlp.deidentify_content(
        request=dlp_v2.DeidentifyContentRequest(
            parent=f"projects/costco-project",
            deidentify_config=deidentify_config,
            inspect_config=inspect_config,
            item=dlp_v2.ContentItem(value=json.dumps(data))
        )
    )

    return json.loads(response.item.value)
```

---

### 2.5 Encryption — At Rest and In Transit

**Encryption at rest on GCP**:
```
All GCP services encrypt data at rest by default using Google-managed keys.

Three key management options:
1. Google-managed keys (GMEK) — default
   → Google handles key rotation, storage
   → Zero effort, good enough for most use cases

2. Customer-managed keys (CMEK) — KMS
   → You control the key (stored in Cloud KMS), Google uses it
   → If you rotate/delete your key, data is inaccessible
   → Required for some compliance frameworks (HIPAA, certain financial regs)

3. Customer-supplied keys (CSEK) — BYOK
   → You provide the key with each API call
   → Key never stored by Google
   → Maximum control, maximum operational burden
```

```python
# BigQuery with CMEK
from google.cloud import bigquery, kms

# Create KMS key for BigQuery encryption
kms_client = kms.KeyManagementServiceClient()
key_name = "projects/costco-project/locations/us/keyRings/bigquery-ring/cryptoKeys/bq-key"

# Create BigQuery dataset with CMEK
bq_client = bigquery.Client()
dataset = bigquery.Dataset("costco-project.sensitive_data")
dataset.default_encryption_configuration = bigquery.EncryptionConfiguration(
    kms_key_name=key_name
)
bq_client.create_dataset(dataset)

# Any table created in this dataset uses your KMS key automatically
```

**Encryption in transit**:
- All GCP APIs use TLS 1.3 by default
- Pub/Sub, BigQuery, GCS: all communication is encrypted in transit
- Internal network traffic within GCP: encrypted with AES-256
- No action required for GCP services — it's handled automatically
- For on-premises → GCP: use VPN or Cloud Interconnect (private network, no public internet)

---

### 2.6 Data Lineage

Data lineage tracks the journey of data from source to destination — enabling auditability, impact analysis, and debugging.

**Column-level lineage** (the gold standard):
```
Source: PostgreSQL.customers.email
    ↓ (Cloud Datastream CDC)
Raw: BigQuery.raw.customers.email
    ↓ (DBT staging model: SHA256 hash)
Staging: BigQuery.staging.stg_customers.email_hashed
    ↓ (DBT mart model: join + select)
Mart: BigQuery.marts.dim_members.email_hash
    ↓ (Looker: display in CRM dashboard)
Dashboard: Member CRM Dashboard → Email (masked)
```

**Tools for lineage in GCP**:

1. **Dataplex Lineage** (automatic for Dataflow + BigQuery):
```python
# Dataplex automatically records lineage when:
# - Dataflow reads from BigQuery/GCS and writes to BigQuery/GCS
# - BigQuery scheduled queries run
# Manual lineage for custom pipelines:

from google.cloud import datacatalog_lineage_v1

lineage_client = datacatalog_lineage_v1.LineageClient()

# Record: Dataflow job transformed raw_clicks → stg_clicks
process = lineage_client.create_process(
    parent="projects/costco-project/locations/us",
    process=datacatalog_lineage_v1.Process(
        display_name="CDM Staging Transform",
        attributes={"pipeline": "cdm_ad_clicks_staging"}
    )
)

run = lineage_client.create_run(
    parent=process.name,
    run=datacatalog_lineage_v1.Run(
        display_name="2024-01-15 06:00 run",
        state=datacatalog_lineage_v1.Run.State.COMPLETED,
        start_time=start_ts, end_time=end_ts
    )
)

lineage_event = lineage_client.create_lineage_event(
    parent=run.name,
    lineage_event=datacatalog_lineage_v1.LineageEvent(
        sources=[datacatalog_lineage_v1.EntityReference(
            fully_qualified_name="bigquery:costco-project.raw.google_ads_clicks"
        )],
        targets=[datacatalog_lineage_v1.EntityReference(
            fully_qualified_name="bigquery:costco-project.staging.stg_ad_clicks"
        )]
    )
)
```

2. **DBT lineage** (automatic from `ref()` and `source()` calls):
```bash
# Generate lineage manifest
dbt docs generate

# View lineage DAG in browser
dbt docs serve
# → Shows full lineage from sources to marts with column-level documentation
```

---

### 2.7 Audit Logging

```python
# BigQuery audit logs: who ran what query, when, on which table

# Enable audit logs in GCP (Cloud Console or Terraform)
# DATA_READ: log all table reads
# DATA_WRITE: log all table writes/deletes
# ADMIN_READ: log schema/permission changes

# Query audit logs to investigate suspicious access
from google.cloud import bigquery

bq = bigquery.Client()
results = bq.query("""
    SELECT
        protopayload_auditlog.authenticationInfo.principalEmail AS user_email,
        protopayload_auditlog.resourceName AS resource,
        protopayload_auditlog.methodName AS method,
        timestamp AS access_time,
        protopayload_auditlog.servicedata_v1_bigquery.jobCompletedEvent.job.jobStatistics.totalBilledBytes / 1e9 AS gb_billed,
        JSON_EXTRACT_SCALAR(protopayload_auditlog.metadataJson, '$.jobChange.job.jobConfig.queryConfig.query') AS query_text
    FROM `costco-project.cloudaudit_googleapis_com_data_access_*`
    WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
      AND protopayload_auditlog.methodName LIKE '%bigquery%'
      AND protopayload_auditlog.resourceName LIKE '%sensitive_data%'  -- focus on sensitive datasets
    ORDER BY access_time DESC
    LIMIT 1000
""").result()

# Use cases for audit logs:
# - Security review: who accessed PII tables?
# - Cost review: which users ran the most expensive queries?
# - Compliance: was member data accessed by authorized users only?
# - Incident response: what queries ran before a data breach was detected?
```

---

## L3: Real-World Scenarios

### 3.1 Scenario: Securing a Multi-Tenant Data Platform

**Problem**: 60 application teams share one BigQuery project. Team A should not be able to see Team B's data.

**Solution architecture**:

```python
# 1. Separate datasets per team
# costco-data-platform.martech_raw    (only martech SA can read)
# costco-data-platform.martech_marts  (martech SA writes, martech analysts read)
# costco-data-platform.finance_raw    (only finance SA can read)
# costco-data-platform.finance_marts  (finance SA writes, finance analysts read)

# 2. Terraform: automate isolation per team
resource "google_bigquery_dataset_iam_binding" "team_dataset_isolation" {
  for_each   = var.teams
  dataset_id = "${each.key}_marts"
  role       = "roles/bigquery.dataViewer"
  members    = ["group:${each.key}-analysts@costco.com"]
}

# 3. Shared dimension tables: read-only access for all
resource "google_bigquery_dataset_iam_binding" "shared_dims_read" {
  dataset_id = "shared_dimensions"
  role       = "roles/bigquery.dataViewer"
  members    = ["domain:costco.com"]  # all Costco users
}

# 4. Audit: weekly report of cross-team data access attempts
# (someone from finance accessing martech tables = security alert)
```

---

### 3.2 Scenario: GDPR Right-to-Erasure Pipeline

**Problem**: When a Costco member requests data deletion (GDPR Article 17), ALL their data across ALL systems must be deleted within 30 days.

**Challenge**: Member data exists in 20+ BigQuery tables, GCS files, Pub/Sub backlog, ML model training data, and backup snapshots.

```python
# Data deletion request handler

class GDPRDataEraser:
    def __init__(self, member_id: str, request_id: str):
        self.member_id = member_id
        self.request_id = request_id
        self.bq = bigquery.Client()

    def execute_deletion(self):
        """Orchestrate deletion across all systems."""
        results = {}

        # 1. BigQuery operational tables
        tables_to_clean = [
            ("raw.ad_clicks", "user_id"),
            ("raw.conversions", "user_id"),
            ("staging.stg_members", "member_id"),
            ("marts.dim_members", "member_id"),
            ("marts.fact_ad_clicks", "member_sk"),
        ]

        for table, key_col in tables_to_clean:
            count = self._delete_from_bq(table, key_col)
            results[table] = count

        # 2. GCS raw files (cannot delete individual rows — replace with nulled version)
        # This is why column-level masking at ingest is better than post-hoc deletion
        self._mask_in_gcs_files(self.member_id)

        # 3. ML training datasets — rebuild without this member
        # (flag for next training cycle)
        self._flag_for_ml_retraining()

        # 4. Audit trail: log that erasure was completed
        self._log_erasure_completion(results)

        return results

    def _delete_from_bq(self, table: str, key_col: str) -> int:
        """Delete all rows for member_id from a BigQuery table."""
        result = self.bq.query(f"""
            DELETE FROM `{table}`
            WHERE {key_col} = '{self.member_id}'
        """).result()

        # Return count of deleted rows
        row_count = list(self.bq.query(f"""
            SELECT @@row_count AS deleted_count
        """).result())[0].deleted_count

        return row_count

    def _log_erasure_completion(self, results: dict):
        """GDPR requires proof that erasure was executed."""
        self.bq.query(f"""
            INSERT INTO governance.gdpr_erasure_log VALUES (
                '{self.request_id}',
                '{self.member_id}',
                CURRENT_TIMESTAMP(),
                'COMPLETED',
                '{json.dumps(results)}'
            )
        """).result()
```

**Proactive design to simplify GDPR deletion**:
```sql
-- BETTER APPROACH: pseudonymization from the start
-- Store member_id (opaque ID) everywhere, not PII directly
-- PII (email, name, phone) only in one dimension table
-- When member requests deletion: delete from ONE table
-- All fact tables become orphaned records (no PII attached)

-- dim_members: email, phone, name, address → DELETE one row
-- fact_ad_clicks: member_id (FK) → orphaned, no PII exposed
-- mart_campaign_performance: aggregated, no member_id at all → untouched
```

---

## L4: Hands-On Implementation

### 4.1 Implement Column-Level Masking in a DBT Model

```sql
-- models/staging/stg_members.sql
-- Apply masking at the staging layer — PII never flows into marts unmasked

{{
    config(materialized='view')
}}

SELECT
    member_id,
    acquisition_channel,
    loyalty_tier,
    zip_code,
    region,

    -- PII columns: masked in staging
    -- Only authorized roles/SAs see unmasked values via policy tags on dim_members

    {% if target.name == 'prod_pii' %}
        -- Special target for ML/analytics that legitimately needs PII
        email,
        phone_number
    {% else %}
        -- Default: hash PII for all other environments
        TO_HEX(SHA256(LOWER(TRIM(email))))          AS email_hash,
        TO_HEX(SHA256(REGEXP_REPLACE(phone_number, '[^0-9]', ''))) AS phone_hash
    {% endif %}

FROM {{ source('members', 'raw_profiles') }}
WHERE is_active = TRUE
  AND email_marketing_opt_in = TRUE  -- only include opted-in members for marketing pipelines
```

---

## L5: Edge Cases & Pitfalls

### 5.1 Over-Permissioning — The Most Common Security Mistake

```python
# MISTAKE: pipeline service account gets project-wide owner role
# "It was easier to set up and we'll tighten it later"
# "Later" never comes

# Result: if the service account key is compromised:
# Attacker can read ALL data across ALL datasets
# Attacker can delete ALL tables
# Attacker can exfiltrate 15 PB of sensitive member data

# RULE: start with the minimum permission, add more only when needed
# It's much easier to add permissions than to clean up after a breach

# Detection: audit over-permissioned service accounts
resource "google_project_iam_audit_config" "detect_overperm" {
  project = "costco-prod"
  service = "allServices"
  audit_log_config {
    log_type = "ADMIN_READ"  # who is changing permissions
  }
}

# Monthly review: list all bindings and flag any owner/editor on prod project
gcloud projects get-iam-policy costco-prod --format=json | \
  jq '.bindings[] | select(.role == "roles/owner" or .role == "roles/editor")'
```

### 5.2 Unencrypted PII in Pipeline Logs

```python
# MISTAKE: logging raw PII values during pipeline execution
logger.info(f"Processing member {member_id}: email={email}, phone={phone}")
# This PII is now in Cloud Logging, visible to anyone with logging.read permission
# AND retained in logs for 30 days by default

# CORRECT: never log PII; log only IDs and metadata
logger.info(f"Processing member_id={member_id}, email_hash={sha256(email)[:8]}...")
# Or: log structured data, mark PII fields as sensitive
from google.cloud.logging import Logger
logger.info("Processing member", extra={
    "member_id": member_id,          # safe: opaque ID
    "email_hash_prefix": sha256(email)[:8],  # safe: truncated hash
    # NO: "email": email  ← DO NOT LOG
})
```

### 5.3 Public BigQuery Datasets

```python
# DANGER: accidentally making a BigQuery dataset public
# This has happened to many companies (PII exposed to internet)

# Prevention: deny allUsers and allAuthenticatedUsers at org level
resource "google_organization_policy" "deny_public_access" {
  org_id     = var.org_id
  constraint = "iam.allowedPolicyMemberDomains"
  list_policy {
    allow {
      values = ["C0xxxxxx"]  # only your Google Workspace domain
    }
  }
}

# Detection: audit check for public datasets
gcloud asset search-all-iam-policies \
  --scope="projects/costco-prod" \
  --query="policy:allUsers OR policy:allAuthenticatedUsers"
# If this returns any results → SECURITY ISSUE, fix immediately
```

---

## L6: Interview Questions — Easy to Very Hard

### EASY

**Q1: What is the principle of least privilege and how do you apply it in BigQuery?**

**Answer**: Principle of least privilege means giving each user or service account only the minimum permissions needed to perform their function — nothing more.

In BigQuery: A DBT pipeline service account needs to read from source datasets and write to staging/mart datasets. So I grant it `bigquery.dataViewer` on source datasets and `bigquery.dataEditor` on staging/mart datasets — not `bigquery.admin` or project-level `Editor`. If the service account key is compromised, the blast radius is limited to the datasets it specifically had access to.

For human users: analysts get `bigquery.dataViewer` on mart tables (they read, don't write). They don't get access to raw tables containing PII. Senior engineers get dataEditor on their team's datasets. Only the platform team gets broader permissions, and even those are scoped to specific projects.

I also apply this to column-level access: PII columns (email, phone) are tagged with policy tags and only accessible to service accounts that have a specific business need (e.g., the email marketing SA).

---

### MEDIUM

**Q2: What is data lineage and why is it important for data governance?**

**Answer**: Data lineage tracks the full journey of data — from where it originated (source system), through every transformation (staging, intermediate, mart), to where it's consumed (dashboards, APIs, ML models).

It's important for several reasons:

**Impact analysis**: If I need to change the schema of `fact_ad_clicks`, lineage tells me exactly which downstream models, dashboards, and APIs will break. Without lineage, you discover breakages after deployment.

**Debugging**: "Why does this ROAS number look wrong?" — lineage lets me trace from the dashboard back to the raw source, identifying at which transformation step the wrong value was introduced.

**Compliance**: Regulators (GDPR) may ask "show me every place this member's email address appears and how it was processed." Without lineage, this audit is a manual nightmare.

**Auditability**: "When was this calculation changed and by whom?" — lineage combined with Git history answers this.

On GCP: Dataplex provides automatic lineage for Dataflow and BigQuery jobs. DBT provides lineage through its `ref()` and `source()` DAG. For maximum coverage, I configure both and store the combined lineage metadata in Data Catalog.

---

### HARD

**Q3: A data analyst reports that they can query a BigQuery table containing member email addresses, even though you thought they only had access to the masked view. How do you investigate and fix this?**

**Answer**:

**Step 1: Verify the reported access**
```python
# Check what the analyst can actually access
# Run this AS the analyst using impersonation (admin privilege required)
bq query --impersonate_service_account=analyst@costco.com \
  "SELECT email FROM dim_members LIMIT 1"
# If this returns data: confirmed, analyst has unexpected access
```

**Step 2: Check IAM bindings on the dim_members table**
```bash
bq get-iam-policy costco-prod:marts.dim_members
# Look for the analyst's email or group in the bindings
```

**Step 3: Check dataset-level IAM** (table IAM inherits from dataset)
```bash
bq get-iam-policy --format=json costco-prod:marts
# Analyst may have been added to the dataset level, not just the view
```

**Step 4: Check if column-level security is configured**
- Are policy tags applied to the `email` column?
- Does the analyst have the `datacatalog.categoryFineGrainedReader` role on the PII policy tag?

**Root causes by likelihood**:
1. Analyst was granted `bigquery.dataViewer` on the `marts` dataset (not just the masked view) → they can see all tables in marts including dim_members
2. Policy tags weren't applied to the email column
3. Someone added the analyst to an overly broad group (e.g., `costco-engineers@costco.com`) that has dataset access

**Fix**:
1. Revoke analyst's direct dataset access
2. Grant access ONLY to the specific masked view: `bq add-iam-policy-binding --table costco-prod:marts.dim_members_masked --member user:analyst@costco.com --role roles/bigquery.dataViewer`
3. Apply policy tags to PII columns on dim_members to add defense in depth
4. Add monitoring alert: any query on `dim_members` by non-privileged accounts → Slack alert

**Post-fix audit**:
```sql
-- Check audit logs for how long this access existed and what was queried
SELECT timestamp, protopayload_auditlog.authenticationInfo.principalEmail, 
       JSON_EXTRACT_SCALAR(protopayload_auditlog.metadataJson, '$.jobChange.job.jobConfig.queryConfig.query') AS query
FROM `cloudaudit_googleapis_com_data_access_*`
WHERE protopayload_auditlog.resourceName LIKE '%dim_members%'
  AND protopayload_auditlog.authenticationInfo.principalEmail = 'analyst@costco.com'
ORDER BY timestamp;
```

---

### VERY HARD

**Q4: Design a complete data security architecture for Costco's MarTech BigQuery platform that handles: GDPR/CCPA compliance for member PII, column-level masking, row-level access for regional data residency, audit logging, and key management. Include operational considerations.**

**Answer**:

**1. Data Classification Taxonomy**

```
Level 1: Public         → No restrictions (aggregated campaign metrics)
Level 2: Internal       → All Costco employees (campaign names, channel data)
Level 3: Confidential   → Data team only (financial spend data, advertiser configs)
Level 4: Restricted/PII → Specific role only (member email, phone, DOB, address)
```

**2. Column-Level Security via Policy Tags**

```
Policy Tag hierarchy in Data Catalog:
├── PII
│   ├── Email          → Only: email-marketing-sa, crm-sa, compliance-team
│   ├── Phone          → Only: email-marketing-sa, crm-sa
│   ├── DateOfBirth    → Only: compliance-team, analytics-pii-approved
│   └── Address        → Only: logistics-sa, compliance-team
├── Financial
│   ├── CampaignSpend  → marketing-team, finance-team
│   └── Revenue        → finance-team, execs
└── Internal (no tag)  → All authenticated Costco users
```

**3. Row-Level Security for Regional Residency**

```sql
-- Members are tagged by region (US, EU, CA for CCPA)
CREATE ROW ACCESS POLICY eu_members_only ON dim_members
  GRANT TO ('group:eu-data-team@costco.com')
  FILTER USING (data_residency_region = 'EU');

CREATE ROW ACCESS POLICY us_members_only ON dim_members
  GRANT TO ('group:us-data-team@costco.com')
  FILTER USING (data_residency_region = 'US');

-- Platform admins: no row policy (they see all, but are audited heavily)
```

**4. Key Management Strategy**

- Default data: Google-managed encryption keys (GMEK) — zero ops overhead
- PII dataset (`marts.dim_members`): Customer-managed keys (CMEK) via Cloud KMS
  - Key rotation: automatic 90-day rotation
  - Key destruction: triggers data inaccessibility — use as last resort for breach response
- Payment/financial data: CMEK with separate key ring, access restricted to 3 platform admins

**5. Audit Logging**

```python
# Enable all three log types for sensitive datasets
# DATA_READ: who ran SELECT queries on PII tables
# DATA_WRITE: who modified/deleted PII data
# ADMIN_READ: who changed permissions

# Weekly automated audit report:
def generate_weekly_security_audit():
    return bq.query("""
        SELECT
            user_email,
            COUNT(*) AS query_count,
            SUM(bytes_billed) / 1e9 AS gb_billed,
            COUNTIF(table LIKE '%dim_members%') AS pii_table_accesses
        FROM audit_log_analysis
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
        GROUP BY user_email
        ORDER BY pii_table_accesses DESC
    """)
```

**6. GDPR/CCPA Operational Procedures**

- **Right to erasure SLA**: 30 days from request. Automated pipeline: request → identify all tables → delete → audit trail → notify requester.
- **Data retention**: `partition_expiration_days = 365` on raw tables. Aggregated marts: no expiry (no PII).
- **Data inventory**: Dataplex catalog with every PII field tagged, business justification documented, data owner identified.
- **Breach response**: KMS key rotation → data inaccessible within hours. Audit logs reveal scope of breach. 72-hour GDPR breach notification window is achievable.

**7. Operational Checklist (Quarterly)**

- Review all IAM bindings: remove departed employees, tighten over-permissioned SAs
- Audit query logs for unusual access patterns
- Test GDPR deletion pipeline end-to-end
- Rotate service account keys (or confirm Workload Identity Federation is used — no keys at all)
- Review column classification: new tables added → are PII columns tagged?

---

## Summary: Data Security & Governance — Senior Mastery Checklist

| Skill | What Senior Looks Like |
|-------|------------------------|
| IAM / Least privilege | Designs SA permissions from scratch; knows all BigQuery IAM roles |
| Column-level security | Implements policy tags; knows the workflow (taxonomy → tag → grant) |
| Row-level security | Creates row access policies; knows they apply to COUNT(*) too |
| PII masking | SHA256 hashing, Cloud DLP, format-preserving masking — knows when to use each |
| CMEK | Knows when to use vs GMEK; understands key rotation implications |
| GDPR/CCPA | Can design a deletion pipeline; pseudonymization strategy |
| Audit logging | Knows what DATA_READ/WRITE/ADMIN logs capture; can query them |
| Data lineage | Uses Dataplex + DBT for automated lineage; knows its value for compliance |
| Security architecture | Designs defense-in-depth: IAM + column policies + row policies + audit |
| Incident response | Knows how to investigate unauthorized access end-to-end |
