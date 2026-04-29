# Costco Round 3 — Complete Preparation
## Techno-Managerial Interview | Tomorrow's Round
## Role-Specific Answers Using Your CDM Next Experience

---

# WHAT TO EXPECT IN ROUND 3

```
WHO WILL INTERVIEW YOU:
  Likely: Engineering Manager OR Director of Data Engineering
  Possibly: VP of Data/Analytics OR Cross-functional (Product, Analytics)
  
  These are senior leaders. They've seen many candidates.
  They can tell in 10 minutes if you're prepared or improvising.

WHAT THEY ARE EVALUATING:
  Technical judgment:   Can you make sound architecture decisions?
  Leadership:           Have you led, not just contributed?
  Business thinking:    Do you understand WHY the data matters (not just HOW)?
  Cultural fit:         Will you thrive and grow in how Costco works?
  Ambition:             Are you here for a job or a career?

TONE OF THE ROUND:
  Less "prove you can code" — they trust Round 1 result
  More "tell me about decisions you've made and why"
  More "how would you handle [specific situation]"
  More "what would you do in your first 90 days here"

YOUR MINDSET GOING IN:
  You are not auditioning for a job.
  You are having a peer conversation about technical leadership.
  You have 11 years of real experience to draw from.
  You have cleared 2 hard rounds already — they WANT you to succeed.
  Your job: be specific, be honest, show judgment.
```

---

# PART 1: YOUR COMPLETE STORY — POLISHED FOR COSTCO

## The Opening (90 seconds — memorize this)

*"I'm a Senior Data Engineer with 11 years of experience, and my specialty is building data platforms that serve many teams from a single well-governed infrastructure — rather than everyone building their own pipelines in silos.*

*My most recent work at Wells Fargo was leading the architecture and delivery of CDM Next — a config-driven cloud data movement platform that migrated 15 petabytes of data across 60-plus application teams from Hadoop to GCP. We reduced pipeline development time from 5 days to 1.5 days, cut production incidents by 40%, and delivered 60-plus percent throughput improvement over legacy infrastructure. What I'm most proud of is that it was fully config-driven — teams described their pipeline in YAML and the platform generated the code, quality checks, and orchestration. That's the kind of platform thinking I want to bring here.*

*Over the last few years I've consciously expanded from pure individual contribution into technical leadership — owning architecture decisions, mentoring junior engineers, aligning cross-functional teams, and presenting to senior leadership. I've found my highest leverage is no longer writing the best code — it's making the team around me 10x more capable.*

*I'm drawn to Costco's MarTech engineering specifically because the problem is genuinely complex — real-time attribution across multi-channel, identity resolution, the shift from third-party to first-party data, all in a high-scale AdTech environment. That's not a commodity data engineering problem. That's a platform problem that requires deep technical leadership."*

---

## Your 5 Core STAR Stories — Ready for Any Question

### Story 1: The CDM Next Architecture Decision
*Use for: "Walk me through a hard technical decision" / "How do you handle trade-offs" / "System design thinking"*

**Situation**: Wells Fargo needed to migrate 15PB of data from Hadoop to GCP for 60+ application teams, each with different schemas, SLAs, and source systems.

**Task**: Design the core platform architecture before development began. The foundational decision: code-driven (each team writes their own Spark jobs using platform libraries) vs config-driven (teams declare what they want in YAML, platform generates the code).

**Action**: *"I evaluated both options on five dimensions: correctness, scalability, operability, reversibility, and team fit. Code-driven failed the scale dimension — at 60 teams, supporting 60 different codebases is unsustainable. Config-driven failed the transparency dimension initially — teams couldn't debug what the platform was doing. I chose config-driven but added a dry-run mode showing generated SQL, a validation layer catching errors before submission, and a plugin escape hatch for the 20% of genuinely custom logic. I documented the decision in an ADR with explicit review triggers."*

**Result**: 60+ teams onboarded. Pipeline dev time 5 days → 1.5 days. 15PB migrated. Config spec is still the production standard today.

**Principle**: "The right architecture for scale is not the one that's most powerful — it's the one that makes complexity invisible to its users while remaining transparent when things go wrong."

---

### Story 2: Influencing Without Authority
*Use for: "Tell me about driving change across teams you didn't control" / "How do you align stakeholders"*

**Situation**: 10 application teams needed to migrate to CDM Next. I had zero authority over any of them. Several were actively skeptical.

**Task**: Get all 10 to migrate voluntarily within 3 months.

**Action**: *"I ran listening sessions — not presentations — to understand their specific concerns. Three themes emerged: reliability, rollback capability, feature parity. I built all three before asking anyone to migrate. Then I chose the most skeptical team for the pilot and gave them concierge support — my direct contact, 2-hour SLA on any issue. When they succeeded publicly, their tech lead became an advocate on our shared Slack channels. The remaining 9 teams needed much less convincing from me — their peer had already done it."*

**Result**: All 10 teams migrated. Zero critical incidents during migration. 9 months ahead of the original estimate.

**Principle**: "The fastest way to change minds is not persuasion — it's demonstrated success by someone the skeptics trust."

---

### Story 3: Production Incident — Ownership Under Pressure
*Use for: "Tell me about a time you dealt with a production failure" / "Ownership when things go wrong"*

**Situation**: My pipeline design flaw caused 4x duplicate rows in a production analytics table — a critical table used for marketing decisions.

**Task**: Detect, communicate, remediate, and prevent recurrence — all in one day.

**Action**: *"The moment I detected it via our row-count anomaly alert at 7 AM, my first action was stakeholder communication — not code. I sent: 'Data issue detected, do not use these tables for decisions, update in 30 minutes.' Then I isolated root cause: stale watermark after a 4-day Airflow pause causing catchup runs to double-process data. I quantified impact — 30 days of affected data — ran the corrective SQL on staging first, validated against 5 manual calculations, then ran on production. By 10:30 AM: all data corrected, stakeholders notified, prevention measures in place: MERGE instead of APPEND, catchup=False in Airflow, max_active_runs=1."*

**Result**: Fully resolved in 3.5 hours. Root cause documented in post-mortem. Pattern became a team-wide standard. That class of bug never recurred.

**Principle**: "In incidents, communicating to stakeholders early is as important as fixing the problem. Stakeholders who hear from you first — not through a broken dashboard — never lose trust in the platform."

---

### Story 4: Mentoring — Growing an Engineer
*Use for: "Describe your mentoring approach" / "How do you develop others" / "Leadership beyond technical contribution"*

**Situation**: Junior engineer joined the team — technically sharp but no production data engineering experience. Writing queries that worked in dev but caused expensive full scans in production.

**Task**: Move them from "writes code that works" to "writes code that works at production scale reliably."

**Action**: *"I deliberately didn't give them answers. I used a question-then-show method. When they wrote a query with YEAR(click_date) = 2024, I ran both versions in the Query Validator and showed them 15TB scanned vs 2GB scanned. Then I asked: 'Why do you think there's a 700x difference?' Let them reason through it. After 6 weeks of this approach, I gave them a stretch assignment: own the data quality monitoring module end-to-end. Design, build, present to the team. They did it. It caught a data issue within its first week that had been undetected for two weeks."*

**Result**: 3 months later, other engineers were going to them with BigQuery optimization questions. My mentoring capacity reduced because they no longer needed me for day-to-day technical guidance — which was the goal.

**Principle**: "The fastest way to develop someone is not to give them answers — it's to build the habit of asking themselves the right questions. A good mentor makes themselves unnecessary."

---

### Story 5: Technical Disagreement — Backbone + Data
*Use for: "Tell me about disagreeing with a senior technical decision" / "Handling conflict" / "Courage"*

**Situation**: A senior architect proposed using Apache Beam/Dataflow for all transformations — both streaming and batch SQL. I believed DBT was better for the 80% SQL workload.

**Task**: Make the case without damaging the relationship or being overruled.

**Action**: *"First, I genuinely explored his concern — not to find a counterargument, but because he might be right. His worry: team expertise was in Beam, and he wanted one framework not two. Both valid. I then built a proof of concept — same transformation in both Beam and DBT. Measured: dev time (DBT: 2 hours, Beam: 6 hours), debuggability (DBT shows compiled SQL I can run manually; Beam errors are in job logs), team ramp-up (10 new engineers need Beam training; all know SQL). I requested a 30-minute meeting and proposed a hybrid: DBT for SQL batch, Dataflow for streaming and Python-heavy transforms. I acknowledged the Beam advantages. The hybrid addressed his 'one framework' concern because we kept Dataflow — just used it for the right workloads."*

**Result**: Hybrid approach adopted. Decision documented in ADR. The relationship improved because I came with evidence and a solution, not just a complaint.

**Principle**: "Disagreement that leads to a better decision is a gift. The key is coming with data and alternatives — not just 'I don't like this.'"

---

# PART 2: COSTCO-SPECIFIC QUESTIONS AND ANSWERS

### "What would you do in your first 90 days at Costco?"

```
ANSWER:

"I'd divide it into three phases.

MONTH 1: UNDERSTAND, DON'T CHANGE.
I'd spend the first month listening — not fixing. I'd run 1:1s with every 
engineer on the team, every key stakeholder (PM, analytics, campaign managers), 
and understand the current architecture end-to-end. Not from documentation, 
but by reading the actual pipelines, querying the actual tables, tracing 
an actual click event from Pub/Sub through Dataflow to BigQuery.

My specific questions: What's working well that I should protect? What's the 
biggest pain point engineers face daily? What are the 3 most common data 
quality issues stakeholders complain about? Where does the team spend the 
most time on rework?

I would NOT make any architecture proposals in month 1. No 'at my old company 
we did it this way.' No changes to established processes. Context first.

MONTH 2: ONE MEANINGFUL IMPROVEMENT.
Based on what I learned, I'd pick one concrete problem and fix it.
Not the biggest problem — the one where the effort-to-impact ratio is best.

In every team I've joined, there's always something that's been slightly 
broken for months and nobody fixed it because it wasn't critical but it 
annoyed everyone. Finding and fixing that builds credibility fast.

I'd also use this month to identify where the biggest leverage points are 
technically — is it the identity graph that needs work? Is it attribution 
accuracy? Is it pipeline reliability? That becomes my longer-term roadmap input.

MONTH 3: PROPOSE DIRECTION.
With enough context, I'd present my view of the technical roadmap: where 
I think we should invest, what problems I'd prioritize, and why. Not as 
a monologue — as a working document I share with the team and manager 
first, then refine based on feedback.

The specific technical area I'd focus on at Costco: given the conversation 
in Round 2 about clickstream analytics and identity resolution, I'd bet 
the highest leverage opportunity is the attribution layer — making sure 
that cross-device, cross-session attribution is accurate, because everything 
downstream (ROAS, campaign optimization, budget allocation) depends on it 
being right."
```

---

### "How would you handle a situation where the engineering team and product team have conflicting priorities?"

```
ANSWER:

"First, I'd separate the conflict into two types, because they need 
different responses.

TYPE 1: PRIORITY CONFLICT (both are valid, there's just not enough capacity)
This is the most common type. Engineering wants to pay down tech debt; 
product wants new features. Both are legitimate.

My approach: make the trade-off visible and explicit, then let the 
right people decide. I'd quantify both options:
'If we build Feature X: it ships in 3 weeks and enables campaign managers 
to do Y, which impacts revenue Z.'
'If we fix the reliability issue first: we prevent ~4 hours of data downtime 
per month, which currently costs analysts ~8 hours of rework per incident.'

That gives product and engineering leadership the information to make 
the call. I don't make it unilaterally. I make sure it's made explicitly 
rather than by default.

TYPE 2: ALIGNMENT CONFLICT (we disagree on what the right solution is)
Engineering says: 'This will take 6 weeks properly done.'
Product says: 'We need it in 2 weeks.'

Here I'd want to understand the real constraint on both sides:
Why 2 weeks for product? (External deadline? Other dependencies? 
Or just impatience?) What does 'properly done' mean for engineering? 
(What's the minimum viable version that's still correct?)

Often the gap is smaller than it appears once you get specific.
'The full feature takes 6 weeks, but the MVP that covers 80% of the use 
case takes 2 weeks. Would that work for the business?' 

And if it genuinely can't be compressed: I'd explain the risk clearly — 
'If we ship this in 2 weeks, the risks are X and Y. We can mitigate X 
with Z, but Y is a real risk. The decision to accept that risk is yours, 
not mine.' I give decision-makers the information they need, not the 
decision I think they should make."
```

---

### "Costco has a reputation for being methodical and conservative. How do you balance moving fast with doing it right?"

```
ANSWER:

"I actually think the 'fast vs right' framing is a false dichotomy 
in most cases. In my experience, the things that make you go slow 
are usually: unclear requirements, rework from skipped quality steps, 
and incidents that consume engineering time. Fix those and you go fast.

The real question is: where is the cost of being wrong?

For Costco's financial and membership data: being wrong has real cost —
wrong ROAS calculation misdirects ad spend, wrong attribution breaks 
budget planning. Here, I'd invest heavily in correctness upfront.

For new analytics features or exploratory dashboards: being wrong is cheap.
An imperfect dashboard that you learn from is better than a perfect 
specification that takes 3 months to validate.

My approach in practice: distinguish what needs to be highly reliable 
from day one (the data infrastructure, the identity graph, the attribution 
engine) vs what can be iterated (the specific metrics on a dashboard, 
the ML features for segmentation).

One concrete thing I'd do: propose a tiered SLA for data pipelines.
Tier 1 (critical, drives financial decisions): 99.9% uptime, 15-min 
alerting, manual runbooks.
Tier 2 (analytics, drives optimization decisions): best effort, daily 
freshness.
Tier 3 (experimental, exploration): no SLA guarantee, documented as such.

This lets us move fast on tier 3 and tier 2 without contaminating tier 1."
```

---

### "Tell me about a time you had to make a decision without complete information."

*Covered in File 1 with the CDM Next pull vs push architecture story. Here's an additional Costco-specific version:*

```
ANSWER:

"In CDM Next, we had to choose between Dataflow and Spark on Dataproc 
for our primary batch transformation engine before we had load-tested 
either at our target scale of 15PB.

I had performance data from published benchmarks (directional, not 
specific to our workload), team familiarity surveys (Spark was known, 
Dataflow less so), and a cost model based on GCP published pricing.

I ran a structured evaluation with what I had:
- 2-week spike: both teams built the SAME transformation in both engines
- I measured: development time, debugging experience, cost at projected volume
- The Dataflow version took 30% longer to build but was 40% cheaper at scale

I made the call: Dataflow, with a documented review trigger:
'If actual throughput at 100B rows/day is >20% off our model, we reassess.'

I also had a mitigation: the Beam API runs on both Dataflow and Spark.
If we needed to switch runners, the core processing code wouldn't change.
That reversibility gave me more confidence to commit.

Principle: for irreversible decisions with incomplete information, 
find ways to reduce the irreversibility. The ability to switch Beam 
runners made this a much lower-stakes choice than it appeared."
```

---

### "What would you change about how data engineering teams are typically run?"

```
ANSWER:

"Three things I'd change based on what I've seen go wrong at scale.

First: data quality as a first-class citizen, not an afterthought.
Most teams treat data quality testing as something you add after the 
pipeline is 'done.' I'd flip that. Data quality tests are part of the 
definition of done. A pipeline that loads data but doesn't validate 
it is an incomplete pipeline. This requires shifting the cultural 
expectation: 'working' means the data is correct, not just that the 
job didn't fail.

Second: treat pipelines as products with real SLAs, not as scripts 
that 'should run.'
Every production pipeline should have: a documented expected output 
(row count range, freshness SLA), an alert if it violates that SLA, 
and a runbook for the most common failure modes. Engineers shouldn't 
have to diagnose from scratch every time a pipeline misbehaves. 
The runbook should answer: what's the most likely cause given 
symptom X, what's the fix, who do you call.

Third: make technical decisions visible and permanent.
The biggest source of rework I've seen is architecture decisions 
that were made verbally, never documented, and then relitigated 
six months later by someone who wasn't in the room. 
ADRs — Architecture Decision Records — take 15 minutes to write 
and save hours of future confusion. I'd make them mandatory 
for any decision that would be painful to reverse."
```

---

# PART 3: TRICKY QUESTIONS WITH DIRECT ANSWERS

### Questions Designed to Catch You Off Guard

**"What would your previous team say is your biggest weakness as a leader?"**

*"Two things I've heard consistently: I sometimes invest too much time understanding a problem before proposing a solution — which reads as indecision to stakeholders who need faster direction. And I underinvested in real-time documentation during build phases — I had the context in my head and didn't write it down until after the build was complete. Both are real. I've addressed the first by setting explicit decision timelines with myself and communicating intermediate positions even before I'm fully confident. I've addressed the second by writing a 3-sentence architecture note at the moment of each decision — it takes 5 minutes and prevents hours of confusion for the next engineer."*

---

**"We're looking for someone who can both code and lead. Most engineers are better at one than the other. Which one are you better at?"**

*"Honest answer: I'm stronger technically than I am as a people leader, because I have 11 years of technical practice and 3 years of formal leadership experience. My technical judgment is well-calibrated. My leadership edge cases — like managing a persistent underperformer or navigating a political budget conflict — I've navigated but I'm still developing nuance in. What I'd say is: I'm already performing at the bar this role requires technically, and I'm on a deliberate growth trajectory for leadership. The question for me is whether there's enough room here to develop the leadership muscles I'm building."*

---

**"What would you do if a product manager kept changing requirements mid-sprint?"**

*"I'd start by understanding why the requirements keep changing. Requirements churn is usually a symptom, not the root cause. Sometimes it's because the PM is getting new information from users or leadership that genuinely changes priorities — that's actually correct behavior. Sometimes it's because requirements were never properly specified before the sprint began — that's a process failure. Sometimes it's because the PM doesn't trust the team to execute and micro-manages through requirements. Each needs a different response. If it's a process failure: I'd propose a working agreement — a 48-hour requirements freeze before sprint start. If it's a trust issue: I'd address it directly with the PM: 'I've noticed requirements often change mid-sprint. What would make you confident enough to let us execute for the full sprint?' I'd never treat a PM as the adversary — they have information I don't. But I'd protect engineering capacity from churn that comes from a broken process."*

---

**"How do you handle stakeholders who don't understand data quality issues and just want the data now?"**

*"I translate. Stakeholders saying 'I need the data now' are not wrong — they have a business need that's real. The problem is they don't have enough information to understand the risk. So I give them that information in business terms, not technical terms. Not: 'The pipeline has a watermark lag causing event-time skew in the 5-minute aggregation windows.' But: 'If you use today's ROAS numbers right now, they might show Campaign A at 3.2x when the actual number is 2.8x — that's a 14% overestimate. If you're about to increase Campaign A's budget by $50K based on that 3.2x, you'd be making a $7K mistake.' When they understand the business cost of acting on incorrect data, they almost always agree to wait for the corrected version. The ones who still want it immediately — they've decided the cost of waiting exceeds the cost of the potential error. That's their call to make, not mine. I just make sure they're making it with full information, and I document that they made the call."*

---

**"Tell me something you know about data engineering that most people don't."**

*"The hardest problems in data engineering are never the ones that are technically challenging — they're the ones that sit at the boundary between technical and organizational. The hardest problem I've faced wasn't building a real-time streaming pipeline or designing a distributed identity graph. It was convincing 60 teams — each with their own technical culture, their own manager, and their own reasons to be skeptical — to trust a new platform with their production data. No algorithm solves that. What solves it is demonstrating respect for their concerns, building what they actually need (not what you think they need), and finding your champion. Most data engineering content treats this as a postscript. In my experience, it's the critical path."*

---

# PART 4: NIGHT-BEFORE PREPARATION

## What to Review, What to Release

```
REVIEW (30 minutes):
  □ The 90-second opening — say it out loud 3 times
  □ Your 5 STAR stories — just the headlines, not the full text
  □ 3 questions to ask the interviewer
  □ The one-page "Why Costco" narrative

RELEASE (don't try to memorize):
  □ Every possible question and answer
  □ Perfect wording for every sentence
  □ Being completely "ready" — you never are, and trying makes you robotic

MINDSET CHECK:
  You have cleared Round 1 (SQL, Python, BigQuery) ✓
  You have cleared Round 2 (System design — clickstream, identity) ✓
  They WANT you to succeed in Round 3
  
  You are not performing for them.
  You are having a conversation with a peer about technical leadership.
  You have 11 years of real experience to draw from.
  You are not making things up — you are describing reality.

IF YOU GET A QUESTION YOU DON'T HAVE A GREAT ANSWER FOR:
  "I haven't dealt with that specific scenario directly. But my approach 
   would be [your reasoning]. Is that directionally aligned with how 
   your team handles it, or is there something specific I should know 
   about the context here?"
  
  This is a completely acceptable answer at senior level.
  Leaders who claim to have experience in everything are lying.
  Leaders who say "I haven't done this but here's how I'd approach it"
  demonstrate judgment and intellectual honesty.
  
  Both of those are things good leaders have.
```

## Questions to Ask Tomorrow

```
PICK 2-3 FROM THIS LIST:

ON THE ROLE:
  "What does success look like for this role at 6 months? And at 2 years?"
  "What's the biggest technical challenge the data team is working through 
   right now that I'd be expected to contribute to immediately?"

ON THE TEAM:
  "How does the data engineering team collaborate with campaign managers 
   and media buyers? Is there a regular feedback loop?"
  "What does the growth path look like from this role — are there people 
   who've moved from here into lead or architect positions?"

ON TECHNOLOGY DIRECTION:
  "How is the team thinking about the shift from third-party cookies to 
   first-party identity — is that an active initiative right now?"
  "Is the current stack GCP-native end-to-end, or are there components 
   on other clouds I should be aware of?"

ON CULTURE:
  "What separates the engineers who have the most impact here from those 
   who are technically excellent but less influential?"
  "What's the engineering culture around technical decision-making — 
   is there a formal RFC or ADR process, or more discussion-based?"

ON THEM PERSONALLY:
  "What's been the most interesting technical problem you've worked on 
   here in the last year?"
  "What made you choose Costco as the place to do this work?"
```

---

# CLOSING: YOUR UNIQUE ANGLE FOR TOMORROW

```
WHAT MAKES YOU DIFFERENT FROM OTHER CANDIDATES:

Most senior data engineering candidates can:
  → Write good SQL and Python ✓
  → Design a streaming pipeline architecture ✓
  → Talk about BigQuery optimization ✓

Very few candidates can:
  → Show they led a 15PB, 60-team platform migration (not just contributed)
  → Speak about config-driven platform thinking vs point-solution pipelines
  → Connect technical identity resolution to actual MarTech business outcomes
  → Articulate what it means to move from IC to technical leader and WHY

THAT IS YOUR DIFFERENTIATION.

You are not "a good data engineer."
You are someone who has operated at the intersection of technical architecture, 
organizational influence, and business impact.

Make that clear tomorrow.
Own it.

You've done the work.
Now go describe it honestly.
```
