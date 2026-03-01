# SQL Problem Solving Playbook — Senior Data Engineer Level

## 🎯 Purpose

This document provides structured strategies to solve SQL interview and real-world data engineering problems, including:

* Gap & island problems
* Window function patterns
* Sequence problems
* Aggregation patterns
* Joins & hierarchy problems
* Time-series analysis
* Advanced analytical SQL
* Interview question patterns

Use this as a **decision framework** when solving SQL problems.

---

# 🧠 HOW TO THINK IN SQL (Golden Framework)

When you see a SQL problem, classify it:

1. **Row comparison?** → LAG/LEAD
2. **Ranking / latest / top N?** → ROW_NUMBER / RANK
3. **Aggregation filtering?** → GROUP BY + HAVING
4. **Consecutive sequences?** → Gaps & Islands
5. **Time series analysis?** → Window functions
6. **Hierarchical relationship?** → Self Join / Recursive CTE
7. **Generate missing data?** → Sequence generator
8. **Transform rows ↔ columns?** → Pivot
9. **Multiple values in single row?** → Arrays / string split
10. **Pair combinations?** → Self join

---

# ⭐ CORE SQL PATTERNS

---

# 1️⃣ Aggregation Pattern (GROUP BY + HAVING)

## When to Use

* Duplicate detection
* Threshold filtering
* Per-group metrics

## Template

```sql
SELECT col, COUNT(*)
FROM table
GROUP BY col
HAVING COUNT(*) > n;
```

## Example

Find customers who placed same order amount multiple times.

```sql
SELECT DISTINCT customer_id
FROM orders
GROUP BY customer_id, amount
HAVING COUNT(*) > 1;
```

---

# 2️⃣ Window Functions (Most Important Skill)

## When to Use

* Running totals
* Ranking
* Latest record
* Compare rows
* Time-series analysis
* Gap detection

## Key Functions

| Function   | Use Case             |
| ---------- | -------------------- |
| ROW_NUMBER | Unique ranking       |
| RANK       | Ranking with gaps    |
| DENSE_RANK | Ranking without gaps |
| LAG        | Previous row         |
| LEAD       | Next row             |
| SUM OVER   | Running totals       |
| AVG OVER   | Moving averages      |

---

## Example — Running Total

```sql
SELECT id,
       amount,
       SUM(amount) OVER (ORDER BY id) AS running_total
FROM sales;
```

---

# 3️⃣ LAG / LEAD Pattern (Row Comparison)

## When to Use

* Compare current vs previous row
* Time gaps
* Trend detection
* Consecutive logic

## Template

```sql
SELECT col,
       LAG(col) OVER (PARTITION BY group ORDER BY order_col)
FROM table;
```

---

## Example — Days Between Transactions

```sql
SELECT user_id,
       txn_date,
       txn_date - LAG(txn_date) OVER (
           PARTITION BY user_id ORDER BY txn_date
       ) AS days_diff
FROM transactions;
```

---

# 4️⃣ Gaps & Islands Pattern (VERY IMPORTANT)

## When to Use

* Consecutive dates
* Streak detection
* Continuous sequences
* Login streaks
* Transaction streaks

## Key Idea

```text
date - row_number() → constant for consecutive values
```

---

## Example — 5 Consecutive Login Days

```sql
WITH cte AS (
  SELECT employee_id,
         login_date,
         login_date - INTERVAL '1 day' *
         ROW_NUMBER() OVER (
            PARTITION BY employee_id ORDER BY login_date
         ) AS grp
  FROM logins
)
SELECT employee_id
FROM cte
GROUP BY employee_id, grp
HAVING COUNT(*) >= 5;
```

---

# 5️⃣ Recursive CTE Pattern

## When to Use

* Generate sequence
* Tree traversal
* Hierarchy queries
* Digit extraction

## Template

```sql
WITH RECURSIVE cte AS (
    SELECT base
    UNION ALL
    SELECT next
    FROM cte
    WHERE condition
)
```

---

## Example — Find Missing Numbers

```sql
WITH RECURSIVE cte AS (
  SELECT MIN(num) AS n FROM numbers
  UNION ALL
  SELECT n+1 FROM cte
  WHERE n < (SELECT MAX(num) FROM numbers)
)
SELECT n
FROM cte
LEFT JOIN numbers t ON t.num=n
WHERE t.num IS NULL;
```

---

# 6️⃣ Self Join Pattern

## When to Use

* Pair combinations
* Hierarchy
* Manager relationships
* Match mapping

---

## Example — Cricket Match Mapping

```sql
SELECT t1.team, t2.team
FROM teams t1
JOIN teams t2
ON t1.team_id < t2.team_id;
```

---

# 7️⃣ Latest Record Per Group

## When to Use

* Most recent transaction
* Latest order
* Current status

---

## Template

```sql
ROW_NUMBER() OVER (
  PARTITION BY group
  ORDER BY date DESC
)
```

---

## Example

```sql
SELECT *
FROM (
  SELECT *,
         ROW_NUMBER() OVER (
            PARTITION BY customer_id
            ORDER BY order_date DESC
         ) rn
  FROM orders
) t
WHERE rn=1;
```

---

# 8️⃣ Sequence / Missing Data Problems

## Approaches

* Generate full range + LEFT JOIN
* LEAD gap detection
* Recursive sequence

---

# 9️⃣ Pivot / Unpivot Pattern

## When to Use

* Transform rows → columns
* Reporting dashboards

Example:

```sql
SUM(CASE WHEN month='Jan' THEN sales END)
```

---

# 🔟 Arrays / String Manipulation

## When to Use

* Split values
* Digit extraction
* JSON parsing

---

## Example — Sum of Digits

(BigQuery)

```sql
SELECT num,
SUM(CAST(digit AS INT64))
FROM numbers,
UNNEST(SPLIT(CAST(num AS STRING),"")) digit
GROUP BY num;
```

---

# ⭐ INTERVIEW QUESTION COLLECTION (From Our Practice)

---

## 1️⃣ Sum of digits of integer

Recursive approach or string split.

---

## 2️⃣ Cricket match mappings

```sql
SELECT t1.team,t2.team
FROM teams t1
JOIN teams t2 ON t1.team_id<t2.team_id;
```

---

## 3️⃣ Second highest salary

```sql
SELECT salary
FROM employees
WHERE salary < (SELECT MAX(salary) FROM employees)
ORDER BY salary DESC
LIMIT 1;
```

---

## 4️⃣ Latest order per customer

```sql
ROW_NUMBER() OVER (PARTITION BY customer ORDER BY date DESC)
```

---

## 5️⃣ Consecutive transaction days

Gaps & islands pattern.

---

## 6️⃣ Running total

```sql
SUM(amount) OVER (ORDER BY id)
```

---

## 7️⃣ Missing numbers in sequence

Recursive CTE.

---

## 8️⃣ Employees above average salary

```sql
SELECT employee_id
FROM employees
WHERE salary>(SELECT AVG(salary) FROM employees);
```

---

## 9️⃣ Consecutive duplicates (3 times)

```sql
SELECT DISTINCT num
FROM (
 SELECT num,
        LAG(num,1) OVER(ORDER BY id) p1,
        LAG(num,2) OVER(ORDER BY id) p2
 FROM logs
)t
WHERE num=p1 AND num=p2;
```

---

## 🔟 Gap between transactions

```sql
txn_date - LAG(txn_date)
```

---

## 1️⃣1️⃣ Users with gap > 5 days

```sql
WITH cte AS (...)
SELECT DISTINCT user_id
FROM cte
WHERE days_diff>5;
```

---

# ⭐ ADVANCED SQL — SENIOR DATA ENGINEER LEVEL

---

## Query Optimization

* Use EXISTS vs IN
* Avoid unnecessary DISTINCT
* Push filters early
* Use indexes
* Avoid correlated subqueries on large tables

---

## Data Engineering Patterns

### Slowly Changing Dimensions

* Type 1
* Type 2
* Versioning with window functions

---

### Deduplication

```sql
ROW_NUMBER() OVER(PARTITION BY key ORDER BY timestamp DESC)
```

---

### Data Quality Checks

* Missing keys
* Duplicate records
* Referential integrity

---

### Time Series Analysis

* Rolling averages
* Sessionization
* Retention analysis

---

# 🚀 MUST MASTER FOR SENIOR ROLES

* Window functions deeply
* Gaps & islands
* Recursive CTE
* Join optimization
* Data modeling logic
* Query performance
* Analytical SQL
* Time series SQL
* Hierarchical queries

---

# 🎯 INTERVIEW SUCCESS STRATEGY

1. Clarify requirement
2. Choose pattern
3. Write query
4. Handle edge cases
5. Optimize

---

# ✅ If you master this document:

You can solve ~90% of SQL interview problems.





# SQL Interview Questions & Solutions — Practice Log

This document contains all SQL interview questions and solutions discussed during mock interview practice.

---

# ⭐ Question 1 — Sum of Digits of a Number

## Problem

Table has one column with integers:

```
12
234
5324
234234
```

Create another column with sum of digits.

---

## Solution (BigQuery)

```sql
SELECT
    num,
    SUM(CAST(digit AS INT64)) AS digit_sum
FROM numbers_table,
UNNEST(SPLIT(CAST(num AS STRING), "")) AS digit
GROUP BY num;
```

---

## Solution (Recursive CTE — Generic SQL)

```sql
WITH RECURSIVE digits AS (
    SELECT num,
           CAST(num AS VARCHAR) AS str,
           1 AS pos,
           0 AS digit_sum
    FROM numbers_table

    UNION ALL

    SELECT num,
           str,
           pos + 1,
           digit_sum + CAST(SUBSTRING(str, pos, 1) AS INT)
    FROM digits
    WHERE pos <= LENGTH(str)
)

SELECT num, MAX(digit_sum)
FROM digits
GROUP BY num;
```

---

# ⭐ Question 2 — Cricket Match Mapping Between Teams

## Problem

Table contains team names. Generate all match pair combinations.

---

## Solution

```sql
SELECT t1.team, t2.team
FROM teams t1
JOIN teams t2
ON t1.team_id < t2.team_id;
```

Prevents:

* self matches
* duplicate reverse pairs

---

# ⭐ Question 3 — Second Highest Salary

## Problem

Find 2nd highest salary.

---

## Solution

```sql
SELECT salary
FROM employees
WHERE salary < (SELECT MAX(salary) FROM employees)
ORDER BY salary DESC
LIMIT 1;
```

---

## Alternative (Window Function)

```sql
SELECT salary
FROM (
    SELECT salary,
           DENSE_RANK() OVER (ORDER BY salary DESC) rnk
    FROM employees
) t
WHERE rnk = 2;
```

---

# ⭐ Question 4 — Latest Order Per Customer

## Problem

Find latest order per customer.

---

## Solution

```sql
WITH cte AS (
    SELECT *,
           ROW_NUMBER() OVER(
               PARTITION BY customer_id
               ORDER BY order_date DESC
           ) rn
    FROM orders
)
SELECT *
FROM cte
WHERE rn = 1;
```

---

# ⭐ Question 5 — Employees Above Average Salary

## Problem

Find employees whose salary > overall average.

---

## Solution

```sql
SELECT employee_id
FROM employees
WHERE salary > (SELECT AVG(salary) FROM employees);
```

---

# ⭐ Question 6 — Customers With Duplicate Order Amounts

## Problem

Find customers who placed more than one order with same amount.

---

## Solution

```sql
SELECT DISTINCT customer_id
FROM orders
GROUP BY customer_id, amount
HAVING COUNT(*) > 1;
```

---

# ⭐ Question 7 — Missing Numbers in Sequence

## Problem

Table:

```
1
2
4
7
```

Find missing numbers.

---

## Solution (Recursive CTE)

```sql
WITH RECURSIVE cte AS (
    SELECT MIN(num) AS all_nums FROM numbers

    UNION ALL

    SELECT all_nums + 1
    FROM cte
    WHERE all_nums < (SELECT MAX(num) FROM numbers)
)

SELECT a.all_nums
FROM cte a
LEFT JOIN numbers n
ON n.num = a.all_nums
WHERE n.num IS NULL;
```

---

# ⭐ Question 8 — Consecutive Login Days (Gaps & Islands)

## Problem

Find employees who logged in ≥ 5 consecutive days.

---

## Solution

```sql
WITH cte AS (
    SELECT employee_id,
           login_date,
           login_date - INTERVAL '1 day' *
           ROW_NUMBER() OVER(
               PARTITION BY employee_id
               ORDER BY login_date
           ) grp
    FROM employee_logins
)

SELECT employee_id
FROM cte
GROUP BY employee_id, grp
HAVING COUNT(*) >= 5;
```

---

# ⭐ Question 9 — Consecutive Duplicate Numbers (3 Times)

## Problem

Find numbers appearing at least 3 times consecutively.

---

## Solution

```sql
WITH cte AS (
    SELECT num,
           LAG(num,1) OVER(ORDER BY id) prev1,
           LAG(num,2) OVER(ORDER BY id) prev2
    FROM logs
)

SELECT DISTINCT num
FROM cte
WHERE num = prev1
AND num = prev2;
```

---

# ⭐ Question 10 — Running Total of Sales

## Problem

Calculate cumulative sum.

---

## Solution

```sql
SELECT id,
       amount,
       SUM(amount) OVER (
           ORDER BY id
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS running_total
FROM sales;
```

---

# ⭐ Question 11 — Days Between Transactions

## Problem

Find days between current and previous transaction per user.

---

## Solution (Postgres)

```sql
SELECT user_id,
       txn_date,
       txn_date - LAG(txn_date) OVER(
           PARTITION BY user_id
           ORDER BY txn_date
       ) AS days_since_last_txn
FROM transactions;
```

---

## Solution (BigQuery)

```sql
SELECT user_id,
       txn_date,
       DATE_DIFF(
           txn_date,
           LAG(txn_date) OVER(
               PARTITION BY user_id
               ORDER BY txn_date
           ),
           DAY
       ) AS days_since_last_txn
FROM transactions;
```

---

# ⭐ Question 12 — Users With Gap > 5 Days Between Transactions

## Problem

Return users who had transaction gap greater than 5 days.

---

## Solution

```sql
WITH cte AS (
    SELECT user_id,
           txn_date,
           txn_date - LAG(txn_date) OVER(
               PARTITION BY user_id
               ORDER BY txn_date
           ) AS days_diff
    FROM transactions
)

SELECT DISTINCT user_id
FROM cte
WHERE days_diff > 5;
```

---

# ⭐ Question 13 — Find Managers of Managers

## Problem

Employee manages someone who also manages someone.

---

## Solution

```sql
SELECT DISTINCT e1.employee_id
FROM employees e1
JOIN employees e2
    ON e1.employee_id = e2.manager_id
JOIN employees e3
    ON e2.employee_id = e3.manager_id;
```

---

# ⭐ Question 14 — Sum of Transactions in 3 Consecutive Days > 10000

## Solution

```sql
WITH daily_txn AS (
    SELECT account_id,
           CAST(txn_time AS DATE) txn_date,
           SUM(amount) total_amount_per_day
    FROM transactions
    GROUP BY account_id, CAST(txn_time AS DATE)
),

grp_table AS (
    SELECT account_id,
           txn_date,
           total_amount_per_day,
           txn_date - INTERVAL '1 day' *
           ROW_NUMBER() OVER(
               PARTITION BY account_id
               ORDER BY txn_date
           ) grp
    FROM daily_txn
)

SELECT account_id
FROM grp_table
GROUP BY account_id, grp
HAVING COUNT(*) >= 3
AND SUM(total_amount_per_day) > 10000;
```

---

# ⭐ Question 15 — Parity (Odd/Even)

## Problem

Label numbers as odd or even.

---

## Solution

```sql
SELECT num,
       CASE
           WHEN num % 2 = 0 THEN 'even'
           ELSE 'odd'
       END AS parity
FROM numbers;
```

---

# ✅ End of Practice Log
