# SQL & Data Modelling — Exhaustive Interview Q&A
### Tailored for Senior Data Engineer with CDM Next / GCP Background

---

## SECTION 1: WINDOW FUNCTIONS

**Q1. Explain the difference between ROW_NUMBER, RANK, and DENSE_RANK with an example.**

All three assign numbers to rows within a partition, but they handle ties differently. Given amounts: 500, 500, 300, 100:

- `ROW_NUMBER()` → 1, 2, 3, 4 — always unique, tie-breaking is arbitrary
- `RANK()` → 1, 1, 3, 4 — ties share rank, next rank skips (gap after ties)
- `DENSE_RANK()` → 1, 1, 2, 3 — ties share rank, no gaps

In practice: use `ROW_NUMBER()` when you need exactly one row per group (deduplication, latest record per customer). Use `DENSE_RANK()` when you want top-N per category and ties should both be included (top 3 products — if two products tie for 3rd, both should appear). Use `RANK()` when the gaps matter semantically (competition rankings where 4th place after a tie means no one came 3rd).

---

**Q2. Write a query to get the latest record per customer from an orders table.**

```sql
-- Method 1: QUALIFY (BigQuery — cleanest)
SELECT *
FROM orders
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) = 1;

-- Method 2: Subquery (standard SQL)
SELECT * FROM (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn
    FROM orders
)
WHERE rn = 1;

-- Method 3: CTE (same as subquery but more readable)
WITH ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn
    FROM orders
)
SELECT * FROM ranked WHERE rn = 1;
```

I prefer `QUALIFY` in BigQuery — it's concise and avoids an extra subquery layer. In CDM Next, this pattern was fundamental for deduplication when multiple source systems sent the same record — we'd rank by `ingestion_timestamp DESC` and take `rn = 1`.

---

**Q3. How do you calculate a running total and a 7-day moving average in SQL?**

```sql
SELECT
    order_date,
    amount,

    -- Running total: all rows from beginning to current
    SUM(amount) OVER (
        PARTITION BY customer_id
        ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_total,

    -- 7-row moving average: current row + 6 preceding rows
    AVG(amount) OVER (
        PARTITION BY customer_id
        ORDER BY order_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS moving_avg_7

FROM orders;
```

The key distinction is the frame clause: `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` means "all rows from the start of the partition to the current row." For the moving average, `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW` means "this row and the 6 before it." If working with dates that may have gaps, `RANGE BETWEEN INTERVAL 6 DAY PRECEDING AND CURRENT ROW` is more semantically correct — it includes all rows within a 6-day window, not just 6 physical rows.

---

**Q4. Write a query to find the percentage change in monthly revenue compared to the previous month.**

```sql
WITH monthly AS (
    SELECT
        DATE_TRUNC(order_date, MONTH) AS month,
        SUM(amount) AS revenue
    FROM orders
    GROUP BY 1
)
SELECT
    month,
    revenue,
    LAG(revenue) OVER (ORDER BY month) AS prev_revenue,
    ROUND(
        (revenue - LAG(revenue) OVER (ORDER BY month)) /
        NULLIF(LAG(revenue) OVER (ORDER BY month), 0) * 100,
        2
    ) AS pct_change
FROM monthly
ORDER BY month;
```

Two things to note: `LAG()` gets the previous month's revenue. `NULLIF(prev, 0)` prevents division by zero — returns NULL if previous revenue was 0 rather than throwing an error. In BigQuery, `SAFE_DIVIDE()` does the same thing more cleanly.

---

**Q5. What is the difference between ROWS and RANGE in window frame definitions?**

`ROWS` counts physical rows in the result set. `RANGE` counts rows with the same ORDER BY value as the current row — it treats equal-value rows as a group.

Example: calculating a running sum with ORDER BY on a date column where multiple rows share the same date:
- `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` — adds each physical row one at a time
- `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` — adds all rows with the same date value together in one step

For running totals, `ROWS` is usually what you want (predictable). For date-range windows where you want "all events within the last 7 days" regardless of how many rows per day, use `RANGE BETWEEN INTERVAL 7 DAY PRECEDING AND CURRENT ROW`.

---

## SECTION 2: CTEs AND ADVANCED PATTERNS

**Q6. When would you use a CTE vs a subquery vs a temp table?**

**CTE:** Use when you need to name and reference an intermediate result for readability, or when the same subquery is referenced multiple times. CTEs improve readability significantly — a 6-step pipeline reads like a story. In BigQuery, CTEs are optimised well and don't inherently add overhead.

**Subquery:** Use for simple, one-off filtering or single references. If a subquery is used only once and is short, inlining it is fine. Avoid nested subqueries more than 2 levels deep — CTEs become much cleaner.

**Temp table:** Use when: (1) you need to reference the intermediate result in multiple separate queries (not just multiple CTEs in one query); (2) the intermediate result is expensive to compute and you want BigQuery to materialise it once; (3) you need to add indexes or specific clustering on the intermediate result for downstream joins. In BigQuery, `CREATE TEMP TABLE` scopes to the session and is auto-cleaned.

---

**Q7. Write a recursive CTE to find all ancestors of an employee in an org chart.**

```sql
WITH RECURSIVE ancestors AS (

    -- Base case: start with the target employee
    SELECT employee_id, name, manager_id, 0 AS depth
    FROM employees
    WHERE employee_id = 'EMP042'

    UNION ALL

    -- Recursive: walk up to manager
    SELECT e.employee_id, e.name, e.manager_id, a.depth + 1
    FROM employees e
    JOIN ancestors a ON e.employee_id = a.manager_id
    WHERE a.depth < 20  -- prevent infinite loop if data has cycles

)
SELECT employee_id, name, depth AS levels_above
FROM ancestors
WHERE employee_id != 'EMP042'  -- exclude the starting employee
ORDER BY depth;
```

In data engineering, I use recursive CTEs for lineage traversal — finding all upstream tables for a given target table, which is exactly what we needed in CDM Next to understand the impact of schema changes. Given a target table, recursively walk the lineage graph to find every upstream source.

---

**Q8. Explain the Gaps and Islands problem and how you'd solve it.**

Gaps and Islands is the problem of identifying contiguous sequences (islands) and breaks in sequences (gaps) within ordered data. A classic example: find each customer's continuous subscription periods from a daily activity log.

The key insight is: if you subtract the row number from a date value, consecutive dates produce the same result (since both increment by 1). Dates with gaps produce different values.

```sql
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
SELECT customer_id,
       MIN(activity_date) AS period_start,
       MAX(activity_date) AS period_end,
       COUNT(*) AS consecutive_days
FROM grouped
GROUP BY customer_id, island_id;
```

In CDM Next, I used this pattern to identify continuous migration windows — periods where data was flowing without interruption vs gaps where a pipeline was down.

---

**Q9. How would you PIVOT monthly data from rows to columns?**

```sql
-- Conditional aggregation — most portable, works in all SQL dialects
SELECT
    region,
    SUM(CASE WHEN month = 1 THEN revenue ELSE 0 END) AS jan,
    SUM(CASE WHEN month = 2 THEN revenue ELSE 0 END) AS feb,
    SUM(CASE WHEN month = 3 THEN revenue ELSE 0 END) AS mar,
    SUM(CASE WHEN month = 4 THEN revenue ELSE 0 END) AS apr
FROM (
    SELECT region, EXTRACT(MONTH FROM order_date) AS month, SUM(amount) AS revenue
    FROM orders WHERE EXTRACT(YEAR FROM order_date) = 2024
    GROUP BY region, month
)
GROUP BY region;
```

The challenge with PIVOT is when the number of columns isn't known at query write time (dynamic PIVOT). Standard SQL can't do this. In BigQuery, you'd need to: (1) query the distinct values dynamically, (2) construct the PIVOT SQL as a string, (3) execute it with `EXECUTE IMMEDIATE`. For pipelines, I'd handle dynamic pivoting in Python/PySpark instead — more testable and maintainable.

---

## SECTION 3: BIGQUERY-SPECIFIC SQL

**Q10. What is QUALIFY in BigQuery and when do you use it?**

`QUALIFY` is a BigQuery-specific clause (similar to `HAVING` for aggregates, but for window functions) that filters rows based on a window function result, without requiring a subquery wrapper. It executes after window functions are evaluated.

```sql
-- Without QUALIFY — requires subquery
SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC) AS rn
    FROM customers
) WHERE rn = 1;

-- With QUALIFY — clean and efficient
SELECT * FROM customers
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC) = 1;
```

I use it constantly in BigQuery for deduplication, top-N-per-group queries, and filtering on window function results. It's one of the things I miss most when writing SQL for non-BigQuery systems.

---

**Q11. Explain BigQuery ARRAYs and STRUCTs. When are they useful?**

`ARRAY` stores an ordered list of values of the same type in a single field. `STRUCT` groups named fields of potentially different types — like a nested record. Both represent nested data natively, which is one of BigQuery's most powerful features.

They're useful when: (1) data is naturally nested and flattening would create massive fan-out (a customer with 1000 orders stored flat = 1000 identical customer rows); (2) you want to avoid joins — store related data together; (3) representing semi-structured data from JSON/Kafka payloads.

```sql
-- ARRAY: store customer's entire purchase history in one row
SELECT customer_id,
       ARRAY_AGG(STRUCT(product_id, amount, order_date) ORDER BY order_date DESC) AS orders
FROM order_items GROUP BY customer_id;

-- Access: UNNEST to explode back into rows
SELECT customer_id, o.product_id, o.amount
FROM customers, UNNEST(orders) AS o;
```

In CDM Next, we used STRUCT/ARRAY fields to load Kafka streaming data (which is inherently nested JSON) into BigQuery without flattening — preserving the original structure while enabling powerful nested queries.

---

**Q12. How does partition pruning work in BigQuery and how do you ensure your queries use it?**

BigQuery partitions a table into segments — typically by date. When you filter on the partition column, BigQuery reads only the relevant partitions, not the entire table. For a 5-year table partitioned by day, filtering `WHERE order_date = '2024-01-15'` reads 1/1826th of the data.

To ensure pruning: (1) always filter on the partition column in WHERE; (2) use the exact column without wrapping it in a function — `WHERE DATE(order_timestamp) = '2024-01-15'` disables pruning because BigQuery can't evaluate the function during partition selection; instead use `WHERE order_timestamp BETWEEN '2024-01-15 00:00:00' AND '2024-01-15 23:59:59'`; (3) check bytes processed in BigQuery console before running production queries; (4) use `INFORMATION_SCHEMA.JOBS_BY_PROJECT` to audit partition efficiency across your team's queries.

In CDM Next, all migration pipelines were designed to filter on partition columns — critical when running daily incremental loads across petabyte-scale tables.

---

**Q13. Write a MERGE statement for an upsert operation in BigQuery.**

```sql
MERGE INTO target_orders T
USING staging_orders S
ON T.order_id = S.order_id

WHEN MATCHED AND T.updated_at < S.updated_at THEN
    UPDATE SET
        T.status      = S.status,
        T.amount      = S.amount,
        T.updated_at  = S.updated_at

WHEN NOT MATCHED BY TARGET THEN
    INSERT (order_id, customer_id, amount, status, created_at, updated_at)
    VALUES (S.order_id, S.customer_id, S.amount, S.status, S.created_at, S.updated_at)

WHEN NOT MATCHED BY SOURCE AND T.status != 'CANCELLED' THEN
    UPDATE SET T.status = 'DELETED', T.deleted_at = CURRENT_TIMESTAMP();
```

MERGE is how we handled incremental loads in CDM Next for sources that sent change feeds. The three clauses handle: (1) updates to existing records; (2) new records; (3) records deleted from source. The `AND T.updated_at < S.updated_at` guard in MATCHED prevents overwriting newer data with older data during retries.

---

## SECTION 4: DATA MODELLING

**Q14. Explain the difference between a fact table and a dimension table.**

A fact table stores measurable business events — each row is one occurrence of something that happened: an order placed, a payment received, a page viewed. It contains numeric metrics (amount, quantity, duration) and foreign keys pointing to dimension tables. Fact tables are typically wide (many columns) and very tall (billions of rows). The grain — what one row represents — must be explicitly defined and consistently maintained.

A dimension table provides context for facts — it answers who, what, where, and when. It stores descriptive attributes: customer name, product category, store location, date properties. Dimension tables are typically short (thousands to millions of rows) and intentionally denormalised to avoid joins at query time. The performance tradeoff in analytical systems is: store some redundancy in dimension tables to avoid expensive joins later.

---

**Q15. What is the difference between SCD Type 1, Type 2, and Type 3? Which did you use and why?**

**Type 1 (Overwrite):** Simply update the existing record when attributes change. No history preserved. Use when the old value is wrong or irrelevant — correcting typos, updating email addresses. Simple to implement, no extra storage.

**Type 2 (Versioned rows):** Add a new row when an attribute changes; mark the old row as expired. Full history preserved — you can query what the data looked like at any point in time. Each row has `effective_start`, `effective_end`, and `is_current` columns. Use when history matters for analysis: what tier was the customer when they made this purchase? Most important SCD type in analytics. Storage cost is higher.

**Type 3 (Previous column):** Add a column for the previous value alongside the current. Only preserves one change. Use when only the last change matters: "where did the customer use to live?"

In CDM Next, I implemented SCD Type 2 for all dimension tables because we were migrating data from regulated banking systems where point-in-time accuracy is non-negotiable. A risk report run in March 2024 must show customer tiers as they were in March 2024, not their current tier.

---

**Q16. What is dimensional modelling and how do you define the grain of a fact table?**

Dimensional modelling (Kimball method) is a technique for designing analytical databases using fact tables (events with metrics) and dimension tables (context). It's optimised for query performance and business user accessibility.

The grain is the most atomic level of detail one row in the fact table represents. Defining grain is the first and most critical step — everything else follows from it.

To define grain, answer: "What does one row represent?" Examples:
- "One row per order" — order-level grain
- "One row per order line item" — line item grain (more granular)
- "One row per customer per day" — daily summary grain

The grain determines: which dimensions you can join (line item grain can join product dimension; order grain cannot), what questions you can answer (line item grain can calculate per-product revenue; order grain cannot), and how large the fact table will be. Choose the finest grain that the business needs — you can always aggregate up, you can never disaggregate down.

---

**Q17. What is Data Vault modelling and why might you use it in a banking environment?**

Data Vault is a modelling methodology designed for enterprise data warehouses in regulated industries. It uses three entity types: Hubs (business keys, immutable), Links (relationships between hubs), and Satellites (descriptive attributes, insert-only history).

Why it suits banking: (1) **Audit trail** — it's insert-only; records are never updated or deleted, so every state of every record is preserved — directly meets regulatory requirements for auditability; (2) **Source agnostic** — multiple source systems (Teradata, Oracle, Kafka) can feed the same hub; each source's records are tracked by `record_source` metadata; (3) **Parallel load** — hubs, links, and satellites can be loaded in parallel without dependency ordering; great for our high-throughput migration needs in CDM Next; (4) **Schema flexibility** — new attributes from a new source? Add a new satellite without touching existing tables.

The tradeoff: querying is more complex than a star schema — joins across hubs, links, and satellites require more SQL. Typically you build a Business Vault or Mart layer on top for consumption.

---

**Q18. How would you design a BigQuery schema for a financial transactions table that handles 1 billion rows per day?**

Design decisions:

**Partitioning:** `PARTITION BY transaction_date` (DATE) — daily partitions mean each day's queries scan only one partition. For 1B rows/day, this keeps per-query bytes processed manageable.

**Clustering:** `CLUSTER BY (account_id, transaction_type)` — most queries filter by account and/or transaction type; clustering ensures BigQuery scans only relevant blocks.

**Schema:**
```sql
CREATE TABLE transactions (
    transaction_id   STRING NOT NULL,
    account_id       STRING NOT NULL,
    transaction_date DATE   NOT NULL,
    transaction_time TIMESTAMP,
    transaction_type STRING,   -- DEBIT, CREDIT, TRANSFER
    amount           NUMERIC,  -- NUMERIC not FLOAT64 for financial precision
    currency         STRING,
    counterparty_id  STRING,
    status           STRING,
    metadata         JSON
)
PARTITION BY transaction_date
CLUSTER BY account_id, transaction_type
OPTIONS (
    partition_expiration_days = 2555,  -- 7-year retention for compliance
    require_partition_filter = TRUE    -- force all queries to filter on partition
);
```

`NUMERIC` type (not `FLOAT64`) for amounts — financial systems require exact decimal precision, and floating-point representation causes rounding errors. `require_partition_filter = TRUE` prevents full table scans — any query without a date filter fails, protecting against accidental cost explosions.

---

**Q19. Write a query to build a cohort retention table.**

```sql
WITH cohorts AS (
    -- Each customer's acquisition month
    SELECT customer_id,
           DATE_TRUNC(MIN(order_date), MONTH) AS cohort_month
    FROM orders
    GROUP BY customer_id
),
monthly_orders AS (
    -- All months each customer was active
    SELECT o.customer_id,
           DATE_TRUNC(o.order_date, MONTH) AS active_month
    FROM orders o
    GROUP BY 1, 2
),
retention AS (
    SELECT
        c.cohort_month,
        DATE_DIFF(m.active_month, c.cohort_month, MONTH) AS months_since_acq,
        COUNT(DISTINCT m.customer_id) AS retained_customers
    FROM cohorts c
    JOIN monthly_orders m ON c.customer_id = m.customer_id
    GROUP BY 1, 2
),
sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size FROM cohorts GROUP BY 1
)
SELECT
    r.cohort_month,
    r.months_since_acq,
    r.retained_customers,
    s.cohort_size,
    ROUND(r.retained_customers / s.cohort_size * 100, 1) AS retention_pct
FROM retention r
JOIN sizes s ON r.cohort_month = s.cohort_month
ORDER BY cohort_month, months_since_acq;
```

This gives a retention matrix: rows are cohort months, columns are months 0/1/2/3... and each cell shows what % of the original cohort was still active.

---

## SECTION 5: QUERY OPTIMISATION

**Q20. How do you optimise a BigQuery query that is scanning too much data?**

Step-by-step approach: (1) **Check the query plan** in BigQuery console — identify which table is causing the large scan; (2) **Verify partition pruning** — is the WHERE clause filtering on the partition column? Functions on partition columns disable pruning; (3) **Check clustering** — queries filtering on clustered columns benefit from block-level pruning within partitions; (4) **Eliminate SELECT *** — specify only needed columns; BigQuery is columnar, so reading fewer columns directly reduces bytes scanned; (5) **Push filters before joins** — filter in a CTE or subquery before joining to reduce the dataset; (6) **Consider materialised views** — if this is a repeated aggregation (daily summary, rolling totals), a materialised view lets BigQuery reuse precomputed results; (7) **Check for cross joins** — an accidental Cartesian product will explode scan size.

---

**Q21. What is the difference between a materialised view and a regular view in BigQuery?**

A regular view is a saved SQL query — it executes fresh every time it's queried. No data is stored; no performance benefit over running the query directly.

A materialised view actually stores the precomputed results. BigQuery automatically refreshes it when the base tables change (within minutes for incremental updates). When a query references a materialised view's base tables, BigQuery's query optimiser may transparently rewrite the query to use the materialised view even if you didn't reference it directly — this is called "smart tuning."

Use materialised views for: frequently-run aggregations (daily sales summaries), expensive window function results, common JOINs that many downstream queries share. The limitation: materialised views in BigQuery don't support all SQL features (no UNION, limited window functions). For complex transformations, a scheduled query writing to a regular table is more flexible.

---

**Q22. You have a query joining two tables: one with 500GB and one with 500KB. How do you optimise?**

This is a classic use case for a **broadcast join** (BigQuery handles this automatically, but understanding it matters). When one table is very small, BigQuery can broadcast the entire small table to every worker that's processing the large table — eliminating the shuffle phase that a standard distributed join requires.

In BigQuery this happens automatically when the smaller table is below the broadcast threshold. To ensure it: (1) filter the small table first in a CTE to make it as small as possible before joining; (2) place the large table first in the FROM clause and the small table in the JOIN; (3) avoid operations on the join key in the small table that would prevent optimiser from recognising it as broadcastable.

In Spark, you'd explicitly hint: `large.join(broadcast(small), on="key")`. In BigQuery, verify by checking the query plan — if it shows "BROADCAST_HASH_JOIN" rather than "HASH_JOIN", the broadcast is happening.

---

*End of SQL & Data Modelling Q&A*
