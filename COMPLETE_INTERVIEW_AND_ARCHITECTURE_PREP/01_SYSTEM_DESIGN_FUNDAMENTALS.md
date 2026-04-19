# MODULE 1: System Design Fundamentals & Concepts
## Building the Foundation for Distributed Architecture

---

## Table of Contents
1. [What is System Design?](#what-is-system-design)
2. [Why System Design Matters](#why-matters)
3. [The Role of a System Architect](#architect-role)
4. [Understanding Requirements](#requirements)
5. [Key Theorems & Concepts](#theorems)
6. [Design Evolution](#evolution)
7. [Essential Metrics & Definitions](#metrics)
8. [Common Mistakes](#mistakes)

---

## What is System Design?

### Definition

**System Design** is the process of creating a blueprint for how a software system will be organized, how its components will interact, and how it will meet specific requirements under various constraints.

Unlike coding interviews where you optimize a single algorithm, system design involves:
- **Architectural decisions** (which components to use)
- **Trade-off analysis** (performance vs cost vs complexity)
- **Scalability planning** (10x, 100x, 1000x growth)
- **Fault handling** (what happens when things break)
- **Team organization** (how this gets built and maintained)

### System Design vs Software Design

```
SOFTWARE DESIGN (Tactical)
├─ Classes, functions, modules
├─ Design patterns (Factory, Observer, etc.)
├─ Code organization
├─ Scope: Single application

SYSTEM DESIGN (Strategic)
├─ Services, databases, caches
├─ Distributed patterns
├─ Infrastructure organization
├─ Scope: Multiple services, multiple teams, massive scale
└─ Timeline: Decisions affect company for 5-10 years
```

### Why Not Just Code It?

When building at scale, coding fast isn't enough:

```
Problem: Build a system to handle 1M users

Approach 1: Code fast, optimize later
├─ Month 1: Build working system
├─ Month 2: System collapses at 10K users
├─ Month 3-12: Redesign from scratch
└─ Cost: 11 months, massive technical debt

Approach 2: Design thoughtfully
├─ Week 1: Design for 100M users
├─ Month 1: Implement carefully
├─ Year 1+: Scales smoothly
└─ Cost: 1 week planning, 11 months implementation
```

**Netflix example**: They redesigned from monolith to microservices not because they wanted to, but because monolith couldn't handle scale. They could have saved 2 years by designing for scale initially.

---

## Why System Design Matters

### For Your Career (L7 Perspective)

At Level 7 (Manager/Principal Engineer), you're expected to:

```
L3-L4 (Senior Engineer)
├─ Code fast
├─ Optimize algorithms
└─ Scope: Single module/service

L5-L6 (Staff/Senior Staff)
├─ Design systems for teams
├─ Think about trade-offs
├─ Scope: Multiple services

L7+ (Principal/Distinguished)
├─ Design systems for companies
├─ Make strategic decisions
├─ Mentorship & architecture governance
├─ Scope: Everything
└─ Your decisions affect 1000+ engineers
```

**You're being hired as L7** → Your system design skills matter more than coding skills

### For Accenture Research

Accenture Research values architects who can:

1. **Think at 10,000 ft altitude**
   - See the forest, not just trees
   - Understand how systems interconnect
   - Plan for unknown future changes

2. **Make hard trade-off decisions**
   - Cost vs performance vs complexity
   - Build vs buy vs partner
   - When to optimize vs when to wait

3. **Communicate architecture effectively**
   - To engineers (technical)
   - To managers (business impact)
   - To executives (strategic value)

4. **Lead architecture discussions**
   - Ask right questions
   - Challenge assumptions
   - Bring data to debates

### For Data Engineering Specifically

Data systems are uniquely complex:

```
Web Application Design
├─ Throughput: 10K-100K QPS
├─ Latency: 100ms acceptable
├─ Consistency: Often eventual
└─ Scale: 100s of GB-TB

Data Pipeline Design
├─ Throughput: 1TB-100TB/day
├─ Latency: 1-24 hours acceptable (or <1 second for real-time)
├─ Consistency: Critical (financial data!)
└─ Scale: PB-scale, growing exponentially
```

Your system design skills directly impact:
- **Cost**: A poorly designed pipeline could cost $1M/month in wasted compute
- **Reliability**: Bad design leads to data loss or corruption
- **Performance**: Query latency affects hundreds of teams' productivity
- **Governance**: Architecture determines if you can track data lineage, enforce policies

**Your role at Accenture**: Designing systems that 60+ teams depend on (like CDM Next)

---

## The Role of a System Architect

### What Architects Do

Unlike developers (build features) or managers (plan people), architects:

```
1. UNDERSTAND THE PROBLEM DEEPLY
   ├─ Stakeholder interviews
   ├─ Competitive analysis
   ├─ Technology landscape assessment
   └─ Future trend analysis

2. DESIGN SOLUTIONS
   ├─ High-level architecture
   ├─ Component selection
   ├─ Interface design
   └─ Trade-off analysis

3. GUIDE IMPLEMENTATION
   ├─ Technical standards
   ├─ Code review patterns
   ├─ Dependency management
   └─ Technical debt tracking

4. EVOLVE THE SYSTEM
   ├─ Bottleneck analysis
   ├─ Scaling strategies
   ├─ Technology upgrades
   └─ Organizational scaling
```

### The Architect's Triangle

Every good architect balances three perspectives:

```
        VISION
       /     \
      /       \
  TECHNICAL - BUSINESS
  /             \
 /               \
CONSTRAINTS    REQUIREMENTS
```

**Technical**: "What's technologically possible?"
- Scalability limits
- Integration complexity
- Operational overhead

**Business**: "What makes financial sense?"
- Cost per unit
- Time to market
- Revenue impact
- Strategic value

**Vision**: "Where are we going?"
- 5-year roadmap
- Technology trends
- Organizational growth
- Market positioning

**Bad architects** focus on only one (usually technical):
- "We'll use the coolest technology!" (ignores cost, business value)
- "Whatever's cheapest!" (ignores scalability, maintainability)
- "This matches our 5-year vision!" (ignores immediate reality)

**Good architects** balance all three

### Working with Stakeholders

When designing a system, you need input from:

```
PRODUCT
├─ What features matter most?
├─ What's the 3-month roadmap?
├─ What's the 2-year vision?
└─ How will success be measured?

ENGINEERING
├─ What are the reusable components?
├─ What's the team's expertise?
├─ What's the maintenance burden?
└─ What technical debt can we accept?

OPERATIONS
├─ How will this be deployed?
├─ What's the runbook?
├─ What alerting is needed?
├─ What's the SLA?

FINANCE
├─ What's the budget?
├─ What's the cost per unit?
├─ What's the ROI timeline?
└─ What's acceptable capex/opex ratio?

SECURITY
├─ What compliance is required?
├─ What encryption is needed?
├─ What audit trails?
└─ What attack surface?
```

**Your job**: Synthesize all this into ONE coherent design

---

## Understanding Requirements

### Functional Requirements (WHAT the system does)

Functional requirements describe the features and behaviors:

```
Example: Design a data ingestion platform

FUNCTIONAL REQUIREMENTS:
├─ Must accept data from 50+ source systems
├─ Must support real-time (streaming) AND batch ingestion
├─ Must detect and flag sensitive data (PII)
├─ Must apply encryption to sensitive columns
├─ Must support 50+ file formats
├─ Must route SAR data to separate dataset
└─ Must provide API for team self-service
```

**Note**: Functional requirements usually don't determine architecture (much). Any good architect can implement required features. **Non-functional requirements** are what make architecture hard.

### Non-Functional Requirements (HOW well it must do it)

Non-functional requirements describe quality attributes:

```
SCALABILITY
├─ Must handle 15+ PB of data migrated
├─ Must ingest from 60+ teams simultaneously
└─ Must scale to 1000+ sources by year 3

PERFORMANCE
├─ P50 latency: <30 seconds for files
├─ P99 latency: <2 minutes for large files
├─ Streaming: <5 second end-to-end latency
└─ Query performance: Sub-second for metadata

RELIABILITY
├─ 99.9% uptime SLA (8 hours downtime/year)
├─ Zero data loss tolerance
├─ Automatic failover within 60 seconds
└─ Daily backups, 30-day retention

COST
├─ <$0.05 per GB ingested
├─ <$0.10 per GB stored (after 90 days archival)
└─ No cost overruns if volume 10x

SECURITY
├─ All data encrypted in transit & at rest
├─ Customer isolation (no cross-project data leak)
├─ Audit trail for all access
└─ GDPR/CCPA compliance
```

**These NFRs determine architecture**. Not the features—the constraints.

### How to Extract Requirements

In an interview, the worst thing you can do is start designing without clarifying:

```
WEAK START (No clarification):
Interviewer: "Design a data platform"
You: "We'll use Kafka for streaming, BigQuery for storage, Dataflow for ETL..."
Interviewer: "Why?"
You: "Uh... because that's what works?"

STRONG START (Clarify first):
Interviewer: "Design a data platform"
You: "Before I design, let me clarify the requirements:
     - How much data per day?
     - How many teams will use this?
     - What's the latency requirement?
     - Is real-time important?
     - What's the cost constraint?
     - What about compliance?"
Interviewer: (impressed with your thinking)
```

**This is the #1 sign of a good architect**: Asking questions before designing

---

## Key Theorems & Concepts

### CAP Theorem (The Fundamental Trade-off)

The **CAP Theorem** states that distributed systems can guarantee only **2 of 3** properties:

```
       ┌─────────────┐
       │ CONSISTENCY │
       │ (C)         │
       └──────┬──────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───▼───┐          ┌────▼──┐
│AVAIL- │          │PARTI- │
│ABILITY│          │TION   │
│(A)    │          │TOLER- │
│       │          │ANCE   │
└───────┘          │(P)    │
                   └───────┘
```

#### Consistency
**Definition**: All nodes see the same data at the same time

```
What it means:
├─ Write to node 1: x = 5
└─ Read from node 2: x = 5 (immediately)

Not consistency:
├─ Write to node 1: x = 5
├─ Read from node 2: x = ??? (old value still there)
└─ Wait 100ms
└─ Read from node 2: x = 5 (now it's consistent)
```

**Cost**: Write latency increases (must wait for all replicas)

#### Availability
**Definition**: Every request gets a response (not error or timeout)

```
What it means:
├─ Send request to system
└─ Always get a response (not "please retry")

Not availability:
├─ Send request
└─ Get "service temporarily unavailable"
```

**Cost**: Might return stale data

#### Partition Tolerance
**Definition**: System works even if network partitions (nodes can't talk)

```
What it means:
┌─────────┐         ┌─────────┐
│ Node 1  │ CRASH   │ Node 2  │
│         │◄────────►│         │
│ (can't  │         │(can't   │
│ reach   │         │ reach   │
│ Node 2) │         │ Node 1) │
└─────────┘         └─────────┘

Can your system still function?
```

**Cost**: Must make trade-off between C and A

#### The Three Choices

```
CA (No Partition Tolerance)
├─ Impossible in distributed systems
├─ Network partitions WILL happen
└─ Don't choose this

CP (Consistency + Partition Tolerance)
├─ Example: Google Spanner, PostgreSQL (single-primary)
├─ When network is partitioned: Refuse writes (fail closed)
├─ Upside: Strong consistency
├─ Downside: System goes down if partition occurs
└─ Use when: Consistency more important than availability
   (Financial systems, banking)

AP (Availability + Partition Tolerance)
├─ Example: Cassandra, DynamoDB
├─ When network is partitioned: Accept writes to either side
├─ Upside: Always available
├─ Downside: Data inconsistent until partition heals
└─ Use when: Availability more important than consistency
   (Social media feeds, caches)
```

**For CDM Next**: You chose **CP** implicitly
- BigQuery (strongly consistent)
- But required high availability → Must have replicas
- If partition between quarantine & app project → Fail safe (don't lose data)

### PACELC Theorem (Evolution of CAP)

CAP Theorem is incomplete. It only talks about partitions. What about normal operation?

**PACELC**: "If there's a Partition, choose either Availability or Consistency; Else, choose between Latency or Consistency"

```
PARTITION:
├─ Partition occurs → Choose A or C (CAP)

ELSE (No partition):
├─ Normal operation → Choose L or C
│
├─ Low Latency:
│  ├─ Local writes (no sync to other replicas)
│  ├─ Fast (1-5ms)
│  └─ Might have inconsistency
│
└─ High Consistency:
   ├─ Sync writes (wait for all replicas)
   ├─ Slow (50-200ms)
   └─ Guaranteed consistency
```

**Example**: Database Read Replicas

```
STRONG CONSISTENCY (Slow, L):
├─ Read from primary only
├─ Always latest data
└─ Latency: 50-200ms

EVENTUAL CONSISTENCY (Fast, but C):
├─ Read from replica (load balanced)
├─ Might be stale (1-10 sec old)
└─ Latency: 1-5ms
```

### RTO & RPO (Recovery Concepts)

When disaster strikes, two metrics matter:

```
DISASTER OCCURS
    │
    ├─ System down
    ├─ Customers impacted
    │
    ├─ Time goes on...
    │
    └─ System comes back up
       (RPO = data loss period)
       (RTO = downtime period)

RTO (Recovery Time Objective)
├─ How long is system down?
├─ Measured in minutes/hours
├─ Example: RTO = 1 hour (system back up within 60 min)

RPO (Recovery Point Objective)
├─ How much data can we afford to lose?
├─ Measured in data/time
├─ Example: RPO = 15 minutes (we lose last 15 min of data)
```

**Example Scenarios**:

```
Scenario 1: Daily backups only
├─ RTO: 4 hours (restore from backup, restart)
├─ RPO: 24 hours (lose last day of data!)
└─ Use case: Non-critical systems

Scenario 2: Hourly backups
├─ RTO: 2 hours
├─ RPO: 1 hour
└─ Use case: Important systems

Scenario 3: Real-time replication + automated failover
├─ RTO: 1 minute (auto-failover)
├─ RPO: 1 second (sync replication)
└─ Use case: Critical systems (financial, healthcare)

Scenario 4: Synchronous multi-region replication
├─ RTO: 10 seconds (detect + failover)
├─ RPO: 0 seconds (no data loss ever)
└─ Use case: Most critical systems
└─ Cost: 5-10x more expensive
```

**Your CDM Next design**:
- RTO requirement: How long can data movement be down?
  - Probably: 1-4 hours (non-critical)
- RPO requirement: How much data loss is acceptable?
  - Probably: 1 hour (can rerun jobs)

### Eventual Consistency Explained

Many people don't understand eventual consistency. Let me clarify:

```
SCENARIO: Update customer address

STRONG CONSISTENCY:
  1. Customer updates address to "New York"
  2. Server updates primary database
  3. Waits for replicas to update
  4. Returns "success"
  5. Any read now sees "New York"
  └─ Guarantees: All reads see new value immediately

EVENTUAL CONSISTENCY:
  1. Customer updates address to "New York"
  2. Server updates primary database, returns "success"
  3. Asynchronously updates replicas
  4. For next few seconds:
     ├─ Some reads see "New York"
     ├─ Some reads see old value (old replica)
  5. Eventually (within seconds), all replicas updated
  6. After that, all reads see "New York"
  └─ Trade-off: Fast writes, eventual consistency
```

**When to use**:
- Social media (eventual consistency fine)
- Real-time analytics (eventual consistency fine)
- E-commerce (strong consistency needed)
- Financial systems (strong consistency required)

---

## Design Evolution

Understanding how systems evolve helps you design for the future.

### Generation 1: Monolithic Era

```
┌──────────────────────────┐
│  WEB APPLICATION         │
├──────────────────────────┤
│ ├─ User Service          │
│ ├─ Order Service         │
│ ├─ Payment Service       │
│ ├─ Inventory Service     │
│ ├─ Shipping Service      │
│ └─ Analytics Service     │
└──────────────────────────┘
        ↓
    DATABASE
```

**Characteristics**:
- Single codebase
- One database
- Deploy everything or nothing
- Technology locked (everything in Java, or Python, etc.)

**Why it fails at scale**:
- One team's bug brings down entire system
- Can't scale payment service independently
- Database becomes bottleneck
- Hard to onboard new engineers (massive codebase)

**When to use**: <1M users, <50 engineers, <5 year roadmap

### Generation 2: Microservices Era

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  User    │  │  Order   │  │ Payment  │  │Inventory │
│ Service  │  │ Service  │  │ Service  │  │ Service  │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │
     ├─────────────┼─────────────┼─────────────┤
     │             │             │             │
   USER DB      ORDER DB      PAYMENT DB   INVENTORY DB

  API GATEWAY (routes requests)
```

**Characteristics**:
- Separate codebases per service
- Separate databases per service
- Services call each other via APIs
- Can deploy independently
- Different teams can use different tech stacks

**Why it wins**:
- LinkedIn inversion: Service team can scale independently
- Fault isolation: One service crash doesn't bring down others
- Technology diversity: Payment team uses Go, User team uses Python
- Org scaling: 5 teams can work independently

**When to use**: 1M-100M users, 50-500 engineers

### Generation 3: Data Mesh Era

Monolith and microservices assume centralized data. Data Mesh flips this:

```
DOMAIN 1: Payments        DOMAIN 2: Users
├─ Payment Service        ├─ User Service
├─ Payment Data Lake      ├─ User Data Lake
└─ Payment Lineage        └─ User Lineage
      ↓                         ↓
      └──────┬──────────────┬──────┘
             │              │
      SHARED DATA PLATFORM
      ├─ Governance engine
      ├─ Data catalog
      ├─ Lineage tracker
      └─ Access control
```

**Characteristics**:
- Each business domain owns its own data
- Each domain has its own data warehouse
- Domains share via central platform
- Federation (not centralization)

**Why it wins**:
- Data team ownership mapped to domain teams
- Faster iterations (don't wait for central data team)
- Better data quality (domain team responsible)
- Governance at scale (central platform enforces policies)

**When to use**: 100M+ users, 500+ engineers, 50+ teams producing data

**This is the future** (and partially what CDM Next enables)

### Generation 4: Event-Driven Era

Systems are becoming less "request/response" and more "events flowing":

```
OLD: Request/Response
Service A → Service B → Service C
(synchronous calls)

NEW: Event-Driven
Service A: [publishes: "user_created" event]
Service B: [subscribes, processes, publishes "notification_sent"]
Service C: [subscribes, processes, publishes "loyalty_points_added"]
Service D: [subscribes, updates analytics]

All asynchronous, decoupled, parallelizable
```

**Benefits**:
- Lower coupling
- Better scalability (don't wait for other services)
- Natural audit trail (event log = history)
- Easy to add new subscribers

**CDM Next uses this**: Pub/Sub for real-time events

---

## Essential Metrics & Definitions

### Throughput vs Latency

The two fundamental metrics for any system:

```
THROUGHPUT: How much work per unit time?
├─ Example: 1000 requests per second (RPS)
├─ Example: 100 GB per hour ingestion rate
├─ Measured in: Requests/sec, Bytes/sec, Transactions/sec

LATENCY: How long does single request take?
├─ Example: 100ms average request time
├─ Example: 2 hours to ingest 1 GB file
├─ Measured in: ms, seconds, hours

KEY INSIGHT: These are often inversely related
```

**Example**: Database write

```
Option 1: Batch write (high throughput, high latency)
├─ Batch 10,000 writes
├─ Write all at once
├─ Throughput: 10,000 writes per second
├─ Latency: 1 second (user waits)

Option 2: Single write (low throughput, low latency)
├─ Write immediately
├─ Throughput: 100 writes per second
├─ Latency: 10ms (user happy)

Option 3: Async write (high throughput, low latency)
├─ Queue the write, return immediately
├─ Throughput: 10,000 writes per second
├─ Latency: 10ms (user happy)
└─ Trade-off: Write might fail (user doesn't know)
```

### Percentile Latency (P50, P99, P999)

Average latency is often misleading:

```
AVERAGE (Mean) Latency: 100ms
├─ 1000 requests
├─ 999 requests: 10ms
├─ 1 request: 100,000ms (outlier!)
├─ Average: 100ms
└─ Problem: Doesn't tell you about the outlier

PERCENTILE Latency is better:
├─ P50 (median): 50% of requests faster than this
│  └─ P50 = 15ms (half your users are happy)
├─ P99: 99% of requests faster than this
│  └─ P99 = 50ms (99% of users happy, 1% frustrated)
└─ P999: 99.9% of requests faster than this
   └─ P999 = 100ms (99.9% happy, 0.1% angry)
```

**Why P99 matters**: That 1% of slow requests are often your most important customers (largest data transfer, complex query)

### Availability & Uptime

**Availability** = (Uptime / Total Time) × 100%

```
99% Availability (Two Nines)
├─ Downtime per year: 87.6 hours (3.6 days)
├─ Downtime per month: 7.2 hours
├─ Acceptable for: Non-critical systems

99.9% Availability (Three Nines)
├─ Downtime per year: 8.76 hours (~1 day)
├─ Downtime per month: 43.2 minutes
├─ Acceptable for: Important business systems

99.99% Availability (Four Nines)
├─ Downtime per year: 52 minutes
├─ Downtime per month: 4.3 minutes
├─ Acceptable for: Critical systems (payment, health)

99.999% Availability (Five Nines)
├─ Downtime per year: 5.2 minutes
├─ Downtime per month: 26 seconds
├─ Acceptable for: Life-critical systems
├─ Cost: 5-10x higher than 99.9%
└─ Example: Pacemakers, aircraft controls
```

**Your CDM Next**: Probably targets 99.9% (similar to enterprise data pipelines)

### QPS (Queries Per Second) & Capacity Planning

```
How much traffic can your system handle?

Twitter Example:
├─ 200M active users
├─ Each posts average: 0.1 tweets/day
├─ Peak traffic: 10x average
│
├─ Calculations:
│  ├─ Tweets per day: 200M × 0.1 = 20M
│  ├─ QPS average: 20M / 86,400 = 231 QPS
│  ├─ QPS peak: 231 × 10 = 2,300 QPS
│  └─ Your system must handle 2,300 QPS
│
└─ Capacity Planning:
   ├─ Write database: Must handle 2,300 writes/sec
   ├─ Read replicas: If 10:1 read/write, need 23,000 reads/sec
   └─ Cache: Can absorb 90% of reads, so 2,300/sec misses
```

---

## Common Mistakes in System Design

### Mistake 1: Premature Optimization

**"We need to scale to 100M users on day one"**

```
WRONG: Optimize everything immediately
├─ Use distributed database (Cassandra)
├─ Shard users across 10 databases
├─ Deploy to 5 regions
├─ Add every caching layer
├─ Result: Over-engineered, $500K/month cost, 20 engineers needed

RIGHT: Build for actual scale, optimize as needed
├─ Start simple (single database, single region)
├─ Add monitoring/metrics
├─ When you hit bottleneck, optimize that specific thing
├─ Result: $10K/month, 5 engineers, better code quality
```

**Lesson**: YAGNI = "You Aren't Gonna Need It"

### Mistake 2: Ignoring Operational Complexity

**"This architecture looks cool on paper"**

```
COMPLEX ARCHITECTURE:
├─ Kafka + Spark + Storm + Cassandra + Redis + ElasticSearch
├─ 8 different technologies
├─ 8 different learning curves
├─ 8 different deployment pipelines
├─ 8 different failure modes
│
OPERATIONAL REALITY:
├─ 3am: Something fails
├─ On-call engineer: "Was it Kafka? Spark? Cassandra?"
├─ 2 hours debugging
├─ Still broken
├─ Escalate to data engineer
├─ Solution: Simplify architecture
```

**Lesson**: Operational simplicity is worth 10x in engineer productivity

### Mistake 3: Single Points of Failure (SPOF)

**"One database is simpler"**

```
WRONG:
Application → Database
             (one copy)

If database dies:
├─ All reads fail
├─ All writes fail
├─ Business stops
└─ RTO = 4+ hours
   (restore from backup)

RIGHT:
Application → Primary Database
           ↘ Replica Database 1
             Replica Database 2

If primary dies:
├─ Failover to replica (automatic)
├─ RTO < 1 minute
├─ Reads never interrupted
├─ Writes might be lost (RPO tradeoff)
```

**Never trust one copy** (especially in data systems)

### Mistake 4: Over-engineering for Consistency

**"We need strong consistency everywhere"**

```
REALITY CHECK:
├─ Social media feeds: Don't need consistency
│  (slightly stale data is fine)
│
├─ E-commerce cart: Need consistency
│  (can't sell items that don't exist)
│
├─ Financial system: MUST have consistency
│  (money can't disappear or duplicate)

YOUR CASE (CDM Next):
├─ Data pipelines: Strong consistency important
│  (data quality critical)
└─ But you can accept 1-5 min delays
   (doesn't need to be instant)

MISTAKE:
├─ "Let's use Spanner (strong consistency)"
├─ Cost: 10x more expensive
├─ Complexity: Much harder to operate
└─ Benefit: Not needed (eventual consistency fine)
```

### Mistake 5: Not Measuring Before Optimizing

**"Our query is slow, let's add caching"**

```
WRONG:
├─ Assume query is bottleneck
├─ Add Redis caching
├─ Cost: $2K/month, 2 weeks implementation
├─ Problem: Query was actually fast
│  (bottleneck was network)
└─ Result: Wasted time and money

RIGHT:
├─ Measure where time is spent
│  ├─ Query: 10ms
│  ├─ Network: 500ms
│  ├─ Parsing: 50ms
│  └─ Total: 560ms
│
├─ Optimize the bottleneck (network)
│  ├─ Use compression: 200ms
│  ├─ Use batching: 100ms
│  └─ Total: 160ms (3.5x improvement)
│
└─ Result: 90% cost reduction, better solution
```

**Lesson**: Always measure first

---

## Key Takeaways for Module 1

✅ System design is about **architecture decisions**, not just features  
✅ **Non-functional requirements** drive architecture  
✅ CAP theorem says you choose 2 of 3 (Consistency, Availability, Partition tolerance)  
✅ **Trade-offs are everywhere** (cost vs performance, complexity vs scalability)  
✅ **Operational simplicity** matters more than clever architecture  
✅ **No single point of failure** in production systems  
✅ **Measure before optimizing** (don't guess)  
✅ Design for actual scale, not theoretical scale  

---

## Next Steps

You now understand:
- Why system design matters (especially for L7 roles)
- Core concepts (CAP, RTO/RPO, eventual consistency)
- How systems evolve (monolith → microservices → data mesh)
- Common metrics (throughput, latency, availability)
- Common mistakes to avoid

**In Module 2**, we'll dive into specific components:
- Compute options (VMs, containers, serverless)
- Database options (SQL, NoSQL, data warehouses)
- Messaging systems (Kafka, Pub/Sub)
- Caching strategies
- And how to choose between them

---

**Module 1 Complete**: You've built your foundation. Time to learn the components.
