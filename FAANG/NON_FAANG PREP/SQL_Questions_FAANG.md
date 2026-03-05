# SQL Interview Questions - FAANG Level

Advanced SQL for FAANG data engineering interviews.

---

# EASY QUESTIONS (1-5)

## Question 1: Window Functions - NTILE & PERCENT_RANK

**Difficulty:** Easy (but FAANG specific)  
**Time:** 10 minutes

### Problem Statement

Divide customers into quartiles by spending amount. Show percentile rank.

```sql
SELECT 
    customer_id,
    total_spent,
    NTILE(4) OVER (ORDER BY total_spent DESC) AS quartile,
    PERCENT_RANK() OVER (ORDER BY total_spent DESC) AS percentile_rank
FROM customer_summary
ORDER BY quartile, percentile_rank;
```

### Key Concepts

```
NTILE(n) - Divide into n equal buckets
PERCENT_RANK() - Percentile (0-1 scale)
CUME_DIST() - Cumulative distribution
ROW_NUMBER() - Unique numbers
RANK() - With ties (1,2,2,4)
DENSE_RANK() - No gaps (1,2,2,3)
```

---

## Question 2: Recursive CTE - Hierarchy

**Difficulty:** Easy

### Employee Hierarchy

```sql
WITH RECURSIVE employee_tree AS (
    -- Base case: top-level managers
    SELECT 
        employee_id,
        name,
        manager_id,
        1 AS level
    FROM employees
    WHERE manager_id IS NULL
    
    UNION ALL
    
    -- Recursive case: find direct reports
    SELECT 
        e.employee_id,
        e.name,
        e.manager_id,
        et.level + 1
    FROM employees e
    JOIN employee_tree et ON e.manager_id = et.employee_id
    WHERE et.level < 10
)
SELECT * FROM employee_tree
ORDER BY level, name;
```

---

## Question 3: Cumulative Distribution

```sql
SELECT 
    product_id,
    revenue,
    SUM(revenue) OVER (
        ORDER BY revenue DESC 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_revenue,
    100.0 * SUM(revenue) OVER (
        ORDER BY revenue DESC 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) / SUM(revenue) OVER () AS pct_of_total
FROM product_revenue
ORDER BY revenue DESC;
```

---

## Question 4: Date Window Functions

```sql
SELECT 
    order_date,
    order_amount,
    -- Last order in 7-day window
    LAG(order_date) OVER (
        PARTITION BY customer_id 
        ORDER BY order_date
    ) AS prev_order_date,
    -- Days since last order
    DATE_DIFF(
        order_date,
        LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date),
        DAY
    ) AS days_since_last_order
FROM orders
ORDER BY customer_id, order_date;
```

---

## Question 5: QUALIFY Clause

```sql
SELECT 
    customer_id,
    order_amount,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_amount DESC) AS rank
FROM orders
QUALIFY rank <= 3  -- Keep top 3 per customer
ORDER BY customer_id, rank;
```

---

# MEDIUM QUESTIONS (6-18)

## Question 6: Complex Window Function with Multiple Frames

```sql
SELECT 
    date,
    revenue,
    -- 7-day moving average
    AVG(revenue) OVER (
        ORDER BY date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS moving_avg_7d,
    -- Cumulative sum
    SUM(revenue) OVER (
        ORDER BY date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_revenue,
    -- Compare to previous value
    revenue - LAG(revenue) OVER (ORDER BY date) AS daily_change
FROM daily_sales
ORDER BY date;
```

---

## Question 7: Gaps and Islands (Advanced)

```sql
WITH numbered_dates AS (
    SELECT 
        order_date,
        ROW_NUMBER() OVER (ORDER BY order_date) AS row_num
    FROM orders
    GROUP BY order_date
),
islands AS (
    SELECT 
        order_date,
        DATE_SUB(order_date, INTERVAL row_num DAY) AS island
    FROM numbered_dates
),
island_summary AS (
    SELECT 
        island,
        MIN(order_date) AS start_date,
        MAX(order_date) AS end_date,
        DATEDIFF(MAX(order_date), MIN(order_date)) + 1 AS days_in_sequence,
        COUNT(*) AS num_days
    FROM islands
    GROUP BY island
)
SELECT * FROM island_summary
WHERE days_in_sequence >= 7;
```

---

## Question 8: Pivot Query (Complex)

```sql
SELECT 
    product_category,
    SUM(CASE WHEN status = 'Completed' THEN amount ELSE 0 END) AS completed,
    SUM(CASE WHEN status = 'Pending' THEN amount ELSE 0 END) AS pending,
    SUM(CASE WHEN status = 'Cancelled' THEN amount ELSE 0 END) AS cancelled,
    COUNT(DISTINCT CASE WHEN status = 'Completed' THEN order_id END) AS completed_orders,
    ROUND(100.0 * SUM(CASE WHEN status = 'Completed' THEN amount ELSE 0 END) 
        / SUM(amount), 2) AS completion_rate_pct
FROM orders
GROUP BY product_category
ORDER BY completed DESC;
```

---

## Question 9: Year-over-Year Comparison with Growth

```sql
WITH monthly_sales AS (
    SELECT 
        EXTRACT(YEAR FROM order_date) AS year,
        EXTRACT(MONTH FROM order_date) AS month,
        SUM(order_amount) AS sales
    FROM orders
    GROUP BY year, month
),
yoy_comparison AS (
    SELECT 
        COALESCE(current.month, previous.month) AS month,
        previous.sales AS prev_year_sales,
        current.sales AS current_year_sales,
        current.sales - previous.sales AS sales_diff,
        ROUND(
            100.0 * (current.sales - previous.sales) / previous.sales,
            2
        ) AS growth_pct
    FROM monthly_sales previous
    FULL OUTER JOIN monthly_sales current
        ON previous.month = current.month
        AND previous.year = EXTRACT(YEAR FROM CURRENT_DATE) - 1
        AND current.year = EXTRACT(YEAR FROM CURRENT_DATE)
)
SELECT * FROM yoy_comparison
WHERE month IS NOT NULL
ORDER BY month;
```

---

## Question 10: Percentile Calculations

```sql
SELECT 
    customer_id,
    total_spent,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY total_spent) OVER () AS q1,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_spent) OVER () AS median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY total_spent) OVER () AS q3,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_spent) OVER () AS p95
FROM customers
ORDER BY total_spent DESC;
```

---

## Question 11: Recursive Path Finding

```sql
WITH RECURSIVE path AS (
    -- Start node
    SELECT 
        node_id,
        parent_id,
        1 AS depth,
        CAST(node_id AS STRING) AS path
    FROM nodes
    WHERE parent_id IS NULL
    
    UNION ALL
    
    -- Find descendants
    SELECT 
        n.node_id,
        n.parent_id,
        p.depth + 1,
        CONCAT(p.path, '->', n.node_id)
    FROM nodes n
    JOIN path p ON n.parent_id = p.node_id
    WHERE p.depth < 10
)
SELECT * FROM path
ORDER BY depth, node_id;
```

---

## Question 12-18: Complex Patterns

**12. Funnel Analysis** - Track user progression through stages
**13. Cohort Analysis** - Group users by signup date, track retention
**14. RFM Segmentation** - Recency, Frequency, Monetary value
**15. Running Product** - Cumulative multiplication
**16. String Aggregation** - Concatenate with ordering
**17. Mode/Most Frequent** - Find most common value
**18. Correlation Computation** - Calculate statistical correlation

---

# HARD QUESTIONS (19-30)

## Question 19: Advanced Pivot with Aggregation

```sql
SELECT *
FROM (
    SELECT 
        user_id,
        category,
        DATE_TRUNC(order_date, MONTH) AS month,
        order_amount
    FROM orders
)
PIVOT (
    SUM(order_amount)
    FOR category IN ('Electronics', 'Clothing', 'Food')
)
ORDER BY user_id;
```

---

## Question 20: Complex Multi-level Aggregation

```sql
WITH customer_stats AS (
    SELECT 
        customer_id,
        DATE_TRUNC(order_date, MONTH) AS month,
        COUNT(*) AS order_count,
        SUM(order_amount) AS monthly_total,
        AVG(order_amount) AS avg_order
    FROM orders
    GROUP BY customer_id, month
),
annual_summary AS (
    SELECT 
        customer_id,
        EXTRACT(YEAR FROM month) AS year,
        SUM(order_count) AS annual_orders,
        SUM(monthly_total) AS annual_total,
        AVG(avg_order) AS avg_order_value,
        MAX(monthly_total) AS max_monthly,
        MIN(monthly_total) AS min_monthly
    FROM customer_stats
    GROUP BY customer_id, year
)
SELECT 
    customer_id,
    year,
    annual_orders,
    annual_total,
    avg_order_value,
    ROUND(avg_order_value * annual_orders, 2) AS expected_total,
    CASE 
        WHEN annual_total > 10000 THEN 'VIP'
        WHEN annual_total > 5000 THEN 'Premium'
        ELSE 'Standard'
    END AS customer_tier
FROM annual_summary
ORDER BY annual_total DESC;
```

---

## Question 21: Performance-Critical Query

**Problem:** Optimize slow query at scale (billions of rows)

```sql
-- SLOW: Full table scan
SELECT *
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
ORDER BY o.order_date DESC
LIMIT 1000;

-- FAST: Partition pruning + clustering
SELECT o.order_id, o.order_amount, c.customer_name
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
-- Partition pruning happens automatically
-- Clustering on customer_id enables efficient join
ORDER BY o.order_date DESC
LIMIT 1000;

-- FASTER: Materialized view
SELECT *
FROM orders_last_7_days
ORDER BY order_date DESC
LIMIT 1000;
```

---

## Question 22-30: Most Advanced Problems

**22. Graph algorithms in SQL** - Find connected components, shortest paths
**23. Temporal queries** - Time-series analysis, event sequences
**24. Machine learning features** - Statistical calculations
**25. Budget allocation** - Optimization problems
**26. Package delivery** - Traveling salesman type
**27. Seat allocation** - Complex constraints
**28. Top-K frequent** - Heavy hitters problem
**29. User similarity** - Jaccard distance
**30. Data deduplication at scale** - Probabilistic data structures

---

## FAANG-Specific Patterns

✅ **What FAANG emphasizes:**
- Query optimization at billion-row scale
- Handling NULL values correctly
- Complex window functions
- Performance debugging with EXPLAIN
- Understanding query plans deeply
- Cost awareness (especially GCP/BigQuery)

✅ **Common follow-ups:**
- "How would you optimize this for 1TB dataset?"
- "What's the time complexity?"
- "How would you test this query?"
- "What edge cases might break this?"

---

