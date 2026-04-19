# Topic 6: BigQuery Advanced + AlloyDB + Spanner
## Complete Interview Textbook — Costco Sr. Data Engineer

---

## TABLE OF CONTENTS

1. [BigQuery Architecture — Deep Dive](#1-bigquery-architecture)
2. [BigQuery Storage — Tables, Partitioning, Clustering](#2-bigquery-storage)
3. [BigQuery Optimization — Query Performance](#3-bigquery-optimization)
4. [BigQuery Advanced SQL Features](#4-bigquery-advanced-sql)
5. [BigQuery Materialized Views & Scheduled Queries](#5-materialized-views)
6. [BigQuery Data Ingestion Patterns](#6-data-ingestion)
7. [BigQuery Cost Management](#7-cost-management)
8. [BigQuery ML (BQML)](#8-bigquery-ml)
9. [BigQuery Omni & Cross-Cloud Analytics](#9-bigquery-omni)
10. [AlloyDB — Architecture & Use Cases](#10-alloydb)
11. [Cloud Spanner — Architecture & Use Cases](#11-cloud-spanner)
12. [Choosing the Right Database: Decision Framework](#12-decision-framework)
13. [Interview Q&A Bank](#13-interview-qa)

---

## 1. BigQuery Architecture — Deep Dive

### Dremel: The Query Engine

BigQuery is built on **Dremel**, Google's columnar query engine. Understanding Dremel explains all of BigQuery's strengths and quirks.

```
┌──────────────────────────────────────────────────────────────┐
│                    QUERY ENGINE (Dremel)                      │
│                                                              │
│  Root Server (query coordinator)                             │
│       │                                                      │
│  Mixing Servers (query parallelization)                      │
│       │         │         │         │                        │
│  Leaf Servers (actual scan + compute workers)                │
│       │         │         │         │                        │
│  Colossus (distributed columnar storage)                     │
└──────────────────────────────────────────────────────────────┘
```

**Key architectural properties:**
1. **Separation of storage and compute**: Query compute (Dremel slots) scales independently from storage (Colossus). You pay for storage at rest and for compute when querying.
2. **Columnar storage**: Data stored column by column, not row by row. Querying 3 columns from a 1000-column table only reads those 3 columns. This is why `SELECT *` is so expensive.
3. **Columnar compression**: Similar values in a column compress extremely well — especially low-cardinality columns.
4. **Serverless**: No cluster to manage. Dremel dynamically allocates slots for your query.
5. **Slot-based execution**: A slot is a unit of computational capacity. On-demand: fair-share auto-allocation. Reservations: dedicated slots for enterprise.

### Storage: Capacitor Format

BigQuery uses the **Capacitor** columnar format (successor to ColumnIO). Key properties:
- Encoding: dictionary encoding, run-length encoding, bit packing
- Compression: LZ4, Snappy, Zstd
- Nested/repeated fields stored natively (Dremel nested data model)
- Micro-partitioning within a column for predicate pushdown

### The Query Execution Pipeline

```
1. SQL parsing and validation (syntax check, column resolution)
2. Logical plan construction (algebraic query tree)
3. Optimization:
   a. Predicate pushdown (filter as early as possible)
   b. Column pruning (don't read unused columns)
   c. Partition pruning (skip entire partitions via metadata)
   d. Join reordering (smallest table as probe side)
   e. Aggregation pushdown (pre-aggregate before join)
4. Physical plan → distributed execution plan
5. Slot allocation from slot pool
6. Parallel execution across leaf nodes
7. Results shuffled to mixer → aggregated → returned to root
8. Results cached (24 hours for identical queries on unchanged data)
```

---

## 2. BigQuery Storage — Tables, Partitioning, Clustering

### Table Types

```sql
-- 1. Standard (Native BigQuery) table
CREATE TABLE dataset.my_table (
    id INT64,
    name STRING,
    created_at TIMESTAMP
);

-- 2. External table (data stays in GCS/Cloud Storage, queried via BQ)
CREATE EXTERNAL TABLE dataset.external_events
OPTIONS (
    format = 'PARQUET',
    uris = ['gs://my-bucket/events/*.parquet']
);

-- 3. Materialized View (auto-maintained derived table)
CREATE MATERIALIZED VIEW dataset.mv_daily_metrics AS
SELECT DATE(event_time) AS dt, COUNT(*) AS events
FROM dataset.raw_events
GROUP BY 1;

-- 4. Authorized View (shared access without raw data access)
CREATE VIEW dataset.safe_customer_view AS
SELECT customer_id, segment, lifetime_value  -- no PII columns
FROM dataset.customers;

-- 5. Wildcard table (query multiple tables matching a pattern)
SELECT * FROM `project.dataset.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131';
```

### Partitioning — Critical for Cost & Performance

**Partition pruning** is the single biggest BigQuery optimization. A partitioned table only scans the partitions that satisfy the filter predicate.

```sql
-- Date/Timestamp partitioned (most common)
CREATE TABLE analytics.events (
    event_id      STRING,
    user_id       STRING,
    event_type    STRING,
    event_time    TIMESTAMP,
    revenue       FLOAT64
)
PARTITION BY DATE(event_time)
OPTIONS (
    partition_expiration_days = 730,  -- Auto-delete after 2 years
    require_partition_filter = TRUE   -- Reject queries without partition filter
);

-- Integer range partitioning
CREATE TABLE analytics.users_by_id (
    user_id   INT64,
    name      STRING,
    region    STRING
)
PARTITION BY RANGE_BUCKET(user_id, GENERATE_ARRAY(0, 10000000, 100000));
-- Creates partitions: [0,100000), [100000,200000), ...

-- Ingestion time partitioning (no explicit date column needed)
CREATE TABLE analytics.streaming_events (
    message   STRING,
    payload   JSON
)
PARTITION BY _PARTITIONDATE;
-- Query with: WHERE _PARTITIONDATE = '2024-01-15'
```

**Partition pruning rules:**
```sql
-- ✅ Partition filter applied — only reads matching partitions
SELECT * FROM analytics.events WHERE DATE(event_time) = '2024-01-15';
SELECT * FROM analytics.events WHERE event_time >= '2024-01-01';

-- ❌ No partition pruning — full table scan!
SELECT * FROM analytics.events WHERE EXTRACT(YEAR FROM event_time) = 2024;
SELECT * FROM analytics.events WHERE DATE_DIFF(CURRENT_DATE(), DATE(event_time), DAY) < 30;

-- ✅ Correct equivalent of the above
SELECT * FROM analytics.events 
WHERE event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY);
```

### Clustering — Column-Level Optimization

Clustering physically co-locates data with similar values for the specified columns within each partition. Reduces data scanned for filters and joins.

```sql
-- Clustered by up to 4 columns
CREATE TABLE analytics.ad_events (
    event_id      STRING,
    event_date    DATE,
    channel       STRING,
    campaign_id   STRING,
    user_id       STRING,
    revenue       FLOAT64
)
PARTITION BY event_date
CLUSTER BY channel, campaign_id, user_id;
-- Best for: WHERE channel = 'paid_search' AND campaign_id = 'camp_123'
-- Clustering order matters: filter on leftmost columns for best pruning

-- Check if query uses clustering (look at "bytes processed" estimate)
-- Clustered query:
SELECT SUM(revenue) FROM analytics.ad_events
WHERE event_date = '2024-01-15'   -- partition filter
  AND channel = 'paid_search'     -- cluster filter
  AND campaign_id = 'camp_123';   -- cluster filter
```

**Partitioning vs Clustering Decision:**
- Use **partitioning** when: you always filter on a date range; data expires regularly; query costs need predictable reduction.
- Use **clustering** when: you filter on specific column values (non-date); cardinality too high for partitioning; multiple filter columns needed.
- Use **both** (most production tables): partition by date + cluster by category/ID columns.

---

## 3. BigQuery Optimization — Query Performance

### The 7 Core Optimization Principles

#### Principle 1: Partition Pruning (Biggest Impact)
```sql
-- Always filter on partition column explicitly
WHERE DATE(event_timestamp) BETWEEN '2024-01-01' AND '2024-01-31'
-- Not:
WHERE EXTRACT(YEAR FROM event_timestamp) = 2024  -- No pruning!
```

#### Principle 2: Column Selection (Columnar Storage Benefit)
```sql
-- Only select columns you need
SELECT campaign_id, SUM(revenue) FROM events GROUP BY 1
-- Not:
SELECT * FROM events  -- Reads all columns! 100x more bytes in wide tables
```

#### Principle 3: Filter Early / Push Predicates Into CTEs
```sql
-- Good: filter before joining
WITH recent_events AS (
    SELECT user_id, campaign_id, revenue
    FROM raw.events
    WHERE DATE(event_timestamp) = CURRENT_DATE() - 1  -- Filter here
      AND event_type = 'purchase'
)
SELECT c.segment, SUM(e.revenue)
FROM recent_events e
JOIN curated.customers c ON e.user_id = c.customer_id
GROUP BY 1;
```

#### Principle 4: Denormalize for Query Performance
```sql
-- BigQuery is NOT normalized like OLTP — denormalize for performance
-- Instead of 3-table join per query, create denormalized table:
CREATE TABLE analytics.enriched_events AS
SELECT
    e.*,
    c.segment,
    c.membership_type,
    p.campaign_name,
    p.channel
FROM events e
LEFT JOIN customers c ON e.user_id = c.customer_id
LEFT JOIN campaigns p ON e.campaign_id = p.campaign_id;
```

#### Principle 5: Approximate Functions
```sql
-- Exact count distinct: reads all data, uses sort
SELECT COUNT(DISTINCT user_id) FROM events;  -- 10 seconds, expensive

-- Approximate: HyperLogLog, returns result within 1% accuracy
SELECT APPROX_COUNT_DISTINCT(user_id) FROM events;  -- 1 second, cheap

-- Approximate quantiles
SELECT APPROX_QUANTILES(revenue, 100)[OFFSET(50)] AS median_revenue FROM events;

-- Approximate top N
SELECT APPROX_TOP_COUNT(event_type, 5) FROM events;
```

#### Principle 6: Use TEMP Tables for Multi-Use Intermediates
```sql
-- If a CTE is referenced 3+ times, materialize it
CREATE TEMP TABLE daily_sessions AS
SELECT user_id, session_id, MIN(ts) AS start_time, MAX(ts) AS end_time
FROM events WHERE DATE(ts) = '2024-01-15'
GROUP BY user_id, session_id;

-- Now reuse multiple times without recomputation
SELECT * FROM daily_sessions WHERE user_id IN (...);
SELECT COUNT(*) FROM daily_sessions;
```

#### Principle 7: Avoid Data Skew in GROUP BY / JOINS
```sql
-- Check for skew first
SELECT campaign_id, COUNT(*) AS cnt
FROM events
WHERE event_date = '2024-01-15'
GROUP BY campaign_id
ORDER BY cnt DESC
LIMIT 10;

-- If one campaign has 90% of rows, it skews aggregation
-- Solution: pre-filter or use approximate functions for hot keys
```

### Reading the Query Execution Plan

```sql
-- Run EXPLAIN (BigQuery calls it "Query Plan Explanation" in Console)
-- Or use bq CLI:
-- bq query --format prettyjson 'SELECT ...' | jq '.statistics.query.queryPlan'

-- Key things to look in execution plan:
-- 1. Stage output records (look for stages producing 10x more rows than input = fan-out from bad join)
-- 2. Shuffle size (large shuffles = expensive, try to reduce with pre-aggregation)
-- 3. Slot milliseconds (total compute consumed)
-- 4. Read bytes (should be much less than table size with partition pruning)
```

### Common Performance Anti-Patterns

```sql
-- ANTI-PATTERN 1: Self-join for median (use PERCENTILE_CONT instead)
-- Bad:
SELECT a.revenue
FROM events a JOIN events b ON ...
WHERE ...
-- Good:
SELECT PERCENTILE_CONT(revenue, 0.5) OVER () AS median FROM events;

-- ANTI-PATTERN 2: Row-by-row processing with correlated subqueries
-- Bad:
SELECT *, (SELECT COUNT(*) FROM orders WHERE customer_id = c.id) AS order_count
FROM customers c;
-- Good:
SELECT c.*, COALESCE(o.order_count, 0)
FROM customers c
LEFT JOIN (SELECT customer_id, COUNT(*) AS order_count FROM orders GROUP BY 1) o
ON c.id = o.customer_id;

-- ANTI-PATTERN 3: DISTINCT to fix wrong join
-- Bad:
SELECT DISTINCT c.id, SUM(o.revenue) ...  -- DISTINCT after SUM is wrong
-- Fix the join cardinality problem at source

-- ANTI-PATTERN 4: Wildcard at start of LIKE
SELECT * FROM products WHERE name LIKE '%organic%';  -- Full scan
-- Better: use SEARCH function (if data supports it) or full-text search alternative

-- ANTI-PATTERN 5: Unnecessary ORDER BY in subquery/CTE
-- BigQuery doesn't guarantee order in intermediate results anyway
-- Only ORDER BY at final SELECT level
```

---

## 4. BigQuery Advanced SQL Features

### QUALIFY — Window Function Filter (BigQuery Extension)

```sql
-- Without QUALIFY (verbose):
WITH ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC) AS rn
    FROM customers
)
SELECT * EXCEPT(rn) FROM ranked WHERE rn = 1;

-- With QUALIFY (elegant):
SELECT * FROM customers
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC) = 1;

-- More QUALIFY examples:
-- Get events with above-average revenue per campaign
SELECT * FROM ad_events
QUALIFY revenue > AVG(revenue) OVER (PARTITION BY campaign_id);

-- Get top 3 products per category
SELECT * FROM products
QUALIFY RANK() OVER (PARTITION BY category ORDER BY sales DESC) <= 3;
```

### UNNEST — Working with Arrays

```sql
-- UNNEST: expand array into rows
SELECT order_id, item
FROM orders, UNNEST(line_items) AS item;

-- WITH OFFSET: include array position
SELECT order_id, pos, item
FROM orders, UNNEST(line_items) WITH OFFSET AS pos;

-- Filter on array element
SELECT DISTINCT order_id
FROM orders, UNNEST(tags) AS tag
WHERE tag = 'premium';

-- Aggregate after UNNEST
SELECT
    order_id,
    SUM(item.qty * item.price) AS order_total
FROM orders, UNNEST(line_items) AS item
GROUP BY order_id;

-- ARRAY_AGG: build arrays from rows
SELECT
    customer_id,
    ARRAY_AGG(STRUCT(product_id, qty, price) ORDER BY purchase_date) AS purchases
FROM transactions
GROUP BY customer_id;

-- ARRAY functions
SELECT
    ARRAY_LENGTH(tags) AS num_tags,
    tags[OFFSET(0)] AS first_tag,
    tags[SAFE_OFFSET(10)] AS tenth_tag_or_null
FROM posts;
```

### STRUCT — Nested Records

```sql
-- Create struct inline
SELECT
    customer_id,
    STRUCT(
        first_name AS given_name,
        last_name AS family_name,
        CONCAT(first_name, ' ', last_name) AS full_name
    ) AS name_record
FROM customers;

-- Access struct fields
SELECT name_record.full_name FROM customers_with_struct;

-- STRUCT in aggregation
SELECT
    customer_id,
    ARRAY_AGG(STRUCT(order_id, amount, order_date)) AS orders
FROM order_data
GROUP BY customer_id;
```

### JSON Functions (BigQuery)

```sql
-- Extract scalar values from JSON string
SELECT
    JSON_VALUE(properties, '$.user_id') AS user_id,
    JSON_VALUE(properties, '$.campaign.id') AS campaign_id,
    JSON_VALUE(properties, '$.page.url') AS page_url,
    CAST(JSON_VALUE(properties, '$.revenue') AS FLOAT64) AS revenue;

-- Extract JSON object (returns JSON string, not scalar)
SELECT JSON_QUERY(properties, '$.campaign') AS campaign_json;

-- Extract array
SELECT value FROM events, UNNEST(JSON_QUERY_ARRAY(properties, '$.tags')) AS value;

-- Check if key exists
SELECT JSON_VALUE(props, '$.key') IS NOT NULL AS has_key FROM events;

-- Build JSON from columns
SELECT TO_JSON(STRUCT(id, name, revenue)) AS json_record FROM table;

-- Parse JSON with explicit schema (LAX_JSON approach)
SELECT JSON_VALUE_ARRAY(props, '$.product_ids') AS product_id_array FROM events;
```

### GENERATE Functions

```sql
-- Generate date array (date spine)
SELECT date
FROM UNNEST(GENERATE_DATE_ARRAY('2024-01-01', '2024-12-31', INTERVAL 1 DAY)) AS date;

-- Generate timestamp array (hourly)
SELECT ts
FROM UNNEST(GENERATE_TIMESTAMP_ARRAY(
    '2024-01-15 00:00:00 UTC',
    '2024-01-15 23:00:00 UTC',
    INTERVAL 1 HOUR
)) AS ts;

-- Generate integer array
SELECT n
FROM UNNEST(GENERATE_ARRAY(1, 100)) AS n;

-- Fill missing days in time series (date spine pattern)
WITH date_spine AS (
    SELECT date FROM UNNEST(
        GENERATE_DATE_ARRAY(
            DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY),
            CURRENT_DATE() - 1,
            INTERVAL 1 DAY
        )
    ) AS date
)
SELECT
    ds.date,
    COALESCE(d.revenue, 0) AS revenue,
    COALESCE(d.orders, 0) AS orders
FROM date_spine ds
LEFT JOIN daily_metrics d ON ds.date = d.report_date
ORDER BY ds.date;
```

### INFORMATION_SCHEMA — Metadata Queries

```sql
-- Table sizes and row counts
SELECT
    table_name,
    row_count,
    size_bytes / POW(1024, 3) AS size_gb
FROM `project.dataset.INFORMATION_SCHEMA.TABLE_STORAGE`
ORDER BY size_bytes DESC;

-- Query history (last 7 days, ordered by bytes processed)
SELECT
    job_id,
    user_email,
    total_bytes_processed / POW(1024, 3) AS gb_processed,
    total_slot_ms / 1000 AS slot_seconds,
    cache_hit,
    TIMESTAMP_DIFF(end_time, start_time, SECOND) AS duration_sec,
    query
FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE DATE(creation_time) >= CURRENT_DATE() - 7
  AND state = 'DONE'
  AND error_result IS NULL
ORDER BY total_bytes_processed DESC
LIMIT 100;

-- Most expensive queries
SELECT
    SUBSTR(query, 1, 100) AS query_snippet,
    COUNT(*) AS executions,
    AVG(total_bytes_processed) / POW(1024, 3) AS avg_gb,
    SUM(total_bytes_processed) / POW(1024, 3) AS total_gb
FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE DATE(creation_time) >= CURRENT_DATE() - 30
  AND statement_type = 'SELECT'
GROUP BY query_snippet
ORDER BY total_gb DESC;

-- Partition metadata
SELECT
    partition_id,
    total_rows,
    total_logical_bytes / POW(1024, 2) AS mb
FROM `project.dataset.INFORMATION_SCHEMA.PARTITIONS`
WHERE table_name = 'my_table'
ORDER BY partition_id DESC
LIMIT 30;
```

---

## 5. Materialized Views & Scheduled Queries

### Materialized Views

Materialized views automatically maintain pre-computed results. BigQuery incrementally updates them as base data changes.

```sql
-- Create materialized view
CREATE MATERIALIZED VIEW analytics.mv_campaign_daily_metrics
PARTITION BY report_date
CLUSTER BY channel
OPTIONS (
    enable_refresh = TRUE,
    refresh_interval_minutes = 60  -- Auto-refresh every hour
)
AS
SELECT
    DATE(event_timestamp) AS report_date,
    channel,
    campaign_id,
    COUNT(*) AS total_events,
    COUNT(DISTINCT user_id) AS unique_users,
    COUNT(CASE WHEN event_type = 'purchase' THEN 1 END) AS purchases,
    SUM(CASE WHEN event_type = 'purchase' THEN revenue END) AS revenue,
    SUM(spend) AS spend
FROM analytics.ad_events
GROUP BY 1, 2, 3;

-- BigQuery query optimizer automatically uses materialized view
-- when query matches the MV's aggregation pattern
SELECT channel, SUM(revenue) FROM analytics.ad_events
WHERE DATE(event_timestamp) = '2024-01-15'
GROUP BY channel;
-- ^ This query will silently use mv_campaign_daily_metrics
```

**Materialized View Limitations:**
- Cannot use window functions, non-deterministic functions, JOINs (as of 2024)
- Must be an aggregate query (GROUP BY required)
- Only appends to base table trigger incremental refresh
- DML on base table triggers full refresh

### Scheduled Queries

```sql
-- In BigQuery Console UI or via API:
-- Schedule a query to run daily and INSERT results
INSERT INTO reporting.daily_snapshot
SELECT
    CURRENT_DATE() AS snapshot_date,
    COUNT(*) AS total_events,
    SUM(revenue) AS total_revenue
FROM analytics.ad_events
WHERE DATE(event_timestamp) = CURRENT_DATE() - 1;
```

---

## 6. Data Ingestion Patterns

### Batch Load

```python
from google.cloud import bigquery

client = bigquery.Client()

# Load from GCS
job_config = bigquery.LoadJobConfig(
    source_format=bigquery.SourceFormat.PARQUET,
    write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    time_partitioning=bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="event_date"
    ),
    clustering_fields=["channel", "campaign_id"],
    schema_update_options=[
        bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION  # Schema evolution
    ]
)
load_job = client.load_table_from_uri(
    "gs://bucket/events/dt=2024-01-15/*.parquet",
    "project.dataset.events",
    job_config=job_config
)
load_job.result()  # Wait for completion
print(f"Loaded {load_job.output_rows} rows")
```

### Streaming Insert (for real-time)

```python
# BigQuery Streaming Insert — for near real-time (<2 min latency)
# Limitations: 10,000 rows/second per table; cannot be queried immediately;
# de-duplication window 1 minute (not guaranteed)

errors = client.insert_rows_json(
    "project.dataset.streaming_events",
    [
        {"event_id": "e1", "user_id": "u1", "event_type": "click"},
        {"event_id": "e2", "user_id": "u2", "event_type": "purchase"}
    ],
    row_ids=["e1", "e2"]  # For deduplication
)
if errors:
    print(f"Errors: {errors}")

# Better for high-throughput: use Dataflow → BigQuery Storage Write API
```

### Storage Write API (Modern Recommended Approach)

```python
# BigQuery Storage Write API — higher throughput, exactly-once semantics
from google.cloud.bigquery_storage_v1 import BigQueryWriteClient, types

write_client = BigQueryWriteClient()

# COMMITTED mode — immediately queryable after write
stream_name = write_client.create_write_stream(
    parent=f"projects/{project}/datasets/{dataset}/tables/{table}",
    write_stream=types.WriteStream(type_=types.WriteStream.Type.COMMITTED)
)

# BUFFERED mode — batch up rows, commit when ready
# PENDING mode — batch, finalize, then commit atomically (exactly-once)
```

### Merge / Upsert (DML)

```sql
-- MERGE statement for SCD Type 1 (upsert)
MERGE INTO curated.customers AS target
USING staging.customers_delta AS source
ON target.customer_id = source.customer_id

WHEN MATCHED AND (
    target.email != source.email
    OR target.membership_type != source.membership_type
    OR target.updated_at < source.updated_at
) THEN UPDATE SET
    email = source.email,
    membership_type = source.membership_type,
    updated_at = source.updated_at

WHEN NOT MATCHED THEN INSERT (
    customer_id, email, membership_type, created_at, updated_at
) VALUES (
    source.customer_id, source.email, source.membership_type,
    source.created_at, source.updated_at
);

-- SCD Type 2 merge (expire old + insert new)
MERGE INTO curated.customers_scd2 AS target
USING (
    -- Identify changed records
    SELECT
        s.customer_id,
        s.email,
        s.membership_type,
        s.updated_at
    FROM staging.customers_delta s
    WHERE EXISTS (
        SELECT 1 FROM curated.customers_scd2 t
        WHERE t.customer_id = s.customer_id
          AND t.is_current = TRUE
          AND t.email != s.email
    )
) AS source
ON target.customer_id = source.customer_id AND target.is_current = TRUE

WHEN MATCHED THEN UPDATE SET
    is_current = FALSE,
    effective_to = source.updated_at;

-- Then insert new versions separately
INSERT INTO curated.customers_scd2
SELECT customer_id, email, membership_type, updated_at AS effective_from,
       DATE '9999-12-31' AS effective_to, TRUE AS is_current
FROM staging.customers_delta
WHERE customer_id IN (SELECT customer_id FROM staging.changes);
```

---

## 7. Cost Management

### Understanding BigQuery Pricing

```
On-demand pricing:
  - $5 per TB of data scanned (may vary by region)
  - Storage: $0.02/GB/month (active), $0.01/GB/month (long-term after 90 days)

Committed use:
  - $1700/slot/month (committed 1 year)
  - Better for consistent, predictable workloads

Free tier:
  - 1TB queries free per month
  - 10GB storage free per month
```

### Cost Control Techniques

```sql
-- 1. Estimate bytes before running (use DRY RUN)
-- In Console: "This query will process X GB when run"
-- Via API:
SELECT job_config.dry_run = True

-- 2. Set maximum bytes billed (fail if query exceeds budget)
-- In Console: Set "Maximum bytes billed"
-- In Python:
job_config = bigquery.QueryJobConfig(maximum_bytes_billed=10 * 1024**3)  # 10 GB limit

-- 3. Use table snapshots instead of full copies
CREATE SNAPSHOT TABLE dataset.snapshot_20240115
CLONE dataset.large_table
FOR SYSTEM_TIME AS OF TIMESTAMP '2024-01-15 00:00:00 UTC'
OPTIONS (expiration_timestamp = TIMESTAMP '2024-03-15 00:00:00 UTC');

-- 4. Partition expiration for cost reduction
ALTER TABLE analytics.raw_events
SET OPTIONS (partition_expiration_days = 365);

-- 5. Column-level partitioning vs full scans
-- Verify partition pruning works via bytes estimate

-- 6. Reservation / slot commitment for predictable workloads
-- Attach reservations to specific projects/folders for cost isolation
```

### Cost Monitoring Query

```sql
-- Track spend by user/project over last 30 days
SELECT
    user_email,
    ROUND(SUM(total_bytes_processed) / POW(1024, 4) * 5, 2) AS estimated_cost_usd,
    SUM(total_bytes_processed) / POW(1024, 3) AS total_gb_scanned,
    COUNT(*) AS query_count
FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE DATE(creation_time) >= CURRENT_DATE() - 30
  AND state = 'DONE'
  AND job_type = 'QUERY'
GROUP BY user_email
ORDER BY estimated_cost_usd DESC
LIMIT 20;
```

---

## 8. BigQuery ML (BQML)

BQML enables training and serving ML models directly in BigQuery using SQL — critical for MarTech propensity scoring use cases.

```sql
-- Train a logistic regression for churn prediction
CREATE OR REPLACE MODEL `analytics.member_churn_model`
OPTIONS (
    model_type = 'LOGISTIC_REG',
    input_label_cols = ['churned'],
    auto_class_weights = TRUE,
    max_iterations = 100
) AS
SELECT
    -- Features
    recency_days,
    frequency,
    monetary,
    membership_tenure_days,
    total_categories_purchased,
    sessions_last_90d,
    -- Label
    CASE WHEN NOT renewed AND days_to_renewal < 30 THEN 1 ELSE 0 END AS churned
FROM curated.member_features
WHERE feature_date = DATE_SUB(CURRENT_DATE(), INTERVAL 180 DAY);

-- Score all active members
SELECT
    customer_id,
    predicted_churned_probs[OFFSET(0)].prob AS churn_probability
FROM ML.PREDICT(
    MODEL `analytics.member_churn_model`,
    (SELECT * FROM curated.member_features WHERE feature_date = CURRENT_DATE())
);

-- K-Means clustering for RFM segmentation
CREATE OR REPLACE MODEL analytics.rfm_clusters
OPTIONS (model_type = 'KMEANS', num_clusters = 5)
AS
SELECT recency_days, frequency, monetary
FROM curated.rfm_features;

-- Assign clusters to members
SELECT customer_id, CENTROID_ID AS cluster
FROM ML.PREDICT(MODEL analytics.rfm_clusters,
    (SELECT customer_id, recency_days, frequency, monetary FROM curated.rfm_features));

-- Matrix factorization for product recommendations
CREATE OR REPLACE MODEL analytics.product_recommender
OPTIONS (
    model_type = 'MATRIX_FACTORIZATION',
    user_col = 'customer_id',
    item_col = 'product_id',
    rating_col = 'purchase_count',
    feedback_type = 'implicit'
)
AS
SELECT customer_id, product_id, COUNT(*) AS purchase_count
FROM curated.purchase_history
GROUP BY 1, 2;

-- Get top 5 recommendations per member
SELECT * FROM ML.RECOMMEND(
    MODEL analytics.product_recommender,
    (SELECT DISTINCT customer_id FROM curated.members),
    STRUCT(5 AS top_k)
);
```

---

## 9. BigQuery Omni & Cross-Cloud

```sql
-- BigQuery Omni: query data in S3 or Azure Data Lake without moving it
-- Create connection to AWS S3
-- Then create external table:
CREATE EXTERNAL TABLE dataset.s3_events
WITH CONNECTION `us.aws-connection`
OPTIONS (
    format = 'PARQUET',
    uris = ['s3://my-bucket/events/*.parquet']
);

-- Query cross-cloud data
SELECT e.user_id, a.customer_segment
FROM dataset.s3_events e  -- AWS S3 data
JOIN `bq-project.analytics.customers` a  -- BigQuery data
ON e.user_id = a.customer_id;

-- Cross-region queries via authorized datasets
```

---

## 10. AlloyDB — Architecture & Use Cases

### What is AlloyDB?

AlloyDB is Google Cloud's **fully managed PostgreSQL-compatible database** designed for high-performance analytical and transactional workloads. It combines:
- Full PostgreSQL compatibility (use any Postgres client/driver)
- Google-built storage layer with columnar caching
- Automatic read replicas that can handle both OLTP and OLAP

### AlloyDB Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      ALLOYDB CLUSTER                          │
│                                                              │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │  Primary Instance│    │  Read Replicas  │                 │
│  │  (Read/Write)   │    │  (Read-only)    │                 │
│  │                 │    │  - Auto-scaling  │                 │
│  │  HTAP Engine:   │    │  - Columnar cache│                 │
│  │  - Row store    │    │    for analytics │                 │
│  │  - Column store │    └─────────────────┘                 │
│  └────────┬────────┘                                        │
│           │                                                  │
│  ┌────────▼────────────────────────────────────────────┐   │
│  │           DISTRIBUTED STORAGE LAYER                  │   │
│  │  - Log-structured, append-only                      │   │
│  │  - 6-way replication across 3 zones                 │   │
│  │  - Instant database cloning                         │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### AlloyDB vs Standard PostgreSQL vs Cloud SQL

| Feature | AlloyDB | Cloud SQL (PostgreSQL) | Self-managed PostgreSQL |
|---------|---------|----------------------|------------------------|
| Compatibility | 100% PostgreSQL | 100% PostgreSQL | Native |
| Throughput | 4x PostgreSQL | 1x | 1x |
| Analytics (HTAP) | Columnar engine built-in | No | No |
| Availability | 99.99% (HA) | 99.95% | Manual HA |
| Scaling | Vertical + read replicas | Vertical + read replicas | Manual |
| Cloning | Instant | Hours | Manual |
| Price | Premium (~$0.12/vCPU/hr) | Standard | Hardware cost |

### AlloyDB Use Cases (and When to Choose It)

**Ideal for:**
1. **Operational HTAP workloads**: Real-time dashboards alongside transactional writes — e.g., order management with live reporting.
2. **High-throughput transactional workloads**: Online checkout, inventory updates — needs 4-5x throughput of standard PostgreSQL.
3. **PostgreSQL migration with performance boost**: Lift-and-shift existing PostgreSQL with no code changes but better performance.
4. **AlloyDB Omni**: Run AlloyDB anywhere (on-prem, other clouds) — critical for hybrid deployments.

**In Costco context:**
- AlloyDB could serve as the **operational data store** for customer profile APIs — fast lookups of member data with low latency (<10ms P99).
- MarTech personalization API: given a member_id, return their top product recommendations in real time. AlloyDB handles thousands of such queries per second.

### AlloyDB SQL Examples

```sql
-- AlloyDB uses standard PostgreSQL syntax
-- Enabling columnar engine for analytics query
SET columnar.enabled = true;

-- Create table with columnar engine hint for mixed workload
CREATE TABLE member_activity (
    member_id      BIGINT NOT NULL,
    activity_date  DATE NOT NULL,
    activity_type  VARCHAR(50),
    revenue        DECIMAL(12,2),
    PRIMARY KEY (member_id, activity_date)
);

-- AlloyDB auto-detects analytical queries and uses columnar cache
-- No syntax change required

-- Full-text search (PostgreSQL tsvector)
CREATE INDEX idx_product_search ON products USING GIN(
    to_tsvector('english', name || ' ' || description)
);

SELECT product_id, name
FROM products
WHERE to_tsvector('english', name || ' ' || description) @@ plainto_tsquery('organic olive oil')
ORDER BY ts_rank(to_tsvector('english', name || ' ' || description), plainto_tsquery('organic olive oil')) DESC;

-- JSONB for semi-structured product attributes
ALTER TABLE products ADD COLUMN attributes JSONB;

SELECT product_id, attributes->>'origin' AS origin
FROM products
WHERE attributes @> '{"category": "organic", "certified": true}';

-- Partial index for active members (common in OLTP)
CREATE INDEX idx_active_members ON members (member_id, last_visit_date)
WHERE membership_status = 'active';  -- Only indexes active members

-- Window functions work as standard PostgreSQL
SELECT
    member_id,
    activity_date,
    SUM(revenue) OVER (PARTITION BY member_id ORDER BY activity_date
                       ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS rolling_30d_revenue
FROM member_activity;
```

### AlloyDB vs BigQuery Decision

```
Use AlloyDB when:
- Need <10ms query latency (OLTP + light analytics)
- PostgreSQL application compatibility required
- Transactional workloads (ACID compliance)
- Operational data serving (real-time reads by primary key)
- Data is <10TB (BigQuery starts shining at multi-TB)

Use BigQuery when:
- Full analytical workloads (TB+ scans, no row-level latency SLA)
- Serverless (no cluster to manage)
- Historical data analysis, reporting, ML training
- Complex aggregations, window functions, JOINs across massive data
- Federated queries across multiple sources
```

---

## 11. Cloud Spanner — Architecture & Use Cases

### What is Cloud Spanner?

Cloud Spanner is Google's **globally distributed, horizontally scalable, strongly consistent relational database**. It uniquely combines:
- SQL query language + relational schema
- Horizontal scaling (add nodes = more throughput, not just storage)
- External consistency (the highest form of ACID — globally consistent reads)
- Multi-region replication with synchronous writes

### Why Spanner Exists: The CAP Theorem Violation (Sort Of)

Traditional databases: Horizontal scale → give up ACID consistency (NoSQL route) OR keep consistency → give up horizontal scale (RDBMS).

Spanner's answer: **TrueTime** — atomic clocks + GPS receivers in every Google datacenter provide bounded timestamp uncertainty, enabling globally consistent reads without coordination delays.

### Spanner Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                     SPANNER INSTANCE                              │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                        │
│  │  Node 1  │  │  Node 2  │  │  Node 3  │   ... N nodes          │
│  │(us-east1)│  │(us-west1)│  │(europe-w)│                        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                        │
│       │              │              │                              │
│  ┌────▼──────────────▼──────────────▼───────────────────────┐    │
│  │                   SPANNER STORAGE                          │    │
│  │  - Colossus-backed tablets (sorted key-value store)       │    │
│  │  - Data partitioned into splits by primary key range     │    │
│  │  - Each split replicated across all nodes (Paxos)        │    │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  TrueTime: globally synchronized clocks (GPS + atomic clocks)    │
└───────────────────────────────────────────────────────────────────┘
```

### Spanner Data Model

Spanner uses **interleaved tables** — child table rows are physically stored with parent rows to reduce cross-node lookups.

```sql
-- Parent table
CREATE TABLE Members (
    MemberId   INT64 NOT NULL,
    Name       STRING(100) NOT NULL,
    Email      STRING(255),
    Status     STRING(20),
    CreatedAt  TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp = true),
) PRIMARY KEY (MemberId);

-- Interleaved child table (physically co-located with parent)
CREATE TABLE MemberOrders (
    MemberId   INT64 NOT NULL,    -- References parent
    OrderId    INT64 NOT NULL,
    OrderDate  DATE NOT NULL,
    TotalAmount FLOAT64,
) PRIMARY KEY (MemberId, OrderId),
  INTERLEAVE IN PARENT Members ON DELETE CASCADE;

-- Secondary index
CREATE INDEX MembersByEmail ON Members(Email);
CREATE INDEX OrdersByDate ON MemberOrders(OrderDate);

-- DML
INSERT INTO Members (MemberId, Name, Email, Status, CreatedAt)
VALUES (1, 'John Doe', 'john@example.com', 'active', PENDING_COMMIT_TIMESTAMP());

UPDATE Members SET Status = 'inactive'
WHERE MemberId = 1;

DELETE FROM Members WHERE Status = 'cancelled'
  AND TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), CreatedAt, DAY) > 365;

-- Transaction (all-or-nothing across tables)
BEGIN;
UPDATE Members SET balance = balance - 100 WHERE MemberId = 1;
INSERT INTO MemberTransactions VALUES (1, 'debit', 100, PENDING_COMMIT_TIMESTAMP());
COMMIT;
```

### Spanner Query Patterns

```sql
-- Standard SQL (ANSI 2011 compliant)
SELECT m.Name, COUNT(o.OrderId) AS order_count, SUM(o.TotalAmount) AS total_spend
FROM Members m
LEFT JOIN MemberOrders o ON m.MemberId = o.MemberId
WHERE m.Status = 'active'
  AND o.OrderDate >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
GROUP BY m.MemberId, m.Name
HAVING total_spend > 1000
ORDER BY total_spend DESC;

-- Stale reads (read historical data without coordinating with leader)
-- Useful for analytics that don't need absolute freshness
SELECT * FROM Members
@{stale_read = EXACT_STALENESS(30s)}
WHERE Status = 'active';

-- Change streams (CDC — capture data changes)
CREATE CHANGE STREAM MemberChanges
FOR Members, MemberOrders
OPTIONS (retention_period = '7d');

-- Query change stream
SELECT ChangeRecord FROM READ_MemberChanges(
    start_timestamp => '2024-01-15T00:00:00Z',
    end_timestamp => '2024-01-15T23:59:59Z',
    partition_token => NULL,
    read_options => JSON '{"data_change_record_limit": 1000}'
);
```

### Spanner Use Cases

**Ideal for:**
1. **Global retail/e-commerce**: Inventory updates that need to be consistent across all global warehouses simultaneously.
2. **Financial transactions**: Account balances, transfers — need guaranteed ACID across horizontal scale.
3. **Session state at scale**: Millions of concurrent user sessions that need fast read/write with no data loss.
4. **Membership management** (Costco-relevant): Globally consistent member profiles where a membership cancellation in one region must immediately prevent access in all regions.

**In Costco context:**
- Spanner could be the **source of truth for membership data** — when a member renews or cancels, that update is globally visible with zero lag. Critical for access control at warehouses globally.
- Inventory availability APIs — real-time stock levels across all warehouses.

### Spanner vs AlloyDB vs BigQuery Decision

```
Cloud Spanner:
✓ Global distribution required (multi-region strong consistency)
✓ Horizontal write scalability (>10K writes/second)
✓ Financial-grade ACID transactions
✓ Predictable <10ms latency at any scale
✗ More expensive than other options
✗ No native PostgreSQL compatibility (uses own SQL dialect + drivers)

AlloyDB:
✓ PostgreSQL compatibility (migrate existing apps without code changes)
✓ High throughput OLTP + columnar read replicas for HTAP
✓ Best price-performance for single-region OLTP
✗ Not horizontally scalable (vertical + read replicas only)
✗ Single-region (no global distribution)

BigQuery:
✓ Petabyte-scale analytics at low cost
✓ Serverless (no infrastructure management)
✓ Best for batch analytics, ML, reporting
✗ Not for OLTP — high latency (seconds, not milliseconds)
✗ No real-time row-level reads
```

---

## 12. Decision Framework — Choosing the Right Database

### Decision Matrix for Common Use Cases

| Use Case | Best Choice | Why |
|----------|------------|-----|
| Campaign performance dashboards | BigQuery | TB-scale aggregations, SQL, serverless |
| Real-time member profile API | AlloyDB | Low latency, PostgreSQL compatibility |
| Global inventory tracking | Spanner | Horizontal scale, global consistency |
| Historical event data lake | BigQuery | Petabytes, columnar, cheap storage |
| Transactional order management | AlloyDB or Spanner | ACID, low latency |
| ML model training data | BigQuery | Bulk scans, BQML integration |
| Real-time personalization serving | AlloyDB | <10ms P99, high-read throughput |
| Global membership management | Spanner | Strong consistency across regions |
| Ad-hoc analysis by analysts | BigQuery | Standard SQL, pay-per-query |
| CDC / streaming pipeline target | BigQuery (streaming) | High ingestion rate |

### Interview Answer Framework: "Which database would you choose for X?"

**Template:**
1. **State access pattern**: OLTP (point reads/writes) vs OLAP (full scans, aggregations) vs HTAP (both)?
2. **State scale**: GB-TB-PB? Queries/second? Writes/second?
3. **State consistency needs**: Eventual vs strong vs globally consistent?
4. **State latency SLA**: <10ms (operational) vs seconds acceptable (analytical)?
5. **State operational overhead**: How much cluster management is acceptable?
6. **Then recommend**: BigQuery (analytics/batch) / AlloyDB (OLTP+HTAP) / Spanner (global scale+consistency).

---

## 13. Interview Q&A Bank

**Q: Explain how BigQuery's columnar storage helps with analytical queries.**
A: BigQuery stores data column-by-column. When you run `SELECT revenue, user_id FROM events WHERE date = '2024-01-15'`, it only reads the revenue, user_id, and date columns — skipping all other columns. On a table with 200 columns, this means reading 3/200 = 1.5% of the storage. Combined with compression (values in the same column are similar and compress well), a query that would read 1TB row-by-row might only read 20GB column-by-column. This is the core reason BigQuery can scan petabytes efficiently.

**Q: What is the difference between partitioning and clustering in BigQuery? When would you use each?**
A: Partitioning divides the table into segments (usually by date), and BigQuery maintains metadata about which partition contains which data — allowing entire partitions to be skipped when a filter excludes them. This is coarse-grained pruning at the partition level. Clustering is finer-grained: within each partition, rows with similar values for the cluster columns are co-located. Clustering helps when queries filter on specific column values (campaign_id = 'x', channel = 'email'). Use both together for best results: partition by date (reduces scope to a day's data) + cluster by channel/campaign_id (within that day, skip rows that don't match the filter).

**Q: When would you choose Cloud Spanner over AlloyDB for a new application?**
A: Choose Spanner when: (1) global distribution is required — the app serves users across multiple continents and needs consistent data everywhere without replication lag; (2) write throughput must scale horizontally beyond what a single node can handle (100K+ writes/second); (3) financial-grade consistency is critical — can't have any data inconsistency even for milliseconds. Choose AlloyDB when: (1) the application is PostgreSQL-based and migration simplicity matters; (2) workload is primarily regional; (3) need columnar acceleration for mixed OLTP+OLAP without a separate analytics system; (4) cost is a constraint (AlloyDB is cheaper than Spanner for single-region).

**Q: A BigQuery query that scans 500GB is running for 10 minutes. How do you optimize it?**
A: Step 1 — check the query plan for partition pruning: is the WHERE clause on the partition column? If not, add a date filter. Step 2 — check for `SELECT *` — replace with specific column names to leverage columnar storage. Step 3 — look for correlated subqueries in SELECT — replace with LEFT JOINs. Step 4 — check for skew in GROUP BY: use `APPROX_COUNT_DISTINCT` if exact counts not needed. Step 5 — check if the query can benefit from a materialized view (if it's a frequently-run aggregation). Step 6 — if it's a multi-step pipeline, use TEMP tables to materialize intermediate results used more than once.

**Q: How does BigQuery handle transactions and what are its ACID guarantees?**
A: BigQuery supports DML (INSERT, UPDATE, DELETE, MERGE) with ACID semantics within a single DML statement via snapshot isolation. As of 2024, BigQuery also supports multi-statement transactions: `BEGIN TRANSACTION; UPDATE...; INSERT...; COMMIT TRANSACTION;` — providing atomicity across multiple statements. However, BigQuery is optimized for analytical workloads, not high-frequency transactional operations — DML has higher latency than streaming inserts and is limited to 1500 DML statements per table per day on the free tier. For high-frequency transactional workloads, AlloyDB or Spanner is more appropriate.

**Q: Describe a BigQuery pipeline for near-real-time campaign dashboards with <5 minute latency.**
A: Architecture: (1) Pub/Sub collects click/impression events from ad tags; (2) Dataflow Streaming job reads from Pub/Sub, applies transformations (UTM parsing, identity resolution lookup from Firestore), and writes to BigQuery using Storage Write API (committed stream for immediate queryability); (3) BigQuery materialized view over the raw events table, refreshed every 60 seconds, pre-aggregates by campaign/channel/hour; (4) Looker dashboard queries the materialized view with filters on the current hour's date partition. End-to-end latency: event generation → Pub/Sub (~1s) → Dataflow (~30s) → BigQuery write → materialized view refresh (60s) → dashboard auto-refresh (60s) = ~3 min total.
