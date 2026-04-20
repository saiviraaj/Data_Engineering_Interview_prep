# SQL Practice Questions — Easy to Hard
## Costco Sr. Data Engineer Interview Prep

---

## SECTION 1: EASY (Warm-Up)

---

### E1. Count clicks per campaign for yesterday
**Tables**: `ad_clicks(click_id, campaign_id, clicked_at, cost_usd)`

```sql
SELECT
    campaign_id,
    COUNT(*)        AS clicks,
    SUM(cost_usd)   AS total_spend
FROM ad_clicks
WHERE DATE(clicked_at) = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
GROUP BY campaign_id
ORDER BY clicks DESC;
```

---

### E2. Find campaigns with no clicks in the last 7 days
**Tables**: `campaigns(campaign_id, campaign_name, status)`, `ad_clicks(click_id, campaign_id, clicked_at)`

```sql
SELECT
    c.campaign_id,
    c.campaign_name,
    c.status
FROM campaigns c
WHERE c.status = 'active'
  AND NOT EXISTS (
      SELECT 1
      FROM ad_clicks cl
      WHERE cl.campaign_id = c.campaign_id
        AND cl.clicked_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  );
```

**Key point**: Use `NOT EXISTS` not `NOT IN` — if `ad_clicks.campaign_id` has NULLs, `NOT IN` returns zero rows.

---

### E3. Calculate CTR per campaign (handle division by zero)
**Table**: `campaign_daily(campaign_id, report_date, impressions, clicks)`

```sql
SELECT
    campaign_id,
    report_date,
    impressions,
    clicks,
    SAFE_DIVIDE(clicks, impressions)        AS ctr,           -- BigQuery
    -- Standard SQL alternative:
    CASE WHEN impressions = 0 THEN NULL
         ELSE ROUND(clicks * 1.0 / impressions, 6)
    END                                     AS ctr_standard
FROM campaign_daily
WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY);
```

---

### E4. Top 5 campaigns by spend last month
```sql
SELECT
    campaign_id,
    SUM(cost_usd) AS total_spend
FROM ad_clicks
WHERE DATE_TRUNC(DATE(clicked_at), MONTH) = DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH), MONTH)
GROUP BY campaign_id
ORDER BY total_spend DESC
LIMIT 5;
```

---

### E5. Find duplicate click_ids
**Table**: `raw_ad_clicks(click_id, campaign_id, clicked_at, cost_usd)`

```sql
-- Method 1: GROUP BY + HAVING
SELECT
    click_id,
    COUNT(*) AS occurrences
FROM raw_ad_clicks
GROUP BY click_id
HAVING COUNT(*) > 1
ORDER BY occurrences DESC;

-- Method 2: Self-join (alternative)
SELECT DISTINCT a.click_id
FROM raw_ad_clicks a
JOIN raw_ad_clicks b
    ON a.click_id = b.click_id
    AND a.ctid != b.ctid;  -- PostgreSQL rowid; in BigQuery use _table_suffix or loaded_at

-- Method 3: COUNT vs COUNT DISTINCT (quick check)
SELECT
    COUNT(*)                    AS total_rows,
    COUNT(DISTINCT click_id)    AS unique_clicks,
    COUNT(*) - COUNT(DISTINCT click_id) AS duplicate_count
FROM raw_ad_clicks;
```

---

### E6. Members who made more than 3 purchases in January 2024
**Table**: `transactions(transaction_id, member_id, amount_usd, purchase_date)`

```sql
SELECT
    member_id,
    COUNT(*)            AS purchase_count,
    SUM(amount_usd)     AS total_spend
FROM transactions
WHERE purchase_date BETWEEN '2024-01-01' AND '2024-01-31'
GROUP BY member_id
HAVING COUNT(*) > 3
ORDER BY purchase_count DESC;
```

---

### E7. NULL handling — campaigns with missing budget
**Table**: `campaigns(campaign_id, campaign_name, daily_budget_usd, status)`

```sql
-- Find campaigns where budget is NULL or zero
SELECT
    campaign_id,
    campaign_name,
    COALESCE(daily_budget_usd, 0)   AS budget_or_zero,
    CASE
        WHEN daily_budget_usd IS NULL THEN 'missing'
        WHEN daily_budget_usd = 0 THEN 'zero_budget'
        ELSE 'has_budget'
    END                              AS budget_status
FROM campaigns
WHERE status = 'active'
  AND (daily_budget_usd IS NULL OR daily_budget_usd = 0);
```

---

### E8. Join: enrich clicks with campaign name
```sql
SELECT
    cl.click_id,
    cl.campaign_id,
    c.campaign_name,
    c.channel,
    cl.cost_usd,
    cl.clicked_at
FROM ad_clicks cl
LEFT JOIN campaigns c ON cl.campaign_id = c.campaign_id
-- LEFT JOIN: keep all clicks even if campaign record is missing
WHERE DATE(cl.clicked_at) = CURRENT_DATE() - 1;
```

**Why LEFT not INNER**: If a campaign was deleted from the campaigns table, INNER JOIN silently drops all clicks for that campaign from your report.

---

## SECTION 2: MEDIUM

---

### M1. Running total spend per campaign per month (resets each month)

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
    ROUND(100.0 * SUM(spend_usd) OVER (
        PARTITION BY campaign_id, DATE_TRUNC(report_date, MONTH)
        ORDER BY report_date
        ROWS UNBOUNDED PRECEDING
    ) / NULLIF(SUM(daily_budget_usd) OVER (
        PARTITION BY campaign_id, DATE_TRUNC(report_date, MONTH)
    ), 0), 2)                                               AS pct_budget_used
FROM campaign_daily
ORDER BY campaign_id, report_date;
```

**Key concept**: `PARTITION BY campaign_id, DATE_TRUNC(report_date, MONTH)` — the month in the PARTITION forces the window to reset at the start of each new month.

---

### M2. Deduplicate: keep the most recent record per click_id

```sql
-- Method 1: ROW_NUMBER (most common, deterministic)
SELECT * EXCEPT (rn)
FROM (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY click_id
               ORDER BY _loaded_at DESC, updated_at DESC
           ) AS rn
    FROM raw_ad_clicks
)
WHERE rn = 1;

-- Method 2: QUALIFY (BigQuery shorthand)
SELECT *
FROM raw_ad_clicks
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY click_id
    ORDER BY _loaded_at DESC
) = 1;

-- Method 3: Aggregate (when you want max value per key)
SELECT
    click_id,
    MAX(campaign_id)    AS campaign_id,
    MAX(cost_usd)       AS cost_usd,
    MAX(_loaded_at)     AS latest_load
FROM raw_ad_clicks
GROUP BY click_id;
```

---

### M3. Find the second highest ROAS per channel

```sql
-- Method 1: DENSE_RANK (handles ties correctly)
SELECT channel, campaign_id, roas
FROM (
    SELECT
        channel,
        campaign_id,
        roas,
        DENSE_RANK() OVER (PARTITION BY channel ORDER BY roas DESC) AS dr
    FROM (
        SELECT
            c.channel,
            p.campaign_id,
            SAFE_DIVIDE(SUM(p.revenue_usd), SUM(p.spend_usd)) AS roas
        FROM campaign_daily_performance p
        JOIN campaigns c USING (campaign_id)
        WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        GROUP BY 1, 2
    )
)
WHERE dr = 2;
```

**DENSE_RANK vs ROW_NUMBER**: If two campaigns tie for first place ROAS, `DENSE_RANK` gives them both rank 1 and the next gets rank 2. `ROW_NUMBER` would assign ranks 1,2 arbitrarily and the next would be rank 3 — potentially skipping the "true" second highest.

---

### M4. Pivot: channel spend as columns

```sql
-- Input: one row per (date, channel, spend)
-- Output: one row per date, one column per channel

SELECT
    report_date,
    SUM(CASE WHEN channel = 'google_search'  THEN spend_usd END)    AS google_search_spend,
    SUM(CASE WHEN channel = 'google_display' THEN spend_usd END)    AS google_display_spend,
    SUM(CASE WHEN channel = 'meta_facebook'  THEN spend_usd END)    AS meta_facebook_spend,
    SUM(CASE WHEN channel = 'meta_instagram' THEN spend_usd END)    AS meta_instagram_spend,
    SUM(CASE WHEN channel = 'tiktok'         THEN spend_usd END)    AS tiktok_spend,
    SUM(spend_usd)                                                   AS total_spend,
    SAFE_DIVIDE(
        SUM(revenue_usd),
        SUM(spend_usd)
    )                                                                AS blended_roas
FROM campaign_daily_performance
WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY report_date
ORDER BY report_date;
```

---

### M5. Sessionize user events (30-minute gap = new session)

```sql
WITH events_ordered AS (
    SELECT
        user_id,
        event_type,
        event_at,
        TIMESTAMP_DIFF(
            event_at,
            LAG(event_at) OVER (PARTITION BY user_id ORDER BY event_at),
            MINUTE
        ) AS gap_minutes
    FROM user_events
    WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
),

with_session_flag AS (
    SELECT *,
        CASE
            WHEN gap_minutes IS NULL OR gap_minutes > 30 THEN 1
            ELSE 0
        END AS is_new_session
    FROM events_ordered
),

with_session_id AS (
    SELECT *,
        SUM(is_new_session) OVER (
            PARTITION BY user_id
            ORDER BY event_at
            ROWS UNBOUNDED PRECEDING
        ) AS session_num
    FROM with_session_flag
)

SELECT
    user_id,
    session_num,
    MIN(event_at)                                           AS session_start,
    MAX(event_at)                                           AS session_end,
    COUNT(*)                                                AS events_in_session,
    TIMESTAMP_DIFF(MAX(event_at), MIN(event_at), MINUTE)   AS duration_min,
    MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS had_purchase
FROM with_session_id
GROUP BY user_id, session_num
ORDER BY user_id, session_num;
```

---

### M6. Week-over-week ROAS change with percentage

```sql
SELECT
    report_date,
    campaign_id,
    roas,
    LAG(roas, 7) OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
    )                                               AS roas_prior_week,
    ROUND(
        SAFE_DIVIDE(
            roas - LAG(roas, 7) OVER (PARTITION BY campaign_id ORDER BY report_date),
            LAG(roas, 7) OVER (PARTITION BY campaign_id ORDER BY report_date)
        ) * 100,
        2
    )                                               AS roas_wow_pct_change,
    CASE
        WHEN roas > LAG(roas, 7) OVER (PARTITION BY campaign_id ORDER BY report_date) * 1.1
            THEN 'improving'
        WHEN roas < LAG(roas, 7) OVER (PARTITION BY campaign_id ORDER BY report_date) * 0.9
            THEN 'declining'
        ELSE 'stable'
    END                                             AS trend
FROM mart_campaign_performance
WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
ORDER BY campaign_id, report_date;
```

---

### M7. Cohort retention — members returning each month

```sql
WITH first_purchase AS (
    SELECT
        member_id,
        DATE_TRUNC(MIN(purchase_date), MONTH) AS cohort_month
    FROM transactions
    GROUP BY member_id
),

activity AS (
    SELECT DISTINCT
        member_id,
        DATE_TRUNC(purchase_date, MONTH) AS activity_month
    FROM transactions
),

cohort_data AS (
    SELECT
        fp.cohort_month,
        a.activity_month,
        DATE_DIFF(a.activity_month, fp.cohort_month, MONTH) AS months_since_cohort,
        COUNT(DISTINCT a.member_id) AS retained_members
    FROM first_purchase fp
    JOIN activity a USING (member_id)
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
    cd.months_since_cohort,
    cd.retained_members,
    ROUND(100.0 * cd.retained_members / cs.cohort_size, 1) AS retention_pct
FROM cohort_data cd
JOIN cohort_sizes cs USING (cohort_month)
WHERE cd.months_since_cohort BETWEEN 0 AND 11
ORDER BY cd.cohort_month, cd.months_since_cohort;
```

---

### M8. Find users who clicked on 3+ consecutive days

```sql
WITH daily_clickers AS (
    SELECT DISTINCT user_id, DATE(clicked_at) AS click_date
    FROM ad_clicks
),

numbered AS (
    SELECT
        user_id,
        click_date,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY click_date) AS rn
    FROM daily_clickers
),

islands AS (
    SELECT
        user_id,
        click_date,
        DATE_SUB(click_date, INTERVAL rn DAY) AS island_key
    FROM numbered
)

SELECT
    user_id,
    MIN(click_date)     AS streak_start,
    MAX(click_date)     AS streak_end,
    COUNT(*)            AS consecutive_days
FROM islands
GROUP BY user_id, island_key
HAVING COUNT(*) >= 3
ORDER BY consecutive_days DESC;
```

**Key trick**: For consecutive dates, `date - row_number = constant`. Any gap in dates changes the constant, creating a new "island."

---

### M9. Attribution: last-touch revenue per campaign

```sql
WITH clicks AS (
    SELECT
        click_id,
        campaign_id,
        user_id,
        clicked_at
    FROM ad_clicks
    WHERE clicked_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
),

conversions AS (
    SELECT
        conversion_id,
        user_id,
        converted_at,
        conversion_value_usd
    FROM ad_conversions
    WHERE converted_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
),

attributed AS (
    SELECT
        c.conversion_id,
        c.conversion_value_usd,
        cl.campaign_id,
        cl.clicked_at,
        ROW_NUMBER() OVER (
            PARTITION BY c.conversion_id
            ORDER BY cl.clicked_at DESC   -- LAST click
        ) AS touch_rank
    FROM conversions c
    JOIN clicks cl
        ON c.user_id = cl.user_id
        AND cl.clicked_at < c.converted_at
        AND cl.clicked_at >= TIMESTAMP_SUB(c.converted_at, INTERVAL 30 DAY)
)

SELECT
    campaign_id,
    COUNT(*)                    AS attributed_conversions,
    SUM(conversion_value_usd)   AS attributed_revenue
FROM attributed
WHERE touch_rank = 1
GROUP BY campaign_id
ORDER BY attributed_revenue DESC;
```

---

## SECTION 3: HARD

---

### H1. Fill missing dates with forward-fill (carry last known value)

**Problem**: Campaign daily performance has gaps (no data on days with zero spend). Fill those gaps by carrying the last known ROAS forward.

```sql
WITH date_spine AS (
    SELECT date_day
    FROM UNNEST(GENERATE_DATE_ARRAY(
        DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY),
        CURRENT_DATE() - 1,
        INTERVAL 1 DAY
    )) AS date_day
),

campaigns AS (
    SELECT DISTINCT campaign_id FROM campaign_daily
),

full_grid AS (
    SELECT d.date_day, c.campaign_id
    FROM date_spine d
    CROSS JOIN campaigns c
),

actual_data AS (
    SELECT report_date, campaign_id, roas, spend_usd
    FROM campaign_daily
    WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
),

joined AS (
    SELECT
        g.date_day,
        g.campaign_id,
        a.roas,
        a.spend_usd
    FROM full_grid g
    LEFT JOIN actual_data a
        ON g.date_day = a.report_date
        AND g.campaign_id = a.campaign_id
),

forward_filled AS (
    SELECT
        date_day,
        campaign_id,
        spend_usd,
        LAST_VALUE(roas IGNORE NULLS) OVER (
            PARTITION BY campaign_id
            ORDER BY date_day
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )                       AS roas_filled,
        CASE WHEN roas IS NULL THEN 'filled' ELSE 'actual' END AS data_type
    FROM joined
)

SELECT * FROM forward_filled
ORDER BY campaign_id, date_day;
```

---

### H2. Find the longest streak of days above ROAS target

**Problem**: For each campaign, find the longest consecutive-day streak where ROAS >= 3.0.

```sql
WITH daily_roas AS (
    SELECT
        report_date,
        campaign_id,
        roas,
        CASE WHEN roas >= 3.0 THEN 1 ELSE 0 END AS above_target
    FROM campaign_daily
    WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
),

filtered_above AS (
    SELECT
        report_date,
        campaign_id,
        ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY report_date) AS rn
    FROM daily_roas
    WHERE above_target = 1
),

streaks AS (
    SELECT
        campaign_id,
        DATE_SUB(report_date, INTERVAL rn DAY) AS island_key,
        MIN(report_date)    AS streak_start,
        MAX(report_date)    AS streak_end,
        COUNT(*)            AS streak_days
    FROM filtered_above
    GROUP BY campaign_id, island_key
)

SELECT
    campaign_id,
    streak_start,
    streak_end,
    streak_days,
    RANK() OVER (PARTITION BY campaign_id ORDER BY streak_days DESC) AS streak_rank
FROM streaks
QUALIFY streak_rank = 1
ORDER BY streak_days DESC;
```

---

### H3. Multi-touch attribution — linear model in SQL

```sql
WITH touchpoints AS (
    SELECT
        c.conversion_id,
        c.user_id,
        c.conversion_value_usd,
        c.converted_at,
        cl.click_id,
        cl.campaign_id,
        cl.channel,
        cl.clicked_at,
        TIMESTAMP_DIFF(c.converted_at, cl.clicked_at, HOUR) AS hours_before_conv,
        COUNT(*) OVER (PARTITION BY c.conversion_id) AS total_touches,
        ROW_NUMBER() OVER (PARTITION BY c.conversion_id ORDER BY cl.clicked_at ASC) AS touch_pos,
        ROW_NUMBER() OVER (PARTITION BY c.conversion_id ORDER BY cl.clicked_at DESC) AS touch_pos_rev
    FROM ad_conversions c
    JOIN ad_clicks cl
        ON c.user_id = cl.user_id
        AND cl.clicked_at BETWEEN
            TIMESTAMP_SUB(c.converted_at, INTERVAL 30 DAY)
            AND c.converted_at
)

SELECT
    campaign_id,
    channel,
    COUNT(DISTINCT conversion_id)                                   AS assisted_conversions,

    -- Last touch
    SUM(CASE WHEN touch_pos_rev = 1 THEN conversion_value_usd ELSE 0 END)
                                                                    AS last_touch_revenue,

    -- First touch
    SUM(CASE WHEN touch_pos = 1 THEN conversion_value_usd ELSE 0 END)
                                                                    AS first_touch_revenue,

    -- Linear (equal split)
    SUM(conversion_value_usd * 1.0 / total_touches)                AS linear_revenue,

    -- Time decay (half-life = 7 days = 168 hours)
    SUM(
        conversion_value_usd *
        POW(0.5, hours_before_conv / 168.0) /
        SUM(POW(0.5, hours_before_conv / 168.0)) OVER (PARTITION BY conversion_id)
    )                                                               AS time_decay_revenue

FROM touchpoints
GROUP BY campaign_id, channel
ORDER BY linear_revenue DESC;
```

---

### H4. Detect anomalous spend days using Z-score

```sql
WITH daily_spend AS (
    SELECT
        report_date,
        campaign_id,
        SUM(spend_usd) AS daily_spend
    FROM campaign_daily
    WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    GROUP BY 1, 2
),

stats AS (
    SELECT
        campaign_id,
        AVG(daily_spend)    AS mean_spend,
        STDDEV(daily_spend) AS std_spend
    FROM daily_spend
    WHERE report_date < DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)  -- exclude today from baseline
    GROUP BY campaign_id
)

SELECT
    d.report_date,
    d.campaign_id,
    d.daily_spend,
    s.mean_spend,
    s.std_spend,
    SAFE_DIVIDE(d.daily_spend - s.mean_spend, s.std_spend) AS z_score,
    CASE
        WHEN ABS(SAFE_DIVIDE(d.daily_spend - s.mean_spend, s.std_spend)) > 3
            THEN 'ANOMALY'
        WHEN ABS(SAFE_DIVIDE(d.daily_spend - s.mean_spend, s.std_spend)) > 2
            THEN 'WARNING'
        ELSE 'NORMAL'
    END AS status
FROM daily_spend d
JOIN stats s USING (campaign_id)
WHERE d.report_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
  AND ABS(SAFE_DIVIDE(d.daily_spend - s.mean_spend, s.std_spend)) > 2
ORDER BY ABS(z_score) DESC;
```

---

### H5. SCD Type 2 — point-in-time budget lookup

**Problem**: Given daily ad spend, join each row to the campaign budget that was active on THAT day (not today's budget).

```sql
-- dim_campaigns_scd2: campaign_id, daily_budget_usd, valid_from, valid_to (NULL = current)

SELECT
    p.report_date,
    p.campaign_id,
    p.spend_usd,
    c.daily_budget_usd,
    ROUND(100.0 * p.spend_usd / NULLIF(c.daily_budget_usd, 0), 2) AS pct_of_budget,
    CASE
        WHEN p.spend_usd > c.daily_budget_usd THEN 'over_budget'
        WHEN p.spend_usd > c.daily_budget_usd * 0.9 THEN 'near_budget'
        ELSE 'within_budget'
    END AS budget_status
FROM campaign_daily_performance p
JOIN dim_campaigns_scd2 c
    ON p.campaign_id = c.campaign_id
    AND p.report_date >= c.valid_from
    AND p.report_date < COALESCE(c.valid_to, '9999-12-31')
ORDER BY p.report_date DESC, pct_of_budget DESC;
```

---

### H6. Funnel drop-off analysis

**Problem**: Given an events table with session_id, event_type, and event_at, compute step-by-step funnel conversion rates.

**Funnel**: impression → click → page_view → add_to_cart → purchase

```sql
WITH session_funnel AS (
    SELECT
        session_id,
        user_id,
        campaign_id,
        MAX(CASE WHEN event_type = 'impression'     THEN 1 ELSE 0 END) AS had_impression,
        MAX(CASE WHEN event_type = 'click'          THEN 1 ELSE 0 END) AS had_click,
        MAX(CASE WHEN event_type = 'page_view'      THEN 1 ELSE 0 END) AS had_page_view,
        MAX(CASE WHEN event_type = 'add_to_cart'    THEN 1 ELSE 0 END) AS had_add_to_cart,
        MAX(CASE WHEN event_type = 'purchase'       THEN 1 ELSE 0 END) AS had_purchase
    FROM ad_events
    WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY session_id, user_id, campaign_id
)

SELECT
    campaign_id,
    COUNT(*)                                    AS total_sessions,
    SUM(had_impression)                         AS impressions,
    SUM(had_click)                              AS clicks,
    SUM(had_page_view)                          AS page_views,
    SUM(had_add_to_cart)                        AS add_to_carts,
    SUM(had_purchase)                           AS purchases,

    -- Step conversion rates
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_click),        SUM(had_impression)),    2) AS imp_to_click_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_page_view),    SUM(had_click)),         2) AS click_to_view_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_add_to_cart),  SUM(had_page_view)),     2) AS view_to_cart_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_purchase),     SUM(had_add_to_cart)),   2) AS cart_to_purchase_pct,

    -- Overall conversion rate (impression to purchase)
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_purchase),     SUM(had_impression)),    4) AS overall_cvr_pct

FROM session_funnel
GROUP BY campaign_id
ORDER BY purchases DESC;
```

---

### H7. Recursive CTE — find all upstream dependencies of a pipeline

```sql
-- Table: pipeline_dependencies(pipeline_id, depends_on_pipeline_id)
-- Goal: find all transitive dependencies of pipeline P_MART_ROAS

WITH RECURSIVE deps AS (
    -- Anchor: start with the target pipeline
    SELECT
        pipeline_id,
        depends_on_pipeline_id,
        1 AS depth,
        CAST(pipeline_id AS STRING) AS path
    FROM pipeline_dependencies
    WHERE pipeline_id = 'P_MART_ROAS'

    UNION ALL

    -- Recursive: find each dependency's dependencies
    SELECT
        d.pipeline_id,
        pd.depends_on_pipeline_id,
        deps.depth + 1,
        CONCAT(deps.path, ' -> ', d.pipeline_id)
    FROM pipeline_dependencies pd
    JOIN deps d ON pd.pipeline_id = deps.depends_on_pipeline_id
    WHERE deps.depth < 20  -- prevent infinite loops
)

SELECT DISTINCT
    depends_on_pipeline_id AS upstream_pipeline,
    MIN(depth) AS shortest_path_depth,
    path
FROM deps
GROUP BY depends_on_pipeline_id, path
ORDER BY shortest_path_depth, upstream_pipeline;
```

---

### H8. Median CPC without PERCENTILE functions

```sql
WITH ordered AS (
    SELECT
        campaign_id,
        cost_usd,
        ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY cost_usd)  AS rn,
        COUNT(*)     OVER (PARTITION BY campaign_id)                     AS cnt
    FROM ad_clicks
    WHERE click_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
)

SELECT
    campaign_id,
    AVG(cost_usd)   AS median_cpc
FROM ordered
WHERE
    -- For odd count: pick middle row (cnt=5 → rn=3)
    -- For even count: pick two middle rows (cnt=6 → rn IN (3,4)), AVG = median
    rn IN (
        FLOOR((cnt + 1) / 2.0),
        CEIL((cnt + 1) / 2.0)
    )
GROUP BY campaign_id
ORDER BY median_cpc DESC;
```

---

## SECTION 4: VERY HARD

---

### VH1. Build a complete ROAS report with anomaly detection, WoW trend, and budget pacing — in one query

```sql
WITH base AS (
    SELECT
        p.report_date,
        p.campaign_id,
        c.campaign_name,
        c.channel,
        c.daily_budget_usd,
        p.impressions,
        p.clicks,
        p.spend_usd,
        p.conversions,
        p.revenue_usd,
        SAFE_DIVIDE(p.revenue_usd, p.spend_usd)     AS roas,
        SAFE_DIVIDE(p.clicks, p.impressions)         AS ctr,
        SAFE_DIVIDE(p.spend_usd, p.clicks)           AS cpc_usd,
        SAFE_DIVIDE(p.conversions, p.clicks)         AS cvr
    FROM campaign_daily_performance p
    JOIN dim_campaigns c ON p.campaign_id = c.campaign_id AND c.is_current = TRUE
    WHERE p.report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
),

with_trends AS (
    SELECT
        *,
        -- Week-over-week comparisons
        LAG(roas, 7)      OVER (PARTITION BY campaign_id ORDER BY report_date) AS roas_wow,
        LAG(spend_usd, 7) OVER (PARTITION BY campaign_id ORDER BY report_date) AS spend_wow,

        -- 7-day rolling averages
        AVG(roas) OVER (
            PARTITION BY campaign_id
            ORDER BY report_date
            ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
        )    AS roas_7d_avg,
        STDDEV(roas) OVER (
            PARTITION BY campaign_id
            ORDER BY report_date
            ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
        )    AS roas_7d_std,

        -- Month-to-date spend
        SUM(spend_usd) OVER (
            PARTITION BY campaign_id, DATE_TRUNC(report_date, MONTH)
            ORDER BY report_date
            ROWS UNBOUNDED PRECEDING
        )    AS spend_mtd,

        -- Monthly budget (sum of daily budgets)
        SUM(daily_budget_usd) OVER (
            PARTITION BY campaign_id, DATE_TRUNC(report_date, MONTH)
        )    AS monthly_budget

    FROM base
)

SELECT
    report_date,
    campaign_id,
    campaign_name,
    channel,
    impressions,
    clicks,
    spend_usd,
    revenue_usd,

    -- Core metrics
    ROUND(roas, 4)                                          AS roas,
    ROUND(ctr * 100, 4)                                     AS ctr_pct,
    ROUND(cpc_usd, 4)                                       AS cpc_usd,
    ROUND(cvr * 100, 4)                                     AS cvr_pct,

    -- Week-over-week
    ROUND(roas_wow, 4)                                      AS roas_prior_week,
    ROUND(SAFE_DIVIDE(roas - roas_wow, roas_wow) * 100, 2)  AS roas_wow_pct,

    -- Rolling baseline
    ROUND(roas_7d_avg, 4)                                   AS roas_7d_avg,

    -- Anomaly detection
    ROUND(SAFE_DIVIDE(roas - roas_7d_avg, roas_7d_std), 2)  AS roas_z_score,
    CASE
        WHEN roas < roas_7d_avg - 2 * roas_7d_std THEN '🔴 ANOMALY LOW'
        WHEN roas > roas_7d_avg + 2 * roas_7d_std THEN '🟡 ANOMALY HIGH'
        ELSE '🟢 NORMAL'
    END                                                     AS roas_status,

    -- Budget pacing
    ROUND(spend_mtd, 2)                                     AS spend_mtd,
    ROUND(monthly_budget, 2)                                AS monthly_budget,
    ROUND(100.0 * SAFE_DIVIDE(spend_mtd, monthly_budget), 2) AS budget_pct_used,
    ROUND(
        -- Expected pacing: (days elapsed / days in month) * monthly budget
        100.0 * SAFE_DIVIDE(
            spend_mtd,
            SAFE_DIVIDE(monthly_budget, EXTRACT(DAY FROM LAST_DAY(report_date)))
            * EXTRACT(DAY FROM report_date)
        ), 2
    )                                                       AS pacing_vs_expected_pct,

    CASE
        WHEN SAFE_DIVIDE(spend_mtd, monthly_budget) > 0.95 THEN 'near_cap'
        WHEN SAFE_DIVIDE(
            spend_mtd,
            SAFE_DIVIDE(monthly_budget, EXTRACT(DAY FROM LAST_DAY(report_date)))
            * EXTRACT(DAY FROM report_date)
        ) > 1.2 THEN 'overpacing'
        WHEN SAFE_DIVIDE(
            spend_mtd,
            SAFE_DIVIDE(monthly_budget, EXTRACT(DAY FROM LAST_DAY(report_date)))
            * EXTRACT(DAY FROM report_date)
        ) < 0.8 THEN 'underpacing'
        ELSE 'on_track'
    END                                                     AS pacing_status

FROM with_trends
WHERE report_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
ORDER BY
    CASE WHEN roas_status LIKE '%ANOMALY%' THEN 0 ELSE 1 END,
    ABS(SAFE_DIVIDE(roas - roas_7d_avg, roas_7d_std)) DESC;
```

---

### VH2. Members at risk — build a churn indicator using recency, frequency, and value

```sql
WITH member_metrics AS (
    SELECT
        member_id,
        DATE_DIFF(CURRENT_DATE(), MAX(purchase_date), DAY)  AS recency_days,
        COUNT(DISTINCT transaction_id)                       AS frequency,
        SUM(amount_usd)                                      AS monetary,
        AVG(amount_usd)                                      AS avg_order_value,
        DATE_DIFF(MAX(purchase_date), MIN(purchase_date), DAY) AS customer_tenure_days
    FROM transactions
    WHERE purchase_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
    GROUP BY member_id
),

rfm AS (
    SELECT
        *,
        NTILE(5) OVER (ORDER BY recency_days ASC)   AS r,   -- 5 = most recent
        NTILE(5) OVER (ORDER BY frequency ASC)       AS f,
        NTILE(5) OVER (ORDER BY monetary ASC)        AS m
    FROM member_metrics
),

segmented AS (
    SELECT
        *,
        CONCAT(CAST(r AS STRING), CAST(f AS STRING), CAST(m AS STRING)) AS rfm_cell,
        r + f + m AS rfm_score,
        CASE
            WHEN r >= 4 AND f >= 4 AND m >= 4 THEN 'champions'
            WHEN r >= 3 AND f >= 3 AND m >= 3 THEN 'loyal'
            WHEN r >= 4 AND f <= 2             THEN 'new'
            WHEN r <= 2 AND f >= 3 AND m >= 3 THEN 'at_risk'
            WHEN r <= 2 AND f >= 4 AND m >= 4 THEN 'cannot_lose'
            WHEN r <= 2 AND f <= 2 AND m <= 2 THEN 'lost'
            ELSE 'potential_loyalist'
        END AS segment
    FROM rfm
)

SELECT
    segment,
    COUNT(*) AS member_count,
    ROUND(AVG(monetary), 2) AS avg_total_spend,
    ROUND(AVG(recency_days), 1) AS avg_days_since_last_purchase,
    ROUND(AVG(frequency), 1) AS avg_purchase_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
FROM segmented
GROUP BY segment
ORDER BY
    CASE segment
        WHEN 'champions'    THEN 1
        WHEN 'loyal'        THEN 2
        WHEN 'cannot_lose'  THEN 3
        WHEN 'at_risk'      THEN 4
        WHEN 'potential_loyalist' THEN 5
        WHEN 'new'          THEN 6
        WHEN 'lost'         THEN 7
    END;
```

---

### VH3. Write a query to identify "gap days" in time series and fill them using a date spine with interpolation

**Problem**: Some campaigns have missing dates in the performance table. For each missing date, interpolate spend as the average of the previous and next day's spend.

```sql
WITH date_spine AS (
    SELECT date_day
    FROM UNNEST(GENERATE_DATE_ARRAY(
        '2024-01-01', '2024-01-31', INTERVAL 1 DAY
    )) AS date_day
),

campaign_dates AS (
    SELECT DISTINCT campaign_id FROM campaign_daily
    WHERE report_date BETWEEN '2024-01-01' AND '2024-01-31'
),

full_grid AS (
    SELECT d.date_day, c.campaign_id
    FROM date_spine d
    CROSS JOIN campaign_dates c
),

with_actuals AS (
    SELECT
        g.date_day,
        g.campaign_id,
        a.spend_usd,
        CASE WHEN a.spend_usd IS NULL THEN 'gap' ELSE 'actual' END AS day_type
    FROM full_grid g
    LEFT JOIN campaign_daily a
        ON g.date_day = a.report_date
        AND g.campaign_id = a.campaign_id
),

with_prev_next AS (
    SELECT
        date_day,
        campaign_id,
        spend_usd,
        day_type,
        -- Previous non-null spend
        LAST_VALUE(spend_usd IGNORE NULLS) OVER (
            PARTITION BY campaign_id
            ORDER BY date_day
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS prev_spend,
        -- Next non-null spend
        FIRST_VALUE(spend_usd IGNORE NULLS) OVER (
            PARTITION BY campaign_id
            ORDER BY date_day
            ROWS BETWEEN 1 FOLLOWING AND UNBOUNDED FOLLOWING
        ) AS next_spend
    FROM with_actuals
)

SELECT
    date_day,
    campaign_id,
    day_type,
    CASE
        WHEN day_type = 'actual' THEN spend_usd
        -- Linear interpolation: average of prev and next
        ELSE ROUND((COALESCE(prev_spend, next_spend) + COALESCE(next_spend, prev_spend)) / 2.0, 4)
    END AS spend_usd_filled
FROM with_prev_next
ORDER BY campaign_id, date_day;
```

---

## QUICK REFERENCE: SQL Patterns Cheat Sheet

```sql
-- DEDUP: keep latest row per key
QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY loaded_at DESC) = 1

-- TOP N PER GROUP: top 3 campaigns per channel by ROAS
QUALIFY RANK() OVER (PARTITION BY channel ORDER BY roas DESC) <= 3

-- RUNNING TOTAL (resets monthly)
SUM(spend) OVER (PARTITION BY campaign_id, DATE_TRUNC(date, MONTH) ORDER BY date ROWS UNBOUNDED PRECEDING)

-- FORWARD FILL nulls
LAST_VALUE(col IGNORE NULLS) OVER (PARTITION BY key ORDER BY date ROWS UNBOUNDED PRECEDING)

-- CONSECUTIVE DAYS island key
DATE_SUB(date_col, INTERVAL ROW_NUMBER() OVER (PARTITION BY id ORDER BY date_col) DAY)

-- Z-SCORE anomaly
(value - AVG(value) OVER (PARTITION BY id)) / NULLIF(STDDEV(value) OVER (PARTITION BY id), 0)

-- SAFE DIVISION (BigQuery)
SAFE_DIVIDE(numerator, denominator)
-- Standard SQL:
NULLIF(denominator, 0)  -- then divide (returns NULL if denom=0)

-- PERCENT OF TOTAL
100.0 * value / SUM(value) OVER ()

-- MONTH-TO-DATE
SUM(v) OVER (PARTITION BY id, DATE_TRUNC(d, MONTH) ORDER BY d ROWS UNBOUNDED PRECEDING)

-- NULL-SAFE NOT IN
NOT EXISTS (SELECT 1 FROM other WHERE other.key = main.key)
```
