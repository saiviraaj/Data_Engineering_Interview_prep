# Topic 5: Data Warehousing & Modeling
## Costco Sr. Data Engineer — Exhaustive Interview Textbook

---

## Table of Contents
1. [L1: Core Concepts — Fact vs Dimension, Schema Types](#l1-core-concepts)
2. [L2: Deep Technical Understanding](#l2-deep-technical-understanding)
3. [L3: Real-World Scenarios — Costco/MarTech Style](#l3-real-world-scenarios)
4. [L4: Hands-On Design & Code](#l4-hands-on-design--code)
5. [L5: Edge Cases & Pitfalls](#l5-edge-cases--pitfalls)
6. [L6: Interview Questions — Easy to Very Hard](#l6-interview-questions)

---

## L1: Core Concepts

### 1.1 OLTP vs OLAP — The Foundational Divide

Every data warehousing conversation starts with understanding why we need a warehouse at all.

**OLTP (Online Transaction Processing)**:
- Operational databases (PostgreSQL, MySQL, Oracle)
- Many small, fast read/write transactions
- Highly normalized (3NF) to avoid update anomalies
- Optimized for: INSERT, UPDATE, DELETE on individual rows
- Example: Costco's POS system recording a member purchase

**OLAP (Online Analytical Processing)**:
- Analytical databases (BigQuery, Snowflake, Redshift)
- Few large, complex read queries across millions of rows
- Denormalized for read performance
- Optimized for: SELECT with aggregations, GROUP BY, window functions
- Example: "What is the ROAS for each campaign by channel for the last 90 days?"

**Why not just query OLTP directly for analytics?**
- OLTP queries compete with production traffic → slows down the app
- OLTP schema (3NF, many joins) is wrong for analytical queries
- OLTP doesn't store history (deletes/updates overwrite records)
- OLTP can't handle the scale of analytical workloads (TBs of data)

---

### 1.2 Dimensional Modeling — The Kimball Approach

Dimensional modeling (Ralph Kimball) is the dominant design methodology for data warehouses. Core principle: model data the way business users think about it — as facts (measurements) and dimensions (context).

**Fact table**: Contains measurements/metrics of a business process.
- One row per business event (click, sale, impression, conversion)
- Numeric, additive measures (spend, revenue, clicks, quantity)
- Foreign keys to dimension tables
- Typically wide (many FK columns) but each row is "thin" (few actual facts)

**Dimension table**: Provides context for the facts.
- Describes WHO, WHAT, WHERE, WHEN, WHY
- Attributes used for filtering, grouping, labeling
- Usually wide (many descriptive columns)
- Relatively small compared to fact tables

```
Fact Table (ad_clicks):                Dimension Tables:
┌─────────────────────────────────┐    ┌──────────────────────────┐
│ click_id (PK)                   │    │ dim_campaign:            │
│ campaign_sk (FK) ───────────────┼───►│   campaign_sk            │
│ user_sk (FK) ───────────────────┼──┐ │   campaign_id (NK)       │
│ date_sk (FK) ───────────────────┼─┐│ │   campaign_name          │
│ channel_sk (FK)                 │ ││ │   channel                │
│ cost_usd (MEASURE)              │ ││ │   bidding_strategy       │
│ revenue_usd (MEASURE)           │ ││ └──────────────────────────┘
│ is_conversion (MEASURE)         │ ││
└─────────────────────────────────┘ ││ ┌──────────────────────────┐
                                     │└►│ dim_user:                │
                                     │  │   user_sk                │
                                     │  │   member_id (NK)         │
                                     │  │   loyalty_tier           │
                                     │  │   zip_code               │
                                     │  └──────────────────────────┘
                                     │
                                     └─►┌──────────────────────────┐
                                        │ dim_date:                 │
                                        │   date_sk                 │
                                        │   full_date               │
                                        │   day_of_week             │
                                        │   is_holiday              │
                                        │   fiscal_quarter          │
                                        └──────────────────────────┘
```

---

### 1.3 Star Schema vs Snowflake Schema

**Star Schema**: Dimension tables are denormalized — all attributes in one flat dimension table. Looks like a star (fact center, dimensions as points).

```
                    dim_campaign (flat)
                   ┌─────────────────────┐
                   │ campaign_sk          │
                   │ campaign_name        │
                   │ channel_name         │ ← channel embedded directly
                   │ channel_category     │ ← no separate channel table
                   │ advertiser_name      │ ← advertiser embedded
                   └─────────────────────┘
                            ↑
                    fact_ad_clicks ──► dim_user
                            ↓
                         dim_date
```

**Snowflake Schema**: Dimension tables are normalized — sub-dimensions split into separate tables.

```
                    dim_campaign
                   ┌────────────────┐
                   │ campaign_sk    │
                   │ campaign_name  │
                   │ channel_sk ────┼──► dim_channel
                   │ advertiser_sk ─┼──► dim_advertiser
                   └────────────────┘
```

**When to use each**:

| | Star | Snowflake |
|-|------|-----------|
| Query complexity | Simple (fewer joins) | More complex (more joins) |
| Query speed | Faster (fewer joins) | Slower |
| Storage | More (redundant data) | Less (normalized) |
| Maintenance | Easier to update | Updates in one place |
| BI tool friendliness | High | Lower |
| Recommended for | Analytical queries, BI tools | When dimension data changes frequently |

**Senior insight**: In BigQuery specifically, star schema is almost always preferred. BigQuery's optimizer handles hash joins efficiently, and the extra storage cost of denormalization is negligible compared to query performance and simplicity gains. Snowflake schemas in BigQuery lead to complex multi-join queries that are harder to optimize.

---

## L2: Deep Technical Understanding

### 2.1 Slowly Changing Dimensions (SCD) — All Types

SCDs handle the challenge of dimension attribute changes over time.

#### SCD Type 0 — Retain Original (No Change)

```sql
-- Dimension attribute never changes (birth date, account open date)
-- Once set, never updated regardless of what source sends
-- Example: original acquisition channel for a member

-- Implementation: no special handling needed
-- Just load once and never update that column
```

#### SCD Type 1 — Overwrite (Current Value Only)

```sql
-- Always reflect the CURRENT value; no history kept
-- Example: member email address — you only need the current one

-- Implementation: simple MERGE
MERGE INTO dim_members AS target
USING staged_members AS source
ON target.member_id = source.member_id
WHEN MATCHED THEN UPDATE SET
    target.email        = source.email,
    target.phone        = source.phone,
    target.updated_at   = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (...);

-- Consequence: if you join historical facts to this dimension,
-- you'll see the CURRENT email, not the email at time of the event
```

#### SCD Type 2 — Add New Row (Full History)

```sql
-- Most important SCD type for analytics
-- Each version of the dimension gets its own row
-- Enables point-in-time joins: "what was the campaign budget on Jan 15?"

-- Table structure
CREATE TABLE dim_campaigns (
    -- Surrogate key: technical PK, unique per row/version
    campaign_sk         STRING      NOT NULL,   -- GENERATE_UUID()

    -- Natural key: business identifier (same across all versions)
    campaign_id         STRING      NOT NULL,

    -- Dimension attributes
    campaign_name       STRING,
    daily_budget_usd    FLOAT64,
    bidding_strategy    STRING,
    status              STRING,

    -- SCD2 tracking columns
    valid_from          DATE        NOT NULL,
    valid_to            DATE,       -- NULL = currently active record
    is_current          BOOL        NOT NULL,

    -- Audit
    created_at          TIMESTAMP,
    row_hash            STRING      -- hash of all attributes for change detection
);

-- When campaign budget changes from $500 to $1000 on 2024-06-01:

-- Step 1: Close the current record
UPDATE dim_campaigns
SET
    valid_to    = DATE_SUB('2024-06-01', INTERVAL 1 DAY),  -- 2024-05-31
    is_current  = FALSE
WHERE campaign_id = 'C001'
  AND is_current = TRUE;

-- Step 2: Insert new version
INSERT INTO dim_campaigns VALUES (
    GENERATE_UUID(),    -- new surrogate key
    'C001',             -- same natural key
    'Summer Sale',
    1000.0,             -- new budget
    'target_cpa',
    'active',
    '2024-06-01',       -- valid_from
    NULL,               -- valid_to = still current
    TRUE,               -- is_current
    CURRENT_TIMESTAMP(),
    MD5('C001|Summer Sale|1000.0|target_cpa|active')
);

-- Querying: point-in-time join
-- "What was the budget for campaign C001 on March 15, 2024?"
SELECT c.daily_budget_usd
FROM dim_campaigns c
WHERE c.campaign_id = 'C001'
  AND DATE('2024-03-15') >= c.valid_from
  AND DATE('2024-03-15') <= COALESCE(c.valid_to, '9999-12-31');

-- Querying: join fact to dimension with correct historical version
SELECT
    f.click_date,
    f.campaign_id,
    f.spend_usd,
    c.daily_budget_usd,   -- budget active on click_date, not today's budget
    f.spend_usd / c.daily_budget_usd AS budget_utilization
FROM fact_ad_clicks f
JOIN dim_campaigns c
    ON f.campaign_id = c.campaign_id
    AND f.click_date >= c.valid_from
    AND f.click_date <= COALESCE(c.valid_to, '9999-12-31');
```

#### SCD Type 3 — Add New Column (Limited History)

```sql
-- Store only the PREVIOUS value in an extra column
-- Example: track one tier change for members

ALTER TABLE dim_members ADD COLUMN prev_loyalty_tier STRING;
ALTER TABLE dim_members ADD COLUMN tier_changed_date DATE;

-- When tier changes from 'Gold' to 'Platinum' on 2024-06-01:
UPDATE dim_members
SET
    prev_loyalty_tier = loyalty_tier,   -- save old value
    loyalty_tier      = 'Platinum',     -- set new value
    tier_changed_date = '2024-06-01'
WHERE member_id = 'M001';

-- Limitation: only one level of history (can't track 3+ changes)
-- Use when: exactly one previous value is sufficient

-- Advantage: single row per dimension record (simpler than SCD2)
```

#### SCD Type 4 — History Table

```sql
-- Separate current and historical versions into two tables
-- dim_campaigns: always current version only (fast lookups)
-- dim_campaigns_history: all historical versions

-- Best of both worlds:
-- Fast current lookups (no valid_to/is_current filter needed)
-- Full history available when needed

CREATE TABLE dim_campaigns AS  -- current only
SELECT * FROM source WHERE is_current = TRUE;

CREATE TABLE dim_campaigns_history AS  -- all versions
SELECT * FROM source;  -- includes all valid_from/valid_to rows
```

#### SCD Type 6 — Hybrid (1+2+3)

```sql
-- Combines SCD1, SCD2, and SCD3
-- Adds "current_*" columns to every historical row for convenience

CREATE TABLE dim_campaigns (
    campaign_sk             STRING,     -- SCD2: surrogate key
    campaign_id             STRING,     -- natural key
    -- Historical values (SCD2):
    campaign_name           STRING,     -- name at time of this version
    daily_budget_usd        FLOAT64,    -- budget at time of this version
    -- Current values (SCD1 overwrite): always current, even on old rows
    current_campaign_name   STRING,     -- today's name (overwritten on all rows)
    current_budget          FLOAT64,    -- today's budget (overwritten on all rows)
    -- SCD3: previous value
    prev_budget_usd         FLOAT64,
    -- SCD2 tracking
    valid_from              DATE,
    valid_to                DATE,
    is_current              BOOL
);

-- Benefit: can ask both "what was the budget then?" AND "what is it now?"
-- without joining back to current version separately
```

---

### 2.2 Fact Table Design Patterns

#### 2.2.1 Grain — The Most Critical Design Decision

The grain defines exactly what one row in the fact table represents. Getting this wrong ruins the entire model.

```
Too fine grain: one row per individual website click event
- Pros: maximum flexibility for analysis
- Cons: massive storage, complex queries for summary reports

Too coarse grain: one row per campaign per month
- Pros: fast queries, small storage
- Cons: can't drill down to daily, can't analyze individual events

Right grain: one row per ad click event (atomic grain)
- Store at the atomic level — you can always roll up, never drill down
- Let the analytics layer aggregate to the right level

Common grains:
- Transaction grain: one row per financial transaction
- Event grain: one row per user action (click, view, add-to-cart)
- Snapshot grain: one row per entity per time period (campaign per day)
- Accumulating snapshot: one row per business process instance (order lifecycle)
```

#### 2.2.2 Transaction Fact Table

```sql
-- One row per atomic business event (most common)
CREATE TABLE fact_ad_clicks (
    -- Surrogate keys (FKs to dimensions)
    click_sk        STRING      NOT NULL,   -- degenerate dimension or PK
    campaign_sk     STRING      NOT NULL,
    user_sk         STRING,                  -- nullable: unknown users
    date_sk         STRING      NOT NULL,
    channel_sk      STRING      NOT NULL,
    device_sk       STRING,

    -- Degenerate dimensions: IDs with no corresponding dimension table
    -- (high cardinality, no useful attributes beyond the ID itself)
    click_id        STRING      NOT NULL,    -- business transaction ID
    session_id      STRING,

    -- Measures (numeric, additive)
    cost_usd        FLOAT64     NOT NULL DEFAULT 0,
    revenue_usd     FLOAT64     DEFAULT NULL,    -- NULL if no conversion
    is_conversion   INT64       NOT NULL DEFAULT 0,  -- 0/1 flag

    -- Audit
    loaded_at       TIMESTAMP
)
PARTITION BY click_date
CLUSTER BY campaign_sk, channel_sk;
```

#### 2.2.3 Periodic Snapshot Fact Table

```sql
-- One row per entity per time period (always present, even for zero values)
-- Example: campaign performance snapshot per day

CREATE TABLE fact_campaign_daily_snapshot (
    -- Time dimension (always present)
    snapshot_date       DATE        NOT NULL,

    -- Entity key
    campaign_sk         STRING      NOT NULL,

    -- Measures: additive across time
    impressions         INT64       NOT NULL DEFAULT 0,
    clicks              INT64       NOT NULL DEFAULT 0,
    conversions         INT64       NOT NULL DEFAULT 0,
    spend_usd           FLOAT64     NOT NULL DEFAULT 0,
    revenue_usd         FLOAT64     NOT NULL DEFAULT 0,

    -- Derived metrics (store for convenience, could compute from above)
    roas                FLOAT64,    -- NULL if spend=0
    ctr                 FLOAT64,    -- NULL if impressions=0

    -- Audit
    loaded_at           TIMESTAMP
)
PARTITION BY snapshot_date
CLUSTER BY campaign_sk;

-- Key property: every campaign has a row for every day (even 0-spend days)
-- Enables: simple aggregations without handling missing dates
-- Requires: date spine × campaign cross join to fill gaps
```

#### 2.2.4 Accumulating Snapshot Fact Table

```sql
-- One row per business process lifecycle (order, campaign flight, membership)
-- Row is UPDATED as the process progresses through stages
-- Rare: most data warehouses are append-only

CREATE TABLE fact_campaign_lifecycle (
    campaign_id         STRING      NOT NULL,
    
    -- Milestone dates (fill as campaign progresses)
    campaign_created_date   DATE,
    campaign_launched_date  DATE,   -- NULL until launched
    first_click_date        DATE,   -- NULL until first click
    first_conversion_date   DATE,   -- NULL until first conversion
    campaign_ended_date     DATE,   -- NULL if still active
    
    -- Cumulative measures (updated over time)
    total_spend_usd         FLOAT64 DEFAULT 0,
    total_conversions       INT64   DEFAULT 0,
    total_revenue_usd       FLOAT64 DEFAULT 0,
    
    -- Lag measures
    days_to_first_click     INT64,  -- filled when first_click_date set
    days_to_first_conversion INT64,
    
    loaded_at               TIMESTAMP
);

-- Querying: "How long do campaigns typically take to get first conversion?"
SELECT AVG(days_to_first_conversion) AS avg_days_to_convert
FROM fact_campaign_lifecycle
WHERE campaign_created_date >= '2024-01-01'
  AND days_to_first_conversion IS NOT NULL;
```

---

### 2.3 Partitioning & Clustering in BigQuery — DWH Focus

#### 2.3.1 Partitioning Strategy for Warehouse Tables

```sql
-- FACT TABLE STRATEGY: partition by the event date
-- Most fact table queries filter by date → huge partition pruning benefit

CREATE TABLE fact_ad_clicks
PARTITION BY click_date    -- DATE column (daily granularity)
OPTIONS (
    partition_expiration_days = 730   -- auto-delete after 2 years
)
AS SELECT ...;

-- DIMENSION TABLE STRATEGY: usually NOT partitioned
-- Dimension tables are small (thousands to millions of rows, not billions)
-- Full scans are fast; partitioning adds complexity without benefit

CREATE TABLE dim_campaigns AS SELECT ...;
-- No partition by clause — full table scans are fine at dimension scale

-- EXCEPTION: SCD2 dimension tables with long history
-- If dim_campaigns has 10 years of history with millions of version rows:
CREATE TABLE dim_campaigns
PARTITION BY valid_from   -- partition by when the version became active
AS SELECT ...;
```

#### 2.3.2 Clustering Strategy

```sql
-- FACT TABLE CLUSTERING: cluster by the dimensions used most in queries
-- First cluster column = most selective filter in most queries

CREATE TABLE fact_ad_clicks
PARTITION BY click_date
CLUSTER BY campaign_id, channel, device_type, user_segment;
-- Query: WHERE click_date = '2024-01-15' AND campaign_id = 'C001'
--   → partition pruning on click_date (eliminates all other dates)
--   → clustering pruning on campaign_id (eliminates other campaign blocks)

-- RULE: put high-cardinality columns first in CLUSTER BY
-- (more distinct values = more effective block pruning)
-- RULE: put columns most commonly filtered first
```

---

### 2.4 Data Marts vs Data Lakehouse

#### Data Mart
A data mart is a subject-specific subset of the data warehouse — optimized for a specific team or business function.

```
Enterprise Data Warehouse (BigQuery — all data)
├── Marketing Data Mart
│   ├── mart_campaign_performance
│   ├── mart_roas_by_channel
│   └── mart_member_acquisition
├── Finance Data Mart
│   ├── mart_revenue_by_product
│   └── mart_campaign_roi
└── Member Analytics Mart
    ├── mart_member_ltv
    └── mart_cohort_retention
```

**Why marts**: Reduces query complexity for domain users, faster performance (pre-aggregated), controlled access (finance users see only finance mart), hides implementation complexity.

#### Data Lakehouse
A lakehouse combines the raw storage of a data lake with the analytical query capabilities of a data warehouse.

```
Traditional architecture:
  Data Lake (GCS) → batch ETL → Data Warehouse (BigQuery)
  Raw storage         separate   structured queries

Lakehouse architecture:
  Data Lake (GCS/BigLake) ← directly queryable from BigQuery
  + BigQuery as query engine over GCS files
  + Metadata via Dataplex/BigLake
  + ACID transactions (optional: BigLake Managed Tables)
```

**BigLake** (GCP's lakehouse approach):
```sql
-- Create external table pointing to GCS Parquet files
-- Query them with BigQuery SQL as if they were native tables
CREATE EXTERNAL TABLE `project.dataset.external_clicks`
WITH CONNECTION `us.my-connection`
OPTIONS (
    format = 'PARQUET',
    uris = ['gs://costco-data-lake/clicks/*.parquet'],
    hive_partition_uri_prefix = 'gs://costco-data-lake/clicks/'
);

-- Now query raw GCS files with BigQuery SQL
SELECT campaign_id, COUNT(*) FROM `project.dataset.external_clicks`
WHERE click_date = '2024-01-15'
GROUP BY campaign_id;
-- Partition pruning works on GCS files too!
```

---

## L3: Real-World Scenarios — Costco/MarTech Style

### 3.1 Scenario: Design a Data Warehouse for Costco MarTech

**Business requirements**:
- Track campaign performance across Google, Meta, TikTok, and organic channels
- Support member-level analysis (which campaigns acquired which members)
- Historical reporting (SCD2 for budgets, campaign names)
- Real-time BI via Looker

**Dimensional model**:

```sql
-- ============================================================
-- DIMENSION: dim_date (pre-generated, 10 years)
-- ============================================================
CREATE TABLE dim_date AS
SELECT
    FORMAT_DATE('%Y%m%d', d)    AS date_sk,
    d                           AS full_date,
    EXTRACT(YEAR FROM d)        AS year,
    EXTRACT(MONTH FROM d)       AS month,
    FORMAT_DATE('%B', d)        AS month_name,
    EXTRACT(DAY FROM d)         AS day_of_month,
    EXTRACT(DAYOFWEEK FROM d)   AS day_of_week_num,
    FORMAT_DATE('%A', d)        AS day_of_week_name,
    EXTRACT(WEEK FROM d)        AS week_of_year,
    EXTRACT(QUARTER FROM d)     AS quarter,
    d = LAST_DAY(d)             AS is_month_end,
    FORMAT_DATE('%Y-Q%Q', d)    AS fiscal_quarter_label,
    -- Costco fiscal year starts in September
    CASE
        WHEN EXTRACT(MONTH FROM d) >= 9
        THEN EXTRACT(YEAR FROM d) + 1
        ELSE EXTRACT(YEAR FROM d)
    END                         AS fiscal_year
FROM UNNEST(GENERATE_DATE_ARRAY('2020-01-01', '2030-12-31', INTERVAL 1 DAY)) AS d;

-- ============================================================
-- DIMENSION: dim_campaign (SCD Type 2)
-- ============================================================
CREATE TABLE dim_campaign (
    campaign_sk         STRING      NOT NULL,   -- GENERATE_UUID()
    campaign_id         STRING      NOT NULL,   -- natural key
    campaign_name       STRING,
    channel             STRING,     -- google_search, meta_display, etc.
    campaign_type       STRING,     -- prospecting, retargeting, brand
    daily_budget_usd    FLOAT64,
    target_cpa_usd      FLOAT64,
    bidding_strategy    STRING,
    advertiser_id       STRING,
    -- SCD2 fields
    valid_from          DATE        NOT NULL,
    valid_to            DATE,
    is_current          BOOL        NOT NULL,
    row_hash            STRING
)
PARTITION BY valid_from
CLUSTER BY campaign_id;

-- ============================================================
-- DIMENSION: dim_member (SCD Type 2 for loyalty tier)
-- ============================================================
CREATE TABLE dim_member (
    member_sk           STRING      NOT NULL,
    member_id           STRING      NOT NULL,
    acquisition_channel STRING,     -- SCD0: never changes
    zip_code            STRING,
    loyalty_tier        STRING,     -- GOLD/PLATINUM/EXECUTIVE
    age_band            STRING,
    household_size_band STRING,
    -- SCD2 tracking
    valid_from          DATE        NOT NULL,
    valid_to            DATE,
    is_current          BOOL        NOT NULL
)
PARTITION BY valid_from
CLUSTER BY member_id;

-- ============================================================
-- FACT TABLE: fact_ad_clicks (transaction grain, atomic)
-- ============================================================
CREATE TABLE fact_ad_clicks (
    -- Surrogate keys
    campaign_sk         STRING      NOT NULL,
    member_sk           STRING,                 -- nullable
    date_sk             STRING      NOT NULL,
    
    -- Degenerate dimensions
    click_id            STRING      NOT NULL,
    session_id          STRING,
    
    -- Date for partitioning
    click_date          DATE        NOT NULL,
    
    -- Measures
    cost_usd            FLOAT64     NOT NULL DEFAULT 0,
    is_conversion       INT64       NOT NULL DEFAULT 0,
    revenue_usd         FLOAT64,
    
    loaded_at           TIMESTAMP
)
PARTITION BY click_date
CLUSTER BY campaign_sk, date_sk;

-- ============================================================
-- FACT TABLE: fact_campaign_daily_snapshot (periodic snapshot)
-- ============================================================
CREATE TABLE fact_campaign_daily_snapshot (
    snapshot_date       DATE        NOT NULL,
    campaign_sk         STRING      NOT NULL,
    impressions         INT64       NOT NULL DEFAULT 0,
    clicks              INT64       NOT NULL DEFAULT 0,
    spend_usd           FLOAT64     NOT NULL DEFAULT 0,
    conversions         INT64       NOT NULL DEFAULT 0,
    revenue_usd         FLOAT64     NOT NULL DEFAULT 0,
    roas                FLOAT64,
    ctr                 FLOAT64,
    loaded_at           TIMESTAMP
)
PARTITION BY snapshot_date
CLUSTER BY campaign_sk;
```

---

### 3.2 Scenario: Populate the Periodic Snapshot

```sql
-- Daily job: populate fact_campaign_daily_snapshot for yesterday
-- Include all active campaigns even if they had zero activity

INSERT INTO fact_campaign_daily_snapshot
PARTITION (snapshot_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY))

WITH active_campaigns AS (
    -- All campaigns active on the snapshot date
    SELECT campaign_sk, campaign_id
    FROM dim_campaign
    WHERE is_current = TRUE
      OR (valid_from <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
          AND COALESCE(valid_to, '9999-12-31') >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY))
),

daily_actuals AS (
    -- Actual metrics for yesterday
    SELECT
        c.campaign_sk,
        SUM(impressions)        AS impressions,
        SUM(clicks)             AS clicks,
        SUM(spend_usd)          AS spend_usd,
        SUM(is_conversion)      AS conversions,
        SUM(COALESCE(revenue_usd, 0)) AS revenue_usd
    FROM fact_ad_clicks f
    JOIN dim_campaign c ON f.campaign_sk = c.campaign_sk
    WHERE f.click_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    GROUP BY c.campaign_sk
)

SELECT
    DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)    AS snapshot_date,
    ac.campaign_sk,
    COALESCE(da.impressions, 0)                  AS impressions,
    COALESCE(da.clicks, 0)                       AS clicks,
    COALESCE(da.spend_usd, 0)                    AS spend_usd,
    COALESCE(da.conversions, 0)                  AS conversions,
    COALESCE(da.revenue_usd, 0)                  AS revenue_usd,
    SAFE_DIVIDE(da.revenue_usd, da.spend_usd)    AS roas,
    SAFE_DIVIDE(da.clicks, da.impressions)       AS ctr,
    CURRENT_TIMESTAMP()                          AS loaded_at
FROM active_campaigns ac
LEFT JOIN daily_actuals da USING (campaign_sk);
-- LEFT JOIN ensures zero-activity campaigns still get a row
```

---

## L4: Hands-On Design & Code

### 4.1 Build a Date Dimension

```sql
-- Full-featured date dimension for warehouse
CREATE OR REPLACE TABLE dim_date AS
WITH dates AS (
    SELECT d AS full_date
    FROM UNNEST(GENERATE_DATE_ARRAY('2020-01-01', '2030-12-31', INTERVAL 1 DAY)) AS d
)
SELECT
    FORMAT_DATE('%Y%m%d', full_date)    AS date_sk,
    full_date,
    EXTRACT(YEAR FROM full_date)        AS year,
    EXTRACT(MONTH FROM full_date)       AS month_num,
    FORMAT_DATE('%B', full_date)        AS month_name,
    FORMAT_DATE('%b', full_date)        AS month_abbr,
    EXTRACT(DAY FROM full_date)         AS day_of_month,
    EXTRACT(DAYOFWEEK FROM full_date)   AS day_of_week_num,  -- 1=Sun
    FORMAT_DATE('%A', full_date)        AS day_of_week_name,
    FORMAT_DATE('%a', full_date)        AS day_of_week_abbr,
    EXTRACT(WEEK FROM full_date)        AS week_of_year,
    DATE_TRUNC(full_date, WEEK)         AS week_start_date,
    DATE_TRUNC(full_date, MONTH)        AS month_start_date,
    LAST_DAY(full_date, MONTH)          AS month_end_date,
    EXTRACT(QUARTER FROM full_date)     AS quarter_num,
    CONCAT('Q', CAST(EXTRACT(QUARTER FROM full_date) AS STRING)) AS quarter_label,
    DATE_TRUNC(full_date, QUARTER)      AS quarter_start_date,
    -- Is it a US federal holiday? (simplified)
    full_date IN (
        '2024-01-01', '2024-07-04', '2024-12-25'  -- expand as needed
    )                                   AS is_holiday,
    EXTRACT(DAYOFWEEK FROM full_date) NOT IN (1, 7) AS is_weekday,
    EXTRACT(DAYOFWEEK FROM full_date) IN (1, 7) AS is_weekend,
    -- Fiscal year (Costco: Sept 1 start)
    CASE
        WHEN EXTRACT(MONTH FROM full_date) >= 9
        THEN EXTRACT(YEAR FROM full_date) + 1
        ELSE EXTRACT(YEAR FROM full_date)
    END                                 AS fiscal_year
FROM dates;
```

### 4.2 Implement SCD2 Update Logic

```python
# Python implementation of SCD2 update for BigQuery

from google.cloud import bigquery
import hashlib
import json

def compute_row_hash(row: dict, hash_columns: list) -> str:
    """Compute hash of relevant columns for change detection."""
    values = '|'.join(str(row.get(c, '')) for c in sorted(hash_columns))
    return hashlib.md5(values.encode()).hexdigest()

def apply_scd2_update(
    bq: bigquery.Client,
    dim_table: str,
    staged_table: str,
    natural_key: str,
    hash_columns: list,
    effective_date: str
):
    """
    Apply SCD2 logic:
    1. Compare staged rows to current dim rows using row hash
    2. Close changed rows (set valid_to, is_current=FALSE)
    3. Insert new versions for changed + new rows
    """

    merge_sql = f"""
    -- Step 1: Close changed records
    UPDATE `{dim_table}` AS dim
    SET
        dim.valid_to    = DATE_SUB('{effective_date}', INTERVAL 1 DAY),
        dim.is_current  = FALSE
    WHERE dim.is_current = TRUE
      AND EXISTS (
          SELECT 1 FROM `{staged_table}` AS stg
          WHERE stg.{natural_key} = dim.{natural_key}
            AND stg.row_hash != dim.row_hash   -- something changed
      );

    -- Step 2: Insert new versions (for changed records) and new records
    INSERT INTO `{dim_table}`
    SELECT
        GENERATE_UUID()         AS campaign_sk,
        stg.*,
        '{effective_date}'      AS valid_from,
        NULL                    AS valid_to,
        TRUE                    AS is_current,
        CURRENT_TIMESTAMP()     AS created_at
    FROM `{staged_table}` stg
    WHERE
        -- Changed records: exist in dim but hash differs
        EXISTS (
            SELECT 1 FROM `{dim_table}` dim
            WHERE dim.{natural_key} = stg.{natural_key}
              AND dim.row_hash != stg.row_hash
        )
        OR
        -- New records: don't exist in dim at all
        NOT EXISTS (
            SELECT 1 FROM `{dim_table}` dim
            WHERE dim.{natural_key} = stg.{natural_key}
        );
    """

    bq.query(merge_sql).result()
```

---

## L5: Edge Cases & Pitfalls

### 5.1 Fact Table Fan-Out — The Silent Row Multiplication Bug

```sql
-- Problem: joining a fact table to a dimension where the join key
-- is not unique in the dimension (violates the model)

-- dim_campaign has multiple rows per campaign_id (SCD2)
-- If you join WITHOUT filtering to the correct version:

SELECT f.*, c.campaign_name, c.daily_budget_usd
FROM fact_ad_clicks f
JOIN dim_campaign c ON f.campaign_sk = c.campaign_sk;
-- Wait — this uses campaign_SK (surrogate key), not campaign_ID
-- Surrogate key is unique per row → no fan-out ✓

-- DANGER: joining on NATURAL key without SCD2 filter
SELECT f.*, c.campaign_name
FROM fact_ad_clicks f
JOIN dim_campaign c ON f.campaign_id = c.campaign_id;
-- If C001 has 3 versions in dim_campaign: 3 rows per click! → 3x row count
-- ALWAYS filter SCD2 dimensions:

SELECT f.*, c.campaign_name
FROM fact_ad_clicks f
JOIN dim_campaign c
    ON f.campaign_id = c.campaign_id
    AND c.is_current = TRUE;  -- current version only
-- OR: use surrogate key (fact table stores campaign_SK pointing to exact version)
```

### 5.2 Missing Grain Declaration

```sql
-- Mistake: unclear grain leads to incorrect aggregations

-- "Daily campaign performance" — what's the grain?
-- Option A: one row per campaign per day (correct for snapshot)
-- Option B: one row per campaign per day per device_type (finer grain)
-- Option C: one row per click (atomic grain)

-- If BI tool doesn't know the grain, it might double-count:
SELECT report_date, SUM(spend_usd)
FROM mart_campaign_performance_by_device   -- Option B grain
GROUP BY report_date;
-- This gives total spend per day — correct ONLY if understanding is "sum across all devices"
-- But if user thinks grain is Option A (one row per campaign per day),
-- they might think SUM(spend_usd) = total spend per day, which would be overcounted
-- if a campaign has 3 device types (mobile, desktop, tablet)

-- Document grain explicitly in table description and README
-- Never mix grains in a single mart table
```

### 5.3 Null Foreign Keys in Fact Tables

```sql
-- Fact table has member_sk = NULL (unknown users / non-member visitors)
-- This is EXPECTED — not all ad clicks come from known members

-- Problem: JOIN drops NULL FK rows
SELECT f.campaign_id, m.loyalty_tier, COUNT(*) AS clicks
FROM fact_ad_clicks f
INNER JOIN dim_member m ON f.member_sk = m.member_sk  -- drops unknown users!
GROUP BY 1, 2;

-- Better: LEFT JOIN + handle NULLs
SELECT
    f.campaign_id,
    COALESCE(m.loyalty_tier, 'Non-Member') AS loyalty_tier,
    COUNT(*) AS clicks
FROM fact_ad_clicks f
LEFT JOIN dim_member m ON f.member_sk = m.member_sk
GROUP BY 1, 2;

-- Best practice: create a "Not Applicable" or "Unknown" surrogate key
-- FK = -1 or 'UNKNOWN' points to a placeholder dimension row
-- Avoids NULLs in FK columns while preserving referential integrity
INSERT INTO dim_member VALUES ('UNKNOWN', 'UNKNOWN', 'Unknown', NULL, NULL, NULL, ...);
-- Fact table FK = 'UNKNOWN' (not NULL) for unidentified users
```

---

## L6: Interview Questions — Easy to Very Hard

### EASY

**Q1: What is the difference between a fact table and a dimension table?**

**Answer**: A fact table contains the measurable, numeric business metrics — the "what happened." Each row represents one occurrence of a business event (an ad click, a sale, a conversion). The columns are numeric measures (spend_usd, clicks, revenue) and foreign keys to dimension tables.

A dimension table provides the context — the "who, what, where, when, why" of the event. Dimension tables describe the entities involved: which campaign (with its name, channel, budget), which member (with their loyalty tier, zip code), which date (with weekday/holiday flags). Dimension tables are typically wide (many descriptive columns) and small compared to fact tables.

The star schema joins fact to dimensions: you query the fact table for metrics and JOIN to dimensions for labels and filters.

---

**Q2: What is SCD Type 2 and when would you use it?**

**Answer**: SCD Type 2 (Slowly Changing Dimension Type 2) preserves the full history of dimension attribute changes by adding a new row for each change, rather than overwriting the old value. Each row has `valid_from`, `valid_to`, and `is_current` columns to track which version was active when.

Use it when: historical accuracy matters for business analysis. Example — a campaign's daily budget changes from $500 to $1,000 on June 1. A stakeholder asks "what was our ROAS for May?" If we used SCD Type 1 (overwrite), the May report would show a $1,000 budget — incorrect. With SCD Type 2, the fact table's campaign_sk points to the $500-budget version for May events and the $1,000-budget version for June events. The historical report is accurate.

Don't use it when: history doesn't matter (email address changes — you only care about current email), or when the dimension changes too frequently (SCD2 can cause dimension table explosion).

---

### MEDIUM

**Q3: What is the grain of a fact table and why is it the most important design decision?**

**Answer**: The grain defines precisely what one row in the fact table represents. It answers: "one row = one ___." Examples: one row per ad click, one row per campaign per day, one row per transaction per line item.

It's the most important design decision because: once you set the grain, every fact and dimension in the table must be consistent with it. If the grain is "one row per ad click" but you try to store "impressions served by this campaign today" in the same table, the number would need to be repeated for every click — that's wrong. Mixing grains causes aggregation errors that are very hard to detect.

The rule: always design at the most atomic (finest) grain. Coarser aggregations can always be computed from atomic-grain facts; you can never disaggregate a coarse fact into finer detail. For ad events: grain = one row per click event. For campaign reporting: a separate periodic snapshot fact table at grain = one row per campaign per day.

---

**Q4: You're designing a data warehouse for Costco's MarTech. A marketing analyst says "I want to analyze campaign performance by member loyalty tier." Walk me through your dimensional model design.**

**Answer**:

**Identify the business process**: Ad campaign performance, analyzed at the intersection of campaign and member.

**Declare the grain**: One row per ad click event (atomic). This lets us attribute each click/conversion to a specific campaign AND a specific member.

**Identify dimensions**: 
- dim_campaign (campaign name, channel, type, budget — SCD2 for budget changes)
- dim_member (member loyalty tier, zip code, household size — SCD2 for tier changes)
- dim_date (date, day of week, holiday flag, fiscal quarter)
- dim_channel (google/meta/organic, paid/organic flag)

**Fact table**: fact_ad_clicks with measures: cost_usd, revenue_usd, is_conversion.

**Key design decisions**:
1. Member SK can be NULL (non-member ad clicks) — handle with "Unknown" surrogate key
2. Use SCD2 for dim_member.loyalty_tier — if a member upgrades from Gold to Platinum in March, I want March analyses to show Gold tier for pre-March events
3. Campaign budget changes → SCD2 for dim_campaign.daily_budget_usd
4. Point-in-time join: `fact_ad_clicks.click_date BETWEEN dim_member.valid_from AND COALESCE(dim_member.valid_to, '9999-12-31')`

**The analysis becomes**:
```sql
SELECT
    dc.channel,
    dm.loyalty_tier,
    SUM(f.spend_usd)    AS spend,
    SUM(f.revenue_usd)  AS revenue,
    SAFE_DIVIDE(SUM(f.revenue_usd), SUM(f.spend_usd)) AS roas
FROM fact_ad_clicks f
JOIN dim_campaign dc ON f.campaign_sk = dc.campaign_sk
JOIN dim_member dm ON f.member_sk = dm.member_sk
JOIN dim_date dd ON f.date_sk = dd.date_sk
WHERE dd.full_date BETWEEN '2024-01-01' AND '2024-03-31'
GROUP BY 1, 2;
```

---

### HARD

**Q5: A BI analyst reports that the total spend from the campaign mart ($1.2M) doesn't match the sum from the fact table ($1.5M) for the same period. How do you investigate?**

**What they're testing**: Fact table/mart integrity, join logic understanding, debugging.

**Answer**:

**Step 1: Check the grains**
```sql
-- Fact table query (atomic grain)
SELECT SUM(spend_usd) FROM fact_ad_clicks
WHERE click_date BETWEEN '2024-01-01' AND '2024-01-31';
-- Result: $1.5M

-- Mart table query (periodic snapshot grain)
SELECT SUM(spend_usd) FROM fact_campaign_daily_snapshot
WHERE snapshot_date BETWEEN '2024-01-01' AND '2024-01-31';
-- Result: $1.2M
```

**Step 2: Identify the discrepancy pattern**
```sql
-- Which campaigns/dates have mismatches?
SELECT
    a.snapshot_date,
    a.campaign_id,
    a.spend_usd AS mart_spend,
    b.spend_usd AS fact_spend,
    a.spend_usd - b.spend_usd AS diff
FROM fact_campaign_daily_snapshot a
JOIN (
    SELECT click_date, campaign_id, SUM(spend_usd) AS spend_usd
    FROM fact_ad_clicks
    GROUP BY 1, 2
) b ON a.snapshot_date = b.click_date AND a.campaign_id = b.campaign_id
WHERE ABS(a.spend_usd - b.spend_usd) > 0.01
ORDER BY ABS(diff) DESC;
```

**Common root causes**:
1. **SCD2 fan-out in mart build**: The mart SQL joins fact to dim_campaign on natural key without `is_current = TRUE` → fan-out multiplies spend by number of versions
2. **Date boundary mismatch**: Fact table uses PST click_date, mart uses UTC click_date
3. **Different dedup logic**: Fact has deduplication, mart doesn't (or vice versa)
4. **Partial coverage**: Mart missing some campaigns (INNER JOIN dropped unmatched campaigns)
5. **Backdated data**: Fact table picks up late-arriving clicks, mart snapshot doesn't update

**Fix**: Find the specific campaign/date with largest discrepancy, trace the mart build SQL for that combination, compare compiled SQL against fact table query.

---

### VERY HARD

**Q6: Design a data warehousing strategy for Costco with these constraints: 5TB fact tables, 50+ dimensions, 200 active BI users (100 daily dashboards), query SLA < 5 seconds for standard reports, < 30 seconds for ad hoc. Budget: minimize BigQuery costs.**

**What they're testing**: Enterprise DWH design, performance engineering, cost awareness.

**Answer**:

**Layer 1: Storage design**

All fact tables:
- Partition by event_date (daily)
- Cluster by 2-3 most common filter columns (campaign_id, channel)
- `require_partition_filter = TRUE` to prevent accidental full scans

Dimension tables:
- No partitioning (small enough for full scan)
- Materialize with DBT table materialization (not views)

**Layer 2: Mart architecture — the key performance lever**

Rather than 200 users querying the 5TB fact tables directly, build pre-aggregated marts:

```
Raw Facts (5TB atomic): → read rarely (for ad hoc deep-dive only)
├── mart_campaign_daily (partition by date, cluster by campaign) → 50GB
├── mart_channel_weekly (partition by week) → 5GB
├── mart_member_monthly (partition by month) → 10GB
└── mart_executive_summary (pre-aggregated top-level KPIs) → 500MB
```

100 daily dashboard queries hit the pre-aggregated marts (50-500MB scans) not the 5TB fact table. Massive cost reduction.

**Layer 3: BigQuery BI Engine for dashboard queries**

```
BigQuery BI Engine: in-memory query acceleration
- Allocate 10-50 GB of BI Engine memory
- Looker/Tableau dashboard queries: sub-second (BI Engine cache hit)
- Cost: ~$0.04/GB/hour (~$30-150/month for 10-50GB)
- ROI: eliminates most BigQuery slot usage for dashboard queries
```

**Layer 4: DBT for mart refresh strategy**

```python
# mart_campaign_daily: refresh daily (new partition each day)
# mart_channel_weekly: refresh weekly (new partition each week)
# mart_executive_summary: refresh daily (small, always current)

# Use incremental models for large marts:
# Only process new dates, not full recompute
```

**Layer 5: Query governance**

- Set per-user daily byte quota (e.g., 1TB/user/day) to prevent expensive ad hoc queries
- Require partition filter on raw fact tables
- Provide query templates for common analyses
- Monitor expensive queries weekly and optimize top-10 recurring expensive queries

**Expected cost**:
- 200 users × 100 queries/day × 50MB average mart scan = 1TB/day
- 1TB/day × $6.25/TB = $6.25/day = ~$190/month for BI queries
- BI Engine: ~$100/month
- Storage (5TB active + 20TB cold): ~$300/month
- Total: ~$590/month vs unoptimized ~$5,000-15,000/month

---

## Summary: Data Warehousing — Senior Mastery Checklist

| Skill | What Senior Looks Like |
|-------|------------------------|
| Fact vs dimension | Clear definitions; grain, measures, degenerate dims |
| Star vs snowflake | Makes decision based on query patterns; recommends star for BigQuery |
| SCD types | Can implement SCD2 from scratch; knows when SCD1/3/6 are appropriate |
| Grain declaration | Always declares grain first; knows grain violation bugs |
| Fact table types | Transaction, periodic snapshot, accumulating snapshot — when to use each |
| Partitioning/clustering | Facts by date, cluster by common filters, no partition on small dims |
| Data marts | Designs mart layer to shield BI users from raw facts |
| Lakehouse | Understands BigLake/external tables for GCS-based queries |
| Cost awareness | Quantifies query costs; designs pre-aggregation strategy |
| Enterprise design | Handles 5TB facts, 200 users, SLA requirements end-to-end |
