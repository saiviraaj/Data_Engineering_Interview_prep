# Topic 7: GCP Data Services — Dataflow, Dataproc, Pub/Sub, Dataplex

> **Textbook Reference — Costco Sr. Data Engineer Interview Prep**
> Exhaustive deep dive into the four core GCP data processing services. Covers architecture, internals, configuration, code patterns, tuning, and MarTech/AdTech use cases.

---

## Table of Contents
1. Cloud Dataflow — Apache Beam on GCP
2. Apache Beam Programming Model
3. Dataflow Streaming Patterns
4. Dataflow Performance & Tuning
5. Cloud Dataproc — Managed Spark/Hadoop
6. Dataproc Architecture & Configuration
7. Dataproc vs Dataflow Decision Framework
8. Cloud Pub/Sub — Messaging & Event Streaming
9. Pub/Sub Advanced Patterns
10. Cloud Dataplex — Data Mesh & Governance
11. Dataplex Data Quality & Discovery
12. Integration Patterns Across Services
13. MarTech/AdTech Pipeline Architectures
14. Interview Q&A Bank

---

## 1. Cloud Dataflow — Apache Beam on GCP

### What Dataflow Is
Dataflow is a **fully managed, serverless stream and batch data processing service** built on Apache Beam. Unlike Dataproc (where you manage a cluster), Dataflow auto-provisions, auto-scales, and auto-manages the underlying infrastructure.

**Key differentiators:**
- **Unified model**: Same pipeline code runs in batch or streaming mode — just change the runner
- **Auto-scaling**: Workers scale up/down dynamically based on backlog and throughput
- **No cluster management**: No VMs to size, patch, or monitor
- **Exactly-once processing**: Dataflow Streaming guarantees exactly-once semantics

### Dataflow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Dataflow Job                            │
│                                                             │
│  ┌─────────┐    ┌───────────┐    ┌──────────┐             │
│  │ Source  │───▶│ Transform │───▶│  Sink    │             │
│  │(PRead)  │    │(PTransform│    │ (PWrite) │             │
│  └─────────┘    └───────────┘    └──────────┘             │
│                                                             │
│  Dataflow Service (Job Manager)                            │
│  ├── Optimizer (Fusion, Work stealing)                     │
│  ├── Scheduler (Work item distribution)                    │
│  └── Monitoring (Metrics, Logging, Alerts)                 │
│                                                             │
│  Workers (auto-provisioned GCE VMs)                        │
│  ├── Worker 1 (processes data bundles)                     │
│  ├── Worker 2 (processes data bundles)                     │
│  └── Worker N (scales up/down)                             │
└─────────────────────────────────────────────────────────────┘
```

**Component definitions:**
- **PCollection**: Immutable, potentially unbounded dataset — Beam's core data abstraction
- **PTransform**: Transformation applied to a PCollection, produces another PCollection
- **Pipeline**: DAG of PCollections and PTransforms
- **Runner**: Execution engine — Dataflow runner executes on Google Cloud
- **Fusion**: Dataflow optimizer combines multiple transforms into a single stage to avoid serialization overhead

### Dataflow Execution Model

**Bundle processing:**
1. Job graph is submitted to Dataflow service
2. Service decomposes the pipeline into stages
3. Each stage is split into work items (bundles of data)
4. Workers claim bundles, process them, checkpoint progress
5. Failed bundles are retried on other workers — fault tolerance built in

**Work stealing:**
When one worker finishes faster, it can steal unbounded work items from other workers' queues. This prevents stragglers from slowing the entire job.

**Liquid sharding (streaming):**
In streaming mode, Dataflow dynamically splits and merges key ranges based on throughput — prevents hot partitions.

---

## 2. Apache Beam Programming Model

### Core Concepts in Code

```python
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, GoogleCloudOptions
from apache_beam.io.gcp.bigquery import WriteToBigQuery, ReadFromBigQuery
from apache_beam.io.gcp.pubsub import ReadFromPubSub, WriteToPubSub
from apache_beam.transforms.window import FixedWindows, SlidingWindows, Sessions
from apache_beam.transforms.trigger import AfterWatermark, AfterProcessingTime, AccumulationMode
import json
from datetime import datetime

# --- Pipeline Options ---
options = PipelineOptions()
google_cloud_options = options.view_as(GoogleCloudOptions)
google_cloud_options.project = 'costco-martech-prod'
google_cloud_options.region = 'us-central1'
google_cloud_options.staging_location = 'gs://costco-dataflow/staging'
google_cloud_options.temp_location = 'gs://costco-dataflow/temp'
google_cloud_options.job_name = 'ad-event-processing'

from apache_beam.options.pipeline_options import StandardOptions, WorkerOptions
options.view_as(StandardOptions).runner = 'DataflowRunner'
options.view_as(StandardOptions).streaming = True  # for streaming jobs

worker_options = options.view_as(WorkerOptions)
worker_options.num_workers = 10
worker_options.max_num_workers = 100
worker_options.machine_type = 'n1-standard-4'
worker_options.disk_size_gb = 100
worker_options.autoscaling_algorithm = 'THROUGHPUT_BASED'
```

### DoFn — The Core Transform Unit

```python
# DoFn is the unit of user logic
class ParseAdEventDoFn(beam.DoFn):
    """Parse raw Pub/Sub message bytes into structured AdEvent dicts."""
    
    def setup(self):
        """Called once per worker — use for expensive initialization (DB connections, ML models)."""
        import redis
        self.redis_client = redis.Redis(host='redis-host', port=6379)
    
    def process(self, element, timestamp=beam.DoFn.TimestampParam, window=beam.DoFn.WindowParam):
        """
        Called for each element.
        element: PubsubMessage or raw bytes
        timestamp: event timestamp (DoFn.TimestampParam injects it automatically)
        window: current window (DoFn.WindowParam injects it)
        """
        try:
            # Parse the message
            msg = json.loads(element.decode('utf-8'))
            
            # Enrich with lookup
            user_segment = self.redis_client.get(f"segment:{msg['user_id']}")
            
            yield {
                'event_id': msg['event_id'],
                'user_id': msg['user_id'],
                'campaign_id': msg['campaign_id'],
                'event_type': msg['event_type'],  # impression, click, conversion
                'timestamp': msg['timestamp'],
                'revenue': float(msg.get('revenue', 0.0)),
                'user_segment': user_segment.decode() if user_segment else 'unknown',
                'processing_timestamp': datetime.utcnow().isoformat()
            }
        except (json.JSONDecodeError, KeyError) as e:
            # Tag bad records for dead-letter queue
            yield beam.pvalue.TaggedOutput('dead_letter', {
                'raw_message': element.decode('utf-8', errors='replace'),
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
    
    def teardown(self):
        """Called once per worker on shutdown — clean up resources."""
        self.redis_client.close()


# ParDo = Parallel Do — applies a DoFn to each element
class EnrichWithGeolocationDoFn(beam.DoFn):
    def setup(self):
        import geoip2.database
        self.reader = geoip2.database.Reader('/path/to/GeoLite2-City.mmdb')
    
    def process(self, element):
        ip = element.get('ip_address')
        if ip:
            try:
                response = self.reader.city(ip)
                element['country'] = response.country.iso_code
                element['city'] = response.city.name
                element['dma'] = response.subdivisions.most_specific.name
            except Exception:
                element['country'] = 'unknown'
                element['city'] = 'unknown'
                element['dma'] = 'unknown'
        yield element
```

### Composite Transforms — Reusable Pipeline Components

```python
class ParseAndEnrichAdEvent(beam.PTransform):
    """
    Composite transform: parse + validate + enrich ad events.
    Returns a tuple of (valid_events, dead_letters).
    """
    
    def expand(self, pcollection):
        # Step 1: Parse
        parsed = (
            pcollection
            | 'Parse JSON' >> beam.ParDo(ParseAdEventDoFn()).with_outputs(
                'dead_letter', main='valid'
            )
        )
        
        # Step 2: Filter
        valid_events = (
            parsed.valid
            | 'Filter Test Events' >> beam.Filter(
                lambda e: not e['campaign_id'].startswith('TEST_')
            )
        )
        
        # Step 3: Enrich
        enriched = (
            valid_events
            | 'Enrich Geolocation' >> beam.ParDo(EnrichWithGeolocationDoFn())
        )
        
        return enriched, parsed.dead_letter


# Usage in pipeline
with beam.Pipeline(options=options) as p:
    messages = (
        p
        | 'Read Pub/Sub' >> ReadFromPubSub(
            subscription='projects/costco-martech-prod/subscriptions/ad-events-sub',
            with_attributes=True,
            timestamp_attribute='event_timestamp'  # use event time, not arrival time
        )
    )
    
    enriched_events, dead_letters = (
        messages
        | 'Parse and Enrich' >> ParseAndEnrichAdEvent()
    )
    
    # Write dead letters to BigQuery for investigation
    dead_letters | 'Write Dead Letters' >> WriteToBigQuery(
        table='costco-martech-prod:monitoring.ad_event_dead_letters',
        schema='raw_message:STRING,error:STRING,timestamp:TIMESTAMP',
        write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND
    )
```

### Branch & Merge Pipelines

```python
# Fan-out: one PCollection → multiple outputs
with beam.Pipeline(options=options) as p:
    events = p | 'Read' >> ReadFromPubSub(topic='...')
    
    # Split by event type
    impressions = events | 'Filter Impressions' >> beam.Filter(
        lambda e: e['event_type'] == 'impression'
    )
    clicks = events | 'Filter Clicks' >> beam.Filter(
        lambda e: e['event_type'] == 'click'
    )
    conversions = events | 'Filter Conversions' >> beam.Filter(
        lambda e: e['event_type'] == 'conversion'
    )
    
    # Each branch written to separate tables
    impressions | 'Write Impressions' >> WriteToBigQuery('...impressions')
    clicks      | 'Write Clicks'      >> WriteToBigQuery('...clicks')
    conversions | 'Write Conversions' >> WriteToBigQuery('...conversions')
    
    # Fan-in: merge multiple PCollections
    all_events = (impressions, clicks, conversions) | 'Flatten' >> beam.Flatten()
    all_events | 'Write All Events' >> WriteToBigQuery('...all_events')
```

---

## 3. Dataflow Streaming Patterns

### Windowing — Core Concept

In streaming, data arrives continuously. **Windows** group elements by time so you can compute aggregations over bounded time slices.

```
Event time vs Processing time:

Event time:       [10:00]  [10:01]  [10:02]  [10:03]  [10:04]
                    |        |        |        |        |
                   e1       e2       e3       e4       e5

Processing time:           [10:01] [10:03]           [10:06]
(when we receive)            e1,e2    e3                e4,e5
                                                (e4 arrived 2 min late)

Watermark: "I believe all events up to time T have arrived"
Late data: events arriving after the watermark
```

```python
from apache_beam import window
from apache_beam.transforms.trigger import (
    AfterWatermark, AfterProcessingTime, AfterCount, Repeatedly, AccumulationMode
)

# Fixed Windows: non-overlapping, fixed-size time intervals
fixed_windowed = (
    enriched_events
    | 'Fixed 5min Windows' >> beam.WindowInto(
        window.FixedWindows(5 * 60),  # 5-minute windows
        trigger=AfterWatermark(
            late=Repeatedly(AfterCount(1))  # emit result, then emit again for each late element
        ),
        allowed_lateness=3600,  # accept data up to 1 hour late
        accumulation_mode=AccumulationMode.ACCUMULATING  # accumulate late arrivals into window
    )
)

# Sliding Windows: overlapping windows (for rolling metrics)
# sliding_size=1 minute, window_period=15 seconds → lots of overlap, good for real-time dashboards
sliding_windowed = (
    enriched_events
    | 'Sliding 1min Windows' >> beam.WindowInto(
        window.SlidingWindows(
            size=60,      # 1-minute window
            period=15     # new window every 15 seconds
        )
    )
)

# Session Windows: gap-based grouping (user sessions)
session_windowed = (
    enriched_events
    | 'Session Windows' >> beam.WindowInto(
        window.Sessions(gap_size=30 * 60)  # 30-minute inactivity = new session
    )
)

# Global Window with periodic triggers (no time-based windowing, just trigger-based emission)
global_windowed = (
    enriched_events
    | 'Global Window' >> beam.WindowInto(
        window.GlobalWindows(),
        trigger=Repeatedly(AfterProcessingTime(60)),  # emit every 60s of processing time
        accumulation_mode=AccumulationMode.DISCARDING  # discard after each emission
    )
)
```

### Aggregations in Windowed Streams

```python
# Count clicks per campaign per 5-minute window
campaign_click_counts = (
    enriched_events
    | 'Window 5min' >> beam.WindowInto(window.FixedWindows(300))
    | 'Filter Clicks' >> beam.Filter(lambda e: e['event_type'] == 'click')
    | 'Key by Campaign' >> beam.Map(lambda e: (e['campaign_id'], 1))
    | 'Count per Campaign' >> beam.CombinePerKey(sum)
    | 'Format for BQ' >> beam.Map(lambda kv: {
        'campaign_id': kv[0],
        'click_count': kv[1]
    })
)

# Sum revenue per campaign per window using CombineFn
class SumRevenueCombineFn(beam.CombineFn):
    def create_accumulator(self):
        return {'revenue': 0.0, 'count': 0}
    
    def add_input(self, accumulator, element):
        return {
            'revenue': accumulator['revenue'] + element.get('revenue', 0.0),
            'count': accumulator['count'] + 1
        }
    
    def merge_accumulators(self, accumulators):
        merged = {'revenue': 0.0, 'count': 0}
        for acc in accumulators:
            merged['revenue'] += acc['revenue']
            merged['count'] += acc['count']
        return merged
    
    def extract_output(self, accumulator):
        return accumulator

campaign_revenue = (
    enriched_events
    | 'Key by Campaign for Revenue' >> beam.Map(lambda e: (e['campaign_id'], e))
    | 'Combine Revenue' >> beam.CombinePerKey(SumRevenueCombineFn())
)
```

### Stateful Processing — Per-Key State

```python
import apache_beam as beam
from apache_beam.transforms.userstate import BagStateSpec, CombiningValueStateSpec, TimerSpec, on_timer
from apache_beam.coders import VarIntCoder
from apache_beam.transforms.timeutil import TimeDomain

class SessionizerDoFn(beam.DoFn):
    """
    Stateful DoFn: tracks user session state.
    Emits a complete session record when a timer fires (session ends).
    """
    
    # State: accumulate events in a bag
    EVENTS_STATE = BagStateSpec('events', beam.coders.FastPrimitivesCoder())
    # State: total click count
    CLICK_COUNT_STATE = CombiningValueStateSpec('click_count', sum)
    # Timer: fires when session is idle for 30 minutes
    SESSION_END_TIMER = TimerSpec('session_end', TimeDomain.WATERMARK)
    
    def process(
        self,
        element,
        events=beam.DoFn.StateParam(EVENTS_STATE),
        click_count=beam.DoFn.StateParam(CLICK_COUNT_STATE),
        session_end_timer=beam.DoFn.TimerParam(SESSION_END_TIMER),
        timestamp=beam.DoFn.TimestampParam
    ):
        user_id, event = element
        
        # Accumulate event in state
        events.add(event)
        
        if event['event_type'] == 'click':
            click_count.add(1)
        
        # Set/extend the session end timer by 30 minutes from now
        session_end_timer.set(timestamp + 1800)
    
    @on_timer(SESSION_END_TIMER)
    def on_session_end(
        self,
        events=beam.DoFn.StateParam(EVENTS_STATE),
        click_count=beam.DoFn.StateParam(CLICK_COUNT_STATE)
    ):
        event_list = list(events.read())
        if event_list:
            yield {
                'user_id': event_list[0]['user_id'],
                'session_start': min(e['timestamp'] for e in event_list),
                'session_end': max(e['timestamp'] for e in event_list),
                'total_events': len(event_list),
                'total_clicks': click_count.read(),
                'campaigns_touched': list(set(e['campaign_id'] for e in event_list))
            }
        
        # Clear state after emission
        events.clear()
        click_count.clear()
```

---

## 4. Dataflow Performance & Tuning

### Key Performance Parameters

```python
from apache_beam.options.pipeline_options import WorkerOptions, SetupOptions

worker_options = options.view_as(WorkerOptions)

# Worker sizing
worker_options.num_workers = 5                    # initial workers
worker_options.max_num_workers = 200              # autoscaling ceiling
worker_options.machine_type = 'n1-standard-8'    # 8 vCPU, 30GB RAM
worker_options.disk_size_gb = 250                 # persistent disk per worker

# For memory-intensive jobs (large shuffles):
worker_options.machine_type = 'n1-highmem-8'     # 8 vCPU, 52GB RAM

# Use Dataflow Shuffle (server-side) for batch jobs
# Add to pipeline options:
# --experiments=use_runner_v2
# --experiments=shuffle_mode=appliance

# Use Streaming Engine for streaming jobs
# --enable_streaming_engine
# This moves windowing/state to Dataflow managed service instead of worker memory

setup_options = options.view_as(SetupOptions)
setup_options.requirements_file = 'requirements.txt'  # Python deps
setup_options.setup_file = './setup.py'               # custom packages
```

### Fusion Optimization

**Fusion** is Dataflow's key optimization: it combines multiple adjacent transforms into a single fused stage, executed as a single unit without intermediate serialization.

```
Without Fusion:
ParDo(ParseJSON) → serialize → ParDo(FilterTest) → serialize → ParDo(Enrich)

With Fusion:
[ParseJSON + FilterTest + Enrich] → all in memory, single pass per element
```

**Fusion breaking** — sometimes you WANT to prevent fusion:
- Before a GroupByKey (shuffle) — you want parallelism, not one big stage
- After a resource-heavy DoFn — separate stages allow independent autoscaling

```python
# Force fusion break by inserting a Reshuffle
from apache_beam.transforms.util import Reshuffle

pipeline = (
    input_pcollection
    | 'Heavy CPU Transform' >> beam.ParDo(HeavyMLTransform())
    | 'Reshuffle (fusion break)' >> Reshuffle()  # breaks fusion here
    | 'Next Transform' >> beam.ParDo(NextTransform())
)
```

### Handling Hot Keys (Data Skew)

```python
# Problem: one campaign_id has 90% of traffic
# GroupByKey on campaign_id → one worker gets 90% of work

# Solution: Add a random suffix to spread load, then combine
import random

def add_random_suffix(element, num_shards=100):
    key, value = element
    shard = random.randint(0, num_shards - 1)
    return (f"{key}_{shard}", value)

def remove_suffix(element):
    key_with_suffix, value = element
    original_key = '_'.join(key_with_suffix.split('_')[:-1])
    return (original_key, value)

class SumCombineFn(beam.CombineFn):
    def create_accumulator(self): return 0
    def add_input(self, acc, input): return acc + input
    def merge_accumulators(self, accs): return sum(accs)
    def extract_output(self, acc): return acc

result = (
    events
    | 'Key by Campaign' >> beam.Map(lambda e: (e['campaign_id'], e['revenue']))
    | 'Add Shard Suffix' >> beam.Map(add_random_suffix)
    | 'Partial Aggregate' >> beam.CombinePerKey(SumCombineFn())  # spread across 100 shards
    | 'Remove Suffix' >> beam.Map(remove_suffix)
    | 'Final Aggregate' >> beam.CombinePerKey(SumCombineFn())    # final merge per campaign
)
```

### Side Inputs — Broadcast Lookup Tables

```python
# Load a small lookup table and broadcast to all workers
campaign_metadata = (
    p
    | 'Read Campaign Metadata' >> ReadFromBigQuery(
        query='SELECT campaign_id, campaign_name, budget FROM campaigns.metadata',
        use_standard_sql=True
    )
    | 'Index by ID' >> beam.Map(lambda row: (row['campaign_id'], row))
)

# Convert to AsDict for O(1) lookup in DoFn
campaign_dict = beam.pvalue.AsDict(campaign_metadata)

class EnrichWithCampaignMetadataDoFn(beam.DoFn):
    def process(self, element, campaign_map):
        campaign_id = element['campaign_id']
        metadata = campaign_map.get(campaign_id, {})
        element['campaign_name'] = metadata.get('campaign_name', 'Unknown')
        element['budget'] = metadata.get('budget', 0)
        yield element

enriched = (
    events
    | 'Enrich Campaign Metadata' >> beam.ParDo(
        EnrichWithCampaignMetadataDoFn(),
        campaign_map=campaign_dict  # side input — broadcast to all workers
    )
)
```

---

## 5. Cloud Dataproc — Managed Spark/Hadoop

### What Dataproc Is
Dataproc is a **fully managed service** for running Apache Spark, Hadoop, Hive, Presto, Flink, and other open-source data processing frameworks on GCP. Unlike Dataflow (fully serverless), Dataproc requires you to provision clusters — but provides full control over the Spark configuration.

**When to choose Dataproc over Dataflow:**
- Existing Spark/PySpark codebase that you want to lift-and-shift
- Complex Spark operations (GraphX, Spark MLlib, custom SparkSQL UDFs)
- Need for Spark shell / interactive notebooks (Jupyter)
- Hive metastore and SQL-on-Hadoop workloads
- Hadoop workloads (MapReduce, HDFS-based pipelines)
- Custom libraries not available in Beam SDK

---

## 6. Dataproc Architecture & Configuration

### Cluster Types

```
Standard Cluster:
├── 1 Master Node (NameNode, YARN ResourceManager, Spark Driver)
│   └── n1-standard-4 recommended
├── N Worker Nodes (DataNode, NodeManager, Spark Executors)
│   └── n1-standard-8 or n1-highmem-8 for memory-heavy jobs
└── M Preemptible Workers (cheap, can be reclaimed by GCP → good for fault-tolerant batch)

High Availability Cluster:
├── 3 Master Nodes (Zookeeper quorum, YARN HA)
└── N Worker Nodes
→ Use for production jobs where master failure is unacceptable

Dataproc Serverless (no cluster to manage):
└── Submit PySpark directly, no cluster provisioning
→ Best for ad-hoc / infrequent jobs
```

### Creating a Cluster via gcloud

```bash
# Standard production cluster
gcloud dataproc clusters create costco-etl-cluster \
  --project=costco-martech-prod \
  --region=us-central1 \
  --zone=us-central1-a \
  --master-machine-type=n1-standard-8 \
  --master-boot-disk-size=500 \
  --num-workers=10 \
  --worker-machine-type=n1-highmem-16 \
  --worker-boot-disk-size=500 \
  --num-preemptible-workers=20 \
  --image-version=2.1-debian11 \
  --properties="spark:spark.executor.memory=12g,spark:spark.executor.cores=4,spark:spark.sql.adaptive.enabled=true" \
  --initialization-actions=gs://costco-dataproc/init/install_deps.sh \
  --metadata="PIP_PACKAGES=great-expectations==0.18.0 dbt-bigquery==1.7.0" \
  --enable-component-gateway \  # enables Jupyter, Spark UI via browser
  --optional-components=JUPYTER \
  --autoscaling-policy=costco-autoscaling-policy \
  --max-idle=30m  # delete cluster if idle > 30 min (cost saving)

# Autoscaling policy
gcloud dataproc autoscaling-policies create costco-autoscaling-policy \
  --project=costco-martech-prod \
  --region=us-central1 \
  --basic-algorithm-cooldown-duration=2m \
  --basic-algorithm-yarn-config-scale-up-factor=1.0 \
  --basic-algorithm-yarn-config-scale-down-factor=1.0 \
  --basic-algorithm-yarn-config-scale-up-min-worker-fraction=0.0 \
  --basic-algorithm-yarn-config-scale-down-min-worker-fraction=0.0 \
  --min-instances=2 \
  --max-instances=50
```

### Submitting Jobs

```bash
# Submit PySpark job
gcloud dataproc jobs submit pyspark gs://costco-martech/scripts/campaign_etl.py \
  --cluster=costco-etl-cluster \
  --region=us-central1 \
  --py-files=gs://costco-martech/libs/common_utils.zip \
  --properties="spark.executor.memory=12g,spark.executor.cores=4,spark.sql.shuffle.partitions=400" \
  -- \
  --date=2024-01-15 \
  --env=prod

# Submit Spark SQL job
gcloud dataproc jobs submit spark \
  --cluster=costco-etl-cluster \
  --region=us-central1 \
  --class=org.apache.spark.examples.SparkPi \
  --jars=gs://costco-martech/jars/custom-transform.jar
```

### PySpark on Dataproc — Production Patterns

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
import argparse
import sys

def create_spark_session(app_name: str) -> SparkSession:
    """Create optimized SparkSession for Dataproc on GCP."""
    return (
        SparkSession.builder
        .appName(app_name)
        # BigQuery connector configuration
        .config("spark.jars", "gs://spark-lib/bigquery/spark-bigquery-latest_2.12.jar")
        .config("spark.jars.packages", "com.google.cloud.spark:spark-bigquery-with-dependencies_2.12:0.36.1")
        # Memory configuration
        .config("spark.executor.memory", "12g")
        .config("spark.executor.memoryOverhead", "2g")
        .config("spark.driver.memory", "8g")
        # Adaptive Query Execution
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.sql.adaptive.skewJoin.enabled", "true")
        # Shuffle
        .config("spark.sql.shuffle.partitions", "400")
        # GCS connector
        .config("spark.hadoop.fs.gs.impl", "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFileSystem")
        .config("spark.hadoop.google.cloud.auth.service.account.enable", "true")
        .getOrCreate()
    )


def run_campaign_attribution_etl(spark: SparkSession, date: str, project: str):
    """
    Full campaign attribution ETL: reads events from BigQuery,
    applies last-touch attribution, writes results back.
    """
    
    # Read from BigQuery
    events_df = (
        spark.read
        .format("bigquery")
        .option("table", f"{project}.ad_events.raw_events")
        .option("filter", f"DATE(event_timestamp) = '{date}'")
        .load()
    )
    
    # Read campaign metadata
    campaigns_df = (
        spark.read
        .format("bigquery")
        .option("table", f"{project}.campaigns.metadata")
        .load()
        .select("campaign_id", "campaign_name", "channel", "budget")
    )
    
    # Cache frequently accessed dataframe
    events_df.cache()
    
    print(f"Events loaded: {events_df.count():,}")
    
    # --- Last Touch Attribution ---
    # For each conversion, credit the last touch point
    
    # Window: per user, ordered by timestamp
    user_window = Window.partitionBy("user_id").orderBy("event_timestamp")
    
    # Assign a session_id (new session after 30-min gap)
    events_with_session = (
        events_df
        .withColumn("prev_timestamp", F.lag("event_timestamp").over(user_window))
        .withColumn("gap_seconds", 
            F.when(
                F.col("prev_timestamp").isNull(), 0
            ).otherwise(
                (F.unix_timestamp("event_timestamp") - F.unix_timestamp("prev_timestamp"))
            )
        )
        .withColumn("new_session_flag", F.when(F.col("gap_seconds") > 1800, 1).otherwise(0))
        .withColumn("session_id", 
            F.concat(
                F.col("user_id"),
                F.lit("_"),
                F.sum("new_session_flag").over(user_window)
            )
        )
    )
    
    # Find last touch before each conversion
    session_window = Window.partitionBy("session_id").orderBy("event_timestamp")
    session_window_full = Window.partitionBy("session_id")
    
    # Identify the campaign of the last touch (impression/click) before conversion
    last_touch_df = (
        events_with_session
        .withColumn("rank_desc", F.row_number().over(
            Window.partitionBy("session_id")
            .orderBy(F.desc("event_timestamp"))
        ))
        .withColumn("has_conversion", 
            F.sum(F.when(F.col("event_type") == "conversion", 1).otherwise(0))
            .over(session_window_full)
        )
        .filter(F.col("has_conversion") > 0)  # only sessions with conversions
        .filter(F.col("event_type").isin(["click", "impression"]))
        .filter(F.col("rank_desc") == 1)  # last touch
        .select("session_id", "user_id", "campaign_id", "event_timestamp")
        .withColumnRenamed("campaign_id", "attributed_campaign_id")
    )
    
    # Aggregate attributions
    attribution_summary = (
        last_touch_df
        .join(campaigns_df, 
              last_touch_df["attributed_campaign_id"] == campaigns_df["campaign_id"],
              "left")
        .groupBy("attributed_campaign_id", "campaign_name", "channel")
        .agg(
            F.count("session_id").alias("attributed_conversions"),
            F.countDistinct("user_id").alias("unique_users")
        )
        .withColumn("attribution_date", F.lit(date))
        .withColumn("model", F.lit("last_touch"))
    )
    
    # Write results to BigQuery
    (
        attribution_summary
        .write
        .format("bigquery")
        .option("table", f"{project}.campaign_analytics.attribution_daily")
        .option("temporaryGcsBucket", "costco-dataproc-temp")
        .option("createDisposition", "CREATE_IF_NEEDED")
        .option("writeDisposition", "WRITE_APPEND")
        .mode("append")
        .save()
    )
    
    print(f"Attribution written for {date}: {attribution_summary.count():,} campaign rows")
    
    # Unpersist cached DF
    events_df.unpersist()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="Processing date YYYY-MM-DD")
    parser.add_argument("--project", default="costco-martech-prod")
    args = parser.parse_args()
    
    spark = create_spark_session("CampaignAttributionETL")
    
    try:
        run_campaign_attribution_etl(spark, args.date, args.project)
    finally:
        spark.stop()
```

### Dataproc Serverless (No Cluster)

```bash
# Submit Spark job without provisioning a cluster
gcloud dataproc batches submit pyspark gs://costco-martech/scripts/daily_rollup.py \
  --project=costco-martech-prod \
  --region=us-central1 \
  --deps-bucket=gs://costco-dataproc-deps \
  --py-files=gs://costco-martech/libs/utils.zip \
  --properties="spark.executor.cores=4,spark.executor.memory=8g" \
  -- \
  --date=2024-01-15
```

---

## 7. Dataproc vs Dataflow Decision Framework

| Dimension | Dataflow | Dataproc |
|-----------|----------|----------|
| **Programming model** | Apache Beam (unified batch+stream) | Spark, Hadoop, Hive, Presto |
| **Cluster management** | Fully serverless | You provision clusters |
| **Existing codebase** | Rewrite required if not Beam | Lift-and-shift from on-prem Spark |
| **Streaming** | First-class citizen, exactly-once | Spark Structured Streaming (at-least-once) |
| **Data locality** | Optimized for GCS+BigQuery | HDFS + GCS |
| **Startup latency** | ~2 min | ~3-5 min (persistent cluster: instant) |
| **Cost model** | Per vCPU-hour processed | Cluster uptime, regardless of utilization |
| **ML integration** | Beam with TensorFlow Extended | Spark MLlib, native Python MLflow |
| **Interactive** | Not ideal | Jupyter on Dataproc, Spark shell |
| **Complex SQL** | Use BigQuery instead | Hive, SparkSQL, Presto/Trino |
| **Custom libraries** | Limited (Python/Java SDK only) | Any library installable on cluster |

**Decision rule:**
- New greenfield streaming pipeline → **Dataflow**
- Existing Spark ETL migration from on-prem → **Dataproc**
- Complex ML feature engineering with Spark MLlib → **Dataproc**
- Need Hive compatibility / Metastore → **Dataproc**
- Want zero infrastructure management → **Dataflow**

---

## 8. Cloud Pub/Sub — Messaging & Event Streaming

### What Pub/Sub Is
Pub/Sub is a **fully managed, serverless, globally distributed messaging service**. It decouples event producers from consumers, guaranteeing at-least-once delivery and handling global message routing.

```
Ad Tag (Publisher)
    │
    ▼
[Pub/Sub Topic]
    │
    ├──────────────────────────────────────────────┐
    │                                              │
    ▼                                              ▼
[Subscription 1]                         [Subscription 2]
  (Dataflow Streaming)                    (BigQuery direct)
  ↓                                        ↓
BigQuery Raw Events Table           BigQuery Analytics Table
```

### Core Concepts

| Concept | Definition |
|---------|------------|
| **Topic** | Named resource to which messages are published |
| **Subscription** | Named resource representing a stream of messages from a topic |
| **Publisher** | Application writing messages to a topic |
| **Subscriber** | Application reading messages from a subscription |
| **Message** | Data + attributes (key-value metadata) |
| **Acknowledgement** | Subscriber confirms message processing; prevents redelivery |
| **Ack deadline** | Time window subscriber has to ack before Pub/Sub redelivers |
| **Dead letter topic** | Messages exceeding max delivery attempts go here |

### Publishing Events

```python
from google.cloud import pubsub_v1
from google.api_core import retry
import json
import time
from concurrent.futures import TimeoutError

# --- Publisher ---
publisher = pubsub_v1.PublisherClient(
    publisher_options=pubsub_v1.types.PublisherOptions(
        enable_message_ordering=False,
        flow_control=pubsub_v1.types.PublishFlowControl(
            message_limit=1000,        # max 1000 messages in flight
            byte_limit=10 * 1024 * 1024,  # max 10MB in flight
            limit_exceeded_behavior=pubsub_v1.types.LimitExceededBehavior.BLOCK
        )
    ),
    # Batching settings (built into client)
    batch_settings=pubsub_v1.types.BatchSettings(
        max_bytes=1024 * 1024,  # max batch size: 1MB
        max_latency=0.01,       # max wait before flushing batch: 10ms
        max_messages=1000       # max messages per batch
    )
)

topic_path = publisher.topic_path('costco-martech-prod', 'ad-events')

def publish_ad_event(event: dict) -> str:
    """Publish an ad event to Pub/Sub. Returns message ID."""
    
    message_data = json.dumps(event).encode('utf-8')
    
    # Attributes are filterable metadata (avoid putting large data here)
    attributes = {
        'event_type': event['event_type'],
        'campaign_id': event['campaign_id'],
        'source': 'ad-tag-v2',
        'event_timestamp': str(int(event['timestamp']))  # for ordering
    }
    
    future = publisher.publish(
        topic_path,
        data=message_data,
        **attributes
    )
    
    # Wait for publish confirmation (non-blocking in prod — use callbacks instead)
    try:
        message_id = future.result(timeout=30)
        return message_id
    except Exception as e:
        print(f"Failed to publish: {e}")
        raise


def publish_batch(events: list[dict]):
    """Publish a batch of events — futures are resolved asynchronously."""
    futures = []
    
    for event in events:
        future = publisher.publish(
            topic_path,
            data=json.dumps(event).encode('utf-8'),
            event_type=event['event_type']
        )
        futures.append(future)
    
    # Wait for all futures
    for future in futures:
        try:
            future.result(timeout=30)
        except Exception as e:
            print(f"Publish failed: {e}")
    
    print(f"Published {len(events)} events")
```

### Pulling & Processing Messages

```python
from google.cloud import pubsub_v1

# --- Subscriber ---
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(
    'costco-martech-prod', 
    'ad-events-dataflow-sub'
)

def process_message(message: pubsub_v1.types.ReceivedMessage):
    """Callback function — called for each received message."""
    try:
        # Parse message
        event = json.loads(message.data.decode('utf-8'))
        
        # Process the event
        print(f"Processing event: {event['event_id']}")
        
        # Do work here (write to DB, call API, etc.)
        process_event(event)
        
        # Acknowledge — tells Pub/Sub this message is processed, don't redeliver
        message.ack()
        
    except Exception as e:
        print(f"Processing failed: {e}")
        # nack() — tells Pub/Sub to redeliver this message
        message.nack()


# Flow control settings
flow_control = pubsub_v1.types.FlowControl(
    max_messages=100,           # max unacked messages at a time
    max_bytes=10 * 1024 * 1024  # max 10MB of unacked data
)

streaming_pull_future = subscriber.subscribe(
    subscription_path,
    callback=process_message,
    flow_control=flow_control,
    scheduler=pubsub_v1.ThreadScheduler(executor=concurrent.futures.ThreadPoolExecutor(max_workers=10))
)

print(f"Listening for messages on {subscription_path}")

with subscriber:
    try:
        streaming_pull_future.result(timeout=300)
    except TimeoutError:
        streaming_pull_future.cancel()
        streaming_pull_future.result()  # block until cancel completes
```

### Pub/Sub Lite vs Pub/Sub Standard

| Feature | Pub/Sub Standard | Pub/Sub Lite |
|---------|-----------------|--------------|
| **Global routing** | Yes — messages routed globally | No — zonal (Zonal Lite) or regional (Regional Lite) |
| **Ordering** | Optional (with ordering keys) | Always ordered within partition |
| **Capacity** | Auto-scales | Pre-provisioned (must specify throughput/storage) |
| **Price** | Per-message ($0.04/1M msg + storage) | Per-capacity (cheaper at high throughput) |
| **Use case** | Variable load, global delivery | Predictable high-throughput, cost-sensitive |

### BigQuery Subscription (No Code Required)

```bash
# Direct Pub/Sub → BigQuery without any Dataflow code
gcloud pubsub subscriptions create ad-events-bq-sub \
  --topic=ad-events \
  --bigquery-table=costco-martech-prod:ad_events.raw_events \
  --write-metadata  # adds Pub/Sub metadata as columns
  
# BigQuery must have schema matching message schema
# Messages must be JSON (or Avro with a schema)
# No transformation — raw messages only
```

---

## 9. Pub/Sub Advanced Patterns

### Message Ordering

```python
# Publisher with ordering key — messages with same key delivered in order
future = publisher.publish(
    topic_path,
    data=message_data,
    ordering_key=event['user_id']  # all events for same user arrive in order
)

# Subscription must have ordering enabled:
# --enable-message-ordering flag when creating subscription
```

### Dead Letter Queue Pattern

```bash
# Create dead letter topic
gcloud pubsub topics create ad-events-dlq

# Create subscription with DLQ
gcloud pubsub subscriptions create ad-events-sub \
  --topic=ad-events \
  --dead-letter-topic=ad-events-dlq \
  --max-delivery-attempts=5 \  # after 5 nacks/timeouts → move to DLQ
  --ack-deadline=60s            # subscriber has 60s to ack
```

### Schema Enforcement

```bash
# Create Avro schema for ad events
gcloud pubsub schemas create ad-event-schema \
  --type=AVRO \
  --definition='{
    "type": "record",
    "name": "AdEvent",
    "fields": [
      {"name": "event_id", "type": "string"},
      {"name": "user_id", "type": "string"},
      {"name": "campaign_id", "type": "string"},
      {"name": "event_type", "type": "string"},
      {"name": "timestamp", "type": "long"},
      {"name": "revenue", "type": ["null", "double"], "default": null}
    ]
  }'

# Attach schema to topic — rejects invalid messages at publish time
gcloud pubsub topics create ad-events-typed \
  --schema=ad-event-schema \
  --message-encoding=JSON
```

### Seek — Replay Messages

```python
# Seek to a timestamp — replay all messages published after this time
from google.protobuf.timestamp_pb2 import Timestamp

subscriber = pubsub_v1.SubscriberClient()
subscription_path = 'projects/costco-martech-prod/subscriptions/ad-events-sub'

# Replay last 24 hours
import datetime
seek_time = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
timestamp = Timestamp()
timestamp.FromDatetime(seek_time)

subscriber.seek(
    request={
        "subscription": subscription_path,
        "time": timestamp
    }
)
# Now the subscription will re-deliver all messages from the last 24 hours
```

---

## 10. Cloud Dataplex — Data Mesh & Governance

### What Dataplex Is
Dataplex is GCP's **intelligent data fabric** — a unified platform for data management, governance, discovery, and quality across a data mesh architecture. It's not a processing engine; it's a **management layer** on top of BigQuery, GCS, and Dataproc.

```
Dataplex Hierarchy:
├── Lake (coarsest unit — typically maps to a domain or department)
│   ├── Zone (logical grouping within a lake)
│   │   ├── Raw Zone (landing zone — raw data, minimal curation)
│   │   ├── Curated Zone (cleaned, conformed data)
│   │   └── Analytics Zone (aggregated, business-ready data)
│   └── Assets (BigQuery datasets or GCS buckets registered in a zone)
```

### Setting Up a Dataplex Lake

```bash
# Create a Dataplex lake for MarTech domain
gcloud dataplex lakes create martech-lake \
  --project=costco-martech-prod \
  --location=us-central1 \
  --display-name="MarTech Data Lake" \
  --description="Ad events, campaign data, member analytics"

# Create zones
gcloud dataplex zones create raw-zone \
  --project=costco-martech-prod \
  --location=us-central1 \
  --lake=martech-lake \
  --type=RAW \
  --resource-spec-required-location=us-central1 \
  --display-name="Raw Ingestion Zone"

gcloud dataplex zones create curated-zone \
  --project=costco-martech-prod \
  --location=us-central1 \
  --lake=martech-lake \
  --type=CURATED \
  --display-name="Curated Analytics Zone"

# Register BigQuery dataset as an asset in the curated zone
gcloud dataplex assets create campaign-analytics-asset \
  --project=costco-martech-prod \
  --location=us-central1 \
  --lake=martech-lake \
  --zone=curated-zone \
  --resource-spec-type=BIGQUERY_DATASET \
  --resource-spec-name="projects/costco-martech-prod/datasets/campaign_analytics" \
  --display-name="Campaign Analytics Dataset"
```

### Dataplex Catalog — Data Discovery

```python
from google.cloud import dataplex_v1
from google.cloud import datacatalog_v1

# Search for datasets across the data mesh
catalog_client = datacatalog_v1.DataCatalogClient()

# Search for all ad_events tables
request = datacatalog_v1.SearchCatalogRequest(
    query='type=TABLE name:ad_events',
    scope=datacatalog_v1.SearchCatalogRequest.Scope(
        include_project_ids=['costco-martech-prod']
    )
)

results = catalog_client.search_catalog(request=request)

for result in results:
    print(f"Table: {result.relative_resource_name}")
    print(f"Description: {result.description}")
    print(f"Last modified: {result.modify_time}")
    print()


# Tag a BigQuery table with business metadata
tag_template_client = datacatalog_v1.DataCatalogClient()

# Create a tag template for MarTech tables
tag_template = datacatalog_v1.TagTemplate(
    display_name="MarTech Table Metadata",
    fields={
        "data_owner": datacatalog_v1.TagTemplateField(
            display_name="Data Owner",
            type_=datacatalog_v1.FieldType(
                primitive_type=datacatalog_v1.FieldType.PrimitiveType.STRING
            )
        ),
        "pii_data": datacatalog_v1.TagTemplateField(
            display_name="Contains PII",
            type_=datacatalog_v1.FieldType(
                primitive_type=datacatalog_v1.FieldType.PrimitiveType.BOOL
            )
        ),
        "refresh_frequency": datacatalog_v1.TagTemplateField(
            display_name="Refresh Frequency",
            type_=datacatalog_v1.FieldType(
                primitive_type=datacatalog_v1.FieldType.PrimitiveType.STRING
            )
        )
    }
)

# Tag specific table
tag = datacatalog_v1.Tag(
    template="projects/costco-martech-prod/locations/us-central1/tagTemplates/martech-metadata",
    fields={
        "data_owner": datacatalog_v1.TagField(string_value="martech-team@costco.com"),
        "pii_data": datacatalog_v1.TagField(bool_value=True),
        "refresh_frequency": datacatalog_v1.TagField(string_value="hourly")
    }
)
```

### Data Lineage Tracking

```python
# Dataplex automatically tracks lineage for:
# - BigQuery jobs (query → tables touched)
# - Dataflow jobs (source → sinks)
# - Dataproc jobs (with lineage plugin)

# Manual lineage events for custom pipelines
from google.cloud import lineage_v1

lineage_client = lineage_v1.LineageClient()

# Record that pipeline "campaign_attribution_etl" reads from raw_events
# and writes to attribution_daily
process_run = lineage_v1.ProcessOpenLineageRunEventRequest(
    parent=f"projects/costco-martech-prod/locations/us-central1",
    open_lineage={
        "eventType": "COMPLETE",
        "eventTime": "2024-01-15T12:00:00Z",
        "run": {"runId": "run-20240115-001"},
        "job": {
            "namespace": "costco-martech",
            "name": "campaign_attribution_etl"
        },
        "inputs": [{
            "namespace": "bigquery",
            "name": "costco-martech-prod.ad_events.raw_events"
        }],
        "outputs": [{
            "namespace": "bigquery",
            "name": "costco-martech-prod.campaign_analytics.attribution_daily"
        }]
    }
)

lineage_client.process_open_lineage_run_event(request=process_run)
```

---

## 11. Dataplex Data Quality

### Defining Data Quality Rules

```python
from google.cloud import dataplex_v1

dataplex_client = dataplex_v1.DataplexServiceClient()

# Create a DataScan with data quality rules
datascan = dataplex_v1.DataScan(
    display_name="Ad Events Data Quality Scan",
    resource_spec=dataplex_v1.DataScan.ResourceSpec(
        resource="//bigquery.googleapis.com/projects/costco-martech-prod/datasets/ad_events/tables/raw_events"
    ),
    data_quality_spec=dataplex_v1.DataQualitySpec(
        sampling_percent=10.0,  # sample 10% of rows
        row_filter="DATE(event_timestamp) = CURRENT_DATE()",
        rules=[
            # Completeness: event_id must not be null
            dataplex_v1.DataQualityRule(
                column="event_id",
                name="event_id_not_null",
                non_null_expectation=dataplex_v1.DataQualityRule.NonNullExpectation(),
                threshold=1.0,  # 100% non-null
                dimension="COMPLETENESS"
            ),
            # Uniqueness: event_id must be unique
            dataplex_v1.DataQualityRule(
                column="event_id",
                name="event_id_unique",
                uniqueness_expectation=dataplex_v1.DataQualityRule.UniquenessExpectation(),
                threshold=1.0,
                dimension="UNIQUENESS"
            ),
            # Range: revenue must be >= 0
            dataplex_v1.DataQualityRule(
                column="revenue",
                name="revenue_non_negative",
                range_expectation=dataplex_v1.DataQualityRule.RangeExpectation(
                    min_value="0",
                    strict_min_value=False
                ),
                dimension="VALIDITY"
            ),
            # Set membership: event_type must be in allowed values
            dataplex_v1.DataQualityRule(
                column="event_type",
                name="event_type_valid",
                set_expectation=dataplex_v1.DataQualityRule.SetExpectation(
                    values=["impression", "click", "conversion", "viewthrough"]
                ),
                threshold=0.99,  # 99% must be valid (1% tolerance for new types)
                dimension="VALIDITY"
            ),
            # Custom SQL: no events from future
            dataplex_v1.DataQualityRule(
                name="no_future_events",
                sql_assertion=dataplex_v1.DataQualityRule.SqlAssertion(
                    sql_statement="SELECT COUNT(*) = 0 FROM `costco-martech-prod.ad_events.raw_events` WHERE event_timestamp > CURRENT_TIMESTAMP()"
                ),
                dimension="CONSISTENCY"
            ),
        ]
    ),
    execution_spec=dataplex_v1.DataScan.ExecutionSpec(
        trigger=dataplex_v1.Trigger(
            schedule=dataplex_v1.Trigger.Schedule(
                cron="0 * * * *"  # Run hourly
            )
        )
    )
)

# Create the scan
parent = "projects/costco-martech-prod/locations/us-central1"
dataplex_client.create_data_scan(
    parent=parent,
    data_scan=datascan,
    data_scan_id="ad-events-quality-scan"
)
```

### Reading Data Quality Results

```python
# Get latest scan result
scan_name = "projects/costco-martech-prod/locations/us-central1/dataScans/ad-events-quality-scan"
scan_result = dataplex_client.get_data_scan(name=scan_name)

# List past scan jobs
for job in dataplex_client.list_data_scan_jobs(parent=scan_name):
    print(f"Job: {job.name}")
    print(f"State: {job.state}")
    print(f"Score: {job.data_quality_result.score}")
    
    for rule_result in job.data_quality_result.rule_results:
        status = "PASS" if rule_result.passed else "FAIL"
        print(f"  Rule: {rule_result.rule.name} → {status}")
        if not rule_result.passed:
            print(f"    Failing rows: {rule_result.failing_rows_count:,}")
```

---

## 12. Integration Patterns Across Services

### Pattern 1: Pub/Sub → Dataflow → BigQuery (Real-Time)

```
Ad Tag → Pub/Sub (ad-events topic)
    └── Dataflow Streaming Job
        ├── Parse + Validate (DoFn)
        ├── Enrich with Redis side inputs
        ├── Window into 5-min fixed windows
        ├── Aggregate by campaign
        └── Write to BigQuery (Storage Write API)
            ├── raw_events table (every event)
            └── campaign_5min_rollup table (windowed aggregates)
```

```python
# Full integration pipeline
with beam.Pipeline(options=streaming_options) as p:
    
    # Source: Pub/Sub
    raw_messages = (
        p
        | 'Read Ad Events' >> ReadFromPubSub(
            subscription='projects/costco-martech-prod/subscriptions/ad-events-df-sub',
            with_attributes=True,
            timestamp_attribute='event_timestamp'
        )
    )
    
    # Parse and validate
    parsed, dead_letters = (
        raw_messages
        | 'Parse Events' >> beam.ParDo(ParseAdEventDoFn()).with_outputs(
            'dead_letter', main='valid'
        )
    )
    
    # Write raw events
    parsed.valid | 'Write Raw' >> WriteToBigQuery(
        table='costco-martech-prod:ad_events.raw_events',
        method=WriteToBigQuery.Method.STORAGE_WRITE_API,
        triggering_frequency=60  # write every 60 seconds
    )
    
    # Window and aggregate
    campaign_rollup = (
        parsed.valid
        | 'Window 5min' >> beam.WindowInto(window.FixedWindows(300))
        | 'Key by Campaign' >> beam.Map(lambda e: (e['campaign_id'], {
            'clicks': 1 if e['event_type'] == 'click' else 0,
            'impressions': 1 if e['event_type'] == 'impression' else 0,
            'revenue': e.get('revenue', 0.0)
        }))
        | 'Aggregate' >> beam.CombinePerKey(AdMetricsCombineFn())
        | 'Format Rollup' >> beam.Map(lambda kv: {
            'campaign_id': kv[0],
            **kv[1]
        })
    )
    
    campaign_rollup | 'Write Rollup' >> WriteToBigQuery(
        table='costco-martech-prod:ad_analytics.campaign_5min_rollup',
        method=WriteToBigQuery.Method.STORAGE_WRITE_API
    )
    
    # Dead letters to monitoring
    dead_letters | 'Write DLQ' >> WriteToBigQuery(
        table='costco-martech-prod:monitoring.dead_letters'
    )
```

### Pattern 2: Cloud Composer (Airflow) → Dataproc → BigQuery (Batch)

```python
# Airflow DAG orchestrating daily Dataproc job
from airflow import DAG
from airflow.providers.google.cloud.operators.dataproc import (
    DataprocCreateClusterOperator,
    DataprocSubmitJobOperator,
    DataprocDeleteClusterOperator
)
from airflow.providers.google.cloud.sensors.dataproc import DataprocJobSensor
from airflow.utils.trigger_rule import TriggerRule
from datetime import datetime, timedelta

PROJECT_ID = 'costco-martech-prod'
REGION = 'us-central1'
CLUSTER_NAME = 'campaign-attribution-{{ ds_nodash }}'

default_args = {
    'owner': 'martech-eng',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'on_failure_callback': send_slack_alert
}

with DAG(
    dag_id='daily_campaign_attribution',
    default_args=default_args,
    schedule_interval='0 6 * * *',  # 6am daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['martech', 'attribution']
) as dag:
    
    # Create ephemeral cluster
    create_cluster = DataprocCreateClusterOperator(
        task_id='create_cluster',
        project_id=PROJECT_ID,
        cluster_config={
            'master_config': {
                'num_instances': 1,
                'machine_type_uri': 'n1-standard-8',
                'disk_config': {'boot_disk_type': 'pd-ssd', 'boot_disk_size_gb': 500}
            },
            'worker_config': {
                'num_instances': 10,
                'machine_type_uri': 'n1-highmem-16',
                'disk_config': {'boot_disk_type': 'pd-ssd', 'boot_disk_size_gb': 500}
            },
            'secondary_worker_config': {
                'num_instances': 20,
                'is_preemptible': True
            },
            'software_config': {
                'image_version': '2.1-debian11',
                'properties': {
                    'spark:spark.sql.adaptive.enabled': 'true',
                    'spark:spark.executor.memory': '12g'
                }
            }
        },
        region=REGION,
        cluster_name=CLUSTER_NAME
    )
    
    # Submit attribution job
    run_attribution = DataprocSubmitJobOperator(
        task_id='run_attribution_etl',
        job={
            'reference': {'project_id': PROJECT_ID},
            'placement': {'cluster_name': CLUSTER_NAME},
            'pyspark_job': {
                'main_python_file_uri': 'gs://costco-martech/scripts/campaign_attribution.py',
                'args': ['--date={{ ds }}', f'--project={PROJECT_ID}'],
                'python_file_uris': ['gs://costco-martech/libs/utils.zip']
            }
        },
        region=REGION,
        project_id=PROJECT_ID
    )
    
    # Delete cluster even if job fails (cost control)
    delete_cluster = DataprocDeleteClusterOperator(
        task_id='delete_cluster',
        project_id=PROJECT_ID,
        cluster_name=CLUSTER_NAME,
        region=REGION,
        trigger_rule=TriggerRule.ALL_DONE  # run even if upstream fails
    )
    
    create_cluster >> run_attribution >> delete_cluster
```

### Pattern 3: GCS → Dataplex → BigQuery (Data Mesh Ingestion)

```bash
# Dataplex auto-discovery: when files land in GCS,
# Dataplex discovers schema, creates BigQuery external table
# and triggers data quality scans

# File lands: gs://costco-raw/ad-events/date=2024-01-15/part-00001.parquet
# Dataplex discovers: creates BQ external table ad_events.raw_ad_events_ext
# Quality scan runs: validates schema, nulls, ranges
# On pass: Dataflow ingest job triggered to write to native BQ table
```

---

## 13. MarTech/AdTech Pipeline Architectures on GCP

### Architecture 1: Real-Time Campaign Performance Dashboard

```
[Ad Servers, Ad Tags]
    │
    │ HTTPS POST (click/impression events)
    ▼
[Pub/Sub: ad-events-topic]
    │
    ├─[Dataflow Streaming]──────────────────────────────────┐
    │   • Parse event JSON                                   │
    │   • Resolve user_id via Redis lookup                  │
    │   • Parse UTM parameters                              │
    │   • Deduplicate (using Bloom filter state)            │
    │   • Window: 1-minute fixed windows                    │
    │   • Aggregate: impressions, clicks, conversions       │
    │   • Write: Storage Write API (committed mode)         │
    ▼                                                        ▼
[BigQuery: raw_events]                   [BigQuery: campaign_1min_rollup]
    │                                            │
    │                                            ▼
    │                                   [Materialized View: campaign_live_stats]
    │                                            │
    │                                            ▼
    │                                   [Looker Dashboard (auto-refresh 60s)]
    │
    └─[Dataproc: Batch]──────────────────────────────┐
        • Daily at 6am                                │
        • Full session reconstruction                 │
        • Multi-touch attribution                     │
        • Cohort analysis                             │
        • Write: BigQuery partitioned tables          │
        ▼                                             │
[BigQuery: campaign_daily_attribution]               │
        │                                             │
        ▼                                             │
[Looker: Attribution Reports]          ◀─────────────┘
```

### Architecture 2: Member Segmentation Pipeline

```
[Costco Membership DB (AlloyDB)]
    │ CDC via Datastream
    ▼
[Pub/Sub: member-changes-topic]
    │
    ▼
[Dataflow Streaming]
    • Parse CDC events (INSERT/UPDATE/DELETE)
    • Merge with member profile (stateful)
    • Apply RFM scoring (per-key state)
    • Emit updated member segments
    │
    ├─▶ [AlloyDB: member_profiles] (for real-time API serving, <10ms)
    └─▶ [BigQuery: member_segments_history] (for analytics)
    
[Cloud Composer DAG: daily_rfm_refresh]
    │
    ▼
[Dataproc PySpark]
    • Full RFM recalculation on all members
    • Segment assignment (Champions, Loyal, At Risk, etc.)
    • Write to BigQuery + AlloyDB
    │
    ▼
[BigQuery: member_segments_daily]
    │
    ▼
[Vertex AI: Churn Prediction Model]
    │
    ▼
[BigQuery: member_churn_scores]
    │
    ▼
[Pub/Sub: high-risk-members] → [Email/Push Campaign trigger]
```

---

## 14. Interview Q&A Bank

**Q: Explain the difference between Dataflow and Dataproc. When would you choose each?**
A: Dataflow is fully serverless and uses the Apache Beam model — you write pipeline code that runs as either batch or streaming with no cluster management. Ideal for new pipeline development, streaming use cases, and when you want zero operational overhead. Dataproc is managed Spark/Hadoop — you provision clusters and run Spark, Hive, or Presto jobs. Ideal for lifting existing PySpark code from on-prem, complex Spark MLlib workflows, or when you need interactive Jupyter notebooks. In practice at Costco, I'd use Dataflow for real-time ad event streaming pipelines and Dataproc for daily batch attribution jobs that need full Spark SQL capabilities.

**Q: Explain watermarks and late data in Dataflow streaming.**
A: In streaming, the watermark is Dataflow's estimate of "I believe all events up to time T have arrived." This is necessary because events can arrive out of order due to network delays. When a window's watermark passes the window's end time, Dataflow emits the window's results. Late data — events arriving after the watermark — can be handled with `allowed_lateness` on the WindowInto. You can configure triggers to re-emit the window result when late data arrives, using `AccumulationMode.ACCUMULATING` to update the result, or `DISCARDING` to emit incremental deltas. Without handling late data, you lose those events silently.

**Q: What is fusion in Dataflow and when would you break it?**
A: Fusion is Dataflow's optimization that merges consecutive transforms into a single execution stage, avoiding intermediate serialization. For example, ParseJSON → Filter → Map would be fused into one stage that processes each element in-memory without writing intermediate results to disk. This is generally beneficial. You'd break fusion (using `Reshuffle()`) when: (1) a stage before a `GroupByKey` should be parallelized independently; (2) a CPU-heavy transform should scale independently of downstream transforms; (3) you want to reset the fan-out for better work distribution.

**Q: How does Pub/Sub guarantee at-least-once delivery? What does this mean for your pipeline?**
A: Pub/Sub retains messages until they're acknowledged. If a subscriber processes a message but crashes before acking, Pub/Sub redelivers the message after the ack deadline expires. This guarantees every message is delivered at least once. The implication for pipelines: you must make your consumers idempotent — processing the same message twice should produce the same result. In Dataflow, we achieve this by deduplicating on event_id using stateful processing. In BigQuery writes, we use MERGE or INSERT IGNORE patterns. For Pub/Sub Lite with ordered delivery, you can use exactly-once semantics.

**Q: Describe how you'd design a Dataplex data mesh for a retail company.**
A: I'd organize Dataplex around business domains: (1) a MarTech lake with Raw zone (raw ad events, raw click streams) and Curated zone (parsed events, attribution tables); (2) a Member lake with transaction history, segment tables; (3) a Supply Chain lake with inventory, logistics data. Each lake has a designated owner team with IAM bindings to their lake/zones. Dataplex auto-discovers schemas, creates unified catalog entries, and applies data quality scans on schedule. Tag templates enforce business metadata (PII flag, data owner, refresh frequency) across all assets. Lineage is automatically tracked for all BigQuery and Dataflow jobs. Analysts query the Dataplex catalog to find tables without knowing where they live.

**Q: How would you handle a hot partition in a Dataflow GroupByKey?**
A: Hot partitions (one key dominating all traffic, e.g., a single massive campaign_id) cause one worker to get overwhelmed. The solution is to add a random shard suffix to the key before GroupByKey, splitting one key across N shards. Then do a partial aggregation per shard, strip the suffix, and do a second aggregation. This is the "pre-aggregation" or "combiner lifting" pattern. Dataflow's AQE (if enabled) can also detect and split hot keys automatically in some versions. Additionally, using `CombineFn` instead of GroupByKey allows Dataflow to lift the combine to the map side, reducing data sent to the shuffle.

**Q: Walk me through how you'd build a Pub/Sub → Dataflow → BigQuery pipeline for tracking ad clicks in real time.**
A: (1) Publisher: Ad tag POSTs click events to a backend service, which publishes to a Pub/Sub topic with the event timestamp as a message attribute. Schema validation enforces the expected fields via Pub/Sub schema. (2) Dataflow job: Reads from a Pub/Sub subscription with `timestamp_attribute='event_timestamp'` to use event time, not processing time. A DoFn parses JSON and handles malformed messages by routing to a dead-letter tag. We apply a 5-minute FixedWindow with AfterWatermark trigger and 1-hour allowed_lateness. CombinePerKey aggregates impressions/clicks/revenue by campaign within each window. (3) Writing: Raw events go to a BigQuery table using Storage Write API in committed mode (available immediately for queries). Aggregates go to a separate rollup table. The Dataflow job runs with Streaming Engine enabled and THROUGHPUT_BASED autoscaling between 10–100 workers.

---

*End of Topic 7 — GCP Data Services: Dataflow, Dataproc, Pub/Sub, Dataplex*
