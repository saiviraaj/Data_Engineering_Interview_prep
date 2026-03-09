# Data Governance, Quality & Observability — Complete Textbook
### Building Trustworthy, Secure, and Observable Data Platforms

---

## CHAPTER 1: DATA GOVERNANCE FUNDAMENTALS

### 1.1 What Is Data Governance?

Data governance is the framework of policies, processes, roles, and standards that ensure data is accurate, available, consistent, secure, and used appropriately.

**Four pillars:**
```
DATA QUALITY   — Is the data accurate, complete, timely, consistent?
DATA SECURITY  — Who can access what data, under what conditions?
DATA LINEAGE   — Where did this data come from? How was it transformed?
DATA CATALOGUE — What data exists, where is it, what does it mean?
```

**Why critical in banking:**
- Regulatory: GDPR, CCPA, PCI-DSS, SOX, Basel III/BCBS 239
- Auditability: regulators demand traceable, accurate financial data
- Trust: 60+ application teams need confidence in CDM Next data

### 1.2 Data Governance Roles

```
DATA OWNER        Business stakeholder. Approves access, defines quality standards.
DATA STEWARD      Senior DE. Implements quality rules, maintains metadata.
DATA CONSUMER     Analyst/engineer. Responsible for appropriate data use.
PLATFORM TEAM     Implements governance controls: IAM, DLP, audit, schema registry.
```

### 1.3 GCP Governance Stack

```
DISCOVERY      Dataplex Data Catalog (what exists, where, what it means)
CLASSIFICATION Cloud DLP (detect PII, financial data, sensitive fields)
ACCESS CONTROL IAM + Column-Level Security + Row-Level Security
LINEAGE        Dataplex Lineage + custom audit tables
QUALITY        Dataplex Data Quality (DQ rules as code) + custom SQL checks
AUDIT          Cloud Logging → BigQuery (long-term storage and querying)
COMPLIANCE     VPC Service Controls + CMEK encryption
```

---

## CHAPTER 2: DATA QUALITY FRAMEWORK

### 2.1 Dimensions of Data Quality

```
COMPLETENESS   Are all expected values present? Null rate per column.
ACCURACY       Does data correctly represent real-world values?
CONSISTENCY    Is data consistent across systems? BQ matches Teradata?
TIMELINESS     Is data current enough for its intended use? Freshness SLA.
UNIQUENESS     Are records appropriately deduplicated? No duplicate PKs.
VALIDITY       Do values conform to expected formats, ranges, and rules?
REFERENTIAL    Do foreign keys reference valid parent records?
INTEGRITY
```

### 2.2 Data Quality Checks in SQL

```sql
-- COMPLETENESS: null rates
SELECT
    COUNTIF(customer_id IS NULL) / COUNT(*) AS id_null_rate,
    COUNTIF(amount IS NULL)      / COUNT(*) AS amount_null_rate,
    COUNTIF(email IS NULL)       / COUNT(*) AS email_null_rate
FROM orders
WHERE order_date = CURRENT_DATE() - 1;

-- UNIQUENESS: duplicate primary keys
SELECT customer_id, COUNT(*) AS cnt
FROM customers
GROUP BY customer_id
HAVING cnt > 1;

-- VALIDITY: range and format checks
SELECT
    COUNTIF(amount < 0)        AS negative_amounts,
    COUNTIF(amount > 10000000) AS suspicious_large,
    COUNTIF(order_date > CURRENT_DATE()) AS future_dates
FROM orders;

SELECT COUNT(*) AS invalid_emails
FROM customers
WHERE NOT REGEXP_CONTAINS(email,
    r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$');

-- REFERENTIAL INTEGRITY: orphaned foreign keys
SELECT COUNT(*) AS orphaned_orders
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

-- FRESHNESS: stale data detection
SELECT
    MAX(created_at) AS latest_record,
    TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(created_at), HOUR) AS hours_stale
FROM orders
HAVING hours_stale > 26;

-- CONSISTENCY: source vs target row count
SELECT 'SOURCE' AS sys, COUNT(*) AS rows FROM source_mirror
WHERE partition_date = CURRENT_DATE() - 1
UNION ALL
SELECT 'TARGET', COUNT(*) FROM bq_target
WHERE partition_date = CURRENT_DATE() - 1;

-- STATISTICAL PROFILING: full column profile
SELECT
    COUNT(*)                                           AS total_rows,
    COUNTIF(amount IS NULL)                            AS null_count,
    MIN(amount) AS min, MAX(amount) AS max,
    ROUND(AVG(amount), 2)                              AS mean,
    ROUND(STDDEV(amount), 2)                           AS std_dev,
    ROUND(APPROX_QUANTILES(amount, 100)[OFFSET(25)], 2) AS p25,
    ROUND(APPROX_QUANTILES(amount, 100)[OFFSET(50)], 2) AS median,
    ROUND(APPROX_QUANTILES(amount, 100)[OFFSET(95)], 2) AS p95,
    ROUND(APPROX_QUANTILES(amount, 100)[OFFSET(99)], 2) AS p99
FROM orders;

-- ANOMALY DETECTION: distribution shift (z-score)
WITH baseline AS (
    SELECT AVG(amount) AS avg_amt, STDDEV(amount) AS std_amt
    FROM orders
    WHERE order_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
      AND DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY)
),
today AS (
    SELECT AVG(amount) AS today_avg FROM orders
    WHERE order_date = CURRENT_DATE() - 1
)
SELECT
    baseline.avg_amt AS baseline_avg,
    today.today_avg,
    ROUND(ABS(today.today_avg - baseline.avg_amt) / NULLIF(baseline.std_amt, 0), 2) AS z_score,
    IF(ABS(today.today_avg - baseline.avg_amt) / NULLIF(baseline.std_amt, 0) > 3,
       'ANOMALY', 'NORMAL') AS status
FROM baseline, today;
```

### 2.3 Great Expectations — DQ as Code

```python
import great_expectations as gx

context = gx.get_context()
datasource = context.sources.add_bigquery(name="cdm_bq", project="wf-cdm-prod")
suite = context.add_expectation_suite("orders_suite")

# Completeness
suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="customer_id"))
suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(
    column="amount", mostly=0.99))

# Uniqueness
suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="order_id"))

# Value range
suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(
    column="amount", min_value=0, max_value=10_000_000))

# Allowed values
suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(
    column="status",
    value_set=["PENDING", "COMPLETED", "CANCELLED", "REFUNDED"]))

# Row count
suite.add_expectation(gx.expectations.ExpectTableRowCountToBeBetween(
    min_value=100_000, max_value=10_000_000))

# Schema
suite.add_expectation(gx.expectations.ExpectTableColumnsToMatchOrderedList(
    column_list=["order_id", "customer_id", "amount", "status", "order_date"]))

# Run and fail pipeline if violations found
result = context.run_validation_operator("action_list_operator",
    assets_to_validate=[batch], run_id="daily_check")
if not result["success"]:
    raise DataQualityError(f"Quality check failed: {result}")
```

---

## CHAPTER 3: PII DETECTION AND MASKING

### 3.1 PII in Banking Data Engineering

PII (Personally Identifiable Information) is data that can identify an individual. In CDM Next, raw source data from Teradata/Oracle contains: names, SSNs, account numbers, dates of birth, addresses, card numbers.

**Regulatory obligations:**
- GDPR: right to erasure, explicit consent, data minimisation
- PCI-DSS: card numbers and CVV must never be stored in plaintext
- Banking regs: strict controls on customer financial data sharing

**The engineer's responsibility:**
- Never load PII to unprotected tables (including dev/staging)
- Mask or tokenise PII before it crosses environment boundaries
- Ensure PII never appears in logs or error messages
- Apply column-level security

### 3.2 Cloud DLP for Detection

```python
from google.cloud import dlp_v2

def scan_for_pii(project_id: str, text_samples: list) -> dict:
    client = dlp_v2.DlpServiceClient()
    info_types = [
        {"name": "PERSON_NAME"},
        {"name": "EMAIL_ADDRESS"},
        {"name": "US_SOCIAL_SECURITY_NUMBER"},
        {"name": "CREDIT_CARD_NUMBER"},
        {"name": "DATE_OF_BIRTH"},
        {"name": "FINANCIAL_ACCOUNT_NUMBER"},
    ]
    inspect_config = {"info_types": info_types,
                      "min_likelihood": dlp_v2.Likelihood.LIKELY}
    response = client.inspect_content(
        request={"parent": f"projects/{project_id}",
                 "inspect_config": inspect_config,
                 "item": {"value": " | ".join(text_samples)}}
    )
    findings = {}
    for f in response.result.findings:
        findings[f.info_type.name] = findings.get(f.info_type.name, 0) + 1
    return findings
```

### 3.3 PII Masking Strategies

```
SUPPRESSION      Remove value entirely → NULL
                 Use when field not needed for use case

MASKING          Partial mask: ****-****-****-1234
                 Use when partial value needed for support/reference

TOKENISATION     Replace with reversible random token (vault lookup)
                 Use when downstream system needs to join on original value

PSEUDONYMISATION Replace with consistent hash: HMAC(id, key)
                 Same input → same token; not reversible without key
                 Use when cross-table joins needed without exposing identity

GENERALISATION   Replace exact value with bucket: age 34 → "30-39"
                 Use when statistical analysis, not individual tracking

SYNTHETIC DATA   Statistically similar fake data
                 Use for dev/test environments
```

### 3.4 Column-Level Security in BigQuery

```sql
-- Policy tags protect specific columns
-- Assign via Dataplex Policy Tag Manager

-- CREATE TABLE with sensitive columns tagged (in BigQuery metadata):
-- ssn column: policy tag = PII.SSN
-- account_no column: policy tag = Financial.AccountNo

-- Grant access to see SSN values:
-- Principal: pii-access-group@company.com
-- Permission: roles/datacatalog.categoryFineGrainedReader on PII.SSN tag

-- Analysts WITHOUT the tag permission see NULL for ssn
-- Analysts WITH the tag permission see actual SSN values
-- Same query, different results based on IAM
```

### 3.5 Row-Level Security

```sql
-- Each team sees only their own data
CREATE ROW ACCESS POLICY finance_filter
ON dataset.orders
GRANT TO ('group:finance-team@company.com')
FILTER USING (business_unit = 'FINANCE');

CREATE ROW ACCESS POLICY risk_filter
ON dataset.orders
GRANT TO ('group:risk-team@company.com')
FILTER USING (business_unit = 'RISK');

-- Finance team: SELECT * FROM orders
-- Automatically gets WHERE business_unit = 'FINANCE'
-- Other rows are completely invisible
```

---

## CHAPTER 4: DATA LINEAGE

### 4.1 Why Lineage Matters

Data lineage tracks the complete journey of data. It answers:
- "Where does this BigQuery column come from?" (backward lineage)
- "If I change this source column, what breaks?" (forward impact lineage)
- "Show me every transform this data went through"

**Use cases:**
- Regulatory audit: "Where does this risk metric come from?"
- Impact analysis: schema change → which downstream reports break?
- Debugging: anomalous data → trace back to root cause
- Trust: lineage makes data verifiable to sceptical stakeholders

### 4.2 Custom Lineage Table

```sql
CREATE TABLE governance.pipeline_lineage (
    pipeline_name   STRING,
    run_id          STRING,
    run_date        DATE,
    source_type     STRING,   -- 'TERADATA', 'BIGQUERY', 'GCS', 'KAFKA'
    source_table    STRING,
    target_table    STRING,
    transformation  STRING,   -- description of transform applied
    columns_mapped  JSON,     -- {source_col: target_col}
    recorded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY run_date;

-- Impact analysis: which pipelines read from customer_master?
SELECT DISTINCT pipeline_name, target_table
FROM governance.pipeline_lineage
WHERE source_table = 'customer_master'
ORDER BY pipeline_name;

-- Full upstream lineage (recursive CTE)
WITH RECURSIVE upstream AS (
    SELECT source_table, target_table, 1 AS depth
    FROM governance.pipeline_lineage
    WHERE target_table = 'fact_orders'

    UNION ALL

    SELECT l.source_table, l.target_table, u.depth + 1
    FROM governance.pipeline_lineage l
    JOIN upstream u ON l.target_table = u.source_table
    WHERE u.depth < 15
)
SELECT DISTINCT source_table, depth FROM upstream ORDER BY depth;
```

### 4.3 Dataplex Automatic Lineage

Dataplex automatically captures lineage for BigQuery SQL jobs, Dataflow, and Dataproc — no instrumentation needed for most pipelines. Access via the Dataplex UI or API to visualise lineage graphs for any BigQuery table.

---

## CHAPTER 5: DATA CATALOGUING

### 5.1 Dataplex Structure

```
LAKE       Logical grouping for a business domain (Finance Lake, Customer Lake)
  ZONE     Data quality tier within a lake
    Raw Zone      → GCS bucket with raw source data
    Curated Zone  → BigQuery datasets with business-ready data
  ASSET    Individual BigQuery dataset, GCS bucket, or table
```

### 5.2 Automated Documentation at Scale

```python
def auto_document_table(project: str, dataset: str, table: str) -> None:
    """Generate column descriptions using LLM and publish to BigQuery."""
    bq = bigquery.Client()
    tbl = bq.get_table(f"{project}.{dataset}.{table}")

    # Get schema and sample
    schema = {f.name: f.field_type for f in tbl.schema}
    sample = bq.query(f"SELECT * FROM `{project}.{dataset}.{table}` LIMIT 5"
                      ).to_dataframe().to_dict(orient='records')

    # LLM generates descriptions (see GenAI chapter)
    descriptions = generate_column_descriptions(schema, sample)

    # Update BigQuery schema descriptions
    new_schema = [
        bigquery.SchemaField(
            f.name, f.field_type,
            description=descriptions.get("columns", {}).get(f.name, "")
        ) for f in tbl.schema
    ]
    tbl.schema = new_schema
    tbl.description = descriptions.get("table_description", "")
    bq.update_table(tbl, ["schema", "description"])
```

---

## CHAPTER 6: ACCESS CONTROL AND SECURITY

### 6.1 IAM Principles

```
LEAST PRIVILEGE     Grant only permissions required. Data Viewer not Data Editor.
SEPARATION OF DUTIES  DE creates tables, Data Owner approves access.
JUST-IN-TIME ACCESS  Temporary grants that expire; no standing privileged access.
```

### 6.2 BigQuery IAM Roles

```
bigquery.admin          Full control. Platform team only.
bigquery.dataOwner      Full control over owned datasets. DE team.
bigquery.dataEditor     Create/update/delete tables, run queries. Pipeline SAs.
bigquery.dataViewer     Read data only. Analysts, BI tools.
bigquery.jobUser        Run jobs (no table access alone). Combine with dataViewer.
bigquery.metadataViewer See schema/names but not data. Cataloguing tools.
```

### 6.3 Service Account Best Practices

```
Each pipeline gets a dedicated SA with minimum permissions.
pipeline-finance@proj.iam.gserviceaccount.com:
  bigquery.dataEditor  on finance_staging (write)
  bigquery.dataViewer  on finance_source (read)
  storage.objectViewer on source GCS bucket
  secretmanager.secretAccessor for finance-db-creds

Workload Identity (preferred): no JSON key files.
GKE/Cloud Run services authenticate as SA via workload identity.
No key to rotate, no key to leak.
```

### 6.4 VPC Service Controls

Creates a security perimeter around GCP services — data cannot leave the perimeter even with valid credentials.

```
INSIDE PERIMETER:  BigQuery, GCS, Dataflow, Composer, Secret Manager
EFFECT:            Requests from outside allowed IPs → blocked
                   Even compromised credentials → data stays inside
EXCEPTIONS:        Corporate VPN IPs, specific developer machines, partner grants

CDM Next: All services inside a VPC SC perimeter.
External source connections go through Cloud Interconnect (private, not internet).
```

---

## CHAPTER 7: AUDIT LOGGING AND COMPLIANCE

### 7.1 Cloud Audit Log Types

```
ADMIN ACTIVITY (always on, free)
  Who created/deleted/modified resources? Who changed IAM?
  Example: "user@co.com deleted table finance.customer_master"

DATA ACCESS (optional, chargeable)
  Who read what data? Which queries ran?
  Example: "analyst@co.com ran SELECT on finance.orders at 14:32"

POLICY DENIED
  Access attempts blocked by VPC SC or IAM.
```

### 7.2 Querying Audit Logs in BigQuery

```sql
-- Export Cloud Logging to BigQuery for long-term analysis
SELECT
    timestamp,
    protopayload_auditlog.authenticationInfo.principalEmail AS user,
    protopayload_auditlog.serviceData.jobCompletedEvent.job.jobStatistics
        .totalBilledBytes / POW(1024,3) AS gb_billed,
    protopayload_auditlog.serviceData.jobCompletedEvent.job.jobConfiguration
        .query.query AS query_text
FROM `project.dataset.cloudaudit_googleapis_com_data_access`
WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
ORDER BY timestamp DESC;

-- Who accessed sensitive columns?
SELECT user, query_text, timestamp
FROM query_audit
WHERE REGEXP_CONTAINS(LOWER(query_text),
    r'\b(ssn|social_security|date_of_birth|account_number)\b')
ORDER BY timestamp DESC;
```

### 7.3 Compliance Mapping

```
SOX              Financial reports traceable to source with documented transforms.
                 CDM Next: schema registry + lineage table + validation trail.

GDPR             Right to erasure. Tokenise customer_id → delete from vault.
                 All records become anonymous without source mapping.

PCI-DSS          Card data encrypted at rest and in transit. Never plaintext.
                 CDM Next: Cloud DLP masking before BigQuery load, CMEK.

BCBS 239         Risk calculation data must have documented lineage.
                 CDM Next: full lineage tracking, source-to-BQ reconciliation.
```

---

## CHAPTER 8: DATA CONTRACTS

### 8.1 What Is a Data Contract?

A data contract is a formal, machine-readable agreement between a data producer and consumers about schema, quality guarantees, and SLAs. Think of it as an API contract for data.

```yaml
id: orders-v2
version: "2.1.0"
owner: "data-platform@company.com"

schema:
  fields:
    - name: order_id
      type: STRING
      nullable: false
    - name: amount
      type: NUMERIC
      nullable: false
      constraints: {min: 0, max: 10000000}

quality:
  completeness: {order_id: 100%, amount: 99.9%}
  freshness: {max_lag_hours: 2}
  uniqueness: {primary_key: [order_id]}

sla:
  availability: 99.9%
  freshness: "Available by 02:00 UTC daily"
  schema_change_notice: "14 days for breaking changes"
```

### 8.2 Enforcing Contracts in Pipelines

```python
class DataContract:
    @classmethod
    def load(cls, path: str) -> "DataContract":
        with open(path) as f:
            return cls(**yaml.safe_load(f))

    def validate_schema(self, actual_schema: dict) -> list:
        violations = []
        for field in self.schema["fields"]:
            if field["name"] not in actual_schema:
                violations.append(f"Missing column: {field['name']}")
            elif actual_schema[field["name"]] != field["type"]:
                violations.append(f"Type mismatch: {field['name']}")
        return violations

# Run as pipeline gate — fail if contract violated
contract = DataContract.load("contracts/orders-v2.yaml")
violations = contract.validate_schema(get_bq_schema("project.dataset.orders"))
if violations:
    raise DataContractViolationError(violations)
```

---

## CHAPTER 9: DATA OBSERVABILITY

### 9.1 Five Pillars of Data Observability

```
FRESHNESS    Is data current? When last updated? Hours since update per table.
VOLUME       Is row count as expected? Alert on > 50% drop or > 200% spike.
SCHEMA       Have columns changed? Alert on removals, type changes.
DISTRIBUTION Are values within expected ranges? Z-score anomaly detection.
LINEAGE      Are upstream dependencies healthy? Propagate SLA breaches.
```

### 9.2 Volume Anomaly Detection

```sql
SELECT
    table_name,
    run_date,
    rows_loaded,
    AVG(rows_loaded) OVER (
        PARTITION BY table_name ORDER BY run_date
        ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
    ) AS avg_7d,
    ROUND(rows_loaded / NULLIF(AVG(rows_loaded) OVER (
        PARTITION BY table_name ORDER BY run_date
        ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING), 0), 2) AS ratio,
    CASE
        WHEN rows_loaded / NULLIF(AVG(rows_loaded) OVER (
            PARTITION BY table_name ORDER BY run_date
            ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING), 0) < 0.5 THEN 'VOLUME_DROP'
        WHEN rows_loaded / NULLIF(AVG(rows_loaded) OVER (
            PARTITION BY table_name ORDER BY run_date
            ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING), 0) > 2.0 THEN 'VOLUME_SPIKE'
        ELSE 'NORMAL'
    END AS status
FROM pipeline_audit
WHERE run_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND status = 'SUCCESS';
```

### 9.3 Schema Drift Detection

```python
def detect_schema_drift(
    table_ref: str,
    expected_schema: dict
) -> list:
    """Compare current BQ schema to expected and return drift."""
    client = bigquery.Client()
    tbl = client.get_table(table_ref)
    actual = {f.name: f.field_type for f in tbl.schema}

    drift = []
    for col, dtype in expected_schema.items():
        if col not in actual:
            drift.append({"type": "COLUMN_REMOVED", "column": col})
        elif actual[col] != dtype:
            drift.append({"type": "TYPE_CHANGED", "column": col,
                          "expected": dtype, "actual": actual[col]})
    for col in actual:
        if col not in expected_schema:
            drift.append({"type": "COLUMN_ADDED", "column": col})
    return drift
```

---

*End of Data Governance, Quality & Observability Textbook*
