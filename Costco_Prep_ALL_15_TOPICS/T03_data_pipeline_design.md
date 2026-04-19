# Topic 3: Data Pipeline Design (Batch + Streaming)
## Costco Sr. Data Engineer — Exhaustive Interview Textbook

---

## Table of Contents
1. [L1: Core Concepts — Pipeline Basics, DAGs](#l1-core-concepts)
2. [L2: Deep Technical Understanding](#l2-deep-technical-understanding)
3. [L3: Real-World Scenarios — Costco/MarTech Style](#l3-real-world-scenarios)
4. [L4: Hands-On Design](#l4-hands-on-design)
5. [L5: Edge Cases & Pitfalls](#l5-edge-cases--pitfalls)
6. [L6: Interview Questions — Easy to Very Hard](#l6-interview-questions)

---

## L1: Core Concepts

### 1.1 What is a Data Pipeline?

A data pipeline is an automated sequence of data processing steps that moves data from one or more sources to a destination in a reliable, repeatable manner. Each step transforms, validates, or routes the data.

```
Source(s) → Ingest → Transform → Validate → Load → Destination(s)
```

**Key properties every production pipeline must have**:

| Property | Definition | Why It Matters |
|----------|------------|----------------|
| **Idempotency** | Running the same pipeline multiple times produces the same result | Safe to retry on failure without duplicating data |
| **Reliability** | The pipeline runs successfully even when individual components fail | Data consumers can trust the output is always produced |
| **Observability** | You can see what happened, when, and why | You can debug failures without guessing |
| **Scalability** | Performance degrades gracefully as data volume grows | You don't need to rewrite the pipeline when data 10x's |
| **Recoverability** | You can re-run any past period and reproduce the same output | Historical corrections are possible |

---

### 1.2 Batch vs Streaming — The Fundamental Choice

**Batch processing**: Process data in discrete, fixed-size chunks at scheduled intervals.

```
Data accumulates → Trigger at schedule → Process entire batch → Write output
[midnight] → [6 AM trigger] → [process yesterday's 50M rows] → [mart table updated]
```

**Streaming processing**: Process each event as it arrives (or in micro-batches of seconds).

```
Event arrives → Process immediately → Output updated continuously
[click event at 14:23:07] → [processed by 14:23:08] → [real-time dashboard updated]
```

**Decision framework**:

| Dimension | Batch | Streaming |
|-----------|-------|-----------|
| Latency | Minutes to hours | Milliseconds to seconds |
| Throughput | Very high (optimized for bulk) | Lower per-unit (overhead per event) |
| Cost | Lower (process once/day) | Higher (compute always running) |
| Complexity | Simpler | Significantly more complex |
| Use cases | Reports, aggregations, ML training | Fraud detection, real-time dashboards, alerting |
| Late data handling | Natural (just include in next batch) | Requires watermarks + explicit handling |

---

### 1.3 DAG — Directed Acyclic Graph

A DAG defines the dependency relationships between pipeline tasks. "Directed" means edges have direction (A must run before B). "Acyclic" means no circular dependencies (A cannot depend on B if B depends on A).

```
ingest_google_ads ─────┐
                        ↓
ingest_meta_ads ───► join_ad_sources ──► compute_roas ──► load_mart
                        ↑
ingest_campaigns ──────┘
```

Airflow/Cloud Composer uses DAGs explicitly. DBT builds its DAG from `ref()` calls. Dataflow builds its execution graph from the pipeline definition code.

---

## L2: Deep Technical Understanding

### 2.1 Idempotency — The Most Important Pipeline Property

**Idempotency**: `f(f(x)) = f(x)`. Running the pipeline 1 time or 10 times produces the same output.

**Why non-idempotent pipelines are dangerous**:
- A pipeline fails at 2 AM, is automatically retried at 2:05 AM
- If non-idempotent: 2 AM run partially loaded data, 2:05 AM run loads again → duplicate rows
- Your data is now incorrect with no obvious error

**Patterns for achieving idempotency**:

#### Pattern 1: Overwrite (INSERT OVERWRITE / TRUNCATE + INSERT)
```sql
-- Full overwrite: always produces the same result
TRUNCATE TABLE mart_daily_performance;
INSERT INTO mart_daily_performance
SELECT ... FROM source WHERE report_date = '2024-01-15';

-- BigQuery: use CREATE OR REPLACE TABLE / WRITE_TRUNCATE disposition
```

#### Pattern 2: MERGE (UPSERT)
```sql
-- Safe to run multiple times: insert if new, update if exists
MERGE INTO mart_daily_performance AS target
USING (
    SELECT * FROM staged_performance WHERE report_date = '2024-01-15'
) AS source
ON target.report_date = source.report_date
   AND target.campaign_id = source.campaign_id
WHEN MATCHED THEN UPDATE SET
    target.spend_usd = source.spend_usd,
    target.roas = source.roas
WHEN NOT MATCHED THEN INSERT VALUES (source.*);
```

#### Pattern 3: Partition-Level Overwrite
```sql
-- BigQuery: overwrite a specific partition
INSERT INTO `mart.campaign_performance`
PARTITION (report_date = '2024-01-15')
SELECT ... FROM source WHERE report_date = '2024-01-15';
-- If run twice: second run overwrites the partition → idempotent
```

#### Pattern 4: Deduplication Key
```python
# Streaming: use message_id as dedup key
# Process message only if message_id hasn't been seen
def process_message(message):
    if redis_client.setnx(f"processed:{message.id}", 1):  # atomic set-if-not-exists
        do_processing(message)
    else:
        logger.info(f"Duplicate message {message.id}, skipping")
```

---

### 2.2 Reprocessing Strategies — Backfill Design

**Scenario**: A bug is discovered in the cost calculation logic. All historical data for the last 90 days is incorrect. You need to reprocess.

**Strategy 1: Full backfill with date parameterization**
```python
# Airflow: backfill specific date range
airflow dbt run --start-date 2024-01-01 --end-date 2024-03-31

# Or trigger via API
for date in date_range('2024-01-01', '2024-03-31'):
    trigger_dag_run('campaign_performance_pipeline', {'execution_date': date})
```

```python
# Pipeline designed for backfill from the start
def run_pipeline(execution_date: date):
    """
    All operations scoped to execution_date.
    Re-running with the same date always produces the same output.
    """
    data = extract(source, date_filter=execution_date)
    transformed = transform(data, execution_date)
    load(transformed, target_partition=execution_date, mode='overwrite')
    # 'overwrite' for partition = idempotent
```

**Strategy 2: Incremental backfill with dependency tracking**
```python
# For tables with many dependencies:
# 1. Reprocess raw/staging layer first
# 2. Propagate downstream in dependency order

backfill_order = [
    'stg_ad_clicks',           # Layer 1: staging
    'stg_conversions',
    'int_attributed_conversions',  # Layer 2: intermediate
    'mart_campaign_performance',   # Layer 3: mart
    'mart_roas_by_channel'
]
```

---

### 2.3 CDC — Change Data Capture

CDC captures changes (INSERT, UPDATE, DELETE) to source operational databases and propagates them to the data warehouse. Critical for near-real-time pipelines without full table scans.

#### Method 1: Log-Based CDC (Debezium, Striim)

```
Source DB (MySQL/Postgres) writes changes → Binary Log (WAL)
Debezium reads the WAL → Kafka/Pub/Sub
Kafka → Dataflow/Flink → BigQuery/GCS
```

**Advantages**: True real-time, captures deletes, no load on source DB (reads log only).
**Disadvantages**: Complex setup, requires DB-level access, log retention management.

```json
// Example CDC event (Debezium format)
{
  "op": "u",           // u=update, i=insert, d=delete, r=read(snapshot)
  "before": {
    "campaign_id": "C001",
    "daily_budget_usd": 500.0,
    "updated_at": "2024-01-14T10:00:00Z"
  },
  "after": {
    "campaign_id": "C001",
    "daily_budget_usd": 750.0,       // budget increased
    "updated_at": "2024-01-15T08:30:00Z"
  },
  "ts_ms": 1705298600000,
  "source": {
    "table": "campaigns",
    "db": "costco_crm"
  }
}
```

#### Method 2: Timestamp-Based CDC (Simpler, Polling)

```python
# Poll source database for rows modified since last run
def extract_changed_rows(last_run_timestamp: datetime):
    query = f"""
        SELECT *
        FROM campaigns
        WHERE updated_at > '{last_run_timestamp}'
        ORDER BY updated_at
    """
    return db.execute(query)

# State management: store last_run_timestamp somewhere durable
last_run = state_store.get('campaigns_last_run')
new_data = extract_changed_rows(last_run)
process_and_load(new_data)
state_store.set('campaigns_last_run', datetime.utcnow())
```

**Advantages**: Simple, no special DB access required.
**Disadvantages**: Misses deletes, requires reliable `updated_at` column, polling adds DB load.

#### Method 3: Incremental Key (Auto-increment ID or sequence)

```python
# Use an always-increasing surrogate key
last_processed_id = state_store.get('last_click_id', 0)
new_clicks = db.query(f"SELECT * FROM clicks WHERE id > {last_processed_id}")
# Process...
state_store.set('last_click_id', new_clicks['id'].max())
```

---

### 2.4 Late-Arriving Data — Design Patterns

Late data is one of the hardest problems in streaming and batch pipelines.

**Scenario**: Ad click events may arrive up to 72 hours late due to mobile app batching, network delays, or ad network reporting delays.

#### Batch Strategy: Lookback Window
```python
# Instead of "process events from yesterday only":
WHERE event_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)

# Use a lookback window that covers potential late arrivals:
WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 DAY)  # 3-day lookback

# Combined with partition overwrite: reprocesses last 3 partitions each run
# Cost: 3x data scanned vs 1x, but ensures late data is captured
```

#### Streaming Strategy: Watermarks
```python
# Apache Beam / Dataflow: define acceptable lateness
pipeline = beam.Pipeline()

events = (pipeline
    | 'ReadFromPubSub' >> beam.io.ReadFromPubSub(subscription='...')
    | 'ParseEvents' >> beam.Map(parse_event)
    | 'WindowIntoSessions' >> beam.WindowInto(
        beam.window.FixedWindows(3600),  # 1-hour windows
        # Allow late data up to 24 hours after window closes
        allowed_lateness=beam.window.Duration(seconds=24*3600),
        # If late data arrives after 5 min but before 24h: update the result
        trigger=trigger.AfterWatermark(
            early=trigger.AfterProcessingTime(5 * 60),   # fire after 5 min
            late=trigger.AfterCount(1)                    # fire for each late event
        ),
        accumulation_mode=trigger.AccumulationMode.ACCUMULATING
    )
    | 'AggregateByWindow' >> beam.CombinePerKey(sum)
)
```

#### Hybrid: Lambda Architecture Pattern
```
Streaming path: process events immediately → real-time dashboard (approximate)
Batch path:     reprocess all events daily → authoritative numbers (exact)
Serving layer:  query batch if available, fall back to streaming for recent data
```

---

### 2.5 Dependency Management with Airflow/Cloud Composer

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryOperator
from airflow.providers.google.cloud.sensors.gcs import GCSObjectExistenceSensor
from datetime import datetime, timedelta

default_args = {
    'owner': 'martech-de',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(hours=1),
    'email_on_failure': True,
    'email': ['martech-alerts@costco.com'],
    'sla': timedelta(hours=2)  # Alert if DAG takes >2 hours
}

with DAG(
    dag_id='martech_daily_pipeline',
    schedule_interval='0 6 * * *',   # 6 AM UTC daily
    start_date=datetime(2024, 1, 1),
    catchup=False,                   # Don't backfill automatically
    max_active_runs=1,               # Only one run at a time
    default_args=default_args,
    tags=['martech', 'daily']
) as dag:

    # Step 1: Wait for upstream data to land in GCS
    wait_for_google_ads = GCSObjectExistenceSensor(
        task_id='wait_for_google_ads_data',
        bucket='costco-raw-data',
        object='google_ads/{{ ds }}/clicks_*.parquet',  # {{ ds }} = execution_date
        timeout=3600,        # Wait up to 1 hour
        poke_interval=300    # Check every 5 minutes
    )

    wait_for_meta_ads = GCSObjectExistenceSensor(
        task_id='wait_for_meta_ads_data',
        bucket='costco-raw-data',
        object='meta_ads/{{ ds }}/ad_insights_*.parquet',
        timeout=3600,
        poke_interval=300
    )

    # Step 2: Run DBT staging models
    run_staging = BashOperator(
        task_id='dbt_run_staging',
        bash_command='dbt run --target prod --select tag:staging --vars \'{"execution_date": "{{ ds }}"}\' '
    )

    # Step 3: Test staging
    test_staging = BashOperator(
        task_id='dbt_test_staging',
        bash_command='dbt test --target prod --select tag:staging'
    )

    # Step 4: Run intermediate + mart models
    run_marts = BashOperator(
        task_id='dbt_run_marts',
        bash_command='dbt run --target prod --select tag:daily'
    )

    # Step 5: Test marts
    test_marts = BashOperator(
        task_id='dbt_test_marts',
        bash_command='dbt test --target prod --select tag:daily'
    )

    # Step 6: Send completion notification
    notify_success = PythonOperator(
        task_id='notify_slack',
        python_callable=send_slack_notification,
        op_kwargs={'message': 'MarTech daily pipeline completed for {{ ds }}'}
    )

    # Define dependency order
    [wait_for_google_ads, wait_for_meta_ads] >> run_staging
    run_staging >> test_staging >> run_marts >> test_marts >> notify_success
```

---

### 2.6 Exactly-Once vs At-Least-Once vs At-Most-Once

| Semantic | Definition | Risk | Use Case |
|----------|------------|------|----------|
| **At-most-once** | Messages may be lost but never duplicated | Data loss | Logs where some loss is OK |
| **At-least-once** | Messages always delivered but may duplicate | Duplicates | Financial events (dedup downstream) |
| **Exactly-once** | Every message processed exactly once | Highest complexity/cost | Financial transactions |

**In practice**:
- Most streaming systems (Kafka, Pub/Sub) provide at-least-once by default
- Exactly-once requires: idempotent consumers + transactional writes + coordination overhead
- Best approach: at-least-once delivery + idempotent processing = effectively exactly-once results

```python
# At-least-once + idempotent = effectively exactly-once
def process_click_event(message: PubSubMessage):
    click_id = message.attributes['click_id']
    
    # Idempotent write: MERGE on click_id — safe to run multiple times
    bq_client.query(f"""
        MERGE INTO `mart.clicks` AS target
        USING (SELECT '{click_id}' AS click_id, ...) AS source
        ON target.click_id = source.click_id
        WHEN NOT MATCHED THEN INSERT (...)
        WHEN MATCHED THEN UPDATE SET ...
    """)
    
    # Only ack after successful write
    message.ack()
```

---

## L3: Real-World Scenarios — Costco/MarTech Style

### 3.1 Scenario: API → GCS → BigQuery Pipeline

**Business requirement**: Ingest Google Ads performance data daily from Google Ads API, land in GCS, transform in BigQuery.

```python
# Full pipeline design

# ============================================================
# Stage 1: Extract from Google Ads API → GCS
# ============================================================
from google.ads.googleads.client import GoogleAdsClient
from google.cloud import storage
import json, datetime

def extract_google_ads_to_gcs(
    customer_id: str,
    execution_date: datetime.date,
    gcs_bucket: str
):
    """Idempotent: overwrites GCS file if run again for same date."""
    client = GoogleAdsClient.load_from_env()
    service = client.get_service("GoogleAdsService")

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value
        FROM campaign
        WHERE segments.date = '{execution_date}'
    """

    response = service.search_stream(customer_id=customer_id, query=query)

    records = []
    for batch in response:
        for row in batch.results:
            records.append({
                'campaign_id': str(row.campaign.id),
                'campaign_name': row.campaign.name,
                'impressions': row.metrics.impressions,
                'clicks': row.metrics.clicks,
                'cost_micros': row.metrics.cost_micros,
                'conversions': row.metrics.conversions,
                'conversion_value': row.metrics.conversions_value,
                'report_date': str(execution_date),
                'extracted_at': datetime.datetime.utcnow().isoformat()
            })

    # Write to GCS (overwrite = idempotent)
    gcs_client = storage.Client()
    bucket = gcs_client.bucket(gcs_bucket)
    blob = bucket.blob(f"google_ads/{execution_date}/campaign_performance.jsonl")
    blob.upload_from_string(
        '\n'.join(json.dumps(r) for r in records),
        content_type='application/json'
    )

    return len(records)

# ============================================================
# Stage 2: GCS → BigQuery (via BigQuery Load Job)
# ============================================================
from google.cloud import bigquery

def load_gcs_to_bigquery(
    gcs_uri: str,
    project: str,
    dataset: str,
    table: str,
    execution_date: datetime.date
):
    """Idempotent: uses partition decorator to overwrite date partition."""
    bq_client = bigquery.Client(project=project)

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # overwrite partition
        time_partitioning=bigquery.TimePartitioning(
            field='report_date',
            type_=bigquery.TimePartitioningType.DAY
        )
    )

    destination = f"{project}.{dataset}.{table}${execution_date.strftime('%Y%m%d')}"
    load_job = bq_client.load_table_from_uri(
        gcs_uri,
        destination,
        job_config=job_config
    )
    load_job.result()  # wait for completion

    if load_job.errors:
        raise RuntimeError(f"Load job failed: {load_job.errors}")

    return bq_client.get_table(f"{project}.{dataset}.{table}").num_rows
```

---

### 3.2 Scenario: Real-Time Ad Event Pipeline (Pub/Sub → Dataflow → BigQuery)

```python
# Apache Beam pipeline: Pub/Sub → Parse → Validate → BigQuery Streaming Insert

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.io.gcp.pubsub import ReadFromPubSub
from apache_beam.io.gcp.bigquery import WriteToBigQuery

class ParseAdEvent(beam.DoFn):
    def process(self, element):
        import json
        try:
            event = json.loads(element.decode('utf-8'))
            # Normalize and validate
            yield {
                'event_id':     event['id'],
                'event_type':   event['type'],
                'campaign_id':  event['campaign']['id'],
                'user_id':      event.get('user', {}).get('id'),
                'clicked_at':   event['timestamp'],
                'cost_micros':  event.get('cost_micros', 0),
                'device_type':  event.get('device', 'unknown')
            }
        except (KeyError, json.JSONDecodeError) as e:
            # Route to dead-letter topic
            yield beam.pvalue.TaggedOutput('dead_letter', {
                'raw_message': element.decode('utf-8'),
                'error': str(e)
            })

def run_pipeline():
    options = PipelineOptions([
        '--runner=DataflowRunner',
        '--project=costco-martech',
        '--region=us-central1',
        '--streaming',
        '--enable_streaming_engine',
        '--autoscaling_algorithm=THROUGHPUT_BASED',
        '--max_num_workers=20'
    ])

    with beam.Pipeline(options=options) as p:
        # Read from Pub/Sub
        raw = (p
            | 'ReadFromPubSub' >> ReadFromPubSub(
                subscription='projects/costco/subscriptions/ad-events-sub',
                with_attributes=True
            )
        )

        # Parse and route
        parsed = (raw
            | 'ParseEvents' >> beam.ParDo(ParseAdEvent()).with_outputs(
                'dead_letter',
                main='valid_events'
            )
        )

        # Window into 5-minute fixed windows for aggregation
        windowed = (parsed.valid_events
            | 'Window' >> beam.WindowInto(
                beam.window.FixedWindows(300),     # 5 minutes
                allowed_lateness=beam.window.Duration(seconds=3600),  # 1-hour lateness
                trigger=trigger.AfterWatermark(late=trigger.AfterCount(1)),
                accumulation_mode=trigger.AccumulationMode.ACCUMULATING
            )
        )

        # Write raw events to BigQuery (streaming insert)
        (parsed.valid_events
            | 'WriteRawToBQ' >> WriteToBigQuery(
                table='costco-martech:streaming.raw_ad_events',
                schema='auto',
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                insert_retry_strategy='RETRY_ON_TRANSIENT_ERROR',
                # Deduplication: BigQuery streaming uses insertId for best-effort dedup
            )
        )

        # Write dead letters for monitoring
        (parsed.dead_letter
            | 'WriteDeadLetter' >> WriteToBigQuery(
                table='costco-martech:monitoring.dead_letter_events',
                schema='auto'
            )
        )
```

---

## L4: Hands-On Design

### 4.1 Design: Airflow DAG for Multi-Source Daily Pipeline

**Requirement**: Every day at 6 AM, ingest from Google Ads + Meta Ads, transform, load, alert.

```
Key design decisions:
1. Use sensors (not just time triggers) to wait for actual data arrival
2. Separate staging run + test from mart run + test
3. Use task groups for cleaner organization
4. Build in SLA monitoring

DAG dependency graph:
  
  sense_google_data ──┐
                       ├──► run_staging ──► test_staging ──► run_marts ──► test_marts ──► notify
  sense_meta_data ────┘
```

```python
from airflow.utils.task_group import TaskGroup

with DAG('martech_daily', schedule='0 6 * * *', ...) as dag:

    with TaskGroup('sense') as sense_group:
        sense_google = GCSObjectExistenceSensor(...)
        sense_meta = GCSObjectExistenceSensor(...)

    with TaskGroup('staging') as staging_group:
        run_staging = BashOperator(task_id='run', bash_command='dbt run --select tag:staging')
        test_staging = BashOperator(task_id='test', bash_command='dbt test --select tag:staging')
        run_staging >> test_staging

    with TaskGroup('marts') as marts_group:
        run_marts = BashOperator(task_id='run', bash_command='dbt run --select tag:daily')
        test_marts = BashOperator(task_id='test', bash_command='dbt test --select tag:daily')
        run_marts >> test_marts

    notify = PythonOperator(task_id='notify', python_callable=send_slack)

    sense_group >> staging_group >> marts_group >> notify
```

---

### 4.2 Design: Incremental Load Pattern — BigQuery

```python
# Incremental load logic for a large events table
# Pattern: process new + reprocess last 3 days for late data

def incremental_load(execution_date: str, lookback_days: int = 3):
    """
    Process events for [execution_date - lookback_days] to [execution_date].
    Use INSERT OVERWRITE on each affected partition.
    """
    start_date = datetime.fromisoformat(execution_date) - timedelta(days=lookback_days)
    end_date = datetime.fromisoformat(execution_date)

    query = f"""
    -- Source → staging (with dedup)
    CREATE OR REPLACE TEMP TABLE staged_events AS
    SELECT *
    FROM (
        SELECT *,
               ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY _loaded_at DESC) AS rn
        FROM `raw.ad_events`
        WHERE event_date BETWEEN '{start_date.date()}' AND '{end_date.date()}'
    ) WHERE rn = 1;

    -- Overwrite affected partitions (idempotent)
    INSERT INTO `mart.ad_events`
    PARTITION (event_date)
    SELECT * EXCEPT (rn)
    FROM staged_events;
    """

    bq_client.query(query).result()
```

---

## L5: Edge Cases & Pitfalls

### 5.1 The Backfill Trap — Catchup Mode in Airflow

```python
# DANGEROUS: catchup=True with daily schedule and start_date in the past
with DAG(
    dag_id='my_pipeline',
    schedule_interval='@daily',
    start_date=datetime(2023, 1, 1),  # Start date 1 year ago
    catchup=True  # DEFAULT IS TRUE — will trigger 365 runs immediately!
):
    ...

# SAFE: disable catchup for new pipelines
with DAG(
    catchup=False,      # Only run for current/future schedules
    max_active_runs=1,  # Prevent concurrent runs if catchup is enabled
    ...
):
    ...

# CORRECT backfill: use CLI explicitly for controlled backfill
# airflow dags backfill my_pipeline --start-date 2024-01-01 --end-date 2024-01-31
```

---

### 5.2 The Watermark Lag Problem in Streaming

```python
# Problem: Dataflow's watermark estimates when "all data has arrived"
# If watermark is too aggressive (advances too fast), late data is dropped

# Symptom: real-time counts differ from daily batch counts by 2-5%
# Root cause: some mobile events arrive 2-3 hours after the event time
# Watermark advanced past those events → they were too late → dropped

# Fix 1: Increase allowed_lateness
beam.WindowInto(
    beam.window.FixedWindows(3600),
    allowed_lateness=beam.window.Duration(seconds=24*3600)  # accept up to 24h late
)

# Fix 2: Use batch job for authoritative numbers
# Streaming = approximate (real-time)
# Batch = exact (T+1 day)
# Reconcile and alert when they differ by >1%
```

---

### 5.3 Silent Data Loss from INNER JOIN in Pipelines

```python
# Mistake: using INNER JOIN in a transformation pipeline
enriched = clicks.join(campaigns, on='campaign_id', how='inner')
# Clicks for DELETED or UNMATCHED campaigns silently disappear
# This is almost always wrong in analytics pipelines

# Correct: use LEFT JOIN and monitor the null rate
enriched = clicks.join(campaigns, on='campaign_id', how='left')

# Add data quality check
null_rate = enriched.filter(F.col('campaign_name').isNull()).count() / enriched.count()
if null_rate > 0.01:  # >1% unmatched clicks
    raise DataQualityError(f"High null rate in campaign join: {null_rate:.2%}")
```

---

### 5.4 Timezone Pitfalls

```python
# Problem: ad events from global platforms come in UTC
# Costco reports in PST/PDT (UTC-8 / UTC-7)
# If you assign events to days using UTC, you split US events across wrong days

# Wrong: naive UTC date assignment
events = events.withColumn('event_date', F.to_date('event_timestamp'))
# An event at 11 PM PST = next day in UTC → wrong date bucket

# Correct: convert to report timezone first
events = events.withColumn(
    'event_date',
    F.to_date(
        F.from_utc_timestamp('event_timestamp', 'America/Los_Angeles')
    )
)

# Document timezone in your pipeline
REPORT_TIMEZONE = 'America/Los_Angeles'  # PST/PDT
```

---

### 5.5 Partial Failures and Half-Written Partitions

```python
# Problem: pipeline writes 3 of 5 partitions before failing
# Next run skips already-written partitions → some partitions missing

# Solution 1: Write to staging location first, then atomic move
# Step 1: write all data to temp location
spark.write.parquet("gs://bucket/tmp/output_20240115/")
# Step 2: only if ALL writes successful, move to final location
gcs_client.rename("gs://bucket/tmp/output_20240115/",
                  "gs://bucket/output/report_date=2024-01-15/")

# Solution 2: Track write completion in metadata table
def write_with_tracking(df, partition_date):
    df.write.mode('overwrite').parquet(f"gs://bucket/output/date={partition_date}/")
    bq_client.query(f"""
        INSERT INTO pipeline_metadata.partition_status
        VALUES ('{partition_date}', 'SUCCESS', CURRENT_TIMESTAMP())
    """)

# Solution 3: Idempotent overwrite — always overwrite, never skip
# The extra cost of re-writing a few already-correct partitions is worth the reliability
```

---

## L6: Interview Questions — Easy to Very Hard

### EASY

---

**Q1: What is a data pipeline and what are its key properties?**

**What they're testing**: Fundamentals, ability to define clearly.

**Answer**: A data pipeline is a sequence of automated steps that moves data from sources to destinations — typically involving ingestion, transformation, validation, and loading. The key properties every production pipeline must have are: idempotency (re-running produces the same result, safe to retry), reliability (handles failures gracefully), observability (logs and metrics let you see what happened), scalability (handles growing data volumes without redesign), and recoverability (you can reprocess past periods).

---

**Q2: What is the difference between batch and streaming processing? When would you choose each?**

**Answer**: Batch processes data in chunks at scheduled intervals (e.g., daily at 6 AM), optimized for high throughput and lower cost. Streaming processes events as they arrive, optimized for low latency.

Choose batch when: results needed daily/hourly, cost matters more than latency, business logic is complex (easier to test in batch), late data is common (batch naturally handles it).

Choose streaming when: real-time decisions are needed (fraud detection, real-time dashboards), events trigger immediate actions (send notification when user abandons cart), latency requirement is < 1 minute.

Many production systems use both: streaming for approximate real-time results, batch for authoritative daily numbers.

---

### MEDIUM

---

**Q3: What is idempotency and why is it critical for data pipelines?**

**Answer**: Idempotency means running a pipeline once or multiple times produces the same result. It's critical because: pipelines fail and are retried automatically (by Airflow, by Dataflow, by Kubernetes). If a pipeline isn't idempotent, a retry after partial failure causes duplicate data. A pipeline that loads "new records since last run" is NOT idempotent — if it ran at midnight, partially loaded, then was retried at 12:15 AM, some records get loaded twice.

Making a pipeline idempotent: use partition overwrite (process date X → always write/overwrite partition X), or MERGE/UPSERT with a natural key, or deduplication on a business key. The key pattern: the pipeline's output should be a pure function of its inputs and the execution date — no side effects that depend on prior runs.

**Follow-up**: "How do you make a streaming pipeline idempotent?" → At-least-once delivery + idempotent consumers (MERGE on message_id), or use Apache Beam's exactly-once mode with checkpointing.

---

**Q4: Walk me through how you'd design a CDC pipeline to capture changes from an operational MySQL database into BigQuery.**

**Answer**:

Architecture:
1. **Source**: MySQL with binary logging enabled (binlog_format=ROW)
2. **CDC tool**: Debezium running on Kafka Connect, reading MySQL binlog
3. **Message queue**: Kafka topic per table (e.g., `mysql.campaigns.campaigns_table`)
4. **Stream processor**: Dataflow reading from Kafka → parse CDC events → classify as INSERT/UPDATE/DELETE
5. **Destination**: BigQuery with MERGE logic

For the BigQuery landing:
- INSERT events → new rows in staging table
- UPDATE events → MERGE on primary key, update changed columns
- DELETE events → either soft delete (set is_deleted=TRUE) or hard delete (DELETE statement)

For SCD Type 2 tracking: every UPDATE event creates a new row with valid_from/valid_to, preserving full history.

**Key consideration**: Handle schema changes (ALTER TABLE in MySQL) — Debezium sends schema change events. Your pipeline must handle new columns gracefully (add to BigQuery schema, backfill with NULL).

---

### HARD

---

**Q5: You have a daily pipeline that processes 500GB. It ran successfully at 6 AM. At 10 AM, the source team says 20% of yesterday's data was missing and has now been loaded. How do you reprocess without corrupting existing data?**

**What they're testing**: Backfill design, idempotency under partial correction scenarios.

**Answer**:

**Step 1: Assess impact**
- Which tables are downstream of the affected source?
- What is the execution date range? (Yesterday only, or does this source affect 3-day lookbacks?)

**Step 2: Trigger a targeted backfill**
- Re-run the pipeline for yesterday's execution date specifically
- The pipeline must be designed to overwrite (not append) its output for that date

```python
# Correct pipeline design: OVERWRITE the affected partition
def run_pipeline(execution_date: date):
    data = extract(source, date_filter=execution_date)
    transformed = transform(data)
    load(
        transformed,
        partition=execution_date,
        mode='overwrite'   # not 'append'
    )
```

**Step 3: Propagate downstream**
- After re-running the staging layer, re-run intermediate and mart layers in dependency order
- This is where DBT's `dbt run --select +mart_campaign_performance` is valuable — it runs upstream models first

**Step 4: Validate**
- Compare row counts before and after correction
- Check that the 20% missing data appears in the output
- Alert downstream consumers that data was corrected

**What would break this**: If the pipeline uses `WHERE event_date > MAX(processed_date)` (append-only, watermark-based) — it would NOT pick up the backdated data at all. This is why idempotent overwrite is superior to append-based incremental patterns for correctable pipelines.

---

**Q6: Design a pipeline that handles late-arriving ad events (up to 48 hours late) for a campaign performance dashboard that business stakeholders check at 8 AM every day.**

**What they're testing**: Late data handling, batch/streaming design, stakeholder communication.

**Answer**:

**Architecture decision**: Hybrid — streaming for real-time approximation, batch for authoritative T+2 numbers.

**Batch pipeline (authoritative)**:
- Runs at 6 AM daily
- Processes events from D-3 to D-0 (3-day lookback window)
- Uses INSERT OVERWRITE on each date partition
- Handles up to 72 hours of late data
- Takes ~45 min → data ready before stakeholders arrive at 8 AM

```
Scheduled: 6 AM daily
Process: [D-3, D-2, D-1, D-0] using partition overwrite
Duration: ~45 minutes
Ready: ~6:45 AM ✓ Before 8 AM stakeholder check
```

**Streaming pipeline (near-real-time)**:
- Continuously processes events as they arrive
- Writes to a separate `real_time` table with a `is_preliminary` flag
- Stakeholders see this for intra-day monitoring
- Data from this table is REPLACED by the batch pipeline each morning

**Data freshness contract with stakeholders**:
- Numbers before 6 AM (yesterday): preliminary, streaming-based
- Numbers after 6:45 AM: authoritative, includes late arrivals up to 48h
- Corrections beyond 48h: manual reprocessing on request

**Monitoring**:
- Alert if late data rate exceeds 5% (indicates systemic delay in ad networks)
- Alert if D-1 authoritative numbers differ from D-1 streaming by >2%

---

### VERY HARD

---

**Q7: Design an end-to-end data platform for Costco MarTech that handles 100M ad events per day, supports real-time campaign monitoring, daily performance reporting, and requires data lineage for compliance. Walk me through every architectural decision.**

**What they're testing**: System design, trade-off reasoning, breadth of platform knowledge.

**Answer**:

**Requirements clarification** (always do this first):
- Latency: real-time = seconds or minutes?
- Scale: 100M events/day = ~1,200 events/second at peak
- Compliance: which regulations? (GDPR, CCPA for member data)
- Consumers: BI dashboards, ML models, ad hoc SQL?

**Architecture**:

**Layer 1 — Ingestion**
- Ad platform APIs (Google Ads, Meta, TikTok) → Cloud Composer DAGs → GCS (raw landing zone)
- Clickstream events → Pub/Sub → Dataflow → BigQuery Streaming Insert (real-time path)
- Member events from POS/web → Pub/Sub → GCS (batch) or BigQuery Streaming (real-time)

**Layer 2 — Storage**
- GCS: raw data lake (source of truth for reprocessing), partitioned by source/date
- BigQuery: analytical warehouse, partitioned by event_date, clustered by campaign_id
- Separate datasets: `raw`, `staging`, `intermediate`, `marts`, `monitoring`

**Layer 3 — Transformation**
- DBT on Cloud Composer: daily batch transformations (staging → intermediate → marts)
- Dataflow: real-time stream processing (sessionization, real-time aggregations)
- Separate real-time tables (streaming) + authoritative daily tables (batch)

**Layer 4 — Data Quality**
- DBT tests on every model (unique, not_null, referential integrity)
- Row count reconciliation: source system counts vs BigQuery counts
- Freshness checks via DBT source freshness
- Anomaly detection: alert if ROAS drops >50% vs prior 7-day average

**Layer 5 — Governance & Lineage**
- Dataplex: automatic data discovery and tagging
- DBT lineage graph: column-level lineage from source to mart
- BigQuery column-level security: PII columns (member_id, email) accessible only to approved roles
- Data catalog: every table/column documented in DBT + Dataplex

**Layer 6 — Serving**
- Looker: BI dashboards for marketing team
- BigQuery: ad hoc SQL for analysts
- BigQuery ML: churn prediction, LTV models reading from marts
- Real-time: BigQuery streaming or Firestore for sub-second lookups

**Trade-off decisions**:
- Why BigQuery over Snowflake: native GCP integration, serverless, BigQuery ML built-in
- Why Pub/Sub over Kafka: fully managed, native GCP, sufficient for 1,200 events/sec; Kafka would be chosen if sub-100ms latency or complex routing needed
- Why DBT over custom Spark: SQL-first, built-in testing, lineage, documentation; Spark for >TB-scale transformations or ML feature engineering
- Why batch-authoritative + streaming-approximate: streaming exactly-once is expensive; authoritative daily numbers needed for billing anyway

---

**Q8: Your daily pipeline sometimes produces different row counts for the same execution date on different runs. Stakeholders are complaining that the 8 AM report shows one number, but the 11 AM re-run shows another. How do you diagnose and permanently fix this?**

**What they're testing**: Debugging non-determinism, pipeline design maturity.

**Root causes to investigate**:

1. **Non-idempotent extraction**: Is the API extraction using `WHERE created_at > last_run_timestamp`? If last_run_timestamp changes between runs, different rows are extracted.

2. **Append-only load**: Is the pipeline appending instead of overwriting? Each run adds more rows to the same partition.

3. **Source data mutability**: Is the source table being written to between the 8 AM and 11 AM runs? New data arrives and the pipeline picks it up.

4. **Timestamp-based filtering without timezone handling**: Events at 11:50 PM PST might be in two different UTC days — which day they land in depends on when the pipeline runs.

5. **Non-deterministic deduplication**: Using `dropDuplicates()` in PySpark without specifying columns — the "kept" row may differ between runs.

**Permanent fixes**:
- Change extract to use execution_date as the filter (not "since last run")
- Change load to OVERWRITE the partition (not append)
- Add an immutable snapshot to GCS: always load FROM the snapshot, not FROM the live source
- Add row count monitoring: alert if row count for a partition changes after initial load
- For the source mutability issue: define a "data freeze window" — pipeline runs at 6 AM, uses data as of 5:59 AM, any new data goes to the NEXT day's run

---

## Summary: Data Pipeline Design — Senior Mastery Checklist

| Skill | What Senior Looks Like |
|-------|------------------------|
| Idempotency | Designs pipelines that are safe to retry by default |
| Batch vs Streaming | Can articulate trade-offs and choose for given requirements |
| Late data | Lookback windows for batch; watermarks for streaming |
| CDC | Knows log-based vs timestamp-based; knows when each applies |
| Airflow DAGs | Sensors, retries, task groups, catchup, SLAs |
| Backfill design | Execution date parameterization + partition overwrite |
| Exactly-once | Understands it's at-least-once + idempotent consumer |
| Failure handling | Dead-letter queues, alerting, partial failure detection |
| Observability | Row count checks, freshness monitoring, SLA alerts |
| System design | Can design end-to-end platform with reasoned trade-offs |
