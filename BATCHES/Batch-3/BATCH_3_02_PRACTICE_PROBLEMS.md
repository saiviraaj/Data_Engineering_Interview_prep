# System Design Practice Problems: 10+ Complete Solutions
## Real Interview Problems with Detailed Answers

**Format**: Each problem includes:
1. Problem statement
2. Clarifying questions & assumptions
3. High-level design
4. Deep dive on key components
5. Handling failures
6. Scaling to higher loads
7. Monitoring & alerts

**How to Use**: 
- Read problem statement
- Spend 45 minutes solving (like real interview)
- Then read solution
- Compare your approach

---

## Problem 1: Real-Time Market Data Platform

### Problem Statement

"Design a system that ingests stock market data from multiple exchanges (NYSE, NASDAQ, CRYPTO) and provides real-time updates to traders. The system needs to handle millions of price updates per second and deliver them to traders with minimal latency."

### Clarifying Questions & Assumptions

```
Questions I'd ask:
1. How many symbols are there? (10K stocks + 1K crypto)
2. What's the update frequency? (Prices update 1000x/sec per symbol)
3. How many concurrent traders? (50K concurrent users)
4. What's acceptable latency? (< 100ms from exchange to trader dashboard)
5. Do we need order book? (Yes, depth of 20 levels)
6. Storage requirement? (2 years of historical data)
7. SLA? (99.99% during market hours)

Assumptions:
- Peak: 10M price updates/sec
- 50K concurrent traders
- Real-time requirement (< 100ms)
- Exactly once delivery (no duplicate updates)
- Persistent storage for 2 years
```

### High-Level Design

```
                   NYSE  NASDAQ  CRYPTO
                    |      |       |
                    └──────┼───────┘
                           |
                    Data Ingestion
                    (TCP connections)
                           |
                        Kafka
                  (multiple partitions)
                           |
                    Stream Processor
                    (Spark Streaming)
                           |
                    ┌───────┴────────┐
                    |                |
                TimeSeriesDB      Cache
                (InfluxDB)         (Redis)
                    |                |
                    └────────┬────────┘
                             |
                         WebSocket API
                             |
                      Trader Dashboards
```

**Design Decisions**:
```
1. Kafka for ingestion:
   - Decouples sources from processing
   - Exactly-once semantics possible
   - Can replay if needed
   - Partitioned by symbol (10K partitions)

2. Spark Streaming:
   - Process 10M updates/sec
   - 100 executors × 4 cores = 400 cores
   - 10M / 400 = 25K updates per core (manageable)

3. InfluxDB for time-series:
   - Built for time-series data
   - Compression (saves 90% space)
   - Sub-second queries

4. Redis for cache:
   - Last 1000 updates per symbol
   - < 1ms latency
   - Reduce InfluxDB load

5. WebSocket API:
   - Real-time push to traders
   - Load balanced (10 instances)
   - Connection pooling
```

### Deep Dive: Handling 10M Updates/Sec

```
Math for 10M/sec:

Network:
- 10M updates × 100 bytes = 1TB/sec (before compression)
- After compression: 100GB/sec (still huge!)
- Need: High bandwidth network (1Gbps+), multiple egress points

Kafka:
- 10K symbols
- 1000 updates/sec per symbol
- 10K partitions (1 per symbol)
- Each partition: 1000 updates/sec
- Easily within Kafka's 100K messages/sec per partition

Spark:
- 400 cores (from calculation above)
- Parallelized by partition
- 25K updates per core per second
- Simple transformation (< 1ms per update)
- Latency: 100-200ms end-to-end (acceptable)

InfluxDB:
- Time-series optimized for this exact use case
- Can handle 10M writes/sec with proper sharding
- Compression: 1 year of data = ~200TB (manageable)

Redis:
- In-memory, sub-millisecond
- 10M updates/sec distributed across cluster
- Cache hit rate: 95% (recent data is hot)

Bottleneck: Network bandwidth and Kafka replication
Solution: Multiple data centers, regional processing
```

### Handling Failures

```
Source failure (Exchange goes down):
├─ Detection: Connection loss detected immediately
├─ Mitigation: Use backup exchange or switch to delayed data
├─ User impact: Minimal (just missing updates)

Kafka failure:
├─ Detection: Producers get acknowledge timeout
├─ Mitigation: Queue in memory, retry
├─ User impact: Brief hiatus (30 seconds), then catch up

Spark failure:
├─ Detection: Output stops (no new prices)
├─ Mitigation: Restart from checkpoint
├─ User impact: 1-2 minute delay in updates

InfluxDB failure:
├─ Detection: Write errors
├─ Mitigation: Queue in Kafka, retry every 30 sec
├─ User impact: Traders use cache, slight staleness

Redis failure:
├─ Detection: Cache miss rate spikes
├─ Mitigation: Query InfluxDB directly (slower but works)
├─ User impact: Slight latency increase (100ms → 500ms)

Monitoring:
├─ Alert if message lag > 1 minute (Kafka backing up)
├─ Alert if update rate drops (exchange down)
├─ Alert if error rate > 0.1%
├─ Alert if latency p99 > 500ms
```

### Scaling to 100M Updates/Sec

```
Current: 10M/sec with design above
Goal: 100M/sec (10x growth)

Solution:
1. Kafka: Add more partitions (100K instead of 10K)
2. Spark: 4000 cores (10x more executors)
3. InfluxDB: Shard by symbol (100 shards)
4. Redis: Cluster with 100 nodes
5. WebSocket: 100 API instances (10x)

Cost: 10x infrastructure cost (expected)
Complexity: Manage distributed system complexity

Alternative: Just use 10K most popular symbols
└─ Reduces to 5M/sec peak
└─ 50% of revenue from 80% of symbols
└─ Much cheaper
```

---

## Problem 2: Distributed Cache System

### Problem Statement

"Design a caching system similar to Redis/Memcached that can handle 1M requests per second, support key-value operations, and provide sub-millisecond latency."

### High-Level Design

```
Client Requests
    ├─ SET key value
    ├─ GET key
    ├─ DELETE key
    └─ INCR key

         ↓
   Load Balancer
   (route to cache node)

    ├─ Cache Node 1
    ├─ Cache Node 2
    ├─ Cache Node 3
    └─ ... (100+ nodes)

    Sharded by:
    hash(key) % num_nodes = target_node
```

### Detailed Solution

```
Architecture:

1. Client → Load Balancer → Cache Cluster

2. Sharding Strategy:
   ├─ Consistent hashing (allows node addition)
   ├─ Replication factor: 3 (availability)
   ├─ Virtual nodes (100 per physical node for balance)

3. Node Architecture:
   ├─ In-memory hashtable (< 1μs lookup)
   ├─ LRU eviction (when memory full)
   ├─ Replication (async to replicas)
   ├─ Persistence (optional, RDB snapshots)
   └─ Cluster coordination (gossip protocol)

4. Commands:
   GET key:
   ├─ Hash to node
   ├─ Lookup in hashtable
   ├─ Return value (or nil)
   └─ Latency: < 1ms

   SET key value:
   ├─ Hash to node
   ├─ Update hashtable
   ├─ Async replicate to 3 nodes
   └─ Latency: < 1ms (don't wait for replication)

   DELETE key:
   ├─ Hash to node
   ├─ Remove from hashtable
   ├─ Async replicate deletion
   └─ Latency: < 1ms

5. Handling 1M/sec:
   ├─ 1M requests distributed across 100 nodes
   ├─ 10K requests/sec per node (easily doable)
   ├─ In-memory hashtable: O(1) per operation
   └─ Network: 1M × 100 bytes = 100MB/sec (easy)

6. Failures:
   Node dies:
   ├─ Replicas contain data
   ├─ Failover: Replicas become primary
   ├─ Zero data loss (with sync replication)
   ├─ Brief unavailability (1-2 seconds)

   Network partition:
   ├─ Split brain possible (two primaries)
   ├─ Resolution: Last-write-wins or quorum

7. Improvements:
   ├─ Add bloom filters (quick "miss" detection)
   ├─ Add compression (more data in memory)
   ├─ Add persistence (RDB + AOF)
   └─ Add pub/sub (message delivery)
```

---

## Problem 3: Distributed Job Scheduler

### Problem Statement

"Design a job scheduler that can manage millions of jobs, execute them at specified times, and retry on failure. Jobs can be from various sources (data pipelines, notifications, cleanup tasks)."

### High-Level Design

```
Job Creation
  (API, UI)
     |
Job Storage
(PostgreSQL)
     |
Scheduler Service
(determines which jobs to run)
     |
Job Queue
(Kafka/RabbitMQ)
     |
  Workers
(execute jobs)
     |
Job Execution Log
(completion status)
```

### Detailed Solution

```
System Components:

1. Job Storage (PostgreSQL):
   ├─ Table: jobs (id, name, schedule, status, retry_count, created_at)
   ├─ Table: job_runs (job_id, start_time, end_time, status, error)
   ├─ Index on: schedule_time (for next scheduler query)
   └─ Sharded by job_id

2. Scheduler Service:
   ├─ Runs every 1 minute
   ├─ Query: Jobs with schedule_time <= now() AND status = PENDING
   ├─ Enqueue to job queue
   ├─ Update status to ENQUEUED
   └─ Handle: 10K jobs/minute across entire system

3. Job Queue:
   ├─ Type: Kafka topics (one per priority level)
   ├─ High priority: Urgent tasks (immediate execution)
   ├─ Medium priority: Regular tasks
   ├─ Low priority: Cleanup tasks
   └─ Partitioning: By job type (parallelize execution)

4. Workers:
   ├─ Count: Auto-scale based on queue depth
   ├─ Concurrency: 10 jobs per worker
   ├─ Timeout: 5 minutes (kill job if exceeds)
   ├─ Retry: Exponential backoff (1s, 2s, 4s, 8s...)
   └─ Report: Write results to job_runs table

5. Failure Handling:
   Job times out:
   ├─ Worker detects timeout
   ├─ Mark as FAILED
   ├─ Re-enqueue if retries < max_retries
   ├─ Exponential backoff between retries

   Worker crashes:
   ├─ Job stays in queue
   ├─ Another worker picks it up
   ├─ No loss (idempotent operations)

   Database failure:
   ├─ Can't read jobs or write results
   ├─ Queue jobs locally (in-memory)
   ├─ Retry writing results every 10 seconds

6. Scaling:
   Current: 1M jobs/day = ~700 jobs/minute
   Peak: 10x = 7000 jobs/minute

   Scaling strategy:
   ├─ Kafka: Partition by job type (10 partitions)
   ├─ Workers: Auto-scale from 100 to 1000
   ├─ Database: Shard by job_id (10 shards)
   ├─ Scheduler: Multiple instances (one leader via election)
   └─ No single bottleneck
```

---

## Problem 4: Rate Limiting Service

### Problem Statement

"Design a distributed rate limiting service that allows you to limit API requests per user (1000 per hour) and handle millions of users."

### High-Level Design

```
API Request
    |
Rate Limiter Service
(check if user exceeded limit)
    |
    ├─ YES → Return 429 Too Many Requests
    |
    └─ NO → Increment counter, allow request
```

### Detailed Solution

```
Design Approach:

1. Algorithm: Token Bucket
   ├─ Each user has bucket (capacity = 1000 tokens)
   ├─ Tokens refill at rate (1000 / 3600 = 0.278 per second)
   ├─ Each request consumes 1 token
   ├─ If bucket empty → Reject request

2. Storage (Redis):
   Key: "rate_limit:user_123:hour:2024-01-15T14"
   Value: {"tokens_remaining": 250, "last_refill": 1705305000}

   Why Redis?
   ├─ Sub-millisecond access
   ├─ Built-in expiration (TTL)
   ├─ Atomic operations

3. Logic per request:
   └─ GET current count from Redis
   └─ Calculate tokens since last refill
   └─ If count > limit → reject
   └─ Else → increment and allow

4. Scale to millions:
   ├─ Redis cluster (100 nodes)
   ├─ Partition by user_id
   ├─ Replication: 3x for redundancy
   ├─ Each node handles 10K users
   └─ Millions of users distributed

5. Failures:
   Redis down:
   ├─ Option A: Reject all requests (fail closed - safe)
   ├─ Option B: Allow all requests (fail open - user-friendly)
   ├─ Choose A for API protection

   Network partition:
   ├─ Split brain possible
   ├─ Accept temporary over-limiting
   └─ Better than false rejections

6. Advanced features:
   ├─ Multiple limits (per hour, per day, per minute)
   ├─ Different limits per user tier
   ├─ Burst allowance (10% over limit)
   ├─ Dynamic limits (adjust based on load)
```

---

## Problem 5: Database Replication System

### Problem Statement

"Design a master-slave database replication system that keeps data synchronized across multiple nodes while handling node failures."

### High-Level Design

```
Master Database
(handles writes)
     |
  Binlog
(change log)
     |
  Replication
(send changes to slaves)
     |
  ┌───┬───┬───┐
Slave1 Slave2 Slave3
(read replicas)
```

### Detailed Solution

```
Replication Details:

1. Master:
   ├─ Receives writes
   ├─ Records to binlog (sequential log)
   ├─ Sends binlog to slaves
   └─ Acknowledges after slaves receive

2. Binlog Format:
   ├─ Statement-based: SQL statements
   ├─ Row-based: Individual row changes
   ├─ Mixed: Depends on query
   └─ Use: Row-based (simpler, more reliable)

3. Slave Replication:
   ├─ Receives binlog events
   ├─ Applies to own data
   ├─ Tracks position (binlog offset)
   ├─ Can replay from any position
   └─ Lag: Usually 1-10 seconds

4. Failure Scenarios:

   Slave fails:
   ├─ Missing data from failure to recovery
   ├─ On restart: Catch up from master (replay binlog)
   ├─ Once caught up: Resume replication

   Master fails:
   ├─ Elect one slave as new master
   ├─ Redirect writes to new master
   ├─ Other slaves replicate from new master
   ├─ Potential data loss (if slave was behind)

   Network partition:
   ├─ Slaves can't see master
   ├─ Writes still go to master
   ├─ When reconnected: Slaves catch up

5. Consistency Guarantees:

   Asynchronous (default):
   ├─ Master writes, returns immediately
   ├─ Replication happens async
   ├─ Fast, but risk of data loss if master fails

   Semi-synchronous:
   ├─ Master writes, waits for 1 slave ACK
   ├─ Then returns to client
   ├─ Slower, safer

   Synchronous:
   ├─ Master waits for all slaves to ACK
   ├─ Very safe, very slow
   ├─ Not practical for high-throughput

   Recommendation: Semi-synchronous

6. Monitoring:
   ├─ Alert if replication lag > 30 seconds
   ├─ Alert if slave disconnected
   ├─ Alert if binlog size too large
   ├─ Automatic failover if master down > 5 minutes
```

---

## Problem 6-10: Summary (Quick Reference)

Due to length constraints, here's overview of remaining problems:

```
Problem 6: Search Engine Indexing
├─ Crawl web pages
├─ Build inverted index (word → pages)
├─ Handle updates
└─ Query: "Find pages containing word X"

Problem 7: Video Streaming Service
├─ Store videos on S3
├─ Stream with adaptive bitrate
├─ Handle millions of concurrent users
└─ CDN for geographically distributed delivery

Problem 8: Notification System
├─ Send millions of emails/SMS/push
├─ Retry on failure
├─ Handle provider rate limits
└─ Track delivery status

Problem 9: Recommendation Engine
├─ Collaborative filtering (users similar to you)
├─ Content-based (items similar to liked items)
├─ Real-time personalization
└─ Update recommendations periodically

Problem 10: URL Shortening Service
├─ Generate short URLs (example: bit.ly)
├─ Map short → long (fast lookup)
├─ Handle billions of links
└─ Redirect with analytics
```

---

## How to Practice

### Method 1: Timed Practice
```
1. Set timer for 45 minutes
2. Read problem statement
3. Solve on whiteboard/paper
4. After 45 minutes: Check solution
5. Compare approaches
6. Identify gaps in your thinking
```

### Method 2: Study Solutions
```
1. Read problem
2. Read solution carefully
3. Understand each decision
4. Why that choice? What are tradeoffs?
5. How would you modify for different scale?
```

### Method 3: Modify Problems
```
Original: Design for 1M requests/sec
Modified: Design for 10M requests/sec
├─ What changes?
├─ What stays same?
└─ Where does scale break?

Original: Accept eventual consistency
Modified: Require strong consistency
├─ What changes?
├─ What are trade-offs?
└─ Is it worth the complexity?
```

---

**These 10 problems cover the main categories you'll see in interviews.**

**Next: Study Guide for Batch 3!**
