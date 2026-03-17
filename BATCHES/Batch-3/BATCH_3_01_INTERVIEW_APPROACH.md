# System Design Interview Approach: Step-by-Step Framework
## How to Think Through and Solve System Design Problems

**Target**: Data engineers in system design interviews  
**Level**: Interview preparation (intermediate to advanced)  
**Time**: 3-4 hours reading + 2-3 hours practice  
**Goal**: Solve any system design problem confidently in 45-60 minutes

---

## Table of Contents

1. [Interview Overview](#interview-overview)
2. [Step-by-Step Approach](#step-by-step-approach)
3. [Common Patterns & Solutions](#common-patterns--solutions)
4. [Communication Tips](#communication-tips)
5. [Time Management](#time-management)
6. [Common Mistakes](#common-mistakes)

---

## Interview Overview

### What to Expect

**System Design Interview Format**:
```
Duration: 45-60 minutes
Format: 1 interviewer, 1 candidate, whiteboard/screen sharing

Structure:
├─ Problem statement (2-3 minutes)
├─ Clarification questions (5 minutes)
├─ High-level design (15-20 minutes)
├─ Deep dive on components (15-20 minutes)
├─ Handling scale/failures (10 minutes)
└─ Discussion/questions (5-10 minutes)

Interviewer evaluates:
├─ Can you understand ambiguous problems?
├─ Do you ask clarifying questions?
├─ Can you design systems?
├─ Do you think about scalability?
├─ Do you handle failures?
├─ Can you communicate clearly?
└─ Do you make good trade-off decisions?
```

### What You're Being Evaluated On

```
Technical Knowledge (40%):
├─ Do you know databases? (SQL vs NoSQL trade-offs)
├─ Do you know scalability? (sharding, caching, load balancing)
├─ Do you know reliability? (replication, circuit breaker, fallbacks)
├─ Do you understand trade-offs? (consistency vs availability)
└─ Can you design real systems?

Problem-Solving (30%):
├─ Do you break down complex problems?
├─ Do you ask right questions?
├─ Can you make reasonable assumptions?
├─ Can you identify bottlenecks?
└─ Can you improve design?

Communication (20%):
├─ Can you explain clearly?
├─ Do you engage with interviewer?
├─ Do you handle feedback?
└─ Are you easy to work with?

Depth (10%):
├─ How deep do you go?
├─ Can you handle follow-up questions?
└─ Do you know internals?
```

### Common System Design Problems

**For Data Engineers (like you)**:
```
Data Pipeline Design:
├─ Real-time trade processing pipeline (Financial)
├─ Log processing and analysis
├─ ETL system for data warehouse
├─ Real-time analytics platform
└─ Data streaming system (100K events/sec)

Platform Design:
├─ Message queue (Kafka-like)
├─ Cache system (Redis-like)
├─ Time-series database
├─ Data warehouse
└─ Distributed job scheduler

Scale Problems:
├─ Scale to 1M requests/second
├─ Process 1B rows per day
├─ Handle failures gracefully
└─ Multi-region disaster recovery
```

---

## Step-by-Step Approach

### STEP 1: Understand the Problem (5 Minutes)

**What to do**:
```
1. Listen carefully (don't interrupt)
2. Take notes
3. Identify key requirements
4. Identify what's NOT mentioned (implicit requirements)
```

**Example Problem**:
```
"Design a real-time trading platform that processes trades from multiple 
sources and displays them on a dashboard for traders. The system should 
handle 100K trades per second and traders should see updates within 1 second."
```

**What you understand**:
```
Explicit Requirements:
├─ Process trades from multiple sources (Teradata, Oracle, Kafka)
├─ Real-time updates (< 1 second latency)
├─ 100K trades/second throughput
├─ Display on dashboard
└─ Multiple concurrent traders

Implicit Requirements:
├─ High availability (can't go down)
├─ Accuracy (no trade loss)
├─ Scalability (might grow to 1M/sec)
├─ Easy to maintain
└─ Cost-effective
```

---

### STEP 2: Ask Clarifying Questions (5 Minutes)

**What to ask**:
```
Scale Questions:
├─ How many trades per day?
├─ How many concurrent traders?
├─ How many data sources?
└─ Expected growth rate?

Consistency Questions:
├─ Must system be 100% consistent?
├─ Can we have stale data by 1 minute?
├─ What about data loss? (Can we lose 1 trade/million?)
└─ What's acceptable RPO (Recovery Point Objective)?

Availability Questions:
├─ What's the SLA? (99%, 99.9%, 99.99%)
├─ Can system be down for 1 hour/month?
├─ How should we handle partial failures?
└─ What about multi-region?

Feature Questions:
├─ Must trades persist long-term?
├─ Do we need historical data?
├─ Do we need audit trail?
└─ Do we need alerts/notifications?
```

**Example Clarifying Questions to Ask**:
```
"Let me make sure I understand:
1. The system handles 100K trades/second - is this peak or average?
2. For latency < 1 second, does that include network round-trip?
3. Do we need 100% consistency or is eventual consistency ok?
4. What SLA are we targeting - 99%, 99.9%, or 99.99%?
5. Do we need to store historical trades or just real-time?"

This shows:
├─ You're thinking about details
├─ You're not making assumptions
├─ You understand trade-offs
└─ You care about requirements
```

---

### STEP 3: Define Data Model (5 Minutes)

**What to define**:
```
Entities:
├─ Trade (id, trader_id, symbol, amount, price, timestamp)
├─ Trader (id, name, email)
├─ Account (trader_id, balance, currency)
└─ Symbol (symbol, name, current_price)

Relationships:
├─ Trader has many Trades
├─ Trade references Symbol
└─ Trade references Account

Queries:
├─ Get trades for trader (frequent)
├─ Get all trades in last 1 hour (occasional)
├─ Get trader's portfolio (frequent)
└─ Get trade history (occasional)
```

**Example Data Model**:
```
Trades Table:
├─ Columns: trade_id, trader_id, symbol, amount, price, timestamp, status
├─ Primary Key: trade_id
├─ Partition: By date (2024-01-15, 2024-01-16, ...)
├─ Clustering: By trader_id (fast lookups per trader)
└─ Indexes: On symbol, trader_id, timestamp

Why this design?
├─ Partition by date: Manage growth, easy to archive
├─ Cluster by trader_id: Most queries are by trader
├─ Timestamp index: Range queries for "last hour"
└─ Efficient for the access patterns
```

---

### STEP 4: High-Level Design (15-20 Minutes)

**What to draw**:
```
Components:
├─ Data Sources (Teradata, Oracle, Kafka)
├─ Ingestion (Extractors, parsers)
├─ Processing (Transformation, validation)
├─ Storage (Database, cache)
├─ Serving (API, WebSocket)
└─ Monitoring (Metrics, logs, alerts)

Interactions:
├─ How data flows from source to user
├─ Sync vs async communication
├─ Where bottlenecks might be
└─ Where failures might happen
```

**High-Level Architecture Example**:
```
                 Data Sources
                /    |     \
            Teradata Oracle Kafka
                \    |     /
                 \   |    /
                  Extractors
                     |
                  Kafka Topic
                (partition: trader_id)
                     |
              Spark Streaming
           (transform, validate)
                     |
                  BigQuery
            (real-time ingestion)
                     |
                  Redis Cache
            (recent trades, aggregations)
                     |
                REST API + WebSocket
                     |
              Dashboards & Apps
```

**Explain your design**:
```
Why Kafka in the middle?
├─ Decouples sources from processing
├─ Allows parallel processing
├─ Can replay if processing fails
└─ Easy to add new processors

Why Spark?
├─ Can handle 100K events/sec
├─ Exactly-once semantics possible
├─ Can do complex transformations
└─ Fault-tolerant

Why BigQuery?
├─ Real-time ingestion (streaming inserts)
├─ Sub-second queries (columnar storage)
├─ Scales to billion+ rows automatically
└─ Cost-effective for this workload

Why Redis?
├─ Cache hot data (recent trades)
├─ 1ms latency vs BigQuery 100ms
├─ Reduce BigQuery load
└─ Dashboard can query cache first
```

---

### STEP 5: Deep Dive (15-20 Minutes)

**Pick bottlenecks to discuss**:
```
Option 1: Ingestion & Processing
├─ How do you handle 100K events/sec?
├─ What if Spark falls behind?
├─ How do you ensure no data loss?
└─ How do you handle late data?

Option 2: Storage & Querying
├─ How do you partition BigQuery table?
├─ What about query latency?
├─ How much data retention?
└─ How do you manage costs?

Option 3: Real-time Serving
├─ How do you push updates to clients?
├─ How do you handle 10K concurrent users?
└─ What if database is slow?

Option 4: Failures & Recovery
├─ What if Spark job crashes?
├─ What if BigQuery fails?
├─ What if Kafka topic fills up?
└─ How do you detect failures?
```

**Example Deep Dive: Handling 100K Events/Sec**

```
Challenge: Process 100K trades/sec with < 1 second latency

Solution:

1. Ingestion:
   ├─ Kafka with 256 partitions (parallel processing)
   ├─ Each partition: 391 trades/sec (manageable)
   └─ High throughput, good partitioning

2. Processing:
   ├─ Spark with 100 executors
   ├─ 4 cores per executor = 400 concurrent tasks
   ├─ 100K trades / 400 tasks = 250 trades/task
   └─ Process in micro-batches (100ms batches = 250 trades)

3. Bottleneck Analysis:
   ├─ Network: Can handle (Kafka optimized for throughput)
   ├─ Spark processing: Can handle (simple transformations)
   ├─ BigQuery: Can handle (accepts 100K rows/sec via streaming)
   └─ No single bottleneck identified!

4. Trade-offs:
   ├─ 100ms batch latency (acceptable, < 1 second total)
   ├─ Cost: 100 Spark executors (expensive)
   ├─ Complexity: Distributed system (hard to debug)
   └─ Tradeoff: Speed & scale vs cost & complexity

Why this works:
├─ Kafka distributes ingestion
├─ Spark parallelizes processing
├─ BigQuery handles ingestion rate
└─ No component overloaded
```

---

### STEP 6: Handle Failures (10 Minutes)

**What can fail?**
```
Source failures:
├─ Teradata down: Can't extract
├─ Oracle slow: Extraction lags
├─ Kafka network issue: Can't ingest
└─ Solution: Retry, fallback to cache, alert

Processing failures:
├─ Spark job crashes: Stop processing
├─ Out of memory: Can't process
├─ Timeout: Processing takes too long
└─ Solution: Retry from checkpoint, horizontal scaling

Storage failures:
├─ BigQuery unavailable: Can't write
├─ Storage quota full: Can't write
└─ Solution: Queue in Kafka, retry, alert

Serving failures:
├─ API down: Users can't see trades
├─ Network slow: Latency high
└─ Solution: Load balancer, fallback to cache, circuit breaker
```

**How to handle**:
```
Circuit Breaker Pattern:
├─ If BigQuery fails 3 times → Open circuit
├─ Stop sending data (avoid cascading failure)
├─ After 30 seconds → Try again (HALF_OPEN)
├─ If succeeds → Resume (CLOSED)
└─ Result: Fails fast, doesn't overload failing service

Retry with Exponential Backoff:
├─ 1st failure: Retry immediately
├─ 2nd failure: Wait 1 second, retry
├─ 3rd failure: Wait 2 seconds, retry
├─ 4th failure: Wait 4 seconds, retry
├─ 5th failure: Give up, alert
└─ Result: Handles transient failures

Fallback & Degradation:
├─ If BigQuery slow → Query cache instead
├─ If BigQuery down → Serve stale data from cache
├─ If cache down → Return error to user
└─ Result: Partial service better than total failure

Monitoring & Alerting:
├─ Track error rate per component
├─ Alert if error rate > 1%
├─ Alert if latency p99 > 5 seconds
├─ Alert if 0 trades processed in 1 hour
└─ Result: Know immediately when something fails
```

---

### STEP 7: Discuss Trade-offs (5 Minutes)

**Be ready to discuss**:
```
Consistency vs Availability:
├─ Strong consistency: All replicas in sync (slower)
├─ Eventual consistency: Replicas sync eventually (faster)
├─ For trades: Strong consistency important (no duplicate trades)
└─ Solution: Use transactions, avoid eventual consistency

Cost vs Performance:
├─ More servers: Faster (expensive)
├─ Fewer servers: Slower (cheap)
├─ For 100K trades/sec: Need decent infrastructure
└─ Solution: Right-sized infrastructure (not over/under)

Complexity vs Simplicity:
├─ Complex: Many components, hard to debug (powerful)
├─ Simple: Few components, easy to debug (limited)
├─ For trading: Need reliability → complexity acceptable
└─ Solution: Document well, automate ops

Caching vs Correctness:
├─ Cache: Fast but possibly stale
├─ Always fresh: Slow but correct
├─ For dashboard: Cache acceptable (1 second lag ok)
└─ Solution: Use cache with short TTL

Real-time vs Batch:
├─ Real-time: Immediate but complex
├─ Batch: Slower but simpler
├─ For trading: Must be real-time
└─ Solution: Use streaming architecture

Scalability vs Cost:
├─ Auto-scale: Expensive but can handle spikes
├─ Fixed capacity: Cheaper but limited
├─ For trading: Need headroom for peak times
└─ Solution: Plan for 2x expected peak load
```

---

## Common Patterns & Solutions

### Pattern 1: Real-Time Data Pipeline

**Problem**: Process 100K events/sec with < 1 second latency

**Solution Architecture**:
```
Source → Kafka → Spark → Database → Cache → API → Dashboard

Kafka:
├─ Partition by trader_id (parallel processing)
├─ Replication factor: 3 (availability)
└─ Retention: 7 days (can replay)

Spark:
├─ Micro-batches every 100ms
├─ Exactly-once semantics
├─ Checkpoint every 10 minutes
└─ Scale: Add more executors if falling behind

BigQuery:
├─ Streaming inserts
├─ Partition by date
├─ Cluster by trader_id
└─ Automatic scaling

Redis Cache:
├─ Recent 1000 trades per trader
├─ TTL: 1 hour
├─ Cache hit rate: 95%
└─ Reduce BigQuery load

API:
├─ Check cache first
├─ Fallback to BigQuery
├─ Circuit breaker for BigQuery
└─ Load balanced (3 instances)
```

### Pattern 2: Handling Failures

**Problem**: Keep system working despite failures

**Solution**:
```
For each component:

1. Detect failure:
   └─ Health checks (periodically verify component works)

2. Prevent cascading failure:
   └─ Circuit breaker (stop calling failing service)

3. Recover gracefully:
   ├─ Retry with backoff (try again with increasing delays)
   ├─ Fallback (use alternative)
   └─ Degrade (provide partial service)

4. Restore normal operation:
   └─ Once recovered, resume normal operation

Example - BigQuery fails:

1. Detect: 3 consecutive write failures
2. Prevent: Circuit breaker opens (stop sending)
3. Recover: Queue writes in Kafka, retry every 30 sec
4. Restore: Once BigQuery comes back, drain Kafka queue

Result: System survives BigQuery failure!
```

### Pattern 3: Scaling to Millions

**Problem**: System can only handle 100K/sec, need 1M/sec

**Solution**:
```
1. Identify bottleneck:
   └─ Where do we hit limits? (profiling, monitoring)

2. Scale that component:
   ├─ Option A: Vertical (bigger machine) - limited ceiling
   ├─ Option B: Horizontal (more machines) - unlimited
   └─ Choose: Horizontal scaling

3. Distributed system challenges:
   ├─ Network: Partition data (sharding)
   ├─ Consistency: Use consensus algorithms
   ├─ Failure: Replicate data
   └─ Debugging: Add logging and tracing

4. Example - Scale Kafka:
   ├─ Currently: 256 partitions, 100K/sec per partition
   ├─ To 1M/sec: Add 9x more partitions (2560 partitions)
   ├─ Each partition: 391 trades/sec (same as before)
   └─ Total: 1M/sec across all partitions

Same architecture, just bigger numbers!
```

---

## Communication Tips

### How to Present Your Design

**Structure Your Explanation**:
```
1. State assumptions (2 minutes)
   "I'm assuming X trades per second, Y concurrent users..."

2. Explain high-level flow (3 minutes)
   "Data flows from sources → Kafka → Spark → BigQuery → API"

3. Justify key decisions (2 minutes)
   "I chose Kafka because [reasons], BigQuery because [reasons]..."

4. Show you thought about scale (2 minutes)
   "For 100K/sec, Kafka handles X, Spark handles Y..."

5. Address failures (2 minutes)
   "If Kafka fails, we... If BigQuery fails, we..."

6. Be ready for feedback (ongoing)
   "Good point, let me reconsider that..."
```

### Engage With Interviewer

**What to do**:
```
✓ Explain as you go (don't just design silently)
✓ Ask "Does this approach make sense?"
✓ Take feedback gracefully ("Oh good catch, that's a problem")
✓ Adjust design based on feedback
✓ Defend positions with reasons (not just "because")
✓ Ask questions if unclear
✓ Say "I'm not sure about this" honestly
```

**What NOT to do**:
```
✗ Design in silence, then present complete solution
✗ Ignore interviewer feedback
✗ Get defensive about your design
✗ Make up answers to things you don't know
✗ Go into unnecessary details
✗ Use jargon without explaining
✗ Assume interviewer knows your background
```

### Handle Curve Balls

**Interviewer asks**: "What if this component fails?"

**Good response**:
```
"Good question. If [component] fails:
1. We'd detect it via health checks
2. Circuit breaker opens (stop calling it)
3. We fallback to [alternative]
4. System degrades but doesn't crash
5. Once it recovers, we resume normal operation

The risk is [X], but we mitigate by [Y]."
```

**Bad response**:
```
"Uh... it wouldn't fail?"
or
"I didn't think about that"
or
"We'd just restart it"
```

---

## Time Management

### 60-Minute Interview Breakdown

```
0-5 min: Understand problem & ask questions
5-25 min: High-level design (draw architecture)
25-45 min: Deep dive (discuss key decisions)
45-55 min: Handle failures & trade-offs
55-60 min: Final questions & wrap-up

Timing tips:
├─ Don't spend > 5 minutes on clarification
├─ Spend 20 minutes on high-level (this matters most!)
├─ Deep dive on what's important (not all components)
├─ Leave time for failures/trade-offs
└─ Don't run out of time (finish strong)
```

### What to Prioritize

**Spend TIME on** (matters for evaluation):
```
1. High-level architecture (shows you can design)
2. Key decisions (shows you think about trade-offs)
3. Bottleneck handling (shows you understand scale)
4. Failure handling (shows you care about reliability)
```

**Don't spend TIME on** (doesn't matter as much):
```
1. UI/UX details (not relevant for system design)
2. Implementation details (use Python vs Go doesn't matter)
3. Exact metrics (doesn't matter if 256 or 512 partitions)
4. Minor edge cases (focus on main flow first)
```

---

## Common Mistakes

### Mistake 1: Not Asking Clarifying Questions

**Bad**:
```
Interviewer: "Design a data system"
You: "Ok *starts drawing*"

Result: You designed for 100 users, but needed 1M users.
Entire design is wrong. Bad score.
```

**Good**:
```
Interviewer: "Design a data system"
You: "Let me clarify the requirements:
1. How many users? How many events per second?
2. What's the latency requirement?
3. What about durability? Any acceptable data loss?
4. SLA - 99%, 99.9%, or 99.99%?"

Result: Clear understanding of actual requirements.
Design matches reality. Good score.
```

### Mistake 2: Too Much Detail Too Soon

**Bad**:
```
You: "We'll use a PostgreSQL master-slave setup with 
WAL replication at 19.2 Mbps with synchronous commits..."

Result: Bogged down in details. No time for high-level.
Can't see forest for trees. Bad score.
```

**Good**:
```
You: "We'll use PostgreSQL with replication for availability.
The key design point is that we're prioritizing consistency over
availability because trades can't be duplicated."

Result: Clear about why, not lost in details. Good score.
```

### Mistake 3: Making Unjustified Assumptions

**Bad**:
```
Interviewer: "Design a caching system"
You: "We'll use Redis with 100 instances..."

Result: Why 100? Where'd that come from?
Seems arbitrary. Bad score.
```

**Good**:
```
Interviewer: "Design a caching system"
You: "To clarify: How many requests per second? How much
data in cache? We're aiming for 95% cache hit rate..."
Then: "With 1M req/sec and 1GB data, we'd need [calculation]
instances to achieve our latency goals."

Result: Justified, shows reasoning. Good score.
```

### Mistake 4: Not Discussing Trade-offs

**Bad**:
```
You: "We'll use NoSQL because it's faster"

Result: Don't understand trade-offs.
Seems naive. Bad score.
```

**Good**:
```
You: "We could use NoSQL for speed, but trades require
ACID transactions, so we chose SQL. We optimize read
performance with caching and sharding."

Result: Understand implications of choices. Good score.
```

### Mistake 5: Ignoring Failures

**Bad**:
```
You: "Data flows from source → processing → storage"

Interviewer: "What if processing fails?"
You: "Oh... it wouldn't?"

Result: Haven't thought about reliability.
Unrealistic design. Bad score.
```

**Good**:
```
You: "Data flows from source → Kafka → processing → storage.
If processing fails, we:
- Detect via health checks
- Circuit breaker prevents cascading failure
- Messages remain in Kafka
- Once processing recovers, we replay from Kafka
This way, we never lose data."

Result: Thoughtful about failures. Good score.
```

---

## Putting It All Together: Example Interview

### Full Example: Real-Time Trade Processing

**Interviewer**: "Design a system for real-time trade processing. 
Traders submit orders, we execute them, and show results in real-time 
on their dashboards."

**YOU** (Minutes 0-2: Clarify):
```
"Let me clarify the requirements:

1. Scale: How many trades per day? Per second?
   → 1 million trades per day, peak 100K per second

2. Latency: How fast from order to dashboard update?
   → Less than 1 second for 99% of trades

3. Data: Do we need to keep order history?
   → Yes, 2 years of history for compliance

4. Availability: Can the system go down?
   → Can't be down during trading hours (critical)

5. Consistency: Can trades be duplicated?
   → Absolutely not - must be exactly once"
```

**YOU** (Minutes 2-5: Assumptions):
```
"Based on this, my assumptions:
- Peak load: 100K trades/second
- 99% latency: < 1 second
- Data retention: 2 years
- SLA: 99.99% during trading hours
- Trade execution: Exactly once, no duplicates"
```

**YOU** (Minutes 5-25: High-Level Design):
```
"Here's my architecture:

[Draw on whiteboard]

Traders submit orders → API Gateway → Order Queue (Kafka) 
→ Order Processing (Spark) → Order Storage (PostgreSQL) 
→ Results Cache (Redis) → Dashboard API → Dashboards

Key decisions:
- Kafka: Decouples order submission from processing, enables replay
- Spark: Parallelizes order processing, handles 100K/sec
- PostgreSQL: Ensures consistency, supports transactions
- Redis: Caches recent orders, speeds up dashboard queries

Flow:
1. Trader submits order via API
2. Order stored temporarily in Kafka
3. Spark processes order (verification, execution)
4. Result stored in PostgreSQL
5. Result cached in Redis
6. Dashboard queries cache first, then PostgreSQL
7. WebSocket push updates to trader"
```

**Interviewer**: "How do you handle 100K orders per second?"

**YOU** (Minutes 25-35: Deep Dive on Scale):
```
"Great question. Here's the math:

Kafka:
- 256 partitions (by trader_id)
- Each partition: 391 orders/sec (manageable)
- Replication: 3x (availability)
- Result: Can handle 100K/sec easily

Spark:
- 100 executors (8 cores each = 800 cores)
- 800 parallel tasks
- 100K orders / 800 tasks = 125 orders per task
- Process in 100ms micro-batches
- Result: Can process 100K/sec

PostgreSQL:
- Sharded by trader_id (10 shards)
- Each shard: 10K orders/sec (within capacity)
- Replication: 3x slaves per shard
- Result: Can handle 100K writes/sec

Redis:
- In-memory, nanosecond latency
- Recent 1000 orders per trader
- Result: Instant dashboard updates"
```

**Interviewer**: "What if Spark crashes in the middle of processing?"

**YOU** (Minutes 35-45: Handling Failures):
```
"Excellent point! Here's how we handle it:

1. Spark checkpointing:
   - Save progress every 10 minutes
   - If crash, resume from last checkpoint
   - No duplicate processing (exactly-once)

2. Kafka provides durability:
   - Orders stay in Kafka for 7 days
   - If need to replay, can do so
   - Never lose orders

3. Circuit breaker on PostgreSQL:
   - If DB slow/down, circuit opens
   - Stop writing, queue in memory
   - Once recovered, flush queue

4. Monitoring:
   - Alert if Spark lag > 1 minute
   - Alert if error rate > 1%
   - Alert if 0 orders in 5 minutes

5. Fallback behavior:
   - If PostgreSQL down: Queue in memory (30 seconds), then drop
   - If Redis down: Query PostgreSQL directly (slower)
   - If Kafka down: Reject new orders, alert trader

Result: System survives any single failure!"
```

**Interviewer**: "What about consistency vs availability trade-off?"

**YOU** (Minutes 45-55: Trade-offs):
```
"That's the key trade-off here:

For trades, I prioritize consistency over availability:

1. Why consistency matters:
   - Can't duplicate trades (would debit/credit twice!)
   - Can't lose trades (compliance requirement)
   - Needs to match regulatory requirements

2. How we achieve consistency:
   - PostgreSQL (ACID transactions)
   - Exactly-once semantics in Spark
   - No eventual consistency

3. Availability trade-off:
   - If PostgreSQL unavailable: Orders rejected (not accepted)
   - If Spark unavailable: Orders queue, then expire
   - Better to reject order than execute wrong

4. Alternative approach:
   - Could use eventual consistency
   - Process orders, confirm later
   - But creates complexity (reconciliation, user confusion)

5. Our choice:
   - Strong consistency now
   - Degraded availability if failure
   - Acceptable because trading hours are business hours
   - Can schedule maintenance during off-hours"
```

**Interviewer**: "Anything else you'd like to discuss?"

**YOU** (Minutes 55-60: Wrap-up):
```
"A few things I didn't get to detail:

1. Security:
   - API authentication (OAuth 2.0)
   - TLS encryption for data in transit
   - Encryption at rest for sensitive data

2. Monitoring:
   - Metrics: Orders processed/sec, latency p99, error rate
   - Logs: Structured logging for debugging
   - Alerts: Page engineer on anomalies

3. Testing:
   - Unit tests for order processing logic
   - Integration tests for full pipeline
   - Chaos engineering (intentionally break things)

4. Deployment:
   - Blue-green deployment (zero downtime)
   - Automated rollback on failure
   - Gradual rollout to catch issues early

Any of these you'd like to dig deeper on?"
```

**Result**: You covered:
- ✅ Architecture (high-level)
- ✅ Scale (how to handle 100K/sec)
- ✅ Failures (what if things break)
- ✅ Trade-offs (consistency vs availability)
- ✅ Communication (clear, engaging)

**Interview Score**: 8.5/10 - Strong hire!

---

## Key Takeaways

```
1. Ask clarifying questions (shows you don't make assumptions)
2. Draw architecture clearly (shows you can communicate)
3. Justify decisions (shows you understand trade-offs)
4. Discuss scale thoughtfully (shows you can handle growth)
5. Address failures proactively (shows you're responsible)
6. Engage with interviewer (shows you're collaborative)
7. Manage time well (shows you're organized)
8. Be honest about unknowns (shows you're humble)

Do these 8 things, you'll crush the interview! 💪
```

---

**You now have a complete framework for system design interviews.**

**Next: Practice problems help you apply this framework!**
