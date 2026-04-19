# Topic 9: Data Quality, Governance & Compliance

> **Textbook Reference — Costco Sr. Data Engineer Interview Prep**
> Exhaustive coverage of data quality frameworks, validation techniques, governance patterns, PII handling, regulatory compliance, and lineage in GCP-native environments.

---

## Table of Contents
1. Data Quality Fundamentals
2. Dimensions of Data Quality
3. Data Quality Implementation: Great Expectations
4. Data Quality in BigQuery / Dataplex
5. PII Detection & Management
6. GCP DLP (Data Loss Prevention)
7. Data Governance Frameworks
8. Metadata Management & Data Catalog
9. Data Lineage
10. Access Control & Security Architecture
11. Regulatory Compliance (GDPR, CCPA)
12. Audit Logging & Compliance Monitoring
13. Data Retention & Lifecycle Management
14. Interview Q&A Bank

---

## 1. Data Quality Fundamentals

### Why Data Quality Is a First-Class Engineering Concern

Poor data quality costs organizations an average of $12.9M per year (Gartner). In MarTech, bad data quality means:
- **Wrong attribution**: Revenue credited to the wrong campaign → budget misallocation
- **Inflated metrics**: Duplicate impressions → CPM appears better than it is
- **Privacy violations**: PII in analytics tables → GDPR/CCPA breach risk
- **Lost revenue**: Null user_id → can't personalize → lower conversion rates

### Data Quality as a System Property

Data quality is not a one-time check. It's an architectural property maintained throughout the pipeline:

```
Source → Bronze → Silver → Gold → Serving
          │         │        │       │
          DQ        DQ       DQ      DQ
       (schema)  (validity) (biz   (freshness,
                            rules)  accuracy)
```

**Fail fast principle:** Catch quality issues as early as possible — ideally at the source. A duplicate event caught in Bronze costs a SQL query; a duplicate event discovered in a board-level revenue report costs credibility.

---

## 2. Dimensions of Data Quality

The six universally recognized dimensions of data quality:

### 1. Completeness
**Definition:** Required fields have values. Non-null constraints are met.

```sql
-- Completeness check: what % of event_id values are populated?
SELECT
    COUNT(*) AS total_rows,
    COUNTIF(event_id IS NULL) AS null_event_ids,
    COUNTIF(user_id IS NULL) AS null_user_ids,
    COUNTIF(campaign_id IS NULL) AS null_campaign_ids,
    ROUND(COUNTIF(event_id IS NULL) / COUNT(*), 4) AS event_id_null_rate,
    ROUND(COUNTIF(user_id IS NULL) / COUNT(*), 4) AS user_id_null_rate
FROM silver.ad_events
WHERE event_date = CURRENT_DATE() - 1;

-- Acceptable thresholds (from data contract):
-- event_id null rate: 0%
-- user_id null rate: < 20% (anonymous users are expected)
-- campaign_id null rate: 0%
```

### 2. Uniqueness
**Definition:** No duplicate records where uniqueness is expected.

```sql
-- Uniqueness check: detect duplicate event_ids
SELECT
    event_id,
    COUNT(*) AS occurrence_count
FROM silver.ad_events
WHERE event_date = CURRENT_DATE() - 1
GROUP BY event_id
HAVING COUNT(*) > 1
ORDER BY 2 DESC
LIMIT 100;

-- Count of duplicate records
SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT event_id) AS unique_event_ids,
    COUNT(*) - COUNT(DISTINCT event_id) AS duplicate_count,
    ROUND((COUNT(*) - COUNT(DISTINCT event_id)) / COUNT(*), 4) AS duplicate_rate
FROM silver.ad_events
WHERE event_date = CURRENT_DATE() - 1;
```

### 3. Validity
**Definition:** Values conform to expected formats, ranges, and allowed sets.

```sql
-- Validity check: event_type must be in allowed set
SELECT event_type, COUNT(*) AS cnt
FROM silver.ad_events
WHERE event_date = CURRENT_DATE() - 1
  AND event_type NOT IN ('impression', 'click', 'conversion', 'viewthrough')
GROUP BY 1
ORDER BY 2 DESC;

-- Revenue must be non-negative
SELECT COUNT(*) AS negative_revenue_count
FROM silver.ad_events
WHERE event_date = CURRENT_DATE() - 1
  AND revenue < 0;

-- Timestamp must not be in the future
SELECT COUNT(*) AS future_events
FROM silver.ad_events
WHERE event_date = CURRENT_DATE() - 1
  AND event_timestamp > CURRENT_TIMESTAMP();

-- URL formats valid (basic regex)
SELECT COUNT(*) AS invalid_urls
FROM silver.ad_clicks
WHERE event_date = CURRENT_DATE() - 1
  AND page_url IS NOT NULL
  AND NOT REGEXP_CONTAINS(page_url, r'^https?://');
```

### 4. Consistency
**Definition:** Data is consistent across related tables and systems.

```sql
-- Cross-table consistency: every campaign_id in ad_events must exist in campaigns.metadata
SELECT
    e.campaign_id,
    COUNT(*) AS event_count
FROM silver.ad_events e
LEFT JOIN campaigns.metadata c USING (campaign_id)
WHERE e.event_date = CURRENT_DATE() - 1
  AND c.campaign_id IS NULL
GROUP BY 1
ORDER BY 2 DESC;

-- Cross-day consistency: daily event count shouldn't drop >50% vs 7-day avg
WITH daily_counts AS (
    SELECT
        event_date,
        COUNT(*) AS daily_events
    FROM silver.ad_events
    WHERE event_date >= CURRENT_DATE() - 8
    GROUP BY 1
),
avg_count AS (
    SELECT AVG(daily_events) AS avg_7d
    FROM daily_counts
    WHERE event_date < CURRENT_DATE() - 1
)
SELECT
    dc.event_date,
    dc.daily_events,
    ac.avg_7d,
    dc.daily_events / ac.avg_7d AS ratio
FROM daily_counts dc, avg_count ac
WHERE dc.event_date = CURRENT_DATE() - 1;
-- Alert if ratio < 0.5 (dropped >50% vs 7-day avg)
```

### 5. Timeliness / Freshness
**Definition:** Data is available within the expected time window.

```sql
-- Freshness check: max event timestamp should be within last 2 hours
SELECT
    MAX(event_timestamp) AS latest_event,
    TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(event_timestamp), MINUTE) AS minutes_stale
FROM silver.ad_events
WHERE event_date = CURRENT_DATE();

-- Late-arriving data distribution
SELECT
    TIMESTAMP_DIFF(ingestion_timestamp, event_timestamp, MINUTE) AS latency_minutes,
    COUNT(*) AS event_count
FROM silver.ad_events
WHERE event_date = CURRENT_DATE() - 1
GROUP BY 1
ORDER BY 1;
```

### 6. Accuracy
**Definition:** Data correctly represents real-world entities and events.

```sql
-- Accuracy: total attributed revenue shouldn't exceed total transaction revenue
-- Cross-system check
WITH attributed_revenue AS (
    SELECT SUM(revenue) AS total_attributed
    FROM gold.campaign_daily_performance
    WHERE report_date = CURRENT_DATE() - 1
),
transaction_revenue AS (
    SELECT SUM(transaction_amount) AS total_transacted
    FROM orders.transactions
    WHERE order_date = CURRENT_DATE() - 1
)
SELECT
    a.total_attributed,
    t.total_transacted,
    a.total_attributed / t.total_transacted AS attribution_ratio
FROM attributed_revenue a, transaction_revenue t;
-- Attribution ratio > 1.0 would indicate over-attribution (double counting)
```

---

## 3. Data Quality Implementation: Great Expectations

### Why Great Expectations (GE)

GE is an open-source Python library that:
- Defines **Expectations** (assertions about data properties)
- Generates **Data Docs** (human-readable quality reports)
- Integrates with Airflow, DBT, Spark, BigQuery, Pandas
- Produces machine-readable validation results for alerting

### Setup and Configuration

```python
import great_expectations as ge
from great_expectations.core.batch import RuntimeBatchRequest
from great_expectations.checkpoint import SimpleCheckpoint
from great_expectations.core import ExpectationSuite
import pandas as pd
from google.cloud import bigquery

# --- Initialize context ---
context = ge.DataContext()

# --- Create Expectation Suite ---
suite_name = "silver_ad_events_suite"
suite = context.add_expectation_suite(expectation_suite_name=suite_name)

# --- Define Expectations ---
# Load sample data
client = bigquery.Client()
df = client.query("""
    SELECT * FROM silver.ad_events
    WHERE event_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    LIMIT 100000
""").to_dataframe()

validator = context.get_validator(
    batch_request=RuntimeBatchRequest(
        datasource_name="pandas_datasource",
        data_connector_name="runtime_data_connector",
        data_asset_name="ad_events",
        runtime_parameters={"batch_data": df},
        batch_identifiers={"run_id": "manual"}
    ),
    expectation_suite_name=suite_name
)

# Completeness
validator.expect_column_values_to_not_be_null("event_id")
validator.expect_column_values_to_not_be_null("campaign_id")
validator.expect_column_values_to_not_be_null("event_type")
validator.expect_column_values_to_not_be_null("event_timestamp")

# Uniqueness
validator.expect_column_values_to_be_unique("event_id")

# Validity: allowed values
validator.expect_column_values_to_be_in_set(
    "event_type",
    ["impression", "click", "conversion", "viewthrough"]
)

# Validity: range
validator.expect_column_values_to_be_between(
    "revenue",
    min_value=0,
    mostly=0.999  # 99.9% of rows — allow 0.1% tolerance for edge cases
)

# Freshness: timestamps should be recent
validator.expect_column_values_to_be_between(
    "event_timestamp",
    min_value="2020-01-01",
    max_value=pd.Timestamp.now().isoformat()
)

# Statistical: row count should match expected range
validator.expect_table_row_count_to_be_between(
    min_value=500_000,   # at least 500K events per day
    max_value=50_000_000  # no more than 50M (anomaly detection)
)

# Schema: required columns must exist with correct types
validator.expect_table_columns_to_match_ordered_list([
    "event_id", "user_id", "campaign_id", "channel",
    "event_type", "event_timestamp", "revenue", "event_date"
])

validator.expect_column_values_to_be_of_type("event_id", "str")
validator.expect_column_values_to_be_of_type("revenue", "float")

# Save suite
validator.save_expectation_suite()
```

### Running Validations in Airflow

```python
from airflow.operators.python import PythonOperator

def run_great_expectations_validation(**context):
    """Run GE validation as an Airflow task."""
    import great_expectations as ge
    from great_expectations.checkpoint import SimpleCheckpoint
    
    ge_context = ge.DataContext()
    
    # Checkpoint = suite + batch request + action list
    checkpoint_config = {
        "name": "silver_ad_events_checkpoint",
        "config_version": 1,
        "class_name": "SimpleCheckpoint",
        "validations": [{
            "batch_request": {
                "datasource_name": "bigquery_datasource",
                "data_connector_name": "configured_data_connector",
                "data_asset_name": "ad_events",
                "data_connector_query": {
                    "batch_filter_parameters": {
                        "partition_date": context['ds']
                    }
                }
            },
            "expectation_suite_name": "silver_ad_events_suite"
        }],
        "action_list": [
            {
                "name": "store_validation_result",
                "action": {"class_name": "StoreValidationResultAction"}
            },
            {
                "name": "update_data_docs",
                "action": {"class_name": "UpdateDataDocsAction"}
            },
            {
                "name": "send_slack_notification",
                "action": {
                    "class_name": "SlackNotificationAction",
                    "slack_webhook": "https://hooks.slack.com/...",
                    "notify_on": "failure"
                }
            }
        ]
    }
    
    result = ge_context.run_checkpoint(
        checkpoint_name="silver_ad_events_checkpoint",
        validations=checkpoint_config["validations"]
    )
    
    if not result.success:
        failed_expectations = [
            f"{res.expectation_config.expectation_type}: {res.result}"
            for res in result.run_results.values()
            for res in [res for res in res.results if not res.success]
        ]
        raise ValueError(f"Data quality validation failed:\n" + "\n".join(failed_expectations))
    
    return True


quality_gate = PythonOperator(
    task_id='data_quality_gate',
    python_callable=run_great_expectations_validation,
    provide_context=True
)
```

---

## 4. Data Quality in BigQuery / Dataplex

### BigQuery Data Quality via SQL (Lightweight Alternative to GE)

```python
from google.cloud import bigquery
from dataclasses import dataclass
from typing import Callable
import json

@dataclass
class DQRule:
    name: str
    dimension: str  # COMPLETENESS, UNIQUENESS, VALIDITY, CONSISTENCY, FRESHNESS
    sql: str
    threshold: float  # 1.0 = 100% pass rate required
    severity: str    # CRITICAL, WARNING

class BigQueryDQRunner:
    """Run SQL-based data quality checks against BigQuery tables."""
    
    def __init__(self, project: str):
        self.client = bigquery.Client(project=project)
    
    def run_check(self, rule: DQRule, table: str, date: str) -> dict:
        """Run a single DQ check. Returns pass/fail with stats."""
        
        query = rule.sql.replace('{table}', table).replace('{date}', date)
        
        result = self.client.query(query).result()
        row = list(result)[0]
        
        # Convention: queries return (total_rows, failing_rows) or (pass_bool)
        if hasattr(row, 'total_rows'):
            total = row.total_rows
            failing = row.failing_rows
            pass_rate = (total - failing) / total if total > 0 else 1.0
        else:
            pass_rate = float(row[0])
        
        passed = pass_rate >= rule.threshold
        
        return {
            'rule': rule.name,
            'dimension': rule.dimension,
            'table': table,
            'date': date,
            'pass_rate': pass_rate,
            'threshold': rule.threshold,
            'passed': passed,
            'severity': rule.severity
        }
    
    def run_suite(self, rules: list[DQRule], table: str, date: str) -> dict:
        """Run all rules, return summary."""
        results = [self.run_check(r, table, date) for r in rules]
        
        passed = [r for r in results if r['passed']]
        failed = [r for r in results if not r['passed']]
        critical_failures = [r for r in failed if r['severity'] == 'CRITICAL']
        
        summary = {
            'table': table,
            'date': date,
            'total_rules': len(results),
            'passed': len(passed),
            'failed': len(failed),
            'critical_failures': len(critical_failures),
            'overall_pass': len(critical_failures) == 0,
            'results': results
        }
        
        # Log to BigQuery audit table
        self.client.insert_rows_json(
            'monitoring.dq_run_results',
            [{'run_timestamp': 'AUTO', 'summary': json.dumps(summary)}]
        )
        
        return summary


# Define rules for silver.ad_events
AD_EVENTS_DQ_RULES = [
    DQRule(
        name='event_id_completeness',
        dimension='COMPLETENESS',
        sql="""
            SELECT 
                COUNT(*) AS total_rows,
                COUNTIF(event_id IS NULL) AS failing_rows
            FROM `{table}`
            WHERE event_date = '{date}'
        """,
        threshold=1.0,
        severity='CRITICAL'
    ),
    DQRule(
        name='event_id_uniqueness',
        dimension='UNIQUENESS',
        sql="""
            SELECT
                COUNT(*) AS total_rows,
                COUNT(*) - COUNT(DISTINCT event_id) AS failing_rows
            FROM `{table}`
            WHERE event_date = '{date}'
        """,
        threshold=0.999,  # allow 0.1% duplicates before alerting
        severity='CRITICAL'
    ),
    DQRule(
        name='event_type_validity',
        dimension='VALIDITY',
        sql="""
            SELECT
                COUNT(*) AS total_rows,
                COUNTIF(event_type NOT IN ('impression','click','conversion','viewthrough')) AS failing_rows
            FROM `{table}`
            WHERE event_date = '{date}'
        """,
        threshold=0.99,
        severity='WARNING'
    ),
    DQRule(
        name='revenue_range',
        dimension='VALIDITY',
        sql="""
            SELECT
                COUNT(*) AS total_rows,
                COUNTIF(revenue < 0) AS failing_rows
            FROM `{table}`
            WHERE event_date = '{date}' AND revenue IS NOT NULL
        """,
        threshold=1.0,
        severity='CRITICAL'
    ),
    DQRule(
        name='no_future_events',
        dimension='VALIDITY',
        sql="""
            SELECT
                COUNT(*) AS total_rows,
                COUNTIF(event_timestamp > CURRENT_TIMESTAMP()) AS failing_rows
            FROM `{table}`
            WHERE event_date = '{date}'
        """,
        threshold=1.0,
        severity='WARNING'
    )
]
```

---

## 5. PII Detection & Management

### PII Categories in MarTech Data

| PII Type | Examples in MarTech | Risk Level |
|----------|--------------------|----|
| Direct identifiers | Full name, email, phone, SSN | Critical |
| Device identifiers | IDFA, GAID, cookie IDs, IP address | High |
| Behavioral + identity | User ID + purchase history combined | High |
| Quasi-identifiers | ZIP + DOB + gender = re-identification risk | Medium |
| Inferred | Predicted income, health interests | Medium |

### PII Handling Architecture

```
PRODUCTION SYSTEM (with PII)
    │
    │ ETL / Dataflow
    ▼
┌──────────────────────────────────────────────────────┐
│  PII Transformation Layer                            │
│                                                      │
│  Tokenization: user_email → sha256(salt + email)     │
│  Masking:      phone_number → ****-****-1234          │
│  Generalization: zip_code 98110 → 981**               │
│  Suppression: SSN → NULL                             │
│  Pseudonymization: user_id → deterministic token     │
└──────────────────────────────────────────────────────┘
    │
    ▼
ANALYTICS SYSTEM (no direct PII)
    ├── BigQuery (hashed user_ids only)
    ├── Dataflow pipelines (tokenized identifiers)
    └── ML training data (pseudonymized)
```

### Tokenization vs Hashing vs Encryption

```python
import hashlib
import hmac
import base64
from cryptography.fernet import Fernet
from google.cloud import kms

# --- Hashing (one-way, fast, cannot reverse) ---
SALT = "costco_martech_pii_salt_2024"  # in practice: store in Secret Manager

def hash_pii(value: str) -> str:
    """Deterministic hash — same input always produces same output (joinable)."""
    if not value:
        return None
    return hashlib.sha256(f"{SALT}:{value}".encode()).hexdigest()

# Usage: join on hashed_email across tables without exposing real email
hashed = hash_pii("john.doe@example.com")
# "a3f4d9b2..." — can compare across tables, cannot reverse to email


# --- HMAC (keyed hash — harder to brute-force) ---
def hmac_hash_pii(value: str, secret_key: bytes) -> str:
    """HMAC hash with rotating keys for better security."""
    return hmac.new(secret_key, value.encode(), hashlib.sha256).hexdigest()


# --- GCP Cloud KMS Encryption (reversible, for fields you might need to restore) ---
def encrypt_pii_with_kms(plaintext: str, key_name: str) -> str:
    """Encrypt PII using Cloud KMS (AES-256). Reversible by authorized principals."""
    client = kms.KeyManagementServiceClient()
    
    response = client.encrypt(
        request={
            "name": key_name,
            "plaintext": plaintext.encode('utf-8')
        }
    )
    
    return base64.b64encode(response.ciphertext).decode('utf-8')


def decrypt_pii_with_kms(ciphertext_b64: str, key_name: str) -> str:
    """Decrypt PII — only accessible by principals with KMS decryptRole."""
    client = kms.KeyManagementServiceClient()
    
    response = client.decrypt(
        request={
            "name": key_name,
            "ciphertext": base64.b64decode(ciphertext_b64)
        }
    )
    
    return response.plaintext.decode('utf-8')
```

---

## 6. GCP DLP (Data Loss Prevention)

### What DLP Does
Cloud DLP identifies, classifies, and optionally transforms PII and sensitive data. It can:
- **Inspect**: Find PII in BigQuery tables, GCS files, Dataflow streams
- **Deidentify**: Replace PII with tokens, hashes, or masked values
- **Re-identify**: Reverse pseudonymization (with proper authorization)
- **Profile**: Generate data risk profiles across all BigQuery tables

### DLP Inspection in Code

```python
from google.cloud import dlp_v2
import json

dlp_client = dlp_v2.DlpServiceClient()

def inspect_text_for_pii(text: str, project: str) -> list:
    """Scan a piece of text for PII using Cloud DLP."""
    
    inspect_config = dlp_v2.InspectConfig(
        info_types=[
            {"name": "EMAIL_ADDRESS"},
            {"name": "PHONE_NUMBER"},
            {"name": "US_SOCIAL_SECURITY_NUMBER"},
            {"name": "CREDIT_CARD_NUMBER"},
            {"name": "PERSON_NAME"},
            {"name": "IP_ADDRESS"},
            {"name": "DATE_OF_BIRTH"},
            {"name": "US_PASSPORT"},
        ],
        min_likelihood=dlp_v2.Likelihood.POSSIBLE,
        include_quote=False  # don't return actual PII values in response
    )
    
    item = dlp_v2.ContentItem(value=text)
    
    response = dlp_client.inspect_content(
        request={
            "parent": f"projects/{project}",
            "inspect_config": inspect_config,
            "item": item
        }
    )
    
    findings = []
    for finding in response.result.findings:
        findings.append({
            'info_type': finding.info_type.name,
            'likelihood': finding.likelihood.name,
            'start_offset': finding.location.byte_range.start if finding.location else None
        })
    
    return findings


def deidentify_text(text: str, project: str) -> str:
    """Replace PII in text with tokens."""
    
    deidentify_config = dlp_v2.DeidentifyConfig(
        info_type_transformations=dlp_v2.InfoTypeTransformations(
            transformations=[
                # Replace email with surrogate token
                dlp_v2.InfoTypeTransformations.InfoTypeTransformation(
                    info_types=[{"name": "EMAIL_ADDRESS"}],
                    primitive_transformation=dlp_v2.PrimitiveTransformation(
                        replace_with_info_type_config=dlp_v2.ReplaceWithInfoTypeConfig()
                    )
                ),
                # Mask phone numbers
                dlp_v2.InfoTypeTransformations.InfoTypeTransformation(
                    info_types=[{"name": "PHONE_NUMBER"}],
                    primitive_transformation=dlp_v2.PrimitiveTransformation(
                        character_mask_config=dlp_v2.CharacterMaskConfig(
                            masking_character="*",
                            number_to_mask=7,
                            reverse_order=False
                        )
                    )
                ),
                # Crypto-based pseudonymization for user IDs (reversible)
                dlp_v2.InfoTypeTransformations.InfoTypeTransformation(
                    info_types=[{"name": "PERSON_NAME"}],
                    primitive_transformation=dlp_v2.PrimitiveTransformation(
                        crypto_deterministic_config=dlp_v2.CryptoDeterministicConfig(
                            crypto_key=dlp_v2.CryptoKey(
                                kms_wrapped=dlp_v2.KmsWrappedCryptoKey(
                                    wrapped_key=b"...",  # KMS-wrapped AES key
                                    crypto_key_name="projects/.../cryptoKeyVersions/1"
                                )
                            )
                        )
                    )
                )
            ]
        )
    )
    
    item = dlp_v2.ContentItem(value=text)
    
    response = dlp_client.deidentify_content(
        request={
            "parent": f"projects/{project}",
            "deidentify_config": deidentify_config,
            "item": item
        }
    )
    
    return response.item.value


# --- DLP on BigQuery table scan ---
def scan_bigquery_table_for_pii(project: str, dataset: str, table: str):
    """Schedule a DLP job to inspect an entire BigQuery table."""
    
    inspect_job = dlp_v2.InspectJobConfig(
        storage_config=dlp_v2.StorageConfig(
            big_query_options=dlp_v2.BigQueryOptions(
                table_reference=dlp_v2.BigQueryTable(
                    project_id=project,
                    dataset_id=dataset,
                    table_id=table
                ),
                rows_limit=1_000_000,       # sample 1M rows
                sample_method=dlp_v2.BigQueryOptions.SampleMethod.RANDOM_START
            )
        ),
        inspect_config=dlp_v2.InspectConfig(
            info_types=[
                {"name": "EMAIL_ADDRESS"},
                {"name": "PHONE_NUMBER"},
                {"name": "CREDIT_CARD_NUMBER"},
                {"name": "US_SOCIAL_SECURITY_NUMBER"}
            ],
            min_likelihood=dlp_v2.Likelihood.LIKELY,
            limits=dlp_v2.InspectConfig.FindingLimits(max_findings_per_request=1000)
        ),
        actions=[
            dlp_v2.Action(
                pub_sub=dlp_v2.Action.PublishToPubSub(
                    topic=f"projects/{project}/topics/dlp-findings"
                )
            ),
            dlp_v2.Action(
                save_findings=dlp_v2.Action.SaveFindings(
                    output_config=dlp_v2.OutputStorageConfig(
                        table=dlp_v2.BigQueryTable(
                            project_id=project,
                            dataset_id="monitoring",
                            table_id="dlp_findings"
                        )
                    )
                )
            )
        ]
    )
    
    response = dlp_client.create_dlp_job(
        request={
            "parent": f"projects/{project}",
            "inspect_job": inspect_job
        }
    )
    
    print(f"DLP job created: {response.name}")
    return response.name
```

---

## 7. Data Governance Frameworks

### What Data Governance Covers

Data governance is the set of policies, processes, and standards that ensure data is:
- **Discoverable**: People can find the data they need
- **Understandable**: Data has documented meaning and business context
- **Trustworthy**: Data quality is known and maintained
- **Secure**: Data access is controlled and audited
- **Compliant**: Data usage follows regulatory requirements

### Data Governance Roles

| Role | Responsibilities |
|------|-----------------|
| **Data Owner** | Business leader accountable for a dataset's quality and usage. Approves access requests. |
| **Data Steward** | Business user who defines business rules, validates data definitions, resolves quality issues. |
| **Data Engineer** | Implements pipelines, quality checks, and access controls. |
| **Data Product Manager** | Manages a data product — defines SLAs, contracts, roadmap. |
| **Data Consumer** | Analyst or ML engineer using the data. Responsible for reporting quality issues. |

### Data Mesh Architecture (for large organizations)

```
Traditional Data Governance:
   Central team owns ALL data → bottleneck, poor domain knowledge
   
Data Mesh Governance:
   ├── Marketing Domain Team
   │   owns: campaign data, attribution models, member segments
   │   responsible for: quality, SLAs, contracts, access
   │
   ├── Supply Chain Domain Team
   │   owns: inventory, logistics, procurement data
   │
   ├── Finance Domain Team
   │   owns: transaction data, revenue reports, budget data
   │
   └── Central Platform Team (federated governance)
       provides: shared infrastructure (Dataplex, DLP, IAM)
       defines: cross-domain standards (naming, quality thresholds, security)
       does NOT own: domain-specific data
```

**Data mesh principles:**
1. **Domain ownership**: Teams own their data as a product
2. **Data as a product**: Data is treated like a software product — with SLAs, versioning, documentation
3. **Self-serve platform**: Central team provides tools, domain teams use them
4. **Federated governance**: Standards are central; implementation is distributed

---

## 8. Metadata Management & Data Catalog

### What to Catalog

```python
from google.cloud import datacatalog_v1

client = datacatalog_v1.DataCatalogClient()

# --- Create a Tag Template (reusable metadata schema) ---
tag_template = datacatalog_v1.TagTemplate(
    display_name="MarTech Table Classification",
    fields={
        "domain": datacatalog_v1.TagTemplateField(
            display_name="Business Domain",
            type_=datacatalog_v1.FieldType(
                enum_type=datacatalog_v1.FieldType.EnumType(
                    allowed_values=[
                        datacatalog_v1.FieldType.EnumType.EnumValue(display_name="marketing"),
                        datacatalog_v1.FieldType.EnumType.EnumValue(display_name="finance"),
                        datacatalog_v1.FieldType.EnumType.EnumValue(display_name="supply_chain"),
                        datacatalog_v1.FieldType.EnumType.EnumValue(display_name="member_data"),
                    ]
                )
            )
        ),
        "data_layer": datacatalog_v1.TagTemplateField(
            display_name="Medallion Layer",
            type_=datacatalog_v1.FieldType(
                enum_type=datacatalog_v1.FieldType.EnumType(
                    allowed_values=[
                        datacatalog_v1.FieldType.EnumType.EnumValue(display_name="bronze"),
                        datacatalog_v1.FieldType.EnumType.EnumValue(display_name="silver"),
                        datacatalog_v1.FieldType.EnumType.EnumValue(display_name="gold"),
                    ]
                )
            )
        ),
        "contains_pii": datacatalog_v1.TagTemplateField(
            display_name="Contains PII",
            type_=datacatalog_v1.FieldType(
                primitive_type=datacatalog_v1.FieldType.PrimitiveType.BOOL
            )
        ),
        "data_owner": datacatalog_v1.TagTemplateField(
            display_name="Data Owner (email)",
            type_=datacatalog_v1.FieldType(
                primitive_type=datacatalog_v1.FieldType.PrimitiveType.STRING
            )
        ),
        "refresh_sla": datacatalog_v1.TagTemplateField(
            display_name="Refresh SLA",
            type_=datacatalog_v1.FieldType(
                primitive_type=datacatalog_v1.FieldType.PrimitiveType.STRING
            )
        ),
        "last_validated": datacatalog_v1.TagTemplateField(
            display_name="Last Quality Validation",
            type_=datacatalog_v1.FieldType(
                primitive_type=datacatalog_v1.FieldType.PrimitiveType.TIMESTAMP
            )
        )
    }
)

# --- Tag a specific table ---
entry_name = (
    "//bigquery.googleapis.com/projects/costco-martech-prod"
    "/datasets/silver/tables/ad_events"
)

lookup_entry_req = datacatalog_v1.LookupEntryRequest(
    linked_resource=entry_name
)
entry = client.lookup_entry(request=lookup_entry_req)

tag = datacatalog_v1.Tag(
    template="projects/costco-martech-prod/locations/us-central1/tagTemplates/martech-classification",
    fields={
        "domain": datacatalog_v1.TagField(
            enum_value=datacatalog_v1.TagField.EnumValue(display_name="marketing")
        ),
        "data_layer": datacatalog_v1.TagField(
            enum_value=datacatalog_v1.TagField.EnumValue(display_name="silver")
        ),
        "contains_pii": datacatalog_v1.TagField(bool_value=True),
        "data_owner": datacatalog_v1.TagField(string_value="martech-eng@costco.com"),
        "refresh_sla": datacatalog_v1.TagField(string_value="T+2h daily"),
    }
)

client.create_tag(parent=entry.name, tag=tag)
```

---

## 9. Data Lineage

### Why Lineage Matters
- **Root cause analysis**: "Where did this wrong number come from?" → trace back through transformations
- **Impact analysis**: "If I change this table's schema, what downstream tables break?"
- **Regulatory compliance**: GDPR requires knowing where personal data flows
- **Trust building**: Analysts trust data more when they can see its provenance

### Automatic Lineage in GCP

BigQuery and Dataflow automatically emit lineage events to **Cloud Data Catalog Lineage API**. No code required — just enable the API.

```bash
# Enable Data Lineage API
gcloud services enable datalineage.googleapis.com

# BigQuery automatically emits lineage for:
# - CREATE TABLE AS SELECT (reads source, writes destination)
# - INSERT INTO ... SELECT (reads source, appends to destination)
# - MERGE (reads source, modifies destination)
# - Scheduled queries and BigQuery jobs

# Dataflow automatically emits lineage when:
# - Reading from BigQuery/GCS
# - Writing to BigQuery/GCS
# - (via the Dataflow Lineage integration)
```

### Querying Lineage

```python
from google.cloud import lineage_v1

lineage_client = lineage_v1.LineageClient()

# Find all processes that READ from silver.ad_events
def find_downstream_tables(source_table: str, project: str) -> list:
    """Find all tables that depend on a given table."""
    
    # Search for lineage where the source table is an input
    request = lineage_v1.SearchLinksRequest(
        parent=f"projects/{project}/locations/us",
        source={
            "fully_qualified_name": f"bigquery:{source_table}"
        }
    )
    
    downstream = []
    for link in lineage_client.search_links(request=request):
        downstream.append({
            'target': link.target.fully_qualified_name,
            'process': link.name
        })
    
    return downstream


# Find all processes that WROTE to gold.campaign_daily_performance
def find_upstream_sources(target_table: str, project: str) -> list:
    """Find all tables that feed into a given table."""
    
    request = lineage_v1.SearchLinksRequest(
        parent=f"projects/{project}/locations/us",
        target={
            "fully_qualified_name": f"bigquery:{target_table}"
        }
    )
    
    upstream = []
    for link in lineage_client.search_links(request=request):
        upstream.append({
            'source': link.source.fully_qualified_name,
            'process': link.name
        })
    
    return upstream


# Example use case: Schema change impact analysis
source = "costco-martech-prod.silver.ad_events"
downstream = find_downstream_tables(source, "costco-martech-prod")
print(f"Tables downstream of {source}:")
for d in downstream:
    print(f"  → {d['target']} (via {d['process']})")
```

---

## 10. Access Control & Security Architecture

### BigQuery IAM Best Practices

```bash
# Principle of Least Privilege — grant minimum necessary permissions

# Analysts: read-only on gold layer
gcloud projects add-iam-policy-binding costco-martech-prod \
  --member="group:martech-analysts@costco.com" \
  --role="roles/bigquery.dataViewer"  # read-only

# Dataset-level (more granular than project-level)
bq update --set-iam-policy costco-martech-prod:gold \
  '{"bindings": [{"role": "roles/bigquery.dataViewer",
     "members": ["group:martech-analysts@costco.com"]}]}'

# Pipeline service accounts: write to specific datasets only
gcloud projects add-iam-policy-binding costco-martech-prod \
  --member="serviceAccount:pipeline-sa@costco-martech-prod.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"  # read + write, no DDL

# DBT service account: create/replace tables in silver and gold only
bq update --set-iam-policy costco-martech-prod:silver \
  '{"bindings": [{"role": "roles/bigquery.dataOwner",
     "members": ["serviceAccount:dbt-sa@costco-martech-prod.iam.gserviceaccount.com"]}]}'

# DLP inspection: separate service account for DLP jobs
gcloud projects add-iam-policy-binding costco-martech-prod \
  --member="serviceAccount:dlp-sa@costco-martech-prod.iam.gserviceaccount.com" \
  --role="roles/dlp.inspectTemplatesReader"
```

### Column-Level Security in BigQuery

```sql
-- Create a policy tag for PII columns
-- Done via Data Catalog UI or API, then referenced in BigQuery schema

-- Once a column has a policy tag, only principals with the policy tag's
-- Fine-Grained Reader role can see the actual values.

-- Grant access to PII data:
-- IAM > Policy Tag > roles/datacatalog.categoryFineGrainedReader

-- Masking policy: analysts see masked values, engineers see real values
CREATE OR REPLACE ROW ACCESS POLICY analyst_row_filter
ON silver.ad_events
GRANT TO ("group:martech-analysts@costco.com")
FILTER USING (
    -- Analysts can only see non-PII columns
    -- Column-level security handles the actual PII masking
    event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)  -- row-level: only last 90 days
);


-- Row-level security: segment-specific data access
CREATE OR REPLACE ROW ACCESS POLICY emea_only
ON gold.campaign_daily_performance
GRANT TO ("group:emea-analysts@costco.com")
FILTER USING (region = 'EMEA');
```

---

## 11. Regulatory Compliance (GDPR, CCPA)

### GDPR Key Requirements for Data Engineers

| Requirement | Technical Implementation |
|-------------|--------------------------|
| **Data minimization** | Only collect fields necessary for stated purpose |
| **Purpose limitation** | Don't use data for purposes beyond original consent |
| **Storage limitation** | Implement retention policies, auto-delete |
| **Right to be forgotten** | Delete all PII for a given user_id across all tables |
| **Data portability** | Export all data for a user in a machine-readable format |
| **Privacy by design** | Pseudonymize at ingestion, not as an afterthought |
| **Breach notification** | Detect and report breaches within 72 hours |

### Right to be Forgotten Implementation

```python
from google.cloud import bigquery

class GDPRComplianceManager:
    """Handle GDPR subject access requests and deletion requests."""
    
    def __init__(self, project: str):
        self.client = bigquery.Client(project=project)
        self.project = project
        # Tables with user PII (maintained as a catalog)
        self.pii_tables = [
            ('silver', 'ad_events', 'user_id'),
            ('silver', 'member_profiles', 'member_id'),
            ('gold', 'campaign_daily_performance', None),  # No user_id
            ('bronze', 'ad_events_raw', None),  # JSON — need special handling
        ]
    
    def delete_user_data(self, user_id: str) -> dict:
        """
        Execute GDPR right-to-erasure for a given user_id.
        Deletes or anonymizes all user data across all PII-bearing tables.
        """
        deletion_log = []
        
        for dataset, table, id_column in self.pii_tables:
            if id_column is None:
                # JSON tables need UPDATE to null out the user_id within JSON
                if table == 'ad_events_raw':
                    query = f"""
                        UPDATE `{self.project}.{dataset}.{table}`
                        SET raw_message = JSON_REMOVE(raw_message, '$.user_id')
                        WHERE JSON_VALUE(raw_message, '$.user_id') = '{user_id}'
                    """
                else:
                    continue
            else:
                # Direct DELETE
                query = f"""
                    DELETE FROM `{self.project}.{dataset}.{table}`
                    WHERE {id_column} = '{user_id}'
                """
            
            job = self.client.query(query)
            job.result()
            
            deletion_log.append({
                'table': f"{dataset}.{table}",
                'rows_affected': job.num_dml_affected_rows,
                'status': 'deleted'
            })
        
        # Log the deletion for audit trail
        self.client.insert_rows_json(
            f'{self.project}.compliance.gdpr_deletion_log',
            [{
                'user_id_hash': hashlib.sha256(user_id.encode()).hexdigest(),  # log hash not real ID
                'deletion_timestamp': datetime.utcnow().isoformat(),
                'tables_affected': len(deletion_log),
                'total_rows_deleted': sum(d['rows_affected'] for d in deletion_log)
            }]
        )
        
        return {'status': 'complete', 'deletion_details': deletion_log}
    
    def export_user_data(self, user_id: str) -> dict:
        """
        GDPR data portability: export all data for a user in JSON format.
        """
        user_data = {}
        
        for dataset, table, id_column in self.pii_tables:
            if id_column is None:
                continue
            
            result = self.client.query(f"""
                SELECT TO_JSON_STRING(t) AS row_json
                FROM `{self.project}.{dataset}.{table}` t
                WHERE {id_column} = '{user_id}'
            """).result()
            
            user_data[f"{dataset}.{table}"] = [
                json.loads(row.row_json) for row in result
            ]
        
        return user_data
```

---

## 12. Audit Logging & Compliance Monitoring

### BigQuery Audit Logs

```bash
# BigQuery audit logs are automatically written to Cloud Audit Logs
# Data Access logs record: who queried what, when, from where

# Enable data access audit logs (required — off by default for performance)
gcloud projects set-iam-policy costco-martech-prod policy.json
# In policy.json: auditLogConfigs for bigquery.googleapis.com/DATA_READ, DATA_WRITE
```

```sql
-- Query BigQuery audit logs via BigQuery log sink
-- Set up log sink: Cloud Logging → BigQuery dataset (bigquery_audit_logs)

SELECT
    timestamp,
    protopayload_auditlog.authenticationInfo.principalEmail AS user_email,
    protopayload_auditlog.serviceData.jobGetQueryResultsResponse.job.jobConfiguration.query.query AS query_text,
    protopayload_auditlog.serviceData.jobGetQueryResultsResponse.job.jobStatistics.totalBilledBytes / POW(10,9) AS billed_gb
FROM `costco-martech-prod.bigquery_audit_logs.cloudaudit_googleapis_com_data_access_*`
WHERE DATE(_PARTITIONTIME) = CURRENT_DATE() - 1
  AND protopayload_auditlog.methodName = 'jobservice.jobcompleted'
  AND protopayload_auditlog.serviceData.jobGetQueryResultsResponse.job.jobConfiguration.query.query 
      LIKE '%silver.ad_events%'
ORDER BY billed_gb DESC;

-- Alert on unusual access patterns:
-- Analyst querying > 1TB in a single query
-- New service account accessing PII tables
-- Access from unusual IP/location
-- Off-hours access to sensitive tables
```

---

## 13. Data Retention & Lifecycle Management

### BigQuery Retention Policies

```sql
-- Table-level partition expiration
ALTER TABLE bronze.ad_events_raw
SET OPTIONS (
    partition_expiration_days = 90  -- raw data expires after 90 days
);

ALTER TABLE silver.ad_events
SET OPTIONS (
    partition_expiration_days = 548  -- silver: 18 months
);

-- Gold layer: no expiration (business reports kept indefinitely)
-- But archive to cold storage after 3 years:

-- Create long-term storage table (automatically discounted for data not touched 90+ days)
-- BigQuery automatically charges active vs long-term rates
-- No configuration needed — just don't query old partitions

-- Table expiration (for temp/staging tables)
CREATE TABLE tmp.daily_staging_20240115
OPTIONS (expiration_timestamp = TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR))
AS SELECT ...;
```

### GCS Lifecycle Rules

```bash
# Set GCS bucket lifecycle policy for raw data
cat > lifecycle.json << 'EOF'
{
  "rule": [
    {
      "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
      "condition": {"age": 30}  # Move to nearline after 30 days
    },
    {
      "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
      "condition": {"age": 90}  # Move to coldline after 90 days
    },
    {
      "action": {"type": "SetStorageClass", "storageClass": "ARCHIVE"},
      "condition": {"age": 365}  # Archive after 1 year
    },
    {
      "action": {"type": "Delete"},
      "condition": {"age": 2555}  # Delete after 7 years
    }
  ]
}
EOF

gsutil lifecycle set lifecycle.json gs://costco-raw-events/
```

---

## 14. Interview Q&A Bank

**Q: How do you ensure data quality in a production BigQuery pipeline?**
A: I implement quality checks at every layer. At Bronze ingestion: schema validation (required fields present, correct types) using a lightweight SQL check or DLP scan. At Silver transformation: a full quality suite covering completeness (null rates), uniqueness (event_id dedup), validity (allowed values, range checks), and consistency (referential integrity against dimension tables). This runs as an Airflow task that gates downstream work — if critical checks fail, the pipeline stops. At Gold: freshness checks confirm partitions are up-to-date and row counts are within historical norms. All check results are logged to a monitoring table and alerted via Slack for critical failures. The approach gives us a "quality score" per table per run, and we track this over time.

**Q: What is the difference between pseudonymization, anonymization, and tokenization?**
A: Pseudonymization replaces direct identifiers with artificial identifiers (tokens), but the mapping from original to token is preserved — so the data can be re-identified by an authorized party. It's reversible. Anonymization is irreversible — the original identifier cannot be recovered even by the data controller (e.g., one-way hashing with no key). Tokenization is a form of pseudonymization: each value is replaced by a non-revealing token, with the original stored in a secure vault. In MarTech, I typically pseudonymize user_ids (deterministic hash with a secret salt — same user always gets the same hash, so you can join across tables), mask phone/email, and suppress fields like SSN entirely. Re-identification is only possible if you have the salt.

**Q: How would you implement GDPR right-to-erasure in a BigQuery-based data warehouse?**
A: First, maintain a catalog of all tables that contain user PII, with the column name used as the user identifier. When a deletion request arrives: (1) for tables with direct DELETE support (partitioned tables), run a DELETE WHERE user_id = X; (2) for tables with JSON blobs, run UPDATE to null out the user_id within the JSON; (3) for derived/aggregated tables that don't contain user_id (like daily campaign rollups), no action needed — the aggregate can't be traced to an individual. Log a hash of the deleted user_id with a timestamp for audit. The challenge in BigQuery is that DML on large unpartitioned tables is expensive — so proper partitioning by date enables deletes to run on a small subset of data. Also, streaming buffer data is immutable for 90 minutes — so truly real-time deletion isn't possible without architecture changes.

**Q: What is the difference between data governance and data quality?**
A: Data governance is the umbrella framework — the policies, roles, and processes that define how data should be managed, who owns it, how access is controlled, and what compliance requirements apply. Data quality is a specific domain within governance focused on the measurable properties of data: completeness, uniqueness, validity, consistency, freshness, and accuracy. Governance answers "Who is responsible for this data and what are the rules?" Quality answers "Does this data meet those rules right now?" In practice, governance without quality monitoring is theater — you need both.

**Q: Explain data lineage and why it matters for a MarTech platform.**
A: Lineage tracks the flow of data from source to consumption: which tables feed which other tables, through which transformation processes. In MarTech, this matters for: (1) debugging — if the campaign revenue report shows wrong numbers, lineage lets you trace back through gold → silver → bronze → source within minutes rather than manually checking each transformation; (2) schema impact analysis — if I need to rename a column in silver.ad_events, lineage shows me every downstream query, view, and gold table that will break; (3) GDPR compliance — when a deletion request comes in, lineage helps identify all tables that derived data from the user's events; (4) trust — analysts trust data more when they can see its lineage. In GCP, BigQuery and Dataflow automatically emit lineage events to the Lineage API with no code changes.

---

*End of Topic 9 — Data Quality, Governance & Compliance*
