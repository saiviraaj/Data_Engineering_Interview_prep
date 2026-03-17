# Quick Reference Cards: 1-Page Cheat Sheets
## Keep These Visible During System Design Interview Practice

---

## CARD 1: THE 7-STEP INTERVIEW FRAMEWORK

```
STEP 1: Understand (2-3 min)
  □ Listen carefully
  □ Take notes
  □ Clarify ambiguity
  → "So, if I understand..."

STEP 2: Clarify Requirements (3-5 min)
  Ask about:
  □ Scale (users, events/sec, data size)
  □ Latency (required response time)
  □ Consistency (strong vs eventual)
  □ Availability (SLA needed)
  □ Features (must-have vs nice-to-have)
  → "Is X critical or nice-to-have?"

STEP 3: Define Data Model (3-5 min)
  □ Key entities
  □ Relationships
  □ Access patterns (queries)
  □ Partition strategy
  → "Most queries will be by..."

STEP 4: High-Level Design (15-20 min)
  □ Draw 5-7 major components
  □ Show data flow
  □ Explain each decision
  □ Check with interviewer
  → "Does this approach make sense?"

STEP 5: Deep Dive (15-20 min)
  Pick 2-3 components:
  □ How would you scale this?
  □ What if it fails?
  □ Why that choice over alternatives?
  □ Trade-offs and constraints

STEP 6: Handle Failures (5-10 min)
  □ What can fail?
  □ How to detect?
  □ How to recover?
  □ Monitoring/alerting

STEP 7: Final Discussion (5 min)
  □ "Anything else important?"
  □ "Shall we go deeper on X?"
  □ Answer remaining questions

TIMING: 45-60 minutes total
```

---

## CARD 2: SCALABILITY FORMULAS

```
THROUGHPUT SCALING:

Current capacity: X req/sec
Target capacity: 10X req/sec

Approach 1 - Horizontal Scaling:
  Number of servers = 10X / (capacity per server)
  Example: 10K req/sec with 1K per server = 10 servers

Approach 2 - Sharding:
  Shards needed = Total data / (shard max size)
  Example: 1TB total ÷ 100GB per shard = 10 shards
  Each shard handles: 10X requests ÷ 10 shards = X requests

LATENCY SCALING:

Current latency: X ms
Target latency: Y ms (faster)

Solutions (in order of effectiveness):
  1. Caching (reduce by 100x)
  2. Index optimization (reduce by 10x)
  3. Compression (reduce by 90% data)
  4. Parallelization (reduce by # of cores)
  5. Hardware upgrade (reduce by 2-5x)

BANDWIDTH SCALING:

Required bandwidth: X GB/sec
Network capacity: Y GB/sec

If X > Y:
  1. Compression (90% reduction typical)
  2. Multiple regions (distribute load)
  3. Batching (fewer, larger requests)
  4. Caching (reduce request frequency)

STORAGE SCALING:

Data growth: X GB/day
Current storage: Y TB
Available storage: Z TB

Time until full: (Z TB × 1000 GB/TB) ÷ X GB/day = Days

Add storage proactively at:
  ├─ 70% capacity: Start plan
  ├─ 80% capacity: Order new storage
  ├─ 90% capacity: Implement archival
```

---

## CARD 3: COMMON PATTERNS

```
REAL-TIME STREAMING:
  Flow: Source → Kafka → Processor → Storage
  Example: Events/sec, sub-second latency
  Tools: Kafka, Spark, BigQuery
  Key: Partitioning, checkpoints, exactly-once

BATCH PROCESSING:
  Flow: Source → Scheduler → Processor → Storage
  Example: Daily load, acceptable delay
  Tools: Airflow, Spark, BigQuery
  Key: Idempotency, rollback, verification

CACHING LAYER:
  Flow: Client → Cache → Storage
  Hit rate: > 95% for performance
  TTL: Based on staleness tolerance
  Tools: Redis, Memcached
  Key: Eviction policy, cache invalidation

SHARDING:
  Strategy: hash(key) % num_shards
  Rebalancing: Consistent hashing for adding shards
  Hot shards: Monitor and plan for growth
  Cross-shard: Batch or limit

REPLICATION:
  Master-slave: Reads from slaves, writes to master
  Async: Fast, risk of loss
  Sync: Safe, slower
  Quorum: Balance of both
  
DATABASE CHOICE:
  SQL: Transactions, consistency, structured
  NoSQL: Scale, flexibility, eventual consistency
  Time-series: Metrics, events, timestamps
  Search: Full-text, indexing, ranking
```

---

## CARD 4: FAILURE PATTERNS

```
CIRCUIT BREAKER:
  States: CLOSED → OPEN → HALF_OPEN → CLOSED
  
  CLOSED: Normal operation, requests go through
  OPEN: Too many failures, block requests (fail fast)
  HALF_OPEN: Wait period elapsed, try one request
  
  If HALF_OPEN succeeds: Return to CLOSED
  If HALF_OPEN fails: Return to OPEN

RETRY WITH BACKOFF:
  Attempt 1: Immediate (0 sec)
  Attempt 2: Wait 1s, retry
  Attempt 3: Wait 2s, retry
  Attempt 4: Wait 4s, retry
  Attempt 5: Wait 8s, retry
  Give up: After N attempts
  
  Formula: wait_time = base_delay × 2^(attempt_num)

BULKHEADS:
  Separate resource pools:
  ├─ Thread pool A: Service A
  ├─ Thread pool B: Service B
  └─ Thread pool C: Service C
  
  If A uses all threads, B & C unaffected

TIMEOUTS:
  Every external call needs timeout
  ├─ Network timeout: 5-30 seconds
  ├─ Database timeout: 1-5 seconds
  ├─ API timeout: 10-30 seconds
  └─ Default if not specified: 30 seconds

FALLBACK:
  If primary fails:
  ├─ Cache: Serve stale data
  ├─ Secondary: Use backup service
  ├─ Degrade: Partial functionality
  └─ Error: Return clear error message
```

---

## CARD 5: DEUTSCHE BÖRSE SPECIFICS

```
REQUIREMENTS:
  Scale: 100K+ trades/second
  Latency: < 100ms to dashboard
  Uptime: 99.99% (4 nines, ~43 min/year)
  Consistency: No duplicate trades (exactly-once)
  Compliance: Audit trails, data retention

TECH STACK:
  Ingestion: Kafka (multi-source, Teradata/Oracle)
  Processing: Spark Streaming (100K/sec)
  Storage: BigQuery (real-time, analytics)
  Cache: Redis (dashboard, < 5ms)
  ORchestration: Airflow/Cloud Composer

TRADE-OFFS:
  Reliability > Speed
  Consistency > Availability
  Batch > Real-time (where acceptable)
  Cost > Performance (where acceptable)

TALKING POINTS:
  ✓ CDM Next experience (multi-source, scale)
  ✓ Real-time processing (Kafka + Spark)
  ✓ BigQuery expertise (cost, scale)
  ✓ Leadership (team building, strategy)
  ✓ Reliability mindset (99.99% uptime)
```

---

## CARD 6: DATA MODEL QUESTIONS

```
When designing data model, ask:

ENTITIES:
  □ What are the main objects?
  □ What are their attributes?
  □ How do they relate?

RELATIONSHIPS:
  □ One-to-many? Many-to-many?
  □ Denormalize or normalize?
  □ Foreign keys or no-SQL approach?

ACCESS PATTERNS:
  □ How will data be queried?
  □ By what key primarily?
  □ Range queries? Point queries?
  □ Frequency of each query?

PARTITIONING:
  □ By date? By user? By geographic region?
  □ Hot partitions? Cold partitions?
  □ Archival strategy?

INDEXING:
  □ B-Tree for range? Hash for exact?
  □ Composite indexes?
  □ Too many = slow writes

SCALABILITY:
  □ How data grows over time
  □ Sharding strategy if needed
  □ Cross-shard queries minimized
```

---

## CARD 7: TRADE-OFFS MATRIX

```
CONSISTENCY vs AVAILABILITY:
  Strong consistency + High availability = Expensive
  (Distributed consensus required)
  
CONSISTENCY vs LATENCY:
  Strong consistency = Slower
  (Must verify all replicas)
  
COST vs PERFORMANCE:
  High performance = Expensive
  (More servers, specialized hardware)
  
SIMPLICITY vs FLEXIBILITY:
  Simple = Harder to change
  (Tight coupling)
  
BATCH vs REAL-TIME:
  Real-time = More complex
  (Harder to debug, scale)

VERTICAL SCALE vs HORIZONTAL SCALE:
  Vertical = Simpler, hits ceiling
  Horizontal = Complex, unlimited

When choosing:
  1. Understand requirements deeply
  2. Identify non-negotiables
  3. Accept compromises elsewhere
  4. Document reasoning
```

---

## CARD 8: COMMUNICATION TIPS

```
EXPLAIN COMPLEX IDEAS:
  Don't: "Use columnar storage with Dremel architecture"
  Do: "Store by column instead of row (like library by topic)"

USE NUMBERS:
  Don't: "Lots of data"
  Do: "100K events/sec, < 100ms latency"

JUSTIFY CHOICES:
  Don't: "We'll use Redis"
  Do: "Redis for cache because sub-millisecond latency
       and can cache recent trades for dashboard"

CHECK UNDERSTANDING:
  Don't: Talk for 10 minutes without pause
  Do: "Does this architecture make sense?" every 3 minutes

HANDLE QUESTIONS:
  Don't: "I don't know"
  Do: "Great question. I'm not 100% sure,
       but here's my approach..."

ADMIT GAPS:
  Don't: Make up answer
  Do: "That's edge case I didn't consider.
       Let me think... I'd solve it by..."
```

---

## HOW TO USE THESE CARDS

```
Before Interview:
  □ Print or have on screen
  □ Review 1-2 cards (quick refresh)
  □ DON'T study new material

During Practice:
  □ Have cards visible
  □ Refer if you get stuck
  □ Use as confidence boost

During Real Interview:
  □ Have for reference (if remote)
  □ Probably won't need them
  □ But nice to have nearby
  □ Build confidence knowing they're there

Key: These are reminders, not learning tools.
You should know this material already!
```

---

**Print these cards and keep nearby during practice.**

**They'll give you confidence knowing you have them.**

**But you probably won't need to reference them!** ✓

**You've prepared thoroughly. Trust yourself!** 💪
