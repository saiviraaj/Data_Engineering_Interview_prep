# Topic 11: Performance Optimization (CRITICAL FOR SENIOR ROLE)
## Costco Sr. Data Engineer — Exhaustive Interview Textbook

---

## Table of Contents
1. [L1: Core Concepts — Performance Basics](#l1-core-concepts)
2. [L2: Deep Technical Understanding](#l2-deep-technical-understanding)
3. [L3: Real-World Scenarios — Costco/MarTech Style](#l3-real-world-scenarios)
4. [L4: Hands-On Optimization](#l4-hands-on-optimization)
5. [L5: Edge Cases & Pitfalls](#l5-edge-cases--pitfalls)
6. [L6: Interview Questions — Easy to Very Hard](#l6-interview-questions)

---

## L1: Core Concepts

### 1.1 What is Performance Optimization?

Performance optimization in data engineering means making data pipelines and queries faster, cheaper, and more reliable — without changing their output. The goal is to process more data with less time, less compute, and less cost.

**Three dimensions of performance**:

| Dimension | Measure | Optimization Goal |
|-----------|---------|-------------------|
| **Speed** | Query/job execution time | Minimize latency |
| **Cost** | Bytes processed, slot hours | Minimize spend |
| **Scale** | Throughput at peak load | Maximize without degradation |

**The golden rule**: You cannot optimize what you cannot measure. Before tuning anything, establish a baseline — execution time, bytes scanned, slot usage, cost. Then measure after each change.

---

### 1.2 Where Performance Is Lost — The Stack

```
Query/Job Performance = f(
    Data Volume Scanned,    ← partition/filter optimization
    Data Organization,      ← partitioning, clustering, file format
    Computation,            ← join strategy, aggregation method
    I/O (network/disk),     ← shuffle, spill, data locality
    Parallelism             ← partition count, slot allocation
)
```

**In BigQuery**:
- Primary lever: reduce bytes scanned (partition pruning, column selection)
- Secondary: join strategy, slot efficiency

**In Spark/Dataproc**:
- Primary lever: minimize shuffle (wide transformations)
- Secondary: partition count, skew handling, caching

---

## L2: Deep Technical Understanding

### 2.1 BigQuery Optimization — Complete Deep Dive

#### 2.1.1 Partitioning

Partitioning divides a table into physical segments by a column. BigQuery reads ONLY the partitions that satisfy your filter — not the entire table.

**Types of partitioning**:

```sql
-- 1. Date/Timestamp partitioning (most common)
CREATE TABLE `project.dataset.ad_clicks`
PARTITION BY click_date               -- DATE column
OPTIONS (
    partition_expiration_days = 365   -- auto-delete old partitions
)
AS SELECT *, DATE(clicked_at) AS click_date FROM raw_clicks;

-- 2. Integer range partitioning
CREATE TABLE `project.dataset.campaigns`
PARTITION BY RANGE_BUCKET(campaign_id_int, GENERATE_ARRAY(0, 10000000, 100000))
-- Creates partitions for campaign_id ranges: [0-100K), [100K-200K), etc.

-- 3. Ingestion-time partitioning (automatic, uses _PARTITIONTIME)
CREATE TABLE `project.dataset.events`
PARTITION BY _PARTITIONDATE  -- auto-assigned when rows are loaded
```

**Partition pruning — how it works**:
```sql
-- Table: 1000 partitions (1000 days), 100GB total

-- WITH partition filter → reads 1 partition (0.1GB)
SELECT * FROM `project.dataset.ad_clicks`
WHERE click_date = '2024-01-15';        -- reads 0.1GB ✓

-- WITHOUT partition filter → reads all 1000 partitions (100GB) 
SELECT * FROM `project.dataset.ad_clicks`
WHERE campaign_id = 'C001';            -- reads 100GB ✗

-- Partition filter requirement (for large tables):
ALTER TABLE `project.dataset.ad_clicks`
SET OPTIONS (require_partition_filter = TRUE);
-- Now queries without partition filter FAIL with an error
-- Prevents accidental full table scans
```

**Partition pruning killers**:
```sql
-- KILLER: function on partition column destroys pruning
WHERE YEAR(click_date) = 2024           -- NO pruning: function evaluated on all rows
WHERE DATE_TRUNC(click_date, YEAR) = '2024-01-01'  -- NO pruning

-- FIX: compare directly
WHERE click_date BETWEEN '2024-01-01' AND '2024-12-31'  -- pruning works ✓
WHERE click_date >= '2024-01-01' AND click_date < '2025-01-01'  -- also works ✓
```

#### 2.1.2 Clustering

Clustering colocates similar data within each partition, enabling BigQuery to skip entire blocks within a partition.

```sql
-- Create table with 4-column clustering
CREATE TABLE `project.dataset.ad_clicks`
PARTITION BY click_date
CLUSTER BY campaign_id, channel, device_type, ad_group_id
-- BigQuery sorts data by (campaign_id, channel, device_type, ad_group_id) within each partition

-- Clustering benefits queries that filter on leading cluster columns
-- Full benefit: filter on campaign_id (first cluster column)
-- Partial benefit: filter on campaign_id + channel (first two)
-- No benefit: filter on device_type without campaign_id (not leading)
```

**Measuring clustering benefit**:
```sql
-- BigQuery shows "rows scanned" vs "rows returned" in job stats
-- If rows_scanned >> rows_returned, clustering is helping
-- If rows_scanned ≈ total_rows, clustering isn't being used

-- Check actual bytes scanned using DRY RUN
-- In BigQuery Console: query shows estimated bytes before you run
```

**When clustering beats partitioning**:
- High-cardinality column (thousands of distinct values — too many partitions)
- Column often filtered but not date-based
- Need multi-column filtering optimization

**Partition vs Cluster rule of thumb**:
- Use partition for the time dimension (date/timestamp) — drives coarse pruning
- Use cluster for the analytical dimensions (campaign_id, channel) — drives fine pruning within partition

#### 2.1.3 Column Selection — Columnar Advantage

BigQuery is columnar: it stores each column separately and reads only requested columns.

```sql
-- BAD: reads ALL columns across all rows in the partition
SELECT * FROM `project.dataset.ad_clicks`
WHERE click_date = '2024-01-15';
-- If table has 100 columns, reads 100 columns even if you need 5

-- GOOD: reads only 5 columns
SELECT click_id, campaign_id, user_id, clicked_at, cost_usd
FROM `project.dataset.ad_clicks`
WHERE click_date = '2024-01-15';
-- Cost can be 20x lower (5/100 = 5% of data scanned)

-- Rule: Never SELECT * in production queries on large tables
-- Exception: staging models where you intentionally want all columns
```

#### 2.1.4 Join Optimization in BigQuery

```sql
-- BigQuery uses hash joins: smaller table is hashed, larger table probes
-- Optimizer usually chooses correctly, but you can hint

-- If optimizer makes wrong choice:
SELECT /*+ BROADCAST(small_table) */ *
FROM large_table
JOIN small_table USING (id);

-- For small lookup tables (<10MB), BigQuery automatically broadcasts
-- Set threshold:
-- In job: SET @@query.large_results_threshold = 100MB;

-- Denormalization: for frequently-joined dimensions, embed in fact table
-- Avoid: joins at query time for every BI query
-- Better: embed campaign_name, channel directly in mart table
-- Tradeoff: stale dimension data → solve with scheduled refresh
```

#### 2.1.5 Slot Management and Concurrency

```sql
-- BigQuery slots = units of computation (1 slot = 1 CPU core approx)
-- On-demand pricing: each query gets up to 2000 slots (shared pool)
-- Reservations: dedicated slot pool for consistent performance

-- Check slot utilization for your queries
SELECT
    job_id,
    total_slot_ms / (end_time - start_time) / 1000 AS avg_slots_used,
    total_bytes_processed / POW(1024, 3) AS gb_processed
FROM `region-us`.INFORMATION_SCHEMA.JOBS
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
ORDER BY total_slot_ms DESC
LIMIT 20;
```

---

### 2.2 Spark/Dataproc Optimization — Complete Deep Dive

#### 2.2.1 The Shuffle — Root Cause of Most Spark Performance Issues

Every GROUP BY, JOIN, DISTINCT, repartition triggers a shuffle. Shuffle = network I/O + disk I/O = expensive.

**Measuring shuffle impact**:
```
Spark UI → Stages tab → look for:
- "Shuffle Write" size in Stage N
- "Shuffle Read" size in Stage N+1
- Spill (Memory) and Spill (Disk) — indicate partition size > memory
- Stage duration dominated by one task (skew)
```

**Minimizing shuffle**:
```python
# Strategy 1: Combine multiple groupBys into one
# BAD: 3 shuffles
daily_clicks = df.groupBy("campaign_id").agg(F.sum("clicks"))
daily_spend  = df.groupBy("campaign_id").agg(F.sum("spend"))
daily_convs  = df.groupBy("campaign_id").agg(F.sum("conversions"))
result = daily_clicks.join(daily_spend, "campaign_id") \
                     .join(daily_convs, "campaign_id")  # 3 separate shuffles

# GOOD: 1 shuffle
result = df.groupBy("campaign_id").agg(
    F.sum("clicks").alias("clicks"),
    F.sum("spend").alias("spend"),
    F.sum("conversions").alias("conversions")
)

# Strategy 2: Pre-filter before shuffle
# BAD: shuffle entire table then filter
df.groupBy("campaign_id").agg(F.sum("spend")) \
  .filter(F.col("campaign_id").isin(active_ids))

# GOOD: filter before shuffle (less data to shuffle)
df.filter(F.col("campaign_id").isin(active_ids)) \
  .groupBy("campaign_id").agg(F.sum("spend"))
```

#### 2.2.2 Partition Count Tuning

```python
# Too few partitions: not enough parallelism, large partitions → OOM
# Too many partitions: overhead of managing thousands of tiny tasks
# Target: 128-256 MB per partition

# Check current partition sizes
df.rdd.mapPartitions(lambda it: [sum(1 for _ in it)]).collect()
# → [10000, 9800, 400000, 9900, ...]  ← partition 2 is 40x larger = skew

# Set shuffle partitions (default=200, often wrong)
spark.conf.set("spark.sql.shuffle.partitions", "500")

# AQE (Adaptive Query Execution) — auto-tunes partition count
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.minPartitionNum", "1")
spark.conf.set("spark.sql.adaptive.advisoryPartitionSizeInBytes", "128MB")
# AQE combines small post-shuffle partitions and splits large ones

# For input data: repartition to right count before heavy operations
optimal_partitions = max(df.rdd.getNumPartitions(), 
                         int(df_size_bytes / (128 * 1024 * 1024)))
df = df.repartition(optimal_partitions)
```

#### 2.2.3 Broadcast Join — Eliminate Small-Table Shuffles

```python
from pyspark.sql.functions import broadcast

# Standard join: BOTH sides shuffled → 2 shuffles
result = large_clicks.join(campaigns, "campaign_id")

# Broadcast join: campaigns broadcast to all executors → 0 shuffles
result = large_clicks.join(broadcast(campaigns), "campaign_id")
# Requirements: campaigns must fit in executor memory (default threshold: 10MB)

# Increase threshold for larger lookup tables (be careful of OOM)
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "100MB")
# Rule: only broadcast tables that fit comfortably in executor memory
# with headroom. If executor has 4GB, don't broadcast 3GB table.

# Check join strategy in physical plan
result.explain(True)
# Look for: BroadcastHashJoin vs SortMergeJoin
# BroadcastHashJoin = one side broadcasted (fast)
# SortMergeJoin = both sides shuffled (slow for large data)
```

#### 2.2.4 Data Skew — Detection and Fix

```python
# Step 1: Detect skew in Spark UI
# Stage → Task Duration → look for one task taking 10x longer than others
# Or check programmatically:
key_distribution = df.groupBy("campaign_id").count() \
                     .orderBy(F.desc("count"))
key_distribution.show(10)
# output: one campaign_id has 500M rows, others have 1M → severe skew

# Step 2: Fix with salting
import random

N_SALT = 50

# Salt the skewed (large) side
skewed = clicks.withColumn("salt", (F.rand() * N_SALT).cast("int")) \
               .withColumn("salted_key", F.concat_ws("_", "campaign_id", "salt"))

# Explode the small side to match all salts
small = campaigns \
    .withColumn("salt_arr", F.array([F.lit(i) for i in range(N_SALT)])) \
    .withColumn("salt", F.explode("salt_arr")) \
    .withColumn("salted_key", F.concat_ws("_", "campaign_id", "salt")) \
    .drop("salt_arr", "salt")

# Join on salted key
result = skewed.join(small, "salted_key", "left").drop("salt", "salted_key")

# Step 3: AQE Skew Join (automatic, Spark 3.0+)
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.skewedPartitionFactor", "5")
# AQE splits skewed partitions and replicates the non-skewed side automatically
```

#### 2.2.5 Caching and Persistence

```python
from pyspark import StorageLevel

# When to cache:
# - DataFrame is used multiple times in the same job
# - Recomputation is expensive (many transformations upstream)

# Don't cache:
# - Data used only once
# - Extremely large data (cache thrashing → slower than recompute)
# - Data that fits in a single pass

# Cache levels
df.cache()                           # = MEMORY_AND_DISK_2 (default)
df.persist(StorageLevel.MEMORY_ONLY)  # fastest but OOM risk
df.persist(StorageLevel.MEMORY_AND_DISK)  # safe, spills to disk
df.persist(StorageLevel.DISK_ONLY)   # slowest but no OOM
df.persist(StorageLevel.MEMORY_AND_DISK_SER)  # serialized = smaller memory footprint

# CRITICAL: always unpersist when done
df.unpersist()

# Example: transformation fan-out (cache the base, compute each branch once)
base = spark.read.parquet("gs://bucket/events/") \
             .filter(F.col("event_date") == "2024-01-15") \
             .cache()  # used 3 times below

clicks = base.filter(F.col("event_type") == "click").groupBy("campaign_id").count()
impressions = base.filter(F.col("event_type") == "impression").groupBy("campaign_id").count()
conversions = base.filter(F.col("event_type") == "conversion").groupBy("campaign_id").count()

result = clicks.join(impressions, "campaign_id").join(conversions, "campaign_id")
result.write.parquet("gs://bucket/output/")

base.unpersist()  # release memory after use
```

#### 2.2.6 File Format and Compression

```python
# Parquet: columnar format — best for analytical queries
# Benefits: column pruning, compression, predicate pushdown, schema evolution
# Use for: all analytical data in GCS/HDFS

# ORC: similar to Parquet, used in Hive ecosystem
# Avro: row-based, good for streaming and schema registry
# CSV/JSON: avoid for large-scale processing (no columnar advantage, slow to parse)

# Writing optimized Parquet
df.write \
  .mode("overwrite") \
  .option("compression", "snappy")  \     # snappy: good balance of speed/compression
  .option("parquet.block.size", "134217728")  \  # 128MB row groups
  .partitionBy("event_date") \               # partition for pruning
  .parquet("gs://bucket/output/")

# Compression comparison:
# snappy: fast compress/decompress, decent ratio → good for hot data
# gzip:   slow compress, fast decompress, best ratio → good for cold/archived data
# lz4:    fastest, worst ratio → good for temp/intermediate data
# zstd:   best balance (Spark 3+) → increasingly preferred

# File size: target 128-512MB per Parquet file
# Too small (< 10MB): too many files → slow listing, excessive task overhead
# Too large (> 1GB): slow individual task processing

# Compact small files before heavy operations
df.repartition(optimal_partition_count).write.parquet(...)
```

---

### 2.3 Cost Optimization Strategies

#### BigQuery Cost Model
```
Cost = (bytes scanned) × ($6.25 per TB)  [on-demand pricing]
     + storage cost ($0.02/GB/month for active data)

Cost reduction levers:
1. Partition pruning → reduce bytes scanned by 100x
2. Column selection → SELECT 5 cols vs SELECT * can be 20x cheaper
3. Materialized views → pre-compute expensive aggregations
4. Clustering → reduce bytes scanned within partitions
5. Caching → repeated queries hit cache (free)
```

```sql
-- Monitoring BigQuery costs
SELECT
    project_id,
    user_email,
    DATE(creation_time) AS query_date,
    COUNT(*) AS query_count,
    SUM(total_bytes_processed) / POW(1024, 4) AS tb_processed,
    SUM(total_bytes_processed) / POW(1024, 4) * 6.25 AS estimated_cost_usd
FROM `region-us`.INFORMATION_SCHEMA.JOBS
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY 1, 2, 3
ORDER BY tb_processed DESC;
```

#### Spark/Dataproc Cost Model
```
Cost = (cluster uptime) × (machine type cost)
     = (VM hours) × ($0.04-0.20/VM hour depending on type)

Cost reduction levers:
1. Use preemptible/spot VMs for batch jobs (60-80% discount)
2. Right-size cluster: don't overprovision executor count
3. Tune job duration: faster jobs = shorter uptime = lower cost
4. Use Dataproc autoscaling: scale out during peak, scale in during idle
5. Use Dataproc serverless (Spark Serverless): pay per CU-second, no idle cost
```

---

## L3: Real-World Scenarios

### 3.1 Scenario: Slow Daily Report Query

**Problem**: The marketing team's 8 AM ROAS report takes 45 minutes. They want it in under 5 minutes.

**Investigation approach**:
```sql
-- Step 1: Check job execution stats
SELECT
    job_id,
    query,
    total_bytes_processed / POW(1024,3) AS gb_processed,
    total_slot_ms / 1000 AS slot_seconds,
    TIMESTAMP_DIFF(end_time, start_time, SECOND) AS duration_sec,
    total_bytes_processed / (total_slot_ms / 1000) AS bytes_per_slot_second
FROM `region-us`.INFORMATION_SCHEMA.JOBS
WHERE job_id = 'bq_job_xxx'

-- Step 2: Check if partition filter is applied
-- BigQuery UI shows "Will scan X.XX GB" before running
-- If it shows "All partitions" → partition filter missing

-- Step 3: Check if clustering is helping
-- EXPLAIN in BigQuery shows estimated rows scanned vs total
```

**Root cause and fix**:
```sql
-- BEFORE (slow, scans all data):
SELECT
    campaign_id,
    ROUND(SUM(revenue_usd) / SUM(spend_usd), 4) AS roas
FROM `project.mart.ad_clicks`   -- 10B rows, no partition filter!
JOIN `project.mart.conversions` USING (campaign_id, user_id)
GROUP BY 1;
-- Scans 2.5TB → 45 minutes, $15 per run

-- AFTER (fast, optimized):
-- Option A: Add partition filter (if report is for yesterday)
SELECT campaign_id, ROUND(SUM(revenue_usd) / SUM(spend_usd), 4) AS roas
FROM `project.mart.campaign_daily_performance`  -- pre-joined, aggregated table
WHERE report_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)  -- partition filter!
GROUP BY 1;
-- Scans 0.1GB → 10 seconds, $0.0006 per run

-- Option B: Use pre-aggregated mart (even better)
SELECT campaign_id, roas
FROM `project.mart.campaign_daily_performance`
WHERE report_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY);
-- No aggregation needed: reads 0.01GB → 2 seconds
```

---

### 3.2 Scenario: Spark Job OOM (Out of Memory) on Join

```python
# Problem: Spark job crashes with OOM during join of 500GB table with 20GB table

# Investigation
# 1. Check Spark UI: which stage fails?
# 2. Check executor memory: how much is allocated vs needed?
# 3. Check spill: is data spilling to disk before OOM?

# Root cause: 20GB table is too large to broadcast, SortMergeJoin creates
# shuffle partitions of 5GB each → doesn't fit in 4GB executor memory

# Fix 1: Increase shuffle partitions to reduce size per partition
spark.conf.set("spark.sql.shuffle.partitions", "2000")
# Each partition: 520GB / 2000 = 260MB → fits in executor memory

# Fix 2: Increase executor memory
# In Dataproc: choose larger machine type or increase spark.executor.memory

# Fix 3: If 20GB table can be reduced, filter it before join
small_filtered = large_table.filter(F.col("status") == "active")  # 20GB → 5GB
# 5GB might now fit in executor for broadcast

# Fix 4: Partition both tables on join key, join partition by partition
# Using partition join hints in Spark 3+
result = large_table.hint("PARTITIONED") \
                    .join(medium_table.hint("PARTITIONED"), "campaign_id")
```

---

## L4: Hands-On Optimization

### 4.1 Rewrite: Optimize This Slow BigQuery Query

```sql
-- ORIGINAL (slow):
SELECT
    u.user_id,
    u.email,
    SUM(t.amount) AS total_spend,
    COUNT(t.transaction_id) AS purchase_count
FROM users u
INNER JOIN transactions t
    ON u.user_id = t.user_id
WHERE EXTRACT(YEAR FROM t.transaction_date) = 2024
  AND LOWER(u.membership_tier) = 'gold'
  AND u.user_id IN (
      SELECT user_id FROM transactions
      WHERE amount > 1000
  )
GROUP BY u.user_id, u.email
ORDER BY total_spend DESC;

-- Problems:
-- 1. EXTRACT(YEAR FROM t.transaction_date) = 2024 → no partition pruning
-- 2. LOWER(u.membership_tier) = 'gold' → function on column, no index benefit
-- 3. Correlated subquery (IN) → runs for each row in outer query
-- 4. SELECT u.email but only GROUP BY u.user_id, u.email needed
-- 5. ORDER BY on full result → expensive sort

-- OPTIMIZED:
WITH high_value_users AS (
    -- Pre-compute the IN subquery as a CTE (computed once)
    SELECT DISTINCT user_id
    FROM transactions
    WHERE transaction_date >= '2024-01-01'     -- partition pruning
      AND transaction_date < '2025-01-01'
      AND amount > 1000
),

user_spend AS (
    SELECT
        t.user_id,
        SUM(t.amount)           AS total_spend,
        COUNT(t.transaction_id) AS purchase_count
    FROM transactions t
    WHERE t.transaction_date >= '2024-01-01'   -- partition pruning ✓
      AND t.transaction_date < '2025-01-01'
    GROUP BY t.user_id
)

SELECT
    u.user_id,
    u.email,
    us.total_spend,
    us.purchase_count
FROM users u
JOIN user_spend us ON u.user_id = us.user_id
JOIN high_value_users hvu ON u.user_id = hvu.user_id  -- semi-join
WHERE u.membership_tier = 'gold'   -- no LOWER() needed if data is normalized ✓
ORDER BY us.total_spend DESC
LIMIT 1000;   -- add LIMIT to avoid massive result transfer
```

---

### 4.2 Rewrite: Optimize This PySpark Job

```python
# ORIGINAL (slow, expensive):
def compute_daily_metrics(spark, date_str):
    # Problem 1: reading all data, no filter
    clicks = spark.read.parquet("gs://bucket/clicks/")
    
    # Problem 2: multiple separate groupBys = multiple shuffles
    click_counts = clicks.groupBy("campaign_id").count().alias("clicks")
    spend_totals = clicks.groupBy("campaign_id").agg(F.sum("cost_usd").alias("spend"))
    unique_users = clicks.groupBy("campaign_id").agg(
        F.countDistinct("user_id").alias("unique_users")
    )
    
    # Problem 3: multiple joins after multiple groupBys
    result = click_counts \
        .join(spend_totals, "campaign_id") \
        .join(unique_users, "campaign_id")
    
    # Problem 4: writing with coalesce(1) on large data
    result.coalesce(1).write.csv("gs://bucket/output/")

# OPTIMIZED:
def compute_daily_metrics_optimized(spark, date_str):
    # Fix 1: partition pruning on read
    clicks = spark.read.parquet("gs://bucket/clicks/") \
                  .filter(F.col("click_date") == date_str)  # push filter to read
    
    # Fix 2: single groupBy with all aggregations = one shuffle
    result = clicks.groupBy("campaign_id").agg(
        F.count("*").alias("clicks"),
        F.sum("cost_usd").alias("spend_usd"),
        F.countDistinct("user_id").alias("unique_users"),
        F.avg("cost_usd").alias("avg_cpc"),
        F.percentile_approx("cost_usd", 0.5).alias("median_cpc")
    )
    
    # Fix 3: Enrich with broadcast join (campaigns is small)
    campaigns = spark.read.parquet("gs://bucket/campaigns/")
    result = result.join(broadcast(campaigns), "campaign_id", "left")
    
    # Fix 4: Write as Parquet with appropriate partition count
    # Each output file should be 128MB-512MB
    output_rows = result.count()
    output_partitions = max(1, output_rows // 500000)  # ~500K rows per partition
    
    result.repartition(output_partitions) \
          .write \
          .mode("overwrite") \
          .parquet(f"gs://bucket/output/date={date_str}/")
```

---

## L5: Edge Cases & Pitfalls

### 5.1 The Over-Partitioning Trap

```sql
-- Problem: too many partitions → too many files → slow metastore queries, high overhead

-- BAD: partition by high-cardinality column
CREATE TABLE events PARTITION BY user_id;
-- If 10M users → 10M partitions → BigQuery metadata becomes bottleneck
-- File listing alone takes minutes

-- BAD: partition by timestamp (too granular)
CREATE TABLE events PARTITION BY TIMESTAMP_TRUNC(event_at, HOUR);
-- 24 partitions/day × 365 days = 8,760 partitions after 1 year
-- Still manageable, but hourly granularity usually adds no benefit over daily

-- GOOD: partition by date (most common, right granularity)
CREATE TABLE events PARTITION BY DATE(event_at);
-- ~365 partitions/year — BigQuery handles this efficiently

-- For high-cardinality filtering needs: use CLUSTERING instead
CREATE TABLE events
PARTITION BY DATE(event_at)
CLUSTER BY user_id, campaign_id;  -- cluster on high-cardinality columns
```

---

### 5.2 The Re-Partition Mistake in Spark

```python
# Mistake: repartitioning AFTER filtering when coalesce would suffice

# Context: 1000 partitions, filter removes 90% of rows
# After filter: 1000 tiny partitions (0.1MB each) — too many
filtered = df.filter(F.col("status") == "active")  # 90% removed

# BAD: repartition triggers full shuffle even for reduction
filtered.repartition(100)  # unnecessary shuffle

# GOOD: coalesce merges partitions on the same node (no shuffle)
filtered.coalesce(100)  # no network I/O, just merge locally

# RULE: use repartition when INCREASING partitions or need uniform distribution
# RULE: use coalesce when DECREASING partitions after reduction (filter, etc.)
```

---

### 5.3 Materialized Views — When They Help vs Hurt

```sql
-- BigQuery materialized views: pre-computed aggregations auto-refreshed
CREATE MATERIALIZED VIEW `project.mart.mv_daily_roas`
AS
SELECT
    report_date,
    campaign_id,
    SUM(spend_usd)      AS total_spend,
    SUM(revenue_usd)    AS total_revenue,
    SAFE_DIVIDE(SUM(revenue_usd), SUM(spend_usd)) AS roas
FROM `project.staging.ad_clicks`
GROUP BY report_date, campaign_id;

-- Benefits:
-- 1. Queries that scan the base table CAN use the MV automatically (smart tuning)
-- 2. Incremental refresh (only refreshes changed partitions)
-- 3. Dramatically reduces query cost for repeated aggregations

-- When NOT to use:
-- 1. Table changes very frequently (constant refreshes negate benefit)
-- 2. Complex transformations that MVs can't express (BigQuery MV has constraints)
-- 3. Very large base tables with expensive refresh cost

-- Check if BigQuery is using your MV (look for "materialized_view" in EXPLAIN output)
```

---

### 5.4 The COUNT(DISTINCT) Scalability Problem

```sql
-- COUNT(DISTINCT) in BigQuery triggers a full global aggregation (expensive for high-card)

-- SLOW: exact COUNT(DISTINCT) on 10B rows
SELECT COUNT(DISTINCT user_id) FROM events;
-- Requires passing all user_ids through a single aggregation node

-- FAST: approximate with HyperLogLog (1-2% error, 10-100x faster)
SELECT APPROX_COUNT_DISTINCT(user_id) FROM events;

-- For Spark:
df.select(F.approx_count_distinct("user_id", rsd=0.05))  # 5% error, ~10x faster

-- When exact COUNT(DISTINCT) is truly needed:
-- Pre-aggregate to the unique key level, then COUNT(*)
WITH distinct_users AS (
    SELECT DISTINCT user_id FROM events
    WHERE event_date = '2024-01-15'
)
SELECT COUNT(*) FROM distinct_users;
-- BigQuery can parallelize this better than a single COUNT(DISTINCT)
```

---

## L6: Interview Questions — Easy to Very Hard

### EASY

---

**Q1: What is partitioning in BigQuery and why does it matter for performance?**

**Answer**: Partitioning divides a BigQuery table into segments based on a column value (usually a date). When you query with a filter on the partition column, BigQuery reads only the relevant partitions instead of the entire table. For a table with 1 year of daily data (365 partitions), a filter for one specific date reads 1/365 of the data — reducing query cost and time by up to 365x. Without partitioning, every query scans the full table regardless of date filters.

---

**Q2: What is the difference between partitioning and clustering in BigQuery?**

**Answer**: Partitioning divides data into physically separate storage segments — BigQuery can skip entire partitions when the partition column is filtered. Clustering sorts data within each partition by one or more columns — BigQuery can skip blocks within a partition when the cluster columns are filtered.

They work at different granularities:
- Partition: coarse pruning (skip entire partitions → potential 1000x reduction)
- Clustering: fine pruning within partitions (skip blocks → additional 2-10x reduction)

Use both together: partition by date (coarse), cluster by campaign_id and channel (fine). A query filtering on both columns benefits from both layers of pruning.

---

### MEDIUM

---

**Q3: Your BigQuery query runs for 10 minutes and scans 5TB. The business says it should run in under 1 minute. Walk me through how you'd optimize it.**

**Answer**:

**Step 1: Look at the query**
- Is there a partition column filter? If not, add one immediately. Filter on `event_date` or whichever column the table is partitioned by.
- Is the partition column being wrapped in a function (`EXTRACT`, `DATE_TRUNC`, `CAST`)? Functions prevent pruning — replace with direct comparison or range filter.
- Is there a `SELECT *` on a wide table? Replace with explicit column list.

**Step 2: Check the join pattern**
- Are small lookup tables being joined without broadcasting? Joining a 5TB table with a 50MB lookup table without broadcasting causes both to shuffle. Enable broadcast by increasing `autoBroadcastJoinThreshold` or use the `BROADCAST` hint.
- Is the join producing fan-out? Check if the join key is unique on both sides — non-unique key causes row multiplication.

**Step 3: Check aggregation**
- Is there a `COUNT(DISTINCT ...)` on a high-cardinality column? Replace with `APPROX_COUNT_DISTINCT` if exactness isn't critical.
- Can the aggregation be done on a pre-aggregated table instead of raw events?

**Step 4: Structural fix**
- Create a pre-aggregated mart table with partitioning and clustering configured appropriately
- Change the report query to read from the mart instead of raw events

**Expected result**: Partition pruning alone typically reduces 5TB → 50GB (100x). Column selection further reduces it. Combined with a pre-aggregated mart: 5TB/10min → 100MB/15sec.

---

**Q4: What is data skew in Spark and how do you fix it?**

**Answer**: Data skew occurs when the data distribution across partitions is uneven — one partition (and thus one task) has significantly more data than others. In a join or GROUP BY, if one key value appears in 80% of rows, that key's partition takes 10x longer than others. The entire stage waits for the "straggler" partition to finish, making the whole job slow.

**Detection**: Spark UI → Stages → Task Duration distribution. If one task took 45 minutes while others took 2 minutes, that's skew. Or check programmatically: `df.groupBy("join_key").count().orderBy(F.desc("count"))`.

**Fixes**:
1. **Salting**: For skewed joins, add a random salt (0 to N) to the skewed key on the large side, explode the small side to match. The skewed key's data is now distributed across N buckets.
2. **AQE Skew Join** (Spark 3+): `spark.sql.adaptive.skewJoin.enabled=true` — automatically splits skewed partitions.
3. **Broadcast join**: If the non-skewed side is small enough, broadcast it to avoid shuffle entirely.
4. **Isolate skewed key**: Process the skewed key separately (its own query), process all other keys together, then UNION ALL.

---

### HARD

---

**Q5: A Spark job processes 500GB of data and runs for 3 hours. The executor logs show "GC overhead limit exceeded" errors. What do you do?**

**What they're testing**: Memory management, GC tuning, deep Spark internals.

**Answer**:

"GC overhead limit exceeded" means the JVM is spending >98% of time doing garbage collection and recovering <2% of memory — effectively stuck in an infinite GC loop. This means executors are running out of heap memory.

**Root cause investigation**:
1. Check the Spark UI → Executor tab: what is "GC Time" as % of "Task Time"? >20% is bad.
2. Check memory usage: storage memory + execution memory > total executor memory?
3. Are there large objects being created in map operations (e.g., `collect_list` with millions of elements)?
4. Check for Python UDFs — Python UDFs deserialize data to Python heap, bypassing JVM managed memory.

**Fixes in priority order**:

1. **Increase executor memory**:
```python
spark.conf.set("spark.executor.memory", "8g")       # heap memory
spark.conf.set("spark.executor.memoryOverhead", "2g")  # off-heap for native/Python
```

2. **Tune memory fractions**:
```python
# storage (caching) + execution (shuffle/aggregation) fractions
spark.conf.set("spark.memory.fraction", "0.8")        # fraction for storage+execution
spark.conf.set("spark.memory.storageFraction", "0.3") # fraction for storage within above
# execution memory = 0.8 * (1 - 0.3) = 56% of heap
```

3. **Reduce partition size** (less data per task = less memory pressure):
```python
spark.conf.set("spark.sql.shuffle.partitions", "2000")
# Smaller partitions → less data held in memory per task
```

4. **Avoid UDFs**: Replace Python UDFs with native Spark SQL functions whenever possible. Python UDFs serialize data to Python → JVM GC can't manage Python objects.

5. **Tune GC settings**:
```python
spark.conf.set("spark.executor.extraJavaOptions",
    "-XX:+UseG1GC -XX:InitiatingHeapOccupancyPercent=35")
# G1GC handles fragmented heap better than default CMS
```

6. **Check for `collect_list` or `array_agg` on unbounded data**: These can create enormous arrays in memory per key. Add a `LIMIT` or use approximate methods.

---

**Q6: Design a cost optimization strategy for a BigQuery environment where the monthly bill is $50,000 and the engineering team wants to reduce it to $15,000 within 60 days. What do you do?**

**What they're testing**: Practical cost optimization, prioritization, organizational awareness.

**Answer**:

**Phase 1: Measure (Week 1)** — Can't cut what you can't see.
```sql
-- Who is spending most?
SELECT user_email,
       SUM(total_bytes_processed) / POW(1024,4) AS tb_processed,
       SUM(total_bytes_processed) / POW(1024,4) * 6.25 AS cost_usd
FROM INFORMATION_SCHEMA.JOBS
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY 1 ORDER BY cost_usd DESC;

-- Which queries are most expensive?
SELECT query, total_bytes_processed / POW(1024,4) * 6.25 AS cost_per_run,
       creation_time
FROM INFORMATION_SCHEMA.JOBS
ORDER BY cost_per_run DESC LIMIT 20;
```

**Phase 2: Quick Wins (Weeks 2-3)** — Low effort, high impact.

1. **Add partition filters to top-10 most expensive queries**: Often a single `WHERE event_date = ...` reduces a query from 1TB to 1GB. This alone can cut 50% of costs.
2. **Remove `SELECT *` from recurring queries**: Columnar databases charge by bytes scanned. Selecting 5 columns from a 100-column table cuts cost by 95% for that query.
3. **Enable BigQuery cost controls**: Set per-user daily byte quotas in BigQuery IAM.
4. **Schedule dashboard queries**: BI tool polling every 5 minutes on raw tables = hundreds of expensive queries/day. Cache results in BigQuery BI Engine or materialize as a view.

**Phase 3: Structural Changes (Weeks 4-8)** — Architectural improvements.

1. **Add partitioning and clustering to top-10 most queried tables**: Ensures all future queries benefit automatically.
2. **Build pre-aggregated mart tables**: Replace raw event queries with daily/weekly aggregated tables. A campaign performance query on a mart table (1MB) vs raw events (1TB) = 1000x cost reduction.
3. **Implement materialized views** for repeated aggregations.
4. **Migrate repeated BI queries to BigQuery BI Engine** (in-memory cache for dashboards).
5. **Use Flex Slots or flat-rate pricing** if query volume is high and predictable.

**Expected outcome**: Phase 2 alone (partition filters + column selection) typically reduces costs by 40-60%. With mart tables and partitioning, 70% reduction is achievable = $50K → $15K.

---

### VERY HARD

---

**Q7: You're managing a Dataproc cluster running daily Spark jobs. The jobs take 4 hours. The business has a hard requirement: jobs must complete in 1 hour. The jobs process 2TB of data, join 5 tables, and compute 50 metrics. Design your optimization plan.**

**What they're testing**: Holistic Spark optimization, architectural thinking, prioritization.

**Answer**:

**Step 1: Profile before optimizing** (30 min)
- Run the current job, capture Spark UI screenshots
- Identify: which stages take most time? Are there shuffle bottlenecks? Skew? Spill?
- Check executor utilization: are executors idle between stages? (indicates stragglers)

**Step 2: Data layer optimizations** (highest impact)

1. **Convert CSV/JSON to Parquet**: If source data is CSV, conversion alone can give 5-10x speedup (columnar reads + compression).

2. **Add partition pruning to source reads**:
```python
# Instead of reading all 2TB
df = spark.read.parquet("gs://bucket/events/")
# Filter at read time (partition pruning)
df = spark.read.parquet("gs://bucket/events/") \
           .filter(F.col("event_date") == execution_date)
# If only 1/30 of data is needed: 2TB → 67GB
```

3. **Pre-sort and pre-partition source data by join key**: If the 5-table join always joins on `campaign_id`, pre-sort each source table by `campaign_id`. Then re-runs use `bucketed reads` and avoid shuffle.

**Step 3: Shuffle minimization** (second highest impact)

1. Identify all wide transformations (groupBy, join, distinct) — each is a stage boundary
2. Merge multiple groupBys on same key into one
3. Broadcast all small lookup tables (< 200MB)
4. Enable AQE: adaptive partition coalescing + skew join handling

**Step 4: Parallelism tuning**

1. Right-size shuffle partitions: target 256MB per post-shuffle partition
   - 2TB input, 50% reduction from filters = ~1TB
   - 1TB / 256MB = ~4000 shuffle partitions
   - Set: `spark.sql.shuffle.partitions = 4000`

2. Right-size cluster: 4000 partitions, 4 cores/executor, 200 executors = comfortable
   - Dataproc: 50 workers × n1-standard-4 (4 cores each) = 200 cores = 200 parallel tasks

**Step 5: Caching the join spine**

If 50 metrics all read the same joined dataset, cache it:
```python
joined_base = (
    events.join(broadcast(campaigns), "campaign_id")
          .join(broadcast(channels), "channel_id")
          .join(broadcast(regions), "region_id")
          .join(conversions, ["campaign_id", "user_id"])
          .cache()
)
# Compute all 50 metrics from this cached base
metric1 = joined_base.groupBy("campaign_id").agg(...)
metric2 = joined_base.groupBy("channel").agg(...)
# ...
joined_base.unpersist()
```

**Expected impact**:
- Parquet conversion: 4hr → 2hr
- Partition pruning + filter pushdown: 2hr → 45min  
- Shuffle optimization + AQE: 45min → 25min
- Broadcast joins for small tables: 25min → ~15min
- Caching the join spine: 15min → ~8min

**Total**: 4 hours → ~8-10 minutes. Well within the 1-hour requirement.

**Bonus**: Set up Dataproc autoscaling so you only pay for peak compute when needed, not full cluster all day.

---

## Summary: Performance Optimization — Senior Mastery Checklist

| Skill | What Senior Looks Like |
|-------|------------------------|
| BigQuery partitioning | Knows pruning mechanics; catches function-on-partition-column bugs |
| BigQuery clustering | Uses both partition + cluster; explains column order matters |
| Column selection | Never uses SELECT * in production; understands columnar cost model |
| Spark shuffle | Identifies wide vs narrow; minimizes shuffles by design |
| Broadcast join | Knows threshold; knows when to use; understands OOM risk |
| Data skew | Detects in Spark UI; fixes with salting or AQE |
| Partition count | Targets 128-256MB/partition; uses AQE for auto-tuning |
| File format | Parquet for analytical; right compression per use case |
| Cost monitoring | Can query INFORMATION_SCHEMA to find expensive queries |
| Holistic thinking | Profiles first, prioritizes highest-impact changes, measures after |
