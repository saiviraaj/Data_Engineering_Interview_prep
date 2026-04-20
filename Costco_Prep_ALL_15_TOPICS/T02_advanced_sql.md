# Topic 2: Advanced SQL (🔥 CORE SKILL)
## Costco Sr. Data Engineer — Exhaustive Interview Textbook

---

## Table of Contents
1. [L1: Core Concepts — Joins, Filters, Aggregations](#l1-core-concepts)
2. [L2: Deep Technical Understanding](#l2-deep-technical-understanding)
3. [L3: Real-World Scenarios — Costco/MarTech Style](#l3-real-world-scenarios)
4. [L4: Hands-On Coding](#l4-hands-on-coding)
5. [L5: Edge Cases & Pitfalls](#l5-edge-cases--pitfalls)
6. [L6: Interview Questions — Easy to Very Hard](#l6-interview-questions)

---

## L1: Core Concepts

### 1.1 The SQL Execution Order (Most Misunderstood Concept)

SQL is written in a specific ORDER but executed in a completely different order. Misunderstanding this is the root cause of 80% of SQL bugs.

**Written order** (how you type it):
```
SELECT → FROM → WHERE → GROUP BY → HAVING → ORDER BY → LIMIT
```

**Execution order** (how the engine processes it):
```
1. FROM      — identify source tables, apply JOINs
2. WHERE     — filter rows BEFORE grouping
3. GROUP BY  — form groups
4. HAVING    — filter groups AFTER aggregation
5. SELECT    — compute output columns (aliases defined here)
6. DISTINCT  — remove duplicates from output
7. ORDER BY  — sort (can reference SELECT aliases)
8. LIMIT     — truncate output
```

**Why this matters**:
```sql
-- WRONG: can't use SELECT alias in WHERE (alias not defined yet at WHERE step)
SELECT spend_usd * 1.1 AS adjusted_spend
FROM campaigns
WHERE adjusted_spend > 1000;  -- ERROR: unknown column 'adjusted_spend'

-- CORRECT: repeat the expression, or wrap in subquery/CTE
SELECT spend_usd * 1.1 AS adjusted_spend
FROM campaigns
WHERE spend_usd * 1.1 > 1000;

-- OR use CTE (cleaner)
WITH adjusted AS (
    SELECT spend_usd * 1.1 AS adjusted_spend FROM campaigns
)
SELECT * FROM adjusted WHERE adjusted_spend > 1000;

-- CORRECT for HAVING (runs after GROUP BY, can use aggregates)
SELECT campaign_id, SUM(spend_usd) AS total_spend
FROM daily_performance
GROUP BY campaign_id
HAVING SUM(spend_usd) > 10000;  -- OK: HAVING runs after GROUP BY
```

---

### 1.2 Joins — Complete Reference

**INNER JOIN**: Only rows where the join condition is TRUE in BOTH tables.
```sql
SELECT c.campaign_name, p.spend_usd
FROM campaigns c
INNER JOIN performance p ON c.campaign_id = p.campaign_id;
-- Rows with no matching performance record are DROPPED
```

**LEFT JOIN** (LEFT OUTER JOIN): All rows from left table; matching rows from right (NULL if no match).
```sql
SELECT c.campaign_name, COALESCE(p.spend_usd, 0) AS spend_usd
FROM campaigns c
LEFT JOIN performance p ON c.campaign_id = p.campaign_id;
-- All campaigns returned; campaigns with no performance get NULL spend
```

**RIGHT JOIN**: Mirror of LEFT JOIN. Rarely used — just swap table order and use LEFT JOIN.

**FULL OUTER JOIN**: All rows from both tables; NULL where no match on either side.
```sql
SELECT 
    COALESCE(a.date, b.date) AS report_date,
    a.google_spend,
    b.meta_spend
FROM google_performance a
FULL OUTER JOIN meta_performance b ON a.date = b.date;
-- Returns dates that exist in Google only, Meta only, or both
```

**CROSS JOIN**: Every row from left × every row from right. Cardinality = M × N.
```sql
-- Use case: generate all (campaign, date) combinations
SELECT c.campaign_id, d.report_date
FROM campaigns c
CROSS JOIN date_spine d
WHERE d.report_date BETWEEN c.start_date AND c.end_date;
```

**SEMI JOIN** (EXISTS / IN): Return left rows where match exists in right, but don't add right columns.
```sql
-- Campaigns that had at least one click today
SELECT campaign_id, campaign_name FROM campaigns c
WHERE EXISTS (
    SELECT 1 FROM clicks cl
    WHERE cl.campaign_id = c.campaign_id
      AND cl.click_date = CURRENT_DATE()
);
-- Equivalent: WHERE campaign_id IN (SELECT campaign_id FROM clicks WHERE ...)
-- Semi-join is more efficient: stops searching after first match found
```

**ANTI JOIN** (NOT EXISTS / NOT IN): Return left rows where NO match exists in right.
```sql
-- Campaigns with zero clicks (not in clicks table)
SELECT campaign_id, campaign_name FROM campaigns c
WHERE NOT EXISTS (
    SELECT 1 FROM clicks cl
    WHERE cl.campaign_id = c.campaign_id
      AND cl.click_date = CURRENT_DATE()
);
-- WARNING: NOT IN with NULLs is dangerous (see L5
```

---

### 1.3 Aggregation Functions Reference

```sql
SELECT
    campaign_id,
    COUNT(*)                            AS total_rows,
    COUNT(cost_usd)                     AS non_null_cost_rows,
    COUNT(DISTINCT user_id)             AS unique_users,
    SUM(cost_usd)                       AS total_cost,
    AVG(cost_usd)                       AS avg_cost,
    MIN(clicked_at)                     AS first_click,
    MAX(clicked_at)                     AS last_click,
    STDDEV(cost_usd)                    AS cost_stddev,
    VARIANCE(cost_usd)                  AS cost_variance,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cost_usd)   AS median_cost,  -- exact
    APPROX_QUANTILES(cost_usd, 100)[OFFSET(50)]             AS approx_median, -- BigQuery
    STRING_AGG(device_type, ', ' ORDER BY device_type)      AS devices_list,
    ARRAY_AGG(click_id ORDER BY clicked_at LIMIT 10)        AS recent_clicks
FROM ad_clicks
GROUP BY campaign_id;
```

---

## L2: Deep Technical Understanding

### 2.1 Window Functions — The Complete Architecture

Window functions compute values across a set of rows related to the current row — without collapsing them (unlike GROUP BY). They are the single most important advanced SQL skill for data engineering interviews.

**Full syntax**:
```sql
function_name() OVER (
    [PARTITION BY partition_expression, ...]
    [ORDER BY sort_expression [ASC|DESC], ...]
    [ROWS|RANGE BETWEEN frame_start AND frame_end]
)
```

**Frame options**:
```
UNBOUNDED PRECEDING    = from start of partition
N PRECEDING            = N rows/values before current
CURRENT ROW            = current row
N FOLLOWING            = N rows/values after current
UNBOUNDED FOLLOWING    = to end of partition
```

#### 2.1.1 Ranking Functions

```sql
SELECT
    campaign_id,
    channel,
    roas,
    spend_usd,

    -- Unique sequential number — no gaps, no ties
    ROW_NUMBER() OVER (PARTITION BY channel ORDER BY roas DESC)     AS row_num,

    -- Tied rows share rank; next rank skips (1,1,3,4)
    RANK() OVER (PARTITION BY channel ORDER BY roas DESC)           AS rnk,

    -- Tied rows share rank; no skip (1,1,2,3)
    DENSE_RANK() OVER (PARTITION BY channel ORDER BY roas DESC)     AS dense_rnk,

    -- Relative rank as fraction: (rank-1)/(n-1)
    PERCENT_RANK() OVER (PARTITION BY channel ORDER BY roas DESC)   AS pct_rank,

    -- Cumulative distribution: fraction of rows <= current
    CUME_DIST() OVER (PARTITION BY channel ORDER BY roas DESC)      AS cume_dist,

    -- Divide into N equal buckets
    NTILE(4) OVER (ORDER BY roas DESC)                              AS roas_quartile,
    NTILE(10) OVER (ORDER BY spend_usd DESC)                        AS spend_decile

FROM mart_campaign_performance
WHERE report_date = CURRENT_DATE() - 1;
```

#### 2.1.2 LAG / LEAD — Time-Series Patterns

```sql
SELECT
    report_date,
    campaign_id,
    spend_usd,
    roas,

    -- Previous value (1 row back, 3rd arg = default if NULL)
    LAG(spend_usd, 1, 0.0) OVER (PARTITION BY campaign_id ORDER BY report_date)
        AS prev_day_spend,

    -- 7 rows back (week-over-week)
    LAG(roas, 7) OVER (PARTITION BY campaign_id ORDER BY report_date)
        AS roas_wow,

    -- Day-over-day absolute change
    spend_usd - LAG(spend_usd, 1, spend_usd) OVER (
        PARTITION BY campaign_id ORDER BY report_date)
        AS spend_dod,

    -- Day-over-day percentage change
    SAFE_DIVIDE(
        spend_usd - LAG(spend_usd, 1) OVER (PARTITION BY campaign_id ORDER BY report_date),
        LAG(spend_usd, 1) OVER (PARTITION BY campaign_id ORDER BY report_date)
    ) * 100 AS spend_dod_pct,

    -- Next value (look-ahead — useful for churn analysis)
    LEAD(roas, 1) OVER (PARTITION BY campaign_id ORDER BY report_date)
        AS next_day_roas,

    -- Was this the last active day? (no next row = last)
    LEAD(report_date, 1) OVER (PARTITION BY campaign_id ORDER BY report_date) IS NULL
        AS is_last_day

FROM campaign_daily_performance;
```

#### 2.1.3 Rolling Aggregates

```sql
SELECT
    report_date,
    campaign_id,
    spend_usd,
    roas,

    -- 7-day rolling average
    AVG(roas) OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS roas_7d_ma,

    -- 30-day rolling total spend
    SUM(spend_usd) OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS spend_30d_rolling,

    -- Month-to-date (all rows in same month up to current)
    SUM(spend_usd) OVER (
        PARTITION BY campaign_id, DATE_TRUNC(report_date, MONTH)
        ORDER BY report_date
        ROWS UNBOUNDED PRECEDING
    ) AS spend_mtd,

    -- Cumulative max (high watermark)
    MAX(roas) OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
        ROWS UNBOUNDED PRECEDING
    ) AS roas_all_time_high,

    -- Rolling standard deviation (volatility)
    STDDEV(roas) OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS roas_30d_volatility

FROM campaign_daily_performance;
```

#### 2.1.4 ROWS vs RANGE — The Critical Distinction

```sql
-- Table has multiple rows per date (one per campaign)
-- 
-- ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
--   = exactly 7 physical rows regardless of values
--
-- RANGE BETWEEN 6 PRECEDING AND CURRENT ROW
--   = all rows where ORDER BY value is within 6 of current row's value
--   = if ORDER BY is a date, includes all rows within 6 days

-- Example: when would they differ?
-- If report_date has duplicates (same date, different campaigns in same partition)
-- ROWS: counts duplicates as separate physical rows
-- RANGE: includes ALL rows with the same date value as the current row

-- Best practice: use ROWS for performance metrics (you want exactly N data points)
-- Use RANGE for "trailing X days" calculations
```

---

### 2.2 Recursive CTEs — Hierarchical Queries

```sql
-- Use case: traversing campaign category hierarchy
-- categories(id, name, parent_id)

WITH RECURSIVE category_tree AS (
    -- Anchor: root categories (no parent)
    SELECT
        id,
        name,
        parent_id,
        CAST(name AS STRING)    AS full_path,
        0                       AS depth
    FROM categories
    WHERE parent_id IS NULL

    UNION ALL

    -- Recursive: each level joins to its parent
    SELECT
        c.id,
        c.name,
        c.parent_id,
        CONCAT(ct.full_path, ' > ', c.name),
        ct.depth + 1
    FROM categories c
    JOIN category_tree ct ON c.parent_id = ct.id
    WHERE ct.depth < 10          -- safety: prevent infinite recursion
)

SELECT id, name, full_path, depth
FROM category_tree
ORDER BY full_path;

-- Use case 2: find all manager-report relationships in org chart
WITH RECURSIVE org_chain AS (
    SELECT employee_id, manager_id, name, 1 AS level
    FROM employees
    WHERE employee_id = :start_employee_id

    UNION ALL

    SELECT e.employee_id, e.manager_id, e.name, oc.level + 1
    FROM employees e
    JOIN org_chain oc ON e.manager_id = oc.employee_id
)
SELECT * FROM org_chain;
```

---

### 2.3 CTE Chaining — Multi-Step Transformation Pipeline

```sql
-- Full pipeline: raw clicks → daily ROAS with anomaly detection

WITH

-- Step 1: Source with basic cleaning
raw AS (
    SELECT
        click_id,
        campaign_id,
        user_id,
        DATE(clicked_at)                AS click_date,
        COALESCE(cost_micros, 0) / 1e6  AS cost_usd
    FROM `raw.ad_clicks`
    WHERE DATE(clicked_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
      AND click_id IS NOT NULL
),

-- Step 2: Deduplication
deduped AS (
    SELECT * EXCEPT (rn)
    FROM (
        SELECT *, ROW_NUMBER() OVER (
            PARTITION BY click_id ORDER BY cost_usd DESC
        ) AS rn
        FROM raw
    ) WHERE rn = 1
),

-- Step 3: Daily aggregation
daily_clicks AS (
    SELECT
        click_date,
        campaign_id,
        COUNT(*)                AS clicks,
        SUM(cost_usd)           AS spend_usd,
        COUNT(DISTINCT user_id) AS unique_users
    FROM deduped
    GROUP BY 1, 2
),

-- Step 4: Join conversions
daily_conv AS (
    SELECT
        DATE(converted_at)          AS conv_date,
        campaign_id,
        COUNT(*)                    AS conversions,
        SUM(conv_value_usd)         AS revenue_usd
    FROM `raw.conversions`
    WHERE DATE(converted_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    GROUP BY 1, 2
),

joined AS (
    SELECT
        dc.click_date                       AS report_date,
        dc.campaign_id,
        dc.clicks,
        dc.spend_usd,
        dc.unique_users,
        COALESCE(dv.conversions, 0)         AS conversions,
        COALESCE(dv.revenue_usd, 0)         AS revenue_usd
    FROM daily_clicks dc
    LEFT JOIN daily_conv dv
        ON dc.click_date = dv.conv_date
       AND dc.campaign_id = dv.campaign_id
),

-- Step 5: Derived metrics + 7-day rolling average for anomaly detection
with_metrics AS (
    SELECT
        *,
        SAFE_DIVIDE(revenue_usd, spend_usd)     AS roas,
        SAFE_DIVIDE(conversions, clicks)        AS cvr,
        AVG(SAFE_DIVIDE(revenue_usd, spend_usd)) OVER (
            PARTITION BY campaign_id
            ORDER BY report_date
            ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
        ) AS roas_7d_avg
    FROM joined
),

-- Step 6: Flag anomalies
final AS (
    SELECT
        *,
        CASE
            WHEN roas < 0.5 * roas_7d_avg THEN 'roas_drop'
            WHEN roas > 3.0 * roas_7d_avg THEN 'roas_spike'
            ELSE NULL
        END AS anomaly_flag
    FROM with_metrics
)

SELECT * FROM final
WHERE report_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
ORDER BY roas ASC;
```

---

### 2.4 Query Optimization — BigQuery Focus

#### 2.4.1 Partition Pruning

```sql
-- BAD: no partition filter — full table scan (billions of rows)
SELECT * FROM `events.ad_clicks`
WHERE campaign_id = 'C001';
-- Reads ALL partitions even though only a few have C001

-- GOOD: partition filter pushes predicate to storage layer
SELECT * FROM `events.ad_clicks`
WHERE click_date = '2024-01-15'    -- partition column filter
  AND campaign_id = 'C001';
-- Only reads the 2024-01-15 partition: 1000x less data scanned

-- BigQuery tip: always verify partition pruning with EXPLAIN
-- or check "Estimated bytes processed" before running
```

#### 2.4.2 Clustering Benefits

```sql
-- Table is clustered by (campaign_id, channel)
-- Clustering makes range scans on cluster columns extremely fast
-- BUT: only helps if you filter/sort on cluster columns in query

-- BENEFITS from clustering:
SELECT * FROM mart_campaign_performance
WHERE report_date = '2024-01-15'
  AND campaign_id IN ('C001', 'C002', 'C003');  -- cluster key filter

-- DOESN'T benefit:
SELECT * FROM mart_campaign_performance
WHERE report_date = '2024-01-15'
  AND spend_usd > 1000;  -- non-cluster column filter (full partition scan)
```

#### 2.4.3 JOIN Optimization

```sql
-- Put the LARGER table on the LEFT side of JOIN
-- BigQuery builds a hash table from the right side (probe phase)
-- Smaller right = smaller hash table = fits in memory

-- Filter before joining (reduce rows early)
WITH recent_clicks AS (
    SELECT * FROM clicks WHERE click_date >= '2024-01-01'  -- filter first
),
active_campaigns AS (
    SELECT * FROM campaigns WHERE status = 'active'         -- filter first
)
SELECT * FROM recent_clicks
JOIN active_campaigns USING (campaign_id);

-- Avoid SELECT * across joins (reads all columns from both tables)
-- Be explicit: select only needed columns
```

#### 2.4.4 Avoiding Common Performance Killers

```sql
-- KILLER 1: Functions on indexed/partition columns prevent pruning
-- BAD:
WHERE YEAR(click_date) = 2024
-- GOOD:
WHERE click_date BETWEEN '2024-01-01' AND '2024-12-31'

-- KILLER 2: Wildcard SELECT on wide tables
-- BAD: SELECT * FROM events (reads all columns — expensive in columnar DB)
-- GOOD: SELECT event_id, campaign_id, clicked_at FROM events

-- KILLER 3: Repeated subqueries (BigQuery re-executes each reference)
-- BAD:
SELECT
    (SELECT MAX(spend) FROM t) AS max_spend,
    spend / (SELECT MAX(spend) FROM t) AS pct_of_max  -- runs TWICE
FROM t
-- GOOD: use CTE to compute once
WITH max_val AS (SELECT MAX(spend) AS max_spend FROM t)
SELECT spend, spend / max_val.max_spend AS pct_of_max
FROM t CROSS JOIN max_val;

-- KILLER 4: DISTINCT on large datasets (causes full shuffle)
-- BAD: SELECT DISTINCT * FROM events
-- GOOD: identify WHY there are duplicates and fix upstream
```

---

## L3: Real-World Scenarios — Costco/MarTech Style

### 3.1 Scenario: Cohort Retention Analysis

**Business question**: Of members who made their first purchase in January 2024, what percentage returned each subsequent month?

```sql
WITH first_purchase AS (
    -- Step 1: identify each member's cohort month
    SELECT
        member_id,
        DATE_TRUNC(MIN(purchase_date), MONTH)   AS cohort_month
    FROM member_transactions
    GROUP BY member_id
),

monthly_activity AS (
    -- Step 2: all months each member was active
    SELECT DISTINCT
        member_id,
        DATE_TRUNC(purchase_date, MONTH)        AS activity_month
    FROM member_transactions
),

cohort_data AS (
    -- Step 3: join to get months_since_cohort
    SELECT
        fp.cohort_month,
        ma.activity_month,
        DATE_DIFF(ma.activity_month, fp.cohort_month, MONTH) AS month_num,
        COUNT(DISTINCT ma.member_id)            AS active_members
    FROM first_purchase fp
    JOIN monthly_activity ma USING (member_id)
    GROUP BY 1, 2, 3
),

cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM first_purchase
    GROUP BY 1
)

SELECT
    cd.cohort_month,
    cs.cohort_size,
    cd.month_num,
    cd.active_members,
    ROUND(100.0 * cd.active_members / cs.cohort_size, 1) AS retention_pct
FROM cohort_data cd
JOIN cohort_sizes cs USING (cohort_month)
WHERE cd.cohort_month = '2024-01-01'
  AND cd.month_num BETWEEN 0 AND 11
ORDER BY cd.month_num;
```

---

### 3.2 Scenario: Sessionization — Group Events into Sessions

**Business question**: Group user website events into sessions (new session = 30-minute inactivity gap), then compute session metrics.

```sql
WITH events_ordered AS (
    SELECT
        user_id,
        event_type,
        event_at,
        page_url,
        -- Time gap from previous event by same user
        TIMESTAMP_DIFF(
            event_at,
            LAG(event_at) OVER (PARTITION BY user_id ORDER BY event_at),
            MINUTE
        )                               AS gap_minutes
    FROM user_events
    WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
),

with_session_flag AS (
    SELECT
        *,
        -- New session if gap > 30 min OR first ever event
        CASE
            WHEN gap_minutes > 30 OR gap_minutes IS NULL THEN 1
            ELSE 0
        END AS is_session_start
    FROM events_ordered
),

with_session_id AS (
    SELECT
        *,
        -- Session ID = cumulative count of session starts per user
        SUM(is_session_start) OVER (
            PARTITION BY user_id
            ORDER BY event_at
            ROWS UNBOUNDED PRECEDING
        ) AS session_num
    FROM with_session_flag
),

session_summary AS (
    SELECT
        user_id,
        session_num,
        MIN(event_at)                                       AS session_start,
        MAX(event_at)                                       AS session_end,
        TIMESTAMP_DIFF(MAX(event_at), MIN(event_at), MINUTE) AS duration_min,
        COUNT(*)                                            AS event_count,
        COUNT(DISTINCT page_url)                            AS unique_pages,
        STRING_AGG(event_type ORDER BY event_at LIMIT 5)    AS first_5_events,
        MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS had_purchase,
        MAX(CASE WHEN event_type = 'add_to_cart' THEN 1 ELSE 0 END) AS had_add_to_cart
    FROM with_session_id
    GROUP BY user_id, session_num
)

SELECT * FROM session_summary
ORDER BY user_id, session_start;
```

---

### 3.3 Scenario: SCD Type 2 Query — Point-in-Time Join

**Business question**: What was the daily budget for each campaign on each day they had spend? (Budget changes over time.)

```sql
-- scd_campaigns has: campaign_id, daily_budget_usd, valid_from, valid_to (NULL = current)

SELECT
    p.report_date,
    p.campaign_id,
    p.spend_usd,
    -- Get the budget that was active on that date
    scd.daily_budget_usd,
    SAFE_DIVIDE(p.spend_usd, scd.daily_budget_usd)  AS budget_utilization
FROM campaign_daily_performance p
LEFT JOIN scd_campaigns scd
    ON  p.campaign_id = scd.campaign_id
    AND p.report_date BETWEEN scd.valid_from AND COALESCE(scd.valid_to, '9999-12-31')
ORDER BY p.report_date, p.campaign_id;
```

---

### 3.4 Scenario: Finding Consecutive Active Days (Islands Problem)

**Business question**: Find the longest streak of consecutive days each campaign was active.

```sql
WITH active_days AS (
    SELECT DISTINCT
        campaign_id,
        report_date
    FROM campaign_daily_performance
    WHERE spend_usd > 0
),

numbered AS (
    SELECT
        campaign_id,
        report_date,
        ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY report_date) AS rn
    FROM active_days
),

-- Key insight: for consecutive dates, (date - row_number) is constant
islands AS (
    SELECT
        campaign_id,
        report_date,
        DATE_SUB(report_date, INTERVAL rn DAY)  AS island_key
    FROM numbered
),

streaks AS (
    SELECT
        campaign_id,
        island_key,
        MIN(report_date)    AS streak_start,
        MAX(report_date)    AS streak_end,
        COUNT(*)            AS streak_length_days
    FROM islands
    GROUP BY campaign_id, island_key
)

SELECT
    campaign_id,
    streak_start,
    streak_end,
    streak_length_days,
    -- Rank streaks within each campaign
    RANK() OVER (
        PARTITION BY campaign_id ORDER BY streak_length_days DESC
    ) AS streak_rank
FROM streaks
ORDER BY streak_length_days DESC;
```

---

## L4: Hands-On Coding

### 4.1 Write a Query From Scratch: Top N Per Group

**Problem**: For each channel, return the top 3 campaigns by ROAS for the last 30 days.

```sql
-- Method 1: ROW_NUMBER (most reliable — guaranteed N rows per group)
SELECT * FROM (
    SELECT
        channel,
        campaign_id,
        campaign_name,
        ROUND(AVG(roas), 4)         AS avg_roas,
        SUM(spend_usd)              AS total_spend,
        ROW_NUMBER() OVER (
            PARTITION BY channel
            ORDER BY AVG(roas) DESC
        )                           AS rn
    FROM campaign_daily_performance
    WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY channel, campaign_id, campaign_name
)
WHERE rn <= 3
ORDER BY channel, rn;

-- Method 2: QUALIFY (BigQuery shorthand)
SELECT
    channel,
    campaign_id,
    AVG(roas) AS avg_roas
FROM campaign_daily_performance
WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY channel, campaign_id
QUALIFY ROW_NUMBER() OVER (PARTITION BY channel ORDER BY AVG(roas) DESC) <= 3;
```

---

### 4.2 Write a Query: Running Balance with Reset

**Problem**: Track cumulative spend per campaign per month. Reset to 0 each new month.

```sql
SELECT
    report_date,
    campaign_id,
    spend_usd,
    DATE_TRUNC(report_date, MONTH)                          AS month,
    SUM(spend_usd) OVER (
        PARTITION BY campaign_id, DATE_TRUNC(report_date, MONTH)
        ORDER BY report_date
        ROWS UNBOUNDED PRECEDING
    )                                                       AS spend_mtd,
    SUM(daily_budget_usd) OVER (
        PARTITION BY campaign_id, DATE_TRUNC(report_date, MONTH)
    )                                                       AS monthly_budget,
    SAFE_DIVIDE(
        SUM(spend_usd) OVER (
            PARTITION BY campaign_id, DATE_TRUNC(report_date, MONTH)
            ORDER BY report_date ROWS UNBOUNDED PRECEDING
        ),
        SUM(daily_budget_usd) OVER (
            PARTITION BY campaign_id, DATE_TRUNC(report_date, MONTH)
        )
    ) * 100                                                 AS pct_budget_used
FROM campaign_daily_performance
ORDER BY campaign_id, report_date;
```

---

### 4.3 Write a Query: Detect Data Gaps in a Time Series

**Problem**: Find dates where a campaign had impressions but no click data recorded (data pipeline gap).

```sql
-- Generate expected dates × campaigns
WITH date_spine AS (
    SELECT date_day
    FROM UNNEST(GENERATE_DATE_ARRAY(
        DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY),
        CURRENT_DATE(),
        INTERVAL 1 DAY
    )) AS date_day
),

active_campaigns AS (
    SELECT DISTINCT campaign_id FROM impressions
    WHERE served_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
),

expected AS (
    SELECT d.date_day, ac.campaign_id
    FROM date_spine d
    CROSS JOIN active_campaigns ac
),

actual_clicks AS (
    SELECT DISTINCT click_date, campaign_id FROM clicks
),

gaps AS (
    SELECT
        e.date_day,
        e.campaign_id,
        CASE WHEN ac.click_date IS NULL THEN 'MISSING' ELSE 'OK' END AS status
    FROM expected e
    LEFT JOIN actual_clicks ac
        ON e.date_day = ac.click_date
       AND e.campaign_id = ac.campaign_id
)

SELECT * FROM gaps WHERE status = 'MISSING'
ORDER BY campaign_id, date_day;
```

---

### 4.4 Write a Query: Median and Percentiles Without PERCENTILE_CONT

**Problem**: Compute the median CPC per campaign using only basic SQL (no percentile functions).

```sql
WITH ordered AS (
    SELECT
        campaign_id,
        cost_usd,
        ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY cost_usd) AS rn,
        COUNT(*) OVER (PARTITION BY campaign_id)                       AS cnt
    FROM ad_clicks
    WHERE click_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
)

SELECT
    campaign_id,
    AVG(cost_usd) AS median_cpc  -- average of middle 1 or 2 values
FROM ordered
WHERE
    rn IN (FLOOR((cnt + 1) / 2.0), CEIL((cnt + 1) / 2.0))
    -- For odd count: picks middle row
    -- For even count: picks two middle rows, AVG gives median
GROUP BY campaign_id;
```

---

## L5: Edge Cases & Pitfalls

### 5.1 The NULL Trap in NOT IN

```sql
-- DANGEROUS: NOT IN with subquery that can return NULLs
SELECT campaign_id FROM campaigns
WHERE campaign_id NOT IN (
    SELECT campaign_id FROM blacklist  -- What if this has NULLs?
);

-- If blacklist.campaign_id has any NULLs:
-- campaign_id NOT IN (1, 2, NULL)
-- = campaign_id != 1 AND campaign_id != 2 AND campaign_id != NULL
-- = campaign_id != 1 AND campaign_id != 2 AND NULL
-- = NULL (the whole expression is NULL → row is excluded!)
-- RESULT: returns ZERO ROWS even for campaigns not in the blacklist

-- SAFE: use NOT EXISTS (handles NULLs correctly)
SELECT campaign_id FROM campaigns c
WHERE NOT EXISTS (
    SELECT 1 FROM blacklist b WHERE b.campaign_id = c.campaign_id
);

-- OR: filter NULLs explicitly
WHERE campaign_id NOT IN (
    SELECT campaign_id FROM blacklist WHERE campaign_id IS NOT NULL
);
```

---

### 5.2 Join Fan-Out (Multiplication of Rows)

```sql
-- Problem: joining two tables where the join key is not unique in BOTH tables
-- clicks: 1M rows, one per click_id (unique)
-- campaign_tags: multiple rows per campaign_id (one per tag)

-- BAD: this MULTIPLIES rows — 1M clicks × 5 tags per campaign = 5M rows
SELECT c.*, t.tag
FROM clicks c
JOIN campaign_tags t ON c.campaign_id = t.campaign_id;

-- Check before joining:
SELECT campaign_id, COUNT(*) AS cnt
FROM campaign_tags
GROUP BY campaign_id
HAVING COUNT(*) > 1;
-- If this returns rows, the join will fan out!

-- FIX option 1: aggregate tags first
WITH tags_agg AS (
    SELECT campaign_id, STRING_AGG(tag ORDER BY tag) AS all_tags
    FROM campaign_tags
    GROUP BY campaign_id
)
SELECT c.*, t.all_tags
FROM clicks c
LEFT JOIN tags_agg t ON c.campaign_id = t.campaign_id;

-- FIX option 2: use ARRAY join (BigQuery)
WITH tags_arr AS (
    SELECT campaign_id, ARRAY_AGG(tag ORDER BY tag) AS tags
    FROM campaign_tags
    GROUP BY campaign_id
)
SELECT c.*, t.tags
FROM clicks c
LEFT JOIN tags_arr t ON c.campaign_id = t.campaign_id;
```

---

### 5.3 Window Function vs GROUP BY — The "Why Did I Get More Rows?" Bug

```sql
-- Mistake: using window function expecting GROUP BY behavior
-- Goal: get total spend per campaign alongside per-day spend

-- WRONG expectation: expects one row per campaign
SELECT DISTINCT
    campaign_id,
    SUM(spend_usd) OVER (PARTITION BY campaign_id) AS total_spend
FROM daily_performance;
-- This still returns one row PER DAY per campaign (window doesn't collapse rows)
-- DISTINCT then de-dupes, but you've done unnecessary work

-- CORRECT if you want one row per campaign:
SELECT campaign_id, SUM(spend_usd) AS total_spend
FROM daily_performance
GROUP BY campaign_id;

-- CORRECT if you want both daily and total on same row:
SELECT
    report_date,
    campaign_id,
    spend_usd,
    SUM(spend_usd) OVER (PARTITION BY campaign_id) AS campaign_total_spend,
    SAFE_DIVIDE(spend_usd,
        SUM(spend_usd) OVER (PARTITION BY campaign_id)
    ) AS pct_of_campaign_total
FROM daily_performance;
-- window function keeps all rows; adds context without collapsing
```

---

### 5.4 Incorrect Partition in Window Function

```sql
-- Goal: running total of spend for each campaign, RESET each month
-- WRONG: no month in partition → cumulative across ALL months
SELECT
    report_date,
    campaign_id,
    SUM(spend_usd) OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
        ROWS UNBOUNDED PRECEDING
    ) AS cumulative_spend  -- never resets for new month

-- CORRECT: include month in partition to reset monthly
SELECT
    report_date,
    campaign_id,
    SUM(spend_usd) OVER (
        PARTITION BY campaign_id, DATE_TRUNC(report_date, MONTH)  -- reset per month
        ORDER BY report_date
        ROWS UNBOUNDED PRECEDING
    ) AS spend_mtd
```

---

### 5.5 DISTINCT vs GROUP BY Performance

```sql
-- DISTINCT forces a full deduplication shuffle
-- For simple deduplications, GROUP BY with aggregation is equivalent and often faster

-- DISTINCT: reads everything, sorts/hashes all columns, drops duplicates
SELECT DISTINCT campaign_id, channel FROM daily_performance;

-- GROUP BY: can use partial aggregation optimizations
SELECT campaign_id, channel FROM daily_performance GROUP BY 1, 2;
-- In practice: same output, similar performance for simple cases
-- GROUP BY wins when you need ANY aggregation alongside

-- For complex deduplication (keep specific row):
-- ALWAYS use ROW_NUMBER() approach — DISTINCT doesn't let you choose WHICH row to keep
```

---

## L6: Interview Questions — Easy to Very Hard

### EASY

---

**Q1: What is the difference between WHERE and HAVING?**

**What they're testing**: Execution order understanding, fundamentals.

**Answer**: WHERE filters rows BEFORE GROUP BY executes — it operates on individual row values, not aggregates. HAVING filters AFTER GROUP BY — it operates on aggregate results. You cannot use aggregate functions in WHERE (they don't exist yet at that execution step). You cannot use non-aggregated, non-grouped columns in HAVING.

```sql
-- WHERE: row-level filter before aggregation
SELECT campaign_id, SUM(spend_usd) AS total
FROM clicks
WHERE status = 'valid'          -- row-level: fine
GROUP BY campaign_id
HAVING SUM(spend_usd) > 1000;   -- aggregate-level: fine

-- Common mistake:
HAVING status = 'valid'         -- WRONG: status is not aggregated/grouped
WHERE SUM(spend_usd) > 1000     -- WRONG: aggregate not available at WHERE step
```

---

**Q2: What is a LEFT JOIN vs INNER JOIN? When would you use each?**

**Answer**: INNER JOIN returns only rows where the join condition is TRUE in BOTH tables — non-matching rows are dropped. LEFT JOIN returns ALL rows from the left table; for rows with no match in the right table, right-side columns are NULL.

Use INNER JOIN when you only care about rows that have matches in both tables (e.g., campaigns with at least one click). Use LEFT JOIN when you want ALL left-side rows regardless of whether there's a match — e.g., campaigns including those with zero clicks (you want to see zero-performance campaigns, not just drop them).

Senior nuance: In analytical pipelines, LEFT JOINs are almost always preferred over INNER JOINs because dropping rows silently is dangerous — you lose campaigns from your report without knowing it. Be explicit about the join type and verify row counts before and after.

---

### MEDIUM

---

**Q3: Write a query to find the second highest salary per department.**

**What they're testing**: Window functions, ranking, filtering.

```sql
-- Method 1: DENSE_RANK (handles ties correctly)
SELECT department, employee_id, salary
FROM (
    SELECT
        department,
        employee_id,
        salary,
        DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS dr
    FROM employees
)
WHERE dr = 2;

-- Method 2: ROW_NUMBER (arbitrary tiebreaker — picks one if tied)
SELECT department, employee_id, salary
FROM (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS rn
    FROM employees
)
WHERE rn = 2;

-- Why DENSE_RANK vs ROW_NUMBER matters:
-- Salaries: 100K, 100K, 80K
-- ROW_NUMBER: 1, 2, 3 → second = 100K (second person tied for first)
-- DENSE_RANK: 1, 1, 2 → second = 80K (second DISTINCT salary)
-- The business question determines which is right.
```

**Follow-up trap**: "What if there are ties for second place and I want ALL employees with the second-highest salary?" → Use DENSE_RANK.

---

**Q4: You have a table of ad impressions and a table of clicks. Write a query to compute CTR per campaign, including campaigns with zero clicks.**

```sql
WITH impressions AS (
    SELECT campaign_id, COUNT(*) AS impressions
    FROM ad_impressions
    WHERE served_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    GROUP BY campaign_id
),

clicks AS (
    SELECT campaign_id, COUNT(*) AS clicks
    FROM ad_clicks
    WHERE click_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    GROUP BY campaign_id
)

SELECT
    i.campaign_id,
    i.impressions,
    COALESCE(c.clicks, 0)               AS clicks,
    SAFE_DIVIDE(
        COALESCE(c.clicks, 0),
        i.impressions
    ) * 100                             AS ctr_pct
FROM impressions i
LEFT JOIN clicks c USING (campaign_id)   -- LEFT to keep campaigns with 0 clicks
ORDER BY ctr_pct DESC;
```

**What they're testing**: LEFT JOIN understanding, COALESCE, SAFE_DIVIDE.

---

### HARD

---

**Q5: Given a table of login events, find users who logged in on 3 or more consecutive days.**

**What they're testing**: Islands problem, window functions, self-awareness of SQL date arithmetic.

```sql
WITH login_days AS (
    -- Deduplicate: one row per user per day
    SELECT DISTINCT user_id, DATE(login_at) AS login_date
    FROM user_logins
),

numbered AS (
    SELECT
        user_id,
        login_date,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS rn
    FROM login_days
),

islands AS (
    SELECT
        user_id,
        login_date,
        DATE_SUB(login_date, INTERVAL rn DAY) AS island_key  -- constant for consecutive
    FROM numbered
),

streaks AS (
    SELECT
        user_id,
        island_key,
        MIN(login_date)     AS streak_start,
        MAX(login_date)     AS streak_end,
        COUNT(*)            AS streak_days
    FROM islands
    GROUP BY user_id, island_key
)

SELECT DISTINCT user_id
FROM streaks
WHERE streak_days >= 3;

-- With full streak info:
SELECT user_id, streak_start, streak_end, streak_days
FROM streaks
WHERE streak_days >= 3
ORDER BY streak_days DESC;
```

**What the interviewer is really testing**: Can you solve a classic "gaps and islands" problem? Do you know the `date - row_number = constant for consecutive dates` trick? Can you explain WHY that works?

**Why it works**: If dates are consecutive (day 1, day 2, day 3), and row numbers are sequential (1, 2, 3), then date - rn = day 0 for all three. Any gap in dates breaks the consecutive sequence and produces a different constant.

---

**Q6: You have an events table with 10 billion rows partitioned by date. The following query takes 4 minutes. How would you optimize it?**

```sql
-- SLOW QUERY:
SELECT
    user_id,
    COUNT(*) AS event_count,
    SUM(revenue) AS total_revenue
FROM events
WHERE EXTRACT(YEAR FROM event_date) = 2024
  AND event_type IN ('purchase', 'add_to_cart')
GROUP BY user_id;
```

**What they're testing**: Query optimization, understanding of partition pruning, function on partition columns.

**Answer**:

**Problem 1**: `EXTRACT(YEAR FROM event_date) = 2024` applies a function to the partition column. BigQuery cannot prune partitions because it must evaluate the function for every row. The query scans all 10 billion rows.

**Fix**: Replace with range filter on the partition column directly:
```sql
WHERE event_date BETWEEN '2024-01-01' AND '2024-12-31'
```

**Problem 2**: `event_type IN (...)` is a non-cluster column filter — if `event_type` is a cluster column, it helps. If not, it's a full scan within each partition.

**Problem 3**: Aggregation over user_id on 10B rows creates a massive shuffle (GROUP BY is a wide transformation).

**Additional fixes**:
- Ensure `event_date` is the partition column (it is, based on description)
- Consider whether a pre-aggregated table already exists (e.g., `events_daily_agg` materialized)
- If running repeatedly, materialize as a table in BigQuery
- Add `event_type` to the clustering key if it's frequently filtered

**Optimized query**:
```sql
SELECT
    user_id,
    COUNT(*) AS event_count,
    SUM(revenue) AS total_revenue
FROM events
WHERE event_date BETWEEN '2024-01-01' AND '2024-12-31'  -- partition pruning
  AND event_type IN ('purchase', 'add_to_cart')
GROUP BY user_id;
```

---

### VERY HARD

---

**Q7: You have a table of ad spend and a table of revenue. Both have campaign_id and date. Design a query that computes the 7-day rolling ROAS for each campaign, but fills in days with no data using the previous day's value (forward-fill). Handle campaigns that might start mid-period.**

**What they're testing**: Date spine generation, forward-fill with LAST_VALUE, complex window logic.

```sql
WITH date_spine AS (
    SELECT date_day
    FROM UNNEST(GENERATE_DATE_ARRAY(
        DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY),
        CURRENT_DATE(),
        INTERVAL 1 DAY
    )) AS date_day
),

all_campaigns AS (
    SELECT DISTINCT campaign_id,
           MIN(report_date) OVER (PARTITION BY campaign_id) AS first_active_date
    FROM campaign_daily_performance
),

-- Cross join to get full grid of campaign × date (only from their first active date)
full_grid AS (
    SELECT
        d.date_day,
        c.campaign_id
    FROM date_spine d
    CROSS JOIN all_campaigns c
    WHERE d.date_day >= c.first_active_date
),

-- Left join actual data onto the full grid
with_gaps AS (
    SELECT
        fg.date_day,
        fg.campaign_id,
        p.spend_usd,
        p.revenue_usd
    FROM full_grid fg
    LEFT JOIN campaign_daily_performance p
        ON fg.date_day = p.report_date
       AND fg.campaign_id = p.campaign_id
),

-- Forward-fill: use LAST_VALUE ignoring NULLs
forward_filled AS (
    SELECT
        date_day,
        campaign_id,
        -- Fill spend: last non-null value going forward
        LAST_VALUE(spend_usd IGNORE NULLS) OVER (
            PARTITION BY campaign_id
            ORDER BY date_day
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS spend_usd_filled,
        LAST_VALUE(revenue_usd IGNORE NULLS) OVER (
            PARTITION BY campaign_id
            ORDER BY date_day
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS revenue_usd_filled,
        -- Track whether day had actual data
        CASE WHEN spend_usd IS NOT NULL THEN 1 ELSE 0 END AS has_actual_data
    FROM with_gaps
),

-- Compute 7-day rolling ROAS
with_rolling AS (
    SELECT
        date_day,
        campaign_id,
        spend_usd_filled,
        revenue_usd_filled,
        has_actual_data,
        -- 7-day rolling ROAS
        SAFE_DIVIDE(
            SUM(revenue_usd_filled) OVER (
                PARTITION BY campaign_id
                ORDER BY date_day
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ),
            SUM(spend_usd_filled) OVER (
                PARTITION BY campaign_id
                ORDER BY date_day
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            )
        ) AS roas_7d_rolling
    FROM forward_filled
)

SELECT * FROM with_rolling
ORDER BY campaign_id, date_day;
```

**What the interviewer is really testing**: 
- Do you know how to generate a date spine?
- Do you know CROSS JOIN for creating a complete grid?
- Do you know `LAST_VALUE(col IGNORE NULLS)` for forward-fill?
- Can you compose multiple CTEs with different responsibilities?

---

**Q8: You have a transactions table with user_id, amount, and transaction_date. Write a query to find users whose spending in the current month is tracking to exceed their average monthly spend from the past 6 months, assuming today is the 10th of the month.**

**What they're testing**: Proportional projection, window functions for historical average, date arithmetic.

```sql
WITH monthly_spend AS (
    SELECT
        user_id,
        DATE_TRUNC(transaction_date, MONTH)     AS month,
        SUM(amount)                             AS monthly_total
    FROM transactions
    WHERE transaction_date >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 7 MONTH)
    GROUP BY 1, 2
),

historical_avg AS (
    -- Average over the 6 months BEFORE the current month
    SELECT
        user_id,
        AVG(monthly_total)  AS avg_monthly_spend
    FROM monthly_spend
    WHERE month < DATE_TRUNC(CURRENT_DATE(), MONTH)
    GROUP BY user_id
),

current_month AS (
    SELECT
        user_id,
        SUM(amount)                             AS spend_so_far,
        -- Days elapsed in current month (assuming today = day 10)
        EXTRACT(DAY FROM CURRENT_DATE())        AS days_elapsed,
        -- Days in current month
        EXTRACT(DAY FROM LAST_DAY(CURRENT_DATE())) AS days_in_month,
        -- Projected full-month spend (linear extrapolation)
        SUM(amount) * EXTRACT(DAY FROM LAST_DAY(CURRENT_DATE()))
            / EXTRACT(DAY FROM CURRENT_DATE())  AS projected_monthly_spend
    FROM transactions
    WHERE transaction_date >= DATE_TRUNC(CURRENT_DATE(), MONTH)
    GROUP BY user_id
)

SELECT
    cm.user_id,
    cm.spend_so_far,
    cm.projected_monthly_spend,
    ha.avg_monthly_spend,
    ROUND(cm.projected_monthly_spend / ha.avg_monthly_spend * 100, 1) AS pct_of_avg,
    cm.projected_monthly_spend > ha.avg_monthly_spend  AS is_tracking_to_exceed
FROM current_month cm
JOIN historical_avg ha USING (user_id)
WHERE cm.projected_monthly_spend > ha.avg_monthly_spend
ORDER BY pct_of_avg DESC;
```

---

**Q9: Explain how you would debug a query that returns different results every time it runs on the same data. What are the possible causes?**

**What they're testing**: SQL determinism, understanding of non-deterministic functions and behaviors.

**Answer**:

**Possible causes**:

1. **Non-deterministic functions**: `RAND()`, `UUID()`, `CURRENT_TIMESTAMP()` return different values each run. If used in CASE or WHERE, results differ.

2. **ROW_NUMBER with ties**: `ROW_NUMBER() OVER (ORDER BY col)` — if `col` has duplicates, which row gets rank 1 is non-deterministic. Deterministic only if ORDER BY uniquely identifies each row.

3. **LIMIT without ORDER BY**: `SELECT * FROM t LIMIT 10` — the 10 rows returned are not guaranteed to be the same each time.

4. **Floating-point rounding**: Aggregations on FLOAT64 can have rounding differences depending on scan order (parallel execution may aggregate in different orders).

5. **Concurrent data changes**: If the underlying table is being written to during query execution (e.g., append-only streaming table), results differ between runs.

6. **Non-deterministic string functions**: Some regex or string functions with ambiguous matching.

**Fix**: Ensure ORDER BY has a unique tiebreaker (add primary key as last sort column), avoid non-deterministic functions in deduplication logic, use TIMESTAMP_TRUNC instead of CURRENT_TIMESTAMP for partitioning.

---

**Q10 (System/Architecture): You're asked to build a daily SQL-based transformation pipeline for a 500GB table that joins 4 other tables and computes 20 different metrics. Currently it runs as one massive query taking 2 hours. How do you redesign it?**

**What they're testing**: Pipeline design thinking, incremental processing, materialization strategy.

**Answer**:

**Step 1: Break into layers**
- Layer 1 (staging): clean and deduplicate each source table independently. Materialize each as a temp table or BigQuery table. Now each has a defined row count you can validate.
- Layer 2 (intermediate): do the expensive joins once. Materialize the joined dataset as a physical table. This is the "spine" all 20 metrics build from.
- Layer 3 (mart): compute the 20 metrics FROM the materialized intermediate. These are now fast SELECTs on an already-joined table.

**Step 2: Make it incremental**
- Instead of processing 500GB every day, process only yesterday's data (filter by partition date), MERGE or INSERT OVERWRITE into the existing tables.
- Result: daily processing drops from 500GB → ~2GB (one day's data).

**Step 3: Parallelize independent paths**
- If 5 of the 20 metrics depend on different source tables, compute those in parallel (separate Airflow tasks or BigQuery jobs running concurrently).

**Step 4: Validate each layer**
- Add row count checks after each materialization. If intermediate table has fewer rows than expected, fail before computing metrics.

**Result**: 2-hour monolith → 15-minute incremental pipeline with clear failure points.

---

## Summary: Advanced SQL — Senior Mastery Checklist

| Skill | What Senior Looks Like |
|-------|------------------------|
| Execution order | Can explain why `WHERE alias` fails without hesitation |
| Joins | Knows fan-out risk; always checks cardinality before joining |
| Window functions | Writes sessionization, islands, forward-fill from memory |
| Rolling aggregates | Understands ROWS vs RANGE distinction |
| Recursive CTEs | Can traverse org charts and category hierarchies |
| Query optimization | Partition pruning, avoiding functions on partition columns |
| NULL traps | Knows NOT IN / NULL interaction; uses NOT EXISTS instead |
| Top N per group | ROW_NUMBER + filter; knows QUALIFY shorthand |
| Date spine | GENERATE_DATE_ARRAY + CROSS JOIN for complete grids |
| Debugging | Can diagnose non-determinism, fan-out, missing rows systematically |
