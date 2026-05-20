# MODULE 3: CRITICAL DESIGN PRINCIPLES
## PhD-Level Data Engineering Interview Preparation
### Tailored for Viraaj Sivaraju — Senior Data Engineer, Wells Fargo CDM Next

---

## PART 1: SCALABILITY PATTERNS

### The Scalability Pyramid

```
                    ┌─────────────┐
                    │  SHARDING   │  ← Split data across nodes
                    ├─────────────┤
                    │  CACHING    │  ← Avoid redundant computation
                    ├─────────────┤
                    │  ASYNC      │  ← Decouple producers/consumers
                    ├─────────────┤
                    │ REPLICATION │  ← Distribute reads
                    ├─────────────┤
                    │  STATELESS  │  ← Enable horizontal scaling
                    └─────────────┘
                    (Build bottom-up)
```

### Stateless Design — The Foundation

```
STATELESS SERVICE:
  - Each request contains all information needed to process it
  - Service holds no session state between requests
  - Any instance can handle any request
  - Scale by adding instances behind load balancer
  
STATEFUL SERVICE (avoid when possible):
  - Service holds state between requests (session, cache, lock)
  - Specific requests must go to specific instances
  - Harder to scale, harder to fail over

MAKING STATELESS WORK:
  State that must exist:
    - Session data → store in Redis/Firestore (externalize)
    - User context → encode in JWT token (client-side)
    - Processing position → store in Firestore watermark (externalize)
  
  CDM NEXT STATELESS DESIGN:
    - Dataflow templates are stateless at the job level
    - Pipeline config read from Firestore at startup (not hardcoded)
    - Watermarks stored in Firestore (not in-memory)
    - Any new Dataflow worker can pick up from last watermark
    - Worker failure → auto-replace with fresh worker, reads same config
```

### Asynchronous Processing

```
SYNCHRONOUS (tight coupling):
  Client → API → [process immediately] → Response
  
  Problem: Client waits for entire processing
  Problem: Processing spike blocks all clients
  Problem: If processing fails, client request fails

ASYNCHRONOUS (loose coupling):
  Client → API → Queue → Response("accepted")
                 ↓
          Worker pool → [process when capacity available]

BENEFITS:
  - Client gets immediate acknowledgment
  - Processing can scale independently
  - Failures isolated (retry from queue)
  - Peaks absorbed by queue

CDM NEXT ASYNC DESIGN:
  - Application team submits pipeline config (immediate ACK)
  - Cloud Composer DAG scheduled asynchronously
  - Pipeline runs in background (Dataflow job)
  - Results written to BigQuery
  - Notification sent on completion
  
  None of this blocks the application team's systems.
```

### The Fan-Out Pattern

```
FAN-OUT: One input → multiple parallel outputs

Use case: After ingesting a transaction, simultaneously:
  1. Write to BigQuery (analytics)
  2. Update Bigtable risk profile
  3. Publish to audit topic
  4. Update data catalog (Dataplex)
  5. Increment monitoring counters

NAIVE (sequential):
  ingest → write_bq → update_bigtable → publish_audit → update_catalog
  Total latency: 10ms + 5ms + 50ms + 30ms = 95ms

FAN-OUT (parallel):
  ingest → ┬── write_bq (10ms)
           ├── update_bigtable (5ms)
           ├── publish_audit (50ms)
           └── update_catalog (30ms)
  Total latency: max(10, 5, 50, 30) = 50ms
  
  ALSO: If one output fails, others can succeed
  (partial success is often better than total failure)

BEAM IMPLEMENTATION:
  enriched_events = pipeline | "Enrich" >> beam.ParDo(EnrichDoFn())
  
  # Fan-out to multiple sinks in parallel
  enriched_events | "WriteBQ" >> beam.io.WriteToBigQuery(BQ_TABLE)
  enriched_events | "UpdateBigtable" >> beam.ParDo(BigtableWriteDoFn())
  enriched_events | "PublishAudit" >> beam.io.WriteToPubSub(AUDIT_TOPIC)
  # All three run concurrently — Beam handles parallelism
```

---

## PART 2: HIGH AVAILABILITY PATTERNS

### Active-Passive Failover

```
ACTIVE-PASSIVE:
  
  NORMAL:           FAILURE:
  Client            Client
    │                 │
  [PRIMARY] ●       [PRIMARY] ✗ (down)
  [STANDBY] ○       [STANDBY] ● (promoted)
  
  PRIMARY handles all traffic.
  STANDBY replicates but serves nothing.
  On primary failure: standby promoted (RTO = promotion time)

TYPES:
  Hot standby: standby fully synchronized, seconds to fail over
  Warm standby: standby slightly behind, minutes to catch up + fail over
  Cold standby: standby not running, must start + restore, hours to fail over

CDM NEXT CLOUD COMPOSER HA:
  Cloud Composer 2 uses GKE Autopilot → multi-zone by default
  Scheduler: 2 replicas (active-passive HA)
  Workers: GKE auto-heals failed pods
  Database: Cloud SQL with automatic failover to hot standby
  Effective RTO: < 2 minutes for scheduler failure
```

### Active-Active

```
ACTIVE-ACTIVE:
  
  Client
    │
  Load Balancer
  ├── [SERVER A] ● (handles 50%)
  └── [SERVER B] ● (handles 50%)
  
  Both servers handle traffic simultaneously.
  On failure of A: load balancer routes all traffic to B.
  
  REQUIRES:
  - Stateless services (no session state)
  - Or: shared state store (Redis cluster, Spanner)
  - Or: sticky sessions (same client → same server)
  
  BENEFIT: No failover delay; immediate redundancy
  COMPLEXITY: Consistency of shared state

MULTIREGIONAL ACTIVE-ACTIVE FOR CDM NEXT:
  GCS multi-region: data replicated to multiple regions
  BigQuery multi-region datasets: query from any region
  Cloud Composer: single region (multi-region Composer not available)
  → CDM Next is single-region active, with GCS/BQ as multi-region storage
```

### Circuit Breaker Pattern

```
PROBLEM: If downstream service is slow/down, callers wait and pile up
         → Caller exhausts connection pool
         → Caller also goes down (cascade failure)

CIRCUIT BREAKER:
  
  CLOSED (normal):
    All requests pass through
    Track failure rate
    
  OPEN (tripped):
    Triggered when failure rate > threshold (e.g., 50% in 10s)
    All requests FAIL FAST (don't even attempt)
    After timeout: → HALF-OPEN
    
  HALF-OPEN (testing recovery):
    Let a few requests through
    If they succeed: → CLOSED
    If they fail: → OPEN

CDM NEXT APPLICATION:
  When calling external source system (Teradata/Oracle):
  - Closed: normal JDBC reads
  - Open after 3 consecutive timeouts: fail pipeline immediately
  - Log circuit open → alert team → source system team notified
  - After 30 min: half-open, retry connection
  
  Effect: Pipeline fails fast instead of hanging for hours.
          Releases Dataflow workers for other pipelines.
```

### Bulkhead Pattern

```
PROBLEM: One slow consumer uses all resources, starving others

BULKHEAD (from ship compartments):
  Isolate resources per consumer/service
  
  WITHOUT BULKHEAD:
    60 pipelines share 100 Dataflow workers
    Pipeline A gets stuck, uses all 100 workers
    59 other pipelines starve → SLA breach for everyone
    
  WITH BULKHEAD (BigQuery Reservations):
    Finance pipelines: 200 dedicated slots
    Risk pipelines: 150 dedicated slots
    Marketing pipelines: 100 dedicated slots
    Default pool: 50 slots (for everything else)
    
    Finance pipeline going wild: uses max 200 slots
    Risk + Marketing unaffected: still have their dedicated slots
```

---

## PART 3: PERFORMANCE OPTIMIZATION PRINCIPLES

### Data Locality

```
PRINCIPLE: Move computation to data, not data to computation.

BAD: 
  Read 1TB from GCS → Send to API server for processing → Write results
  (1TB travels twice over the network)
  
GOOD (BigQuery pushdown):
  Run SQL on BigQuery where data lives
  Only results (KB-MB) travel over network
  
CDM NEXT PRINCIPLE:
  - Transformations run in Dataflow workers co-located with GCS data
  - BigQuery transformations (dbt) run inside BigQuery
  - Avoid pulling data out of BigQuery for transformation — push SQL instead
```

### Read/Write Amplification

```
WRITE AMPLIFICATION:
  One logical write causes multiple physical writes
  
  Example: LSM-tree (used in Bigtable, Cassandra):
    Write → MemTable (in memory)
    MemTable full → flush to SSTable on disk
    Too many SSTables → compaction → merge into larger SSTable
    
    One logical write may trigger 10 physical writes during compaction
    
  MITIGATION: Batch writes, tune compaction settings, use right storage engine

READ AMPLIFICATION:
  One logical read causes multiple physical reads
  
  Example: Reading from multiple SSTables before compaction
    Read 1 key → check MemTable → check SSTable1 → check SSTable2 → ...
    
  MITIGATION: Bloom filters (quickly reject SSTables that don't contain key)
              Bigtable handles this automatically

CDM NEXT: 
  Using BigQuery's columnar format eliminates read amplification for analytics
  (only relevant columns read, not entire rows)
```

### Batching vs Streaming Tradeoffs

```
BATCHING:
  Advantages:
    - Higher throughput (amortize per-request overhead across batch)
    - Better compression (more data → better compression ratio)
    - Lower cost (BigQuery load jobs free; streaming inserts cost money)
    - Simpler error handling (retry entire batch)
    
  Disadvantages:
    - Higher latency (data sits in batch until flush)
    - More memory needed (hold batch in memory)
    - Larger failure units (entire batch fails together)
    
  CDM NEXT Batch: 100TB/day in 4-hour windows using Dataflow

STREAMING:
  Advantages:
    - Low latency (seconds to minutes)
    - Smaller memory footprint (process one event at a time)
    - Earlier error detection (catch bad data immediately)
    
  Disadvantages:
    - Lower throughput per worker
    - More complex state management
    - Higher cost at scale (BigQuery streaming inserts: $0.01/200MB)
    
  CDM NEXT Streaming: Used for fraud/risk real-time feeds only
```

---

## PART 4: DATA CONSISTENCY PATTERNS

### Saga Pattern (Distributed Transactions)

```
PROBLEM: ACID transactions don't span multiple microservices/databases
         How do you maintain consistency across CDM Next pipeline + BQ + Bigtable?

SAGA: A sequence of local transactions, each publishing an event/message
      that triggers the next transaction. On failure, compensating transactions
      undo completed steps.

CDM NEXT SAGA (Pipeline Execution):

  Step 1: Config validation (Firestore read)
            ✓ → Proceed
            ✗ → Abort (no side effects yet)
  
  Step 2: Source extraction to GCS staging
            ✓ → Proceed
            ✗ → Compensate: delete GCS staging files
  
  Step 3: DLP masking + quality check
            ✓ → Proceed
            ✗ → Compensate: delete GCS files, mark run failed
  
  Step 4: BigQuery load
            ✓ → Proceed
            ✗ → Compensate: delete GCS files, truncate BQ partition if partial
  
  Step 5: Watermark update (Firestore)
            ✓ → Success
            ✗ → Compensate: will re-run from previous watermark (idempotent)

Each step is idempotent → re-running is safe
Compensation at each step → no orphaned partial data
```

### Idempotency — Critical Design Pattern

```
IDEMPOTENT OPERATION: Performing it N times has same effect as 1 time.

WHY IT MATTERS:
  Networks are unreliable. Retries are necessary.
  Without idempotency: retry = duplicate data / double charge / inconsistency
  With idempotency: retry = safe (same result)

MAKING OPERATIONS IDEMPOTENT:

  Database writes:
    NOT idempotent: INSERT INTO table VALUES (...)
      → Retry creates duplicate row
    
    IDEMPOTENT (upsert):
      INSERT INTO table VALUES (...) ON CONFLICT (id) DO NOTHING
      → Retry ignored if row exists
    
  API calls:
    NOT idempotent: POST /payments (creates new payment each call)
    IDEMPOTENT: POST /payments with idempotency_key header
      → Server stores key + result; duplicate request returns cached result
    
  BigQuery loads:
    NOT idempotent: WRITE_APPEND without job_id control
      → Retry appends duplicate data
    
    IDEMPOTENT: Deterministic job_id
      → BQ rejects duplicate job_id submissions

CDM NEXT IDEMPOTENCY DESIGN:
  GCS file naming: {pipeline_id}/{date}/{watermark_hash}.parquet
    → Same run always writes to same path → OVERWRITE, not duplicate
  
  BigQuery job_id: sha256(pipeline_id + watermark_start + watermark_end)
    → Retried job uses same job_id → BQ ignores duplicate
  
  Watermark update: overwrite, not append
    → Always reflects latest successful state
```

---

## PART 5: RELIABILITY ENGINEERING

### Error Budget and SLOs

```
SLO (Service Level Objective):
  Internal target for reliability.
  Example: 99.9% of pipeline runs complete successfully.

SLA (Service Level Agreement):
  External commitment with consequences for breach.
  Example: Contract with business teams.

SLI (Service Level Indicator):
  The actual metric being measured.
  Example: successful_runs / total_runs over 30 days.

ERROR BUDGET:
  The allowed "failure" within your SLO.
  
  99.9% SLO over 30 days:
    Total minutes: 43,200
    Allowed downtime: 43,200 × 0.001 = 43.2 minutes
    
  CDM NEXT SLOs:
    Batch pipeline success rate: 99.5%
    Streaming end-to-end latency P99: < 120 seconds
    Daily data freshness: < 4 hours from source
    
  When error budget is consumed:
    - Freeze feature development
    - Focus 100% on reliability
    - Post-mortem required
```

### Chaos Engineering

```
PRINCIPLE: Deliberately inject failures to find weaknesses before they matter.

CDM NEXT CHAOS SCENARIOS:
  
  Level 1 (Low blast radius):
    - Kill one Dataflow worker mid-job
      Expected: Job auto-restarts worker, continues from checkpoint
    
    - Inject latency on GCS reads (100ms delay)
      Expected: Dataflow handles gracefully, throughput reduced but no failure
  
  Level 2 (Medium blast radius):
    - Bring down source DB connection for 5 minutes
      Expected: Circuit breaker trips, pipeline fails cleanly, alert fires
    
    - Corrupt one GCS staging file
      Expected: Data quality check catches it, file quarantined, pipeline continues
  
  Level 3 (High blast radius — GameDay only):
    - Take down Cloud Composer for 30 minutes
      Expected: No pipelines run, backlog builds, auto-recovery on Composer restart
    
    - Simulate GCS bucket unavailability
      Expected: Pipelines fail, data in Pub/Sub retained, pipelines replay on recovery
```

### Runbook Design

```
EVERY CRITICAL ALERT should have a runbook:
  
  ALERT: cdm_watermark_lag > 3600 (data lag > 1 hour)
  
  RUNBOOK:
  Step 1: Check Dataflow job status
    → cloud.google.com/dataflow → check job {pipeline_id}
    → Is job RUNNING? If FAILED: go to step 4
    
  Step 2: Check Pub/Sub backlog
    → Cloud Monitoring → Pub/Sub → subscription/{pipeline_id}-sub
    → If backlog > 1M messages: Dataflow overwhelmed → add workers (step 3)
    → If backlog = 0: source not producing → check source system
    
  Step 3: Add workers
    → gcloud dataflow jobs update-options --max-workers=200 --job-id={job_id}
    → Monitor: backlog should decrease within 10 minutes
    
  Step 4: Restart failed job
    → Check job error in Cloud Logging (filter: resource.type=dataflow_job)
    → Common errors and fixes: [link to error guide]
    → Re-trigger DAG: Composer → {pipeline_id}_dag → trigger
  
  ESCALATION:
    After 30 min without resolution: page {team-lead}
    After 60 min: involve {source-system-team}
    SLA breach threshold: 4 hours data lag
```

---

## PART 6: DATA MANAGEMENT PRINCIPLES

### Data Contracts

```
A DATA CONTRACT is a formal agreement between data producers and consumers:
  - Schema: column names, types, nullability
  - Semantics: what each field means
  - SLA: freshness, availability
  - Ownership: who maintains this data
  - Breaking change policy: how changes are communicated

CDM NEXT DATA CONTRACT EXAMPLE:
  Dataset: finance.accounts_clean
  Owner: CDM Platform Team + Finance Data Team
  Schema version: v3.2
  
  SLA:
    Freshness: Updated daily by 06:00 UTC
    Availability: 99.9%
    Historical coverage: 2015-present
    
  Schema:
    acct_id: STRING NOT NULL (primary key)
    customer_id: STRING NOT NULL
    acct_type: STRING (CHECKING | SAVINGS | LOAN)
    balance: NUMERIC(18,4) — always in USD
    status: STRING (ACTIVE | CLOSED | FROZEN)
    open_date: DATE
    last_updated_dt: TIMESTAMP
    
  Breaking change policy:
    - Column additions: 2-week notice
    - Column renames: 4-week notice + migration support
    - Column removals: 8-week notice + migration support
    - Type changes: 8-week notice + validation
```

### Data Lineage Principles

```
COLUMN-LEVEL LINEAGE:
  Not just "Table A feeds Table B"
  But: "Table B.revenue = SUM(Table A.order_amount WHERE status='COMPLETE')"
  
  Required for:
    Impact analysis: "if I change Table A.order_amount, what else breaks?"
    Root cause: "Table B.revenue is wrong — which source column is bad?"
    Compliance: "which tables contain PII derived from customer.ssn?"

CDM NEXT LINEAGE CAPTURE:
  OpenLineage events emitted on every pipeline run:
    Source: oracle://prod-db/ACCOUNTS
    Transform: cdm-next/accounts_daily_ingest
    Destination: bigquery://project/finance.accounts_clean
  
  Column mapping:
    acct_id ← ACCT_ID (direct copy)
    balance ← BALANCE (type-cast DECIMAL to NUMERIC)
    status ← ACCT_STATUS (renamed)
    [PII columns masked by DLP — not propagated]
  
  Stored in: Dataplex (GCP-native lineage)
  Queryable: Dataplex Lineage API for impact analysis
```

### Data Quality Dimensions

```
COMPLETENESS: Is all expected data present?
  Metric: null_rate per column
  CDM NEXT check: COUNTIF(acct_id IS NULL) / COUNT(*) = 0

ACCURACY: Does data correctly represent reality?
  Metric: business rule validation
  CDM NEXT check: balance >= 0 for all ACTIVE accounts

CONSISTENCY: Does data agree across systems?
  Metric: referential integrity, cross-system comparison
  CDM NEXT check: every customer_id in accounts exists in customers table

TIMELINESS: Is data fresh enough for its intended use?
  Metric: age of latest record vs expected freshness
  CDM NEXT check: MAX(last_updated_dt) >= CURRENT_DATE - 1

UNIQUENESS: Are there duplicate records?
  Metric: duplicate rate on primary key
  CDM NEXT check: COUNT(*) = COUNT(DISTINCT acct_id)

VALIDITY: Does data conform to defined formats?
  Metric: format validation
  CDM NEXT check: acct_type IN ('CHECKING', 'SAVINGS', 'LOAN')
```

---

## PART 7: COST OPTIMIZATION PRINCIPLES

### The Cost Hierarchy in Cloud Data Platforms

```
COST SOURCES (highest to lowest typically):
1. Compute: Dataflow workers, Dataproc clusters
2. Storage: GCS, BigQuery storage
3. Data transfer: Egress, Interconnect
4. Managed services: Cloud Composer, Pub/Sub
5. API calls: DLP, Firestore reads/writes

OPTIMIZATION ORDER:
  Start with #1 (biggest bucket).
  Don't optimize #5 until #1 is addressed.
```

### Compute Cost Optimization

```
DATAFLOW COST OPTIMIZATION:
  
  1. Use Dataflow Flex Templates (not classic templates)
     → Custom workers, right-sized for workload
  
  2. Right-size worker machines
     NOT: n1-standard-4 for I/O bound pipeline (over-provisioned CPU)
     YES: n1-highmem-2 for memory-intensive transforms
  
  3. Use Streaming Engine for streaming jobs
     → 5-10% cost reduction (no shuffle disk needed)
  
  4. Batch during off-peak for preemptible workers
     → Spot/preemptible VMs: 60-80% cheaper
     → Risk: worker preempted mid-job (Dataflow handles gracefully via checkpoints)
  
  5. Auto-scaling with appropriate min/max
     min_workers=1 (not 0 — cold start too slow for production)
     max_workers=100 (not 1000 — protect budget)

BIGQUERY COST OPTIMIZATION:
  
  1. Always partition + cluster
     → 10-100× less data scanned
  
  2. Materialized views for repeated queries
     → Pre-compute common aggregations
  
  3. Use slot reservations for predictable workloads
     → Break-even at ~150TB/day per 1000 slots
  
  4. Table expiration for temp tables
     → Never let temp tables accumulate
     CREATE TABLE temp.my_analysis
     OPTIONS (expiration_timestamp = TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 7 DAY))
  
  5. Query result caching
     → Identical queries served from cache (free)
     → Cache invalidated when underlying data changes
```

---

## MODULE 3 SUMMARY

| Principle | CDM Next Application | Tradeoff |
|---|---|---|
| Stateless design | Dataflow templates read config from Firestore | Firestore dependency (mitigated by caching) |
| Async processing | Pipelines run in background; teams get immediate ACK | Harder to debug (async failures) |
| Circuit breaker | JDBC source failures trip circuit, fail fast | Risk of false positives on transient errors |
| Bulkhead | BigQuery reservations per team | Wasted capacity if team underutilizes |
| Idempotency | Deterministic GCS paths + BQ job IDs | Slightly complex naming conventions |
| Data contracts | Schema versioning, breaking change policy | Organizational overhead to enforce |
| Error budget | 99.5% success rate SLO | Feature freeze when budget consumed |
| Column lineage | OpenLineage events to Dataplex | Performance overhead per pipeline run |

---

*Module 3 Complete — ~7,200 words.*
