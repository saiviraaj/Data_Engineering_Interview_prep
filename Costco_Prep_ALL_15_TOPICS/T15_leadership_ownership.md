# Topic 15: Leadership & Ownership
## Costco Sr. Data Engineer — Exhaustive Interview Textbook

---

## Table of Contents
1. [L1: Core Concepts — Role Expectations at Senior Level](#l1-core-concepts)
2. [L2: Deep Technical Understanding — Leadership Frameworks](#l2-deep-technical-understanding)
3. [L3: Real-World Scenarios — Your Stories](#l3-real-world-scenarios)
4. [L4: STAR Story Bank](#l4-star-story-bank)
5. [L5: Common Pitfalls & How to Avoid Them](#l5-common-pitfalls--how-to-avoid-them)
6. [L6: Interview Questions — Easy to Very Hard](#l6-interview-questions)

---

## L1: Core Concepts

### 1.1 What Senior-Level Leadership Means in Data Engineering

At the senior/principal level, technical skill is table stakes. What differentiates senior engineers is their **multiplier effect** — they make the entire team more effective, not just themselves.

**The ladder of impact**:
```
Junior engineer:     Completes assigned tasks well
Mid-level engineer:  Independently owns features/components
Senior engineer:     Drives technical direction, unblocks others, raises quality
Principal engineer:  Shapes platform strategy, influences org-wide decisions
```

**Senior data engineer leadership dimensions**:

| Dimension | What It Looks Like |
|-----------|-------------------|
| **Technical ownership** | You own a system end-to-end: design, build, monitor, improve |
| **Proactive problem-solving** | Identify issues before they become fires; don't wait to be asked |
| **Mentoring** | Raise the floor of your team's capabilities; create leverage |
| **Stakeholder communication** | Translate technical complexity for non-technical audiences |
| **Decision-making** | Make informed trade-off decisions under uncertainty; document them |
| **Cross-functional influence** | Align engineering, analytics, product, and operations |

---

### 1.2 The STAR Framework — Answering Behavioral Questions

**Situation**: What was the context? Set the scene briefly.
**Task**: What was YOUR specific responsibility or challenge?
**Action**: What did YOU specifically do? (Not "we" — focus on your contribution)
**Result**: What was the measurable outcome? Always quantify.

**The most common mistake**: Spending 80% of time on Situation and Task, only 20% on Action and Result. Interviewers want to hear what YOU did and what changed.

**The anti-patterns to avoid**:
- "We did X" → always clarify YOUR specific role
- Vague results: "it went better" → use numbers: "40% reduction in incident rate"
- No learning: always add what you'd do differently
- Negative framing: frame setbacks as learnings, not failures

---

### 1.3 What Costco/Accenture Interviewers Are Actually Testing

For a Research Manager / Senior DE role at an AdTech-focused GCC:

1. **Can you lead without authority?** Drive alignment across teams you don't manage.
2. **Do you have ownership instinct?** Do you go beyond your job description when something is broken?
3. **Can you mentor and grow others?** Will you make your team stronger?
4. **Do you communicate complexity clearly?** Can you brief VP-level stakeholders?
5. **Have you driven architectural decisions?** Not just implemented — proposed and defended.
6. **Do you handle failure well?** Self-aware, learns, improves.

---

## L2: Deep Technical Understanding — Leadership Frameworks

### 2.1 Technical Decision-Making Framework

When making architectural decisions, senior engineers follow a structured process:

```
1. IDENTIFY the decision to be made (not the symptom — the root decision)
   "Should we use Dataflow or Dataproc for the new ingestion pipeline?"

2. GATHER context: requirements, constraints, stakeholder needs
   "Processing 100M events/day, team has Spark expertise, budget is $X"

3. GENERATE options (at least 3 — avoid binary thinking)
   Option A: Dataflow (serverless Beam)
   Option B: Dataproc Spark
   Option C: Hybrid (Dataflow for streaming, Dataproc for batch)

4. EVALUATE trade-offs on each dimension that matters
   | Dimension    | Option A  | Option B  | Option C  |
   | Ops burden   | Low       | Medium    | Medium    |
   | Team skill   | New       | Existing  | Both      |
   | Cost         | Per-job   | Per-hour  | Mixed     |
   | Flexibility  | Medium    | High      | High      |

5. DECIDE with explicit reasoning
   "We chose Option B because our team has 3 years of Spark expertise,
   reducing ramp-up risk. We accept the ops overhead because we already
   have a Dataproc cluster for ML."

6. DOCUMENT the decision (Architecture Decision Record)
   ADR captures: context, options considered, trade-offs, final decision, review date

7. REVISIT at defined intervals
   "We'll re-evaluate in 6 months if we hire Beam-experienced engineers"
```

---

### 2.2 Stakeholder Communication Framework

**The three audiences you'll face**:

| Audience | What They Care About | How to Communicate |
|----------|---------------------|--------------------|
| **Engineers** | Technical correctness, edge cases, implementation | Full technical depth, code examples |
| **Engineering managers** | Timeline, risk, team impact, quality | High-level + key risks + dependencies |
| **Business stakeholders (VP/Director)** | Business impact, cost, timeline, risk | Business metrics only, no jargon |

**The executive communication formula**:
```
[BOTTOM LINE UP FRONT]: What happened / what you recommend (1 sentence)
[IMPACT]: Why this matters to the business (1-2 sentences)
[STATUS]: What's been done / what's happening now (2-3 sentences)
[NEXT STEPS]: What you need / what comes next (1-2 sentences)

Example (production incident communication to VP):
"Our campaign performance pipeline was delayed by 2 hours this morning,
causing the 8 AM marketing dashboard to be unavailable. This affected
20 users and delayed the weekly campaign review by 90 minutes.
The root cause was a schema change in Google Ads' API that broke our
validation layer. We've deployed a fix, all reports are now current,
and we're adding automated schema drift detection to prevent recurrence.
No data was lost and no reports contain incorrect data."

Notice: No mention of Dataflow, Pub/Sub, YAML schemas, or Beam.
The VP cares about: impact, resolution, prevention.
```

---

### 2.3 Mentoring Framework

Effective senior engineers don't give answers — they create learning:

**The GROW model for mentoring conversations**:
```
Goal:     "What are you trying to achieve with this pipeline design?"
Reality:  "What's happening right now? What have you tried?"
Options:  "What are the possible approaches? What are the trade-offs of each?"
Will:     "Which option will you pursue? What will you do by when?"
```

**Practical mentoring actions**:
- **Code reviews**: don't just flag bugs — explain WHY and link to documentation
- **Design reviews**: ask questions instead of giving answers ("What happens if this table has 10 billion rows?")
- **Pair programming**: let the junior drive, you navigate
- **Post-mortems**: create psychological safety — what did WE learn, not who is to blame
- **Stretch assignments**: assign tasks slightly above their current level (with support)

---

### 2.4 Production Incident Management

Senior engineers own incidents. The protocol:

```
DETECTION (T+0):
  - Alert fires (monitoring caught it) OR stakeholder reports
  - Acknowledge alert immediately

TRIAGE (T+5 min):
  - Assess severity: data loss? wrong data? latency? cosmetic?
  - Identify scope: which pipelines, which tables, which users affected?
  - Communicate to affected stakeholders: "We're aware and investigating"

MITIGATION (T+15-30 min):
  - Stop the bleeding: pause pipeline if actively corrupting data
  - Implement temporary fix if available (rollback, manual override)
  - Keep stakeholders updated every 30 min

ROOT CAUSE (T+1-4 hours):
  - Identify WHAT failed, WHY it failed
  - Distinguish symptom from root cause

RESOLUTION (T+4-24 hours):
  - Fix root cause
  - Validate data correctness
  - Communicate all-clear to stakeholders

POST-MORTEM (T+48-72 hours):
  - Written document: timeline, root cause, contributing factors
  - 3-5 action items to prevent recurrence (with owners + due dates)
  - Blameless: focus on systems and processes, not individuals
```

---

## L3: Real-World Scenarios — Your Stories

### 3.1 Map Your CDM Next Experience to Leadership Stories

Your CDM Next platform is a goldmine of leadership stories. Here's how to frame them:

**Story 1: Driving a Technical Direction Decision**

```
Context: CDM Next needed to choose between custom Spark code vs DBT-based transformations
for the 60+ application teams' data pipelines.

Your role: Lead data engineer proposing the architecture

Action:
- Analyzed requirements from 10 teams (surveyed their transformation complexity)
- Built proof-of-concept in both approaches
- Documented trade-offs in an ADR (Architecture Decision Record)
- Presented to engineering leadership with a recommendation
- Addressed pushback from team that had existing Spark expertise
- Negotiated hybrid: DBT for SQL-based transformations, Spark for complex ML features

Result:
- Decision adopted across all 60+ teams
- 40% reduction in pipeline development time (config-driven vs custom code)
- Enabled teams to onboard without dedicated DE support
```

**Story 2: Mentoring a Junior Engineer**

```
Context: New junior DE joined the team, struggled with understanding BigQuery
partitioning and why queries were expensive

Your role: Senior DE, informal mentor

Action:
- Set up weekly 1:1 knowledge-sharing sessions
- Created a "BigQuery cost guide" document explaining partitioning with examples
- Had them write queries, gave detailed code reviews explaining each optimization
- Gradually increased their autonomy: from "fix this" to "design and propose a solution"

Result:
- Within 3 months, junior DE independently wrote optimized BigQuery queries
- They found and fixed a partitioning issue that reduced monthly BigQuery costs by $800
- Became the team's go-to person for BigQuery optimization questions
```

**Story 3: Cross-Team Stakeholder Alignment**

```
Context: CDM Next needed buy-in from 10 application teams to migrate their
pipelines to the new platform. Teams had concerns about reliability and feature parity.

Your role: Technical lead for the migration

Action:
- Conducted 1:1 sessions with each team's lead engineer to understand concerns
- Created a migration FAQ addressing top 15 questions
- Built a pilot with the most skeptical team first (proving reliability early)
- Established a joint Slack channel for real-time support during migration
- Committed to SLA: any migration issue resolved within 2 hours during pilot

Result:
- Pilot team migrated successfully → became an internal advocate
- Remaining 9 teams migrated over 3 months with zero critical incidents
- 15 PB migrated, 99.7% success rate on first attempt
```

**Story 4: Production Incident Ownership**

```
Context: CDM Next pipeline had a data corruption issue — wrong exchange rates
were applied to cost conversions, affecting 30 days of historical ROAS data

Your role: On-call engineer who detected and owned the incident

Action:
- Detected via automated reconciliation check (difference >1% vs source)
- Immediately communicated to 3 stakeholder teams: "Data issue detected,
  do not use ROAS reports for decisions until further notice"
- Traced root cause: exchange rate lookup table was updated mid-month
  but the pipeline's cache wasn't invalidated
- Quantified impact: 30 days × 60 campaigns × $X revenue mis-attributed
- Built fix: invalidate cache + backfill 30 days with corrected exchange rates
- Ran reconciliation again to verify fix
- Post-mortem: added cache invalidation trigger + automated daily reconciliation

Result:
- 4 hours from detection to resolution
- All 30 days of data corrected
- Post-mortem action items: 40% reduction in similar incidents next quarter
```

---

## L4: STAR Story Bank

### Complete Story Templates (Customize with Your Real Details)

#### Story A: "Tell me about a time you took initiative beyond your job description"

**Situation**: While working on Wells Fargo's CDM Next platform, I noticed that application teams were spending 2-3 days writing custom Spark jobs to do the same set of transformations (type casting, column renaming, PII masking) that every other team also needed.

**Task**: My assigned role was to build the ingestion connectors. The transformation framework wasn't in my scope.

**Action**:
1. Gathered data: surveyed 10 teams, found 8 common transformation patterns
2. Built a proof of concept: YAML-config-driven transformation engine (2 weeks, in spare time alongside my regular work)
3. Presented to my tech lead with a measured proposal — here's the build effort (3 weeks), here's the value (saves 2-3 days per team per pipeline)
4. Got buy-in, built the production version with tests and documentation
5. Ran 3 onboarding sessions to train teams on using it

**Result**:
- Adopted by 40+ application teams
- Average pipeline development time reduced from 5 days to 1.5 days
- Enabled non-data-engineers to build pipelines via config files
- The feature became part of CDM Next's core differentiator in internal marketing materials

---

#### Story B: "Tell me about a time you had a technical disagreement with a colleague"

**Situation**: Senior architect proposed using Dataflow (Apache Beam) for all batch transformations in CDM Next. My view was that DBT would be better for the SQL-based transformations that comprised 80% of our workload.

**Task**: Express disagreement constructively and reach the best technical decision for the platform.

**Action**:
1. First, thoroughly understood the architect's reasoning — what concerns led to Dataflow?
   (They wanted a unified streaming+batch framework, and the team knew Beam from prior work)
2. Prepared a structured comparison: I built the same transformation in both Dataflow (Python Beam) and DBT, measured development time, debuggability, and performance
3. Proposed a meeting: "I'd like to share some data I gathered — can I get 30 min?"
4. Presented the comparison objectively — including where Dataflow was superior (streaming, Python UDFs, complex stateful processing)
5. Proposed a hybrid: DBT for SQL-based batch transforms, Dataflow for streaming and Python-heavy transforms

**Result**:
- Hybrid approach was adopted
- We documented the decision criteria (when to use each) so future engineers had a clear guide
- The architect and I built a stronger working relationship — they appreciated that I came with data, not just an opinion

**What I learned**: Disagreements are most productive when you come with evidence, show you understand the other person's valid concerns, and offer a compromise that addresses both needs.

---

#### Story C: "Tell me about a time you failed"

**Situation**: Early in the CDM Next project, I designed a PySpark-based incremental load mechanism that used `MAX(event_timestamp)` as the watermark for processing new data.

**Task**: Build an incremental pipeline for ad click events that processed only new data each run.

**Action**: Built and deployed the pipeline. It worked correctly in dev and the first few weeks in prod.

**The failure**: 
- After a scheduled maintenance window, the pipeline's Airflow DAG was paused for 4 days
- When unpaused, the `MAX(event_timestamp)` watermark was stale by 4 days
- The pipeline processed 4 days of backlog in one run — but the output table had `mode='append'`
- When the backlog run completed and the next normal run started, 4 days of data were processed AGAIN (Airflow's catchup ran each day separately)
- Result: duplicate data for 4 days in the production table

**What I did**:
- Detected via row count anomaly alert (4x normal volume)
- Immediately communicated to stakeholders
- Deduped the table using ROW_NUMBER on the business key
- Rewrote the pipeline to use MERGE (idempotent) instead of APPEND
- Added a test that validates no duplicates exist post-run
- Set Airflow `catchup=False` and `max_active_runs=1` to prevent this class of issue

**Result**: 
- Duplicate issue resolved within 2 hours
- No downstream reports were impacted (caught before business hours)
- The new pipeline has been running for 18 months with zero duplicate incidents
- Wrote an internal "incremental pipeline best practices" guide shared with the team

**What I learned**: Append-only incremental pipelines are inherently fragile. Always use idempotent patterns (MERGE / partition overwrite) for pipelines that can be retried.

---

#### Story D: "Tell me about a time you communicated a complex technical topic to a non-technical audience"

**Situation**: Executive stakeholders at Wells Fargo were skeptical about the CDM Next migration project — they saw it as a 6-month investment with unclear ROI.

**Task**: Present the technical case for CDM Next migration in terms the CFO and VP Engineering could understand and approve.

**Action**:
1. Translated technical benefits into business language:
   - "We're reducing the 35 different custom pipeline implementations to 1 shared platform" → "We're going from 35 teams maintaining separate codebases to one team maintaining one platform — ops savings of $X/year"
   - "15 PB data migration" → "This is the equivalent of digitizing 15 years of Costco's entire transaction history — all available for real-time analysis"
   - "60% throughput improvement" → "Reports that took 8 hours to generate will take 3 hours — daily reporting will be available before market open instead of mid-morning"

2. Used a simple visual: 3-column slide (Current State Pain Points | CDM Next Benefits | Quantified Value)

3. Pre-handled the "what could go wrong" question: showed our risk mitigation plan upfront

4. Let the numbers speak: cost savings of $X vs project cost of $Y → ROI in 14 months

**Result**:
- Budget approved in the first presentation
- Executive sponsor became an advocate, mentioned the project in company-wide all-hands as an example of innovation
- Learned that executives are far more persuadable with ROI analysis than technical architecture diagrams

---

## L5: Common Pitfalls & How to Avoid Them

### 5.1 The "We" Trap

**Problem**: Candidates say "we built" and "we designed" everywhere. Interviewers can't assess YOUR contribution.

**Fix**: Lead with "I", then give credit to the team:
- "I designed the incremental load architecture. I then worked with two junior engineers to implement it, and I led the code reviews."
- "I proposed using DBT for the transformation layer. My tech lead challenged this, so I built a proof of concept to validate the approach before the team adopted it."

---

### 5.2 Underselling Results

**Problem**: "The pipeline worked better after my changes."

**Fix**: Always quantify:
- Latency: "Reduced from 6 hours to 45 minutes (87% improvement)"
- Cost: "Reduced BigQuery costs from $8,000/month to $1,200/month"
- Reliability: "Incident rate dropped from 3/week to 0.2/week (15x improvement)"
- Scale: "15 PB migrated across 60+ application teams over 8 months"
- Team impact: "Framework adopted by 40 teams, eliminated need for custom code"

---

### 5.3 Being Too Technical in Behavioral Interviews

**Problem**: Question is "Tell me about a time you handled a difficult stakeholder." Candidate spends 8 minutes explaining the technical architecture of their pipeline instead of the stakeholder dynamics.

**Fix**: Match the answer to the question. Behavioral questions are about YOUR behaviors (communication, decision-making, conflict resolution), not the technical details. Give just enough technical context for the story to make sense, then spend 70% on your actions and interpersonal navigation.

---

### 5.4 No Self-Awareness in Failure Stories

**Problem**: Failure story that subtly blames others ("The requirements weren't clear"), or minimizes the failure ("It was a minor issue"), or doesn't show learning.

**Fix**: Own it. Show genuine reflection:
- "Looking back, I should have anticipated this edge case during design."
- "I underestimated the complexity of the schema evolution problem — I should have done more research before committing to the approach."
- "What I'd do differently: I'd build a proof of concept with real data before designing the full system."

---

## L6: Interview Questions — Easy to Very Hard

### EASY

**Q1: How do you prioritize your work when you have multiple competing deadlines?**

**Answer**:

I use a three-tier prioritization framework:

1. **Urgency × Impact matrix**: I assess each item on two dimensions — how urgent it is (what breaks if this doesn't get done today?) and what the business impact is. Production incidents or data quality issues affecting executive reports always jump to the top regardless of scheduled work.

2. **Communication over silent juggling**: When I'm genuinely capacity-constrained, I make the trade-off visible. I'll tell my tech lead or stakeholders: "I have X, Y, and Z competing right now. I can deliver X by EOD, Y by tomorrow, and Z needs to slip to next week — or we can reschedule Z if it's higher priority." This prevents surprises.

3. **Protect deep work**: for high-complexity engineering tasks, I block 3-4 hour focus blocks in my calendar and set Slack to DND. Shallow tasks (reviews, quick questions) get batched at the start and end of day.

**Real example from CDM Next**: During the peak migration period, I had three simultaneous demands — a production incident to resolve, a design review to deliver for a new team's onboarding, and a quarterly architecture review presentation. I communicated proactively: resolved the incident first (customer-impacting), delegated the design review to a mid-level engineer I'd mentored (stretch opportunity for them), and rescheduled the presentation by one day. All three outcomes were delivered, and I used the design review delegation as a growth opportunity for the team.

---

### MEDIUM

**Q2: Tell me about a time you mentored a junior engineer. What was your approach and what was the outcome?**

**Answer** (use your real story, adapt this template):

**Situation**: A junior data engineer joined our team fresh from college, technically competent in Python but unfamiliar with production data engineering patterns — distributed systems, BigQuery optimization, idempotent pipelines.

**Task**: I wasn't their formal manager, but as the senior engineer on the team, I took informal ownership of their technical development.

**Action**:
I used a structured approach over 3 months:

*Month 1 — Foundation*: Paired with them on real tasks. I had them write queries first, then I gave detailed code reviews explaining the WHY behind each feedback point. For example, when they wrote `WHERE YEAR(click_date) = 2024`, I didn't just say "change to a range" — I explained how BigQuery's partition pruning works, showed them the cost difference with the query validator, and linked them to our team's BigQuery guide.

*Month 2 — Autonomy with guardrails*: I assigned them an end-to-end task with clear success criteria but let them design the approach. I asked questions rather than giving answers in design reviews: "What happens to this pipeline if the source sends 3x normal volume?" This built problem-solving instinct, not just ability to follow instructions.

*Month 3 — Stretch*: I gave them ownership of a real production feature — a data quality monitoring module for our mart tables. They designed it, implemented it, and presented it to the team.

**Result**: By end of month 3, they were independently designing and deploying pipelines. The DQ monitoring module they built caught a data issue that had been undetected for 2 weeks. They became the team's primary point of contact for monitoring questions — 6 months later they'd effectively taken over that domain. It freed up 4-5 hours of my week that I'd previously spent on monitoring-related questions.

---

**Q3: Describe a time you had to drive a project without formal authority. How did you get alignment across teams?**

**Answer**:

**Situation**: The CDM Next migration required 10 application teams to rewrite their data pipelines using our new framework. My role was technical lead for the platform — I had no authority over those teams, who had their own managers, priorities, and concerns.

**Task**: Get all 10 teams aligned on the migration timeline and approach without being able to mandate anything.

**Action**:

*First: understand their concerns, don't sell*. I started with listening sessions — not "here's why CDM Next is great" but "what concerns do you have about migrating?" I heard: "What if it doesn't support our custom SQL functions?", "We're mid-quarter, we can't break our pipelines," "How do we roll back if something goes wrong?"

*Second: address concerns with evidence*. I built a migration FAQ based on their actual questions. I built a rollback plan. For the custom SQL concern, I worked with two of the most complex teams to validate their use cases worked in the new framework — before asking anyone to migrate.

*Third: social proof*. I identified the most skeptical but influential team and made them the pilot. I gave them VIP support: my personal mobile number, 2-hour SLA for any issue. They succeeded. Their lead engineer then became an internal advocate — "we migrated, it was smooth, here's what to watch out for."

*Fourth: make migration feel low-risk*. I offered dual-run: run old and new pipelines in parallel for 2 weeks, validate outputs match, then cut over. Teams could see the new system worked before decommissioning the old one.

**Result**: All 10 teams migrated within 3 months. Zero critical incidents during migration. Two team leads explicitly mentioned the support model as the reason they felt confident proceeding.

**What I learned**: Cross-functional alignment without authority requires first understanding what people need to feel safe, then systematically removing those barriers. Mandate never works as well as making the right path also the easy path.

---

### HARD

**Q4: Tell me about the most technically complex problem you've solved. Walk me through your approach.**

**(This is your CDM Next architecture story — use it)**

**Answer**:

**Situation**: CDM Next needed to support 60+ application teams with radically different data schemas — some with 50-column flat tables, others with nested JSON with 300+ fields, some with PII requiring column-level masking, others with financial data requiring audit trails. All of this needed to work through a single configuration-driven framework.

**Task**: Design and build the transformation and security layers of CDM Next that could handle this diversity without requiring custom code per team.

**The challenge**: Two opposing forces — teams need flexibility (their schemas are unique) but the platform needs consistency (can't write custom code for 60 teams). How do you design a system that's simultaneously flexible AND consistent?

**My approach**:

*Step 1: Pattern analysis*. I analyzed 15 existing pipelines to find common patterns. Despite the diversity, 80% of transformations fell into 8 categories: rename, type cast, compute derived column, mask PII, filter rows, deduplicate, flatten JSON, union multiple sources. The remaining 20% were truly custom.

*Step 2: Plugin architecture*. I designed a strategy pattern: `TransformationEngine` with pluggable `TransformationPlugin` implementations. Adding a new transformation type = add a new class implementing the interface. No changes to core pipeline code.

*Step 3: Declarative YAML spec*. Transformations are expressed in YAML, not code. `type: mask_pii, columns: [email, phone], method: sha256_hash` — teams describe what they want, the engine handles how.

*Step 4: Escape hatch for the 20%*. For genuinely custom logic, teams can provide a Python file that implements the `TransformationPlugin` interface. Platform loads it dynamically. Custom code is isolated — it can't break other teams' pipelines.

*Step 5: Testing the system itself*. Built a test suite that verified each built-in plugin with edge cases (null handling, encoding issues, type coercion). Any contribution to the plugin library required passing these tests + adding new test cases.

**Technical depth on the security layer**:
- Column masking: intercepted at the Spark DataFrame level before any write
- DLP integration: Cloud DLP scanned new columns in source schemas to auto-detect PII
- Audit trail: every transformation logged (which column was masked, by which pipeline, at what time) to BigQuery for compliance

**Result**:
- 60+ teams onboarded
- 15 PB migrated
- Average pipeline development: 5 days → 1.5 days
- Zero security incidents related to PII exposure
- Platform now handles 40% more throughput than the system it replaced (60% improvement metric from your resume)

---

### VERY HARD

**Q5: "Describe a situation where you had to make a major architectural decision with incomplete information and significant risk. What was your decision process, and in hindsight, what would you do differently?"**

**What they're testing**: Mature decision-making, comfort with uncertainty, genuine self-reflection, senior-level thinking.

**Answer**:

**Situation**: Early in CDM Next's design, we had to decide: should the platform use a pull-based model (teams configure their sources, platform fetches data) or a push-based model (teams send data to the platform's Pub/Sub topics)? This was a fundamental architectural choice — reverting later would require rearchitecting 60+ pipelines.

We had incomplete information: we'd only done detailed requirements gathering with 5 of the 60 teams. We didn't know how many teams had event-driven sources vs batch files. We had a 3-week deadline for the architecture decision before development would begin.

**My decision process**:

*What I knew*: 4 of the 5 surveyed teams had batch file sources (GCS exports, database dumps). 1 had real-time events. Pull-based models are simpler to implement and audit — the platform controls all data access.

*What I didn't know*: The other 55 teams' source patterns. If many were event-driven, a pull-based model would require building a fake polling layer on top of event sources — inefficient.

*Risk assessment*: Pull-based was the safe choice for the majority pattern. Push-based was optimal for event sources but had more complex security (teams need to send directly to your topics — auth, schema validation at the edge).

*Decision*: I chose pull-based with an event-stream adapter as an optional plugin. The adapter let event-driven sources simulate pull by subscribing to a Pub/Sub topic and writing to GCS, which the pull pipeline then read. This was slightly inefficient for event sources but avoided building two fundamentally different architectures.

*How I validated with incomplete data*: Did a rapid 2-day survey of all 60 team leads with a simple 3-question form. 48 of 60 responded: 40 were batch file based, 8 were event-driven. Pull-based with adapter was validated as the right choice for this distribution.

**Result**: Architecture was stable across all 60 teams. The adapter for event-driven sources worked but added ~15 minutes of latency. For the 8 event-driven teams with strict latency requirements, we later built a native Pub/Sub ingestion path as a second option.

**In hindsight, what I'd do differently**: 

I'd have done the rapid survey BEFORE the architecture review rather than concurrently. I spent 3 days defending an architectural choice I wasn't fully confident in because I didn't have the data. A 2-day survey before the review would have given me solid ground. The lesson: for high-stakes decisions, the most valuable investment is gathering just enough data to significantly reduce uncertainty — it doesn't have to be perfect data. In this case, 2 days of surveys would have saved 3 days of architectural debate.

---

## Summary: Leadership & Ownership — Senior Mastery Checklist

| Skill | What Senior Looks Like |
|-------|------------------------|
| STAR framework | Action-focused (70%), quantified results, clear personal contribution |
| Initiative | Has "beyond job description" stories with measurable impact |
| Mentoring | Specific approach (GROW model), measurable junior growth |
| Cross-functional | Alignment without authority; listens first, removes barriers |
| Stakeholder comms | Translates tech to business impact; no jargon with executives |
| Decision-making | Structured framework, documents trade-offs, revisits decisions |
| Incident ownership | Full lifecycle: detect → communicate → mitigate → RCA → prevent |
| Failure stories | Genuinely owns it, specific learning, changed behavior afterward |
| Technical influence | Proposed and defended architectural decisions, not just implemented |
| Self-awareness | Can articulate growth areas; learning mindset throughout career |
