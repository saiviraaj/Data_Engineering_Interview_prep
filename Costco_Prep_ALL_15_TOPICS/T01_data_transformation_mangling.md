# Topic 1: Data Transformation & Data Mangling
## Costco Sr. Data Engineer — Exhaustive Interview Textbook

---

## Table of Contents
1. [Advanced SQL Transformations](#1-advanced-sql-transformations)
2. [PySpark Transformations — Wide vs Narrow, Shuffle](#2-pyspark-transformations--wide-vs-narrow-shuffle)
3. [Complex Aggregations & Metrics Building](#3-complex-aggregations--metrics-building)
4. [Window Functions Mastery](#4-window-functions-mastery)
5. [Data Normalization / Denormalization](#5-data-normalization--denormalization)
6. [Handling Messy Data — Nulls, Skew, Duplicates](#6-handling-messy-data--nulls-skew-duplicates)
7. [JSON, Nested & Semi-Structured Transformations](#7-json-nested--semi-structured-transformations)
8. [Business Metric Derivation — Real-World Scenarios](#8-business-metric-derivation--real-world-scenarios)

---

## 1. Advanced SQL Transformations

### 1.1 Concept: What "Advanced SQL Transformation" Means at Senior Level

At a senior level, SQL transformation is not just querying — it's the ability to model complex business logic entirely in SQL without moving data out of the warehouse. Senior engineers are expected to:
- Write transformations that process billions of rows efficiently
- Build multi-step pipelines using CTEs
- Replace procedural Python loops with set-based SQL
- Know exactly when SQL is superior to Spark (and vice versa)

The foundation of advanced SQL transformation is thinking **set-based**: every operation should act on the entire dataset at once, never row by row.

---

### 1.2 CTE Chains — Building SQL Pipelines

A Common Table Expression (CTE) is a named subquery defined before the main query. Multiple CTEs chained together create a readable, maintainable SQL pipeline.

**Why CTEs over subqueries**:
- Named → self-documenting
- Reusable within the same query
- Optimizer can materialize once (warehouse-dependent)
- Easier to debug: replace `SELECT * FROM final` with `SELECT * FROM any_step`

**Pattern: Layered CTE pipeline**
```sql
-- BigQuery: End-to-end AdTech transformation pipeline
-- Goal: Compute daily ROAS per campaign with anomaly flags

WITH
-- Step 1: Raw data with basic type casts
raw_clicks AS (
    SELECT
        click_id,
        campaign_id,
        user_id,
        DATE(clicked_at)                AS click_date,
        clicked_at,
        COALESCE(cost_micros, 0) / 1e6  AS cost_usd
    FROM `raw.google_ads_clicks`
    WHERE clicked_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
      AND click_id IS NOT NULL
),

-- Step 2: Deduplicate (same click_id can appear from multiple loads)
deduped_clicks AS (
    SELECT *
    FROM (
        SELECT *,
               ROW_NUMBER() OVER (
                   PARTITION BY click_id
                   ORDER BY clicked_at DESC
               ) AS rn
        FROM raw_clicks
    )
    WHERE rn = 1
),

-- Step 3: Daily aggregation
daily_clicks AS (
    SELECT
        click_date,
        campaign_id,
        COUNT(*)            AS clicks,
        SUM(cost_usd)       AS spend_usd,
        COUNT(DISTINCT user_id) AS unique_users
    FROM deduped_clicks
    GROUP BY 1, 2
),

-- Step 4: Conversions (similar pipeline)
daily_conversions AS (
    SELECT
        DATE(converted_at)              AS conversion_date,
        campaign_id,
        COUNT(*)                        AS conversions,
        SUM(conversion_value_usd)       AS revenue_usd
    FROM `raw.google_ads_conversions`
    WHERE converted_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    GROUP BY 1, 2
),

-- Step 5: Join and compute metrics
joined AS (
    SELECT
        dc.click_date                   AS report_date,
        dc.campaign_id,
        dc.clicks,
        dc.spend_usd,
        dc.unique_users,
        COALESCE(conv.conversions, 0)   AS conversions,
        COALESCE(conv.revenue_usd, 0)   AS revenue_usd
    FROM daily_clicks dc
    LEFT JOIN daily_conversions conv
        ON dc.click_date     = conv.conversion_date
       AND dc.campaign_id    = conv.campaign_id
),

-- Step 6: Derived metrics + anomaly flag
final AS (
    SELECT
        report_date,
        campaign_id,
        clicks,
        spend_usd,
        unique_users,
        conversions,
        revenue_usd,
        SAFE_DIVIDE(revenue_usd, spend_usd)             AS roas,
        SAFE_DIVIDE(clicks, unique_users)               AS click_density,
        SAFE_DIVIDE(conversions, clicks)                AS cvr,
        -- Anomaly: ROAS drops > 50% vs prior 7-day average
        SAFE_DIVIDE(revenue_usd, spend_usd) <
            0.5 * AVG(SAFE_DIVIDE(revenue_usd, spend_usd)) OVER (
                PARTITION BY campaign_id
                ORDER BY report_date
                ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
            )                                           AS is_roas_anomaly
    FROM joined
)

SELECT * FROM final
ORDER BY report_date DESC, roas ASC;
```

**What makes this senior-level**:
- Deduplication in a separate CTE (not inline)
- `SAFE_DIVIDE` prevents division-by-zero silently
- Anomaly detection using window function within final SELECT
- Each step is testable independently

---

### 1.3 CASE-Based Pivoting

Traditional `PIVOT` syntax isn't in BigQuery. Use conditional aggregation instead.

```sql
-- Goal: Pivot channel performance from rows to columns
-- Input: one row per (date, channel, metric_name, metric_value)
-- Output: one row per (date) with columns per channel

SELECT
    report_date,
    -- Google
    SUM(CASE WHEN channel = 'google' THEN spend_usd END)    AS google_spend,
    SUM(CASE WHEN channel = 'google' THEN clicks END)       AS google_clicks,
    SUM(CASE WHEN channel = 'google' THEN revenue_usd END)  AS google_revenue,
    -- Meta
    SUM(CASE WHEN channel = 'meta' THEN spend_usd END)      AS meta_spend,
    SUM(CASE WHEN channel = 'meta' THEN clicks END)         AS meta_clicks,
    SUM(CASE WHEN channel = 'meta' THEN revenue_usd END)    AS meta_revenue,
    -- TikTok
    SUM(CASE WHEN channel = 'tiktok' THEN spend_usd END)    AS tiktok_spend,
    -- Total
    SUM(spend_usd)                                          AS total_spend,
    SAFE_DIVIDE(SUM(revenue_usd), SUM(spend_usd))           AS blended_roas
FROM campaign_performance
GROUP BY report_date
ORDER BY report_date;
```

**Dynamic pivot (when channel values are not known ahead of time)** — requires two steps in BigQuery:

```sql
-- Step 1: Get distinct channel values (run separately or use EXECUTE IMMEDIATE)
SELECT STRING_AGG(DISTINCT CONCAT(
    'SUM(CASE WHEN channel = ''', channel, ''' THEN spend_usd END) AS ', channel, '_spend'
), ', ') AS pivot_cols
FROM campaign_performance;

-- Step 2: Use EXECUTE IMMEDIATE for dynamic SQL
DECLARE pivot_query STRING;
SET pivot_query = (
    SELECT CONCAT(
        'SELECT report_date, ',
        STRING_AGG(DISTINCT CONCAT(
            'SUM(CASE WHEN channel = ''', channel, ''' THEN spend_usd END) AS ', channel, '_spend'
        ), ', '),
        ' FROM campaign_performance GROUP BY report_date'
    )
    FROM campaign_performance
);
EXECUTE IMMEDIATE pivot_query;
```

---

### 1.4 Recursive CTEs

Recursive CTEs enable hierarchical/graph queries — e.g., org charts, campaign hierarchies, category trees.

**Syntax structure**:
```sql
WITH RECURSIVE cte_name AS (
    -- Anchor: base case (starting nodes)
    SELECT ...
    UNION ALL
    -- Recursive step: join CTE to itself
    SELECT ...
    FROM source
    JOIN cte_name ON ...
)
SELECT * FROM cte_name;
```

**Example: Campaign category hierarchy**
```sql
-- Table: categories(category_id, category_name, parent_id)
-- Goal: Find all ancestors of a given category

WITH RECURSIVE category_path AS (
    -- Anchor: start at the leaf category
    SELECT
        category_id,
        category_name,
        parent_id,
        0           AS depth,
        CAST(category_name AS STRING) AS path
    FROM categories
    WHERE category_id = 42   -- starting category

    UNION ALL

    -- Recursive: go to parent
    SELECT
        c.category_id,
        c.category_name,
        c.parent_id,
        cp.depth + 1,
        CONCAT(c.category_name, ' > ', cp.path)
    FROM categories c
    JOIN category_path cp ON c.category_id = cp.parent_id
    WHERE cp.parent_id IS NOT NULL   -- stop condition
)

SELECT category_id, category_name, depth, path
FROM category_path
ORDER BY depth;
```

**BigQuery Note**: BigQuery supports recursive CTEs from 2022 onwards. Syntax is `WITH RECURSIVE`.

---

### 1.5 Interview Questions — Advanced SQL Transformations

**Q: Explain the difference between WHERE and HAVING.**

WHERE filters rows before grouping (before GROUP BY executes). HAVING filters after grouping (on aggregate results). Use WHERE for row-level conditions on raw data; use HAVING for conditions on group-level aggregates.

```sql
-- WHERE: filter individual rows first
SELECT campaign_id, SUM(spend_usd) AS total_spend
FROM ad_clicks
WHERE status = 'active'       -- row-level filter BEFORE grouping
GROUP BY campaign_id
HAVING SUM(spend_usd) > 1000; -- aggregate filter AFTER grouping
```

**Q: When would you use a CTE vs a subquery vs a temp table?**

Use CTE when the logic is referenced once and readability matters. Use a subquery when it's simple and inline is cleaner. Use a temp table / materialized CTE when the result is referenced multiple times in a query (CTEs are re-evaluated each time they're referenced in some engines unless materialized) or when the intermediate result is very large and needs to be physically persisted for performance.

In BigQuery specifically: CTEs are re-evaluated each time referenced (not cached by default). If you reference the same CTE 3 times, it runs 3 times. In that case, either use temp tables or restructure the query.

**Senior Q: You have a 5-step CTE pipeline and it's running slow. How do you diagnose which step is the bottleneck?**

Approach:
1. Comment out steps progressively — run through step 1 only, then 1+2, etc. Note when execution time jumps sharply — that's the expensive step.
2. Use BigQuery's Query Execution Plan (EXPLAIN) to see bytes processed per stage.
3. Check for: missing filters early in the pipeline (letting massive raw data flow into later steps), Cartesian joins (missing join condition), missing partition pruning.
4. Fix by: pushing filters as early as possible (earliest CTE), materializing expensive intermediate results as temp tables, ensuring partition filters exist.

---

## 2. PySpark Transformations — Wide vs Narrow, Shuffle

### 2.1 Concept: The Fundamental Split — Narrow vs Wide Transformations

Understanding narrow vs wide transformations is the single most important concept for Spark optimization at a senior level. It determines whether data must be physically moved between executor nodes — which is the dominant source of Spark performance problems.

**Narrow transformations**: Each output partition depends on at most one input partition. No data movement across nodes.

```
Input:  [P1][P2][P3][P4]
         ↓   ↓   ↓   ↓    (each partition processed independently)
Output: [P1][P2][P3][P4]
```

Examples: `map`, `filter`, `flatMap`, `select`, `withColumn`, `drop`, `sample`, `union`

**Wide transformations (shuffle)**: Each output partition may depend on many input partitions. Requires data movement across the network.

```
Input:  [P1 has key=A,B] [P2 has key=A,C] [P3 has key=B,C]
                    ↓ Shuffle (sort + move by key)
Output: [P_A has all A] [P_B has all B] [P_C has all C]
```

Examples: `groupBy`, `join`, `distinct`, `repartition`, `sortBy`, `reduceByKey`, `aggregateByKey`, `cogroup`

### 2.2 What Happens During a Shuffle

A shuffle is the most expensive operation in Spark. Understanding the internals helps you minimize it.

**Shuffle stages**:
1. **Map side (write)**: Each task in Stage 1 writes its output to local disk, partitioned by the target partition key (hash of join/group key)
2. **Shuffle service**: Data is sorted and indexed on disk
3. **Reduce side (read)**: Each task in Stage 2 reads its required partitions from ALL map-side tasks across the network
4. Result: Every row with the same key ends up in the same reduce partition

**Cost of shuffle**:
- Network I/O (data transferred between all nodes)
- Disk I/O (data is spilled to disk during map and reduce phases)
- Memory pressure (shuffle buffers must fit in memory or spill)
- A shuffle forces a stage boundary — Stage N cannot start until Stage N-1 is 100% complete

```
Stage 1 (narrow): filter + select
    ↓ shuffle boundary (caused by groupBy)
Stage 2 (wide): groupBy + agg
    ↓ shuffle boundary (caused by join)
Stage 3 (wide): join
    ↓ no more shuffles
Stage 4 (narrow): select + write
```

### 2.3 PySpark Transformations — Full Reference with Examples

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import *

spark = SparkSession.builder.appName("CostcoMartech").getOrCreate()

# Read ad events (1B+ rows, partitioned by date)
df = spark.read.parquet("gs://costco-data/ad_events/")
```

**Narrow Transformations**:
```python
# filter — narrow: each partition filtered independently
active = df.filter(F.col("status") == "active")
active = df.filter("status = 'active'")  # SQL string form

# select / selectExpr — narrow
minimal = df.select("campaign_id", "user_id", "clicked_at", "cost_usd")
# selectExpr allows SQL expressions
clean = df.selectExpr(
    "campaign_id",
    "user_id",
    "CAST(clicked_at AS TIMESTAMP) AS clicked_at",
    "cost_micros / 1000000.0 AS cost_usd"
)

# withColumn — narrow (adds/replaces one column)
df = df.withColumn("click_date", F.to_date("clicked_at"))
df = df.withColumn("cost_usd", F.col("cost_micros") / 1e6)
df = df.withColumn(
    "device_category",
    F.when(F.col("device_type") == "mobile", "mobile")
     .when(F.col("device_type") == "tablet", "mobile")
     .otherwise("desktop")
)

# withColumnRenamed — narrow
df = df.withColumnRenamed("gclid", "click_id")

# drop — narrow
df = df.drop("_metadata", "_loaded_at")

# map-like: use select + expressions instead of RDD map
# AVOID: df.rdd.map(...) — forces deserialization from JVM to Python
# PREFER: df.select(F.expr("...")) — stays in JVM
```

**Wide Transformations**:
```python
# groupBy + agg — wide (shuffle by group key)
daily = df.groupBy("click_date", "campaign_id").agg(
    F.count("*").alias("clicks"),
    F.countDistinct("user_id").alias("unique_users"),
    F.sum("cost_usd").alias("spend_usd"),
    F.avg("cost_usd").alias("avg_cpc"),
    F.max("cost_usd").alias("max_cpc"),
    F.collect_list("click_id").alias("click_ids")  # careful: memory-intensive
)

# join — wide (shuffle both sides unless broadcast)
campaigns = spark.read.parquet("gs://costco-data/campaigns/")
enriched = df.join(campaigns, on="campaign_id", how="left")

# distinct — wide (shuffle to deduplicate)
unique_users = df.select("user_id").distinct()

# repartition — wide (explicit shuffle)
# Use when: want to increase partitions before expensive operations
df_repartitioned = df.repartition(200, "campaign_id")

# coalesce — narrow (merge partitions without shuffle)
# Use when: reducing partition count AFTER a filter that reduced data volume
small_df = df.filter("report_date = '2024-01-01'").coalesce(10)

# sort / orderBy — wide
df_sorted = df.orderBy("clicked_at", ascending=False)
# PREFER: sortWithinPartitions for local sort without full shuffle
df_local_sorted = df.sortWithinPartitions("clicked_at")
```

### 2.4 Shuffle Optimization Techniques

**Technique 1: Broadcast Join (eliminates shuffle for the small table)**

```python
# Standard join: both tables shuffled → expensive
result = large_clicks.join(small_campaigns, "campaign_id")

# Broadcast join: small table sent to ALL executors → no shuffle for large table
from pyspark.sql.functions import broadcast

result = large_clicks.join(broadcast(small_campaigns), "campaign_id")

# Automatic broadcast threshold (default 10MB)
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "50MB")

# When to use: small table (< 100-200MB), large table is massive
# Rule of thumb: if one side fits in executor memory, broadcast it

# BigQuery equivalent: /*+ BROADCAST(campaigns) */ hint
```

**Technique 2: Reduce Shuffle Partitions**

```python
# Default: 200 shuffle partitions (often wrong for your data size)
# Too many: many tiny tasks → overhead dominates
# Too few: data doesn't fit in memory per partition → spills to disk

# Right value: target ~128-256MB per partition after shuffle
# Formula: compressed_shuffle_output_size / 200MB

# Small job (few GB):
spark.conf.set("spark.sql.shuffle.partitions", "50")

# Medium job (100GB):
spark.conf.set("spark.sql.shuffle.partitions", "500")

# Large job (1TB+):
spark.conf.set("spark.sql.shuffle.partitions", "2000")

# Best: use Adaptive Query Execution (AQE) — auto-tunes partitions
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
```

**Technique 3: Pre-partitioning for Repeated Operations**

```python
# BAD: multiple groupBys on same key → multiple shuffles
daily_clicks = df.groupBy("campaign_id", "date").agg(F.sum("clicks"))
daily_spend  = df.groupBy("campaign_id", "date").agg(F.sum("spend"))
daily_conv   = df.groupBy("campaign_id", "date").agg(F.sum("conversions"))

# GOOD: single groupBy with multiple aggregations → one shuffle
daily = df.groupBy("campaign_id", "date").agg(
    F.sum("clicks").alias("total_clicks"),
    F.sum("spend").alias("total_spend"),
    F.sum("conversions").alias("total_conversions")
)
```

**Technique 4: Salting for Skewed Keys**

```python
# Problem: one campaign_id has 80% of the data → one partition is huge → stragglers
# Solution: salt the key to distribute work

import random

NUM_SALT_BUCKETS = 20

# Add salt to the skewed table
skewed_df = clicks.withColumn(
    "salt",
    (F.rand() * NUM_SALT_BUCKETS).cast("int")
).withColumn(
    "salted_campaign_id",
    F.concat(F.col("campaign_id"), F.lit("_"), F.col("salt"))
)

# Explode the small (right) table to match all salt values
small_df = campaigns.withColumn(
    "salt",
    F.explode(F.array([F.lit(i) for i in range(NUM_SALT_BUCKETS)]))
).withColumn(
    "salted_campaign_id",
    F.concat(F.col("campaign_id"), F.lit("_"), F.col("salt"))
)

# Join on salted key
result = skewed_df.join(small_df, "salted_campaign_id", "left") \
                  .drop("salt", "salted_campaign_id")
```

### 2.5 Transformations — Real-World Pipeline

```python
def build_daily_campaign_performance(spark, date_str: str):
    """
    Full PySpark transformation pipeline:
    Raw ad events → daily campaign performance metrics
    """
    
    # --- 1. Read with partition pruning (narrow) ---
    clicks = spark.read.parquet("gs://costco-data/clicks/") \
                  .filter(F.col("click_date") == date_str)
    
    campaigns = spark.read.parquet("gs://costco-data/campaigns/")
    
    # --- 2. Clean (all narrow transformations) ---
    clicks_clean = (
        clicks
        .filter(F.col("click_id").isNotNull())
        .withColumn("cost_usd", F.col("cost_micros") / 1e6)
        .withColumn("device_cat",
            F.when(F.col("device").isin("mobile","tablet"), "mobile")
             .otherwise("desktop")
        )
        .dropDuplicates(["click_id"])   # wide: one shuffle
    )
    
    # --- 3. Aggregate (wide: one shuffle) ---
    daily = clicks_clean.groupBy("campaign_id", "device_cat").agg(
        F.count("click_id").alias("clicks"),
        F.countDistinct("user_id").alias("unique_users"),
        F.sum("cost_usd").alias("spend_usd"),
        F.percentile_approx("cost_usd", 0.5).alias("median_cpc")
    )
    
    # --- 4. Enrich (broadcast join — no shuffle) ---
    result = daily.join(broadcast(campaigns), "campaign_id", "left") \
                  .select(
                      F.lit(date_str).alias("report_date"),
                      "campaign_id",
                      "campaign_name",
                      "campaign_type",
                      "device_cat",
                      "clicks",
                      "unique_users",
                      "spend_usd",
                      "median_cpc",
                      F.safe_divide("spend_usd", "clicks").alias("avg_cpc")
                  )
    
    # --- 5. Write with partitioning (narrow except sort) ---
    result.repartition(1, "campaign_id") \
          .write \
          .mode("overwrite") \
          .partitionBy("report_date") \
          .parquet("gs://costco-data/mart_campaign_performance/")

# F.safe_divide doesn't exist natively — define it
from pyspark.sql import functions as F
def safe_divide(numerator, denominator):
    return F.when(F.col(denominator) != 0, F.col(numerator) / F.col(denominator))
```

### 2.6 Interview Questions — PySpark Transformations

**Q: What is the difference between a narrow and wide transformation?**

Narrow: each output partition depends on exactly one input partition. No data is moved across the network. Examples: filter, map, select. Wide: output partitions may depend on multiple input partitions, requiring a shuffle — data is physically moved across nodes. Examples: groupBy, join, distinct. Shuffles are expensive because they involve network I/O, disk I/O, and serialization overhead. Stage boundaries only occur at wide transformations.

**Q: Why should you prefer `coalesce` over `repartition` when reducing partition count?**

`repartition(n)` triggers a full shuffle — data is redistributed uniformly across all nodes. `coalesce(n)` merges existing partitions without a shuffle by simply combining them on the same node. When you're reducing partition count (e.g., after a filter that eliminated 90% of data), `coalesce` achieves the same result with zero network overhead. Use `repartition` only when you want uniform distribution or need to increase partitions.

**Senior Q: You have a Spark job that joins a 1TB table with a 5TB table. It runs for 6 hours and keeps OOM-ing. Walk me through your diagnostic and fix process.**

1. **Check for data skew first** — look at the Spark UI's stage detail. If one task took 90% of the time, there's key skew. Use `df.groupBy("join_key").count().orderBy(F.desc("count"))` to confirm. Fix: salt the key.

2. **Check join strategy** — look at the physical plan (`df.explain(True)`). If it shows SortMergeJoin, both sides are being shuffled. Ask: can either side be broadcast? 5TB and 1TB — probably not. Can you pre-aggregate before joining to reduce size?

3. **Check shuffle partition count** — 200 default partitions for 6TB of data = ~30GB per partition = OOM. Set `spark.sql.shuffle.partitions` to 2000–5000 so each partition is 1-3GB.

4. **Enable AQE** — `spark.sql.adaptive.enabled=true` will auto-adjust partition count and detect skewed joins.

5. **Consider pre-sorting both tables by join key** — if this join runs repeatedly, pre-sort both inputs once, then use `df.hint("SORT_MERGE_JOIN")` with `spark.sql.join.preferSortMergeJoin=true`.

6. **Add partition pruning** — join only on the partitions you need. Filter both sides before the join.

---

## 3. Complex Aggregations & Metrics Building

### 3.1 Concept: Aggregation Hierarchy

Aggregations at senior level go far beyond `SUM/COUNT/AVG`. The key skill is building **business metric hierarchies** — going from raw events to per-session, per-user, per-campaign, and then cross-sectional metrics.

### 3.2 Multi-Level Aggregation

```sql
-- Problem: compute metrics at three levels simultaneously
-- Level 1: per ad_group per day
-- Level 2: per campaign per day (rollup of ad_group)
-- Level 3: total per day (rollup of campaign)

-- Method 1: GROUPING SETS — one scan, multiple levels
SELECT
    report_date,
    campaign_id,
    ad_group_id,
    SUM(spend_usd)          AS spend,
    SUM(clicks)             AS clicks,
    SUM(conversions)        AS conversions,
    GROUPING(campaign_id)   AS is_campaign_rollup,
    GROUPING(ad_group_id)   AS is_total_rollup
FROM daily_ad_performance
GROUP BY GROUPING SETS (
    (report_date, campaign_id, ad_group_id),  -- Level 1
    (report_date, campaign_id),               -- Level 2
    (report_date)                              -- Level 3
);

-- Method 2: ROLLUP — hierarchical (same result as above for hierarchical data)
SELECT
    report_date,
    campaign_id,
    ad_group_id,
    SUM(spend_usd) AS spend
FROM daily_ad_performance
GROUP BY ROLLUP (report_date, campaign_id, ad_group_id);

-- Method 3: CUBE — all combinations
SELECT
    COALESCE(channel, 'ALL')        AS channel,
    COALESCE(device_type, 'ALL')    AS device_type,
    COALESCE(region, 'ALL')         AS region,
    SUM(spend_usd)                  AS total_spend
FROM daily_ad_performance
GROUP BY CUBE (channel, device_type, region);
-- Produces: all individual + all pairs + all triples + grand total
```

### 3.3 Running Totals and Cumulative Metrics

```sql
-- Running total spend and cumulative budget utilization
SELECT
    report_date,
    campaign_id,
    spend_usd,
    daily_budget_usd,
    
    -- Running total spend for the month
    SUM(spend_usd) OVER (
        PARTITION BY campaign_id, DATE_TRUNC(report_date, MONTH)
        ORDER BY report_date
        ROWS UNBOUNDED PRECEDING
    ) AS mtd_spend,
    
    -- Cumulative budget utilization (what % of monthly budget used so far)
    SAFE_DIVIDE(
        SUM(spend_usd) OVER (
            PARTITION BY campaign_id, DATE_TRUNC(report_date, MONTH)
            ORDER BY report_date
            ROWS UNBOUNDED PRECEDING
        ),
        SUM(daily_budget_usd) OVER (
            PARTITION BY campaign_id, DATE_TRUNC(report_date, MONTH)
        )
    )                           AS cumulative_budget_pct,
    
    -- Day of month budget pacing: are we on track?
    -- Expected: (day_of_month / days_in_month) * monthly_budget
    EXTRACT(DAY FROM report_date) /
    EXTRACT(DAY FROM LAST_DAY(report_date)) *
    SUM(daily_budget_usd) OVER (
        PARTITION BY campaign_id, DATE_TRUNC(report_date, MONTH)
    )                           AS expected_spend_to_date

FROM campaign_daily_performance
ORDER BY campaign_id, report_date;
```

### 3.4 Cohort Analysis — Retention Metrics

```sql
-- Goal: Compute weekly retention for member cohorts
-- Cohort: week of first purchase
-- Retention: % of cohort active N weeks later

WITH member_first_purchase AS (
    SELECT
        member_id,
        DATE_TRUNC(MIN(purchase_date), WEEK) AS cohort_week
    FROM purchases
    GROUP BY member_id
),

member_activity AS (
    SELECT DISTINCT
        member_id,
        DATE_TRUNC(purchase_date, WEEK) AS activity_week
    FROM purchases
),

cohort_activity AS (
    SELECT
        c.cohort_week,
        a.activity_week,
        DATE_DIFF(a.activity_week, c.cohort_week, WEEK) AS weeks_since_cohort,
        COUNT(DISTINCT a.member_id) AS active_members
    FROM member_first_purchase c
    JOIN member_activity a USING (member_id)
    GROUP BY 1, 2, 3
),

cohort_sizes AS (
    SELECT cohort_week, COUNT(*) AS cohort_size
    FROM member_first_purchase
    GROUP BY 1
)

SELECT
    ca.cohort_week,
    cs.cohort_size,
    ca.weeks_since_cohort,
    ca.active_members,
    ROUND(100.0 * ca.active_members / cs.cohort_size, 2) AS retention_pct
FROM cohort_activity ca
JOIN cohort_sizes cs USING (cohort_week)
WHERE ca.weeks_since_cohort BETWEEN 0 AND 12
ORDER BY ca.cohort_week, ca.weeks_since_cohort;
```

### 3.5 Funnel Analysis

```sql
-- Marketing funnel: impression → click → landing page → add to cart → purchase
-- Goal: compute step-by-step conversion rates

WITH funnel_events AS (
    SELECT
        session_id,
        user_id,
        campaign_id,
        MAX(CASE WHEN event_type = 'impression' THEN 1 ELSE 0 END)     AS had_impression,
        MAX(CASE WHEN event_type = 'click' THEN 1 ELSE 0 END)          AS had_click,
        MAX(CASE WHEN event_type = 'page_view' THEN 1 ELSE 0 END)      AS had_page_view,
        MAX(CASE WHEN event_type = 'add_to_cart' THEN 1 ELSE 0 END)    AS had_add_to_cart,
        MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END)       AS had_purchase
    FROM ad_events
    WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY 1, 2, 3
)

SELECT
    campaign_id,
    COUNT(*)                                            AS sessions,
    SUM(had_impression)                                 AS impressions,
    SUM(had_click)                                      AS clicks,
    SUM(had_page_view)                                  AS page_views,
    SUM(had_add_to_cart)                                AS add_to_carts,
    SUM(had_purchase)                                   AS purchases,
    
    -- Step-by-step rates
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_click), SUM(had_impression)), 2)          AS imp_to_click_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_page_view), SUM(had_click)), 2)           AS click_to_view_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_add_to_cart), SUM(had_page_view)), 2)     AS view_to_cart_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_purchase), SUM(had_add_to_cart)), 2)      AS cart_to_purchase_pct,
    
    -- End-to-end rate
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_purchase), SUM(had_impression)), 4)       AS overall_cvr_pct

FROM funnel_events
GROUP BY campaign_id
ORDER BY purchases DESC;
```

### 3.6 Interview Questions — Aggregations

**Q: What's the difference between ROLLUP and CUBE in SQL?**

ROLLUP generates a hierarchy of subtotals. Given `GROUP BY ROLLUP(A, B, C)`, it produces groupings: (A,B,C), (A,B), (A), and (). The order matters — it only rolls up from right to left. CUBE generates all possible combinations. Given `GROUP BY CUBE(A, B, C)`, it produces all 8 combinations: (A,B,C), (A,B), (A,C), (B,C), (A), (B), (C), (). Use ROLLUP for hierarchical dimensions (year→month→day). Use CUBE when you want all cross-sectional aggregations (e.g., all combinations of channel, device, region).

**Senior Q: Your cohort retention query runs for 45 minutes on BigQuery. How do you fix it?**

First, check the query plan. Common issues:
1. `member_activity` does a full table scan — add a partition filter: `WHERE purchase_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)`
2. The self-join in cohort_activity might be a many-to-many explosion — verify cardinality is controlled by the `DISTINCT` and `GROUP BY`
3. Ensure the `purchases` table is partitioned by `purchase_date` and has `member_id` as a clustering key — then the `MIN(purchase_date)` GROUP BY scans minimal data
4. Consider pre-computing `member_first_purchase` as a materialized table refreshed daily — it's referenced every time this query runs

---

## 4. Window Functions Mastery

### 4.1 Concept: The Full Window Function Architecture

A window function performs a calculation across a set of rows related to the current row — without collapsing the rows like GROUP BY does. The window is defined by:
1. `PARTITION BY` — divides rows into groups (like GROUP BY but keeps all rows)
2. `ORDER BY` — defines row ordering within the partition
3. Frame clause — defines which rows relative to the current row are included

```
FUNCTION() OVER (
    PARTITION BY partition_columns
    ORDER BY order_columns
    ROWS/RANGE BETWEEN frame_start AND frame_end
)
```

**Frame types**:
- `ROWS`: physical row offset (n rows before/after)
- `RANGE`: logical value offset (based on ORDER BY column value)

**Frame bounds**:
- `UNBOUNDED PRECEDING` — all rows from partition start
- `N PRECEDING` — N rows before current row
- `CURRENT ROW` — current row only
- `N FOLLOWING` — N rows after current row
- `UNBOUNDED FOLLOWING` — all rows to partition end

### 4.2 Ranking Functions

```sql
-- Setup: campaign performance ranked by ROAS
SELECT
    campaign_id,
    campaign_name,
    channel,
    roas,
    spend_usd,
    
    -- ROW_NUMBER: unique sequential rank (no ties)
    ROW_NUMBER() OVER (ORDER BY roas DESC)              AS overall_row_num,
    
    -- RANK: tied rows get same rank, next rank skips
    -- Example: 1, 2, 2, 4 (skips 3)
    RANK() OVER (ORDER BY roas DESC)                    AS roas_rank,
    
    -- DENSE_RANK: tied rows get same rank, no skip
    -- Example: 1, 2, 2, 3 (no skip)
    DENSE_RANK() OVER (ORDER BY roas DESC)              AS roas_dense_rank,
    
    -- PERCENT_RANK: relative rank as 0-1 fraction
    -- (rank - 1) / (total_rows - 1)
    PERCENT_RANK() OVER (ORDER BY roas DESC)            AS roas_pct_rank,
    
    -- NTILE: divide into N buckets
    NTILE(4) OVER (ORDER BY roas DESC)                  AS roas_quartile,
    NTILE(10) OVER (ORDER BY roas DESC)                 AS roas_decile,
    
    -- Ranking WITHIN channel (partitioned)
    RANK() OVER (PARTITION BY channel ORDER BY roas DESC) AS rank_within_channel,
    
    -- Top N per channel: filter WHERE rank_within_channel <= 3
    ROW_NUMBER() OVER (PARTITION BY channel ORDER BY spend_usd DESC) AS spend_rank_in_channel

FROM mart_campaign_performance
WHERE report_date = '2024-01-15';

-- Top 3 campaigns by ROAS within each channel
SELECT * FROM (
    SELECT *,
           RANK() OVER (PARTITION BY channel ORDER BY roas DESC) AS r
    FROM mart_campaign_performance
    WHERE report_date = '2024-01-15'
)
WHERE r <= 3;
```

### 4.3 LAG and LEAD — Time-Series Analysis

```sql
-- Campaign performance trend analysis
SELECT
    report_date,
    campaign_id,
    spend_usd,
    roas,
    
    -- LAG: value from N rows before (previous period)
    LAG(spend_usd, 1, 0) OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
    )                                   AS prev_day_spend,
    
    LAG(roas, 1) OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
    )                                   AS prev_day_roas,
    
    -- LEAD: value from N rows after (next period)
    LEAD(spend_usd, 1) OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
    )                                   AS next_day_spend,
    
    -- Day-over-day change
    spend_usd - LAG(spend_usd, 1, spend_usd) OVER (
        PARTITION BY campaign_id ORDER BY report_date
    )                                   AS spend_dod_change,
    
    -- Week-over-week (lag by 7 rows)
    LAG(roas, 7) OVER (
        PARTITION BY campaign_id ORDER BY report_date
    )                                   AS roas_wow_prev,
    
    SAFE_DIVIDE(
        roas - LAG(roas, 7) OVER (PARTITION BY campaign_id ORDER BY report_date),
        LAG(roas, 7) OVER (PARTITION BY campaign_id ORDER BY report_date)
    ) * 100                             AS roas_wow_pct_change

FROM campaign_daily_performance
ORDER BY campaign_id, report_date;
```

### 4.4 Rolling Aggregates (Moving Averages)

```sql
SELECT
    report_date,
    campaign_id,
    spend_usd,
    roas,
    
    -- 7-day rolling average ROAS (current + 6 preceding)
    AVG(roas) OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    )                                   AS roas_7d_avg,
    
    -- 30-day rolling total spend
    SUM(spend_usd) OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    )                                   AS spend_30d_rolling,
    
    -- Rolling max (high watermark)
    MAX(roas) OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
        ROWS UNBOUNDED PRECEDING
    )                                   AS all_time_max_roas,
    
    -- Exponential moving average (approximation using weighted window)
    -- True EMA requires UDF; approximate with decreasing weights:
    (roas * 0.5 +
     LAG(roas,1) OVER (PARTITION BY campaign_id ORDER BY report_date) * 0.25 +
     LAG(roas,2) OVER (PARTITION BY campaign_id ORDER BY report_date) * 0.125 +
     LAG(roas,3) OVER (PARTITION BY campaign_id ORDER BY report_date) * 0.0625
    ) / 0.9375                          AS roas_ema_approx,
    
    -- Rolling standard deviation (detect volatility)
    STDDEV(roas) OVER (
        PARTITION BY campaign_id
        ORDER BY report_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    )                                   AS roas_30d_stddev

FROM campaign_daily_performance;
```

### 4.5 ROWS vs RANGE — Critical Distinction

```sql
-- Example: report_date has duplicates (multiple campaigns same date)
-- This matters when ORDER BY column has ties

-- ROWS BETWEEN: physical row offset — precise, literal row count
SUM(spend_usd) OVER (
    ORDER BY report_date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
)
-- Always includes exactly 7 rows

-- RANGE BETWEEN: logical value offset — includes ALL rows with same ORDER BY value
SUM(spend_usd) OVER (
    ORDER BY report_date
    RANGE BETWEEN INTERVAL 6 DAY PRECEDING AND CURRENT ROW
)
-- Includes all rows within 6 days of current row's date
-- If 3 rows have report_date = '2024-01-15', all 3 are included in each other's window

-- RANGE for "last 7 days" including all rows on same date:
SUM(spend_usd) OVER (
    ORDER BY UNIX_DATE(report_date)  -- BigQuery: use numeric for RANGE arithmetic
    RANGE BETWEEN 6 PRECEDING AND CURRENT ROW
)
```

### 4.6 Sessionization — Gap-and-Island Problem

One of the most common senior SQL interview questions: given a stream of events, group them into sessions based on a time gap.

```sql
-- Sessionize user click events: new session if gap > 30 minutes

WITH events AS (
    SELECT
        user_id,
        event_type,
        event_at,
        -- Flag start of new session (gap > 30 min from previous event)
        CASE
            WHEN TIMESTAMP_DIFF(
                event_at,
                LAG(event_at) OVER (PARTITION BY user_id ORDER BY event_at),
                MINUTE
            ) > 30 OR
            LAG(event_at) OVER (PARTITION BY user_id ORDER BY event_at) IS NULL
            THEN 1
            ELSE 0
        END AS is_session_start
    FROM user_events
),

sessions AS (
    SELECT
        user_id,
        event_type,
        event_at,
        -- Session ID = cumulative sum of session starts
        SUM(is_session_start) OVER (
            PARTITION BY user_id
            ORDER BY event_at
            ROWS UNBOUNDED PRECEDING
        ) AS session_num
    FROM events
)

SELECT
    user_id,
    session_num,
    MIN(event_at)                                   AS session_start,
    MAX(event_at)                                   AS session_end,
    TIMESTAMP_DIFF(MAX(event_at), MIN(event_at), MINUTE) AS session_duration_min,
    COUNT(*)                                        AS event_count,
    STRING_AGG(event_type ORDER BY event_at)        AS event_sequence
FROM sessions
GROUP BY user_id, session_num;
```

### 4.7 Islands Problem — Consecutive Sequences

```sql
-- Find consecutive days when a campaign was active
-- Input: one row per (campaign_id, date) when campaign was active

WITH numbered AS (
    SELECT
        campaign_id,
        active_date,
        ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY active_date) AS rn
    FROM campaign_active_days
),

island_groups AS (
    SELECT
        campaign_id,
        active_date,
        -- If consecutive, (date - row_number) is constant → same "island"
        DATE_SUB(active_date, INTERVAL rn DAY) AS island_key
    FROM numbered
)

SELECT
    campaign_id,
    MIN(active_date)    AS streak_start,
    MAX(active_date)    AS streak_end,
    COUNT(*)            AS consecutive_days
FROM island_groups
GROUP BY campaign_id, island_key
ORDER BY campaign_id, streak_start;
```

### 4.8 Interview Questions — Window Functions

**Q: What's the difference between RANK(), DENSE_RANK(), and ROW_NUMBER()?**

All three assign numbers to rows in a specified order. When there are no ties, all three produce identical results. With ties: ROW_NUMBER always assigns unique numbers (arbitrary tiebreaker). RANK assigns the same number to tied rows but skips the next number(s) — e.g., 1,2,2,4. DENSE_RANK assigns the same number to tied rows and doesn't skip — e.g., 1,2,2,3. Use ROW_NUMBER for deduplication. Use RANK/DENSE_RANK when you want to communicate that rows are "tied".

**Q: Explain the difference between ROWS and RANGE in window frames.**

ROWS defines the frame by physical row offsets — `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW` always includes exactly 7 rows. RANGE defines the frame by value offsets relative to the ORDER BY column — `RANGE BETWEEN 6 PRECEDING AND CURRENT ROW` when ordered by a numeric includes all rows where the ORDER BY value is within 6 of the current row's value. With RANGE, if multiple rows have the same ORDER BY value as the current row, they're all included. This matters when ORDER BY has ties.

**Senior Q: You need to compute, for each ad click, "how many other clicks happened in the same session by the same user, before this click." No session_id column exists — you must derive sessions using a 30-minute gap rule. Walk me through the SQL.**

```sql
WITH with_session_flag AS (
    SELECT
        click_id, user_id, clicked_at,
        CASE
            WHEN TIMESTAMP_DIFF(clicked_at,
                LAG(clicked_at) OVER (PARTITION BY user_id ORDER BY clicked_at), MINUTE) > 30
              OR LAG(clicked_at) OVER (PARTITION BY user_id ORDER BY clicked_at) IS NULL
            THEN 1 ELSE 0
        END AS is_new_session
    FROM clicks
),
with_session_id AS (
    SELECT *, SUM(is_new_session) OVER (PARTITION BY user_id ORDER BY clicked_at
                                        ROWS UNBOUNDED PRECEDING) AS session_id
    FROM with_session_flag
),
with_position AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY user_id, session_id ORDER BY clicked_at) - 1
           AS clicks_before_this_in_session
    FROM with_session_id
)
SELECT click_id, user_id, clicked_at, session_id, clicks_before_this_in_session
FROM with_position;
```

Explanation: Step 1 — flag session boundaries using LAG. Step 2 — assign session IDs using cumulative sum of flags. Step 3 — row number within session minus 1 = clicks before current click.

---

## 5. Data Normalization / Denormalization

### 5.1 Concept: The Spectrum from 3NF to Fully Denormalized

**Normalization** eliminates data redundancy by splitting data into related tables. Good for OLTP (transactional systems). **Denormalization** combines tables to reduce joins, trading storage for query speed. Good for OLAP (analytical queries).

| Form | What It Eliminates | Example |
|------|--------------------|---------|
| 1NF | Repeating groups; atomic values | No arrays in columns |
| 2NF | Partial dependencies on composite key | No column depends on only part of a compound PK |
| 3NF | Transitive dependencies | No non-key column determines another non-key column |
| BCNF | Anomalies 3NF misses | Stricter 3NF |
| Denormalized | Joins for read performance | Star schema; flat tables |

### 5.2 When to Normalize vs Denormalize

```
NORMALIZE WHEN:                          DENORMALIZE WHEN:
- Frequent updates to dimension data      - Read-heavy analytical queries
- Storage is expensive                    - Low-latency dashboard queries
- Data consistency is paramount           - BI tools struggle with many joins
- Source-of-truth operational database    - BigQuery (columnar storage, joins are cheap but denorm is faster)
```

### 5.3 Normalization — Practical SQL Example

```sql
-- NORMALIZED: 3NF schema for campaign management
-- campaigns table
CREATE TABLE campaigns (
    campaign_id STRING PRIMARY KEY,
    campaign_name STRING NOT NULL,
    advertiser_id STRING NOT NULL,  -- FK to advertisers
    channel_id INT NOT NULL,        -- FK to channels
    campaign_type_id INT NOT NULL   -- FK to campaign_types
);

-- channels lookup (avoids repeating channel info in every campaign row)
CREATE TABLE channels (
    channel_id INT PRIMARY KEY,
    channel_name STRING NOT NULL,
    channel_category STRING NOT NULL
);

-- To query: requires JOIN
SELECT c.campaign_name, ch.channel_name, ch.channel_category
FROM campaigns c
JOIN channels ch ON c.channel_id = ch.channel_id;
```

### 5.4 Denormalization — Flat Table for Analytics

```sql
-- DENORMALIZED: flat fact table for BigQuery analytics
-- All dimension attributes embedded directly

CREATE TABLE mart_campaign_performance AS
SELECT
    report_date,
    campaign_id,
    campaign_name,          -- denormalized from campaigns
    channel_name,           -- denormalized from channels
    channel_category,       -- denormalized from channels
    campaign_type,          -- denormalized from campaign_types
    advertiser_name,        -- denormalized from advertisers
    impressions,
    clicks,
    spend_usd,
    conversions,
    revenue_usd,
    roas
FROM daily_metrics dm
JOIN campaigns c USING (campaign_id)
JOIN channels ch USING (channel_id)
JOIN campaign_types ct USING (campaign_type_id)
JOIN advertisers a USING (advertiser_id);
-- No joins needed at query time — everything is in one table
```

### 5.5 SCD (Slowly Changing Dimensions) — Handling Dimension Changes

When a campaign's budget or name changes, how do you preserve history in an analytical context?

```sql
-- SCD Type 1: Overwrite (no history kept)
UPDATE dim_campaigns
SET daily_budget_usd = 1000
WHERE campaign_id = 'C001';
-- Simple, but historical analyses show the new budget for old dates

-- SCD Type 2: Add new row with validity period (full history)
-- Table structure:
-- campaign_surrogate_key (PK), campaign_id (NK), daily_budget_usd,
-- valid_from, valid_to (NULL = current), is_current

-- When budget changes from $500 to $1000 on 2024-06-01:

-- Step 1: Close old record
UPDATE dim_campaigns
SET valid_to = '2024-05-31', is_current = FALSE
WHERE campaign_id = 'C001' AND is_current = TRUE;

-- Step 2: Insert new record
INSERT INTO dim_campaigns VALUES (
    GENERATE_UUID(),  -- new surrogate key
    'C001',           -- natural key stays same
    1000,             -- new budget
    '2024-06-01',     -- valid_from
    NULL,             -- valid_to (current)
    TRUE              -- is_current
);

-- Querying as of a specific date:
SELECT d.*
FROM fact_ad_clicks f
JOIN dim_campaigns d
    ON f.campaign_id = d.campaign_id
    AND f.click_date BETWEEN d.valid_from AND COALESCE(d.valid_to, '9999-12-31')

-- SCD Type 3: Add new column for "previous value"
ALTER TABLE dim_campaigns ADD COLUMN prev_budget_usd FLOAT64;
-- Simple, but only one level of history
```

### 5.6 Interview Questions — Normalization/Denormalization

**Q: When would you denormalize a data model in BigQuery?**

BigQuery is a columnar, distributed query engine. It reads only the columns requested (columnarity). Joins in BigQuery are executed via hash joins or broadcast joins across distributed workers — they're efficient but not zero-cost. Denormalization reduces join overhead and enables better column pruning. For a BI dashboard that runs 10,000 queries/day, a denormalized mart table with all needed attributes embedded is significantly faster and cheaper than a normalized schema requiring 4-5 joins. The tradeoff: storage cost (minor in BigQuery) and stale dimension data (solve with scheduled refreshes).

**Senior Q: A dimension table in your data warehouse changes values frequently (e.g., campaign budget changes daily). You have a fact table linking to it. Stakeholders want historical reports to reflect the budget that was active on that day, not today's budget. How do you implement this?**

This is SCD Type 2. The dimension table needs: a surrogate key (physical PK), the natural key (campaign_id), all dimension attributes (budget), `valid_from` date, `valid_to` date (NULL for current), and `is_current` flag.

When a budget changes: close the current record (set valid_to to yesterday), insert a new record (valid_from = today, valid_to = NULL, is_current = TRUE).

The fact table's FK references the surrogate key (not campaign_id), so it naturally points to the version of the dimension that was active when the fact was recorded. Alternatively (BigQuery pattern): store campaign_id in the fact table and join using the date range: `fact.event_date BETWEEN dim.valid_from AND COALESCE(dim.valid_to, '9999-12-31')`. In DBT, this is implemented using a snapshot.

---

## 6. Handling Messy Data — Nulls, Skew, Duplicates

### 6.1 Null Handling — Comprehensive Patterns

Nulls are not zeros. Nulls are not empty strings. Null represents the absence of a value. This distinction causes subtle bugs in aggregations, joins, and filters.

```sql
-- NULL arithmetic: any arithmetic with NULL returns NULL
SELECT 100 + NULL;     -- NULL
SELECT 100 * NULL;     -- NULL
SELECT NULL = NULL;    -- NULL (not TRUE)
SELECT NULL IS NULL;   -- TRUE

-- NULL in aggregations: NULLs are IGNORED
SELECT AVG(revenue_usd) FROM campaigns;
-- If 5 of 10 rows have NULL revenue, AVG uses only the 5 non-null values
-- This is usually correct for revenue but wrong for "average score including missing as 0"

-- Correct pattern when NULLs should be 0:
SELECT AVG(COALESCE(revenue_usd, 0)) FROM campaigns;

-- NULL in JOINs: NULL never equals NULL
-- Rows where join key is NULL are DROPPED in INNER JOIN
-- In LEFT JOIN, NULL key rows keep the left side with NULLs on right

-- Detect NULLs in join keys before joining:
SELECT COUNT(*) FROM clicks WHERE campaign_id IS NULL;
-- If non-zero → investigate: why are we recording clicks with no campaign?

-- Safe aggregation patterns
SELECT
    campaign_id,
    COUNT(*)                        AS total_rows,
    COUNT(revenue_usd)              AS non_null_revenue_rows,  -- excludes NULLs
    COUNT(*) - COUNT(revenue_usd)   AS null_revenue_rows,
    
    SUM(COALESCE(revenue_usd, 0))   AS total_revenue_treat_null_as_0,
    AVG(COALESCE(revenue_usd, 0))   AS avg_revenue_incl_null,
    AVG(revenue_usd)                AS avg_revenue_excl_null,
    
    -- NULL-safe comparison
    NULLIF(campaign_status, '')     AS status_null_if_empty,
    COALESCE(campaign_name, 'Unknown Campaign') AS safe_name

FROM campaigns
GROUP BY 1;
```

### 6.2 Null Handling in PySpark

```python
from pyspark.sql import functions as F

df = spark.read.parquet("gs://costco-data/ad_events/")

# Check null counts per column
null_counts = df.select([
    F.count(F.when(F.col(c).isNull(), c)).alias(c)
    for c in df.columns
])
null_counts.show()

# Fill nulls
df = df.fillna({
    "campaign_id": "UNKNOWN",
    "cost_usd": 0.0,
    "revenue_usd": 0.0,
    "device_type": "unknown"
})

# Drop rows where critical column is null
df = df.filter(F.col("click_id").isNotNull())

# Conditional null handling
df = df.withColumn(
    "adjusted_cost",
    F.when(F.col("cost_usd").isNull(), 0.0)
     .when(F.col("cost_usd") < 0, 0.0)   # negative costs = data issue
     .otherwise(F.col("cost_usd"))
)

# NULL-safe equality (when joining on potentially-null keys)
# Standard: NULL != NULL → rows are dropped
# NULL-safe: use eqNullSafe
result = df.join(other, df["campaign_id"].eqNullSafe(other["campaign_id"]))
```

### 6.3 Deduplication — Full Arsenal

```sql
-- ============================================================
-- Method 1: ROW_NUMBER (most flexible — choose best duplicate)
-- ============================================================
WITH ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY click_id                    -- dedup key
               ORDER BY _loaded_at DESC, updated_at DESC -- prefer most recent load
           ) AS rn
    FROM raw_ad_clicks
)
SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1;

-- ============================================================
-- Method 2: GROUP BY + aggregate (lossy but simple)
-- ============================================================
-- Use when: you want max/latest value per key
SELECT
    click_id,
    MAX(campaign_id)    AS campaign_id,
    MAX(clicked_at)     AS clicked_at,
    MAX(cost_usd)       AS cost_usd,
    MAX(_loaded_at)     AS loaded_at
FROM raw_ad_clicks
GROUP BY click_id;

-- ============================================================
-- Method 3: QUALIFY (BigQuery/Snowflake shorthand)
-- ============================================================
SELECT * FROM raw_ad_clicks
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY click_id
    ORDER BY _loaded_at DESC
) = 1;

-- ============================================================
-- Method 4: Exact duplicate removal (all columns identical)
-- ============================================================
SELECT DISTINCT * FROM raw_ad_clicks;
-- Caution: DISTINCT on wide tables is expensive (triggers shuffle in Spark)

-- ============================================================
-- Method 5: MERGE-based dedup (for incremental tables)
-- ============================================================
MERGE INTO clean_clicks AS target
USING (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY click_id ORDER BY _loaded_at DESC) AS rn
    FROM raw_ad_clicks
    WHERE _loaded_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 DAY)
) AS source
ON target.click_id = source.click_id AND source.rn = 1
WHEN MATCHED THEN
    UPDATE SET target.cost_usd = source.cost_usd,
               target.updated_at = source._loaded_at
WHEN NOT MATCHED AND source.rn = 1 THEN
    INSERT VALUES (source.click_id, source.campaign_id, source.cost_usd, source._loaded_at);
```

### 6.4 Deduplication in PySpark

```python
# Method 1: dropDuplicates (exact match on specified columns)
df_dedup = df.dropDuplicates(["click_id"])
# Problem: which duplicate is kept is non-deterministic!

# Method 2: Window-based (deterministic — keep latest)
from pyspark.sql.window import Window

w = Window.partitionBy("click_id").orderBy(F.desc("_loaded_at"))
df_dedup = df.withColumn("rn", F.row_number().over(w)) \
             .filter(F.col("rn") == 1) \
             .drop("rn")

# Method 3: Aggregate-based (for simple cases)
from pyspark.sql.functions import first

df_dedup = df.orderBy("click_id", F.desc("_loaded_at")) \
             .groupBy("click_id") \
             .agg(
                 F.first("campaign_id").alias("campaign_id"),
                 F.first("cost_usd").alias("cost_usd"),
                 F.first("_loaded_at").alias("_loaded_at")
             )
```

### 6.5 Data Skew — Detection and Fix

Data skew happens when one key has far more rows than others. In Spark, this means one partition (and one task) handles most of the data while others finish quickly — the job stalls waiting for the "straggler."

```python
# Step 1: Detect skew
# Check distribution of join key
skew_check = df.groupBy("campaign_id") \
               .count() \
               .orderBy(F.desc("count"))
skew_check.show(20)

# If one campaign_id has 10M rows and others have 10K → severe skew

# Step 2: Fix with salting
N_SALT = 50

# Salt the large (skewed) side
df_salted = df.withColumn("salt", (F.rand() * N_SALT).cast("int")) \
              .withColumn("salted_key", F.concat_ws("_", "campaign_id", "salt"))

# Explode the small side to match all salts
small_df_exploded = small_df \
    .withColumn("salt", F.explode(F.array([F.lit(i) for i in range(N_SALT)]))) \
    .withColumn("salted_key", F.concat_ws("_", "campaign_id", "salt"))

# Join on salted key (skew is now distributed)
result = df_salted.join(small_df_exploded, "salted_key", "left") \
                  .drop("salt", "salted_key")

# Step 3: Use AQE skew handling (automatic)
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.skewedPartitionFactor", "5")
spark.conf.set("spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes", "256MB")
# AQE splits skewed partitions automatically
```

### 6.6 Type Coercion and Schema Enforcement

```sql
-- BigQuery: strict typing — explicit casts required
SELECT
    -- String to numeric
    CAST(clicks AS INT64)               AS clicks_int,
    SAFE_CAST(spend_str AS FLOAT64)     AS spend_float,  -- returns NULL on failure
    
    -- Numeric to string
    CAST(campaign_id AS STRING)         AS campaign_id_str,
    
    -- Date/timestamp conversions
    CAST(date_string AS DATE)           AS event_date,
    PARSE_DATE('%Y%m%d', '20240115')    AS parsed_date,
    PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', ts_str) AS parsed_ts,
    
    -- Consistent null handling during cast
    NULLIF(TRIM(status_col), '')        AS clean_status,  -- empty string → NULL
    COALESCE(SAFE_CAST(amount AS FLOAT64), 0.0) AS safe_amount
```

```python
# PySpark: schema enforcement on read
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType

schema = StructType([
    StructField("click_id", StringType(), nullable=False),
    StructField("campaign_id", StringType(), nullable=True),
    StructField("cost_usd", DoubleType(), nullable=True),
    StructField("clicked_at", TimestampType(), nullable=False)
])

df = spark.read.schema(schema).parquet("gs://costco-data/clicks/")
# Rows that don't match schema → NULL for that column (not error by default)

# Enforce schema: fail on unknown columns
df = spark.read.schema(schema).option("mode", "FAILFAST").parquet(...)
```

### 6.7 Interview Questions — Messy Data

**Q: How do you handle NULL values in a GROUP BY aggregation?**

NULL values are treated as their own group in GROUP BY — all rows with NULL key are grouped together into one group labeled NULL. In aggregation functions (SUM, AVG, COUNT), NULLs in the VALUE column are ignored. Null in a COUNT(*) is counted (it counts rows). COUNT(column) ignores NULLs. To treat NULL as a specific value in aggregation, use `COALESCE(col, 0)`. To treat NULL as a specific group label, use `COALESCE(group_col, 'Unknown')`.

**Senior Q: You're building an incremental pipeline that processes click events. The same click_id can appear multiple times due to late loads and retransmissions. The cost_usd may be updated after initial ingestion (cost adjustments). How do you design the deduplication logic?**

Use a three-step approach:
1. In the raw/staging layer, use ROW_NUMBER with `PARTITION BY click_id ORDER BY _loaded_at DESC, updated_at DESC` to pick the most recent version of each click. This handles retransmissions.
2. In the incremental pipeline, use a MERGE with `click_id` as the unique key. If a click_id already exists, update cost_usd and updated_at. If new, insert. This handles the cost adjustment case.
3. Add a data quality check: assert that after deduplication, COUNT(click_id) = COUNT(DISTINCT click_id). Alert if it fails.
4. For late data, process a 3-day lookback window (not just "new since last run") to catch delayed loads.

---

## 7. JSON, Nested & Semi-Structured Transformations

### 7.1 Concept: Semi-Structured Data in Modern Pipelines

AdTech and MarTech data is inherently semi-structured. Ad event payloads, campaign configurations, audience segments, and tracking parameters all arrive as JSON. Senior engineers must extract, flatten, and reshape this data efficiently.

### 7.2 BigQuery JSON Functions

```sql
-- Example: raw_events.payload is a JSON STRING column
-- {"event":"click","campaign":{"id":"C001","name":"Summer Sale"},"user":{"id":"U123","age":28},"props":{"device":"mobile","utm_source":"google"}}

SELECT
    event_id,
    
    -- Extract scalar values
    JSON_VALUE(payload, '$.event')                  AS event_type,
    JSON_VALUE(payload, '$.campaign.id')            AS campaign_id,
    JSON_VALUE(payload, '$.campaign.name')          AS campaign_name,
    JSON_VALUE(payload, '$.user.id')                AS user_id,
    CAST(JSON_VALUE(payload, '$.user.age') AS INT64) AS user_age,
    JSON_VALUE(payload, '$.props.device')           AS device_type,
    JSON_VALUE(payload, '$.props.utm_source')       AS utm_source,
    
    -- Extract nested object as JSON string (for further processing)
    JSON_QUERY(payload, '$.campaign')               AS campaign_json,
    
    -- Extract array
    JSON_QUERY_ARRAY(payload, '$.tags')             AS tags_array,
    
    -- Array element
    JSON_VALUE(payload, '$.tags[0]')                AS first_tag,
    
    -- Check existence
    JSON_VALUE(payload, '$.experimental') IS NOT NULL AS has_experimental_field

FROM raw_events;

-- UNNEST arrays from JSON
SELECT
    event_id,
    tag
FROM raw_events,
UNNEST(JSON_QUERY_ARRAY(payload, '$.tags')) AS tag;

-- Parse JSON into struct
SELECT
    event_id,
    STRUCT(
        JSON_VALUE(payload, '$.campaign.id')    AS id,
        JSON_VALUE(payload, '$.campaign.name')  AS name,
        JSON_VALUE(payload, '$.campaign.type')  AS type
    ) AS campaign
FROM raw_events;
```

### 7.3 BigQuery STRUCT and ARRAY Columns (Native Semi-Structured)

```sql
-- BigQuery natively supports STRUCT and ARRAY types in table columns
-- Example: a table with nested structs

-- Schema:
-- event_id: STRING
-- campaign: STRUCT<id STRING, name STRING, budget FLOAT64>
-- tags: ARRAY<STRING>
-- targeting: ARRAY<STRUCT<type STRING, value STRING>>

SELECT
    event_id,
    
    -- Access struct fields with dot notation
    campaign.id                         AS campaign_id,
    campaign.name                       AS campaign_name,
    campaign.budget                     AS campaign_budget,
    
    -- Array operations
    ARRAY_LENGTH(tags)                  AS tag_count,
    tags[SAFE_OFFSET(0)]                AS first_tag,        -- NULL-safe
    tags[ORDINAL(1)]                    AS first_tag_ordinal, -- 1-indexed
    'retargeting' IN UNNEST(tags)       AS is_retargeting,
    
    -- UNNEST array of structs
    t.type                              AS targeting_type,
    t.value                             AS targeting_value

FROM ad_events,
UNNEST(targeting) AS t      -- each targeting element becomes a row
WHERE event_date = '2024-01-15';

-- Flatten nested array into separate rows
SELECT
    e.event_id,
    e.campaign.id AS campaign_id,
    tag
FROM ad_events e,
UNNEST(e.tags) AS tag
WHERE '2024-01-15' = e.event_date;

-- Reconstruct arrays from flat data
SELECT
    campaign_id,
    ARRAY_AGG(STRUCT(device_type, clicks, spend_usd)
              ORDER BY spend_usd DESC) AS device_breakdown
FROM daily_performance
GROUP BY campaign_id;
```

### 7.4 PySpark JSON and Nested Data

```python
from pyspark.sql.functions import (
    from_json, to_json, get_json_object, json_tuple,
    schema_of_json, explode, explode_outer, posexplode,
    col, struct, array
)
from pyspark.sql.types import StructType, StructField, StringType, ArrayType, MapType

# ============================================================
# Parse JSON string column
# ============================================================
# Option 1: Define schema explicitly (faster — no schema inference)
event_schema = StructType([
    StructField("event", StringType()),
    StructField("campaign", StructType([
        StructField("id", StringType()),
        StructField("name", StringType()),
        StructField("budget", DoubleType())
    ])),
    StructField("user", StructType([
        StructField("id", StringType()),
        StructField("age", IntegerType())
    ])),
    StructField("tags", ArrayType(StringType())),
    StructField("props", MapType(StringType(), StringType()))
])

df_parsed = df.withColumn("parsed", from_json(col("payload"), event_schema))

# Access nested fields
df_flat = df_parsed.select(
    "event_id",
    col("parsed.event").alias("event_type"),
    col("parsed.campaign.id").alias("campaign_id"),
    col("parsed.campaign.name").alias("campaign_name"),
    col("parsed.user.id").alias("user_id"),
    col("parsed.user.age").alias("user_age"),
    col("parsed.tags").alias("tags"),
    col("parsed.props").alias("props")
)

# Option 2: Infer schema from sample (convenient but slower)
sample_json = '{"event":"click","campaign":{"id":"C1"}}'
inferred_schema = schema_of_json(sample_json)
df_parsed2 = df.withColumn("parsed", from_json(col("payload"), inferred_schema))

# Option 3: get_json_object for individual fields (no schema needed)
df_simple = df.select(
    "event_id",
    get_json_object(col("payload"), "$.campaign.id").alias("campaign_id"),
    get_json_object(col("payload"), "$.user.age").cast("int").alias("user_age")
)

# ============================================================
# EXPLODE arrays
# ============================================================
# Explode tags array — each tag becomes its own row
df_exploded = df_flat.select(
    "event_id",
    "campaign_id",
    explode(col("tags")).alias("tag")  # NULL array → dropped
)

# explode_outer: keeps rows even when array is NULL/empty
df_exploded_outer = df_flat.select(
    "event_id",
    explode_outer(col("tags")).alias("tag")  # NULL array → one row with NULL tag
)

# posexplode: includes array index
df_with_pos = df_flat.select(
    "event_id",
    posexplode(col("tags")).alias("tag_pos", "tag")
)

# ============================================================
# Map type access
# ============================================================
df_with_device = df_flat.select(
    "event_id",
    col("props")["device"].alias("device_type"),
    col("props")["utm_source"].alias("utm_source"),
    col("props")["utm_medium"].alias("utm_medium")
)

# ============================================================
# Reconstruct nested from flat
# ============================================================
df_nested = df_flat.select(
    "event_id",
    struct("campaign_id", "campaign_name").alias("campaign"),
    array("tag1", "tag2").alias("tags")
)
```

### 7.5 Handling Schema Evolution in Semi-Structured Data

```sql
-- Problem: JSON payload structure changes over time (new fields added, old removed)
-- Solution: Use JSON_VALUE with NULL-safe extraction and defaults

SELECT
    event_id,
    event_date,
    
    -- New field (may not exist in old events)
    COALESCE(JSON_VALUE(payload, '$.new_field'), 'default_value') AS new_field,
    
    -- Renamed field (check both old and new name)
    COALESCE(
        JSON_VALUE(payload, '$.new_campaign_id'),
        JSON_VALUE(payload, '$.campaign_id')  -- old field name
    ) AS campaign_id,
    
    -- Conditional parsing based on event version
    CASE
        WHEN JSON_VALUE(payload, '$.schema_version') = '2'
            THEN JSON_VALUE(payload, '$.user.external_id')
        ELSE JSON_VALUE(payload, '$.user_id')
    END AS user_id

FROM raw_events;
```

### 7.6 Interview Questions — Semi-Structured Data

**Q: How do you flatten a nested JSON structure in BigQuery?**

In BigQuery, if the JSON is stored as a STRING column, use `JSON_VALUE(col, '$.path')` for scalar fields and `JSON_QUERY_ARRAY(col, '$.array_field')` for arrays. Then UNNEST the array to get flat rows. If the data is stored as native STRUCT/ARRAY types (BigQuery's preferred approach for known schemas), use dot notation for structs (`col.field.subfield`) and `UNNEST(array_col)` in the FROM clause. For performance, native STRUCT/ARRAY is faster than parsing JSON strings at query time.

**Senior Q: Your ad event pipeline receives JSON payloads from multiple ad platforms. Each platform has a different schema. Design a PySpark transformation that handles them all consistently.**

Approach:
1. Read each platform's data into separate DataFrames with platform-specific schemas defined explicitly (don't infer at runtime).
2. Build a `normalize_platform` function per platform that extracts and renames fields to a unified schema: `{event_id, platform, campaign_id, ad_group_id, user_id, event_type, event_at, cost_usd, revenue_usd}`.
3. UNION ALL the normalized DataFrames.
4. For fields that don't exist in a platform, fill with NULL and document the limitation.
5. Version the schema: store `schema_version` in the output so downstream consumers know what to expect.
6. Use a `schema_registry` config (YAML or BigQuery table) to map each platform's raw fields to the unified schema, making the mapping declarative rather than hardcoded.

---

## 8. Business Metric Derivation — Real-World Scenarios

### 8.1 AdTech Metrics — The Full Set

```sql
-- Complete AdTech metrics for a campaign performance report

SELECT
    report_date,
    campaign_id,
    campaign_name,
    channel,
    
    -- ===== Volume Metrics =====
    impressions,
    clicks,
    conversions,
    
    -- ===== Rate Metrics =====
    ROUND(SAFE_DIVIDE(clicks, impressions) * 100, 4)            AS ctr_pct,        -- Click-Through Rate
    ROUND(SAFE_DIVIDE(conversions, clicks) * 100, 4)            AS cvr_pct,        -- Conversion Rate
    ROUND(SAFE_DIVIDE(conversions, impressions) * 100, 6)       AS view_cvr_pct,   -- View-Through CVR
    
    -- ===== Cost Metrics =====
    spend_usd,
    ROUND(SAFE_DIVIDE(spend_usd, impressions) * 1000, 4)        AS cpm_usd,        -- Cost Per Mille
    ROUND(SAFE_DIVIDE(spend_usd, clicks), 4)                    AS cpc_usd,        -- Cost Per Click
    ROUND(SAFE_DIVIDE(spend_usd, conversions), 4)               AS cpa_usd,        -- Cost Per Acquisition
    
    -- ===== Revenue Metrics =====
    revenue_usd,
    ROUND(SAFE_DIVIDE(revenue_usd, spend_usd), 4)               AS roas,           -- Return on Ad Spend
    revenue_usd - spend_usd                                     AS profit_usd,     -- Gross Profit
    ROUND(SAFE_DIVIDE(revenue_usd - spend_usd, revenue_usd) * 100, 2) AS margin_pct,
    
    -- ===== Efficiency Metrics =====
    ROUND(SAFE_DIVIDE(unique_reach, impressions) * 100, 2)      AS reach_pct,      -- % unique users reached
    ROUND(SAFE_DIVIDE(impressions, unique_reach), 2)            AS avg_frequency,  -- Avg impressions per user
    
    -- ===== Engagement =====
    video_views,
    ROUND(SAFE_DIVIDE(video_views, impressions) * 100, 2)       AS vtr_pct,        -- View-Through Rate
    engagements,
    ROUND(SAFE_DIVIDE(engagements, impressions) * 100, 2)       AS engagement_rate_pct

FROM mart_campaign_daily_performance
WHERE report_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) AND CURRENT_DATE();
```

### 8.2 Costco-Specific Metrics — Member LTV and RFM

```sql
-- RFM Scoring for Costco members
-- Recency: days since last purchase
-- Frequency: number of purchases
-- Monetary: total spend

WITH member_metrics AS (
    SELECT
        member_id,
        DATE_DIFF(CURRENT_DATE(), MAX(purchase_date), DAY)  AS recency_days,
        COUNT(DISTINCT transaction_id)                       AS frequency,
        SUM(purchase_amount_usd)                             AS monetary_value,
        AVG(purchase_amount_usd)                             AS avg_order_value,
        MIN(purchase_date)                                   AS first_purchase_date,
        MAX(purchase_date)                                   AS last_purchase_date,
        DATE_DIFF(MAX(purchase_date), MIN(purchase_date), DAY) AS customer_age_days
    FROM member_transactions
    WHERE purchase_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
    GROUP BY 1
),

rfm_scored AS (
    SELECT
        *,
        -- Quintile scoring (1=worst, 5=best)
        NTILE(5) OVER (ORDER BY recency_days ASC)   AS r_score,   -- lower days = better
        NTILE(5) OVER (ORDER BY frequency ASC)       AS f_score,
        NTILE(5) OVER (ORDER BY monetary_value ASC)  AS m_score
    FROM member_metrics
),

segmented AS (
    SELECT
        *,
        CONCAT(CAST(r_score AS STRING), CAST(f_score AS STRING), CAST(m_score AS STRING)) AS rfm_cell,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Loyal Members'
            WHEN r_score >= 4 AND f_score <= 2                   THEN 'New Members'
            WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3 THEN 'At Risk'
            WHEN r_score <= 2 AND f_score <= 2 AND m_score >= 3 THEN 'Cant Lose Them'
            WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN 'Lost'
            ELSE 'Potential Loyalists'
        END AS member_segment,
        
        -- Simple LTV: avg_order_value * frequency * expected_years_remaining
        avg_order_value * frequency * (3 - customer_age_days / 365.0) AS simple_ltv_usd
    FROM rfm_scored
)

SELECT * FROM segmented;
```

### 8.3 Attribution Models — SQL Implementation

```sql
-- Compare Last-Touch, First-Touch, Linear, Time-Decay attribution
-- in one query using window functions

WITH touchpoints AS (
    SELECT
        conversion_id,
        user_id,
        conversion_value_usd,
        campaign_id,
        channel,
        touch_timestamp,
        conversion_timestamp,
        
        -- Touch position metadata
        ROW_NUMBER() OVER (
            PARTITION BY conversion_id ORDER BY touch_timestamp ASC
        ) AS touch_num,
        ROW_NUMBER() OVER (
            PARTITION BY conversion_id ORDER BY touch_timestamp DESC
        ) AS touch_num_rev,
        COUNT(*) OVER (PARTITION BY conversion_id) AS total_touches,
        TIMESTAMP_DIFF(conversion_timestamp, touch_timestamp, HOUR) AS hours_before_conv
    FROM conversion_touchpoints  -- one row per touch per conversion
),

attributed AS (
    SELECT
        *,
        
        -- Last-touch: 100% to last click
        CASE WHEN touch_num_rev = 1 THEN conversion_value_usd ELSE 0 END
            AS last_touch_credit,
        
        -- First-touch: 100% to first click
        CASE WHEN touch_num = 1 THEN conversion_value_usd ELSE 0 END
            AS first_touch_credit,
        
        -- Linear: equal split
        conversion_value_usd / total_touches AS linear_credit,
        
        -- Time-decay: recency weighted (half-life = 7 days)
        conversion_value_usd *
            POW(0.5, hours_before_conv / 168.0)  -- 168 hours = 7 days
            / SUM(POW(0.5, hours_before_conv / 168.0)) OVER (PARTITION BY conversion_id)
            AS time_decay_credit,
        
        -- U-shaped: 40% first, 40% last, 20% split among middle
        CASE
            WHEN total_touches = 1 THEN conversion_value_usd
            WHEN touch_num = 1 THEN conversion_value_usd * 0.4
            WHEN touch_num_rev = 1 THEN conversion_value_usd * 0.4
            ELSE conversion_value_usd * 0.2 / GREATEST(total_touches - 2, 1)
        END AS u_shaped_credit

    FROM touchpoints
)

SELECT
    campaign_id,
    channel,
    COUNT(DISTINCT conversion_id)       AS conversions,
    SUM(last_touch_credit)              AS last_touch_revenue,
    SUM(first_touch_credit)             AS first_touch_revenue,
    SUM(linear_credit)                  AS linear_revenue,
    SUM(time_decay_credit)              AS time_decay_revenue,
    SUM(u_shaped_credit)                AS u_shaped_revenue
FROM attributed
GROUP BY 1, 2
ORDER BY last_touch_revenue DESC;
```

### 8.4 Interview Questions — Business Metrics

**Q: What is ROAS and how is it different from ROI?**

ROAS (Return on Ad Spend) = Revenue / Ad Spend. It measures how much revenue was generated for each dollar spent on advertising specifically. A ROAS of 4 means $4 of revenue per $1 of ad spend. ROI (Return on Investment) = (Gain - Cost) / Cost. It accounts for ALL costs (not just ad spend) and measures net profit relative to total investment. ROAS > ROI because ROAS ignores COGS, overhead, and other costs. For a Costco marketing campaign with $100K spend generating $400K revenue: ROAS = 4.0, but if COGS is 60%, actual profit is $60K (profit margin applied), so true ROI = ($60K - $100K) / $100K = -40%. The campaign lost money despite a "good" ROAS.

**Senior Q: You're asked to build a multi-touch attribution model. Last-touch shows Google Search gets 80% of credit. But the marketing team suspects Meta display ads play a role earlier in the funnel. How do you design the analysis to prove or disprove this?**

Build a path analysis:
1. Reconstruct the full path to conversion: ORDER BY touch_timestamp per conversion, STRING_AGG channels to get paths like "meta_display > email > google_search > conversion".
2. Group by path and count conversions + total revenue. Identify which paths lead to conversion most often and with highest value.
3. Compare first-touch vs last-touch attribution by channel — if Meta is high on first-touch and low on last-touch, it's playing a top-of-funnel assist role.
4. Compute "assist rate" for Meta: what % of conversions had at least one Meta touch that wasn't the last touch?
5. Run Markov chain attribution (probabilistic) to quantify the marginal contribution of removing each channel from the path.
6. Present: "If we removed Meta display from the mix, assisted conversions through Google Search would drop by X% because Meta was responsible for Y% of top-funnel awareness."

---

## Summary: Data Transformation & Mangling — Senior-Level Mastery Checklist

| Skill | What Senior Looks Like |
|-------|------------------------|
| SQL CTEs | Multi-step pipelines, each step testable, no nested subqueries |
| Window Functions | Can write sessionization, islands, rolling metrics from memory |
| Aggregations | GROUPING SETS, cohort analysis, funnel analysis |
| Deduplication | ROW_NUMBER approach, handles late data, incremental MERGE |
| Spark transformations | Knows wide vs narrow, optimizes shuffle, uses broadcast/salt |
| Null handling | Never makes null == 0 silently; documents assumption |
| JSON | Handles schema evolution, uses STRUCT/ARRAY natively in BigQuery |
| Attribution | Implements last/first/linear/time-decay in SQL from scratch |
| RFM | Can build NTILE-based segmentation and interpret segments |
| Skew | Detects in Spark UI, fixes with salting or AQE |
