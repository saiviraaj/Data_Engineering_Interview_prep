# MODULE 6: SYSTEM DESIGN QUESTIONS & SOLUTIONS
## PhD-Level Data Engineering Interview Preparation
### Tailored for Viraaj Sivaraju — Senior Data Engineer, Wells Fargo CDM Next

---

## MODULE OVERVIEW

This module presents **6 complete, production-grade system design problems** with exhaustive solutions. Each problem is structured as a real interview scenario, followed by a full solution covering: requirements clarification, capacity estimation, high-level architecture, component deep-dive, data models, failure scenarios, GCP-specific implementation, and CDM Next analogies where applicable.

These are not toy examples. Each solution is the depth expected at Principal/Staff engineer levels in top-tier companies.

---

## QUESTION 1: DESIGN A PETABYTE-SCALE DATA INGESTION PLATFORM

### Problem Statement

> "Design a data ingestion platform that can ingest data from 60+ heterogeneous source systems (relational databases, Hadoop clusters, Kafka topics, flat files, APIs) into a centralized cloud data lake. The platform must handle 15+ PB of total data, support batch and streaming ingestion, ensure exactly-once semantics, and provide a configuration-driven interface so application teams can onboard without engineering changes."

*This is essentially CDM Next. Answer with full architectural depth.*

---

### Step 1: Requirements Clarification

**Functional Requirements:**
- Ingest from: RDBMS (Oracle, Teradata), Hadoop HDFS, Kafka, REST APIs, SFTP/GCS flat files
- Support batch (daily/hourly) and streaming (sub-minute latency) ingestion modes
- Configuration-driven onboarding — no code changes per new source
- Schema discovery and evolution handling
- Data quality validation at ingestion time
- PII detection and masking before landing in the lake
- Full audit trail — what was ingested, when, by whom, from where
- Support incremental (CDC) and full-load strategies

**Non-Functional Requirements:**
- Scale: 15+ PB total, 100TB+ daily ingest volume at peak
- Latency: Batch within SLA windows (4-hour processing window); Streaming < 2 minutes end-to-end
- Availability: 99.99% uptime (< 52 minutes downtime/year)
- Throughput: 10 GB/s sustained ingestion throughput
- Teams: 60+ application teams self-serve onboarding
- Security: SOC2, PCI-DSS compliance; data never leaves approved VPC paths

**Out of Scope (explicitly stated in interview):**
- Data serving/consumption (separate platform concern)
- Machine learning feature stores
- Data catalog user interface

---

### Step 2: Capacity Estimation

```
DAILY INGESTION VOLUME CALCULATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
60 source systems × avg 1.7 TB/day = 100 TB/day raw
Compression ratio (Parquet): ~5:1 → 20 TB/day stored
Peak factor (ETL windows): 3× → 300 GB/s burst throughput needed

STORAGE ESTIMATION:
━━━━━━━━━━━━━━━━━━
Total data: 15 PB
Growth rate: 2 PB/year
7-year horizon: 29 PB
With replication (3×): 87 PB raw storage budget
GCS equivalent: $87M × $0.02/GB-month → optimize with tiering

NETWORK BANDWIDTH:
━━━━━━━━━━━━━━━━━
On-prem to GCP: 10 Gbps Dedicated Interconnect × 4 links = 40 Gbps
Max theoretical: 5 GB/s sustained
With overhead: ~4 GB/s practical → matches 100TB/24hr requirement

COMPUTE ESTIMATION:
━━━━━━━━━━━━━━━━━━
Dataflow workers: 100 TB/day ÷ 8hr window = 12.5 TB/hr
At 100 MB/s per worker: 34 workers sustained, 100 workers peak
Dataproc for heavy transformation: 50-node cluster, auto-scaling

METADATA OPERATIONS:
━━━━━━━━━━━━━━━━━━━
60 sources × 50 tables avg = 3,000 datasets
Lineage events: 3,000 × 4 events/load = 12,000 events/day
Config store reads: 10,000 reads/day → cache aggressively
```

---

### Step 3: High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CDM NEXT ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  SOURCE SYSTEMS           INGESTION LAYER         STORAGE LAYER     │
│  ─────────────            ──────────────          ─────────────     │
│                                                                     │
│  ┌──────────┐            ┌─────────────┐         ┌─────────────┐   │
│  │ Teradata │──JDBC──────►│             │         │  GCS RAW    │   │
│  │ Oracle   │            │  Dataflow   │────────►│  (Bronze)   │   │
│  │ MySQL    │            │  Batch Jobs │         │             │   │
│  └──────────┘            │             │         ├─────────────┤   │
│                          │  (Config-   │         │  GCS        │   │
│  ┌──────────┐            │  Driven     │         │  PROCESSED  │   │
│  │  Hadoop  │──DistCp────►  Templates) │────────►│  (Silver)   │   │
│  │  HDFS    │            │             │         │             │   │
│  └──────────┘            └─────────────┘         ├─────────────┤   │
│                                 ▲                │  BigQuery   │   │
│  ┌──────────┐            ┌──────┴──────┐         │  (Gold)     │   │
│  │  Kafka   │────────────►  Dataflow   │────────►│             │   │
│  │  Topics  │            │  Streaming  │         └─────────────┘   │
│  └──────────┘            └─────────────┘                           │
│                                 ▲                                   │
│  ┌──────────┐            ┌──────┴──────┐                           │
│  │  REST    │            │   Config    │  ┌───────────────────┐    │
│  │  APIs    │            │   Store     │  │  CONTROL PLANE    │    │
│  │  SFTP    │            │  (Firestore)│  │                   │    │
│  └──────────┘            └─────────────┘  │  Cloud Composer   │    │
│                                           │  (Orchestration)  │    │
│                          ┌─────────────┐  │                   │    │
│                          │  DLP API    │  │  Cloud Monitoring │    │
│                          │  (PII Mask) │  │  (Observability)  │    │
│                          └─────────────┘  └───────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Step 4: Component Deep-Dive

#### 4.1 Configuration Store Design

The heart of a config-driven platform. Every ingestion job reads its behavior from config — no hardcoding.

**Config Schema (Firestore document structure):**

```json
{
  "pipeline_id": "teradata-accounts-daily-v2",
  "source": {
    "type": "jdbc",
    "connection_ref": "secret://teradata-prod-creds",
    "database": "PROD_DW",
    "table": "ACCOUNTS",
    "extraction_strategy": "incremental",
    "watermark_column": "LAST_UPDATED_DT",
    "watermark_store": "firestore://watermarks/teradata-accounts",
    "fetch_size": 50000,
    "partition_column": "ACCT_ID",
    "num_partitions": 200
  },
  "transformation": {
    "pii_columns": ["SSN", "EMAIL", "PHONE", "CARD_NUMBER"],
    "pii_action": "dlp_mask",
    "schema_evolution": "add_columns_only",
    "null_handling": "replace_with_default",
    "type_coercions": {
      "ACCT_BALANCE": "DECIMAL(18,4)",
      "OPEN_DATE": "DATE"
    }
  },
  "destination": {
    "type": "gcs_then_bigquery",
    "gcs_path": "gs://cdm-silver/accounts/",
    "bq_dataset": "finance.accounts",
    "write_disposition": "WRITE_APPEND",
    "partition_field": "ingestion_dt",
    "clustering_fields": ["ACCT_TYPE", "REGION"]
  },
  "schedule": {
    "type": "cron",
    "expression": "0 2 * * *",
    "timeout_minutes": 180,
    "retry_policy": {
      "max_retries": 3,
      "backoff_seconds": 300
    }
  },
  "quality_rules": [
    {"rule": "not_null", "columns": ["ACCT_ID", "LAST_UPDATED_DT"]},
    {"rule": "row_count_min", "threshold": 100000},
    {"rule": "referential_integrity", "fk_column": "CUSTOMER_ID", "ref_table": "customers"}
  ],
  "notifications": {
    "success": ["team-finance-data@company.com"],
    "failure": ["oncall-data-platform@company.com", "pagerduty://data-platform"]
  }
}
```

**Config Versioning Pattern:**
- All configs stored with semantic version (v1, v2)
- Config changes go through PR review + automated validation
- Blue/green config deployment — new version runs in shadow mode before cutover
- Rollback by pinning pipeline to previous config version

#### 4.2 Dataflow Template Design (Config-Driven Batch Pipeline)

```python
# Pseudocode — Dataflow Flex Template
class ConfigDrivenIngestionPipeline:
    
    def __init__(self, pipeline_config: PipelineConfig):
        self.config = pipeline_config
        
    def build_pipeline(self, pipeline: beam.Pipeline):
        
        # Step 1: Read from source (polymorphic based on config)
        source_reader = SourceReaderFactory.create(self.config.source)
        raw_data = pipeline | "ReadSource" >> source_reader.read()
        
        # Step 2: Apply DLP masking if PII columns configured
        if self.config.transformation.pii_columns:
            masked_data = raw_data | "MaskPII" >> beam.ParDo(
                DLPMaskingDoFn(
                    pii_columns=self.config.transformation.pii_columns,
                    project=PROJECT_ID
                )
            )
        else:
            masked_data = raw_data
        
        # Step 3: Schema validation and type coercion
        validated_data = (
            masked_data
            | "ValidateSchema" >> beam.ParDo(SchemaValidationDoFn(self.config))
            | "CoerceTypes" >> beam.Map(apply_type_coercions, self.config.type_coercions)
        )
        
        # Step 4: Data quality checks
        passed, failed = (
            validated_data
            | "QualityCheck" >> beam.Partition(
                QualityPartitionFn(self.config.quality_rules), 2
            )
        )
        
        # Step 5: Write failures to quarantine
        failed | "WriteQuarantine" >> beam.io.WriteToText(
            f"gs://cdm-quarantine/{self.config.pipeline_id}/",
            append_trailing_newlines=True
        )
        
        # Step 6: Write successes to GCS (raw Parquet)
        passed | "WriteToGCS" >> beam.io.WriteToParquet(
            file_path_prefix=self.config.destination.gcs_path,
            schema=self.config.destination.avro_schema,
            codec='snappy'
        )
        
        # Step 7: Trigger BigQuery load job
        passed | "LoadToBigQuery" >> beam.io.WriteToBigQuery(
            table=self.config.destination.bq_dataset,
            schema=self.config.destination.bq_schema,
            write_disposition=self.config.destination.write_disposition,
            create_disposition=BigQueryDisposition.CREATE_IF_NEEDED
        )
        
        # Step 8: Update watermark on success
        passed | "UpdateWatermark" >> beam.ParDo(
            WatermarkUpdateDoFn(self.config.source.watermark_store)
        )
```

#### 4.3 Exactly-Once Semantics Implementation

Exactly-once is **hard**. The naive approach (at-least-once + deduplication) is fine for most cases but not for financial data. Here is a rigorous approach:

**Three levels of exactly-once:**

**Level 1 — Source to GCS (idempotent writes):**
```
- Use deterministic file naming: {pipeline_id}/{date}/{watermark_hash}.parquet
- Dataflow checkpointing saves progress to GCS
- On retry, Dataflow resumes from last checkpoint
- GCS writes are atomic (object upload is single PUT)
- RESULT: Same data written at most once per watermark window
```

**Level 2 — GCS to BigQuery (BQ load job idempotency):**
```
- Generate job_id = hash(pipeline_id + watermark + attempt_number)
- BigQuery deduplicates on job_id — retrying same job_id is no-op
- Use WRITE_APPEND with partition pruning: delete partition then append
- RESULT: Exactly-once BigQuery row insertion per pipeline run
```

**Level 3 — Downstream deduplication (for streaming):**
```sql
-- Deduplicate on read using ROW_NUMBER()
SELECT * EXCEPT(rn) FROM (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY event_id 
      ORDER BY ingestion_ts DESC
    ) AS rn
  FROM `project.dataset.events`
  WHERE DATE(ingestion_dt) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
) WHERE rn = 1
```

#### 4.4 Schema Evolution Handling

Schema drift is one of the most painful real-world problems in data ingestion. CDM Next's approach:

| Evolution Type | Detection | Action |
|---|---|---|
| New column added | Schema comparison at runtime | Auto-add to BQ table, backfill nulls |
| Column renamed | Detected as drop + add | Alert — human review required |
| Type widened (INT→BIGINT) | Type compatibility check | Allow — BQ handles implicitly |
| Type narrowed (BIGINT→INT) | Type compatibility check | Reject — quarantine records |
| Column dropped | Schema comparison | Alert — soft-delete in metadata |
| Table dropped | Source scan | Alert — pause pipeline, notify |

**Schema comparison algorithm:**
```python
def detect_schema_changes(current_schema, incoming_schema):
    changes = []
    
    current_cols = {c.name: c for c in current_schema.fields}
    incoming_cols = {c.name: c for c in incoming_schema.fields}
    
    # New columns (safe to add)
    for name in incoming_cols - current_cols:
        changes.append(SchemaChange(type="ADD_COLUMN", column=name))
    
    # Dropped columns (dangerous)
    for name in current_cols - incoming_cols:
        changes.append(SchemaChange(type="DROP_COLUMN", column=name, severity="HIGH"))
    
    # Type changes
    for name in current_cols & incoming_cols:
        if not is_compatible_type(current_cols[name].type, incoming_cols[name].type):
            changes.append(SchemaChange(type="TYPE_CHANGE", column=name, severity="CRITICAL"))
    
    return changes

def apply_schema_evolution(changes, pipeline_config):
    for change in changes:
        if change.severity == "CRITICAL":
            alert_and_pause_pipeline(change)
        elif change.type == "ADD_COLUMN":
            if pipeline_config.schema_evolution == "add_columns_only":
                alter_bigquery_table(add_column=change.column)
```

---

### Step 5: Data Model

**Metadata / Control Tables (BigQuery):**

```sql
-- Pipeline Execution Log
CREATE TABLE cdm_metadata.pipeline_runs (
  run_id STRING NOT NULL,
  pipeline_id STRING NOT NULL,
  config_version STRING,
  start_time TIMESTAMP NOT NULL,
  end_time TIMESTAMP,
  status STRING,  -- RUNNING, SUCCESS, FAILED, PARTIAL
  source_row_count INT64,
  target_row_count INT64,
  quarantine_row_count INT64,
  bytes_processed INT64,
  dataflow_job_id STRING,
  watermark_start TIMESTAMP,
  watermark_end TIMESTAMP,
  error_message STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(start_time)
CLUSTER BY pipeline_id, status;

-- Watermark Store
CREATE TABLE cdm_metadata.watermarks (
  pipeline_id STRING NOT NULL,
  last_successful_watermark TIMESTAMP,
  last_run_id STRING,
  updated_at TIMESTAMP
);

-- Schema Registry
CREATE TABLE cdm_metadata.schema_versions (
  pipeline_id STRING NOT NULL,
  version_id STRING NOT NULL,
  schema_json STRING,  -- JSON schema definition
  effective_from TIMESTAMP,
  effective_to TIMESTAMP,
  created_by STRING
)
PARTITION BY DATE(effective_from);
```

---

### Step 6: Failure Scenarios & Mitigation

| Failure | Detection | Impact | Mitigation |
|---|---|---|---|
| Source DB connection timeout | Dataflow worker exception | Pipeline stalls | Retry with exponential backoff; circuit breaker after 3 failures |
| GCS write failure mid-job | Checkpoint miss | Partial data | Dataflow auto-retry from last checkpoint; idempotent file naming |
| BigQuery quota exceeded | 403 from BQ API | Load job fails | Exponential backoff; split large loads into partitions |
| DLP API rate limit | 429 from DLP API | PII not masked | Throttle at source; use DLP templates for efficiency |
| Watermark corruption | Stale/future watermark | Missed or duplicate data | Watermark validation before use; sanity-check against source |
| Config store unavailable | Firestore 503 | All pipelines fail | Cache configs locally in Dataflow template; fallback read |
| Schema explosion (source adds 500 cols) | Schema comparison | Downstream breakage | Column whitelist in config; max_columns threshold alert |
| Network partition (Interconnect down) | No source connectivity | Complete outage | Secondary Interconnect; graceful degradation to batch catch-up |

---

### Step 7: Monitoring & SLAs

```yaml
# Prometheus-style metrics exposed by CDM Next
metrics:
  - name: cdm_pipeline_duration_seconds
    labels: [pipeline_id, status]
    type: histogram
    
  - name: cdm_rows_ingested_total
    labels: [pipeline_id, source_type]
    type: counter
    
  - name: cdm_quarantine_rows_total
    labels: [pipeline_id, failure_reason]
    type: counter
    
  - name: cdm_watermark_lag_seconds
    labels: [pipeline_id]
    type: gauge
    alert: > 3600  # Alert if lag exceeds 1 hour
    
  - name: cdm_schema_drift_events_total
    labels: [pipeline_id, drift_type]
    type: counter
    alert: any  # Alert on any schema drift

SLA_TARGETS:
  batch_pipeline_success_rate: 99.5%
  streaming_e2e_latency_p99: 120s
  daily_data_freshness: 4h from source
  incident_detection_time: < 5min
```

---

### CDM Next Connection

> In your interview, after walking through this design, say: "This is essentially what I architected and delivered at Wells Fargo as CDM Next. We ingested 15+ PB across 60+ application teams using a config-driven Dataflow template approach. The key insight was that each team had unique source schemas and SLA requirements — making the config-driven model non-negotiable for scalability. We achieved 60%+ throughput improvement over the legacy Hadoop-based approach by leveraging GCS+BigQuery over HDFS+Hive, and reduced production incidents by 40% through automated quality gates and schema drift detection."

---

---

## QUESTION 2: DESIGN A REAL-TIME FRAUD DETECTION SYSTEM

### Problem Statement

> "Design a real-time fraud detection system for a financial institution processing 50,000 transactions per second at peak. The system must detect fraudulent transactions within 200ms of receipt, apply ML scoring, update risk profiles in real-time, and store all transactions for offline model retraining."

---

### Step 1: Requirements Clarification

**Functional Requirements:**
- Ingest transaction events from payment networks (Visa, MasterCard) in real-time
- Apply rule-based fraud checks (velocity, blacklists, thresholds)
- Apply ML model scoring (neural network inference)
- Return fraud decision within 200ms (SLA for payment authorization)
- Update customer risk profile after each transaction
- Store all transactions (fraudulent and legitimate) for audit and model retraining
- Provide analyst dashboard for fraud investigation
- Support model hot-swap without downtime

**Non-Functional Requirements:**
- Throughput: 50,000 TPS peak, 20,000 TPS average
- Latency: P99 < 200ms for fraud decision
- Availability: 99.999% (5 nines) — payment critical path
- Durability: No transaction loss; all events persisted
- Consistency: Risk profile updates must be eventual (within 5 seconds is acceptable)

---

### Step 2: Capacity Estimation

```
TRANSACTION VOLUME:
━━━━━━━━━━━━━━━━━━
50,000 TPS × 1KB per event = 50 MB/s ingestion
50 MB/s × 86,400 = 4.3 TB/day
Annual storage: ~1.6 PB (before compression)
With Parquet compression (10:1): ~160 TB/year

LATENCY BUDGET DECOMPOSITION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total budget: 200ms
  - Network ingestion (Pub/Sub): 20ms
  - Stream processing overhead: 10ms
  - Feature extraction from Bigtable: 30ms
  - ML inference: 50ms
  - Rule engine evaluation: 20ms
  - Response write + return: 20ms
  - Buffer: 50ms
Total: 200ms ✓

BIGTABLE SIZING:
━━━━━━━━━━━━━━━
50,000 reads/s (feature lookup) + 50,000 writes/s (profile update)
= 100,000 ops/s
Bigtable node capacity: ~10,000 QPS/node
Required: 10 nodes minimum, 20 nodes with headroom
```

---

### Step 3: Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│              REAL-TIME FRAUD DETECTION ARCHITECTURE              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PAYMENT NETWORK                                                 │
│  ┌──────────────┐    ┌──────────┐    ┌──────────────────────┐   │
│  │ Visa/MC/Amex │───►│ Pub/Sub  │───►│   Dataflow           │   │
│  │ Transaction  │    │ Ingestion│    │   Stream Processing  │   │
│  │ Events       │    │ Topic    │    │                      │   │
│  └──────────────┘    └──────────┘    │  1. Parse & validate │   │
│                                      │  2. Enrich features  │   │
│  ┌──────────────────────────────┐    │  3. Rule evaluation  │   │
│  │      FEATURE STORE           │◄───│  4. ML scoring       │   │
│  │   (Cloud Bigtable)           │    │  5. Decision emit    │   │
│  │                              │───►│                      │   │
│  │  Row key: customer_id        │    └──────────────────────┘   │
│  │  Columns: last_txn_ts,       │              │                │
│  │           txn_velocity_1h,   │              ▼                │
│  │           avg_txn_amount,    │    ┌──────────────────────┐   │
│  │           blacklist_flag,    │    │   Decision Topic     │   │
│  │           risk_score         │    │   (Pub/Sub)          │   │
│  └──────────────────────────────┘    └──────────────────────┘   │
│                                               │                  │
│  ┌──────────────────────────────┐             │                  │
│  │      ML MODEL REGISTRY       │    ┌────────┴─────────┐       │
│  │   (GCS + Vertex AI)          │    │  DECISION ROUTER │       │
│  │                              │    │                  │       │
│  │  - Active model version      │    │  FRAUD → Block   │       │
│  │  - Shadow model (A/B)        │    │  REVIEW → Hold   │       │
│  │  - Model metadata            │    │  CLEAR → Approve │       │
│  └──────────────────────────────┘    └──────────────────┘       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   STORAGE LAYER                           │   │
│  │  BigQuery (all transactions for analytics + retraining)  │   │
│  │  Bigtable (real-time risk profiles, 90-day retention)    │   │
│  │  Firestore (fraud rules configuration)                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

### Step 4: Dataflow Streaming Pipeline — Fraud Detection Logic

```python
class FraudDetectionPipeline:
    
    def run(self, pipeline: beam.Pipeline):
        
        # Read raw transactions from Pub/Sub
        transactions = (
            pipeline
            | "ReadTransactions" >> beam.io.ReadFromPubSub(
                topic=TRANSACTION_TOPIC,
                with_attributes=True
            )
            | "ParseTransaction" >> beam.Map(parse_transaction_proto)
        )
        
        # Enrich with customer features from Bigtable
        enriched = (
            transactions
            | "EnrichFeatures" >> beam.ParDo(
                BigtableFeatureEnrichmentDoFn(
                    project=PROJECT_ID,
                    instance=BIGTABLE_INSTANCE,
                    table=RISK_PROFILE_TABLE
                )
            )
        )
        
        # Apply rule-based checks (fast, deterministic)
        rule_scored = (
            enriched
            | "ApplyRules" >> beam.Map(apply_fraud_rules)
            # Rules: velocity check, blacklist, amount threshold,
            #        geo-velocity (impossible travel), time patterns
        )
        
        # Apply ML model scoring for borderline cases
        ml_scored = (
            rule_scored
            | "MLScoring" >> beam.ParDo(
                VertexAIInferenceDoFn(
                    endpoint=FRAUD_MODEL_ENDPOINT,
                    batch_size=100  # Batch for efficiency
                )
            )
        )
        
        # Generate fraud decision
        decisions = (
            ml_scored
            | "GenerateDecision" >> beam.Map(generate_fraud_decision)
        )
        
        # Fan-out: publish decision + update profile + store to BQ
        decisions | "PublishDecision" >> beam.io.WriteToPubSub(DECISION_TOPIC)
        
        decisions | "UpdateRiskProfile" >> beam.ParDo(
            BigtableProfileUpdateDoFn(BIGTABLE_INSTANCE)
        )
        
        decisions | "StoreToBigQuery" >> beam.io.WriteToBigQuery(
            table=f"{PROJECT_ID}:{DATASET}.transactions",
            schema=TRANSACTION_BQ_SCHEMA,
            write_disposition=BigQueryDisposition.WRITE_APPEND
        )


def apply_fraud_rules(enriched_txn: EnrichedTransaction) -> RuleResult:
    """Rule engine — ordered by computational cost (cheap first)."""
    
    rules = [
        # Rule 1: Blacklist check (O(1) Bigtable lookup — already in enrichment)
        ("blacklist", enriched_txn.features.blacklist_flag == True),
        
        # Rule 2: Amount threshold (configurable per customer segment)
        ("amount_threshold", enriched_txn.txn.amount > enriched_txn.features.amount_limit),
        
        # Rule 3: Velocity — more than 10 txns in 1 hour
        ("velocity_1h", enriched_txn.features.txn_count_1h > 10),
        
        # Rule 4: Geo-velocity — impossible travel
        ("geo_velocity", is_impossible_travel(
            enriched_txn.features.last_txn_location,
            enriched_txn.txn.location,
            enriched_txn.features.last_txn_ts,
            enriched_txn.txn.timestamp
        )),
        
        # Rule 5: New merchant category for this customer
        ("new_mcc", enriched_txn.txn.mcc not in enriched_txn.features.known_mccs),
    ]
    
    triggered_rules = [name for name, condition in rules if condition]
    risk_score_from_rules = len(triggered_rules) / len(rules)
    
    return RuleResult(
        triggered_rules=triggered_rules,
        rule_risk_score=risk_score_from_rules,
        requires_ml_scoring=0.2 < risk_score_from_rules < 0.8  # ML only for borderline
    )
```

#### ML Model Serving — Achieving < 50ms Inference

**Model architecture choices:**
- Gradient Boosted Trees (XGBoost/LightGBM): ~5ms inference, good accuracy, interpretable
- Neural network (Vertex AI): ~30-50ms, higher accuracy, black-box
- Hybrid: Rules + GBT for <5ms decisions on clear cases; NN for borderline

**Model hot-swap without downtime:**
```
Traffic routing pattern:
  - Active model: receives 100% traffic
  - Candidate model: shadow mode (receives copy of traffic, results not used)
  - After validation: 10% → 25% → 50% → 100% canary rollout
  - Rollback: instant — just update model endpoint pointer in config
  
Implementation:
  - Vertex AI Endpoints support traffic splitting natively
  - Dataflow reads model endpoint from Firestore config
  - Config update triggers new model without pipeline restart
```

---

### Step 5: Bigtable Schema for Risk Profiles

```
Row Key Design: [customer_id]#[shard_prefix]
(Sharding prevents hotspots for high-velocity customers)

Column Families:
  cf:risk          → risk_score, risk_tier, blacklist_flag
  cf:velocity      → txn_count_1h, txn_count_24h, amount_sum_1h
  cf:geo           → last_txn_location, last_txn_ts
  cf:patterns      → known_mccs (serialized set), avg_amount, stddev_amount

TTL Configuration:
  cf:velocity: 24 hours (auto-expire old counters)
  cf:risk: 90 days
  cf:geo: 30 days
  cf:patterns: 1 year

Read Pattern:
  Single row read by customer_id → all feature columns
  P99 latency: < 10ms at 50,000 RPS with 20-node cluster
```

---

### Step 6: Handling the 200ms SLA Under Load

The P99 < 200ms SLA is the hardest constraint. Under peak 50K TPS:

**Pub/Sub back-pressure handling:**
- Pub/Sub buffers up to 7 days of messages; no loss during spikes
- Dataflow auto-scales workers based on subscription backlog
- Scale from 50 to 500 workers in ~90 seconds (cold start bottleneck)
- Use Dataflow Streaming Engine (serverless) to eliminate worker cold start

**Bigtable latency management:**
- Bigtable P99 < 10ms is achievable with proper key design
- Avoid hotspots: hash-prefix the customer_id
- Pre-warm app profiles with frequent customers in cache
- Use Bigtable connection pools with keepalive

**ML inference optimization:**
- Batch small groups of transactions for GPU inference
- Use Vertex AI Prediction with autoscaling (0 to N replicas)
- Cache model in memory; no cold-loading per request
- If ML endpoint is slow: fail-open (approve + flag for review) rather than blocking payment

---

---

## QUESTION 3: DESIGN A MULTI-TENANT DATA WAREHOUSE PLATFORM

### Problem Statement

> "Design a multi-tenant data warehouse platform for a large enterprise where 200+ internal teams share infrastructure but need complete data isolation, cost attribution, and independent scaling. Teams range from small analytics teams (10 queries/day) to heavy engineering teams (10,000 queries/day)."

---

### Step 1: Requirements Clarification

**Functional Requirements:**
- 200+ tenants (teams) sharing a common BigQuery environment
- Complete data isolation: Team A cannot read Team B's data without explicit grant
- Cost attribution: per-team cost reporting with chargeback capability
- Independent query scaling: Team A's heavy workload cannot degrade Team B
- Self-service onboarding: New team provisioned in < 1 hour
- Centralized governance: Data catalog, lineage, compliance from one pane
- Cross-team data sharing with approval workflow

**Non-Functional Requirements:**
- Query concurrency: 10,000 concurrent queries across all tenants
- Query latency: P95 < 30 seconds for interactive queries
- Storage: 500 TB total, growing 5 TB/week
- Availability: 99.9%
- Cost: < $500K/year for infrastructure

---

### Step 2: Tenant Isolation Architecture

The core design question: **one GCP project per tenant, or multi-tenant within a single project?**

| Approach | Pros | Cons | Best For |
|---|---|---|---|
| One project per tenant | Perfect isolation, easy billing | 200+ projects = management nightmare | External customers |
| Single project, dataset-level isolation | Simple management | IAM complexity, quota sharing | Internal teams |
| **Shared project + BQ resource reservation** | **Balance of isolation + manageability** | **Slightly more complex setup** | **This use case** |

**Chosen approach: Shared project with BigQuery Reservations + Dataset-level IAM**

```
ARCHITECTURE:
━━━━━━━━━━━━
GCP Organization
  └── Folder: data-platform
       ├── Project: cdm-platform-prod (control plane)
       └── Project: cdm-data-warehouse (data plane)
            ├── BQ Dataset: team_finance (IAM: finance-data@)
            ├── BQ Dataset: team_risk (IAM: risk-data@)
            ├── BQ Dataset: team_marketing (IAM: marketing-data@)
            ├── BQ Dataset: shared_reference (IAM: all-data-users@)
            └── BQ Reservations:
                 ├── reservation/finance: 500 slots (committed)
                 ├── reservation/risk: 300 slots (committed)
                 ├── reservation/marketing: 200 slots (committed)
                 └── reservation/default: 1000 slots (auto-scale)
```

#### IAM Policy Design

```python
# Terraform-managed IAM for each team dataset

resource "google_bigquery_dataset_iam_binding" "team_owners" {
  for_each = var.teams
  
  dataset_id = "team_${each.key}"
  role       = "roles/bigquery.dataEditor"
  
  members = [
    "group:${each.key}-data-owners@company.com"
  ]
}

resource "google_bigquery_dataset_iam_binding" "team_viewers" {
  for_each = var.teams
  
  dataset_id = "team_${each.key}"
  role       = "roles/bigquery.dataViewer"
  
  members = [
    "group:${each.key}-data-analysts@company.com"
  ]
}

# Row-level security for sensitive tables
resource "google_bigquery_row_access_policy" "pii_access" {
  dataset_id = "team_finance"
  table_id   = "customer_accounts"
  policy_id  = "pii_restricted"
  
  filter_predicate = "data_classification != 'PII' OR SESSION_USER() IN (SELECT email FROM `team_finance.pii_authorized_users`)"
  
  grantees = ["group:finance-analysts@company.com"]
}
```

---

### Step 3: Cost Attribution System

**Query-level cost tracking:**

```sql
-- BigQuery INFORMATION_SCHEMA for cost attribution
CREATE OR REPLACE VIEW cdm_metadata.team_cost_daily AS
SELECT
  DATE(creation_time) AS query_date,
  -- Extract team from reservation assignment
  reservation_id AS team_reservation,
  -- Compute cost: 1 TB = $5 (on-demand rate)
  user_email,
  COUNT(*) AS query_count,
  SUM(total_bytes_billed) / POW(10, 12) AS tb_billed,
  SUM(total_bytes_billed) / POW(10, 12) * 5 AS estimated_cost_usd,
  SUM(total_slot_ms) / 1000 AS total_slot_seconds,
  AVG(TIMESTAMP_DIFF(end_time, start_time, MILLISECOND)) AS avg_latency_ms
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
  AND job_type = 'QUERY'
  AND state = 'DONE'
GROUP BY 1, 2, 3
ORDER BY query_date DESC, estimated_cost_usd DESC;
```

**Monthly chargeback report:**
```sql
-- Monthly chargeback by team with budget alerts
WITH monthly_costs AS (
  SELECT
    FORMAT_DATE('%Y-%m', query_date) AS month,
    team_reservation,
    SUM(estimated_cost_usd) AS total_cost_usd,
    SUM(query_count) AS total_queries,
    SUM(tb_billed) AS total_tb_billed
  FROM cdm_metadata.team_cost_daily
  GROUP BY 1, 2
),
budgets AS (
  SELECT team_id, monthly_budget_usd
  FROM cdm_metadata.team_budgets
)
SELECT
  m.*,
  b.monthly_budget_usd,
  m.total_cost_usd / b.monthly_budget_usd * 100 AS budget_utilization_pct,
  CASE 
    WHEN m.total_cost_usd > b.monthly_budget_usd THEN 'OVER_BUDGET'
    WHEN m.total_cost_usd > b.monthly_budget_usd * 0.8 THEN 'WARNING'
    ELSE 'OK'
  END AS budget_status
FROM monthly_costs m
JOIN budgets b ON m.team_reservation LIKE CONCAT('%', b.team_id, '%')
ORDER BY month DESC, total_cost_usd DESC;
```

---

### Step 4: Query Governance & Abuse Prevention

In a multi-tenant environment, one bad query can consume all available slots.

**Query Governor (Cloud Run service):**
```python
class QueryGovernor:
    """Intercepts BigQuery queries before execution."""
    
    def __init__(self, config: GovernorConfig):
        self.config = config
        self.bq_client = bigquery.Client()
        
    def pre_flight_check(self, query: str, user_email: str, team: str) -> CheckResult:
        
        # 1. Dry-run to estimate bytes processed
        job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        dry_run_job = self.bq_client.query(query, job_config=job_config)
        estimated_bytes = dry_run_job.total_bytes_processed
        
        # 2. Check against team limits
        team_limits = self.config.get_limits(team)
        
        if estimated_bytes > team_limits.max_bytes_per_query:
            return CheckResult(
                allowed=False,
                reason=f"Query estimated {estimated_bytes/1e12:.2f} TB exceeds team limit of {team_limits.max_bytes_per_query/1e12:.2f} TB"
            )
        
        # 3. Check team's daily quota
        daily_usage = self.get_daily_usage(team)
        if daily_usage + estimated_bytes > team_limits.daily_bytes_quota:
            return CheckResult(
                allowed=False,
                reason=f"Query would exceed team's daily quota. Used: {daily_usage/1e12:.2f} TB, Limit: {team_limits.daily_bytes_quota/1e12:.2f} TB"
            )
        
        # 4. Complexity check (prevent cartesian joins, etc.)
        if has_cross_join_without_filter(query):
            return CheckResult(
                allowed=False,
                reason="Query contains cross join without filter condition. Add WHERE clause."
            )
        
        return CheckResult(allowed=True, estimated_bytes=estimated_bytes)
```

---

### Step 5: Cross-Team Data Sharing with Approval Workflow

```
REQUEST FLOW:
━━━━━━━━━━━━
1. Team A analyst submits: "I need read access to team_finance.revenue_summary"
2. Data portal creates approval ticket (Jira/ServiceNow)
3. Team Finance data owner gets notified (email + Slack)
4. Data owner approves → Terraform PR auto-generated
5. PR reviewed by platform team → merged → IAM updated
6. Requester gets notified: "Access granted for 90 days"
7. After 90 days: access auto-revoked unless renewed

IMPLEMENTATION:
━━━━━━━━━━━━━━
- Cloud Workflows orchestrates the approval flow
- Terraform Cloud applies IAM changes on PR merge
- Dataplex manages data catalog entries and policy tags
- All access grants logged to BigQuery for compliance audit

AUTHORIZED VIEW PATTERN (preferred over direct dataset access):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- In team_finance dataset:
CREATE VIEW team_finance.revenue_summary_shared AS
SELECT
  fiscal_year,
  fiscal_quarter,
  business_unit,
  total_revenue,
  -- Do NOT expose: customer_id, contract_value, margin
FROM team_finance.revenue_raw
WHERE data_classification = 'PUBLIC_INTERNAL';

-- Grant only view access to requesting team, never underlying table
GRANT `roles/bigquery.dataViewer` ON VIEW `team_finance.revenue_summary_shared`
TO 'group:team-analytics-data@company.com';
```

---

---

## QUESTION 4: DESIGN A REAL-TIME ANALYTICS DASHBOARD PLATFORM

### Problem Statement

> "Design a platform that powers real-time analytics dashboards for business users. Dashboards show metrics that update within 30 seconds of an event occurring. The platform serves 5,000 concurrent dashboard users, handles 1 million events per minute, and needs to support ad-hoc query capability alongside pre-aggregated views."

---

### Step 1: The Core Tension

Real-time analytics has a fundamental tension:

```
SPEED vs COST vs FLEXIBILITY

Pre-aggregated (Materialized Views):
  ✓ Sub-second query response
  ✓ Low cost (pre-computed)
  ✗ Inflexible — must predict queries in advance
  ✗ Stale by aggregation window

Ad-hoc on raw (BigQuery streaming inserts):
  ✓ Fully flexible — any query
  ✗ Expensive at high QPS
  ✗ Minutes-scale latency for complex queries
  
Lambda Architecture hybrid:
  ✓ Speed layer for recent data (< 1 hour)
  ✓ Batch layer for historical accuracy
  ✗ Complex to maintain two code paths
```

**Solution for this problem: Lambda + BigQuery BI Engine + Materialized Views**

---

### Step 2: Architecture

```
EVENT SOURCES                                                         
┌──────────────┐    ┌─────────────┐    ┌──────────────────────────┐
│ App Events   │───►│  Pub/Sub    │───►│   Dataflow Stream        │
│ Clickstream  │    │  (Ingestion)│    │                          │
│ Transactions │    └─────────────┘    │  • Validate & enrich     │
└──────────────┘                       │  • Compute micro-batch   │
                                       │    aggregations (1-min)   │
                                       │  • Write to multiple sinks│
                                       └──────────────────────────┘
                                                    │
                          ┌─────────────────────────┼───────────────┐
                          ▼                         ▼               ▼
                  ┌──────────────┐      ┌──────────────────┐  ┌──────────┐
                  │   Bigtable   │      │    BigQuery       │  │   GCS    │
                  │  (Hot Data)  │      │  (Warm + Cold)    │  │  (Cold   │
                  │              │      │                   │  │  Archive)│
                  │ Last 1 hour  │      │ Streaming buffer  │  │          │
                  │ of events    │      │ + Historical      │  │ 7+ years │
                  │ by dimension │      │ Partitioned tables│  │          │
                  └──────┬───────┘      └────────┬──────────┘  └──────────┘
                         │                       │
                         └──────────┬────────────┘
                                    ▼
                          ┌──────────────────┐
                          │   Query Router   │
                          │   (Cloud Run)    │
                          │                  │
                          │ recent? → Bigtable│
                          │ historical? → BQ  │
                          │ complex? → BQ     │
                          └──────────────────┘
                                    │
                                    ▼
                          ┌──────────────────┐
                          │  BI Engine Cache │
                          │  (in-memory BQ)  │
                          │                  │
                          │ Popular queries  │
                          │ served in-memory │
                          │ < 100ms response │
                          └──────────────────┘
                                    │
                                    ▼
                          ┌──────────────────┐
                          │   Dashboard      │
                          │   Frontend       │
                          │   (Looker/       │
                          │    Looker Studio)│
                          └──────────────────┘
```

---

### Step 3: BigQuery Materialized Views for Dashboard Metrics

```sql
-- Pre-aggregate key metrics every 5 minutes
-- BigQuery auto-refreshes materialized views incrementally

CREATE MATERIALIZED VIEW analytics.revenue_by_region_5min
OPTIONS (
  enable_refresh = true,
  refresh_interval_minutes = 5,
  allow_non_incremental_definition = false
)
AS
SELECT
  TIMESTAMP_TRUNC(event_ts, MINUTE) AS minute_bucket,
  region,
  product_category,
  COUNT(*) AS transaction_count,
  SUM(amount) AS total_revenue,
  AVG(amount) AS avg_order_value,
  COUNT(DISTINCT customer_id) AS unique_customers
FROM analytics.raw_transactions
WHERE event_ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY 1, 2, 3;

-- BigQuery BI Engine reserved for this dataset
-- Automatically serves this materialized view from in-memory cache
-- Query response: < 100ms for cached results
```

---

### Step 4: Handling 5,000 Concurrent Users

```
CONCURRENCY STRATEGY:
━━━━━━━━━━━━━━━━━━━━
5,000 users × 10 queries/hour = 50,000 queries/hour = 14 QPS

BigQuery can handle this easily IF:
  1. Queries hit materialized views (cached by BI Engine)
  2. BI Engine has enough reserved memory
  3. Queries are parameterized (not unique per user)

BI ENGINE SIZING:
━━━━━━━━━━━━━━━━
Most popular 20% of tables/views serve 80% of queries
Reserve 100 GB BI Engine capacity for top tables
Cost: 100 GB × $0.04/GB-hour = $4/hour

RATE LIMITING:
━━━━━━━━━━━━━
- Per-user: max 10 concurrent queries
- Per-dashboard: max 50 queries/minute
- Global: BigQuery project-level 300 concurrent queries limit
- Queue excess requests with 30-second timeout

QUERY RESULT CACHING:
━━━━━━━━━━━━━━━━━━━━
- BQ caches identical queries for 24 hours (free)
- Dashboard frontend caches last result for 30 seconds
- Parameterized queries by time range avoid cache busting
```

---

### Step 5: 30-Second Freshness Guarantee

```
DATA FRESHNESS PATH:
━━━━━━━━━━━━━━━━━━━

Event occurs → Pub/Sub (< 1s) → Dataflow window close (10s) 
→ BigQuery streaming insert (< 1s) → BI Engine cache invalidation (5s)
→ Dashboard refresh (10s polling)

TOTAL: ~27 seconds ✓

OPTIMIZATION POINTS:
  1. Dataflow: Use 10-second tumbling windows (not 60s)
  2. BigQuery: streaming inserts visible immediately
  3. BI Engine: invalidate cache on new data arrival (webhook)
  4. Dashboard: WebSocket push instead of polling (reduces to < 15s)

FRESHNESS MONITORING:
━━━━━━━━━━━━━━━━━━━━
SELECT 
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(event_ts), SECOND) AS data_lag_seconds
FROM analytics.raw_transactions;
-- Alert if > 60 seconds
```

---

---

## QUESTION 5: DESIGN A DATA LINEAGE AND GOVERNANCE PLATFORM

### Problem Statement

> "Design a data lineage platform that automatically tracks how data flows from source systems to consumption points, enabling: (1) impact analysis — 'if I change this table, what breaks?', (2) root cause analysis — 'this dashboard is wrong, where did the bad data come from?', (3) compliance reporting — 'show me all data flows that touch PII.'"

---

### Step 1: What is Data Lineage?

Data lineage is the complete audit trail of data's journey:

```
SOURCE → INGESTION → TRANSFORMATION → STORAGE → CONSUMPTION

Example lineage graph:
  Oracle.ACCOUNTS 
    → Dataflow.AccountsIngestion 
    → GCS.raw/accounts/ 
    → Dataflow.AccountsTransform 
    → BigQuery.finance.accounts_clean 
    → dbt.monthly_revenue_model 
    → BigQuery.analytics.monthly_revenue 
    → Looker.RevenueByRegionDashboard
    → (consumed by: FinanceTeam, ExecDashboard)
```

---

### Step 2: Lineage Capture Strategies

**Strategy 1: API-based lineage (OpenLineage standard)**

OpenLineage is the industry standard (used by Airflow, dbt, Spark, Flink). Every job emits lineage events via HTTP to a lineage backend.

```json
{
  "eventType": "COMPLETE",
  "eventTime": "2024-01-15T10:30:00Z",
  "job": {
    "namespace": "cdm-next",
    "name": "accounts_daily_ingest"
  },
  "inputs": [
    {
      "namespace": "oracle://prod-db",
      "name": "PROD_DW.ACCOUNTS",
      "facets": {
        "schema": {
          "fields": [
            {"name": "ACCT_ID", "type": "VARCHAR"},
            {"name": "BALANCE", "type": "DECIMAL"}
          ]
        }
      }
    }
  ],
  "outputs": [
    {
      "namespace": "bigquery://project.finance",
      "name": "accounts_clean",
      "facets": {
        "columnLineage": {
          "fields": {
            "acct_id": {"inputFields": [{"namespace": "oracle://prod-db", "name": "PROD_DW.ACCOUNTS", "field": "ACCT_ID"}]},
            "balance": {"inputFields": [{"namespace": "oracle://prod-db", "name": "PROD_DW.ACCOUNTS", "field": "BALANCE"}]}
          }
        }
      }
    }
  ]
}
```

**Strategy 2: SQL parsing lineage (for dbt/SQL transformations)**

```python
import sqlglot

def extract_column_lineage_from_sql(sql: str, dialect: str = "bigquery") -> LineageGraph:
    """
    Parse SQL and extract column-level lineage automatically.
    No instrumentation needed — works on any SQL.
    """
    parsed = sqlglot.parse_one(sql, dialect=dialect)
    
    lineage_graph = LineageGraph()
    
    # Extract SELECT columns and their sources
    for select_expr in parsed.selects:
        output_col = select_expr.alias_or_name
        
        # Trace each column back to its source
        source_cols = trace_column_to_source(select_expr, parsed)
        
        for source_col in source_cols:
            lineage_graph.add_edge(
                source=source_col,
                target=output_col,
                transformation=get_transformation_type(select_expr)
            )
    
    # Extract source tables
    for table in parsed.find_all(sqlglot.exp.Table):
        lineage_graph.add_table_reference(table.name)
    
    return lineage_graph
```

**Strategy 3: Dataplex auto-lineage (GCP-native)**

For BigQuery-to-BigQuery flows, Dataplex automatically captures lineage:
- BigQuery jobs automatically emit lineage to Dataplex
- No instrumentation needed for BQ-native transformations
- Column-level lineage for SQL jobs
- Integrated with Data Catalog entries

---

### Step 3: Lineage Storage — Graph Database Design

Lineage is a directed acyclic graph (DAG). Optimal storage: graph database.

**Spanner Graph (or Neo4j for non-GCP) schema:**

```sql
-- Nodes: data assets
CREATE TABLE lineage_nodes (
  node_id STRING NOT NULL,
  node_type STRING NOT NULL,  -- TABLE, VIEW, FILE, TOPIC, DASHBOARD, JOB
  fqn STRING NOT NULL,  -- fully qualified name: project.dataset.table
  namespace STRING,
  platform STRING,  -- bigquery, kafka, gcs, looker
  schema_json STRING,  -- current schema
  tags JSON,  -- PII, PCI, CONFIDENTIAL
  created_at TIMESTAMP,
  PRIMARY KEY (node_id)
);

-- Edges: data flows
CREATE TABLE lineage_edges (
  edge_id STRING NOT NULL,
  source_node_id STRING NOT NULL,
  target_node_id STRING NOT NULL,
  edge_type STRING,  -- READS_FROM, WRITES_TO, TRANSFORMS
  job_name STRING,
  job_run_id STRING,
  column_mappings JSON,  -- source_col → target_col mappings
  created_at TIMESTAMP,
  PRIMARY KEY (edge_id),
  FOREIGN KEY (source_node_id) REFERENCES lineage_nodes(node_id),
  FOREIGN KEY (target_node_id) REFERENCES lineage_nodes(node_id)
);

-- Index for fast traversal
CREATE INDEX idx_lineage_source ON lineage_edges(source_node_id);
CREATE INDEX idx_lineage_target ON lineage_edges(target_node_id);
```

---

### Step 4: Impact Analysis Query (Upstream/Downstream)

```python
def get_downstream_impact(
    node_fqn: str,
    max_depth: int = 10
) -> List[ImpactedAsset]:
    """
    Given a table/column, find everything that would break if it changes.
    Used for: "I want to delete this column, what breaks?"
    """
    
    query = """
    WITH RECURSIVE downstream AS (
      -- Base case: the changed node
      SELECT 
        n.node_id,
        n.fqn,
        n.node_type,
        n.platform,
        0 AS depth,
        ARRAY[n.node_id] AS path
      FROM lineage_nodes n
      WHERE n.fqn = @target_fqn
      
      UNION ALL
      
      -- Recursive case: follow edges downstream
      SELECT
        n.node_id,
        n.fqn,
        n.node_type,
        n.platform,
        d.depth + 1 AS depth,
        d.path || n.node_id AS path
      FROM downstream d
      JOIN lineage_edges e ON e.source_node_id = d.node_id
      JOIN lineage_nodes n ON n.node_id = e.target_node_id
      WHERE d.depth < @max_depth
        AND NOT n.node_id = ANY(d.path)  -- Prevent cycles
    )
    SELECT DISTINCT
      node_id, fqn, node_type, platform, depth
    FROM downstream
    WHERE depth > 0
    ORDER BY depth, fqn;
    """
    
    results = spanner_client.execute_query(query, params={"target_fqn": node_fqn, "max_depth": max_depth})
    
    return [
        ImpactedAsset(
            fqn=row.fqn,
            type=row.node_type,
            platform=row.platform,
            hop_distance=row.depth,
            severity=classify_severity(row.node_type)
        )
        for row in results
    ]


def get_upstream_root_cause(node_fqn: str) -> List[DataSource]:
    """
    Given a broken dashboard/table, trace back to source systems.
    Used for: "My dashboard shows wrong numbers. Where did the bad data come in?"
    """
    # Same query but traverse edges in reverse direction
    # Follow lineage_edges where target_node_id = current node
    pass
```

---

### Step 5: PII Compliance Reporting

```sql
-- Find all data flows that touch PII-tagged assets
-- Critical for GDPR Article 30 records of processing activities

WITH RECURSIVE pii_flows AS (
  -- Start from PII-tagged source tables
  SELECT 
    n.node_id,
    n.fqn AS asset_fqn,
    n.node_type,
    n.tags,
    0 AS hop_count,
    ARRAY[n.fqn] AS lineage_path
  FROM lineage_nodes n
  WHERE JSON_VALUE(n.tags, '$.pii') = 'true'
  
  UNION ALL
  
  -- Follow downstream
  SELECT
    target.node_id,
    target.fqn,
    target.node_type,
    target.tags,
    f.hop_count + 1,
    f.lineage_path || target.fqn
  FROM pii_flows f
  JOIN lineage_edges e ON e.source_node_id = f.node_id
  JOIN lineage_nodes target ON target.node_id = e.target_node_id
  WHERE f.hop_count < 15
)
SELECT
  lineage_path[1] AS pii_source,
  asset_fqn AS downstream_asset,
  node_type,
  hop_count,
  lineage_path
FROM pii_flows
WHERE hop_count > 0
ORDER BY pii_source, hop_count, asset_fqn;
```

---

---

## QUESTION 6: DESIGN A CONFIGURATION-DRIVEN ML FEATURE PLATFORM

### Problem Statement

> "Design a feature platform that allows ML teams to: (1) define features once and reuse across multiple models, (2) ensure training-serving consistency (no training-serving skew), (3) serve features with < 10ms latency for online inference, (4) support both batch and real-time feature computation."

---

### Step 1: The Training-Serving Skew Problem

This is the #1 failure mode in production ML:

```
TRAINING TIME:
  Feature = "customer's average purchase in last 30 days"
  Computed using: pandas.rolling(30).mean()
  Data source: Snowflake historical table
  
SERVING TIME (3 months later):
  Same feature computed using: different SQL query on BigQuery
  Data source: different table, different schema
  
RESULT: Model trained on Feature-A, served Feature-B → silent model degradation
```

The feature platform eliminates this by ensuring one definition, used everywhere.

---

### Step 2: Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              ML FEATURE PLATFORM ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  FEATURE DEFINITION                                             │
│  ┌─────────────────────────────────────────────┐               │
│  │  Feature Repository (Git)                    │               │
│  │                                              │               │
│  │  customer_features.py:                       │               │
│  │    @feature(name="avg_purchase_30d",         │               │
│  │             entity="customer_id",            │               │
│  │             ttl_days=1)                      │               │
│  │    def avg_purchase_30d(txns: DataFrame):    │               │
│  │      return txns.rolling("30d").amount.mean()│               │
│  └─────────────────────────────────────────────┘               │
│                    │                                            │
│          ┌─────────┴──────────┐                                 │
│          ▼                    ▼                                 │
│  ┌───────────────┐    ┌──────────────────┐                     │
│  │ BATCH         │    │ STREAMING        │                     │
│  │ MATERIALIZATION│    │ MATERIALIZATION  │                     │
│  │               │    │                  │                     │
│  │ Cloud Composer│    │ Dataflow         │                     │
│  │ + Dataproc    │    │ (real-time)      │                     │
│  └───────┬───────┘    └────────┬─────────┘                     │
│          │                     │                                │
│          └──────────┬──────────┘                                │
│                     ▼                                           │
│          ┌─────────────────────┐                                │
│          │   FEATURE STORE     │                                │
│          │                     │                                │
│          │  Bigtable (online)  │  ← Low-latency serving        │
│          │  BigQuery (offline) │  ← Training data retrieval    │
│          └──────────┬──────────┘                                │
│                     │                                           │
│          ┌──────────┴──────────┐                                │
│          ▼                     ▼                                │
│  ┌───────────────┐    ┌──────────────────┐                     │
│  │ ONLINE        │    │ OFFLINE           │                     │
│  │ SERVING       │    │ SERVING           │                     │
│  │               │    │                   │                     │
│  │ < 10ms        │    │ Training dataset  │                     │
│  │ REST API      │    │ point-in-time     │                     │
│  │ (Cloud Run)   │    │ correct joins     │                     │
│  └───────────────┘    └───────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

---

### Step 3: Feature Definition DSL

```python
from feature_platform import feature, entity, FeatureView

# Define the entity (what features are keyed on)
customer = entity(
    name="customer",
    join_key="customer_id",
    description="Customer entity for all customer-level features"
)

# Define a feature view (group of related features)
@FeatureView(
    name="customer_transaction_features",
    entities=[customer],
    ttl=timedelta(days=1),  # Features expire after 1 day
    online=True,  # Materialize to online store (Bigtable)
    offline=True  # Materialize to offline store (BigQuery)
)
def customer_transaction_features(transactions: DataFrame) -> DataFrame:
    """
    Computes transaction-based features for customers.
    This same code runs during batch materialization AND online serving.
    Eliminates training-serving skew.
    """
    return (
        transactions
        .groupby("customer_id")
        .agg(
            avg_txn_30d=("amount", lambda x: x.rolling("30d").mean().iloc[-1]),
            txn_count_7d=("txn_id", lambda x: x.rolling("7d").count().iloc[-1]),
            max_txn_90d=("amount", lambda x: x.rolling("90d").max().iloc[-1]),
            days_since_last_txn=("txn_ts", lambda x: (pd.Timestamp.now() - x.max()).days)
        )
        .reset_index()
    )
```

---

### Step 4: Point-in-Time Correct Feature Retrieval (Critical for Training)

The biggest mistake in ML feature stores: **label leakage**.

```
WRONG (future data leaks into training):
  Training label: "did customer churn in month 3?"
  Features: computed using ALL data including months 1, 2, 3, 4
  → Model learns from future, performs badly in production

CORRECT (point-in-time):
  Training label: "did customer churn in month 3?"
  Features: computed using ONLY data available BEFORE prediction time
  → Model only sees what it would see in production
```

```python
def get_historical_features(
    entity_df: pd.DataFrame,  # Contains: customer_id, event_timestamp
    feature_views: List[str]
) -> pd.DataFrame:
    """
    Retrieves features as of each row's event_timestamp.
    This is point-in-time correct retrieval.
    """
    
    results = []
    
    for _, row in entity_df.iterrows():
        customer_id = row["customer_id"]
        as_of_ts = row["event_timestamp"]
        
        # BigQuery query: get features as of this timestamp
        query = f"""
        SELECT 
          customer_id,
          avg_txn_30d,
          txn_count_7d,
          max_txn_90d
        FROM `feature_store.customer_transaction_features`
        WHERE customer_id = '{customer_id}'
          AND feature_ts <= TIMESTAMP('{as_of_ts}')
        ORDER BY feature_ts DESC
        LIMIT 1
        """
        
        features = bq_client.query(query).to_dataframe()
        results.append(features)
    
    return pd.concat(results).reset_index(drop=True)
```

---

### Step 5: Online Feature Serving at < 10ms

```python
# Cloud Run service for online feature serving
from fastapi import FastAPI
from google.cloud import bigtable

app = FastAPI()
bt_client = bigtable.Client(project=PROJECT_ID)
table = bt_client.instance(INSTANCE_ID).table(TABLE_ID)

@app.get("/features/{customer_id}")
async def get_online_features(
    customer_id: str,
    feature_names: List[str]
) -> Dict[str, Any]:
    """
    P99 target: < 10ms
    Bigtable single-row read: < 5ms
    Network overhead: < 3ms (same VPC)
    Total: < 10ms ✓
    """
    
    # Single Bigtable row read (all features for one customer)
    row = table.read_row(
        row_key=f"customer#{customer_id}".encode(),
        filter_=bigtable.row_filters.ColumnQualifierRegexFilter(
            "|".join(feature_names).encode()
        )
    )
    
    if row is None:
        # Feature not found — return defaults
        return {name: DEFAULT_FEATURE_VALUES[name] for name in feature_names}
    
    features = {}
    for feature_name in feature_names:
        cell = row.cells["features"][feature_name.encode()][0]
        features[feature_name] = deserialize_feature_value(cell.value)
    
    return features
```

---

## MODULE 6 SUMMARY: KEY DESIGN PATTERNS ACROSS ALL QUESTIONS

| Pattern | Where Used | Why It Matters |
|---|---|---|
| Config-driven design | Q1 (CDM Next) | Scalability without code changes |
| Idempotent writes | Q1, Q2 | Exactly-once semantics |
| Hot/warm/cold storage tiering | Q2, Q4 | Cost-performance balance |
| Schema evolution handling | Q1, Q5 | Production stability |
| Graph traversal for impact analysis | Q5 | Lineage & governance |
| Point-in-time correctness | Q6 | ML model reliability |
| Pre-aggregation + ad-hoc hybrid | Q4 | Real-time analytics at scale |
| IAM + Resource reservations | Q3 | Multi-tenancy isolation |

---

*Module 6 Complete — 12,200 words. Proceed to Module 7: Advanced Scenarios.*
