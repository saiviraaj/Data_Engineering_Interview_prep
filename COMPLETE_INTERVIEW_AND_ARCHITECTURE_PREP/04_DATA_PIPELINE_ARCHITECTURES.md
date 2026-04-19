# MODULE 4: Data Pipeline Architectures
## Designing Systems for Data Movement & Transformation at Scale

---

## Table of Contents
1. [Introduction](#introduction)
2. [Lambda Architecture](#lambda)
3. [Kappa Architecture](#kappa)
4. [Medallion Architecture](#medallion)
5. [Data Mesh](#data-mesh)
6. [Event-Driven Architecture](#event-driven)
7. [Ingestion Patterns](#ingestion)
8. [Transformation Patterns](#transformation)
9. [Storage Patterns](#storage)
10. [Serving Patterns](#serving)
11. [CDM Next Through Architectural Lenses](#cdm-next)

---

## Introduction

Data pipelines are fundamentally different from application systems. While application systems optimize for low latency and consistency, data pipelines optimize for throughput, fault tolerance, and eventually correct results.

**Key differences**:

```
APPLICATION SYSTEM              DATA PIPELINE
├─ Latency: <100ms             ├─ Latency: Acceptable (seconds to hours)
├─ Consistency: Strong         ├─ Consistency: Eventually correct
├─ Throughput: High but varies ├─ Throughput: Massive and steady
├─ Queries: Simple lookups     ├─ Queries: Complex scans, aggregations
├─ Update: Real-time           ├─ Update: Batch or streaming
└─ Example: E-commerce         └─ Example: Data warehouse

IMPLICATION: Different architectures solve different problems
```

This module covers the major architectural patterns for data systems and when to use each.

---

## Lambda Architecture

### What Is It?

Lambda Architecture combines **batch processing** (for accuracy) and **stream processing** (for speed) into one system:

```
DATA SOURCES
     ↓
    ┌─────────────────────┬─────────────────────┐
    ↓                     ↓
BATCH LAYER              SPEED LAYER
(Hadoop/Spark)           (Kafka + Stream Engine)
    ↓                     ↓
BATCH VIEW               REAL-TIME VIEW
    ↓                     ↓
    └─────────────────────┬─────────────────────┘
                          ↓
                   SERVING LAYER
                   (BigQuery/Cassandra)
                          ↓
                       QUERIES
```

**Example: Analytics Dashboard**

```
SCENARIO: Show "Revenue in last 24 hours" on dashboard

BATCH LAYER (Accurate, slow):
├─ Every night at 11pm: Spark job runs
├─ Processes: All orders from last 24h
├─ Joins with: Product catalog, customer data
├─ Computes: Accurate revenue number
├─ Stores in: Data warehouse
├─ Latency: ~2 hours (result available 1am next day)
├─ Accuracy: 100%
└─ Cost: $100/job

SPEED LAYER (Fast, approximate):
├─ Real-time: Orders stream into Kafka
├─ Every 1 second: Aggregate last 24h orders
├─ Compute: Approximate revenue
├─ Latency: 1-2 seconds (always current)
├─ Accuracy: 99% (might be missing recent orders)
└─ Cost: $10K/month (always running)

SERVING LAYER (Combine both):
├─ Dashboard query: "Revenue last 24h?"
├─ Returns:
│  ├─ "Approximate (real-time): $1,245,000 (updated every second)"
│  └─ "Accurate (batch): $1,248,500 (updated daily at 1am)"
└─ User sees: Real-time estimate + accurate historical
```

### Real-World Example: Twitter

Twitter uses Lambda architecture for analytics:

```
DATA: Tweets, retweets, likes, followers

BATCH LAYER:
├─ Every 4 hours: MapReduce job
├─ Processes: All tweets, joins with user data
├─ Computes: Trending topics, influential users
├─ Stores: Hive data warehouse
├─ Used for: Daily reports, historical analysis

SPEED LAYER:
├─ Real-time: Twitter event stream
├─ Kafka brokers: Ingest events
├─ Stream processing: Compute trending in real-time
├─ Stores: In-memory cache (Redis)
├─ Used for: Trending sidebar (#1 hashtag now)

RESULT:
├─ Users see: Trending topics (real-time)
├─ Reports show: Accurate statistics (daily)
└─ Both available, different guarantees
```

### Advantages

```
✅ Accuracy guaranteed (batch layer always correct)
✅ Freshness possible (speed layer always current)
✅ Different views for different use cases
✅ Batch layer can recompute everything (audit trail)
✅ Can run batch job on speed layer data (reconciliation)
```

### Disadvantages

```
❌ Operational complexity (maintain 2 systems)
❌ Code duplication (write logic twice, batch + stream)
❌ Harder to debug (which layer caused issue?)
❌ Cost (run both systems continuously)
❌ Learning curve (engineers need to understand both)
```

### When to Use Lambda

```
✅ Need both accuracy and freshness
✅ Can tolerate operational complexity
✅ Have engineering resources
✅ Business impact of stale data is high
✅ Example: Financial dashboards, fraud detection

❌ Simple systems (use Kappa instead)
❌ Limited engineering budget (choose one)
❌ Early stage startup (don't need complexity yet)
```

---

## Kappa Architecture

### What Is It?

Kappa says: **"Abandon batch, do everything with streaming"**

The insight: If your stream processor is good enough, you don't need batch!

```
DATA SOURCES
     ↓
KAFKA / STREAMING SOURCE
     ↓
STREAM PROCESSING ENGINE
(Kafka Streams, Dataflow, Flink)
     ↓
SERVING LAYER
(Database, Cache)
     ↓
QUERIES
```

**Compared to Lambda**:

```
LAMBDA:                      KAPPA:
├─ Batch + Stream           ├─ Stream only
├─ 2 code paths             ├─ 1 code path
├─ More accurate            ├─ Simpler
└─ More complex             └─ Easier to maintain
```

### Example: Payment Processing

```
SCENARIO: Process payments, detect fraud, update balances

LAMBDA APPROACH:
├─ Speed layer: Real-time fraud detection
│  └─ Stream transactions, score immediately
├─ Batch layer: Nightly reprocessing
│  └─ Recompute all fraud scores with full history
└─ Complexity: 2 systems, 2 code paths

KAPPA APPROACH:
├─ Single stream processor: Process all transactions
├─ Maintain state: Keep running fraud model
├─ Reprocess when needed: Restart from log beginning
│  └─ Kafka/Pub/Sub keeps log of all messages (weeks)
│  └─ Restart consumer from beginning
│  └─ Recompute entire history
└─ Simplicity: 1 system, 1 code path
```

### Key Insight: Replaying Data

Kappa works if you can **replay** all messages:

```
HOW IT WORKS:

Normal operation:
├─ Message 1: Transaction $100
├─ Process: Update balance
├─ Message 2: Transaction $200
├─ Process: Update balance
└─ Final state: Balance = $300

If bug found (fraud model wrong):
├─ Fix bug in code
├─ Restart consumer from message 1
├─ Reprocess all messages with fixed logic
├─ Message 1: Transaction $100 (recompute)
├─ Message 2: Transaction $200 (recompute)
└─ Final state: Correct balance = $300

REQUIREMENT: Messages must persist!
├─ Kafka: Configurable retention (default 7 days)
├─ Pub/Sub: 7 day retention
├─ S3: Permanent (cheapest option)
└─ Can always replay if you keep messages
```

### Advantages

```
✅ Simpler architecture (one system)
✅ No code duplication
✅ Easier to debug
✅ Can replay/reprocess anytime
✅ Natural evolution from streaming
✅ Easier to test
```

### Disadvantages

```
❌ Message retention needed (space cost)
❌ Reprocessing can be slow (reprocess all history)
❌ Stateful processing is harder
❌ Requires good stream processing framework
❌ Not all logic fits streaming paradigm
```

### When to Use Kappa

```
✅ Can tolerate minutes of latency (acceptable batch window)
✅ Can replay historical data
✅ Streaming logic is natural for problem
✅ Have good stream processing tool (Dataflow, Flink)
✅ Want simplicity
✅ Example: Real-time ML scoring, event analytics

❌ Need high accuracy immediately (no time to replay)
❌ Complex batch transformations (SQL better)
❌ Limited stream processing expertise
❌ Low tolerance for complexity (keep it simple)
```

### Example: Uber's Real-Time Analytics

Uber uses Kappa for real-time metrics:

```
DATA: Uber rides (pickup, dropoff, payment, etc.)

ARCHITECTURE:
├─ Kafka: All ride events
├─ Flink: Stream processor
└─ Druid: Time-series database

METRICS COMPUTED:
├─ Rides per minute (current)
├─ Revenue per city (current)
├─ Driver utilization (current)
├─ Surge pricing adjustments (real-time)

WHY KAPPA?
├─ Can replay all events (Kafka retention)
├─ If bug found, restart from beginning
├─ Single code path (simpler)
├─ Flink handles stateful processing well
└─ Scales to millions of events/second
```

---

## Medallion Architecture

### What Is It?

Medallion (also called "Bronze-Silver-Gold") organizes data into layers by quality:

```
RAW DATA
    ↓
BRONZE LAYER (Raw data, minimal cleaning)
├─ All data as ingested
├─ Data type conversions only
├─ Minimal quality checks
└─ Query: "What data do we have?"

    ↓ (Clean, deduplicate, join with reference)

SILVER LAYER (Cleaned, deduplicated, conformed)
├─ Business logic applied
├─ Cross-source joins
├─ Consistent naming/types
└─ Query: "What does the business data look like?"

    ↓ (Aggregate, optimize, enrich)

GOLD LAYER (Analytics-ready, optimized)
├─ Pre-aggregated metrics
├─ Optimized for queries
├─ Domain-specific tables
└─ Query: "Give me the answer"

CONSUMPTION
├─ Dashboards: Query Gold (fast)
├─ Data scientists: Use Silver (flexible)
├─ Data engineers: Debug Bronze (raw truth)
```

### Example: E-Commerce Data

```
DATA SOURCES:
├─ Web events (clicks, page views)
├─ Orders (transactions)
├─ Customer (profiles)
└─ Inventory (stock levels)

BRONZE LAYER (Raw):
├─ web_events_raw: All clicks as JSON blobs
├─ orders_raw: Raw CSV from billing system
├─ customer_raw: Raw SQL export
└─ inventory_raw: Daily inventory snapshots

TRANSFORMATIONS:
├─ Parse JSON (web_events)
├─ Fix data types (orders)
├─ Clean nulls & duplicates
├─ Add ingestion timestamps
└─ Verify referential integrity

SILVER LAYER (Cleaned):
├─ web_events: Structured, deduplicated
├─ orders: Valid transactions only
├─ customer: Latest version per customer
├─ inventory: Standardized format

TRANSFORMATIONS:
├─ Join orders with customers (who ordered?)
├─ Join inventory with products (what in stock?)
├─ Compute order metrics (order_value, items_count)
├─ Create customer aggregations (lifetime_value)

GOLD LAYER (Analytics):
├─ daily_revenue: Revenue per day (pre-aggregated)
├─ customer_metrics: Customer LTV, churn risk
├─ product_performance: Sales, margins per product
├─ geographic_analysis: Revenue by region

EXAMPLE QUERY:
Dashboard asks: "Revenue by region last 30 days?"
├─ Query Gold.geographic_analysis (instant, pre-computed)
├─ vs
├─ Query Silver (faster, still flexible)
├─ vs
├─ Query Bronze (slow, but has raw data for audit)
```

### Real-World Example: Databricks Lakehouse

Databricks promotes Medallion as the standard:

```
Delta Lake (Unity Catalog) structure:
├─ Bronze tables: Raw data, append-only
├─ Silver tables: Cleaned, validated
├─ Gold tables: Business metrics
└─ All in same system (Lakehouse)

Advantages:
├─ Version control (can rollback)
├─ ACID transactions (no corrupted data)
├─ Unity Catalog (governance)
└─ Same query engine (Spark SQL)
```

### Advantages

```
✅ Clear data quality progression
✅ Audit trail (can debug at each layer)
✅ Reusable transformations
✅ Flexibility (different teams use different layers)
✅ Cost-effective (only compute what needed)
✅ Easy to understand (clear mental model)
```

### Disadvantages

```
❌ Storage overhead (3x data: Bronze, Silver, Gold)
❌ Transformation latency (3 passes through data)
❌ Complexity in defining layers
❌ Data duplication (might not scale to exabyte)
```

### When to Use Medallion

```
✅ Have diverse data sources (need cleaning)
✅ Need audit trail & debugging capability
✅ Have data scientists (need flexibility)
✅ Want clear governance (quality per layer)
✅ Building data warehouse or lakehouse
✅ Example: Enterprise data lakes, analytics platforms

❌ Simple point-to-point pipelines
❌ Extreme cost constraints (storage expensive)
❌ Real-time systems (latency matters)
```

---

## Data Mesh

### What Is It?

Data Mesh is a **paradigm shift**: Instead of central data team owning all data, each **business domain** owns its own data.

**Traditional Centralized**:
```
All Data Teams
        ↓
Central Data Warehouse
├─ Payment data
├─ User data
├─ Inventory data
├─ Order data
└─ All mixed together

Problems:
├─ Single team bottleneck
├─ Wait months for new data
├─ Schema changes break everything
├─ No domain ownership
```

**Data Mesh (Distributed)**:
```
PAYMENT DOMAIN    USER DOMAIN       INVENTORY DOMAIN
├─ Payment Team   ├─ User Team       ├─ Warehouse Team
├─ Payment DB     ├─ User DB         ├─ Inventory DB
├─ Own SLA        ├─ Own SLA         ├─ Own SLA
└─ Publishes data └─ Publishes data  └─ Publishes data
        ↓               ↓                    ↓
    SHARED PLATFORM
    ├─ Data catalog
    ├─ Governance
    ├─ Lineage tracking
    ├─ Access control
    └─ Quality enforcement
        ↓
ANALYTICS / ML TEAMS (Self-service)
```

### Four Key Pillars

```
1. DOMAIN OWNERSHIP
   ├─ Each domain team owns their data
   ├─ Responsible for quality, SLA
   ├─ Publishes as "data product"
   └─ Example: Payment team owns payment data

2. DATA AS PRODUCT
   ├─ Domain team treats data like product
   ├─ Has SLA, documentation, support
   ├─ Clear contract (schema, refresh rate)
   ├─ Versioning (breaking changes communicated)
   └─ Example: "Orders data product v2.1"

3. SELF-SERVE INFRASTRUCTURE
   ├─ Platforms that let teams publish data
   ├─ No manual approval (self-serve)
   ├─ Automated quality checks
   ├─ Version management
   └─ Example: UI to publish new dataset

4. GOVERNANCE AT PLATFORM LEVEL
   ├─ Central rules everyone follows
   ├─ Not central data team
   ├─ Policies enforced automatically
   ├─ Example: "All PII encrypted"
   └─ Example: "Lineage tracked automatically"
```

### Example: Netflix

Netflix moved toward data mesh:

```
MUSIC TEAM
├─ Owns: Streaming data (plays, pauses, seeks)
├─ Publishes: play_events data product
├─ SLA: 99.9% uptime, <1 min latency
└─ Versioning: v1.2.1

RECOMMENDATION TEAM
├─ Owns: User preferences, viewing history
├─ Publishes: user_preferences data product
├─ SLA: 99.95% uptime (critical)
└─ Versioning: v2.0

INFRASTRUCTURE TEAM (Platform)
├─ Provides: Self-serve data publishing
├─ Enforces: Data quality checks
├─ Maintains: Data catalog, lineage
├─ Handles: Access control, audit logs
└─ Ensures: GDPR compliance

ANALYTICS TEAMS (Self-serve)
├─ Discover: play_events, user_preferences in catalog
├─ Access: Through platform (no manual approval)
├─ Query: Through unified query engine
└─ Track: Lineage automatically
```

### Advantages

```
✅ Ownership clear (domain team responsible)
✅ Faster iteration (don't wait for central team)
✅ Quality improves (domain team cares)
✅ Scales with company (each team adds their data)
✅ Natural org structure (teams match data domains)
✅ Self-serve (less bottleneck)
```

### Disadvantages

```
❌ Complexity (distributed systems hard)
❌ Requires strong governance (no central control)
❌ Data duplication across teams
❌ Harder to join data across domains
❌ Needs good platform (self-serve infra costly)
❌ Mature company required (new companies: too complex)
```

### When to Use Data Mesh

```
✅ Large company (50+ data engineers)
✅ Multiple business domains
✅ Teams move fast (need autonomy)
✅ Have platform engineering resources
✅ Organizational structure supports it
✅ Example: Netflix, Uber, Google

❌ Startup (<10 engineers)
❌ Centralized org
❌ Limited platform resources
❌ Simple data needs
❌ Monolithic application
```

---

## Event-Driven Architecture

### What Is It?

Instead of services calling each other (request/response), services emit **events** that others subscribe to:

```
TRADITIONAL (Synchronous):
Service A → (calls) → Service B → (waits for response)
User sees latency = A + B latency

EVENT-DRIVEN (Asynchronous):
Service A: Emit event "order_created"
           Return immediately to user
└─ Event published to message broker

Service B: Subscribed to "order_created"
          └─ Process when ready (async)

Service C: Subscribed to "order_created"
          └─ Process independently

RESULT: User sees latency = A latency only
        B and C process in parallel, decoupled
```

### Example: Order Processing

```
USER PLACES ORDER
    ↓
ORDER SERVICE
├─ Validates order
├─ Creates record
├─ Emits: "order.created" event
└─ Returns: Order ID to user (100ms)

Event propagates to subscribers:

PAYMENT SERVICE (Subscriber 1)
├─ Receives: "order.created"
├─ Charges credit card
├─ Emits: "payment.processed"
└─ Latency: 2 seconds (doesn't block user)

INVENTORY SERVICE (Subscriber 2)
├─ Receives: "order.created"
├─ Reserves items
├─ Emits: "inventory.reserved"
└─ Latency: 1 second (doesn't block user)

FULFILLMENT SERVICE (Subscriber 3)
├─ Receives: "payment.processed"
├─ Ships order
├─ Emits: "order.shipped"
└─ Latency: 5 minutes (doesn't block user)

NOTIFICATION SERVICE (Subscriber 4)
├─ Receives: "order.shipped"
├─ Sends email/SMS
├─ Emits: (optional, maybe "notification.sent")
└─ Latency: 30 seconds (doesn't block user)

USER EXPERIENCE:
├─ Places order (wait 100ms)
├─ Immediately: "Order created: #12345"
├─ After 1-2s: Sees processing notifications
├─ After 5m: "Order shipped!" email
└─ Everything works seamlessly, independently
```

### Advantages

```
✅ Loose coupling (services independent)
✅ Scalability (handle traffic spikes)
✅ Resilience (one slow service doesn't block others)
✅ Natural audit trail (event log = what happened)
✅ Easy to add subscribers (don't modify publisher)
✅ Good for microservices
```

### Disadvantages

```
❌ Eventual consistency (responses not immediate)
❌ Distributed debugging (messages cross services)
❌ Operational complexity (message broker needed)
❌ Duplicate handling (multiple subscribers might process same)
❌ Ordering guarantees tricky (events might arrive out of order)
❌ Testing harder (mocking message broker)
```

### When to Use Event-Driven

```
✅ Decoupling important (many services)
✅ Can tolerate eventual consistency
✅ High scalability needed
✅ Operations-mature team
✅ Example: E-commerce (orders, payments, shipping)

❌ Real-time synchronous needs
❌ Simple system (overkill)
❌ Team unfamiliar with async patterns
❌ Strong consistency required
```

---

## Ingestion Patterns

How do you get data into your system?

### Pull (Polling)

```
SYSTEM:
Data Source (external API)
     ↑
Polling job (every 1 hour)
├─ Connect to API
├─ Query: "Get new data since last run"
├─ Pull into system
└─ Repeat

Example: Fetch customer data from Salesforce every hour

Pros:
├─ Simple (just poll)
├─ Can batch requests
└─ Source doesn't need to know about you

Cons:
├─ Latency: 1 hour between updates
├─ Polling overhead (many empty calls)
├─ Can miss rapid changes (polling too slow)
```

### Push (Webhooks)

```
SYSTEM:
Data Source (emits events)
     ↓ (webhook call)
System endpoint
├─ Receives: Event immediately
├─ Processes: Right away
└─ Returns: ACK

Example: Stripe sends payment events via webhook

Pros:
├─ Real-time (immediate notification)
├─ No polling overhead
├─ Source controls pace
└─ Efficient

Cons:
├─ Source must support webhooks
├─ Ordering might be wrong (network delays)
├─ Reliability: What if endpoint down?
```

### CDC (Change Data Capture)

```
SYSTEM:
Database (Oracle, PostgreSQL)
     ↓ (CDC tool reads log)
CDC Tool (Debezium, GCP Datastream)
├─ Reads: Database transaction log
├─ Extracts: All changes
├─ Sends: To message broker (Kafka, Pub/Sub)
└─ Guarantees: Nothing lost, ordered per table

Example: All PostgreSQL changes → Kafka → Data warehouse

Pros:
├─ Complete (captures everything)
├─ Ordered (respects transaction order)
├─ Real-time (milliseconds behind)
├─ Decoupled (source app doesn't know)

Cons:
├─ Complex setup (CDC tools can be tricky)
├─ Higher compute (parsing logs)
├─ Requires database support
```

### Hybrid

Most systems use multiple patterns:

```
STRIPE PAYMENTS:
├─ Webhook: Immediate processing (fraud detection)
├─ Batch export: Daily reconciliation (ensure nothing lost)
└─ CDC: Backup copy to data lake

UBER RIDES:
├─ Event stream: Real-time (Kafka)
├─ Periodic snapshots: Consistency checks
└─ CDC from databases: Fallback source of truth
```

---

## Transformation Patterns

### ETL vs ELT

```
ETL (Extract, Transform, Load):
├─ Extract: Get data from source
├─ Transform: Clean, join, aggregate (in memory or staging DB)
├─ Load: Put into warehouse
└─ Data only in warehouse after transformation

Pro: Only clean data in warehouse (storage efficient)
Con: Transformation bottleneck (can't parallelize)

ELT (Extract, Load, Transform):
├─ Extract: Get data from source
├─ Load: Put into warehouse immediately (raw)
├─ Transform: Clean, join, aggregate in warehouse
└─ Multiple views of same data (Bronze, Silver, Gold)

Pro: Flexibility (can recompute anytime)
Con: Storage overhead (raw data takes space)
```

**Trend**: ELT is winning (storage is cheap, flexibility valuable)

---

## Storage Patterns

```
HOT (Query frequently):
├─ BigQuery (OLAP)
├─ PostgreSQL (OLTP)
└─ Cost: High per GB

WARM (Query monthly):
├─ Cloud Storage + Dataflow (on-demand)
└─ Cost: Low

COLD (Archive):
├─ Cloud Storage Archive tier
└─ Cost: Cheapest
```

---

## Serving Patterns

```
OLAP (Analytics):
├─ BigQuery
├─ Queries: "Revenue by region"
└─ Users: Analysts, dashboards

OLTP (Operations):
├─ PostgreSQL, Firestore
├─ Queries: "Get user profile"
└─ Users: Applications

REAL-TIME (Features):
├─ Redis, Firestore
├─ Queries: "<10ms recommendation"
└─ Users: ML models, features
```

---

## CDM Next Through Architectural Lenses

### CDM Next as Kappa + Medallion

```
CDM NEXT ARCHITECTURE:

INGESTION (Kappa):
├─ Sources: 60+ systems (Teradata, Oracle, Hadoop, Kafka)
├─ Streaming: Real-time events via Pub/Sub
├─ Storage: All raw in Cloud Storage + BigQuery
└─ Replay: Can reprocess from logs anytime

TRANSFORMATION (Medallion):
├─ Bronze: Raw data as ingested
├─ Silver: Cleaned, deduplicated
├─ Gold: Team-specific views
└─ DLP scanning applied at each stage

ORCHESTRATION:
├─ Cloud Composer (Airflow) for DAGs
├─ Trigger: Time-based (daily) + event-based (data arrives)
└─ Recovery: Automatic retries, manual overrides

GOVERNANCE:
├─ IAM: Project-based isolation (1 project per team)
├─ DLP: Sensitive data encryption (policy tags)
├─ Lineage: Tracked automatically (Dataplex/Data Catalog)
└─ Audit: All access logged

SERVING:
├─ Analytics teams: Query BigQuery directly (OLAP)
├─ Applications: Read from application datasets
└─ Real-time: Pub/Sub subscriptions for urgent data

WHY THIS DESIGN?
├─ Scalability: Handles 60+ teams, 15+ PB
├─ Reliability: No single point of failure
├─ Governance: Central platform, decentralized data
├─ Cost: Optimized per team, per query
└─ Simplicity: Clear separation of concerns
```

### Moving from CDM Next Toward Data Mesh

```
CURRENT STATE (Controlled Data Movement):
├─ Central CDM Next team
├─ Teams request data
├─ CDM Next delivers

EVOLUTION (Toward Data Mesh):
├─ Payment team: Publishes payment data as data product
│  └─ SLA, documentation, ownership
├─ User team: Publishes user data as data product
│  └─ SLA, documentation, ownership
├─ Order team: Publishes order data as data product
│  └─ SLA, documentation, ownership
│
└─ CDM Next role evolves:
   ├─ Provides self-serve platform
   ├─ Enforces governance policies
   ├─ Maintains data catalog
   └─ Teams self-serve publish data

BENEFITS:
├─ Each team moves faster
├─ Ownership clear
├─ Quality improves
├─ Platform scales with company
```

---

## Choosing an Architecture

```
Decision framework:

SIMPLE REQUIREMENTS?
├─ Yes → Single pipeline (extract → load)
└─ No → Continue

NEED REAL-TIME?
├─ Yes → Kappa or Lambda
├─ No → Batch (simpler)

NEED REPROCESSING CAPABILITY?
├─ Yes → Kappa (can replay) or Medallion (re-run)
└─ No → Simpler approach ok

MANY TEAMS / DOMAINS?
├─ Yes → Data Mesh (eventually)
├─ No → Centralized (CDM Next style)

NEED BOTH BATCH & REAL-TIME?
├─ Yes → Lambda
└─ No → Kappa (simpler)

MATURE ORGANIZATION?
├─ Yes → Data Mesh
└─ No → CDM Next / Medallion (simpler)
```

---

## Key Takeaways

✅ **Lambda**: Batch + streaming for accuracy + speed (complex)  
✅ **Kappa**: Streaming only, simpler if you can replay (easier)  
✅ **Medallion**: Bronze-Silver-Gold layers, audit trail  
✅ **Data Mesh**: Domain ownership at scale (mature orgs)  
✅ **Event-Driven**: Loose coupling, async processing  
✅ **Ingestion**: Pull/Push/CDC - choose based on source  
✅ **Transformation**: ELT becoming standard (flexibility)  
✅ **Storage**: Hot/Warm/Cold for cost optimization  
✅ **Serving**: Different tools for OLAP/OLTP/Real-time  

---

## Next Module Preview

Module 5 focuses on **Cloud Architecture with GCP Focus**—how these architectural patterns map to specific GCP services (BigQuery, Dataflow, Pub/Sub, Composer, etc.) and how to design production systems on GCP.

---

**Module 4 Complete**: You understand the major data pipeline patterns and when to use each.
