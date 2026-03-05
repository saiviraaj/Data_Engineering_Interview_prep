# SQL Interview Questions - Non-FAANG Level

Complete collection of SQL interview questions with detailed explanations, solutions, and real-world context.

---

## Table of Contents
1. [Easy Questions (1-10)](#easy-questions)
2. [Medium Questions (11-22)](#medium-questions)
3. [Hard Questions (23-30)](#hard-questions)

---

# EASY QUESTIONS

## Question 1: Basic SELECT and Filtering

**Difficulty:** Easy  
**Time to Solve:** 5 minutes  
**Topics:** SELECT, WHERE, Basic Filtering  
**Frequency in Interviews:** Very High

### Problem Statement

Write a SQL query to find all employees with salary greater than $50,000.

**Table: employees**
```
id | name | salary | department
1  | John | 55000  | Sales
2  | Jane | 48000  | IT
3  | Bob  | 60000  | Sales
4  | Alice| 45000  | HR
```

### Solution

```sql
SELECT * 
FROM employees 
WHERE salary > 50000;
```

### Result
```
id | name | salary | department
1  | John | 55000  | Sales
3  | Bob  | 60000  | Sales
```

### Complexity Analysis
- Time: O(n) - Must scan all rows
- Space: O(k) - Where k is result set size

### Key Interview Points

✅ **What interviewers look for:**
- Correct WHERE clause syntax
- Understanding of comparison operators
- Ability to filter data correctly

✅ **Interview Tips:**
- Always specify which columns you need (avoid SELECT *)
- Clearly state filtering conditions
- Verify your WHERE clause logic

### Follow-up 1: Can you find employees with salary between $45,000 and $55,000?

```sql
SELECT * 
FROM employees 
WHERE salary BETWEEN 45000 AND 55000;

-- OR

SELECT * 
FROM employees 
WHERE salary >= 45000 AND salary <= 55000;
```

### Follow-up 2: Find employees NOT in the Sales department

```sql
SELECT * 
FROM employees 
WHERE department != 'Sales';
-- OR
WHERE department <> 'Sales';
```

### Common Mistakes

❌ **Mistake 1:** Using `=` for comparison instead of comparison operators
```sql
SELECT * FROM employees WHERE salary;  -- WRONG! Incomplete
```

❌ **Mistake 2:** Forgetting quotes around string values
```sql
SELECT * FROM employees WHERE department = Sales;  -- WRONG! Will error
```

✅ **Correct:** Always use quotes for string values and correct operators

### Real Interview Scenario

**Interviewer:** "Write a query to get all active customers with order value > $100"

**Candidate approach:**
1. Identify tables needed
2. Understand filtering conditions
3. Write WHERE clause correctly
4. Test mentally with sample data

---

## Question 2: JOIN - INNER JOIN

**Difficulty:** Easy  
**Time to Solve:** 7 minutes  
**Topics:** INNER JOIN, Combining Tables  
**Frequency:** Very High

### Problem Statement

Write a query to find all orders with customer names. Return order_id, customer_name, and order_amount.

**Table: customers**
```
customer_id | name
1          | John
2          | Jane
3          | Bob
```

**Table: orders**
```
order_id | customer_id | amount
101      | 1           | 500
102      | 2           | 750
103      | 1           | 600
```

### Solution

```sql
SELECT 
  o.order_id,
  c.name AS customer_name,
  o.amount
FROM orders o
INNER JOIN customers c ON o.customer_id = c.customer_id;
```

### Result
```
order_id | customer_name | amount
101      | John          | 500
102      | Jane          | 750
103      | John          | 600
```

### Complexity Analysis
- Time: O(n*m) - Depends on join algorithm
- Space: O(k) - Result set size

### Key Points

✅ **Critical Points:**
- INNER JOIN returns only matching records
- Use ON clause for join condition
- Use aliases to improve readability

✅ **Best Practices:**
- Always use table aliases (a, b, c)
- Qualify column names with alias (o.order_id)
- Order matters in ON clause logic

### Follow-up 1: Include all customers even if they have no orders (LEFT JOIN)

```sql
SELECT 
  c.customer_id,
  c.name,
  o.order_id,
  o.amount
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id;
```

### Follow-up 2: Join with a WHERE clause to filter

```sql
SELECT 
  o.order_id,
  c.name,
  o.amount
FROM orders o
INNER JOIN customers c ON o.customer_id = c.customer_id
WHERE o.amount > 600;
```

### Common Mistakes

❌ **Mistake:** Forgetting the join condition
```sql
SELECT o.*, c.* FROM orders o JOIN customers c;  -- CROSS JOIN! Wrong!
```

❌ **Mistake:** Using WHERE instead of ON for join
```sql
SELECT * FROM orders, customers WHERE orders.customer_id = customers.customer_id;
-- Works but bad practice, mixing JOIN and WHERE
```

✅ **Correct:** Use ON clause for joins, WHERE for filtering

---

## Question 3: GROUP BY and Aggregate Functions

**Difficulty:** Easy  
**Time to Solve:** 8 minutes  
**Topics:** GROUP BY, COUNT, SUM, AVG, MAX, MIN

### Problem Statement

Find the total amount spent by each customer.

### Solution

```sql
SELECT 
  c.name,
  SUM(o.amount) AS total_spent,
  COUNT(o.order_id) AS number_of_orders
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name;
```

### Result
```
name | total_spent | number_of_orders
John | 1100        | 2
Jane | 750         | 1
Bob  | NULL        | 0
```

### Complexity Analysis
- Time: O(n log n) - Due to grouping
- Space: O(k) - Number of groups

### Key Points

✅ **GROUP BY Rules:**
- All non-aggregated columns must be in GROUP BY
- Can aggregate with SUM, COUNT, AVG, MAX, MIN
- NULL in GROUP BY becomes its own group

✅ **Interview Tips:**
- Explain why each column is in GROUP BY
- Test with NULL values
- Verify aggregation logic

### Follow-up 1: Filter groups using HAVING

```sql
SELECT 
  c.name,
  SUM(o.amount) AS total_spent
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
HAVING SUM(o.amount) > 500;
```

### Follow-up 2: Order results by total

```sql
SELECT 
  c.name,
  SUM(o.amount) AS total_spent
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
ORDER BY total_spent DESC;
```

### Common Mistakes

❌ **Mistake:** Including non-aggregated column not in GROUP BY
```sql
SELECT c.name, o.amount, SUM(o.amount)  -- ERROR! o.amount not in GROUP BY
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.name;
```

✅ **Fix:** Either add column to GROUP BY or aggregate it

---

## Question 4: ORDER BY and LIMIT

**Difficulty:** Easy  
**Time to Solve:** 5 minutes  
**Topics:** ORDER BY, LIMIT, TOP N records

### Problem Statement

Get the top 5 highest-paid employees.

### Solution

```sql
SELECT 
  name,
  salary
FROM employees
ORDER BY salary DESC
LIMIT 5;
```

### Key Points

✅ **ORDER BY Syntax:**
- DESC = Descending (highest first)
- ASC = Ascending (lowest first, default)
- Can order by multiple columns

✅ **LIMIT Syntax:**
- LIMIT 5 = Return first 5 rows
- LIMIT 5 OFFSET 10 = Skip 10, return next 5 (pagination)

### Follow-up: Paginate results (rows 11-20)

```sql
SELECT * 
FROM employees
ORDER BY salary DESC
LIMIT 10 OFFSET 10;  -- Skip 10, get next 10
```

---

## Question 5: DISTINCT

**Difficulty:** Easy  
**Time to Solve:** 5 minutes  
**Topics:** DISTINCT, Removing Duplicates

### Problem Statement

Find all unique departments in the company.

### Solution

```sql
SELECT DISTINCT department
FROM employees
ORDER BY department;
```

### Key Points

✅ **DISTINCT behavior:**
- Removes duplicate rows
- Works with multiple columns: DISTINCT col1, col2
- Can be expensive on large datasets

✅ **Performance Note:**
- DISTINCT requires sorting/hashing
- Avoid if possible; filter at source instead

---

## Question 6-10: Practice Questions

### Question 6: COUNT distinct values

```
Find number of unique customers who placed orders.

SELECT COUNT(DISTINCT customer_id) AS unique_customers
FROM orders;
```

### Question 7: LIKE for pattern matching

```
Find all employees whose name starts with 'J'

SELECT * FROM employees WHERE name LIKE 'J%';
```

### Question 8: IN clause

```
Find employees in Sales or IT departments

SELECT * FROM employees 
WHERE department IN ('Sales', 'IT');
```

### Question 9: NULL handling

```
Find employees with no assigned department

SELECT * FROM employees WHERE department IS NULL;
```

### Question 10: CASE statement

```
Categorize employees by salary

SELECT 
  name,
  salary,
  CASE 
    WHEN salary > 60000 THEN 'High'
    WHEN salary > 45000 THEN 'Medium'
    ELSE 'Low'
  END AS salary_level
FROM employees;
```

---

# MEDIUM QUESTIONS

## Question 11: Window Functions - ROW_NUMBER

**Difficulty:** Medium  
**Time to Solve:** 15 minutes  
**Topics:** Window Functions, ROW_NUMBER, Ranking  
**Frequency:** High in data roles

### Problem Statement

Rank employees by salary within each department. Get top earner in each dept.

### Solution

```sql
WITH ranked_employees AS (
  SELECT 
    name,
    department,
    salary,
    ROW_NUMBER() OVER (
      PARTITION BY department 
      ORDER BY salary DESC
    ) AS rank
  FROM employees
)
SELECT *
FROM ranked_employees
WHERE rank = 1;
```

### Explanation

```
ROW_NUMBER():
- Assigns unique number within partition
- PARTITION BY = Define groups
- ORDER BY = How to number within groups

Example output:
name  | department | salary | rank
Bob   | Sales      | 60000  | 1  (highest in Sales)
Alice | IT         | 55000  | 1  (highest in IT)
```

### Key Window Function Points

✅ **Window Functions:**
- ROW_NUMBER(): Unique numbers (1,2,3...)
- RANK(): With ties (1,2,2,4...)
- DENSE_RANK(): No gaps (1,2,2,3...)
- LAG/LEAD: Previous/next row values
- SUM/AVG OVER: Running totals

### Follow-up 1: Get top 2 earners per department

```sql
WITH ranked AS (
  SELECT 
    name, department, salary,
    ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS rank
  FROM employees
)
SELECT * FROM ranked WHERE rank <= 2;
```

### Common Mistakes

❌ **Mistake:** Forgetting PARTITION BY
```sql
SELECT *, ROW_NUMBER() OVER (ORDER BY salary DESC) FROM employees;
-- This ranks ALL employees, ignores department
```

✅ **Correct:** Always use PARTITION BY for group-level ranking

---

## Question 12: CTE (Common Table Expression)

**Difficulty:** Medium  
**Time to Solve:** 12 minutes  
**Topics:** WITH clause, CTEs, Code readability

### Problem Statement

Find customers who spent more than the average customer spending.

### Solution

```sql
WITH customer_spending AS (
  SELECT 
    c.customer_id,
    c.name,
    SUM(o.amount) AS total_spent
  FROM customers c
  LEFT JOIN orders o ON c.customer_id = o.customer_id
  GROUP BY c.customer_id, c.name
),
average_spending AS (
  SELECT AVG(total_spent) AS avg_spent
  FROM customer_spending
)
SELECT 
  cs.name,
  cs.total_spent,
  ROUND((cs.total_spent - avgs.avg_spent), 2) AS above_average
FROM customer_spending cs
CROSS JOIN average_spending avgs
WHERE cs.total_spent > avgs.avg_spent
ORDER BY cs.total_spent DESC;
```

### Benefits of CTEs

✅ **Why use CTEs:**
- More readable than nested subqueries
- Reuse same CTE multiple times
- Easier to debug step by step
- Clear logical flow

### Follow-up: Using recursive CTE (hierarchy)

```sql
WITH RECURSIVE employee_hierarchy AS (
  -- Base case: employees with no manager
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
    eh.level + 1
  FROM employees e
  JOIN employee_hierarchy eh ON e.manager_id = eh.employee_id
  WHERE eh.level < 10
)
SELECT * FROM employee_hierarchy ORDER BY level, name;
```

---

## Question 13: Subquery vs JOIN

**Difficulty:** Medium  
**Time to Solve:** 15 minutes  
**Topics:** Subqueries, JOINs, Query optimization

### Problem Statement

Find all orders for customers who are in the 'Premium' tier.

**Subquery approach:**

```sql
SELECT *
FROM orders
WHERE customer_id IN (
  SELECT customer_id 
  FROM customers 
  WHERE tier = 'Premium'
);
```

**JOIN approach:**

```sql
SELECT o.*
FROM orders o
INNER JOIN customers c ON o.customer_id = c.customer_id
WHERE c.tier = 'Premium';
```

### Performance Comparison

| Aspect | Subquery | JOIN |
|--------|----------|------|
| Readability | More explicit | More efficient |
| Performance | Slower (dependent subquery) | Faster (set-based) |
| Flexibility | Good for exists check | Better for complex joins |
| Scalability | Degrades with size | Better at scale |

### Key Interview Points

✅ **When to use subqueries:**
- EXISTS checks
- Simple filters
- One-level nesting

✅ **When to use JOINs:**
- Multiple tables
- Complex logic
- Performance critical

### Common Mistakes

❌ **Mistake:** Using IN with NULL
```sql
SELECT * FROM orders WHERE customer_id IN (SELECT customer_id FROM customers WHERE status IS NULL);
-- Will return NO rows even if matches exist!
```

✅ **Fix:** Use EXISTS or handle NULL explicitly
```sql
SELECT * FROM orders WHERE EXISTS (
  SELECT 1 FROM customers c WHERE c.customer_id = o.customer_id AND c.status IS NULL
);
```

---

## Question 14-22: Medium Practice Questions

### Question 14: UNION vs UNION ALL

```sql
-- Combine two result sets
SELECT name FROM employees
UNION
SELECT name FROM contractors;

-- UNION: Removes duplicates (slower)
-- UNION ALL: Keeps duplicates (faster)
```

### Question 15: Self JOIN

```sql
-- Find pairs of employees in same department
SELECT 
  e1.name AS emp1,
  e2.name AS emp2,
  e1.department
FROM employees e1
JOIN employees e2 ON e1.department = e2.department 
  AND e1.employee_id < e2.employee_id;
```

### Question 16: Multiple aggregations

```sql
-- Get stats for each product
SELECT 
  product_id,
  COUNT(*) AS num_orders,
  SUM(quantity) AS total_qty,
  AVG(price) AS avg_price,
  MAX(price) AS max_price,
  MIN(price) AS min_price
FROM order_items
GROUP BY product_id
HAVING COUNT(*) > 10
ORDER BY total_qty DESC;
```

### Question 17: String functions

```sql
-- Extract and format data
SELECT 
  UPPER(name) AS uppercase_name,
  LOWER(email) AS lowercase_email,
  LENGTH(phone) AS phone_length,
  SUBSTRING(name, 1, 3) AS first_three
FROM customers;
```

### Question 18: Date functions

```sql
-- Filter and calculate dates
SELECT 
  order_id,
  order_date,
  DATEDIFF(NOW(), order_date) AS days_old,
  DATE_ADD(order_date, INTERVAL 30 DAY) AS delivery_date
FROM orders
WHERE order_date >= DATE_SUB(NOW(), INTERVAL 90 DAY);
```

### Question 19: CASE with aggregation

```sql
-- Calculate metrics by category
SELECT 
  product_category,
  SUM(CASE WHEN status = 'Completed' THEN amount ELSE 0 END) AS completed_amount,
  SUM(CASE WHEN status = 'Pending' THEN amount ELSE 0 END) AS pending_amount,
  COUNT(CASE WHEN status = 'Cancelled' THEN 1 END) AS cancelled_count
FROM orders
GROUP BY product_category;
```

### Question 20: Multiple JOINs

```sql
-- Combine 3+ tables
SELECT 
  o.order_id,
  c.name AS customer,
  p.product_name,
  oi.quantity,
  oi.price
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE o.order_date >= '2024-01-01';
```

### Question 21: NOT IN with multiple conditions

```sql
-- Complex filtering
SELECT * FROM employees
WHERE department NOT IN ('Admin', 'Finance')
  AND salary > 50000
  AND hire_date >= '2020-01-01';
```

### Question 22: COALESCE for NULL handling

```sql
-- Handle NULL values
SELECT 
  customer_id,
  COALESCE(phone, email, 'No contact') AS primary_contact,
  COALESCE(middle_name, '') AS middle,
  COALESCE(discount_pct, 0) AS discount
FROM customers;
```

---

# HARD QUESTIONS

## Question 23: Pivot/Cross-Tab Query

**Difficulty:** Hard  
**Time to Solve:** 20 minutes  
**Topics:** Conditional aggregation, CASE with GROUP BY

### Problem Statement

Create a monthly sales report showing sales by product category.

**Input:**
```
date       | category  | amount
2024-01-05 | Electronics| 500
2024-01-10 | Clothing  | 200
2024-02-05 | Electronics| 600
2024-02-10 | Clothing  | 300
```

**Expected Output:**
```
category   | Jan    | Feb
Electronics| 500    | 600
Clothing   | 200    | 300
```

### Solution

```sql
SELECT 
  category,
  SUM(CASE WHEN MONTH(date) = 1 THEN amount ELSE 0 END) AS Jan,
  SUM(CASE WHEN MONTH(date) = 2 THEN amount ELSE 0 END) AS Feb,
  SUM(CASE WHEN MONTH(date) = 3 THEN amount ELSE 0 END) AS Mar,
  SUM(CASE WHEN MONTH(date) = 4 THEN amount ELSE 0 END) AS Apr,
  SUM(CASE WHEN MONTH(date) = 5 THEN amount ELSE 0 END) AS May,
  SUM(CASE WHEN MONTH(date) = 6 THEN amount ELSE 0 END) AS Jun
FROM sales
WHERE YEAR(date) = 2024
GROUP BY category
ORDER BY category;
```

### Alternative with PIVOT (if using SQL Server)

```sql
SELECT *
FROM (
  SELECT 
    MONTH(date) AS month,
    category,
    amount
  FROM sales
) AS source
PIVOT (
  SUM(amount)
  FOR month IN ([1], [2], [3], [4], [5], [6])
) AS pivot_table;
```

### Key Interview Points

✅ **What interviewer looks for:**
- Understanding of conditional aggregation
- Ability to transform data structure
- Creative problem solving

✅ **Follow-up discussion:**
- "How would this scale to 12 months?"
- "How to make it dynamic?"
- "Performance implications?"

---

## Question 24: Gaps and Islands Problem

**Difficulty:** Hard  
**Time to Solve:** 25 minutes  
**Topics:** Window functions, ROW_NUMBER, Complex logic

### Problem Statement

Identify consecutive dates with sales. Group them into islands.

**Input:**
```
order_date
2024-01-01
2024-01-02
2024-01-03
2024-01-05  <- Gap
2024-01-06
2024-01-07
2024-01-10  <- Gap
```

**Expected Output:**
```
island | start_date | end_date    | num_days
1      | 2024-01-01 | 2024-01-03  | 3
2      | 2024-01-05 | 2024-01-07  | 3
3      | 2024-01-10 | 2024-01-10  | 1
```

### Solution

```sql
WITH daily_sales AS (
  SELECT DISTINCT order_date
  FROM orders
  ORDER BY order_date
),
with_gaps AS (
  SELECT 
    order_date,
    ROW_NUMBER() OVER (ORDER BY order_date) AS row_num,
    DATE_SUB(order_date, INTERVAL 
      ROW_NUMBER() OVER (ORDER BY order_date) DAY) AS island_id
  FROM daily_sales
),
islands AS (
  SELECT 
    island_id,
    MIN(order_date) AS start_date,
    MAX(order_date) AS end_date,
    DATEDIFF(MAX(order_date), MIN(order_date)) + 1 AS num_days,
    ROW_NUMBER() OVER (ORDER BY island_id) AS island
  FROM with_gaps
  GROUP BY island_id
)
SELECT island, start_date, end_date, num_days
FROM islands
ORDER BY start_date;
```

### Explanation

The trick:
1. Get ROW_NUMBER for each day
2. Subtract ROW_NUMBER from DATE → creates constant for consecutive dates
3. GROUP BY that constant → groups consecutive dates
4. Aggregate to get islands

---

## Question 25: Running Totals with Window Functions

**Difficulty:** Hard  
**Time to Solve:** 18 minutes

### Problem Statement

Calculate cumulative sales by customer over time.

### Solution

```sql
SELECT 
  customer_id,
  order_date,
  order_amount,
  SUM(order_amount) OVER (
    PARTITION BY customer_id 
    ORDER BY order_date
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS cumulative_total,
  LAG(order_amount, 1, 0) OVER (
    PARTITION BY customer_id 
    ORDER BY order_date
  ) AS prev_order_amount,
  order_amount - LAG(order_amount, 1, 0) OVER (
    PARTITION BY customer_id 
    ORDER BY order_date
  ) AS diff_from_prev
FROM orders
ORDER BY customer_id, order_date;
```

### Key Window Frame Clauses

```
ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
-> Running total from start to current

ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING
-> Running total from current to end

ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
-> 3-row moving average

RANGE BETWEEN INTERVAL '7' DAY PRECEDING AND CURRENT ROW
-> Last 7 days (date-based)
```

---

## Question 26-30: Hard Practice Questions

### Question 26: Duplicate removal (keeping latest)

```sql
WITH ranked AS (
  SELECT 
    *,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC) AS rn
  FROM customer_records
)
SELECT * FROM ranked WHERE rn = 1;
```

### Question 27: Percentile calculation

```sql
SELECT 
  customer_id,
  total_spent,
  PERCENT_RANK() OVER (ORDER BY total_spent) AS percentile
FROM customer_summary
WHERE percentile BETWEEN 0.75 AND 1.0;  -- Top 25%
```

### Question 28: Complex hierarchical query

```sql
-- Find customers and their product purchases
WITH customer_products AS (
  SELECT 
    c.customer_id,
    c.name,
    p.product_name,
    COUNT(*) AS purchase_count,
    SUM(oi.quantity) AS total_qty
  FROM customers c
  JOIN orders o ON c.customer_id = o.customer_id
  JOIN order_items oi ON o.order_id = oi.order_id
  JOIN products p ON oi.product_id = p.product_id
  GROUP BY c.customer_id, c.name, p.product_name
)
SELECT 
  customer_id,
  name,
  STRING_AGG(product_name, ', ' ORDER BY purchase_count DESC) AS products,
  SUM(purchase_count) AS total_purchases
FROM customer_products
GROUP BY customer_id, name;
```

### Question 29: Correlation between metrics

```sql
-- Find products with high correlation between price and quantity sold
SELECT 
  p.product_id,
  p.product_name,
  CORR(oi.price, oi.quantity) AS price_qty_correlation,
  COUNT(*) AS transaction_count
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
GROUP BY p.product_id, p.product_name
HAVING COUNT(*) > 50
ORDER BY ABS(price_qty_correlation) DESC;
```

### Question 30: Year-over-year comparison

```sql
WITH monthly_sales AS (
  SELECT 
    EXTRACT(YEAR FROM order_date) AS year,
    EXTRACT(MONTH FROM order_date) AS month,
    SUM(order_amount) AS sales
  FROM orders
  GROUP BY year, month
)
SELECT 
  COALESCE(yoy.month, py.month) AS month,
  py.sales AS prior_year_sales,
  yoy.sales AS current_year_sales,
  ROUND((yoy.sales - py.sales) / py.sales * 100, 2) AS yoy_growth_pct
FROM monthly_sales py
FULL OUTER JOIN monthly_sales yoy 
  ON py.month = yoy.month 
  AND py.year = EXTRACT(YEAR FROM CURRENT_DATE) - 1
  AND yoy.year = EXTRACT(YEAR FROM CURRENT_DATE)
ORDER BY month;
```

---

## Interview Tips for SQL

✅ **During the interview:**
1. **Clarify requirements** - Ask about data, expected output, edge cases
2. **Start simple** - Write basic query, then add complexity
3. **Test mentally** - Trace through logic with sample data
4. **Optimize** - After getting correct answer, discuss optimization
5. **Explain your thinking** - Talk through JOIN logic, filtering, aggregation

✅ **Common SQL pitfalls:**
- NULL handling (NULL != NULL)
- DISTINCT vs GROUP BY performance
- Forgetting to group non-aggregated columns
- Using WHERE instead of HAVING for grouped data
- Inefficient JOINs on large tables

✅ **Performance considerations:**
- Index on frequently filtered/joined columns
- Avoid functions on indexed columns in WHERE
- Use EXPLAIN PLAN to check execution
- Window functions can be expensive
- GROUP BY on many columns increases memory

---

**Next:** Continue to Medium and Hard sections for comprehensive mastery!

