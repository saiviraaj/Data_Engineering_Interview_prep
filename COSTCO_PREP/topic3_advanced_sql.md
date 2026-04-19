# Topic 3: Advanced SQL + Data Mangling, Transformations & Metric Creation
## Complete Interview Textbook — Costco Sr. Data Engineer

---

## TABLE OF CONTENTS

1. [SQL Foundations Refresher — The Execution Model](#1-sql-foundations-refresher)
2. [Window Functions — Complete Deep Dive](#2-window-functions)
3. [Advanced Aggregations & GROUPING SETS](#3-advanced-aggregations)
4. [CTEs, Recursive Queries & Subquery Patterns](#4-ctes-and-recursive-queries)
5. [Data Mangling — Cleaning & Transformation Patterns](#5-data-mangling)
6. [String Transformations](#6-string-transformations)
7. [Date & Time Transformations](#7-date-and-time-transformations)
8. [JSON & Semi-Structured Data in SQL](#8-json-and-semi-structured-data)
9. [Metric Creation from Raw Data](#9-metric-creation)
10. [AdTech / MarTech Metrics in SQL](#10-adtech-martech-metrics)
11. [Advanced Joins — All Patterns](#11-advanced-joins)
12. [Performance Optimization for BigQuery SQL](#12-performance-optimization)
13. [SQL Anti-Patterns & Debugging](#13-sql-anti-patterns)
14. [Practice Problems — Graded Complexity](#14-practice-problems)

---

## 1. SQL Foundations Refresher — The Execution Model

Understanding *how* SQL executes helps you write correct, performant queries and answer "why doesn't this work?" questions in interviews.

### Logical Query Processing Order (NOT the written order)

```
Written order:          Execution order:
SELECT          →   1. FROM
FROM            →   2. JOIN (ON conditions)
JOIN            →   3. WHERE
WHERE           →   4. GROUP BY
GROUP BY        →   5. HAVING
HAVING          →   6. SELECT (aliases created here)
ORDER BY        →   7. DISTINCT
LIMIT           →   8. ORDER BY
                    9. LIMIT / OFFSET
```

**Why this matters in interviews:**
- You cannot reference a SELECT alias in WHERE (alias doesn't exist yet)
- You CAN reference a SELECT alias in ORDER BY (ORDER BY executes after SELECT)
- HAVING filters on GROUP BY results; WHERE filters before grouping
- Window functions execute AFTER WHERE, GROUP BY, HAVING — but BEFORE ORDER BY and LIMIT

```sql
-- This FAILS — WHERE executes before SELECT, alias unknown
SELECT SUM(amount) AS total_revenue
FROM orders
WHERE total_revenue > 1000;  -- ❌ ERROR

-- Correct approach — use HAVING for aggregates
SELECT SUM(amount) AS total_revenue
FROM orders
GROUP BY customer_id
HAVING SUM(amount) > 1000;  -- ✅

-- OR use subquery / CTE
WITH revenue AS (
    SELECT customer_id, SUM(amount) AS total_revenue
    FROM orders
    GROUP BY customer_id
)
SELECT * FROM revenue WHERE total_revenue > 1000;  -- ✅
```

### NULL Semantics — Critical for Data Mangling

NULL is the source of more bugs in data pipelines than almost anything else.

```sql
-- NULL comparisons: NEVER use = for NULL check
SELECT * FROM table WHERE column = NULL;   -- ❌ Always returns 0 rows
SELECT * FROM table WHERE column IS NULL;  -- ✅

-- NULL in arithmetic: NULL propagates
SELECT 5 + NULL;  -- Returns NULL
SELECT NULL * 0;  -- Returns NULL (not 0!)

-- NULL in aggregates: ignored by most functions (except COUNT(*))
SELECT AVG(score) FROM students;  -- NULLs excluded from average
SELECT COUNT(score) FROM students;  -- NULLs excluded
SELECT COUNT(*) FROM students;     -- NULLs INCLUDED (counts rows)

-- NULL in comparisons: three-valued logic (TRUE, FALSE, UNKNOWN)
SELECT * FROM t WHERE col != 5;  -- Does NOT return rows where col IS NULL!
-- Correct:
SELECT * FROM t WHERE col != 5 OR col IS NULL;

-- COALESCE — returns first non-NULL
SELECT COALESCE(preferred_email, work_email, personal_email, 'no-email') AS email;

-- NULLIF — returns NULL if two values are equal (great for avoiding div by zero)
SELECT revenue / NULLIF(clicks, 0) AS cpc;  -- Returns NULL instead of div/0 error

-- IFNULL / NVL (dialect-specific)
SELECT IFNULL(discount, 0) AS discount;  -- MySQL/BigQuery
SELECT NVL(discount, 0) AS discount;     -- Oracle
```

---

## 2. Window Functions — Complete Deep Dive

Window functions are the most important advanced SQL topic for a Sr. Data Engineer. Mastery separates junior from senior.

### Core Syntax

```sql
function_name([arguments])
OVER (
    [PARTITION BY column1, column2]
    [ORDER BY column3 ASC/DESC]
    [ROWS/RANGE BETWEEN frame_start AND frame_end]
)
```

### The Window Frame

```
ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW  -- from start to current row
ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING          -- sliding 3-row window
ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING  -- entire partition
RANGE BETWEEN INTERVAL '7' DAY PRECEDING AND CURRENT ROW  -- 7-day rolling (BigQuery)
```

**ROWS vs RANGE:**
- `ROWS` counts physical rows
- `RANGE` compares values (all rows with same ORDER BY value treated as one group)

### Ranking Functions

```sql
-- Sample data: sales by rep per month
CREATE TABLE sales (
    rep_id INT,
    region VARCHAR,
    month DATE,
    revenue DECIMAL(10,2)
);

-- ROW_NUMBER: unique sequential rank (no ties)
SELECT
    rep_id,
    region,
    revenue,
    ROW_NUMBER() OVER (PARTITION BY region ORDER BY revenue DESC) AS rn
FROM sales;

-- RANK: ties get same rank, next rank SKIPS (1,1,3)
SELECT
    rep_id,
    revenue,
    RANK() OVER (ORDER BY revenue DESC) AS rnk
FROM sales;

-- DENSE_RANK: ties get same rank, next rank is CONSECUTIVE (1,1,2)
SELECT
    rep_id,
    revenue,
    DENSE_RANK() OVER (ORDER BY revenue DESC) AS dense_rnk
FROM sales;

-- NTILE: divide into N buckets (quartiles, deciles, percentiles)
SELECT
    rep_id,
    revenue,
    NTILE(4) OVER (ORDER BY revenue) AS quartile,   -- 1=bottom 25%, 4=top 25%
    NTILE(10) OVER (ORDER BY revenue) AS decile,
    NTILE(100) OVER (ORDER BY revenue) AS percentile
FROM sales;

-- PERCENT_RANK: relative rank 0 to 1
SELECT
    rep_id,
    revenue,
    PERCENT_RANK() OVER (ORDER BY revenue) AS pct_rank
FROM sales;
-- Formula: (rank - 1) / (total_rows - 1)

-- CUME_DIST: cumulative distribution 0 to 1
SELECT
    rep_id,
    revenue,
    CUME_DIST() OVER (ORDER BY revenue) AS cum_dist
FROM sales;
-- Formula: rank / total_rows
```

**Interview problem: Get top N per group**
```sql
-- Top 3 sales reps per region
WITH ranked AS (
    SELECT
        rep_id,
        region,
        revenue,
        ROW_NUMBER() OVER (PARTITION BY region ORDER BY revenue DESC) AS rn
    FROM sales
)
SELECT rep_id, region, revenue
FROM ranked
WHERE rn <= 3;
```

### Offset Functions (LAG/LEAD)

Critical for time-series analysis and change detection.

```sql
-- LAG: access previous row's value
SELECT
    month,
    revenue,
    LAG(revenue, 1) OVER (ORDER BY month) AS prev_month_revenue,
    LAG(revenue, 1, 0) OVER (ORDER BY month) AS prev_month_revenue_default,  -- default=0 if no prev
    revenue - LAG(revenue, 1) OVER (ORDER BY month) AS mom_change,
    ROUND(
        (revenue - LAG(revenue, 1) OVER (ORDER BY month))
        / NULLIF(LAG(revenue, 1) OVER (ORDER BY month), 0) * 100,
        2
    ) AS mom_pct_change
FROM sales
WHERE rep_id = 101
ORDER BY month;

-- LEAD: access next row's value
SELECT
    month,
    revenue,
    LEAD(revenue, 1) OVER (ORDER BY month) AS next_month_revenue,
    CASE
        WHEN LEAD(revenue, 1) OVER (ORDER BY month) > revenue THEN 'Growing'
        WHEN LEAD(revenue, 1) OVER (ORDER BY month) < revenue THEN 'Declining'
        ELSE 'Flat'
    END AS trend
FROM sales;

-- LAG with PARTITION (per-group previous value)
SELECT
    rep_id,
    region,
    month,
    revenue,
    LAG(revenue) OVER (PARTITION BY rep_id ORDER BY month) AS rep_prev_month
FROM sales;
```

### Aggregate Window Functions (Running Totals, Rolling Averages)

```sql
-- Running total
SELECT
    month,
    revenue,
    SUM(revenue) OVER (ORDER BY month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total
FROM sales;

-- Shorthand (same as above — default frame when ORDER BY is present)
SELECT
    month,
    revenue,
    SUM(revenue) OVER (ORDER BY month) AS running_total
FROM sales;

-- 7-day rolling average (BigQuery syntax with RANGE and INTERVAL)
SELECT
    event_date,
    daily_revenue,
    AVG(daily_revenue) OVER (
        ORDER BY UNIX_DATE(event_date)
        RANGE BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7d_avg
FROM daily_sales;

-- 30-day rolling average
SELECT
    event_date,
    daily_revenue,
    AVG(daily_revenue) OVER (
        PARTITION BY region
        ORDER BY UNIX_DATE(event_date)
        RANGE BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS rolling_30d_avg_by_region
FROM daily_sales;

-- Running SUM reset per partition
SELECT
    rep_id,
    month,
    revenue,
    SUM(revenue) OVER (PARTITION BY rep_id ORDER BY month) AS rep_running_total
FROM sales;

-- Running COUNT of non-null values
SELECT
    month,
    revenue,
    COUNT(revenue) OVER (ORDER BY month) AS cumulative_count
FROM sales;

-- Running MIN / MAX (useful for tracking all-time high/low)
SELECT
    month,
    revenue,
    MAX(revenue) OVER (ORDER BY month) AS all_time_high,
    MIN(revenue) OVER (ORDER BY month) AS all_time_low
FROM sales;

-- Percentage of total (no PARTITION = whole table denominator)
SELECT
    region,
    SUM(revenue) AS region_revenue,
    SUM(SUM(revenue)) OVER () AS total_revenue,
    ROUND(SUM(revenue) / SUM(SUM(revenue)) OVER () * 100, 2) AS pct_of_total
FROM sales
GROUP BY region;
-- Note: SUM(SUM(revenue)) — inner SUM is GROUP BY aggregate; outer SUM is window over groups
```

### FIRST_VALUE / LAST_VALUE / NTH_VALUE

```sql
-- First purchase amount for each customer
SELECT
    customer_id,
    order_date,
    amount,
    FIRST_VALUE(amount) OVER (
        PARTITION BY customer_id
        ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS first_order_amount
FROM orders;

-- Last value needs explicit frame (default excludes rows after current!)
SELECT
    customer_id,
    order_date,
    amount,
    LAST_VALUE(amount) OVER (
        PARTITION BY customer_id
        ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING  -- CRITICAL
    ) AS last_order_amount
FROM orders;

-- Second highest revenue per region
SELECT DISTINCT
    region,
    NTH_VALUE(revenue, 2) OVER (
        PARTITION BY region
        ORDER BY revenue DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS second_highest_revenue
FROM sales;
```

### Complex Window Function Patterns

```sql
-- PATTERN: Detect gaps in sequential IDs or dates
WITH numbered AS (
    SELECT
        event_id,
        event_date,
        LAG(event_date) OVER (ORDER BY event_date) AS prev_date,
        event_date - LAG(event_date) OVER (ORDER BY event_date) AS gap_days
    FROM events
)
SELECT * FROM numbered WHERE gap_days > 1;

-- PATTERN: Sessionization (group events into sessions by inactivity gap)
WITH with_gaps AS (
    SELECT
        user_id,
        event_time,
        CASE
            WHEN TIMESTAMP_DIFF(event_time,
                 LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time),
                 MINUTE) > 30
            OR LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time) IS NULL
            THEN 1
            ELSE 0
        END AS new_session_flag
    FROM clickstream
),
with_session_id AS (
    SELECT
        user_id,
        event_time,
        SUM(new_session_flag) OVER (
            PARTITION BY user_id
            ORDER BY event_time
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS session_id
    FROM with_gaps
)
SELECT user_id, session_id, COUNT(*) AS events_in_session,
       MIN(event_time) AS session_start, MAX(event_time) AS session_end
FROM with_session_id
GROUP BY user_id, session_id;

-- PATTERN: De-duplicate keeping latest record
WITH deduped AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY customer_id
            ORDER BY updated_at DESC
        ) AS rn
    FROM customers
)
SELECT * EXCEPT(rn) FROM deduped WHERE rn = 1;

-- PATTERN: Find consecutive runs (islands problem)
-- E.g., find consecutive days a user logged in
WITH ordered AS (
    SELECT
        user_id,
        login_date,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS rn
    FROM logins
),
grouped AS (
    SELECT
        user_id,
        login_date,
        DATE_SUB(login_date, INTERVAL rn DAY) AS grp  -- same group if consecutive
    FROM ordered
)
SELECT
    user_id,
    MIN(login_date) AS streak_start,
    MAX(login_date) AS streak_end,
    COUNT(*) AS streak_length
FROM grouped
GROUP BY user_id, grp
ORDER BY streak_length DESC;
```

---

## 3. Advanced Aggregations & GROUPING SETS

### Standard GROUP BY Recap

```sql
-- Multi-level grouping
SELECT
    region,
    product_category,
    EXTRACT(YEAR FROM sale_date) AS year,
    SUM(revenue) AS total_revenue,
    COUNT(DISTINCT customer_id) AS unique_customers,
    AVG(order_value) AS avg_order_value
FROM sales
GROUP BY region, product_category, year
HAVING SUM(revenue) > 100000
ORDER BY total_revenue DESC;
```

### GROUPING SETS — Multiple Aggregation Levels in One Query

```sql
-- Without GROUPING SETS — need UNION ALL (verbose, slow)
SELECT region, NULL AS product, SUM(revenue) FROM sales GROUP BY region
UNION ALL
SELECT NULL, product, SUM(revenue) FROM sales GROUP BY product
UNION ALL
SELECT NULL, NULL, SUM(revenue) FROM sales;

-- With GROUPING SETS (BigQuery supports this)
SELECT
    region,
    product_category,
    SUM(revenue) AS total_revenue
FROM sales
GROUP BY GROUPING SETS (
    (region, product_category),  -- Group by both
    (region),                    -- Group by region only
    (product_category),          -- Group by product only
    ()                           -- Grand total
);
```

### ROLLUP — Hierarchical Subtotals

```sql
-- ROLLUP creates subtotals at each level of hierarchy
SELECT
    COALESCE(year::TEXT, 'ALL YEARS') AS year,
    COALESCE(region, 'ALL REGIONS') AS region,
    COALESCE(product_category, 'ALL PRODUCTS') AS product_category,
    SUM(revenue) AS total_revenue
FROM sales
GROUP BY ROLLUP(year, region, product_category);
-- Creates: (year,region,product), (year,region), (year), () grand total

-- BigQuery ROLLUP
SELECT
    IFNULL(CAST(EXTRACT(YEAR FROM sale_date) AS STRING), 'ALL') AS year,
    IFNULL(region, 'ALL') AS region,
    SUM(revenue) AS revenue
FROM sales
GROUP BY ROLLUP(EXTRACT(YEAR FROM sale_date), region);
```

### CUBE — All Combinations

```sql
-- CUBE creates subtotals for ALL combinations
SELECT
    year,
    region,
    product_category,
    SUM(revenue) AS total_revenue
FROM sales
GROUP BY CUBE(year, region, product_category);
-- Creates 2^3 = 8 combinations: all 3, each pair, each single, grand total
```

### GROUPING() Function — Identifying Subtotal Rows

```sql
SELECT
    CASE GROUPING(region) WHEN 1 THEN 'ALL REGIONS' ELSE region END AS region,
    CASE GROUPING(product_category) WHEN 1 THEN 'ALL PRODUCTS' ELSE product_category END AS product,
    SUM(revenue) AS total_revenue,
    GROUPING(region) AS is_region_subtotal,
    GROUPING(product_category) AS is_product_subtotal
FROM sales
GROUP BY ROLLUP(region, product_category);
```

### Conditional Aggregation (CASE inside aggregate — very powerful)

```sql
-- Pivot-style conditional aggregation
SELECT
    customer_id,
    COUNT(*) AS total_orders,
    SUM(CASE WHEN channel = 'web' THEN 1 ELSE 0 END) AS web_orders,
    SUM(CASE WHEN channel = 'mobile' THEN 1 ELSE 0 END) AS mobile_orders,
    SUM(CASE WHEN channel = 'email' THEN 1 ELSE 0 END) AS email_orders,
    SUM(CASE WHEN channel = 'web' THEN amount ELSE 0 END) AS web_revenue,
    SUM(CASE WHEN status = 'returned' THEN amount ELSE 0 END) AS returned_amount,
    AVG(CASE WHEN channel = 'web' THEN amount END) AS avg_web_order_value,
    -- MarTech: conversion by channel
    COUNTIF(channel = 'web' AND converted = TRUE) AS web_conversions,
    SAFE_DIVIDE(
        COUNTIF(channel = 'web' AND converted = TRUE),
        COUNTIF(channel = 'web')
    ) AS web_conversion_rate
FROM orders
GROUP BY customer_id;

-- Multi-period comparison in one query
SELECT
    product_id,
    SUM(CASE WHEN sale_date BETWEEN '2024-01-01' AND '2024-03-31' THEN revenue END) AS q1_2024,
    SUM(CASE WHEN sale_date BETWEEN '2024-04-01' AND '2024-06-30' THEN revenue END) AS q2_2024,
    SUM(CASE WHEN sale_date BETWEEN '2024-07-01' AND '2024-09-30' THEN revenue END) AS q3_2024,
    SUM(CASE WHEN sale_date BETWEEN '2024-10-01' AND '2024-12-31' THEN revenue END) AS q4_2024,
    SUM(revenue) AS full_year_2024
FROM sales
WHERE EXTRACT(YEAR FROM sale_date) = 2024
GROUP BY product_id;
```

### ARRAY_AGG, STRING_AGG — Collecting Values

```sql
-- Collect all products a customer bought into an array
SELECT
    customer_id,
    ARRAY_AGG(product_id ORDER BY purchase_date) AS purchased_products,
    ARRAY_AGG(DISTINCT product_category) AS categories_purchased,
    STRING_AGG(product_name, ', ' ORDER BY purchase_date) AS product_list
FROM purchases
GROUP BY customer_id;

-- Use with STRUCT in BigQuery (nested record)
SELECT
    customer_id,
    ARRAY_AGG(
        STRUCT(product_id AS pid, amount AS amt, purchase_date AS dt)
        ORDER BY purchase_date
    ) AS purchase_history
FROM purchases
GROUP BY customer_id;

-- Flatten arrays back out
SELECT customer_id, product
FROM customers,
UNNEST(purchased_products) AS product;
```

---

## 4. CTEs and Recursive Queries

### CTE Patterns

```sql
-- Multi-step transformation using CTEs (readable pipeline)
WITH
raw_events AS (
    SELECT
        user_id,
        event_type,
        event_timestamp,
        properties
    FROM raw.clickstream
    WHERE DATE(event_timestamp) = CURRENT_DATE - 1
),
cleaned_events AS (
    SELECT
        user_id,
        event_type,
        event_timestamp,
        JSON_VALUE(properties, '$.page_url') AS page_url,
        JSON_VALUE(properties, '$.campaign_id') AS campaign_id
    FROM raw_events
    WHERE user_id IS NOT NULL
      AND event_type IN ('page_view', 'add_to_cart', 'purchase')
),
session_attributed AS (
    SELECT
        *,
        SUM(CASE
            WHEN TIMESTAMP_DIFF(event_timestamp,
                 LAG(event_timestamp) OVER (PARTITION BY user_id ORDER BY event_timestamp),
                 MINUTE) > 30
            OR LAG(event_timestamp) OVER (PARTITION BY user_id ORDER BY event_timestamp) IS NULL
            THEN 1 ELSE 0
        END) OVER (PARTITION BY user_id ORDER BY event_timestamp) AS session_id
    FROM cleaned_events
),
session_metrics AS (
    SELECT
        user_id,
        session_id,
        MIN(event_timestamp) AS session_start,
        MAX(event_timestamp) AS session_end,
        COUNT(*) AS events_in_session,
        MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS converted,
        MAX(campaign_id) AS attributed_campaign
    FROM session_attributed
    GROUP BY user_id, session_id
)
SELECT
    attributed_campaign,
    COUNT(*) AS total_sessions,
    SUM(converted) AS converting_sessions,
    SAFE_DIVIDE(SUM(converted), COUNT(*)) AS conversion_rate
FROM session_metrics
WHERE attributed_campaign IS NOT NULL
GROUP BY attributed_campaign
ORDER BY converting_sessions DESC;
```

### Recursive CTEs

Used for hierarchical data (org charts, category trees, bill of materials).

```sql
-- Org chart: find all reports under a manager (BigQuery supports recursive CTEs)
WITH RECURSIVE org_hierarchy AS (
    -- Anchor: start with the target manager
    SELECT
        employee_id,
        manager_id,
        name,
        title,
        0 AS level
    FROM employees
    WHERE employee_id = 1001  -- CEO or target manager

    UNION ALL

    -- Recursive: join employees to their manager
    SELECT
        e.employee_id,
        e.manager_id,
        e.name,
        e.title,
        oh.level + 1
    FROM employees e
    INNER JOIN org_hierarchy oh ON e.manager_id = oh.employee_id
)
SELECT * FROM org_hierarchy ORDER BY level, name;

-- Find path from root to a node
WITH RECURSIVE path AS (
    SELECT
        category_id,
        parent_category_id,
        name,
        CAST(name AS STRING) AS path
    FROM categories
    WHERE parent_category_id IS NULL  -- root nodes

    UNION ALL

    SELECT
        c.category_id,
        c.parent_category_id,
        c.name,
        CONCAT(p.path, ' > ', c.name)
    FROM categories c
    INNER JOIN path p ON c.parent_category_id = p.category_id
)
SELECT * FROM path;
```

---

## 5. Data Mangling — Cleaning & Transformation Patterns

This section covers the exact transformations you'll be asked about for the Costco role — messy real-world data handling.

### Deduplication Strategies

```sql
-- Strategy 1: ROW_NUMBER (most flexible)
WITH deduped AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY email          -- define uniqueness key
            ORDER BY updated_at DESC    -- keep most recent
        ) AS rn
    FROM raw_customers
)
SELECT * EXCEPT(rn) FROM deduped WHERE rn = 1;

-- Strategy 2: Distinct on all columns
SELECT DISTINCT * FROM raw_events;

-- Strategy 3: Keep first occurrence (by ID)
SELECT * FROM raw_customers
QUALIFY ROW_NUMBER() OVER (PARTITION BY email ORDER BY customer_id) = 1;
-- QUALIFY is BigQuery/Snowflake syntax — filters on window function results directly

-- Strategy 4: GROUP BY with aggregate
SELECT
    email,
    MIN(customer_id) AS customer_id,
    MAX(created_at) AS last_seen,
    COUNT(*) AS duplicate_count
FROM raw_customers
GROUP BY email;
```

### Handling Nulls in Transformation Pipelines

```sql
-- Fill nulls with defaults
SELECT
    user_id,
    COALESCE(first_name, 'Unknown') AS first_name,
    COALESCE(age, ROUND(AVG(age) OVER (), 0)) AS age,  -- fill with avg
    COALESCE(country, 'US') AS country,
    IFNULL(discount_pct, 0.0) AS discount_pct
FROM users;

-- Forward fill (use last known non-null value)
-- Useful for time series where readings are only recorded on change
WITH with_groups AS (
    SELECT
        sensor_id,
        reading_time,
        temperature,
        -- Create a group ID that changes only when temperature is non-null
        COUNT(temperature) OVER (
            PARTITION BY sensor_id
            ORDER BY reading_time
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS grp
    FROM sensor_readings
)
SELECT
    sensor_id,
    reading_time,
    FIRST_VALUE(temperature) OVER (
        PARTITION BY sensor_id, grp
        ORDER BY reading_time
    ) AS temperature_filled
FROM with_groups;

-- Replace nulls with interpolated values (midpoint)
SELECT
    date,
    revenue,
    COALESCE(revenue,
        (LAG(revenue) OVER (ORDER BY date) + LEAD(revenue) OVER (ORDER BY date)) / 2
    ) AS revenue_interpolated
FROM daily_revenue;
```

### Data Type Casting & Coercion

```sql
-- Safe casting (BigQuery: SAFE_CAST returns NULL instead of error)
SELECT
    SAFE_CAST(user_id_str AS INT64) AS user_id,
    SAFE_CAST(amount_str AS FLOAT64) AS amount,
    SAFE_CAST(event_date_str AS DATE) AS event_date,
    SAFE_CAST(price AS NUMERIC) AS price_precise
FROM raw_events;

-- Standard CAST
SELECT CAST('2024-01-15' AS DATE);
SELECT CAST(123.45 AS INT64);  -- truncates, doesn't round
SELECT CAST(123.45 AS STRING);

-- String to number with regex validation
SELECT
    raw_amount,
    CASE
        WHEN REGEXP_CONTAINS(raw_amount, r'^\d+\.?\d*$')
        THEN CAST(raw_amount AS FLOAT64)
        ELSE NULL
    END AS cleaned_amount
FROM transactions;
```

### Normalizing & Standardizing Values

```sql
-- Normalize categorical values (inconsistent formats)
SELECT
    CASE
        WHEN UPPER(TRIM(status)) IN ('ACTIVE', 'A', '1', 'YES', 'Y') THEN 'active'
        WHEN UPPER(TRIM(status)) IN ('INACTIVE', 'I', '0', 'NO', 'N') THEN 'inactive'
        WHEN UPPER(TRIM(status)) IN ('PENDING', 'P', 'WAIT', 'WAITING') THEN 'pending'
        ELSE 'unknown'
    END AS normalized_status
FROM customers;

-- Normalize phone numbers
SELECT
    phone_raw,
    REGEXP_REPLACE(phone_raw, r'[\s\-\(\)\+]', '') AS phone_digits_only,
    CASE
        WHEN REGEXP_CONTAINS(phone_raw, r'^\+?1?\s?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}$')
        THEN REGEXP_REPLACE(phone_raw, r'[^\d]', '')
        ELSE NULL
    END AS normalized_phone
FROM users;

-- Normalize email (lowercase, trim)
SELECT
    LOWER(TRIM(email)) AS normalized_email,
    REGEXP_EXTRACT(LOWER(TRIM(email)), r'@(.+)$') AS email_domain
FROM users;

-- Normalize currency amounts (strip $ , and convert)
SELECT
    amount_str,
    CAST(
        REGEXP_REPLACE(
            REGEXP_REPLACE(amount_str, r'[\$,]', ''),
            r'\s', ''
        ) AS FLOAT64
    ) AS amount_numeric
FROM transactions;
```

### Pivoting and Unpivoting

```sql
-- PIVOT: Rows to columns using conditional aggregation
-- From: (product, month, revenue) → To: (product, jan_rev, feb_rev, mar_rev)
SELECT
    product_id,
    SUM(CASE WHEN month = 1 THEN revenue END) AS jan_revenue,
    SUM(CASE WHEN month = 2 THEN revenue END) AS feb_revenue,
    SUM(CASE WHEN month = 3 THEN revenue END) AS mar_revenue,
    SUM(CASE WHEN month = 4 THEN revenue END) AS apr_revenue
FROM monthly_sales
GROUP BY product_id;

-- BigQuery native PIVOT syntax (newer)
SELECT * FROM monthly_sales
PIVOT (
    SUM(revenue)
    FOR month IN (1 AS jan, 2 AS feb, 3 AS mar, 4 AS apr)
);

-- UNPIVOT: Columns to rows
-- From: (product, jan_rev, feb_rev) → To: (product, month, revenue)
SELECT product_id, month, revenue
FROM monthly_pivot
UNPIVOT (
    revenue
    FOR month IN (jan_revenue AS 'January', feb_revenue AS 'February', mar_revenue AS 'March')
);

-- Manual UNPIVOT with UNION ALL (works everywhere)
SELECT product_id, 'January' AS month, jan_revenue AS revenue FROM monthly_pivot
UNION ALL
SELECT product_id, 'February', feb_revenue FROM monthly_pivot
UNION ALL
SELECT product_id, 'March', mar_revenue FROM monthly_pivot;
```

### Outlier Detection & Capping

```sql
-- IQR-based outlier detection
WITH stats AS (
    SELECT
        PERCENTILE_CONT(order_value, 0.25) OVER () AS q1,
        PERCENTILE_CONT(order_value, 0.75) OVER () AS q3
    FROM orders
    LIMIT 1
),
bounds AS (
    SELECT
        q1,
        q3,
        q1 - 1.5 * (q3 - q1) AS lower_bound,
        q3 + 1.5 * (q3 - q1) AS upper_bound
    FROM stats
)
SELECT
    o.*,
    CASE
        WHEN o.order_value < b.lower_bound THEN 'low_outlier'
        WHEN o.order_value > b.upper_bound THEN 'high_outlier'
        ELSE 'normal'
    END AS outlier_flag
FROM orders o, bounds b;

-- Winsorization (cap outliers at percentile boundary instead of removing)
WITH bounds AS (
    SELECT
        PERCENTILE_CONT(order_value, 0.01) OVER () AS p1,
        PERCENTILE_CONT(order_value, 0.99) OVER () AS p99
    FROM orders
    LIMIT 1
)
SELECT
    order_id,
    order_value,
    GREATEST(b.p1, LEAST(b.p99, order_value)) AS capped_order_value
FROM orders, bounds b;
```

---

## 6. String Transformations

### Core String Functions (BigQuery)

```sql
-- LENGTH / CHAR_LENGTH
SELECT LENGTH('hello world');  -- 11 bytes
SELECT CHAR_LENGTH('hello');   -- 5 characters

-- Trimming whitespace
SELECT TRIM('  hello  ');          -- 'hello'
SELECT LTRIM('  hello  ');         -- 'hello  '
SELECT RTRIM('  hello  ');         -- '  hello'
SELECT TRIM('###hello###', '#');   -- 'hello' (trim specific chars)

-- Case transformations
SELECT UPPER('hello World');    -- 'HELLO WORLD'
SELECT LOWER('HELLO World');    -- 'hello world'
SELECT INITCAP('hello world');  -- 'Hello World' (BigQuery: not native, use custom)

-- Substring extraction
SELECT SUBSTR('hello world', 7);      -- 'world' (from position 7)
SELECT SUBSTR('hello world', 7, 5);   -- 'world' (from 7, length 5)
SELECT LEFT('hello world', 5);        -- 'hello'
SELECT RIGHT('hello world', 5);       -- 'world'

-- String concatenation
SELECT CONCAT('hello', ' ', 'world');  -- 'hello world'
SELECT 'hello' || ' ' || 'world';      -- Standard SQL concat
SELECT FORMAT('%s has %d orders', name, order_count);  -- BigQuery FORMAT

-- String search
SELECT INSTR('hello world', 'world');         -- 7 (position)
SELECT STRPOS('hello world', 'world');        -- 7 (BigQuery)
SELECT CONTAINS_SUBSTR('hello world', 'ell'); -- TRUE (BigQuery, case-insensitive)
SELECT 'hello' LIKE '%ell%';                  -- TRUE

-- String replacement
SELECT REPLACE('hello world', 'world', 'earth');  -- 'hello earth'
SELECT REGEXP_REPLACE('abc123', r'[0-9]', '');     -- 'abc'

-- String splitting
SELECT SPLIT('a,b,c,d', ',');            -- ['a','b','c','d'] (BigQuery returns ARRAY)
SELECT SPLIT('a,b,c,d', ',')[OFFSET(0)]; -- 'a' (first element)
SELECT SPLIT('a,b,c,d', ',')[SAFE_OFFSET(10)]; -- NULL (safe, no error)

-- Extract parts
SELECT REGEXP_EXTRACT('user_id=12345&session=abc', r'user_id=(\d+)');  -- '12345'
SELECT REGEXP_EXTRACT_ALL('cat,dog,bird', r'[a-z]+');  -- ['cat','dog','bird']
```

### URL Parsing (Critical for MarTech)

```sql
-- Parse UTM parameters from URL
SELECT
    page_url,
    REGEXP_EXTRACT(page_url, r'[?&]utm_source=([^&]+)') AS utm_source,
    REGEXP_EXTRACT(page_url, r'[?&]utm_medium=([^&]+)') AS utm_medium,
    REGEXP_EXTRACT(page_url, r'[?&]utm_campaign=([^&]+)') AS utm_campaign,
    REGEXP_EXTRACT(page_url, r'[?&]utm_content=([^&]+)') AS utm_content,
    REGEXP_EXTRACT(page_url, r'[?&]utm_term=([^&]+)') AS utm_term,
    REGEXP_EXTRACT(page_url, r'^https?://([^/?]+)') AS domain,
    REGEXP_EXTRACT(page_url, r'^https?://[^/]+(/.*)') AS path
FROM web_events;

-- Extract product SKU from URL path
SELECT
    url_path,
    REGEXP_EXTRACT(url_path, r'/product/([A-Z0-9]+)') AS product_sku,
    REGEXP_EXTRACT(url_path, r'/category/([^/]+)') AS category
FROM page_views;
```

### String Aggregation and Array Operations

```sql
-- Concatenate strings from multiple rows
SELECT
    customer_id,
    STRING_AGG(product_name, ', ' ORDER BY purchase_date) AS all_products_purchased,
    STRING_AGG(DISTINCT category ORDER BY category) AS unique_categories
FROM purchases
GROUP BY customer_id;

-- Check if any value in array matches condition
SELECT user_id
FROM users
WHERE EXISTS (
    SELECT 1 FROM UNNEST(product_history) AS product
    WHERE product LIKE '%electronics%'
);

-- Count occurrences of character in string (BigQuery)
SELECT
    ARRAY_LENGTH(REGEXP_EXTRACT_ALL(text_field, r',')) + 1 AS comma_count
FROM data;

-- Pad strings
SELECT LPAD('42', 6, '0');   -- '000042'
SELECT RPAD('hello', 10, '.'); -- 'hello.....'
```

---

## 7. Date and Time Transformations

Dates are central to every analytics and MarTech pipeline.

### Date Construction and Parsing

```sql
-- Current date/time (BigQuery)
SELECT CURRENT_DATE();           -- 2024-01-15 (DATE type)
SELECT CURRENT_TIMESTAMP();      -- 2024-01-15 10:30:45 UTC (TIMESTAMP)
SELECT CURRENT_DATETIME();       -- 2024-01-15T10:30:45 (DATETIME, no timezone)

-- Construct dates
SELECT DATE(2024, 1, 15);                         -- 2024-01-15
SELECT DATETIME(2024, 1, 15, 10, 30, 0);          -- 2024-01-15 10:30:00
SELECT TIMESTAMP('2024-01-15 10:30:00 UTC');      -- Explicit UTC

-- Parse from string
SELECT PARSE_DATE('%Y-%m-%d', '2024-01-15');
SELECT PARSE_DATE('%m/%d/%Y', '01/15/2024');
SELECT PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', '2024-01-15 10:30:00');
SELECT PARSE_DATETIME('%d-%b-%Y', '15-Jan-2024');

-- Format to string
SELECT FORMAT_DATE('%B %d, %Y', CURRENT_DATE());  -- 'January 15, 2024'
SELECT FORMAT_TIMESTAMP('%Y%m%d', CURRENT_TIMESTAMP()); -- '20240115'
```

### Date Arithmetic

```sql
-- Add/subtract intervals
SELECT DATE_ADD(CURRENT_DATE(), INTERVAL 7 DAY);
SELECT DATE_ADD(CURRENT_DATE(), INTERVAL 1 MONTH);
SELECT DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY);
SELECT TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR);

-- Difference between dates
SELECT DATE_DIFF(end_date, start_date, DAY);    -- number of days between
SELECT DATE_DIFF(end_date, start_date, MONTH);  -- number of months between
SELECT DATE_DIFF(end_date, start_date, WEEK);   -- number of weeks
SELECT TIMESTAMP_DIFF(end_ts, start_ts, SECOND);
SELECT TIMESTAMP_DIFF(end_ts, start_ts, MINUTE);
SELECT TIMESTAMP_DIFF(end_ts, start_ts, HOUR);

-- Truncate to period boundary
SELECT DATE_TRUNC(CURRENT_DATE(), WEEK);    -- Monday of current week
SELECT DATE_TRUNC(CURRENT_DATE(), MONTH);   -- First day of month
SELECT DATE_TRUNC(CURRENT_DATE(), QUARTER); -- First day of quarter
SELECT DATE_TRUNC(CURRENT_DATE(), YEAR);    -- Jan 1 of year
SELECT TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), HOUR);   -- Top of current hour
SELECT TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), DAY);    -- Midnight of today
```

### Date Extraction

```sql
SELECT EXTRACT(YEAR FROM CURRENT_DATE());       -- 2024
SELECT EXTRACT(MONTH FROM CURRENT_DATE());      -- 1
SELECT EXTRACT(DAY FROM CURRENT_DATE());        -- 15
SELECT EXTRACT(DAYOFWEEK FROM CURRENT_DATE()); -- 1=Sunday, 7=Saturday
SELECT EXTRACT(DAYOFYEAR FROM CURRENT_DATE()); -- 1-366
SELECT EXTRACT(WEEK FROM CURRENT_DATE());      -- ISO week number
SELECT EXTRACT(QUARTER FROM CURRENT_DATE());   -- 1-4
SELECT EXTRACT(HOUR FROM CURRENT_TIMESTAMP());
SELECT EXTRACT(MINUTE FROM CURRENT_TIMESTAMP());
SELECT EXTRACT(SECOND FROM CURRENT_TIMESTAMP());

-- Day of week as string
SELECT FORMAT_DATE('%A', CURRENT_DATE());  -- 'Monday'
SELECT FORMAT_DATE('%a', CURRENT_DATE());  -- 'Mon'

-- Is it a weekend?
SELECT
    event_date,
    EXTRACT(DAYOFWEEK FROM event_date) IN (1, 7) AS is_weekend
FROM events;
```

### Time Zone Handling

```sql
-- Convert timezone
SELECT CONVERT_TZ(CURRENT_TIMESTAMP(), 'UTC', 'America/Los_Angeles');
-- BigQuery:
SELECT TIMESTAMP '2024-01-15 18:00:00 UTC';
SELECT DATETIME(CURRENT_TIMESTAMP(), 'America/Los_Angeles');
SELECT FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S %Z', ts, 'America/Chicago') AS local_ts;

-- Extract date in specific timezone
SELECT DATE(event_timestamp, 'America/Los_Angeles') AS local_date FROM events;

-- Critical: event timestamps in UTC, reporting in local time
SELECT
    user_id,
    event_timestamp AS utc_ts,
    DATETIME(event_timestamp, 'America/Los_Angeles') AS local_dt,
    DATE(event_timestamp, 'America/Los_Angeles') AS local_date
FROM web_events;
```

### Complex Date Patterns (Interview Favorites)

```sql
-- Fiscal year (e.g., Costco fiscal year ends in August)
SELECT
    sale_date,
    CASE
        WHEN EXTRACT(MONTH FROM sale_date) >= 9
        THEN EXTRACT(YEAR FROM sale_date) + 1
        ELSE EXTRACT(YEAR FROM sale_date)
    END AS fiscal_year,
    CASE
        WHEN EXTRACT(MONTH FROM sale_date) IN (9,10,11) THEN 1
        WHEN EXTRACT(MONTH FROM sale_date) IN (12,1,2) THEN 2
        WHEN EXTRACT(MONTH FROM sale_date) IN (3,4,5) THEN 3
        ELSE 4
    END AS fiscal_quarter
FROM sales;

-- Week-over-week comparison
SELECT
    DATE_TRUNC(event_date, WEEK) AS week_start,
    SUM(revenue) AS this_week_revenue,
    LAG(SUM(revenue)) OVER (ORDER BY DATE_TRUNC(event_date, WEEK)) AS last_week_revenue,
    SUM(revenue) - LAG(SUM(revenue)) OVER (ORDER BY DATE_TRUNC(event_date, WEEK)) AS wow_change
FROM daily_sales
GROUP BY week_start;

-- Same period last year comparison
SELECT
    this_year.month,
    this_year.revenue AS current_revenue,
    last_year.revenue AS prior_year_revenue,
    SAFE_DIVIDE(
        this_year.revenue - last_year.revenue,
        last_year.revenue
    ) * 100 AS yoy_growth_pct
FROM (
    SELECT DATE_TRUNC(sale_date, MONTH) AS month, SUM(revenue) AS revenue
    FROM sales WHERE EXTRACT(YEAR FROM sale_date) = 2024
    GROUP BY 1
) this_year
LEFT JOIN (
    SELECT DATE_TRUNC(sale_date, MONTH) AS month,
           DATE_ADD(DATE_TRUNC(sale_date, MONTH), INTERVAL 1 YEAR) AS comparison_month,
           SUM(revenue) AS revenue
    FROM sales WHERE EXTRACT(YEAR FROM sale_date) = 2023
    GROUP BY 1, 2
) last_year ON this_year.month = last_year.comparison_month;

-- Fill missing dates (generate date spine)
WITH date_spine AS (
    SELECT date
    FROM UNNEST(
        GENERATE_DATE_ARRAY(DATE '2024-01-01', CURRENT_DATE() - 1, INTERVAL 1 DAY)
    ) AS date
)
SELECT
    ds.date,
    COALESCE(s.revenue, 0) AS revenue,
    COALESCE(s.orders, 0) AS orders
FROM date_spine ds
LEFT JOIN daily_sales s ON ds.date = s.sale_date
ORDER BY ds.date;
```

---

## 8. JSON and Semi-Structured Data in SQL

### BigQuery JSON Functions

```sql
-- Sample: events table with JSON properties column
-- {"user_id": 123, "page": "/home", "campaign": {"id": "c1", "name": "Summer Sale"}, "tags": ["promo","new"]}

-- Extract scalar value
SELECT JSON_VALUE(properties, '$.user_id') AS user_id;
SELECT JSON_VALUE(properties, '$.campaign.id') AS campaign_id;
SELECT JSON_VALUE(properties, '$.campaign.name') AS campaign_name;

-- Extract as JSON (keeps nested structure)
SELECT JSON_QUERY(properties, '$.campaign') AS campaign_json;

-- Extract array element
SELECT JSON_VALUE(properties, '$.tags[0]') AS first_tag;

-- Extract all array elements
SELECT value
FROM events,
UNNEST(JSON_QUERY_ARRAY(properties, '$.tags')) AS value;

-- Check if key exists
SELECT
    JSON_VALUE(props, '$.user_id') IS NOT NULL AS has_user_id,
    ARRAY_LENGTH(JSON_QUERY_ARRAY(props, '$.tags')) > 0 AS has_tags
FROM events;

-- Parse JSON string into typed columns
SELECT
    event_id,
    CAST(JSON_VALUE(properties, '$.amount') AS FLOAT64) AS amount,
    CAST(JSON_VALUE(properties, '$.quantity') AS INT64) AS quantity,
    JSON_VALUE(properties, '$.currency') AS currency,
    DATE(JSON_VALUE(properties, '$.event_date')) AS event_date
FROM raw_events;
```

### Working with Nested / Repeated Fields (BigQuery Native)

```sql
-- Schema: orders with nested line_items ARRAY<STRUCT<product_id, qty, price>>
-- Unnest line items
SELECT
    o.order_id,
    o.customer_id,
    item.product_id,
    item.qty,
    item.price,
    item.qty * item.price AS line_total
FROM orders o,
UNNEST(o.line_items) AS item;

-- Aggregate back after unnesting
SELECT
    o.order_id,
    COUNT(item.product_id) AS num_items,
    SUM(item.qty * item.price) AS order_total
FROM orders o,
UNNEST(o.line_items) AS item
GROUP BY o.order_id;

-- Filter on nested field
SELECT DISTINCT o.order_id
FROM orders o,
UNNEST(o.line_items) AS item
WHERE item.product_id = 'PROD123';

-- CROSS JOIN UNNEST (explicit syntax)
SELECT o.order_id, item.product_id
FROM orders o
CROSS JOIN UNNEST(o.line_items) AS item;

-- LEFT JOIN UNNEST (keep orders with empty arrays)
SELECT o.order_id, item.product_id
FROM orders o
LEFT JOIN UNNEST(o.line_items) AS item;
```

---

## 9. Metric Creation from Raw Data

This section covers building production metrics — exactly what Costco's MarTech pipeline requires.

### Customer Lifetime Value (CLV/LTV)

```sql
-- Basic historical LTV
WITH customer_orders AS (
    SELECT
        customer_id,
        COUNT(DISTINCT order_id) AS total_orders,
        SUM(order_total) AS total_revenue,
        MIN(order_date) AS first_order_date,
        MAX(order_date) AS last_order_date,
        DATE_DIFF(MAX(order_date), MIN(order_date), DAY) AS customer_tenure_days
    FROM orders
    WHERE status != 'cancelled'
    GROUP BY customer_id
)
SELECT
    customer_id,
    total_orders,
    total_revenue,
    first_order_date,
    last_order_date,
    customer_tenure_days,
    SAFE_DIVIDE(total_revenue, total_orders) AS avg_order_value,
    SAFE_DIVIDE(total_orders, GREATEST(customer_tenure_days, 1)) * 365 AS orders_per_year,
    -- Simple LTV projection
    SAFE_DIVIDE(total_revenue, GREATEST(customer_tenure_days, 1)) * 365 AS annual_revenue_rate
FROM customer_orders;
```

### RFM Segmentation (Recency, Frequency, Monetary)

```sql
-- Critical MarTech metric used in CRM/CDP platforms
WITH rfm_raw AS (
    SELECT
        customer_id,
        DATE_DIFF(CURRENT_DATE(), MAX(order_date), DAY) AS recency_days,
        COUNT(DISTINCT order_id) AS frequency,
        SUM(order_total) AS monetary
    FROM orders
    WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
    GROUP BY customer_id
),
rfm_scored AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        monetary,
        NTILE(5) OVER (ORDER BY recency_days ASC) AS r_score,   -- Lower days = higher score
        NTILE(5) OVER (ORDER BY frequency DESC) AS f_score,      -- More orders = higher score
        NTILE(5) OVER (ORDER BY monetary DESC) AS m_score        -- More spend = higher score
    FROM rfm_raw
),
rfm_segments AS (
    SELECT
        *,
        r_score + f_score + m_score AS rfm_total,
        CAST(r_score AS STRING) || CAST(f_score AS STRING) || CAST(m_score AS STRING) AS rfm_code,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2 THEN 'Recent Customers'
            WHEN r_score >= 3 AND f_score <= 2 AND m_score >= 3 THEN 'Potential Loyalists'
            WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3 THEN 'At Risk'
            WHEN r_score <= 2 AND f_score >= 4 AND m_score >= 4 THEN 'Cannot Lose Them'
            WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost'
            ELSE 'About to Sleep'
        END AS segment
    FROM rfm_scored
)
SELECT
    segment,
    COUNT(*) AS customer_count,
    ROUND(AVG(monetary), 2) AS avg_monetary,
    ROUND(AVG(frequency), 2) AS avg_frequency,
    ROUND(AVG(recency_days), 0) AS avg_recency_days
FROM rfm_segments
GROUP BY segment
ORDER BY avg_monetary DESC;
```

### Funnel Analysis

```sql
-- E-commerce conversion funnel: impression → click → add_to_cart → purchase
WITH funnel_steps AS (
    SELECT
        session_id,
        user_id,
        campaign_id,
        MAX(CASE WHEN event_type = 'impression' THEN 1 ELSE 0 END) AS saw_impression,
        MAX(CASE WHEN event_type = 'click' THEN 1 ELSE 0 END) AS clicked,
        MAX(CASE WHEN event_type = 'add_to_cart' THEN 1 ELSE 0 END) AS added_to_cart,
        MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS purchased
    FROM clickstream_events
    WHERE event_date = CURRENT_DATE() - 1
    GROUP BY session_id, user_id, campaign_id
)
SELECT
    campaign_id,
    COUNT(*) AS total_sessions,
    SUM(saw_impression) AS impressions,
    SUM(clicked) AS clicks,
    SUM(added_to_cart) AS add_to_carts,
    SUM(purchased) AS purchases,
    -- Step-by-step conversion rates
    SAFE_DIVIDE(SUM(clicked), SUM(saw_impression)) AS ctr,
    SAFE_DIVIDE(SUM(added_to_cart), SUM(clicked)) AS cart_rate,
    SAFE_DIVIDE(SUM(purchased), SUM(added_to_cart)) AS checkout_rate,
    -- Overall funnel conversion
    SAFE_DIVIDE(SUM(purchased), SUM(saw_impression)) AS overall_cvr
FROM funnel_steps
GROUP BY campaign_id
ORDER BY purchases DESC;
```

### Cohort Analysis (Retention)

```sql
-- User retention cohort: what % of each signup cohort returns in weeks 1-8?
WITH cohorts AS (
    SELECT
        user_id,
        DATE_TRUNC(first_visit_date, WEEK) AS cohort_week
    FROM (
        SELECT
            user_id,
            MIN(event_date) AS first_visit_date
        FROM web_events
        GROUP BY user_id
    )
),
weekly_activity AS (
    SELECT
        c.user_id,
        c.cohort_week,
        DATE_TRUNC(e.event_date, WEEK) AS activity_week,
        DATE_DIFF(DATE_TRUNC(e.event_date, WEEK), c.cohort_week, WEEK) AS weeks_since_cohort
    FROM cohorts c
    JOIN web_events e ON c.user_id = e.user_id
),
cohort_sizes AS (
    SELECT cohort_week, COUNT(DISTINCT user_id) AS cohort_size
    FROM cohorts
    GROUP BY cohort_week
),
retention AS (
    SELECT
        wa.cohort_week,
        wa.weeks_since_cohort,
        COUNT(DISTINCT wa.user_id) AS retained_users
    FROM weekly_activity wa
    WHERE wa.weeks_since_cohort BETWEEN 0 AND 8
    GROUP BY wa.cohort_week, wa.weeks_since_cohort
)
SELECT
    r.cohort_week,
    cs.cohort_size,
    r.weeks_since_cohort,
    r.retained_users,
    ROUND(SAFE_DIVIDE(r.retained_users, cs.cohort_size) * 100, 2) AS retention_pct
FROM retention r
JOIN cohort_sizes cs ON r.cohort_week = cs.cohort_week
ORDER BY r.cohort_week, r.weeks_since_cohort;
```

---

## 10. AdTech / MarTech Metrics in SQL

### Core Ad Metrics

```sql
-- CTR, CPC, CPM, ROAS, CPA — all in one query
SELECT
    campaign_id,
    campaign_name,
    channel,
    SUM(impressions) AS total_impressions,
    SUM(clicks) AS total_clicks,
    SUM(spend) AS total_spend,
    SUM(conversions) AS total_conversions,
    SUM(revenue) AS total_revenue,

    -- CTR: Click-through rate
    ROUND(SAFE_DIVIDE(SUM(clicks), SUM(impressions)) * 100, 4) AS ctr_pct,

    -- CPC: Cost per click
    ROUND(SAFE_DIVIDE(SUM(spend), SUM(clicks)), 4) AS cpc,

    -- CPM: Cost per 1000 impressions
    ROUND(SAFE_DIVIDE(SUM(spend), SUM(impressions)) * 1000, 4) AS cpm,

    -- CPA: Cost per acquisition/conversion
    ROUND(SAFE_DIVIDE(SUM(spend), SUM(conversions)), 4) AS cpa,

    -- ROAS: Return on ad spend
    ROUND(SAFE_DIVIDE(SUM(revenue), SUM(spend)), 4) AS roas,

    -- CVR: Conversion rate (conversions / clicks)
    ROUND(SAFE_DIVIDE(SUM(conversions), SUM(clicks)) * 100, 4) AS cvr_pct,

    -- Revenue per click
    ROUND(SAFE_DIVIDE(SUM(revenue), SUM(clicks)), 4) AS rpc

FROM ad_performance
WHERE report_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) AND CURRENT_DATE() - 1
GROUP BY campaign_id, campaign_name, channel
HAVING SUM(impressions) > 1000  -- Filter low-volume
ORDER BY total_revenue DESC;
```

### Attribution Models

```sql
-- Last-touch attribution (simplest, most common)
WITH last_touch AS (
    SELECT
        conversion_id,
        user_id,
        conversion_value,
        -- Get the last touchpoint before conversion
        LAST_VALUE(channel) OVER (
            PARTITION BY user_id
            ORDER BY touchpoint_time
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS attributed_channel
    FROM conversion_touchpoints
    WHERE touchpoint_time <= conversion_time
)
SELECT
    attributed_channel,
    COUNT(DISTINCT conversion_id) AS conversions,
    SUM(conversion_value) AS attributed_revenue
FROM last_touch
GROUP BY attributed_channel;

-- First-touch attribution
WITH first_touch AS (
    SELECT
        conversion_id,
        user_id,
        conversion_value,
        FIRST_VALUE(channel) OVER (
            PARTITION BY user_id
            ORDER BY touchpoint_time
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS attributed_channel
    FROM conversion_touchpoints
)
SELECT
    attributed_channel,
    COUNT(DISTINCT conversion_id) AS conversions,
    SUM(conversion_value) AS attributed_revenue
FROM first_touch
WHERE attributed_channel IS NOT NULL
GROUP BY attributed_channel;

-- Linear attribution (equal credit to all touchpoints)
WITH touchpoint_counts AS (
    SELECT
        user_id,
        channel,
        conversion_id,
        conversion_value,
        COUNT(*) OVER (PARTITION BY conversion_id) AS total_touchpoints
    FROM conversion_touchpoints
)
SELECT
    channel,
    SUM(1.0 / total_touchpoints) AS attributed_conversions,
    SUM(conversion_value / total_touchpoints) AS attributed_revenue
FROM touchpoint_counts
GROUP BY channel;

-- Time-decay attribution (more credit to recent touchpoints)
WITH time_decayed AS (
    SELECT
        user_id,
        channel,
        conversion_id,
        conversion_value,
        touchpoint_time,
        conversion_time,
        TIMESTAMP_DIFF(conversion_time, touchpoint_time, HOUR) AS hours_before_conversion,
        -- Half-life of 7 days (168 hours)
        POW(0.5, TIMESTAMP_DIFF(conversion_time, touchpoint_time, HOUR) / 168.0) AS decay_weight
    FROM conversion_touchpoints
),
weights_normalized AS (
    SELECT
        *,
        decay_weight / SUM(decay_weight) OVER (PARTITION BY conversion_id) AS normalized_weight
    FROM time_decayed
)
SELECT
    channel,
    SUM(normalized_weight) AS attributed_conversions,
    SUM(conversion_value * normalized_weight) AS attributed_revenue
FROM weights_normalized
GROUP BY channel;
```

### Member Analytics (Costco-Specific)

```sql
-- Membership renewal / churn prediction signals
WITH member_activity AS (
    SELECT
        member_id,
        membership_type,
        renewal_date,
        DATE_DIFF(renewal_date, CURRENT_DATE(), DAY) AS days_to_renewal,
        last_visit_date,
        DATE_DIFF(CURRENT_DATE(), last_visit_date, DAY) AS days_since_last_visit,
        COUNT(DISTINCT visit_date) AS visits_last_12m,
        SUM(purchase_amount) AS spend_last_12m,
        COUNT(DISTINCT purchase_category) AS category_breadth
    FROM member_visits
    WHERE visit_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
    GROUP BY member_id, membership_type, renewal_date, last_visit_date
)
SELECT
    member_id,
    membership_type,
    days_to_renewal,
    visits_last_12m,
    spend_last_12m,
    -- Engagement score
    CASE
        WHEN visits_last_12m >= 24 AND spend_last_12m >= 1000 THEN 'High'
        WHEN visits_last_12m >= 12 AND spend_last_12m >= 500 THEN 'Medium'
        ELSE 'Low'
    END AS engagement_tier,
    -- Churn risk
    CASE
        WHEN days_since_last_visit > 90 AND days_to_renewal < 60 THEN 'High Risk'
        WHEN days_since_last_visit > 60 AND days_to_renewal < 90 THEN 'Medium Risk'
        ELSE 'Low Risk'
    END AS churn_risk
FROM member_activity;
```

---

## 11. Advanced Joins — All Patterns

### Join Types Reference

```sql
-- INNER JOIN: only matching rows
SELECT a.*, b.* FROM a INNER JOIN b ON a.id = b.a_id;

-- LEFT JOIN: all rows from left, nulls for unmatched right
SELECT a.*, b.* FROM a LEFT JOIN b ON a.id = b.a_id;

-- RIGHT JOIN: all rows from right, nulls for unmatched left
SELECT a.*, b.* FROM a RIGHT JOIN b ON a.id = b.a_id;

-- FULL OUTER JOIN: all rows from both, nulls where no match
SELECT a.*, b.* FROM a FULL OUTER JOIN b ON a.id = b.a_id;

-- CROSS JOIN: cartesian product
SELECT a.*, b.* FROM a CROSS JOIN b;  -- All combinations

-- SELF JOIN: join table to itself
SELECT
    e.name AS employee,
    m.name AS manager
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.employee_id;
```

### Anti-Joins and Semi-Joins

```sql
-- Anti-join: rows in A with NO match in B
-- Pattern 1: LEFT JOIN + IS NULL
SELECT a.*
FROM a
LEFT JOIN b ON a.id = b.a_id
WHERE b.a_id IS NULL;

-- Pattern 2: NOT EXISTS (often more readable)
SELECT * FROM customers c
WHERE NOT EXISTS (
    SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id
);

-- Pattern 3: NOT IN (CAUTION: fails if subquery returns any NULL)
SELECT * FROM customers
WHERE customer_id NOT IN (
    SELECT DISTINCT customer_id FROM orders WHERE customer_id IS NOT NULL
);

-- Semi-join: check existence without duplicating rows
SELECT DISTINCT c.*
FROM customers c
WHERE EXISTS (
    SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id
    AND o.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
);
```

### Non-Equi Joins

```sql
-- Join on range (lookup salary bands)
SELECT
    e.name,
    e.salary,
    b.band_name,
    b.min_salary,
    b.max_salary
FROM employees e
JOIN salary_bands b
    ON e.salary BETWEEN b.min_salary AND b.max_salary;

-- Slowly Changing Dimension (SCD Type 2) lookup
-- Get the product price that was in effect at time of sale
SELECT
    s.sale_id,
    s.sale_date,
    s.product_id,
    p.price AS price_at_sale_time
FROM sales s
JOIN product_price_history p
    ON s.product_id = p.product_id
    AND s.sale_date BETWEEN p.effective_from AND p.effective_to;

-- Find rows where date falls within another table's range
SELECT
    v.visit_id,
    v.member_id,
    v.visit_date,
    p.promotion_name
FROM visits v
LEFT JOIN promotions p
    ON v.visit_date BETWEEN p.start_date AND p.end_date;
```

### Handling Fan-out in Joins (Duplicate Row Problem)

```sql
-- Problem: joining two tables that both have multiple rows per key
-- customers → orders (1:many) → order_items (1:many)
-- Naive join will multiply rows

-- WRONG approach (row multiplication):
SELECT c.customer_id, SUM(o.amount) AS revenue, SUM(oi.quantity) AS items
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.customer_id;
-- SUM(o.amount) is inflated because order rows repeat for each item!

-- CORRECT approach: aggregate before joining
WITH order_totals AS (
    SELECT order_id, SUM(quantity) AS total_items
    FROM order_items
    GROUP BY order_id
),
customer_orders AS (
    SELECT customer_id, SUM(amount) AS revenue, COUNT(*) AS num_orders
    FROM orders
    GROUP BY customer_id
)
SELECT
    c.customer_id,
    co.revenue,
    co.num_orders,
    SUM(ot.total_items) AS total_items_purchased
FROM customers c
LEFT JOIN customer_orders co ON c.customer_id = co.customer_id
LEFT JOIN orders o ON c.customer_id = o.customer_id
LEFT JOIN order_totals ot ON o.order_id = ot.order_id
GROUP BY c.customer_id, co.revenue, co.num_orders;
```

---

## 12. Performance Optimization for BigQuery SQL

### Partitioning and Clustering Strategies

```sql
-- Create partitioned + clustered table
CREATE TABLE analytics.events_optimized
PARTITION BY DATE(event_timestamp)
CLUSTER BY user_id, event_type
OPTIONS (
    partition_expiration_days = 365,
    require_partition_filter = TRUE  -- Force queries to specify partition
)
AS SELECT * FROM raw.events;

-- Query that leverages partition pruning
SELECT COUNT(*), SUM(revenue)
FROM analytics.events_optimized
WHERE DATE(event_timestamp) BETWEEN '2024-01-01' AND '2024-01-31'  -- partition filter
  AND event_type = 'purchase'  -- cluster filter
  AND user_id IN (SELECT user_id FROM target_segment);  -- cluster filter
```

### Avoiding Full Scans

```sql
-- BAD: Functions on partitioned column defeat pruning
SELECT * FROM events WHERE EXTRACT(YEAR FROM event_timestamp) = 2024;  -- ❌ Full scan!

-- GOOD: Direct date comparison
SELECT * FROM events
WHERE event_timestamp >= '2024-01-01' AND event_timestamp < '2025-01-01';  -- ✅

-- BAD: Wildcard leading character
SELECT * FROM events WHERE event_type LIKE '%click%';  -- ❌ Full scan

-- GOOD: Specific prefix or use clustering
SELECT * FROM events WHERE event_type IN ('page_click', 'button_click', 'ad_click');
```

### Reducing Data Processed

```sql
-- Use column selection (avoid SELECT *)
SELECT event_id, user_id, event_type, revenue  -- name columns explicitly
FROM events
WHERE DATE(event_timestamp) = CURRENT_DATE() - 1;

-- Approximate functions for large datasets
SELECT
    APPROX_COUNT_DISTINCT(user_id) AS approx_unique_users,  -- Much faster than COUNT(DISTINCT)
    APPROX_QUANTILES(revenue, 100)[OFFSET(50)] AS median_revenue,
    APPROX_TOP_COUNT(event_type, 5) AS top_5_event_types
FROM events
WHERE DATE(event_timestamp) = CURRENT_DATE() - 1;

-- Materialize intermediate results as temp tables for multi-use
CREATE TEMP TABLE daily_sessions AS
SELECT
    user_id,
    session_id,
    MIN(event_timestamp) AS session_start,
    MAX(event_timestamp) AS session_end,
    COUNT(*) AS event_count
FROM events
WHERE DATE(event_timestamp) = CURRENT_DATE() - 1
GROUP BY user_id, session_id;

-- Now use daily_sessions multiple times without recomputing
SELECT * FROM daily_sessions WHERE event_count > 10;
SELECT user_id, COUNT(*) FROM daily_sessions GROUP BY user_id;
```

### Optimizing Joins in BigQuery

```sql
-- Broadcast join: put small table on right side
-- BigQuery auto-broadcasts tables < 10MB, but you can hint

-- Avoid joining in WHERE clause (forces CROSS JOIN then filter)
-- BAD:
SELECT * FROM a, b WHERE a.id = b.id;  -- ❌ Cross join syntax

-- GOOD:
SELECT * FROM a JOIN b ON a.id = b.id;  -- ✅

-- Pre-filter before joining
WITH filtered_orders AS (
    SELECT * FROM orders
    WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
      AND status = 'completed'
)
SELECT c.*, fo.*
FROM customers c
JOIN filtered_orders fo ON c.customer_id = fo.customer_id;

-- Use INT64 keys instead of STRING for joins (much faster)
-- If you must join on STRING, normalize case first
SELECT a.*, b.*
FROM table_a a
JOIN table_b b ON UPPER(TRIM(a.str_key)) = UPPER(TRIM(b.str_key));
```

---

## 13. SQL Anti-Patterns & Debugging

### Common Anti-Patterns

```sql
-- ANTI-PATTERN 1: Correlated subquery in SELECT (O(n^2) complexity)
-- BAD:
SELECT
    c.customer_id,
    (SELECT SUM(amount) FROM orders o WHERE o.customer_id = c.customer_id) AS total_spend
FROM customers c;

-- GOOD: Use LEFT JOIN with aggregation
SELECT c.customer_id, COALESCE(o.total_spend, 0)
FROM customers c
LEFT JOIN (
    SELECT customer_id, SUM(amount) AS total_spend FROM orders GROUP BY customer_id
) o ON c.customer_id = o.customer_id;

-- ANTI-PATTERN 2: NOT IN with nullable subquery
-- BAD (silent data loss if orders has NULL customer_ids):
SELECT * FROM customers WHERE customer_id NOT IN (SELECT customer_id FROM orders);

-- GOOD:
SELECT * FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id);

-- ANTI-PATTERN 3: Division without null guard
-- BAD:
SELECT clicks / impressions AS ctr FROM ad_stats;  -- Fails on zero impressions

-- GOOD:
SELECT SAFE_DIVIDE(clicks, impressions) AS ctr FROM ad_stats;
-- OR:
SELECT clicks / NULLIF(impressions, 0) AS ctr FROM ad_stats;

-- ANTI-PATTERN 4: DISTINCT to hide join problems
-- BAD (DISTINCT masks fan-out bug):
SELECT DISTINCT customer_id, SUM(revenue) FROM customers c JOIN orders o ...
-- This might still double-count revenue

-- GOOD: Understand the join cardinality and fix it at the root

-- ANTI-PATTERN 5: String date comparison
-- BAD:
SELECT * FROM events WHERE event_date > '2024-01-01';  -- String comparison!

-- GOOD:
SELECT * FROM events WHERE event_date > DATE '2024-01-01';
```

### Debugging Queries

```sql
-- Debug step 1: Verify row counts at each join stage
SELECT COUNT(*) FROM table_a;              -- 100,000
SELECT COUNT(*) FROM table_b;              -- 50,000
SELECT COUNT(*) FROM table_a a JOIN table_b b ON a.id = b.a_id;  -- Expected: ≤ 100,000

-- If result > table_a row count, there are duplicates in table_b on join key
-- Investigate:
SELECT a_id, COUNT(*) FROM table_b GROUP BY a_id ORDER BY COUNT(*) DESC LIMIT 20;

-- Debug step 2: Check for unexpected nulls after join
SELECT
    COUNT(*) AS total,
    COUNTIF(b.some_column IS NULL) AS null_after_join,
    COUNTIF(b.some_column IS NOT NULL) AS matched
FROM table_a a
LEFT JOIN table_b b ON a.id = b.a_id;

-- Debug step 3: Validate aggregation sums
SELECT SUM(revenue) FROM orders;  -- Should match source system
SELECT SUM(revenue) FROM orders_joined_version;  -- Should be same

-- Debug step 4: Sample problematic rows
SELECT * FROM (
    SELECT *, COUNT(*) OVER (PARTITION BY customer_id) AS cnt
    FROM customer_data
)
WHERE cnt > 1
LIMIT 100;
```

---

## 14. Practice Problems — Graded Complexity

### Level 1: Foundational

**Q1: Find customers who placed more than 5 orders in the last 30 days.**
```sql
SELECT customer_id, COUNT(DISTINCT order_id) AS order_count
FROM orders
WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY customer_id
HAVING COUNT(DISTINCT order_id) > 5
ORDER BY order_count DESC;
```

**Q2: Get the second highest revenue product.**
```sql
SELECT product_id, SUM(revenue) AS total_revenue
FROM sales
GROUP BY product_id
ORDER BY total_revenue DESC
LIMIT 1 OFFSET 1;
-- OR using DENSE_RANK:
SELECT product_id, total_revenue
FROM (
    SELECT product_id, SUM(revenue) AS total_revenue,
           DENSE_RANK() OVER (ORDER BY SUM(revenue) DESC) AS rnk
    FROM sales GROUP BY product_id
)
WHERE rnk = 2;
```

### Level 2: Intermediate

**Q3: Calculate 7-day rolling average daily revenue per campaign.**
```sql
SELECT
    campaign_id,
    report_date,
    daily_revenue,
    AVG(daily_revenue) OVER (
        PARTITION BY campaign_id
        ORDER BY UNIX_DATE(report_date)
        RANGE BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7d_avg
FROM daily_campaign_performance
ORDER BY campaign_id, report_date;
```

**Q4: Find users who clicked on an ad but never made a purchase.**
```sql
SELECT DISTINCT c.user_id
FROM clicks c
WHERE NOT EXISTS (
    SELECT 1 FROM purchases p
    WHERE p.user_id = c.user_id
);
```

**Q5: For each product category, find the top 2 best-selling products.**
```sql
WITH ranked AS (
    SELECT
        category,
        product_id,
        SUM(units_sold) AS total_units,
        ROW_NUMBER() OVER (PARTITION BY category ORDER BY SUM(units_sold) DESC) AS rn
    FROM sales
    GROUP BY category, product_id
)
SELECT category, product_id, total_units
FROM ranked
WHERE rn <= 2;
```

### Level 3: Advanced

**Q6: Sessionize user clickstream events (30-min inactivity = new session) and calculate avg session duration per campaign.**
```sql
WITH gaps AS (
    SELECT
        user_id, event_time, campaign_id,
        CASE
            WHEN TIMESTAMP_DIFF(event_time,
                 LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time),
                 MINUTE) > 30
            OR LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time) IS NULL
            THEN 1 ELSE 0
        END AS new_session
    FROM clickstream
),
sessions AS (
    SELECT
        user_id, event_time, campaign_id,
        SUM(new_session) OVER (PARTITION BY user_id ORDER BY event_time) AS session_id
    FROM gaps
),
session_agg AS (
    SELECT
        user_id, session_id,
        MAX(campaign_id) AS campaign_id,  -- attribute to dominant campaign
        MIN(event_time) AS session_start,
        MAX(event_time) AS session_end,
        TIMESTAMP_DIFF(MAX(event_time), MIN(event_time), SECOND) AS duration_sec
    FROM sessions
    GROUP BY user_id, session_id
)
SELECT
    campaign_id,
    COUNT(*) AS total_sessions,
    ROUND(AVG(duration_sec) / 60, 2) AS avg_session_duration_min
FROM session_agg
WHERE campaign_id IS NOT NULL
GROUP BY campaign_id
ORDER BY avg_session_duration_min DESC;
```

**Q7: Build a 12-week retention cohort table showing what % of each signup cohort returned each week.**
```sql
WITH first_visits AS (
    SELECT user_id, MIN(DATE_TRUNC(event_date, WEEK)) AS cohort_week
    FROM events GROUP BY user_id
),
weekly_visits AS (
    SELECT DISTINCT user_id, DATE_TRUNC(event_date, WEEK) AS visit_week
    FROM events
),
joined AS (
    SELECT
        fv.user_id,
        fv.cohort_week,
        wv.visit_week,
        DATE_DIFF(wv.visit_week, fv.cohort_week, WEEK) AS week_number
    FROM first_visits fv
    JOIN weekly_visits wv ON fv.user_id = wv.user_id
    WHERE DATE_DIFF(wv.visit_week, fv.cohort_week, WEEK) BETWEEN 0 AND 12
),
cohort_size AS (
    SELECT cohort_week, COUNT(*) AS size FROM first_visits GROUP BY cohort_week
)
SELECT
    j.cohort_week,
    cs.size AS cohort_size,
    j.week_number,
    COUNT(DISTINCT j.user_id) AS retained,
    ROUND(COUNT(DISTINCT j.user_id) / cs.size * 100, 2) AS retention_pct
FROM joined j
JOIN cohort_size cs ON j.cohort_week = cs.cohort_week
GROUP BY j.cohort_week, cs.size, j.week_number
ORDER BY j.cohort_week, j.week_number;
```

**Q8: Implement time-decay attribution model and compare to last-touch for each campaign.**
```sql
WITH all_touchpoints AS (
    SELECT
        t.user_id, t.channel, t.campaign_id, t.touchpoint_time,
        c.conversion_id, c.conversion_time, c.revenue,
        TIMESTAMP_DIFF(c.conversion_time, t.touchpoint_time, HOUR) AS hours_before,
        POW(0.5, TIMESTAMP_DIFF(c.conversion_time, t.touchpoint_time, HOUR) / 168.0) AS decay_weight
    FROM touchpoints t
    JOIN conversions c ON t.user_id = c.user_id
    WHERE t.touchpoint_time <= c.conversion_time
),
normalized AS (
    SELECT *,
        decay_weight / SUM(decay_weight) OVER (PARTITION BY conversion_id) AS td_weight,
        ROW_NUMBER() OVER (PARTITION BY conversion_id ORDER BY touchpoint_time DESC) = 1 AS is_last_touch
    FROM all_touchpoints
)
SELECT
    campaign_id,
    SUM(td_weight) AS time_decay_conversions,
    SUM(revenue * td_weight) AS time_decay_revenue,
    SUM(CASE WHEN is_last_touch THEN 1 ELSE 0 END) AS last_touch_conversions,
    SUM(CASE WHEN is_last_touch THEN revenue ELSE 0 END) AS last_touch_revenue
FROM normalized
GROUP BY campaign_id
ORDER BY time_decay_revenue DESC;
```

---

## Quick Reference: Interview Cheat Sheet

### Top 10 Most-Asked SQL Patterns

| Pattern | Key Function(s) |
|---------|----------------|
| Top N per group | `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)` |
| Running total | `SUM() OVER (ORDER BY date)` |
| MoM / WoW change | `LAG()` |
| De-duplicate | `ROW_NUMBER() + WHERE rn = 1` |
| Sessionize events | `SUM(new_session_flag) OVER (PARTITION BY user_id ORDER BY time)` |
| Funnel analysis | `MAX(CASE WHEN event_type = 'X' THEN 1 ELSE 0 END)` |
| Date spine | `GENERATE_DATE_ARRAY` + LEFT JOIN |
| Cohort retention | `DATE_DIFF()` + conditional aggregation |
| Multi-period compare | CASE WHEN inside SUM |
| Attribution | Window functions + decay weights |

### Critical BigQuery-Specific Functions

| Function | Use Case |
|----------|----------|
| `SAFE_DIVIDE(a, b)` | Null-safe division |
| `SAFE_CAST(x AS TYPE)` | Null-safe type cast |
| `DATE_DIFF(d1, d2, PART)` | Date arithmetic |
| `GENERATE_DATE_ARRAY(s, e, INTERVAL)` | Date spine |
| `APPROX_COUNT_DISTINCT()` | Fast distinct count |
| `COUNTIF(condition)` | Conditional count |
| `QUALIFY` | Filter on window functions inline |
| `EXCEPT` | Remove columns: `SELECT * EXCEPT(col1)` |
| `UNNEST()` | Flatten arrays |
| `JSON_VALUE(col, '$.path')` | Extract from JSON |
| `STRING_AGG()` | Aggregate strings |
| `ARRAY_AGG()` | Aggregate into array |
| `FORMAT_DATE()` | Date to string |
| `DATE_TRUNC()` | Floor to period |
| `TIMESTAMP_TRUNC()` | Floor timestamp |
