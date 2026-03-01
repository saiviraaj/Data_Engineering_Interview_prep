# 🎯 COMPLETE SQL PATTERNS & STRATEGIES GUIDE
## Master Every SQL Pattern for Senior Data Engineer Interviews

**Purpose:** Comprehensive reference for recognizing and solving ANY SQL interview question  
**Level:** Senior Data Engineer and above  
**Coverage:** All patterns, strategies, when to use, and exhaustive examples

---

## 📚 TABLE OF CONTENTS

1. **PATTERN RECOGNITION FRAMEWORK** - How to identify which pattern to use
2. **WINDOW FUNCTIONS** - All variations and use cases
3. **GAPS AND ISLANDS** - Consecutive sequences and grouping
4. **SELF-JOINS & HIERARCHIES** - Recursive patterns
5. **PIVOTING & UNPIVOTING** - Data reshaping
6. **ADVANCED AGGREGATIONS** - Conditional and complex aggregations
7. **DATE & TIME PATTERNS** - Temporal analysis
8. **RANKING & TOP-N** - Finding extremes
9. **DEDUPLICATION STRATEGIES** - Handling duplicates
10. **RUNNING TOTALS & CUMULATIVE** - Progressive calculations
11. **LEAD & LAG** - Time series comparisons
12. **ARRAYS & JSON** - Semi-structured data
13. **PERFORMANCE OPTIMIZATION** - Query tuning patterns
14. **REAL-WORLD SCENARIOS** - Complete problem patterns

---

## 🎯 PART 1: PATTERN RECOGNITION FRAMEWORK

### **How to Identify Which Pattern to Use**

```
QUESTION TYPE → PATTERN TO USE → KEY INDICATORS
```

#### **Recognition Decision Tree:**

```
├─ Does the question mention "consecutive" / "streak" / "continuous"?
│  └─ YES → **GAPS AND ISLANDS PATTERN**
│
├─ Does it ask for "running total" / "cumulative" / "growing"?
│  └─ YES → **WINDOW FUNCTIONS with SUM OVER**
│
├─ Does it need "previous value" / "next value" / "compared to last"?
│  └─ YES → **LAG/LEAD WINDOW FUNCTIONS**
│
├─ Does it ask for "top N per group" / "highest within each"?
│  └─ YES → **ROW_NUMBER/RANK with PARTITION BY**
│
├─ Does it need "pivot" / "cross-tab" / "rows to columns"?
│  └─ YES → **PIVOT PATTERN with CASE WHEN**
│
├─ Does it mention "moving average" / "rolling" / "sliding window"?
│  └─ YES → **WINDOW FUNCTIONS with ROWS BETWEEN**
│
├─ Does it ask about "hierarchy" / "manager-employee" / "tree structure"?
│  └─ YES → **RECURSIVE CTE or SELF-JOIN**
│
├─ Does it need "deduplication" / "remove duplicates" / "unique records"?
│  └─ YES → **ROW_NUMBER or DISTINCT ON**
│
├─ Does it mention "cohort" / "retention" / "funnel"?
│  └─ YES → **COMPLEX JOINS + CONDITIONAL AGGREGATION**
│
└─ Does it need "sessionization" / "group by time gaps"?
   └─ YES → **GAPS AND ISLANDS + LAG**
```

### **Keywords to Pattern Mapping**

| **Keywords in Question** | **Pattern to Use** | **Primary Function** |
|-------------------------|-------------------|---------------------|
| "consecutive", "streak", "continuous", "uninterrupted" | Gaps and Islands | ROW_NUMBER + DATE arithmetic |
| "running total", "cumulative", "progressive" | Running Totals | SUM() OVER (ORDER BY) |
| "moving average", "rolling", "sliding window" | Moving Aggregates | AVG() OVER (ROWS BETWEEN) |
| "previous", "prior", "compare to last" | Time Comparisons | LAG() |
| "next", "following", "look ahead" | Future Comparisons | LEAD() |
| "top N per group", "highest in each", "ranking within" | Top N Per Group | ROW_NUMBER() OVER (PARTITION BY) |
| "pivot", "cross-tab", "rows to columns" | Pivot | CASE WHEN + GROUP BY |
| "unpivot", "normalize", "columns to rows" | Unpivot | UNION ALL or CROSS JOIN |
| "hierarchy", "tree", "organizational chart", "recursive" | Hierarchical | RECURSIVE CTE or CONNECT BY |
| "deduplicate", "remove duplicates", "keep latest" | Deduplication | ROW_NUMBER() or DISTINCT ON |
| "median", "percentile", "quartile" | Percentiles | PERCENTILE_CONT or NTILE |
| "session", "group by gaps", "activity groups" | Sessionization | LAG + Gaps and Islands |
| "cohort", "retention", "funnel" | Analytics | Complex JOINs + CASE WHEN |
| "first occurrence", "last occurrence" | Boundary Values | FIRST_VALUE / LAST_VALUE |

---

## 🔵 PART 2: WINDOW FUNCTIONS - COMPLETE GUIDE

### **2.1 What Are Window Functions?**

Window functions perform calculations across a set of rows related to the current row **without collapsing** the rows (unlike GROUP BY).

**Syntax Structure:**
```sql
<FUNCTION>() OVER (
    [PARTITION BY column1, column2]  -- Optional: Define groups
    [ORDER BY column3]                -- Optional: Define order within groups
    [ROWS/RANGE BETWEEN ...]         -- Optional: Define frame
)
```

### **2.2 When to Use Window Functions vs GROUP BY**

| **Use Window Functions When:** | **Use GROUP BY When:** |
|---------------------------------|------------------------|
| Need to keep all rows | Want to collapse rows |
| Need row-level calculations alongside aggregates | Only need group-level aggregates |
| Comparing rows within groups | Simple aggregation per group |
| Calculating running totals | Calculating totals per group |
| Finding ranks within groups | Counting items per group |

### **2.3 All Window Function Types**

#### **A. RANKING FUNCTIONS**

```sql
/*
ROW_NUMBER() - Unique sequential number (1,2,3,4...)
RANK()       - Same rank for ties, with gaps (1,2,2,4...)
DENSE_RANK() - Same rank for ties, no gaps (1,2,2,3...)
NTILE(n)     - Divide rows into n buckets (1,1,2,2,3,3...)
*/

-- Example: Rank employees by salary in each department
SELECT 
    employee_id,
    department,
    salary,
    ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS row_num,
    RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS rank_with_gaps,
    DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS rank_no_gaps,
    NTILE(4) OVER (PARTITION BY department ORDER BY salary DESC) AS quartile
FROM employees;

/*
Output:
emp_id | dept  | salary | row_num | rank_gaps | rank_no_gaps | quartile
1      | Sales | 80000  | 1       | 1         | 1            | 1
2      | Sales | 80000  | 2       | 1         | 1            | 1
3      | Sales | 75000  | 3       | 3         | 2            | 2
4      | Sales | 70000  | 4       | 4         | 3            | 2
*/
```

**When to Use Each:**
- **ROW_NUMBER()**: When you need unique identifiers or strict ordering (most common)
- **RANK()**: When ties should have same rank but skip next numbers (sports rankings)
- **DENSE_RANK()**: When ties should have same rank without gaps (percentile buckets)
- **NTILE()**: When dividing into equal groups (quartiles, deciles, percentiles)

#### **B. VALUE FUNCTIONS**

```sql
/*
LAG()          - Previous row's value
LEAD()         - Next row's value
FIRST_VALUE()  - First value in window
LAST_VALUE()   - Last value in window
NTH_VALUE()    - N-th value in window
*/

-- Example: Compare each month's sales to previous and next month
SELECT 
    month,
    sales,
    LAG(sales, 1) OVER (ORDER BY month) AS prev_month_sales,
    LEAD(sales, 1) OVER (ORDER BY month) AS next_month_sales,
    sales - LAG(sales, 1) OVER (ORDER BY month) AS growth_from_prev,
    FIRST_VALUE(sales) OVER (ORDER BY month) AS first_month_sales,
    LAST_VALUE(sales) OVER (
        ORDER BY month 
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS last_month_sales
FROM monthly_sales
ORDER BY month;

/*
Output:
month   | sales | prev  | next  | growth | first | last
2024-01 | 100   | NULL  | 120   | NULL   | 100   | 180
2024-02 | 120   | 100   | 150   | 20     | 100   | 180
2024-03 | 150   | 120   | 180   | 30     | 100   | 180
2024-04 | 180   | 150   | NULL  | 30     | 100   | 180
*/
```

**When to Use Each:**
- **LAG()**: Compare current row to previous (month-over-month growth, sequential analysis)
- **LEAD()**: Compare current row to future (forecasting, looking ahead)
- **FIRST_VALUE()**: Get first value in group (cohort start, baseline)
- **LAST_VALUE()**: Get last value in group (most recent status) - **Note:** Requires proper frame!
- **NTH_VALUE()**: Get specific position (e.g., 2nd highest)

#### **C. AGGREGATE FUNCTIONS AS WINDOW FUNCTIONS**

```sql
/*
SUM()   - Running/moving totals
AVG()   - Running/moving averages
COUNT() - Running counts
MAX()   - Running maximum
MIN()   - Running minimum
*/

-- Example: Running totals and moving averages
SELECT 
    date,
    revenue,
    -- Running total (all rows up to current)
    SUM(revenue) OVER (ORDER BY date) AS running_total,
    
    -- 7-day moving average
    AVG(revenue) OVER (
        ORDER BY date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS moving_avg_7day,
    
    -- Running average
    AVG(revenue) OVER (ORDER BY date) AS running_avg,
    
    -- Count of days so far
    COUNT(*) OVER (ORDER BY date) AS days_count,
    
    -- Maximum revenue seen so far
    MAX(revenue) OVER (ORDER BY date) AS max_so_far
FROM daily_revenue
ORDER BY date;
```

### **2.4 Window Frame Specifications (ROWS BETWEEN)**

**Critical for LAST_VALUE and aggregate functions!**

```sql
-- Syntax:
ROWS BETWEEN <start> AND <end>
RANGE BETWEEN <start> AND <end>

-- Common frames:
ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW        -- Default for ORDER BY
ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING -- Entire partition
ROWS BETWEEN 6 PRECEDING AND CURRENT ROW                -- Last 7 rows (including current)
ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING                -- 3 before + current + 3 after
ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING        -- Current to end
```

**ROWS vs RANGE:**
- **ROWS**: Physical position-based (count of rows)
- **RANGE**: Logical value-based (same ORDER BY values grouped)

```sql
-- Example showing ROWS vs RANGE difference
WITH data AS (
    SELECT * FROM (VALUES 
        (1, '2024-01-01', 100),
        (2, '2024-01-01', 150),  -- Same date
        (3, '2024-01-02', 200)
    ) AS t(id, date, amount)
)
SELECT 
    id,
    date,
    amount,
    SUM(amount) OVER (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS sum_rows,
    SUM(amount) OVER (ORDER BY date RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS sum_range
FROM data;

/*
Output:
id | date       | amount | sum_rows | sum_range
1  | 2024-01-01 | 100    | 100      | 250  (includes all rows with same date)
2  | 2024-01-01 | 150    | 250      | 250  (includes all rows with same date)
3  | 2024-01-02 | 200    | 450      | 450
*/
```

### **2.5 Complete Window Function Examples**

#### **Example 1: Running Total by Category**

```sql
-- Calculate running total of sales by product category
SELECT 
    date,
    category,
    sales,
    SUM(sales) OVER (
        PARTITION BY category 
        ORDER BY date
    ) AS running_total_by_category
FROM product_sales
ORDER BY category, date;
```

#### **Example 2: Moving Average with Different Windows**

```sql
-- Calculate various moving averages
SELECT 
    date,
    stock_price,
    -- 7-day moving average
    AVG(stock_price) OVER (
        ORDER BY date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS ma_7,
    -- 30-day moving average
    AVG(stock_price) OVER (
        ORDER BY date 
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS ma_30,
    -- Centered moving average (3 before, current, 3 after)
    AVG(stock_price) OVER (
        ORDER BY date 
        ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING
    ) AS ma_centered
FROM stock_prices
ORDER BY date;
```

#### **Example 3: Comparing to Previous and Next Values**

```sql
-- Compare each day's metrics to previous and next day
SELECT 
    date,
    active_users,
    LAG(active_users) OVER (ORDER BY date) AS prev_day,
    LEAD(active_users) OVER (ORDER BY date) AS next_day,
    active_users - LAG(active_users) OVER (ORDER BY date) AS daily_change,
    ROUND(
        100.0 * (active_users - LAG(active_users) OVER (ORDER BY date)) 
        / NULLIF(LAG(active_users) OVER (ORDER BY date), 0),
        2
    ) AS pct_change
FROM user_activity
ORDER BY date;
```

#### **Example 4: Top 3 in Each Category**

```sql
-- Find top 3 products by revenue in each category
SELECT 
    category,
    product_name,
    revenue,
    rank
FROM (
    SELECT 
        category,
        product_name,
        revenue,
        ROW_NUMBER() OVER (
            PARTITION BY category 
            ORDER BY revenue DESC
        ) AS rank
    FROM products
) ranked
WHERE rank <= 3
ORDER BY category, rank;
```

---

## 🟠 PART 3: GAPS AND ISLANDS PATTERN

### **3.1 What is Gaps and Islands?**

**Definition:** Identifying consecutive sequences (islands) and gaps between them in ordered data.

**When to Use:**
- Finding consecutive login days
- Identifying uninterrupted streaks
- Detecting gaps in sequences
- Grouping continuous time periods
- Finding missing values in sequences

### **3.2 Core Concept**

The key insight: **When you subtract ROW_NUMBER from a sequential value (like date), consecutive rows produce the same result.**

```
Date       | Row_Number | Date - Row_Number | Group
2024-01-01 | 1          | 2023-12-31        | A
2024-01-02 | 2          | 2023-12-31        | A (same!)
2024-01-03 | 3          | 2023-12-31        | A (same!)
2024-01-05 | 4          | 2024-01-01        | B (gap!)
2024-01-06 | 5          | 2024-01-01        | B (same!)
```

### **3.3 Standard Gaps and Islands Query**

```sql
/*
Problem: Find consecutive login streaks for each user

Table: user_logins
+---------+------------+
| user_id | login_date |
+---------+------------+
| 1       | 2024-01-01 |
| 1       | 2024-01-02 |
| 1       | 2024-01-03 |
| 1       | 2024-01-05 | -- Gap
| 1       | 2024-01-06 |
+---------+------------+

Expected Output:
+---------+--------------+------------+------+
| user_id | streak_start | streak_end | days |
+---------+--------------+------------+------+
| 1       | 2024-01-01   | 2024-01-03 | 3    |
| 1       | 2024-01-05   | 2024-01-06 | 2    |
+---------+--------------+------------+------+
*/

-- Solution:
WITH numbered AS (
    SELECT 
        user_id,
        login_date,
        ROW_NUMBER() OVER (
            PARTITION BY user_id 
            ORDER BY login_date
        ) AS rn,
        -- Key: Subtract row number from date to identify groups
        DATE_SUB(login_date, INTERVAL ROW_NUMBER() OVER (
            PARTITION BY user_id 
            ORDER BY login_date
        ) DAY) AS group_id
    FROM user_logins
)
SELECT 
    user_id,
    MIN(login_date) AS streak_start,
    MAX(login_date) AS streak_end,
    COUNT(*) AS days_in_streak,
    -- Alternative: use DATE_DIFF
    DATE_DIFF(MAX(login_date), MIN(login_date), DAY) + 1 AS days_calculated
FROM numbered
GROUP BY user_id, group_id
HAVING COUNT(*) >= 2  -- Optional: Filter for streaks of 2+ days
ORDER BY user_id, streak_start;
```

### **3.4 Variations of Gaps and Islands**

#### **Variation 1: Find Gaps (Missing Dates)**

```sql
/*
Problem: Find missing dates in a sequence

Expected: Identify date ranges where there's no activity
*/

WITH date_range AS (
    -- Generate complete date range
    SELECT date
    FROM UNNEST(GENERATE_DATE_ARRAY('2024-01-01', '2024-01-31', INTERVAL 1 DAY)) AS date
),
activity_dates AS (
    SELECT DISTINCT DATE(activity_timestamp) AS date
    FROM user_activity
)
SELECT 
    dr.date AS missing_date
FROM date_range dr
LEFT JOIN activity_dates ad ON dr.date = ad.date
WHERE ad.date IS NULL
ORDER BY dr.date;

-- Find gap ranges (consecutive missing dates)
WITH numbered AS (
    SELECT 
        missing_date,
        ROW_NUMBER() OVER (ORDER BY missing_date) AS rn,
        DATE_SUB(missing_date, INTERVAL ROW_NUMBER() OVER (ORDER BY missing_date) DAY) AS gap_group
    FROM (
        SELECT dr.date AS missing_date
        FROM date_range dr
        LEFT JOIN activity_dates ad ON dr.date = ad.date
        WHERE ad.date IS NULL
    )
)
SELECT 
    MIN(missing_date) AS gap_start,
    MAX(missing_date) AS gap_end,
    COUNT(*) AS days_missing
FROM numbered
GROUP BY gap_group
ORDER BY gap_start;
```

#### **Variation 2: Islands with Minimum Duration**

```sql
/*
Problem: Find login streaks of at least 7 consecutive days
*/

WITH numbered AS (
    SELECT 
        user_id,
        login_date,
        DATE_SUB(login_date, INTERVAL ROW_NUMBER() OVER (
            PARTITION BY user_id 
            ORDER BY login_date
        ) DAY) AS group_id
    FROM user_logins
)
SELECT 
    user_id,
    MIN(login_date) AS streak_start,
    MAX(login_date) AS streak_end,
    COUNT(*) AS days
FROM numbered
GROUP BY user_id, group_id
HAVING COUNT(*) >= 7  -- At least 7 days
ORDER BY user_id, days DESC;
```

#### **Variation 3: Islands with Non-Date Sequences**

```sql
/*
Problem: Find consecutive order IDs for each customer

Table: orders
+-------------+----------+
| customer_id | order_id |
+-------------+----------+
| 1           | 100      |
| 1           | 101      |
| 1           | 102      |
| 1           | 105      | -- Gap
| 1           | 106      |
+-------------+----------+
*/

WITH numbered AS (
    SELECT 
        customer_id,
        order_id,
        ROW_NUMBER() OVER (
            PARTITION BY customer_id 
            ORDER BY order_id
        ) AS rn,
        -- Subtract row number from order_id
        order_id - ROW_NUMBER() OVER (
            PARTITION BY customer_id 
            ORDER BY order_id
        ) AS group_id
    FROM orders
)
SELECT 
    customer_id,
    MIN(order_id) AS sequence_start,
    MAX(order_id) AS sequence_end,
    COUNT(*) AS consecutive_orders
FROM numbered
GROUP BY customer_id, group_id
ORDER BY customer_id, sequence_start;
```

### **3.5 Advanced: Gaps and Islands with Conditions**

```sql
/*
Problem: Find consecutive days where sales exceeded $10,000

Only count as "island" if ALL days in sequence exceed threshold
*/

WITH qualifying_days AS (
    SELECT 
        sale_date,
        daily_sales
    FROM sales
    WHERE daily_sales > 10000
),
numbered AS (
    SELECT 
        sale_date,
        daily_sales,
        DATE_SUB(sale_date, INTERVAL ROW_NUMBER() OVER (ORDER BY sale_date) DAY) AS group_id
    FROM qualifying_days
)
SELECT 
    MIN(sale_date) AS streak_start,
    MAX(sale_date) AS streak_end,
    COUNT(*) AS days_over_threshold,
    ROUND(AVG(daily_sales), 2) AS avg_sales_in_streak
FROM numbered
GROUP BY group_id
HAVING COUNT(*) >= 3  -- At least 3 consecutive days
ORDER BY streak_start;
```

---

## 🟢 PART 4: SELF-JOINS & HIERARCHIES

### **4.1 Self-Joins - When to Use**

**Use self-joins when:**
- Comparing rows within the same table
- Finding relationships between records
- Building hierarchies (employee-manager)
- Detecting overlapping intervals
- Finding pairs or combinations

### **4.2 Basic Self-Join Patterns**

#### **Pattern 1: Employee-Manager Hierarchy**

```sql
/*
Problem: List all employees with their manager's name

Table: employees
+--------+-----------+------------+
| emp_id | emp_name  | manager_id |
+--------+-----------+------------+
| 1      | CEO       | NULL       |
| 2      | VP Sales  | 1          |
| 3      | Sales Mgr | 2          |
+--------+-----------+------------+
*/

-- Solution:
SELECT 
    e.emp_id,
    e.emp_name AS employee,
    m.emp_name AS manager,
    m.emp_id AS manager_id
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.emp_id
ORDER BY e.emp_id;

/*
Output:
emp_id | employee  | manager   | manager_id
1      | CEO       | NULL      | NULL
2      | VP Sales  | CEO       | 1
3      | Sales Mgr | VP Sales  | 2
*/

-- With hierarchy level:
WITH RECURSIVE hierarchy AS (
    -- Base: Top-level (no manager)
    SELECT 
        emp_id,
        emp_name,
        manager_id,
        1 AS level,
        CAST(emp_name AS STRING) AS path
    FROM employees
    WHERE manager_id IS NULL
    
    UNION ALL
    
    -- Recursive: Add employees reporting to current level
    SELECT 
        e.emp_id,
        e.emp_name,
        e.manager_id,
        h.level + 1,
        CONCAT(h.path, ' > ', e.emp_name)
    FROM employees e
    INNER JOIN hierarchy h ON e.manager_id = h.emp_id
)
SELECT 
    emp_id,
    emp_name,
    level,
    path,
    REPEAT('  ', level - 1) || emp_name AS indented_name
FROM hierarchy
ORDER BY path;
```

#### **Pattern 2: Find Pairs with Conditions**

```sql
/*
Problem: Find all pairs of employees in the same department 
with similar salaries (within 10%)

Table: employees (emp_id, dept_id, salary)
*/

SELECT 
    e1.emp_id AS emp1_id,
    e1.emp_name AS emp1_name,
    e2.emp_id AS emp2_id,
    e2.emp_name AS emp2_name,
    e1.salary AS emp1_salary,
    e2.salary AS emp2_salary,
    ABS(e1.salary - e2.salary) AS salary_diff
FROM employees e1
INNER JOIN employees e2 
    ON e1.dept_id = e2.dept_id
    AND e1.emp_id < e2.emp_id  -- Avoid duplicates (A-B = B-A)
    AND ABS(e1.salary - e2.salary) / e1.salary <= 0.10
ORDER BY e1.dept_id, salary_diff;
```

#### **Pattern 3: Detect Overlapping Intervals**

```sql
/*
Problem: Find overlapping meeting rooms bookings

Table: bookings (room_id, start_time, end_time, meeting_name)
*/

SELECT 
    b1.room_id,
    b1.meeting_name AS meeting1,
    b2.meeting_name AS meeting2,
    b1.start_time AS meeting1_start,
    b1.end_time AS meeting1_end,
    b2.start_time AS meeting2_start,
    b2.end_time AS meeting2_end
FROM bookings b1
INNER JOIN bookings b2
    ON b1.room_id = b2.room_id
    AND b1.meeting_name < b2.meeting_name  -- Avoid duplicates
    AND b1.start_time < b2.end_time       -- Overlap condition
    AND b2.start_time < b1.end_time       -- Overlap condition
ORDER BY b1.room_id, b1.start_time;
```

### **4.3 Recursive CTEs (Common Table Expressions)**

**When to use:**
- Tree traversal (org charts, category hierarchies)
- Graph traversal (social networks, dependencies)
- Bill of materials (manufacturing)
- Any parent-child relationship

#### **Complete Recursive CTE Pattern:**

```sql
/*
Generic recursive CTE structure:

WITH RECURSIVE cte_name AS (
    -- BASE CASE (anchor member)
    SELECT ... FROM table WHERE <base_condition>
    
    UNION ALL
    
    -- RECURSIVE CASE (recursive member)
    SELECT ... FROM table 
    JOIN cte_name ON <join_condition>
    WHERE <termination_condition>
)
SELECT * FROM cte_name;
*/

-- Example: Full org chart with all descendants
WITH RECURSIVE org_tree AS (
    -- Base: Start with CEO
    SELECT 
        emp_id,
        emp_name,
        manager_id,
        1 AS level,
        CAST(emp_name AS STRING) AS reporting_chain,
        ARRAY[emp_id] AS path_ids  -- Track path for cycle detection
    FROM employees
    WHERE manager_id IS NULL
    
    UNION ALL
    
    -- Recursive: Add direct reports
    SELECT 
        e.emp_id,
        e.emp_name,
        e.manager_id,
        ot.level + 1,
        CONCAT(ot.reporting_chain, ' → ', e.emp_name),
        ARRAY_APPEND(ot.path_ids, e.emp_id)
    FROM employees e
    INNER JOIN org_tree ot ON e.manager_id = ot.emp_id
    WHERE e.emp_id NOT IN UNNEST(ot.path_ids)  -- Prevent infinite loops
)
SELECT 
    emp_id,
    emp_name,
    level,
    reporting_chain,
    REPEAT('│   ', level - 1) || '├── ' || emp_name AS tree_view
FROM org_tree
ORDER BY reporting_chain;
```

#### **Recursive CTE with Aggregations:**

```sql
/*
Problem: Count total subordinates for each manager
(including indirect reports)
*/

WITH RECURSIVE subordinate_count AS (
    -- Base: All employees
    SELECT 
        emp_id,
        manager_id,
        emp_name,
        0 AS direct_count,
        0 AS total_count
    FROM employees
    
    UNION ALL
    
    SELECT 
        m.emp_id,
        m.manager_id,
        m.emp_name,
        COUNT(e.emp_id) AS direct_count,
        COUNT(e.emp_id) + COALESCE(SUM(sc.total_count), 0) AS total_count
    FROM employees m
    LEFT JOIN employees e ON m.emp_id = e.manager_id
    LEFT JOIN subordinate_count sc ON e.emp_id = sc.emp_id
    GROUP BY m.emp_id, m.manager_id, m.emp_name
)
SELECT 
    emp_name AS manager,
    MAX(direct_count) AS direct_reports,
    MAX(total_count) AS total_subordinates
FROM subordinate_count
GROUP BY emp_id, emp_name
HAVING MAX(direct_count) > 0
ORDER BY total_subordinates DESC;
```

---

## 🔴 PART 5: PIVOTING & UNPIVOTING

### **5.1 Pivoting - Rows to Columns**

**When to use:**
- Creating cross-tabulation reports
- Month/quarter columns from rows
- Transforming normalized data for readability
- Building comparison matrices

#### **Standard Pivot Pattern (CASE WHEN):**

```sql
/*
Problem: Convert monthly sales from rows to columns

Input (long format):
product   | month | sales
Product A | Jan   | 100
Product A | Feb   | 150
Product B | Jan   | 80

Output (wide format):
product   | Jan | Feb | Mar
Product A | 100 | 150 | 200
Product B | 80  | 90  | 110
*/

-- Solution:
SELECT 
    product,
    SUM(CASE WHEN month = 'Jan' THEN sales ELSE 0 END) AS Jan,
    SUM(CASE WHEN month = 'Feb' THEN sales ELSE 0 END) AS Feb,
    SUM(CASE WHEN month = 'Mar' THEN sales ELSE 0 END) AS Mar,
    SUM(CASE WHEN month = 'Apr' THEN sales ELSE 0 END) AS Apr,
    SUM(CASE WHEN month = 'May' THEN sales ELSE 0 END) AS May,
    SUM(CASE WHEN month = 'Jun' THEN sales ELSE 0 END) AS Jun,
    SUM(sales) AS total_sales
FROM sales
GROUP BY product
ORDER BY product;
```

#### **Dynamic Pivot (BigQuery PIVOT):**

```sql
-- BigQuery native PIVOT (SQL 2011 standard)
SELECT *
FROM sales
PIVOT (
    SUM(sales) AS total_sales
    FOR month IN ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun')
)
ORDER BY product;

-- With multiple aggregations:
SELECT *
FROM sales
PIVOT (
    SUM(sales) AS total,
    AVG(sales) AS average,
    COUNT(*) AS count
    FOR month IN ('Jan', 'Feb', 'Mar')
)
ORDER BY product;
```

#### **Pivot with Multiple Dimensions:**

```sql
/*
Problem: Pivot by both month AND metric type

Output:
product   | Jan_sales | Jan_quantity | Feb_sales | Feb_quantity
Product A | 100       | 10           | 150       | 15
*/

SELECT 
    product,
    SUM(CASE WHEN month = 'Jan' THEN sales ELSE 0 END) AS Jan_sales,
    SUM(CASE WHEN month = 'Jan' THEN quantity ELSE 0 END) AS Jan_quantity,
    SUM(CASE WHEN month = 'Feb' THEN sales ELSE 0 END) AS Feb_sales,
    SUM(CASE WHEN month = 'Feb' THEN quantity ELSE 0 END) AS Feb_quantity
FROM sales
GROUP BY product;
```

### **5.2 Unpivoting - Columns to Rows**

**When to use:**
- Normalizing wide-format data
- Converting Excel-like structure to database format
- Preparing data for analysis/graphing
- Standardizing inconsistent schemas

#### **Standard Unpivot Pattern (UNION ALL):**

```sql
/*
Problem: Convert columns to rows

Input (wide format):
product   | Jan | Feb | Mar
Product A | 100 | 150 | 200
Product B | 80  | 90  | 110

Output (long format):
product   | month | sales
Product A | Jan   | 100
Product A | Feb   | 150
Product A | Mar   | 200
Product B | Jan   | 80
...
*/

-- Solution using UNION ALL:
SELECT product, 'Jan' AS month, Jan AS sales FROM product_sales
UNION ALL
SELECT product, 'Feb' AS month, Feb AS sales FROM product_sales
UNION ALL
SELECT product, 'Mar' AS month, Mar AS sales FROM product_sales
UNION ALL
SELECT product, 'Apr' AS month, Apr AS sales FROM product_sales
WHERE sales IS NOT NULL  -- Optional: exclude null values
ORDER BY product, month;
```

#### **Unpivot using CROSS JOIN:**

```sql
-- More elegant solution using CROSS JOIN
SELECT 
    product,
    month_name AS month,
    CASE month_name
        WHEN 'Jan' THEN Jan
        WHEN 'Feb' THEN Feb
        WHEN 'Mar' THEN Mar
        WHEN 'Apr' THEN Apr
    END AS sales
FROM product_sales
CROSS JOIN UNNEST(['Jan', 'Feb', 'Mar', 'Apr']) AS month_name
WHERE CASE month_name
    WHEN 'Jan' THEN Jan
    WHEN 'Feb' THEN Feb
    WHEN 'Mar' THEN Mar
    WHEN 'Apr' THEN Apr
END IS NOT NULL
ORDER BY product, month;
```

#### **BigQuery UNPIVOT (Native):**

```sql
-- BigQuery native UNPIVOT
SELECT product, month, sales
FROM product_sales
UNPIVOT (
    sales FOR month IN (Jan, Feb, Mar, Apr, May, Jun)
)
ORDER BY product, month;

-- Unpivot multiple value columns:
SELECT product, month, metric_name, metric_value
FROM product_metrics
UNPIVOT (
    metric_value FOR metric_name IN (sales AS 'Sales', quantity AS 'Quantity', profit AS 'Profit')
)
ORDER BY product, month, metric_name;
```

---

## 🟣 PART 6: ADVANCED AGGREGATIONS

### **6.1 Conditional Aggregation (CASE WHEN)**

**When to use:**
- Count/sum different categories separately
- Calculate multiple metrics in one pass
- Create derived metrics based on conditions

```sql
/*
Problem: Calculate success/failure metrics for notifications

Table: notifications (id, status, type, sent_date)
*/

SELECT 
    DATE(sent_date) AS date,
    type,
    COUNT(*) AS total,
    SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS delivered,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS delivery_rate_pct
FROM notifications
GROUP BY DATE(sent_date), type
ORDER BY date, type;

-- Alternative using COUNTIF (BigQuery specific):
SELECT 
    DATE(sent_date) AS date,
    COUNT(*) AS total,
    COUNTIF(status = 'delivered') AS delivered,
    COUNTIF(status = 'failed') AS failed,
    ROUND(100.0 * COUNTIF(status = 'delivered') / COUNT(*), 2) AS delivery_rate_pct
FROM notifications
GROUP BY date;
```

### **6.2 FILTER Clause (Standard SQL)**

```sql
-- More readable alternative to CASE WHEN
SELECT 
    product,
    COUNT(*) AS total_sales,
    SUM(amount) FILTER (WHERE region = 'North') AS north_sales,
    SUM(amount) FILTER (WHERE region = 'South') AS south_sales,
    AVG(amount) FILTER (WHERE amount > 1000) AS avg_large_sales
FROM sales
GROUP BY product;
```

### **6.3 Percentiles and Quantiles**

```sql
/*
Calculate salary percentiles by department
*/

-- Method 1: PERCENTILE_CONT (continuous, interpolates)
SELECT 
    department,
    PERCENTILE_CONT(salary, 0.25) OVER (PARTITION BY department) AS p25,
    PERCENTILE_CONT(salary, 0.50) OVER (PARTITION BY department) AS median,
    PERCENTILE_CONT(salary, 0.75) OVER (PARTITION BY department) AS p75,
    PERCENTILE_CONT(salary, 0.90) OVER (PARTITION BY department) AS p90
FROM employees;

-- Method 2: APPROX_QUANTILES (BigQuery, faster for large datasets)
SELECT 
    department,
    APPROX_QUANTILES(salary, 4) AS quartiles,  -- Returns array [min, Q1, Q2, Q3, max]
    APPROX_QUANTILES(salary, 4)[OFFSET(1)] AS q1,
    APPROX_QUANTILES(salary, 4)[OFFSET(2)] AS median,
    APPROX_QUANTILES(salary, 4)[OFFSET(3)] AS q3
FROM employees
GROUP BY department;
```

---

## 🟡 PART 7: DATE & TIME PATTERNS

### **7.1 Date Ranges and Series Generation**

```sql
-- Generate date series (BigQuery)
SELECT date
FROM UNNEST(GENERATE_DATE_ARRAY('2024-01-01', '2024-12-31', INTERVAL 1 DAY)) AS date;

-- Generate time series with specific intervals
SELECT timestamp
FROM UNNEST(GENERATE_TIMESTAMP_ARRAY(
    '2024-01-01 00:00:00',
    '2024-01-01 23:59:59',
    INTERVAL 1 HOUR
)) AS timestamp;

-- Find missing dates in activity log
WITH all_dates AS (
    SELECT date
    FROM UNNEST(GENERATE_DATE_ARRAY('2024-01-01', '2024-01-31', INTERVAL 1 DAY)) AS date
)
SELECT 
    ad.date,
    COALESCE(COUNT(a.activity_id), 0) AS activity_count
FROM all_dates ad
LEFT JOIN activities a ON DATE(a.activity_date) = ad.date
GROUP BY ad.date
ORDER BY ad.date;
```

### **7.2 Date Bucketing and Truncation**

```sql
SELECT 
    -- Various date truncations
    DATE_TRUNC(order_date, YEAR) AS year,
    DATE_TRUNC(order_date, QUARTER) AS quarter,
    DATE_TRUNC(order_date, MONTH) AS month,
    DATE_TRUNC(order_date, WEEK) AS week,
    DATE_TRUNC(order_date, DAY) AS day,
    
    -- Extract components
    EXTRACT(YEAR FROM order_date) AS year_num,
    EXTRACT(MONTH FROM order_date) AS month_num,
    EXTRACT(DAY FROM order_date) AS day_num,
    EXTRACT(DAYOFWEEK FROM order_date) AS dow,  -- 1=Sunday, 7=Saturday
    EXTRACT(DAYOFYEAR FROM order_date) AS doy,
    
    -- Formatting
    FORMAT_DATE('%Y-%m', order_date) AS year_month,
    FORMAT_DATE('%Y-Q%Q', order_date) AS year_quarter,
    FORMAT_DATE('%A', order_date) AS day_name,
    
    COUNT(*) AS orders
FROM orders
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13;
```

### **7.3 Time-Based Cohort Analysis**

```sql
/*
Calculate monthly cohort retention

Cohort = month of first purchase
Retention = purchases in subsequent months
*/

WITH first_purchase AS (
    SELECT 
        user_id,
        DATE_TRUNC(MIN(purchase_date), MONTH) AS cohort_month
    FROM purchases
    GROUP BY user_id
),
purchases_with_cohort AS (
    SELECT 
        p.user_id,
        fp.cohort_month,
        DATE_TRUNC(p.purchase_date, MONTH) AS purchase_month,
        DATE_DIFF(
            DATE_TRUNC(p.purchase_date, MONTH),
            fp.cohort_month,
            MONTH
        ) AS month_number
    FROM purchases p
    JOIN first_purchase fp ON p.user_id = fp.user_id
)
SELECT 
    cohort_month,
    month_number,
    COUNT(DISTINCT user_id) AS active_users,
    ROUND(
        100.0 * COUNT(DISTINCT user_id) / 
        FIRST_VALUE(COUNT(DISTINCT user_id)) OVER (
            PARTITION BY cohort_month 
            ORDER BY month_number
        ),
        2
    ) AS retention_rate
FROM purchases_with_cohort
GROUP BY cohort_month, month_number
ORDER BY cohort_month, month_number;
```

---

## 🔵 PART 8: RANKING & TOP-N PATTERNS

### **8.1 Top N Per Group - Complete Guide**

```sql
/*
Standard Pattern: Top 3 products by revenue in each category
*/

-- Method 1: ROW_NUMBER (Most common)
SELECT 
    category,
    product_name,
    revenue,
    rank
FROM (
    SELECT 
        category,
        product_name,
        revenue,
        ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC) AS rank
    FROM products
) ranked
WHERE rank <= 3;

-- Method 2: QUALIFY (BigQuery - cleaner!)
SELECT 
    category,
    product_name,
    revenue,
    ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC) AS rank
FROM products
QUALIFY rank <= 3;

-- Method 3: Correlated subquery (older style)
SELECT p1.*
FROM products p1
WHERE (
    SELECT COUNT(*)
    FROM products p2
    WHERE p2.category = p1.category
      AND p2.revenue >= p1.revenue
) <= 3;
```

### **8.2 Finding Second/Nth Highest Value**

```sql
-- Second highest salary per department
SELECT 
    department,
    salary
FROM (
    SELECT 
        department,
        salary,
        DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS rank
    FROM employees
)
WHERE rank = 2;

-- Nth highest (e.g., 5th highest)
SELECT 
    department,
    NTH_VALUE(salary, 5) OVER (
        PARTITION BY department 
        ORDER BY salary DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS fifth_highest
FROM employees
QUALIFY ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) = 1;
```

---

## 🟠 PART 9: DEDUPLICATION STRATEGIES

### **9.1 Complete Deduplication Guide**

```sql
/*
Scenario: Remove duplicate user records, keep the latest
Table: users (user_id, email, updated_at, data)
*/

-- Method 1: ROW_NUMBER (Most flexible)
SELECT 
    user_id,
    email,
    updated_at,
    data
FROM (
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY email 
            ORDER BY updated_at DESC, user_id DESC
        ) AS rn
    FROM users
) ranked
WHERE rn = 1;

-- Method 2: QUALIFY (BigQuery)
SELECT 
    user_id,
    email,
    updated_at,
    data
FROM users
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY email 
    ORDER BY updated_at DESC
) = 1;

-- Method 3: DISTINCT ON (PostgreSQL)
SELECT DISTINCT ON (email)
    user_id,
    email,
    updated_at,
    data
FROM users
ORDER BY email, updated_at DESC;

-- Method 4: GROUP BY + aggregation (when you just need one column)
SELECT 
    email,
    MAX(updated_at) AS latest_update,
    ARRAY_AGG(user_id ORDER BY updated_at DESC LIMIT 1)[OFFSET(0)] AS latest_user_id
FROM users
GROUP BY email;
```

### **9.2 Identifying Duplicates Before Removal**

```sql
-- Find all duplicate emails with counts
SELECT 
    email,
    COUNT(*) AS duplicate_count,
    ARRAY_AGG(user_id ORDER BY updated_at DESC) AS all_user_ids,
    MAX(updated_at) AS latest_update
FROM users
GROUP BY email
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;

-- Mark duplicates for review
SELECT 
    user_id,
    email,
    updated_at,
    ROW_NUMBER() OVER (PARTITION BY email ORDER BY updated_at DESC) AS version_rank,
    CASE 
        WHEN ROW_NUMBER() OVER (PARTITION BY email ORDER BY updated_at DESC) = 1 
        THEN 'KEEP'
        ELSE 'DELETE'
    END AS action
FROM users
WHERE email IN (
    SELECT email 
    FROM users 
    GROUP BY email 
    HAVING COUNT(*) > 1
)
ORDER BY email, updated_at DESC;
```

---

## 🔴 PART 10: LEAD & LAG DEEP DIVE

### **10.1 Complete LAG/LEAD Patterns**

```sql
/*
Compare current row with previous/next values
*/

SELECT 
    date,
    metric_value,
    
    -- Previous values (different offsets)
    LAG(metric_value, 1) OVER (ORDER BY date) AS prev_day,
    LAG(metric_value, 7) OVER (ORDER BY date) AS prev_week,
    LAG(metric_value, 30) OVER (ORDER BY date) AS prev_month,
    
    -- Next values
    LEAD(metric_value, 1) OVER (ORDER BY date) AS next_day,
    
    -- Calculations with LAG
    metric_value - LAG(metric_value) OVER (ORDER BY date) AS day_over_day_change,
    ROUND(
        100.0 * (metric_value - LAG(metric_value) OVER (ORDER BY date)) / 
        NULLIF(LAG(metric_value) OVER (ORDER BY date), 0),
        2
    ) AS day_over_day_pct,
    
    -- Default value when LAG returns NULL
    COALESCE(
        metric_value - LAG(metric_value) OVER (ORDER BY date),
        0
    ) AS change_with_default
FROM metrics
ORDER BY date;
```

### **10.2 Sessionization Using LAG**

```sql
/*
Create user sessions based on 30-minute inactivity gaps
*/

WITH time_gaps AS (
    SELECT 
        user_id,
        event_time,
        LAG(event_time) OVER (
            PARTITION BY user_id 
            ORDER BY event_time
        ) AS prev_event_time,
        TIMESTAMP_DIFF(
            event_time,
            LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time),
            MINUTE
        ) AS minutes_since_last_event
    FROM user_events
),
session_starts AS (
    SELECT 
        user_id,
        event_time,
        CASE 
            WHEN minutes_since_last_event IS NULL 
                OR minutes_since_last_event > 30 
            THEN 1 
            ELSE 0 
        END AS is_session_start
    FROM time_gaps
),
sessions AS (
    SELECT 
        user_id,
        event_time,
        SUM(is_session_start) OVER (
            PARTITION BY user_id 
            ORDER BY event_time
        ) AS session_id
    FROM session_starts
)
SELECT 
    user_id,
    session_id,
    MIN(event_time) AS session_start,
    MAX(event_time) AS session_end,
    COUNT(*) AS events_in_session,
    TIMESTAMP_DIFF(MAX(event_time), MIN(event_time), MINUTE) AS session_duration_minutes
FROM sessions
GROUP BY user_id, session_id
ORDER BY user_id, session_start;
```

---

## 🟢 PART 11: PERFORMANCE OPTIMIZATION PATTERNS

### **11.1 Query Optimization Checklist**

```sql
-- ❌ BAD: Full table scan
SELECT * FROM large_table WHERE YEAR(date_col) = 2024;

-- ✅ GOOD: Allows partition pruning
SELECT * FROM large_table WHERE date_col >= '2024-01-01' AND date_col < '2025-01-01';

-- ❌ BAD: Function on indexed column
SELECT * FROM users WHERE LOWER(email) = 'user@example.com';

-- ✅ GOOD: Direct comparison
SELECT * FROM users WHERE email = 'user@example.com';

-- ❌ BAD: Implicit type conversion
SELECT * FROM orders WHERE order_id = '12345';  -- order_id is INT

-- ✅ GOOD: Correct types
SELECT * FROM orders WHERE order_id = 12345;

-- ❌ BAD: NOT IN with NULL values
SELECT * FROM table1 WHERE id NOT IN (SELECT id FROM table2);

-- ✅ GOOD: NOT EXISTS or LEFT JOIN
SELECT * FROM table1 t1
WHERE NOT EXISTS (SELECT 1 FROM table2 t2 WHERE t2.id = t1.id);
```

### **11.2 Join Optimization**

```sql
-- Filter before join (push down predicates)
-- ✅ GOOD
SELECT e.*, d.dept_name
FROM (
    SELECT * FROM employees WHERE salary > 50000
) e
JOIN departments d ON e.dept_id = d.dept_id;

-- Avoid Cartesian products
-- ❌ BAD: Missing join condition
SELECT * FROM table1, table2 WHERE table1.value > 100;

-- ✅ GOOD: Explicit join
SELECT * FROM table1 
JOIN table2 ON table1.id = table2.id 
WHERE table1.value > 100;
```

---

## 🟣 PART 12: REAL-WORLD COMPLETE SCENARIOS

### **12.1 Funnel Analysis**

```sql
/*
Calculate conversion funnel: View → Cart → Purchase

Output: Step name, users, conversion rate, drop-off
*/

WITH funnel_steps AS (
    SELECT 
        user_id,
        MAX(CASE WHEN event_type = 'page_view' THEN 1 ELSE 0 END) AS viewed,
        MAX(CASE WHEN event_type = 'add_to_cart' THEN 1 ELSE 0 END) AS carted,
        MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS purchased
    FROM events
    WHERE event_date >= CURRENT_DATE - 30
    GROUP BY user_id
),
step_counts AS (
    SELECT 
        SUM(viewed) AS step1_view,
        SUM(carted) AS step2_cart,
        SUM(purchased) AS step3_purchase
    FROM funnel_steps
)
SELECT 'Step 1: View' AS step, step1_view AS users, 
    100.00 AS conversion, 0.00 AS dropoff FROM step_counts
UNION ALL
SELECT 'Step 2: Cart', step2_cart,
    ROUND(100.0 * step2_cart / step1_view, 2),
    ROUND(100.0 * (step1_view - step2_cart) / step1_view, 2) FROM step_counts
UNION ALL
SELECT 'Step 3: Purchase', step3_purchase,
    ROUND(100.0 * step3_purchase / step1_view, 2),
    ROUND(100.0 * (step2_cart - step3_purchase) / step2_cart, 2) FROM step_counts;
```

### **12.2 Customer Lifetime Value (CLV)**

```sql
/*
Calculate CLV by customer cohort
*/

WITH customer_cohorts AS (
    SELECT 
        customer_id,
        DATE_TRUNC(MIN(order_date), MONTH) AS cohort_month
    FROM orders
    GROUP BY customer_id
),
customer_revenue AS (
    SELECT 
        c.customer_id,
        c.cohort_month,
        SUM(o.amount) AS total_revenue,
        COUNT(o.order_id) AS total_orders,
        MAX(o.order_date) AS last_order_date
    FROM customer_cohorts c
    JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.cohort_month
)
SELECT 
    cohort_month,
    COUNT(customer_id) AS cohort_size,
    ROUND(AVG(total_revenue), 2) AS avg_clv,
    ROUND(AVG(total_orders), 2) AS avg_orders_per_customer,
    ROUND(SUM(total_revenue) / COUNT(customer_id), 2) AS clv_per_customer
FROM customer_revenue
GROUP BY cohort_month
ORDER BY cohort_month;
```

---

## 🎓 SUMMARY: QUICK DECISION MATRIX

```
NEED TO... → USE THIS PATTERN → KEY FUNCTION
├─ Find consecutive sequences → Gaps & Islands → ROW_NUMBER + DATE arithmetic
├─ Compare to previous row → LAG/LEAD → LAG(col) OVER (ORDER BY)
├─ Running total → Window SUM → SUM() OVER (ORDER BY)
├─ Moving average → Window AVG with frame → AVG() OVER (ROWS BETWEEN)
├─ Top N per group → ROW_NUMBER + filter → ROW_NUMBER() OVER (PARTITION BY)
├─ Rows to columns → Pivot → CASE WHEN + GROUP BY or PIVOT
├─ Columns to rows → Unpivot → UNION ALL or UNPIVOT
├─ Remove duplicates → Deduplication → ROW_NUMBER() = 1
├─ Hierarchies → Recursive CTE → WITH RECURSIVE
├─ Percentiles → Quantiles → PERCENTILE_CONT or APPROX_QUANTILES
├─ Conditional counts → Conditional Agg → SUM(CASE WHEN) or COUNTIF
└─ Time-based grouping → Date bucketing → DATE_TRUNC or EXTRACT
```

---

## 📖 INTERVIEW STRATEGY

**When given a SQL problem:**

1. **Identify the pattern** (use keywords from question)
2. **Choose the right tool** (window function vs GROUP BY vs CTE)
3. **Start simple** (basic query first)
4. **Add complexity** (window functions, CTEs, aggregations)
5. **Optimize** (explain performance considerations)
6. **Test edge cases** (NULLs, empty results, boundaries)

**Always explain:**
- Why you chose this approach
- What alternatives exist
- Performance implications
- Edge cases handled

---

**STATUS:** Complete! 🎉

This guide covers EVERY major SQL pattern needed for senior data engineer interviews. Use the pattern recognition framework at the start to quickly identify which approach to use for any question.
