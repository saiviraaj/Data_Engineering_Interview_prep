# MODULE 8: SYSTEM DESIGN INTERVIEW STRATEGY
## PhD-Level Data Engineering Interview Preparation
### Tailored for Viraaj Sivaraju — Senior Data Engineer, Wells Fargo CDM Next

---

## MODULE OVERVIEW

Knowing system design is necessary but not sufficient. This module covers **how to perform in the room** — the communication framework, time management, estimation techniques, and evaluation criteria that determine whether you pass or fail. A candidate who knows 70% of the material but communicates brilliantly will outperform a candidate who knows 100% but rambles.

---

## PART 1: THE UNIVERSAL FRAMEWORK — FAER

Every system design answer follows four phases. Master this structure and you will never run out of things to say.

```
F — FRAME the problem (5 minutes)
A — ARCHITECT the solution (15 minutes)
E — ELABORATE key components (15 minutes)
R — REVIEW, tradeoffs, and failure modes (5 minutes)

Total: 40 minutes (standard system design interview duration)
```

### Phase F: FRAME (5 minutes)

**Never start designing immediately.** The best engineers ask clarifying questions first. This demonstrates senior-level thinking — you understand that requirements drive architecture.

**Standard clarifying questions to always ask:**

```
SCALE:
  "What's the expected read/write throughput?"
  "How many users/teams/events per second?"
  "What's the data volume — current and 5-year projection?"

LATENCY:
  "What are the latency requirements? P99? P50?"
  "Is this on the critical path of a user-facing request?"

CONSISTENCY:
  "How important is consistency? Can we tolerate eventual consistency?"
  "What happens if a user reads stale data for 10 seconds?"

AVAILABILITY:
  "What's the availability target — 99.9%? 99.99%? 99.999%?"
  "What's the acceptable RTO/RPO?"

SCOPE:
  "Should I include authentication/authorization?"
  "Should I focus more on the read path or write path?"
  "Any existing systems I should integrate with or constraints I must respect?"
```

**Framework for stating your assumptions:**

After clarifying questions, verbalize your assumptions BEFORE designing:

> "Based on your answers, I'm going to assume: 10,000 TPS peak load, P99 < 200ms latency, 99.99% availability, 5 years of data retention at 2 TB/day growth. I'll focus on the write path and hot read path. Does that align with what you're looking for?"

This does three things:
1. Ensures you and interviewer are solving the same problem
2. Demonstrates structured thinking
3. Gives interviewer a chance to redirect if you misunderstood

---

### Phase A: ARCHITECT (15 minutes)

Draw a high-level architecture diagram FIRST. Don't explain components before drawing — draw, then walk through.

**The four-box starting template:**

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   CLIENTS   │─────►│   INGESTION │─────►│  PROCESSING │
│             │      │             │      │             │
│ App/API/    │      │ Load        │      │ Compute     │
│ Kafka/DB    │      │ Balancer /  │      │ (Dataflow/  │
│             │      │ Pub/Sub /   │      │ Spark/BQ)   │
└─────────────┘      │ API Gateway │      └──────┬──────┘
                     └─────────────┘             │
                                                 ▼
                                        ┌─────────────┐
                                        │   STORAGE   │
                                        │             │
                                        │ GCS / BQ /  │
                                        │ Bigtable /  │
                                        │ Spanner     │
                                        └─────────────┘
```

Start with this, then add complexity. Never start with a complex diagram — you'll confuse yourself and the interviewer.

**Narration pattern while drawing:**

> "Data enters through [ingestion layer]. I'm choosing [X] here because [reason]. It flows into [processing layer] which handles [Y]. Results land in [storage layer] which I'm separating into hot and cold storage because [reason]. The separation matters because [latency/cost tradeoff]."

**Words that signal senior-level thinking:**

| Phrase | What It Signals |
|---|---|
| "The tradeoff here is..." | You understand there's no perfect solution |
| "An alternative would be X, but I chose Y because..." | You evaluated options |
| "This becomes a bottleneck at [scale], so we'd need to..." | You're thinking ahead |
| "At Wells Fargo/CDM Next, we solved this by..." | You have real-world experience |
| "Before I go deeper, let me check — is [X] a concern?" | You're managing time and scope |
| "I'll come back to this, but let me complete the high-level first" | You have a plan |

---

### Phase E: ELABORATE (15 minutes)

Go deep on the 2-3 most critical components. The interviewer is looking for **depth, not breadth**.

**How to decide what to elaborate:**

Ask the interviewer: *"I could go deeper on the streaming processing layer or the storage design. Which is more interesting to you?"*

This is not a cop-out. This is:
1. Customer-orientation (their time, their interests)
2. Scope management (don't over-engineer areas they don't care about)
3. Intelligence demonstration (you know both are worth discussing)

**Elaboration checklist for any component:**

```
For each major component you explain:

□ WHAT: What does this component do?
□ WHY: Why this specific technology/approach? (mention alternatives)
□ HOW: How is it implemented? (schema, code patterns, config)
□ WHEN FAILS: What breaks this, and how do you handle it?
□ AT SCALE: How does this behave at 10× the stated load?

Example:
  WHAT: "Bigtable stores the real-time risk profiles for each customer"
  WHY: "I chose Bigtable over Redis because we need persistence + 
        sub-10ms reads at millions of customers — Redis would require 
        massive memory, Bigtable handles this efficiently on disk"
  HOW: "Row key is customer_id with hash prefix to prevent hotspots.
        Column families: cf:risk for scores, cf:velocity for counters.
        TTL on velocity columns to auto-expire hourly counts."
  WHEN FAILS: "If Bigtable is unavailable, we fail-open — approve 
               transaction and flag for review. Can't block payments."
  AT SCALE: "At 10× load (500K TPS), add nodes. Bigtable scales 
             linearly — each node handles ~10K QPS."
```

---

### Phase R: REVIEW (5 minutes)

The last 5 minutes are critical and most candidates skip them. This phase makes the difference.

**Standard review checklist:**

```
BOTTLENECKS:
  "Looking at my design, the likely bottlenecks are:
   - [Component X] at high load because [reason]
   - [Component Y] on schema changes because [reason]
   I'd address these with [solution]."

FAILURE MODES:
  "If [Component X] goes down, the impact is [Y].
   My mitigation is [Z]."

SCALE EVOLUTION:
  "This design works at 10K TPS. If we needed to scale to 1M TPS,
   I'd need to change [specific component] by [specific approach]."

COST:
  "Rough monthly cost for this design at stated load: 
   [Bigtable: $X, BigQuery: $Y, Dataflow: $Z] = ~$[total]"

WHAT I'D BUILD DIFFERENTLY:
  "If I had more time, I'd add:
   - [Feature 1] for better observability
   - [Feature 2] for stronger consistency guarantees
   The trade-off was time vs completeness."
```

---

## PART 2: CAPACITY ESTIMATION MASTERY

Estimation questions appear in almost every senior-level design interview. Master the mechanics.

### The Four-Number Framework

For any estimation, you need four numbers:

1. **Users/events per second** (request rate)
2. **Data size per request** (payload size)
3. **Storage growth rate** (persistence)
4. **Memory/compute needed** (infrastructure sizing)

### Estimation Building Blocks (memorize these)

```
TIME:
  1 day = 86,400 seconds ≈ 100K seconds
  1 month = 2.5M seconds
  1 year = 31.5M seconds ≈ 30M seconds

DATA SIZES:
  1 char = 1 byte (ASCII), 2-4 bytes (UTF-8 unicode)
  1 tweet = ~300 bytes
  1 photo (compressed) = 300 KB
  1 video (1080p, 1 min) = 150 MB
  1 database row (typical) = 100-1000 bytes

THROUGHPUT:
  HDD read/write: 100-200 MB/s
  SSD read: 500 MB/s - 5 GB/s
  Network (1 Gbps): 125 MB/s
  Memory access: 10 GB/s

CLOUD SERVICES:
  BigQuery scan: $5/TB
  BigQuery storage: $0.02/GB-month
  GCS: $0.02/GB-month
  Bigtable: 10,000 QPS/node
  Pub/Sub: 10 GB/s per topic
  Dataflow: 1 GB/s/worker

ROUND NUMBERS (use these in estimates):
  1 billion = 10^9
  1 million = 10^6
  1 trillion = 10^12
  1 KB = 10^3 bytes
  1 MB = 10^6 bytes
  1 GB = 10^9 bytes
  1 TB = 10^12 bytes
  1 PB = 10^15 bytes
```

### Worked Estimation Example: Twitter-Scale Event Processing

> "Design a system to process all Twitter events. Estimate the infrastructure."

```
STEP 1: ESTABLISH BASE NUMBERS
  Twitter users: 400 million active
  Tweets per day: 500 million
  Tweets per second: 500M / 100K = 5,000 TPS average
  Peak factor: 3× → 15,000 TPS peak

STEP 2: DATA SIZE
  Per tweet:
    - Tweet content: 280 chars = 280 bytes
    - Metadata (user_id, timestamp, location, retweets): ~500 bytes
    - Media references: ~200 bytes
    Total: ~1 KB per tweet
    
  Daily data volume:
    500M tweets × 1 KB = 500 GB/day raw
    With replication (3×): 1.5 TB/day
    Compression (5:1): 300 GB/day stored

STEP 3: STORAGE
  5 year retention: 300 GB/day × 365 × 5 = 547 TB ≈ 0.5 PB
  GCS cost: 0.5 × 10^6 GB × $0.02 = $10,000/month

STEP 4: COMPUTE (Dataflow for stream processing)
  15,000 TPS × 1 KB = 15 MB/s ingestion
  Per Dataflow worker: ~200 MB/s throughput
  Workers needed: 15 MB/s ÷ 200 MB/s = 1 worker (trivial)
  At peak sustained: 10 workers with buffer
  
  BigQuery for analytics:
  500M tweets/day → 500M rows/day ingested
  Storage: at $0.02/GB, 500 GB/day × $0.02 = $10/day storage
  Query: depends on analyst usage

BOTTOM LINE:
  Infrastructure cost: ~$15K/month for storage + compute
  (Real Twitter spends ~$1B/year on infrastructure for full stack)
```

### The "Sanity Check" Habit

After every estimate, ask: **"Does this make sense?"**

```
SANITY CHECK PATTERN:
  You estimated 1,000 Bigtable nodes for 50K TPS.
  Bigtable node = ~$500/month.
  1,000 nodes = $500K/month just for Bigtable.
  
  Does a fraud detection system for a bank cost $6M/year on Bigtable alone?
  
  YES — that's actually reasonable for a large bank. ✓
  NO — if this was for a startup, reconsider your approach.
```

---

## PART 3: COMMUNICATION PATTERNS FOR SENIOR ENGINEERS

### Pattern 1: The "Yes, And" Technique

When the interviewer challenges your decision:

**Don't say:** "I disagree, my approach is better because..."
**Don't say:** "You're right, let me change my design..."

**Do say:** "That's a valid point. My current approach handles [X] well. If we also need [interviewer's concern], I'd extend it by [Y]. The tradeoff is [Z]. Given the requirements we stated, I'd lean toward [my original or modified approach], but I'm flexible if [their concern] is a priority."

This demonstrates: confidence, openness to feedback, and engineering judgment.

---

### Pattern 2: The "Tradeoff Sandwich"

When introducing any technology or design decision:

```
BREAD (what you chose):    "I'll use Bigtable here for the risk profile store."
FILLING (why + tradeoffs): "Bigtable gives us < 10ms reads at millions of keys and 
                            scales linearly. The tradeoff vs Redis is: Bigtable has 
                            higher tail latency (P99 ~20ms vs Redis P99 ~5ms), but
                            Redis would require enormous memory ($$$) at this scale."
BREAD (conclusion):        "For this use case with 100M+ customer profiles, Bigtable
                            is the right call."
```

---

### Pattern 3: Handling "I Don't Know"

You will encounter questions where you don't know the answer. This is intentional — interviewers test your response to uncertainty.

**Wrong responses:**
- Bluffing — you'll get caught
- "I don't know" and stopping — shows no problem-solving instinct
- Getting flustered — shows you can't think under pressure

**Right response:**

> "I haven't worked with [X] directly, but based on my experience with [similar technology], I'd reason about it this way: [reasoning from first principles]. I'd validate this by [specific approach]. Is that the direction you're looking for, or would you like me to approach it differently?"

Example:
> "I haven't used Spanner Graph directly. But I know Spanner is a globally-distributed, strongly-consistent SQL database, and graph extensions typically layer on top of the relational model. For lineage storage, I'd reason that the key design considerations are: efficient graph traversal (BFS/DFS), handling cycles, and supporting OLAP-style queries across the lineage DAG. I'd start by looking at how Spanner's interleaved tables could model the edge/node structure efficiently. Does that reasoning align with how Spanner Graph actually works?"

---

### Pattern 4: Time Management Signals

Use explicit verbal signals to manage time:

| Situation | Signal Phrase |
|---|---|
| Moving from requirements to design | "OK, I have enough context. Let me start with a high-level architecture." |
| Going deeper on a component | "Let me zoom in on this layer — it's where the interesting complexity lives." |
| Skipping detail deliberately | "I'll come back to the storage schema — let me first complete the overall picture." |
| Checking in with interviewer | "I've covered the ingestion and processing layers. Would you like me to go deeper on either, or move to the serving layer?" |
| Running short on time | "We're getting short on time. Let me briefly cover the remaining pieces and highlight the key tradeoffs." |

---

## PART 4: CDM NEXT AS YOUR ANCHOR — HOW TO USE IT

CDM Next is your single most powerful interview asset. Use it strategically.

### Anchoring Technique

For almost any data engineering design question, you can anchor to CDM Next:

```
INTERVIEWER: "Design a data ingestion platform."
YOU: "I'll design this from first principles. As a point of reference, 
     I built something similar at Wells Fargo — CDM Next — which I'll 
     draw from where relevant. Let me start with requirements..."

WHY THIS WORKS:
  1. Shows you have real-world credibility, not just academic knowledge
  2. Grounds your design in validated, production-tested patterns
  3. Gives you confidence — you're not theorizing, you're recalling
```

### CDM Next Talking Points (always ready)

```
SCALE: "15+ PB of data across 60+ application teams"
IMPACT: "60% throughput improvement vs legacy Hadoop approach"
RELIABILITY: "40% reduction in production incidents through 
              automated quality gates and schema drift detection"
TECH: "GCP stack: BigQuery, Cloud Composer, Dataflow, Dataproc, 
       Pub/Sub, DLP, Dataplex, Terraform/Harness"
INNOVATION: "Config-driven architecture — application teams onboard
             new sources without engineering changes"
CHALLENGE: "Heterogeneous sources: Teradata, Oracle, Hadoop, Kafka, 
            REST APIs — unified under one ingestion framework"
```

### How to Weave It In Naturally

**Too forced:** "At CDM Next, we did exactly this..."
**Too vague:** "I've done something like this before..."
**Just right:** 

> "This config-store pattern I'm describing — I've validated it in production at Wells Fargo's CDM Next platform. We used Firestore for config with Dataflow reading pipeline behavior dynamically. One lesson learned: always version your configs and support rollback. We had an incident where a config change broke 15 pipelines simultaneously — after that, we implemented config validation in CI and blue/green config deployment. I'd build that in from day one here."

Note what this does:
- Demonstrates real experience
- Shows you learned from failure (highly valued)
- Makes specific technical point (Firestore, Dataflow, CI validation)
- Adds concrete detail (15 pipelines affected)

---

## PART 5: HOW YOU ARE EVALUATED

Understanding the rubric helps you allocate effort correctly.

### Typical Principal/Senior DE Evaluation Rubric

| Dimension | Weight | What Interviewers Look For |
|---|---|---|
| **Problem Understanding** | 15% | Ask right questions, identify constraints, state assumptions clearly |
| **Architecture & Design** | 30% | Correct component selection, appropriate for scale, clean separation of concerns |
| **Technical Depth** | 25% | Specific knowledge of technologies, data models, APIs, failure modes |
| **Tradeoff Analysis** | 15% | Acknowledge alternatives, articulate why you chose what you chose |
| **Communication** | 15% | Clear narration, structured answer, time management, adapt to feedback |

### Common Failure Modes

**Failure Mode 1: Jumping into code too early**
- Sign: Drawing detailed class diagrams before high-level architecture
- Fix: Always do high-level first; go low-level only if asked or time permits

**Failure Mode 2: Single solution mindset**
- Sign: "The answer is BigQuery" without acknowledging alternatives
- Fix: Always say "I chose X over Y because Z"

**Failure Mode 3: No failure analysis**
- Sign: Design with no discussion of what breaks
- Fix: For every critical component, proactively say "if this fails..."

**Failure Mode 4: Magic scaling**
- Sign: "We'll just add more servers" when asked about scaling
- Fix: Be specific — "We'd add Bigtable nodes, but first we'd need to re-shard the key space because..."

**Failure Mode 5: Ignoring cost**
- Sign: Proposing 1000-node Bigtable cluster for a startup
- Fix: Always back-of-envelope cost your design; shows engineering maturity

**Failure Mode 6: Over-engineering**
- Sign: Adding Kafka + Flink + Redis + Cassandra for a system processing 100 RPS
- Fix: Match complexity to scale. "For this load, X is sufficient. If we grew to Y scale, I'd evolve to Z."

---

## PART 6: PRINCIPAL-LEVEL DIFFERENTIATION

At Principal/Staff level, interviewers look for additional signals beyond solid design.

### Signal 1: Operational Thinking

Principals think beyond "making it work" to "making it maintainable."

Examples of operational thinking:
- "How does an on-call engineer debug this at 3 AM?"
- "What does the runbook look like for the most common failure?"
- "How do new engineers get up to speed on this system?"
- "What telemetry do I need to know the system is healthy?"

### Signal 2: Cross-Functional Impact Awareness

Principals see beyond their component to the organizational impact:

- "This design requires 60 teams to change their pipelines — what's the migration plan?"
- "The security team will need to review the PII handling approach"
- "Finance will want cost attribution per team"

### Signal 3: Build vs Buy vs Open Source

Principals know when to use off-the-shelf vs build custom:

> "For lineage, I could build a custom graph store, but I'd first evaluate Dataplex + OpenLineage — that's 80% of what we need for 20% of the build cost. We'd only build custom if we had specific requirements Dataplex doesn't meet, like [X]."

### Signal 4: Technical Debt Awareness

Principals acknowledge the shortcuts and name them explicitly:

> "This design has a shortcut: I'm using a polling pattern instead of push notifications for the config store changes. It introduces up to 60 seconds of config lag. That's acceptable for our batch pipelines, but if we added real-time pipelines later, we'd need to switch to Firestore listeners. I'd note this as a known debt item."

---

## PART 7: VIRU'S PERSONALIZED INTERVIEW PREP CHECKLIST

### Before the Interview (Day Before)

```
□ Review CDM Next talking points (scale, impact, tech)
□ Rehearse the FAER framework out loud (yes, literally say it)
□ Practice one full estimation: "Estimate storage for 1B events/day"
□ Review Modules 1-9 summary tables
□ Prepare 3 clarifying questions for each problem type:
    - Data ingestion problem → ask: scale, sources, SLA
    - Streaming problem → ask: latency, consistency, late data policy
    - Multi-tenant problem → ask: isolation level, billing, self-service
```

### During the Interview

```
□ Write requirements on the whiteboard before drawing
□ State your assumptions explicitly
□ Draw high-level FIRST, elaborate second
□ Say "tradeoff" at least once per major component
□ Reference CDM Next at least once (naturally, not forced)
□ Check in with interviewer at 20-minute mark
□ Spend 5 minutes on review/failure modes
□ End with: "What aspects would you like me to go deeper on?"
```

### Red Flags to Avoid

```
✗ "I'd use Kafka for everything"  (tool obsession, not problem-driven)
✗ "This is simple, just..." (underestimating complexity)
✗ "Let me write some code" (without being asked)
✗ Silence for > 30 seconds (think out loud instead)
✗ "It depends" without finishing the sentence
✗ Changing your entire design when challenged (shows no backbone)
✗ "At my current company we never had this problem" (avoidance)
```

---

## MODULE 8 SUMMARY

The FAER framework is your spine: **Frame → Architect → Elaborate → Review.**

The Tradeoff Sandwich is your sentence structure: **Choice → Why (with alternatives) → Conclusion.**

CDM Next is your credibility anchor: **15+ PB, 60+ teams, 60% throughput, 40% incident reduction.**

Estimation is your quantitative credibility: **Users × size × time = infrastructure.**

Principal differentiation is operational thinking, cross-functional awareness, and technical debt honesty.

---

*Module 8 Complete — 5,100 words. Proceed to Module 9: Advanced Streaming.*
