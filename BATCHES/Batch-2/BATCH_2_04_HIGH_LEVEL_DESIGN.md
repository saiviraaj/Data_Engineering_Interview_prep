# High-Level Design (HLD): Designing System Architecture
## How to Design Systems That Scale, Survive Failures, and Evolve

**Target**: Data engineers designing systems  
**Level**: Intermediate to advanced  
**Time**: 8-10 hours reading + 5-6 hours practice  
**Goal**: Design systems that are scalable, reliable, and maintainable

---

## Table of Contents

1. [What is High-Level Design?](#what-is-high-level-design)
2. [Core HLD Principles](#core-hld-principles)
3. [System Components](#system-components)
4. [Scalability Patterns](#scalability-patterns)
5. [Reliability Patterns](#reliability-patterns)
6. [HLD Design Process](#hld-design-process)
7. [HLD Examples](#hld-examples)

---

## What is High-Level Design?

### Definition

**High-Level Design** = Designing overall system architecture

```
Low-Level Design:
├─ Designing a single class
├─ Example: How should TradeValidator work?
└─ Focus: Single component, internal logic

High-Level Design:
├─ Designing entire system
├─ Example: How should whole trading platform work?
└─ Focus: Components, interactions, scalability, reliability

HLD Decisions:
├─ Which databases? (PostgreSQL, BigQuery, Redis)
├─ How do services communicate? (REST, gRPC, Kafka)
├─ How do we scale? (Horizontal, vertical, caching)
├─ How do we handle failures? (Redundancy, fallbacks)
└─ How do we monitor? (Metrics, logs, traces)
```

### HLD vs LLD

```
Low-Level Design:
├─ "Design the DataExtractor class"
├─ What methods? What attributes?
├─ How does it work internally?
└─ Focus: Single component

High-Level Design:
├─ "Design a real-time data pipeline"
├─ What components? (Extractor, Transformer, Loader)
├─ How do they communicate?
├─ What databases? What message queues?
├─ How do we scale each component?
└─ Focus: Entire system

Analogy:
├─ LLD: Designing a car engine (details)
├─ HLD: Designing a factory that makes cars (big picture)
```

---

## Core HLD Principles

### 1. Scalability

**Definition**: System can handle increasing load

```
Vertical Scaling (scale up):
├─ Bigger machine (more CPU, RAM)
├─ Easier but limited (max machine size)
└─ Example: 8 core → 32 core server

Horizontal Scaling (scale out):
├─ More machines
├─ Harder but unlimited
└─ Example: 1 server → 10 servers

For data pipelines:
├─ Extract: Horizontal (more extractors reading different sources)
├─ Transform: Horizontal (Spark with more executors)
├─ Load: Horizontal (parallel writes to BigQuery)
└─ Most systems use mix of both
```

### 2. Reliability

**Definition**: System keeps working when things fail

```
Redundancy:
├─ Multiple copies of critical components
├─ If one fails, others take over
└─ Example: 3 database replicas (one fails, 2 keep running)

Fault Tolerance:
├─ System continues despite failures
├─ Degraded service is better than no service
└─ Example: If cache fails, query database directly (slower but works)

Recovery:
├─ Detect failures quickly
├─ Restart failed components
├─ Restore state
└─ Example: Kubernetes auto-restarts crashed services

Monitoring:
├─ Know immediately when something fails
├─ Alert engineers
├─ Useful metrics help diagnose issues
└─ Example: CPU high → suspect resource leak
```

### 3. Maintainability

**Definition**: System is easy to understand and modify

```
Separation of Concerns:
├─ Each component has clear responsibility
├─ Changes to one don't affect others
└─ Example: Extraction separate from transformation

Documentation:
├─ How system works (architecture diagrams)
├─ How to deploy (runbooks)
├─ How to debug (troubleshooting guides)
└─ Why decisions were made (ADRs - Architecture Decision Records)

Testability:
├─ Easy to test components in isolation
├─ Easy to test entire system
├─ Quick feedback (tests run fast)
└─ Example: Mock external services for testing

Version Control:
├─ Code, config, infrastructure all in Git
├─ Track history of changes
├─ Easy to roll back
└─ Enables safe experimentation
```

### 4. Efficiency

**Definition**: System uses resources well

```
Cost Efficiency:
├─ Use right tool for job (don't over-engineer)
├─ Cache to reduce expensive operations
├─ Batch operations where possible
└─ Example: Batch writes to database (1 transaction for 100 records vs 100 transactions)

Performance Efficiency:
├─ Minimize latency (faster response)
├─ Maximize throughput (more work per second)
├─ Profile to find bottlenecks
└─ Example: Add caching layer to reduce database latency

Resource Efficiency:
├─ Use memory wisely (streaming instead of loading all)
├─ Use CPU wisely (parallel processing)
├─ Use network wisely (compression, batching)
└─ Example: Stream large files instead of loading to memory
```

---

## System Components

### Types of Components

**Data Sources**:
```
Where data comes from:
├─ Databases (PostgreSQL, Oracle)
├─ Data warehouses (BigQuery, Snowflake)
├─ Message queues (Kafka, RabbitMQ)
├─ APIs (REST, GraphQL)
└─ Files (S3, GCS)

Design questions:
├─ How often does data change?
├─ How much data is there?
├─ How current does it need to be?
└─ Is it 24/7 or on schedule?
```

**Processing**:
```
What transforms the data:
├─ Batch processing (Spark, Hadoop)
├─ Stream processing (Kafka Streams, Flink)
├─ Real-time processing (Lambda architecture)
└─ Scheduled jobs (Airflow, Cron)

Design questions:
├─ How long can processing take?
├─ Must it be real-time?
├─ Can it run in parallel?
└─ What's failure tolerance?
```

**Storage**:
```
Where data lives:
├─ Transactional (PostgreSQL - fast reads/writes)
├─ Analytical (BigQuery - fast aggregations)
├─ Cache (Redis - ultra-fast reads)
├─ Archive (S3 - cheap, slow)
└─ Search (Elasticsearch - full-text search)

Design questions:
├─ Read or write heavy?
├─ How current does data need to be?
├─ How much data?
├─ What queries are most common?
```

**Serving**:
```
How data is delivered to users:
├─ REST API
├─ GraphQL API
├─ Dashboards (web UI)
├─ Reports (batch delivery)
└─ Real-time streams (WebSocket)

Design questions:
├─ How many concurrent users?
├─ How fast must responses be?
├─ How much data per request?
└─ What SLA is needed?
```

---

## Scalability Patterns

### Pattern 1: Sharding

```
Problem: Data too large for single database

Teradata database: 1 trillion rows
├─ Single database: Unbearably slow
└─ Solution: Split across multiple databases

Sharding by trader_id:
├─ Shard 1: Traders T0000-T1999
├─ Shard 2: Traders T2000-T3999
├─ Shard 3: Traders T4000-T5999
└─ Each shard 1/3 the data = 3x faster!

Queries:
├─ Single trader: Hit one shard (fast)
├─ All traders: Hit all shards, aggregate (slower)
└─ Tradeoff: Usually 99% of queries are single-shard

Challenges:
├─ Hot shards (some traders more active)
├─ Cross-shard transactions (complex)
├─ Resharding (adding shards requires data movement)
└─ Know your access patterns before sharding!
```

### Pattern 2: Caching

```
Problem: Database queries are slow

Database query: 100ms (accessing disk)
Cache hit: 1ms (in memory)
100x faster!

Caching strategy:
├─ Cache frequently accessed data
├─ Use TTL to expire stale data
├─ Invalidate when data changes
└─ Have fallback if cache fails

Levels:
├─ Browser cache (user's computer)
├─ CDN cache (geographically distributed)
├─ Application cache (in-memory)
├─ Database cache (built-in)
└─ Use multiple levels!

Example:
1. User requests: GET /api/trade/123
2. Check browser cache: Miss
3. Check CDN cache: Miss
4. Check Redis cache: Miss
5. Query database: Hit (slow)
6. Populate all caches
7. Return to user

Next request same user:
└─ Browser cache hit (instant!)

Next request different user (same trade):
1. Browser cache: Miss (different user)
2. CDN cache: Hit (instant!)
```

### Pattern 3: Replication

```
Problem: Single database is point of failure

One database:
├─ It goes down: No data access
└─ Unacceptable for critical systems

Replication:
├─ Master database (receives writes)
├─ Slave 1 (backup copy)
├─ Slave 2 (backup copy)
├─ All data replicated across 3 machines

Master fails:
├─ Promote Slave 1 to Master
├─ Point writes to Slave 1
├─ Data is safe!

Reads scale:
├─ Read from Slaves (don't overload Master)
├─ 1 Master + 2 Slaves = 3x read capacity!

Tradeoff:
├─ Synchronous: All replicas updated before success (slow)
├─ Asynchronous: Master updates, slaves catch up (fast, risk of loss)
└─ Semi-sync: At least 1 replica updated (balance)
```

### Pattern 4: Load Balancing

```
Problem: Single server can't handle all requests

1000 requests/second:
├─ Single server: Overloaded, slow, fails
└─ Solution: Multiple servers with load balancer

Load balancer:
├─ Receives all requests
├─ Distributes to available servers
└─ Each server handles fewer requests

Algorithms:
├─ Round-robin: Server 1, 2, 3, 1, 2, 3...
├─ Least connections: Send to server with fewest active connections
├─ IP hash: Same client always goes to same server (session stickiness)
└─ Weighted: More powerful servers get more requests

Benefits:
├─ Horizontal scaling (add more servers)
├─ High availability (server failure doesn't bring down system)
└─ Maintenance (can take servers down for updates)
```

---

## Reliability Patterns

### Pattern 1: Circuit Breaker

```
Problem: Failing service crashes caller

Scenario:
├─ Service A calls Service B
├─ Service B is down (network error, timeout)
├─ Service A keeps retrying
├─ Service A times out, becomes slow
└─ Cascading failure!

Circuit Breaker Solution:

States:
├─ CLOSED: Normal operation
├─ OPEN: Service failing, don't call it
└─ HALF_OPEN: Try calling again

Transitions:
CLOSED → OPEN (failures exceed threshold)
    ↓
OPEN → HALF_OPEN (wait, then try)
    ↓
HALF_OPEN → CLOSED (success, resume normal)
    ↓
HALF_OPEN → OPEN (still failing, back to open)

Example:
Service A calls Service B:
├─ Request 1: Succeeds (CLOSED)
├─ Request 2: Times out
├─ Request 3: Times out
├─ Threshold reached → Open circuit
├─ Request 4: Fails immediately (don't call B)
├─ Request 5: Fails immediately (don't call B)
├─ Wait 30 seconds...
├─ Request 6: Try calling B (HALF_OPEN)
├─ Request 6: Succeeds!
├─ Circuit closes (CLOSED)
└─ Request 7: Normal operation

Benefits:
├─ Fails fast (don't wait for timeout)
├─ Protects failing service (gives it time to recover)
└─ Prevents cascading failures
```

### Pattern 2: Retry with Exponential Backoff

```
Problem: Transient failures (temporary, will recover)

Network hiccup:
├─ Request fails
├─ Immediate retry might also fail
├─ Need to wait and try again

Exponential Backoff:
├─ 1st attempt: Send immediately
├─ 1st failure: Wait 1 second, retry
├─ 2nd failure: Wait 2 seconds, retry
├─ 3rd failure: Wait 4 seconds, retry
├─ 4th failure: Wait 8 seconds, retry
├─ 5th failure: Give up

Why exponential?
├─ If temporary issue, resolved by 1-2 seconds
├─ If not, maybe recovering, give more time
├─ Avoids overwhelming failing service
└─ System recovers on its own in many cases

Pseudocode:
for attempt in range(5):
    try:
        result = call_service()
        return result
    except TransientError:
        wait_time = 2 ** attempt  # 1, 2, 4, 8, 16
        sleep(wait_time)

# Fails after 5 attempts
raise ServiceUnavailable()
```

### Pattern 3: Bulkheads

```
Problem: One failing component cascades to others

Thread pool: 100 threads

Service A needs 50 threads (memory leak, acquiring but not releasing)
└─ Service B starves for threads!
└─ Service B can't respond to requests
└─ Users think entire system is down

Bulkhead Solution:

Separate thread pools per service:
├─ Service A: 50 threads
├─ Service B: 30 threads
├─ Service C: 20 threads
└─ Each has own resources!

Service A thread pool exhausted:
├─ Service A slows down
├─ Service B unaffected (separate pool)
└─ Service C unaffected (separate pool)

Failure isolation:
├─ One service failure doesn't cascade
├─ Others continue working
└─ Partial degradation > total failure

Apply to:
├─ Database connections (separate pools per service)
├─ Thread pools (separate pools per feature)
├─ Message queues (separate topics per service)
└─ Disk (separate volumes per service)
```

---

## HLD Design Process

### Step 1: Understand Requirements

```
Functional Requirements:
├─ What should the system do?
├─ Extract trades from multiple sources
├─ Process millions of trades per day
├─ Load to BigQuery warehouse
└─ Provide reports to traders

Non-Functional Requirements:
├─ Latency: Should users wait <1 second for report?
├─ Throughput: How many trades per second?
├─ Availability: Can system be down?
├─ Consistency: Can data be slightly stale?
└─ Scalability: How much growth expected?
```

### Step 2: Identify Components

```
What needs to be built?

Data Pipeline example:
├─ Extraction (read from Teradata, Oracle, Kafka)
├─ Transformation (apply business logic)
├─ Validation (check data quality)
├─ Loading (write to BigQuery)
├─ Monitoring (track health)
└─ Alerting (notify on errors)
```

### Step 3: Design Interactions

```
How do components talk?

Synchronous:
├─ REST API
├─ gRPC
└─ Direct function calls

Asynchronous:
├─ Message queues (Kafka, RabbitMQ)
├─ Event streaming
└─ Webhooks

Choose based on:
├─ Does caller need immediate response? → Synchronous
├─ Is latency critical? → Synchronous
├─ Can work be done later? → Asynchronous
└─ Do you need reliability? → Asynchronous
```

### Step 4: Plan for Scalability

```
How will each component scale?

Extract:
├─ Parallel extraction from multiple sources
├─ Kafka partitions for parallelism
└─ Horizontal scaling

Transform:
├─ Spark with multiple executors
├─ RDD/DataFrame partitioning
└─ Linear scaling with CPU

Load:
├─ Parallel writes to BigQuery
├─ Batch loading (more efficient than row-by-row)
└─ Stream loading for real-time

Cache:
├─ Redis for frequent queries
├─ TTL for staleness tolerance
└─ Horizontal scaling with Redis cluster
```

### Step 5: Plan for Failures

```
What can fail?

Data source down:
├─ Retry with backoff
├─ Use cached data if available
├─ Alert after repeated failures
└─ Manual intervention if persistent

Network timeout:
├─ Timeout after 30 seconds
├─ Retry 3 times with exponential backoff
├─ Fail if still not working
└─ Circuit breaker prevents cascading

Database full:
├─ Monitor disk usage
├─ Archive old data
├─ Expand capacity proactively
└─ Alert if reaching limit

Processing crash:
├─ Kubernetes auto-restart
├─ Preserve state (resume from checkpoint)
├─ Human monitoring and intervention
└─ Detailed logs for debugging
```

### Step 6: Design Monitoring

```
What to monitor?

Application metrics:
├─ Trades processed per second
├─ Processing latency (p50, p95, p99)
├─ Error rate
└─ Cache hit rate

Infrastructure metrics:
├─ CPU usage
├─ Memory usage
├─ Disk I/O
└─ Network bandwidth

Database metrics:
├─ Query latency
├─ Connections active
├─ Long-running queries
└─ Replication lag

Alerts:
├─ Error rate > 1% → Page engineer
├─ Latency p99 > 5s → Page engineer
├─ Disk > 90% full → Page engineer
└─ 0 trades in 1 hour → Page engineer
```

---

## HLD Examples

### Example: Real-Time Trade Processing Pipeline

```
Requirements:
├─ Process 100K trades/second
├─ Latency < 1 second to dashboard
├─ 99.99% availability
└─ Support multiple data sources

Architecture:

                     Teradata   Oracle   Kafka
                        ↓        ↓        ↓
                    Extraction Layer
                        ↓
                   Kafka Cluster
                  (partition: trader_id)
                        ↓
                 Spark Streaming
              (transform, validate)
                        ↓
                   BigQuery
              (real-time ingestion)
                        ↓
                    Redis Cache
                  (recent trades)
                        ↓
                   REST API
                        ↓
                  Dashboards

Components:

1. Extraction:
   ├─ TeradataExtractor (500 records/sec)
   ├─ OracleExtractor (300 records/sec)
   ├─ KafkaConsumer (99200 records/sec)
   └─ Parallel extraction from 3 sources

2. Kafka:
   ├─ Topic: trades
   ├─ Partitions: 256 (by trader_id)
   ├─ Replication: 3 (availability)
   └─ Retention: 7 days

3. Spark Streaming:
   ├─ Consume from Kafka
   ├─ Transform (calculate metrics)
   ├─ Validate (check rules)
   ├─ Executors: 100
   └─ Latency: 5-10 seconds

4. BigQuery:
   ├─ Table: trades (partitioned by date)
   ├─ Clustering: trader_id, symbol
   ├─ Streaming inserts
   └─ Real-time dashboard queries

5. Redis Cache:
   ├─ Last 1000 trades per trader
   ├─ Recent aggregations
   ├─ TTL: 1 hour
   └─ Cache hit rate: 95%

6. API:
   ├─ GET /trades/trader/:id
   ├─ GET /dashboard/:trader_id
   ├─ POST /alert/:rule_id
   └─ Load balanced (3 instances)

Scalability:

Growth 2x:
├─ Kafka: Increase partitions to 512
├─ Spark: Increase executors to 200
├─ BigQuery: Already scales automatically
└─ API: Add more instances

Growth 10x:
├─ Shard by trader (multiple pipelines)
├─ More Kafka clusters
├─ BigQuery slot reservation
└─ Regional caches

Reliability:

Data loss prevention:
├─ Kafka replication (3 replicas)
├─ BigQuery backup (automatic)
├─ Checkpointing in Spark
└─ Retry with backoff

Failure handling:
├─ Source fails: Retry, use other sources
├─ Kafka fails: Replay from disk
├─ Spark fails: Restart from checkpoint
├─ BigQuery fails: Queue in Kafka, retry later
└─ Cache fails: Query BigQuery directly
```

---

**You now understand High-Level Design.**

**Next: Combining LLD + HLD + SOLID + Patterns = Expert System Design!**
