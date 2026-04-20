# Advanced SQL Practice — Window Functions, Aggregations & Optimization
## Costco Sr. Data Engineer Interview Prep

---

## PART 1: WINDOW FUNCTIONS — Deep Practice

---

### W1. All ranking functions side by side — understand differences

```sql
-- Dataset: campaigns ranked by ROAS
-- Assume ROAS values: 5.0, 4.0, 4.0, 3.0, 2.0

SELECT
    campaign_id,
    roas,
    ROW_NUMBER() OVER (ORDER BY roas DESC)  AS row_num,
    -- Result: 1, 2, 3, 4, 5 (always unique — arbitrary tiebreak for tied ROASes)

    RANK() OVER (ORDER BY roas DESC)        AS rnk,
    -- Result: 1, 2, 2, 4, 5 (tied 4.0 = both rank 2, next is 4 not 3)

    DENSE_RANK() OVER (ORDER BY roas DESC)  AS dense_rnk,
    -- Result: 1, 2, 2, 3, 4 (tied 4.0 = both rank 2, next is 3 — no gaps)

    PERCENT_RANK() OVER (ORDER BY roas DESC) AS pct_rank,
    -- Result: 0.0, 0.25, 0.25, 0.75, 1.0 → (rank-1)/(n-1)

    CUME_DIST() OVER (ORDER BY roas DESC)   AS cume_dist,
    -- Result: 0.2, 0.6, 0.6, 0.8, 1.0 → fraction of rows <= current

    NTILE(4) OVER (ORDER BY roas DESC)      AS quartile
    -- Divides into 4 equal buckets: Q1=top 25%, Q4=bottom 25%

FROM (
    SELECT 'C001' AS campaign_id, 5.0 AS roas UNION ALL
    SELECT 'C002', 4.0 UNION ALL
    SELECT 'C003', 4.0 UNION ALL
    SELECT 'C004', 3.0 UNION ALL
    SELECT 'C005', 2.0
);

-- INTERVIEW QUESTION: "When would you use DENSE_RANK vs ROW_NUMBER?"
-- Use DENSE_RANK when ties are semantically meaningful:
--   "Show the second-highest ROAS campaign" → DENSE_RANK = 2 gives all tied campaigns
--   "Pick one row to deduplicate" → ROW_NUMBER = arbitrary but unique
```

---

### W2. ROWS vs RANGE — critical distinction

```sql
-- Table has multiple rows per date (one per campaign)

SELECT
    report_date,
    campaign_id,
    spend_usd,

    -- ROWS: exactly 3 physical rows before current row
    SUM(spend_usd) OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
        ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
    ) AS spend_rows_3_preceding,

    -- RANGE: all rows where report_date is within 3 days of current row's date
    -- (includes ALL rows on same date as current row)
    SUM(spend_usd) OVER (
        PARTITION BY campaign_id
        ORDER BY UNIX_DATE(report_date)  -- must use numeric for RANGE arithmetic
        RANGE BETWEEN 3 PRECEDING AND CURRENT ROW
    ) AS spend_range_3_days

FROM campaign_daily
WHERE report_date >= '2024-01-01'
ORDER BY campaign_id, report_date;

-- KEY INSIGHT:
-- Use ROWS when you want exactly N data points in the window
-- Use RANGE when you want "all data within N units of value"
-- For date windows, RANGE is more semantically correct ("last 7 calendar days")
-- but ROWS is more commonly used and avoids edge cases with ties
```

---

### W3. Lead/Lag — multi-period comparison

```sql
SELECT
    report_date,
    campaign_id,
    spend_usd,
    roas,

    -- Prior day
    LAG(spend_usd, 1, 0.0) OVER (PARTITION BY campaign_id ORDER BY report_date)
        AS spend_d_minus_1,

    -- Same day last week
    LAG(roas, 7) OVER (PARTITION BY campaign_id ORDER BY report_date)
        AS roas_d_minus_7,

    -- Same day last month (approximately 30 lags)
    LAG(roas, 30) OVER (PARTITION BY campaign_id ORDER BY report_date)
        AS roas_d_minus_30,

    -- Next day (look-ahead — useful for "last active day" detection)
    LEAD(spend_usd, 1) OVER (PARTITION BY campaign_id ORDER BY report_date)
        AS next_day_spend,

    -- Flag: is today the last day this campaign ran?
    LEAD(report_date, 1) OVER (PARTITION BY campaign_id ORDER BY report_date) IS NULL
        AS is_last_day,

    -- Day-over-day change
    spend_usd - LAG(spend_usd, 1, spend_usd) OVER (
        PARTITION BY campaign_id ORDER BY report_date
    ) AS spend_dod_delta,

    -- Rolling 7-day average (exclude today to avoid "today influences today")
    AVG(roas) OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
        ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
    ) AS roas_7d_trailing_avg

FROM campaign_daily
ORDER BY campaign_id, report_date;
```

---

### W4. NTH_VALUE — get the 3rd highest value

```sql
SELECT DISTINCT
    channel,
    -- 1st highest ROAS in channel
    FIRST_VALUE(roas) OVER (PARTITION BY channel ORDER BY roas DESC) AS highest_roas,

    -- 3rd highest ROAS in channel
    NTH_VALUE(roas, 3) OVER (
        PARTITION BY channel
        ORDER BY roas DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        -- MUST include full frame for NTH_VALUE to see all rows
    ) AS third_highest_roas,

    -- Last (lowest) ROAS in channel
    LAST_VALUE(roas) OVER (
        PARTITION BY channel
        ORDER BY roas DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS lowest_roas

FROM campaign_daily
WHERE report_date = CURRENT_DATE() - 1;

-- GOTCHA: NTH_VALUE and LAST_VALUE require explicit full frame
-- Default frame is ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
-- This means LAST_VALUE by default gives the current row, not the last row in partition
```

---

### W5. Percent of total and cumulative percent

```sql
SELECT
    channel,
    SUM(spend_usd)          AS channel_spend,

    -- Percent of total spend across all channels
    ROUND(100.0 * SUM(spend_usd) / SUM(SUM(spend_usd)) OVER (), 2)
        AS pct_of_total,

    -- Cumulative percent (from highest to lowest spend)
    ROUND(100.0 * SUM(SUM(spend_usd)) OVER (
        ORDER BY SUM(spend_usd) DESC
        ROWS UNBOUNDED PRECEDING
    ) / SUM(SUM(spend_usd)) OVER (), 2)
        AS cumulative_pct,

    -- Rank by spend
    RANK() OVER (ORDER BY SUM(spend_usd) DESC) AS spend_rank

FROM campaign_daily
WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY channel
ORDER BY channel_spend DESC;

-- Note: SUM(SUM(spend_usd)) OVER () — outer window function over inner aggregate
-- This is valid: first GROUP BY computes SUM per channel, then OVER() sums all channels
```

---

## PART 2: COMPLEX AGGREGATIONS

---

### A1. GROUPING SETS — multi-level rollup in one query

```sql
-- Goal: spend by (date, channel), by (date), by (channel), and grand total
-- Without GROUPING SETS: 4 separate queries + UNION ALL
-- With GROUPING SETS: one scan of the table

SELECT
    report_date,
    channel,
    SUM(spend_usd)  AS spend,
    SUM(clicks)     AS clicks,
    GROUPING(report_date)   AS is_date_rolled_up,    -- 1 when date is aggregated away
    GROUPING(channel)       AS is_channel_rolled_up, -- 1 when channel is aggregated away
    CASE
        WHEN GROUPING(report_date) = 0 AND GROUPING(channel) = 0 THEN 'date_channel'
        WHEN GROUPING(report_date) = 0 AND GROUPING(channel) = 1 THEN 'date_only'
        WHEN GROUPING(report_date) = 1 AND GROUPING(channel) = 0 THEN 'channel_only'
        ELSE 'grand_total'
    END AS aggregation_level
FROM campaign_daily
WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY GROUPING SETS (
    (report_date, channel),  -- detailed: daily per channel
    (report_date),           -- daily total
    (channel),               -- channel total over period
    ()                       -- grand total
)
ORDER BY
    GROUPING(report_date), GROUPING(channel), report_date, channel;
```

---

### A2. ROLLUP vs CUBE — when to use each

```sql
-- ROLLUP: hierarchical, rolls up from right to left
-- Given ROLLUP(year, month, day): generates (y,m,d), (y,m), (y), ()

SELECT
    EXTRACT(YEAR FROM report_date)  AS year,
    EXTRACT(MONTH FROM report_date) AS month,
    EXTRACT(DAY FROM report_date)   AS day,
    SUM(spend_usd)                  AS spend,
    -- Identify the aggregation level
    CASE
        WHEN GROUPING(EXTRACT(DAY FROM report_date)) = 1
         AND GROUPING(EXTRACT(MONTH FROM report_date)) = 1 THEN 'yearly'
        WHEN GROUPING(EXTRACT(DAY FROM report_date)) = 1 THEN 'monthly'
        WHEN GROUPING(EXTRACT(YEAR FROM report_date)) = 0 THEN 'daily'
    END AS level
FROM campaign_daily
GROUP BY ROLLUP(
    EXTRACT(YEAR FROM report_date),
    EXTRACT(MONTH FROM report_date),
    EXTRACT(DAY FROM report_date)
)
ORDER BY year NULLS LAST, month NULLS LAST, day NULLS LAST;

-- CUBE: all combinations
-- Given CUBE(channel, device, region):
-- Generates all 8 combinations: (c,d,r), (c,d), (c,r), (d,r), (c), (d), (r), ()
-- Use for cross-sectional analysis where ALL combinations matter

SELECT
    COALESCE(channel, 'ALL')    AS channel,
    COALESCE(device, 'ALL')     AS device,
    SUM(spend_usd)              AS spend
FROM campaign_daily
GROUP BY CUBE(channel, device)
ORDER BY channel, device;
```

---

### A3. STRING_AGG and ARRAY_AGG — collect values into lists

```sql
-- Collect all keywords per campaign as a comma-separated string
SELECT
    campaign_id,
    STRING_AGG(keyword ORDER BY keyword)                    AS all_keywords,
    STRING_AGG(DISTINCT keyword ORDER BY keyword)           AS unique_keywords,
    STRING_AGG(keyword, ' | ' ORDER BY clicks DESC LIMIT 5) AS top_5_keywords,
    COUNT(DISTINCT keyword)                                 AS keyword_count,
    ARRAY_AGG(STRUCT(keyword, clicks, spend_usd)
              ORDER BY spend_usd DESC LIMIT 10)             AS top_10_keywords_struct
FROM keyword_performance
WHERE report_date = CURRENT_DATE() - 1
GROUP BY campaign_id;

-- Reconstruct from array: UNNEST
SELECT campaign_id, kw.keyword, kw.clicks, kw.spend_usd
FROM (
    SELECT campaign_id, ARRAY_AGG(STRUCT(keyword, clicks, spend_usd)
                                  ORDER BY spend_usd DESC LIMIT 10) AS keywords
    FROM keyword_performance
    GROUP BY campaign_id
) t,
UNNEST(t.keywords) AS kw;
```

---

### A4. Approximate aggregations for large datasets

```sql
-- For 10B rows: exact COUNT(DISTINCT) is slow → use approximate

SELECT
    campaign_id,

    -- EXACT: expensive, requires full shuffle
    COUNT(DISTINCT user_id)                         AS exact_unique_users,

    -- APPROXIMATE: 1-2% error, much faster (HyperLogLog)
    APPROX_COUNT_DISTINCT(user_id)                  AS approx_unique_users,

    -- APPROXIMATE QUANTILES: percentiles without exact sort
    APPROX_QUANTILES(cost_usd, 100)[OFFSET(50)]     AS approx_median_cpc,
    APPROX_QUANTILES(cost_usd, 100)[OFFSET(95)]     AS approx_p95_cpc,

    -- EXACT percentile (when exactness required)
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cost_usd)   AS exact_median_cpc

FROM ad_clicks
WHERE click_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY campaign_id;

-- Rule: use APPROX for exploration/monitoring, EXACT for financial reporting
```

---

## PART 3: QUERY OPTIMIZATION PRACTICE

---

### O1. Rewrite this slow query (identify and fix all problems)

```sql
-- SLOW VERSION:
SELECT
    u.email,
    u.loyalty_tier,
    SUM(t.amount) AS total_spend
FROM users u
INNER JOIN transactions t ON u.user_id = t.user_id
WHERE YEAR(t.transaction_date) = 2024
  AND LOWER(u.loyalty_tier) = 'gold'
  AND u.user_id IN (
      SELECT user_id
      FROM transactions
      WHERE amount > 500
  )
GROUP BY u.email, u.loyalty_tier
ORDER BY total_spend DESC;

-- PROBLEMS:
-- 1. YEAR(t.transaction_date) = 2024: function on column → no partition pruning
-- 2. LOWER(u.loyalty_tier) = 'gold': function prevents index use (in OLAP, adds overhead)
-- 3. IN (subquery): runs subquery once per row in outer query (correlated)
-- 4. SELECT u.email: reads email column even if not needed for filtering
-- 5. INNER JOIN: silently drops users with transactions but loyalty_tier doesn't match

-- FAST VERSION:
WITH high_value_users AS (
    -- Pre-compute once as CTE (replaces correlated subquery)
    SELECT DISTINCT user_id
    FROM transactions
    WHERE transaction_date >= '2024-01-01'   -- partition filter
      AND transaction_date <  '2025-01-01'
      AND amount > 500
),

gold_spend AS (
    SELECT
        t.user_id,
        SUM(t.amount) AS total_spend
    FROM transactions t
    JOIN high_value_users hvu USING (user_id)  -- semi-join: filter early
    WHERE t.transaction_date >= '2024-01-01'   -- partition filter
      AND t.transaction_date <  '2025-01-01'
    GROUP BY t.user_id
)

SELECT
    u.email,
    u.loyalty_tier,
    gs.total_spend
FROM gold_spend gs
JOIN users u ON gs.user_id = u.user_id
WHERE u.loyalty_tier = 'gold'   -- no LOWER() if data is already lowercase
ORDER BY total_spend DESC;
```

---

### O2. Identify what makes this BigQuery query scan 5TB instead of 5GB

```sql
-- EXPENSIVE: 5TB scan
SELECT user_id, COUNT(*) AS events
FROM events
WHERE EXTRACT(YEAR FROM event_date) = 2024  -- ← KILLER: function on partition column
  AND event_type = 'purchase';

-- WHY: EXTRACT(YEAR FROM event_date) = 2024 applies a function to the partition column.
-- BigQuery cannot determine which partitions to skip without evaluating the function for every row.
-- Result: full table scan across ALL 1000+ partitions.

-- FIXED: 5GB scan (only 2024 partitions)
SELECT user_id, COUNT(*) AS events
FROM events
WHERE event_date >= '2024-01-01'            -- ← direct comparison = partition pruning
  AND event_date <  '2025-01-01'
  AND event_type = 'purchase';

-- OTHER PARTITION PRUNING KILLERS:
-- WHERE DATE_TRUNC(event_date, YEAR) = '2024-01-01'  ← function on partition column
-- WHERE CAST(event_date AS STRING) LIKE '2024%'       ← cast on partition column
-- WHERE event_date + INTERVAL '1 DAY' > '2024-01-02' ← arithmetic on partition column

-- THE RULE: partition column must appear alone on the left side of the comparison
-- event_date = '2024-01-15'           ← GOOD
-- event_date BETWEEN '...' AND '...'  ← GOOD
-- event_date >= '...' AND < '...'     ← GOOD
-- YEAR(event_date) = 2024             ← BAD
```

---

### O3. Optimize a slow JOIN query

```sql
-- SLOW: large table joined to medium table, no filters
SELECT l.*, r.campaign_name, r.channel
FROM ad_events l
JOIN campaigns r ON l.campaign_id = r.campaign_id;
-- Scans: all 10B rows of ad_events + all 1M rows of campaigns

-- OPTIMIZATION 1: Filter before joining
SELECT l.*, r.campaign_name, r.channel
FROM (
    SELECT * FROM ad_events
    WHERE event_date = '2024-01-15'  -- partition filter: 10M not 10B rows
) l
JOIN campaigns r ON l.campaign_id = r.campaign_id;

-- OPTIMIZATION 2: Select only needed columns
SELECT
    l.event_id,
    l.user_id,
    l.event_date,
    l.revenue_usd,
    r.campaign_name,
    r.channel
FROM ad_events l                            -- not SELECT l.*
JOIN campaigns r ON l.campaign_id = r.campaign_id
WHERE l.event_date = '2024-01-15';

-- OPTIMIZATION 3: For BigQuery, if campaigns is < 10MB → auto-broadcast
-- For larger tables, hint explicitly:
SELECT /*+ BROADCAST(r) */ l.*, r.campaign_name
FROM ad_events l
JOIN campaigns r ON l.campaign_id = r.campaign_id
WHERE l.event_date = '2024-01-15';
```

---

### O4. Turn a correlated subquery into a window function

```sql
-- SLOW: correlated subquery (runs once per row)
SELECT
    campaign_id,
    report_date,
    spend_usd,
    (SELECT AVG(spend_usd)
     FROM campaign_daily cd2
     WHERE cd2.campaign_id = cd.campaign_id
       AND cd2.report_date BETWEEN
           DATE_SUB(cd.report_date, INTERVAL 7 DAY)
           AND cd.report_date
    ) AS spend_7d_avg
FROM campaign_daily cd;
-- Cost: O(n × m) — for each row, reruns the subquery

-- FAST: window function (single pass)
SELECT
    campaign_id,
    report_date,
    spend_usd,
    AVG(spend_usd) OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
        ROWS BETWEEN 7 PRECEDING AND CURRENT ROW
    ) AS spend_7d_avg
FROM campaign_daily;
-- Cost: O(n) — one scan of the table with rolling window

-- RULE: any aggregation that references "other rows in the same group" → window function
-- Correlated subqueries are almost always replaceable with window functions
-- Exception: when the subquery logic is too complex to express as a window
```

---

## PART 4: TRICKY SQL PROBLEMS

---

### T1. Find members who purchased in EVERY month of Q1 2024

```sql
WITH monthly_purchasers AS (
    SELECT DISTINCT
        member_id,
        DATE_TRUNC(purchase_date, MONTH) AS purchase_month
    FROM transactions
    WHERE purchase_date BETWEEN '2024-01-01' AND '2024-03-31'
),

member_month_counts AS (
    SELECT
        member_id,
        COUNT(DISTINCT purchase_month) AS months_active
    FROM monthly_purchasers
    GROUP BY member_id
)

SELECT member_id
FROM member_month_counts
WHERE months_active = 3;  -- all 3 months of Q1

-- Alternative: using COUNTIF
SELECT member_id
FROM (
    SELECT
        member_id,
        COUNTIF(DATE_TRUNC(purchase_date, MONTH) = '2024-01-01') AS jan,
        COUNTIF(DATE_TRUNC(purchase_date, MONTH) = '2024-02-01') AS feb,
        COUNTIF(DATE_TRUNC(purchase_date, MONTH) = '2024-03-01') AS mar
    FROM transactions
    WHERE purchase_date BETWEEN '2024-01-01' AND '2024-03-31'
    GROUP BY member_id
)
WHERE jan > 0 AND feb > 0 AND mar > 0;
```

---

### T2. NOT IN with NULLs — the silent bug

```sql
-- WRONG: may return zero rows if subquery has NULLs
SELECT * FROM campaigns
WHERE campaign_id NOT IN (
    SELECT campaign_id FROM blacklisted_campaigns
    -- If any row here has campaign_id IS NULL:
    -- 'C001' NOT IN (..., NULL) = NULL (not TRUE!)
    -- RESULT: WHERE NULL is FALSE → zero rows returned!
);

-- SAFE option 1: NOT EXISTS (handles NULLs correctly)
SELECT * FROM campaigns c
WHERE NOT EXISTS (
    SELECT 1 FROM blacklisted_campaigns b
    WHERE b.campaign_id = c.campaign_id
);

-- SAFE option 2: filter NULLs from subquery
SELECT * FROM campaigns
WHERE campaign_id NOT IN (
    SELECT campaign_id FROM blacklisted_campaigns
    WHERE campaign_id IS NOT NULL  -- explicit null filter
);

-- SAFE option 3: LEFT JOIN anti-pattern
SELECT c.*
FROM campaigns c
LEFT JOIN blacklisted_campaigns b USING (campaign_id)
WHERE b.campaign_id IS NULL;  -- NULL on right side = no match = not blacklisted

-- VERIFY: test the NULL behavior
SELECT 1 WHERE 'A' NOT IN ('B', 'C', NULL);  -- returns 0 rows (NULL!)
SELECT 1 WHERE 'A' NOT IN ('B', 'C');        -- returns 1 row (correct)
```

---

### T3. Join fan-out — detect and fix

```sql
-- PROBLEM: campaigns has multiple rows per campaign_id (SCD2 history)
-- Joining on campaign_id (not surrogate key) causes row multiplication

-- Check for fan-out risk:
SELECT campaign_id, COUNT(*) AS versions
FROM dim_campaigns
GROUP BY campaign_id
HAVING COUNT(*) > 1;
-- If this returns rows → joining on campaign_id will fan out

-- BEFORE join: check cardinality
SELECT COUNT(*) AS clicks FROM ad_clicks;      -- 10M
SELECT COUNT(DISTINCT campaign_id) FROM ad_clicks;  -- 1000 campaigns

-- After join WITHOUT SCD2 filter: count changes?
SELECT COUNT(*) FROM ad_clicks cl
JOIN dim_campaigns c ON cl.campaign_id = c.campaign_id;
-- If result >> 10M: fan-out happened!

-- FIXED: filter to current version only
SELECT COUNT(*) FROM ad_clicks cl
JOIN dim_campaigns c ON cl.campaign_id = c.campaign_id
WHERE c.is_current = TRUE;
-- OR: join on surrogate key (fact stores campaign_sk pointing to specific version)

-- GENERAL RULE: always check join multiplicity before production deployment
SELECT COUNT(*) BEFORE, COUNT(*) AFTER join, compare
```

---

### T4. Gaps in a sequence — find missing IDs

```sql
-- Problem: transaction IDs should be sequential (1,2,3,4,...)
-- Find missing IDs

WITH id_range AS (
    SELECT
        MIN(transaction_id) AS min_id,
        MAX(transaction_id) AS max_id
    FROM transactions
),

expected_ids AS (
    SELECT id
    FROM UNNEST(GENERATE_ARRAY(
        (SELECT min_id FROM id_range),
        (SELECT max_id FROM id_range)
    )) AS id
)

SELECT e.id AS missing_transaction_id
FROM expected_ids e
LEFT JOIN transactions t ON e.id = t.transaction_id
WHERE t.transaction_id IS NULL
ORDER BY e.id;

-- For very large ranges: use EXCEPT instead
SELECT id FROM UNNEST(GENERATE_ARRAY(1, 1000000)) AS id
EXCEPT DISTINCT
SELECT transaction_id FROM transactions;
```

---

### T5. Pivot unknown/dynamic values

```sql
-- Problem: number of distinct channels is unknown at query time
-- Need: one column per channel, regardless of how many channels exist

-- Step 1: Get all distinct channels (run once)
SELECT DISTINCT channel FROM campaign_daily ORDER BY channel;
-- Result: ['email', 'google_display', 'google_search', 'meta', 'tiktok']

-- Step 2: Manually write pivot (in BigQuery — dynamic SQL needed for truly dynamic pivot)
SELECT
    report_date,
    SUM(CASE WHEN channel = 'email'          THEN spend_usd END) AS email_spend,
    SUM(CASE WHEN channel = 'google_display' THEN spend_usd END) AS google_display_spend,
    SUM(CASE WHEN channel = 'google_search'  THEN spend_usd END) AS google_search_spend,
    SUM(CASE WHEN channel = 'meta'           THEN spend_usd END) AS meta_spend,
    SUM(CASE WHEN channel = 'tiktok'         THEN spend_usd END) AS tiktok_spend
FROM campaign_daily
GROUP BY report_date
ORDER BY report_date;

-- For truly dynamic pivot in BigQuery: use EXECUTE IMMEDIATE
DECLARE pivot_query STRING;
SET pivot_query = (
    SELECT CONCAT(
        'SELECT report_date, ',
        STRING_AGG(
            CONCAT('SUM(CASE WHEN channel = ''', channel, ''' THEN spend_usd END) AS ', channel, '_spend'),
            ', ' ORDER BY channel
        ),
        ' FROM campaign_daily GROUP BY report_date ORDER BY report_date'
    )
    FROM (SELECT DISTINCT channel FROM campaign_daily)
);
EXECUTE IMMEDIATE pivot_query;
```

---

## PART 5: INTERVIEW SCENARIOS

---

### S1. "Write a query to identify the top 20% of campaigns by ROAS that account for 80% of total revenue" (Pareto principle)

```sql
WITH campaign_metrics AS (
    SELECT
        campaign_id,
        SUM(spend_usd)      AS total_spend,
        SUM(revenue_usd)    AS total_revenue,
        SAFE_DIVIDE(SUM(revenue_usd), SUM(spend_usd)) AS roas
    FROM campaign_daily
    WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY campaign_id
),

ranked AS (
    SELECT
        *,
        -- Revenue rank (highest to lowest)
        ROW_NUMBER() OVER (ORDER BY total_revenue DESC)     AS revenue_rank,
        COUNT(*) OVER ()                                    AS total_campaigns,
        -- Cumulative revenue percentage
        SUM(total_revenue) OVER (
            ORDER BY total_revenue DESC
            ROWS UNBOUNDED PRECEDING
        ) / SUM(total_revenue) OVER ()                      AS cumulative_revenue_pct,
        -- Campaign percentile by ROAS
        NTILE(5) OVER (ORDER BY roas DESC)                  AS roas_quintile
    FROM campaign_metrics
)

SELECT
    campaign_id,
    total_spend,
    total_revenue,
    ROUND(roas, 4) AS roas,
    revenue_rank,
    ROUND(cumulative_revenue_pct * 100, 2) AS cumulative_revenue_pct,
    roas_quintile
FROM ranked
WHERE roas_quintile = 1     -- top 20% by ROAS
ORDER BY total_revenue DESC;
```

---

### S2. "Show me all campaigns where spend increased >20% but ROAS decreased >20% week over week"

```sql
WITH weekly AS (
    SELECT
        DATE_TRUNC(report_date, WEEK)   AS week,
        campaign_id,
        SUM(spend_usd)                  AS spend,
        SAFE_DIVIDE(SUM(revenue_usd), SUM(spend_usd)) AS roas
    FROM campaign_daily
    WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)
    GROUP BY 1, 2
),

comparison AS (
    SELECT
        campaign_id,
        week,
        spend,
        roas,
        LAG(spend, 1) OVER (PARTITION BY campaign_id ORDER BY week) AS prev_spend,
        LAG(roas,  1) OVER (PARTITION BY campaign_id ORDER BY week) AS prev_roas
    FROM weekly
)

SELECT
    campaign_id,
    week,
    ROUND(spend, 2)                                          AS current_spend,
    ROUND(prev_spend, 2)                                     AS prior_week_spend,
    ROUND(100.0 * (spend - prev_spend) / prev_spend, 1)      AS spend_pct_change,
    ROUND(roas, 4)                                           AS current_roas,
    ROUND(prev_roas, 4)                                      AS prior_week_roas,
    ROUND(100.0 * (roas - prev_roas) / prev_roas, 1)         AS roas_pct_change
FROM comparison
WHERE prev_spend IS NOT NULL
  AND (spend - prev_spend) / prev_spend > 0.20     -- spend increased >20%
  AND (roas - prev_roas) / prev_roas < -0.20       -- ROAS decreased >20%
ORDER BY roas_pct_change ASC;

-- This pattern: high spend + low ROAS = inefficient scaling
-- Business insight: campaign is getting more expensive but less effective
-- Possible causes: audience saturation, bid inflation, creative fatigue
```

---

### S3. "Write a query to find the shortest path between two campaign categories in a hierarchy" (recursive CTE)

```sql
-- category_hierarchy: (category_id, name, parent_id)
-- Find path from 'Electronics' (id=10) to 'TV' (id=47)

WITH RECURSIVE paths AS (
    -- Start from source node
    SELECT
        category_id,
        parent_id,
        name,
        CAST(category_id AS STRING) AS path,
        1 AS depth
    FROM category_hierarchy
    WHERE category_id = 10  -- start: Electronics

    UNION ALL

    -- Traverse to children
    SELECT
        ch.category_id,
        ch.parent_id,
        ch.name,
        CONCAT(p.path, ' -> ', CAST(ch.category_id AS STRING)),
        p.depth + 1
    FROM category_hierarchy ch
    JOIN paths p ON ch.parent_id = p.category_id
    WHERE p.depth < 10                          -- max depth guard
      AND INSTR(p.path, CAST(ch.category_id AS STRING)) = 0  -- prevent cycles
)

SELECT path, depth, name
FROM paths
WHERE category_id = 47  -- target: TV
ORDER BY depth
LIMIT 1;  -- shortest path only
```

---

## QUICK PATTERNS FOR WINDOW FUNCTIONS

```
Pattern                          | SQL
─────────────────────────────────────────────────────────────────────────
Top N per partition              | ROW_NUMBER() OVER (PARTITION BY X ORDER BY Y) <= N
Running total (reset per group)  | SUM(v) OVER (PARTITION BY grp, DATE_TRUNC(d,MONTH) ORDER BY d ROWS UNBOUNDED PRECEDING)
Percent of partition total       | v / SUM(v) OVER (PARTITION BY X)
Rank with ties (no gaps)         | DENSE_RANK() OVER (PARTITION BY X ORDER BY Y)
Prior period comparison          | LAG(v, N) OVER (PARTITION BY X ORDER BY d)
Forward fill NULLs               | LAST_VALUE(v IGNORE NULLS) OVER (PARTITION BY X ORDER BY d ROWS UNBOUNDED PRECEDING)
Rolling N-period average         | AVG(v) OVER (PARTITION BY X ORDER BY d ROWS BETWEEN N PRECEDING AND CURRENT ROW)
Consecutive-day islands          | DATE_SUB(d, INTERVAL ROW_NUMBER() OVER (PARTITION BY X ORDER BY d) DAY)
Session ID from 30-min gaps      | SUM(CASE WHEN gap>30 OR gap IS NULL THEN 1 ELSE 0 END) OVER (PARTITION BY user ORDER BY event_at ROWS UNBOUNDED PRECEDING)
Anomaly z-score                  | (v - AVG(v) OVER (PARTITION BY X)) / NULLIF(STDDEV(v) OVER (PARTITION BY X), 0)
```
