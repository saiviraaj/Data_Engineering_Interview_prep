# Topic 14: System Design for Data Engineering (🔥 L5/L6 CORE)
## Costco Sr. Data Engineer — Exhaustive Interview Textbook

---

## Table of Contents
1. [L1: Core Concepts — Design Fundamentals](#l1-core-concepts)
2. [L2: Deep Technical Understanding](#l2-deep-technical-understanding)
3. [L3: Real-World Scenarios — CDM-Style Platform Design](#l3-real-world-scenarios)
4. [L4: Hands-On Architecture Walkthroughs](#l4-hands-on-architecture-walkthroughs)
5. [L5: Edge Cases, Bottlenecks & Trade-offs](#l5-edge-cases-bottlenecks--trade-offs)
6. [L6: Interview Questions — Easy to Very Hard](#l6-interview-questions)

---

## L1: Core Concepts

### 1.1 The System Design Interview Framework

Senior data engineering system design interviews follow a structured pattern. Interviewers evaluate whether you can think like an architect — not just a developer.

**The 6-step framework** (use this for EVERY system design question):

```
Step 1: CLARIFY REQUIREMENTS (3-5 min)
  → Functional: what must the system do?
  → Non-functional: scale, latency, availability, cost
  → Constraints: team size, existing stack, timeline

Step 2: ESTIMATE SCALE (2-3 min)
  → Data volume: events/day, GB/day, growth rate
  → Query patterns: how many users, what types of queries
  → Latency requirements: real-time vs batch

Step 3: HIGH-LEVEL DESIGN (5 min)
  → Draw the boxes and arrows
  → Identify the major components
  → Don't go deep yet

Step 4: DEEP DIVE on critical components (15-20 min)
  → Pick 2-3 hardest parts and explain in detail
  → Trade-offs for each design choice
  → How you handle failure

Step 5: TRADE-OFFS AND ALTERNATIVES (5 min)
  → What would you do differently with more time?
  → What are the weaknesses of your design?
  → How does it evolve as requirements change?

Step 6: COST AND OPERABILITY (3 min)
  → Rough cost estimate
  → How do you monitor it?
  → How do you recover from failure?
```

---

### 1.2 Key Design Principles for Data Systems

**1. Immutability First**
Raw data should never be modified. Append-only sources of truth. Transformations produce new data, never mutate originals.

**2. Idempotency**
Every operation can be safely retried. `f(f(x)) = f(x)`. Partition overwrites, not appends where possible.

**3. Separation of Concerns**
Ingestion ≠ Transformation ≠ Serving. Each layer has one job and one clear interface.

**4. Fail Fast, Fail Loudly**
Better to fail with a clear error than silently produce wrong results. Data quality gates at each layer.

**5. Schema Evolution by Design**
The schema WILL change. Design for backwards compatibility from day one.

**6. The Waterfall Rule**
Data flows in one direction: sources → raw → staging → marts → serving. Never circular dependencies.

---

### 1.3 CAP Theorem — Applied to Data Systems

```
CAP Theorem: In a distributed system, you can guarantee at most 2 of 3:
  C = Consistency  (every read reflects the latest write)
  A = Availability (every request gets a response)
  P = Partition tolerance (system works despite network failures)

Network partitions are inevitable → choose CP or AP:

CP (Consistency + Partition tolerance):
  BigQuery: always consistent, may be temporarily unavailable during partition events
  PostgreSQL with synchronous replication: consistent but blocks during failures
  Use when: financial data, inventory, any case where stale reads cause real harm

AP (Availability + Partition tolerance):
  Pub/Sub: always accepts messages, might deliver out of order
  Cassandra: always responds, may return stale data
  Use when: event streams, logs, analytics — stale data for seconds is acceptable

For data engineering: most systems are AP (event streams, data lakes)
with eventual consistency toward CP (final marts must be correct)
```

---

## L2: Deep Technical Understanding

### 2.1 Lambda Architecture vs Kappa Architecture

#### Lambda Architecture

```
                    ┌─────────────────────────────────────┐
                    │           Batch Layer               │
Source events ──────┤  (Reprocesses ALL historical data)  ├──► Batch views
      │             │  BigQuery + DBT + Dataproc           │    (authoritative)
      │             └─────────────────────────────────────┘         │
      │                                                              │
      │             ┌─────────────────────────────────────┐         │
      └─────────────┤          Speed Layer                ├──► Real-time views
                    │  (Processes only recent data)        │    (approximate)
                    │  Dataflow + Pub/Sub                  │         │
                    └─────────────────────────────────────┘         │
                                                                     ▼
                                                         ┌───────────────────┐
                                                         │   Serving Layer   │
                                                         │ (merges batch +   │
                                                         │  real-time views) │
                                                         └───────────────────┘
```

**Lambda pros**: Clear separation, batch layer is always correct, speed layer is always fast.

**Lambda cons**: Two codebases doing similar work, data duplication, complexity of merging views.

**When to use**: When you genuinely need both real-time AND authoritative batch numbers AND they have different accuracy requirements (e.g., real-time dashboard vs daily finance report).

#### Kappa Architecture

```
Source events ──► Message Queue ──► Single Streaming Layer ──► Serving Layer
                  (Kafka/Pub/Sub)   (Dataflow/Flink)           (BigQuery/Redis)

For reprocessing: replay from the message queue with a new pipeline version
```

**Kappa pros**: Single codebase, simpler operations, no need to merge two systems.

**Kappa cons**: Message queue must retain data long enough for reprocessing (expensive), streaming is harder to reason about for complex transformations.

**When to use**: When your streaming logic is the authoritative path and you can afford long retention (Kafka with tiered storage), or when the business doesn't need batch-authoritative numbers.

**Practical recommendation for GCP/Costco**: Lambda architecture is standard. Dataflow streaming for real-time (approximate), DBT+BigQuery daily for authoritative.

---

### 2.2 Data Platform Architecture — Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GOVERNANCE LAYER                            │
│            Dataplex (catalog + lineage + quality)                   │
│            IAM (access control)                                     │
│            Audit Logs (who accessed what when)                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                         SERVING LAYER                               │
│    BigQuery Marts    │    BI Engine    │    APIs    │    ML Models  │
│    (Looker, Tableau) │    (dashboards) │  (FastAPI) │  (Vertex AI)  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                      TRANSFORMATION LAYER                           │
│         DBT (SQL-based, lineage, tests, documentation)              │
│         Dataproc/Spark (ML features, complex transforms)            │
│         Dataflow (streaming transforms)                             │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                         STORAGE LAYER                               │
│    GCS (raw data lake)    │    BigQuery (raw/staging datasets)      │
│    (immutable, partitioned)│   (structured, queryable)              │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                        INGESTION LAYER                              │
│    Pub/Sub (streaming)  │  Fivetran/Airbyte (connectors)           │
│    Cloud Functions      │  Dataflow (batch + stream)               │
│    Datastream (CDC)     │  Cloud Composer (orchestration)          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                         SOURCE LAYER                                │
│    Operational DBs  │  Ad Platforms  │  SaaS tools  │  IoT/devices │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 2.3 Scalability Patterns

#### Horizontal vs Vertical Scaling

```
Vertical scaling (scale up): give each component more resources
  → BigQuery: increase slot reservations
  → Dataproc: larger machine types
  → Limit: always a ceiling; single point of failure

Horizontal scaling (scale out): add more instances
  → Dataflow: add more workers (auto-scales)
  → Pub/Sub: add more subscriber instances
  → BigQuery: inherently horizontally scaled (thousands of leaf servers)
  → No ceiling; more resilient
```

#### Partitioning for Scale

```python
# Horizontal partitioning (sharding): split by key range
# e.g., Pub/Sub topics per region, BigQuery tables per application team

# Temporal partitioning (most common in data engineering):
# BigQuery: PARTITION BY click_date
# → Each day's data is independent
# → Can process days in parallel
# → Can delete old data efficiently
# → Storage scales linearly with retention

# Partition-based parallelism in Spark:
df.repartition(200, "campaign_id")  # 200 partitions, each processes independently
# More partitions → more parallel tasks → higher throughput
```

#### Fan-Out Pattern (Event-Driven Scaling)

```python
# One event → multiple downstream consumers
# Pub/Sub topic: purchase-events

# Consumer A: analytics pipeline (BigQuery)
# Consumer B: loyalty points service
# Consumer C: email notification service
# Consumer D: inventory update service

# Each consumer scales independently
# Adding new consumer doesn't change publisher
# This is how platforms scale: decouple producers from consumers
```

---

### 2.4 Fault Tolerance Patterns

#### Dead Letter Queue (DLQ)

```python
# Pattern: if a message fails N times, route to DLQ for investigation
# Prevents one bad message from blocking the entire pipeline

# Pub/Sub: configure dead letter topic
resource "google_pubsub_subscription" "main_subscription" {
  name  = "ad-events-subscription"
  topic = google_pubsub_topic.ad_events.name

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.ad_events_dlq.id
    max_delivery_attempts = 5  # after 5 failures → send to DLQ
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"  # exponential backoff up to 10 min
  }
}

# Monitor DLQ: alert when messages arrive
# Investigate: parse DLQ messages to understand failure pattern
# Fix: fix the pipeline, then replay DLQ messages
```

#### Circuit Breaker

```python
# Pattern: stop trying an operation that's consistently failing
# Prevents cascading failures (one slow service brings down everything)

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.state = 'CLOSED'  # CLOSED=normal, OPEN=blocking, HALF_OPEN=testing
        self.last_failure_time = None
        self.timeout = timeout

    def call(self, fn, *args, **kwargs):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
            else:
                raise CircuitOpenError("Circuit breaker is OPEN — service unavailable")

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self.failure_count = 0
        self.state = 'CLOSED'

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.critical(f"Circuit breaker OPENED after {self.failure_count} failures")

# Use for: calls to external APIs (Google Ads API, Meta API)
# If API is down, stop hammering it; let it recover
bq_writer = CircuitBreaker(failure_threshold=3, timeout=120)
bq_writer.call(write_to_bigquery, events)
```

#### Checkpoint and Resume

```python
# Pattern: save processing state periodically so you can resume from last checkpoint
# Prevents reprocessing from scratch after failures

class PipelineCheckpoint:
    def __init__(self, checkpoint_table: str):
        self.bq = bigquery.Client()
        self.table = checkpoint_table

    def save(self, pipeline_id: str, last_processed: dict):
        """Save checkpoint state."""
        self.bq.query(f"""
            MERGE `{self.table}` AS target
            USING (SELECT '{pipeline_id}' AS pipeline_id,
                          '{json.dumps(last_processed)}' AS checkpoint_data,
                          CURRENT_TIMESTAMP() AS updated_at) AS source
            ON target.pipeline_id = source.pipeline_id
            WHEN MATCHED THEN UPDATE SET
                target.checkpoint_data = source.checkpoint_data,
                target.updated_at = source.updated_at
            WHEN NOT MATCHED THEN INSERT VALUES (source.*)
        """).result()

    def load(self, pipeline_id: str) -> dict:
        """Load last checkpoint."""
        rows = list(self.bq.query(f"""
            SELECT checkpoint_data FROM `{self.table}`
            WHERE pipeline_id = '{pipeline_id}'
        """).result())
        return json.loads(rows[0].checkpoint_data) if rows else {}

# In Dataflow: checkpointing is built-in (auto-saves every 30s to GCS)
# In custom Spark jobs: save checkpoint to GCS after each partition completes
checkpoint = PipelineCheckpoint("project.monitoring.pipeline_checkpoints")
last_state = checkpoint.load("ad_events_daily")
start_from = last_state.get('last_processed_date', '2020-01-01')
```

---

### 2.5 Cost Architecture Patterns

```python
# PATTERN 1: Tiered storage
# Hot data (last 30 days): BigQuery STANDARD storage + high slot allocation
# Warm data (31-90 days): BigQuery STANDARD, reduced query priority
# Cold data (91+ days): BigQuery LONG_TERM storage (50% cheaper), or GCS NEARLINE
# Archive (1yr+): GCS COLDLINE or ARCHIVE

# PATTERN 2: Compute on demand
# Batch jobs: run only when needed (6 AM, 30 min duration)
# Streaming: always-on but right-sized (autoscaling enabled)
# Ad hoc: users get capped slot allocation (prevent runaway queries)

# PATTERN 3: Materialization strategy
# Raw tables: no aggregation, full data (used rarely — only for debug)
# Staging tables: clean, still full data (used by transformation)
# Mart tables: pre-aggregated, small, fast (used by BI every day)
# Pre-aggregation reduces BI query cost from TB → GB → MB

# Cost estimation formula for BigQuery:
# Monthly cost = (TB_scanned × $6.25) + (GB_stored × $0.02)
# Optimization lever: reduce TB_scanned (partition filters, marts)
```

---

## L3: Real-World Scenarios — CDM-Style Platform Design

### 3.1 Design: Cloud Data Movement Platform (Your CDM Next Experience)

This is your strongest card in the interview. Frame it as a system design answer.

**Problem statement**: Design a configuration-driven, cloud-native data movement platform that migrates 15+ PB of data from on-premises systems to GCP, supporting 60+ application teams, each with different schemas, SLAs, and security requirements.

**Requirements clarification**:
- Scale: 15 PB total, ~500 GB/day ongoing delta
- Teams: 60+ application teams, each owns their schemas
- Latency: batch (T+1 for most), T+15min for high-priority feeds
- Security: column-level PII masking, row-level access control
- Reliability: 99.9% pipeline availability, zero data loss
- Self-service: application teams configure their pipelines via YAML, no code required

**High-level architecture**:

```
Application Teams
    │ YAML config files (schema, SLA, transformation rules)
    ↓
Configuration Service (Git-backed config store)
    │
    ↓
Pipeline Orchestrator (Cloud Composer)
    │ generates DAGs from YAML configs
    ↓
┌──────────────────────────────────────────────┐
│            CDM Platform Core                  │
│                                              │
│  Ingestion Engine    Transform Engine        │
│  (Dataflow batch/    (Dataproc Spark +       │
│   stream connectors) DBT models)             │
│                                              │
│  Quality Gate        Security Engine         │
│  (DQ checks,         (DLP masking,           │
│   reconciliation)    column masking,         │
│                       row-level IAM)         │
└──────────────────────────────────────────────┘
    │
    ↓
GCP Storage (GCS + BigQuery)
    │ partitioned by app team + date
    ↓
Serving Layer
    ├── BigQuery (SQL analytics)
    ├── Vertex AI (ML models)
    └── APIs (downstream applications)
```

**Deep dive: Configuration-driven pipeline generation**:

```yaml
# Application team YAML config (example: Google Ads team)
pipeline:
  name: google_ads_clicks
  team: martech
  sla:
    type: batch
    schedule: "0 6 * * *"
    max_delay_hours: 2

  source:
    type: gcs
    bucket: costco-raw-ingestion
    path_pattern: "google_ads/clicks/{date}/*.parquet"

  schema:
    file: schemas/google_ads_clicks_v2.json
    evolution: append_new_columns    # or: fail, ignore

  transformations:
    - type: rename
      mappings:
        gclid: click_id
        cost_micros: cost_usd_micros
    - type: compute
      column: cost_usd
      expression: "cost_usd_micros / 1000000.0"
    - type: mask_pii
      columns: [user_ip]
      method: sha256_hash

  quality_checks:
    - column: click_id
      rule: not_null
      severity: ERROR
    - column: cost_usd
      rule: "value >= 0"
      severity: WARNING
    - type: row_count_anomaly
      z_score_threshold: 3.0

  destination:
    project: costco-data-platform
    dataset: martech_staging
    table: ad_clicks
    partition_by: click_date
    cluster_by: [campaign_id, channel]
```

```python
# Pipeline generator: reads YAML → generates Airflow DAG
class PipelineGenerator:
    def generate_dag(self, config: dict) -> DAG:
        """Generate Airflow DAG from YAML configuration."""
        with DAG(
            dag_id=config['pipeline']['name'],
            schedule_interval=config['pipeline']['sla']['schedule'],
            ...
        ) as dag:
            # Generate tasks from config
            ingest = self._create_ingest_task(config['source'])
            transform = self._create_transform_task(config['transformations'])
            quality_check = self._create_dq_task(config['quality_checks'])
            load = self._create_load_task(config['destination'])

            ingest >> transform >> quality_check >> load
            return dag
```

---

### 3.2 Design: Real-Time Campaign Performance Platform

**Requirements**: 100M ad events/day, <5 min latency for ROAS dashboard, 99.9% availability, handles 48h late data.

**Full architecture**:

```
Ad Platforms (Google, Meta, TikTok)
    │ API polling every 5 min OR webhook/Pub/Sub
    ↓
Cloud Pub/Sub Topics
  • raw-ad-events (all events)
  • raw-conversions (conversion events)
    │
    ↓ Split paths
    │
    ├──► REAL-TIME PATH (Dataflow Streaming)
    │       │ 5-min FixedWindows, 1hr allowed_lateness
    │       ↓
    │    BigQuery streaming.roas_realtime
    │       │ (preliminary, approximate)
    │       ↓
    │    Looker dashboard (shows as "preliminary")
    │
    └──► BATCH PATH (GCS landing)
            │ Dataflow also writes raw events to GCS
            │ gs://costco-data/raw/ad_events/date={date}/
            ↓
         Cloud Composer DAG (daily 6 AM)
            │ DBT run: stg → int → mart
            │ 3-day lookback window (handles 48h late data)
            ↓
         BigQuery mart.campaign_performance
            │ (authoritative, partition overwrite)
            ↓
         Looker dashboard (shows as "authoritative")
```

**Availability design**:
- Pub/Sub: Google SLA 99.95% → messages buffered 7 days → no data loss during outage
- Dataflow: auto-restarts from GCS checkpoint (< 5 min recovery)
- Cloud Composer: multi-zone, retry on failure, alert on SLA breach
- BigQuery: Google SLA 99.99% → always available

---

## L4: Hands-On Architecture Walkthroughs

### 4.1 Design a Data Platform for 1 PB/Day — Step by Step

**Step 1: Clarify requirements** (always start here in interview):
```
Q: What is the latency requirement?
A: Dashboard latency <1 hour; batch reports T+1

Q: What query patterns dominate?
A: Campaign performance by date+channel, member analytics, ad hoc exploration

Q: What's the team size?
A: 5 data engineers, 20 analysts

Q: Existing stack?
A: GCP-native, Google Ads + Meta Ads, BigQuery preferred

Q: Budget constraint?
A: Minimize cost, but reliability > cost
```

**Step 2: Scale estimation**:
```
1 PB/day raw events:
  = 1,000,000 GB / day
  = ~11.6 GB/sec peak
  = ~100K events/sec (assuming 100KB/event) — actually too large
  
Realistic: 1 PB/day at 1KB/event = 1 billion events/day
  = ~11,600 events/sec average, ~50,000/sec peak

BigQuery storage:
  1 PB raw × $0.02/GB/month = $20,000/month raw storage
  After Parquet compression (10:1): ~100 TB → $2,000/month
  Marts (aggregated, ~1%): ~1 TB → $20/month

Query cost:
  1000 queries/day × 100 GB avg scan = 100 TB/day × $6.25/TB = $625/day = $19K/month
  With partition filters + marts: 100 GB/day × $6.25 = $0.63/day = $19/month
  → Pre-aggregation is the highest-ROI optimization
```

**Step 3: High-level design**:
```
[Ad Platforms] → Pub/Sub → Dataflow → GCS (raw) → DBT/BigQuery (marts) → Looker
                                    ↘ BigQuery (streaming) for real-time
```

**Step 4: Deep dive — the ingestion bottleneck**:
- 50,000 events/sec → Pub/Sub throughput: handles millions/sec, no issue
- Dataflow: need ~50 workers at n1-standard-4 to process 50K/sec (each handles ~1000/sec)
- GCS writes: batch every 5 minutes → 50K × 5min × 60s = 15M events/file → large Parquet → efficient

**Step 5: Trade-offs**:
- Dataflow vs Kafka: Dataflow is serverless, auto-scales, no broker management → chose Dataflow
- Streaming vs batch: both paths → Lambda for accuracy + speed
- Snowflake vs BigQuery: already on GCP → BigQuery for native integration

---

### 4.2 Design a Configuration-Driven Pipeline Framework

```python
# Core design pattern: strategy pattern for pluggable connectors

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class PipelineConfig:
    name: str
    source_type: str        # 'gcs', 'bigquery', 'postgres', 'api'
    destination_type: str   # 'bigquery', 'gcs'
    schedule: str
    transformations: list
    quality_checks: list

class SourceConnector(ABC):
    @abstractmethod
    def read(self, config: dict, execution_date: str) -> Any:
        pass

class GCSSourceConnector(SourceConnector):
    def read(self, config: dict, execution_date: str):
        spark = SparkSession.builder.getOrCreate()
        path = config['path_pattern'].replace('{date}', execution_date)
        return spark.read.parquet(f"gs://{config['bucket']}/{path}")

class BigQuerySourceConnector(SourceConnector):
    def read(self, config: dict, execution_date: str):
        return spark.read.format('bigquery') \
            .option('table', config['table']) \
            .option('filter', f"date = '{execution_date}'") \
            .load()

class TransformationEngine:
    """Apply a list of transformation steps from config."""

    def apply(self, df, transformations: list):
        for transform in transformations:
            df = self._apply_one(df, transform)
        return df

    def _apply_one(self, df, transform: dict):
        transform_type = transform['type']

        if transform_type == 'rename':
            for old, new in transform['mappings'].items():
                df = df.withColumnRenamed(old, new)

        elif transform_type == 'compute':
            df = df.withColumn(
                transform['column'],
                F.expr(transform['expression'])
            )

        elif transform_type == 'mask_pii':
            for col in transform['columns']:
                method = transform.get('method', 'sha256_hash')
                if method == 'sha256_hash':
                    df = df.withColumn(col, F.sha2(F.col(col).cast('string'), 256))
                elif method == 'nullify':
                    df = df.withColumn(col, F.lit(None))

        elif transform_type == 'filter':
            df = df.filter(F.expr(transform['condition']))

        return df

class CDMPipeline:
    """Configuration-driven pipeline executor."""

    CONNECTORS = {
        'gcs': GCSSourceConnector,
        'bigquery': BigQuerySourceConnector,
    }

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.transformer = TransformationEngine()

    def run(self, execution_date: str):
        # 1. Extract
        connector = self.CONNECTORS[self.config.source_type]()
        df = connector.read(self.config.__dict__, execution_date)
        source_count = df.count()

        # 2. Transform
        df = self.transformer.apply(df, self.config.transformations)

        # 3. Quality check
        self._run_quality_checks(df, execution_date)

        # 4. Load
        df.write \
          .mode('overwrite') \
          .partitionBy('date') \
          .parquet(f"gs://costco-data/processed/{self.config.name}/")

        return {'source_count': source_count, 'status': 'SUCCESS'}

    def _run_quality_checks(self, df, execution_date: str):
        for check in self.config.quality_checks:
            # Run each check and raise on ERROR severity failures
            result = run_check(df, check)
            if not result.passed and check.get('severity') == 'ERROR':
                raise DataQualityError(f"Quality check failed: {result.message}")
```

---

## L5: Edge Cases, Bottlenecks & Trade-offs

### 5.1 The Small Files Problem

```python
# Problem: Spark writes one file per partition
# If 1000 partitions, each 1MB → 1000 small files
# GCS/HDFS metastore operations on 1000 files is slow
# BigQuery external table on 1000 tiny files is slow

# Detection:
files = list(gcs_client.list_blobs(bucket, prefix="output/"))
file_sizes = [f.size for f in files]
print(f"Min: {min(file_sizes)/1e6:.1f}MB, Max: {max(file_sizes)/1e6:.1f}MB, Count: {len(files)}")
# If most files < 10MB → small files problem

# Fix: coalesce before write to produce fewer, larger files
optimal_partitions = max(1, total_bytes // (128 * 1024 * 1024))  # target 128MB files
df.coalesce(optimal_partitions).write.parquet("gs://bucket/output/")

# For BigQuery partitioned tables: hive-style partitions, 1-2 files per partition
df.repartition(1, "event_date").write \
  .partitionBy("event_date") \
  .parquet("gs://bucket/output/")
# → one file per date partition → efficient BigQuery external table

# Use compaction job for long-running streaming:
# Daily: read all small files for yesterday, coalesce, write back as one large file
```

### 5.2 Schema Registry and Schema Evolution

```python
# Problem: producer adds a new column, consumer code breaks with KeyError
# At scale: 60+ pipelines, any schema change can break downstream

# Solution: centralized schema registry
# Avro/Protobuf schemas with version compatibility checks

# Schema evolution rules:
# BACKWARD compatible: new consumer can read old data
#   → adding a field with a default value is backward compatible
#   → removing a required field is NOT backward compatible

# FORWARD compatible: old consumer can read new data
#   → adding a field (even without default) is forward compatible if consumer uses get()

# FULL compatible: both backward and forward
#   → safest: only add optional fields with defaults

# Implementation in Pub/Sub with Avro:
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer

schema_registry_conf = {'url': 'https://schema-registry.costco.com'}
schema_registry_client = SchemaRegistryClient(schema_registry_conf)

# On publish: schema is serialized with message
# On consume: schema version is decoded from message prefix
# If schema is incompatible: consumer gets descriptive error, not silent data corruption
```

### 5.3 Multi-Tenancy in a Shared Platform

```python
# Problem: 60 application teams share one data platform
# Team A's expensive job shouldn't starve Team B

# Solution: resource quotas + slot reservations in BigQuery

# BigQuery: create separate reservations per team
# Team A (marketing): 500 slots reserved
# Team B (finance): 200 slots reserved
# Default pool: remaining slots, shared

# Spark/Dataproc: separate queues with capacity scheduler
# Queue: martech   → 40% cluster capacity
# Queue: finance   → 20% cluster capacity
# Queue: default   → 40% elastic

# Cost attribution: tag every BigQuery job with team label
bq_job_config = bigquery.QueryJobConfig(
    labels={'team': 'martech', 'pipeline': 'campaign_performance'}
)
# Monthly report: team X used Y TB → charged back to their cost center
```

---

## L6: Interview Questions — Easy to Very Hard

### EASY

**Q1: What is the difference between a data warehouse and a data lake?**

**Answer**: A data warehouse stores structured, processed data optimized for SQL analytical queries. Data is cleaned, transformed, and organized into schemas (fact and dimension tables). Example: BigQuery with mart tables.

A data lake stores raw data in its native format — structured (CSV, Parquet), semi-structured (JSON), or unstructured (images, logs). Data is stored cheaply at scale and processed when needed (schema-on-read). Example: GCS with raw event dumps.

The modern pattern is a data lakehouse — BigLake or Delta Lake — which combines the raw storage of a data lake with the query performance and governance of a data warehouse. Raw files in GCS, queryable via BigQuery external tables with partition pruning.

For Costco's MarTech: raw ad events land in GCS (data lake), DBT transforms them into BigQuery marts (data warehouse), Dataplex governs both (lakehouse governance).

---

### MEDIUM

**Q2: What is the CAP theorem and how does it apply to your pipeline design decisions?**

**Answer**: CAP theorem states that in a distributed system, you can guarantee only two of: Consistency (every read reflects the latest write), Availability (every request gets a response), and Partition tolerance (system works despite network failures). Since network partitions are inevitable in distributed systems, you always trade off between Consistency and Availability.

In data pipeline design: I choose AP (Availability + Partition tolerance) for event ingestion — Pub/Sub always accepts messages and delivers at-least-once, even if briefly inconsistent. Missing a message entirely is worse than briefly seeing stale data.

For marts and reports, I choose CP (Consistency + Partition tolerance) — the daily ROAS report must be correct, so I'll accept brief unavailability during a DBT run rather than show wrong numbers. BigQuery's transactional table updates are consistent.

The pattern: AP at the edge (event collection), CP at the core (analytical results).

---

**Q3: Walk me through how you'd design a system that processes 1 billion events per day and must deliver query results in under 5 seconds.**

**Answer**:

**Ingestion**: 1 billion events/day = ~11,500 events/sec. Pub/Sub handles this comfortably (scales to millions/sec). Events land in Pub/Sub.

**Processing**: Dataflow streaming reads from Pub/Sub, parses and validates events, writes to:
1. BigQuery streaming buffer (for near-real-time queries, available within seconds)
2. GCS Parquet files (for batch processing and replay)

**Storage design for 5-second queries**:
- DON'T query 1 billion raw events — that would scan TBs, too slow
- Build pre-aggregated mart tables: `mart_campaign_hourly` (1B events → ~10K aggregated rows per hour per campaign)
- Partition mart by report_date, cluster by campaign_id
- A query on the mart: ~10MB scan → sub-second

**The key insight**: 5-second query SLA is achieved through pre-aggregation, not by making raw queries faster. The serving layer query plan: BI tool queries mart (10MB) → BigQuery returns in 1-2 seconds. If a user needs individual events, that's an ad hoc query on raw data — accept the 30-60 second latency for that use case.

---

### HARD

**Q4: Design a data platform that serves 20 application teams, each with different data sources, SLAs, and security requirements. Teams should be able to onboard new data pipelines without engineering help. How do you build it?**

**What they're testing**: This is exactly your CDM Next experience. Structured platform thinking.

**Answer**:

**Core design philosophy**: Configuration-over-code. Teams describe WHAT they want in YAML; the platform handles HOW.

**Self-service onboarding flow**:
```
Team submits YAML config file via Git PR
  → Automated validation (schema check, SLA check, security policy check)
  → If valid: CI/CD generates Airflow DAG + DBT model + DQ checks automatically
  → Team gets a Slack notification: "Pipeline 'google_ads_clicks' is live"
  → No data engineering involvement required
```

**Platform components**:

1. **Config registry** (Git-backed): versioned YAML configs per pipeline. Git history = audit trail of every change.

2. **Config validator**: pydantic schema validation + business rule checks (e.g., all PII columns must declare masking strategy).

3. **Pipeline generator**: Jinja templates for Airflow DAGs + DBT models. Given a YAML config, generates boilerplate code.

4. **Ingestion connectors**: pluggable source connectors (GCS, Pub/Sub, Postgres, API). New source type = new connector class, no config changes.

5. **Security engine**: automatic PII detection (Cloud DLP), column-level masking for sensitive fields, row-level IAM based on team membership.

6. **Quality gate**: auto-generated DQ checks from config (not_null, uniqueness, range) + row count anomaly detection.

7. **Monitoring hub**: single dashboard showing all pipelines, SLA status, data freshness, quality scores.

**Multi-tenancy isolation**:
- BigQuery: separate datasets per team (`team_name_raw`, `team_name_staging`, `team_name_marts`)
- Slot reservations per team (marketing gets 500 slots, can't starve others)
- GCS: separate bucket paths per team + bucket-level IAM
- Airflow: separate task pools per team (limit concurrent runs per team)

**SLA enforcement**:
- Each pipeline declares its SLA (e.g., "must complete by 8 AM")
- Cloud Monitoring alert: if pipeline not GREEN by SLA time → PagerDuty
- SLA dashboard: real-time status of all pipelines

---

### VERY HARD

**Q5: Design a data platform for Costco that handles 1 PB/day, supports 99.9% availability, zero data loss, multi-region data residency (US + EU), costs under $100K/month, and can onboard a new data source within 2 hours. Walk through every architectural decision and trade-off.**

**What they're testing**: Enterprise-scale thinking, cost awareness, multi-region, self-service design.

**Answer**:

**Step 1: Requirements validation**
- 1 PB/day = 11.5 GB/sec = ~10M events/sec (at 100KB/event) or higher at smaller events
- 99.9% availability = max 8.7 hours downtime/year
- Zero data loss = durable buffering + checksums at every boundary
- US + EU data residency = physically separate pipelines per region
- $100K/month = significant but finite; need detailed cost model
- 2-hour onboarding = config-driven, automated

**Step 2: Regional architecture**

```
US Region                              EU Region
──────────────────────────            ──────────────────────────
Pub/Sub (us-central1)                 Pub/Sub (europe-west1)
  ↓                                     ↓
Dataflow (us-central1)                Dataflow (europe-west1)
  ↓                                     ↓
GCS (us multi-region)                 GCS (eu multi-region)
  ↓                                     ↓
BigQuery (dataset: location=US)       BigQuery (dataset: location=EU)
  ↓                                     ↓
Looker / Vertex AI                    Looker / Vertex AI
```

Non-PII aggregated data only crosses regions (for global executive dashboards):
```
BigQuery US marts → BigQuery Data Transfer → BigQuery EU (aggregated only, no PII)
```

**Step 3: Cost model for 1 PB/day**

```
GCS raw storage:
  1 PB/day × 30 days retention × $0.02/GB = $600K/month RAW → not feasible
  
Solution: compress to Parquet (10:1 ratio) → 100 TB/day
  100 TB × 30 days = 3 PB at $0.02/GB = $60K/month GCS

BigQuery:
  Raw tables: 30-day partition expiry, 3 PB = $60K/month
  After LONG_TERM storage discount (90+ days): $30K/month
  Marts: aggregated, ~0.1% of raw = 3 TB = $60/month
  Query cost: pre-aggregated queries, 100 GB/day = $625/day → $19K/month

Compute:
  Dataflow: 50 workers × $0.05/hour × 24h × 30 days = $1,800/month
  Dataproc batch: 4h/day × 100 workers × $0.04/hour × 30 days = $480/month
  Cloud Composer: $300/month
  Pub/Sub: $0.04 per 1M messages × 10B messages/day × 30 = $12K/month

Total estimate: ~$93K/month → within $100K target
```

**Step 4: Zero data loss design**

Every boundary has durability:
1. Producer → Pub/Sub: `acks='all'`, publisher retries with exponential backoff
2. Pub/Sub: Google replicates across 3+ datacenters, 7-day retention buffer
3. Dataflow → GCS: Dataflow checkpoints to GCS every 30s, auto-restarts from checkpoint
4. GCS: multi-region bucket, 99.999999999% durability (11 nines)
5. GCS → BigQuery: load job with `WRITE_TRUNCATE` per partition = idempotent
6. End-to-end checksum: source row count == BigQuery row count, validated daily

**Step 5: 2-hour onboarding**

```
Hour 0:00 - Team fills out YAML config (30 min)
Hour 0:30 - Submit PR → automated validation runs (5 min)
Hour 0:35 - PR auto-merges if valid → CI/CD generates and deploys pipeline (15 min)
Hour 0:50 - Pipeline first run: GCS sensor waits for data
            First data arrives → pipeline executes automatically
Hour 1:30 - Data visible in BigQuery → team queries and validates
Hour 2:00 - Looker dashboard connected → team presents first report
```

**Step 6: 99.9% availability design**

Failure points and mitigations:
- Pub/Sub: Google SLA 99.95% → buffering means no data loss during brief outage
- Dataflow: auto-restarts from GCS checkpoint (< 5 min RTO)
- BigQuery: Google SLA 99.99% → write pipeline might queue, but data is in Pub/Sub
- Cloud Composer: multi-zone, task retries, SLA alerts
- GCS: multi-region, transparent failover

Net availability: limited by the weakest link. With Pub/Sub 99.95% + Dataflow auto-restart:
effective data processing availability ≈ 99.92% → slightly under 99.9% at the pipeline level.

**To reach 99.9%**: implement multi-region Pub/Sub push replication (global topics), so even if us-central1 has an outage, events route to backup region's Dataflow pipeline.

---

## Summary: System Design — Senior Mastery Checklist

| Skill | What Senior Looks Like |
|-------|------------------------|
| Requirements gathering | Always clarifies scale, latency, availability, cost before designing |
| Scale estimation | Computes events/sec, storage cost, query cost from first principles |
| Lambda vs Kappa | Makes the right choice with explicit reasoning |
| Platform layers | Clear ingestion/transform/serve/govern separation |
| Fault tolerance | DLQ, circuit breaker, checkpoint/resume — not just "add retries" |
| CAP theorem | Applies it to real decisions (AP at edge, CP at core) |
| Cost modeling | Estimates monthly cost, identifies top levers, targets pre-aggregation |
| Config-driven design | Self-service onboarding, YAML config, pluggable connectors |
| Multi-tenancy | Slot reservations, dataset isolation, cost attribution per team |
| CDM-like platform | Can articulate your real experience as a system design answer |
