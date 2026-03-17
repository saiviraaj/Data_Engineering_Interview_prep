# System Design Core Components: Building Blocks
## Complete Guide to Databases, Caches, Message Queues, and Services

**Target**: Data engineers learning system design  
**Level**: Beginner to intermediate  
**Time**: 5-7 hours reading + practice  
**Goal**: Understand each component and when to use them

---

## Table of Contents

1. [Relational Databases - Deep Dive](#relational-databases--deep-dive)
2. [NoSQL Databases - Detailed Overview](#nosql-databases--detailed-overview)
3. [Caching Systems](#caching-systems)
4. [Message Queues & Event Streaming](#message-queues--event-streaming)
5. [Load Balancing & API Gateways](#load-balancing--api-gateways)
6. [Distributed File Systems](#distributed-file-systems)
7. [Search Systems](#search-systems)
8. [Monitoring & Observability](#monitoring--observability)
9. [Component Selection Guide](#component-selection-guide)

---

## Relational Databases - Deep Dive

### Why Relational Databases?

**Structured Data** = Data with clear schema
```
All trades have same fields:
├─ trade_id (integer)
├─ trader_id (string)
├─ amount (number)
└─ timestamp (date)

All rows fit same structure.
Relational database perfect for this.
```

**Relationships** = Connections between tables

```
Traders table:
├─ trader_id (primary key)
├─ name
└─ email

Trades table:
├─ trade_id (primary key)
├─ trader_id (foreign key → Traders table)
├─ amount
└─ date

Relationship: One trader has many trades
Foreign key enforces referential integrity (no orphan trades).
```

---

### Relational Database Internals

**Table Storage** (How data is physically stored):

```
Traditional Row Storage:
Row 1: [1, "T001", 100000, "2024-01-01"]
Row 2: [2, "T002", 250000, "2024-01-02"]
Row 3: [3, "T001", 150000, "2024-01-03"]

When you query: "Get amount from row 3"
Database reads entire row 3 into memory.
All columns loaded (even if you only need amount).

Problem: Read amplification
Query: SELECT amount FROM trades WHERE trade_id = 3
Result: Must read trade_id, trader_id, amount, date
Cost: 4x more I/O than needed!
```

**Column Storage** (Alternative, used in data warehouses):

```
Column-Based Storage:
trade_id: [1, 2, 3]
trader_id: ["T001", "T002", "T001"]
amount: [100000, 250000, 150000]
date: ["2024-01-01", "2024-01-02", "2024-01-03"]

When you query: "Get amount from row 3"
Database reads only amount column.

Benefit: Compression (similar values compress better)
```

**Index Storage** (Separate from table):

```
B-Tree Index on trader_id:
"T001" → [1, 3]
"T002" → [2]

Query: "Find all trades by T001"
Without index: Scan all rows (slow)
With index: Look up T001 in index, get rows 1 and 3 immediately

Index is sorted tree:
       "T001"
      /      \
   "T000"  "T002"
```

---

### Transaction Isolation Levels

**Why we need isolation**: Prevent dirty reads, lost updates, etc.

**Dirty Read** (Reading uncommitted data):
```
Transaction A: UPDATE trader SET balance = 100 (not committed yet)
Transaction B: READ trader balance → gets 100

If Transaction A rolls back:
Transaction B now has invalid data (dirty read)
```

**Isolation Levels** (ordered by safety):

```
Level 0 - READ UNCOMMITTED (No isolation):
├─ Can read uncommitted changes
├─ Problem: Dirty reads possible
├─ Speed: Fastest
└─ Use: Never (too risky)

Level 1 - READ COMMITTED (Default for many databases):
├─ Only reads committed data
├─ Problem: Phantom reads (data changes between reads)
├─ Speed: Fast
└─ Use: Most applications (good balance)

Level 2 - REPEATABLE READ:
├─ Prevents dirty reads and non-repeatable reads
├─ Problem: Phantom reads (new rows added)
├─ Speed: Slower (more locking)
└─ Use: When need consistency within transaction

Level 3 - SERIALIZABLE (Strictest):
├─ Complete isolation (transactions execute one at a time)
├─ Problem: Very slow (serialization bottleneck)
├─ Speed: Slowest
└─ Use: Only critical financial transactions
```

**Phantom Read Example**:
```
Transaction A: SELECT COUNT(*) FROM trades WHERE date = TODAY
Result: 10 trades

Meanwhile, Transaction B: INSERT new trade for today

Transaction A: SELECT COUNT(*) FROM trades WHERE date = TODAY
Result: 11 trades (different result!)

This is phantom read (new row added between queries).
```

---

### Query Optimization

**Query Planner** = Decides how to execute query efficiently

```
Query: SELECT trader_id, SUM(amount) FROM trades 
       WHERE date >= '2024-01-01' GROUP BY trader_id

Possible plans:
1. Full scan: Read all rows, filter by date, group by trader
   Cost: 1 billion row scans

2. Index scan: Use index on date, read matching rows, group
   Cost: 1 million row scans (100x faster!)

Query optimizer chooses plan 2.
```

**Query Plan Analysis**:
```
EXPLAIN PLAN shows:
├─ Index scans (good)
├─ Seq scans (slow, full table scans)
├─ Joins (expensive, watch for cartesian products)
├─ Sorts (expensive, avoid if possible)
└─ Aggregations (expensive for large datasets)

Example output:
Seq Scan on trades (cost=0..2000)
  Filter: (date >= '2024-01-01')
├─ Problem: Full scan of 1 billion rows!
│
Better with index:
Index Scan using trades_date_idx (cost=0..10)
  Index Cond: (date >= '2024-01-01')
├─ 100x faster!
```

---

### Scaling Relational Databases

**Vertical Scaling** (Bigger machine):
```
Add more CPU, more RAM, better disk.
Limitations:
├─ Cost increases exponentially
├─ Eventually hit maximum machine size
├─ Single point of failure
└─ Not scalable beyond ~100K RPS
```

**Read Replicas**:
```
        Master (writes)
          │ replication
    ┌─────┼─────┐
    │     │     │
 Slave1 Slave2 Slave3 (read-only)

Writes go to master only.
Reads distributed to replicas.
```

**Horizontal Scaling (Sharding)**:
```
Problem: Master replication doesn't help writes.
10K writes/sec on master = bottleneck.

Solution: Shard data across multiple databases.

Shard 1: Traders T0000-T1999 (handled by DB1)
Shard 2: Traders T2000-T3999 (handled by DB2)
Shard 3: Traders T4000-T5999 (handled by DB3)

Now:
├─ 10K writes distributed across 3 DBs
├─ Each DB handles ~3.3K writes/sec
└─ Scale linearly with number of shards!
```

**Sharding Challenges**:
```
Cross-shard query:
Query: "Total trades across all traders"
├─ Must query all shards
├─ Must aggregate results
└─ Slower than single-shard query

Cross-shard transaction:
Transfer money between traders on different shards
├─ Can't use standard ACID (different databases)
├─ Must use distributed transactions (2-phase commit)
└─ Slow, error-prone
```

---

### Materialized Views (Precomputed Results)

**Problem**: Some queries are expensive but needed frequently

```
Query: Total revenue by region for all time
Cost: Scan billions of rows, aggregate by region
Time: 10 minutes

If need this result every hour:
├─ 10 minutes computation
├─ 50 minutes waiting for next computation
└─ Users always see stale data
```

**Solution: Materialized View**

```
Materialized View = Precomputed result stored in database

├─ Created by: 
│  SELECT region, SUM(revenue) as total
│  FROM sales GROUP BY region
│
├─ Stores result:
│  US: $1 billion
│  Europe: $500 million
│  Asia: $300 million
│
└─ Updated: Hourly via scheduled job

Query: "Total revenue by region"
Cost: Direct lookup (no aggregation)
Time: < 1 millisecond
```

**Tradeoff**:
```
Pro: Query extremely fast
Con: Data might be stale (if updated hourly)
    Uses extra storage (materialized result + original data)

Best for:
├─ Reports (can tolerate 1-hour lag)
├─ Heavy aggregations (saves repeated computation)
└─ Frequently run queries
```

---

## NoSQL Databases - Detailed Overview

### Key-Value Stores

**Concept**: Dictionary/HashMap stored persistently

```
Redis example:
SET user:1001 '{"name": "John", "age": 30}'
GET user:1001
→ '{"name": "John", "age": 30}'

INCR counter
→ 1

INCR counter
→ 2
```

**Characteristics**:
```
Speed: Extremely fast (in-memory)
Latency: 1-10 microseconds
Throughput: 100K+ operations/second per instance

Use cases:
├─ Caching (session data, query results)
├─ Counters (page views, likes)
├─ Leaderboards (sorted sets)
├─ Rate limiting (tokens per user)
└─ Pub/Sub messaging

Redis-specific features:
├─ Expiration (auto-delete after TTL)
├─ Pub/Sub (simple messaging)
├─ Lists (ordered sequences)
├─ Sorted Sets (ranking/leaderboards)
└─ Transactions (MULTI/EXEC)
```

**Limitations**:
```
├─ All data in memory (limited by RAM)
├─ Only basic queries (by key)
├─ No complex filtering
├─ Single-threaded (throughput limited per instance)
└─ Can lose data if not configured for persistence
```

---

### Document Stores (MongoDB)

**Concept**: Store JSON documents with flexible schema

```
Document (like JSON object):
{
  "_id": ObjectId("507f1f77bcf86cd799439011"),
  "trader_id": "T001",
  "trades": [
    {
      "symbol": "AAPL",
      "amount": 100000,
      "date": "2024-01-01"
    },
    {
      "symbol": "MSFT",
      "amount": 250000,
      "date": "2024-01-02"
    }
  ],
  "metadata": {
    "region": "US",
    "experience_years": 10
  }
}

Can vary structure per document:
Doc 1: Has "trades" and "metadata"
Doc 2: Only has "trades"
Doc 3: Has completely different fields

No schema enforcement!
```

**Query Capability**:
```
db.traders.find({
  trader_id: "T001",
  "trades.amount": { $gt: 50000 }
})

Result: Find trader T001 with trades > 50000

Compare to SQL:
SELECT * FROM traders 
WHERE trader_id = 'T001' 
  AND EXISTS (
    SELECT 1 FROM trades 
    WHERE trader_id = 'T001' AND amount > 50000
  )

MongoDB query is simpler, more intuitive for nested data.
```

**Strengths**:
```
├─ Flexible schema (evolve over time)
├─ Natural for nested data (documents are JSON)
├─ Can query nested fields
├─ Developer-friendly (looks like JavaScript objects)
└─ Scales horizontally (sharding supported)
```

**Limitations**:
```
├─ No ACID transactions across documents (until v4.0)
├─ No joins (relational integrity must be in app code)
├─ Slower than relational for certain queries
├─ Requires denormalization (duplicate data)
└─ Memory usage higher (JSON overhead)
```

---

### Column-Family Stores (HBase, Cassandra)

**Concept**: Data stored by columns, not rows

```
Traditional row storage:
Row Key: trade_1
├─ Columns: trader_id, symbol, amount, date
└─ Values: [T001, AAPL, 100000, 2024-01-01]

Column-family storage:
trade_1:trader_id = "T001"
trade_1:symbol = "AAPL"
trade_1:amount = 100000
trade_1:date = 2024-01-01

Stored physically:
Column "trader_id": [("trade_1", "T001"), ("trade_2", "T002")]
Column "symbol": [("trade_1", "AAPL"), ("trade_2", "MSFT")]
```

**Why Column Storage?**

```
Query: "Get symbol for all trades where amount > 50000"

Row storage:
├─ Load entire row (all columns)
├─ Extract symbol
├─ Cost: O(n rows)

Column storage:
├─ Load only amount column + symbol column
├─ Filter amount > 50000
├─ Cost: O(n rows) but only 2 columns loaded
└─ Compression: Similar values compress well

Result: 10x-100x faster for selective columns!
```

**Cassandra Features**:
```
├─ Distributed: Runs on multiple machines
├─ Scalable: Add nodes to scale
├─ Highly available: No single point of failure
├─ Eventually consistent: Replicas eventually sync
├─ Time-series friendly: Optimized for time-ordered data

Use cases:
✓ Time-series data (metrics, stock prices)
✓ Wide data (many columns)
✓ Massive scale (terabytes to petabytes)
✓ High availability (always-on systems)
✗ Complex queries (limited to specific patterns)
✗ ACID transactions (not supported)
```

---

### Graph Databases (Neo4j)

**Concept**: Data stored as nodes and relationships

```
Nodes:
├─ Trader (id: T001, name: "John")
├─ Stock (symbol: "AAPL", price: 150)
└─ Desk (name: "EQUITY_DESK")

Relationships:
├─ Trader T001 --[TRADES]--> Stock AAPL
├─ Trader T001 --[WORKS_ON]--> Desk EQUITY_DESK
└─ Stock AAPL --[LISTED_ON]--> Exchange NYSE

Queries:
"Find all stocks traded by traders in EQUITY_DESK"
Result: Traverse Desk → Traders → Stocks
Much simpler than SQL with multiple JOINs!
```

**Advantages**:
```
├─ Natural representation of relationships
├─ Fast traversal (following relationships)
├─ Efficient for complex queries (recursive, multiple hops)
└─ Powerful pattern matching
```

**Disadvantages**:
```
├─ Not suitable for tabular data (relational better)
├─ Smaller ecosystem (less tools, less adoption)
├─ Performance degrades with very large graphs
└─ Not ideal for pure analytical queries
```

---

## Caching Systems

### Cache Levels and Strategies

**Cache Hierarchy** (from fastest to slowest):

```
Level 1: CPU Cache (L1, L2, L3)
├─ Speed: < 10 nanoseconds
├─ Size: Kilobytes
├─ Automatic (hardware)
└─ Transparent to applications

Level 2: RAM Cache
├─ Speed: 10-100 nanoseconds  
├─ Size: Megabytes to gigabytes
├─ In-application (HashMap, etc.)
└─ Manual management

Level 3: Redis/Memcached Cache
├─ Speed: 1-10 milliseconds (includes network)
├─ Size: Gigabytes (distributed)
├─ Separate service
└─ Shared across servers

Level 4: Database Cache
├─ Speed: 1-100 milliseconds
├─ Size: Gigabytes
├─ Built into database
└─ Transparent

Level 5: Disk / File System Cache
├─ Speed: 10-100 milliseconds
├─ Size: Terabytes
├─ Operating system managed
└─ Transparent
```

### Writing Cache Patterns

**Cache-Aside (Lazy Loading)**:

```
Application code:
1. Check cache: Is data in cache?
   ├─ Yes: Return from cache
   └─ No: Continue
2. Read from database
3. Write to cache
4. Return data

Code:
value = cache.get(key)
if value is null:
    value = database.get(key)
    cache.set(key, value, ttl=1hour)
return value

Pros:
├─ Simple to implement
├─ Only cache accessed data
└─ No wasted cache space

Cons:
├─ Cache miss on first request (slow)
├─ Complex cache invalidation
└─ Potential stale data
```

**Write-Through Cache**:

```
Application code:
1. Write to cache
2. Write to database (synchronously)
3. Return success

Code:
cache.set(key, value)
database.set(key, value)  // Wait for this
return success

Pros:
├─ Data always in sync
├─ No stale data
└─ Consistency guaranteed

Cons:
├─ Write latency = database latency (slow)
├─ Cache failure blocks writes
└─ Extra complexity if cache down
```

**Write-Behind Cache**:

```
Application code:
1. Write to cache
2. Return success immediately
3. Asynchronously write to database

Code:
cache.set(key, value)
async {
    database.set(key, value)  // Happens later
}
return success  // Return immediately

Pros:
├─ Fast writes (don't wait for DB)
├─ Reduced load on database
└─ Better user experience

Cons:
├─ Data loss if cache fails before DB write
├─ Temporary inconsistency
└─ Complex error handling
```

### Cache Invalidation Strategies

**Time-Based (TTL)**:
```
Cache-Control: max-age=3600
├─ Automatically expire after 1 hour
├─ Simple
└─ Might serve stale data up to 1 hour

Good for:
├─ Data that changes infrequently
├─ Non-critical data (recommendations, analytics)
```

**Event-Based**:
```
When data changes:
├─ Database publishes event: "trades:updated"
├─ Application listens to events
├─ Invalidates cache when event received

Code:
on_event("trades:updated"):
    cache.delete("trades:*")  // Remove all trade cache

Good for:
├─ Data that changes frequently
├─ Critical consistency needed
```

**Versioning**:
```
Instead of deleting:
├─ Old cache key: "trades:v1"
├─ New cache key: "trades:v2"
├─ Clients gradually migrate to v2

Benefit: No cache miss (always have valid version)
Cost: Extra storage (multiple versions)
```

---

## Message Queues & Event Streaming

### Message Queue Concept

**Problem**: Decoupling producers from consumers

```
Without queue:
Producer directly calls Consumer
├─ Producer must wait for Consumer to finish
├─ If Consumer slow → Producer slow
├─ If Consumer down → Producer fails
└─ Tightly coupled

With queue:
Producer → Queue → Consumer
├─ Producer writes to queue, returns immediately
├─ Consumer processes when ready
├─ If Consumer slow: Queue builds up (acceptable)
├─ If Consumer down: Queue persists messages
└─ Loosely coupled
```

### Types of Message Systems

**Message Queues** (Point-to-Point):

```
Producer: "New trade: T001 for AAPL"
└─ Sends to queue

Consumer 1: Processes trade (one consumer processes message)
└─ Dequeues, processes, deletes

Result: Message processed by exactly one consumer
```

**Publish-Subscribe**:

```
Producer: Publishes event "trade:executed"

Subscribers:
├─ Consumer 1: Risk management (receives copy)
├─ Consumer 2: Reporting (receives copy)
├─ Consumer 3: Notifications (receives copy)

Result: Multiple consumers receive same message
```

**Event Streaming** (Log-based):

```
Events written to immutable log:
Time 1: trade:executed T001 AAPL 100000
Time 2: trade:executed T002 MSFT 250000
Time 3: price:updated AAPL 150.25

Consumers:
├─ Consumer A: Reads from beginning (replay all events)
├─ Consumer B: Reads from time 2 (missed first event)
└─ Consumer C: Real-time (reads new events)

Benefits:
├─ Replay history
├─ Multiple consumers at different paces
├─ Append-only (never delete events)
└─ Enables event sourcing
```

### Message Queue Components

**Message Broker** (Stores messages):
```
Examples: RabbitMQ, Apache Kafka, AWS SQS

Responsibilities:
├─ Persist messages
├─ Route messages to consumers
├─ Acknowledgment handling
├─ Delivery guarantees
└─ Scaling

Kafka specifics:
├─ Partitioned topics (parallel processing)
├─ Replication (availability)
├─ Consumer groups (coordinated consumption)
└─ Offset tracking (know which messages read)
```

**Producer** (Sends messages):
```
pub = KafkaProducer()
pub.send("trades", {
    trader_id: "T001",
    amount: 100000,
    symbol: "AAPL"
})

Decisions:
├─ Which topic/queue?
├─ Any key (partition assignment)?
└─ Wait for acknowledgment? (speed vs. safety)
```

**Consumer** (Reads messages):
```
sub = KafkaConsumer(
    "trades",
    group_id="risk-team"
)

for message in sub:
    process_trade(message)
    sub.commit()  # Mark as processed

Features:
├─ Consumer group (parallel processing)
├─ Offset tracking (resume from failure)
└─ Rebalancing (add/remove consumers)
```

---

## Load Balancing & API Gateways

### Load Balancing Algorithms

**Round Robin**:
```
Request 1 → Server A
Request 2 → Server B
Request 3 → Server C
Request 4 → Server A (cycle)

Pros:
├─ Simple
├─ Fair distribution
└─ O(1) computation

Cons:
├─ Ignores server capacity
├─ Ignores request complexity
└─ Can be unbalanced with varied request sizes
```

**Least Connections**:
```
Track connections per server:
Server A: 10 connections
Server B: 25 connections
Server C: 5 connections

Route next request to Server C (fewest connections)

Pros:
├─ Better load distribution
└─ Adapts to varying request lengths

Cons:
├─ Slightly more computation
└─ Server failures can disrupt tracking
```

**Weighted Round Robin**:
```
Server A: 2x power (weight=2)
Server B: 1x power (weight=1)

Requests:
Server A, Server A, Server B, Server A, Server A, Server B...

Pros:
├─ Can account for different server capacity
└─ Fair for heterogeneous clusters

Cons:
├─ Manual weight configuration
└─ Doesn't adapt to load
```

**IP Hash**:
```
Hash = hash(client_ip) % num_servers

Same client always routes to same server.

Pros:
├─ Session stickiness (no session sync needed)
└─ Consistent (same client always same server)

Cons:
├─ Unbalanced if clients have skewed distribution
└─ Adding/removing servers breaks mapping
```

---

### API Gateway

**Role**: Entry point for all client requests

```
Clients
   │
   ↓
┌──────────────────┐
│ API Gateway      │ (single entry point)
├──────────────────┤
│ ├─ Load balance  │
│ ├─ Auth check    │
│ ├─ Rate limit    │
│ ├─ Log requests  │
│ └─ Route to service
└──────────────────┘
   │ │ │
   ↓ ↓ ↓
Service A  Service B  Service C
```

**Responsibilities**:

```
1. Request Routing
   GET /api/trades → route to trades service
   GET /api/accounts → route to accounts service

2. Load Balancing
   Route requests evenly across service instances

3. Authentication
   Check API key, JWT token, etc.
   Deny if unauthorized

4. Rate Limiting
   Limit 1000 requests per user per hour
   Return 429 if exceeded

5. Logging
   Log all requests for monitoring

6. Caching
   Cache responses of GET requests
   Return cached version if available

7. Circuit Breaker
   If service down: Return cached response or error
   Don't forward to dead service
```

---

## Distributed File Systems

### Why Distributed File Systems?

**Problem**: Single server can't store all data

```
Data volume: 100TB
Server capacity: 10TB
Solution: Distribute across 10 servers
```

### HDFS (Hadoop Distributed File System)

**Architecture**:
```
NameNode (Master)
├─ Tracks file system tree
├─ Maintains file system image
└─ Doesn't store actual data

DataNodes (Slaves)
├─ Store actual data blocks
├─ Send heartbeats to NameNode
└─ Perform block creation/deletion
```

**How Files Stored**:
```
File: "trades.csv" (150GB)
↓
Split into blocks: 64MB each
├─ Block 1: Bytes 0-67MB
├─ Block 2: Bytes 67-134MB
└─ Block 3: Bytes 134-150MB

Each block replicated 3 times (replication factor):
Block 1: DataNode A, DataNode B, DataNode C
Block 2: DataNode D, DataNode E, DataNode F
Block 3: DataNode G, DataNode H, DataNode I

Rack-aware:
├─ Replica 1: Same node as writer
├─ Replica 2: Different rack
├─ Replica 3: Different node, same rack
└─ Minimizes rack bandwidth
```

**Read/Write Process**:
```
Read:
1. Client asks NameNode: "Where's file X?"
2. NameNode returns list of DataNodes with blocks
3. Client reads from nearest DataNode
4. If DataNode fails: Read from next DataNode

Write:
1. Client asks NameNode: "Can I write file X?"
2. NameNode checks permissions, creates new file record
3. Client writes to first DataNode
4. First DataNode pipes to second DataNode
5. Second DataNode pipes to third DataNode
6. Acknowledgment sent back
7. Client gets confirmation all replicas written
```

---

### Cloud Object Storage (S3, GCS)

**Simple Concept**: Store files with key-value mapping

```
PUT /bucket/path/to/file.csv
│ [file content]

Data stored at: gs://bucket/path/to/file.csv

GET /bucket/path/to/file.csv
→ [file content returned]

Benefits:
├─ Simple API (put, get, delete)
├─ Unlimited scalability
├─ High availability (replicated)
├─ Pay only for storage used
└─ Access from anywhere
```

**Classes of Storage** (cost vs. latency):

```
Standard: 
├─ Speed: < 1 second
├─ Cost: $0.020 per GB/month
└─ Use: Frequently accessed data

Nearline:
├─ Speed: < 1 second
├─ Cost: $0.010 per GB/month
├─ Min storage: 30 days
└─ Use: Monthly backups, infrequent access

Coldline:
├─ Speed: < 1 second (but slower retrieval)
├─ Cost: $0.004 per GB/month
├─ Min storage: 90 days
└─ Use: Yearly archives

Glacier:
├─ Speed: Hours (data must be retrieved first)
├─ Cost: $0.001 per GB/month
├─ Min storage: 1 year
└─ Use: Long-term archives, compliance
```

---

## Search Systems

### Full-Text Search

**Problem**: Traditional database search is slow

```
Query: "Find all trades with comment containing 'urgent'"

Without index:
├─ Scan entire trades table
├─ Check each row's comment field
├─ Slow for large datasets

With inverted index:
├─ Pre-computed mapping: word → documents containing it
├─ "urgent" → [Trade_1, Trade_45, Trade_123]
├─ Fast lookup
└─ Instant results
```

### Elasticsearch

**How It Works**:

```
Document (like JSON):
{
  "_id": "trade_1",
  "trader": "John",
  "comment": "Urgent sell order for AAPL"
}

Inverted Index:
"urgent" → [trade_1]
"sell" → [trade_1]
"order" → [trade_1]
"AAPL" → [trade_1]

Query: "urgent sell order"
→ Find documents containing all three words
→ Return [trade_1]

Scoring:
└─ Documents with more matching terms ranked higher
```

**Elasticsearch Features**:

```
1. Full-text search
   ├─ Stemming (run, running, ran → root "run")
   ├─ Tokenization (break text into words)
   └─ Synonyms (buy = purchase)

2. Filtering (exact match)
   ├─ status = "ACTIVE"
   ├─ date >= "2024-01-01"
   └─ Range queries

3. Aggregations (grouping)
   ├─ GROUP BY status
   ├─ COUNT(*) per group
   └─ Complex analytics

4. Autocomplete
   ├─ User types "uni"
   └─ Suggest "universe", "unicorn", "union"
```

**When to Use**:
```
✓ Search features (find documents by keyword)
✓ Logging (search logs by content)
✓ Analytics (complex aggregations)
✗ Transactional (not ACID)
✗ Primary database (data loss risk)
```

---

## Monitoring & Observability

### Metrics

**Infrastructure Metrics**:
```
CPU usage: 45%
Memory: 8GB / 16GB (50%)
Disk I/O: 500 MB/s
Network: 100 Mbps
```

**Application Metrics**:
```
Requests per second: 1000
Error rate: 0.1%
Cache hit rate: 85%
Database queries per second: 500
```

**Business Metrics**:
```
Trades per day: 100,000
Revenue: $1 million
Active traders: 5,000
```

### Logs

**Log Levels**:
```
DEBUG: Detailed info for debugging
  └─ Rarely needed in production

INFO: General informational messages
  ├─ Trade executed
  └─ User logged in

WARN: Warning conditions
  ├─ Cache miss
  └─ Slow database query

ERROR: Error conditions
  ├─ Database connection failed
  └─ Invalid input

CRITICAL/FATAL: System is unusable
  ├─ Out of memory
  └─ Disk full
```

**Structured Logging**:
```
Traditional:
"User T001 traded AAPL for $100000 at 10:30:45"

Structured (JSON):
{
  "timestamp": "2024-01-15T10:30:45",
  "trader_id": "T001",
  "symbol": "AAPL",
  "amount": 100000,
  "event": "trade_executed"
}

Benefits:
├─ Searchable in logs (filter by trader_id)
├─ Parseable by machines
└─ Can aggregate/analyze
```

### Tracing

**Problem**: Request goes through many services, need to track its path

```
User request
   ↓
API Gateway (50ms)
   ↓
Trade Service (100ms)
   ↓
Risk Service (75ms)
   ↓
Database (25ms)
   ↓
Total: 250ms

Distributed trace shows:
├─ Which service took longest (Trade Service)
├─ Where bottleneck is (Risk Service slow)
└─ Can identify slow external calls
```

---

## Component Selection Guide

### Database Selection Matrix

```
Your Data          Best Choice      Why
─────────────────────────────────────────────
Structured         PostgreSQL       Relational ideal
ACID needed        PostgreSQL       Strong transactions
Flexible schema    MongoDB          No schema enforcement
Time series        InfluxDB         Optimized for time
Billions rows      BigQuery         Scalable analytics
Real-time logs     Elasticsearch    Full-text search
Key-value pairs    Redis            Ultra-fast
Relationships      Neo4j            Graph queries
Wide columns       Cassandra        Columnar storage
```

### Caching Selection

```
Use Case            Best Choice    Reason
──────────────────────────────────────────
Session cache       Redis          Fast, TTL, serialization
Rate limiting       Redis          Atomic operations
Leaderboards        Redis          Sorted sets
Page cache          CDN            Geographic distribution
Query results       Redis/Memcached In-process cache
```

### Communication Pattern Selection

```
Pattern              Best Choice      Why
────────────────────────────────────────────────
Synchronous RPC      REST/gRPC        Direct response needed
Async events        Kafka            Decoupling, replay
One-to-many         Pub/Sub          Fan-out needed
Delayed execution   Scheduler        Batch jobs
```

---

## Summary: Core Components

```
Database Selection:
├─ OLTP (many small reads/writes): PostgreSQL
├─ OLAP (few large reads): BigQuery, Snowflake
├─ Cache: Redis
├─ Time-series: InfluxDB
├─ Search: Elasticsearch

Scaling Strategies:
├─ Vertical: Bigger machine (limited)
├─ Horizontal: More machines (sharding)
├─ Caching: Reduce database hits
├─ Replication: Redundancy and read scaling
├─ Message queues: Decoupling

Communication:
├─ Synchronous: REST, gRPC
├─ Asynchronous: Message queues, Pub/Sub

Monitoring:
├─ Metrics: Infrastructure and application
├─ Logs: Structured logging
├─ Traces: Request flow across services
```

---

**You now understand the core components. Next batch will cover Low-Level Design (SOLID principles, design patterns) and how to approach system design interviews!**
