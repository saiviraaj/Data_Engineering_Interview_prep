# MODULE 5: Cloud Architecture Deep Dive (GCP) + Streaming Processing
## Production-Grade System Design on Google Cloud Platform

---

## Table of Contents
1. [GCP Compute Services](#compute)
2. [GCP Data Services](#data-services)
3. [GCP Messaging & Streaming](#messaging-streaming)
4. [GCP Orchestration](#orchestration)
5. [GCP Security & Governance](#security)
6. [GCP Cost Management](#cost)
7. [STREAMING DEEP DIVE: Dataflow & Real-Time Processing](#streaming)
8. [Design Patterns on GCP](#patterns)
9. [CDM Next: Complete GCP Architecture](#cdm-next-example)

---

## GCP Compute Services

### Compute Engine (Virtual Machines)

```
Instance Types:
├─ E2: Cost-optimized (general purpose)
│  └─ $0.025/hour small instance
├─ N2/N2D: Balance (standard)
│  └─ $0.035/hour
└─ M2: Memory-optimized (data processing)
   └─ $0.15/hour

Machine Types:
├─ Predefined: e2-medium, n2-standard-2, etc.
└─ Custom: Choose exact CPU/RAM

Persistent Disks:
├─ Standard: $0.04/GB/month
├─ SSD: $0.17/GB/month
└─ Balanced: $0.10/GB/month

Example: CDM Next worker
├─ Machine: n2-standard-4 (4 CPU, 16GB RAM)
├─ Disk: 100GB SSD
├─ Cost: $0.14/hour
├─ Use: Heavy data transformation
└─ Scales: Auto-scaling groups (1-100 workers)
```

### Cloud Run (Serverless Containers)

```
Perfect for: Microservices, APIs, event handlers

Example: CDM Next validation service
├─ Container: Custom validation logic
├─ Trigger: Pub/Sub event (new file uploaded)
├─ Execution: 2-60 second processing
├─ Scaling: Auto (0-1000 instances)
├─ Cost: $0.00002/request + $0.40/GB-month

Advantages:
├─ No server management
├─ Auto-scaling
├─ Pay per invocation
└─ Standard containers (any language)
```

### App Engine (PaaS)

```
Use case: Full applications (web, API)

Example: CDM Next metadata service
├─ Runtime: Python 3.9
├─ Framework: Flask
├─ Scaling: Auto
├─ Traffic splitting: A/B testing
└─ Cost: Flexible environment (~$0.05/hour)
```

### Cloud Functions (FaaS)

```
Use case: Simple event handlers

Example: CDM Next DLP scanning trigger
├─ Language: Python
├─ Trigger: Cloud Storage (file upload)
├─ Execution: <1 second
├─ Scaling: Auto
└─ Cost: $0.40/million invocations

vs Cloud Run:
├─ Functions: Simpler (single function)
├─ Run: More flexible (full apps)
```

---

## GCP Data Services

### BigQuery (OLAP Data Warehouse)

```
Architecture:
├─ Columnar storage (compress data 100x)
├─ Distributed query execution (1000s of nodes)
├─ Automatic sharding (transparent to user)
└─ Real-time streaming inserts

Pricing:
├─ Storage: $0.02/GB/month (hot), $0.01/GB/month (cool)
├─ Queries: $6.25/TB scanned (on-demand)
├─ Slots: $2,000/month per 100 slots (flat rate, unlimited queries)

Example: CDM Next analytics
├─ Data: 15 PB in BigQuery
├─ Cost: ~$300K/month storage + slots
├─ Queries: 500+ teams querying daily
├─ Availability: 99.99% SLA
└─ Performance: Sub-second queries on PB-scale
```

**Partitioning & Clustering**:
```
Partitioning (by date):
├─ SELECT * FROM orders WHERE date = '2024-01-15'
├─ Only scans that date's partition (faster, cheaper)
└─ Best for: Time-series data

Clustering (by key):
├─ SELECT * FROM orders WHERE customer_id = 123
├─ Data organized by customer_id (faster, cheaper)
└─ Best for: Common query filters

Example: CDM Next
├─ Partition: By ingestion_date (daily)
├─ Cluster: By source_system (50+ sources)
└─ Result: 100x faster queries
```

### Cloud SQL (OLTP Database)

```
Options:
├─ PostgreSQL: Open source, powerful
├─ MySQL: Popular, simpler
└─ SQL Server: Enterprise

Example: CDM Next metadata store
├─ Database: PostgreSQL
├─ Instance: db-custom-4-16GB ($0.14/hour)
├─ Storage: 100GB ($10/month)
├─ Backups: Daily, 7-day retention
└─ High Availability: Multi-region failover

Replication:
├─ Read replicas: Scale reads (1-10 replicas)
├─ Cross-region: Disaster recovery
└─ Automatic failover: 60-120 seconds
```

### Firestore (NoSQL Document Database)

```
Use case: Real-time app data

Example: CDM Next user preferences
├─ Document structure: JSON-like
├─ Real-time sync: Clients notified of changes
├─ Offline support: Local cache
└─ Pricing: $0.06 per 100K read operations

Query capabilities:
├─ Simple: Get by ID (fast)
├─ Queries: Filter, sort, range (slower)
└─ Transactions: ACID guaranteed
```

### Datastore (Key-Value Store - Legacy)

```
Being replaced by Firestore, but still used for:
├─ Sessions storage
├─ Caching metadata
└─ Quick lookups

Pricing: $0.06 per 100K operations
```

### AlloyDB (PostgreSQL-Compatible)

```
What: Managed PostgreSQL on steroids

Improvements over Cloud SQL:
├─ 2x faster queries (optimized architecture)
├─ Better for OLAP + OLTP mix
├─ Columnar storage option
├─ Advanced analytics functions

Cost: Higher than Cloud SQL (~$1.50/hour)

Use case: When Cloud SQL not fast enough
```

---

## GCP Messaging & Streaming

### Cloud Pub/Sub (Messaging)

```
Architecture:
├─ Publisher: Sends messages
├─ Topic: Channel (like Kafka topic)
├─ Subscriber: Receives messages
└─ Subscription: Consumer group (multiple subscribers)

Example: CDM Next event streaming
├─ Topic: data.ingestion.events
├─ Messages: File uploaded, transformed, validated
├─ Subscribers:
│  ├─ DLP scanning
│  ├─ Quality checks
│  ├─ Metadata updates
│  └─ Real-time dashboards

Pricing:
├─ Ingestion: Free
├─ Storage: $0.05/GB/month
└─ Operations: $0.40/million messages

Guarantees:
├─ At-least-once delivery (might see duplicates)
├─ No ordering guarantee across partitions
├─ 7-day message retention (configurable)
```

**Push vs Pull Delivery**:
```
PULL (Subscriber requests messages):
├─ Subscriber: "Give me messages"
├─ Pub/Sub: Returns batch
├─ Control: Subscriber controls pace
├─ Latency: ~100-500ms (polling)
└─ Use: Dataflow, high throughput

PUSH (Pub/Sub sends to subscriber):
├─ Pub/Sub: Sends to HTTP endpoint
├─ Control: Pub/Sub controls pace
├─ Latency: <100ms (immediate)
└─ Use: Cloud Functions, lightweight
```

---

## STREAMING DEEP DIVE: Dataflow & Real-Time Processing

### What is Dataflow?

**Dataflow** = Managed Apache Beam (open-source streaming framework)

```
BEFORE DATAFLOW:
├─ Provision Kafka cluster
├─ Provision Spark cluster
├─ Write Spark code
├─ Deploy to cluster
├─ Monitor manually
├─ Scale manually
└─ Operational nightmare

WITH DATAFLOW:
├─ Write Beam code
├─ Submit to Dataflow
├─ Auto-scales (0-1000 workers)
├─ Fully managed (no ops)
└─ Pay per resource used
```

### Stream vs Batch Unification

**The Power of Beam**: Same code for batch AND streaming!

```
DATAFLOW FOR BATCH:
└─ Read from Cloud Storage
   └─ Process (same code as streaming)
   └─ Write to BigQuery
   └─ Cost: ~$2 per job (fast)

DATAFLOW FOR STREAMING:
└─ Read from Pub/Sub
   └─ Process (SAME CODE!)
   └─ Write to BigQuery
   └─ Cost: ~$0.10/hour (always on)

HYBRID:
└─ Same code
└─ Choose: --runner=DataflowRunner
└─ Flexibility!
```

### Windowing (Breaking Infinite Streams into Batches)

Streaming = infinite data. How do you aggregate?

```
FIXED WINDOW (1 hour buckets):
├─ 0:00-1:00: Aggregate 1
├─ 1:00-2:00: Aggregate 2
├─ 2:00-3:00: Aggregate 3
└─ Use: Hourly metrics, dashboards

Example: Orders per hour
├─ Window: 1 hour
├─ Metric: Sum(order_amount)
├─ Output: Every hour, total revenue

Code:
├─ p = beam.Pipeline()
├─ events = p | 'Read' >> beam.io.ReadFromPubSub(...)
├─ windowed = events | 'Window' >> beam.WindowInto(
│                          beam.window.FixedWindows(3600))
├─ aggregated = windowed | 'Aggregate' >> beam.CombinePerKey(sum)
└─ aggregated | 'Write' >> beam.io.WriteToBigQuery(...)

SLIDING WINDOW (overlapping):
├─ Window 0:00-1:00
├─ Window 0:15-1:15
├─ Window 0:30-1:30
├─ Window 0:45-1:45
└─ Use: Detect trends in rolling window

Example: 1-hour revenue (updated every 15 min)

CODE:
├─ beam.window.SlidingWindows(size=3600, period=900)

SESSION WINDOW (activity-based):
├─ Group events by user session
├─ Session ends when 30 min of inactivity
├─ Windows of different lengths
└─ Use: User behavior analysis

Example: User session analysis
├─ Events: click, view, purchase
├─ Group by user
├─ Session ends after 30 min idle
└─ Analyze: Actions per session

CODE:
├─ beam.window.Sessions(gap_duration=1800)
```

### Stateful Processing

Maintaining state across events:

```
EXAMPLE: Running count of orders

Without state:
├─ Event 1: order_amount=100
│  └─ Can't compute "total orders so far"
├─ Event 2: order_amount=50
│  └─ Can't compute "total orders so far"
└─ Problem: No memory of previous events

WITH STATEFUL PROCESSING:
├─ Event 1: order_amount=100
│  └─ State: count=1, total=100
├─ Event 2: order_amount=50
│  └─ State: count=2, total=150
├─ Event 3: order_amount=200
│  └─ State: count=3, total=350
└─ Output: Running totals

HOW DATAFLOW HANDLES STATE:
├─ Per key: User ID 123 has own state
├─ Distributed: State stored across workers
├─ Checkpointing: Persisted periodically
├─ Recovery: Restored after failure

EXAMPLE CODE (Beam):
├─ class CountPerUser(beam.DoFn):
│  └─ process(self, element, state=beam.pvalue.Per...):
│     ├─ user_id, amount = element
│     ├─ current_count = state.read()
│     ├─ new_count = current_count + 1
│     ├─ state.write(new_count)
│     └─ yield (user_id, new_count)
```

### Exactly-Once Processing

**Guarantee**: Each event processed exactly once (not lost, not duplicated)

```
WHY IT'S HARD:
├─ Network fails after processing
│  └─ Source doesn't know if processed
│  └─ Might retry: Duplicate!
├─ Process crashes mid-processing
│  └─ State not saved
│  └─ Might re-process: Duplicate!
└─ Multiple subscribers
   └─ Coordination needed

HOW DATAFLOW DOES IT:
├─ Checkpointing: Save state periodically
├─ Deduplication: Track message IDs
├─ Idempotent writes: Safe to write twice
└─ Distributed consensus: Agree on completion

EXAMPLE: Payment processing
├─ Event: Transfer $100 from A to B
├─ Processing:
│  ├─ Deduct $100 from A (checkpoint 1)
│  ├─ Add $100 to B (checkpoint 2)
│  ├─ Mark as processed (checkpoint 3)
├─ If crash at checkpoint 1:
│  └─ Restart from checkpoint 1 (don't redo everything)
└─ If duplicate event: Deduplication blocks second processing

COST:
├─ Exactly-once: Slower (more checkpointing)
├─ At-least-once: Faster (less overhead)
└─ Trade-off: Reliability vs speed
```

### Stream Joins (Combining Multiple Streams)

```
SCENARIO: Match orders with payment confirmations

Stream 1: Orders
├─ Event: order_id=123, amount=100, timestamp=10:00:01

Stream 2: Payments
├─ Event: order_id=123, status=approved, timestamp=10:00:05

GOAL: Match them together

WINDOWED JOIN:
├─ Window: 1 hour
├─ Join on: order_id
├─ Output: (order_id, order_amount, payment_status)
└─ Only works if events arrive within window

CODE:
├─ orders | 'Order Window' >> beam.WindowInto(...)
├─ payments | 'Payment Window' >> beam.WindowInto(...)
├─ combined = (orders, payments) \
│     | 'Join' >> beam.Flatten()
└─ (More complex in reality)

STREAM-TABLE JOIN (Better):
├─ Stream: Orders (infinite)
├─ Table: Products (BigQuery, cached)
├─ Join: Each order with product info
├─ Always fresh: Product table updated

CODE:
├─ orders = p | 'Read Orders' >> beam.io.ReadFromPubSub(...)
├─ products = p | 'Read Products' >> beam.io.ReadFromBigQuery(...)
├─ enriched = orders \
│     | 'Enrich' >> beam.Map(lambda order, products_dict: ...)
└─ Output: Orders with product details
```

### Deduplication

```
PROBLEM: Duplicate events in stream
├─ Event: "Order created" (arrives twice)
├─ Process twice: Wrong total!

SOLUTION: Deduplication window

CODE:
├─ events = p | 'Read' >> beam.io.ReadFromPubSub(...)
├─ deduped = events | 'Deduplicate' >> beam.Distinct()
│     (Within window: 1 hour)
└─ deduped | 'Process' >> ...

HOW IT WORKS:
├─ Stores seen message IDs (in state/cache)
├─ If ID seen before: Drop it
├─ If new ID: Process it
└─ Cost: Small storage overhead, big benefit

ALTERNATIVE: Idempotent Processing
├─ Process duplicate, but get same result
├─ Example: Set user.status=verified twice = idempotent
└─ No deduplication needed (process safely)
```

### Monitoring Streaming Pipelines

```
KEY METRICS:
├─ Lag: How far behind are we?
│  └─ Lag = current_time - event_timestamp
│  └─ 1 second lag = processing 1 second behind real-time
│  └─ 10 minute lag = stale data!
│
├─ Throughput: Messages per second
│  └─ 1000 msg/sec = healthy
│  └─ Decreasing? = Bottleneck
│
├─ Error rate: Failed messages %
│  └─ 0.1% = excellent
│  └─ 1%+ = investigate
│
└─ Resource usage: CPU, memory, network
   └─ Growing lag = need more workers

DATAFLOW MONITORING:
├─ Cloud Console: Graphs, lag, throughput
├─ Custom metrics: Beam Counter, Distribution
├─ Logging: Cloud Logging integration
└─ Alerting: Cloud Monitoring alerts on lag>5min
```

### Scaling Streaming Pipelines

```
AUTO-SCALING IN DATAFLOW:
├─ Monitors lag
├─ If lag increasing: Add workers
├─ If lag decreasing: Remove workers
└─ Range: 1-1000 workers (configurable)

MANUAL SCALING:
├─ Set: --num_workers=10
├─ Pipeline uses exactly 10 workers
└─ Cost predictable but static

CUSTOM SCALING:
├─ Write scaling function
├─ Dataflow calls your function
├─ You decide: More or fewer workers?
└─ Advanced: For complex scaling logic

COST OF SCALING:
├─ 1 worker: $0.07/hour
├─ 10 workers: $0.70/hour
├─ 100 workers: $7.00/hour
└─ Trade-off: Latency vs cost
```

### CDM Next Real-Time Example

```
CDM NEXT REAL-TIME PIPELINE:

Input: Kafka topic (external data source)
└─ Schema: {source_id, record, timestamp}

Dataflow Job:
├─ Read from Kafka (via Pub/Sub bridge)
├─ Parse JSON
├─ DLP scanning (inline)
├─ Apply policy tags (encryption)
├─ Validate schema
├─ Window: 1-second tumbling window
├─ Aggregate: Count by source
└─ Write to BigQuery (streaming inserts)

Latency: <5 seconds end-to-end
Throughput: 100K events/sec
Cost: $0.10/hour (flex slots)
Availability: 99.95% SLA

Monitoring:
├─ Lag: Should be <1 second
├─ If lag >5 sec: Alert
├─ Auto-scale: 1-100 workers
└─ Error rate: <0.01%
```

---

## GCP Orchestration

### Cloud Composer (Managed Airflow)

```
What: Managed Apache Airflow (workflow orchestration)

Example: CDM Next daily migration
├─ DAG: Define workflow as Python code
├─ Tasks: Run Dataflow, check DLP, validate, notify
├─ Dependencies: Task 1 must finish before Task 2
├─ Scheduling: Daily at 2am
├─ Retries: Auto-retry on failure

Code:
├─ from airflow import DAG
├─ from airflow.providers.google.cloud.operators import \
│      DataflowTemplateOperator
├─ dag = DAG('cdm_next_daily', schedule_interval='0 2 * * *')
├─ dataflow_task = DataflowTemplateOperator(
│      template='gs://templates/migrate.json',
│      dag=dag)
└─ validate_task = PythonOperator(...)

Pricing:
├─ Composer environment: ~$0.15/hour
├─ Workers: Included
└─ Total: ~$100/month small environment

vs Cloud Functions:
├─ Functions: Simple event handlers
├─ Composer: Complex workflows with dependencies
```

---

## GCP Security & Governance

### IAM (Identity & Access Management)

```
Example: CDM Next access control

Service account: cdm-next-dataflow@project.iam.gserviceaccount.com
Permissions:
├─ Read from source Cloud Storage
├─ Write to BigQuery
├─ Publish to Pub/Sub
└─ Read/write secrets

User: analyst@company.com
Permissions:
├─ Query BigQuery (specific tables)
├─ View dashboards
└─ Cannot modify pipelines
```

### Data Loss Prevention (DLP)

```
Scanning data for sensitive info:

Example: Find credit card numbers
├─ Scan Cloud Storage files
├─ Find pattern: XXXX-XXXX-XXXX-XXXX
├─ Alert or auto-redact
└─ Replace with: ****-****-****-1234

In CDM Next:
├─ Scan incoming data for PII
├─ Apply policy tags (mark as sensitive)
├─ Encrypt automatically
├─ Track access
```

### Dataplex & Data Catalog

```
DATAPLEX: Unified data governance
├─ Define zones (Bronze, Silver, Gold)
├─ Apply policies across zones
├─ Govern data assets

DATA CATALOG: Metadata & lineage
├─ What data exists?
├─ Where did it come from?
├─ Who has access?
├─ What's its quality?

CDM Next uses:
├─ Data Catalog: Track all datasets
├─ Lineage: Source → Quarantine → Application
├─ Quality metrics: Data freshness, completeness
```

---

## GCP Cost Management

```
BigQuery:
├─ Storage: $0.02-0.01/GB/month (25-50GB/month = $0.50-1)
├─ Queries: $6.25/TB scanned (or slots: $2000/month)
└─ Example: 100TB query = $625

Dataflow:
├─ Batch: $0.035/worker/hour
├─ Streaming: $0.045/worker/hour
└─ Example: 10 workers, 8 hours = $2.80

Pub/Sub:
├─ Ingestion: Free
├─ Storage: $0.05/GB/month
└─ Operations: $0.40/million messages

COST OPTIMIZATION:
├─ Use storage tiering (cold data = cheap)
├─ Use slots instead of on-demand (if high volume)
├─ Schedule jobs (don't always run)
├─ Right-size workers (not too many)
└─ Monitor & alert on cost anomalies
```

---

## Design Patterns on GCP

### Lambda Architecture on GCP

```
BATCH LAYER:
├─ Cloud Storage (raw data)
├─ Dataflow batch jobs
├─ BigQuery (batch views)
└─ Scheduled: Daily at 2am

SPEED LAYER:
├─ Pub/Sub (streaming)
├─ Dataflow streaming
├─ Firestore (real-time views)
└─ Latency: <5 seconds

SERVING:
├─ Users query BigQuery (accurate batch)
├─ Users query Firestore (fresh real-time)
└─ Both available for different use cases
```

### Multi-Region Design

```
PRIMARY REGION (us-central1):
├─ Main BigQuery instance
├─ Dataflow jobs
├─ Pub/Sub topics
└─ Write requests go here

SECONDARY REGION (europe-west1):
├─ Read replicas (BigQuery)
├─ Cache instances (Redis)
└─ Low latency for EU users

DISASTER RECOVERY:
├─ Automated failover
├─ Backup in 3rd region (us-east1)
└─ RTO: <5 minutes
```

---

## CDM Next: Complete GCP Architecture

```
COMPLETE SYSTEM:

DATA SOURCES (External):
├─ Teradata, Oracle, Hadoop, Kafka
└─ 60+ systems

INGESTION LAYER:
├─ Cloud Datastream (CDC for databases)
├─ Cloud Pub/Sub (events)
├─ Cloud Storage (batch files)
└─ HTTP API (custom sources)

PROCESSING LAYER:
├─ Dataflow (streaming transformations)
├─ Cloud Composer (orchestration)
├─ Cloud Dataproc (Spark for heavy lifting)
└─ Cloud Functions (validation)

SECURITY LAYER:
├─ DLP scanning (all data)
├─ Policy tags (sensitive data encryption)
├─ IAM (per-project isolation)
└─ Audit logging (all access)

STORAGE LAYER:
├─ BRONZE: Cloud Storage (raw data)
├─ SILVER: BigQuery (cleaned, deduplicated)
├─ GOLD: BigQuery (team-specific views)
└─ Tiering: Hot → Warm → Cold → Archive

SERVING LAYER:
├─ BigQuery (OLAP queries)
├─ Cloud SQL (metadata)
├─ Pub/Sub (real-time events)
└─ API Gateway (controlled access)

OBSERVABILITY:
├─ Cloud Logging (all logs)
├─ Cloud Monitoring (metrics, alerts)
├─ Cloud Trace (distributed tracing)
└─ Data quality checks (custom)

GOVERNANCE:
├─ Data Catalog (metadata)
├─ Dataplex (policies)
├─ Lineage tracking (automated)
└─ Access control (IAM + DLP)

RESULTS:
├─ 60+ teams supported
├─ 15+ PB migrated
├─ 99.9% uptime
├─ Sub-second queries
└─ Cost: ~$0.04/TB ingested
```

---

## Key Takeaways

✅ **GCP compute**: VMs, containers, serverless choices  
✅ **BigQuery**: OLAP at massive scale, columnar storage  
✅ **Pub/Sub**: Simple, managed messaging  
✅ **Dataflow**: Unified batch + streaming, managed infrastructure  
✅ **Windowing**: Break infinite streams into batches  
✅ **Stateful processing**: Maintain state across events  
✅ **Exactly-once**: Achieved through checkpointing & deduplication  
✅ **Cloud Composer**: Orchestrate complex workflows  
✅ **IAM + DLP**: Security from the start  
✅ **Cost optimization**: Use pricing to your advantage  

---

## Next Module Preview

Module 6 focuses on **System Design Interview Questions**—6 detailed data engineering problems with complete solutions, covering data ingestion platforms, data warehouses, real-time analytics, and more.

---

**Module 5 Complete**: You understand GCP architecture for production data systems, with deep streaming coverage integrated.

