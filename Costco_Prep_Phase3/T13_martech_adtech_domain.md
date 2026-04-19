# Topic 13: MarTech / AdTech Domain
## Costco Sr. Data Engineer — Exhaustive Interview Textbook

---

## Table of Contents
1. [L1: Core Concepts — CDP, DMP, DSP, Tracking](#l1-core-concepts)
2. [L2: Deep Technical Understanding](#l2-deep-technical-understanding)
3. [L3: Real-World Scenarios — Costco/MarTech Style](#l3-real-world-scenarios)
4. [L4: Hands-On Metrics & Code](#l4-hands-on-metrics--code)
5. [L5: Edge Cases & Pitfalls](#l5-edge-cases--pitfalls)
6. [L6: Interview Questions — Easy to Very Hard](#l6-interview-questions)

---

## L1: Core Concepts

### 1.1 The MarTech/AdTech Ecosystem

Understanding this ecosystem is critical for the Costco role. Costco uses these systems to run targeted advertising campaigns and measure their effectiveness.

```
DATA SOURCES                    MANAGEMENT                    ACTIVATION
──────────────────────────────  ───────────────────────────  ─────────────────────
• Website behavior              CDP                          Ad Platforms
• App events                    (Customer Data Platform)     • Google Ads
• Purchase history              └── Unified member profiles  • Meta Ads
• Loyalty program                   + behavioral data        • TikTok
• Email interactions                                         • Display/Programmatic
• Call center                   DMP
• Third-party data              (Data Management Platform)   
                                └── Audience segments        DSP
                                    + lookalike modeling     (Demand-Side Platform)
                                                             └── Programmatic buying
                                                                 across exchanges
MEASUREMENT
────────────────────────────────────────────────────────────────────────────────
• Attribution models (last-touch, multi-touch)
• ROAS, CTR, CPM, CPC, CPA, CVR, LTV
• Incrementality testing (holdout groups)
• A/B testing
• Campaign analytics (BigQuery + DBT + Looker)
```

### 1.2 Key Platform Definitions

**CDP (Customer Data Platform)**:
- Collects and unifies customer data from all touchpoints into a single profile
- Persistent, addressable customer database
- Used by: marketing to understand full customer journey
- Examples: Segment, mParticle, Google Analytics 4
- Key capability: identity resolution (matching anonymous browser ID to known member)

**DMP (Data Management Platform)**:
- Aggregates and segments audience data for advertising
- Primarily for third-party data and anonymous audiences
- Short data retention (90 days typical) — cookie-based
- Examples: Adobe Audience Manager, Oracle BlueKai
- Declining importance due to cookie deprecation

**DSP (Demand-Side Platform)**:
- Automated system for buying digital advertising
- Connects advertisers to multiple ad exchanges via real-time bidding (RTB)
- Examples: Google DV360, The Trade Desk, Amazon DSP
- Key capability: target specific audiences across thousands of websites simultaneously

**Ad Exchange**:
- Marketplace where publishers sell ad inventory and advertisers buy it
- Transactions happen via RTB in milliseconds
- Examples: Google Ad Exchange, Index Exchange, OpenX

**SSP (Supply-Side Platform)**:
- Platform used by publishers to sell their ad inventory
- Connects to multiple DSPs/ad exchanges to maximize yield
- Examples: Google Ad Manager, Magnite

---

### 1.3 Campaign Types and Their Data Signatures

| Campaign Type | Goal | Targeting | Measurement Focus |
|--------------|------|-----------|------------------|
| **Brand awareness** | Increase brand recognition | Broad audience, demographics | Reach, frequency, impressions |
| **Prospecting** | Acquire new customers | Lookalike audiences, interest targeting | CPA, CVR, new member count |
| **Retargeting** | Re-engage past visitors | People who visited site/app but didn't convert | ROAS, CVR, revenue |
| **Retention** | Keep existing members engaged | Existing members by segment | Repeat purchase rate, LTV |
| **Conquest** | Steal customers from competitors | Competitor brand keywords | Share of voice, new member CPA |

---

### 1.4 The Ad Delivery Lifecycle

```
User opens app/website
    ↓
Publisher sends bid request to SSP (contains: user cookies/ID, page content, ad slot size)
    ↓
SSP sends bid request to multiple DSPs via Real-Time Bidding (RTB) — takes < 100ms total
    ↓
DSP (e.g., Costco's DV360) evaluates:
  • Does this user match any of our target audiences?
  • What is our bid for this impression?
  ↓
DSP submits bid (or passes)
    ↓
Highest bidder wins the auction (usually second-price: pay 2nd highest + $0.01)
    ↓
Winning ad creative is served to user → IMPRESSION recorded
    ↓
User clicks on ad → CLICK recorded (with: gclid, campaign_id, ad_group_id, keyword)
    ↓
User lands on Costco website → LANDING PAGE VIEW recorded
    ↓
User makes purchase → CONVERSION recorded
    ↓
All events joined in BigQuery for attribution and reporting
```

---

## L2: Deep Technical Understanding

### 2.1 Tracking Events — Clickstream Architecture

```
User clicks Google Ad
    ↓
Google appends gclid parameter to URL:
  costco.com/?gclid=CjwKCAjw...&utm_source=google&utm_medium=cpc&utm_campaign=summer_sale
    ↓
Costco website's Google Tag Manager fires multiple tags:
  • Google Ads conversion tag (fire on purchase confirmation page)
  • GA4 tag (fire on every pageview, add-to-cart, purchase)
  • Segment track() call (fire custom events to CDP)
    ↓
Events flow to:
  GA4 → BigQuery Export (raw_events table)
  Segment → Costco's custom event stream → Pub/Sub → Dataflow → BigQuery
  Google Ads → Conversion Import (Costco sends conversion data back to Google)
```

**UTM Parameters** (critical for attribution):
```
utm_source   = where the traffic came from (google, meta, email, organic)
utm_medium   = marketing channel (cpc, display, social, email)
utm_campaign = campaign name/id (summer_sale_2024)
utm_content  = creative variant (banner_v1, banner_v2 — for A/B testing)
utm_term     = keyword that triggered the ad (for search campaigns)

Example: costco.com/membership?utm_source=meta&utm_medium=social&utm_campaign=member_acquisition_q3
```

**Event schema** (standard clickstream event):
```json
{
  "event_id": "evt_abc123",
  "event_type": "purchase",
  "session_id": "sess_xyz789",
  "user_id": "M001234",           // member ID if logged in
  "anonymous_id": "anon_abcd",    // cookie-based, always present
  "occurred_at": "2024-01-15T14:23:07Z",
  "properties": {
    "page_url": "https://costco.com/checkout/confirmation",
    "order_id": "ORD-2024-001234",
    "order_value_usd": 124.99,
    "items": [
      {"sku": "ITEM-001", "qty": 2, "price": 39.99},
      {"sku": "ITEM-002", "qty": 1, "price": 44.99}
    ]
  },
  "context": {
    "campaign": {
      "source": "google",
      "medium": "cpc",
      "name": "summer_sale_search",
      "term": "costco membership"
    },
    "device": {"type": "mobile", "os": "iOS"},
    "ip": "192.168.1.1",
    "user_agent": "Mozilla/5.0..."
  }
}
```

---

### 2.2 Attribution Models — Deep Technical Understanding

Attribution determines which marketing touchpoints get credit for a conversion.

#### 2.2.1 Rule-Based Attribution Models

```sql
-- Complete attribution model comparison in SQL

WITH touchpoints AS (
    SELECT
        conversion_id,
        user_id,
        conversion_value_usd,
        channel,
        clicked_at,
        converted_at,
        TIMESTAMP_DIFF(converted_at, clicked_at, HOUR) AS hours_before_conv,
        ROW_NUMBER() OVER (
            PARTITION BY conversion_id ORDER BY clicked_at ASC
        ) AS touch_num,
        ROW_NUMBER() OVER (
            PARTITION BY conversion_id ORDER BY clicked_at DESC
        ) AS touch_num_rev,
        COUNT(*) OVER (PARTITION BY conversion_id) AS total_touches
    FROM conversion_touchpoints
    WHERE clicked_at >= TIMESTAMP_SUB(converted_at, INTERVAL 30 DAY)
),

attribution_weights AS (
    SELECT
        *,

        -- ================================================
        -- LAST-TOUCH: 100% credit to the last click
        -- Favors bottom-of-funnel channels (search, brand)
        -- Most commonly used (Google default)
        -- ================================================
        CASE WHEN touch_num_rev = 1 THEN 1.0 ELSE 0.0 END
            AS last_touch_weight,

        -- ================================================
        -- FIRST-TOUCH: 100% credit to the first click
        -- Favors top-of-funnel channels (display, social prospecting)
        -- ================================================
        CASE WHEN touch_num = 1 THEN 1.0 ELSE 0.0 END
            AS first_touch_weight,

        -- ================================================
        -- LINEAR: equal credit to all touches
        -- More fair but treats all touches equally
        -- ================================================
        1.0 / total_touches AS linear_weight,

        -- ================================================
        -- TIME-DECAY: more credit to recent touches
        -- Half-life = 7 days (168 hours)
        -- ================================================
        POW(0.5, hours_before_conv / 168.0)
        / SUM(POW(0.5, hours_before_conv / 168.0)) OVER (PARTITION BY conversion_id)
            AS time_decay_weight,

        -- ================================================
        -- U-SHAPED (POSITION-BASED): 40% first, 40% last, 20% middle
        -- Recognizes that first and last touches are most important
        -- ================================================
        CASE
            WHEN total_touches = 1 THEN 1.0
            WHEN touch_num = 1 AND total_touches > 1 THEN 0.4
            WHEN touch_num_rev = 1 AND total_touches > 1 THEN 0.4
            ELSE 0.2 / GREATEST(total_touches - 2, 1)
        END AS u_shaped_weight

    FROM touchpoints
)

SELECT
    channel,
    COUNT(DISTINCT conversion_id) AS conversions,
    SUM(conversion_value_usd * last_touch_weight)   AS last_touch_revenue,
    SUM(conversion_value_usd * first_touch_weight)  AS first_touch_revenue,
    SUM(conversion_value_usd * linear_weight)       AS linear_revenue,
    SUM(conversion_value_usd * time_decay_weight)   AS time_decay_revenue,
    SUM(conversion_value_usd * u_shaped_weight)     AS u_shaped_revenue
FROM attribution_weights
GROUP BY channel
ORDER BY last_touch_revenue DESC;
```

#### 2.2.2 Data-Driven Attribution (Algorithmic)

Data-driven attribution uses ML to assign credit based on which touchpoints actually causally contribute to conversions.

```python
# Simplified Markov chain attribution
# Concept: for each channel, remove it from all paths and measure the
# "removal effect" on conversion probability

def markov_attribution(paths: list[tuple]) -> dict:
    """
    paths: list of (channel_list, converted_flag) tuples
    e.g., (['google_search', 'meta_display', 'email'], True)
    """
    # Step 1: Build transition probabilities between states
    transitions = defaultdict(lambda: defaultdict(int))
    for channel_path, converted in paths:
        states = ['start'] + list(channel_path) + ['conversion' if converted else 'null']
        for i in range(len(states) - 1):
            transitions[states[i]][states[i+1]] += 1

    # Step 2: Compute overall conversion probability
    base_conversion_rate = compute_conversion_rate(transitions)

    # Step 3: For each channel, compute removal effect
    channel_credits = {}
    for channel in all_channels:
        # Remove channel from all paths
        paths_without_channel = remove_channel(paths, channel)
        transitions_without = build_transitions(paths_without_channel)
        rate_without = compute_conversion_rate(transitions_without)

        # Removal effect = how much conversion rate drops without this channel
        removal_effect = base_conversion_rate - rate_without
        channel_credits[channel] = removal_effect

    # Normalize to sum to 1
    total = sum(channel_credits.values())
    return {ch: credit/total for ch, credit in channel_credits.items()}
```

---

### 2.3 Campaign Metrics — Complete Reference

```sql
-- All standard AdTech metrics with formulas and interpretations

SELECT
    report_date,
    campaign_id,
    campaign_name,
    channel,

    -- ============================================================
    -- VOLUME METRICS
    -- ============================================================
    impressions,                            -- times ad was shown
    clicks,                                 -- times ad was clicked
    conversions,                            -- purchases/sign-ups attributed
    spend_usd,                              -- money spent on ads
    revenue_usd,                            -- revenue from attributed conversions

    -- ============================================================
    -- RATE METRICS
    -- ============================================================
    -- CTR: Click-Through Rate = clicks / impressions
    -- Industry average: 0.1% (display), 2-5% (search)
    ROUND(SAFE_DIVIDE(clicks, impressions) * 100, 4)        AS ctr_pct,

    -- CVR: Conversion Rate = conversions / clicks
    -- Higher = more effective landing page + offer
    ROUND(SAFE_DIVIDE(conversions, clicks) * 100, 4)        AS cvr_pct,

    -- View-Through CVR: conversions / impressions (all impressions, not just clicks)
    -- Used for awareness campaigns (user saw ad, later converted)
    ROUND(SAFE_DIVIDE(conversions, impressions) * 100, 6)   AS view_cvr_pct,

    -- ============================================================
    -- COST METRICS
    -- ============================================================
    -- CPM: Cost Per Mille (per 1000 impressions)
    -- Measures efficiency of ad delivery
    ROUND(SAFE_DIVIDE(spend_usd, impressions) * 1000, 4)    AS cpm_usd,

    -- CPC: Cost Per Click
    -- How much each click costs
    ROUND(SAFE_DIVIDE(spend_usd, clicks), 4)                AS cpc_usd,

    -- CPA: Cost Per Acquisition (cost per conversion)
    -- Primary KPI for performance marketing
    ROUND(SAFE_DIVIDE(spend_usd, conversions), 4)           AS cpa_usd,

    -- ============================================================
    -- REVENUE METRICS
    -- ============================================================
    -- ROAS: Return on Ad Spend = revenue / spend
    -- ROAS of 4 = $4 revenue per $1 spent
    -- NOT the same as ROI (ROAS ignores COGS and other costs)
    ROUND(SAFE_DIVIDE(revenue_usd, spend_usd), 4)           AS roas,

    -- Profit: revenue - spend (gross, ignoring COGS)
    revenue_usd - spend_usd                                 AS gross_profit_usd,

    -- ROAS margin: (revenue - spend) / revenue
    ROUND(SAFE_DIVIDE(revenue_usd - spend_usd, revenue_usd) * 100, 2) AS roas_margin_pct,

    -- ============================================================
    -- REACH & FREQUENCY
    -- ============================================================
    unique_reach,                           -- unique users who saw the ad
    ROUND(SAFE_DIVIDE(impressions, unique_reach), 2) AS avg_frequency,  -- how often each user saw it
    -- High frequency (>5-7): ad fatigue risk, wasted spend
    -- Low frequency (<1.5 for awareness): not enough exposure

    -- ============================================================
    -- ENGAGEMENT (video campaigns)
    -- ============================================================
    video_views,
    ROUND(SAFE_DIVIDE(video_views, impressions) * 100, 2)   AS vtr_pct  -- View-Through Rate

FROM mart_campaign_performance
WHERE report_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
ORDER BY spend_usd DESC;
```

---

### 2.4 Member LTV and Segmentation

```sql
-- LTV calculation using historical purchase data

WITH purchase_history AS (
    SELECT
        member_id,
        COUNT(DISTINCT transaction_id)                  AS total_purchases,
        SUM(transaction_amount_usd)                     AS total_spend_usd,
        AVG(transaction_amount_usd)                     AS avg_order_value,
        MIN(transaction_date)                           AS first_purchase_date,
        MAX(transaction_date)                           AS last_purchase_date,
        DATE_DIFF(CURRENT_DATE(), MAX(transaction_date), DAY) AS days_since_last_purchase,
        DATE_DIFF(MAX(transaction_date), MIN(transaction_date), DAY) + 1 AS customer_tenure_days,
        -- Purchase frequency: purchases per month of tenure
        COUNT(DISTINCT transaction_id) * 30.0
            / NULLIF(DATE_DIFF(MAX(transaction_date), MIN(transaction_date), DAY), 0)
            AS monthly_purchase_rate
    FROM member_transactions
    WHERE transaction_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 YEAR)
    GROUP BY member_id
),

ltv_calculated AS (
    SELECT
        *,
        -- Simple LTV: avg order value × monthly frequency × expected months remaining
        -- Assumes 3-year customer lifetime on average
        avg_order_value * monthly_purchase_rate * (36 - customer_tenure_days / 30.0)
            AS projected_ltv_usd,

        -- Historical LTV: simply total spend so far
        total_spend_usd AS historical_ltv_usd,

        -- RFM Scoring
        NTILE(5) OVER (ORDER BY days_since_last_purchase ASC) AS recency_score,
        NTILE(5) OVER (ORDER BY total_purchases ASC)          AS frequency_score,
        NTILE(5) OVER (ORDER BY total_spend_usd ASC)          AS monetary_score
    FROM purchase_history
),

segmented AS (
    SELECT
        *,
        -- Segment labels
        CASE
            WHEN recency_score >= 4 AND frequency_score >= 4 AND monetary_score >= 4
                THEN 'Champions'
            WHEN recency_score >= 3 AND frequency_score >= 3 AND monetary_score >= 3
                THEN 'Loyal Members'
            WHEN recency_score >= 4 AND frequency_score <= 2
                THEN 'New Members'
            WHEN recency_score <= 2 AND frequency_score >= 3 AND monetary_score >= 3
                THEN 'At Risk'
            WHEN recency_score <= 2 AND frequency_score >= 4 AND monetary_score >= 4
                THEN 'Cannot Lose Them'
            WHEN recency_score <= 2 AND frequency_score <= 2
                THEN 'Lost Members'
            ELSE 'Potential Loyalists'
        END AS member_segment,

        -- Segment-level marketing action
        CASE
            WHEN recency_score >= 4 AND frequency_score >= 4 THEN 'reward_and_upsell'
            WHEN recency_score <= 2 AND frequency_score >= 3 THEN 'winback_campaign'
            WHEN recency_score >= 4 AND frequency_score <= 2 THEN 'nurture_journey'
            ELSE 'standard_engagement'
        END AS recommended_action
    FROM ltv_calculated
)

SELECT * FROM segmented;
```

---

### 2.5 Incrementality Testing — The Gold Standard

Standard attribution models answer "who got credit?" — but not "did the ad cause the conversion?" A user who was going to buy anyway shouldn't be credited to the retargeting ad they saw.

**Incrementality test design**:
```python
# A/B holdout test: measure TRUE causal impact of advertising

# Setup:
# Test group (80%): shown ads normally
# Holdout group (20%): ads suppressed (or shown PSA / charity ad)
# Measurement: conversion rate difference between groups

def analyze_incrementality_test(
    test_conversions: int,
    test_users: int,
    holdout_conversions: int,
    holdout_users: int,
    ad_spend_usd: float
) -> dict:
    """
    Compute incremental ROAS and statistical significance.
    """
    test_cvr = test_conversions / test_users
    holdout_cvr = holdout_conversions / holdout_users

    # Incremental conversions = test CVR excess × test group size
    baseline_conversions = holdout_cvr * test_users  # what test group would have done without ads
    incremental_conversions = test_conversions - baseline_conversions

    # Incremental revenue
    avg_order_value = 125  # from historical data
    incremental_revenue = incremental_conversions * avg_order_value

    # Incremental ROAS
    incremental_roas = incremental_revenue / ad_spend_usd if ad_spend_usd > 0 else None

    # Statistical significance (Chi-squared test)
    from scipy import stats
    contingency = [
        [test_conversions, test_users - test_conversions],
        [holdout_conversions, holdout_users - holdout_conversions]
    ]
    chi2, p_value, _, _ = stats.chi2_contingency(contingency)

    return {
        'test_cvr': test_cvr,
        'holdout_cvr': holdout_cvr,
        'lift_pct': (test_cvr - holdout_cvr) / holdout_cvr * 100,
        'incremental_conversions': incremental_conversions,
        'incremental_revenue': incremental_revenue,
        'incremental_roas': incremental_roas,
        'p_value': p_value,
        'is_significant': p_value < 0.05
    }

# Result interpretation:
# lift_pct = 30% means ads caused 30% more conversions than would have happened organically
# incrementalROAS = 2.5 means $2.5 incremental revenue per $1 spent
# (vs standard ROAS which might show 6.0 — much of that revenue was organic)
```

---

## L3: Real-World Scenarios — Costco/MarTech Style

### 3.1 Scenario: Build the Costco Campaign Performance Dataset

**Business context**: Costco runs campaigns across Google Search, Google Display, Meta (Facebook + Instagram), and TikTok. The Marketing team needs a unified performance view to make budget allocation decisions.

**Key data engineering challenges**:
1. Each platform has different metrics and naming conventions
2. Attribution must be unified (not Google's numbers vs Meta's numbers — both claim credit)
3. Member-level linkage (which campaigns acquire Costco members?)
4. Cross-device attribution (user saw Meta ad on phone, bought on desktop)

```sql
-- Unified cross-platform performance
WITH google_perf AS (
    SELECT
        'google_search'     AS channel,
        'google'            AS platform,
        report_date,
        campaign_id,
        campaign_name,
        impressions,
        clicks,
        spend_usd,
        conversions,
        conversion_value_usd    AS revenue_usd
    FROM {{ ref('stg_google_ads__campaigns') }}
),

meta_perf AS (
    SELECT
        CONCAT('meta_', placement_type)  AS channel,  -- meta_facebook, meta_instagram
        'meta'                           AS platform,
        date_start                       AS report_date,
        campaign_id,
        campaign_name,
        reach                            AS impressions,  -- Meta calls it "reach" not "impressions"
        link_clicks                      AS clicks,
        spend                            AS spend_usd,
        actions_purchase                 AS conversions,
        action_values_purchase           AS revenue_usd
    FROM {{ ref('stg_meta_ads__insights') }}
),

tiktok_perf AS (
    SELECT
        'tiktok'            AS channel,
        'tiktok'            AS platform,
        stat_time_day       AS report_date,
        campaign_id,
        campaign_name,
        impressions,
        clicks,
        spend / 1000.0      AS spend_usd,  -- TikTok reports in milli-dollars
        conversions,
        gross_profit        AS revenue_usd
    FROM {{ ref('stg_tiktok_ads__reports') }}
),

unified AS (
    SELECT * FROM google_perf
    UNION ALL
    SELECT * FROM meta_perf
    UNION ALL
    SELECT * FROM tiktok_perf
)

SELECT
    report_date,
    platform,
    channel,
    campaign_id,
    campaign_name,
    SUM(impressions)    AS impressions,
    SUM(clicks)         AS clicks,
    SUM(spend_usd)      AS spend_usd,
    SUM(conversions)    AS conversions,
    SUM(revenue_usd)    AS revenue_usd,
    SAFE_DIVIDE(SUM(revenue_usd), SUM(spend_usd))       AS roas,
    SAFE_DIVIDE(SUM(clicks), SUM(impressions))          AS ctr,
    SAFE_DIVIDE(SUM(spend_usd), SUM(clicks))            AS cpc_usd,
    SAFE_DIVIDE(SUM(spend_usd), SUM(conversions))       AS cpa_usd
FROM unified
GROUP BY 1, 2, 3, 4, 5
ORDER BY spend_usd DESC;
```

---

### 3.2 Scenario: Cookie Deprecation — Building First-Party Data Pipeline

**The challenge**: Third-party cookies are being deprecated. Costco must build a first-party data infrastructure to replace audience targeting.

**First-party data strategy**:
```
Costco's first-party data sources:
├── Membership database (member_id, purchase history, loyalty tier)
├── Website behavior (GA4 → BigQuery)
├── App events (Firebase → BigQuery)
├── Email/SMS engagement (open rates, click rates)
└── Loyalty point transactions

Data engineering job:
1. Build Costco's CDP: unify all first-party touchpoints per member
2. Export audience segments to ad platforms via Customer Match / Enhanced Conversions
3. Measure campaign performance using member_id-based attribution (not cookies)
```

```python
# Build audience segment for Google Customer Match
# Export: list of email hashes for high-LTV at-risk members

def export_audience_to_google_ads(segment_name: str, member_segment: str):
    """
    Export member emails (hashed) to Google Ads Customer Match.
    GDPR/CCPA: only include members who've opted in to marketing.
    """
    bq = bigquery.Client()

    # Get segment members who opted in
    members = bq.query(f"""
        SELECT
            -- SHA256 hash as required by Google Customer Match
            TO_HEX(SHA256(LOWER(TRIM(email)))) AS hashed_email,
            TO_HEX(SHA256(LOWER(TRIM(phone_number)))) AS hashed_phone
        FROM dim_members m
        JOIN mart_member_ltv ltv USING (member_id)
        WHERE ltv.member_segment = '{member_segment}'
          AND m.email_marketing_opt_in = TRUE
          AND m.is_current = TRUE
    """).to_dataframe()

    # Upload to Google Ads via API
    customer_match_service = google_ads_client.get_service("CustomerMatchUserListService")
    # ... upload hashed_email list to Customer Match audience

    logger.info(f"Exported {len(members)} members to Google Ads audience: {segment_name}")
    return len(members)

# Run for at-risk members
export_audience_to_google_ads("at_risk_winback_q1", "At Risk")
```

---

## L4: Hands-On Metrics & Code

### 4.1 Complete Campaign Performance SQL

```sql
-- Comprehensive daily campaign performance with all standard metrics

SELECT
    p.report_date,
    p.campaign_id,
    c.campaign_name,
    c.channel,
    c.campaign_type,

    -- Volume
    p.impressions,
    p.clicks,
    p.conversions,
    p.spend_usd,
    p.revenue_usd,

    -- Rate metrics
    ROUND(SAFE_DIVIDE(p.clicks, p.impressions) * 100, 4)        AS ctr_pct,
    ROUND(SAFE_DIVIDE(p.conversions, p.clicks) * 100, 4)        AS cvr_pct,

    -- Cost metrics
    ROUND(SAFE_DIVIDE(p.spend_usd, p.impressions) * 1000, 4)    AS cpm_usd,
    ROUND(SAFE_DIVIDE(p.spend_usd, p.clicks), 4)                AS cpc_usd,
    ROUND(SAFE_DIVIDE(p.spend_usd, p.conversions), 2)           AS cpa_usd,

    -- Revenue metrics
    ROUND(SAFE_DIVIDE(p.revenue_usd, p.spend_usd), 4)           AS roas,

    -- Trend vs prior week
    LAG(SAFE_DIVIDE(p.revenue_usd, p.spend_usd), 7) OVER (
        PARTITION BY p.campaign_id ORDER BY p.report_date
    )                                                           AS roas_wow,

    SAFE_DIVIDE(
        SAFE_DIVIDE(p.revenue_usd, p.spend_usd) -
        LAG(SAFE_DIVIDE(p.revenue_usd, p.spend_usd), 7) OVER (
            PARTITION BY p.campaign_id ORDER BY p.report_date
        ),
        LAG(SAFE_DIVIDE(p.revenue_usd, p.spend_usd), 7) OVER (
            PARTITION BY p.campaign_id ORDER BY p.report_date
        )
    ) * 100                                                     AS roas_wow_pct_change,

    -- Budget utilization
    ROUND(SAFE_DIVIDE(p.spend_usd, c.daily_budget_usd) * 100, 2) AS budget_pct_used

FROM mart_campaign_performance p
JOIN dim_campaign c
    ON p.campaign_id = c.campaign_id
    AND p.report_date >= c.valid_from
    AND p.report_date < COALESCE(c.valid_to, '9999-12-31')
WHERE p.report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
ORDER BY p.report_date DESC, p.spend_usd DESC;
```

---

## L5: Edge Cases & Pitfalls

### 5.1 Attribution Double-Counting

```python
# THE CLASSIC PROBLEM:
# Google Ads reports: 100 conversions, $50K revenue from campaign
# Meta Ads reports:   80 conversions, $40K revenue from campaign
# Total claimed:      180 conversions, $90K revenue
# Actual revenue:     $60K
# Discrepancy: 50%!

# WHY: Both Google and Meta use their OWN last-touch attribution
# A user clicks a Meta ad, then clicks a Google ad, then buys
# → Google claims the conversion (last touch)
# → Meta ALSO claims the conversion (they had a touchpoint)

# SOLUTION: Build your own unified attribution in BigQuery
# One authoritative attribution model, not platform-reported numbers
# Use YOUR BigQuery data for budgeting decisions, not platform reports
# Platform reports = useful for platform optimization, not for total spend decisions
```

### 5.2 View-Through Conversion Inflation

```python
# Meta, TikTok, and display platforms count view-through conversions
# "User saw your ad once, then bought within 30 days" = conversion
# This massively inflates reported conversions

# Problem: most conversions that Meta claims as view-through would have happened anyway
# (users who've seen ANY ad and bought are counted as conversions)

# Check: what % of Meta conversions are view-through vs click-through?
SELECT
    attribution_setting,
    COUNT(*) AS conversions,
    SUM(conversion_value_usd) AS revenue
FROM meta_conversions
GROUP BY attribution_setting;
-- Often: 70% are view-through! (probably organic conversions, not caused by the ad)

# Solution: use only click-through conversions for ROAS calculation
# Use view-through for awareness campaign measurement only
# Set Meta conversion window to 1-day click, 0-day view for more conservative measurement
```

### 5.3 Bot Traffic and Invalid Clicks

```python
# Problem: ~10-20% of ad clicks can be from bots
# Impact: inflated click counts, inflated spend, terrible CVR

# Signs of bot traffic:
# - Sudden CTR spike (20% when industry avg is 2%)
# - Bounce rate 99% from specific traffic source
# - Conversions from display ads from unusual geographies
# - Clicks at unusual hours (e.g., 3-5 AM mass clicks)

# Detection:
def detect_bot_traffic_sql():
    return """
    WITH click_patterns AS (
        SELECT
            ip_address,
            user_agent,
            COUNT(*) AS clicks,
            COUNT(DISTINCT session_id) AS sessions,
            MIN(clicked_at) AS first_click,
            MAX(clicked_at) AS last_click,
            TIMESTAMP_DIFF(MAX(clicked_at), MIN(clicked_at), SECOND) AS span_seconds
        FROM ad_clicks
        WHERE click_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        GROUP BY 1, 2
    )
    SELECT *,
        clicks / NULLIF(span_seconds, 0) AS clicks_per_second,  -- >1/sec = suspicious
        clicks / NULLIF(sessions, 0) AS clicks_per_session      -- >5 = suspicious
    FROM click_patterns
    WHERE clicks > 10
      AND (clicks / NULLIF(span_seconds, 0) > 1  -- rapid clicking
           OR LOWER(user_agent) LIKE '%bot%'       -- declared bot
           OR LOWER(user_agent) LIKE '%crawler%'
           OR span_seconds < 5 AND clicks > 20)   -- many clicks in <5 seconds
    ORDER BY clicks DESC;
    """
```

---

## L6: Interview Questions — Easy to Very Hard

### EASY

**Q1: What is ROAS and how is it different from ROI?**

**Answer**: ROAS (Return on Ad Spend) = Revenue / Ad Spend. It measures how much revenue was generated per dollar spent on advertising. A ROAS of 4.0 means $4 of revenue per $1 of ad spend.

ROI (Return on Investment) = (Net Profit - Investment Cost) / Investment Cost. It accounts for ALL costs including COGS, overhead, and operating expenses, not just ad spend. ROI measures actual profitability.

ROAS is always higher than ROI because ROAS ignores costs. Example: Campaign spends $100K, generates $400K revenue. ROAS = 4.0. But if product COGS is 70% ($280K) and there's $50K operating overhead, net profit = $400K - $280K - $100K - $50K = -$30K. ROI = -30%. The campaign ROAS looks great but the business lost money.

For data engineering: ROAS is the primary metric reported in campaign dashboards. Senior engineers should understand this limitation and be able to build a proper contribution margin analysis when asked.

---

**Q2: What is the difference between a CDP and a DMP?**

**Answer**: A CDP (Customer Data Platform) manages first-party data — data that Costco directly collects about known customers. It builds persistent, identifiable profiles per customer using member IDs, emails, purchase history, and behavioral data. Data is personally identifiable and retained long-term.

A DMP (Data Management Platform) primarily manages anonymous, third-party data using cookies and device IDs. It's used for audience segmentation and targeting at scale — e.g., "people interested in outdoor furniture." Data is typically anonymous and retained for short periods (90 days).

The key difference: CDP = your customers, identified, first-party. DMP = anonymous audiences, cookie-based, third-party. With cookie deprecation underway, DMPs are declining in importance while CDPs are becoming more critical.

---

### MEDIUM

**Q3: Explain last-touch attribution. What are its limitations and when would you use a different model?**

**Answer**: Last-touch attribution gives 100% of the conversion credit to the final touchpoint before the conversion — typically the last ad clicked. It's the simplest model and is the default in Google Ads.

**Limitations**:
- Undervalues upper-funnel channels (brand awareness, social prospecting) that introduced the customer but got no credit
- Overvalues lower-funnel channels (branded search) that capture already-intent users
- A user who saw 10 Meta display ads, then clicked a Google branded search ad → Google gets 100%, Meta gets 0%
- Incentivizes over-investment in last-click channels, underinvestment in awareness

**Better alternatives**:
- **Linear attribution**: when all touchpoints genuinely matter equally (longer sales cycles)
- **Time-decay**: when recent touches are more valuable (impulse purchases, short consideration)
- **U-shaped (position-based)**: when both first touch (awareness) and last touch (decision) are important
- **Data-driven**: when you have enough data for ML-based attribution (>10K conversions/month)
- **Incrementality testing**: when you need causal measurement (not just correlation)

For Costco: I'd use a multi-touch model (linear or time-decay) for budget allocation reporting, and conduct periodic incrementality holdout tests to validate whether campaigns are truly driving incremental purchases vs capturing organic intent.

---

**Q4: What is incrementality testing and why is it considered the gold standard over attribution models?**

**Answer**: Incrementality testing measures whether advertising is truly CAUSING more conversions, rather than just being present when conversions happen.

Standard attribution asks: "Who got credit for this conversion?" An advertiser could show an ad to someone who was going to buy anyway — the conversion gets attributed to the ad, making ROAS look great, but the ad added zero incremental value.

Incrementality testing uses a holdout group: randomly select 20% of the target audience and suppress ads for them. Compare conversion rate of the 80% who saw ads vs the 20% who didn't. The difference is the TRUE incremental lift.

```
Test group (saw ads):   8% conversion rate
Holdout group (no ads): 6% conversion rate
Lift: (8% - 6%) / 6% = 33% incremental lift
```

This means 33% of conversions in the test group were caused by the ads. The other 67% would have happened organically.

**Why it's the gold standard**: Attribution models estimate who got credit — they can't prove causation. An ad that always appears right before purchase might have zero causal impact (the user was going to buy anyway). Incrementality testing proves causation through experimental design.

**Trade-off**: Requires holding out revenue during the test period (opportunity cost), requires statistical sample sizes, and can only test one thing at a time.

---

### HARD

**Q5: Costco's marketing team says "our Google Search ROAS is 8.0 and our Meta Display ROAS is 1.5 — we should cut Meta and double down on Google." As a senior data engineer, what questions do you ask and what analysis do you run?**

**What they're testing**: Critical thinking about attribution, channel role in funnel, incrementality.

**Answer**:

**The underlying issue**: This comparison is misleading for three reasons.

**1. Channels serve different funnel stages**
Google Search captures people who are ALREADY searching for Costco memberships — high intent, near-certain to convert. Meta Display shows ads to people who weren't thinking about Costco — creates awareness. Comparing their ROAS directly is like comparing a closing salesperson to a marketing event organizer.

```sql
-- Analyze: how many Google Search converters had a Meta touchpoint first?
SELECT
    COUNT(DISTINCT conversion_id) AS total_google_search_convs,
    COUNTIF('meta_display' IN UNNEST(prior_channel_list)) AS had_meta_prior,
    ROUND(COUNTIF('meta_display' IN UNNEST(prior_channel_list)) /
          COUNT(DISTINCT conversion_id) * 100, 1) AS pct_with_meta_assist
FROM conversion_path_analysis
WHERE last_touch_channel = 'google_search';
```

If 40% of Google Search converters had a Meta touchpoint earlier, cutting Meta would reduce the pool of high-intent searchers.

**2. Attribution model favors last-touch (Google)**
Using last-touch attribution, Meta gets zero credit even when it drove the initial awareness that led to the eventual search. Run a comparison:

```sql
SELECT channel,
       SUM(last_touch_revenue) AS last_touch,
       SUM(linear_revenue) AS linear,
       SUM(u_shaped_revenue) AS u_shaped
FROM attribution_comparison
GROUP BY channel;
-- If Meta's linear revenue >> last_touch revenue: Meta is assisting many conversions
```

**3. Run an incrementality test for Meta**
Suppress Meta Display for a holdout group of 20% and measure whether their conversion rate drops.

**4. Consider new member acquisition**
Google Search probably converts EXISTING Costco members who searched for renewal. Meta Display might be acquiring NEW members. Pure ROAS comparison misses LTV.

**My recommendation to the marketing team**: "Before reallocating budget, let's run a 4-week incrementality test on Meta Display and a multi-touch attribution comparison. We may find Meta's true ROAS is higher than 1.5 once assisted conversions are credited, and that cutting Meta reduces the top-of-funnel that feeds Google Search."

---

### VERY HARD

**Q6: Design a complete first-party data infrastructure for Costco that enables accurate campaign measurement in a post-cookie world. Cover: data collection, identity resolution, activation, and measurement.**

**What they're testing**: End-to-end MarTech architecture, privacy-aware engineering, GCP expertise.

**Answer**:

**Context**: Third-party cookies are deprecated. Safari/Firefox already block them; Chrome is following. Costco must rely entirely on its first-party data (data from its own customers via direct interaction).

**Layer 1: Data Collection (First-Party)**

```python
# Server-side tagging: instead of browser firing pixels to Google/Meta,
# Costco server receives the event and sends to ad platforms via server APIs
# Benefit: not blocked by ad blockers, more reliable, privacy-compliant

# When a purchase is confirmed:
@app.route('/checkout/confirmation', methods=['POST'])
def checkout_confirmed(order_data):
    # 1. Store in Costco's own database
    db.save_purchase(order_data)

    # 2. Publish to Pub/Sub for pipeline ingestion
    pubsub.publish('purchase-events', order_data)

    # 3. Send to Google Ads Conversion API (server-side, not pixel)
    google_conversions_api.upload_conversion({
        'conversion_action': 'purchase',
        'conversion_value': order_data['total'],
        'email_hash': sha256(order_data['email'])  # hashed, privacy-safe
    })

    # 4. Send to Meta Conversions API
    meta_conversions_api.send_event({
        'event_name': 'Purchase',
        'event_value': order_data['total'],
        'ph': sha256(order_data['phone'])  # hashed phone
    })
```

**Layer 2: Identity Resolution**

```python
# Problem: same person = mobile_browser_id_abc + desktop_browser_id_xyz + member_id_M001
# Solution: identity graph linking all IDs

# BigQuery identity graph table
identity_graph = """
    SELECT DISTINCT
        member_id,
        anonymous_id,
        device_type,
        first_seen_at,
        last_seen_at
    FROM (
        SELECT member_id, anonymous_id, device_type,
               MIN(event_at) OVER (PARTITION BY anonymous_id) AS first_seen_at,
               MAX(event_at) OVER (PARTITION BY anonymous_id) AS last_seen_at
        FROM user_events
        WHERE member_id IS NOT NULL  -- events where user was logged in
    )
"""

# Now you can stitch together the full journey:
# anonymous click on ad (unknown user) → login event (links anon_id to member_id)
# → purchase (member_id)
# Attribution: the anon click gets attributed to the member's purchase
```

**Layer 3: Activation (Audience Export)**

```python
# Export audience segments to ad platforms using Customer Match / Custom Audiences
# These use email/phone hashes — work without cookies

def export_segment_to_platforms(segment_name: str):
    # 1. Query BigQuery for segment members
    members = bq.query(f"""
        SELECT
            TO_HEX(SHA256(LOWER(TRIM(email)))) AS hashed_email,
            TO_HEX(SHA256(REGEXP_REPLACE(phone, '[^0-9]', ''))) AS hashed_phone
        FROM mart_member_ltv
        JOIN dim_members USING (member_id)
        WHERE member_segment = '{segment_name}'
          AND email_opt_in = TRUE
    """).to_dataframe()

    # 2. Upload to Google Ads Customer Match
    google_ads_api.user_list.add(name=segment_name, members=members['hashed_email'])

    # 3. Upload to Meta Custom Audience
    meta_ads_api.custom_audience.update(name=segment_name, members=members)
```

**Layer 4: Measurement (Cookie-Free Attribution)**

```sql
-- Member-ID-based attribution: no cookies needed
-- Join ad clicks (with member_id from login) to purchases (with member_id)

WITH logged_in_clicks AS (
    -- Clicks where user was logged in (member_id known)
    SELECT click_id, member_id, campaign_id, clicked_at
    FROM ad_clicks
    WHERE member_id IS NOT NULL  -- logged in when they clicked
),

post_click_purchases AS (
    SELECT
        c.click_id,
        c.member_id,
        c.campaign_id,
        p.transaction_id,
        p.purchase_amount_usd,
        TIMESTAMP_DIFF(p.purchased_at, c.clicked_at, HOUR) AS hours_to_purchase
    FROM logged_in_clicks c
    JOIN member_transactions p
        ON c.member_id = p.member_id
        AND p.purchased_at BETWEEN c.clicked_at AND TIMESTAMP_ADD(c.clicked_at, INTERVAL 30 DAY)
)

SELECT
    campaign_id,
    COUNT(DISTINCT transaction_id) AS attributed_purchases,
    SUM(purchase_amount_usd) AS attributed_revenue
FROM post_click_purchases
GROUP BY campaign_id;
```

**Privacy compliance**:
- All email/phone stored as SHA256 hashes when sent to platforms
- Data collection covered by Costco membership agreement
- Member opt-out removes from all audience exports
- CCPA: member can request data deletion → cascade to identity graph, audience exports

---

## Summary: MarTech / AdTech Domain — Senior Mastery Checklist

| Skill | What Senior Looks Like |
|-------|------------------------|
| Ecosystem knowledge | CDP/DMP/DSP/SSP/RTB — clear definitions, knows data flows |
| UTM tracking | Knows all parameters, how they flow from click to BigQuery |
| Attribution models | Can implement all 5 models in SQL; explains trade-offs |
| Incrementality | Understands holdout tests, can compute lift + statistical significance |
| Campaign metrics | CTR/CVR/CPC/CPM/CPA/ROAS — formulas, benchmarks, interpretations |
| Member LTV | RFM scoring, segment labels, recommended actions |
| Cookie deprecation | First-party data strategy, server-side tracking, Customer Match |
| Cross-channel analysis | Detects attribution double-counting, channel role in funnel |
| Invalid traffic | Detects bot traffic patterns, knows impact on metrics |
| Business acumen | Can challenge "cut Meta, double Google" decision with data |
