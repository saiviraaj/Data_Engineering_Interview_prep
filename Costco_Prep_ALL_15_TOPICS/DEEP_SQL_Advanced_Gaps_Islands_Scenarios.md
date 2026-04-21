# Deep Advanced SQL — Gaps, Islands, and All Hard Scenarios
## Round 2 Preparation — Costco Sr. Data Engineer

---

## HOW TO READ THIS FILE

Every hard SQL question follows a **pattern**. Before writing a single line of SQL, you need to:
1. **Identify the pattern** — is this gaps-and-islands? ranking? running totals? sessionization?
2. **State the approach out loud** — interviewers want to hear your thinking
3. **Then write the SQL**

This file teaches you the pattern-recognition skill, not just the queries.

---

## PART 1: THE GAPS AND ISLANDS FRAMEWORK

### What is the "Gaps and Islands" Problem?

"Gaps and islands" refers to a class of SQL problems where you need to find **consecutive sequences** (islands) within a dataset, or **missing values** (gaps) in an otherwise complete sequence.

```
ISLAND PROBLEM: Find consecutive sequences that exist
Example: User logged in on Jan 1, 2, 3 (island), then skipped Jan 4, then Jan 5, 6 (island)
Task: Find each island (start date, end date, length)

GAP PROBLEM: Find missing values in a sequence
Example: Transactions should be numbered 1,2,3,4,5 but 3 is missing
Task: Find the gaps (missing numbers)
```

### The Universal Trick: DATE - ROW_NUMBER = Constant

This is THE insight that makes all consecutive-sequence problems solvable:

```
If dates are consecutive, then (date - row_number) = SAME CONSTANT for all rows in that streak.

Example:
  date        | row_number | date - row_number
  ────────────┼────────────┼──────────────────
  2024-01-01  |     1      | 2023-12-31  ← island key
  2024-01-02  |     2      | 2023-12-31  ← same! (consecutive)
  2024-01-03  |     3      | 2023-12-31  ← same! (consecutive)
  -- gap here --
  2024-01-05  |     4      | 2024-01-01  ← DIFFERENT! (new island)
  2024-01-06  |     5      | 2024-01-01  ← same as above (consecutive)

GROUP BY (date - row_number) groups consecutive dates together.
This "island key" is constant within an island and changes between islands.
```

---

## CHALLENGE 1 (YOUR ROUND-1 QUESTION): Find Users Who Logged In 3+ Consecutive Days

```
Table: user_logins(user_id, login_date)
Task: Find user_id of "loyal" users — logged in for at least 3 consecutive days
```

### Step 1: Understand the pattern
This is a classic **islands problem**. We need to find consecutive date sequences per user where the streak length ≥ 3.

### Step 2: State the approach
*"I'll use the date-minus-row-number trick. For each user, I'll assign a row number ordered by login date. For consecutive dates, (login_date - row_number) is the same value — that's my island grouping key. Then I group by (user_id, island_key) and count how many days are in each streak. Finally, filter for streaks ≥ 3."*

### Step 3: Write the SQL

```sql
-- Step 1: Deduplicate (user might login multiple times in a day)
WITH daily_logins AS (
    SELECT DISTINCT
        user_id,
        login_date
    FROM user_logins
),

-- Step 2: Assign row number per user, ordered by date
numbered AS (
    SELECT
        user_id,
        login_date,
        ROW_NUMBER() OVER (
            PARTITION BY user_id
            ORDER BY login_date
        ) AS rn
    FROM daily_logins
),

-- Step 3: Compute the island key
-- For consecutive dates: login_date - rn = CONSTANT (the "island key")
-- In BigQuery: use DATE_SUB to subtract integer days
islands AS (
    SELECT
        user_id,
        login_date,
        rn,
        DATE_SUB(login_date, INTERVAL rn DAY) AS island_key
        -- BigQuery syntax; in PostgreSQL: login_date - rn * INTERVAL '1 day'
        -- In standard SQL: DATEADD(DAY, -rn, login_date)
    FROM numbered
),

-- Step 4: Group by (user_id, island_key) to find each streak
streaks AS (
    SELECT
        user_id,
        island_key,
        MIN(login_date)   AS streak_start,
        MAX(login_date)   AS streak_end,
        COUNT(*)          AS consecutive_days
    FROM islands
    GROUP BY user_id, island_key
)

-- Step 5: Return users with at least one streak of 3+ days
SELECT DISTINCT user_id
FROM streaks
WHERE consecutive_days >= 3
ORDER BY user_id;
```

### BONUS: Return full streak details
```sql
-- If asked: "show the actual streaks, not just user IDs"
SELECT
    user_id,
    streak_start,
    streak_end,
    consecutive_days,
    RANK() OVER (PARTITION BY user_id ORDER BY consecutive_days DESC) AS longest_streak_rank
FROM streaks
WHERE consecutive_days >= 3
ORDER BY user_id, streak_start;
```

### BONUS: Longest streak per user
```sql
SELECT
    user_id,
    MAX(consecutive_days) AS longest_streak
FROM streaks
GROUP BY user_id
ORDER BY longest_streak DESC;
```

### Walkthrough with data — show this thinking in interview:

```
Input data (after dedup):
user_id | login_date
  U1    | 2024-01-01
  U1    | 2024-01-02
  U1    | 2024-01-03    ← streak of 3
  U1    | 2024-01-05    ← gap (no Jan 4)
  U1    | 2024-01-06
  U2    | 2024-01-01
  U2    | 2024-01-03    ← NOT consecutive (missing Jan 2)

After ROW_NUMBER():
user_id | login_date | rn
  U1    | 2024-01-01 | 1
  U1    | 2024-01-02 | 2
  U1    | 2024-01-03 | 3
  U1    | 2024-01-05 | 4
  U1    | 2024-01-06 | 5
  U2    | 2024-01-01 | 1
  U2    | 2024-01-03 | 2

After island_key = DATE_SUB(login_date, INTERVAL rn DAY):
user_id | login_date | rn | island_key
  U1    | 2024-01-01 | 1  | 2023-12-31  ← island A
  U1    | 2024-01-02 | 2  | 2023-12-31  ← island A (same)
  U1    | 2024-01-03 | 3  | 2023-12-31  ← island A (same)
  U1    | 2024-01-05 | 4  | 2024-01-01  ← island B (different!)
  U1    | 2024-01-06 | 5  | 2024-01-01  ← island B (same)
  U2    | 2024-01-01 | 1  | 2023-12-31  ← island C
  U2    | 2024-01-03 | 2  | 2024-01-01  ← island D (different! Jan 2 was missing)

After GROUP BY (user_id, island_key):
user_id | island_key  | streak_start | streak_end | days
  U1    | 2023-12-31  | 2024-01-01   | 2024-01-03 |  3  ← loyal!
  U1    | 2024-01-01  | 2024-01-05   | 2024-01-06 |  2  ← not loyal
  U2    | 2023-12-31  | 2024-01-01   | 2024-01-01 |  1  ← not loyal
  U2    | 2024-01-01  | 2024-01-03   | 2024-01-03 |  1  ← not loyal

Result: Only U1 is loyal (has a streak ≥ 3)
```

---

## CHALLENGE 2 (YOUR ROUND-1 QUESTION): Top 3 Products by Revenue Per Category — No Gaps in Rank

```
Table: Sales(product_id, category, revenue)
Task: Top 3 products per category. Ties share rank, NEXT rank is immediate next integer.
```

### Step 1: Identify the ranking function needed

The key phrase is **"no gaps in rank"**. Let's compare:

```
Revenue: 100, 80, 80, 60

RANK():        1, 2, 2, 4  ← GAP after tie (skips 3)
DENSE_RANK():  1, 2, 2, 3  ← NO GAP (next is immediate next integer)
ROW_NUMBER():  1, 2, 3, 4  ← No ties, always unique

The question says "share a rank" AND "next rank is immediate next integer" = DENSE_RANK
```

### Step 2: Approach
*"DENSE_RANK is the right function here. I'll partition by category, order by revenue descending. Then filter WHERE dense_rank <= 3. This gives us at most 3 distinct revenue tiers per category, but could return more than 3 rows if there are ties at rank 3."*

### Step 3: Write the SQL

```sql
-- Method 1: DENSE_RANK with QUALIFY (BigQuery shorthand — very clean)
SELECT
    category,
    product_id,
    revenue,
    DENSE_RANK() OVER (
        PARTITION BY category
        ORDER BY revenue DESC
    ) AS revenue_rank
FROM Sales
QUALIFY DENSE_RANK() OVER (
    PARTITION BY category
    ORDER BY revenue DESC
) <= 3
ORDER BY category, revenue_rank;

-- Method 2: Subquery (works everywhere, no QUALIFY needed)
SELECT category, product_id, revenue, revenue_rank
FROM (
    SELECT
        category,
        product_id,
        revenue,
        DENSE_RANK() OVER (
            PARTITION BY category
            ORDER BY revenue DESC
        ) AS revenue_rank
    FROM Sales
)
WHERE revenue_rank <= 3
ORDER BY category, revenue_rank;

-- Method 3: CTE (most readable)
WITH ranked AS (
    SELECT
        category,
        product_id,
        revenue,
        DENSE_RANK() OVER (
            PARTITION BY category
            ORDER BY revenue DESC
        ) AS revenue_rank
    FROM Sales
)
SELECT *
FROM ranked
WHERE revenue_rank <= 3
ORDER BY category, revenue_rank;
```

### Walkthrough with data:

```
Input:
category | product_id | revenue
  A      |    P1      |  100
  A      |    P2      |   80
  A      |    P3      |   80
  A      |    P4      |   60
  A      |    P5      |   40
  B      |    P6      |  200
  B      |    P7      |  150

After DENSE_RANK():
category | product_id | revenue | dense_rank
  A      |    P1      |  100    |    1
  A      |    P2      |   80    |    2   ← tied
  A      |    P3      |   80    |    2   ← tied (same revenue = same rank)
  A      |    P4      |   60    |    3   ← NO GAP (3, not 4) ← this is why DENSE_RANK
  A      |    P5      |   40    |    4
  B      |    P6      |  200    |    1
  B      |    P7      |  150    |    2

After WHERE dense_rank <= 3:
category | product_id | revenue | dense_rank
  A      |    P1      |  100    |    1
  A      |    P2      |   80    |    2
  A      |    P3      |   80    |    2
  A      |    P4      |   60    |    3  ← 4 rows returned for category A (tie at rank 2)
  B      |    P6      |  200    |    1
  B      |    P7      |  150    |    2  ← only 2 products in B, so just 2 rows

NOTE: When there's a tie at rank 3 (say P4 and P5 both have revenue 60),
both get rank 3 and both are returned. The result could have 5 rows for category A.
This is correct behavior — the question says ties share rank.
```

### What if the interviewer says "I want EXACTLY 3 rows per category, no more"?

*"Then the requirement changes — ties at rank 3 need a tiebreaker, so we'd use ROW_NUMBER instead of DENSE_RANK to guarantee exactly 3 rows."*

```sql
-- Exactly 3 rows per category (arbitrary tiebreaker for ties)
WITH ranked AS (
    SELECT
        category,
        product_id,
        revenue,
        ROW_NUMBER() OVER (
            PARTITION BY category
            ORDER BY revenue DESC, product_id ASC  -- product_id as tiebreaker
        ) AS rn
    FROM Sales
)
SELECT * FROM ranked WHERE rn <= 3;
```

---

## PART 2: ALL GAP-AND-ISLAND VARIANTS

### Variant 1: Find the gaps (missing values)

```sql
-- Table: order_ids should be 1,2,3,4... Find missing IDs

WITH id_range AS (
    SELECT MIN(order_id) AS min_id, MAX(order_id) AS max_id
    FROM orders
),
all_expected_ids AS (
    -- Generate all IDs from min to max
    SELECT id
    FROM UNNEST(GENERATE_ARRAY(
        (SELECT min_id FROM id_range),
        (SELECT max_id FROM id_range)
    )) AS id  -- BigQuery syntax
    -- In PostgreSQL: generate_series(min_id, max_id)
)
SELECT e.id AS missing_order_id
FROM all_expected_ids e
LEFT JOIN orders o ON e.id = o.order_id
WHERE o.order_id IS NULL
ORDER BY e.id;
```

### Variant 2: Find date gaps in a time series

```sql
-- Table: daily_sales(sale_date, revenue)
-- Find dates in the last 30 days with no sales

WITH date_spine AS (
    SELECT date_day
    FROM UNNEST(GENERATE_DATE_ARRAY(
        DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY),
        CURRENT_DATE(),
        INTERVAL 1 DAY
    )) AS date_day
)
SELECT d.date_day AS missing_date
FROM date_spine d
LEFT JOIN daily_sales s ON d.date_day = s.sale_date
WHERE s.sale_date IS NULL
ORDER BY d.date_day;
```

### Variant 3: Islands with a custom gap threshold

```sql
-- Table: events(user_id, event_time)
-- New session if gap > 30 minutes (sessionization — a common interview question)

WITH events_with_gap AS (
    SELECT
        user_id,
        event_time,
        TIMESTAMP_DIFF(
            event_time,
            LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time),
            MINUTE
        ) AS gap_minutes
    FROM events
),

with_session_flag AS (
    SELECT
        *,
        CASE
            WHEN gap_minutes IS NULL    THEN 1  -- first event ever
            WHEN gap_minutes > 30       THEN 1  -- new session
            ELSE 0
        END AS is_new_session
    FROM events_with_gap
),

with_session_id AS (
    SELECT
        *,
        SUM(is_new_session) OVER (
            PARTITION BY user_id
            ORDER BY event_time
            ROWS UNBOUNDED PRECEDING
        ) AS session_num
    FROM with_session_flag
)

SELECT
    user_id,
    session_num,
    MIN(event_time)                                         AS session_start,
    MAX(event_time)                                         AS session_end,
    TIMESTAMP_DIFF(MAX(event_time), MIN(event_time), MINUTE) AS duration_minutes,
    COUNT(*)                                                AS events_in_session
FROM with_session_id
GROUP BY user_id, session_num
ORDER BY user_id, session_num;
```

### Variant 4: Merge overlapping date ranges

```sql
-- Table: subscriptions(user_id, start_date, end_date)
-- Same user may have overlapping subscriptions. Merge them.

WITH ordered AS (
    SELECT
        user_id,
        start_date,
        end_date,
        MAX(end_date) OVER (
            PARTITION BY user_id
            ORDER BY start_date
            ROWS UNBOUNDED PRECEDING
        ) AS max_end_so_far
    FROM subscriptions
),

with_group AS (
    SELECT
        user_id,
        start_date,
        end_date,
        -- New group when start_date > max end date seen before this row
        CASE
            WHEN start_date > LAG(max_end_so_far) OVER (
                PARTITION BY user_id ORDER BY start_date
            ) THEN 1
            ELSE 0
        END AS is_new_group
    FROM ordered
),

with_group_id AS (
    SELECT
        *,
        SUM(is_new_group) OVER (
            PARTITION BY user_id
            ORDER BY start_date
            ROWS UNBOUNDED PRECEDING
        ) AS group_id
    FROM with_group
)

SELECT
    user_id,
    group_id,
    MIN(start_date) AS merged_start,
    MAX(end_date)   AS merged_end,
    DATE_DIFF(MAX(end_date), MIN(start_date), DAY) + 1 AS total_days
FROM with_group_id
GROUP BY user_id, group_id
ORDER BY user_id, merged_start;
```

### Variant 5: Running streak (reset on miss)

```sql
-- Find each user's current streak (how many consecutive days ending today)
WITH daily_logins AS (
    SELECT DISTINCT user_id, login_date FROM user_logins
),

with_prev AS (
    SELECT
        user_id,
        login_date,
        LAG(login_date) OVER (PARTITION BY user_id ORDER BY login_date) AS prev_date
    FROM daily_logins
),

streak_breaks AS (
    SELECT
        user_id,
        login_date,
        CASE
            WHEN prev_date IS NULL THEN 1                         -- first login
            WHEN DATE_DIFF(login_date, prev_date, DAY) = 1 THEN 0 -- consecutive
            ELSE 1                                                 -- streak broken
        END AS is_streak_start
    FROM with_prev
),

with_streak_id AS (
    SELECT
        *,
        SUM(is_streak_start) OVER (
            PARTITION BY user_id ORDER BY login_date
            ROWS UNBOUNDED PRECEDING
        ) AS streak_id
    FROM streak_breaks
),

streak_lengths AS (
    SELECT
        user_id,
        streak_id,
        MIN(login_date) AS streak_start,
        MAX(login_date) AS streak_end,
        COUNT(*)        AS streak_length
    FROM with_streak_id
    GROUP BY user_id, streak_id
)

-- Current streak: the streak that ends today or yesterday
SELECT
    user_id,
    streak_start,
    streak_end,
    streak_length AS current_streak_days
FROM streak_lengths
WHERE streak_end >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)  -- still active
ORDER BY streak_length DESC;
```

---

## PART 3: RANKING SCENARIOS — EVERY VARIANT

### Scenario Matrix: Which ranking function to use?

```
┌────────────────────────────────────────────────────────────────────┐
│                    RANKING FUNCTION SELECTION                       │
│                                                                      │
│ Question says:                    │ Use:                            │
│ ─────────────────────────────────────────────────────────────────  │
│ "Top N per group, EXACTLY N rows" │ ROW_NUMBER() (arbitrary tie)   │
│ "Top N per group, all ties included│ DENSE_RANK() <= N              │
│  at rank N"                       │                                 │
│ "Second highest" (ties matter)    │ DENSE_RANK() = 2               │
│ "Second highest" (just one row)   │ ROW_NUMBER() = 2               │
│ "No gaps in ranking"              │ DENSE_RANK()                    │
│ "Ties get same rank, skip next"   │ RANK()                          │
│ "Deduplicate: keep one per key"   │ ROW_NUMBER() = 1               │
│ "Percentile bucket"               │ NTILE(N)                        │
│ "Cumulative distribution"         │ CUME_DIST()                     │
└────────────────────────────────────────────────────────────────────┘
```

### All Four Scenarios with Walkthroughs

```sql
-- Setup data for all ranking examples
-- Revenue: 100, 80, 80, 60 (two tied at 80)

-- ROW_NUMBER: always unique, arbitrary tiebreaker
SELECT product_id, revenue,
       ROW_NUMBER() OVER (ORDER BY revenue DESC) AS rn
-- Result: 1, 2, 3, 4 (P3 at revenue=80 might be 2 or 3 — not deterministic)

-- RANK: ties get same rank, SKIPS next (gap)
SELECT product_id, revenue,
       RANK() OVER (ORDER BY revenue DESC) AS rnk
-- Result: 1, 2, 2, 4 (skips 3)

-- DENSE_RANK: ties get same rank, NO SKIP (no gap)
SELECT product_id, revenue,
       DENSE_RANK() OVER (ORDER BY revenue DESC) AS dr
-- Result: 1, 2, 2, 3 (next after tied 2s is 3, not 4)

-- NTILE(4): divide into quartiles
SELECT product_id, revenue,
       NTILE(4) OVER (ORDER BY revenue DESC) AS quartile
-- Result: 1, 2, 3, 4 (one per bucket)
```

---

## PART 4: SELF-JOIN PATTERNS

### Pattern: "Compare each row to other rows in the same group"

Self-joins appear when you need to compare one row to another row in the same table. Common scenarios:

**Scenario 1: Employees earning more than their manager**

```sql
-- employees(employee_id, name, salary, manager_id)
SELECT
    e.name       AS employee,
    e.salary     AS emp_salary,
    m.name       AS manager,
    m.salary     AS mgr_salary
FROM employees e
JOIN employees m ON e.manager_id = m.employee_id
WHERE e.salary > m.salary;
```

**Scenario 2: Find users who bought the same product as user X**

```sql
-- purchases(user_id, product_id)
SELECT DISTINCT p2.user_id AS users_who_bought_same
FROM purchases p1
JOIN purchases p2 ON p1.product_id = p2.product_id
WHERE p1.user_id = 'USER_X'
  AND p2.user_id != 'USER_X';
```

**Scenario 3: Running median using self-join (classic hard problem)**

```sql
-- Find median salary without PERCENTILE functions
WITH ranked AS (
    SELECT
        salary,
        ROW_NUMBER() OVER (ORDER BY salary)  AS rn,
        COUNT(*) OVER ()                     AS total
    FROM employees
)
SELECT AVG(salary) AS median_salary
FROM ranked
WHERE rn BETWEEN total/2.0 AND total/2.0 + 1;
-- For odd count: both conditions point to same middle row
-- For even count: picks two middle rows, AVG = median
```

---

## PART 5: ADVANCED AGGREGATION PATTERNS

### Pattern: Conditional aggregation (pivot without PIVOT)

```sql
-- Convert rows to columns: spend by channel per day
SELECT
    report_date,
    SUM(CASE WHEN channel = 'google'  THEN spend_usd ELSE 0 END) AS google_spend,
    SUM(CASE WHEN channel = 'meta'    THEN spend_usd ELSE 0 END) AS meta_spend,
    SUM(CASE WHEN channel = 'tiktok'  THEN spend_usd ELSE 0 END) AS tiktok_spend,
    SUM(spend_usd)                                                AS total_spend,
    -- Percentages
    ROUND(100.0 * SUM(CASE WHEN channel='google' THEN spend_usd END) /
          NULLIF(SUM(spend_usd), 0), 2)                          AS google_pct
FROM campaign_daily
GROUP BY report_date
ORDER BY report_date;
```

### Pattern: Multi-level aggregation in one scan

```sql
-- GROUPING SETS: get per-campaign, per-channel, AND grand total in one query
SELECT
    COALESCE(campaign_id, 'ALL') AS campaign_id,
    COALESCE(channel, 'ALL')     AS channel,
    SUM(spend_usd)               AS total_spend,
    GROUPING(campaign_id)        AS is_campaign_rollup,
    GROUPING(channel)            AS is_channel_rollup
FROM campaign_daily
WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY GROUPING SETS (
    (campaign_id, channel),  -- detailed
    (campaign_id),           -- per campaign subtotal
    (channel),               -- per channel subtotal
    ()                       -- grand total
)
ORDER BY is_campaign_rollup, is_channel_rollup, campaign_id, channel;
```

---

## PART 6: WINDOW FUNCTION EDGE CASES

### Edge Case 1: NULL in window ORDER BY

```sql
-- Problem: NULL values in ORDER BY affect LAG/LEAD unexpectedly
-- NULL in sort order: treated as LARGEST (NULLS LAST) by default in most DBs

SELECT
    user_id,
    score,
    -- Safe: treat NULL as 0 before sorting
    LAG(COALESCE(score, 0)) OVER (PARTITION BY user_id ORDER BY score ASC NULLS LAST)
    AS prev_score
FROM scores;
```

### Edge Case 2: ROWS vs RANGE

```sql
-- If your ORDER BY column has DUPLICATES (same date multiple rows):
-- ROWS: exact N physical rows
-- RANGE: all rows with same ORDER BY value as current row

-- Example: report_date has 3 rows for 2024-01-15
-- ROWS BETWEEN 6 PRECEDING AND CURRENT ROW: always exactly 7 rows
-- RANGE BETWEEN INTERVAL 6 DAY PRECEDING AND CURRENT ROW: all rows within 6 days

-- USE ROWS for: moving averages over N data points
-- USE RANGE for: "last 7 calendar days" where same-day rows should all be included

-- Rolling 7-day average (safe pattern)
AVG(roas) OVER (
    PARTITION BY campaign_id
    ORDER BY report_date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW  -- always 7 rows
)
```

### Edge Case 3: LAST_VALUE requires explicit frame

```sql
-- GOTCHA: LAST_VALUE default frame is ROWS UNBOUNDED PRECEDING to CURRENT ROW
-- This means LAST_VALUE gives the CURRENT row value, not the last in partition!

-- WRONG: doesn't give you last value in partition
LAST_VALUE(score) OVER (PARTITION BY user_id ORDER BY date)

-- CORRECT: explicit full frame
LAST_VALUE(score) OVER (
    PARTITION BY user_id
    ORDER BY date
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING  -- full partition
)

-- EASIER: just use FIRST_VALUE with reverse order
FIRST_VALUE(score) OVER (PARTITION BY user_id ORDER BY date DESC)
-- Same result, no frame needed
```

---

## PART 7: TRICKY SQL INTERVIEW QUESTIONS

### Q1: Delete duplicates but keep the row with the highest ID

```sql
-- Keep only the row with MAX(id) per (email, name) group
DELETE FROM users
WHERE id NOT IN (
    SELECT MAX(id)
    FROM users
    GROUP BY email, name
);

-- BigQuery alternative (no DELETE in BQ for standard tables):
CREATE OR REPLACE TABLE users AS
SELECT * EXCEPT (rn)
FROM (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY email, name
               ORDER BY id DESC       -- highest id first
           ) AS rn
    FROM users
)
WHERE rn = 1;
```

### Q2: Find the employee with the 3rd highest salary (allow ties at 3rd)

```sql
-- DENSE_RANK = 3 gives all employees at the 3rd distinct salary level
SELECT employee_id, name, salary
FROM (
    SELECT *,
           DENSE_RANK() OVER (ORDER BY salary DESC) AS dr
    FROM employees
)
WHERE dr = 3;
```

### Q3: Cumulative sum that resets at the start of each month

```sql
SELECT
    transaction_date,
    amount,
    SUM(amount) OVER (
        PARTITION BY DATE_TRUNC(transaction_date, MONTH)  -- reset per month
        ORDER BY transaction_date
        ROWS UNBOUNDED PRECEDING
    ) AS cumulative_monthly_total
FROM transactions
ORDER BY transaction_date;
```

### Q4: Find users who have made purchases in EVERY month of Q1 2024

```sql
WITH monthly_purchasers AS (
    SELECT DISTINCT
        user_id,
        DATE_TRUNC(purchase_date, MONTH) AS purchase_month
    FROM purchases
    WHERE purchase_date BETWEEN '2024-01-01' AND '2024-03-31'
)
SELECT user_id
FROM monthly_purchasers
GROUP BY user_id
HAVING COUNT(DISTINCT purchase_month) = 3  -- all 3 months of Q1
ORDER BY user_id;
```

### Q5: "Moving average that ignores NULLs"

```sql
-- Some days have NULL revenue (no data). Rolling 7-day average should ignore NULLs.
SELECT
    report_date,
    revenue,
    -- IGNORE NULLS: only averages non-null values in the window
    AVG(revenue) IGNORE NULLS OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS revenue_7d_avg_ignore_nulls
FROM daily_revenue;
-- Note: IGNORE NULLS syntax is BigQuery/Snowflake specific
-- In PostgreSQL: use a conditional average
-- AVG(CASE WHEN revenue IS NOT NULL THEN revenue END) OVER (...)
```

---

## PART 8: SCENARIO → APPROACH QUICK REFERENCE

```
WHEN YOU SEE:                           THINK:
──────────────────────────────────────────────────────────────
"Consecutive days/values"            → Gaps & Islands (date - rn trick)
"Running total that resets"          → Partition by (key, TRUNC(date, period))
"Top N per group"                    → ROW_NUMBER or DENSE_RANK + filter
"No gaps in ranking"                 → DENSE_RANK (not RANK)
"Deduplicate, keep latest"           → ROW_NUMBER OVER(PARTITION ORDER BY ts DESC) = 1
"% of total"                         → val / SUM(val) OVER ()
"Compare to prior period"            → LAG(val, N) OVER (PARTITION ORDER BY date)
"Anomaly detection"                  → Z-score = (val - AVG) / STDDEV OVER partition
"Session grouping"                   → Cumsum of (gap > threshold) as session_id
"Forward fill NULLs"                 → LAST_VALUE(col IGNORE NULLS) OVER (ORDER BY date ROWS UNBOUNDED PRECEDING)
"Overlapping intervals"              → MAX(end) OVER preceding, flag new group when start > prev max end
"Pivot (rows → columns)"             → SUM(CASE WHEN channel='X' THEN val END)
"Multi-level aggregation"            → GROUPING SETS or ROLLUP
"Cohort retention"                   → Self-join on (cohort_month, months_since_join)
"Attribution"                        → LAG to find last/first touch + window for linear weight
```

---

## INTERVIEW TIPS: HOW TO APPROACH ANY SQL QUESTION

### Step 1: Ask clarifying questions (1 minute)
- "Are there duplicate rows I need to handle?"
- "What should happen with NULLs in this column?"
- "Should ties be treated as equal or arbitrarily broken?"
- "Is this BigQuery, PostgreSQL, or engine-agnostic?"

### Step 2: State your approach BEFORE writing SQL
- "I'll use the date-minus-row-number trick for consecutive sequences"
- "I'll use DENSE_RANK because we need no gaps"
- "I'll write this as a CTE chain: step 1 does X, step 2 does Y"

### Step 3: Walk through with a small example
- Write 3-4 rows of sample data
- Trace through what each step produces
- Show the expected output

### Step 4: Write the SQL incrementally
- Write the innermost CTE first
- Add one layer at a time
- Test each layer mentally as you go

### Step 5: Review before finalizing
- Does it handle NULLs correctly?
- Is there a potential Cartesian join (missing join condition)?
- Is the partition/order correct in window functions?
- Would this be efficient on a large table?
