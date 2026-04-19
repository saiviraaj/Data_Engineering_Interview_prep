# Topic 10: Behavioral, Leadership & MarTech Domain Knowledge

> **Textbook Reference — Costco Sr. Data Engineer Interview Prep**
> STAR-format behavioral answers aligned to Costco's Sr. DE profile, MarTech/AdTech domain vocabulary, leadership principles, and interview strategy.

---

## Table of Contents
1. MarTech & AdTech Domain Knowledge
2. Key MarTech Metrics Deep Dive
3. Attribution Models
4. Identity Resolution in MarTech
5. Cookie Deprecation & Privacy Changes
6. Costco-Specific Context
7. Behavioral Interview Framework
8. STAR Answers — Technical Leadership
9. STAR Answers — Conflict & Collaboration
10. STAR Answers — Impact & Scale
11. STAR Answers — Failure & Learning
12. Questions to Ask the Panel
13. Interview Strategy & Mindset

---

## 1. MarTech & AdTech Domain Knowledge

### The MarTech Stack Layers

```
┌─────────────────────────────────────────────────────────┐
│               DATA ACTIVATION                            │
│   Email, Push Notifications, Paid Media, Personalization │
│   (Marketo, Braze, Google Ads, Facebook Ads API)        │
├─────────────────────────────────────────────────────────┤
│               ANALYTICS & MEASUREMENT                    │
│   Campaign attribution, dashboards, A/B test results    │
│   (Looker, Google Analytics 4, BigQuery ML)             │
├─────────────────────────────────────────────────────────┤
│               AUDIENCE MANAGEMENT                        │
│   Segmentation, lookalike modeling, suppression lists   │
│   (Segment, Lytics, AlloyDB for real-time serving)      │
├─────────────────────────────────────────────────────────┤
│               DATA COLLECTION                            │
│   Web tags, server-side tracking, SDK events            │
│   (GTM, Firebase, Pub/Sub, Dataflow ingestion)          │
├─────────────────────────────────────────────────────────┤
│               DATA FOUNDATION                            │
│   CDP, data warehouse, data lake                        │
│   (BigQuery, GCS, Dataplex, dbt)                        │
└─────────────────────────────────────────────────────────┘
```

### AdTech Ecosystem: The Programmatic Advertising Flow

```
ADVERTISER (Costco)
    │ Campaign brief, budget, targeting
    ▼
DSP (Demand-Side Platform) — e.g., DV360, The Trade Desk
    │ Real-time bid request
    ▼
AD EXCHANGE — e.g., Google AdX
    │ Auction (RTB: Real-Time Bidding, ~100ms)
    ▼
SSP (Supply-Side Platform) — publisher's system
    │ Ad served to winning bidder
    ▼
PUBLISHER WEBSITE / APP
    │ User sees the ad
    ▼
AD TAG / PIXEL — fires tracking events
    │ impression, click, conversion events
    ▼
DATA PIPELINE (Your job!)
    │ Pub/Sub → Dataflow → BigQuery
    ▼
MEASUREMENT & REPORTING
```

**Key terms you must know:**
- **RTB (Real-Time Bidding)**: Automated auction for each ad impression, decided in ~100ms
- **CPM (Cost Per Mille)**: Cost per 1000 impressions — brand awareness campaigns
- **CPC (Cost Per Click)**: Cost per click — performance campaigns
- **CPA (Cost Per Acquisition)**: Cost per conversion — ROI-focused campaigns
- **ROAS (Return on Ad Spend)**: Revenue generated per dollar spent on ads
- **Frequency Cap**: Maximum number of times a user sees the same ad
- **Look-alike Audience**: Targeting users similar to existing high-value customers
- **Retargeting**: Showing ads to users who previously visited your site
- **DMA (Designated Market Area)**: Geographic advertising region (Nielsen standard)
- **Viewability**: % of ad that was actually visible on screen (>50% for 1 sec = viewable)
- **Invalid Traffic (IVT)**: Bot traffic that inflates metrics — filtered in quality pipeline

### Customer Data Platform (CDP) vs Data Warehouse vs CRM

| System | Primary Purpose | Users | Update Pattern |
|--------|-----------------|-------|----------------|
| **CDP** | Unified customer profile, real-time activation | Marketing ops | Real-time streaming |
| **Data Warehouse** | Historical analytics, reporting | Analysts, engineers | Batch (daily/hourly) |
| **CRM** | Sales pipeline, customer relationships | Sales team | Transactional |
| **DMP** | Audience segments for programmatic ads | Campaign managers | Batch (deprecated w/ cookie loss) |

**In a GCP-native stack:**
- CDP function → AlloyDB (real-time profile serving) + BigQuery (analytics)
- Segments computed in BigQuery (SQL), pushed to AlloyDB for <10ms lookup

---

## 2. Key MarTech Metrics Deep Dive

### Conversion Funnel Metrics

```
Awareness:      Impressions, Reach, Frequency
Consideration:  Clicks, CTR, Video Views, Time on Site
Intent:         Add to Cart, Product Page Views, Wishlists
Conversion:     Orders, Revenue, AOV
Loyalty:        Repeat Purchase Rate, LTV, NPS
```

### SQL Implementation of MarTech KPIs

```sql
-- Full campaign performance scorecard
WITH event_agg AS (
    SELECT
        report_date,
        campaign_id,
        channel,
        SUM(impressions) AS impressions,
        SUM(clicks) AS clicks,
        SUM(conversions) AS conversions,
        SUM(revenue) AS revenue,
        SUM(spend) AS spend,
        COUNT(DISTINCT attributed_members) AS unique_members
    FROM gold.campaign_daily_performance
    WHERE report_date BETWEEN '2024-01-01' AND '2024-01-31'
    GROUP BY 1, 2, 3
)
SELECT
    report_date,
    campaign_id,
    channel,
    impressions,
    clicks,
    conversions,
    revenue,
    spend,
    unique_members,
    
    -- Efficiency metrics
    SAFE_DIVIDE(clicks, impressions) AS ctr,                    -- Click-Through Rate
    SAFE_DIVIDE(conversions, clicks) AS cvr,                    -- Conversion Rate
    SAFE_DIVIDE(conversions, impressions) AS ctr_cvr,           -- End-to-end rate
    
    -- Cost metrics
    SAFE_DIVIDE(spend, impressions) * 1000 AS cpm,              -- Cost Per Mille
    SAFE_DIVIDE(spend, clicks) AS cpc,                          -- Cost Per Click
    SAFE_DIVIDE(spend, conversions) AS cpa,                     -- Cost Per Acquisition
    
    -- Revenue metrics
    SAFE_DIVIDE(revenue, spend) AS roas,                        -- Return on Ad Spend
    SAFE_DIVIDE(revenue, conversions) AS aov,                   -- Average Order Value
    SAFE_DIVIDE(revenue - spend, spend) AS roi,                 -- Return on Investment
    
    -- Audience metrics
    SAFE_DIVIDE(impressions, unique_members) AS frequency        -- Avg impressions per member

FROM event_agg
ORDER BY report_date, roas DESC;
```

### RFM Segmentation

```sql
-- RFM: Recency, Frequency, Monetary — classic customer segmentation
WITH member_rfm AS (
    SELECT
        member_id,
        DATE_DIFF(CURRENT_DATE(), MAX(order_date), DAY) AS recency_days,
        COUNT(DISTINCT order_id) AS frequency,
        SUM(order_amount) AS monetary
    FROM orders.transactions
    WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
    GROUP BY 1
),
rfm_scored AS (
    SELECT
        member_id,
        recency_days,
        frequency,
        monetary,
        NTILE(5) OVER (ORDER BY recency_days ASC) AS r_score,   -- lower recency = better
        NTILE(5) OVER (ORDER BY frequency DESC) AS f_score,     -- higher frequency = better
        NTILE(5) OVER (ORDER BY monetary DESC) AS m_score       -- higher monetary = better
    FROM member_rfm
)
SELECT
    member_id,
    r_score, f_score, m_score,
    r_score + f_score + m_score AS total_rfm_score,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champion'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customer'
        WHEN r_score >= 4 AND f_score <= 2 THEN 'Recent Customer'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 AND m_score >= 3 THEN 'Cant Lose Them'
        WHEN r_score <= 1 THEN 'Lost'
        ELSE 'Needs Attention'
    END AS segment
FROM rfm_scored;
```

### Customer Lifetime Value (CLV)

```sql
-- Simplified CLV: historical value + projected future value
WITH member_history AS (
    SELECT
        member_id,
        MIN(order_date) AS first_purchase,
        MAX(order_date) AS last_purchase,
        COUNT(DISTINCT order_id) AS total_orders,
        SUM(order_amount) AS total_spent,
        AVG(order_amount) AS avg_order_value,
        DATE_DIFF(MAX(order_date), MIN(order_date), MONTH) + 1 AS active_months
    FROM orders.transactions
    GROUP BY 1
)
SELECT
    member_id,
    total_spent AS historical_clv,
    SAFE_DIVIDE(total_spent, active_months) AS monthly_value,
    -- Projected 12-month CLV
    SAFE_DIVIDE(total_spent, active_months) * 12 AS projected_12m_clv,
    -- Acquisition cost payback period
    SAFE_DIVIDE(65.0, SAFE_DIVIDE(total_spent, active_months)) AS months_to_payback  -- $65 = Costco membership fee
FROM member_history;
```

---

## 3. Attribution Models

Attribution answers: "Which marketing touchpoints deserve credit for a conversion?"

### Attribution Models Explained

```
User Journey: Email → Ignore → Google Ad → Click → Facebook Ad → Purchase

Last Touch:     Email  0%   |  Google Ad  0%   |  Facebook Ad 100%
First Touch:    Email 100%  |  Google Ad  0%   |  Facebook Ad   0%
Linear:         Email 33%   |  Google Ad 33%   |  Facebook Ad  33%
Time Decay:     Email 17%   |  Google Ad 33%   |  Facebook Ad  50%  (more recent = more credit)
Position Based: Email 40%   |  Google Ad 20%   |  Facebook Ad  40%  (first+last = 40% each)
Data-Driven:    Computed by ML based on actual conversion lift per channel
```

### SQL Implementation: Linear Attribution

```sql
-- Assign equal credit to all touchpoints in a conversion path
WITH conversion_paths AS (
    SELECT
        session_id,
        user_id,
        campaign_id,
        channel,
        event_type,
        event_timestamp,
        -- Find the conversion timestamp for this session
        MAX(CASE WHEN event_type = 'conversion' THEN event_timestamp END) 
            OVER (PARTITION BY session_id) AS conversion_time,
        MAX(CASE WHEN event_type = 'conversion' THEN revenue END)
            OVER (PARTITION BY session_id) AS conversion_revenue
    FROM silver.ad_events
    WHERE event_date BETWEEN '2024-01-01' AND '2024-01-31'
),
touchpoints_before_conversion AS (
    SELECT
        session_id,
        user_id,
        campaign_id,
        channel,
        conversion_revenue,
        COUNT(*) OVER (PARTITION BY session_id) AS total_touchpoints
    FROM conversion_paths
    WHERE conversion_time IS NOT NULL        -- only sessions with conversion
      AND event_type IN ('click', 'impression')
      AND event_timestamp < conversion_time  -- only pre-conversion touchpoints
),
linear_attribution AS (
    SELECT
        session_id,
        campaign_id,
        channel,
        -- Linear: divide revenue equally among all touchpoints
        SAFE_DIVIDE(conversion_revenue, total_touchpoints) AS attributed_revenue,
        SAFE_DIVIDE(1.0, total_touchpoints) AS attributed_conversion_credit
    FROM touchpoints_before_conversion
)
SELECT
    channel,
    campaign_id,
    COUNT(DISTINCT session_id) AS attributed_conversions_approx,
    ROUND(SUM(attributed_conversion_credit), 2) AS attributed_conversions,
    ROUND(SUM(attributed_revenue), 2) AS attributed_revenue
FROM linear_attribution
GROUP BY 1, 2
ORDER BY attributed_revenue DESC;
```

---

## 4. Identity Resolution in MarTech

### The Identity Problem

A single person interacts with Costco as:
- **Authenticated member**: member_id = 12345678 (logged in)
- **Anonymous web visitor**: cookie_id = abc-123 (not logged in)
- **Mobile app user**: IDFA = xyz-789 (iOS device)
- **Email recipient**: email = john@example.com (hashed)
- **In-store buyer**: loyalty card swipe → member_id

**Identity resolution** = stitching these identifiers into a single unified profile.

### Identity Graph Architecture

```python
# Identity graph: edges between identifiers that belong to the same person
# Stored in AlloyDB for real-time lookup, BigQuery for analytics

# Node: an identifier (member_id, cookie_id, email_hash, device_id)
# Edge: "these two identifiers belong to the same person" (with confidence score)

# Example: user logs in on web → we know cookie_id maps to member_id
# INSERT INTO identity_graph (id1, id1_type, id2, id2_type, confidence, source)
# VALUES ('cookie_abc123', 'COOKIE', '12345678', 'MEMBER_ID', 1.0, 'login_event')

# Graph traversal: given any identifier, find all linked identifiers
-- BigQuery: find all identifiers for a given member
WITH RECURSIVE identity_chain AS (
    -- Anchor: start from known member_id
    SELECT id1 AS identifier, id1_type AS id_type, 0 AS depth
    FROM identity_graph
    WHERE id2 = '12345678' AND id2_type = 'MEMBER_ID'
    
    UNION ALL
    
    -- Recursive: follow edges
    SELECT g.id2, g.id2_type, c.depth + 1
    FROM identity_graph g
    INNER JOIN identity_chain c ON g.id1 = c.identifier
    WHERE c.depth < 3  -- max 3 hops
)
SELECT DISTINCT identifier, id_type FROM identity_chain;
```

---

## 5. Cookie Deprecation & Privacy Changes

### What Changed and Why It Matters

**Third-party cookies** (set by advertisers/ad networks on publisher sites) have been the backbone of cross-site tracking, retargeting, and attribution for 20+ years.

**What happened:**
- Safari (Apple): Blocked 3P cookies since 2017 (ITP)
- Firefox: Blocked 3P cookies since 2019
- Chrome: Extended deadline multiple times; now pursuing Privacy Sandbox

**Impact on MarTech data pipelines:**
- Retargeting audiences shrink (can't track users across sites)
- Attribution models break (can't follow click → purchase across domains)
- Frequency capping fails (same user served 50x as unrecognized)
- Measurement gaps (conversion tracking incomplete)

### Solutions and Alternatives

| Solution | How It Works | Data Engineering Implication |
|----------|--------------|------------------------------|
| **First-party data** | Collect data directly from your owned properties (logged-in users) | Invest in member login flows, enrich member profiles |
| **Server-side tracking** | Send events from your server to ad platforms, bypassing browser restrictions | Build server-to-server event pipelines (Pub/Sub → Dataflow → Conversions API) |
| **Hashed email matching** | Share SHA256(email) with ad platforms to match users | Build email hashing pipelines for upload to Google/Meta Customer Match |
| **Privacy Sandbox** | Google's browser-based API (TOPICS, FLEDGE) for targeting without cross-site tracking | Adapt measurement to aggregate cohort-level signals vs user-level |
| **Clean rooms** | Secure multi-party computation (BigQuery Ads Data Hub, LiveRamp) | Enable advertisers to join their data with publisher data without sharing PII |

### BigQuery as a Clean Room (Ads Data Hub)

```sql
-- Ads Data Hub (ADH): Google's clean room
-- Advertisers can query their campaign data joined to Google's signals
-- without accessing individual user data

-- Example: join Costco's conversion data with Google's impression data
-- to compute incrementality (would users have converted without the ad?)
-- This runs in an isolated environment — Google never sees your conversion data
-- Costco never sees Google's individual user data

-- The output: aggregate metrics only, never individual rows
```

---

## 6. Costco-Specific Context

### Costco's Business Model Implications for Data

**Membership-based model:**
- ~128M members globally — known, authenticated users with purchase history
- Membership fee ($65/$130/year) = primary profit driver (not merchandise margin)
- Member data is extraordinarily rich: purchase history + web behavior + app usage
- This means Costco has **first-party data advantage** most retailers don't have

**Key data engineering implications:**
- Member ID is the golden key — everything resolves to member_id
- Cohort analysis is powerful: can compare behavior of members by join date, tier, region
- Personalization ROI is measurable: can attribute member purchases to specific campaigns
- Privacy stakes are high: members trust Costco with their data → CCPA/GDPR compliance critical

**Operational scale:**
- 800+ warehouses globally
- Costco.com: one of the top 10 US e-commerce sites by revenue
- Typical traffic: 30M+ website visits/month
- Marketing channels: email (80M+ subscribers), display, search, social, in-store

**Data challenges specific to Costco:**
1. **Multi-channel attribution**: member sees email → searches → buys in-store or online
2. **Basket size normalization**: $1000 TV vs $5 bananas — different campaign ROI math
3. **Seasonality**: Q4 (Thanksgiving, Christmas) dramatically skews all metrics
4. **Membership cohort effects**: New members buy differently than 10-year members

---

## 7. Behavioral Interview Framework

### The STAR Method (for Sr. DE level)

At Senior level, interviewers want to hear:
- **Scale**: How large was the problem? (petabytes, teams, revenue impact)
- **Complexity**: Was it technically hard? What tradeoffs did you make?
- **Ownership**: Did you drive it, or just participate?
- **Impact**: What actually changed? (metrics, latency, cost, reliability)

**Enhanced STAR for technical roles:**

```
S — Situation: Context (team, company, scale, what was broken/missing)
T — Task: What was your specific responsibility? What were the constraints?
A — Action: Step-by-step what YOU did (use "I" not "we", be specific about technical choices)
R — Result: Quantified outcome + what you learned + what you'd do differently
```

**Common mistakes:**
- Using "we" instead of "I" — interviewer can't tell what your contribution was
- Missing the technical depth — describe the architecture, not just "built a pipeline"
- No quantified result — "it was better" is not a result
- Not addressing the failure or tradeoff — shows maturity when you say "in hindsight, I'd have done X differently"

---

## 8. STAR Answers — Technical Leadership

### "Tell me about a complex data pipeline you designed."

**S:** At Wells Fargo, we had 60+ application teams migrating to GCP, each running ad-hoc migration scripts with no centralized visibility. Engineering leadership had no way to track progress — they were getting conflicting status reports from teams, and the migration timeline was at risk.

**T:** I was tasked with designing CDM Next — a configuration-driven, cloud-native data movement platform that would replace all those ad-hoc scripts with a single, observable system. The constraints were: couldn't change source systems, had to support GCS, BigQuery, Spanner, AlloyDB as targets, had to be adopted by 60+ teams with minimal friction, and had to be production-ready in 6 months.

**A:** I designed the architecture around three principles: configuration over code (teams submit YAML, no pipeline code), observability-first (every run emits structured logs and metrics), and idempotency (every run safe to re-execute). Technically: Cloud Composer orchestrated jobs, Dataflow handled the actual data movement (Beam pipelines generated from YAML configs), Cloud DLP ran PII detection on every load, and Dataplex managed cataloging. I wrote the core YAML-to-Beam transpiler in Python — parsing config to generate the right PTransforms dynamically. I also built the monitoring layer: every job published metrics to Cloud Monitoring, and I built a Looker dashboard for migration status across all 60 teams. For team adoption, I ran 12 enablement sessions and created a self-service onboarding portal.

**R:** We onboarded 60+ teams in 5 months. The platform processed over 15 petabytes of data in its first year. Incident rate dropped 40% compared to the ad-hoc approach because idempotent design meant re-runs were safe. Throughput improved 60% because Dataflow's autoscaling handled burst loads better than the fixed-size Spark clusters teams were running before. Most importantly, leadership had a single dashboard showing migration progress in real-time — that visibility alone changed the executive conversations.

---

### "Tell me about a time you improved pipeline performance."

**S:** Our daily attribution pipeline at Wells Fargo was taking 4.5 hours to run, which meant marketing didn't have attribution results until 10:30am — too late to adjust campaign budgets for the day.

**T:** My goal was to bring it under 2 hours. I owned the Spark-based pipeline running on Dataproc.

**A:** First, I profiled with Spark History Server. Found two bottlenecks: (1) A cross-join between 500M events and 2M member profiles was causing a 300GB shuffle. (2) A specific campaign_id (our highest-spend campaign) had 40% of all events, causing extreme data skew in the GroupByKey stage — one task ran for 90 minutes while all others finished in 5 minutes. Fix for (1): Pre-filter events by date partition before the join, reducing the events dataset from 500M to 80M rows (we only needed yesterday's events). Fix for (2): Salted key approach — I appended a random integer 0-99 to the hot campaign_id, ran a partial aggregation, stripped the suffix, and did a final merge. This distributed the work across 100 tasks instead of 1. Additionally, enabled AQE (Adaptive Query Execution) with `spark.sql.adaptive.skewJoin.enabled=true` to handle future skew automatically.

**R:** Pipeline runtime dropped from 4.5 hours to 1h 45min — a 61% reduction. Marketing team now has attribution data by 7:30am. The skew fix alone saved 60 minutes. I documented the profiling approach and added a "check for skew" step to our pipeline review checklist.

---

## 9. STAR Answers — Conflict & Collaboration

### "Tell me about a time you disagreed with a technical decision."

**S:** Early in the CDM Next project, a senior architect proposed using a monolithic Dataproc cluster with a fixed 50-node config for all data movement jobs — reasoning that a fixed cluster was simpler to manage and would always have capacity.

**T:** I believed this approach would be expensive (idle cluster 20 hours/day) and would create resource contention (all 60 teams competing for the same 50 nodes). My job was to make my case without damaging the relationship with a more senior colleague.

**A:** I didn't push back in the initial meeting — that would have been territorial. Instead, I ran a cost model: fixed 50-node cluster at $0.48/node-hour = $17,280/month at 100% uptime vs ephemeral clusters = ~$8,000/month with typical utilization. I also ran a simulation showing that with 60 teams submitting jobs at the same hour (morning batch), a 50-node fixed cluster would queue jobs for up to 2 hours. I presented this in a 1:1 with the architect first, sharing the numbers. He acknowledged the cost but was concerned about cluster startup latency. I proposed a compromise: a small persistent cluster (10 nodes) for small/ad-hoc jobs, and ephemeral clusters auto-spun by Airflow for large batch jobs. He agreed to pilot this for one quarter.

**R:** After the quarter, the hybrid approach was adopted permanently. Actual cost was $9,200/month vs the projected $17,280 — 47% savings. Cluster startup latency for large jobs was ~4 minutes, which was acceptable given jobs ran for 45+ minutes. The architect and I still work well together and he credits the cost analysis as what changed his mind.

---

### "Tell me about a time you had to work with a difficult stakeholder."

**S:** At Wells Fargo, one of the 60 application teams on CDM Next had a tech lead who was resistant to adopting the platform. He was vocal in leadership meetings that "CDM is forcing us to change our working code for no benefit" and was influencing other teams to delay adoption.

**T:** I needed to bring this team on board — their migration was on the critical path and leadership was watching.

**A:** I requested a 1:1 with the tech lead. Rather than defending CDM Next, I asked him to walk me through his existing pipeline and what concerns he had. Two things emerged: (1) his team's pipeline had a complex custom deduplication logic that he didn't think CDM could support; (2) he'd seen another team's migration cause a 3-day data outage and was worried about risk. I acknowledged both concerns as legitimate. For (1), I spent two days building a custom transform plugin for CDM Next specifically for his deduplication pattern — it only took 200 lines of Python. For (2), I proposed a parallel run: run both old and CDM Next pipelines simultaneously for 2 weeks, compare outputs daily, only cut over when he was confident. I also offered to be on-call personally during the migration.

**R:** The team migrated 3 weeks later. The parallel run actually found a pre-existing bug in their original pipeline — CDM was more accurate. The tech lead became an advocate and mentioned CDM in a company-wide engineering all-hands. That endorsement accelerated adoption across 8 other holdout teams.

---

## 10. STAR Answers — Impact & Scale

### "What's the highest-impact project you've worked on?"

Use CDM Next — it's an extraordinary project.

**S/T:** (Same as "complex pipeline" above — reference it)

**A → impact framing:**
The most impactful thing wasn't the technical work — it was changing how 60 engineering teams thought about data migration. Before CDM Next, each team ran their own bespoke scripts with no visibility, no quality gates, and no consistency. I designed CDM Next not just as a pipeline tool but as an engineering standard.

Key decisions that drove adoption: (1) Configuration over code — the barrier to onboard was 30 minutes, not weeks. (2) I built an internal "migration health" dashboard that was presented in weekly leadership meetings — this created positive competitive pressure: teams that hadn't adopted yet could see other teams progressing. (3) I created a Slack bot that posted daily summaries of each team's pipeline health — this normalized data quality as a team responsibility.

**R:** 15+ petabytes migrated. 60 teams using a consistent platform. 40% reduction in data incidents. But the number I'm most proud of: 6 teams that were originally 6-12 months behind their migration targets are now on schedule, because CDM Next removed the need for them to build and maintain pipeline infrastructure themselves.

---

## 11. STAR Answers — Failure & Learning

### "Tell me about a time you made a mistake."

**S:** Early in my career at TCS, I was responsible for a batch ETL that loaded daily sales data into a data warehouse. I made a change to the date filtering logic in the transformation — changing from `>=` to `>` in a WHERE clause — which seemed like a bug fix.

**T:** The change went into production without a proper code review — I was confident it was correct and under time pressure to deploy.

**A:** The next morning, the sales dashboard showed a 15% drop in same-day revenue. The finance team escalated within 30 minutes. I immediately checked the pipeline logs, found the filter change, and realized it was excluding the start boundary date — a full day's data was missing from every partition going back 6 months (because the pipeline had run in backfill mode). I reverted the change and wrote a one-time backfill script. The fix took 4 hours; the dashboard was corrected by noon.

**R:** No data was permanently lost — just temporarily unavailable. But the incident cost the team credibility with the finance stakeholders and triggered a 2-week audit. What I changed after: I wrote our team's first data pipeline testing protocol — every transformation change must have a before/after row count validation and a smoke test on 1 week of historical data. I also implemented a data reconciliation check (pipeline output rows ≈ source rows ± 5%) that runs after every load and alerts before the business users see the data. Three years later, that protocol had caught 6 potential production incidents before they became incidents.

---

## 12. Questions to Ask the Panel

Good questions signal curiosity, strategic thinking, and that you're evaluating them too.

### For Vincenzo or Pawel (Technical Leadership):

1. **"What does the current data pipeline stack look like, and what are the biggest pain points you're hoping to solve with this hire?"**
   → Shows you want to understand the real problem, not just the job description.

2. **"How does the MarTech engineering team collaborate with the marketing stakeholders on data requirements? Who defines the source of truth for metrics like ROAS?"**
   → Shows awareness that technical and business alignment is a real challenge.

3. **"What's the maturity level of DBT adoption here — is the team already using it in production, or is this a greenfield implementation?"**
   → Critical for you — need to understand how much DBT onboarding is expected.

4. **"What does success look like for this role in the first 90 days vs first year?"**
   → Shows you're results-oriented and want clarity on expectations.

5. **"How does Costco think about first-party data strategy given the cookie deprecation changes?"**
   → Shows MarTech domain awareness and strategic thinking.

### For HR / Final Round:

6. **"What are the most common reasons engineers thrive at Costco's GCC, versus reasons they find it challenging?"**
   → Honest question that surfaces culture fit signals.

7. **"What does the career progression look like for a Senior Data Engineer — is there a defined path to Principal/Staff Engineer?"**
   → Shows ambition, appropriate for the level.

---

## 13. Interview Strategy & Mindset

### Before the Interview

**Research:**
- Read Costco's Q4 2023 / Q1 2024 earnings calls — understand their e-commerce growth, membership metrics, technology investment narrative
- Look up the JD again and map every skill mentioned to one of your STAR stories
- LinkedIn: check Vincenzo and Pawel's profiles — their previous roles tell you what frameworks and approaches they value

**Technical preparation:**
- Be ready to whiteboard a Pub/Sub → Dataflow → BigQuery real-time pipeline
- Know the MarTech metrics cold: CTR, CVR, CPA, ROAS — not just definitions but how to query them
- Be ready to discuss the 3 BigQuery optimization techniques you use most

### During the Interview

**The consultative posture:**
Don't just answer questions — show you think about the business problem first.
- "Before I answer — can I ask, are you dealing with this at the impression level or the session level? That changes the approach."
- This signals Senior+ thinking: understanding context before jumping to solutions.

**Anchoring to impact:**
Every technical answer should end with the business outcome.
- Not: "I implemented partitioning on the BigQuery table."
- But: "I implemented date partitioning on the BigQuery table, which reduced query costs by 70% and brought dashboard load time from 45 seconds to 3 seconds — the marketing team could now use the dashboard in live client meetings, which wasn't possible before."

**The DBT gap:**
You don't have production DBT experience. When it comes up:
- "I haven't used DBT in a production context, but I've been studying it intensively. I understand the core concepts: models as SELECT statements, ref() for DAG dependencies, tests for data quality, and the ELT philosophy of pushing transformations to the warehouse. What's the team using DBT for specifically — is it primarily the transformation layer for silver-to-gold, or are you also using dbt tests as your quality gate?"
- This shows: honesty, initiative, and the habit of turning a weakness into a question that demonstrates domain understanding.

**Closing:**
End every interview round with:
"I'm genuinely excited about this role — the intersection of MarTech and GCP is exactly where I want to build expertise, and from what I've heard, the scale of Costco's member data presents challenges that are technically interesting. Is there anything about my background that gives you pause or that you'd like me to elaborate on?"

This shows confidence + openness to feedback, and often surfaces objections you can address before the room deliberates.

---

*End of Topic 10 — Behavioral, Leadership & MarTech Domain Knowledge*
