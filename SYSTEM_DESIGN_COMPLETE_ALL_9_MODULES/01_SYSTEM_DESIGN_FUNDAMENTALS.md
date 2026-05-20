# MODULE 1: SYSTEM DESIGN FUNDAMENTALS
## PhD-Level Data Engineering Interview Preparation
### Tailored for Viraaj Sivaraju — Senior Data Engineer, Wells Fargo CDM Next

---

## PART 1: WHAT IS SYSTEM DESIGN?

System design is the process of defining the architecture, components, interfaces, and data flows of a system to satisfy specified requirements. In data engineering interviews, system design tests your ability to:

- Break down ambiguous problems into concrete components
- Make architecture decisions with explicit tradeoffs
- Scale solutions from prototype to petabyte
- Reason about failures and recovery
- Communicate complex ideas clearly under time pressure

At senior/principal level, you are expected to not just design a working system but to demonstrate **engineering judgment** — knowing what to optimize for, what to sacrifice, and why.

---

## PART 2: THE CAP THEOREM — DEEP UNDERSTANDING

### Statement

In a distributed system, you can guarantee at most **two** of the following three properties simultaneously:

- **C — Consistency**: Every read receives the most recent write or an error
- **A — Availability**: Every request receives a response (not necessarily the most recent data)
- **P — Partition Tolerance**: The system continues operating despite network partitions

### Why P is Non-Negotiable

In any real distributed system, network partitions **will** occur. A partition is when some nodes cannot communicate with other nodes. This is not a theoretical concern — it happens regularly due to network hardware failures, datacenter issues, and routing problems.

Therefore, in practice, the choice is always **CP vs AP**:

```
CP (Consistency + Partition Tolerance):
  - On partition: refuse reads/writes that might return stale data
  - Return error or wait until partition resolves
  - Examples: HBase, Zookeeper, Spanner (with caveats), etcd
  - Use when: financial transactions, distributed locks, configuration stores

AP (Availability + Partition Tolerance):
  - On partition: continue serving requests, may return stale data
  - Favor availability over correctness
  - Examples: Cassandra, DynamoDB, CouchDB, DNS
  - Use when: user-facing reads, caching, analytics, social media feeds
```

### The Nuance: CAP is Binary, Reality is a Spectrum

CAP theorem is about what happens **during a partition**. Outside of partitions, you can have both consistency and availability. The real-world question is: **how long can you tolerate inconsistency, and how much data loss is acceptable?**

This leads to PACELC.

---

## PART 3: PACELC — THE COMPLETE MODEL

PACELC extends CAP by addressing normal operation (no partition):

```
IF Partition THEN choose between Availability vs Consistency
ELSE (no partition) choose between Latency vs Consistency
```

| System | P → A or C | E → L or C | Implication |
|---|---|---|---|
| DynamoDB (default) | AP | EL | Fast reads, eventual consistency |
| DynamoDB (strong) | CP | EC | Slower reads, always consistent |
| Spanner | CP | EC | Strong consistency everywhere |
| Cassandra | AP | EL | Fast, eventually consistent |
| BigQuery | CP | EC | Consistent, higher latency |
| Bigtable | CP | EL | Consistent reads, low latency |

### How to Use PACELC in Interviews

When choosing a storage system, articulate:

> "For this use case, I need [high availability / strong consistency]. During a partition, I prefer [serve stale data / reject requests]. During normal operation, I'm willing to trade [latency for consistency / consistency for latency]. Therefore I'll use [X]."

---

## PART 4: CONSISTENCY MODELS — THE COMPLETE SPECTRUM

From strongest to weakest:

```
LINEARIZABILITY (Strict Consistency):
  - Operations appear instantaneous and globally ordered
  - Every read reflects the latest write
  - Cost: highest latency, lowest throughput
  - Example: Spanner, Zookeeper
  - Use: distributed locks, leader election

SEQUENTIAL CONSISTENCY:
  - All operations appear in some sequential order
  - Each process's operations appear in program order
  - Not as strong as linearizability (no real-time guarantee)
  - Rarely seen in practice — mostly academic

CAUSAL CONSISTENCY:
  - Causally related operations seen in order by all nodes
  - Concurrent operations may be seen in different orders
  - Example: MongoDB causal sessions
  - Use: comments/replies (reply must come after post)

EVENTUAL CONSISTENCY:
  - If no new updates, all replicas converge to same value
  - No guarantee on convergence time
  - Example: DynamoDB, Cassandra, DNS
  - Use: shopping cart, DNS records, social media likes

READ-YOUR-WRITES:
  - User always sees their own writes
  - Other users may see stale data
  - Practical compromise for user-facing systems
  - Example: sticky sessions to same replica

MONOTONIC READ:
  - Once you've read a value, you'll never read an older value
  - Prevents "time going backwards" experience
  - Combined with read-your-writes: strong user experience
```

---

## PART 5: RTO AND RPO — DISASTER RECOVERY FUNDAMENTALS

### Definitions

```
RPO — Recovery Point Objective:
  Maximum acceptable data loss measured in time.
  "How old can our recovered data be?"
  
  RPO = 0:     Zero data loss (synchronous replication required)
  RPO = 1 hr:  Up to 1 hour of transactions may be lost
  RPO = 24 hr: Up to 1 day of data may be lost (nightly backup sufficient)

RTO — Recovery Time Objective:
  Maximum acceptable downtime after a failure.
  "How quickly must we be back online?"
  
  RTO = 0:      Active-active (no downtime ever)
  RTO = 15 min: Hot standby (failover in minutes)
  RTO = 4 hr:   Warm standby (bring up replica, restore, redirect)
  RTO = 24 hr:  Cold backup (restore from backup, hours to days)
```

### Cost vs RPO/RTO Tradeoff

```
                    HIGH COST
                        │
    Active-Active  ─────┤ RTO≈0, RPO≈0
    (multi-region)      │
                        │
    Hot Standby    ─────┤ RTO=mins, RPO=secs
    (sync replica)      │
                        │
    Warm Standby   ─────┤ RTO=hours, RPO=mins
    (async replica)     │
                        │
    Cold Backup    ─────┤ RTO=days, RPO=hours
    (GCS backup)        │
                    LOW COST
```

### CDM Next Context

> CDM Next targets 99.99% availability (< 52 min downtime/year), which implies RTO < 15 minutes for most failure scenarios. We achieved this via Cloud Composer retry logic, Dataflow auto-restart, and multi-zone GCS + BigQuery deployments.

---

## PART 6: SCALABILITY — VERTICAL VS HORIZONTAL

### Vertical Scaling (Scale Up)

```
Add more resources to a single machine:
  - More CPU cores
  - More RAM
  - Faster SSD
  
PROS:
  - Simple — no distributed systems complexity
  - No data partitioning needed
  - Low latency (no network hops)

CONS:
  - Hard limit (biggest machine = 128 cores, 12 TB RAM)
  - Single point of failure
  - Expensive at the top end
  - Downtime required for upgrade

WHEN TO USE:
  - Databases up to ~10TB (PostgreSQL, MySQL)
  - Single-node analytics (DuckDB for small teams)
  - Early-stage systems
```

### Horizontal Scaling (Scale Out)

```
Add more machines, distribute the load:
  - Stateless services: easy (load balancer + more replicas)
  - Stateful services: hard (data partitioning, consistency)

PROS:
  - Near-infinite scale
  - Fault tolerant (N-1 machines can fail)
  - Cost-linear scaling

CONS:
  - Distributed systems complexity
  - Data partitioning challenges
  - Network overhead
  - Consistency harder to achieve

WHEN TO USE:
  - Dataflow workers (horizontally scaled automatically)
  - BigQuery slots (horizontal compute for queries)
  - Pub/Sub partitions
  - Any cloud-native service
```

---

## PART 7: LOAD BALANCING STRATEGIES

### Round Robin
```
Requests: R1 R2 R3 R4 R5 R6
Servers:   S1 S2 S3 S1 S2 S3

Simple, but ignores server load. Use for stateless, homogeneous servers.
```

### Least Connections
```
Route each request to the server with fewest active connections.
Better than round-robin for variable-duration requests (file uploads).
```

### Consistent Hashing
```
Critical for distributed data systems (Cassandra, Bigtable, Kafka).

PROBLEM: When adding/removing servers, naive hashing (key % N) 
         remaps almost all keys → massive data movement.

CONSISTENT HASHING:
  - Place servers on a hash ring (0 to 2^32)
  - Each key maps to the nearest server clockwise
  - Adding a server: only affects keys between new server and predecessor
  - Removing a server: only affects that server's keys
  
  RESULT: Only K/N keys remapped when adding/removing one server
  (K = total keys, N = number of servers)
  
VIRTUAL NODES:
  - Each physical server appears at multiple points on the ring
  - Prevents hotspots when servers have different capacities
  - Used in: Cassandra (default 256 vnodes), DynamoDB
```

---

## PART 8: CACHING STRATEGIES

### Cache-Aside (Lazy Loading)
```python
def get_merchant_profile(merchant_id: str) -> MerchantProfile:
    # Check cache first
    cached = redis.get(f"merchant:{merchant_id}")
    if cached:
        return deserialize(cached)
    
    # Cache miss — load from database
    profile = db.query("SELECT * FROM merchants WHERE id = ?", merchant_id)
    
    # Store in cache with TTL
    redis.setex(f"merchant:{merchant_id}", 3600, serialize(profile))
    
    return profile

# PROS: Only cache what's actually needed
# CONS: Cache miss causes 3 operations (read cache, read DB, write cache)
#       Initial requests always slow (cold cache)
```

### Write-Through
```python
def update_merchant_profile(merchant_id: str, profile: MerchantProfile):
    # Write to DB
    db.execute("UPDATE merchants SET ... WHERE id = ?", merchant_id)
    
    # Write to cache SYNCHRONOUSLY
    redis.setex(f"merchant:{merchant_id}", 3600, serialize(profile))

# PROS: Cache always consistent with DB
# CONS: Write latency includes cache write
#       Caches data that may never be read
```

### Write-Behind (Write-Back)
```python
def update_merchant_profile(merchant_id: str, profile: MerchantProfile):
    # Write to cache ONLY (returns immediately)
    redis.setex(f"merchant:{merchant_id}", 3600, serialize(profile))
    
    # Asynchronously flush to DB
    write_queue.enqueue(WriteJob(merchant_id, profile))

# PROS: Very fast writes
# CONS: Data loss if cache dies before flush
#       Eventual consistency between cache and DB
```

### Cache Eviction Policies

| Policy | Description | Use Case |
|---|---|---|
| LRU (Least Recently Used) | Evict the item not accessed for longest time | General purpose, most common |
| LFU (Least Frequently Used) | Evict item accessed least often | When access frequency matters more than recency |
| FIFO | Evict oldest inserted item | Simple queues |
| TTL | Expire after fixed time regardless | Config data, session tokens |

---

## PART 9: DATABASE SELECTION FRAMEWORK

### Decision Matrix

| Requirement | Database Type | GCP Option |
|---|---|---|
| ACID transactions, relational | RDBMS | Cloud SQL (PostgreSQL/MySQL) |
| Global transactions, strong consistency | NewSQL | Cloud Spanner |
| OLAP, petabyte analytics | Columnar warehouse | BigQuery |
| Low-latency key-value reads | Wide-column NoSQL | Cloud Bigtable |
| Document store, flexible schema | Document DB | Firestore |
| In-memory cache | Cache | Memorystore (Redis) |
| Time series | Time series DB | BigQuery + partitioning |
| Graph data | Graph DB | Spanner Graph / Neo4j |
| Full-text search | Search engine | Elasticsearch / Vertex AI Search |

### OLTP vs OLAP Deep Comparison

```
OLTP (Online Transaction Processing):
  Optimized for: individual row operations
  Query pattern: WHERE id = 12345
  Row size: small (< 1KB typically)
  Concurrency: thousands of concurrent writes
  Data freshness: real-time
  Examples: payment processing, user accounts, inventory

OLAP (Online Analytical Processing):
  Optimized for: aggregations over millions of rows
  Query pattern: GROUP BY region, SUM(revenue) WHERE date > '2024-01-01'
  Row size: wide (many columns)
  Concurrency: few concurrent, expensive queries
  Data freshness: minutes to hours acceptable
  Examples: business intelligence, data warehousing, reporting
  
  COLUMNAR STORAGE ADVANTAGE FOR OLAP:
    Table: 100 columns, 1 billion rows
    Query: SELECT SUM(revenue) FROM sales WHERE date > '2024-01-01'
    
    Row storage: reads ALL 100 columns × 1B rows = 100TB
    Columnar storage: reads ONLY revenue + date columns = 2TB
    
    50× less data read → 50× faster + 50× cheaper in BigQuery
```

---

## PART 10: PARTITIONING AND SHARDING

### Partitioning (Single Node)

```
HORIZONTAL PARTITIONING (Sharding):
  Split rows across multiple tables/nodes by a partition key
  
  Example: Orders table partitioned by date:
    orders_2024_01 → January orders
    orders_2024_02 → February orders
    orders_2024_03 → March orders
  
  BigQuery equivalent:
    PARTITION BY DATE(order_ts)
    → Query WHERE DATE(order_ts) = '2024-01-15' scans only Jan partition

VERTICAL PARTITIONING:
  Split columns across tables
  
  Example: User table split by access pattern:
    users_core: user_id, email, created_at (queried frequently)
    users_profile: user_id, bio, preferences, avatar (queried rarely)
  
  Benefit: Smaller rows in hot table → more rows cached in memory
```

### Sharding Strategies

```
RANGE-BASED SHARDING:
  Shard A: user_id 1-1,000,000
  Shard B: user_id 1,000,001-2,000,000
  
  PROS: Range queries efficient (all users 500K-600K on same shard)
  CONS: Hotspots if data not uniformly distributed (new users all on Shard Z)

HASH-BASED SHARDING:
  shard = hash(user_id) % num_shards
  
  PROS: Even distribution
  CONS: Range queries require hitting all shards

DIRECTORY-BASED SHARDING:
  Lookup table: user_id → shard_id
  
  PROS: Flexible, can move data between shards
  CONS: Lookup table is single point of failure (must be HA)

GEOGRAPHIC SHARDING:
  Shard US: US users
  Shard EU: EU users
  
  PROS: Data locality, regulatory compliance
  CONS: Cross-shard queries expensive; uneven growth
```

---

## PART 11: REPLICATION

### Single-Leader Replication

```
         LEADER
        /      \
  REPLICA1   REPLICA2
  
- All writes go to leader
- Leader replicates to followers
- Reads can go to any node

SYNCHRONOUS replication: Leader waits for replica ACK before acknowledging write
  PROS: No data loss on leader failure
  CONS: Write latency = network RTT to replica

ASYNCHRONOUS replication: Leader acknowledges write immediately, replicates in background
  PROS: Low write latency
  CONS: If leader fails before replication, data lost

SEMI-SYNCHRONOUS: One replica is synchronous, others async
  PROS: One guaranteed copy, fast writes
  CONS: If sync replica fails, falls back to async
```

### Multi-Leader Replication

```
LEADER1 ←→ LEADER2 ←→ LEADER3
(datacenter A)  (datacenter B)  (datacenter C)

Each region has its own leader for low-latency local writes.
Leaders replicate to each other asynchronously.

CONFLICT RESOLUTION needed when same key written in two regions simultaneously:
  - Last-Write-Wins (LWW): use timestamp, latest wins (can lose data)
  - Application-level: application handles conflicts (complex)
  - CRDT: Conflict-free Replicated Data Types (auto-merge)
```

---

## PART 12: KEY METRICS TO KNOW

### Latency Percentiles

```
P50 (median): 50% of requests faster than this
P95:          95% of requests faster than this
P99:          99% of requests faster than this
P99.9:        99.9% of requests faster than this

WHY P99 MATTERS MORE THAN AVERAGE:
  If 1% of requests take 10 seconds, those are 1% of your most active users
  (Heavy users make more requests → disproportionately affected)
  
  Average can hide tail latency:
    99 requests: 10ms each → 990ms total
    1 request:   10,000ms → 10,000ms
    Average: (990 + 10000) / 100 = 109ms ← looks fine!
    P99: 10,000ms ← 10 seconds! totally unacceptable
```

### Throughput vs Latency Tradeoff

```
THROUGHPUT: Requests/operations per second
LATENCY: Time for a single request

They are in tension:
  - Batching improves throughput but increases latency
  - Streaming improves latency but reduces throughput (per-request overhead)
  
  OPTIMIZATION FOR THROUGHPUT:
    - Batch writes (write 1000 rows at once)
    - Connection pooling
    - Async I/O
    - Larger buffer sizes
  
  OPTIMIZATION FOR LATENCY:
    - Reduce batch sizes
    - Cache hot data
    - Minimize network hops
    - Pre-compute aggregations
```

### The 99.9% → 99.99% Gap

```
99%    availability = 3.65 days downtime/year
99.9%  availability = 8.7 hours downtime/year
99.99% availability = 52 minutes downtime/year  ← CDM Next target
99.999% availability = 5 minutes downtime/year  ← Payment systems

Going from 99.9% to 99.99% is NOT a 0.09% improvement.
It's a 10× reduction in downtime — requires significantly more engineering:
  - Multi-zone deployments
  - Automated failover
  - No single points of failure
  - Rolling deployments (zero-downtime deploys)
  - Chaos engineering
```

---

## PART 13: CDM NEXT FUNDAMENTALS MAPPING

| Concept | CDM Next Implementation |
|---|---|
| CAP theorem | AP for ingestion (availability prioritized; minor staleness acceptable) |
| Consistency model | Eventual consistency for analytics; strong for financial audit trails |
| Horizontal scaling | Dataflow auto-scales workers; BigQuery slots scale horizontally |
| Partitioning | BigQuery tables partitioned by ingestion date; GCS paths by date/source |
| Caching | Config store cached in Dataflow template memory; avoid Firestore hot reads |
| Replication | GCS multi-region; BigQuery multi-region dataset option |
| RTO/RPO | RTO < 15min via Composer retry; RPO ≈ 0 via Pub/Sub message retention |
| Load balancing | Pub/Sub distributes messages across Dataflow workers automatically |

---

## MODULE 1 SUMMARY

| Concept | One-Line Summary |
|---|---|
| CAP Theorem | In distributed systems, choose CP (consistency) or AP (availability) during partitions |
| PACELC | CAP + latency vs consistency tradeoff during normal operation |
| Consistency Models | Spectrum from linearizability (strongest) to eventual (weakest) |
| RTO/RPO | Recovery Time Objective and Recovery Point Objective define your HA requirements |
| Vertical vs Horizontal | Scale up (bigger machine) vs scale out (more machines) |
| Consistent Hashing | Minimizes key remapping when adding/removing nodes |
| Cache Strategies | Cache-aside (lazy), write-through (sync), write-behind (async) |
| OLTP vs OLAP | Row storage for transactions, columnar storage for analytics |
| Sharding | Hash-based for even distribution, range-based for range queries |
| P99 Latency | Average hides tail; optimize for P99 in user-facing systems |

---

*Module 1 Complete — ~8,000 words.*
