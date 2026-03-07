# SQL & Data Modelling — Complete Textbook
### Advanced SQL, BigQuery-Specific Syntax, and Data Modelling for Senior Data Engineers

---

## CHAPTER 1: SQL EXECUTION ORDER

### 1.1 Written Order vs Execution Order

SQL is written in one order but executed in a completely different order. This is the most important foundational concept.

**Written order:** SELECT → FROM → JOIN → WHERE → GROUP BY → HAVING → ORDER BY → LIMIT

**Execution order:**
```
1. FROM           -- identify source tables
2. JOIN           -- combine tables
3. WHERE          -- filter rows (before aggregation)
4. GROUP BY       -- group remaining rows
5. HAVING         -- filter groups (after aggregation)
6. SELECT         -- compute output expressions
7. DISTINCT       -- remove duplicates
8. ORDER BY       -- sort
9. LIMIT/OFFSET   -- return subset
```

**Why this matters:**
```sql
-- FAILS: WHERE executes before SELECT — alias 'total' doesn't exist yet
SELECT customer_id, SUM(amount) AS total
FROM orders
WHERE total > 1000;              -- ERROR

-- CORRECT: HAVING executes after GROUP BY
SELECT customer_id, SUM(amount) AS total
FROM orders
GROUP BY customer_id
HAVING SUM(amount) > 1000;

-- BigQuery QUALIFY: executes after window functions — unique to BigQuery
SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn
FROM orders
QUALIFY rn = 1;   -- filter on window result directly
```

---

## CHAPTER 2: WINDOW FUNCTIONS

### 2.1 Anatomy

```sql
function_name() OVER (
    PARTITION BY col1, col2    -- divide into groups
    ORDER BY col3 DESC         -- order within group
    ROWS BETWEEN ... AND ...   -- frame definition (optional)
)
```
Window functions compute over a "window" of rows related to the current row — without collapsing rows like GROUP BY.

### 2.2 Ranking Functions

```sql
SELECT
    customer_id, order_date, amount,
    ROW_NUMBER()  OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn,
    -- unique sequential: 1, 2, 3, 4
    RANK()        OVER (PARTITION BY customer_id ORDER BY amount DESC)     AS rnk,
    -- ties share rank, next skips: 1, 1, 3, 4
    DENSE_RANK()  OVER (PARTITION BY customer_id ORDER BY amount DESC)     AS dense_rnk,
    -- ties share rank, no skip: 1, 1, 2, 3
    NTILE(4)      OVER (PARTITION BY region ORDER BY amount DESC)          AS quartile
FROM orders;

-- Most common use: latest record per entity
SELECT * FROM orders
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC) = 1;
```

### 2.3 Aggregate Window Functions

```sql
SELECT
    customer_id, order_date, amount,

    -- Running total
    SUM(amount) OVER (
        PARTITION BY customer_id ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_total,

    -- 7-row moving average
    AVG(amount) OVER (
        PARTITION BY customer_id ORDER BY order_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS moving_avg_7,

    -- Percentage of customer's total
    ROUND(amount / SUM(amount) OVER (PARTITION BY customer_id) * 100, 2) AS pct_of_total,

    -- Full partition aggregate (all rows, no order needed)
    MAX(amount) OVER (PARTITION BY customer_id) AS customer_max_order

FROM orders;
```

### 2.4 LAG and LEAD

```sql
SELECT
    customer_id, order_date, amount,

    LAG(amount, 1, 0) OVER (PARTITION BY customer_id ORDER BY order_date) AS prev_amount,
    LEAD(amount, 1)   OVER (PARTITION BY customer_id ORDER BY order_date) AS next_amount,

    -- Change from previous
    amount - LAG(amount, 1, amount) OVER (PARTITION BY customer_id ORDER BY order_date)
        AS amount_delta,

    -- Days since last order
    DATE_DIFF(
        order_date,
        LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date),
        DAY
    ) AS days_since_last,

    FIRST_VALUE(amount) OVER (
        PARTITION BY customer_id ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS first_order_amount

FROM orders;
```

### 2.5 Frame Clauses

```sql
-- ROWS: counts physical rows
-- RANGE: counts rows with same ORDER BY value (handles ties)

-- Exactly 3 preceding rows
AVG(amount) OVER (ORDER BY order_date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)

-- All rows within a 3-day interval (handles date gaps)
AVG(amount) OVER (ORDER BY order_date RANGE BETWEEN INTERVAL 2 DAY PRECEDING AND CURRENT ROW)

-- Frame shortcuts:
-- UNBOUNDED PRECEDING AND CURRENT ROW → running total
-- UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING → full partition aggregate
-- n PRECEDING AND n FOLLOWING → centered moving window
```

---

## CHAPTER 3: CTEs AND RECURSIVE QUERIES

### 3.1 Common Table Expressions

```sql
WITH
monthly_sales AS (
    SELECT
        DATE_TRUNC(order_date, MONTH) AS month,
        customer_id,
        SUM(amount) AS total
    FROM orders
    WHERE order_date >= '2024-01-01'
    GROUP BY 1, 2
),
customer_tiers AS (
    SELECT
        customer_id,
        AVG(total) AS avg_monthly_spend,
        CASE
            WHEN AVG(total) >= 10000 THEN 'PLATINUM'
            WHEN AVG(total) >= 5000  THEN 'GOLD'
            WHEN AVG(total) >= 1000  THEN 'SILVER'
            ELSE 'BRONZE'
        END AS tier
    FROM monthly_sales
    GROUP BY customer_id
)
SELECT tier, COUNT(*) AS customers, ROUND(AVG(avg_monthly_spend), 2) AS avg_spend
FROM customer_tiers
GROUP BY tier ORDER BY avg_spend DESC;
```

### 3.2 Recursive CTEs

```sql
-- Org chart traversal: all reports under a manager
WITH RECURSIVE org_hierarchy AS (

    -- Base case
    SELECT employee_id, name, manager_id, 1 AS level,
           CAST(name AS STRING) AS path
    FROM employees
    WHERE employee_id = 'MGR001'

    UNION ALL

    -- Recursive step
    SELECT e.employee_id, e.name, e.manager_id,
           h.level + 1,
           CONCAT(h.path, ' > ', e.name)
    FROM employees e
    JOIN org_hierarchy h ON e.manager_id = h.employee_id
    WHERE h.level < 10  -- safety limit
)
SELECT * FROM org_hierarchy ORDER BY level, name;

-- Data lineage: find all upstream tables
WITH RECURSIVE lineage AS (
    SELECT source_table, target_table, 1 AS depth
    FROM pipeline_lineage
    WHERE target_table = 'fact_orders'

    UNION ALL

    SELECT dl.source_table, dl.target_table, l.depth + 1
    FROM pipeline_lineage dl
    JOIN lineage l ON dl.target_table = l.source_table
    WHERE l.depth < 20
)
SELECT DISTINCT source_table, depth FROM lineage ORDER BY depth;
```

---

## CHAPTER 4: JOINS AND SET OPERATIONS

### 4.1 Join Types

```sql
-- INNER: only matching rows
SELECT o.order_id, c.name
FROM orders o JOIN customers c ON o.customer_id = c.customer_id;

-- LEFT: all from left, NULLs for unmatched right
SELECT c.customer_id, COUNT(o.order_id) AS orders
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id;

-- Anti-join: customers with NO orders
SELECT c.customer_id
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE o.customer_id IS NULL;

-- FULL OUTER: all rows from both
SELECT COALESCE(a.id, b.id) AS id, a.jan_amount, b.feb_amount
FROM jan_orders a FULL OUTER JOIN feb_orders b ON a.id = b.id;

-- SELF JOIN: compare rows within same table
SELECT a.name AS employee, b.name AS manager
FROM employees a LEFT JOIN employees b ON a.manager_id = b.employee_id;

-- Non-equi join: range condition
SELECT t.tx_id, b.tax_rate
FROM transactions t
JOIN tax_bands b ON t.amount BETWEEN b.low AND b.high;
```

### 4.2 Set Operations

```sql
-- UNION ALL: all rows (keep duplicates, faster)
SELECT id, 'JAN' AS src FROM jan_customers
UNION ALL
SELECT id, 'FEB' AS src FROM feb_customers;

-- INTERSECT: rows in both
SELECT id FROM jan_customers
INTERSECT DISTINCT
SELECT id FROM feb_customers;

-- EXCEPT: in first but not second (churned customers)
SELECT id FROM jan_customers
EXCEPT DISTINCT
SELECT id FROM feb_customers;
```

---

## CHAPTER 5: ADVANCED PATTERNS

### 5.1 Gaps and Islands

```sql
-- Find contiguous active periods per customer
WITH numbered AS (
    SELECT customer_id, activity_date,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY activity_date) AS rn
    FROM activity_log
),
grouped AS (
    SELECT customer_id, activity_date,
           DATE_SUB(activity_date, INTERVAL rn DAY) AS island_id
    FROM numbered
)
SELECT
    customer_id,
    MIN(activity_date) AS period_start,
    MAX(activity_date) AS period_end,
    COUNT(*)           AS days_active
FROM grouped
GROUP BY customer_id, island_id
ORDER BY customer_id, period_start;
```

### 5.2 Pivot and Unpivot

```sql
-- Pivot: rows → columns (conditional aggregation)
SELECT
    region,
    SUM(CASE WHEN EXTRACT(MONTH FROM order_date) = 1  THEN amount ELSE 0 END) AS jan,
    SUM(CASE WHEN EXTRACT(MONTH FROM order_date) = 2  THEN amount ELSE 0 END) AS feb,
    SUM(CASE WHEN EXTRACT(MONTH FROM order_date) = 3  THEN amount ELSE 0 END) AS mar
FROM orders
WHERE EXTRACT(YEAR FROM order_date) = 2024
GROUP BY region;

-- Unpivot: columns → rows (BigQuery syntax)
SELECT region, month_name, amount
FROM monthly_wide
UNPIVOT (amount FOR month_name IN (jan, feb, mar, apr));
```

### 5.3 Date Spine

```sql
-- Generate complete date range and fill gaps
WITH date_spine AS (
    SELECT DATE_ADD('2024-01-01', INTERVAL n DAY) AS dt
    FROM UNNEST(GENERATE_ARRAY(0, 364)) AS n
),
daily_sales AS (
    SELECT DATE(order_date) AS dt, SUM(amount) AS total
    FROM orders WHERE EXTRACT(YEAR FROM order_date) = 2024
    GROUP BY 1
)
SELECT d.dt, COALESCE(s.total, 0) AS daily_total
FROM date_spine d
LEFT JOIN daily_sales s ON d.dt = s.dt
ORDER BY d.dt;
```

---

## CHAPTER 6: BIGQUERY-SPECIFIC SQL

### 6.1 Arrays and Structs

```sql
-- ARRAY_AGG: aggregate rows into array
SELECT customer_id,
       ARRAY_AGG(product_id ORDER BY order_date) AS purchase_history,
       ARRAY_AGG(DISTINCT product_id) AS unique_products
FROM order_items GROUP BY customer_id;

-- UNNEST: explode array into rows
SELECT customer_id, product_id
FROM customers, UNNEST(purchase_history) AS product_id;

-- STRUCT: named record
SELECT customer_id,
       STRUCT(first_name AS first, last_name AS last) AS name,
       address.city   -- dot notation to access struct field
FROM customers;

-- GENERATE_ARRAY + UNNEST
SELECT n FROM UNNEST(GENERATE_ARRAY(1, 100)) AS n;

SELECT d FROM UNNEST(
    GENERATE_DATE_ARRAY('2024-01-01', '2024-12-31', INTERVAL 1 WEEK)
) AS d;
```

### 6.2 MERGE (Upsert)

```sql
MERGE INTO dim_customer T
USING staging_customer S
ON T.customer_id = S.customer_id

WHEN MATCHED AND T.updated_at < S.updated_at THEN
    UPDATE SET T.name = S.name, T.email = S.email, T.updated_at = S.updated_at

WHEN NOT MATCHED BY TARGET THEN
    INSERT (customer_id, name, email, created_at, updated_at)
    VALUES (S.customer_id, S.name, S.email, S.created_at, S.updated_at)

WHEN NOT MATCHED BY SOURCE THEN
    UPDATE SET T.is_active = FALSE;
```

### 6.3 QUALIFY

```sql
-- Get latest record per customer (cleaner than subquery)
SELECT *
FROM customers
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC) = 1;

-- Top 3 products per category
SELECT product_id, category, SUM(amount) AS revenue
FROM order_items
GROUP BY product_id, category
QUALIFY RANK() OVER (PARTITION BY category ORDER BY SUM(amount) DESC) <= 3;
```

### 6.4 Performance Patterns

```sql
-- Partition pruning: always filter on partition column
SELECT * FROM orders
WHERE order_date BETWEEN '2024-01-01' AND '2024-03-31'  -- hits only 3 partitions
  AND region = 'APAC';

-- Avoid functions on partition column (disables pruning)
-- BAD:
WHERE DATE(order_timestamp) = '2024-01-15'
-- GOOD:
WHERE order_timestamp BETWEEN '2024-01-15 00:00:00' AND '2024-01-15 23:59:59'

-- Select only needed columns (reduces bytes scanned)
SELECT customer_id, amount FROM orders  -- not SELECT *

-- APPROX functions for large-scale analytics
SELECT APPROX_COUNT_DISTINCT(customer_id) AS uniq_customers  -- 100x faster, ~1% error
FROM orders;

-- SAFE functions to handle errors gracefully
SELECT SAFE_DIVIDE(revenue, orders) AS avg_order_value,
       SAFE_CAST(price_str AS FLOAT64) AS price
FROM stats;

-- Wildcard tables for date-sharded tables
SELECT * FROM `project.dataset.orders_*`
WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240331';

-- Materialized views for repeated aggregations
CREATE MATERIALIZED VIEW daily_summary AS
SELECT DATE(order_date) AS dt, region, SUM(amount) AS total
FROM orders GROUP BY 1, 2;
```

---

## CHAPTER 7: QUERY OPTIMISATION

### 7.1 BigQuery Optimisation Principles

```sql
-- 1. Filter early — reduce data before joining
WITH filtered AS (
    SELECT customer_id, SUM(amount) AS total
    FROM orders
    WHERE order_date >= '2024-01-01' AND status = 'COMPLETED'
    GROUP BY customer_id
)
SELECT c.name, f.total
FROM customers c JOIN filtered f ON c.customer_id = f.customer_id;

-- 2. Clustered + partitioned tables — filter on both
-- Table: PARTITION BY order_date, CLUSTER BY (region, status)
SELECT * FROM orders
WHERE order_date = '2024-01-15'  -- partition
  AND region = 'US'               -- cluster
  AND status = 'COMPLETED';       -- cluster

-- 3. Avoid SELECT * — specify columns
-- 4. JOIN order: large table left, small table right (BQ build side)
-- 5. Use APPROX functions for exploratory queries

-- Find expensive queries
SELECT job_id, user_email,
       total_bytes_processed / POW(1024, 3) AS gb_scanned,
       TIMESTAMP_DIFF(end_time, start_time, SECOND) AS duration_s
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE DATE(creation_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
ORDER BY total_bytes_processed DESC
LIMIT 20;
```

---

## CHAPTER 8: DATA MODELLING

### 8.1 OLTP vs OLAP

| Dimension | OLTP | OLAP |
|-----------|------|------|
| Purpose | Record transactions | Analyse data |
| Design | Normalised (3NF) | Denormalised (star/snowflake) |
| Query type | Many small reads/writes | Few large scans |
| Examples | Oracle, MySQL | BigQuery, Snowflake |

### 8.2 Dimensional Modelling (Kimball)

**Star Schema:**
```
              dim_customer
              (customer_id PK, name, region, tier)
                    |
dim_date ---- fact_orders ---- dim_product
(date_id PK)  (order_id PK)   (product_id PK, name, category)
(year, month, (date_id FK)
 is_weekend)  (customer_id FK)
              (product_id FK)
              (amount, qty, discount)
```

**Fact table grain** = one row per order line item (must be explicitly defined).

**Dimension tables** = descriptive context (who, what, where, when), denormalised for query performance.

### 8.3 Slowly Changing Dimensions

```sql
-- SCD Type 1: Overwrite (no history)
MERGE INTO dim_customer T
USING (SELECT 'C001' AS id, 'new@email.com' AS email) S
ON T.customer_id = S.id
WHEN MATCHED THEN UPDATE SET T.email = S.email;

-- SCD Type 2: Add new row (full history)
-- Schema: surrogate_key, business_key, attributes..., effective_start, effective_end, is_current

-- Query current state
SELECT * FROM dim_customer WHERE is_current = TRUE;

-- Point-in-time state (as of a specific date)
SELECT * FROM dim_customer
WHERE customer_id = 'C001'
  AND effective_start <= '2023-06-15'
  AND effective_end >= '2023-06-15';

-- Join fact to dimension at correct historical point
SELECT c.tier, SUM(o.amount) AS revenue
FROM fact_orders o
JOIN dim_customer c
  ON o.customer_id = c.customer_id
  AND o.order_date BETWEEN c.effective_start AND c.effective_end
GROUP BY c.tier;

-- SCD Type 3: Previous + Current value columns (limited history)
-- ALTER TABLE: add previous_tier STRING, tier_change_date DATE
```

### 8.4 Data Vault (Banking Context)

Used in CDM Next context — designed for highly regulated, auditable environments.

**Three entity types:**
- **Hubs**: business keys only (customer_id, order_id) — immutable
- **Links**: relationships between hubs
- **Satellites**: descriptive attributes with full insert-only history

```sql
-- Hub: business key + load metadata
CREATE TABLE hub_customer (
    hub_key       BYTES,      -- SHA256 hash of business key
    customer_id   STRING,     -- business key
    load_date     TIMESTAMP,
    record_source STRING      -- CDM Next source system tag
);

-- Satellite: all attributes, insert-only (never update)
CREATE TABLE sat_customer (
    hub_key       BYTES,
    load_date     TIMESTAMP,
    load_end_date TIMESTAMP,  -- NULL means current
    record_source STRING,
    name          STRING,
    email         STRING,
    tier          STRING
);

-- Current state query
SELECT h.customer_id, s.name, s.email, s.tier
FROM hub_customer h
JOIN sat_customer s ON h.hub_key = s.hub_key
WHERE s.load_end_date IS NULL;
```

**Why Data Vault suits banking:**
- Full audit trail by design (never DELETE, never UPDATE)
- Source-system agnostic — multiple sources merge cleanly via hubs
- Highly scalable — add new attributes by adding new satellites
- Parallel load friendly — hubs, links, satellites load independently

### 8.5 BigQuery Native Modelling Patterns

```sql
-- Pattern 1: Wide denormalised fact table
-- Pre-join dimension attributes at load time — fastest query, some duplication
CREATE TABLE fact_orders_wide AS
SELECT
    o.order_id, o.order_date, o.amount,
    c.name AS customer_name, c.region, c.tier,
    p.name AS product_name, p.category
FROM raw_orders o
JOIN dim_customer c ON o.customer_id = c.customer_id AND c.is_current = TRUE
JOIN dim_product  p ON o.product_id  = p.product_id;

-- Pattern 2: Nested/repeated fields — uniquely powerful in BigQuery
CREATE TABLE customers_nested AS
SELECT
    c.customer_id, c.name, c.region,
    ARRAY_AGG(STRUCT(o.order_id, o.order_date, o.amount, o.status)
              ORDER BY o.order_date DESC) AS orders
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name, c.region;

-- Query: no join needed, UNNEST the array
SELECT customer_id, name, o.amount
FROM customers_nested, UNNEST(orders) AS o
WHERE o.status = 'COMPLETED';
```

---

## CHAPTER 9: DATA QUALITY IN SQL

```sql
-- Null rates per column
SELECT
    COUNTIF(customer_id IS NULL) / COUNT(*) AS id_null_rate,
    COUNTIF(amount IS NULL)      / COUNT(*) AS amount_null_rate
FROM orders;

-- Duplicate detection
SELECT customer_id, COUNT(*) AS cnt
FROM customers GROUP BY 1 HAVING cnt > 1;

-- Referential integrity
SELECT o.order_id
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;  -- orphaned orders

-- Range validation
SELECT COUNTIF(amount < 0) AS negatives, COUNTIF(amount > 1000000) AS suspicious
FROM orders;

-- Format validation (email pattern)
SELECT email FROM customers
WHERE NOT REGEXP_CONTAINS(email, r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$');

-- Freshness check
SELECT
    MAX(created_at) AS latest_record,
    TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(created_at), HOUR) AS hours_stale
FROM orders;

-- Statistical profiling
SELECT
    MIN(amount) AS min, MAX(amount) AS max, AVG(amount) AS mean,
    APPROX_QUANTILES(amount, 100)[OFFSET(50)] AS median,
    APPROX_QUANTILES(amount, 100)[OFFSET(95)] AS p95,
    STDDEV(amount) AS std_dev
FROM orders;
```

---

## CHAPTER 10: ANALYTICAL SQL PATTERNS

### 10.1 Cohort Retention

```sql
WITH cohorts AS (
    SELECT customer_id, DATE_TRUNC(MIN(order_date), MONTH) AS cohort_month
    FROM orders GROUP BY customer_id
),
activity AS (
    SELECT o.customer_id,
           DATE_DIFF(DATE_TRUNC(o.order_date, MONTH), c.cohort_month, MONTH) AS month_offset
    FROM orders o JOIN cohorts c ON o.customer_id = c.customer_id
    GROUP BY 1, 2
)
SELECT
    c.cohort_month,
    a.month_offset,
    COUNT(DISTINCT a.customer_id) AS retained,
    COUNT(DISTINCT c2.customer_id) AS cohort_size,
    ROUND(COUNT(DISTINCT a.customer_id) / COUNT(DISTINCT c2.customer_id) * 100, 1) AS retention_pct
FROM cohorts c2
JOIN activity a ON c2.customer_id = a.customer_id
JOIN cohorts c ON a.customer_id = c.customer_id
GROUP BY 1, 2 ORDER BY 1, 2;
```

### 10.2 Funnel Analysis

```sql
WITH funnel AS (
    SELECT user_id,
           MAX(CASE WHEN event = 'view'     THEN 1 ELSE 0 END) AS step1,
           MAX(CASE WHEN event = 'add_cart' THEN 1 ELSE 0 END) AS step2,
           MAX(CASE WHEN event = 'checkout' THEN 1 ELSE 0 END) AS step3,
           MAX(CASE WHEN event = 'purchase' THEN 1 ELSE 0 END) AS step4
    FROM events GROUP BY user_id
)
SELECT
    SUM(step1) AS views,
    SUM(step2) AS cart_adds,
    SUM(step3) AS checkouts,
    SUM(step4) AS purchases,
    ROUND(SUM(step4) / SUM(step1) * 100, 1) AS overall_conversion_pct
FROM funnel;
```

### 10.3 Session Analysis

```sql
WITH gaps AS (
    SELECT user_id, event_time,
           TIMESTAMP_DIFF(event_time,
               LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time),
               MINUTE) AS gap_min
    FROM events
),
sessions AS (
    SELECT user_id, event_time,
           SUM(CASE WHEN gap_min IS NULL OR gap_min > 30 THEN 1 ELSE 0 END)
               OVER (PARTITION BY user_id ORDER BY event_time
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS session_id
    FROM gaps
)
SELECT
    user_id, session_id,
    MIN(event_time) AS session_start,
    MAX(event_time) AS session_end,
    COUNT(*) AS events,
    TIMESTAMP_DIFF(MAX(event_time), MIN(event_time), MINUTE) AS duration_min
FROM sessions
GROUP BY 1, 2;
```

---

*End of SQL & Data Modelling Textbook*
