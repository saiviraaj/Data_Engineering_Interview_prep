# Advanced SQL Patterns for Interview

## Window Functions Mastery

### ROW_NUMBER vs RANK vs DENSE_RANK

```sql
-- Sample data:
-- user_id | amount
-- 1       | 100
-- 1       | 150
-- 1       | 100
-- 2       | 200
-- 2       | 200

SELECT 
  user_id,
  amount,
  ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY amount DESC) as row_num,
  RANK() OVER (PARTITION BY user_id ORDER BY amount DESC) as rank,
  DENSE_RANK() OVER (PARTITION BY user_id ORDER BY amount DESC) as dense_rank
FROM purchases
ORDER BY user_id, amount DESC;

-- Results:
-- user_id | amount | row_num | rank | dense_rank
-- 1       | 150    | 1       | 1    | 1
-- 1       | 100    | 2       | 2    | 2
-- 1       | 100    | 3       | 2    | 2
-- 2       | 200    | 1       | 1    | 1
-- 2       | 200    | 2       | 1    | 1

-- Use ROW_NUMBER for: Deduplication (take first)
-- Use RANK for: Sports rankings (ties get same, next skips)
-- Use DENSE_RANK for: Percentiles (continuous ranking)
```

### Offset Functions (LAG, LEAD, FIRST_VALUE, LAST_VALUE)

```sql
-- Previous/Next values
SELECT 
  user_id,
  order_date,
  amount,
  LAG(amount) OVER (PARTITION BY user_id ORDER BY order_date) as prev_amount,
  LEAD(amount) OVER (PARTITION BY user_id ORDER BY order_date) as next_amount
FROM orders;

-- First and last values
SELECT 
  user_id,
  order_date,
  amount,
  FIRST_VALUE(amount) OVER (
    PARTITION BY user_id 
    ORDER BY order_date
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
  ) as first_purchase,
  LAST_VALUE(amount) OVER (
    PARTITION BY user_id 
    ORDER BY order_date
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
  ) as last_purchase
FROM orders;
```

### Running Aggregates

```sql
-- Cumulative sum
SELECT 
  user_id,
  order_date,
  amount,
  SUM(amount) OVER (
    PARTITION BY user_id 
    ORDER BY order_date
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) as cumulative_amount
FROM orders;

-- Moving average (last 7 days)
SELECT 
  order_date,
  amount,
  AVG(amount) OVER (
    ORDER BY order_date
    RANGE BETWEEN INTERVAL '7' DAY PRECEDING AND CURRENT ROW
  ) as moving_avg_7day
FROM orders;

-- Difference from previous
SELECT 
  user_id,
  order_date,
  amount,
  LAG(amount) OVER (PARTITION BY user_id ORDER BY order_date) as prev_amount,
  amount - LAG(amount) OVER (PARTITION BY user_id ORDER BY order_date) as diff
FROM orders;
```

### Distribution Functions

```sql
-- Percentile rank (what percentile is this value)
SELECT 
  employee_name,
  salary,
  PERCENT_RANK() OVER (ORDER BY salary) as percentile
FROM employees;

-- Cumulative distribution (what % earn <= this amount)
SELECT 
  employee_name,
  salary,
  CUME_DIST() OVER (ORDER BY salary) as cum_dist
FROM employees;

-- Bucket into quartiles
SELECT 
  user_id,
  total_revenue,
  NTILE(4) OVER (ORDER BY total_revenue DESC) as quartile
FROM user_summary;

-- Bucket into deciles
SELECT 
  user_id,
  total_revenue,
  NTILE(10) OVER (ORDER BY total_revenue DESC) as decile
FROM user_summary;
```

---

## Recursive CTEs

```sql
-- Organization hierarchy
WITH RECURSIVE org_hierarchy AS (
  -- Base: Start with CEO (no manager)
  SELECT 
    emp_id,
    emp_name,
    manager_id,
    salary,
    1 as level,
    ARRAY[emp_id] as path
  FROM employees
  WHERE manager_id IS NULL
  
  UNION ALL
  
  -- Recursive: Find direct reports
  SELECT 
    e.emp_id,
    e.emp_name,
    e.manager_id,
    e.salary,
    oh.level + 1,
    ARRAY_CONCAT(oh.path, [e.emp_id])
  FROM employees e
  JOIN org_hierarchy oh ON e.manager_id = oh.emp_id
  WHERE oh.level < 10
)
SELECT 
  level,
  emp_id,
  emp_name,
  path
FROM org_hierarchy
ORDER BY path;
```

---

## PIVOT and UNPIVOT

```sql
-- UNPIVOT (wide to long)
SELECT 
  user_id,
  month,
  sales
FROM (
  SELECT user_id, jan_sales, feb_sales, mar_sales 
  FROM sales_wide
)
UNPIVOT (
  sales FOR month IN (jan_sales, feb_sales, mar_sales)
);

-- PIVOT (long to wide)
SELECT 
  user_id,
  jan,
  feb,
  mar
FROM (
  SELECT user_id, month, sales 
  FROM sales_long
)
PIVOT (
  SUM(sales) FOR month IN ('jan', 'feb', 'mar')
);

-- Alternative PIVOT using CASE
SELECT 
  user_id,
  SUM(CASE WHEN month = 'jan' THEN sales ELSE 0 END) as jan,
  SUM(CASE WHEN month = 'feb' THEN sales ELSE 0 END) as feb,
  SUM(CASE WHEN month = 'mar' THEN sales ELSE 0 END) as mar
FROM sales_long
GROUP BY user_id;
```

---

## Set Operations

```sql
-- UNION (remove duplicates)
SELECT user_id FROM 2023_purchases
UNION
SELECT user_id FROM 2024_purchases;

-- UNION ALL (keep all)
SELECT user_id FROM 2023_purchases
UNION ALL
SELECT user_id FROM 2024_purchases;

-- INTERSECT (in both)
SELECT user_id FROM 2023_purchases
INTERSECT
SELECT user_id FROM 2024_purchases;

-- EXCEPT (in first, not second)
SELECT user_id FROM 2023_purchases
EXCEPT
SELECT user_id FROM 2024_purchases;
```

---

## Practical Interview Queries

### Query 1: Top N per Group

```sql
-- Get top 3 products per category
WITH ranked AS (
  SELECT 
    category,
    product_id,
    product_name,
    sales,
    ROW_NUMBER() OVER (PARTITION BY category ORDER BY sales DESC) as rank
  FROM products
)
SELECT category, product_id, product_name, sales
FROM ranked
WHERE rank <= 3;
```

### Query 2: Cohort Retention

```sql
-- Month-over-month retention
WITH user_cohorts AS (
  SELECT 
    user_id,
    DATE_TRUNC(signup_date, MONTH) as cohort_month
  FROM users
),
user_activity AS (
  SELECT 
    c.user_id,
    c.cohort_month,
    DATE_TRUNC(o.order_date, MONTH) as order_month,
    DATE_DIFF(DATE_TRUNC(o.order_date, MONTH), c.cohort_month, MONTH) as months_since_signup
  FROM user_cohorts c
  LEFT JOIN orders o ON c.user_id = o.user_id
)
SELECT 
  cohort_month,
  months_since_signup,
  COUNT(DISTINCT user_id) as users
FROM user_activity
GROUP BY cohort_month, months_since_signup
ORDER BY cohort_month, months_since_signup;
```

### Query 3: Session Analysis

```sql
-- Create sessions based on 30-minute gap
WITH user_events AS (
  SELECT 
    user_id,
    event_timestamp,
    DATE_DIFF(
      event_timestamp,
      LAG(event_timestamp) OVER (PARTITION BY user_id ORDER BY event_timestamp),
      MINUTE
    ) as minutes_since_last
  FROM events
),
session_flags AS (
  SELECT 
    user_id,
    event_timestamp,
    CASE 
      WHEN minutes_since_last IS NULL THEN 1
      WHEN minutes_since_last > 30 THEN 1
      ELSE 0
    END as session_start
  FROM user_events
),
sessions AS (
  SELECT 
    user_id,
    SUM(session_start) OVER (
      PARTITION BY user_id 
      ORDER BY event_timestamp
    ) as session_id,
    event_timestamp
  FROM session_flags
)
SELECT 
  user_id,
  session_id,
  MIN(event_timestamp) as session_start,
  MAX(event_timestamp) as session_end,
  DATE_DIFF(MAX(event_timestamp), MIN(event_timestamp), SECOND) as session_duration_sec,
  COUNT(*) as event_count
FROM sessions
GROUP BY user_id, session_id
ORDER BY user_id, session_start;
```

### Query 4: RFM Segmentation

```sql
-- Recency, Frequency, Monetary
WITH customer_metrics AS (
  SELECT 
    user_id,
    DATE_DIFF(CURRENT_DATE(), MAX(order_date), DAY) as recency_days,
    COUNT(DISTINCT order_id) as frequency,
    SUM(order_amount) as monetary_value
  FROM orders
  WHERE order_date >= CURRENT_DATE() - 365
  GROUP BY user_id
),
rfm_scores AS (
  SELECT 
    user_id,
    NTILE(5) OVER (ORDER BY recency_days DESC) as r_score,  -- 5=recent
    NTILE(5) OVER (ORDER BY frequency) as f_score,          -- 5=frequent
    NTILE(5) OVER (ORDER BY monetary_value) as m_score      -- 5=high value
  FROM customer_metrics
)
SELECT 
  user_id,
  r_score,
  f_score,
  m_score,
  CASE 
    WHEN r_score = 5 AND f_score = 5 AND m_score = 5 THEN 'Champions'
    WHEN r_score >= 4 AND f_score >= 4 THEN 'Loyal'
    WHEN r_score = 5 AND f_score <= 2 THEN 'At Risk'
    WHEN r_score = 1 THEN 'Lost'
    ELSE 'Need Attention'
  END as segment
FROM rfm_scores;
```

### Query 5: Anomaly Detection

```sql
-- Find unusual spikes in daily metrics
WITH daily_metrics AS (
  SELECT 
    DATE(event_timestamp) as date,
    SUM(amount) as daily_amount,
    COUNT(*) as event_count
  FROM events
  WHERE event_timestamp >= CURRENT_DATE() - 90
  GROUP BY date
),
metric_stats AS (
  SELECT 
    date,
    daily_amount,
    AVG(daily_amount) OVER (
      ORDER BY date 
      ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) as avg_30day,
    STDDEV_POP(daily_amount) OVER (
      ORDER BY date 
      ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) as stddev_30day
  FROM daily_metrics
)
SELECT 
  date,
  daily_amount,
  avg_30day,
  (daily_amount - avg_30day) / NULLIF(stddev_30day, 0) as z_score,
  CASE 
    WHEN ABS((daily_amount - avg_30day) / NULLIF(stddev_30day, 0)) > 3 THEN 'SEVERE'
    WHEN ABS((daily_amount - avg_30day) / NULLIF(stddev_30day, 0)) > 2 THEN 'ANOMALY'
    ELSE 'NORMAL'
  END as status
FROM metric_stats
WHERE daily_amount > 0
ORDER BY ABS((daily_amount - avg_30day) / NULLIF(stddev_30day, 0)) DESC;
```

---

## Performance Tips

1. **Always specify columns** (never SELECT *)
2. **Filter before JOIN** (reduce join input)
3. **Use single GROUP BY** (not multiple)
4. **Window functions** over self-joins (better performance)
5. **APPROX functions** for estimates (faster on large data)
6. **Caching** with 24-hour TTL (free repeat queries)
7. **Materialized views** for expensive aggregations
8. **Partition pruning** (use WHERE on partition column)
9. **Clustering** on filtered columns
10. **DISTINCT** with GROUP BY (sometimes faster)

