# Behavioural & Communication — Exhaustive Interview Q&A
### STAR Answers Mapped to CDM Next + Stakeholder + Leadership Scenarios

---

## HOW TO USE THIS GUIDE

Every answer uses the STAR method: **Situation** (context), **Task** (what you were responsible for), **Action** (what you specifically did), **Result** (measurable outcome). Each answer is tailored to your CDM Next experience. Memorise the structure; adapt the words naturally in conversation.

---

## SECTION 1: IMPACT AND DELIVERY

**Q1. Tell me about the most impactful project you've worked on.**

**Situation:** Wells Fargo had a critical strategic initiative to migrate its entire on-premise data infrastructure to Google Cloud Platform. The CDM Next programme — Cloud Data Movement — was responsible for moving data from Teradata, Oracle, Hadoop, and Kafka systems to BigQuery. The stakes were high: 60+ application teams depended on this data for regulatory reporting, risk modelling, and customer analytics.

**Task:** I was responsible for designing and building the core migration framework as a Senior Data Engineer. The challenge wasn't just technical — we needed to onboard 60+ teams without writing bespoke pipeline code for each one.

**Action:** I architected a configuration-driven pipeline framework where teams submitted YAML configs declaring their source table, target schema, validation rules, and schedule — no code changes required. I built the extraction layer for Teradata and Oracle sources using generator-based batching for memory efficiency, the validation layer with row-count reconciliation and Cloud DLP PII scanning, and the Airflow DAG factory that generated DAGs dynamically from configs at runtime. I also built the governance layer: IAM per team, column-level security, Secret Manager integration, and a pipeline audit table that gave every team a self-service health dashboard.

**Result:** The framework migrated 15+ petabytes of data across 60+ application teams. Onboarding a new team dropped from weeks of bespoke engineering to under two days. Zero production data breaches despite handling highly sensitive financial data. The platform became the foundation for Wells Fargo's cloud analytics strategy.

---

**Q2. Describe a time you solved a complex technical problem under pressure.**

**Situation:** Three weeks before a critical regulatory reporting deadline, the finance team discovered a data discrepancy: their BigQuery risk report showed a $2.3 billion variance against the source Teradata system. The report was due to regulators in 21 days.

**Task:** I was assigned to investigate and resolve the root cause, coordinate with the finance team to validate the fix, and ensure the corrected data was in BigQuery before the deadline.

**Action:** I started with the audit table to trace the issue to its first occurrence — it had been happening for 11 weeks, introduced when a Teradata source team changed their partition scheme without notifying CDM Next. Our watermark query was filtering on an old partition column, missing approximately 0.3% of daily records — tiny per day, but compounding to a significant variance over 11 weeks. I wrote a targeted reconciliation query to quantify the exact gap per day. Then I designed the backfill: fix the watermark logic, process the 11-week historical window in reverse chronological order using partition overwrite for idempotency. I ran the backfill in a dedicated BigQuery slot reservation so it wouldn't impact live pipelines, processing in weekly batches with validation sign-off from the finance team after each batch. I implemented a schema change notification hook so any future source-side DDL changes would alert CDM Next before impacting data.

**Result:** Full backfill completed in 6 days. Finance team validated the reconciled data and the regulatory report was submitted on time. The root cause was converted into a new monitoring rule: daily reconciliation of row counts and financial checksums between source and BigQuery for all production tables. The incident was written up as a post-mortem and shared with the broader data platform community at Wells Fargo.

---

**Q3. Tell me about a time you improved a process significantly.**

**Situation:** When I joined the CDM Next programme, onboarding a new application team required a data engineer to write bespoke Airflow DAGs, configure IAM manually in the console, and handle extraction code specific to each source system. The process took 3–4 weeks per team and didn't scale — we had 40 teams waiting to onboard.

**Task:** I proposed and led the redesign of the onboarding process to make it self-service and configuration-driven.

**Action:** I designed a YAML config schema that captured everything needed for a migration: source connection, table name, watermark column, target dataset, validation tolerances, schedule, and PII column list. I built a DAG factory in Airflow that read configs from a GCS registry and generated DAGs dynamically at runtime — no deployment needed for new configs. I wrote a Terraform module that, given a team name and config, provisioned the complete infrastructure: BigQuery dataset, dedicated service account, IAM bindings, GCS staging prefix, and Secret Manager entry. I wrote a config validator that checked YAML against a schema and gave clear error messages before any infrastructure was touched. Finally, I created a self-service onboarding guide and ran knowledge transfer sessions with application teams.

**Result:** Onboarding time reduced from 3–4 weeks to under 2 days. The remaining 40 teams were onboarded in the following 8 weeks. The platform team's time spent on routine onboarding dropped by 80%, freeing capacity for platform improvements. The config-driven pattern became the CDM Next standard and was adopted for other pipeline types beyond migration.

---

## SECTION 2: TECHNICAL LEADERSHIP AND DECISION-MAKING

**Q4. Describe a time you had to make a technical decision with incomplete information.**

**Situation:** We needed to choose a data replication approach for high-priority Oracle financial tables. The options were: Datastream CDC (near-real-time, complete change history) vs. incremental batch extraction (simpler, proven in our framework). The business wanted a decision in 48 hours because regulatory timelines were fixed.

**Task:** I was asked to make the recommendation and own the technical decision.

**Action:** I listed the decision criteria and what I knew vs didn't know. Known: Datastream was GA, supported Oracle, and had native BigQuery integration. Unknown: whether it could handle our specific Oracle version and the redo log configuration used at Wells Fargo. Instead of asking for more time, I ran a 1-day proof of concept with a non-production Oracle instance alongside our DBA team. The POC confirmed Datastream worked with our Oracle version, could handle the expected volume, and provided the sub-minute latency the finance team needed. I documented the decision, the POC results, the tradeoffs versus batch extraction, and the risks I was accepting.

**Result:** We shipped Datastream for the high-priority Oracle tables on schedule. The CDC approach also gave us a complete audit trail of every change — something regulators later asked for and which we could provide because of this decision. The decision documentation became the template for architectural decision records (ADRs) in CDM Next.

---

**Q5. Tell me about a time you disagreed with a technical approach and what you did.**

**Situation:** A senior architect on the programme proposed storing all pipeline credentials as Airflow Variables, citing simplicity and the fact that they were encrypted in the Airflow metadata database.

**Task:** I believed this was a security risk and needed to raise it appropriately — without damaging the relationship with the architect.

**Action:** I prepared a short written comparison: Airflow Variables vs Secret Manager for credentials. The Airflow approach had two risks: the Airflow metadata database admin had plaintext access to all credentials, and Airflow Variables weren't integrated with GCP audit logging — we couldn't track who accessed a credential. Secret Manager solved both: credentials were encrypted with CMEK, access required explicit IAM grants, and every access was logged in Cloud Audit Logs. I presented this in a one-on-one with the architect first — private conversation before any group forum. I acknowledged that Secret Manager added a small code overhead (one API call per credential at pipeline startup), but argued the security and auditability benefits were non-negotiable for a regulated financial environment. The architect reviewed the comparison and agreed.

**Result:** CDM Next adopted Secret Manager as the credential store standard. When a security audit was conducted 6 months later, the auditors specifically cited our credential management as a best-practice example. The architect and I continued to collaborate effectively — the key was raising the concern privately with evidence, not in a group setting as a challenge.

---

## SECTION 3: COLLABORATION AND STAKEHOLDER MANAGEMENT

**Q6. How do you handle working with non-technical stakeholders?**

**Situation:** The Head of Finance Data at Wells Fargo needed to understand the CDM Next migration timeline and risk profile for a board presentation. She was not technical but needed to make resource allocation decisions.

**Task:** I needed to communicate complex technical migration details in terms meaningful to a senior business leader.

**Action:** I translated technical status into three business-relevant dimensions: what data is available in BigQuery today and reliable for reports; what data is in progress and when it will be ready; what data is blocked and why. I created a single-page dashboard in Looker Studio: green/yellow/red status per business domain, timeline with milestone dates, and a plain-English risk register (not "CDC replication lag" but "real-time account balance data — currently available within 1 hour, target within 5 minutes, on track for Q2"). When I presented, I led with outcomes, not technology. Questions about technical details I answered simply with an analogy before the technical explanation.

**Result:** The Head of Finance Data used the dashboard in her board presentation directly. She subsequently became an advocate for CDM Next, which helped secure additional headcount for the programme. The dashboard became our standard stakeholder communication for all C-level reporting.

---

**Q7. Describe a time you handled a conflict between two teams.**

**Situation:** The CDM Next platform team and the Finance application team disagreed on the SLA for daily data freshness. Finance wanted data available by midnight; the platform team had set a 2 AM SLA because of upstream source system batch windows.

**Task:** I was the technical lead involved in both conversations and needed to broker a resolution.

**Action:** First I made sure I fully understood both sides. Finance's constraint: a critical regulatory report needed to run at 1 AM and depend on that day's data — this was a genuine hard requirement, not a preference. The platform's constraint: Teradata's batch window for Finance data closed at 11:30 PM, and extraction + transformation + validation typically took 90–120 minutes — leaving no buffer for midnight. I reframed the problem: instead of asking "can we make midnight work?" I asked "what would need to change to make midnight work?" The options were: (1) stagger the Teradata batch window to start at 9 PM — required coordination with the Teradata team; (2) prioritise Finance tables in a dedicated high-priority slot pool so they completed faster; (3) identify which specific tables the 1 AM report needed and fast-track only those. Option 3 was the fastest. We identified 8 critical tables, tuned their extraction jobs, and guaranteed midnight availability for those 8 tables only.

**Result:** Finance got their critical tables by midnight. The platform team didn't take on an impossible SLA for 200+ tables. The negotiation established a precedent: specific SLAs could be negotiated per table based on business criticality, not one blanket SLA for everything.

---

**Q8. Tell me about a time you mentored or helped a colleague grow.**

**Situation:** A junior data engineer joined the CDM Next team with strong SQL skills but limited Python and no GCP experience. She was assigned to build an extraction pipeline for Kafka sources.

**Task:** I was asked to mentor her as she worked through the task.

**Action:** Rather than building the pipeline for her, I broke the learning into stages. Week 1: I paired with her to build a minimal working Kafka consumer using Pub/Sub — enough to understand the mechanics. I pointed her to specific GCP documentation pages rather than explaining everything myself, building her ability to self-learn from docs. Week 2: she built the Airflow DAG independently; I reviewed her PR with detailed comments focused on patterns (why partition overwrite, why idempotency) not just fixes. Week 3: we ran a load test together and I walked her through reading Cloud Monitoring metrics to identify a throughput bottleneck. I introduced her to colleagues on other teams working on similar problems so she built her own network.

**Result:** She delivered the Kafka pipeline independently within 6 weeks. More importantly, she understood the design choices, not just the code. Eight months later she was leading the onboarding of streaming sources herself and mentoring the next junior engineer on the team. The approach — guide, don't build for them — was more time-efficient for me too: 3–4 hours a week vs building it myself.

---

## SECTION 4: HANDLING FAILURE AND AMBIGUITY

**Q9. Tell me about a failure or mistake you made and what you learned.**

**Situation:** Early in the CDM Next programme, I deployed a schema migration for a critical customer dimension table directly to production without going through staging first. I had tested it in a local environment, was confident it was correct, and wanted to meet a deadline.

**Task:** I owned the deployment and the consequences.

**Action:** The migration dropped and re-added a column to fix a naming inconsistency. What I hadn't accounted for: a downstream BI report had a hardcoded reference to the old column name. Within 30 minutes of deployment, the Finance BI dashboard broke. I immediately ran the rollback procedure — BigQuery Time Travel to restore the table to its pre-migration state — which brought the dashboard back online in 8 minutes. I wrote a post-mortem the same day: what happened, why the testing was insufficient, what would prevent recurrence. I implemented two changes: a mandatory staging deployment step before any production schema change, and an automated impact analysis tool that checked the lineage table for downstream dependencies before any DDL was run in production.

**Result:** Dashboard was restored within 8 minutes. No data was lost. The impact analysis tool I built has since caught 14 potential breaking changes before they reached production. The lesson I carry: confidence is not a substitute for process. The extra 4 hours to go through staging would have been faster than the incident response.

---

**Q10. How do you handle working on a project with ambiguous requirements?**

**Situation:** At the start of CDM Next, the programme brief said "migrate data to GCP." There were no detailed requirements for how pipelines should be structured, what validation was needed, what security standards applied, or what SLAs were expected.

**Task:** I needed to make forward progress while requirements were still being defined.

**Action:** I identified the decisions that had to be made before anything else — what I call "foundation decisions" — and drove those to closure quickly with the smallest possible group: the technical lead and one business stakeholder. Foundation decisions for CDM Next: storage format (Parquet — agreed in one meeting), ingestion pattern (ELT — agreed after a 30-minute pros/cons discussion), security baseline (VPC SC + DLP — aligned with the existing Wells Fargo security policy). Everything else I treated as iterative. I built a working end-to-end pipeline for one table in week 2 — even if requirements changed, the working example was a forcing function for concrete feedback. I documented assumptions explicitly and made them visible: "I'm assuming daily batch is sufficient unless a team flags a real-time requirement." This surfaced requirement gaps without blocking delivery.

**Result:** The programme delivered a working platform for the first 5 application teams within 8 weeks, despite requirements still being partially defined. The working system generated far more specific feedback than any requirements document could have. Ambiguity is uncomfortable but workable — the key is making your assumptions visible so stakeholders can correct them early.

---

## SECTION 5: NEW ROLE AND GROWTH

**Q11. Why are you interested in this role?**

I've spent 11 years building data infrastructure — from early Hadoop pipelines at TCS, to large-scale ETL at Verizon, to leading a petabyte-scale cloud migration at Wells Fargo. CDM Next gave me deep experience in platform-scale data engineering: the technical depth to design systems that process 15+ PB, and the practical experience of making data governance real rather than theoretical.

What excites me about this role is the combination of modern cloud architecture and the scale of impact. I want to keep working on platforms that serve many teams and business domains simultaneously — that multiplier effect of platform work is what I find most energising. I'm also deliberately investing in closing my GenAI knowledge gap — I have strong infrastructure foundations and I'm building fluency in RAG systems, vector databases, and LLM orchestration to contribute to the AI-driven data platform work that every major financial institution is now pursuing.

Hyderabad is home, and the opportunity to work with a team of this calibre locally is exactly what I've been looking for.

---

**Q12. Where do you see yourself in 3–5 years?**

In the near term, I want to deepen my expertise in two dimensions: distributed systems at even larger scale, and the intersection of data engineering with GenAI applications — specifically building the data infrastructure that makes AI products reliable and trustworthy (data pipelines for RAG, feature stores, model monitoring pipelines). I find the engineering of AI infrastructure more interesting than the modelling itself.

In the medium term, I see myself moving into a Principal or Staff Engineer role — setting technical direction for a data platform, making architectural decisions, and mentoring engineers. The CDM Next experience gave me exposure to what that looks like at scale. I enjoyed the architectural problem-solving and the multiplier of building platforms that 60 teams rely on.

---

**Q13. Tell me about yourself (opening pitch — 90 seconds).**

I'm a Senior Data Engineer with 11 years of experience building large-scale data infrastructure on cloud platforms. Most recently I've been at Wells Fargo, where I was a core engineer on CDM Next — our programme to migrate the bank's on-premise data estate to Google Cloud Platform. That involved building a configuration-driven migration framework that processed 15+ petabytes of data from Teradata, Oracle, Hadoop, and Kafka sources into BigQuery, serving 60+ application teams. The work spanned the full stack: extraction and ingestion pipelines in Python, orchestration with Cloud Composer, governance with Cloud DLP and IAM, and observability with Cloud Monitoring and structured audit logging.

Before Wells Fargo, I built PySpark ETL pipelines at Verizon and started my career at TCS doing Hadoop-based batch processing. I hold GCP Professional Data Engineer and AWS ML Specialty certifications.

My technical strengths are BigQuery and GCP broadly, Python, PySpark, and large-scale pipeline architecture. I'm now actively building GenAI and LLM application skills to complement my infrastructure foundation. I'm looking for a Senior Data Engineer role where I can work on a high-scale platform and continue growing technically — which is what brought me to this conversation.

---

*End of Behavioural & Communication Q&A*
