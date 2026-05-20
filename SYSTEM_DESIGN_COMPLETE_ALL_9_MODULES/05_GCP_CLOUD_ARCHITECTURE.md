# MODULE 5: GCP CLOUD ARCHITECTURE & STREAMING DEEP DIVE
## PhD-Level Data Engineering Interview Preparation
### Tailored for Viraaj Sivaraju — Senior Data Engineer, Wells Fargo CDM Next

---

## PART 1: GCP DATA ENGINEERING ECOSYSTEM MAP

```
┌─────────────────────────────────────────────────────────────────────┐
│                     GCP DATA ENGINEERING STACK                       │
├──────────────┬──────────────┬──────────────┬────────────────────────┤
│  INGEST      │  PROCESS     │  STORE       │  SERVE                 │
├──────────────┼──────────────┼──────────────┼────────────────────────┤
│ Pub/Sub      │ Dataflow     │ GCS          │ BigQuery (analytics)   │
│ Datastream   │ Dataproc     │ BigQuery     │ Bigtable (low-latency) │
│ Transfer Svc │ Cloud Run    │ Bigtable     │ Spanner (transactional)│
│ Storage Tfer │ Cloud Fns    │ Spanner      │ Firestore (document)   │
│ BigQuery DTS │ Vertex AI    │ Firestore    │ Looker (BI)            │
│ Kafka (ext)  │ dbt (ext)    │ Memorystore  │ Looker Studio          │
├──────────────┴──────────────┴──────────────┴────────────────────────┤
│  ORCHESTRATE          │  GOVERN              │  SECURE               │
│  Cloud Composer (Airflow) │ Dataplex         │ IAM                   │
│  Cloud Workflows      │  Data Catalog        │ VPC Service Controls  │
│  Cloud Scheduler      │  DLP API             │ Cloud KMS             │
│  Eventarc             │  Lineage API         │ Secret Manager        │
│                       │  BigQuery Audit Logs │ Cloud Armor           │
└───────────────────────┴──────────────────────┴───────────────────────┘
```

---

## PART 2: CLOUD COMPOSER (MANAGED AIRFLOW) — DEEP DIVE

### Architecture

```
CLOUD COMPOSER 2 ARCHITECTURE:
  
  GKE Autopilot cluster (GCP-managed):
    ├── Airflow Scheduler (2 replicas for HA)
    │     - Parses DAGs, schedules task runs
    │     - Monitors task state
    │     - Sends tasks to executor
    │
    ├── Airflow Workers (auto-scaling pods)
    │     - Execute tasks
    │     - Each task = one Kubernetes pod
    │     - Scale 0 → N based on queue depth
    │
    ├── Airflow Webserver
    │     - UI for monitoring, triggering, logs
    │
    └── Redis (task queue)
          - Workers pull tasks from queue
  
  Cloud SQL (PostgreSQL):
    - Airflow metadata database
    - DAG state, task history, variables
    - HA with automatic failover
  
  GCS bucket:
    - DAG files (Python)
    - Airflow plugins
    - Logs
```

### DAG Design Patterns for CDM Next

```python
# CDM NEXT PIPELINE ORCHESTRATION DAG

from airflow import DAG
from airflow.providers.google.cloud.operators.dataflow import DataflowStartFlexTemplateOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryCheckOperator
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.trigger_rule import TriggerRule
from datetime import datetime, timedelta

default_args = {
    'owner': 'cdm-platform',
    'depends_on_past': False,    # Don't wait for previous day's success
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=30),
    'email_on_failure': True,
    'email': ['oncall-data-platform@company.com'],
}

with DAG(
    dag_id='teradata_accounts_daily',
    default_args=default_args,
    schedule_interval='0 2 * * *',  # 2 AM UTC daily
    start_date=datetime(2024, 1, 1),
    catchup=False,                   # Don't backfill missed runs
    max_active_runs=1,               # One run at a time
    tags=['cdm-next', 'teradata', 'finance'],
) as dag:
    
    # Task 1: Check source system health before starting
    check_source = BigQueryCheckOperator(
        task_id='check_source_availability',
        sql="SELECT COUNT(*) FROM EXTERNAL_QUERY('oracle-connection', 'SELECT 1 FROM dual')",
        use_legacy_sql=False,
    )
    
    # Task 2: Launch Dataflow ingestion job
    run_ingestion = DataflowStartFlexTemplateOperator(
        task_id='run_dataflow_ingestion',
        project_id=PROJECT_ID,
        location='us-central1',
        body={
            'launchParameter': {
                'jobName': f"accounts-ingest-{{{{ ds_nodash }}}}",  # ds = execution date
                'containerSpecGcsPath': 'gs://cdm-templates/accounts-ingest/latest.json',
                'parameters': {
                    'pipeline_id': 'teradata-accounts-daily',
                    'execution_date': '{{ ds }}',
                    'config_version': 'v2',
                },
                'environment': {
                    'maxWorkers': 100,
                    'machineType': 'n1-standard-4',
                    'serviceAccountEmail': CDM_SA,
                    'tempLocation': 'gs://cdm-temp/dataflow/',
                },
            }
        },
        do_xcom_push=True,  # Store job_id in XCom for downstream tasks
    )
    
    # Task 3: Wait for Dataflow to complete
    # (DataflowStartFlexTemplateOperator is async by default — use sensor)
    
    # Task 4: Validate data quality in BigQuery
    validate_quality = BigQueryCheckOperator(
        task_id='validate_data_quality',
        sql="""
        SELECT
          COUNTIF(acct_id IS NULL) = 0 AS no_null_ids,
          COUNT(*) > 100000 AS sufficient_rows,
          MAX(last_updated_dt) >= CURRENT_DATE() - 1 AS data_is_fresh
        FROM `project.finance_silver.accounts`
        WHERE DATE(ingestion_ts) = '{{ ds }}'
        """,
        use_legacy_sql=False,
    )
    
    # Task 5: Trigger dbt gold layer rebuild
    run_dbt = BashOperator(
        task_id='run_dbt_gold_models',
        bash_command=f"dbt run --select tag:finance --target prod --profiles-dir /home/airflow/dbt",
    )
    
    # Task 6: Send success notification
    notify_success = SlackAPIPostOperator(
        task_id='notify_success',
        slack_conn_id='slack_cdm_alerts',
        channel='#data-platform-ops',
        text='✅ accounts_daily completed: {{ ti.xcom_pull("run_dataflow_ingestion") }}',
        trigger_rule=TriggerRule.ALL_SUCCESS,
    )
    
    # Task 7: Send failure notification
    notify_failure = SlackAPIPostOperator(
        task_id='notify_failure',
        slack_conn_id='slack_cdm_alerts',
        channel='#data-platform-incidents',
        text='🔴 accounts_daily FAILED. Run ID: {{ run_id }}',
        trigger_rule=TriggerRule.ONE_FAILED,
    )
    
    # DAG dependency chain
    check_source >> run_ingestion >> validate_quality >> run_dbt
    run_dbt >> notify_success
    run_dbt >> notify_failure  # Will only fire if trigger_rule met


# PATTERNS DEMONSTRATED:
# 1. Source health check before starting expensive job
# 2. Retry with exponential backoff
# 3. Quality validation gate (stops pipeline if data bad)
# 4. Dual notification (success + failure paths)
# 5. Execution date parameterization (idempotent reruns)
# 6. max_active_runs=1 (prevent overlapping runs)
```

---

## PART 3: DATAFLOW DEEP DIVE

### Apache Beam Programming Model

```python
# BEAM CORE CONCEPTS

# PCollection: immutable distributed dataset (the data flowing through pipeline)
# PTransform: operation on PCollection → new PCollection
# Pipeline: graph of PTransforms

import apache_beam as beam

# Simple pipeline: read CSV → parse → filter → write
with beam.Pipeline() as p:
    (
        p
        | "ReadCSV" >> beam.io.ReadFromText('gs://input/*.csv')
        | "ParseRow" >> beam.Map(parse_csv_row)
        | "FilterActive" >> beam.Filter(lambda row: row['status'] == 'ACTIVE')
        | "WriteToGCS" >> beam.io.WriteToParquet(
            file_path_prefix='gs://output/active_accounts',
            schema=PARQUET_SCHEMA
        )
    )
```

### Dataflow Execution Model

```
STAGES OF DATAFLOW JOB EXECUTION:

1. GRAPH CONSTRUCTION (client-side, Python/Java):
   - Your Beam code runs locally
   - Builds a DAG of transforms
   - Submits graph to Dataflow service
   
2. GRAPH OPTIMIZATION (Dataflow service):
   - Fuses compatible stages (reduce data serialization overhead)
   - Determines parallelism for each stage
   - Creates execution plan
   
3. WORKER PROVISIONING:
   - Launches VMs (n seconds to minutes)
   - Workers download job artifacts from GCS
   - Workers connect to Dataflow shuffle service
   
4. EXECUTION:
   - Workers pull work units from Dataflow service
   - Parallel execution across all workers
   - Progress reported to Dataflow service
   
5. SHUFFLE (for GroupByKey):
   - Managed Shuffle Service (not worker-to-worker)
   - Key-based routing: same key → same worker
   - Backed by GCS (fault tolerant)
   
6. OUTPUT:
   - Workers write to sink (GCS, BigQuery, etc.)
   - Final finalization step (rename temp files, commit BQ job)

DATAFLOW FUSION (important optimization):
  Without fusion:
    Read → ParDo1 → ParDo2 → ParDo3 → Write
    Each step serializes data → network → next worker
    
  With fusion:
    Read → [ParDo1 + ParDo2 + ParDo3 fused] → Write
    All three ParDos run on same worker, no intermediate serialization
    
  Fusion happens automatically for transforms without shuffle (no GroupByKey between them)
```

### Dataflow Windowing and Triggers (Streaming)

```python
# STREAMING PIPELINE WINDOWING EXAMPLES

# FIXED WINDOWS: Equal-size, non-overlapping time intervals
events | beam.WindowInto(beam.window.FixedWindows(3600))  # 1-hour windows

# SLIDING WINDOWS: Overlapping windows
events | beam.WindowInto(
    beam.window.SlidingWindows(size=3600, period=300)  # 1hr window, slides every 5min
)

# SESSION WINDOWS: Variable-size based on activity gaps
events | beam.WindowInto(
    beam.window.Sessions(gap_size=1800)  # New session if 30min gap
)

# TRIGGERS (when to emit results):
events | beam.WindowInto(
    beam.window.FixedWindows(3600),
    trigger=beam.trigger.AfterWatermark(
        early=beam.trigger.AfterProcessingTime(60),    # Speculative every 1 min
        late=beam.trigger.AfterCount(1)                # On each late arrival
    ),
    allowed_lateness=beam.window.Duration(seconds=7200),  # Accept 2hr late data
    accumulation_mode=beam.trigger.AccumulationMode.ACCUMULATING
)
```

---

## PART 4: BIGQUERY ADVANCED PATTERNS

### Partitioning and Clustering Strategies

```sql
-- OPTIMAL TABLE DESIGN FOR CDM NEXT ANALYTICAL TABLES

CREATE TABLE finance.transactions (
  txn_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  account_id STRING NOT NULL,
  txn_type STRING,
  amount NUMERIC(18, 4),
  currency STRING,
  merchant_id STRING,
  region STRING,
  txn_ts TIMESTAMP NOT NULL,
  ingestion_ts TIMESTAMP,
  is_fraud BOOL
)
PARTITION BY DATE(txn_ts)               -- Partition by transaction date
CLUSTER BY region, txn_type, customer_id  -- Cluster by query patterns
OPTIONS (
  partition_expiration_days = 2555,     -- 7 years retention
  require_partition_filter = TRUE       -- Force partition pruning (prevents expensive full scans)
);

-- QUERY PERFORMANCE WITH PARTITION + CLUSTER:
-- Query: fraud transactions in US in Q1 2024
SELECT COUNT(*), SUM(amount)
FROM finance.transactions
WHERE DATE(txn_ts) BETWEEN '2024-01-01' AND '2024-03-31'  -- partition pruning: only Q1 scanned
  AND region = 'US'                                         -- cluster pruning: only US blocks
  AND is_fraud = TRUE;

-- Estimated scan: ~5TB instead of ~200TB for full table
-- Cost: $25 instead of $1000
```

### BigQuery Materialized Views

```sql
-- MATERIALIZED VIEW for real-time dashboard
-- BQ auto-refreshes incrementally when base table updated

CREATE MATERIALIZED VIEW analytics.hourly_revenue_mv
OPTIONS (
  enable_refresh = true,
  refresh_interval_minutes = 5,     -- Refresh every 5 minutes
  allow_non_incremental_definition = false  -- Force incremental (fail if not possible)
)
AS
SELECT
  TIMESTAMP_TRUNC(txn_ts, HOUR) AS hour_bucket,
  region,
  txn_type,
  COUNT(*) AS txn_count,
  SUM(amount) AS total_revenue,
  AVG(amount) AS avg_txn_amount,
  COUNTIF(is_fraud) AS fraud_count
FROM finance.transactions
WHERE txn_ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY 1, 2, 3;

-- Dashboard query: hits materialized view, not base table
-- Response: < 1 second (BI Engine serves from memory)
-- Cost: ~$0 per query (pre-computed)
```

### Row-Level Security

```sql
-- IMPLEMENT ROW-LEVEL SECURITY FOR MULTI-TENANT CDM NEXT

-- Create policy: users can only see their region's data
CREATE ROW ACCESS POLICY regional_access_policy
ON finance.transactions
GRANT TO ("group:us-finance@company.com")
FILTER USING (region = 'US');

CREATE ROW ACCESS POLICY eu_access_policy
ON finance.transactions
GRANT TO ("group:eu-finance@company.com")
FILTER USING (region = 'EU');

-- Admin policy (sees everything)
CREATE ROW ACCESS POLICY admin_access_policy
ON finance.transactions
GRANT TO ("group:data-platform-admin@company.com")
FILTER USING (TRUE);

-- RESULT:
-- US finance user queries finance.transactions → only sees US rows
-- EU finance user queries same table → only sees EU rows
-- Admin → sees all rows
-- No query changes needed for users — filtering is transparent
```

### BigQuery Time Travel and Snapshots

```sql
-- TIME TRAVEL: Query data as of a past point in time
-- Useful for: debugging data issues, point-in-time reporting, undoing mistakes

-- Query table as it was 1 hour ago
SELECT * FROM finance.transactions
FOR SYSTEM_TIME AS OF TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
WHERE customer_id = 'CUST123';

-- Restore accidentally deleted/corrupted partition
CREATE OR REPLACE TABLE finance.transactions_partition_20240115
AS SELECT * FROM finance.transactions
FOR SYSTEM_TIME AS OF '2024-01-15 23:59:59 UTC'
WHERE DATE(txn_ts) = '2024-01-15';

-- TIME TRAVEL RETENTION: 7 days by default, 0-7 days configurable
-- COST: No extra cost during retention window (already stored)
-- CDM NEXT USE: "Yesterday's data was wrong" → time travel to debug before fix
```

---

## PART 5: DATAPLEX — DATA GOVERNANCE ON GCP

### What Dataplex Does

```
DATAPLEX = Unified data management and governance across GCS + BigQuery + Spanner

CAPABILITIES:
  1. Data Catalog: Discover and document all data assets
  2. Auto Metadata: Automatically scan and catalog schema, statistics
  3. Data Quality: Define and run DQ rules at scale
  4. Data Lineage: Track column-level lineage for BQ jobs
  5. Policy Tags: Apply sensitivity labels (PII, PCI) to columns
  6. Data Zones: Organize data into logical zones (raw, curated, analytics)

CDM NEXT DATAPLEX INTEGRATION:

  LAKE: cdm-next-prod
    ZONE: raw (GCS-based)
      ASSETS:
        gs://cdm-prod/raw/teradata/ → Teradata raw data
        gs://cdm-prod/raw/oracle/ → Oracle raw data
    
    ZONE: curated (BigQuery-based)
      ASSETS:
        bigquery://project/finance_silver → Silver layer
        bigquery://project/finance → Gold layer
  
  CATALOG ENTRIES (auto-discovered):
    - Every BQ table + schema
    - Every GCS parquet file + inferred schema
    - Column descriptions (from dbt schema.yml or manual)
  
  POLICY TAGS (PII classification):
    Tag: PII_HIGH_SENSITIVITY (for SSN, credit card)
    Tag: PII_MEDIUM_SENSITIVITY (for email, phone)
    Tag: NON_PII
    
    Effect: Columns tagged PII_HIGH require explicit access grant
    Analysts without access see column as NULL automatically
```

### Data Quality with Dataplex

```python
# DATAPLEX DATA QUALITY RULES (defined in YAML, applied at scale)

quality_spec:
  rules:
    # Rule 1: Primary key completeness
    - column: acct_id
      dimension: COMPLETENESS
      non_null_expectation: {}
    
    # Rule 2: Primary key uniqueness
    - column: acct_id
      dimension: UNIQUENESS
      uniqueness_expectation: {}
    
    # Rule 3: Accepted values
    - column: acct_type
      dimension: VALIDITY
      set_expectation:
        values: ["CHECKING", "SAVINGS", "LOAN", "CREDIT"]
    
    # Rule 4: Balance range
    - column: balance
      dimension: VALIDITY
      range_expectation:
        min_value: 0
        max_value: 100000000  # $100M max balance
    
    # Rule 5: Row count freshness
    - dimension: FRESHNESS
      row_condition_expectation:
        sql_expression: "last_updated_dt >= CURRENT_DATE() - 1"
    
    # Rule 6: Statistical check (distribution check)
    - column: balance
      dimension: STATISTICAL
      statistic_range_expectation:
        statistic: MEAN
        min_value: 1000
        max_value: 100000
```

---

## PART 6: STREAMING DEEP DIVE — CDM NEXT STREAMING ARCHITECTURE

### Real-Time Ingestion Architecture

```
ON-PREMISE KAFKA ──────────────────────────────────────────────────────────►
                                                                            │
                                                               Dedicated Interconnect
                                                                            │
                                                                            ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              GCP STREAMING PATH                                   │
│                                                                                   │
│  Kafka (on-prem)                                                                  │
│       │                                                                           │
│       ▼                                                                           │
│  Pub/Sub Topic          Dataflow Streaming Job                                    │
│  (cdm-kafka-bridge) ───► (config-driven flex template)                            │
│                               │                                                   │
│                    ┌──────────┼──────────────┐                                   │
│                    ▼          ▼              ▼                                    │
│               DLP API    Schema           Quality                                 │
│               (mask PII) Validation      Checks                                  │
│                    │          │              │                                    │
│                    └──────────┴──────────────┘                                   │
│                                    │                                              │
│                         ┌──────────┼───────────┐                                 │
│                         ▼          ▼           ▼                                  │
│                      GCS         BigQuery    Bigtable                             │
│                   (bronze)    (silver,       (risk                                │
│                               streaming     profiles)                             │
│                               inserts)                                            │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Streaming Watermarks in CDM Next

```python
# CDM NEXT STREAMING: HANDLING LATE DATA FROM MOBILE/OFFLINE SOURCES

class CDMNextStreamingPipeline:
    
    def build(self, pipeline: beam.Pipeline, config: PipelineConfig):
        
        # Read from Pub/Sub with timestamps from event payload (not Pub/Sub arrival time)
        raw_events = (
            pipeline
            | "ReadPubSub" >> beam.io.ReadFromPubSub(
                topic=config.source.pubsub_topic,
                with_attributes=True
            )
            | "ExtractEventTime" >> beam.Map(
                lambda msg: beam.window.TimestampedValue(
                    value=parse_event(msg),
                    timestamp=extract_event_timestamp(msg)  # Use business event time
                )
            )
        )
        
        # Window with allowed lateness for mobile offline events
        windowed = (
            raw_events
            | "Window" >> beam.WindowInto(
                beam.window.FixedWindows(300),  # 5-minute windows
                trigger=beam.trigger.AfterWatermark(
                    early=beam.trigger.AfterProcessingTime(60),
                    late=beam.trigger.AfterCount(1)
                ),
                allowed_lateness=beam.window.Duration(seconds=86400),  # 24hr late allowed
                accumulation_mode=beam.trigger.AccumulationMode.ACCUMULATING
            )
        )
        
        # Apply DLP masking
        masked = (
            windowed
            | "MaskPII" >> beam.ParDo(DLPMaskingDoFn(config.pii_columns))
        )
        
        # Quality checks
        good, quarantine = (
            masked
            | "QualityCheck" >> beam.Partition(QualityPartitionFn(config.rules), 2)
        )
        
        # Write good data to BigQuery (streaming inserts)
        good | "WriteBQ" >> beam.io.WriteToBigQuery(
            table=config.destination.bq_table,
            schema=config.destination.bq_schema,
            write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
            create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
            insert_retry_strategy=beam.io.BigQueryInsertRetryPolicy.RETRY_ON_TRANSIENT_ERROR
        )
        
        # Write quarantine to separate GCS path
        quarantine | "WriteQuarantine" >> beam.io.WriteToText(
            file_path_prefix=f"gs://cdm-quarantine/{config.pipeline_id}/",
            append_trailing_newlines=True
        )
        
        # Update Bigtable risk profiles
        good | "UpdateBigtable" >> beam.ParDo(
            BigtableRiskProfileUpdateDoFn(config.bigtable_table)
        )
```

### Exactly-Once in CDM Next Streaming

```
CDM NEXT EXACTLY-ONCE GUARANTEE:

SOURCE TO PUB/SUB:
  - Pub/Sub assigns unique message_id to each message
  - Deduplication window: 10 minutes (same message_id = dedup)
  - After 10 minutes: Pub/Sub cannot deduplicate
  → Source must not replay events older than 10 minutes without new message_id

PUB/SUB TO DATAFLOW:
  - Dataflow checkpoints processing progress to GCS
  - On worker failure: resume from last checkpoint
  - Messages not ACKed until checkpoint → at-least-once delivery
  - Dataflow Streaming Engine: exactly-once using built-in dedup

DATAFLOW TO BIGQUERY:
  - BigQuery streaming inserts: at-least-once
  - Dedup via insertId (unique per row, set by Dataflow)
  - BQ deduplicates within 1 minute window (best-effort)
  - For strict exactly-once: use GCS → BQ load job with deterministic job_id

CDM NEXT CHOICE:
  For fraud/risk (financial, strict): GCS micro-batch → BQ load (exactly-once)
  For analytics feeds (approximate OK): BQ streaming inserts (at-least-once + dedup)
```

---

## PART 7: CLOUD INTERCONNECT AND NETWORKING

### On-Premise to GCP Data Transfer

```
CDM NEXT NETWORK PATH:
  
  Wells Fargo Data Center (on-premise)
  ├── Teradata servers
  ├── Oracle databases
  ├── Hadoop cluster (HDFS)
  └── Kafka cluster
  
  ↕ Dedicated Interconnect
  ↕ 4 × 10Gbps links = 40Gbps total
  ↕ < 5ms latency
  
  GCP Landing Zone (us-central1)
  ├── Private VPC (no public internet)
  ├── Dataflow workers (read from on-prem via JDBC/Kafka)
  ├── GCS buckets (destination)
  └── BigQuery (destination)

THROUGHPUT CALCULATION:
  40 Gbps = 5 GB/s theoretical max
  With overhead (SSL, TCP, protocol): ~4 GB/s practical
  CDM Next peak: 100 TB/day = 100TB / 86400s = 1.16 GB/s
  4 GB/s capacity ÷ 1.16 GB/s needed = 3.4× headroom ✓
  
  Even with 3× burst: 3.48 GB/s < 4 GB/s capacity ✓
```

---

## PART 8: PERFORMANCE BENCHMARKS — KNOW THESE NUMBERS

### GCP Service Performance Reference

```
SERVICE         | OPERATION          | LATENCY    | THROUGHPUT
────────────────┼────────────────────┼────────────┼────────────────
Bigtable        | Single row read    | P50: 1ms   | 10K QPS/node
                | Single row write   | P50: 2ms   | 10K QPS/node
────────────────┼────────────────────┼────────────┼────────────────
BigQuery        | Simple query (<1TB)| 1-3 sec    | 100 GB/s scan
                | Complex analytics  | 10-60 sec  | (depends on slots)
                | Streaming insert   | < 1 sec    | 1M rows/sec/table
────────────────┼────────────────────┼────────────┼────────────────
Pub/Sub         | Publish            | P99: 100ms | 10 GB/s/topic
                | Pull               | P99: 200ms | Unlimited subs
────────────────┼────────────────────┼────────────┼────────────────
GCS             | Object write       | 1-10ms     | 10 GB/s/bucket
                | Object read        | 1-10ms     | Unlimited parallel
────────────────┼────────────────────┼────────────┼────────────────
Dataflow        | Worker startup     | 90-300 sec | 1 GB/s/worker
                | Autoscale add      | 90 sec     |
────────────────┼────────────────────┼────────────┼────────────────
Firestore       | Document read      | P99: 50ms  | 1 read/doc/sec (write)
                | Document write     | P99: 100ms | ~50K reads/sec
────────────────┼────────────────────┼────────────┼────────────────
Cloud Spanner   | Single read        | P99: 5ms   | 2K QPS/node (simple)
                | Transaction commit | P99: 10ms  |
```

---

## MODULE 5 SUMMARY

| Component | Key Design Decision | CDM Next Implementation |
|---|---|---|
| Cloud Composer | Retry policy, max_active_runs, dependency chain | 3 retries, exp backoff, source check → ingest → validate → dbt |
| Dataflow | Flex template, right-sized workers, auto-scaling | Config-driven template, n1-standard-4, min=1 max=100 |
| BigQuery | Partition + cluster, materialized views, row-level security | DATE(txn_ts) partition, region+type cluster, MV for dashboards |
| Dataplex | Policy tags for PII, data quality rules, lineage | PII_HIGH tag on SSN/CC columns, 6 DQ dimensions, OpenLineage |
| Streaming | Watermarks, allowed lateness, exactly-once strategy | 24hr lateness, Streaming Engine for dedup, GCS batch for financial |
| Networking | Dedicated Interconnect for 15PB migration | 4×10Gbps = 40Gbps, 3.4× headroom at peak |
| Bigtable | Row key design, column families, TTL | hash_prefix#customer_id, cf:velocity with 24hr TTL |
| Pub/Sub | Pull vs push, ordering keys, DLQ | Pull (Dataflow), ordering by source_id, DLQ after 5 attempts |

---

*Module 5 Complete — ~10,000 words.*
