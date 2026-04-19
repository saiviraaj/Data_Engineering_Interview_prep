# Topic 4: GCP Data Engineering Stack (Deep Dive)
## Costco Sr. Data Engineer — Exhaustive Interview Textbook

---

## Table of Contents
1. [L1: Core Concepts — Overview of GCP Services](#l1-core-concepts)
2. [L2: Deep Technical Understanding](#l2-deep-technical-understanding)
3. [L3: Real-World Scenarios — Costco/MarTech Style](#l3-real-world-scenarios)
4. [L4: Hands-On Design & Code](#l4-hands-on-design--code)
5. [L5: Edge Cases & Pitfalls](#l5-edge-cases--pitfalls)
6. [L6: Interview Questions — Easy to Very Hard](#l6-interview-questions)

---

## L1: Core Concepts

### 1.1 The Modern GCP Data Stack — Service Map

```
                         ┌─────────────────────────────────────────────────────┐
                         │              DATA SOURCES                            │
                         │  APIs │ Databases │ Files │ Streams │ IoT            │
                         └──────────────────┬──────────────────────────────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    ▼                       ▼                       ▼
             [Pub/Sub]              [Cloud Storage]          [Transfer Service]
           (event streams)          (batch files)           (bulk migration)
                    │                       │                       │
                    └───────────────────────┼───────────────────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    ▼                       ▼                       ▼
              [Dataflow]              [Dataproc]              [BigQuery DTS]
           (stream+batch ETL)       (Spark/Hadoop)           (scheduled loads)
           (Apache Beam)            (large-scale ML)
                    │                       │                       │
                    └───────────────────────┼───────────────────────┘
                                            │
                                            ▼
                                      [BigQuery]
                                   (analytical DWH)
                                   (petabyte-scale)
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    ▼                       ▼                       ▼
               [Looker]             [BigQuery ML]            [Dataplex]
            (BI dashboards)        (ML in SQL)             (governance)
```

### 1.2 Service-to-Use-Case Mapping

| Service | Primary Use Case | When to Choose |
|---------|-----------------|----------------|
| **BigQuery** | Analytical DWH, petabyte-scale SQL | OLAP queries, reporting, ML on structured data |
| **Dataflow** | Stream + batch ETL (serverless) | Real-time pipelines, Pub/Sub → BQ, complex transformations |
| **Dataproc** | Managed Spark/Hadoop clusters | Large-scale Spark jobs, ML training, existing Spark codebase |
| **Pub/Sub** | Managed message queue | Decoupled event streaming, IoT, real-time ingestion |
| **Cloud Storage** | Object storage / data lake | Raw data landing zone, archive, ML datasets |
| **Dataplex** | Data governance + discovery | Data catalogs, quality rules, lineage across GCP |
| **Cloud Composer** | Managed Airflow | DAG orchestration, workflow management |
| **Datastream** | CDC from operational DBs | Near-real-time DB replication to GCS/BQ |

---

## L2: Deep Technical Understanding

### 2.1 BigQuery Internals — Storage + Query Engine

#### 2.1.1 Dremel — The Query Engine

BigQuery's query engine is based on **Dremel** (Google's internal columnar query system). Key architectural properties:

**Multi-level execution tree**:
```
                    Root Server (query coordinator)
                   /           |           \
           Mixer 1         Mixer 2         Mixer 3
          /      \        /      \        /      \
       Leaf1   Leaf2   Leaf3   Leaf4   Leaf5   Leaf6
```

- **Root server**: receives the query, builds execution plan, distributes work
- **Mixers**: intermediate aggregation nodes
- **Leaf servers**: actually read data from Capacitor (storage format)

**Why BigQuery is fast**:
1. Columnar storage (Capacitor format): reads only requested columns
2. Massively parallel: thousands of leaf servers read in parallel
3. Disaggregated storage from compute: storage scales independently
4. Automatic optimization: statistics-based query planning

#### 2.1.2 Storage Model

```
BigQuery table
├── Partitions (by date/int range)
│   ├── Partition 2024-01-01
│   │   ├── Column: campaign_id    [compressed block 1][block 2]...[block N]
│   │   ├── Column: spend_usd      [compressed block 1][block 2]...[block N]
│   │   ├── Column: clicked_at     [compressed block 1][block 2]...[block N]
│   │   └── ...
│   └── Partition 2024-01-02
│       └── ...
```

Within each partition, data is sorted by cluster columns and divided into **blocks**. Each block has min/max statistics. When you filter `WHERE campaign_id = 'C001'`, BigQuery reads the min/max of each block and skips blocks where C001 can't exist — this is **block-level pruning** (what clustering enables).

#### 2.1.3 Slot-Based Compute Model

```
BigQuery slot = 1 unit of computational capacity
              ≈ 1 virtual CPU for query execution

On-demand pricing:
  - Query gets up to 2000 slots (shared with all Google customers)
  - Charged by TB scanned (not by slot usage)

Capacity pricing (reservations):
  - Buy dedicated slots (100, 500, 2000, etc.)
  - Pay flat monthly rate regardless of queries run
  - Better for: high-volume, predictable workloads
  - Worse for: spiky, infrequent workloads
```

```sql
-- Monitor slot usage
SELECT
    project_id,
    reservation_id,
    job_count,
    total_slot_ms,
    ROUND(total_slot_ms / (60 * 60 * 1000), 2) AS slot_hours,
    TIMESTAMP_DIFF(MAX(end_time), MIN(start_time), SECOND) AS window_seconds
FROM `region-us`.INFORMATION_SCHEMA.JOBS
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
GROUP BY 1, 2
ORDER BY total_slot_ms DESC;
```

#### 2.1.4 BigQuery Storage Write API vs Legacy Streaming

```python
# Legacy Streaming Insert (older approach)
# - Data available in seconds
# - Best-effort deduplication via insertId
# - Higher cost ($0.01 per 200MB)
# - Data not immediately available for table copy/export

from google.cloud import bigquery
client = bigquery.Client()
errors = client.insert_rows_json(
    "project.dataset.table",
    [{"col1": "val1", "col2": 123}],
    row_ids=["unique-id-for-dedup"]  # insertId for dedup
)

# Storage Write API (recommended for new pipelines)
# - Exactly-once semantics with streams
# - Lower cost ($0.025 per 1GB for committed)
# - PENDING mode: batch-commit (atomic, all-or-nothing)
# - COMMITTED mode: immediately visible

from google.cloud.bigquery_storage_v1 import BigQueryWriteClient
from google.cloud.bigquery_storage_v1.types import WriteStream

client = BigQueryWriteClient()
# PENDING mode: write then commit (exactly-once)
# COMMITTED mode: write immediately visible
# DEFAULT mode: best-effort, compatible with legacy streaming
```

---

### 2.2 Dataflow — Apache Beam Model Deep Dive

#### 2.2.1 The Beam Programming Model

Apache Beam is the programming model; Dataflow is Google's managed runner for Beam.

**Core abstractions**:
```
Pipeline   = the entire job
PCollection = distributed dataset (immutable)
PTransform  = operation on PCollection(s)
Runner     = execution engine (Dataflow, Spark, Flink, Direct)
```

**Pipeline execution flow**:
```python
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions

options = PipelineOptions([
    '--runner=DataflowRunner',
    '--project=costco-martech',
    '--region=us-central1',
    '--temp_location=gs://costco-temp/beam-temp/',
    '--staging_location=gs://costco-temp/beam-staging/',
    '--job_name=ad-events-pipeline',
    '--max_num_workers=20',
    '--autoscaling_algorithm=THROUGHPUT_BASED'
])

with beam.Pipeline(options=options) as p:
    # Read (source) → Transform(s) → Write (sink)
    (p
     | 'Read' >> beam.io.ReadFromText('gs://bucket/input/*.json')
     | 'Parse' >> beam.Map(json.loads)
     | 'Filter' >> beam.Filter(lambda x: x['status'] == 'active')
     | 'Transform' >> beam.Map(transform_fn)
     | 'Write' >> beam.io.WriteToBigQuery(
         table='project:dataset.table',
         schema='auto',
         write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND
     )
    )
```

#### 2.2.2 Batch vs Streaming in Beam — Same Code

One of Beam's key features: **batch and streaming use the same API**.

```python
# BATCH pipeline: reads from GCS files
batch_source = beam.io.ReadFromText('gs://bucket/data/*.json')

# STREAMING pipeline: reads from Pub/Sub
stream_source = beam.io.ReadFromPubSub(
    subscription='projects/project/subscriptions/sub-name'
)

# The same transforms work for both:
def process_event(element):
    return {
        'campaign_id': element['campaign']['id'],
        'cost_usd': element['cost_micros'] / 1e6,
        'clicked_at': element['timestamp']
    }

# Works identically for both batch and streaming sources
processed = source | 'Process' >> beam.Map(process_event)
```

#### 2.2.3 Windowing — The Core of Streaming

Windowing groups streaming elements into finite buckets for aggregation.

```python
import apache_beam as beam
from apache_beam import window
from apache_beam.transforms.trigger import (
    AfterWatermark, AfterProcessingTime, AfterCount,
    AccumulationMode
)

# Fixed windows: equal-sized, non-overlapping time buckets
windowed_fixed = (stream
    | 'FixedWindow' >> beam.WindowInto(
        window.FixedWindows(3600),    # 1-hour buckets
        allowed_lateness=window.Duration(seconds=7200),  # accept 2h late data
        trigger=AfterWatermark(
            early=AfterProcessingTime(60),    # fire early after 60s processing time
            late=AfterCount(1)                # fire for each late element
        ),
        accumulation_mode=AccumulationMode.ACCUMULATING  # accumulate = add to prior
    )
)

# Sliding windows: overlapping — "last N minutes, every M minutes"
windowed_sliding = (stream
    | 'SlidingWindow' >> beam.WindowInto(
        window.SlidingWindows(3600, 300)  # 1-hour window, slides every 5 minutes
    )
)

# Session windows: dynamic — group events within N seconds of each other
windowed_sessions = (stream
    | 'SessionWindow' >> beam.WindowInto(
        window.Sessions(gap_size=1800)   # new session if 30+ minute gap
    )
)

# After windowing: aggregate within windows
hourly_spend = (windowed_fixed
    | 'ExtractSpend' >> beam.Map(lambda e: (e['campaign_id'], e['cost_usd']))
    | 'SumSpend' >> beam.CombinePerKey(sum)
    | 'Format' >> beam.Map(lambda kv: {
        'campaign_id': kv[0],
        'hourly_spend': kv[1]
    })
)
```

#### 2.2.4 Watermarks — Handling Late Data

```
                    Event Time ──────────────────────────────►
                    
      [10:00]         [10:30]          [11:00]
         │               │                │
    Event created    Event arrives     Window closes
                     at processor      (10:00-11:00)
                     
    Lag = 30 minutes → within allowed_lateness → processed
    
    If event arrives at 13:00 (3h late):
    → Depends on allowed_lateness setting
    → If allowed_lateness=2h: event DROPPED
    → If allowed_lateness=4h: event processed, late result emitted
```

```python
# Watermark = estimate of "how far behind we are from real-time"
# Beam auto-advances watermark based on event timestamps seen
# allowed_lateness = how long after watermark closes to still accept events

# For ad events where mobile apps batch-send:
window.FixedWindows(3600),
allowed_lateness=window.Duration(seconds=86400),   # 24 hours of lateness OK
trigger=AfterWatermark(
    late=AfterCount(1)    # fire result for every late event
),
accumulation_mode=AccumulationMode.ACCUMULATING
# ACCUMULATING: late results include all prior data + new late element
# DISCARDING:   late results contain ONLY the late element
```

#### 2.2.5 Dataflow Autoscaling

```python
# Dataflow automatically scales workers based on throughput
options = PipelineOptions([
    '--autoscaling_algorithm=THROUGHPUT_BASED',  # default
    '--max_num_workers=50',       # upper limit
    '--num_workers=5',            # initial workers
    '--machine_type=n1-standard-4'  # 4 CPU, 15GB RAM per worker
])

# For streaming jobs: enable Streaming Engine (recommended)
# Streaming Engine offloads window state to Google infrastructure
# Reduces per-worker memory requirements significantly
'--enable_streaming_engine'

# Cost optimization: use preemptible workers for batch
'--use_public_ips=false'
'--experiments=shuffle_mode=service'  # Dataflow Shuffle: managed shuffle, faster
```

---

### 2.3 Dataproc — Managed Spark Deep Dive

#### 2.3.1 Dataproc vs Dataflow — When to Use Each

| Dimension | Dataflow | Dataproc |
|-----------|----------|----------|
| **Programming model** | Apache Beam (unified) | Apache Spark/Hadoop/Flink |
| **Serverless** | Yes (fully managed) | No (cluster management needed) |
| **Startup time** | 3-5 minutes | 60-90 seconds |
| **Best for** | New pipelines, streaming, Beam native | Existing Spark code, ML, Hadoop migration |
| **Auto-scaling** | Automatic | Manual or autoscaling (less smooth) |
| **Cost model** | Per worker-hour + DFU | Per vCPU/hour (cheaper for long jobs) |
| **Library support** | Beam transforms | Full PySpark/Scala Spark ecosystem |

**Decision rule**:
- New streaming pipeline → **Dataflow** (serverless, scales automatically)
- Existing Spark codebase → **Dataproc** (no rewrite needed)
- Large ML training with complex Spark ML → **Dataproc**
- Complex ETL with rich Spark transformations → **Dataproc**
- Simple ETL from Pub/Sub to BigQuery → **Dataflow**

#### 2.3.2 Dataproc Cluster Configuration

```python
# Create Dataproc cluster via Python client
from google.cloud import dataproc_v1 as dataproc

def create_cluster(project_id: str, region: str, cluster_name: str):
    cluster_client = dataproc.ClusterControllerClient(
        client_options={"api_endpoint": f"{region}-dataproc.googleapis.com:443"}
    )

    cluster = {
        "project_id": project_id,
        "cluster_name": cluster_name,
        "config": {
            "master_config": {
                "num_instances": 1,
                "machine_type_uri": "n1-standard-4",
                "disk_config": {
                    "boot_disk_type": "pd-ssd",
                    "boot_disk_size_gb": 100
                }
            },
            "worker_config": {
                "num_instances": 4,
                "machine_type_uri": "n1-standard-8",
                "disk_config": {
                    "boot_disk_size_gb": 200,
                    "num_local_ssds": 2   # local SSD for shuffle = faster
                }
            },
            # Secondary workers = preemptible (60-80% cheaper)
            "secondary_worker_config": {
                "num_instances": 10,
                "preemptibility": "PREEMPTIBLE"
            },
            "software_config": {
                "image_version": "2.1-debian11",
                "properties": {
                    # Spark tuning
                    "spark:spark.sql.adaptive.enabled": "true",
                    "spark:spark.sql.adaptive.coalescePartitions.enabled": "true",
                    "spark:spark.sql.shuffle.partitions": "auto",
                    "spark:spark.executor.memory": "6g",
                    "spark:spark.executor.cores": "4",
                    "spark:spark.driver.memory": "4g",
                    # BigQuery connector
                    "spark:spark.datasource.bigquery.project": project_id
                }
            },
            "gce_cluster_config": {
                "service_account": "dataproc-sa@project.iam.gserviceaccount.com",
                "service_account_scopes": ["https://www.googleapis.com/auth/cloud-platform"]
            }
        }
    }
    
    operation = cluster_client.create_cluster(
        request={"project_id": project_id, "region": region, "cluster": cluster}
    )
    return operation.result()
```

#### 2.3.3 Dataproc Serverless — No Cluster Management

```python
# Dataproc Serverless: submit Spark jobs without managing clusters
# - No cluster creation/deletion overhead
# - Pay only for execution time (per CU-second)
# - Auto-scales within the job

from google.cloud import dataproc_v1

def submit_serverless_batch(project_id, region, bucket, script_uri):
    batch_client = dataproc_v1.BatchControllerClient(
        client_options={"api_endpoint": f"{region}-dataproc.googleapis.com:443"}
    )

    batch = {
        "pyspark_batch": {
            "main_python_file_uri": script_uri,  # gs://bucket/script.py
            "args": ["--date", "2024-01-15"],
            "python_file_uris": ["gs://bucket/libs/utils.py"],
        },
        "runtime_config": {
            "version": "2.0",
            "properties": {
                "spark.executor.instances": "10",
                "spark.driver.memory": "4g",
                "spark.executor.memory": "8g"
            }
        },
        "environment_config": {
            "execution_config": {
                "service_account": "dataproc-sa@project.iam.gserviceaccount.com",
                "subnetwork_uri": "projects/project/regions/us-central1/subnetworks/default"
            }
        }
    }

    operation = batch_client.create_batch(
        request={"parent": f"projects/{project_id}/locations/{region}", "batch": batch}
    )
    return operation.result()
```

---

### 2.4 Pub/Sub — Event Streaming Deep Dive

#### 2.4.1 Core Concepts

```
Publisher → Topic → Subscription → Subscriber
                    (pull or push)

Topic: named resource where publishers send messages
Subscription: named resource representing a stream of messages from topic
  - Pull: subscriber calls PullRequest to get messages (most common)
  - Push: Pub/Sub pushes messages to a HTTPS endpoint

Message: data (bytes) + attributes (key-value metadata) + message_id
Acknowledgment: subscriber signals message processed successfully
Retention: unacked messages retained for 7 days (default)
```

#### 2.4.2 Publisher and Subscriber Patterns

```python
from google.cloud import pubsub_v1
import json

# ============================================================
# Publisher: Ad event from web tracking
# ============================================================
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path("costco-project", "ad-events")

# Batch settings for high-throughput publishing
batch_settings = pubsub_v1.types.BatchSettings(
    max_messages=1000,          # batch up to 1000 messages
    max_bytes=1024 * 1024,      # or until 1MB
    max_latency=0.05            # or every 50ms
)
publisher = pubsub_v1.PublisherClient(batch_settings=batch_settings)

def publish_ad_event(event: dict):
    data = json.dumps(event).encode('utf-8')
    # Attributes for server-side filtering
    future = publisher.publish(
        topic_path,
        data=data,
        campaign_id=event['campaign_id'],   # message attribute
        event_type=event['type']
    )
    return future.result()  # blocks until published

# ============================================================
# Subscriber: Pull-based consumer (Dataflow/Cloud Function)
# ============================================================
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path("costco-project", "ad-events-sub")

def process_messages(max_messages: int = 100):
    """Pull and process messages with retry logic."""
    response = subscriber.pull(
        request={"subscription": subscription_path, "max_messages": max_messages}
    )

    ack_ids = []
    for msg in response.received_messages:
        try:
            event = json.loads(msg.message.data.decode('utf-8'))
            process_ad_event(event)
            ack_ids.append(msg.ack_id)  # only ack on success
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            # Don't ack → message redelivered after ack_deadline

    if ack_ids:
        subscriber.acknowledge(
            request={"subscription": subscription_path, "ack_ids": ack_ids}
        )

# ============================================================
# Streaming Pull (long-running, callback-based)
# ============================================================
def callback(message: pubsub_v1.types.PubsubMessage):
    try:
        event = json.loads(message.data)
        process_ad_event(event)
        message.ack()           # success → ack
    except Exception as e:
        message.nack()          # failure → redelivery

streaming_pull_future = subscriber.subscribe(
    subscription_path,
    callback=callback,
    flow_control=pubsub_v1.types.FlowControl(
        max_messages=500,           # max in-flight messages
        max_bytes=50 * 1024 * 1024  # max 50MB in-flight
    )
)

with subscriber:
    try:
        streaming_pull_future.result(timeout=300)
    except TimeoutError:
        streaming_pull_future.cancel()
```

#### 2.4.3 Pub/Sub vs Kafka — When to Use Each

| Dimension | Pub/Sub | Kafka |
|-----------|---------|-------|
| **Management** | Fully managed (serverless) | Self-managed or Confluent Cloud |
| **Latency** | ~100ms P99 | ~10-50ms P99 |
| **Replay** | 7 days max | Configurable (days to forever) |
| **Message ordering** | Per-ordering-key only | Per-partition (guaranteed) |
| **Throughput** | Auto-scales to millions/sec | High but needs partition tuning |
| **Cost** | Per-message (predictable) | Per-cluster-hour (flat, expensive if underused) |
| **Ecosystem** | GCP native, Dataflow connectors | Broad (Kafka Connect, Kafka Streams, Flink) |

**Choose Pub/Sub when**: Already on GCP, want zero ops, don't need long-term replay, can tolerate ~100ms latency, throughput auto-scaling is important.

**Choose Kafka when**: Need sub-50ms latency, need message replay beyond 7 days, need Kafka Streams or Kafka Connect ecosystem, multi-cloud or on-prem deployment.

---

### 2.5 Cloud Storage — Data Lake Patterns

#### 2.5.1 Storage Classes and Lifecycle

```python
from google.cloud import storage

# Storage classes:
# STANDARD: hot data, frequent access, highest cost
# NEARLINE: infrequent access (< 1x/month), min 30-day storage
# COLDLINE: very infrequent (< 1x/quarter), min 90-day storage
# ARCHIVE: once-a-year access, min 365-day storage, lowest cost

# Set lifecycle policy: auto-transition between classes
def set_lifecycle_policy(bucket_name: str):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    bucket.add_lifecycle_delete_rule(age=365)  # delete after 1 year

    # OR: transition to cheaper classes
    bucket.add_lifecycle_transition_rule(
        age=30,
        storage_class='NEARLINE'     # after 30 days → nearline
    )
    bucket.add_lifecycle_transition_rule(
        age=90,
        storage_class='COLDLINE'     # after 90 days → coldline
    )

    bucket.patch()
```

#### 2.5.2 GCS as Data Lake — Best Practices

```
gs://costco-data-lake/
├── raw/                    # source of truth — never deleted, append-only
│   ├── google_ads/
│   │   ├── year=2024/month=01/day=15/
│   │   │   └── clicks_20240115_001.parquet
│   ├── meta_ads/
│   └── member_events/
│
├── staging/                # cleaned/validated, may be reprocessed
│   ├── ad_clicks/
│   │   └── event_date=2024-01-15/
│   │       └── part-00000.parquet
│   └── campaigns/
│
├── processed/              # final analytics-ready data
│   └── mart_campaign_performance/
│       └── report_date=2024-01-15/
│
└── temp/                   # short-lived intermediate data
    └── pipeline_runs/
        └── run_20240115_060000/
```

**Naming conventions**:
- Use Hive-style partitioning (`key=value/`) for automatic partition detection
- Keep file sizes between 128MB-1GB for optimal Spark/Dataflow reads
- Use Parquet for structured analytical data, Avro for schema-evolution-heavy streaming

---

### 2.6 Dataplex — Data Governance

#### 2.6.1 Dataplex Hierarchy

```
Dataplex Lake (logical)
└── Zone (security boundary)
    ├── Raw Zone: data in native format, minimal curation
    │   └── Asset: links to GCS bucket or BigQuery dataset
    └── Curated Zone: validated, enriched data
        └── Asset: links to processed GCS/BigQuery data
```

#### 2.6.2 Key Features

```python
# 1. Automatic Metadata Discovery
# Dataplex scans GCS buckets and BigQuery datasets automatically
# Discovers: schemas, partitions, data types, row counts
# No code needed — configure scan frequency in Console or API

# 2. Data Quality Rules
from google.cloud import dataplex_v1

# Define quality rules for a BigQuery table
quality_spec = dataplex_v1.DataQualitySpec(
    rules=[
        # Completeness: click_id should never be null
        dataplex_v1.DataQualityRule(
            non_null_expectation=dataplex_v1.DataQualityRule.NonNullExpectation(),
            column="click_id",
            dimension="COMPLETENESS",
            threshold=1.0       # 100% non-null required
        ),
        # Uniqueness: click_id should be unique
        dataplex_v1.DataQualityRule(
            uniqueness_expectation=dataplex_v1.DataQualityRule.UniquenessExpectation(),
            column="click_id",
            dimension="UNIQUENESS",
            threshold=1.0
        ),
        # Range: cost_usd should be non-negative
        dataplex_v1.DataQualityRule(
            range_expectation=dataplex_v1.DataQualityRule.RangeExpectation(
                min_value="0",
                strict_min_enabled=False
            ),
            column="cost_usd",
            dimension="VALIDITY",
            threshold=0.99  # 99% must satisfy (1% tolerance for data issues)
        )
    ]
)

# 3. Data Lineage (auto-tracked for BQ + Dataflow)
# When Dataflow writes to BigQuery, Dataplex automatically records:
# Source: gs://bucket/raw_clicks → Process: Dataflow job → Sink: BQ table
# Visible in Dataplex Console or queryable via Lineage API
```

---

## L3: Real-World Scenarios — Costco/MarTech Style

### 3.1 Scenario: Build a GCP-Native AdTech Ingestion Pipeline

**Requirement**: Ingest Google Ads click data (50M events/day) with < 5 minute latency. Store raw in GCS, transform, load to BigQuery.

**Architecture**:
```
Google Ads API (polling every 5 min)
    → Cloud Function (fetch + publish)
        → Pub/Sub topic: raw-ad-events
            → Dataflow streaming job (parse + validate + transform)
                ├── → BigQuery: streaming.raw_events (real-time)
                └── → GCS: raw/google_ads/YYYY-MM-DD/ (for batch reprocessing)
                        → Cloud Composer DAG (daily DBT run)
                            → BigQuery: marts.campaign_performance
```

```python
# Dataflow streaming pipeline: Pub/Sub → parse → BigQuery + GCS
import apache_beam as beam
from apache_beam.io.gcp.pubsub import ReadFromPubSub
from apache_beam.io.gcp.bigquery import WriteToBigQuery
from apache_beam.io import WriteToText

class ParseAndValidateAdEvent(beam.DoFn):
    def process(self, element):
        import json
        try:
            raw = json.loads(element.decode('utf-8'))
            
            # Validate required fields
            assert raw.get('click_id'), "Missing click_id"
            assert raw.get('campaign_id'), "Missing campaign_id"
            
            normalized = {
                'click_id':      raw['click_id'],
                'campaign_id':   raw['campaign_id'],
                'user_id':       raw.get('user_id'),
                'cost_usd':      raw.get('cost_micros', 0) / 1e6,
                'device_type':   raw.get('device', 'unknown').lower(),
                'clicked_at':    raw['timestamp'],
                'processed_at':  beam.utils.timestamp.Timestamp.now().to_rfc3339()
            }
            yield normalized
        except (AssertionError, KeyError, json.JSONDecodeError) as e:
            yield beam.pvalue.TaggedOutput('errors', {
                'raw': element.decode('utf-8', errors='replace'),
                'error': str(e)
            })

with beam.Pipeline(options=options) as p:
    parsed = (p
        | 'ReadPubSub' >> ReadFromPubSub(
            subscription='projects/costco/subscriptions/ad-clicks-sub')
        | 'ParseValidate' >> beam.ParDo(ParseAndValidateAdEvent())
            .with_outputs('errors', main='valid')
    )

    # Write valid events to BigQuery
    parsed.valid | 'WriteBQ' >> WriteToBigQuery(
        'costco:streaming.raw_ad_clicks',
        schema={
            'fields': [
                {'name': 'click_id', 'type': 'STRING'},
                {'name': 'campaign_id', 'type': 'STRING'},
                {'name': 'cost_usd', 'type': 'FLOAT64'},
                {'name': 'clicked_at', 'type': 'TIMESTAMP'}
            ]
        },
        write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND
    )

    # Write errors to dead-letter GCS for investigation
    parsed.errors | 'WriteErrors' >> WriteToText(
        'gs://costco-data/dead-letter/ad-clicks/'
    )
```

---

### 3.2 Scenario: Build a Lakehouse Architecture on GCP

**Design**:
```
GCS (raw zone)  →  BigQuery (curated zone)  →  BigQuery (mart zone)
  Standard class    Partitioned + Clustered    Pre-aggregated

Governance layer: Dataplex (catalog + lineage + quality)
Orchestration:    Cloud Composer (DAG scheduling)
Transformation:   DBT (SQL-based, lineage, tests)
BI:               Looker (connected to BigQuery marts)
```

**Cost optimization**:
- Raw data in GCS Standard (hot) for 30 days, then NEARLINE
- BigQuery: raw tables use STANDARD storage, old partitions expire after 90 days
- BigQuery: mart tables kept forever (they're small aggregations)
- Compute: Dataflow autoscaling, Dataproc preemptible workers

---

## L4: Hands-On Design & Code

### 4.1 Write a BigQuery Optimization Query

```sql
-- Table: raw.ad_clicks (10B rows, partitioned by click_date, clustered by campaign_id)
-- Requirement: daily campaign ROAS for last 30 days, under 10 seconds

-- Step 1: Ensure partition filter present
-- Step 2: Select only needed columns
-- Step 3: Use SAFE_DIVIDE for null safety

SELECT
    click_date                              AS report_date,
    campaign_id,
    COUNT(*)                                AS clicks,
    SUM(cost_usd)                           AS spend_usd,
    SAFE_DIVIDE(SUM(revenue_usd), SUM(cost_usd)) AS roas
FROM (
    -- Subquery gets only necessary columns from raw table
    SELECT
        click_date,
        campaign_id,
        cost_usd,
        revenue_usd
    FROM `raw.ad_clicks`
    WHERE click_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)  -- partition filter
      AND click_date < CURRENT_DATE()
)
GROUP BY 1, 2
ORDER BY report_date DESC, roas ASC;
```

---

## L5: Edge Cases & Pitfalls

### 5.1 Dataflow: Hot Key Problem in Streaming

```python
# Problem: all events with campaign_id='VIRAL_CAMPAIGN' go to same worker
# That worker becomes the bottleneck; all others are idle

# Symptom: Dataflow UI shows one worker at 100% CPU, others at 10%

# Fix: Use combiner (partial aggregation) to reduce data before grouping
class SumCombineFn(beam.CombineFn):
    def create_accumulator(self): return 0.0
    def add_input(self, acc, element): return acc + element
    def merge_accumulators(self, accs): return sum(accs)
    def extract_output(self, acc): return acc

(events
    | 'ExtractSpend' >> beam.Map(lambda e: (e['campaign_id'], e['cost_usd']))
    | 'SumSpend' >> beam.CombinePerKey(SumCombineFn())
    # CombinePerKey uses partial aggregation at each worker before shuffle
    # Reduces data volume at the hot key
)
```

### 5.2 BigQuery: Streaming Buffer Not Queryable for DML

```sql
-- BQ Streaming Insert data is in a "streaming buffer"
-- It's queryable immediately, but NOT available for:
-- - Table copy
-- - Table export
-- - CREATE TABLE AS SELECT from the streaming buffer rows
-- - Certain partition management operations

-- Solution: use Storage Write API with COMMITTED mode for immediate DML compatibility
-- OR: wait for streaming buffer to be committed (usually within minutes)

-- Check if data is still in streaming buffer:
SELECT * FROM `project.dataset.table` 
WHERE _PARTITIONTIME IS NULL;  -- streaming buffer rows have NULL _PARTITIONTIME
```

### 5.3 Pub/Sub: Message Ordering and Duplicates

```python
# Pub/Sub does NOT guarantee ordering by default
# Messages published at T1, T2, T3 may arrive at subscriber in any order

# For ordering: use ordering keys (same key → same partition → ordered delivery)
publisher.publish(
    topic_path,
    data=data,
    ordering_key=campaign_id    # messages with same key are ordered
)

# But: ordering key means single-partition for that key → throughput limit
# For most analytical use cases: don't rely on ordering, use event_timestamp in message

# Pub/Sub guarantees: at-least-once delivery
# Duplicates ARE possible (subscriber crash before ack → redelivery)
# Solution: idempotent consumer (dedup on message_id or business key)
```

---

## L6: Interview Questions — Easy to Very Hard

### EASY

**Q1: What is the difference between Dataflow and Dataproc?**

**Answer**: Both are GCP services for data processing, but they differ fundamentally. Dataflow is a fully managed, serverless service that runs Apache Beam pipelines. You write code using the Beam API, submit the job, and Dataflow handles all infrastructure — worker provisioning, scaling, and shutdown. It's best for new streaming and ETL pipelines where you want zero infrastructure management.

Dataproc is a managed Spark and Hadoop cluster service. You provision a cluster (choose machine types, worker count), submit jobs to it (PySpark, SparkR, Hive), and pay by the hour. It's best for existing Spark codebases, ML training with Spark ML, or workloads that don't fit the Beam model.

Key practical difference: Dataflow scales automatically; Dataproc requires you to configure autoscaling or manually size the cluster. Dataflow is per-job serverless; Dataproc charges for cluster uptime even when idle.

---

**Q2: What is Pub/Sub and what problem does it solve?**

**Answer**: Cloud Pub/Sub is a fully managed message queue (publish-subscribe messaging service). It solves the problem of decoupling data producers from data consumers. Without Pub/Sub, if your ad tracking system directly writes to BigQuery and BigQuery is slow or down, clicks are lost. With Pub/Sub, the tracker publishes to a topic (fast, always available), and the downstream consumer (Dataflow, BigQuery, Cloud Function) reads from the subscription independently.

Key properties: at-least-once delivery, 7-day message retention, auto-scales to millions of messages/second, serverless. It's typically used as the entry point for real-time event pipelines: clickstream events, IoT sensor data, ad events → Pub/Sub → Dataflow → BigQuery.

---

### MEDIUM

**Q3: When would you choose BigQuery over Cloud Spanner for a data storage use case?**

**Answer**: BigQuery is an analytical data warehouse (OLAP) — optimized for large-scale analytical queries, aggregations, and scans. It's not designed for transactional, low-latency reads/writes.

Cloud Spanner is a globally distributed relational database (OLTP) — designed for transactional consistency, millisecond reads/writes, and high concurrency.

Choose BigQuery for: historical analytics, reporting, ML training data, dashboards, batch transformations. Query latency: seconds to minutes. Not suitable for individual row lookups.

Choose Cloud Spanner for: operational databases, real-time inventory, financial transactions, any use case needing ACID transactions, sub-10ms read latency, or high-concurrency writes.

In a typical data stack: Spanner stores the operational data (source of truth), and a CDC pipeline replicates it to BigQuery for analytics. They serve different purposes.

---

**Q4: Explain the Apache Beam programming model. How does it abstract batch and streaming?**

**Answer**: Beam's core abstraction is the Pipeline, which processes PCollections through PTransforms. A PCollection is a distributed, immutable dataset — it could represent a finite batch of rows from a file OR an unbounded stream of events from Pub/Sub. The same transforms (Map, Filter, GroupBy, Combine) work on both.

The abstraction works because Beam treats time as first-class. For bounded (batch) data, there's a clear start and end. For unbounded (streaming) data, Beam introduces windowing (FixedWindows, SlidingWindows, Sessions) to create finite buckets from the infinite stream. The aggregation logic is identical — you write `CombinePerKey(sum)` and it works whether the data is a GCS file or a Pub/Sub stream.

The runner (Dataflow, Spark, Flink) executes the pipeline on actual infrastructure. You write once in Beam, and the same code can run as a batch job today and a streaming job tomorrow by swapping the source and enabling windowing.

---

### HARD

**Q5: You have a Dataflow streaming pipeline processing 500K messages/second from Pub/Sub. Latency has increased from 2 seconds to 45 seconds over the past week despite stable message volume. How do you diagnose and fix this?**

**What they're testing**: Dataflow operational knowledge, bottleneck analysis.

**Answer**:

**Step 1: Check Dataflow Monitoring**
- Dataflow Console → Job metrics → "System Lag" (time between message publish and process)
- "Data freshness" (how old is the oldest unprocessed message)
- Worker CPU utilization — are workers maxed out?
- Backlog: is the Pub/Sub subscription backlog growing?

**Step 2: Common causes**

1. **Downstream sink is slow**: If writing to BigQuery and BQ is throttling or slow, Dataflow backs up. Check BigQuery streaming insert quotas (default: 1GB/sec per table). Solution: increase quota or use Storage Write API.

2. **GC pressure on workers**: Memory-intensive transforms (large state, large window buffers) trigger frequent GC. Solution: increase worker memory (`--machine_type=n1-highmem-4`), enable Streaming Engine (offloads state).

3. **Hot key / data skew**: One campaign_id in 80% of messages → one worker handles 80% of load. Solution: use `CombinePerKey` with partial aggregation or use a composite key.

4. **State backend overloaded**: For stateful processing (sessions, dedup), state backend can become a bottleneck. Solution: enable Streaming Engine.

5. **Worker count not scaling fast enough**: Autoscaler lags 5-10 minutes. Solution: increase `--min_num_workers` baseline.

**Immediate fix**: Enable Streaming Engine + increase max workers:
```python
'--enable_streaming_engine',
'--max_num_workers=100',
'--min_num_workers=10'
```

**Root cause fix**: Identify the slow transform using step-level latency in Dataflow UI, then address that specific bottleneck.

---

**Q6: Design a cost-efficient GCP architecture for ingesting and analyzing 100M ad events per day, with these requirements: real-time dashboard (< 5 min latency), daily authoritative report (T+1 day), < $5,000/month total GCP cost.**

**What they're testing**: Cost-aware architecture design, GCP service selection.

**Answer**:

**Real-time path (< 5 min latency)**:
- Ad events → Pub/Sub → Dataflow Streaming → BigQuery Streaming Insert
- Dataflow: 5-10 workers × n1-standard-4, autoscaling
- Cost: ~$200/month (Dataflow) + ~$50/month (Pub/Sub) + ~$100/month (BQ streaming insert)

**Daily authoritative path (T+1)**:
- Raw events land in GCS via Dataflow (write to GCS sink alongside BQ streaming)
- Dataproc Serverless job: deduplicate + transform → BigQuery mart tables
- Run time: ~30 min/day
- Cost: ~$50/month (Dataproc serverless) + $0 (GCS ingestion via Dataflow already running)

**BigQuery Storage**:
- 100M events × 500 bytes = 50GB/day raw
- 90 days retention → 4.5TB storage → $90/month
- Mart tables: aggregated, much smaller → $5/month
- Query cost: if partition-filtered, 5TB/month scanned → $31.25/month

**GCS**:
- Raw: 30 days × 50GB = 1.5TB → $30/month STANDARD
- After 30 days → NEARLINE: 60 days × 50GB = 3TB → $30/month NEARLINE

**Total estimate**: ~$586/month — well under $5,000.

**Cost levers if over budget**:
1. Use Dataproc preemptible workers (80% cheaper) for the daily job
2. Reduce BigQuery streaming inserts (write to GCS only, use batch load job every 5 min to BQ — cheaper than streaming insert)
3. Partition expiry on raw BQ tables (90 days)

---

### VERY HARD

**Q7: Design a multi-region, fault-tolerant GCP data platform for Costco MarTech. Requirements: US and EU regions (data residency), 99.9% pipeline availability, zero data loss, < 1 hour RTO (recovery time objective).**

**What they're testing**: Enterprise-grade architecture, multi-region design, GCP advanced features.

**Answer**:

**Data residency requirements**:
- US member data: BigQuery datasets in `us` multi-region (never leaves US)
- EU member data: BigQuery datasets in `eu` multi-region (GDPR compliance)
- Ad performance data (non-PII): can be in either region

**Multi-region architecture**:

```
US Region                           EU Region
─────────────────────────────       ─────────────────────────────
Pub/Sub topic (us-central1)         Pub/Sub topic (europe-west1)
  ↓                                   ↓
Dataflow (us-central1)              Dataflow (europe-west1)
  ↓                                   ↓
GCS bucket (us multi-region)        GCS bucket (eu multi-region)
  ↓                                   ↓
BigQuery dataset (us)               BigQuery dataset (eu)
  ↓                                   ↓
              ↓           ↓
       Shared mart      Cross-region
       (aggregated,     BigQuery Transfer
       non-PII only)    (aggregated only)
```

**Fault tolerance mechanisms**:

1. **Pub/Sub redundancy**: Pub/Sub is globally replicated by Google — single topic with cross-region delivery. If us-central1 has issues, messages route to backup replicas.

2. **Dataflow failure recovery**: Dataflow checkpoints state to GCS every few seconds. On worker failure, job restarts from last checkpoint (no data loss, at-most 10 seconds replayed). Set `--max_num_workers` high enough that worker loss doesn't stop progress.

3. **BigQuery**: Multi-region datasets (us, eu) are replicated across multiple data centers within the region automatically. SLA: 99.99% monthly uptime.

4. **GCS**: Multi-region buckets replicate across 2+ data centers. Object writes are durable once confirmed.

5. **Cloud Composer (Airflow)**: Use multi-zone deployment. Set `--retry=3` on all tasks. Store DAG state in Cloud SQL (HA instance).

**RTO of < 1 hour**:
- Pub/Sub buffers messages for 7 days → no data loss during outage
- Dataflow restarts automatically (typically < 5 minutes) from checkpoint
- BigQuery is always available (Google SLA)
- Composer DAG retries failed tasks automatically
- If entire region fails: Pub/Sub routes to backup; deploy Dataflow job in backup region (< 10 min with Terraform)

**IaC for fast recovery**:
```hcl
# Terraform: entire Dataflow job definition as code
# Recovery = terraform apply → 5 min to redeploy in new region
resource "google_dataflow_flex_template_job" "ad_events" {
  provider                = google-beta
  name                    = "ad-events-pipeline"
  container_spec_gcs_path = "gs://costco-templates/ad-events-pipeline.json"
  region                  = var.region  # changeable variable
}
```

---

## Summary: GCP Data Engineering Stack — Senior Mastery Checklist

| Service | What Senior Knows |
|---------|------------------|
| BigQuery | Dremel architecture, slot model, partition pruning mechanics, clustering block pruning, Storage Write API |
| Dataflow | Beam model, windowing (fixed/sliding/session), watermarks, autoscaling, hot key fix |
| Dataproc | vs Dataflow decision, serverless mode, cluster config, preemptible workers |
| Pub/Sub | At-least-once semantics, ordering keys, vs Kafka trade-offs, flow control |
| Cloud Storage | Storage classes, lifecycle policies, Hive-style partitioning, file format choice |
| Dataplex | Lake/zone/asset hierarchy, quality rules, automatic lineage |
| Architecture | Can design multi-service pipelines with cost estimates and trade-off reasoning |
