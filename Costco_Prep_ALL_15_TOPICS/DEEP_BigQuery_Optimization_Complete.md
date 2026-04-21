# Deep BigQuery Optimization — Cost and Query Performance
## Round 2 Preparation — Costco Sr. Data Engineer

---

## THE MENTAL MODEL: HOW BIGQUERY CHARGES YOU

Before optimizing, understand EXACTLY how BigQuery costs work:

```
BigQuery On-Demand Pricing:
  Cost = Bytes scanned by your query × $6.25 per TB

  Every time you run a query, BigQuery reads some amount of data.
  You pay for BYTES READ — not for compute time, not for rows returned.

  Example:
  Table: 1 TB (100 billion rows)
  Query: SELECT * FROM table                → scans 1 TB → costs $6.25
  Query: SELECT name FROM table             → scans ~100 GB → costs $0.625
  Query: SELECT * WHERE date = '2024-01-15' → scans ~3 GB → costs $0.019
  Query: same query again                   → $0.00 (result cache hit)

  The levers:
  1. Read FEWER columns (columnar advantage)
  2. Read FEWER rows (partition pruning)
  3. Read FEWER files (clustering)
  4. Read NOTHING (result cache)
```

---

## SECTION 1: PARTITION PRUNING — THE BIGGEST LEVER

### How Partitioning Works Internally

```
Table: fact_ad_clicks (10TB, 3 years of data)
Partition column: click_date (daily partitions)
Number of partitions: ~1000 (roughly 3 years × 365 days)
Size per partition: ~10GB per day

BigQuery Storage:
  fact_ad_clicks/
  ├── partition_20220101/   10GB of Parquet files
  ├── partition_20220102/   10GB of Parquet files
  ├── ...
  ├── partition_20240115/   10GB of Parquet files
  └── ...

When you query with WHERE click_date = '2024-01-15':
  BigQuery reads metadata → identifies which partitions satisfy filter
  → reads ONLY partition_20240115 → 10GB scanned instead of 10TB
  → 1000x cost reduction
  → 1000x speed improvement

This is partition pruning. It's the single most important optimization.
```

### The #1 Partition Killer: Functions on Partition Columns

```sql
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- PROBLEM: Function on partition column = FULL SCAN
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- BAD: EXTRACT function on partition column
WHERE EXTRACT(YEAR FROM click_date) = 2024
-- BigQuery cannot evaluate which partitions satisfy this WITHOUT reading all of them
-- Result: scans ALL 1000 partitions = 10TB = $62.50

-- BAD: DATE_TRUNC on partition column
WHERE DATE_TRUNC(click_date, YEAR) = '2024-01-01'
-- Same problem: function on the partition column

-- BAD: CAST on partition column
WHERE CAST(click_date AS STRING) LIKE '2024%'
-- Same problem

-- BAD: Arithmetic on partition column
WHERE click_date + INTERVAL '1 DAY' > '2024-01-16'
-- Same problem

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- GOOD: Direct comparison on partition column
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- GOOD: Direct range filter
WHERE click_date >= '2024-01-01' AND click_date < '2025-01-01'
-- BigQuery can determine: partition_20220101 → outside range → SKIP
-- Reads only 2024 partitions = ~3.65TB = $22.81

-- GOOD: Exact date match
WHERE click_date = '2024-01-15'
-- Reads exactly 1 partition = 10GB = $0.06

-- GOOD: BETWEEN (inclusive on both ends)
WHERE click_date BETWEEN '2024-01-01' AND '2024-01-31'
-- Reads 31 partitions = 310GB = $1.94

-- THE RULE:
-- Partition column must appear ALONE on the left side of the comparison.
-- Any function/transformation on the partition column = full scan.
```

### Verifying Partition Pruning

```sql
-- Method 1: BigQuery Console "This query will process X bytes"
-- Shown before you run the query. Always check this first.

-- Method 2: Query INFORMATION_SCHEMA
SELECT
    job_id,
    query,
    total_bytes_processed / POW(1024, 3) AS gb_processed,
    total_bytes_billed / POW(1024, 3)    AS gb_billed,
    cache_hit
FROM `region-us`.INFORMATION_SCHEMA.JOBS
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
ORDER BY total_bytes_processed DESC;

-- Method 3: Use INFORMATION_SCHEMA to check partition count
SELECT
    partition_id,
    total_rows,
    total_logical_bytes / POW(1024, 3) AS partition_size_gb
FROM `project.dataset.INFORMATION_SCHEMA.PARTITIONS`
WHERE table_name = 'fact_ad_clicks'
ORDER BY partition_id DESC
LIMIT 10;

-- Method 4: Set require_partition_filter to PREVENT accidental full scans
ALTER TABLE fact_ad_clicks
SET OPTIONS (require_partition_filter = TRUE);
-- Now any query WITHOUT a partition filter will FAIL with an error
-- Forces analysts to always filter on click_date
```

---

## SECTION 2: CLUSTERING — THE SECOND LEVER

### How Clustering Works Internally

```
Partition pruning skips entire date partitions.
Clustering skips BLOCKS WITHIN a partition.

Table: fact_ad_clicks, partitioned by click_date, clustered by (campaign_id, channel)

Within partition_20240115 (10GB):
  The data is SORTED by (campaign_id, channel) within the partition.
  BigQuery stores the min/max of cluster columns per block (each block ~1MB).

  Block 1: campaign_id A001-A099, channel display
  Block 2: campaign_id A100-A199, channel display
  Block 3: campaign_id A100-A199, channel search
  ...
  Block N: campaign_id Z999, channel video

Query: WHERE click_date = '2024-01-15' AND campaign_id = 'B050'
  Step 1: Partition pruning → reads only partition_20240115 (10GB)
  Step 2: Block pruning → reads only blocks where campaign_id overlaps B050
             → maybe 100MB out of 10GB
  
  Net effect: scans 1% of the partition!
```

### Clustering Best Practices

```sql
-- Create table with optimal clustering
CREATE TABLE fact_ad_clicks
PARTITION BY click_date
CLUSTER BY campaign_id, channel, device_type;
-- Up to 4 cluster columns allowed
-- Order matters: most common filter column first

-- Rules for choosing cluster columns:
-- 1. High-cardinality columns work well (campaign_id with 10K+ values)
--    (many distinct values = more precise block pruning)
-- 2. Columns frequently used in WHERE clauses
-- 3. Columns frequently used in JOIN ON conditions
-- 4. DON'T cluster on columns with low cardinality (e.g., status='active'/'paused')
--    (only 2 values = blocks can't be effectively pruned)

-- Check if clustering is helping
SELECT
    query,
    partitions_scanned,
    partitions_total,
    ROUND(100 * (1 - partitions_scanned/partitions_total), 1) AS pct_pruned_partitions,
    total_bytes_processed / POW(1024, 3) AS gb_processed
FROM `region-us`.INFORMATION_SCHEMA.JOBS
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
  AND query LIKE '%fact_ad_clicks%'
ORDER BY total_bytes_processed DESC;
```

### Clustering vs Partitioning — Which Handles What

```
Column Type              Partition or Cluster?      Why
─────────────────────────────────────────────────────────────────────
click_date (DATE)        PARTITION                  Time dimension, queries
                                                    almost always filter by date
campaign_id (VARCHAR)    CLUSTER                    High cardinality, frequently
                         (not partition!)           filtered; too many partitions
                                                    if used as partition (>4000
                                                    partitions = metadata overhead)
channel (VARCHAR, 5 vals) CLUSTER                  Frequently filtered, but low
                                                    cardinality (only 5 values)
user_id (high cardinal)  CLUSTER or BUCKET (Hive)  Very high cardinality;
                                                    clustering still helps here
spend_usd (FLOAT)        Neither                   Range queries on non-discrete
                                                    values don't prune well

The golden rule:
  Partition = time dimension (date, month, hour)
  Cluster = everything else that's frequently filtered
```

---

## SECTION 3: SELECT * IS EXPENSIVE — THE COLUMNAR COST

### Why Column Selection Matters in BigQuery

```
BigQuery is columnar storage. Each column is stored separately.
When you SELECT *, you read ALL columns.
When you SELECT col1, col2, you read ONLY those 2 columns.

Table: fact_ad_clicks
  Columns: click_id, campaign_id, user_id, device_type, channel,
           keyword_id, ad_group_id, creative_id, clicked_at,
           cost_usd, revenue_usd, is_conversion, landing_url,
           referrer_url, user_agent, ip_address, session_id,
           attribution_model, adjusted_cost_usd, roas, ...
  (25 columns)

  Total size: 1TB
  Average per column: 40GB

Query 1: SELECT * FROM fact_ad_clicks WHERE click_date = '2024-01-15'
  Reads: 25 columns × 10GB per day = 250GB per day scanned
  Cost: $1.56 per day

Query 2: SELECT campaign_id, SUM(cost_usd) FROM fact_ad_clicks
         WHERE click_date = '2024-01-15' GROUP BY 1
  Reads: 2 columns (campaign_id + cost_usd) = 2 × 10GB = ~20GB
  Cost: $0.12 per day

  12x cheaper, probably 5x faster.

THE RULE: Always be explicit about column selection. Never SELECT * in
          production analytical queries on large tables.
```

---

## SECTION 4: JOIN OPTIMIZATION

### BigQuery Join Types and When They Happen

```
BigQuery joins execute as distributed operations across many servers.
The two main join strategies:

1. BROADCAST JOIN (fast — one side sent to all workers)
   Happens when: one table is < autoBroadcastJoinThreshold (usually 10MB default,
                 can go higher with query hints)
   How: Small table is copied to every worker. Large table scanned in parallel.
   Each worker does local join with its partition of large data + the small table copy.
   No data movement for large table = very fast.

2. HASH JOIN / SHUFFLE JOIN (slower — data moved across network)
   Happens when: both tables are large
   How: Both tables are hashed on join key, sent to same server by key value.
        All rows with campaign_id='C001' from both tables go to server X.
        Server X joins them locally.
   Data movement = network I/O = slower.

OPTIMIZATION: Make the smaller table even smaller before joining.
```

### Join Anti-Patterns (Know These Cold)

**Anti-pattern 1: Joining before filtering**

```sql
-- BAD: Join 10B rows × 1M rows THEN filter
SELECT c.campaign_name, cl.cost_usd
FROM ad_clicks cl    -- 10 billion rows
JOIN campaigns c ON cl.campaign_id = c.campaign_id
WHERE cl.click_date = '2024-01-15';  -- filter AFTER join (too late)

-- GOOD: Filter FIRST, then join (much smaller join)
SELECT c.campaign_name, cl.cost_usd
FROM (
    SELECT campaign_id, cost_usd
    FROM ad_clicks
    WHERE click_date = '2024-01-15'  -- filter BEFORE join = 10M not 10B rows
) cl
JOIN campaigns c ON cl.campaign_id = c.campaign_id;
```

**Anti-pattern 2: Selecting too many columns from large table**

```sql
-- BAD: SELECT * in the CTE reads ALL columns from the large table
WITH filtered_clicks AS (
    SELECT *   -- reads all 25 columns from 10 billion rows!
    FROM ad_clicks
    WHERE click_date = '2024-01-15'
)
SELECT fc.cost_usd, c.campaign_name FROM filtered_clicks fc
JOIN campaigns c USING (campaign_id);

-- GOOD: Only select what you'll actually use
WITH filtered_clicks AS (
    SELECT campaign_id, cost_usd  -- only 2 columns needed
    FROM ad_clicks
    WHERE click_date = '2024-01-15'
)
SELECT fc.cost_usd, c.campaign_name FROM filtered_clicks fc
JOIN campaigns c USING (campaign_id);
```

**Anti-pattern 3: Fan-out from non-unique join keys**

```sql
-- PROBLEM: dim_campaigns has SCD2 history — multiple rows per campaign_id
-- Joining on campaign_id (natural key) causes row multiplication

SELECT cl.*, c.campaign_name, c.daily_budget_usd
FROM ad_clicks cl
JOIN dim_campaigns c ON cl.campaign_id = c.campaign_id;
-- If dim_campaigns has 5 versions per campaign (5 year history)
-- 10M clicks × 5 = 50M rows!!! 5x fan-out

-- FIX: Always filter SCD2 dimensions
JOIN dim_campaigns c
    ON cl.campaign_id = c.campaign_id
    AND cl.click_date >= c.valid_from
    AND cl.click_date < COALESCE(c.valid_to, '9999-12-31')
-- OR: use is_current = TRUE for current-state joins
JOIN dim_campaigns c
    ON cl.campaign_id = c.campaign_id
    AND c.is_current = TRUE
```

**Anti-pattern 4: Skewed joins (one key has most of the data)**

```sql
-- PROBLEM: campaign_id='VIRAL_2024' has 80% of all click data
-- The server handling that campaign_id gets 80% of the work
-- All other servers finish in minutes; VIRAL_2024 server takes hours

-- DETECTION:
SELECT campaign_id, COUNT(*) AS cnt
FROM ad_clicks
WHERE click_date = '2024-01-15'
GROUP BY campaign_id
ORDER BY cnt DESC
LIMIT 10;
-- If top entry has 10M rows and second has 10K: massive skew

-- FIX for BigQuery: Approximate grouping sets or pre-aggregation
-- Pre-aggregate the skewed key BEFORE joining
WITH click_agg AS (
    SELECT campaign_id, SUM(cost_usd) AS total_spend  -- aggregate first
    FROM ad_clicks
    WHERE click_date = '2024-01-15'
    GROUP BY campaign_id  -- now: 10K rows instead of 10M
)
SELECT ca.campaign_id, c.campaign_name, ca.total_spend
FROM click_agg ca
JOIN campaigns c ON ca.campaign_id = c.campaign_id;
```

---

## SECTION 5: QUERY STRUCTURE OPTIMIZATION

### Correlated Subqueries — Replace with Window Functions

```sql
-- BAD: Correlated subquery (runs once per row — catastrophically slow)
SELECT
    campaign_id,
    spend_usd,
    -- This subquery runs 1 BILLION TIMES for a 1B row table!
    (SELECT AVG(spend_usd)
     FROM campaign_daily cd2
     WHERE cd2.campaign_id = cd.campaign_id  -- correlated to outer row
     AND cd2.report_date >= DATE_SUB(cd.report_date, INTERVAL 7 DAY)
    ) AS avg_spend_7d
FROM campaign_daily cd;

-- GOOD: Window function (single pass)
SELECT
    campaign_id,
    spend_usd,
    AVG(spend_usd) OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS avg_spend_7d
FROM campaign_daily;
-- Single table scan, O(n) complexity vs O(n²) for correlated subquery
```

### Subquery Fan-Out with Multiple Aggregations

```sql
-- BAD: Each metric is a separate subquery — table scanned 5 times
SELECT
    (SELECT SUM(spend_usd) FROM campaign_daily WHERE report_date = '2024-01-15') AS total_spend,
    (SELECT COUNT(DISTINCT campaign_id) FROM campaign_daily WHERE report_date = '2024-01-15') AS campaigns,
    (SELECT AVG(roas) FROM campaign_daily WHERE report_date = '2024-01-15') AS avg_roas,
    (SELECT MAX(spend_usd) FROM campaign_daily WHERE report_date = '2024-01-15') AS max_spend,
    (SELECT MIN(spend_usd) FROM campaign_daily WHERE report_date = '2024-01-15') AS min_spend;
-- 5 separate table scans = 5x the cost

-- GOOD: One aggregation query
SELECT
    SUM(spend_usd)            AS total_spend,
    COUNT(DISTINCT campaign_id) AS campaigns,
    AVG(roas)                 AS avg_roas,
    MAX(spend_usd)            AS max_spend,
    MIN(spend_usd)            AS min_spend
FROM campaign_daily
WHERE report_date = '2024-01-15';
-- 1 table scan = 1/5 the cost
```

---

## SECTION 6: MATERIALIZED VIEWS — PRE-COMPUTE EXPENSIVE AGGREGATIONS

```sql
-- Problem: The same expensive aggregation runs 1000 times per day by dashboards

-- The expensive query (100GB scan, $0.625 each run, 1000 runs/day = $625/day):
SELECT
    DATE_TRUNC(click_date, MONTH) AS month,
    campaign_id,
    SUM(spend_usd) AS total_spend,
    SUM(revenue_usd) AS total_revenue,
    SAFE_DIVIDE(SUM(revenue_usd), SUM(spend_usd)) AS roas
FROM fact_ad_clicks
WHERE click_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
GROUP BY 1, 2;

-- Solution: Materialized View — pre-computed and auto-refreshed
CREATE MATERIALIZED VIEW mv_monthly_campaign_roas
AS
SELECT
    DATE_TRUNC(click_date, MONTH) AS month,
    campaign_id,
    SUM(spend_usd)   AS total_spend,
    SUM(revenue_usd) AS total_revenue,
    COUNT(*)         AS click_count
FROM fact_ad_clicks
GROUP BY 1, 2;
-- Note: can't use SAFE_DIVIDE in MV — compute derived metrics at query time

-- Now the dashboard query hits the MV (KB scan, not 100GB):
SELECT month, campaign_id, total_spend, total_revenue,
       SAFE_DIVIDE(total_revenue, total_spend) AS roas
FROM mv_monthly_campaign_roas
WHERE month >= DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH), MONTH);

-- BigQuery automatically uses MV even for queries on the base table
-- (smart tuning feature) — engine recognizes when MV can answer the query

-- MV auto-refreshes when base table changes (incremental refresh for partitioned tables)
-- Storage cost of MV is additional, but query savings are enormous

-- Check MV refresh status
SELECT * FROM `project.dataset.INFORMATION_SCHEMA.MATERIALIZED_VIEWS`;
```

---

## SECTION 7: RESULT CACHE — FREE QUERIES

```
BigQuery caches query results for 24 hours.
If the EXACT same query runs again: returns cached result instantly.
Cost: $0.00

Conditions for cache hit:
  1. Same query text (identical SQL — even whitespace difference = miss)
  2. Same user/service account role
  3. Underlying tables haven't changed since last run
  4. Query was run within last 24 hours
  5. Query doesn't use non-deterministic functions (CURRENT_TIMESTAMP(), RAND(), etc.)

The last point is critical:
  SELECT * FROM table WHERE click_date = CURRENT_DATE()  → NEVER cached
  SELECT * FROM table WHERE click_date = '2024-01-15'    → CAN be cached

Dashboard optimization:
  Parameterize your BI tool queries with explicit dates, not CURRENT_DATE().
  The first user to run the dashboard pays for the scan.
  All subsequent users in the next 24 hours get it free from cache.

How to check:
SELECT cache_hit FROM `region-us`.INFORMATION_SCHEMA.JOBS
WHERE job_id = 'your_job_id';
-- TRUE = cache hit (cost was $0.00)
```

---

## SECTION 8: COST MONITORING AND ALERTS

### Finding Expensive Queries

```sql
-- Top 20 most expensive queries in the last 7 days
SELECT
    user_email,
    LEFT(query, 200)                            AS query_preview,
    creation_time,
    total_bytes_processed / POW(1024, 3)        AS gb_processed,
    total_bytes_processed / POW(1024, 3) * 6.25 AS estimated_cost_usd,
    total_slot_ms / 1000                        AS slot_seconds,
    cache_hit,
    CASE WHEN cache_hit THEN 0
         ELSE total_bytes_processed / POW(1024, 3) * 6.25
    END                                         AS actual_cost_usd
FROM `region-us`.INFORMATION_SCHEMA.JOBS
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  AND statement_type = 'SELECT'
ORDER BY total_bytes_processed DESC
LIMIT 20;

-- Cost by user (who is spending the most?)
SELECT
    user_email,
    COUNT(*)                                    AS query_count,
    SUM(total_bytes_processed) / POW(1024, 4)   AS tb_processed,
    SUM(total_bytes_processed) / POW(1024, 4) * 6.25 AS total_cost_usd
FROM `region-us`.INFORMATION_SCHEMA.JOBS
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  AND cache_hit = FALSE
GROUP BY user_email
ORDER BY total_cost_usd DESC;

-- Cost by dataset/table (which tables are expensive to query?)
SELECT
    referenced_table.project_id,
    referenced_table.dataset_id,
    referenced_table.table_id,
    COUNT(*)                                    AS query_count,
    SUM(total_bytes_processed) / POW(1024, 4)   AS tb_processed,
    SUM(total_bytes_processed) / POW(1024, 4) * 6.25 AS cost_usd
FROM `region-us`.INFORMATION_SCHEMA.JOBS j,
UNNEST(referenced_tables) AS referenced_table
WHERE j.creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY 1, 2, 3
ORDER BY cost_usd DESC;
```

### Setting Cost Controls

```sql
-- Per-user quotas (via Cloud Console or IAM)
-- Set maximum bytes billed per query to prevent accidental full scans

-- In bq CLI:
-- bq query --maximum_bytes_billed=1000000000 "SELECT ..."
-- (1GB limit — query fails instead of scanning 10TB)

-- Per project daily quota: set in Cloud Console under BigQuery → Settings

-- Resource Alerts (Cloud Monitoring)
-- Alert when: daily BigQuery cost > $500
-- Alert when: single query > 100GB scanned
```

---

## SECTION 9: PRACTICAL OPTIMIZATION WORKFLOW

### The 5-Step Optimization Checklist

When any BigQuery query is slow or expensive, apply this checklist in order:

```
STEP 1: Check partition filter (highest impact, 100-1000x improvement possible)
  → Does WHERE clause filter on the partition column?
  → Is the partition column wrapped in a function? (fix: remove function)
  → Check bytes estimated in BigQuery Console before running

STEP 2: Check column selection (10-50x improvement possible)
  → Any SELECT * on large tables?
  → Can you remove columns that aren't in the final output?
  → Move column filtering as early as possible in CTEs

STEP 3: Check join efficiency (2-10x improvement possible)
  → Are you filtering BEFORE the join?
  → Could the smaller table be even smaller before joining?
  → Is there join fan-out (duplicate keys in join dimension)?

STEP 4: Check for redundant subqueries (2-5x improvement)
  → Any correlated subqueries? Replace with window functions
  → Any metric computed in multiple separate subqueries? Consolidate
  → Any subquery in WHERE clause? Can it be a join?

STEP 5: Check query structure (1.5-3x improvement)
  → Can expensive aggregations be pre-computed as materialized views?
  → Can repeated queries benefit from result cache?
  → Can the query be split into a staged temp table approach?
```

---

## SECTION 10: BIGQUERY INTERVIEW QUESTIONS AND ANSWERS

### Q1: "A BigQuery query on a 5TB table runs for 10 minutes. What are your first 3 questions?"

*"My first three questions are: One — does the query have a partition filter? I'd look at the WHERE clause for a filter on the partition column. If it's missing, adding one could reduce the scan from 5TB to 5GB instantly. Two — is there a function being applied to the partition column? Something like YEAR(date_col) = 2024 prevents pruning even if there is a date filter — the fix is to replace it with date_col >= '2024-01-01' AND date_col < '2025-01-01'. Three — is there a SELECT * anywhere? On a 5TB table with 30 columns, SELECT * reads 5TB; selecting only the 3 needed columns reads 500GB — a 10x reduction. After those three, I'd look at join fan-out and correlated subqueries, but the first three questions address 90% of BigQuery performance issues."*

---

### Q2: "Explain the difference between partitioning and clustering in BigQuery"

*"Partitioning and clustering both reduce data scanned, but they work at different levels of granularity. Partitioning divides the table into physically separate storage segments — when your query filters on the partition column, BigQuery skips entire partitions without reading them. A table with 1000 daily partitions and a filter for one specific date reads 1/1000 of the data. Clustering sorts data within each partition by one to four columns and stores block-level min/max statistics. When you filter on a cluster column, BigQuery can skip individual blocks within the partition — potentially 95% of the partition. The two work together: partitioning provides coarse-grained pruning (skip whole partitions), clustering provides fine-grained pruning (skip blocks within a partition). Best practice: partition on the time dimension, cluster on the most common analytical dimensions like campaign_id or channel."*

---

### Q3: "Your dashboard query takes 30 seconds. Users want it in 2 seconds. What do you do?"

*"I'd approach this in three steps. First, I'd diagnose using INFORMATION_SCHEMA.JOBS to see exactly how much data the query is scanning. If it's scanning TBs when it should scan GBs, the fix is partition pruning or column selection — and that alone might get from 30 seconds to 5 seconds. Second, I'd look at whether this is a repeated aggregation that could be materialized. If the same expensive GROUP BY runs hundreds of times per day, creating a materialized view pre-computes it — dashboard queries then hit the MV, which is tiny, and return in under a second. Third, if the query is already well-optimized but just produces a large result, I'd enable BigQuery BI Engine — it caches results in memory and returns sub-second responses for repeated queries even on fresh data. The combination of partition pruning + materialized views + BI Engine typically gets any dashboard from 30+ seconds to under 2 seconds."*

---

### Q4: "What happens to query performance when you have data skew in BigQuery?"

*"Data skew in BigQuery means one key value has dramatically more rows than others — for example, one campaign_id accounts for 80% of all click data. When you GROUP BY or JOIN on that key, BigQuery distributes work by key value. The server handling the skewed key gets 80% of the data while others handle 20% combined. The query appears to hang near completion — the other servers finish in minutes but you're waiting for the one skewed server to finish its massive partition.*

*The fix depends on the operation. For GROUP BY, pre-aggregate: instead of grouping 10 billion rows by campaign_id, filter to the problematic campaign_id first and aggregate it separately, then UNION ALL with the aggregated non-skewed data. For JOIN, pre-aggregate the large skewed side before joining, so you're joining 10K rows (post-aggregation) instead of 10 billion. BigQuery also has APPROXIMATE_QUANTILES and APPROX_COUNT_DISTINCT which don't need to centralize all data, avoiding skew. In Spark the fix is salting, but in BigQuery pure SQL, pre-aggregation and approximate functions are the primary tools."*
