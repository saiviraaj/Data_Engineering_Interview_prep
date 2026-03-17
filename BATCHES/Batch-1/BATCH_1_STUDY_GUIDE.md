# Batch 1: Study Guide & Learning Plan
## How to Master System Design Fundamentals

**Files in Batch 1**:
1. BATCH_1_01_SYSTEM_DESIGN_PREREQUISITES.md (4-6 hours)
2. BATCH_1_02_SYSTEM_DESIGN_CORE_COMPONENTS.md (5-7 hours)

**Total Time**: 9-13 hours of study
**Goal**: Build foundation for system design interviews
**Approach**: Read for understanding, not memorization

---

## How to Use These Files

### Reading Approach

**Don't try to memorize everything.** Instead:

```
1. Read with UNDERSTANDING (active learning)
   ├─ As you read, ask yourself: "Why does this matter?"
   ├─ Try to explain concepts in your own words
   └─ Draw diagrams (reinforces understanding)

2. Make notes for YOUR knowledge base
   ├─ Not copying text
   └─ Just key points and examples

3. Skip advanced sections on first pass
   ├─ Re-read later when you have context
   └─ Don't get stuck on hard concepts

4. Use your CDM Next experience as anchor
   ├─ Relate new concepts to what you know
   └─ "Is this like how Spark handles X?"
```

### Document Structure

**Each section follows pattern**:
- Concept explanation
- Simple analogy/example
- Real-world application
- Pros/cons tradeoffs
- Why it matters for system design

**Read in order** (sections are progressive):

```
Prerequisites File:
1. Operating Systems → Databases → Networking → Storage → Concurrency
   Each builds on previous concepts.

Core Components File:
1. Relational → NoSQL → Caching → Message Queues → Load Balancing → Monitoring
   Progressive complexity.
```

---

## Day-by-Day Study Plan (2 weeks)

### Week 1: Foundations

**Day 1-2: Operating Systems (4 hours)**
```
Read: PREREQUISITES file, "Operating System Basics" section

Focus on understanding:
├─ Processes vs Threads (fundamental concept)
├─ Memory management (why caching matters)
├─ CPU & context switching (why thread pools sized carefully)
├─ I/O operations (why async I/O critical for web servers)
└─ Virtual memory (why RAM is precious)

Exercises:
├─ Explain to yourself: Why threads faster than processes?
├─ Draw: Memory layout in a process
└─ Think: Your Spark job uses threads. Why better than processes?

Time: 4 hours reading + 1 hour thinking/drawing
```

**Day 3-4: Databases (4 hours)**
```
Read: PREREQUISITES file, "Database Fundamentals" section

Key concepts to understand:
├─ Why relational databases for structured data
├─ Difference between SQL and NoSQL
├─ ACID transactions (why they matter but are slow)
├─ Indexing (how it speeds up queries 100x)
├─ Sharding (horizontal scaling)
└─ Replication (availability and redundancy)

Exercises:
├─ Trace through: How would you shard trades table?
├─ Explain: Why can't you easily JOIN across shards?
├─ Compare: Relational vs NoSQL for your use case

Time: 4 hours reading + 1 hour exercises
```

**Day 5: Networking (3 hours)**
```
Read: PREREQUISITES file, "Networking & HTTP Basics" section

Focus on:
├─ HTTP protocol basics (what you already know but deeper)
├─ HTTP methods and status codes
├─ TCP vs UDP (when to use each)
├─ DNS (how domains resolve to IPs)
├─ Load balancing (distributing requests)
└─ Caching headers (controlling browser/CDN cache)

Exercises:
├─ Explain: TCP handshake (3-way)
├─ Trace: HTTP request from browser to server
├─ Design: How would you route 1M requests/sec?

Time: 3 hours reading + 1 hour exercises
```

### Week 2: Components & Practical Application

**Day 6-7: Databases Deep Dive (6 hours)**
```
Read: CORE COMPONENTS file, "Relational Databases" and "NoSQL Databases"

Understanding goals:
├─ How relational databases store and query data
├─ Transaction isolation levels (why they matter)
├─ Query optimization (EXPLAIN plans)
├─ Different types of NoSQL:
│  ├─ Key-value (Redis)
│  ├─ Document (MongoDB)
│  ├─ Column-family (Cassandra)
│  └─ Graph (Neo4j)
└─ When to use each type

Exercises:
├─ Draw: How would you design trades schema in PostgreSQL?
├─ Explain: Why column-family better for analytics?
├─ Compare: If building real-time dashboard, which database?
└─ Think: How does BigQuery fit into architecture?

Time: 6 hours (deep reading + thinking)

** This is your strength area. Leverage your BigQuery knowledge! **
```

**Day 8-9: Caching (3 hours)**
```
Read: CORE COMPONENTS file, "Caching Systems" section

Key concepts:
├─ Cache levels (CPU, RAM, Redis, database, disk)
├─ Cache-aside pattern (most common)
├─ Write-through vs write-behind
├─ Cache invalidation strategies
└─ TTL and event-based invalidation

Practical design:
├─ How would you cache frequently-accessed trades?
├─ How to invalidate when new trade happens?
├─ Trade-off: Consistency vs speed

Time: 3 hours reading + problem-solving
```

**Day 10-11: Message Queues (3 hours)**
```
Read: CORE COMPONENTS file, "Message Queues & Event Streaming"

This is important for real-time systems!

Concepts:
├─ Message queues (decoupling producers/consumers)
├─ Pub/Sub (one-to-many messaging)
├─ Event streaming (Kafka-style)
├─ Partitioning for parallelism
├─ Consumer groups

Apply to finance:
├─ How would trades flow through message queue?
├─ How to process 100K events/second?
├─ How to ensure no loss of trades?

Time: 3 hours reading + architecture thinking
```

**Day 12: Load Balancing & API Gateway (2 hours)**
```
Read: CORE COMPONENTS file, "Load Balancing & API Gateways"

Understand:
├─ Different load balancing algorithms
├─ When to use each
├─ API gateway responsibilities
└─ Circuit breaker pattern

Time: 2 hours (shorter section)
```

**Day 13: Storage Systems (2 hours)**
```
Read: CORE COMPONENTS file, "Distributed File Systems" and "Cloud Object Storage"

Concepts:
├─ HDFS block replication
├─ Cloud storage (S3, GCS)
├─ Storage classes and cost

Your use case:
├─ Where do you store 100TB dataset?
├─ How to ensure availability?
├─ How to balance cost and performance?

Time: 2 hours
```

**Day 14: Monitoring & Review (2 hours)**
```
Read: CORE COMPONENTS file, "Monitoring & Observability"

Understand:
├─ Metrics (what to measure)
├─ Logging (structured logs)
├─ Tracing (tracking requests)

Review: Go back to "Component Selection Guide"
└─ Should now understand all components and when to use them.

Time: 2 hours
```

---

## Learning Tips

### Active Reading

```
DON'T just passively read. ACTIVELY engage:

When reading about databases:
├─ Pause and think: "How is this different from BigQuery?"
├─ Sketch: Diagram of how sharding works
├─ Apply: "If I had 100B rows of trades, how would I shard?"
└─ Question: "What would happen if shard went down?"

This active engagement moves knowledge to long-term memory.
```

### Relate to Your Experience

```
You know:
├─ PySpark (distributed processing)
├─ Kafka (message streaming)
├─ BigQuery (data warehouse)
├─ Airflow (orchestration)

As you read new concepts, connect:
├─ "This cache pattern is like Spark RDD caching"
├─ "This load balancing like how Spark distributes tasks"
├─ "This sharding like how BigQuery partitions data"

Leverage what you know!
```

### Practice Explaining

```
Best learning technique: Teach someone else (or yourself)

After reading a section:
├─ Close the file
├─ Explain concept out loud (yes, really!)
├─ Use your own words
├─ If you get stuck: That's the knowledge gap, re-read

Example:
"TCP is a protocol that guarantees...
wait, why is it better than UDP again?
Let me think... it's because..."
(If you can't explain, re-read)
```

---

## Checkpoints: Do You Understand?

### After Prerequisites File

You should be able to explain:

```
Operating Systems:
□ What's difference between process and thread?
□ Why virtual memory is bad (10,000x slower)?
□ What's context switching overhead?
□ Blocking vs non-blocking I/O?

Databases:
□ What is ACID? (can explain each letter)
□ Why sharding needed? (trade-offs)
□ How indexing speeds up queries?
□ Difference between row and column storage?

Networking:
□ HTTP request-response flow?
□ How DNS works?
□ TCP vs UDP (when to use each)?
□ How load balancer decides which server?

Storage:
□ Latency: RAM vs SSD vs HDD (relative speeds)?
□ File system operations (sequential vs random)?

Concurrency:
□ Race condition (what is it, why bad)?
□ How mutex (lock) prevents race conditions?

Performance:
□ Little's Law (relationship between throughput, latency, concurrency)?
```

If you can't explain any, re-read that section!

---

### After Core Components File

You should be able to design:

```
□ For 1 billion rows: Which database? Why?
□ For real-time analytics: Which database? Why?
□ For high-frequency reads: Caching strategy?
□ For 100K events/sec: How to process? Queue needed?
□ For 5 million users: Load balancing strategy?
□ For 10TB dataset: Storage solution?
□ For monitoring: What metrics to track?

And for each: Explain the trade-offs!
```

---

## Study Resources While Reading

### Hands-On Practice (Optional but Recommended)

```
While reading, try simple hands-on:

Database:
├─ Install PostgreSQL locally
├─ Create trades table
├─ Try EXPLAIN on queries
└─ See how indexes help

Caching:
├─ Install Redis locally
├─ SET/GET some keys
├─ Try EXPIRE (TTL)
└─ Feel the latency difference

Messaging:
├─ Install Kafka locally (more complex)
├─ Send/receive messages
└─ Understand partitions

Not required, but makes concepts stick!
```

### Discussion (If Possible)

```
If possible, discuss with someone:
├─ Ask them questions from your reading
├─ Explain concepts to them
├─ Defend your design choices
└─ Learn from their perspective

Online communities:
├─ Reddit r/systemdesign
├─ Discord tech communities
├─ System Design Interview Discord servers
└─ (Just read, don't get lost in discussion)
```

---

## After Batch 1: What You've Learned

```
Foundations:
✓ How operating systems work (processes, memory, I/O)
✓ How databases store and retrieve data
✓ How networking and protocols work
✓ Why storage matters (latency, capacity)

Components:
✓ Different database types and when to use each
✓ Caching strategies and invalidation
✓ Message queues for decoupling
✓ Load balancing and API gateways
✓ Monitoring systems

Applied Knowledge:
✓ Can compare different databases objectively
✓ Can design data storage for different scenarios
✓ Understand trade-offs (consistency vs availability, cost vs speed)
✓ Can explain why systems designed certain ways

Ready for:
✓ Batch 2: Low-Level Design and Design Patterns
✓ Batch 3: System Design Interview Approach
```

---

## Common Mistakes to Avoid

```
❌ Trying to memorize everything
   ✅ Focus on understanding concepts

❌ Reading without thinking
   ✅ Pause frequently, ask questions

❌ Skipping sections you find hard
   ✅ Those are the important ones! Re-read them

❌ Not relating to your experience
   ✅ Every concept has parallels in Big Data

❌ Reading too fast
   ✅ Better to deeply understand 30% than shallowly know 100%

❌ Not noting key insights
   ✅ Keep a notebook of "aha!" moments

❌ Waiting for Batch 2 to practice
   ✅ Start thinking about design NOW!
```

---

## Practice Problems (While Reading Batch 1)

### After Prerequisites

```
1. Design a cache for frequently-accessed data
   Question: 1M users, each accesses 5 pieces of data frequently
   └─ Which cache? TTL? Eviction policy?

2. Database selection
   Question: Need to store 100B rows of time-series data
   └─ Which database? Relational or NoSQL? Why?

3. Network problem
   Question: 1M users simultaneous requesting dashboard
   └─ How to distribute requests? Load balancing strategy?
```

### After Core Components

```
1. Complete system design (simplified)
   Question: Design a ride-sharing app (Uber-like)
   └─ What databases? Caching? Message queues?

2. Scaling problem
   Question: Your system getting 10x more load next month
   └─ What breaks first? How to fix?

3. Failure scenario
   Question: Cache goes down
   └─ What happens? How to minimize impact?
```

---

## Summary: Batch 1 Study Plan

```
Week 1:
├─ Days 1-2: Operating Systems
├─ Days 3-4: Database Fundamentals
└─ Day 5: Networking

Week 2:
├─ Days 6-7: Database Deep Dive
├─ Days 8-9: Caching
├─ Days 10-11: Message Queues
├─ Day 12: Load Balancing
├─ Day 13: Storage Systems
└─ Day 14: Monitoring & Review

Total: ~13 hours of focused study
Result: Strong foundation for system design

After Batch 1, you can move to Batch 2: Low-Level Design
```

---

## Questions to Ask Yourself

As you read, ask these questions:

```
1. Why is this component needed?
   └─ What problem does it solve?

2. What are the trade-offs?
   └─ Speed vs consistency? Cost vs availability?

3. When would you use this?
   └─ What are 2-3 use cases?

4. How does it scale?
   └─ Can it handle 1M requests/sec? 1B rows?

5. What happens if it fails?
   └─ Is failure acceptable? How to mitigate?

6. How does this relate to your work?
   └─ Have you used similar concepts in CDM Next?
```

---

## Final Note

**These files are YOUR knowledge base.** You won't find another resource that explains system design fundamentals this comprehensively for non-CS background engineers.

**Read slowly, understand deeply, apply constantly.**

When you're ready, let me know and I'll create **Batch 2**: Low-Level Design, SOLID Principles, Design Patterns, and how to approach system design problems.

**Take your time. Quality over speed. Understanding over memorization.**

You've got this! 💪
