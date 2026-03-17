# System Design Prerequisites: Operating Systems, Databases & Networking
## Complete Beginner's Guide for Non-CS Background Engineers

**Target Audience**: Data engineers without formal CS education  
**Level**: Absolute beginner to intermediate  
**Time to Complete**: 4-6 hours reading + practice  
**Goal**: Build foundation for system design interviews

---

## Table of Contents

1. [Operating System Basics](#operating-system-basics)
2. [Database Fundamentals](#database-fundamentals)
3. [Networking & HTTP Basics](#networking--http-basics)
4. [Storage & File Systems](#storage--file-systems)
5. [Concurrency & Threading](#concurrency--threading)
6. [Performance Metrics](#performance-metrics)

---

## Operating System Basics

### What is an Operating System?

**Simple Analogy**: 
Think of an operating system like a restaurant manager:
- **Restaurant** = Your computer (with CPU, memory, disk)
- **Manager** = Operating system
- **Customers** = Applications (Chrome, VS Code, Spark)
- **Kitchen staff** = CPU cores
- **Storage** = Inventory (RAM, disk)

The manager's job:
- Decide which customer gets served when (scheduling)
- Manage kitchen resources (CPU allocation)
- Manage inventory (memory management)
- Handle payments (I/O operations)

**Real Definition**: An OS is software that manages hardware resources and allows applications to run.

---

### Key Concepts You Need

#### 1. **Processes vs Threads**

**Process**: An independent program execution
```
Program: Google Chrome
Process 1: YouTube tab (isolated, separate memory)
Process 2: Gmail tab (isolated, separate memory)
Process 3: Spotify (isolated, separate memory)

Each process is completely separate:
- Has own memory space
- Has own file handles
- If one crashes, others don't (usually)

Cost: Expensive to create, slow to switch between
```

**Thread**: Lightweight execution within a process
```
Process: Spotify (single program)
Thread 1: Download music in background
Thread 2: Play music
Thread 3: Update UI
Thread 4: Sync with server

All threads share:
- Same memory space
- Same files
- Same resources

Cost: Cheap to create, fast to switch between
Danger: If one crashes, all crash (shared memory)
```

**Why This Matters for System Design**:
```
Web Server Example:
- Process-based: Each request = new process (heavy, slow, safe)
- Thread-based: Each request = new thread (light, fast, risky)

Modern systems use thread-based for performance.
Need to be careful about shared memory (locks, synchronization).
```

**Real Example - Your Data Pipeline**:
```
Spark Application (Process):
├─ Thread 1: Read data from JDBC source
├─ Thread 2: Transform data (PySpark)
├─ Thread 3: Write to BigQuery
└─ Thread 4: Monitor progress

All threads share same Spark context (memory, data).
If Thread 1 fails, whole Spark job might fail.
```

---

#### 2. **Memory Management**

**RAM (Random Access Memory)**: Fast, temporary storage
```
Memory layout in a process:
┌─────────────────────────────────────┐
│ Stack (function calls, local vars)  │ ← Fast, automatic cleanup
├─────────────────────────────────────┤
│ Heap (objects, dynamic allocation)  │ ← Slower, manual cleanup
├─────────────────────────────────────┤
│ Code (program instructions)         │ ← Fixed
└─────────────────────────────────────┘

Size: 4GB - 256GB typical for servers
Speed: ~1 nanosecond to access
Persistence: Lost on restart
```

**Virtual Memory**: Disk space used as memory overflow
```
When RAM is full:
1. OS moves least-used data to disk
2. Frees up RAM for new data
3. When old data needed again, loads back from disk

Benefit: Can run larger programs than RAM
Cost: Disk is 1000x slower than RAM (terrible performance)

Analogy: Your desk is small (RAM). 
You keep frequently-used files on desk.
Rarely-used files go to cabinet (disk).
But getting files from cabinet takes forever!
```

**Memory Leak**: When program doesn't release used memory
```
Example:
for i in range(1000000):
    big_list = [0] * 1000000  # Create 1MB list
    # Forgot to delete it!
    
After loop: Program still using 1000GB RAM
When program should use only few MB!

Result: System slows down, eventually crashes (OOM - Out of Memory)
```

**Why This Matters for System Design**:
```
- Data caching (keep frequently used in RAM, not disk)
- Memory limits (can't cache 1TB dataset in 8GB RAM)
- Garbage collection (Java, Python handle cleanup, but has pauses)
- Memory-efficient algorithms (choosing right data structures)
```

---

#### 3. **CPU & Context Switching**

**CPU Core**: Single computation unit
```
Analogy: 
Server with 16-core CPU = Restaurant with 16 chefs
Each chef cooks one dish at a time.
16 chefs = 16 dishes in parallel.

But:
├─ 1 core takes 100ms per task
├─ 16 cores do 16 tasks in parallel = 100ms total (16x faster!)
└─ But not 16x faster due to context switching overhead
```

**Context Switching**: OS switching between tasks
```
Timeline on single core:
Time 0-100ms: Running Task A
            ↓ (switch)
Time 100-200ms: Running Task B (Task A paused)
              ↓ (switch)
Time 200-300ms: Running Task A (resumed)

Switching cost:
1. Save Task A state to memory
2. Load Task B state
3. Reset CPU cache
4. Start Task B

Cost: 1-10 microseconds (not huge, but adds up)
With 1000 tasks/second = 1-10 milliseconds lost to switching!
```

**Why This Matters for System Design**:
```
Thread Pool Size:
- If thread pool too large: Excessive context switching
- If thread pool too small: Can't utilize CPU

Rule of thumb: 
Number of threads ≈ Number of CPU cores (for CPU-intensive work)
Number of threads >> CPU cores (for I/O-intensive work)
```

**Real Example - Spark**:
```
Spark has 16 executor cores.
You assign 32 concurrent tasks.
This is bad because:
├─ CPU context switching overhead increases
├─ 16 cores competing for 32 tasks
└─ Performance degrades

Good practice:
├─ Partitions = executor cores * 3
├─ Allows flexibility, manageable context switching
└─ Better resource utilization
```

---

#### 4. **I/O Operations**

**I/O Means**: Input/Output to disk, network, or devices

```
I/O Latency Comparison (realistic):
├─ CPU instruction: 1 nanosecond (0.000000001 sec)
├─ Memory access: 100 nanoseconds (0.0000001 sec)
├─ SSD read: 100 microseconds (0.0001 sec) ← 1 MILLION times slower!
├─ HDD read: 10 milliseconds (0.01 sec) ← 10 MILLION times slower!
├─ Network call: 10 milliseconds (0.01 sec) - 1 second (1 sec)
└─ Disk seek + read: 10-100 milliseconds

Analogy:
CPU: Reading word on page (1 nanosecond)
Memory: Getting page from nearby shelf (100 nanoseconds)
SSD: Getting book from room downstairs (100 microseconds)
HDD: Getting book from warehouse (10 milliseconds)
Network: Getting book from another city (100 milliseconds - 1 second)
```

**Blocking vs Non-blocking I/O**:

```
BLOCKING I/O (Simple, but slow):
Thread starts disk read
Thread WAITS (does nothing) until disk returns data
Then thread continues

Problem: Thread is wasted, can't do other work
```

```
NON-BLOCKING I/O (Complex, but efficient):
Thread starts disk read
Thread returns immediately (with "pending" status)
Thread does OTHER work while waiting
When disk data arrives, notification comes back
Thread processes result

Benefit: One thread can handle many I/O operations
Example: Web server can handle 1000 requests with few threads
```

**Why This Matters for System Design**:
```
Web Server Design:
Blocking approach: 1000 requests = need 1000 threads
├─ Memory overhead: 1000 threads * 1MB per thread = 1GB!
├─ Context switching: Massive overhead
└─ Can't handle many concurrent connections

Non-blocking approach: 1000 requests = 1-10 threads
├─ Memory overhead: Minimal
├─ Context switching: Minimal
└─ Event-driven (node.js, async Python)

Your data pipeline:
Blocking: Each source read waits for completion
Non-blocking: Can read from multiple sources in parallel
```

---

### OS Summary for System Design

```
Key Takeaways:

1. Processes are heavy, threads are light
   → Use threads for concurrency in single application

2. Memory is limited resource
   → Design for memory efficiency
   → Cache frequently used data

3. CPU has limited cores
   → Thread pool size should match core count (roughly)
   → Too many threads = context switching overhead

4. I/O is slow relative to CPU
   → Use non-blocking I/O for many concurrent operations
   → Minimize blocking calls in hot paths

5. Virtual memory is a last resort
   → Causes massive slowdown
   → Avoid memory leaks
```

---

## Database Fundamentals

### What is a Database?

**Simple Analogy**:
```
Library analogy:
├─ Books = Data
├─ Library catalog = Database schema (structure)
├─ Library system = Database engine (how to retrieve data)
├─ Librarian = Query engine
├─ Indexing system = Indexes (speed up searches)

Request: "Find all books by Author X"
Librarian options:
├─ Linear search: Go through every book (slow)
├─ Use index: Look up author in catalog (fast)
```

**Real Definition**: Database is organized, persistent storage of structured data with efficient retrieval.

---

### Types of Databases

#### 1. **Relational Databases** (SQL)

**Structure**: Tables with rows and columns (like Excel)

```
Table: trades
├─ Columns: trade_id, trader_id, amount, date, symbol
├─ Row 1: [1, "T001", 100000, "2024-01-01", "AAPL"]
├─ Row 2: [2, "T002", 250000, "2024-01-02", "MSFT"]
└─ Row 3: [3, "T001", 150000, "2024-01-03", "AAPL"]

Query: "SELECT * FROM trades WHERE trader_id = 'T001'"
Result: Rows 1 and 3
```

**Strengths**:
- Structured, organized
- ACID transactions (reliable)
- Query flexibility (SQL)
- Relationships between tables (joins)

**Limitations**:
- Scaling is hard (vertical only - bigger machine)
- Fixed schema (hard to add columns)
- Not good for unstructured data (JSON, images)

**Examples**: PostgreSQL, MySQL, Oracle, Microsoft SQL Server

```
Use cases:
✓ Banking systems (transactions, consistency)
✓ E-commerce (orders, inventory)
✓ Financial trading (accurate accounting)
✗ Large-scale web (billions of rows)
✗ Real-time analytics
```

---

#### 2. **NoSQL Databases** (Non-relational)

**Key-Value Store** (like a dictionary):
```
Simple key-value:
key: "user:1001"
value: {name: "John", age: 30, city: "NYC"}

Query: "Get user 1001"
Result: Instant (direct lookup by key)

Query: "Find all users in NYC"
Result: Slow (must scan all users!)

Examples: Redis, Memcached, DynamoDB
```

**Document Store** (like JSON storage):
```
Document:
{
  "_id": "trade_1",
  "trader_id": "T001",
  "amount": 100000,
  "details": {
    "symbol": "AAPL",
    "price": 150.25,
    "quantity": 666
  }
}

Query: "Find trades with amount > 50000"
Result: Flexible querying on fields

Examples: MongoDB, CouchDB, Firestore
```

**Column-Family Store** (like Google BigTable):
```
Structure organized by COLUMNS, not rows:
Column: user_ids = [1001, 1002, 1003, ...]
Column: names = ["John", "Jane", "Bob", ...]
Column: ages = [30, 28, 35, ...]

Query: "Get names of users 1001-1003"
Result: Scan only names column (not other columns!)

Benefits: Fast for specific columns
Cost: Slow for "get all data about user 1001"

Examples: HBase, Cassandra, BigTable
```

**Graph Database** (relationships):
```
Nodes: User, Stock, Trader
Edges: Connections between them

Query: "Find all stocks traded by friends of T001"
Result: Traverse friendship graph, then find stocks

Examples: Neo4j, ArangoDB
```

**NoSQL Strengths**:
- Horizontal scaling (add more machines)
- Flexible schema (add new fields anytime)
- Better for unstructured data
- Very fast for specific access patterns

**NoSQL Limitations**:
- No transactions (or weak transactions)
- Complex queries are slow
- No joins (usually)
- Eventual consistency (data might be stale)

---

#### 3. **Time-Series Databases**

**Designed for**: Data points with timestamps

```
Example: Stock prices
Time 10:00: Price = $150.00
Time 10:01: Price = $150.25
Time 10:02: Price = $149.99
...
1000000 data points per day per symbol
```

**Special features**:
- Compression for time data (efficient storage)
- Rollup/downsampling (1-min → 1-hour average)
- Time-range queries optimized

**Examples**: InfluxDB, Prometheus, TimescaleDB

**Use cases**:
✓ Metrics (CPU, memory, latency)
✓ Stock prices
✓ Sensor data
✓ Real-time dashboards

---

#### 4. **Search Databases**

**Designed for**: Full-text search

```
Traditional DB query: "Find trades where comment contains 'urgent'"
Result: Slow (scans every trade's comment column)

Search DB query: (Same query on indexed data)
Result: Fast (uses inverted index)

Inverted Index:
Word "urgent" → [Trade_1, Trade_45, Trade_123, ...]
```

**Examples**: Elasticsearch, Solr, Lucene

**Use cases**:
✓ Full-text search (Google, Wikipedia)
✓ Logging (search logs by message)
✓ Analytics (search events)

---

### Database Access Patterns

**Write-Heavy**:
```
Scenario: Stock tick data (100K ticks/sec, rarely read)
Challenge: Writing fast
Solution: Optimized for sequential writes
Examples: Kafka, append-only logs
```

**Read-Heavy**:
```
Scenario: Dashboard (written once, read 1000 times)
Challenge: Reading fast
Solution: Caching, indexing, denormalization
```

**Online Transaction Processing (OLTP)**:
```
Pattern: Many small reads/writes
Example: Bank transfer (read account, write debit, write credit)
Requirement: ACID transactions, consistency
Database: Relational (PostgreSQL, MySQL)
```

**Online Analytical Processing (OLAP)**:
```
Pattern: Few large reads (scan billions of rows)
Example: "Revenue by country for all of 2023"
Requirement: Fast aggregations, not real-time
Database: Data warehouse (BigQuery, Snowflake, Redshift)
```

---

### Key Database Concepts

#### **ACID Transactions**

**Atomicity** (All or nothing):
```
Bank transfer: Debit account A, Credit account B
├─ Both succeed: ✓ Transaction complete
├─ First fails: ✗ Both fail, account A untouched
└─ Halfway crashes: ✗ Both fail, no corruption

Ensures: Either both happen, or neither happens
Benefit: No partial/corrupt state
```

**Consistency** (Valid state):
```
Business rule: Account balance ≥ 0

Transaction tries: Debit $1000 from account with $500
├─ Transaction blocked: ✓ Maintains consistency
└─ Without consistency: Account = -$500 (invalid!)
```

**Isolation** (No interference):
```
Transaction A: Transfer $100
Transaction B: Check balance

Without isolation:
├─ B reads balance during A's transfer
└─ B sees partial state (balance mid-update)

With isolation:
├─ B waits for A to complete
└─ B always sees consistent balance
```

**Durability** (Never lost):
```
Transaction writes data
Power goes out immediately

Without durability: Data lost
With durability: Data persists (written to disk before confirmation)
```

**Tradeoff**: ACID transactions are expensive (slow)
```
Reason: 
├─ Need to lock data (slow)
├─ Need to write to disk (slow)
├─ Need to coordinate across nodes (complex)

Solution: Use ACID only where necessary (financial transactions)
Accept eventual consistency elsewhere (recommendations, analytics)
```

---

#### **Indexing**

**Without index** (scanning entire table):
```
Query: "Find trader with ID = 'T001'"
Process:
├─ Check row 1: ID = 'T002'? No
├─ Check row 2: ID = 'T005'? No
├─ Check row 3: ID = 'T001'? YES!
├─ Checked 1 million rows, found at end
└─ Time: 1 million comparisons

With 1000 queries: 1 BILLION comparisons!
```

**With index** (fast lookup):
```
Index: Trade ID → Row position
'T001' → Row 3
'T002' → Row 1
'T005' → Row 2

Query: Find 'T001'
Process:
├─ Look up 'T001' in index
├─ Get row 3 immediately
└─ Time: Few comparisons (binary search in index)

With 1000 queries: Few thousand comparisons!
```

**Types of Indexes**:

```
B-Tree Index (most common):
Used for: Range queries (age BETWEEN 25 AND 35)
Structure: Balanced tree for fast lookup
Cost: Adds memory overhead, slower writes

Hash Index:
Used for: Exact match (ID = 'T001')
Structure: Hash table (dictionary)
Cost: Very fast for exact match, slow for range

Bitmap Index:
Used for: Columns with few values (status = 'ACTIVE' or 'INACTIVE')
Example: Gender (M/F), Status (yes/no)
Cost: Memory efficient for low-cardinality columns

Inverted Index:
Used for: Full-text search
Example: Find documents containing word "urgent"
Cost: Extra storage, but enables fast text search
```

**Index Tradeoffs**:
```
Pros:
├─ Speeds up reads 100x - 1000x
└─ Makes complex queries feasible

Cons:
├─ Uses extra memory (100GB index for 1TB table)
├─ Slows down writes (need to update index too)
├─ Storage cost
└─ Too many indexes confuse query optimizer

Best practice:
├─ Index columns frequently searched (WHERE, JOIN)
├─ Index columns in JOIN conditions
├─ Don't over-index
```

---

### Database Sharding

**Problem**: Table too large for one machine

```
trades table: 1 billion rows = 100GB
├─ Fits on single machine, but:
├─ Queries slow (full scan)
├─ Writes slow (contention)
└─ Machine failure loses data
```

**Solution: Sharding** (horizontal partitioning)

```
Shard 1: Trades with trader_id = T0000-T1999
Shard 2: Trades with trader_id = T2000-T3999
Shard 3: Trades with trader_id = T4000-T5999
...
Shard 10: Trades with trader_id = T8000-T9999

Each shard on separate machine:
├─ Query faster (100MB instead of 100GB)
├─ Writes faster (less contention)
├─ Data distributed (hardware failure less critical)
└─ Can scale to billions of rows
```

**Sharding strategies**:

```
Range-based:
├─ Shard by trader_id range (T0000-T1999, T2000-T3999)
├─ Pro: Simple
└─ Con: Unbalanced (some traders more active than others)

Hash-based:
├─ Shard = hash(trader_id) % num_shards
├─ Pro: Even distribution
└─ Con: Resharding is hard (changing shard count breaks mapping)

Directory-based:
├─ Lookup table: trader_id → shard
├─ Pro: Flexible, can rebalance
└─ Con: Lookup overhead, extra system to maintain
```

**Challenges**:
```
Cross-shard query:
Query: "Total trades by all traders"
├─ Without sharding: Single query
├─ With sharding: Query all 10 shards, aggregate
└─ Slower but necessary

Cross-shard transaction:
Transfer money between traders on different shards
├─ Can't use ACID transaction (not on same shard)
├─ Must use eventual consistency
└─ Complex application logic
```

---

### Database Replication

**Problem**: Machine failure loses data

**Solution**: Keep copies on multiple machines

```
Master Database (receives writes)
├─ Write: New trade recorded
└─ Replicates to slaves

Slave 1 (backup copy)
├─ Read: Can answer queries from copy
└─ Read-only

Slave 2 (another copy)
├─ Async replication (lag possible)
└─ Read-only

Failure scenario:
├─ Master dies: Promote slave 1 to master
├─ Data persists: All machines had copy
└─ Service continues
```

**Replication Modes**:

```
Synchronous Replication:
├─ Master waits for slaves to acknowledge write
├─ Pro: Strong consistency, no data loss
└─ Con: Slow writes (wait for network)

Asynchronous Replication:
├─ Master doesn't wait for slaves
├─ Pro: Fast writes
└─ Con: Possible data loss if master crashes before slaves sync

Semi-Synchronous:
├─ Master waits for at least 1 slave
├─ Pro: Balance of speed and safety
└─ Used in production most common
```

---

### Database Summary for System Design

```
Key Concepts:

1. Choose database for access pattern
   ├─ OLTP reads/writes: Relational (PostgreSQL)
   ├─ OLAP analytics: Data warehouse (BigQuery)
   ├─ Cache: Key-value (Redis)
   ├─ Search: Elasticsearch
   └─ Time series: InfluxDB

2. Scaling strategies
   ├─ Vertical: Bigger machine (limited)
   ├─ Horizontal: More machines (sharding, replication)
   └─ Caching: Reduce database hits

3. Tradeoffs
   ├─ Consistency vs Speed (ACID vs eventual)
   ├─ Read vs Write optimization (indices, denormalization)
   └─ Normalized vs Denormalized (storage vs speed)

4. Indexing
   ├─ Massively speeds up reads
   ├─ Slows down writes
   └─ Use strategically (not on every column)

5. Replication & Sharding
   ├─ Replication: Redundancy, reads scaling
   ├─ Sharding: Write scaling, availability
   └─ Both needed for large systems
```

---

## Networking & HTTP Basics

### How Internet Works (Simplified)

**Request Journey**:
```
1. Your browser (client)
2. Internet → DNS lookup → Find server IP
3. TCP connection to server (three-way handshake)
4. Send HTTP request
5. Server processes
6. Server sends HTTP response
7. Browser renders

Time: 100ms - 1 second per request
```

---

### HTTP Protocol Basics

**What is HTTP?**: Application protocol (rules for communication)

**Request Format**:
```
GET /api/trades HTTP/1.1
Host: data.dbg.com
User-Agent: Mozilla/5.0
Accept: application/json
Content-Length: 0

[Optional request body for POST/PUT]
```

**Response Format**:
```
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 256
Cache-Control: max-age=3600

[Response body]
{"trades": [...]}
```

**Status Codes**:
```
2xx: Success
├─ 200 OK: Request succeeded
└─ 201 Created: Resource created

3xx: Redirect
├─ 301 Moved: URL changed permanently
└─ 304 Not Modified: Client cache is fresh

4xx: Client error
├─ 400 Bad Request: Invalid request
├─ 401 Unauthorized: Need authentication
├─ 403 Forbidden: Authenticated but not allowed
└─ 404 Not Found: Resource doesn't exist

5xx: Server error
├─ 500 Internal Server Error: Server crashed
├─ 502 Bad Gateway: Server unreachable
└─ 503 Service Unavailable: Server overloaded
```

---

### HTTP Methods

**GET**: Retrieve data (safe, idempotent)
```
GET /api/trades/123
├─ Retrieves trade #123
├─ No side effects
└─ Call multiple times = same result
```

**POST**: Create new data
```
POST /api/trades
Body: {trader_id: "T001", amount: 100000}
├─ Creates new trade
├─ Has side effects
└─ Each call creates new trade (not idempotent)
```

**PUT**: Replace entire resource
```
PUT /api/trades/123
Body: {trader_id: "T001", amount: 150000}
├─ Replaces all fields
└─ Idempotent (calling twice = same result)
```

**PATCH**: Update part of resource
```
PATCH /api/trades/123
Body: {amount: 150000}
├─ Updates only amount field
└─ Idempotent
```

**DELETE**: Remove resource
```
DELETE /api/trades/123
├─ Removes trade #123
└─ Idempotent (deleting twice = same result)
```

---

### HTTP Versions

**HTTP/1.1** (still dominant):
```
Features:
├─ Keep-alive (reuse connection)
├─ Pipelining (send multiple requests)
├─ Compression (gzip)

Limitation: One response per request (head-of-line blocking)
Example: If first request takes 1 second, all others wait
```

**HTTP/2**:
```
Features:
├─ Multiplexing (many requests on one connection)
├─ Server push (send data proactively)
├─ Binary format (more efficient)

Benefit: Faster for many small requests
```

**HTTP/3**:
```
Features:
├─ Uses UDP instead of TCP (faster)
├─ Even better multiplexing
├─ Faster connection establishment

Status: Newer, still rolling out
```

---

### DNS (Domain Name System)

**Problem**: Humans use names (google.com), but internet uses IPs (142.251.41.14)

**Solution**: DNS - Phone book for internet

```
Request: What's IP of google.com?
┌─────────────────────────────────────────────┐
│ DNS Recursive Resolver (ISP or 8.8.8.8)    │
└─────────────────────────────────────────────┘
           ↓ (if not cached)
┌─────────────────────────────────────────────┐
│ Root Nameserver                             │
│ "For .com domains, ask TLD server"          │
└─────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────┐
│ TLD Nameserver (.com)                       │
│ "For google.com, ask authoritative server"  │
└─────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────┐
│ Authoritative Nameserver (Google's server)  │
│ "IP of google.com is 142.251.41.14"         │
└─────────────────────────────────────────────┘

Result: Client gets IP 142.251.41.14, connects to server
```

**Caching**: Results cached at multiple levels (ISP, browser)
```
DNS lookup cost: 10-100ms
With caching: < 1ms (served from cache)
```

**Important for System Design**:
```
DNS Propagation: Takes up to 48 hours for changes to spread
└─ Important when migrating servers

DNS Failover: Can point same domain to multiple IPs
├─ Client gets random IP (load balancing)
└─ Can remove failed server IP

GeoDNS: Return different IP based on client location
├─ User in US gets US server
├─ User in Europe gets European server
└─ Reduces latency
```

---

### TCP vs UDP

**TCP (Transmission Control Protocol)**:
```
Properties:
├─ Ordered: Messages arrive in order
├─ Reliable: All messages arrive
├─ Slow: Requires handshake, acknowledgments
├─ Example: HTTP, FTP, Email

Use cases:
✓ Financial transactions (can't lose trades)
✓ Email (need all messages)
✗ Real-time video (one lost frame is ok)

Three-way handshake (connection establishment):
Client: "Hello, I want to talk"        [SYN]
Server: "OK, I hear you too"            [SYN-ACK]
Client: "Great, let's start"            [ACK]
Result: Connection established
Cost: 1 round trip (~100ms latency)
```

**UDP (User Datagram Protocol)**:
```
Properties:
├─ Unordered: Messages might arrive out of order
├─ Unreliable: Messages might be lost
├─ Fast: No handshake, fire-and-forget
├─ Example: Gaming, VoIP, Streaming

Use cases:
✓ Real-time video (loss of frame is acceptable)
✓ Online gaming (one lost position update is ok)
✗ Financial transactions (can't lose data)

No handshake:
Client: Sends message immediately
Result: Fast, but no guarantee delivery
Cost: No extra latency for connection
```

**Example**: Video streaming
```
Over TCP:
├─ Every frame guaranteed to arrive
├─ But if frame arrives late (out of order), must wait
├─ Result: Buffering (bad user experience)

Over UDP:
├─ Frames might arrive out of order, some might be lost
├─ But receive as many as possible as fast as possible
├─ Result: Smooth playback with occasional glitches
└─ Acceptable for video (human eye doesn't notice)
```

---

### Load Balancing

**Problem**: One server can't handle all requests

```
1000 requests/second
├─ Single server: Crashes, slow responses
└─ Solution: Multiple servers
```

**Solution: Load Balancer**

```
User requests → Load Balancer → distributes to one of many servers

           ┌─ Server 1 (handles 333 requests)
Client ──→ │
           ├─ Server 2 (handles 333 requests)
           │
           └─ Server 3 (handles 334 requests)

Benefits:
├─ Each server less loaded (faster responses)
├─ One server dies: Others handle requests
├─ Can scale horizontally (add more servers)
```

**Load Balancing Strategies**:

```
Round Robin: 
Request 1 → Server 1
Request 2 → Server 2
Request 3 → Server 3
Request 4 → Server 1 (cycle)

Least Connections:
├─ Track connections per server
├─ Route to server with fewest connections
├─ Better for unequal request load

IP Hash:
├─ hash(client_ip) % num_servers = target server
├─ Same client always goes to same server
├─ Pro: Session stickiness
└─ Con: Uneven if clients have varied workloads
```

---

### Caching Layers

**Types of Caches** (in order from closest to client):

```
1. Browser Cache (fastest)
   ├─ Browser stores responses
   ├─ Time: < 1ms
   └─ Control: HTTP headers (Cache-Control, ETag)

2. CDN Cache (Content Delivery Network)
   ├─ Geographically distributed cache
   ├─ Time: 10-50ms
   └─ Example: Cloudflare, Akamai

3. Application Cache (in-memory)
   ├─ Cache in application memory
   ├─ Time: 1-10ms
   └─ Example: Using local HashMap

4. Database Cache (in-process)
   ├─ Database's internal cache
   ├─ Time: 1-100ms
   └─ Automatic in most databases

5. External Cache (Redis, Memcached)
   ├─ Separate service
   ├─ Time: 1-10ms (network latency)
   └─ Shared across multiple servers
```

**Cache-Control Headers**:
```
Cache-Control: public, max-age=3600
├─ public: Browser and CDN can cache
├─ max-age=3600: Cache for 1 hour
└─ After 1 hour: Browser requests fresh from server

Cache-Control: private, max-age=300
├─ private: Only browser can cache (not CDN)
└─ max-age=300: Cache for 5 minutes

Cache-Control: no-cache, no-store
├─ no-cache: Browser must revalidate with server
└─ no-store: Don't cache at all (sensitive data)
```

**ETag** (Entity Tag for cache invalidation):
```
Request: GET /api/trades/123
Response: 
  ETag: "abc123def456"
  [Body with trade data]

Browser caches response with ETag.

Next request (after max-age expires):
Request: GET /api/trades/123
         If-None-Match: "abc123def456"

Server response:
├─ If data unchanged: 304 Not Modified (empty body)
│  Browser uses cached version (bandwidth saved!)
└─ If data changed: 200 OK (full body)
   Browser uses new response, updates ETag
```

---

## Storage & File Systems

### Types of Storage

**RAM (Memory)**:
```
Speed: Nanoseconds (fastest)
Persistence: Lost on power off
Cost: Expensive ($1 per GB)
Capacity: Gigabytes (typical servers)
Use: Caching, databases
```

**SSD (Solid State Drive)**:
```
Speed: Microseconds (100x slower than RAM)
Persistence: Permanent
Cost: Moderate ($0.10 per GB)
Capacity: Terabytes (typical servers)
Use: Operating system, databases, applications
```

**HDD (Hard Disk Drive)**:
```
Speed: Milliseconds (10,000x slower than RAM)
Persistence: Permanent
Cost: Cheap ($0.01 per GB)
Capacity: Terabytes to Petabytes
Use: Archive, backups, data warehouses
```

**Network Storage**:
```
Speed: Milliseconds to seconds (depends on network)
Persistence: Permanent (replicated)
Cost: Variable (cloud storage pricing)
Capacity: Unlimited (can scale)
Use: Cloud systems, data pipelines
```

---

### File Systems

**What is a File System?**: How data is organized on disk

```
Directory structure:
/home/viraaj/
├─ /documents/
│  ├─ resume.pdf
│  └─ interview_notes.txt
├─ /code/
│  ├─ main.py
│  └─ utils.py
└─ /data/
   └─ trades.csv
```

**File System Operations**:
```
Sequential Read:
├─ Read file from start to end
├─ Efficient (data laid out contiguously)
└─ Example: Scan large CSV file

Random Read:
├─ Read file at arbitrary positions
├─ Inefficient (disk has seek time)
└─ Example: Database queries (with indexing helps)

Sequential Write:
├─ Append to file
├─ Very efficient
└─ Example: Logging, append-only databases (Kafka)

Random Write:
├─ Update file at arbitrary position
├─ Inefficient (read-modify-write)
└─ Example: Database updates
```

---

## Concurrency & Threading

### Synchronization Problems

**Race Condition**: Two threads access shared data simultaneously

```
Shared variable: counter = 0

Thread A: Read counter (0) → Add 1 → Write 1
Thread B: Read counter (0) → Add 1 → Write 1

Expected: counter = 2
Actual: counter = 1 (data race!)

Why? Both threads read 0, both write 1, one write lost.
```

**Solution: Mutex (Mutual Exclusion)**
```
Mutex lock: Only one thread can acquire

Thread A: 
  ├─ Lock mutex
  ├─ Read counter (0)
  ├─ Add 1
  ├─ Write 1
  └─ Unlock mutex

Thread B:
  ├─ Try lock (wait, A has it)
  ├─ A unlocks
  ├─ Lock acquired
  ├─ Read counter (1)
  ├─ Add 1
  ├─ Write 2
  └─ Unlock mutex

Result: counter = 2 ✓ Correct!

Cost: Threads must wait for each other (serialization)
```

**Deadlock**: Threads wait for each other forever

```
Thread A holds Mutex 1, wants Mutex 2
Thread B holds Mutex 2, wants Mutex 1

Both wait forever (circular dependency)
```

---

### Concurrency Models

**Threads (Fine-grained concurrency)**:
```
Pros:
├─ Shared memory (easy data sharing)
├─ Parallelism (true on multi-core)
└─ Responsive (one thread blocked doesn't stop others)

Cons:
├─ Race conditions (hard to debug)
├─ Deadlocks (hard to avoid)
├─ Lock contention (slow under load)
└─ Complex to reason about
```

**Processes (Coarse-grained concurrency)**:
```
Pros:
├─ Isolated memory (no race conditions)
├─ Can run on different machines
└─ Failure isolation (one process crash doesn't affect others)

Cons:
├─ No shared memory (slow IPC - Inter-Process Communication)
├─ More resource consumption (each has own memory)
└─ Higher context switching overhead
```

**Event-Driven / Async (Non-blocking)**:
```
Pros:
├─ Single thread (no race conditions)
├─ Memory efficient (many async operations per thread)
├─ Very scalable (handles many concurrent operations)

Cons:
├─ Callback hell (complex code structure)
├─ Debugging difficult (stack traces span async boundaries)
└─ CPU-bound operations block (need care)

Example: node.js, async Python
```

---

## Performance Metrics

### Key Metrics You Need to Know

**Latency**: Time to complete one request
```
Latency 10ms means: One request takes 10 milliseconds

Percentiles important:
├─ P50 (median): Half requests faster, half slower
├─ P95: 95% of requests faster than this
├─ P99: 99% of requests faster than this
└─ P99.9: 99.9% of requests faster than this

Why percentiles?
├─ Average can be misleading
├─ P99 shows worst-case user experience
└─ Focus on P99, not average
```

**Throughput**: Number of requests handled per second
```
Example: 1000 requests per second (RPS)
├─ 1000 clients requesting simultaneously
├─ Server handles all 1000 per second
```

**Availability**: Percentage of time system is working
```
99% availability = 3 days downtime per year
99.9% = 8 hours per year
99.99% = 50 minutes per year
99.999% = 5 minutes per year

DBG requirement: 99.99% (high availability)
```

**Bandwidth**: Amount of data transferred
```
Example: 1 Gbps = 1 gigabit per second
├─ Video streaming: Need high bandwidth
└─ API calls: Need low bandwidth
```

---

### Little's Law (Critical for System Design)

**Relationship between throughput, latency, and concurrency**:

```
Concurrent Users = Throughput × Latency

Example:
├─ Throughput: 100 requests/second
├─ Latency: 0.1 seconds (100ms)
├─ Concurrent Users: 100 × 0.1 = 10 users

If latency increases to 1 second:
├─ Concurrent Users: 100 × 1 = 100 users needed

If want only 10 users concurrently with 1 second latency:
├─ Needed throughput: 10 / 1 = 10 RPS
```

**Why Important for System Design**:
```
Capacity planning:
├─ If expect 100,000 concurrent users
├─ And latency is 100ms
├─ Need throughput: 100,000 / 0.1 = 1,000,000 RPS

That's huge! So either:
├─ Reduce latency (cache, optimize queries)
├─ Reduce concurrent users (not possible)
└─ Add more servers (increase throughput)
```

---

### Amdahl's Law (Parallelization Limits)

**How much faster with more processors?**

```
If 50% of code is serial (can't parallelize):
├─ With 1 processor: 1 second
├─ With 2 processors: 0.75 seconds (25% faster)
├─ With 10 processors: 0.55 seconds (45% faster)
├─ With infinite processors: 0.5 seconds (limited by serial part!)

Formula: 1 / ((1 - p) + p/n)
├─ p = parallelizable fraction
├─ n = number of processors
└─ Result = speedup

Example: p = 0.95 (95% parallelizable), n = 100 processors
├─ Speedup = 1 / ((1 - 0.95) + 0.95/100)
├─ Speedup = 1 / (0.05 + 0.0095)
├─ Speedup = 15.4x (not 100x!)

Why? 5% serial portion becomes bottleneck.
```

**Important for System Design**:
```
Adding more servers has diminishing returns.
Focus on:
├─ Reducing serial portions (caching, preprocessing)
├─ Load balancing expensive operations
└─ Not blindly adding servers (wastes money)
```

---

### Summary: Prerequisites for System Design

```
Operating System:
├─ Processes and threads
├─ Memory management and virtual memory
├─ CPU scheduling and context switching
├─ I/O operations (blocking vs non-blocking)

Databases:
├─ Relational (SQL) vs NoSQL
├─ ACID vs eventual consistency
├─ Indexing and query optimization
├─ Sharding and replication
├─ OLTP vs OLAP patterns

Networking:
├─ HTTP protocol and methods
├─ DNS and domain resolution
├─ TCP vs UDP
├─ Load balancing strategies
├─ Caching and CDN

Storage:
├─ RAM vs SSD vs HDD tradeoffs
├─ File systems and I/O patterns

Concurrency:
├─ Race conditions and mutual exclusion
├─ Different concurrency models

Performance Metrics:
├─ Latency, throughput, availability
├─ Little's Law
├─ Amdahl's Law
```

---

**You now understand the operating system, database, and networking fundamentals needed for system design. Next file will cover core components (cache, message queues, databases, etc.) and how to combine them!**
