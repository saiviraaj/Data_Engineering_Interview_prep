# SQL Problem Solving Patterns & Approaches (Extended Guide)

Author: SQL Interview Preparation Guide

This document contains **systematic SQL problem‑solving patterns** used
in real data engineering, analytics, and product-company interviews.

The goal is to help you **recognize patterns quickly** and apply the
correct SQL strategy.

------------------------------------------------------------------------

# 1. Core SQL Problem Solving Framework

When solving SQL problems, always determine:

1.  **Result Granularity**
    -   Per row
    -   Per user
    -   Per date
    -   Per product
    -   Per session
2.  **Data Transformation Needed**
    -   Filtering
    -   Aggregation
    -   Ranking
    -   Window analytics
3.  **Comparison Type**
    -   Row vs previous row
    -   Row vs group
    -   Row vs global average
4.  **Time-Based Logic**
    -   Rolling windows
    -   Streak detection
    -   Sessionization

------------------------------------------------------------------------

# 2. Basic Aggregation Pattern

Find totals, averages, or counts.

Example: Total revenue per customer

``` sql
SELECT customer_id,
       SUM(amount) AS total_revenue
FROM orders
GROUP BY customer_id;
```

------------------------------------------------------------------------

# 3. Filtering Aggregates (HAVING)

Example: Customers with more than 5 orders

``` sql
SELECT customer_id,
       COUNT(*) AS order_count
FROM orders
GROUP BY customer_id
HAVING COUNT(*) > 5;
```

------------------------------------------------------------------------

# 4. Top-N Per Group

Example: Highest salary per department

``` sql
SELECT *
FROM (
    SELECT *,
           ROW_NUMBER() OVER(
               PARTITION BY dept_id
               ORDER BY salary DESC
           ) AS rn
    FROM employees
) t
WHERE rn = 1;
```

------------------------------------------------------------------------

# 5. Ranking Pattern

Ranking entities by metric.

Example: Rank customers by spending

``` sql
SELECT customer_id,
       SUM(amount) AS total_spent,
       DENSE_RANK() OVER(ORDER BY SUM(amount) DESC) AS rank
FROM orders
GROUP BY customer_id;
```

------------------------------------------------------------------------

# 6. Latest Record Per Entity

Used heavily in **CDC pipelines and deduplication**.

``` sql
SELECT *
FROM (
    SELECT *,
           ROW_NUMBER() OVER(
               PARTITION BY user_id
               ORDER BY updated_at DESC
           ) AS rn
    FROM events
) t
WHERE rn = 1;
```

------------------------------------------------------------------------

# 7. Running Totals

Example: Cumulative revenue

``` sql
SELECT order_date,
       SUM(amount) OVER(ORDER BY order_date) AS running_total
FROM orders;
```

------------------------------------------------------------------------

# 8. Moving Window Analytics

Example: 7-day moving average

``` sql
SELECT order_date,
       AVG(amount) OVER(
           ORDER BY order_date
           ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
       )
FROM orders;
```

------------------------------------------------------------------------

# 9. Lag and Lead Pattern

Compare rows.

``` sql
SELECT order_date,
       amount,
       LAG(amount) OVER(ORDER BY order_date) AS previous_amount
FROM orders;
```

------------------------------------------------------------------------

# 10. Conditional Aggregation

Used for pivoting.

``` sql
SELECT
SUM(CASE WHEN status='completed' THEN 1 END) completed_orders,
SUM(CASE WHEN status='pending' THEN 1 END) pending_orders
FROM orders;
```

------------------------------------------------------------------------

# 11. Pivot Style Pattern

``` sql
SELECT customer_id,
SUM(CASE WHEN year=2023 THEN revenue END) AS rev_2023,
SUM(CASE WHEN year=2024 THEN revenue END) AS rev_2024
FROM sales
GROUP BY customer_id;
```

------------------------------------------------------------------------

# 12. Anti Join Pattern

Find records missing in another table.

``` sql
SELECT c.customer_id
FROM customers c
LEFT JOIN orders o
ON c.customer_id = o.customer_id
WHERE o.customer_id IS NULL;
```

------------------------------------------------------------------------

# 13. EXISTS Pattern

Efficient existence check.

``` sql
SELECT *
FROM customers c
WHERE EXISTS (
SELECT 1
FROM orders o
WHERE o.customer_id = c.customer_id
);
```

------------------------------------------------------------------------

# 14. Correlated Subquery Pattern

``` sql
SELECT *
FROM employees e
WHERE salary >
(
SELECT AVG(salary)
FROM employees
WHERE dept_id = e.dept_id
);
```

------------------------------------------------------------------------

# 15. Self Join Pattern

``` sql
SELECT e.name
FROM employees e
JOIN employees m
ON e.manager_id = m.emp_id
WHERE e.salary > m.salary;
```

------------------------------------------------------------------------

# 16. Gaps and Islands Pattern

Detect consecutive events.

Key trick:

    date - row_number()

Example:

``` sql
SELECT user_id,
txn_date,
txn_date - INTERVAL '1 day' *
ROW_NUMBER() OVER(
PARTITION BY user_id ORDER BY txn_date
)
FROM transactions;
```

------------------------------------------------------------------------

# 17. Longest Streak Detection

``` sql
WITH groups AS (
SELECT user_id,
txn_date,
txn_date - INTERVAL '1 day' *
ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY txn_date) grp
FROM transactions
)

SELECT user_id,
MAX(streak_len)
FROM (
SELECT user_id, grp, COUNT(*) streak_len
FROM groups
GROUP BY user_id, grp
) t
GROUP BY user_id;
```

------------------------------------------------------------------------

# 18. Sessionization Pattern

Create sessions when inactivity gap exceeds threshold.

Example: 30-minute inactivity

Use LAG + timestamp difference.

------------------------------------------------------------------------

# 19. Median Calculation

``` sql
SELECT AVG(amount)
FROM (
SELECT amount,
ROW_NUMBER() OVER(ORDER BY amount) rn,
COUNT(*) OVER() cnt
FROM orders
) t
WHERE rn IN (cnt/2, cnt/2 + 1);
```

------------------------------------------------------------------------

# 20. Window Distribution Functions

Common analytics functions:

    RANK()
    DENSE_RANK()
    ROW_NUMBER()
    NTILE()
    PERCENT_RANK()
    CUME_DIST()

Example:

``` sql
SELECT amount,
NTILE(4) OVER(ORDER BY amount) AS quartile
FROM orders;
```

------------------------------------------------------------------------

# 21. Data Engineering Patterns

Common ETL SQL patterns.

### Deduplication

``` sql
ROW_NUMBER() OVER(
PARTITION BY id
ORDER BY updated_at DESC
)
```

### Incremental Processing

``` sql
WHERE updated_at > last_processed_timestamp
```

### Change Detection

Compare previous and current rows.

------------------------------------------------------------------------

# 22. SQL Debugging Strategy

When queries fail:

1.  Break logic into CTEs
2.  Check intermediate output
3.  Validate joins
4.  Validate aggregations
5.  Validate window partitions

------------------------------------------------------------------------

# 23. Most Important SQL Patterns

  Pattern                   Use Case
  ------------------------- ------------------
  Top-N per group           rankings
  Latest record             CDC pipelines
  Running totals            finance
  Moving averages           analytics
  Gaps & islands            streak detection
  Conditional aggregation   pivot
  Anti joins                missing data
  Sessionization            user activity

------------------------------------------------------------------------

# Final Advice

If you master these **patterns**, you can solve **90% of SQL interview
problems quickly**.
