# Technical Leadership — Complete Guide
## For Senior / Staff / Principal Data Engineers
## Costco Round 3 Prep + Future Manager Interviews

---

# WHAT TECHNICAL LEADERSHIP ACTUALLY MEANS

Most engineers think technical leadership = writing better code. That is wrong.

```
INDIVIDUAL CONTRIBUTOR (IC):
  Scope:     My code, my tickets, my deliverables
  Question:  "How do I build this correctly?"
  Measure:   My PR quality, my delivery speed
  Leverage:  1x (what I personally produce)

TECHNICAL LEAD:
  Scope:     My team's code, architecture, standards, decisions
  Question:  "How does the team build this correctly, consistently, at speed?"
  Measure:   Team velocity, system reliability, engineering quality
  Leverage:  5-10x (what 5-10 engineers produce, shaped by my decisions)

STAFF / PRINCIPAL ENGINEER:
  Scope:     Multiple teams, org-wide technical direction
  Question:  "What should we be building, and how does that connect to business goals?"
  Measure:   Org-level outcomes, platform adoption, technical strategy
  Leverage:  50-100x (what many teams produce, shaped by standards I set)

THE KEY INSIGHT:
  Technical leadership is not about being the best coder in the room.
  It is about multiplying other engineers' output and quality.
  Your code is a small fraction of your total impact.
  Your decisions, standards, and mentoring are the majority.
```

---

# PART 1: ARCHITECTURE DECISION-MAKING

## 1.1 How Senior Engineers Make Architecture Decisions

The most important skill at senior level is not making the right decision — it is making a **well-reasoned, reversible decision quickly** and documenting it so others can build on it.

### The ADR — Architecture Decision Record

Every significant technical decision should have an ADR. This is a short document that captures:

```
ARCHITECTURE DECISION RECORD TEMPLATE:

Title:       ADR-007: Use BigQuery MERGE for CDC instead of Python pre-merge

Status:      ACCEPTED (date: 2024-01-15)

Context:     
  We need to apply CDC (change data capture) updates from MySQL to BigQuery.
  Two options considered: (1) handle MERGE logic in Python before loading,
  (2) use BigQuery's native MERGE statement after loading.

Decision:
  We will use BigQuery's native MERGE (option 2).

Reasons:
  1. At our current volume (50GB/day), BigQuery MERGE runs in <30 seconds 
     using 200 slots — within our reservation
  2. MERGE logic in Python requires spinning up Spark infrastructure, 
     adding ~10 minutes of latency per run
  3. BigQuery MERGE is debuggable via the SQL console; Python merge errors 
     are buried in job logs
  4. All engineers on the team know SQL; fewer know PySpark well

Consequences:
  • Positive: simpler pipeline, faster, cheaper at current scale
  • Negative: if volume grows 100x, MERGE costs will need re-evaluation
  • Risk: BigQuery DML has quotas (1,000 DML statements/day per table) — 
    must stay below this or use table-level batching

Review trigger:
  Re-evaluate if daily table size exceeds 5TB or DML quota approached

WHY ADRs MATTER:
  6 months later: new engineer asks "why don't we use Spark for CDC?"
  Answer: ADR-007 explains it. No meeting needed. No "go ask Viraaj."
  
  18 months later: table is now 8TB, quota concern real.
  ADR-007 says review at 5TB. Engineer knows to revisit the decision.
  
  The ADR is not a legal document. It's a conversation preserved in text.
```

### Framework: How to Evaluate Any Architecture Decision

```
THE 5-DIMENSION FRAMEWORK:

For any architecture choice, evaluate on these 5 dimensions:

1. CORRECTNESS — Does it actually solve the problem?
   Ask: Have I tested the edge cases? What are the failure modes?
   
2. SCALE — Does it work at 10x current volume?
   Ask: Where is the bottleneck at 10x? At 100x?
   Red flag: "It works for now" without understanding the ceiling.

3. OPERABILITY — Can the team debug and fix it at 2 AM?
   Ask: When something breaks, how long to diagnose? What are the alerts?
   Red flag: Any system where the only person who can debug it is its author.

4. REVERSIBILITY — How hard is it to change this decision in 6 months?
   Ask: If we're wrong about X, what would it cost to undo?
   Rule: Prefer reversible decisions. For irreversible ones, demand more evidence.

5. TEAM FIT — Can the team build and maintain this?
   Ask: Who on the team can own this? What training is needed?
   Red flag: Choosing impressive technology the team can't maintain.

EXAMPLE: Choosing between Pub/Sub vs Kafka

Correctness: Both solve the problem (message queue)
Scale:       Kafka scales further; Pub/Sub auto-scales to our needs
Operability: Pub/Sub: Google manages it, no ops; Kafka: need cluster management
Reversibility: Both are hard to replace (deep integration). Choose carefully.
Team Fit:    Team knows GCP but not Kafka cluster operations. Pub/Sub wins.

DECISION: Pub/Sub. Revisit if we need >7 day retention or multi-cloud.
```

---

## 1.2 Trade-Off Thinking — The Senior Engineer's Core Skill

Interviewers at senior level are not looking for "the right answer." They are looking for **trade-off thinking** — the ability to reason about competing constraints and make a reasoned choice.

```
THE WRONG ANSWER to a system design question:
  "We should use X." (no reasoning, no alternatives considered)

THE MEDIOCRE ANSWER:
  "We should use X because it's faster." (one dimension, no trade-offs)

THE SENIOR ANSWER:
  "We should use X over Y in this context because:
   - X gives us A and B which matter here
   - Y gives us C and D which don't matter here
   - The cost of X is E, which is acceptable
   - If the constraint changes (e.g., volume grows 10x), we'd revisit
   - The risk I'm accepting is F, which I'm mitigating by doing G"

TRADE-OFF PAIRS EVERY DATA ENGINEER MUST KNOW:

Latency vs Accuracy:
  Lower latency → less time to collect late events → less accurate metrics
  Higher accuracy → wait longer → higher latency
  Answer: Lambda Architecture. Streaming for speed, batch for accuracy.

Consistency vs Availability:
  ACID transactions → slower but exact
  Eventually consistent → faster but might show stale data briefly
  Answer: Depends on use case. Billing = ACID. Dashboard = eventual is fine.

Cost vs Performance:
  Bigger cluster/warehouse → faster → more expensive
  Smaller resources → cheaper → slower
  Answer: Right-size based on SLA. Don't run a Ferrari for a grocery run.

Flexibility vs Simplicity:
  Generic platform → handles any use case → complex to understand
  Specialized tool → handles one use case perfectly → not reusable
  Answer: Build generic platforms at infrastructure layer, 
          specific tools at application layer.

Build vs Buy:
  Build: full control, maintenance burden, exactly fits needs
  Buy: faster start, vendor dependency, not perfectly fitted
  Answer: Buy for commodity capabilities (logging, auth, CI/CD).
          Build for core differentiating capabilities.

Coupling vs Cohesion:
  Tightly coupled: faster to build, harder to change independently
  Loosely coupled: more complex to wire together, but each piece evolves freely
  Answer: Loose coupling between systems, tight cohesion within them.
```

---

## 1.3 Real Architecture Questions You May Face

### "Walk me through a difficult architecture decision you made."

```
STRUCTURE YOUR ANSWER WITH:
  1. What the decision was (the fork in the road)
  2. What options you considered (at least 2)
  3. What framework you used to evaluate
  4. What you decided and why
  5. What happened (was it the right call?)
  6. What you'd do differently

EXAMPLE (CDM Next):

"The core architecture decision for CDM Next was whether to use a 
CODE-DRIVEN approach (each team writes their own Spark jobs, platform 
provides libraries) or a CONFIG-DRIVEN approach (teams declare what they 
want in YAML, platform generates the code).

OPTIONS:
  Code-driven: familiar to engineers, full flexibility, no abstraction overhead
  Config-driven: lower barrier to entry, consistent patterns, platform controls quality

EVALUATION:
  Correctness: Both handle the transformations needed.
  Scale: Code-driven scales in team count? No — more teams = more custom code to support.
         Config-driven scales well — new team = new YAML file, no new code.
  Operability: Code-driven — every team's pipeline is different. 
               On-call can't debug 60 different codebases.
               Config-driven — on-call has ONE framework to understand.
  Reversibility: High cost to switch once 60 teams are onboarded on either approach.
  Team Fit: Product teams who onboard have SQL/data skills, not Spark skills.

DECISION: Config-driven. The scale argument was decisive — 
  at 60 teams, you cannot afford 60 different codebases.

RESULT: Right call for adoption and consistency. 
  Wrong implementation detail initially: first YAML schema was too opaque.
  Engineers couldn't debug what the platform was doing.
  Added 'dry-run' mode that showed the generated SQL — fixed the trust problem.

LEARNING: Config-driven is right for scale. But the config must be 
transparent — engineers need to understand what it will do to trust it.
Don't abstract away so much that the platform becomes a black box."
```

---

# PART 2: TECHNICAL STANDARDS AND CODE QUALITY

## 2.1 How Senior Engineers Set Standards

A senior engineer's job is not just to write good code. It is to make the **entire team write good code**, consistently, without the senior engineer reviewing every line.

```
LEVELS OF QUALITY ENFORCEMENT:

LEVEL 1: CODE REVIEW (reactive, slowest)
  What: Review PRs and catch issues before merge
  Limitation: Scales linearly with team size. Bottleneck if only one reviewer.
  Best for: Complex logic, design decisions, mentoring conversations

LEVEL 2: LINTING AND STATIC ANALYSIS (automated, fast)
  What: Automated checks that catch mechanical issues
  Tools: flake8, black, mypy (Python), sqlfluff (SQL), pre-commit hooks
  Runs: On every commit, before it even becomes a PR
  Catches: Formatting issues, type errors, unused imports, undefined variables
  Limitation: Can't catch logical errors or design problems

LEVEL 3: AUTOMATED TESTING (proactive, comprehensive)
  What: Unit tests, integration tests, data quality tests
  Tools: pytest (Python), dbt tests (SQL), Great Expectations (data)
  Runs: On every PR in CI/CD pipeline
  Catches: Regressions, edge cases, data quality violations

LEVEL 4: ARCHITECTURE REVIEWS (preventive, highest leverage)
  What: Review design BEFORE implementation, not after
  When: For any change that touches >3 files or involves a new dependency
  Output: ADR if accepted, documented rejection if not
  Catches: Wrong abstractions, scalability problems, security issues

LEVEL 5: POSTMORTEMS (learning from production)
  What: After every significant incident, document root cause and prevention
  Output: Action items that become engineering standards
  Catches: Systemic patterns (e.g., "we keep forgetting partition filters")
  Leverage: One postmortem can prevent 10 future incidents

THE KEY INSIGHT:
  Move quality enforcement as far LEFT as possible.
  Catching a bug in architecture review: 5 minutes.
  Catching it in code review: 30 minutes.
  Catching it in QA: 2 hours.
  Catching it in production: 2 days + incident response + customer impact.
```

## 2.2 Code Review — How Senior Engineers Do It

```
WHAT TO REVIEW (in order of priority):

FIRST: Does it solve the right problem?
  • Does this PR address what the ticket actually asks for?
  • Are there edge cases the author hasn't considered?
  • Is this the right abstraction? (not "does it work" but "is this the right design")

SECOND: Will it survive production?
  • What happens when this fails? Is there error handling?
  • Is there logging to diagnose failures at 2 AM?
  • Are there performance implications at 10x current load?
  • Are there security implications (SQL injection, data exposure)?

THIRD: Is it maintainable?
  • Can someone who didn't write this understand it in 6 months?
  • Are there comments for non-obvious decisions?
  • Are variable/function names clear without needing a comment?

FOURTH: Code style and consistency
  • This should be 90% automated by linters, not manual review.
  • Don't waste PR review time on formatting — automate it.

CODE REVIEW ANTI-PATTERNS (what bad reviewers do):
  ✗ Only review for style ("this variable name should be longer")
  ✗ Approve everything to avoid conflict
  ✗ Give vague feedback ("this looks wrong")
  ✗ Block PRs for trivial issues (bike-shedding on naming)
  ✗ Review 500-line PRs in 5 minutes (not possible to do properly)

CODE REVIEW BEST PRACTICES:
  ✓ PRs should be < 400 lines for reviewability (ask engineers to break up large PRs)
  ✓ Distinguish: "must fix" vs "nice to have" vs "question/curiosity"
  ✓ Ask questions ("What happens if this is null?") rather than state conclusions
  ✓ Approve with minor comments rather than blocking for trivial things
  ✓ Acknowledge what's done well — not just what's wrong
  ✓ If a design is wrong: discuss in real-time, not async in PR comments

HOW TO GIVE SPECIFIC FEEDBACK:

VAGUE (bad):
  "This doesn't look right."
  
SPECIFIC (good):
  "This GROUP BY might produce incorrect results if user_id has NULLs — 
  BigQuery groups NULL values together, so all NULL user_ids would be 
  counted as one user. Add a WHERE user_id IS NOT NULL or handle NULLs 
  explicitly. Here's what I'd suggest: [code]"

QUESTION (often better than statement):
  "What's the expected behavior here when event_id is NULL? I want to 
  make sure we're handling the same edge case consistently across the pipeline."
```

---

## 2.3 Technical Debt — How Leaders Think About It

```
WHAT TECHNICAL DEBT ACTUALLY IS:

Technical debt is NOT "bad code."
Technical debt is a DELIBERATE trade-off:
  "We will do this the quick way now, knowing we'll pay a higher cost later."

Like financial debt: sometimes it's rational.
  "We need to launch in 2 weeks. We'll build the MVP now, 
   refactor after we validate the market."
  
  This is GOOD debt — deliberate, bounded, with a repayment plan.

BAD technical debt: accumulated without awareness or planning.
  "We wrote it this way to hit the deadline" (×50 times, never revisited)
  → Now: nobody can change the system without breaking 3 things.

THE DEBT QUADRANTS:
  
  DELIBERATE + PRUDENT:     "We'll deploy the monolith now and modularize later."
  Best kind. Conscious trade-off with a plan.
  
  DELIBERATE + RECKLESS:    "We don't have time for good design."
  Short-term gain, long-term pain. Avoid.
  
  INADVERTENT + PRUDENT:    "We learned a better way after building this."
  Normal. Address in next refactor cycle.
  
  INADVERTENT + RECKLESS:   "What is coupling?" (didn't know what they didn't know)
  Prevention: good mentoring, standards, review processes.

HOW A TECHNICAL LEADER MANAGES DEBT:

STEP 1: MAKE IT VISIBLE
  Create a "Tech Debt Register" — a simple tracked list:
  Item | Description | Impact if ignored | Effort to fix | Priority | Owner
  
  Engineers know about debt. The problem is it's invisible to managers/PMs.
  Making it visible turns abstract "the codebase needs cleanup" into 
  specific "if we don't fix item 7 by Q3, batch jobs will fail when 
  daily volume crosses 10M rows."

STEP 2: QUANTIFY THE COST
  "Our on-call engineers spend 4 hours/week debugging issues that 
  would be eliminated if we refactored the event parsing layer."
  4 hours × 2 engineers × 52 weeks = 416 engineer-hours/year.
  At $100/hour fully loaded: $41,600/year in engineer time on this one debt item.
  
  Now you have a business case. "This 2-week refactor will save 
  $40K/year in wasted engineer time."

STEP 3: SCHEDULE IT LIKE BUSINESS WORK
  Not as "free time between features" — it never happens.
  As a real allocation: "20% of every sprint is debt reduction."
  OR: "Every third sprint is a debt sprint."
  
  The exact ratio depends on the health of the codebase.
  A codebase where > 30% of bugs are caused by known debt items: 
  needs more debt allocation urgently.

STEP 4: PREVENT NEW DEBT
  Definition of Done checklist: "Does this introduce new tech debt? 
  If yes, is there a ticket to address it within 2 sprints?"
  This makes debt creation conscious, not accidental.
```

---

# PART 3: DATA ENGINEERING TECHNICAL STANDARDS

## 3.1 The Standards Every Senior DE Should Set for Their Team

```
STANDARD 1: ALL PIPELINES MUST BE IDEMPOTENT

Definition: Running a pipeline twice should produce the same result as running it once.

Why it matters:
  - Pipelines fail and get rerun. Always.
  - Without idempotency: reruns create duplicate data.
  - With idempotency: reruns are safe, automatic, self-healing.

How to enforce:
  ✗ INSERT INTO → creates duplicate rows on rerun
  ✓ INSERT OVERWRITE partition → overwrites, no duplicates
  ✓ MERGE on business key → upserts, no duplicates
  ✓ CREATE OR REPLACE TABLE → full table replace, no duplicates

Standard: "No pipeline may use INSERT without a deduplication mechanism."
Automated check: grep for "INSERT INTO" without "MERGE" or "OVERWRITE" in PRs.

─────────────────────────────────────────────────────────────────────────────

STANDARD 2: ALL PIPELINES MUST HAVE DATA QUALITY CHECKS

Definition: Every pipeline run validates its output before signaling success.

Minimum checks:
  □ Row count > 0 (pipeline didn't produce empty output)
  □ Row count within expected range (e.g., ±20% of yesterday's count)
  □ No nulls on NOT NULL columns
  □ No duplicates on primary key
  □ Date range: all rows have event_date in expected range

Enforcement: Pipeline fails if any check fails. Alert fires. Engineer investigates.
             "Succeed silently, fail loudly."

Tool in dbt:
  tests:
    - not_null: {column_name: campaign_id}
    - unique: {column_name: event_id}
    - accepted_values: {column_name: event_type, values: [impression, click, purchase]}
    - dbt_utils.expression_is_true: {expression: "spend_usd >= 0"}

─────────────────────────────────────────────────────────────────────────────

STANDARD 3: ALL QUERIES ON LARGE TABLES MUST HAVE PARTITION FILTERS

Definition: Any query on a table > 1GB must filter on the partition column.

Why: Without partition filter → full table scan → expensive query, slow results.

Enforcement:
  ALTER TABLE large_events SET OPTIONS (require_partition_filter = TRUE);
  → BigQuery REJECTS queries without a partition filter.
  → No manual policing needed.

Code review check:
  Any SQL touching known large tables → verify partition filter present.
  "WHERE click_date = ..." ✓
  "WHERE YEAR(click_date) = 2024" ✗ (prevents pruning, must fix)

─────────────────────────────────────────────────────────────────────────────

STANDARD 4: ALL SECRETS IN VAULT, NEVER IN CODE

Definition: No credentials, API keys, passwords, or tokens in source code.

Why: A committed secret → exposed to everyone with repo access → security breach.

Enforcement:
  pre-commit hook that scans for patterns:
    - AWS_ACCESS_KEY_ID = 
    - password = "
    - api_key = "
    - PRIVATE KEY
  If found: commit blocked.

Approved secret storage:
  GCP: Secret Manager
  Local dev: .env files (gitignored)
  CI/CD: GitHub Secrets / Jenkins credentials store

─────────────────────────────────────────────────────────────────────────────

STANDARD 5: PIPELINE ALERTING IS NON-NEGOTIABLE

Definition: Every production pipeline has alerts for: failure, data quality, 
            SLA breach, and anomalous volume.

Why: Without alerts → failures are found by stakeholders ("my dashboard is wrong")
     → late detection → bigger blast radius → lost trust

Minimum alert set per pipeline:
  1. Pipeline failed (job exit code != 0)
  2. Pipeline didn't run by expected time (SLA breach)
  3. Output row count > 2x or < 0.5x expected (anomaly)
  4. Data freshness: most recent record > N hours old

Tool: Cloud Monitoring (GCP) or Airflow callbacks to Slack/PagerDuty
```

---

## 3.2 CI/CD for Data Engineering

```
WHAT CI/CD MEANS FOR DATA ENGINEERING:

Traditional software: CI/CD = test and deploy application code.
Data engineering: CI/CD = test and deploy pipeline code + validate data models.

THE DATA ENGINEERING CI/CD PIPELINE:

Pull Request opened:
    │
    ▼
CONTINUOUS INTEGRATION (CI) runs automatically:
  1. Lint check (sqlfluff for SQL, black/flake8 for Python)
  2. Unit tests (pytest for Python functions)
  3. dbt compile (verify SQL compiles without errors)
  4. dbt test --select state:modified (test only changed models)
     Uses "slim CI" — only runs tests for changed models + their downstream
     (vs testing everything = too slow for PRs)
  5. Terraform plan (if infrastructure changed — shows what would change)
  
  Time: 5-10 minutes
  All must pass before PR can be merged.
    │
    ▼
PR MERGED to main:
    │
    ▼
CONTINUOUS DEPLOYMENT (CD) runs automatically:
  1. Deploy to staging environment
  2. Run full dbt test suite in staging (not slim — full)
  3. Run integration tests (does end-to-end pipeline produce expected output?)
  4. If all pass: deploy to production
  5. Post-deployment: smoke test (row count check on production output)
    │
    ▼
PRODUCTION MONITORING:
  Ongoing data quality checks on production tables
  Alerting on failures or anomalies

WHY THIS MATTERS FOR A LEAD:
  Without CI/CD: a single bad PR can corrupt production data.
  With CI/CD: bad code is caught before it reaches production.
  Your job as tech lead: set up and maintain this pipeline.
  
  Story for interview:
  "One thing I drove on CDM Next was adding automated data quality checks 
  as a required CI step. Before: engineers submitted pipelines that passed 
  code review but produced empty output or duplicates that weren't caught 
  until stakeholders noticed. After: the CI pipeline ran 5 data quality 
  checks against a sample dataset. Any failure blocked the merge. 
  We eliminated an entire class of production incidents — 
  empty output bugs went to zero."
```

---

# PART 4: TECHNICAL STRATEGY AND ROADMAPPING

## 4.1 How to Build a Technical Roadmap

```
A TECHNICAL ROADMAP answers: "What are we building, in what order, and why?"

It is different from a project plan (which answers "when does each task finish?")

ROADMAP STRUCTURE:

HORIZON 1 (0-3 months): NOW
  Committed deliverables. High confidence. Teams know what to build.
  Granular: specific features and timelines.
  
  Example for Costco MarTech:
  - Complete clickstream pipeline for Google Ads events (2 weeks)
  - Deploy real-time ROAS dashboard (3 weeks)
  - Identity resolution MVP: first-party cookie + login stitch (4 weeks)

HORIZON 2 (3-9 months): NEXT
  Planned but not committed. Directionally clear. May change.
  Less granular: outcomes, not specific features.
  
  Example:
  - Cross-device attribution using identity graph
  - Automated campaign budget pacing alerts
  - DBT marts layer for all campaign metrics

HORIZON 3 (9-18 months): LATER
  Strategic bets. High uncertainty. Based on trends and business direction.
  
  Example:
  - Clean room integration with Meta for privacy-preserving measurement
  - Real-time bidding optimization signals
  - ML-based audience segmentation

HOW TO PRIORITIZE THE ROADMAP:

Use the ICE framework:
  I = Impact:   How much does this move the business metric?
  C = Confidence: How confident are we this will have that impact?
  E = Ease:     How easy is it to build? (inverse of complexity)
  
  ICE score = (Impact × Confidence × Ease) / 3
  Build highest ICE score items first.

COMMUNICATE THE ROADMAP:
  Weekly: team-level task board (Jira/Linear)
  Monthly: stakeholder-level roadmap update (what shipped, what's next, any changes)
  Quarterly: leadership-level strategy review (are we on track for the annual goals?)
  
  The roadmap is a COMMUNICATION TOOL as much as a planning tool.
  Stakeholders who don't know what's coming become anxious and interrupt engineers.
  A visible roadmap reduces interruptions and builds trust.
```

---

## 4.2 Technical Interview Questions at Lead/Staff Level — With Answers

### "How do you decide when to refactor vs rewrite?"

```
ANSWER:

"My starting principle is: prefer refactor over rewrite almost always.
The 'second system' effect is real — rewrites almost always take 
2-3x longer than estimated and introduce new bugs to replace old ones.

I ask four questions to decide:

1. Is the problem structural or superficial?
   Superficial (bad variable names, missing tests, poor comments): refactor.
   Structural (wrong abstraction, cannot extend without breaking): deeper work needed.

2. Can I change the behavior through the existing interface?
   If I can add tests, then change the implementation and tests pass:
   this is safe refactoring. Martin Fowler's definition.
   If tests can't even be written against the current design: the structure is so
   wrong that refactoring is not meaningful. This is a rewrite candidate.

3. What is the cost of incremental improvement vs fresh start?
   Estimate both honestly. Rewrites consistently take 3x the initial estimate.
   Factor that in. Often refactoring over 3 sprints is cheaper.

4. What is the business risk of a rewrite?
   A 6-month rewrite freezes new feature development.
   The business doesn't stop. Debt may be better than 6 months of stagnation.

MY CDM NEXT EXAMPLE:
   Our first YAML config spec was wrong in a fundamental way — it 
   treated every transformation as a separate plugin with no 
   composition model. Adding a new transform type required touching 
   5 files. This was structural, not superficial.
   
   I chose to rewrite the spec, but with three guardrails:
   1. Time-boxed to 2 weeks (if not done, ship what we have)
   2. All existing team configs would auto-migrate (backward compatible)
   3. I wrote the migration script before writing the new spec
      (to prove the migration was feasible)
   
   Result: 2-week rewrite, all configs migrated automatically, 
   new transform types now add in 1 file instead of 5."
```

---

### "How do you handle a team where code quality is declining?"

```
ANSWER:

"I'd start with diagnosis before prescription. Code quality decline 
has three common root causes:

1. Speed pressure: the team is shipping too fast to do it right.
   Symptom: PRs with "we'll fix this later" comments that pile up.
   Fix: make tech debt visible and negotiate capacity for it.
   
2. Knowledge gaps: team members don't know the standard patterns.
   Symptom: same mistakes across multiple engineers (not one person).
   Fix: pairing sessions, playbooks, adding automated checks.
   
3. Low standards: nobody is actually enforcing quality.
   Symptom: PRs get rubber-stamped, code review is cursory.
   Fix: change the code review culture, be explicit about expectations.

I'd run a one-hour retrospective with the team:
'Looking at the last 5 production incidents, what was the root cause 
of each? Were they preventable in code review? What would have caught them?'

This makes the conversation factual, not personal.
Often the team already knows what's wrong — they just haven't had 
space to say it.

Then I'd pick ONE concrete action: not a general 'do better' mandate, 
but a specific change. For example:
'Every PR must have at least 2 reviewers from now on.'
Or: 'We're adding sqlfluff to our pre-commit hooks this week.'
Or: 'For the next month, no PR can be merged by the author alone.'

Measure: track the production incident rate before and after.
If it improves: expand the practice. If not: try a different lever.

The worst thing I can do is talk about quality without changing 
any process. Engineers can tell the difference between 
talk and action."
```

---

### "How do you mentor junior engineers effectively?"

```
ANSWER:

"I've found there's a significant difference between 
mentoring and supervising. Supervising is checking 
their work and correcting it. Mentoring is building 
their ability to check their own work.

My framework has three phases:

PHASE 1: OBSERVE AND DEMONSTRATE (weeks 1-4)
  I pair with them on real tasks.
  I narrate my thinking out loud:
  'I'm choosing MERGE here instead of INSERT because... 
   I'm adding this partition filter because I know this table is 500GB 
   and without it we'd scan the whole thing.'
  I'm building a mental model for them, not just solving the problem.

PHASE 2: GUIDED EXECUTION (weeks 4-12)
  They lead, I ask questions.
  I don't tell them what to do — I ask:
  'What happens if this runs twice?'
  'What would this query cost on a table with 10 billion rows?'
  'Who else needs to know about this change?'
  I'm training them to ask themselves these questions.

PHASE 3: INDEPENDENT WITH SAFETY NET (months 3-6)
  They work independently.
  I review their work but I don't block progress.
  I schedule a weekly 30-minute 1:1 for questions.
  I give them increasing ownership — first: one full feature.
  Then: one full pipeline. Then: one full domain.

HOW I MEASURE MENTORING SUCCESS:
  Not: 'Can they implement what I specify?'
  Yes: 'Can they identify problems I haven't specified and design solutions?'
  
  The moment a junior engineer catches a production bug in code review 
  that I didn't notice — that's when I know the mentoring is working.
  
  Real example: After 3 months of mentoring, the junior engineer I mentioned 
  earlier submitted a PR that included automated tests I hadn't asked for. 
  They said: 'I added these because I realized this function handles user data 
  and we should verify the PII masking works.' 
  That was their internalized standard, not my instruction."
```

---

# PART 5: TECHNICAL LEADERSHIP QUICK-FIRE QUESTIONS

```
Q: "What makes a good data model?"
A: "Three things. First, it reflects the business, not the source system — 
    table names and columns should be understandable by an analyst, not just 
    the engineer who built it. Second, it's performant by design — partitioned 
    and clustered for the queries that will actually be run against it. 
    Third, it handles slowly changing dimensions correctly — if a campaign's 
    name changes, historical reports should still work."

Q: "How do you ensure pipeline reliability?"
A: "Idempotent design (safe to rerun), data quality checks on output, 
    automated alerting on failure or SLA breach, documented runbooks for 
    common failure modes, and regular chaos engineering — deliberately failing 
    components to test recovery. The goal is that any pipeline failure should 
    be detectable in minutes and recoverable without human intervention."

Q: "What's your approach to documentation?"
A: "I think about three audiences: the engineer using the system today 
    (needs: quickstart, common patterns, how-to guides), the engineer debugging 
    at 2 AM (needs: runbook for each alert type, known failure modes, who to call), 
    and the engineer who joins in 6 months (needs: architectural decision context, 
    why things are the way they are). Most teams document for audience 1 and 
    completely neglect audience 2 and 3."

Q: "How do you introduce a new technology to a team?"
A: "I never introduce new technology in production first. I run a proof of concept 
    on a low-stakes, real-but-not-critical problem. Measure the gains against the 
    adoption cost honestly. Write up the evaluation with the team. If it clears 
    the bar: propose a pilot on one pipeline with a rollback plan. If the pilot 
    succeeds: establish the pattern and help three engineers independently replicate 
    it without me. Only after that is it 'adopted.' The mistake most engineers make 
    is introducing technology they personally love without validating the team can 
    operate it without them."

Q: "What's the most important thing a tech lead does?"
A: "Makes decisions, documents them, and enables the team to make good decisions 
    independently. The tech lead who is a bottleneck — where everything has to 
    go through them — has failed at the most important part of the job: 
    creating distributed judgment, not centralized judgment."
```

---

# SUMMARY: TECHNICAL LEADERSHIP CHEAT SHEET

```
ARCHITECTURE:
  Use ADRs for every significant decision (what, why, not what, consequences)
  Evaluate on 5 dimensions: correctness, scale, operability, reversibility, team fit
  Prefer reversible decisions. Demand more evidence for irreversible ones.
  
TRADE-OFFS (the senior engineer's core skill):
  Always present minimum 2 options with trade-offs
  Match the choice to the specific constraints, not just general best practice
  
CODE QUALITY:
  Move enforcement LEFT: pre-commit > CI > code review > production
  Code review priority: does it solve the right problem? → will it survive? → maintainable?
  Never block PRs on style — automate style enforcement
  
TECHNICAL DEBT:
  Make it visible (debt register), quantify the cost, schedule it like business work
  Prevent: conscious debt creation with a repayment plan
  
STANDARDS (the 5 non-negotiables):
  1. All pipelines idempotent
  2. All pipelines have DQ checks
  3. All large table queries have partition filters
  4. No secrets in code
  5. All production pipelines have alerting
  
MENTORING:
  Phase 1: demonstrate with narration
  Phase 2: guide with questions (not answers)
  Phase 3: independent with safety net
  Success: they catch problems you didn't specify
```
