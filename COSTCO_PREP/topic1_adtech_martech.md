# Topic 1: AdTech / MarTech Data Engineering
## Complete Interview Textbook — Costco Sr. Data Engineer

---

## TABLE OF CONTENTS

1. [AdTech & MarTech Landscape — Industry Overview](#1-industry-overview)
2. [The Digital Advertising Ecosystem](#2-digital-advertising-ecosystem)
3. [Core AdTech Data Entities & Schemas](#3-core-data-entities)
4. [The MarTech Stack — Platforms & Tools](#4-martech-stack)
5. [Customer Data Platforms (CDP)](#5-customer-data-platforms)
6. [Event Tracking & Clickstream Data](#6-event-tracking)
7. [Identity Resolution & User Stitching](#7-identity-resolution)
8. [Attribution Modeling — Deep Dive](#8-attribution-modeling)
9. [Audience Segmentation & Targeting](#9-audience-segmentation)
10. [AdTech Metrics — Complete Reference](#10-adtech-metrics)
11. [Real-Time Bidding (RTB) & Programmatic Advertising](#11-rtb-programmatic)
12. [Data Privacy, Consent & Compliance](#12-privacy-and-compliance)
13. [Costco-Specific MarTech Context](#13-costco-martech-context)
14. [Pipeline Architecture for MarTech](#14-pipeline-architecture)
15. [Interview Q&A Bank](#15-interview-qa)

---

## 1. Industry Overview

### AdTech vs MarTech — The Distinction

| Dimension | AdTech (Advertising Technology) | MarTech (Marketing Technology) |
|-----------|--------------------------------|-------------------------------|
| Primary goal | Paid media — buy/sell ad inventory | Owned channels — email, CRM, loyalty |
| Data focus | Anonymous user targeting & measurement | Known customer engagement & retention |
| Key entities | Impressions, clicks, bids, exchanges | Contacts, journeys, segments, campaigns |
| Examples | DSPs, SSPs, DMPs, ad servers | CRMs, CDPs, email platforms, A/B tools |
| Typical data | Cookie IDs, device IDs, bid streams | Email opens, purchase history, LTV |

In practice — especially at retailers like Costco — the two converge: **known member data (MarTech) is used to power more precise paid advertising (AdTech)**. This convergence is the core of **Retail Media Networks** (RMNs).

### The Data Engineering Role in AdTech/MarTech

As a Senior Data Engineer in a MarTech context, your responsibilities span:

1. **Ingestion**: Pull data from ad platforms (Google Ads, Meta, programmatic DSPs), clickstream trackers (Segment, GA4), CRM systems, and POS/transaction systems.
2. **Unification**: Join anonymous ad interactions to known customer identities (identity resolution).
3. **Transformation**: Compute attribution, funnel metrics, audience segments, RFM scores.
4. **Activation**: Push computed segments and scores back to ad platforms for targeting.
5. **Measurement**: Build reporting tables and dashboards for campaign performance.
6. **Governance**: Handle PII, consent flags, data deletion requests (GDPR/CCPA).

---

## 2. The Digital Advertising Ecosystem

### The Ad Stack — Players & Roles

```
ADVERTISER (Costco)
   │  has campaign goals, budget, creative assets
   ▼
DSP — Demand Side Platform (e.g., Google DV360, The Trade Desk)
   │  bids on ad impressions on behalf of advertiser
   │  uses audience segments from DMP/CDP
   ▼
AD EXCHANGE (e.g., Google Ad Exchange, OpenX)
   │  real-time auction marketplace
   ▼
SSP — Supply Side Platform (e.g., Google AdSense, Magnite)
   │  maximizes yield for publishers
   ▼
PUBLISHER (New York Times, Weather.com, etc.)
   │  has users visiting their pages
   ▼
USER sees the ad
```

### Bid Flow — Real-Time Bidding (RTB) in 100ms

```
1. User visits publisher page → browser/app sends bid request to SSP
2. SSP sends OpenRTB bid request to multiple DSPs (~50ms budget)
3. DSP evaluates: Is this user in my target audience? What's my bid price?
4. DSP responds with bid or no-bid (~10ms)
5. SSP runs auction (typically first-price or second-price)
6. Winning DSP's ad creative is returned to publisher page
7. Browser renders the ad → impression fires
8. User clicks (or doesn't) → click event fires
9. User converts (or doesn't) → conversion pixel fires
```

### Key Identifiers in AdTech

| Identifier | Description | Persistence | Privacy Impact |
|-----------|-------------|-------------|---------------|
| Cookie ID (3rd party) | Browser-based, set by ad servers | Session to years | Being deprecated (3PC phase-out) |
| Cookie ID (1st party) | Set by publisher/advertiser domain | Configurable | Lower, still requires consent |
| GAID / IDFA | Mobile device advertising IDs | Device lifetime | Can be reset by user |
| Hashed Email (HEM) | SHA256/MD5 of email — deterministic | Permanent for user | Requires PII handling |
| IP Address | Network identifier | Changes frequently | Privacy concerns |
| UID2 / RampID | Post-cookie identity graphs | License-based | Industry solution |
| Member ID | Retailer's own internal ID | Permanent | Highest signal, 1st party |

### OpenRTB Data Schema (What Engineers Process)

```json
{
  "id": "bid_request_12345",
  "imp": [{
    "id": "1",
    "banner": {"w": 300, "h": 250},
    "bidfloor": 0.50,
    "bidfloorcur": "USD"
  }],
  "site": {
    "id": "pub_site_999",
    "domain": "example.com",
    "page": "https://example.com/article/tech-news"
  },
  "user": {
    "id": "user_cookie_abc123",
    "buyeruid": "mapped_dsp_user_id"
  },
  "device": {
    "ua": "Mozilla/5.0...",
    "ip": "192.168.1.1",
    "geo": {"country": "USA", "region": "WA", "city": "Seattle"},
    "devicetype": 2,
    "os": "Android"
  },
  "at": 1,
  "tmax": 100
}
```

---

## 3. Core AdTech Data Entities & Schemas

### Ad Event Schema (What You'll Build Pipelines For)

```sql
-- Raw ad events table (BigQuery)
CREATE TABLE raw.ad_events (
    event_id          STRING NOT NULL,
    event_type        STRING NOT NULL,   -- 'impression', 'click', 'conversion', 'view'
    event_timestamp   TIMESTAMP NOT NULL,
    event_date        DATE NOT NULL,     -- Partition column

    -- Identity
    user_id           STRING,            -- Internal member ID (if resolved)
    cookie_id         STRING,            -- Browser cookie
    device_id         STRING,            -- GAID / IDFA
    session_id        STRING,

    -- Ad inventory
    campaign_id       STRING,
    ad_group_id       STRING,
    ad_id             STRING,
    creative_id       STRING,
    placement_id      STRING,
    publisher_id      STRING,

    -- Attribution
    channel           STRING,            -- 'paid_search', 'display', 'social', 'email', 'organic'
    utm_source        STRING,
    utm_medium        STRING,
    utm_campaign      STRING,
    utm_content       STRING,
    utm_term          STRING,

    -- Page context
    page_url          STRING,
    referrer_url      STRING,
    page_category     STRING,

    -- Conversion data (populated only for conversion events)
    order_id          STRING,
    revenue           FLOAT64,
    items             ARRAY<STRUCT<
                        product_id STRING,
                        qty INT64,
                        price FLOAT64
                      >>,

    -- Bid data (for paid channels)
    bid_price         FLOAT64,
    winning_price     FLOAT64,
    spend             FLOAT64,

    -- Technical
    ip_address        STRING,
    user_agent        STRING,
    country           STRING,
    region            STRING,

    -- Pipeline metadata
    ingested_at       TIMESTAMP,
    source_system     STRING
)
PARTITION BY event_date
CLUSTER BY channel, campaign_id;
```

### Campaign Performance Schema

```sql
CREATE TABLE curated.campaign_daily_performance (
    report_date       DATE NOT NULL,
    campaign_id       STRING NOT NULL,
    campaign_name     STRING,
    channel           STRING,            -- 'google_search', 'meta_display', 'email'
    ad_group_id       STRING,
    placement_type    STRING,

    -- Volume metrics
    impressions       INT64,
    clicks            INT64,
    conversions       INT64,
    views             INT64,             -- Video views

    -- Financial metrics
    spend             FLOAT64,           -- Total ad spend
    revenue           FLOAT64,           -- Attributed revenue

    -- Computed metrics (materialized for reporting speed)
    ctr               FLOAT64,           -- clicks / impressions
    cvr               FLOAT64,           -- conversions / clicks
    cpc               FLOAT64,           -- spend / clicks
    cpm               FLOAT64,           -- spend / impressions * 1000
    cpa               FLOAT64,           -- spend / conversions
    roas              FLOAT64,           -- revenue / spend

    -- Audience
    unique_users      INT64,
    new_users         INT64,

    created_at        TIMESTAMP
)
PARTITION BY report_date
CLUSTER BY channel, campaign_id;
```

### Customer 360 / CDP Schema

```sql
CREATE TABLE curated.customer_360 (
    customer_id       STRING NOT NULL,

    -- Identity cluster
    email_hashed      STRING,            -- SHA256(lowercase(email))
    cookie_ids        ARRAY<STRING>,     -- All known browser cookies
    device_ids        ARRAY<STRING>,     -- All known device IDs
    member_id         STRING,            -- Loyalty/membership ID

    -- Demographics
    age_bucket        STRING,            -- '25-34', '35-44'
    gender            STRING,
    zip_code          STRING,
    region            STRING,

    -- Behavioral
    first_seen_date   DATE,
    last_seen_date    DATE,
    total_visits      INT64,
    total_purchases   INT64,
    total_spend       FLOAT64,
    avg_order_value   FLOAT64,
    favorite_category STRING,
    purchase_channels ARRAY<STRING>,

    -- RFM
    recency_days      INT64,
    frequency         INT64,
    monetary          FLOAT64,
    rfm_segment       STRING,

    -- Propensity scores
    churn_probability FLOAT64,
    ltv_90d           FLOAT64,
    conversion_prob   FLOAT64,

    -- Consent
    email_opt_in      BOOL,
    sms_opt_in        BOOL,
    ad_personalization_consent BOOL,
    consent_updated   TIMESTAMP,

    updated_at        TIMESTAMP
);
```

---

## 4. The MarTech Stack — Platforms & Tools

### Category Map

```
DATA COLLECTION
├── Web Analytics: Google Analytics 4, Adobe Analytics, Snowplow
├── Tag Management: Google Tag Manager, Tealium
├── CDP / Event Streaming: Segment, mParticle, Rudderstack
└── Mobile: Adjust, AppsFlyer, Branch

DATA STORAGE & PROCESSING
├── Cloud DW: BigQuery, Snowflake, Redshift
├── Data Lake: GCS, S3, Azure ADLS
├── Streaming: Kafka, Pub/Sub, Kinesis
└── Transformation: dbt, Dataflow, Spark

ACTIVATION & ENGAGEMENT
├── Email: Salesforce Marketing Cloud, Braze, Iterable
├── CRM: Salesforce, HubSpot
├── Ad Platforms: Google Ads, Meta Ads, DV360, TTD
└── Personalization: Dynamic Yield, Optimizely

MEASUREMENT & INTELLIGENCE
├── Attribution: Rockerbox, Northbeam, Triple Whale
├── BI: Looker, Tableau, PowerBI
└── Experimentation: Optimizely, VWO, Statsig
```

### How Data Flows in a Modern MarTech Stack

```
TOUCHPOINTS (web, app, email, store)
    │
    ▼
TAG / SDK (GTM, Segment SDK, Firebase)
    │ fires events
    ▼
EVENT STREAMING (Segment, Pub/Sub, Kafka)
    │ real-time event bus
    ▼
DATA LAKE (GCS / S3)
    │ raw event storage
    ▼
TRANSFORMATION LAYER (Dataflow, Spark, dbt)
    │ clean, enrich, model
    ▼
DATA WAREHOUSE (BigQuery, Snowflake)
    │ curated tables, metrics
    ▼
ACTIVATION (DSP, email platform, push)
    │ audience exports
    ▼
AD SERVING / CAMPAIGN EXECUTION
    │
    ▼
MEASUREMENT (attribution, incrementality)
```

### Segment.com — The Most Common CDP Event Hub

Events Segment tracks (you'll process these in BigQuery):

```json
// Page view event (auto-tracked)
{
  "type": "page",
  "anonymousId": "a8b9c1d2-...",
  "userId": "member_123",
  "name": "Product Detail Page",
  "properties": {
    "url": "https://costco.com/product/kirkland-olive-oil",
    "path": "/product/kirkland-olive-oil",
    "referrer": "https://google.com/",
    "title": "Kirkland Signature Olive Oil"
  },
  "context": {
    "campaign": {"source": "google", "medium": "cpc", "name": "olive_oil_q1"},
    "page": {"url": "https://costco.com/..."},
    "userAgent": "Mozilla/5.0..."
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}

// Track event (custom business event)
{
  "type": "track",
  "userId": "member_123",
  "event": "Product Added",
  "properties": {
    "product_id": "KSOLIVE5L",
    "product_name": "Kirkland Signature Olive Oil 5L",
    "category": "Grocery",
    "price": 22.99,
    "quantity": 2,
    "cart_id": "cart_abc456"
  },
  "timestamp": "2024-01-15T10:31:00.000Z"
}

// Identify event (link anonymous to known user)
{
  "type": "identify",
  "anonymousId": "a8b9c1d2-...",
  "userId": "member_123",
  "traits": {
    "email": "john.doe@email.com",
    "membership_type": "Executive",
    "zip_code": "98001"
  }
}
```

---

## 5. Customer Data Platforms (CDP)

### What a CDP Does vs DMP vs CRM

| Capability | CRM | DMP | CDP |
|-----------|-----|-----|-----|
| Stores PII | Yes | No | Yes |
| Data source | 1st party only | 1st + 3rd party | All |
| Identity | Known (authenticated) | Anonymous (cookies) | Both |
| Persistence | Permanent | 90-day cookie | Permanent |
| Use case | Sales, service | Audience targeting | Full customer view |
| Real-time | Limited | Yes | Yes |
| Example | Salesforce | BlueKai | Segment, Tealium |

### Building a CDP in BigQuery (The Engineering Challenge)

The core challenge is **identity resolution** — stitching anonymous events to known users.

```sql
-- Step 1: Build identity graph
-- anonymous_id → user_id mappings from identify() calls
CREATE OR REPLACE TABLE identity.id_graph AS
WITH identity_calls AS (
    SELECT
        anonymous_id,
        user_id,
        received_at,
        ROW_NUMBER() OVER (
            PARTITION BY anonymous_id
            ORDER BY received_at DESC
        ) AS rn
    FROM raw.segment_identifies
    WHERE user_id IS NOT NULL
)
SELECT anonymous_id, user_id, received_at AS last_identified_at
FROM identity_calls
WHERE rn = 1;

-- Step 2: Backfill historical anonymous events with resolved user_id
CREATE OR REPLACE TABLE curated.enriched_events AS
SELECT
    e.*,
    COALESCE(e.user_id, ig.user_id) AS resolved_user_id
FROM raw.segment_events e
LEFT JOIN identity.id_graph ig ON e.anonymous_id = ig.anonymous_id;

-- Step 3: Build Customer 360 profile
CREATE OR REPLACE TABLE curated.customer_360 AS
WITH event_features AS (
    SELECT
        resolved_user_id AS customer_id,
        MIN(DATE(timestamp)) AS first_seen_date,
        MAX(DATE(timestamp)) AS last_seen_date,
        COUNT(DISTINCT session_id) AS total_sessions,
        COUNT(DISTINCT DATE(timestamp)) AS active_days,
        COUNT(CASE WHEN event = 'Product Added' THEN 1 END) AS cart_adds,
        COUNT(CASE WHEN event = 'Order Completed' THEN 1 END) AS total_purchases,
        SUM(CASE WHEN event = 'Order Completed' THEN revenue ELSE 0 END) AS total_revenue,
        ARRAY_AGG(DISTINCT channel IGNORE NULLS) AS channels_used
    FROM curated.enriched_events
    WHERE resolved_user_id IS NOT NULL
    GROUP BY customer_id
)
SELECT
    ef.*,
    DATE_DIFF(CURRENT_DATE(), ef.last_seen_date, DAY) AS recency_days,
    ef.total_revenue / NULLIF(ef.total_purchases, 0) AS avg_order_value
FROM event_features ef;
```

---

## 6. Event Tracking & Clickstream Data

### Standard E-commerce Event Taxonomy

```
AWARENESS EVENTS
├── impression          — ad or product seen
├── page_view           — page loaded
└── search              — search query submitted

CONSIDERATION EVENTS
├── product_view        — product detail page viewed
├── product_list_view   — category/search results page
├── add_to_wishlist     — saved for later
└── video_play          — campaign video watched

INTENT EVENTS
├── add_to_cart         — item added to cart
├── cart_view           — cart page visited
├── checkout_start      — checkout initiated
└── payment_info_added  — payment entered

CONVERSION EVENTS
├── order_completed     — purchase success
├── membership_signup   — new member
└── membership_renewal  — renewal purchase

POST-CONVERSION EVENTS
├── return_initiated    — return started
├── review_submitted    — product review
└── referral_sent       — referred a friend
```

### Sessionization Rules (Important for Interviews)

```sql
-- Session boundary = 30 minutes of inactivity (industry standard)
-- OR = browser close (new cookie session)
-- OR = new campaign attribution (source change)

WITH session_boundaries AS (
    SELECT
        user_id,
        anonymous_id,
        event_timestamp,
        page_url,
        utm_source,
        utm_campaign,

        -- Time-based boundary
        TIMESTAMP_DIFF(
            event_timestamp,
            LAG(event_timestamp) OVER (PARTITION BY COALESCE(user_id, anonymous_id) ORDER BY event_timestamp),
            MINUTE
        ) AS gap_minutes,

        -- Campaign change boundary (optional, depends on business rules)
        utm_campaign != LAG(utm_campaign) OVER (PARTITION BY COALESCE(user_id, anonymous_id) ORDER BY event_timestamp) AS campaign_changed

    FROM raw.events
),
session_flags AS (
    SELECT
        *,
        CASE
            WHEN gap_minutes IS NULL THEN 1       -- First event
            WHEN gap_minutes > 30 THEN 1          -- Inactivity gap
            WHEN campaign_changed THEN 1          -- Campaign changed
            ELSE 0
        END AS new_session_flag
    FROM session_boundaries
),
with_session_id AS (
    SELECT
        *,
        -- Create globally unique session ID
        CONCAT(
            COALESCE(user_id, anonymous_id), '_',
            CAST(
                SUM(new_session_flag) OVER (
                    PARTITION BY COALESCE(user_id, anonymous_id)
                    ORDER BY event_timestamp
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS STRING
            )
        ) AS session_id
    FROM session_flags
)
SELECT * FROM with_session_id;
```

### UTM Parameter Parsing Pipeline

```sql
-- Parse and standardize UTM parameters from all traffic sources
CREATE OR REPLACE TABLE curated.traffic_attribution AS
SELECT
    event_id,
    event_timestamp,
    user_id,
    page_url,

    -- Raw UTM values
    REGEXP_EXTRACT(page_url, r'[?&]utm_source=([^&#]+)') AS utm_source_raw,
    REGEXP_EXTRACT(page_url, r'[?&]utm_medium=([^&#]+)') AS utm_medium_raw,
    REGEXP_EXTRACT(page_url, r'[?&]utm_campaign=([^&#]+)') AS utm_campaign_raw,
    REGEXP_EXTRACT(page_url, r'[?&]utm_content=([^&#]+)') AS utm_content_raw,
    REGEXP_EXTRACT(page_url, r'[?&]utm_term=([^&#]+)') AS utm_term_raw,
    REGEXP_EXTRACT(page_url, r'[?&]gclid=([^&#]+)') AS gclid,     -- Google Click ID
    REGEXP_EXTRACT(page_url, r'[?&]fbclid=([^&#]+)') AS fbclid,   -- Facebook Click ID
    REGEXP_EXTRACT(page_url, r'[?&]msclkid=([^&#]+)') AS msclkid, -- Microsoft Click ID

    -- Normalized channel classification
    CASE
        WHEN REGEXP_EXTRACT(page_url, r'[?&]utm_medium=([^&#]+)') IN ('cpc', 'ppc', 'paid_search') THEN 'paid_search'
        WHEN REGEXP_EXTRACT(page_url, r'[?&]utm_medium=([^&#]+)') IN ('display', 'banner', 'cpm') THEN 'display'
        WHEN REGEXP_EXTRACT(page_url, r'[?&]utm_medium=([^&#]+)') IN ('social', 'social_paid') THEN 'paid_social'
        WHEN REGEXP_EXTRACT(page_url, r'[?&]utm_medium=([^&#]+)') = 'email' THEN 'email'
        WHEN REGEXP_EXTRACT(page_url, r'[?&]utm_medium=([^&#]+)') = 'affiliate' THEN 'affiliate'
        WHEN REGEXP_EXTRACT(page_url, r'[?&]utm_medium=([^&#]+)') = 'organic' THEN 'organic_social'
        WHEN REGEXP_EXTRACT(page_url, r'[?&]gclid=([^&#]+)') IS NOT NULL THEN 'paid_search'
        WHEN REGEXP_EXTRACT(page_url, r'[?&]fbclid=([^&#]+)') IS NOT NULL THEN 'paid_social'
        WHEN referrer_url LIKE '%google.%' AND REGEXP_EXTRACT(page_url, r'[?&]utm_source=([^&#]+)') IS NULL THEN 'organic_search'
        WHEN referrer_url IS NULL OR referrer_url = '' THEN 'direct'
        ELSE 'referral'
    END AS channel

FROM raw.page_views;
```

---

## 7. Identity Resolution & User Stitching

### The Identity Problem

A single real person may appear as many different data records:
- Anonymous cookie A (desktop Chrome)
- Anonymous cookie B (mobile Safari)
- User ID 12345 (after login on desktop)
- Email hash abc123 (from email campaign click)
- Member ID M67890 (from in-store purchase)

Identity resolution = building a unified profile across all these touchpoints.

### Deterministic vs Probabilistic Matching

**Deterministic** (exact match):
- Same email hash across touchpoints
- Same device ID + same user ID at different times
- Login event linking cookie to user_id

**Probabilistic** (statistical inference):
- Same IP + same user agent + same behavior pattern = likely same person
- Lower confidence; used when deterministic signals unavailable

### Building an Identity Graph in BigQuery

```sql
-- Identity graph construction
-- Collect all (anonymous_id, user_id) pairs from events
CREATE OR REPLACE TABLE identity.raw_pairs AS
SELECT DISTINCT anonymous_id, user_id, 'segment_identify' AS source, MIN(timestamp) AS first_seen
FROM raw.segment_identifies WHERE anonymous_id IS NOT NULL AND user_id IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL

SELECT DISTINCT cookie_id, user_id, 'login_event', MIN(event_timestamp)
FROM raw.login_events WHERE cookie_id IS NOT NULL AND user_id IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL

SELECT DISTINCT email_hash, customer_id, 'email_click', MIN(click_time)
FROM raw.email_clicks WHERE email_hash IS NOT NULL AND customer_id IS NOT NULL
GROUP BY 1, 2, 3;

-- Resolve to canonical user_id
-- Strategy: take the user_id that appears most often for an anonymous_id
CREATE OR REPLACE TABLE identity.resolved AS
WITH ranked AS (
    SELECT
        anonymous_id,
        user_id,
        COUNT(*) AS link_count,
        MAX(first_seen) AS last_linked,
        ROW_NUMBER() OVER (PARTITION BY anonymous_id ORDER BY COUNT(*) DESC) AS rn
    FROM identity.raw_pairs
    GROUP BY anonymous_id, user_id
)
SELECT anonymous_id, user_id AS canonical_user_id, link_count, last_linked
FROM ranked
WHERE rn = 1;

-- Apply to events: resolve all anonymous IDs to canonical user
CREATE OR REPLACE TABLE curated.resolved_events AS
SELECT
    e.*,
    COALESCE(e.user_id, r.canonical_user_id) AS resolved_user_id,
    CASE WHEN e.user_id IS NOT NULL THEN 'authenticated'
         WHEN r.canonical_user_id IS NOT NULL THEN 'stitched'
         ELSE 'anonymous' END AS identity_type
FROM raw.events e
LEFT JOIN identity.resolved r ON e.anonymous_id = r.anonymous_id;
```

---

## 8. Attribution Modeling — Deep Dive

### Why Attribution Matters

Attribution answers: **which marketing touchpoints deserve credit for a conversion?** The answer determines how budget is allocated across channels.

### The Touchpoint Journey

```
User Journey Example:
Day 1: Sees display ad (impression) → no action
Day 2: Searches "kirkland olive oil" → clicks Google Ad → browses but doesn't buy
Day 3: Sees retargeting banner → no action
Day 5: Opens email → clicks → PURCHASES $89

Touchpoints: display → paid_search → retargeting → email → CONVERSION
```

### Attribution Models — Technical Implementation

```sql
-- ========================================
-- BUILD: Touchpoints table (all pre-conversion touches)
-- ========================================
WITH conversion_events AS (
    SELECT
        user_id,
        event_timestamp AS conversion_time,
        revenue,
        order_id
    FROM curated.events
    WHERE event_type = 'purchase'
),
touchpoint_events AS (
    SELECT
        user_id,
        event_timestamp AS touch_time,
        channel,
        campaign_id,
        spend
    FROM curated.events
    WHERE event_type IN ('impression', 'click', 'email_open')
),
-- Join: for each conversion, get all touchpoints in 30-day lookback window
touchpoints_per_conversion AS (
    SELECT
        c.user_id,
        c.order_id,
        c.conversion_time,
        c.revenue,
        t.touch_time,
        t.channel,
        t.campaign_id,
        t.spend,
        TIMESTAMP_DIFF(c.conversion_time, t.touch_time, HOUR) AS hours_before_conversion,
        ROW_NUMBER() OVER (PARTITION BY c.order_id ORDER BY t.touch_time ASC) AS touch_position,
        ROW_NUMBER() OVER (PARTITION BY c.order_id ORDER BY t.touch_time DESC) AS touch_position_rev,
        COUNT(*) OVER (PARTITION BY c.order_id) AS total_touches
    FROM conversion_events c
    JOIN touchpoint_events t
        ON c.user_id = t.user_id
        AND t.touch_time <= c.conversion_time
        AND t.touch_time >= TIMESTAMP_SUB(c.conversion_time, INTERVAL 30 DAY)
)

-- ========================================
-- MODEL 1: Last Touch Attribution
-- ========================================
, last_touch AS (
    SELECT
        channel, campaign_id,
        COUNT(DISTINCT order_id) AS conversions,
        SUM(revenue) AS attributed_revenue
    FROM touchpoints_per_conversion
    WHERE touch_position_rev = 1   -- Last touchpoint only
    GROUP BY channel, campaign_id
)

-- ========================================
-- MODEL 2: First Touch Attribution
-- ========================================
, first_touch AS (
    SELECT
        channel, campaign_id,
        COUNT(DISTINCT order_id) AS conversions,
        SUM(revenue) AS attributed_revenue
    FROM touchpoints_per_conversion
    WHERE touch_position = 1       -- First touchpoint only
    GROUP BY channel, campaign_id
)

-- ========================================
-- MODEL 3: Linear Attribution (equal credit)
-- ========================================
, linear AS (
    SELECT
        channel, campaign_id,
        SUM(1.0 / total_touches) AS attributed_conversions,
        SUM(revenue / total_touches) AS attributed_revenue
    FROM touchpoints_per_conversion
    GROUP BY channel, campaign_id
)

-- ========================================
-- MODEL 4: Time Decay Attribution
-- Half-life = 7 days (168 hours)
-- ========================================
, time_decay_raw AS (
    SELECT
        *,
        POW(0.5, hours_before_conversion / 168.0) AS decay_weight
    FROM touchpoints_per_conversion
),
time_decay_normalized AS (
    SELECT
        *,
        decay_weight / SUM(decay_weight) OVER (PARTITION BY order_id) AS normalized_weight
    FROM time_decay_raw
),
time_decay AS (
    SELECT
        channel, campaign_id,
        SUM(normalized_weight) AS attributed_conversions,
        SUM(revenue * normalized_weight) AS attributed_revenue
    FROM time_decay_normalized
    GROUP BY channel, campaign_id
)

-- ========================================
-- MODEL 5: Position-Based / U-Shaped
-- 40% first touch, 40% last touch, 20% distributed to middle
-- ========================================
, position_based AS (
    SELECT
        channel, campaign_id,
        SUM(
            CASE
                WHEN touch_position = 1 AND total_touches = 1 THEN 1.0          -- Only touch
                WHEN touch_position = 1 THEN 0.4                                 -- First touch
                WHEN touch_position_rev = 1 THEN 0.4                            -- Last touch
                ELSE 0.2 / GREATEST(total_touches - 2, 1)                       -- Middle touches
            END
        ) AS attributed_conversions,
        SUM(
            revenue * CASE
                WHEN touch_position = 1 AND total_touches = 1 THEN 1.0
                WHEN touch_position = 1 THEN 0.4
                WHEN touch_position_rev = 1 THEN 0.4
                ELSE 0.2 / GREATEST(total_touches - 2, 1)
            END
        ) AS attributed_revenue
    FROM touchpoints_per_conversion
    GROUP BY channel, campaign_id
)

-- Compare models side by side
SELECT
    COALESCE(lt.channel, ft.channel, ln.channel) AS channel,
    lt.attributed_revenue AS last_touch_revenue,
    ft.attributed_revenue AS first_touch_revenue,
    ln.attributed_revenue AS linear_revenue,
    td.attributed_revenue AS time_decay_revenue,
    pb.attributed_revenue AS position_based_revenue
FROM last_touch lt
FULL OUTER JOIN first_touch ft USING (channel, campaign_id)
FULL OUTER JOIN linear ln USING (channel, campaign_id)
FULL OUTER JOIN time_decay td USING (channel, campaign_id)
FULL OUTER JOIN position_based pb USING (channel, campaign_id);
```

### Incrementality Testing (Beyond Attribution)

Attribution tells you *which channel* gets credit — it doesn't tell you whether the ad **caused** the conversion. For true causal measurement, use incrementality tests (A/B holdout tests):

```
Treatment group: Users exposed to campaign
Control group: Users NOT shown the campaign (holdout)

Incremental conversions = Treatment CVR - Control CVR
Incremental ROAS = (Incremental Revenue) / Spend
```

---

## 9. Audience Segmentation & Targeting

### Behavioral Segments

```sql
-- Audience definitions for campaign targeting
-- Each segment becomes a list of user_ids exported to ad platforms

-- Segment 1: High-value members at risk of churn
CREATE OR REPLACE TABLE audiences.high_value_at_risk AS
SELECT DISTINCT customer_id
FROM curated.customer_360
WHERE total_spend >= 5000                        -- High historical value
  AND recency_days BETWEEN 45 AND 120           -- Inactive 45-120 days
  AND membership_type = 'Executive'
  AND email_opt_in = TRUE;

-- Segment 2: Cart abandoners
CREATE OR REPLACE TABLE audiences.cart_abandoners AS
WITH cart_adds AS (
    SELECT DISTINCT user_id, MAX(event_timestamp) AS last_cart_add
    FROM curated.events
    WHERE event_type = 'add_to_cart'
      AND event_date >= CURRENT_DATE() - 7
    GROUP BY user_id
),
purchasers AS (
    SELECT DISTINCT user_id
    FROM curated.events
    WHERE event_type = 'purchase'
      AND event_date >= CURRENT_DATE() - 7
)
SELECT ca.user_id
FROM cart_adds ca
LEFT JOIN purchasers p ON ca.user_id = p.user_id
WHERE p.user_id IS NULL;

-- Segment 3: Lookalike seed — best customers for acquisition
CREATE OR REPLACE TABLE audiences.lookalike_seed AS
SELECT customer_id, email_hashed
FROM curated.customer_360
WHERE rfm_segment = 'Champions'
  AND total_spend >= 10000
  AND recency_days <= 30
  AND email_hashed IS NOT NULL
LIMIT 50000;  -- Platform limit for lookalike seed

-- Segment 4: Category-specific buyers for cross-sell
CREATE OR REPLACE TABLE audiences.electronics_buyers_no_appliances AS
WITH electronics_buyers AS (
    SELECT DISTINCT customer_id
    FROM curated.purchase_items
    WHERE category = 'Electronics'
      AND purchase_date >= CURRENT_DATE() - 365
),
appliance_buyers AS (
    SELECT DISTINCT customer_id
    FROM curated.purchase_items
    WHERE category = 'Appliances'
      AND purchase_date >= CURRENT_DATE() - 365
)
SELECT e.customer_id
FROM electronics_buyers e
WHERE NOT EXISTS (SELECT 1 FROM appliance_buyers a WHERE a.customer_id = e.customer_id);
```

### Propensity Scoring Pipeline

```python
# Feature engineering for propensity model
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler

def build_propensity_features(df_customers, df_events, df_purchases):
    """Build features for 90-day conversion propensity model."""

    # Behavioral features from events
    event_features = df_events.groupby("customer_id").agg(
        total_sessions=("session_id", "nunique"),
        sessions_last_30d=("session_id", lambda x: x[df_events.loc[x.index, "event_date"] >= pd.Timestamp.today() - pd.Timedelta(30, "d")].nunique()),
        page_views=("event_id", lambda x: (df_events.loc[x.index, "event_type"] == "page_view").sum()),
        product_views=("event_id", lambda x: (df_events.loc[x.index, "event_type"] == "product_view").sum()),
        cart_adds=("event_id", lambda x: (df_events.loc[x.index, "event_type"] == "add_to_cart").sum()),
        email_opens=("event_id", lambda x: (df_events.loc[x.index, "channel"] == "email").sum()),
    ).reset_index()

    # Purchase features
    purchase_features = df_purchases.groupby("customer_id").agg(
        total_purchases=("order_id", "nunique"),
        total_spend=("amount", "sum"),
        avg_order_value=("amount", "mean"),
        days_since_last_purchase=("order_date", lambda x: (pd.Timestamp.today() - x.max()).days),
        purchase_frequency_monthly=("order_date", lambda x: len(x) / max((x.max() - x.min()).days / 30, 1))
    ).reset_index()

    # Combine
    features = df_customers[["customer_id", "membership_type", "tenure_days", "zip_code"]] \
        .merge(event_features, on="customer_id", how="left") \
        .merge(purchase_features, on="customer_id", how="left") \
        .fillna(0)

    return features

def train_and_score_propensity(features_df, labels_df):
    """Train GBM model and return propensity scores."""
    from sklearn.model_selection import train_test_split

    feature_cols = [c for c in features_df.columns if c != "customer_id"]
    X = features_df[feature_cols]
    y = labels_df["converted_90d"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y)

    model = GradientBoostingClassifier(n_estimators=200, max_depth=5, learning_rate=0.05)
    model.fit(X_train, y_train)

    features_df["conversion_probability"] = model.predict_proba(X)[:, 1]
    return features_df[["customer_id", "conversion_probability"]]
```

---

## 10. AdTech Metrics — Complete Reference

### Tier 1: Delivery Metrics

| Metric | Formula | What It Measures |
|--------|---------|-----------------|
| Impressions | Count of ad renders | Reach |
| Clicks | Count of ad clicks | Engagement |
| CTR | Clicks / Impressions × 100 | Click-through rate |
| Viewability | Viewable impressions / Total impressions | Actual visibility |
| Reach | Unique users who saw ad | Unduplicated audience |
| Frequency | Impressions / Reach | Avg exposures per user |

### Tier 2: Efficiency Metrics

| Metric | Formula | What It Measures |
|--------|---------|-----------------|
| CPM | (Spend / Impressions) × 1000 | Cost per 1000 impressions |
| CPC | Spend / Clicks | Cost per click |
| CPV | Spend / Video views | Cost per video view |
| vCPM | (Spend / Viewable Impressions) × 1000 | Cost per 1000 viewable imps |

### Tier 3: Outcome Metrics

| Metric | Formula | What It Measures |
|--------|---------|-----------------|
| Conversions | Count of desired actions (purchases, signups) | Direct outcomes |
| CVR | Conversions / Clicks × 100 | Conversion rate |
| CPA | Spend / Conversions | Cost per acquisition |
| ROAS | Revenue / Spend | Return on ad spend |
| ROI | (Revenue - Spend) / Spend × 100 | Return on investment |

### Tier 4: Customer / LTV Metrics

| Metric | Formula | Description |
|--------|---------|-------------|
| CAC | Marketing Spend / New Customers Acquired | Customer acquisition cost |
| LTV | Avg Order Value × Purchase Frequency × Avg Customer Lifespan | Lifetime value |
| LTV:CAC Ratio | LTV / CAC | Payback efficiency (>3 is good) |
| Payback Period | CAC / (Monthly Revenue per Customer) | Months to recover CAC |

### Full Metrics SQL

```sql
-- Complete campaign performance dashboard query
SELECT
    c.campaign_id,
    c.campaign_name,
    c.channel,
    c.report_date,

    -- Delivery
    SUM(c.impressions) AS impressions,
    SUM(c.clicks) AS clicks,
    APPROX_COUNT_DISTINCT(e.user_id) AS unique_reach,
    SAFE_DIVIDE(SUM(c.impressions), APPROX_COUNT_DISTINCT(e.user_id)) AS avg_frequency,

    -- Efficiency
    ROUND(SAFE_DIVIDE(SUM(c.spend), SUM(c.impressions)) * 1000, 4) AS cpm,
    ROUND(SAFE_DIVIDE(SUM(c.spend), SUM(c.clicks)), 4) AS cpc,
    ROUND(SAFE_DIVIDE(SUM(c.clicks), SUM(c.impressions)) * 100, 4) AS ctr_pct,

    -- Outcomes
    SUM(c.conversions) AS conversions,
    SUM(c.revenue) AS revenue,
    SUM(c.spend) AS spend,
    ROUND(SAFE_DIVIDE(SUM(c.conversions), SUM(c.clicks)) * 100, 4) AS cvr_pct,
    ROUND(SAFE_DIVIDE(SUM(c.spend), SUM(c.conversions)), 4) AS cpa,
    ROUND(SAFE_DIVIDE(SUM(c.revenue), SUM(c.spend)), 4) AS roas,

    -- Member acquisition
    COUNT(DISTINCT CASE WHEN m.is_new_member THEN e.user_id END) AS new_members_acquired,
    ROUND(SAFE_DIVIDE(SUM(c.spend), NULLIF(COUNT(DISTINCT CASE WHEN m.is_new_member THEN e.user_id END), 0)), 2) AS cac,

    -- Rolling 7-day metrics
    AVG(SAFE_DIVIDE(SUM(c.revenue), SUM(c.spend))) OVER (
        PARTITION BY c.campaign_id, c.channel
        ORDER BY c.report_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7d_roas

FROM curated.campaign_daily_performance c
LEFT JOIN curated.resolved_events e ON e.campaign_id = c.campaign_id AND DATE(e.event_timestamp) = c.report_date
LEFT JOIN curated.members m ON e.user_id = m.member_id
WHERE c.report_date >= CURRENT_DATE() - 30
GROUP BY c.campaign_id, c.campaign_name, c.channel, c.report_date
ORDER BY c.report_date DESC, revenue DESC;
```

---

## 11. RTB & Programmatic Advertising

### RTB Data Engineering Challenges

At scale, RTB generates:
- **Bid requests**: 10M–500M per day depending on DSP size
- **Bid responses**: 10B+ per day (most are no-bids)
- **Win notifications**: Subset of bids won
- **Impression events**: Fired when ad renders
- **Click events**: Fired on click
- **Conversion events**: Fired on purchase (via pixel)

**Engineering challenge: join these 5 streams to measure campaign performance.**

```sql
-- Joining bid → win → impression → click → conversion
CREATE OR REPLACE TABLE analytics.campaign_funnel AS
WITH bids AS (
    SELECT bid_id, campaign_id, user_id, bid_price, bid_timestamp
    FROM raw.bid_responses WHERE bid_status = 'submitted'
),
wins AS (
    SELECT bid_id, winning_price, win_timestamp
    FROM raw.win_notifications
),
impressions AS (
    SELECT bid_id, impression_timestamp FROM raw.impression_events
),
clicks AS (
    SELECT bid_id, click_timestamp FROM raw.click_events
),
conversions AS (
    SELECT bid_id, order_id, revenue, conversion_timestamp FROM raw.conversion_events
)
SELECT
    b.campaign_id,
    b.user_id,
    b.bid_price,
    w.winning_price,
    b.bid_timestamp,
    w.win_timestamp,
    i.impression_timestamp,
    k.click_timestamp,
    c.conversion_timestamp,
    c.revenue,
    -- Funnel flags
    w.bid_id IS NOT NULL AS won,
    i.bid_id IS NOT NULL AS impressed,
    k.bid_id IS NOT NULL AS clicked,
    c.bid_id IS NOT NULL AS converted
FROM bids b
LEFT JOIN wins w ON b.bid_id = w.bid_id
LEFT JOIN impressions i ON b.bid_id = i.bid_id
LEFT JOIN clicks k ON b.bid_id = k.bid_id
LEFT JOIN conversions c ON b.bid_id = c.bid_id;
```

---

## 12. Data Privacy, Consent & Compliance

### Regulatory Landscape

| Regulation | Scope | Key Requirements for Data Engineers |
|-----------|-------|-------------------------------------|
| GDPR | EU users | Consent management, right to deletion, data minimization, 72-hr breach notification |
| CCPA/CPRA | California users | Right to opt-out of sale, right to delete, data inventory |
| COPPA | US children <13 | Don't collect data on minors |
| India DPDP 2023 | India users | Consent-first, data localization under consideration |

### Engineering Consent Into the Data Pipeline

```sql
-- Consent management table
CREATE TABLE privacy.user_consent (
    user_id                 STRING NOT NULL,
    consent_timestamp       TIMESTAMP NOT NULL,
    consent_version         STRING,

    -- Granular consent flags
    analytics_consent       BOOL NOT NULL DEFAULT FALSE,
    marketing_consent       BOOL NOT NULL DEFAULT FALSE,
    personalization_consent BOOL NOT NULL DEFAULT FALSE,
    third_party_sharing     BOOL NOT NULL DEFAULT FALSE,

    -- Source of consent
    consent_source          STRING,   -- 'cookie_banner', 'account_settings', 'email'
    ip_country              STRING,
    opt_out_date            TIMESTAMP  -- NULL = not opted out
)
PARTITION BY DATE(consent_timestamp);

-- Apply consent filter to all audience exports
CREATE OR REPLACE TABLE audiences.consented_targeting_list AS
SELECT c360.customer_id, c360.email_hashed
FROM curated.customer_360 c360
INNER JOIN privacy.user_consent pc
    ON c360.customer_id = pc.user_id
WHERE pc.marketing_consent = TRUE
  AND pc.third_party_sharing = TRUE
  AND pc.opt_out_date IS NULL
  AND pc.consent_timestamp = (
      SELECT MAX(consent_timestamp)
      FROM privacy.user_consent
      WHERE user_id = pc.user_id
  );

-- Data deletion pipeline (GDPR/CCPA right to erasure)
-- Step 1: Identify all records for user
-- Step 2: Delete from all tables or replace PII with tombstone

CREATE OR REPLACE PROCEDURE privacy.delete_user_data(target_user_id STRING)
BEGIN
    -- Delete from raw events
    DELETE FROM raw.events WHERE user_id = target_user_id;

    -- Anonymize in analytics tables (keep aggregates, remove PII)
    UPDATE curated.customer_360
    SET
        email_hashed = 'DELETED',
        cookie_ids = [],
        device_ids = [],
        zip_code = NULL
    WHERE customer_id = target_user_id;

    -- Log deletion for compliance audit trail
    INSERT INTO privacy.deletion_log (user_id, requested_at, completed_at, tables_affected)
    VALUES (target_user_id, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), 3);
END;
```

### Data Minimization & PII Handling

```sql
-- Never store raw PII — always hash or tokenize
-- Hash emails for matching without storing raw PII
SELECT
    TO_HEX(SHA256(LOWER(TRIM(email)))) AS email_hashed,  -- Consistent hashing
    -- Never SELECT email directly in downstream tables
FROM raw.member_registrations;

-- Tokenize IP addresses (store only country/region)
SELECT
    NET.IP_FROM_STRING(ip_address) AS ip_bytes,  -- Keep binary if needed for fraud
    -- Or just keep geography:
    country_code,
    region
    -- Drop: ip_address, user_agent, device fingerprint in downstream curated tables
FROM raw.web_events;
```

---

## 13. Costco-Specific MarTech Context

### Costco's Data & Marketing Landscape

**Why Costco's data engineering role is unique:**

1. **Member-first model**: Every purchase is tied to a paid membership — Costco has near-perfect transaction attribution to a known customer. No anonymous purchase data in-store.

2. **First-party data richness**: With 70M+ household members, Costco has extraordinary 1st-party data — purchase history, membership tier, renewal patterns, warehouse visits.

3. **Retail Media Network (Costco Media Network)**: Suppliers pay Costco to advertise to Costco's members — on costco.com, in Costco Connection magazine, in digital channels. Data engineers build the measurement and targeting infrastructure.

4. **Digital + Physical fusion**: costco.com, app, warehouse scan data, membership — all need to be joined for a 360-degree view.

### Costco's MarTech Data Flows (Inferred)

```
COSTCO.COM / APP
    │  Clickstream (add to cart, search, product views)
    │
WAREHOUSE POS
    │  In-store purchase transactions (tied to membership scan)
    │
MEMBERSHIP SYSTEM
    │  Signups, renewals, upgrades, cancellations
    │
EMAIL / MARKETING PLATFORMS
    │  Campaign sends, opens, clicks
    │
                   ▼
            DATA WAREHOUSE (BigQuery likely)
                   │
          ┌────────┴────────┐
          ▼                 ▼
    MARKETING          SUPPLIER MEASUREMENT
    ANALYTICS          (Retail Media Network)
    - Segment LTV      - Ad campaign attribution
    - Retention        - Incremental sales lift
    - Channel ROI      - Audience reach reports
```

### Key Interview Angles for Costco

1. **Member analytics**: "How would you build a churn prediction pipeline for Executive members?" → RFM + behavioral signals + propensity scoring.

2. **Campaign attribution**: "A supplier ran a display campaign targeting members who bought Category X. How do you measure if it drove Category Y purchases?" → Incrementality: control group holdout test, purchase lift measurement.

3. **Personalization**: "How would you power personalized email recommendations for Costco.com?" → Collaborative filtering on purchase history, segment-based product affinity scores.

4. **Data governance**: "A member requests deletion of their data under GDPR. What does your pipeline do?" → Deletion pipeline across raw/curated/audience tables, consent flag propagation.

5. **Pipeline design**: "Raw clickstream from costco.com comes in as events via Pub/Sub. How do you turn this into a campaign performance dashboard?" → Ingest → Pub/Sub → Dataflow → BigQuery raw → dbt/Dataflow transforms → curated tables → Looker dashboard.

---

## 14. Pipeline Architecture for MarTech

### Lambda Architecture (Batch + Speed Layer)

```
┌─────────────────────────────────────────────────────────┐
│                    SOURCE EVENTS                         │
│  Web/App Events → Pub/Sub Topic                         │
└──────────────────────────┬──────────────────────────────┘
                           │
            ┌──────────────┴──────────────┐
            ▼                             ▼
    SPEED LAYER                    BATCH LAYER
    (Real-time, ~1min lag)         (Daily batch)
    Dataflow Streaming              Cloud Composer DAG
    → BigQuery streaming buffer     → Reads GCS daily files
    → Real-time dashboards          → Runs dbt models
    → Alert triggers                → Full historical rebuild
            │                             │
            └──────────────┬──────────────┘
                           ▼
                   SERVING LAYER
                   (BigQuery curated tables)
                   → Looker dashboards
                   → Audience export APIs
                   → Supplier reporting
```

### Daily MarTech ETL DAG (Airflow/Cloud Composer)

```python
from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.providers.google.cloud.operators.dataflow import DataflowCreatePythonJobOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": True,
    "email": ["data-alerts@costco.com"]
}

with DAG(
    dag_id="martech_daily_pipeline",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="0 4 * * *",  # 4 AM daily
    catchup=False,
    tags=["martech", "production"]
) as dag:

    # Task 1: Ingest previous day's events from GCS
    ingest_events = BigQueryInsertJobOperator(
        task_id="ingest_raw_events",
        configuration={
            "query": {
                "query": """
                    INSERT INTO raw.ad_events
                    SELECT * FROM raw.ad_events_staging
                    WHERE DATE(event_timestamp) = '{{ ds }}'
                """,
                "useLegacySql": False
            }
        }
    )

    # Task 2: Run identity resolution
    resolve_identities = BigQueryInsertJobOperator(
        task_id="resolve_identities",
        configuration={
            "query": {
                "query": "CALL identity.resolve_daily('{{ ds }}')",
                "useLegacySql": False
            }
        }
    )

    # Task 3: Compute session metrics
    sessionize = DataflowCreatePythonJobOperator(
        task_id="sessionize_events",
        py_file="gs://costco-pipelines/sessionization.py",
        options={"run_date": "{{ ds }}"},
        dataflow_default_options={
            "project": "costco-prod",
            "region": "us-central1",
            "temp_location": "gs://costco-temp/dataflow/"
        }
    )

    # Task 4: Attribution modeling
    attribution = BigQueryInsertJobOperator(
        task_id="compute_attribution",
        configuration={
            "query": {
                "query": "CALL analytics.compute_attribution('{{ ds }}')",
                "useLegacySql": False
            }
        }
    )

    # Task 5: Refresh campaign performance table
    refresh_campaign_perf = BigQueryInsertJobOperator(
        task_id="refresh_campaign_performance",
        configuration={
            "query": {
                "query": """
                    CALL analytics.refresh_campaign_daily_metrics('{{ ds }}')
                """,
                "useLegacySql": False
            }
        }
    )

    # Task 6: Refresh audience segments
    refresh_audiences = BigQueryInsertJobOperator(
        task_id="refresh_audience_segments",
        configuration={
            "query": {
                "query": "CALL audiences.refresh_all_segments()",
                "useLegacySql": False
            }
        }
    )

    # DAG dependencies
    ingest_events >> resolve_identities >> sessionize >> attribution >> refresh_campaign_perf >> refresh_audiences
```

---

## 15. Interview Q&A Bank

**Q: What is the difference between a DMP and a CDP? When would a retailer like Costco use each?**
A: A DMP (Data Management Platform) handles primarily anonymous, cookie-based 3rd-party data — used for targeting unknown users in programmatic advertising. It typically stores data for 90 days. A CDP (Customer Data Platform) handles known customers with persistent profiles — it unifies 1st-party data from all channels (web, email, store, app) into a single customer record with full history. For Costco, the CDP is more valuable because they have rich 1st-party member data and can build precise segments based on actual purchase history. The DMP would be used to extend reach beyond the known membership base via lookalike audiences.

**Q: How would you approach building an attribution model for a retailer that has both online and offline conversions?**
A: First, establish identity resolution — map digital identifiers (cookies, device IDs) to membership IDs, which tie to in-store transactions. Then build a unified touchpoint table with online events (ad impressions, clicks, site visits) and offline events (in-store purchase, membership scan). For online-to-offline attribution, a conversion = in-store purchase within the attribution window of a digital touchpoint for the same resolved user. For the model itself: start with last-touch for simplicity, then implement data-driven attribution using logistic regression or Shapley values on the touchpoint sequence if data volume supports it. Key challenge: in-store touchpoints (promotions, signage, associate recommendations) are harder to capture — need to acknowledge the model is incomplete.

**Q: What is incrementality testing and how is it different from attribution?**
A: Attribution allocates credit across channels for conversions that happened — it's a retrospective accounting model. Incrementality testing measures whether the advertising *caused* an incremental conversion that wouldn't have happened otherwise. Method: hold out a random subset of the target audience from seeing the campaign (control group), compare conversion rates between exposed (treatment) and not-exposed (control). Incremental conversions = (treatment CVR - control CVR) × treatment audience size. This accounts for "would-have-converted-anyway" users that attribution incorrectly credits to the last touchpoint.

**Q: Explain how third-party cookie deprecation affects MarTech data pipelines.**
A: Third-party cookies enabled cross-site tracking — if a user visited site A and site B, an ad network could link both visits via its cookie. With 3PC deprecation: (1) Frequency capping breaks — can't tell if the same user saw your ad on 10 different sites; (2) Cross-site retargeting breaks — can't retarget users who visited your site across the web; (3) Attribution via click IDs breaks for many flows. Solutions: (1) First-party data + clean rooms (Google PAIR, Meta Advanced Matching) — match your CRM to Google's profile graph via hashed email, without sharing raw PII; (2) Server-side tracking via Conversion API (CAPI) — fire conversion events directly from your server to ad platforms, bypassing browser restrictions; (3) Privacy Sandbox APIs (Topics API) — coarse-grained interest-based targeting without individual IDs.

**Q: How do you handle a data pipeline where the same user generates 10x more events than average?**
A: This is a data skew problem. Strategies: (1) In BigQuery — partition by date, cluster by campaign; skewed users are spread across partitions by time. (2) In PySpark — salt the user_id join key: append random prefix to hot user IDs, explode the lookup table with all salt values, join on salted key. (3) Cap event count per user per session in the pipeline — user generates 1000 page views in 5 minutes? Flag as bot/crawler, exclude or sample. (4) Pre-aggregate before joining — reduce to user-session level before joining with large dimension tables.
    
**Q: What pipeline would you build to detect fraudulent ad clicks?**
A: Multiple signals: (1) Click rate anomaly — CTR > 10% per placement is suspicious; (2) Short inter-click time — same IP/device clicking 5x in 60 seconds; (3) Conversion anomaly — clicks from a specific publisher never convert; (4) Bot-like user agents; (5) IP reputation lookup (known datacenter IPs). Implementation: streaming Dataflow pipeline reading click events, joining with impression events to compute CTR per publisher/placement in real time, writing anomalies to a fraud flag table. Batch: daily aggregation comparing publisher click patterns to conversion data — publishers with high clicks and zero conversions over 7 days get flagged.
