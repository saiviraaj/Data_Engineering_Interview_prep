# MODULE 3: Critical Design Principles
## Mastering the Core Concepts That Drive Architecture

---

## Table of Contents
1. [Introduction](#introduction)
2. [Scalability Dimensions](#scalability)
3. [Performance Optimization](#performance)
4. [Availability & Fault Tolerance](#availability)
5. [Consistency Models](#consistency)
6. [Data Management](#data-management)
7. [Cost Optimization](#cost)
8. [Putting It All Together](#integration)

---

## Introduction

If Module 1 taught you *why* systems are designed certain ways, and Module 2 taught you *what* components exist, then Module 3 teaches you *how* to apply design principles to make smart architectural decisions.

**The Core Principle**: Every architectural decision is a trade-off between competing principles.

```
SCALABILITY
    ↕
PERFORMANCE  ↔  CONSISTENCY
    ↕
AVAILABILITY  →  COST
```

You can't optimize for everything. Your job as an architect is to understand these principles deeply, measure what matters for your specific problem, and make intentional trade-offs.

---

## Scalability Dimensions

Scalability is the ability to handle growth. But growth comes in many forms:

```
USERS (from 1K to 1M)
├─ More read traffic
├─ More write traffic
├─ More concurrent connections
└─ Larger data per user

DATA (from 1GB to 1PB)
├─ Storage grows
├─ Queries get slower
├─ Index sizes grow
└─ Backup time increases

CONCURRENCY (more simultaneous requests)
├─ Database connections pool depletes
├─ Cache hit ratio drops
├─ Lock contention increases
└─ Network becomes bottleneck

GEOGRAPHIC (more regions)
├─ Latency increases
├─ Consistency harder
├─ Compliance complexity
└─ Cost multiplies
```

### Horizontal vs Vertical Scaling

**Vertical Scaling (Scale Up)**:
```
Single Machine Evolution:
├─ 1 CPU → 2 CPU → 4 CPU → 8 CPU
├─ 8GB RAM → 16GB → 32GB → 64GB
└─ Single large server

Characteristics:
├─ Simple (no distributed complexity)
├─ Limited ceiling (biggest machine is still finite)
├─ Single point of failure
├─ Easier to maintain (1 server)
└─ More expensive per CPU

When to use:
├─ Early stage (scale from 0 to 100K users)
├─ Non-critical systems
├─ Development/staging
└─ Before you need HA
```

**Horizontal Scaling (Scale Out)**:
```
Add More Machines:
├─ 1 server (1K users)
├─ 2 servers (2K users)
├─ 5 servers (5K users)
├─ 100 servers (100K users)
└─ 1000 servers (1M+ users)

Characteristics:
├─ Complex (distributed systems problems)
├─ Unlimited ceiling (add more servers)
├─ No single point of failure
├─ Harder to maintain (many servers)
├─ Cheaper per CPU (commodity hardware)

When to use:
├─ Need high availability
├─ Anticipate rapid growth
├─ Want cost efficiency
├─ Need geographic distribution
└─ Building critical systems
```

### Real Example: CDM Next Scaling

CDM Next started with:
```
2016-2017 (Early stage)
├─ Single cloud project
├─ Vertical scaling (bigger VMs)
├─ Single region (us-central1)
└─ ~5 teams using it

2018-2019 (Growth)
├─ Multiple projects per team
├─ Started horizontal scaling (multiple instances)
├─ Multiple regions (considerations)
└─ ~30 teams using it

2020-2024 (Current)
├─ 60+ teams
├─ 15+ PB migrated
├─ Heavily horizontally scaled
├─ Global distribution
└─ Multi-region for HA
```

**Key insight**: CDM Next had to transition from vertical to horizontal scaling as it grew. Systems designed for vertical scaling don't transition smoothly—you often need architectural rework.

### Database Scaling

This is where horizontal scaling gets complex. Databases are stateful, which makes distributing them hard.

**Read Scaling (Easier)**:
```
Write to Primary
     ↓
Read Replicas (1, 2, 3, ...)

Architecture:
├─ Primary (1): Accepts all writes
├─ Replicas (N): Accept reads only
├─ Replication lag: 1-100ms typically

Benefits:
├─ Read throughput increases linearly with replicas
├─ Primary not overloaded by reads
└─ Simple to understand

Drawbacks:
├─ Replication lag means stale reads
├─ All writes still go to primary (bottleneck)
└─ Failover requires promoting replica

When to use:
├─ Read-heavy workloads (90% reads, 10% writes)
├─ Can tolerate eventual consistency
└─ Example: BigQuery, analytics systems
```

**Write Scaling (Hard)**:
```
Option 1: Sharding (Split data by key)
┌─────────────────┬─────────────────┐
│  Shard 1        │  Shard 2        │
│ (Users 0-999)   │ (Users 1000-1999)│
│ Database 1      │ Database 2      │
└─────────────────┴─────────────────┘

Router layer:
├─ Request comes in (user_id = 1500)
├─ Calculate: shard = user_id % 2 = 0
├─ Route to Shard 2
└─ Done!

Benefits:
├─ Write throughput increases with shards
├─ Each shard is smaller (faster queries)
├─ Scales to massive write load

Drawbacks:
├─ Complex to implement
├─ Can't easily join across shards
├─ Resharding is painful (data migration)
├─ Risk of uneven shard sizes
└─ Data locality concerns

When to use:
├─ Write-heavy workloads
├─ Can tolerate complexity
├─ Long-term (resharding is expensive)
└─ Example: MongoDB Atlas, Cassandra
```

**Example: BigQuery's approach**
```
BigQuery doesn't expose sharding to users!
├─ You create one table
├─ BigQuery handles sharding internally
├─ You partition by date (manually specified)
├─ BigQuery physically distributes data
├─ You query as if it's single table
└─ This is the dream (but expensive to build)
```

### Caching for Scaling

Caching is one of the most powerful scaling techniques:

```
WITHOUT CACHE:
├─ Request comes in
├─ Query database (50ms)
├─ Return response
└─ User sees: 50ms latency

WITH CACHE:
├─ Request comes in
├─ Check cache (1ms hit)
├─ Found? Return cached result (1ms)
├─ Not found? Query database (50ms), cache, return
└─ User sees: 1-50ms latency (average much lower)

CACHE HIT RATIO IMPACT:
├─ 50% hit ratio: (0.5 × 1) + (0.5 × 50) = 25.5ms average
├─ 80% hit ratio: (0.8 × 1) + (0.2 × 50) = 10.8ms average
├─ 95% hit ratio: (0.95 × 1) + (0.05 × 50) = 2.95ms average
└─ High hit ratio = massive latency improvement
```

**Cache Saturation Point**:
```
As you add more caches, benefit diminishes:

Cache 1: 0% → 80% hit ratio (huge improvement)
Cache 2: 80% → 85% hit ratio (small improvement)
Cache 3: 85% → 87% hit ratio (tiny improvement)

Why?
└─ After hitting most common requests (80%)
   └─ Remaining 20% are rare/cold data
   └─ Adding cache helps less

Lesson: Cache hot data (80/20 rule applies)
```

**Replication for Scaling**:
```
Sync Replication:
├─ Write to primary
├─ Wait for all replicas to confirm
├─ Return to user: "Write successful"

Benefits:
├─ Guarantee: If function returns, all replicas have it

Drawbacks:
├─ One slow replica slows entire write
├─ Latency = slowest replica
├─ Example: 3 replicas, one on high-latency network
   └─ All writes wait for that one

When to use:
├─ Consistency critical
├─ Financial systems
└─ Small number of replicas

Async Replication:
├─ Write to primary
├─ Return to user immediately: "Write successful"
├─ Replicate to other nodes in background

Benefits:
├─ Fast writes (don't wait for replicas)
├─ Better throughput

Drawbacks:
├─ Risk: Primary crashes before replicating
   └─ User thinks write succeeded but it's lost!
├─ Eventual consistency (replicas lag)

When to use:
├─ Throughput more important than consistency
├─ Can tolerate data loss
├─ Social media, analytics
└─ Example: Cassandra, DynamoDB
```

---

## Performance Optimization

Performance is about minimizing latency and maximizing throughput.

### Latency vs Throughput Trade-off

These are often inversely related:

```
LOW LATENCY, LOW THROUGHPUT:
├─ Process requests one at a time
├─ Each request: 10ms
├─ Throughput: 100 requests/second
└─ Example: Synchronous processing

HIGH LATENCY, HIGH THROUGHPUT:
├─ Batch 1000 requests
├─ Process all together
├─ Latency: 1000ms for whole batch
├─ Throughput: 1000 requests/second (each is 1ms avg)
└─ Example: Batch Dataflow job

Hybrid approach (best of both):
├─ Buffer requests for up to 100ms
├─ Once 1000 buffered or 100ms passed, process
├─ Latency: 100ms (worst case)
├─ Throughput: 10K requests/second
└─ Example: Pub/Sub with Dataflow windowing
```

### P99 Latency (The Real Metric)

Most people think about average latency. **Don't.**

```
AVERAGE LATENCY: 100ms
├─ Calculation: Sum all latencies / count
├─ Problem: One outlier ruins it
├─ Example:
│  ├─ 999 requests: 50ms each = 49.95s total
│  ├─ 1 request: 50,000ms (slow one!)
│  ├─ Total: 50.05s / 1000 = 50ms average
│  └─ But 99.9% of users see <50ms, 0.1% see 50 seconds!

PERCENTILE LATENCY (Better):
├─ P50 (median): 45ms (50% of requests faster)
├─ P95: 55ms (95% of requests faster, 5% slower)
├─ P99: 100ms (99% faster, 1% slower)
└─ P99.9: 500ms (99.9% faster, 0.1% slower)

Why P99 matters:
├─ That 1% of users are often important
│  ├─ Largest companies (most data)
│  ├─ Power users (most requests)
│  └─ They notice slowness most
│
├─ Your reputation determined by worst case
│  └─ "Your system is slow" (because 1% see it)
└─ SLAs measured on P99 or P99.9
```

### Query Optimization

Database queries are often the bottleneck:

```
UNOPTIMIZED QUERY:
SELECT * FROM orders WHERE customer_name = 'John'

Problem:
├─ Scan entire table (1M rows)
├─ Check each row: customer_name = 'John'?
├─ Return matching rows
├─ Latency: 1000ms (full table scan!)

OPTIMIZED QUERY:
Create index on customer_name
SELECT * FROM orders WHERE customer_name = 'John'

Now:
├─ Use index to jump to 'John' rows
├─ Latency: 10ms (100x faster!)
└─ Cost: Extra storage for index

Index Trade-off:
├─ Pros: Query fast
├─ Cons: Writes slower (must update index)
│        Extra storage needed
└─ Decision: Worth it if reads >> writes
```

**Query Optimization Principles**:

```
1. Use Indexes
├─ Index on WHERE clause columns
├─ Index on JOIN columns
└─ Don't index everything (slows writes)

2. Avoid SELECT *
├─ Bad: SELECT * FROM orders
│      └─ Returns 50 columns (1000 bytes per row)
├─ Good: SELECT order_id, amount FROM orders
│        └─ Returns 2 columns (16 bytes per row)
└─ Same query, 50x less data transfer

3. Push Filtering Down
├─ Bad: SELECT * FROM orders
│      └─ Fetch 1M rows, filter in app (customer = 'John')
├─ Good: SELECT * FROM orders WHERE customer = 'John'
│        └─ Database filters, return 100 rows
└─ Huge difference for large tables

4. Use Aggregations Wisely
├─ Bad: Fetch all 1M rows, count in app
├─ Good: SELECT COUNT(*) FROM orders (1ms)
└─ Database can do this efficiently
```

### Batch vs Real-Time Trade-off

```
BATCH PROCESSING (High Throughput, High Latency):
├─ Accumulate data for 1 hour
├─ Process all at once (Dataflow job)
├─ Latency: 1 hour (data might be old)
├─ Throughput: Very high (process efficiently)
└─ Cost: Cheap (process at off-peak hours)

Example: Daily analytics report
├─ Accumulate: Customer orders all day
├─ Process: 11pm Dataflow job
├─ Available: 6am next day (8 hour latency)
├─ Throughput: 1M orders/hour
└─ Cost: $2/day

REAL-TIME PROCESSING (Low Latency, Lower Throughput):
├─ Process immediately (Pub/Sub + Dataflow)
├─ Latency: <1 second
├─ Throughput: Limited (process as it comes)
└─ Cost: Expensive (always running)

Example: Fraud detection
├─ Transaction occurs
├─ Real-time pipeline detects (100ms)
├─ Block fraudulent transaction immediately
├─ Throughput: 1000 txn/sec
└─ Cost: $50,000/month (always on)

HYBRID (Lambda Architecture):
├─ Batch job: Process daily (analytics)
├─ Real-time job: Process streaming (fraud)
├─ Combine results for decision
└─ Cost: Medium, complexity: High
```

**Your CDM Next**: Uses both!
- Batch: Daily migrations (high throughput, can be slow)
- Real-time: Streaming for urgent data (low latency)
- Hybrid: Both available, users choose

---

## Availability & Fault Tolerance

Availability measures how often your system is up and working.

### Single Points of Failure (SPOF)

A SPOF is anything that, if it breaks, takes down the whole system:

```
SYSTEM WITH SPOF:
Application → Database
             (single copy)

Problem:
├─ If database dies
├─ All reads fail
├─ All writes fail
├─ System down: 100% downtime
└─ Recovery: Restore from backup (4+ hours)

SOLUTION - Replication:
Application → Primary Database
           ↘ Replica 1
             Replica 2

Now:
├─ If Primary dies
├─ Failover to Replica automatically (30 seconds)
├─ Downtime: 30 seconds (acceptable)
└─ Recovery: Rebuild primary
```

### Circuit Breaker Pattern

When a service is failing, don't keep hammering it:

```
SERVICE A → SERVICE B (failing)

Problem without Circuit Breaker:
├─ Service B is slow/down
├─ Service A keeps sending requests
├─ Requests pile up, timeout after 30s
├─ Service A's resources depleted
├─ Eventually Service A dies too (cascading failure)

Circuit Breaker Solution:
├─ Service A calls Service B
├─ B responds: ERROR
├─ Count failures (5 in a row)
├─ TRIP CIRCUIT: Stop sending to B for 60s
├─ Service A can recover (not overloaded)
├─ After 60s: Try again (is B fixed?)
│  ├─ Success? Close circuit, resume normal
│  └─ Still failing? Trip again, wait 60s more

States:
├─ CLOSED: Normal, sending requests
├─ OPEN: Failing, not sending (save resources)
└─ HALF-OPEN: Testing, see if fixed

Benefits:
├─ Prevent cascading failures
├─ Faster recovery (don't overload)
├─ Better system resilience
```

### Health Checks & Liveness Probes

How does a load balancer know if a server is healthy?

```
WITHOUT HEALTH CHECKS:
Load Balancer → Server 1 ✓
             → Server 2 ✗ (dead, load balancer doesn't know)
             → Server 3 ✓

When request comes:
├─ LB sends to Server 2 (no response)
├─ Request times out after 30s
├─ User sees 30s delay

WITH HEALTH CHECKS:
Load Balancer checks every 10s:
├─ Server 1: GET /health → 200 OK ✓
├─ Server 2: GET /health → TIMEOUT ✗
└─ Server 3: GET /health → 200 OK ✓

LB removes Server 2 from pool
└─ All new requests go to 1 & 3
└─ Server 2 recovered? Readded to pool

Health check should:
├─ Check if service actually works
│  ├─ Bad: Just check if process running
│  ├─ Good: Check if can query database
│  └─ Example: /health endpoint
│
├─ Be fast (< 1 second)
├─ Not use real business logic
│  └─ Bad: /health checks customer purchase history
│  └─ Good: /health checks local cache
└─ Be reliable (no false positives)
```

### Graceful Degradation

When something fails, don't crash—degrade gracefully:

```
SCENARIO: Recommendation service dies

WITHOUT GRACEFUL DEGRADATION:
├─ User visits product page
├─ Page tries to load recommendations
├─ Recommendation service down
├─ Page crashes
└─ User sees error page

WITH GRACEFUL DEGRADATION:
├─ User visits product page
├─ Page tries to load recommendations
├─ Recommendation service down (circuit breaker open)
├─ Show default: "Bestselling items" instead
├─ User still happy (not ideal, but works)
└─ Recommendation team fixes service
```

### Chaos Engineering

Test your system's resilience by breaking things intentionally:

```
CHAOS EXPERIMENTS:
├─ Kill random pod (Kubernetes)
   └─ System should failover
├─ Disconnect database for 10s
   └─ System should timeout gracefully
├─ Add 500ms latency to all requests
   └─ System should handle with circuit breaker
├─ Lose 10% of network packets
   └─ Retries should handle
└─ All during business hours, monitored

Benefits:
├─ Find failure modes before production
├─ Build confidence in resilience
├─ Improve runbooks
└─ Train on-call team

Netflix heavily uses this (Chaos Monkey)
```

---

## Consistency Models

How much data consistency do you actually need?

### Strong Consistency

**Definition**: All readers see latest write immediately

```
Write: x = 5
└─ Send to all replicas
└─ Wait for confirmation from all
└─ Return to user: "Write successful"

Read: Get x
└─ Can read from any replica
└─ All have x = 5
└─ No stale data possible

Guarantee: If write succeeds, all subsequent reads see it
```

**Cost**:
- Slow writes (wait for all replicas)
- Latency: 50-200ms even for simple write
- Can't tolerate network partition (unavailable)

**When to use**:
- Financial systems (money can't disappear)
- Medical systems (wrong dosage kills)
- Critical data (customer addresses)

**Example**: PostgreSQL with synchronous replication

### Eventual Consistency

**Definition**: All readers will eventually see latest write (within seconds)

```
Write: x = 5
└─ Write to primary
└─ Return to user immediately
└─ Async replicate to other nodes
   └─ After 1-10 seconds, all have x = 5

Read (immediately after write):
├─ Read from replica
├─ Might see old value (x = 3)
├─ Wait 5 seconds, read again: x = 5
└─ Eventually consistent!

Guarantee: If you wait long enough, all see latest
```

**Cost**:
- Fast writes (no waiting)
- Latency: <10ms for writes
- Tolerate network partition (keep serving stale data)

**When to use**:
- Social media feeds (stale ok)
- Analytics (1 hour old ok)
- Real-time dashboards (eventually updated ok)
- High-traffic systems (need speed)

**Example**: Cassandra, DynamoDB, Redis

### Causal Consistency

**Definition**: If operation A caused operation B, all see them in that order

```
User A: "I like this post" → Like event
User B: "I like this post" → Like event
User C: "I'll like too because User A did" → Like event

Causal: C's like must come after A's like (caused by it)
Strong: All see same order, immediately
Eventual: Eventually see same order

Causal consistency:
├─ Cheaper than strong consistency
├─ More intuitive than eventual
└─ Hard to implement
```

### Read-After-Write Consistency

**Definition**: After you write, your reads of that data see the write

```
Problem: Eventual consistency
├─ User changes password to "abc123"
├─ System writes: password = hash("abc123")
├─ User immediately reads password field
├─ Reads from old replica: password = hash("old")
└─ User confused: "Did my change work?"

Read-After-Write consistency:
├─ User writes to primary
├─ For that user's subsequent reads:
│  ├─ If reading own data, read from primary
│  ├─ If reading others' data, ok to read from replica
│  └─ User always sees their own writes
└─ Solves the problem!

Cost: Small overhead (route reads to primary for own data)
```

---

## Data Management

How do you store and replicate data safely?

### Backup Strategies

```
NO BACKUP:
├─ Data loss = gone forever
├─ RTO: 0 (no recovery)
├─ RPO: Unlimited (lose everything)
└─ Only acceptable for test data

DAILY BACKUPS:
├─ Every 24h, snapshot of data
├─ If disaster: Restore from yesterday's backup
├─ RTO: 4-8 hours (restore + restart systems)
├─ RPO: 24 hours (lose last day of data)
└─ Cost: $0 (S3 is cheap)

HOURLY BACKUPS:
├─ Every 1h, backup
├─ RTO: 2-4 hours
├─ RPO: 1 hour
└─ Cost: Still cheap

REAL-TIME REPLICATION:
├─ Write → Primary + Replicas simultaneously
├─ RTO: <1 minute (failover)
├─ RPO: 0-5 seconds
└─ Cost: High (multiple copies, always on)

MULTI-REGION REPLICATION:
├─ Write to region A, sync to region B
├─ If entire region A dies: failover to region B
├─ RTO: <5 minutes
├─ RPO: <1 second
└─ Cost: Very high (2x everything)
```

**Your CDM Next**: Uses daily backups + read replicas
- RTO: 2 hours (restore from backup, replay logs)
- RPO: 1 hour (hourly snapshots)
- Cost: ~$X/month

### Retention & Archival

```
HOT DATA (Last 7 days):
├─ Cloud Storage Standard
├─ Cost: $0.020/GB/month
├─ Access: Instant
└─ Use case: Current analytics

WARM DATA (7 days - 3 months):
├─ Cloud Storage Nearline
├─ Cost: $0.010/GB/month
├─ Access: Within hours
└─ Use case: Historical analysis

COLD DATA (> 3 months):
├─ Cloud Storage Coldline
├─ Cost: $0.004/GB/month
├─ Access: Within days
└─ Use case: Compliance, long-term archive

FROZEN DATA (> 1 year):
├─ Cloud Storage Archive
├─ Cost: $0.0012/GB/month
├─ Access: Within hours (expensive)
└─ Use case: 7-year compliance hold

Example: 1PB over time
├─ First week (hot): $20K/month
├─ After 6 months (warm): $10K/month
├─ After 1 year (cold): $4K/month
└─ Total: Much cheaper than keeping all hot!
```

---

## Cost Optimization

Your beautiful architecture will be shut down if it costs too much.

### Compute Cost

```
ON-DEMAND INSTANCES:
├─ Pay per hour
├─ Compute Engine: $0.05/hour for small instance
├─ Good for: Variable traffic, don't know peak
└─ Cost: High if running 24/7

RESERVED INSTANCES:
├─ Commit for 1 year, pay upfront
├─ Compute Engine: $0.025/hour (50% discount)
├─ Good for: Baseline traffic (always needed)
└─ Cost: Lower if predictable

SPOT INSTANCES:
├─ Use spare capacity, can be killed anytime
├─ Compute Engine: $0.01/hour (80% discount!)
├─ Good for: Batch jobs (can restart)
└─ Cost: Very cheap

MIX STRATEGY:
├─ Baseline: 10 reserved instances ($250/month)
├─ Variable: Auto-scale with spot instances ($50/month)
├─ Total: $300/month (vs $500 if all on-demand)
```

### Storage Cost Optimization

```
OVER-PROVISIONING (Bad):
├─ "We might need 100TB"
├─ Allocate 100TB immediately
├─ Actually use 10TB
├─ Cost: $2000/month for unused storage
└─ Wasted money!

RIGHT-SIZING (Good):
├─ Track actual usage
├─ "We use 10TB now, growing 1TB/month"
├─ Allocate just enough for 3 months
├─ Upgrade when needed
├─ Cost: $200/month, grows gradually
```

### Query Cost in BigQuery

BigQuery charges per byte scanned:

```
UNOPTIMIZED QUERY:
SELECT * FROM orders
Cost: Scan all 100 columns × 1M rows = 100GB scanned = $0.50

OPTIMIZED QUERY:
SELECT order_id, amount FROM orders
Cost: Scan 2 columns × 1M rows = 20MB scanned = $0.0001

100GB vs 20MB query = 5000x cost difference!
```

---

## Putting It All Together

How do these principles interact?

### Case Study: CDM Next Scaling

**2016: Single Team, Simple**
```
Architecture:
├─ Vertical scaling (bigger VMs)
├─ Single Cloud SQL database
├─ Single project
└─ Throughput: 100 GB/day

Principles:
├─ Scalability: Not needed yet
├─ Performance: Good (small data)
├─ Availability: 99% (single database = SPOF)
├─ Consistency: Strong (single DB)
├─ Cost: Low ($1K/month)
```

**2019: Multi-Team Growth**
```
Problems encountered:
├─ Database becoming bottleneck
├─ Single project for all = noisy neighbor
├─ HA needed (too much data loss)
└─ Cost growing (100 teams worth of storage)

Solution (redesign):
├─ Horizontal scaling (multiple projects)
├─ Async replication (speed writes)
├─ Read replicas (fast queries)
├─ Cost optimization (archive cold data)

Principles used:
├─ Scalability: Sharding by project
├─ Performance: Read replicas
├─ Availability: Replication + backups
├─ Consistency: Eventual ok for most data
└─ Cost: Tiered storage
```

**2024: Current Design**
```
Current state: 60+ teams, 15+ PB

Architecture:
├─ BigQuery (OLAP): Analytics warehouse
├─ Cloud SQL: Metadata + configuration
├─ Cloud Storage: Raw data (tiered)
├─ Pub/Sub: Real-time streaming
├─ Dataflow: Processing

Principles:
├─ Scalability: Horizontal (auto-sharding in BQ)
├─ Performance: Columnar storage, caching, query optimization
├─ Availability: Multi-region, failover
├─ Consistency: Strong for metadata, eventual for analytics
├─ Cost: Optimized per query ($M/month, but spread across 60 teams)
```

### Decision Framework

When making architecture decisions:

```
1. MEASURE CURRENT STATE
   └─ What's the actual bottleneck?
   └─ Don't optimize what isn't slow

2. UNDERSTAND TRADE-OFFS
   └─ Scalability vs Complexity
   └─ Performance vs Cost
   └─ Availability vs Simplicity

3. PRIORITIZE BY IMPACT
   └─ Biggest problem first
   └─ 80/20 rule (80% of improvement from 20% of effort)

4. IMPLEMENT INCREMENTALLY
   └─ Add complexity only when needed
   └─ Monitor after each change

5. REVISIT REGULARLY
   └─ Bottlenecks shift as system grows
   └─ What worked at 10K QPS won't at 1M QPS
```

---

## Key Takeaways

✅ **Scalability** comes in different forms (users, data, geography)  
✅ **Horizontal scaling** is powerful but complex  
✅ **Caching** is one of the best scaling tools  
✅ **Performance** is about P99, not average  
✅ **Availability** requires eliminating single points of failure  
✅ **Consistency** models let you trade off safety for speed  
✅ **Data management** (backup, retention) is critical  
✅ **Cost** matters—optimize after measuring  
✅ **Trade-offs** are everywhere—make them intentionally  

---

## Next Module Preview

Module 4 focuses on **Data Pipeline Architectures**—how to structure systems specifically for moving and processing data at scale. You'll learn Lambda, Kappa, Medallion, and Data Mesh architectures, and how CDM Next fits into this landscape.

---

**Module 3 Complete**: You now understand the principles that drive good architecture.

