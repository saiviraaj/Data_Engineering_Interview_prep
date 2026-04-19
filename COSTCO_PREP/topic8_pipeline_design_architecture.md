# Topic 8: Data Pipeline Design & Architecture

> **Textbook Reference — Costco Sr. Data Engineer Interview Prep**
> Comprehensive reference on pipeline design patterns, architectural decisions, orchestration, reliability, and system design principles for data-intensive applications at scale.

---

## Table of Contents
1. Pipeline Architecture Fundamentals
2. Lambda vs Kappa Architecture
3. Medallion Architecture (Bronze/Silver/Gold)
4. Orchestration with Cloud Composer (Airflow)
5. Airflow Advanced Patterns
6. SLA Management & Pipeline Reliability
7. Event-Driven Pipeline Patterns
8. Idempotency & Exactly-Once Semantics
9. Backfill & Reprocessing Strategies
10. Data Contract Design
11. Cost Optimization Architecture
12. Pipeline Observability
13. System Design: End-to-End Scenarios
14. Interview Q&A Bank

---

## 1. Pipeline Architecture Fundamentals

### The Core Pipeline Design Decisions

Every data pipeline design involves these foundational decisions:

**1. Processing Mode**
- **Batch**: Process data in bounded chunks on a schedule (daily, hourly). Simpler, cheaper, high throughput. Acceptable latency = minutes to hours.
- **Streaming (micro-batch)**: Process data as it arrives, in tiny windows (seconds to minutes). Higher complexity, higher cost, lower latency.
- **Hybrid**: Batch for historical correctness + streaming for low-latency dashboards.

**2. Transformation Layer Location**
- **ELT (Extract-Load-Transform)**: Load raw data first, transform in the warehouse (BigQuery SQL, DBT). Modern standard — cheap storage, powerful SQL engines.
- **ETL (Extract-Transform-Load)**: Transform before loading (Dataflow, Dataproc). Used when raw data is too large, too messy, or when transformation needs computation power (ML enrichment, complex joins across systems).

**3. Storage Format**
| Format | Best For | Pros | Cons |
|--------|----------|------|------|
| Parquet | Analytics, columnar reads | Columnar, compressed, fast scans | Not human-readable, no in-place updates |
| Avro | Streaming, schema evolution | Row-based, schema embedded, Kafka-native | Not columnar (slower analytics) |
| ORC | Hive workloads | Highly optimized for Hive | Less ecosystem support outside Hive |
| Delta/Iceberg | ACID on data lakes | ACID transactions, time travel, schema evolution | Overhead, requires Spark/Flink engine |
| BigQuery native | Analytics on BQ | Serverless, auto-optimized | Vendor lock-in |

**4. Partitioning Strategy**
- Partition by **date** (most common for time-series data)
- Partition by **region** for geo-filtered workloads
- Sub-partition by **channel** or **event_type** for MarTech

**5. State Management**
- **Stateless**: Each record processed independently. Simplest, fully parallelizable (map, filter, format transforms).
- **Stateful**: Processing requires knowledge of past records (sessionization, running totals, deduplication). Needs careful design.

---

## 2. Lambda vs Kappa Architecture

### Lambda Architecture

```
         Input
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
[Batch Layer]  [Speed Layer]
(Spark/BQ)    (Dataflow Streaming)
     │           │
     ▼           ▼
[Batch Views] [Real-Time Views]
     │           │
     └─────┬─────┘
           ▼
      [Serving Layer]
      (Merges batch + speed views)
```

**Lambda: two parallel pipelines**
- **Batch layer**: Reprocesses all historical data nightly, produces accurate but delayed views
- **Speed layer**: Processes streaming data in real-time, produces low-latency but potentially less accurate views (sampling, approximations)
- **Serving layer**: Merges both — reads from batch for historical accuracy, speed layer for recent data

**Pros:**
- Batch layer provides high-accuracy historical data
- Speed layer provides low-latency approximations
- Fault tolerance: if speed layer fails, batch layer catches up

**Cons:**
- Two codebases for the same logic → divergence risk
- Complex serving layer merging logic
- High operational overhead

**When to use Lambda:**
- Latency requirement is mixed: historical accuracy + real-time dashboard
- Business accepts T+1 accuracy for historical, approximate for real-time
- Costco example: Batch attribution job runs nightly (accurate), streaming rollup for live dashboards (approx)

---

### Kappa Architecture

```
Input
  │
  ▼
[Persistent Message Log]
(Pub/Sub, Kafka — retains all history)
  │
  ├──────────────────────────────────┐
  │                                  │
  ▼                                  ▼
[Current Streaming Job]    [Reprocessing Job v2]
(processes live data)       (replays history with new logic)
  │                                  │
  ▼                                  ▼
[Current Output Table]     [New Output Table v2]
                                     │
                     (swap → rename table, decommission old job)
```

**Kappa: single stream-processing pipeline**
- One codebase
- When logic changes: spin up new job reading from the beginning of the log, backfill new table, swap serving to point at new table
- No batch layer at all — everything is streaming

**Pros:**
- Single codebase to maintain
- Simpler operational model
- Works well when stream processor can replay history efficiently

**Cons:**
- Requires immutable, replayable event log (Pub/Sub with long retention, or Kafka)
- Reprocessing large history is expensive and slow
- Streaming processing is inherently harder to debug than batch

**When to use Kappa:**
- All logic can be expressed as stream transformations
- Message log has sufficient retention for full replay
- Costco example: If all ad events in Pub/Sub (30-day retention), can reprocess with new attribution logic

**Practical reality:** Most mature systems end up as **Lambda** because batch processing is cheaper for large historical scans and more transparent to debug. Kappa is ideal for greenfield streaming-first architectures.

---

## 3. Medallion Architecture (Bronze/Silver/Gold)

The medallion architecture is the industry standard for organizing data lake/lakehouse tables.

```
RAW DATA SOURCES
(APIs, databases, files, events)
        │
        ▼
┌──────────────────┐
│  BRONZE (Raw)    │  ← Exact copy of source data. No transformations.
│  append-only     │    Immutable audit trail. Data types preserved as-is.
│  partitioned by  │    Failure safe: always re-ingestable.
│  ingestion date  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  SILVER (Clean)  │  ← Cleaned, deduplicated, type-cast, validated data.
│  partitioned by  │    Business rules applied. PII masked/tokenized.
│  event date      │    Source of truth for analysts.
│  SCD2 for dims   │    Schema enforced.
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  GOLD (Business) │  ← Aggregated, business-meaningful tables.
│  denormalized    │    Ready for dashboards and reports.
│  pre-aggregated  │    Specific to a use case (campaigns, members, inventory).
│  materialized    │    Performance-optimized for query tools.
└──────────────────┘
```

### Applying Medallion to MarTech at Costco

**Bronze layer:**
```sql
-- bronze.ad_events_raw
-- Raw Pub/Sub messages as-is, with Pub/Sub metadata
CREATE TABLE bronze.ad_events_raw (
    pubsub_message_id STRING,
    raw_message       STRING,       -- original JSON bytes, no parsing
    attributes        JSON,
    publish_timestamp TIMESTAMP,
    ingestion_date    DATE          -- partition key
)
PARTITION BY ingestion_date;
```

**Silver layer:**
```sql
-- silver.ad_events
-- Parsed, validated, deduplicated
CREATE TABLE silver.ad_events (
    event_id          STRING NOT NULL,
    user_id           STRING,
    campaign_id       STRING,
    channel           STRING,      -- parsed from attributes
    event_type        STRING,      -- validated: impression/click/conversion
    event_timestamp   TIMESTAMP,   -- event time, not ingestion time
    revenue           FLOAT64,     -- null for non-conversion events
    utm_source        STRING,      -- parsed from UTM parameters
    utm_medium        STRING,
    utm_campaign      STRING,
    country           STRING,      -- from IP geolocation
    is_test_event     BOOL,        -- filtered out in gold
    event_date        DATE         -- partition key = event_timestamp::DATE
)
PARTITION BY event_date
CLUSTER BY campaign_id, channel, event_type;
```

**Gold layer:**
```sql
-- gold.campaign_daily_performance
-- Business-ready, pre-aggregated
CREATE TABLE gold.campaign_daily_performance (
    report_date       DATE,
    campaign_id       STRING,
    campaign_name     STRING,
    channel           STRING,
    impressions       INT64,
    clicks            INT64,
    conversions       INT64,
    revenue           FLOAT64,
    spend             FLOAT64,
    ctr               FLOAT64,     -- clicks / impressions
    cvr               FLOAT64,     -- conversions / clicks
    cpa               FLOAT64,     -- spend / conversions
    roas              FLOAT64,     -- revenue / spend
    attributed_members INT64,
    refreshed_at      TIMESTAMP
)
PARTITION BY report_date
CLUSTER BY channel, campaign_id;
```

---

## 4. Orchestration with Cloud Composer (Airflow)

### Airflow Core Concepts

**DAG (Directed Acyclic Graph):** A collection of tasks with defined execution order and dependencies. The graph must be acyclic (no circular dependencies).

**Task:** A unit of work within a DAG. Each task is an instance of an Operator.

**Operator:** A template for a task type — BashOperator, PythonOperator, BigQueryOperator, DataprocSubmitJobOperator, etc.

**Task Instance:** The execution of a task at a specific point in time.

**DAG Run:** A single execution of a DAG for a specific `execution_date`.

**execution_date:** The logical date the DAG run is for — NOT the actual datetime it runs. A DAG scheduled at `schedule_interval='@daily'` running at 2024-01-16 6am will have `execution_date = 2024-01-15`. This is Airflow's key design: logical date = the period being processed.

### Production DAG Patterns

```python
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryInsertJobOperator,
    BigQueryCheckOperator,
    BigQueryValueCheckOperator
)
from airflow.providers.google.cloud.operators.dataproc import (
    DataprocCreateClusterOperator,
    DataprocSubmitJobOperator,
    DataprocDeleteClusterOperator
)
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import (
    GCSToBigQueryOperator
)
from airflow.providers.google.cloud.sensors.gcs import GCSObjectExistenceSensor
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator
from airflow.models import Variable
from airflow.utils.trigger_rule import TriggerRule
from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta
import json

# --- Callbacks ---
def on_failure_alert(context):
    """Send Slack alert on task failure."""
    dag_id = context['dag_id']
    task_id = context['task_id']
    execution_date = context['execution_date']
    log_url = context['task_instance'].log_url
    
    message = f"""
    :red_circle: *Pipeline Failure Alert*
    • DAG: `{dag_id}`
    • Task: `{task_id}`
    • Execution Date: `{execution_date}`
    • <{log_url}|View Logs>
    """
    
    SlackWebhookOperator(
        task_id='slack_alert',
        http_conn_id='slack_webhook',
        message=message
    ).execute(context)


# --- Default Arguments ---
default_args = {
    'owner': 'martech-eng',
    'depends_on_past': False,           # don't wait for previous run to succeed
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email': ['martech-alerts@costco.com'],
    'retries': 3,
    'retry_delay': timedelta(minutes=10),
    'retry_exponential_backoff': True,   # exponential backoff between retries
    'max_retry_delay': timedelta(hours=1),
    'on_failure_callback': on_failure_alert,
    'execution_timeout': timedelta(hours=4)
}


# --- Main DAG ---
with DAG(
    dag_id='daily_campaign_performance',
    default_args=default_args,
    schedule_interval='0 5 * * *',   # 5am UTC daily
    catchup=False,                    # don't backfill missing runs automatically
    max_active_runs=1,               # prevent concurrent runs
    tags=['martech', 'campaign', 'tier1'],
    doc_md="""
    ## Daily Campaign Performance Pipeline
    Processes ad events from the previous day, computes campaign KPIs,
    and loads to gold.campaign_daily_performance.
    SLA: Complete by 7am UTC.
    Owner: martech-eng@costco.com
    """
) as dag:
    
    # ---- Step 1: Wait for upstream data ----
    wait_for_events = GCSObjectExistenceSensor(
        task_id='wait_for_raw_events',
        bucket='costco-raw-events',
        object='ad-events/date={{ ds }}/_SUCCESS',  # sentinel file
        poke_interval=300,   # check every 5 minutes
        timeout=7200,        # fail after 2 hours
        mode='reschedule'    # release worker slot while waiting
    )
    
    # ---- Step 2: Data quality check on bronze ----
    check_bronze_completeness = BigQueryValueCheckOperator(
        task_id='check_bronze_completeness',
        sql="""
            SELECT COUNT(*) 
            FROM bronze.ad_events_raw 
            WHERE ingestion_date = '{{ ds }}'
        """,
        pass_value=1000,       # must have at least 1000 rows
        tolerance=None,        # exact comparison
        use_legacy_sql=False
    )
    
    # ---- Step 3: Silver transformation ----
    with TaskGroup('silver_transform', tooltip='Parse and clean raw events') as silver_tg:
        
        parse_events = BigQueryInsertJobOperator(
            task_id='parse_ad_events',
            configuration={
                "query": {
                    "query": """
                        INSERT INTO silver.ad_events
                        SELECT
                            JSON_VALUE(raw_message, '$.event_id')             AS event_id,
                            JSON_VALUE(raw_message, '$.user_id')              AS user_id,
                            JSON_VALUE(raw_message, '$.campaign_id')          AS campaign_id,
                            JSON_VALUE(attributes, '$.channel')               AS channel,
                            LOWER(JSON_VALUE(raw_message, '$.event_type'))    AS event_type,
                            TIMESTAMP_MILLIS(CAST(JSON_VALUE(raw_message, '$.timestamp') AS INT64)) AS event_timestamp,
                            SAFE_CAST(JSON_VALUE(raw_message, '$.revenue') AS FLOAT64) AS revenue,
                            JSON_VALUE(raw_message, '$.utm_source')           AS utm_source,
                            JSON_VALUE(raw_message, '$.utm_medium')           AS utm_medium,
                            JSON_VALUE(raw_message, '$.utm_campaign')         AS utm_campaign,
                            DATE(TIMESTAMP_MILLIS(CAST(JSON_VALUE(raw_message, '$.timestamp') AS INT64))) AS event_date,
                            JSON_VALUE(raw_message, '$.campaign_id') LIKE 'TEST_%' AS is_test_event
                        FROM bronze.ad_events_raw
                        WHERE ingestion_date = '{{ ds }}'
                          AND JSON_VALUE(raw_message, '$.event_id') IS NOT NULL
                          AND JSON_VALUE(raw_message, '$.event_id') NOT IN (
                              SELECT event_id FROM silver.ad_events WHERE event_date = '{{ ds }}'
                          )
                    """,
                    "useLegacySql": False,
                    "createDisposition": "CREATE_IF_NEEDED",
                    "writeDisposition": "WRITE_APPEND",
                    "destinationTable": {
                        "projectId": "costco-martech-prod",
                        "datasetId": "silver",
                        "tableId": "ad_events"
                    }
                }
            },
            project_id='costco-martech-prod'
        )
        
        validate_silver = BigQueryCheckOperator(
            task_id='validate_silver_events',
            sql="""
                SELECT
                    COUNTIF(event_id IS NULL) = 0 AS no_null_event_ids,
                    COUNTIF(event_type NOT IN ('impression','click','conversion','viewthrough')) = 0 AS valid_event_types,
                    COUNTIF(revenue < 0) = 0 AS no_negative_revenue
                FROM silver.ad_events
                WHERE event_date = '{{ ds }}'
            """,
            use_legacy_sql=False
        )
        
        parse_events >> validate_silver
    
    # ---- Step 4: Attribution (Dataproc) ----
    CLUSTER_NAME = 'attribution-{{ ds_nodash }}'
    
    create_cluster = DataprocCreateClusterOperator(
        task_id='create_attribution_cluster',
        project_id='costco-martech-prod',
        cluster_config={
            'master_config': {'num_instances': 1, 'machine_type_uri': 'n1-standard-8'},
            'worker_config': {'num_instances': 10, 'machine_type_uri': 'n1-highmem-16'},
            'software_config': {'image_version': '2.1-debian11'}
        },
        region='us-central1',
        cluster_name=CLUSTER_NAME
    )
    
    run_attribution = DataprocSubmitJobOperator(
        task_id='run_multi_touch_attribution',
        job={
            'placement': {'cluster_name': CLUSTER_NAME},
            'pyspark_job': {
                'main_python_file_uri': 'gs://costco-martech/scripts/attribution.py',
                'args': ['--date={{ ds }}', '--model=linear']
            }
        },
        region='us-central1',
        project_id='costco-martech-prod'
    )
    
    delete_cluster = DataprocDeleteClusterOperator(
        task_id='delete_attribution_cluster',
        project_id='costco-martech-prod',
        cluster_name=CLUSTER_NAME,
        region='us-central1',
        trigger_rule=TriggerRule.ALL_DONE
    )
    
    # ---- Step 5: Gold aggregation ----
    build_gold = BigQueryInsertJobOperator(
        task_id='build_campaign_gold',
        configuration={
            "query": {
                "query": """
                    MERGE gold.campaign_daily_performance T
                    USING (
                        SELECT
                            '{{ ds }}'                         AS report_date,
                            e.campaign_id,
                            c.campaign_name,
                            e.channel,
                            COUNTIF(e.event_type = 'impression') AS impressions,
                            COUNTIF(e.event_type = 'click')      AS clicks,
                            COUNTIF(e.event_type = 'conversion') AS conversions,
                            SUM(e.revenue)                       AS revenue,
                            c.daily_spend                        AS spend,
                            CURRENT_TIMESTAMP()                  AS refreshed_at
                        FROM silver.ad_events e
                        LEFT JOIN campaigns.metadata c USING (campaign_id)
                        WHERE e.event_date = '{{ ds }}'
                          AND NOT e.is_test_event
                        GROUP BY 1,2,3,4,9,10
                    ) S ON T.report_date = S.report_date AND T.campaign_id = S.campaign_id
                    WHEN MATCHED THEN UPDATE SET *
                    WHEN NOT MATCHED THEN INSERT *
                """,
                "useLegacySql": False
            }
        },
        project_id='costco-martech-prod'
    )
    
    # ---- Dependencies ----
    (
        wait_for_events
        >> check_bronze_completeness
        >> silver_tg
        >> create_cluster
        >> run_attribution
        >> delete_cluster
        >> build_gold
    )
```

---

## 5. Airflow Advanced Patterns

### XCom — Cross-Task Communication

```python
from airflow.operators.python import PythonOperator

def get_row_count(**context):
    """Push row count to XCom."""
    from google.cloud import bigquery
    client = bigquery.Client()
    result = client.query(
        f"SELECT COUNT(*) as cnt FROM silver.ad_events WHERE event_date = '{context['ds']}'"
    ).result()
    count = list(result)[0]['cnt']
    
    # Push to XCom — available to downstream tasks
    context['ti'].xcom_push(key='event_count', value=count)
    return count

def validate_count(**context):
    """Pull row count from XCom and validate."""
    count = context['ti'].xcom_pull(task_ids='get_count', key='event_count')
    
    if count < 1_000_000:
        raise ValueError(f"Event count {count:,} below minimum threshold 1,000,000")
    
    print(f"Validated: {count:,} events for {context['ds']}")

get_count_task = PythonOperator(
    task_id='get_count',
    python_callable=get_row_count
)

validate_count_task = PythonOperator(
    task_id='validate_count',
    python_callable=validate_count
)
```

### Dynamic DAG Generation

```python
# Generate one DAG per data source (instead of one giant DAG)
sources = ['google_ads', 'facebook_ads', 'display_network', 'email_campaigns']

for source in sources:
    with DAG(
        dag_id=f'ingest_{source}',
        default_args=default_args,
        schedule_interval='0 4 * * *',
        catchup=False
    ) as dag:
        
        ingest = BigQueryInsertJobOperator(
            task_id=f'ingest_{source}_events',
            configuration={
                "query": {
                    "query": f"""
                        INSERT INTO silver.ad_events
                        SELECT * FROM bronze.{source}_raw
                        WHERE ingestion_date = '{{{{ ds }}}}'
                    """,
                    "useLegacySql": False
                }
            }
        )
        
        # Register DAG in globals — Airflow picks it up
        globals()[f'dag_{source}'] = dag
```

### Dynamic Task Mapping (Airflow 2.3+)

```python
# Expand a task over a dynamic list — parallelism without explicit fan-out
from airflow.operators.python import PythonOperator
from airflow.decorators import task

@task
def get_partitions(ds: str) -> list:
    """Return list of partitions to process."""
    return ['us-east', 'us-west', 'emea', 'apac']

@task
def process_partition(region: str, ds: str) -> dict:
    """Process one partition."""
    # This runs in parallel for each region
    print(f"Processing {region} for {ds}")
    return {'region': region, 'status': 'complete'}

with DAG('parallel_region_processing', schedule_interval='@daily') as dag:
    partitions = get_partitions()
    results = process_partition.expand(region=partitions)
```

### SLA & Timeout Configuration

```python
from airflow.models.slabreak import SlaMiss
from datetime import timedelta

def sla_miss_callback(dag, task_list, blocking_task_list, slas, blocking_tis):
    """Called when SLA is missed."""
    message = f"SLA MISSED for DAG {dag.dag_id}: tasks {[s.task_id for s in slas]}"
    send_pagerduty_alert(message)

with DAG(
    dag_id='critical_campaign_pipeline',
    sla_miss_callback=sla_miss_callback,
    default_args=default_args
) as dag:
    
    critical_task = BigQueryInsertJobOperator(
        task_id='build_dashboard_data',
        sla=timedelta(hours=2),          # this task must complete within 2h
        execution_timeout=timedelta(hours=3),  # hard kill after 3h
        configuration={...}
    )
```

---

## 6. SLA Management & Pipeline Reliability

### Retry Strategies

```python
# Different retry strategies for different failure types

# 1. Transient failures (network, quota): retry with backoff
transient_task = PythonOperator(
    task_id='api_call',
    retries=5,
    retry_delay=timedelta(minutes=2),
    retry_exponential_backoff=True,
    max_retry_delay=timedelta(minutes=30)
)

# 2. Data-dependent failures (upstream not ready): retry slowly
data_wait_task = BigQueryCheckOperator(
    task_id='check_upstream',
    retries=12,              # retry for up to 6 hours
    retry_delay=timedelta(minutes=30),
    sql="SELECT COUNT(*) > 0 FROM upstream.table WHERE date = '{{ ds }}'"
)

# 3. Critical failures: no retry, alert immediately
critical_task = DataprocSubmitJobOperator(
    task_id='critical_attribution',
    retries=0,
    on_failure_callback=page_oncall
)
```

### Circuit Breaker Pattern

```python
from airflow.operators.python import BranchPythonOperator, ShortCircuitOperator

def check_data_quality(**context) -> bool:
    """Returns False if data quality fails → short-circuits downstream."""
    from google.cloud import bigquery
    
    client = bigquery.Client()
    result = client.query(f"""
        SELECT COUNTIF(event_id IS NULL) / COUNT(*) AS null_rate
        FROM silver.ad_events
        WHERE event_date = '{context["ds"]}'
    """).result()
    
    null_rate = list(result)[0]['null_rate']
    
    if null_rate > 0.05:  # >5% null rate
        print(f"CIRCUIT BREAKER: null_rate={null_rate:.1%} exceeds threshold")
        send_alert(f"Pipeline halted: null_rate={null_rate:.1%}")
        return False  # ShortCircuitOperator skips all downstream tasks
    
    return True

circuit_breaker = ShortCircuitOperator(
    task_id='data_quality_gate',
    python_callable=check_data_quality,
    ignore_downstream_trigger_rules=True  # skips ALL downstream, not just direct children
)
```

### Idempotent Task Design

```python
# Every task must be safe to re-run multiple times without side effects

# BAD: Append-only — re-running duplicates data
bad_task = BigQueryInsertJobOperator(
    task_id='bad_append',
    configuration={"query": {"query": "INSERT INTO gold.table SELECT * FROM silver.table WHERE date = '{{ ds }}'"}}
)

# GOOD: Idempotent — delete then insert (partition overwrite)
good_task = BigQueryInsertJobOperator(
    task_id='good_upsert',
    configuration={
        "query": {
            "query": """
                MERGE gold.campaign_daily T
                USING (SELECT * FROM silver.events WHERE event_date = '{{ ds }}') S
                ON T.report_date = S.event_date AND T.campaign_id = S.campaign_id
                WHEN MATCHED THEN UPDATE SET impressions = S.impressions, clicks = S.clicks
                WHEN NOT MATCHED THEN INSERT VALUES (S.event_date, S.campaign_id, S.impressions, S.clicks)
            """,
            "useLegacySql": False
        }
    }
)

# ALSO GOOD: Partition overwrite — replaces entire partition atomically
partition_overwrite = BigQueryInsertJobOperator(
    task_id='partition_overwrite',
    configuration={
        "query": {
            "query": """
                SELECT * FROM silver.events WHERE event_date = '{{ ds }}'
            """,
            "useLegacySql": False,
            "destinationTable": {
                "projectId": "...",
                "datasetId": "gold",
                "tableId": "events${{ ds_nodash }}"  # $ notation = partition decorator
            },
            "writeDisposition": "WRITE_TRUNCATE",  # replaces the partition
            "createDisposition": "CREATE_IF_NEEDED"
        }
    }
)
```

---

## 7. Event-Driven Pipeline Patterns

### Pub/Sub → Cloud Functions → Trigger DAG

```python
# Cloud Function triggered by Pub/Sub message → triggers Airflow DAG
import functions_framework
from google.cloud import composer_v1
from google.auth import default
import json

@functions_framework.cloud_event
def trigger_dag_on_file_arrival(cloud_event):
    """
    Triggered when a new file lands in GCS.
    GCS sends a notification to Pub/Sub → this function triggers the Airflow DAG.
    """
    # Parse GCS notification
    gcs_event = json.loads(cloud_event.data.decode())
    bucket = gcs_event['bucket']
    file_path = gcs_event['name']
    
    # Only trigger for _SUCCESS sentinel files
    if not file_path.endswith('_SUCCESS'):
        return
    
    # Extract processing date from path: gs://bucket/ad-events/date=2024-01-15/_SUCCESS
    date = file_path.split('date=')[1].split('/')[0]
    
    # Trigger Airflow DAG via Cloud Composer API
    client = composer_v1.EnvironmentsClient()
    
    dag_run_request = {
        'dag_id': 'daily_campaign_performance',
        'conf': {'processing_date': date},
        'execution_date': f'{date}T05:00:00+00:00'
    }
    
    # Use Airflow REST API via IAP
    import google.auth.transport.requests
    import requests
    
    credentials, project = default()
    credentials.refresh(google.auth.transport.requests.Request())
    
    airflow_uri = 'https://COMPOSER_WEBSERVER_URI/api/v1/dags/daily_campaign_performance/dagRuns'
    
    response = requests.post(
        airflow_uri,
        headers={'Authorization': f'Bearer {credentials.token}'},
        json={'conf': {'processing_date': date}}
    )
    
    print(f"DAG triggered for date {date}: {response.status_code}")
```

---

## 8. Idempotency & Exactly-Once Semantics

### Sources of Duplicates in Data Pipelines

1. **Producer retries**: Network timeout → producer retries → Pub/Sub gets duplicate messages
2. **Consumer retries**: Task fails after writing but before acking → re-run writes again
3. **Pub/Sub at-least-once**: Same message delivered multiple times
4. **Dataflow exactly-once**: Only applies within a Dataflow job — not end-to-end

### Deduplication Strategies

```sql
-- Strategy 1: MERGE (upsert) — idempotent by design
MERGE silver.ad_events T
USING (
    SELECT 
        event_id,
        user_id,
        campaign_id,
        event_type,
        event_timestamp,
        revenue,
        DATE(event_timestamp) AS event_date
    FROM bronze.ad_events_raw
    WHERE ingestion_date = '{{ ds }}'
      AND JSON_VALUE(raw_message, '$.event_id') IS NOT NULL
) S ON T.event_id = S.event_id AND T.event_date = S.event_date
WHEN NOT MATCHED THEN INSERT VALUES (
    S.event_id, S.user_id, S.campaign_id, S.event_type,
    S.event_timestamp, S.revenue, S.event_date
);
-- MERGE is idempotent: running twice → same result, no duplicates


-- Strategy 2: ROW_NUMBER dedup before writing
CREATE OR REPLACE TABLE silver.ad_events_{{ ds_nodash }} AS
SELECT * EXCEPT(rn)
FROM (
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY event_id
            ORDER BY ingestion_date DESC, publish_timestamp DESC
        ) AS rn
    FROM bronze.ad_events_raw
    WHERE ingestion_date = '{{ ds }}'
)
WHERE rn = 1;


-- Strategy 3: Partition overwrite — entire partition is replaced atomically
-- Write query results to partition decorator (BigQuery atomic partition swap)
-- This ensures the partition is either fully updated or not at all
-- writeDisposition: WRITE_TRUNCATE on destinationTable: table$20240115
```

### Two-Phase Commit Pattern for BigQuery

```python
def write_with_two_phase_commit(data: list, target_table: str, job_id: str):
    """
    Two-phase commit: write to staging → validate → atomic swap.
    Ensures the main table is never partially updated.
    """
    from google.cloud import bigquery
    client = bigquery.Client()
    
    staging_table = f"{target_table}_staging_{job_id}"
    
    # Phase 1: Write to staging table
    job = client.load_table_from_json(
        data,
        staging_table,
        job_config=bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED
        )
    )
    job.result()
    print(f"Phase 1 complete: {client.get_table(staging_table).num_rows:,} rows in staging")
    
    # Phase 2: Validate staging
    validation_query = f"""
        SELECT 
            COUNT(*) AS total_rows,
            COUNTIF(event_id IS NULL) AS null_event_ids,
            COUNTIF(event_type NOT IN ('impression','click','conversion')) AS invalid_types
        FROM `{staging_table}`
    """
    result = client.query(validation_query).result()
    row = list(result)[0]
    
    if row.null_event_ids > 0 or row.invalid_types > 0:
        # Validation failed — delete staging, don't touch main table
        client.delete_table(staging_table)
        raise ValueError(f"Staging validation failed: {dict(row)}")
    
    # Phase 3: Atomic swap — copy staging to main
    client.query(f"""
        CREATE OR REPLACE TABLE `{target_table}` AS
        SELECT * FROM `{staging_table}`
    """).result()
    
    # Cleanup staging
    client.delete_table(staging_table)
    print(f"Phase 3 complete: {row.total_rows:,} rows written to {target_table}")
```

---

## 9. Backfill & Reprocessing Strategies

### Airflow Backfill

```bash
# Trigger historical backfill for missed/failed runs
airflow dags backfill \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  daily_campaign_performance

# Run backfill in parallel (default is sequential)
airflow dags backfill \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --max-active-runs 5 \  # 5 DAG runs in parallel
  daily_campaign_performance
```

### Partitioned Backfill Pattern

```python
# For large backfills: process one partition (date) at a time in Spark

def backfill_silver_events(start_date: str, end_date: str, project: str):
    """Reprocess silver layer for a date range."""
    from pyspark.sql import SparkSession
    import pandas as pd
    
    spark = create_spark_session("BackfillSilverEvents")
    
    # Generate list of dates to backfill
    dates = pd.date_range(start_date, end_date, freq='D').strftime('%Y-%m-%d').tolist()
    
    print(f"Backfilling {len(dates)} partitions: {dates[0]} to {dates[-1]}")
    
    for date in dates:
        print(f"Processing {date}...")
        
        # Read bronze for this date
        bronze_df = (
            spark.read
            .format("bigquery")
            .option("table", f"{project}.bronze.ad_events_raw")
            .option("filter", f"ingestion_date = '{date}'")
            .load()
        )
        
        if bronze_df.isEmpty():
            print(f"  No data for {date}, skipping")
            continue
        
        # Transform
        silver_df = transform_to_silver(bronze_df)
        
        # Write with partition overwrite
        (
            silver_df
            .write
            .format("bigquery")
            .option("table", f"{project}.silver.ad_events")
            .option("temporaryGcsBucket", "costco-dataproc-temp")
            .option("partitionField", "event_date")
            .option("partitionType", "DAY")
            .option("writeDisposition", "WRITE_TRUNCATE")  # overwrite this date's partition
            .partitionBy("event_date")
            .mode("overwrite")
            .save()
        )
        
        count = silver_df.count()
        print(f"  Written {count:,} rows for {date}")
    
    spark.stop()
    print("Backfill complete")
```

---

## 10. Data Contract Design

### What Is a Data Contract

A **data contract** is a formal agreement between a data producer and consumer about the schema, semantics, SLAs, and quality guarantees of a dataset. It prevents "schema drift" (producers changing schema without warning consumers).

### Contract Structure

```yaml
# data_contract.yaml — ad_events silver table
contract_version: 1.3.0
dataset: silver.ad_events
producer: martech-data-eng
consumers:
  - campaign-analytics-team
  - member-insights-team
  - finance-reporting

schema:
  - name: event_id
    type: STRING
    nullable: false
    description: "Globally unique identifier for each ad event"
    
  - name: user_id
    type: STRING
    nullable: true
    description: "Hashed member ID. Null for anonymous users."
    pii: true
    
  - name: campaign_id
    type: STRING
    nullable: false
    description: "Campaign identifier. Must exist in campaigns.metadata."
    
  - name: event_type
    type: STRING
    nullable: false
    allowed_values: [impression, click, conversion, viewthrough]
    
  - name: event_timestamp
    type: TIMESTAMP
    nullable: false
    description: "Event time (not ingestion time)"
    
  - name: revenue
    type: FLOAT64
    nullable: true
    minimum: 0.0
    description: "Revenue attributed to event. Non-null only for conversions."

quality_guarantees:
  completeness:
    event_id: 100%
    campaign_id: 100%
    event_type: 100%
  uniqueness:
    event_id: 100%
  freshness:
    max_delay_hours: 2
    
sla:
  availability: "Daily partitions available by 7am UTC"
  latency: "Events within 2 hours of occurrence"
  backfill_window: "30 days"
  
breaking_changes_policy:
  notification_period: "14 days"
  contact: martech-data-eng@costco.com
  process: "File change request in #data-contracts Slack channel"
```

### Enforcing Contracts in Code

```python
import great_expectations as ge
from great_expectations.core import ExpectationSuite

def validate_contract(table_id: str, date: str) -> bool:
    """Validate silver.ad_events against its data contract."""
    
    context = ge.DataContext()
    
    # Load the data
    validator = context.get_validator(
        datasource_name='bigquery_datasource',
        data_connector_name='default',
        data_asset_name=table_id,
        batch_identifiers={'partition_date': date}
    )
    
    # Schema / completeness expectations (from contract)
    validator.expect_column_to_exist('event_id')
    validator.expect_column_values_to_not_be_null('event_id')
    validator.expect_column_values_to_be_unique('event_id')
    
    validator.expect_column_values_to_not_be_null('campaign_id')
    
    validator.expect_column_values_to_be_in_set(
        'event_type',
        ['impression', 'click', 'conversion', 'viewthrough']
    )
    
    validator.expect_column_values_to_not_be_null('event_timestamp')
    
    validator.expect_column_values_to_be_between(
        'revenue',
        min_value=0,
        mostly=1.0,  # 100% of non-null values must be >= 0
        catch_exceptions=True
    )
    
    # Freshness check
    validator.expect_column_max_to_be_between(
        'event_timestamp',
        min_value=f'{date}T00:00:00',
        max_value=f'{date}T23:59:59'
    )
    
    results = validator.validate()
    
    if not results.success:
        failed = [r for r in results.results if not r.success]
        print(f"CONTRACT VIOLATION: {len(failed)} expectations failed")
        for r in failed:
            print(f"  - {r.expectation_config.expectation_type}: {r.result}")
        return False
    
    print(f"Contract validation passed for {date}")
    return True
```

---

## 11. Cost Optimization Architecture

### BigQuery Cost Optimization

```sql
-- Cost 1: Slot reservation vs on-demand
-- On-demand: $6.25/TB scanned
-- Slot reservation: fixed monthly cost, better for predictable workloads
-- Rule of thumb: > 3TB/day → reservation is cheaper

-- Cost 2: Materialized views (avoid rescanning)
CREATE MATERIALIZED VIEW gold.campaign_30day_mv
PARTITION BY report_date
OPTIONS (enable_refresh = true, refresh_interval_minutes = 60)
AS
SELECT
    DATE(event_timestamp) AS report_date,
    campaign_id,
    COUNT(*) AS total_events,
    COUNTIF(event_type = 'click') AS clicks
FROM silver.ad_events
WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY 1, 2;
-- Dashboard queries hit the MV (pre-computed), not the raw table

-- Cost 3: Partition expiry — auto-delete old partitions
ALTER TABLE bronze.ad_events_raw
SET OPTIONS (
    partition_expiration_days = 90  -- delete raw data after 90 days
);

-- Cost 4: Table expiry for temp/staging tables
CREATE TABLE tmp.attribution_staging_20240115
OPTIONS (expiration_timestamp = TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 1 DAY))
AS SELECT * FROM ...;
-- Auto-deleted after 1 day
```

### Dataflow Cost Optimization

```python
# 1. Use Dataflow Flex Templates (pre-built container images)
# Avoid JVM startup overhead, reuse template across runs

# 2. Right-size workers
worker_options.machine_type = 'n1-standard-4'  # start small, let autoscaling handle burst
worker_options.max_num_workers = 50

# 3. Use preemptible/spot workers for fault-tolerant batch jobs
# Add to pipeline options:
# --experiments=use_preemptible_workers
# Cost: ~70% cheaper than regular workers

# 4. Enable Dataflow Shuffle (server-side) — reduces worker memory and disk
# --experiments=shuffle_mode=appliance

# 5. Streaming Engine — moves window state off workers
# --enable_streaming_engine
# Reduces worker count needed, cost scales with volume not workers
```

### Dataproc Cost Optimization

```bash
# 1. Ephemeral clusters — create for job, delete immediately after
# No idle cluster costs

# 2. Preemptible workers for batch jobs
--num-preemptible-workers=20  # 3-5x cheaper than regular workers

# 3. max-idle auto-delete
--max-idle=15m  # delete cluster after 15min idle

# 4. Use Dataproc Serverless for infrequent jobs
# No cluster → no idle cost
# Charged per vCPU-hour while job runs

# 5. Custom images — faster startup (don't install deps on cluster start)
# Bake deps into Docker image, use as custom dataproc image
```

---

## 12. Pipeline Observability

### Three Pillars: Metrics, Logs, Traces

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from google.cloud import monitoring_v3
import logging
import time
from functools import wraps

# --- Structured Logging ---
import json
import sys

class StructuredLogger:
    def __init__(self, pipeline_name: str, job_date: str):
        self.pipeline = pipeline_name
        self.date = job_date
        self.logger = logging.getLogger(pipeline_name)
    
    def info(self, message: str, **kwargs):
        log_entry = {
            'severity': 'INFO',
            'message': message,
            'pipeline': self.pipeline,
            'job_date': self.date,
            'timestamp': time.time(),
            **kwargs
        }
        print(json.dumps(log_entry), file=sys.stdout)
    
    def error(self, message: str, **kwargs):
        log_entry = {
            'severity': 'ERROR',
            'message': message,
            'pipeline': self.pipeline,
            'job_date': self.date,
            'timestamp': time.time(),
            **kwargs
        }
        print(json.dumps(log_entry), file=sys.stderr)

# Usage:
logger = StructuredLogger('campaign_attribution_etl', '2024-01-15')
logger.info("Starting ETL", source_rows=1_234_567, target_table="silver.ad_events")
# Output: {"severity": "INFO", "message": "Starting ETL", "source_rows": 1234567, ...}
# Cloud Logging picks this up as structured JSON → filterable by any field


# --- Custom Metrics (Cloud Monitoring) ---
def push_pipeline_metric(metric_type: str, value: float, labels: dict, project: str):
    """Push a custom metric to Cloud Monitoring."""
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project}"
    
    series = monitoring_v3.TimeSeries()
    series.metric.type = f"custom.googleapis.com/pipeline/{metric_type}"
    series.metric.labels.update(labels)
    series.resource.type = "global"
    
    point = monitoring_v3.Point()
    point.value.double_value = value
    now = time.time()
    seconds = int(now)
    point.interval.end_time.seconds = seconds
    series.points = [point]
    
    client.create_time_series(name=project_name, time_series=[series])

# Push row count metric after each pipeline run:
push_pipeline_metric(
    metric_type='rows_processed',
    value=1_234_567,
    labels={'pipeline': 'campaign_attribution', 'date': '2024-01-15', 'stage': 'silver'},
    project='costco-martech-prod'
)

# Create Cloud Monitoring alert on this metric:
# Alert if rows_processed drops >20% from previous day → upstream failure signal
```

### Data Freshness Monitoring

```sql
-- Cloud Monitoring custom query: check if each table has recent data
-- Alert if no new data for > 2 hours

SELECT 
    table_name,
    TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(ingestion_timestamp), HOUR) AS hours_since_refresh,
    MAX(ingestion_timestamp) AS last_refresh
FROM (
    SELECT 'silver.ad_events' AS table_name, MAX(event_timestamp) AS ingestion_timestamp
    FROM silver.ad_events
    WHERE event_date = CURRENT_DATE()
    UNION ALL
    SELECT 'gold.campaign_daily_performance', MAX(refreshed_at)
    FROM gold.campaign_daily_performance
    WHERE report_date = CURRENT_DATE()
)
GROUP BY 1, 3
ORDER BY 2 DESC;
```

---

## 13. System Design: End-to-End Scenarios

### Scenario: Design a Real-Time Ad Spend Dashboard for Costco Marketing

**Requirements:**
- Show live campaign spend, clicks, conversions per campaign
- Latency ≤ 3 minutes from event to dashboard
- Handle 50K events/second peak (Costco Black Friday)
- History available for 18 months
- 20 analysts querying simultaneously

**Design:**

```
[Ad Servers + Web/App Tags]
    │ HTTPS (JSON events)
    ▼
[Pub/Sub: ad-events]
    Retention: 7 days
    Schema: Avro (validated at publish)
    │
    ├─── [Dataflow Streaming Job #1: Raw Ingestion]
    │        Workers: 20 → 200 (autoscale)
    │        Operations: Parse, validate, enrich (geolocation, UTM)
    │        Write: Storage Write API → BQ raw_events (committed, queryable immediately)
    │        Dead-letters → Pub/Sub: ad-events-dlq
    │
    ├─── [Dataflow Streaming Job #2: Rollup]
    │        Workers: 5 → 50
    │        Window: 1-min FixedWindows
    │        Operations: Count impressions, clicks, conversions per campaign
    │        Write: BQ campaign_1min_rollup table
    │        Trigger: AfterWatermark + AfterProcessingTime(30s) for low-latency updates
    │
    ▼
[BigQuery]
    ├── raw_events (partitioned by event_date, clustered by campaign_id, channel)
    │       Retention: 18 months
    │       Streaming Buffer: new events → queryable immediately
    │
    ├── campaign_1min_rollup (materialized from Dataflow)
    │       Partitioned by window_start
    │
    └── [Materialized View: campaign_live_stats]
            Refreshes every 60 seconds
            Aggregates last 24h from raw_events
            Pre-groups by campaign_id, channel, hour
            
[Looker Dashboard]
    Queries: campaign_live_stats MV (fast, pre-computed)
    Auto-refresh: 60 seconds
    20 analysts → slot reservation (avoid per-query cost)
    
[Cloud Monitoring Alerts]
    - Pub/Sub backlog > 100K messages → scale Dataflow
    - Dataflow throughput drops 50% → page on-call
    - BQ query latency > 5s → investigate MV staleness
    - No new data in raw_events for 15min → upstream failure
```

**Scale math:**
- 50K events/second × 200 bytes/event = 10 MB/s → Pub/Sub easily handles (well below 1 GB/s limit)
- Dataflow: 50K events/sec with 20-worker n1-standard-4 (20 × 4 = 80 cores) → ~625 events/core/sec — comfortable
- BigQuery raw_events: 50K events/sec × 86400s = 4.3B events/day → at 200 bytes = ~860GB/day → partition by date + cluster by campaign_id

---

## 14. Interview Q&A Bank

**Q: Explain the Medallion Architecture and how you'd apply it at Costco.**
A: Medallion is a three-layer organization pattern: Bronze (raw, immutable copy of source data with no transformation), Silver (cleaned, validated, deduplicated, type-cast — the trusted single source of truth), and Gold (business-specific aggregations, denormalized for query performance). At Costco MarTech, Bronze would contain raw Pub/Sub messages verbatim so we can always replay from source if a processing bug is found. Silver would parse JSON, validate event types, deduplicate on event_id, and apply UTM parsing. Gold would be pre-aggregated tables like campaign_daily_performance with CTR, ROAS, and attribution results. This separation means analysts never query raw data (too messy), and the engineering team can fix Bronze→Silver logic and reprocess without affecting the Gold tables' availability.

**Q: How do you ensure a pipeline is idempotent? Why does it matter?**
A: Idempotency means running a pipeline multiple times produces the same result — no duplicates, no data loss. It matters because pipelines fail and must be retried: a task might write 80% of records to BigQuery before crashing, and when it retries it must not double-count those 80%. Techniques: (1) Use MERGE/UPSERT instead of INSERT — if a record already exists, it's updated in place rather than duplicated. (2) Use BigQuery partition overwrite — `WRITE_TRUNCATE` on a date partition atomically replaces the entire partition. (3) Dedup on a business key (event_id) using ROW_NUMBER before writing. (4) For Dataflow, use event_id in a state store to deduplicate within the streaming job.

**Q: What's the difference between Pub/Sub at-least-once delivery and Dataflow exactly-once?**
A: Pub/Sub guarantees each message is delivered at least once — if the subscriber doesn't ack within the deadline, the message is redelivered. This means your subscriber might process the same message twice. Dataflow's exactly-once guarantee applies within the Dataflow job — the framework internally deduplicates work items using stable IDs, so even if a worker crashes and a bundle is retried, the output is produced exactly once. However, "exactly-once" only applies within Dataflow's internal state; if Dataflow writes to BigQuery using streaming inserts, duplicate inserts can still happen due to Dataflow's internal retry mechanism. Using the Storage Write API in "committed" mode provides true end-to-end exactly-once semantics.

**Q: A Dataproc job that processes daily campaign data starts taking 4 hours instead of the normal 1 hour. How do you diagnose and fix it?**
A: Diagnosis steps: (1) Check Spark History Server for the slow stage — is it a specific GroupByKey or join that's slow? (2) Look at task duration distribution for the slow stage — if most tasks finish in 30s but one takes 2 hours, it's data skew. (3) Check YARN ResourceManager: are all workers busy? If some workers are idle while one is overloaded → skew. (4) Check GCS I/O metrics — slow reads from source? (5) Check shuffle metrics — is there an unusually large shuffle? Fixes depending on root cause: Skew → add random suffix to keys (shard hot keys). Large shuffle → reduce `spark.sql.shuffle.partitions`, enable AQE. Slow reads → add partition pruning filter to source read. Cluster undersized → increase worker count.

**Q: How do you handle schema evolution in a data pipeline? Give a concrete example.**
A: Schema evolution is when the source adds, removes, or renames fields. Strategy depends on layer. In Bronze: store raw JSON bytes as STRING — never parse in bronze. This means Bronze never needs to change even if source schema changes. In Silver: use `SAFE_CAST` and `JSON_VALUE` with null handling — adding a new source field means adding a nullable column to Silver; downstream that's backward compatible. For Avro schemas in Pub/Sub, use schema compatibility rules (BACKWARD_COMPATIBLE — readers with new schema can read data written with old schema). Data contracts define the allowed change types: adding nullable columns is non-breaking, renaming columns requires 14-day notice. In practice at Wells Fargo CDM, we version-stamped schemas and maintained parallel tables (v1/v2) during transitions.

**Q: Describe a time you designed a system to handle late-arriving data.**
A: In the CDM Next platform at Wells Fargo, we had cloud migration metrics arriving from 60+ application teams at unpredictable intervals — some batch loads arrived hours after their event timestamps. The design: (1) In Dataflow, we set `allowed_lateness=24 hours` on Fixed windows, meaning windows wouldn't be discarded for 24h after the watermark passed. (2) We used `AccumulationMode.ACCUMULATING` so that late arrivals updated the window result rather than being dropped. (3) For BigQuery, we partitioned by event_date (not ingestion_date) and used MERGE on the target table, so late-arriving events for day T would update day T's partition even if they arrived on day T+1. (4) We monitored watermark lag in Dataflow metrics — if lag exceeded 2 hours, an alert fired.

---

*End of Topic 8 — Data Pipeline Design & Architecture*
