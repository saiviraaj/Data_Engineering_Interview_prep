# MODULE 2: Core Architectural Components & Services
## Understanding Building Blocks of Distributed Systems

---

## Table of Contents
1. [Overview of Architectural Components](#overview)
2. [Compute Services](#compute)
3. [Storage & Databases](#storage)
4. [Messaging & Streaming](#messaging)
5. [Caching Systems](#caching)
6. [Load Balancing](#load-balancing)
7. [API Gateway](#api-gateway)
8. [Monitoring & Observability](#monitoring)
9. [Security Services](#security)
10. [Component Selection Matrix](#selection)

---

## Overview of Architectural Components

Every distributed system is composed of standardized, well-understood components. Your job as architect is not to invent new components, but to **select the right combination** for your problem.

```
APPLICATION LAYER
├─ REST APIs / GraphQL / gRPC

API GATEWAY / LOAD BALANCER
├─ Request routing, rate limiting, SSL termination

SERVICE LAYER
├─ User Service, Order Service, Payment Service
├─ Auth Service, Analytics Service

MESSAGING LAYER (Async Communication)
├─ Kafka / RabbitMQ / Cloud Pub/Sub
├─ Message queues for decoupling

STORAGE LAYER
├─ Databases: SQL, NoSQL
├─ Data warehouses: BigQuery
├─ Data lakes: Cloud Storage
├─ Caches: Redis, Memcached

SUPPORTING SERVICES
├─ Logging: Cloud Logging, ELK Stack
├─ Monitoring: Prometheus, Cloud Monitoring
├─ Tracing: Jaeger, Cloud Trace
├─ Secrets: Vault, Cloud Secret Manager
└─ Service Discovery: Consul, Eureka
```

The key insight: **These components are standardized**. AWS has them, GCP has them, on-prem has them. Your design transfers across clouds.

---

## Compute Services

Compute = "Where does code run?"

### 1. Virtual Machines (VMs)

**What**: Linux/Windows instances with full OS

```
┌──────────────┐
│   Your App   │
├──────────────┤
│   OS (Linux) │
├──────────────┤
│ Hypervisor   │
├──────────────┤
│Physical Server
```

**Characteristics**:
- Full control over OS, kernel, packages
- Can install anything (Kafka, custom binaries)
- Need to manage OS patches, security updates
- Startup time: 30-60 seconds
- Hourly billing (more expensive per hour)

**Compute Engine (GCP)**:
- N1, N2, N2D machines
- Custom CPU/memory ratios
- Preemptible instances (75% cheaper, can be killed)

**When to use VMs**:
- ✅ Custom workloads (Kafka, Hadoop)
- ✅ Existing monolithic applications
- ✅ Need OS-level control
- ❌ Variable traffic (waste on idle time)
- ❌ Simple APIs (overkill to manage OS)

**Example**: CDM Next compute would use Compute Engine

---

### 2. Containers (Docker/Kubernetes)

**What**: Lightweight virtual machines (only your app + dependencies)

```
┌──────────────┐
│   Your App   │
├──────────────┤
│ Lib, Deps    │
├──────────────┤
│  Container   │
├──────────────┤
│OS (shared)   │
├──────────────┤
│Physical Server
```

**Characteristics**:
- Lightweight (10-100MB vs 1GB for VMs)
- Fast startup (1-2 seconds vs 30-60 for VMs)
- Pay per resource (CPU/memory actually used)
- Easier deployment (Dockerfile = infrastructure as code)
- Orchestration overhead (Kubernetes is complex)

**GKE (Google Kubernetes Engine)**:
- Managed Kubernetes on GCP
- Auto-scaling, self-healing
- Multi-region support

**When to use Containers**:
- ✅ Microservices architecture
- ✅ Variable traffic (auto-scale up/down)
- ✅ DevOps maturity (can handle K8s complexity)
- ✅ Multi-cloud strategy (same container everywhere)
- ❌ SPOF services (overhead not worth it)
- ❌ Batch jobs (simpler to use VMs + Dataflow)

---

### 3. Serverless (Functions as a Service)

**What**: Write function, platform handles infrastructure

```
You write:
├─ Function(request) → response

Platform handles:
├─ VMs, OS, scaling, networking, monitoring
└─ You pay only for execution time
```

**Characteristics**:
- Zero infrastructure management
- Pay per invocation (1ms granularity)
- Cold start: 100-500ms first call
- Stateless only (no persistent state)
- Limited to platform limits (memory, timeout)

**Cloud Functions (GCP)**:
- HTTP or event-triggered
- 2nd gen: Python, Node, Go, Java
- Max 60 minute timeout

**Cloud Run (GCP)**:
- Container-based serverless
- Can run any language
- Max 60 minute timeout
- Best of both worlds (container + serverless)

**When to use Serverless**:
- ✅ APIs with bursty traffic
- ✅ Event processing (Cloud Pub/Sub triggers)
- ✅ Simple business logic
- ✅ Want zero ops burden
- ❌ Complex dependencies
- ❌ 24/7 heavy traffic (expensive)
- ❌ Needs persistent local state

**Example**: Validation function for CDM Next could be Cloud Function

---

### 4. Managed Services (BigQuery, Dataflow, Dataproc)

**What**: Google runs the infrastructure, you define logic

Dataflow (Apache Beam):
- Stream & batch processing
- Auto-scaling (1-1000 workers)
- Exactly-once semantics
- Serverless (you don't manage VMs)

Dataproc (Hadoop/Spark):
- Spark, Hadoop, Hive
- Ephemeral clusters (create, run job, destroy)
- Faster (no HDFS overhead)

When to use:
- ✅ Data pipeline workflows (ETL/ELT)
- ✅ Batch processing (Spark)
- ✅ Streaming (Dataflow)
- ❌ Interactive queries (use BigQuery instead)
- ❌ Real-time ML (use Vertex AI)

---

## Storage & Databases

Storage = "Where does data live?"

### Understanding: OLTP vs OLAP

These are fundamentally different systems, often confused:

```
OLTP (Online Transactional Processing)
├─ Use case: Processing transactions
├─ Example: E-commerce order
├─ Queries: Single row inserts/updates
├─ Query pattern: Write-heavy, read single rows
├─ Example DB: PostgreSQL, MySQL, Oracle
├─ Example: "Update customer address"
├─ Response time needed: <100ms
└─ Size: GB-TB

OLAP (Online Analytical Processing)
├─ Use case: Analytics, reporting
├─ Example: "What was revenue last month?"
├─ Queries: Scan millions of rows, aggregations
├─ Query pattern: Read-heavy, batch writes, full scans
├─ Example DB: BigQuery, Redshift, Snowflake
├─ Example: "Sum all orders from last month grouped by product"
├─ Response time needed: <1 second (acceptable: 1-30s)
└─ Size: TB-PB
```

**Never use OLTP for analytics**: Would scan entire table, kill system
**Never use OLAP for transactions**: Terrible for single-row access, expensive

---

### OLTP Databases

#### SQL Databases (PostgreSQL, MySQL, Oracle)

**What**: Structured data with ACID guarantees

```
Schema:
├─ USERS table
│  ├─ id (primary key)
│  ├─ email
│  └─ created_at
│
├─ ORDERS table
│  ├─ id (primary key)
│  ├─ user_id (foreign key)
│  └─ amount

Queries:
├─ INSERT INTO users (email) VALUES (...)
├─ UPDATE orders SET status = 'shipped' WHERE id = ?
├─ SELECT * FROM users WHERE id = ?
```

**Characteristics**:
- ACID guarantees (Atomicity, Consistency, Isolation, Durability)
- Strong consistency
- Excellent for structured data
- Scales to ~10K QPS (single instance)
- Scaling requires sharding (complex)

**When to use**:
- ✅ Financial systems (ACID is critical)
- ✅ Structured data (clear schema)
- ✅ Small-medium scale (<1TB)
- ✅ Transactions (insert multiple tables)
- ❌ Unstructured data (JSON blobs)
- ❌ PB-scale (sharding nightmare)
- ❌ Extreme write throughput (>10K QPS)

**Cloud SQL (GCP)**:
- Managed PostgreSQL/MySQL
- Automated backups, high availability
- Read replicas for scaling reads

---

#### NoSQL Databases (MongoDB, Firebase, DynamoDB)

**What**: Flexible schema, horizontal scaling

```
Document:
{
  "user_id": "123",
  "email": "user@example.com",
  "profile": {
    "name": "John",
    "bio": "..."
  },
  "social_links": ["linkedin", "twitter"]
}

Can change schema per document!
```

**Characteristics**:
- Flexible schema (add fields without migration)
- Eventually consistent (fast writes)
- Horizontal scaling (built-in sharding)
- Scales to 1M+ QPS
- Eventual consistency (not ACID)

**Types**:

```
Document DB (MongoDB, Firestore):
├─ JSON documents
├─ Hierarchical data
├─ Good for user profiles, documents

Key-Value DB (Redis, DynamoDB):
├─ Simple key → value lookup
├─ Extremely fast
├─ Good for caching, sessions

Graph DB (Neo4j):
├─ Nodes and relationships
├─ Good for social networks, recommendations

Time Series DB (InfluxDB, Prometheus):
├─ Timestamps as primary key
├─ Good for metrics, logs, monitoring
```

**When to use NoSQL**:
- ✅ Unstructured data
- ✅ Need horizontal scaling
- ✅ Can tolerate eventual consistency
- ✅ Variable schema (users can have different fields)
- ❌ ACID transactions needed
- ❌ Complex joins
- ❌ Structured reporting

**Cloud Firestore (GCP)**:
- Document database
- Real-time updates
- Scales automatically
- Good for mobile apps

**Cloud Datastore (GCP)**:
- Key-value database
- Good for sessions, user state
- Automatic scaling

---

### Data Warehouses (OLAP at Scale)

**What**: Massive parallel processing of structured data

```
Data pipeline:
├─ Raw data (TB-PB)
├─ Transform (Dataflow)
├─ Load into warehouse
├─ Query with SQL
└─ Results in sub-second
```

**BigQuery (GCP)**:
- Serverless OLAP
- 100PB+ scale
- SQL interface
- Automatic parallelization
- Pay per byte scanned (not storage)

**Characteristics**:
- Excellent query performance (even 1B row scans)
- Columnar storage (compress 100:1)
- Built-in ML functions
- Multi-tenant (data isolation via IAM)
- Cost based on data scanned (not processing)

**When to use**:
- ✅ Analytics workloads (1000+ row scans)
- ✅ TB-PB scale data
- ✅ SQL reporting
- ✅ Real-time dashboards
- ❌ Single-row lookups (use OLTP)
- ❌ Transactional consistency needed
- ❌ Sub-100ms required latency

**Your CDM Next**: Uses BigQuery for analytics

---

### Data Lakes (OLAP with Files)

**What**: Store raw data as files, transform on-demand

```
S3/Cloud Storage/ADLS:
├─ Raw data files (Parquet, CSV, JSON)
├─ Data format: Whatever (Parquet best)
└─ Access pattern: Scan files with Spark/Dataflow

vs

BigQuery:
├─ Pre-organized data
├─ Internal columnar format
└─ Direct SQL queries
```

**When to use Data Lake**:
- ✅ Unstructured data (images, documents, logs)
- ✅ Many different data types
- ✅ Want to avoid vendor lock-in
- ✅ Very cost-conscious (storage is cheap)
- ❌ Need sub-second query performance (slow)
- ❌ Want SQL directly (must transform first)

**Cloud Storage (GCP)**:
- Standard, Nearline, Coldline, Archive tiers
- Pay less for data you access less
- Works with Dataflow, BigQuery

---

### Choosing: SQL vs NoSQL vs Warehouse vs Lake

```
Question: Do I need transactions?
├─ YES → SQL (PostgreSQL)
└─ NO → Continue

Question: Do I need horizontal scaling?
├─ YES → NoSQL or Warehouse
└─ NO → SQL works fine

Question: Is data structured?
├─ YES → Warehouse (BigQuery) if analytics
│        SQL (PostgreSQL) if transactional
└─ NO → Data Lake (Cloud Storage)

Question: What's my query pattern?
├─ Single row lookups → OLTP (SQL or NoSQL)
├─ Analytics (scans millions) → Warehouse
├─ Unstructured → Data Lake
└─ Everything → Data mesh (multiple)
```

---

## Messaging & Streaming Systems

Messaging = "How do systems communicate asynchronously?"

### 1. Message Queues (RabbitMQ, Cloud Pub/Sub)

**What**: Async message passing between services

```
Service A (Producer)
├─ "Send message: user_created"
└─ Queue

Queue (durable storage)
├─ Waits for consumer

Service B (Consumer)
├─ Reads message
├─ Processes
└─ Acknowledges (message deleted)
```

**Characteristics**:
- Decoupling (producer doesn't wait)
- Durable (survives crashes)
- Ordering guarantees
- At-least-once delivery

**Cloud Pub/Sub (GCP)**:
- Publisher-Subscriber model
- Scales to 1M+ msg/sec
- Serverless (no cluster to manage)
- Automatic scaling

**When to use**:
- ✅ Decouple services
- ✅ Async processing
- ✅ Microservices communication
- ❌ Need ordering across multiple producers
- ❌ Long-term storage (use data lake)

---

### 2. Event Streaming (Kafka, Cloud Pub/Sub with subscriptions)

**What**: Continuous stream of events

```
Topics:
├─ user_events (partitioned by user_id)
│  ├─ Partition 0: [user_1, user_2, user_3]
│  ├─ Partition 1: [user_4, user_5, user_6]
│  └─ Partition 2: [user_7, user_8, user_9]
│
├─ Consumers:
│  ├─ Analytics consumer (group_A)
│  ├─ Real-time consumer (group_B)
│  └─ ML consumer (group_C)

All three can replay history!
```

**Kafka (open source)**:
- Distributed message broker
- Persistent log (weeks of history)
- Multiple consumers
- Ordering per partition

**Cloud Pub/Sub (GCP)**:
- Simpler than Kafka (no cluster to manage)
- Serverless
- Automatic scaling
- But: No ordering guarantee

**When to use**:
- ✅ Event-driven architecture
- ✅ Multiple consumers need same stream
- ✅ Want to replay history
- ✅ Real-time analytics
- ❌ Simple request/response (overkill)
- ❌ Transactional guarantees needed

**Your CDM Next**: Uses Pub/Sub for real-time events

---

## Caching Systems

Caching = "Store hot data in fast storage"

### Redis (In-Memory Cache)

**What**: Fast key-value store in memory

```
SET user:123 {name: "John", email: "john@example.com"}
GET user:123 → {name: "John", ...}

Latency: <1ms
Throughput: 100K+ ops/sec
```

**Data Types**:
- Strings (cache serialized objects)
- Lists (queue, leaderboard)
- Sets (unique items, bloom filters)
- Sorted Sets (rankings, timestamps)
- Hashes (object fields)

**Characteristics**:
- In-memory (fast but volatile)
- Single-threaded (simple consistency)
- Can persist to disk (slower)
- Clustering available (distributed Redis)

**When to use Redis**:
- ✅ Session storage
- ✅ Leaderboards
- ✅ Rate limiting
- ✅ Real-time analytics
- ❌ Large data (memory expensive)
- ❌ Permanent storage needed (use database)

**Cloud Memorystore (GCP)**:
- Managed Redis
- Automatic failover
- High availability

---

### Caching Strategies

**Cache-Aside (Lazy Loading)**:
```
Request comes in:
├─ Check cache
├─ If hit: Return cached data
└─ If miss: 
   ├─ Query database
   ├─ Store in cache
   └─ Return data

Pros: Simple, no stale data
Cons: First request slow (cache miss)
```

**Write-Through**:
```
Write request comes in:
├─ Write to cache
├─ Write to database
└─ Return success

Pros: Cache always consistent
Cons: Every write hits cache
```

**Write-Behind**:
```
Write request comes in:
├─ Write to cache
├─ Return success
└─ Async write to database

Pros: Fast writes
Cons: Risk of data loss if cache dies
```

---

## Load Balancing

Load Balancing = "Distribute traffic across multiple servers"

### Round-Robin Load Balancing

```
Client requests:
├─ Request 1 → Server 1
├─ Request 2 → Server 2
├─ Request 3 → Server 3
├─ Request 4 → Server 1
└─ ...repeat
```

**Problem**: Doesn't account for server load

### Least Connections Load Balancing

```
Client requests:
├─ Server 1: 10 connections
├─ Server 2: 15 connections
├─ Server 3: 5 connections
│
└─ New request → Server 3 (fewest connections)
```

**Better**: Balances actual load

### Weighted Load Balancing

```
Server 1: 8 cores (weight 4)
├─ Gets 40% of traffic

Server 2: 4 cores (weight 2)
├─ Gets 20% of traffic

Server 3: 4 cores (weight 2)
└─ Gets 20% of traffic
```

**GCP Cloud Load Balancing**:
- Global load balancing
- Auto-scaling groups
- Health checks
- Supports: HTTP(S), TCP, UDP

---

## API Gateway

API Gateway = "Single entry point for all requests"

**What it does**:
```
Request comes in:
├─ Authenticate (check JWT)
├─ Rate limit (user quota)
├─ Route to backend (user service → /users)
├─ Log (for audit trail)
├─ Transform response
└─ Send back

Benefits:
├─ Centralized security
├─ Rate limiting
├─ Request/response transformation
├─ API versioning
└─ Request logging
```

**GCP Cloud API Gateway**:
- Built on OpenAPI/Swagger
- Managed (no VMs)
- Auto-scaling
- Can integrate with Cloud Run, Compute Engine

---

## Monitoring & Observability

Monitoring = "Know what's happening in your system"

### The Three Pillars: Logs, Metrics, Traces

**Logs**: Discrete events
```
2024-01-15 10:32:45 ERROR BigQuery query failed
├─ User: user_123
├─ Query: SELECT * FROM dataset.table
├─ Error: Quota exceeded
└─ Duration: 5000ms
```

**Metrics**: Time-series data (numbers)
```
cpu_usage: 65%
memory_usage: 2.1GB
request_count: 1523
request_latency_p99: 250ms
error_rate: 0.1%
```

**Traces**: Request flow across services
```
User request comes in:
├─ API Gateway: 10ms
├─ Auth Service: 20ms
├─ User Service: 150ms
├─ Database query: 100ms
├─ Cache write: 5ms
└─ Total: 285ms
```

**GCP Suite**:
- Cloud Logging: Centralized log storage
- Cloud Monitoring: Metrics, dashboards, alerts
- Cloud Trace: Distributed tracing

---

## Security Services

Security = "Protect your system from attacks"

### IAM (Identity & Access Management)

**Who can do what?**
```
Service Account X (identity)
├─ Can read from BigQuery dataset Y
├─ Can write to Cloud Storage bucket Z
└─ Cannot delete anything
```

**GCP IAM**:
- Service accounts (for services)
- User accounts (for people)
- Roles (collections of permissions)
- Bindings (who has what role)

### Encryption

**In Transit**: HTTPS/TLS
- Protect data while traveling

**At Rest**: Cloud KMS
- Protect data stored
- Keys managed by Google

**Example**: Customer email encrypted
```
Plaintext: john@example.com
Encrypted: a3f8d7c2b1e9...

Only your service account can decrypt
(using Cloud KMS key)
```

### Secrets Management

Cloud Secret Manager:
- Store API keys securely
- Access control (who can read)
- Audit logs (who accessed when)
- Rotation policies

---

## Component Selection Matrix

```
┌─────────────────────┬──────────────┬──────────────┬──────────────┐
│ Problem             │ GCP Service  │ Scale        │ Cost Model   │
├─────────────────────┼──────────────┼──────────────┼──────────────┤
│ Run custom code     │ Compute Eng. │ 1-1000 VMs   │ Per hour     │
│ Microservices       │ GKE          │ 1-10K pods   │ Per node     │
│ Simple API          │ Cloud Run    │ Auto         │ Per invocation
│ Transactions        │ Cloud SQL    │ 1-10K QPS    │ Per hour     │
│ Unstructured data   │ Firestore    │ 1M+ QPS      │ Per op       │
│ Analytics queries   │ BigQuery     │ PB scale     │ Per byte     │
│ Raw data storage    │ Cloud Stor.  │ Unlimited    │ Per GB/mo    │
│ Batch processing    │ Dataflow     │ Auto         │ Per core/hr  │
│ Streaming           │ Pub/Sub      │ 1M+ msg/s    │ Per msg      │
│ Cache/sessions      │ Memorystore  │ 300GB        │ Per GB/hr    │
│ Auth/secrets        │ Cloud IAM    │ Unlimited    │ Included     │
└─────────────────────┴──────────────┴──────────────┴──────────────┘
```

---

## Key Takeaways

✅ **Compute**: VMs (control), Containers (balance), Serverless (no ops)
✅ **Storage**: SQL (transactions), NoSQL (scale), Warehouse (analytics), Lake (flexible)
✅ **Messaging**: Queues (decoupling), Streaming (events)
✅ **Caching**: Redis (fast), but limited to hot data
✅ **Monitoring**: Logs + Metrics + Traces = observability
✅ **Security**: IAM (access), Encryption (protection), Secrets (keys)

---

**Module 2 Complete**: You understand each component independently.

**In Module 3**, we'll learn how to combine these to design complete systems.
