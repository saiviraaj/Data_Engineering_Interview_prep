# MODULE 4: DATA PIPELINE ARCHITECTURES
## PhD-Level Data Engineering Interview Preparation
### Tailored for Viraaj Sivaraju — Senior Data Engineer, Wells Fargo CDM Next

---

## PART 1: LAMBDA ARCHITECTURE

### Overview

Lambda Architecture was proposed by Nathan Marz in 2011. It addresses the challenge of building large-scale, fault-tolerant systems with both low latency and accurate results.

```
┌─────────────────────────────────────────────────────────────────┐
│                     LAMBDA ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INPUT DATA ──────────────────────────┐                        │
│       │                               │                        │
│       ▼                               ▼                        │
│  ┌──────────┐                   ┌──────────┐                   │
│  │  BATCH   │                   │  SPEED   │                   │
│  │  LAYER   │                   │  LAYER   │                   │
│  │          │                   │          │                   │
│  │ Process  │                   │ Process  │                   │
│  │ ALL data │                   │ recent   │                   │
│  │ Accurate │                   │ data     │                   │
│  │ Slow     │                   │ Fast     │                   │
│  │ Rerun    │                   │ Approx   │                   │
│  │ corrects │                   │ Low lat  │                   │
│  └────┬─────┘                   └────┬─────┘                   │
│       │                              │                         │
│       ▼                              ▼                         │
│  ┌──────────┐                   ┌──────────┐                   │
│  │  BATCH   │                   │  REAL-   │                   │
│  │  VIEWS   │                   │  TIME    │                   │
│  │(BigQuery)│                   │  VIEWS   │                   │
│  │          │                   │(Bigtable)│                   │
│  └────┬─────┘                   └────┬─────┘                   │
│       │                              │                         │
│       └──────────────┬───────────────┘                         │
│                      ▼                                         │
│               ┌─────────────┐                                  │
│               │   SERVING   │                                  │
│               │    LAYER    │                                  │
│               │             │                                  │
│               │ Merge batch │                                  │
│               │ + realtime  │                                  │
│               │ results     │                                  │
│               └─────────────┘                                  │
└─────────────────────────────────────────────────────────────────┘
```

### How Lambda Works in Practice

```
BATCH LAYER:
  - Processes entire dataset (all historical + recent)
  - Runs periodically (hourly, daily)
  - Results are always 100% accurate (re-computes everything)
  - Slow — may take hours for 1TB+ datasets
  - Storage: BigQuery, GCS Parquet
  - Tools: Spark (Dataproc), Dataflow batch

SPEED LAYER:
  - Processes only data since last batch run
  - Runs continuously
  - Results are approximate (limited state, no full history)
  - Fast — seconds to minutes latency
  - Storage: Bigtable, Redis (expires with each batch run)
  - Tools: Dataflow streaming, Spark Streaming

SERVING LAYER:
  - Merges batch view (accurate) + speed view (recent)
  - Query: batch_result + incremental_from_speed_layer
  - Discards speed view results once batch catches up

EXAMPLE (revenue dashboard):
  Batch view (runs at 2 AM daily):
    revenue_by_region_2024_01_14 = $9,234,567 (accurate for Jan 14)
  
  Speed view (real-time):
    revenue_since_last_batch = $45,230 (from midnight to now)
  
  Serving layer returns:
    today's revenue = $9,234,567 + $45,230 = $9,279,797
```

### Lambda Pros and Cons

```
PROS:
  ✓ Fault tolerant: batch layer re-computes from immutable raw data
  ✓ Accurate: batch layer always correct (no windowing issues)
  ✓ Low latency: speed layer serves recent data immediately
  ✓ Mature: well-understood pattern, many implementations

CONS:
  ✗ Code duplication: same logic written twice (batch + streaming)
  ✗ Operational complexity: two systems to maintain, debug, monitor
  ✗ Reprocessing delays: batch layer runs hourly/daily → stale for analytics
  ✗ Serving layer complexity: merging batch + speed is non-trivial

CDM NEXT LAMBDA APPLICATION:
  CDM Next uses a lambda-like pattern:
  - Speed path: Kafka → Dataflow streaming → Bigtable (real-time risk profiles)
  - Batch path: Source DBs → Dataflow batch → GCS → BigQuery (daily analytical loads)
  - Serving: Risk APIs query Bigtable; analysts query BigQuery
  - Two separate code paths maintained by CDM Next platform team
```

---

## PART 2: KAPPA ARCHITECTURE

### Overview

Kappa Architecture (Jay Kreps, 2014) simplifies Lambda by eliminating the batch layer. The insight: if you can replay your stream, you can recompute any batch view by replaying with a new streaming job.

```
┌─────────────────────────────────────────────────────────────────┐
│                      KAPPA ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INPUT DATA                                                     │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────┐      ┌─────────────────────────────────────┐     │
│  │  KAFKA   │      │  STREAM PROCESSING (single path)    │     │
│  │  (durable│─────►│                                     │     │
│  │  log)    │      │  Version 1 job: current logic       │     │
│  │          │      │  Version 2 job: new logic (parallel)│     │
│  │  Retains │      │  → Run on same Kafka, different     │     │
│  │  7-365   │      │    consumer group, catch up         │     │
│  │  days    │      │  → Switch serving when caught up    │     │
│  └──────────┘      └────────────────┬────────────────────┘     │
│                                     │                           │
│                                     ▼                           │
│                              ┌──────────────┐                   │
│                              │   SERVING    │                   │
│                              │   (single    │                   │
│                              │   view)      │                   │
│                              └──────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

### Kappa Reprocessing Flow

```
REPROCESSING SCENARIO:
  You find a bug in your revenue calculation (January data wrong).
  
  LAMBDA approach:
    Fix batch job → re-run batch for January → wait hours → accurate results

  KAPPA approach:
    Step 1: Deploy V2 streaming job with new consumer group offset=Jan 1
    Step 2: V2 job reads from Kafka starting Jan 1 (Kafka has 90 days retention)
    Step 3: V2 job catches up to current time (takes ~hours for 3 months of data)
    Step 4: Once caught up: switch serving layer from V1 view to V2 view
    Step 5: Decommission V1 job
    
  RESULT: Bug fixed, no batch/streaming code duplication, one codebase.

KAPPA REQUIREMENTS:
  1. Message log with long retention (Kafka with 90-day+ retention, or infinite)
  2. Streaming framework handles both batch and real-time (Apache Beam/Dataflow)
  3. Sufficient compute to run historical replay at fast catch-up speed
```

### Kappa Pros and Cons

```
PROS:
  ✓ Single codebase: one streaming job handles both historical and real-time
  ✓ Simpler operations: one system to monitor/debug
  ✓ Consistent results: same code for batch and streaming → no discrepancies
  ✓ Easy reprocessing: run new version, catch up, switch

CONS:
  ✗ Requires durable log: Kafka with long retention (expensive)
  ✗ Reprocessing is slower: streaming replay vs optimized batch
  ✗ Complex windowing: harder to do monthly/yearly aggregations in streaming
  ✗ Pub/Sub limitation: only 7-day retention → not suitable for multi-month replay
  
CDM NEXT KAPPA FIT:
  Partially applicable where source is Kafka (on-premise).
  Not applicable for JDBC sources (Teradata/Oracle) — no durable log at source.
  For Kafka sources: CDM Next could run Kappa architecture.
  For JDBC sources: Must use Lambda (batch extraction, no event log to replay).
```

---

## PART 3: MEDALLION ARCHITECTURE (MOST RELEVANT FOR CDM NEXT)

### Overview

Medallion Architecture (popularized by Databricks) organizes data into quality tiers. This is the dominant pattern in modern cloud data lakes and most aligned with CDM Next.

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEDALLION ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SOURCE          BRONZE              SILVER              GOLD   │
│  SYSTEMS         (Raw)               (Cleaned)          (Curated)│
│                                                                 │
│  Oracle ─────►  gs://raw/            gs://processed/   BigQuery │
│  Teradata        oracle/             oracle/            finance. │
│  Kafka           accounts/           accounts/          accounts │
│  SFTP            dt=2024/            dt=2024/           _clean  │
│                  file.parquet        file.parquet               │
│                                                                 │
│                  CHARACTERISTICS:                               │
│                                                                 │
│  BRONZE:         SILVER:             GOLD:                      │
│  - Raw as-is     - Deduped           - Aggregated               │
│  - No transform  - Type-cast         - Business logic           │
│  - PII intact    - PII masked        - Denormalized             │
│    (if DLP       - Quality           - Optimized for            │
│    not yet run)    checked             consumption              │
│  - Immutable     - Schema            - Partitioned +            │
│  - Audit trail     enforced           clustered                 │
│  - Cheap storage - Append-only       - Materialized views       │
│                  - Incremental       - Served to analysts       │
└─────────────────────────────────────────────────────────────────┘
```

### CDM Next Medallion Implementation

```
BRONZE LAYER (gs://cdm-prod/raw/):
  gs://cdm-prod/raw/teradata/accounts/dt=2024-01-15/
    ├── accounts_00001.parquet  (original schema, no masking)
    ├── accounts_00002.parquet
    └── _metadata.json          (run_id, source, row_count, checksum)
  
  Properties:
    - Written once, never modified
    - Compressed but not transformed
    - Schema: exactly as extracted from source
    - Retention: 7 years (compliance)
    - DLP scan: queued (may run before or after landing)
  
  WHY KEEP RAW:
    - Audit: prove exactly what was extracted from source
    - Reprocessing: can re-derive silver/gold from bronze anytime
    - Debugging: when silver data is wrong, compare to bronze

SILVER LAYER (gs://cdm-prod/processed/ and BigQuery):
  BigQuery: project.finance_silver.accounts
  
  Transformations applied:
    - PII columns masked by DLP
    - Type coercions applied (DECIMAL(18,4) instead of VARCHAR)
    - Null handling applied
    - Schema enforced (extra columns removed)
    - Deduplication on primary key
    - Quality-failed rows written to quarantine (not silver)
  
  Properties:
    - APPEND-ONLY (new partition per day)
    - Never delete/update individual rows
    - Corrections via new partition with is_correction=true flag
    - Partitioned by ingestion_date

GOLD LAYER (BigQuery — consumed by analysts):
  BigQuery: project.finance.accounts_current
  
  Additional transformations:
    - Latest snapshot (deduplicate to one row per account)
    - Business rules applied (derived columns)
    - Joined with reference data (branch, region codes)
    - Aggregated tables (account summary by region)
    - Optimized partitioning + clustering for typical queries
  
  Properties:
    - Rebuilt nightly from silver layer
    - May be full refresh or incremental (depends on table)
    - Served via authorized views (IAM-controlled access)
    - Documented in Dataplex catalog
```

### Medallion vs Lambda/Kappa

| Dimension | Lambda | Kappa | Medallion |
|---|---|---|---|
| Primary goal | Low latency + accuracy | Simplicity | Data quality + governance |
| Data organization | By processing speed | By processing speed | By data quality tier |
| Reprocessing | Batch layer re-runs | Replay stream | Re-derive from bronze |
| Best for | Real-time + batch combo | Streaming-first systems | Data lake governance |
| CDM Next usage | Partial | Partial (Kafka sources) | Primary architecture |

---

## PART 4: DATA MESH

### Overview

Data Mesh (Zhamak Dehghani, 2019) is an organizational and architectural paradigm, not just a technology pattern.

```
CORE PRINCIPLES:

1. DOMAIN OWNERSHIP:
   Data is owned by the domain team that produces it.
   Finance team owns finance data.
   Risk team owns risk data.
   NOT: Central data team owns everything.

2. DATA AS A PRODUCT:
   Each domain treats its data as a product.
   Has an SLA, documentation, quality guarantees.
   NOT: Data dumps that consumers must clean themselves.

3. SELF-SERVE DATA PLATFORM:
   Platform team provides infrastructure.
   Domain teams use it without platform team involvement.
   CDM NEXT: Config-driven onboarding = self-serve.

4. FEDERATED GOVERNANCE:
   Global standards (schema format, PII handling, lineage).
   Local autonomy (implementation, schema specifics).
```

### Data Mesh vs CDM Next

```
CDM NEXT IS ALREADY PARTIALLY DATA MESH:

Data as Product:
  ✓ Each pipeline has defined SLA (freshness, availability)
  ✓ Data documented in Dataplex catalog
  ✓ Quality guarantees (automated checks)
  ✓ Ownership defined (source team + CDM platform team)

Self-Serve Platform:
  ✓ Config-driven onboarding (teams self-serve new pipelines)
  ✓ No code changes needed per new source
  ✓ Teams manage their own pipeline configs

Federated Governance:
  ✓ Global: DLP masking for all pipelines (enforced by platform)
  ✓ Global: Medallion naming conventions
  ✓ Local: Each team defines their quality rules
  ✓ Local: Each team manages their consumption models (dbt)

Domain Ownership:
  ~ Partial: Source teams own their source systems
  ~ Partial: CDM Platform team operates the pipelines
  ✗ Gap: Analytical tables still centrally owned by CDM team
    (true data mesh would have finance team own BigQuery finance datasets)
```

---

## PART 5: EVENT-DRIVEN ARCHITECTURE

### Event Sourcing

```
TRADITIONAL (state-based):
  Table: accounts
  Row: {acct_id: 123, balance: $500, status: ACTIVE}
  
  When balance changes: UPDATE accounts SET balance = 450 WHERE acct_id = 123
  History: LOST (no record of previous $500 balance)

EVENT SOURCING:
  Table: account_events (append-only)
  Events:
    {event_id: 1, acct_id: 123, type: ACCOUNT_OPENED, amount: 500}
    {event_id: 2, acct_id: 123, type: WITHDRAWAL, amount: 50}
    {event_id: 3, acct_id: 123, type: DEPOSIT, amount: 100}
  
  Current state = replay all events:
    $500 - $50 + $100 = $550 (current balance)
  
  State at any point in time = replay events up to that timestamp
  NEVER loses history

BENEFITS:
  - Complete audit trail
  - Time-travel queries
  - Debug by replaying
  - Multiple views from same event log

CDM NEXT RELEVANCE:
  CDM Next ingests events (transaction records, account updates) which are
  themselves event streams from source systems. The bronze layer in CDM Next
  acts as an event log — immutable, append-only, replayable.
```

### CQRS (Command Query Responsibility Segregation)

```
TRADITIONAL: Single model for reads and writes
  API → same database → reads and writes compete for resources

CQRS: Separate models for reads and writes
  Write side: optimized for writes (normalized, OLTP)
  Read side: optimized for reads (denormalized, cached, multiple projections)
  
  Event connects them:
    Write → Event → Read model updated asynchronously

CDM NEXT AS CQRS:
  WRITE SIDE: Source systems (Oracle, Teradata, Kafka)
    Optimized for transactions, normalized schemas
    
  CDM NEXT: The bridge
    Reads from write side → transforms → updates read side
    
  READ SIDE: BigQuery gold layer
    Optimized for analytics (denormalized, partitioned, clustered)
    Multiple projections of same data for different use cases
    (e.g., finance.accounts_by_customer vs finance.accounts_by_region)
```

---

## PART 6: INGESTION PATTERNS

### Full Load vs Incremental Load

```
FULL LOAD:
  - Read ALL data from source every run
  - Overwrite destination
  - Simple: no watermark, no state
  - Expensive for large tables
  - Required when source doesn't support change detection
  
  CDM NEXT FULL LOAD:
    - Small reference tables (< 1 million rows)
    - Tables without reliable watermark column
    - Weekly full refresh for reconciliation (even for incremental pipelines)

INCREMENTAL LOAD (delta/CDC):
  - Read only NEW or CHANGED records since last run
  - Requires: watermark column (updated_at, created_at, row_version)
  - Cheaper: only process changed data
  - Complex: watermark management, handling late updates
  
  CDM NEXT INCREMENTAL:
    WHERE LAST_UPDATED_DT > :last_watermark
    ORDER BY LAST_UPDATED_DT
    
    Watermark stored in Firestore:
    {
      "pipeline_id": "teradata-accounts-daily",
      "last_watermark": "2024-01-14T23:59:59Z",
      "last_run_id": "run-20240115-023045"
    }
    
    Updated ONLY on successful run completion.
    On failure: watermark not updated → next run reprocesses same data (safe — idempotent)

CDC (Change Data Capture):
  - Database-level change tracking (WAL, redo logs)
  - Every INSERT/UPDATE/DELETE captured as event
  - Tools: Debezium (open source), Striim, Datastream (GCP native)
  - Lowest latency: changes captured within seconds
  
  CDM NEXT CDC OPTION:
    For Oracle: Oracle LogMiner → Debezium → Kafka → CDM Next
    This captures every row change, not just latest state
```

### Extraction Strategies by Source Type

```
JDBC (Oracle, Teradata, MySQL):
  
  CHALLENGE: No built-in change tracking on many legacy tables
  
  STRATEGIES:
  1. Watermark column: WHERE updated_dt > last_watermark
     ✓ Simple, widely applicable
     ✗ Misses soft-deletes (deleted rows not captured)
     ✗ Requires reliable updated_dt column
  
  2. Row hash comparison: compare hash(all_columns) vs previous run
     ✓ Detects all changes including deletes
     ✗ Full scan of source (expensive)
     ✗ Requires storing previous run hashes
  
  3. Sequence/rowid: WHERE rowid > last_rowid
     ✓ Very efficient (indexed)
     ✗ Only works for append-only tables (new rows only)
  
  4. Source-side CDC (Oracle LogMiner):
     ✓ Captures all changes with minimal source impact
     ✗ Requires DBA access, Oracle licensing implications
  
  CDM NEXT DEFAULT: Strategy 1 (watermark column)
  CDM NEXT FOR DELETES: Weekly full reconciliation to catch deleted rows

HDFS/PARQUET FILES:
  - Read new files added since last run
  - File naming convention: dt=YYYY-MM-DD → date-based partitions
  - Incremental: only process new partitions
  - Distcp for initial bulk migration (Hadoop to GCS)

KAFKA TOPICS:
  - Consumer group maintains offset
  - No explicit watermark needed — Kafka offset is the watermark
  - Exactly-where-left-off on restart
  - CDM Next: Dataflow reads from Kafka, checkpoints to GCS

REST APIs:
  - Pagination: read page-by-page until no more results
  - Rate limiting: respect API rate limits (exponential backoff)
  - Cursor-based: use API's cursor/token for pagination
  - Time-based: ?since=last_timestamp
```

---

## PART 7: TRANSFORMATION PATTERNS

### ELT vs ETL

```
ETL (Extract → Transform → Load):
  Data extracted from source
  → Transformed in intermediate compute (Dataflow, Spark)
  → Clean data loaded into warehouse
  
  PROS: Data warehouse only sees clean data
  CONS: Transform layer is bottleneck; intermediate storage needed
  USE: When transform is complex (ML, custom logic); when loading to non-SQL store

ELT (Extract → Load → Transform):
  Data extracted from source
  → Loaded RAW into warehouse (BigQuery)
  → Transformed inside the warehouse (SQL/dbt)
  
  PROS: Leverage warehouse compute (BigQuery is fast at SQL)
        Raw data always available for re-transformation
        dbt models are version-controlled SQL
  CONS: Warehouse sees messy data; storage costs for raw
  USE: Cloud warehouses (BigQuery, Snowflake, Redshift); SQL-transformable data

CDM NEXT USES BOTH:
  CDM Next (ETL path):
    Source → [Dataflow: DLP masking, type coercion, quality checks] → GCS → BigQuery
    Why ETL here: DLP masking MUST happen before BigQuery (PII can't touch BQ)
  
  dbt (ELT path):
    BigQuery silver → [dbt SQL transforms] → BigQuery gold
    Why ELT here: Business logic best expressed in SQL; BQ handles compute
```

### dbt in the CDM Next Ecosystem

```
dbt (data build tool) manages the ELT transformation layer:
  
  WHAT dbt DOES:
    - Version-controlled SQL models (git)
    - Dependency management (model A depends on model B)
    - Testing (assert not null, unique, referential integrity)
    - Documentation generation
    - Incremental models (only process new data)
    - Materialization strategies (table, view, incremental, ephemeral)
  
  EXAMPLE dbt MODEL:
  -- models/gold/accounts_current.sql
  {{ config(
      materialized='incremental',
      partition_by={'field': 'ingestion_date', 'data_type': 'date'},
      cluster_by=['account_type', 'region'],
      unique_key='account_id'
  ) }}
  
  SELECT
      a.account_id,
      a.customer_id,
      a.account_type,
      a.balance,
      a.status,
      r.region_name,
      r.region_code,
      DATE(a.last_updated_ts) AS ingestion_date
  FROM {{ ref('accounts_silver') }} a
  LEFT JOIN {{ ref('dim_regions') }} r ON a.region_code = r.region_code
  
  {% if is_incremental() %}
  WHERE DATE(a.last_updated_ts) >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 DAY)
  {% endif %}
  
  CDM NEXT dbt INTEGRATION:
    Cloud Composer → dbt run → BigQuery gold tables
    Schedule: after silver layer loads complete
    On failure: dbt test failures halt promotion to gold
```

---

## PART 8: SERVING PATTERNS

### Batch Serving

```
PRE-COMPUTED RESULTS:
  Run heavy computation nightly → store results → serve queries from results
  
  WHEN TO USE:
    - Complex aggregations over full history (run time: hours)
    - Results needed < 1 second (pre-computed = instant)
    - Same query run by many users
  
  CDM NEXT EXAMPLE:
    Nightly: Compute monthly_revenue_by_region_branch for last 5 years
    Store in: BigQuery analytics.monthly_revenue (100M rows, ~50GB)
    Serve: Dashboard queries this table → sub-second response
    
    Alternative (without pre-computation): Query 15PB raw → minutes wait
```

### Real-Time Serving

```
POINT LOOKUPS (sub-10ms requirement):
  Source: Bigtable
  Pattern: customer risk profile by customer_id
  
RECENT AGGREGATIONS (< 1 second):
  Source: BigQuery BI Engine (in-memory)
  Pattern: revenue last 24 hours by region
  
FULL ANALYTICAL QUERIES (seconds):
  Source: BigQuery standard (slot-based)
  Pattern: ad-hoc SQL over months of data

CDM NEXT SERVING LAYER DECISION TREE:
  
  Is latency < 10ms?
    YES → Bigtable (point lookup by key)
    NO  → Is data < 7 days old AND query is simple?
            YES → BigQuery BI Engine
            NO  → Is query pre-computable?
                    YES → BigQuery materialized view
                    NO  → BigQuery standard query
```

---

## MODULE 4 SUMMARY

| Architecture | Best For | CDM Next Usage |
|---|---|---|
| Lambda | Real-time + batch accuracy | Streaming risk + batch analytics |
| Kappa | Kafka-sourced, streamable logic | Kafka source pipelines |
| Medallion | Data quality, governance, analytics | Primary architecture (bronze/silver/gold) |
| Data Mesh | Org-scale data ownership | Partially implemented (self-serve onboarding) |
| Event-Driven | Audit trail, time-travel | Source system events; bronze as event log |
| CQRS | Separate read/write optimization | Source systems (write) + BigQuery (read) |
| ELT | Cloud warehouse SQL transforms | dbt models on top of silver layer |
| ETL | Non-SQL transforms, PII masking | Dataflow masking + quality checks |

---

*Module 4 Complete — ~9,200 words.*
