# Scalable Architecture & System Design — Complete Textbook
### Designing Petabyte-Scale Data Platforms, Migration Strategies, and Production-Grade Systems

---

## CHAPTER 1: SYSTEM DESIGN FUNDAMENTALS FOR DATA ENGINEERS

### 1.1 How to Approach a System Design Interview

Every design interview should follow this framework:

```
1. CLARIFY REQUIREMENTS (5 min)
   - Scale: rows/day, GB/day, peak TPS
   - Latency: real-time (<1s), near-real-time (<5 min), batch (hours)
   - Consumers: analysts, ML models, APIs, dashboards
   - SLAs: availability, freshness, accuracy
   - Constraints: regulatory, cost budget, existing infra

2. HIGH-LEVEL DESIGN (10 min)
   - Draw end-to-end data flow
   - Identify: sources, ingestion, storage, processing, serving
   - State architectural decisions and tradeoffs

3. DEEP DIVE (15 min)
   - Schema design and data modelling
   - Partitioning and clustering strategy
   - Fault tolerance and retry mechanisms
   - Scalability approach
   - Security and governance

4. BOTTLENECKS AND TRADEOFFS (5 min)
   - What breaks at 10x scale?
   - Cost implications
   - What you'd do differently with more time
```

### 1.2 Key Numbers Every Data Engineer Should Know

```
Throughput:
  BigQuery streaming insert:  up to 1 GB/s per table
  BigQuery batch load:        up to 15 TB per load job
  Pub/Sub:                    millions of messages/sec
  Kafka:                      100K–1M messages/sec per broker

Latency:
  BigQuery query start:       0.5–3 seconds cold start
  Pub/Sub end-to-end:         < 100ms
  Dataflow pipeline start:    2–5 minutes
  Bigtable row lookup:        < 10ms

Cost (approximate):
  BigQuery active storage:    $0.02/GB/month
  BigQuery long-term storage: $0.01/GB/month (90+ days unchanged)
  BigQuery queries:           $6.25/TB scanned
  GCS Standard:               $0.02/GB/month
  GCS Nearline:               $0.01/GB/month
  GCS Archive:                $0.004/GB/month

Scale reference:
  1 TB ≈ 5 billion rows at ~200 bytes/row
  BigQuery 3–5x compression → 15 PB raw ≈ 3–5 PB stored
```

### 1.3 Data Platform Architecture Layers

```
┌──────────────────────────────────────────────────────────┐
│  CONSUMPTION     BI Tools │ ML Models │ APIs │ Apps       │
├──────────────────────────────────────────────────────────┤
│  SERVING         BigQuery │ Bigtable │ Firestore          │
├──────────────────────────────────────────────────────────┤
│  PROCESSING      Dataflow │ Dataproc │ BigQuery SQL        │
├──────────────────────────────────────────────────────────┤
│  STORAGE         GCS (Raw/Staging/Curated) │ BQ datasets  │
├──────────────────────────────────────────────────────────┤
│  INGESTION       Pub/Sub │ Datastream │ Composer          │
├──────────────────────────────────────────────────────────┤
│  SOURCES         Teradata │ Oracle │ Hadoop │ Kafka │ APIs │
└──────────────────────────────────────────────────────────┘
```

---

## CHAPTER 2: BATCH PROCESSING ARCHITECTURES

### 2.1 Lambda Architecture

Two parallel paths — batch for accuracy, speed for low latency:

```
Sources
  ├──→ BATCH LAYER (Spark/Dataproc)
  │     Full historical reprocessing, high accuracy, hours latency
  │         ↓ Batch Views (BigQuery)
  │
  ├──→ SPEED LAYER (Dataflow/Pub/Sub)
  │     Recent data only, lower accuracy, minutes latency
  │         ↓ Real-time Views (Bigtable)
  │
  └──→ SERVING LAYER
        Merges batch + speed views to answer queries
```

**Pros:** Fault tolerant — batch layer reprocesses and corrects speed layer errors. Handles late data.
**Cons:** Two codebases for same logic; complex merge in serving layer.
**Use when:** Both historical accuracy and real-time freshness required.

### 2.2 Kappa Architecture

One streaming pipeline handles both real-time and historical:

```
Sources → STREAM PROCESSING (Dataflow/Flink)
           All data treated as a stream
           Historical reprocess = replay from Pub/Sub/Kafka
               ↓
           Serving Layer (BigQuery / Bigtable)
```

**Pros:** Single codebase, simpler operations, no merge logic.
**Cons:** Reprocessing large history as streams is slow/expensive.
**Use when:** Stream-first logic, historical reprocessing is rare.

### 2.3 Medallion Architecture (Modern Data Lake)

Data flows through quality tiers — the dominant pattern today:

```
BRONZE (Raw)
  - Exact copy of source, no transformation
  - Immutable after landing
  - Format: Parquet/Avro in GCS, partitioned by ingestion date
  - Purpose: full reprocessing source if transforms are wrong

SILVER (Cleaned)
  - Schema enforced, nulls handled, types corrected
  - Deduplication applied, PII masked
  - Join-ready, no business logic yet

GOLD (Curated)
  - Business logic applied
  - Dimensional model (facts + dimensions)
  - Aggregated summaries, optimised for query (partitioned, clustered)
  - What analysts and BI tools query
```

**CDM Next mapping:**
- Bronze: raw data from Teradata/Oracle/Hive landed in GCS
- Silver: CDM Next validation + standardisation in BigQuery staging datasets
- Gold: business-facing BigQuery datasets consumed by 60+ application teams

### 2.4 Incremental Loading Patterns

```
FULL LOAD
  Truncate target, reload all source data.
  Simple but expensive. Use for small dims, monthly snapshots.

INCREMENTAL APPEND
  Append only new rows since last high-watermark (MAX updated_at).
  Use for insert-only event tables (clicks, logs).
  Risk: misses updates and deletes.

INCREMENTAL MERGE (UPSERT)
  INSERT new rows + UPDATE changed rows + DELETE removed rows.
  Use BigQuery MERGE. Requires reliable changed_at column in source.

CHANGE DATA CAPTURE (CDC)
  Capture row-level changes from DB transaction logs.
  GCP: Datastream reads Oracle/MySQL/PostgreSQL redo logs.
  Near-real-time, lowest latency incremental loading.
  Mandatory for regulatory audit trails in banking.

PARTITION OVERWRITE
  Overwrite a specific date partition with fresh full-day data.
  Idempotent: re-running replaces, never duplicates.
  Most common pattern in CDM Next batch loads.
```

---

## CHAPTER 3: STREAMING ARCHITECTURE

### 3.1 Pub/Sub

```
Publisher → Pub/Sub Topic → Subscription → Subscriber (Dataflow, Cloud Functions)
```

**Key concepts:**
- **At-least-once delivery** — messages may be delivered multiple times; consumers must be idempotent
- **Message ordering** — guaranteed within a partition/ordering key
- **Retention** — up to 7 days (for replay)
- **Dead Letter Topic** — failed messages routed here after max delivery attempts

**Pub/Sub vs Kafka:**

| Feature | Pub/Sub | Kafka |
|---------|---------|-------|
| Operations | Fully managed | Self-managed |
| Replay | 7 days max | Configurable (unlimited) |
| GCP native integration | Yes | Via connector |
| Throughput | Auto-scales | Manual broker scaling |

### 3.2 Dataflow (Apache Beam)

Managed Apache Beam runner — both batch and streaming in one framework.

```python
import apache_beam as beam

with beam.Pipeline(options=options) as p:
    (p
     | 'Read'    >> beam.io.ReadFromPubSub(subscription='projects/proj/subscriptions/sub')
     | 'Parse'   >> beam.Map(json.loads)
     | 'Filter'  >> beam.Filter(lambda x: x.get('amount', 0) > 0)
     | 'Window'  >> beam.WindowInto(beam.window.FixedWindows(60))  # 60-sec windows
     | 'Sum'     >> beam.CombinePerKey(sum)
     | 'Write'   >> beam.io.WriteToBigQuery('project:dataset.table',
                        write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND)
    )
```

### 3.3 Windowing Strategies

```
FIXED (Tumbling):   [0:00–1:00][1:00–2:00][2:00–3:00]
  Non-overlapping, equal size. Use for hourly/daily aggregations.

SLIDING:            [0:00–0:30][0:15–0:45][0:30–1:00]
  Overlapping. Use for moving averages.

SESSION:            [events...30-min gap...][events...]
  Variable size based on activity gaps. Use for user sessions.
```

### 3.4 Handling Late Data

```python
beam.WindowInto(
    beam.window.FixedWindows(60),
    allowed_lateness=beam.window.Duration(seconds=600),  # wait 10 min for late data
    trigger=beam.trigger.AfterWatermark(
        early=beam.trigger.AfterCount(100),   # emit early after 100 events
        late=beam.trigger.AfterCount(10)       # re-emit after 10 more late events
    ),
    accumulation_mode=beam.trigger.AccumulationMode.ACCUMULATING
)
```

**Strategy decision:**
- Discard late data: simplest, some data loss — for non-critical metrics
- Wait for watermark: accurate but adds latency — for financial transactions
- Accumulating mode: re-emit updated results as late data arrives — for dashboards
- Dead letter queue: route very late data (>N hours) for manual review

---

## CHAPTER 4: GCP SERVICES — WHEN TO USE WHAT

### 4.1 Storage Decision Guide

```
BigQuery         → Analytics, data warehouse, OLAP, petabyte-scale
Bigtable         → Time-series, key-value, millisecond lookups, high write TPS
Cloud Spanner    → Global ACID transactions, distributed RDBMS
Firestore        → App document store, real-time sync
AlloyDB          → Managed PostgreSQL, pgvector for GenAI
Cloud SQL        → Standard managed MySQL/PostgreSQL

Decision questions:
  Need SQL analytics at scale?              → BigQuery
  Need < 10ms key-based lookups?            → Bigtable
  Need global ACID transactions?            → Spanner
  Need PostgreSQL compatibility?            → AlloyDB or Cloud SQL
```

### 4.2 Processing Decision Guide

```
BigQuery SQL     → ELT transforms on data already in BQ; no infra management
Dataflow         → Streaming + complex batch; exactly-once semantics
Dataproc         → Existing Spark/Hadoop workloads; ML feature engineering
Cloud Run        → Lightweight, event-driven, serverless; scale to zero
Cloud Functions  → Micro-triggers, webhooks, simple event handlers
```

### 4.3 Orchestration Decision Guide

```
Cloud Composer   → Complex DAGs, cross-system dependencies, enterprise scale
Cloud Workflows  → Simpler HTTP-based step execution, serverless
Cloud Scheduler  → Cron triggers only; cheapest option
```

---

## CHAPTER 5: PETABYTE-SCALE MIGRATION PLATFORM (CDM NEXT)

### 5.1 Full Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  CONFIG LAYER                                                      │
│  YAML config per source → Config Registry (BigQuery table)        │
│  Teams onboard via config — no code changes needed                 │
└────────────────────────────┬─────────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────────┐
│  ORCHESTRATION (Cloud Composer / Airflow)                          │
│  Config-driven DAG factory: reads registry → generates DAGs        │
│  Scheduling, retry, backfill, SLA monitoring                       │
└──────┬──────────────────────────────────────┬────────────────────┘
       ↓ Batch sources                        ↓ Streaming sources
┌──────────────┐                    ┌──────────────────────────────┐
│  EXTRACTION  │                    │  STREAMING                   │
│  Teradata    │                    │  Kafka → Pub/Sub             │
│  Oracle      │                    │  Dataflow → BigQuery         │
│  Hive/HDFS   │                    └──────────────────────────────┘
│  File sources│
└──────┬───────┘
       ↓
┌──────────────────────────────────────────────────────────────────┐
│  STAGING (GCS)                                                     │
│  Immutable Parquet/Avro files, partitioned by source/date/batch   │
└──────┬───────────────────────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────────────────────┐
│  VALIDATION                                                        │
│  Row count reconciliation │ Schema check │ DLP PII scan            │
│  Quarantine table for rejected records                             │
└──────┬───────────────────────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────────────────────┐
│  LOAD (BigQuery)                                                   │
│  GCS → BQ batch load │ Partition overwrite │ MERGE for SCD2       │
└──────┬───────────────────────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────────────────────┐
│  SECURITY & GOVERNANCE                                             │
│  IAM per team │ Cloud DLP masking │ Secret Manager │ VPC SC        │
│  Column-level security │ Audit logs                                │
└──────┬───────────────────────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────────────────────┐
│  OBSERVABILITY                                                     │
│  Audit table (every run) │ Dashboards │ Alerting │ Cloud Logging  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Configuration-Driven Design

```yaml
migration:
  source:
    type: teradata
    connection: tdprod-cluster
    database: FINANCE_DB
    table: CUSTOMER_MASTER
    extract_mode: incremental
    watermark_column: UPDATED_DATE

  target:
    project: wf-cdm-prod
    dataset: finance_prod
    table: customer_master
    write_mode: merge
    primary_key: [customer_id]
    partition_column: updated_date

  validation:
    row_count_tolerance_pct: 0.01
    required_columns: [customer_id, account_number]
    pii_columns: [ssn, date_of_birth, account_number]

  schedule:
    cron: "0 2 * * *"
    retry_count: 3

  notifications:
    on_failure: [team-data@wf.com]
```

The Airflow DAG factory reads this config and generates DAGs at runtime — no deployment needed for new sources. This is how 60+ teams onboarded without writing pipeline code.

### 5.3 Scalability Decisions

**Storage (15+ PB):**
- BigQuery is unlimited — no capacity planning
- Partitioning + clustering keeps query costs manageable
- Slot reservations for critical migration jobs

**Multi-tenancy (60+ teams):**
- Per-team BigQuery datasets with IAM isolation
- Slot reservation pools: high-priority prod pool, flex dev pool
- Config validation before DAG creation — bad configs fail fast
- Per-team dashboards in Cloud Monitoring

**Schema changes:**
- Schema registry table in BigQuery
- Pre-migration schema diff: fail on breaking changes
- Non-breaking changes (new nullable columns) handled automatically

---

## CHAPTER 6: REAL-TIME SYSTEMS DESIGN

### 6.1 Real-Time Transaction Monitoring (100K TPS)

**Requirements:** Payment ingest, fraud scoring < 500ms, reports < 5 min, years of history.

```
Payment Systems
    ↓
Pub/Sub Topics (one per source)
    ↓ (fan-out to parallel pipelines)
    ├── Dataflow: Fraud Scoring
    │   Parse → Enrich (customer lookup from Bigtable, < 10ms)
    │   → Score → Write decision to Bigtable
    │   → Publish to fraud-alerts topic
    │
    ├── Dataflow: Streaming Aggregation
    │   Parse → 5-min tumbling window
    │   → Aggregate by account/region/type
    │   → BigQuery streaming insert (5-min freshness)
    │
    └── GCS Sink (raw archive)
        For compliance retention + historical reprocessing

Bigtable: row key = {account_id}#{reversed_timestamp}
  → Reversed timestamp: latest events first (efficient recent lookups)
  → Avoids hotspotting on monotonically increasing keys

BigQuery: partitioned transactions table for analytics
```

### 6.2 Multi-Tenant Analytics Platform (Hub and Spoke)

```
CENTRAL PLATFORM HUB
  Shared infra: Composer, Dataflow, DLP, logging
  Services: config registry, onboarding, cost allocation
  Governance: Dataplex catalog, policy engine, audit

BUSINESS UNIT SPOKES (60+ datasets)
  BU_Finance:    dataset (IAM: finance team only)
  BU_Risk:       dataset (IAM: risk team only)
  BU_Operations: dataset
  ...

SHARED DATASETS
  enterprise_customer_master (all BUs read, platform writes)
  enterprise_reference_data

CROSS-BU SHARING VIA AUTHORISED VIEWS
  BU_Finance can query BU_Risk data via a view
  — no direct table access, full auditability
```

---

## CHAPTER 7: MIGRATION STRATEGIES

### 7.1 Teradata → BigQuery

**Phase 1: Assessment**
```
- Inventory: schemas, row counts, sizes, access patterns
- Dependency mapping: which tables feed which reports
- Complexity classification:
    Low:    flat tables, standard types
    Medium: TD-specific types (PERIOD), some macros
    High:   stored procedures, complex UDFs
- Priority order: high-value + low-complexity first
```

**Phase 2: Type Mapping**
```
Teradata          →  BigQuery
INTEGER           →  INT64
DECIMAL(p,s)      →  NUMERIC (financial) or BIGNUMERIC
VARCHAR(n)        →  STRING
DATE              →  DATE
TIMESTAMP         →  TIMESTAMP
PERIOD(DATE)      →  (split into start_date DATE, end_date DATE)
MULTISET tables   →  Add dedup step (BQ doesn't allow duplicates by policy)
```

**Phase 3: Incremental Migration Strategy**
```
1. Migrate full history in partitioned batches (by year)
2. Switch to incremental mode: sync daily deltas via watermark
3. Run in parallel 2 weeks: compare BQ vs TD output for same queries
4. Application team validates reports match
5. Cutover: application points to BigQuery
6. Keep TD table read-only 30 days (rollback safety net)
7. Decommission TD table
```

**Phase 4: Validation Queries**
```sql
-- Row count reconciliation
SELECT 'TD' AS sys, COUNT(*) AS rows FROM td_mirror
UNION ALL
SELECT 'BQ' AS sys, COUNT(*) AS rows FROM bq_target;

-- Financial checksum (must match exactly)
SELECT SUM(CAST(amount AS BIGNUMERIC)) AS total,
       COUNT(DISTINCT customer_id)    AS unique_customers
FROM target_table;

-- Sample spot check
SELECT * FROM target WHERE customer_id IN (
    SELECT customer_id FROM target TABLESAMPLE SYSTEM (0.001 PERCENT)
);
```

### 7.2 Hadoop/Hive → BigQuery

```
1. DistCp: copy HDFS → GCS (parallel, fast)
   hadoop distcp hdfs://namenode/warehouse gs://target-bucket/hive/

2. BigQuery load: Parquet/ORC directly loadable
   bq load --source_format=PARQUET project:dataset.table gs://bucket/*.parquet

3. Query rewrite: HiveQL → BigQuery SQL
   LATERAL VIEW EXPLODE → CROSS JOIN UNNEST
   FROM_UNIXTIME        → TIMESTAMP_SECONDS
   PERCENTILE_APPROX    → APPROX_QUANTILES

4. UDF rewrite: Hive Java UDFs → BigQuery JS UDFs or Python remote functions
```

---

## CHAPTER 8: COST OPTIMISATION

### 8.1 BigQuery Cost Levers

```
QUERY COST ($6.25/TB scanned):
  1. Partition pruning      → 100TB table, 1-day filter = 274GB scanned (99.7% savings)
  2. Column selection       → SELECT col1,col2 not SELECT * (columnar storage)
  3. Clustering             → 30–50% reduction within partitioned scans
  4. Materialised views     → Precompute repeated aggregations
  5. BI Engine              → In-memory cache for dashboard queries
  6. APPROX functions       → 100x faster for cardinality estimates
  7. require_partition_filter → Block full table scans

STORAGE COST ($0.02→$0.01/GB/month after 90 days):
  8. Partition expiration   → Auto-delete old partitions
  9. Table expiration       → Auto-delete temp/staging tables after 7 days
  10. GCS lifecycle rules   → Standard → Nearline → Archive tiering

SLOT COST:
  11. Slot reservations     → Commit to N slots (cheaper than on-demand for stable workloads)
  12. Flex slots            → Burst capacity for large one-time jobs
  13. Autoscaler            → Scale between min/max for variable workloads
```

### 8.2 Storage Tiering

```
HOT    BigQuery active storage    $0.02/GB/month    Last 90 days, frequently queried
WARM   BigQuery long-term         $0.01/GB/month    Auto at 90 days, fully queryable
COLD   GCS Nearline               $0.01/GB/month    Regulatory archive, rare access
FROZEN GCS Archive                $0.004/GB/month   Long-term compliance, BQ external tables
```

### 8.3 CDM Next Slot Strategy

```
Reservation pool 1: 'migration-prod'
  500 slots, 1-year standard commitment
  Assigned to: production migration jobs
  Priority: HIGH

Reservation pool 2: 'migration-dev'
  100 slots, flex
  Assigned to: dev/test/validation workloads
  Priority: LOW

On-demand: ad-hoc analyst queries, not assigned to any reservation
```

---

## CHAPTER 9: HIGH AVAILABILITY AND DISASTER RECOVERY

### 9.1 BigQuery HA

- Data automatically replicated across multiple AZs (no action needed)
- Multi-region option (US, EU, ASIA) replicates across multiple regions
- 99.99% SLA for queries
- **What you manage:** Composer HA mode, service account rotation, cross-region backup policy

### 9.2 Recovery Mechanisms

```sql
-- BigQuery Time Travel: query data as it was up to 7 days ago
SELECT * FROM orders
FOR SYSTEM_TIME AS OF '2024-01-15 00:00:00';

-- Table Snapshots: cheap point-in-time backup
CREATE SNAPSHOT TABLE backup.orders_snap_20240115
CLONE dataset.orders
FOR SYSTEM_TIME AS OF '2024-01-15 00:00:00';
-- Differential storage — only changed blocks stored
-- Restore: CREATE TABLE FROM SNAPSHOT

-- CDM Next DR posture:
-- RPO: 24 hours (re-run from yesterday's watermark)
-- RTO: 4 hours (reprovision Composer + restart pipelines)
```

---

## CHAPTER 10: OBSERVABILITY

### 10.1 Three Pillars

- **Metrics:** Success rate, rows/hour, slot utilisation, query latency → Cloud Monitoring dashboards
- **Logs:** Structured JSON per pipeline step → Cloud Logging → BigQuery for long-term analysis
- **Traces:** End-to-end latency tracking → Cloud Trace for distributed debugging

### 10.2 Pipeline Audit Table

```sql
CREATE TABLE pipeline_audit (
    run_id          STRING  NOT NULL,
    pipeline_name   STRING  NOT NULL,
    source_table    STRING,
    target_table    STRING,
    run_date        DATE    NOT NULL,
    start_time      TIMESTAMP NOT NULL,
    end_time        TIMESTAMP,
    status          STRING,   -- RUNNING | SUCCESS | FAILED | PARTIAL
    rows_extracted  INT64,
    rows_loaded     INT64,
    rows_rejected   INT64,
    error_message   STRING,
    metadata        JSON
)
PARTITION BY run_date
CLUSTER BY pipeline_name, status;
```

### 10.3 Alerting Tiers

```
TIER 1 — Immediate (PagerDuty):
  Production pipeline failed after all retries
  Data freshness > 26 hours (daily table not refreshed)
  Row count anomaly > 20% vs 7-day average
  DLP policy violation (PII in unprotected table)

TIER 2 — Business hours (Slack/Email):
  Pipeline duration > 2x normal
  Slot utilisation > 80% for > 30 minutes
  Schema drift detected

TIER 3 — Daily digest (Email):
  Cost anomaly > 20% above 30-day average
  Storage growth exceeding projection
  Daily pipeline run summary
```

---

*End of Scalable Architecture & System Design Textbook*
