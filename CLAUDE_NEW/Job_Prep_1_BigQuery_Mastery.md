# 🎯 GCP BIGQUERY INTERVIEW PREPARATION - COMPLETE GUIDE
## Crack the Senior Data Engineer Role at Lloyds Technology Centre

**Target Role:** Senior Data Engineer (GCP/BigQuery Focus)  
**Company:** Lloyds Technology Centre, Hyderabad  
**Key Skills:** BigQuery, Python, Data Engineering, Process Improvement

---

## 📚 TABLE OF CONTENTS

**PART A: BIGQUERY MASTERY**
1. BigQuery Architecture & Fundamentals
2. BigQuery SQL - Advanced Patterns
3. Performance Optimization Techniques
4. Partitioning & Clustering Strategies
5. Cost Optimization Best Practices
6. BigQuery Data Loading Methods
7. BigQuery ML (BQML) Basics
8. Security & Access Control
9. Monitoring & Troubleshooting

**PART B: PYTHON FOR DATA ENGINEERING**
10. Python Data Processing Libraries
11. Google Cloud Client Libraries
12. Data Pipeline Patterns
13. Error Handling & Logging
14. Testing & Quality Assurance

**PART C: DATA MANAGEMENT & PROCESSES**
15. Data Governance & Quality
16. Documentation Best Practices
17. Project Management for Data Engineers
18. Process Improvement Methodologies

---

## 🎯 PART 1: BIGQUERY ARCHITECTURE & FUNDAMENTALS

### **1.1 What is BigQuery?**

BigQuery is Google's **fully managed, serverless, highly scalable enterprise data warehouse** designed for analytics.

**Key Characteristics:**
- **Serverless:** No infrastructure management required
- **Columnar Storage:** Optimized for analytics (read-heavy workloads)
- **Massive Parallelism:** Distributes queries across thousands of machines
- **Separation of Storage & Compute:** Pay for storage and compute separately
- **Standard SQL:** ANSI SQL 2011 compliant

### **1.2 BigQuery Architecture**

```
┌─────────────────────────────────────────────────┐
│              BIGQUERY SERVICE                    │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────┐         ┌─────────────────┐  │
│  │   DREMEL     │────────▶│   COLOSSUS      │  │
│  │ (Query Engine)│         │ (Storage Layer) │  │
│  │              │         │                 │  │
│  │ - Executes   │         │ - Columnar      │  │
│  │   queries    │         │ - Compressed    │  │
│  │ - Parallel   │         │ - Distributed   │  │
│  └──────────────┘         └─────────────────┘  │
│                                                  │
│  ┌──────────────┐                               │
│  │   JUPITER    │                               │
│  │  (Network)   │                               │
│  │              │                               │
│  │ - 1 Petabit/s│                               │
│  │ - Connects   │                               │
│  │   compute &  │                               │
│  │   storage    │                               │
│  └──────────────┘                               │
└─────────────────────────────────────────────────┘
```

**Components:**
1. **Dremel:** Query execution engine (distributed query processing)
2. **Colossus:** Distributed storage system (Google's filesystem)
3. **Jupiter:** High-speed network (1 Petabit/sec bandwidth)
4. **Borg:** Cluster management (allocates compute resources)

### **1.3 Key Concepts You MUST Know**

#### **Slots**
- **What:** Unit of computational capacity
- **Default:** 2000 slots for on-demand queries
- **Pricing:** Flat-rate pricing based on slot reservations
- **Important:** Complex queries use more slots

#### **Storage Format**
- **Capacitor:** Proprietary columnar format
- **Benefits:** Extreme compression (10:1 typical), fast column scans
- **Structure:** Each column stored separately, compressed

#### **Query Execution**
```
1. Query submitted → Parsed & optimized
2. Divided into stages (execution tree)
3. Each stage divided into tasks
4. Tasks distributed across workers
5. Results aggregated and returned
```

### **1.4 Common Interview Questions**

**Q1: Explain BigQuery's separation of storage and compute.**
```
ANSWER:
BigQuery decouples storage from compute, meaning:
- Storage: Data stored in Colossus (Google's distributed filesystem)
- Compute: Dremel engine processes queries independently
- Benefits:
  1. Scale storage and compute independently
  2. Pay only for what you use
  3. No need to provision clusters
  4. Multiple concurrent queries don't affect storage
  5. Pause compute without losing data

Example: Can store 10TB of data but only pay for compute when querying.
```

**Q2: How does BigQuery achieve such fast query performance?**
```
ANSWER:
1. Columnar Storage: Reads only needed columns, not entire rows
2. Compression: Reduces I/O with high compression ratios
3. Massive Parallelism: Distributes work across thousands of machines
4. Tree Architecture: Hierarchical query execution
5. In-Memory Shuffle: Fast data exchange between workers
6. Smart Caching: Caches query results for 24 hours

Example: Query scanning 1TB can complete in seconds due to parallelism.
```

**Q3: What's the difference between on-demand and flat-rate pricing?**
```
ANSWER:
On-Demand:
- Pay per query (bytes scanned)
- $6.25 per TB scanned (first 1TB free/month)
- Good for: Variable workloads, starting out
- No commitment required

Flat-Rate:
- Pay for dedicated slot capacity
- $2,000/month per 100 slots (annual commitment)
- Good for: Predictable workloads, high query volume
- Guaranteed capacity

Example: If scanning 500TB/month, flat-rate becomes cheaper.
```

---

## 🔧 PART 2: BIGQUERY SQL - ADVANCED PATTERNS

### **2.1 BigQuery-Specific SQL Features**

#### **QUALIFY Clause (BigQuery Exclusive)**
```sql
-- Instead of nested SELECT with window function
-- ❌ OLD WAY
SELECT * FROM (
    SELECT 
        user_id,
        purchase_date,
        amount,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY purchase_date DESC) AS rn
    FROM purchases
) WHERE rn = 1;

-- ✅ BIGQUERY WAY (Much cleaner!)
SELECT 
    user_id,
    purchase_date,
    amount
FROM purchases
QUALIFY ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY purchase_date DESC) = 1;
```

#### **ARRAY Functions**
```sql
-- Working with arrays (BigQuery native)
SELECT 
    customer_id,
    ARRAY_AGG(product_id ORDER BY purchase_date) AS products_purchased,
    ARRAY_LENGTH(ARRAY_AGG(product_id)) AS total_products
FROM purchases
GROUP BY customer_id;

-- Unnesting arrays
SELECT 
    customer_id,
    product
FROM customers,
UNNEST(favorite_products) AS product;

-- Array filtering
SELECT 
    customer_id,
    ARRAY(
        SELECT product 
        FROM UNNEST(products) AS product 
        WHERE price > 100
    ) AS expensive_products
FROM customer_products;
```

#### **STRUCT (Record) Types**
```sql
-- Create and query structs
SELECT 
    order_id,
    STRUCT(
        customer_name,
        customer_email,
        customer_phone
    ) AS customer_info
FROM orders;

-- Access struct fields
SELECT 
    order_id,
    customer_info.customer_name,
    customer_info.customer_email
FROM orders_with_struct;
```

#### **Approximate Aggregation Functions**
```sql
-- Much faster for large datasets
SELECT 
    category,
    APPROX_COUNT_DISTINCT(user_id) AS approx_users,    -- Fast
    COUNT(DISTINCT user_id) AS exact_users,            -- Slow
    APPROX_QUANTILES(price, 4) AS quartiles,           -- Fast
    APPROX_TOP_COUNT(product_id, 10) AS top_products   -- Fast
FROM sales
GROUP BY category;
```

### **2.2 Your Interview Questions in BigQuery**

#### **Routes Problem (LEAST/GREATEST)**
```sql
-- EXACT solution for your Q1
SELECT 
    LEAST(source, destination) AS source,
    GREATEST(source, destination) AS destination,
    distance
FROM `project.dataset.routes`
GROUP BY 
    LEAST(source, destination),
    GREATEST(source, destination),
    distance;

-- With additional metrics
SELECT 
    LEAST(source, destination) AS city1,
    GREATEST(source, destination) AS city2,
    MIN(distance) AS min_distance,
    MAX(distance) AS max_distance,
    COUNT(*) AS route_count,
    ARRAY_AGG(STRUCT(source, destination, distance)) AS all_routes
FROM `project.dataset.routes`
GROUP BY city1, city2;
```

#### **Sessionization in BigQuery**
```sql
-- EXACT solution for your Q2 in BigQuery
WITH time_gaps AS (
    SELECT 
        user_id,
        event_ts,
        time_spent_mins,
        LAG(event_ts) OVER (
            PARTITION BY user_id 
            ORDER BY event_ts
        ) AS prev_event_ts,
        TIMESTAMP_DIFF(
            event_ts,
            LAG(event_ts) OVER (PARTITION BY user_id ORDER BY event_ts),
            MINUTE
        ) AS minutes_gap
    FROM `project.dataset.events`
),
session_flags AS (
    SELECT 
        *,
        CASE 
            WHEN minutes_gap IS NULL OR minutes_gap > 30 
            THEN 1 ELSE 0 
        END AS is_new_session
    FROM time_gaps
),
sessions AS (
    SELECT 
        user_id,
        event_ts,
        COALESCE(time_spent_mins, 0) AS time_spent_mins,
        SUM(is_new_session) OVER (
            PARTITION BY user_id 
            ORDER BY event_ts
        ) AS session_id
    FROM session_flags
)
SELECT 
    user_id,
    session_id,
    MIN(event_ts) AS session_start_ts,
    MAX(event_ts) AS session_end_ts,
    COUNT(*) AS total_events,
    SUM(time_spent_mins) AS total_time_spent
FROM sessions
GROUP BY user_id, session_id
ORDER BY user_id, session_id;
```

---

## ⚡ PART 3: PERFORMANCE OPTIMIZATION

### **3.1 Query Optimization Techniques**

#### **1. SELECT Only Needed Columns**
```sql
-- ❌ BAD: Scans entire table
SELECT * FROM `project.dataset.large_table`;

-- ✅ GOOD: Scans only 3 columns
SELECT user_id, event_date, revenue 
FROM `project.dataset.large_table`;

-- Cost difference: 
-- SELECT * on 100-column table = 100x more expensive!
```

#### **2. Use Partitioning for Date Filters**
```sql
-- ❌ BAD: Scans all partitions
SELECT * FROM `project.dataset.events`
WHERE EXTRACT(YEAR FROM event_date) = 2024;

-- ✅ GOOD: Scans only relevant partitions
SELECT * FROM `project.dataset.events`
WHERE event_date BETWEEN '2024-01-01' AND '2024-12-31';

-- Or even better:
WHERE event_date = '2024-01-15';  -- Single partition
```

#### **3. Avoid SELECT DISTINCT When Possible**
```sql
-- ❌ BAD: Requires full shuffle
SELECT DISTINCT user_id FROM events;

-- ✅ GOOD: Use GROUP BY (often faster)
SELECT user_id FROM events GROUP BY user_id;

-- ✅ EVEN BETTER: Use APPROX_COUNT_DISTINCT for counts
SELECT APPROX_COUNT_DISTINCT(user_id) FROM events;
```

#### **4. Filter Early, Join Late**
```sql
-- ❌ BAD: Joins large tables then filters
SELECT * FROM large_table1 t1
JOIN large_table2 t2 ON t1.id = t2.id
WHERE t1.date = '2024-01-01';

-- ✅ GOOD: Filter first, then join smaller result
SELECT * FROM (
    SELECT * FROM large_table1 WHERE date = '2024-01-01'
) t1
JOIN large_table2 t2 ON t1.id = t2.id;
```

#### **5. Use LIMIT with ORDER BY**
```sql
-- ❌ BAD: Sorts entire table
SELECT * FROM large_table ORDER BY created_date DESC;

-- ✅ GOOD: Add LIMIT
SELECT * FROM large_table 
ORDER BY created_date DESC 
LIMIT 1000;
```

### **3.2 Explain Query Execution**
```sql
-- Use EXPLAIN to understand query plan
EXPLAIN
SELECT 
    user_id,
    COUNT(*) as event_count
FROM `project.dataset.events`
WHERE event_date = '2024-01-01'
GROUP BY user_id;

-- Look for:
-- - Slot time (lower is better)
-- - Bytes shuffled (lower is better)
-- - Stages (fewer is better)
-- - Partition filters applied (good!)
```

---

## 📊 PART 4: PARTITIONING & CLUSTERING

### **4.1 Table Partitioning**

**What:** Divides table into segments based on column value  
**Why:** Reduces query cost by scanning only relevant partitions  
**Types:** Date, timestamp, integer range, ingestion time

#### **Creating Partitioned Tables**
```sql
-- Date partitioned table
CREATE TABLE `project.dataset.events_partitioned`
PARTITION BY DATE(event_timestamp)
AS
SELECT * FROM `project.dataset.events`;

-- With partition expiration (auto-delete old data)
CREATE TABLE `project.dataset.events_partitioned`
PARTITION BY DATE(event_timestamp)
OPTIONS(
    partition_expiration_days = 90,
    description = "Events table partitioned by date, 90-day retention"
)
AS SELECT * FROM `project.dataset.events`;

-- Integer range partitioning
CREATE TABLE `project.dataset.users_by_age`
PARTITION BY RANGE_BUCKET(age, GENERATE_ARRAY(0, 100, 10))
AS SELECT * FROM `project.dataset.users`;
```

#### **Querying Partitioned Tables**
```sql
-- ✅ GOOD: Partition pruning applied
SELECT * FROM `project.dataset.events_partitioned`
WHERE DATE(event_timestamp) = '2024-01-01';

-- Query scans: ~1/365 of table (if daily partitions for 1 year)

-- ❌ BAD: No partition pruning
SELECT * FROM `project.dataset.events_partitioned`
WHERE EXTRACT(MONTH FROM event_timestamp) = 1;

-- Query scans: ENTIRE table!
```

### **4.2 Clustering**

**What:** Sorts data within partitions by clustering columns  
**Why:** Improves performance for filtered/aggregated queries  
**Limit:** Up to 4 clustering columns

#### **Creating Clustered Tables**
```sql
-- Partitioned + Clustered
CREATE TABLE `project.dataset.events_optimized`
PARTITION BY DATE(event_timestamp)
CLUSTER BY user_id, event_type
AS
SELECT * FROM `project.dataset.events`;

-- Query that benefits:
SELECT user_id, COUNT(*) as events
FROM `project.dataset.events_optimized`
WHERE DATE(event_timestamp) = '2024-01-01'
  AND user_id = 12345
GROUP BY user_id;

-- Benefit: Scans only blocks containing user_id = 12345
```

#### **Choosing Clustering Columns**
```
RULE: Cluster by columns used in:
1. WHERE filters (most selective first)
2. GROUP BY
3. ORDER BY

Example:
- WHERE user_id = X AND country = 'US'
- CLUSTER BY user_id, country

Order matters! Most selective column first.
```

---

## 💰 PART 5: COST OPTIMIZATION

### **5.1 Understanding BigQuery Pricing**

**Storage Costs:**
- Active: $0.020 per GB per month
- Long-term (90+ days no edit): $0.010 per GB per month

**Query Costs (On-Demand):**
- $6.25 per TB scanned
- First 1 TB per month: FREE

**Example Calculation:**
```
Query: SELECT * FROM 1TB table with 100 columns
Cost: $6.25

Query: SELECT col1 FROM same table
If col1 is 1% of data: $0.0625

Savings: 99% cost reduction!
```

### **5.2 Cost Optimization Strategies**

#### **Strategy 1: Partition Pruning**
```sql
-- Cost: Scans 1 day of 365 days = $6.25/365 = $0.017
SELECT * FROM partitioned_table
WHERE date = '2024-01-01';

-- vs scanning full year: $6.25
```

#### **Strategy 2: Clustering**
```sql
-- Reduces data scanned within partitions
-- Typical savings: 20-50% additional
SELECT * FROM clustered_table
WHERE date = '2024-01-01' AND user_id = 123;
```

#### **Strategy 3: Materialized Views**
```sql
-- Pre-compute expensive aggregations
CREATE MATERIALIZED VIEW `project.dataset.daily_summary`
AS
SELECT 
    DATE(timestamp) as date,
    user_id,
    SUM(amount) as total_amount,
    COUNT(*) as transaction_count
FROM `project.dataset.transactions`
GROUP BY date, user_id;

-- Query materialized view (much cheaper!)
SELECT * FROM `project.dataset.daily_summary`
WHERE date = '2024-01-01';

-- Auto-refresh when base table changes
```

#### **Strategy 4: Table Sampling**
```sql
-- For exploration/testing, sample data
SELECT * FROM `project.dataset.large_table`
TABLESAMPLE SYSTEM (1 PERCENT);  -- Scans only 1%

-- Cost: 1% of full table scan
```

#### **Strategy 5: Use Preview Instead of SELECT ***
```
In BigQuery Console:
- Click "Preview" button → FREE (first 10MB)
- vs SELECT * → Costs money

For data exploration, always use Preview first!
```

### **5.3 Query Cost Estimation**
```sql
-- Before running, check cost estimate
-- In BigQuery Console: Shows "This query will process X GB"

-- Using dry run (no cost):
bq query --dry_run --use_legacy_sql=false '
SELECT * FROM `project.dataset.table`
WHERE date = "2024-01-01"
'

-- Output: "Query will process X bytes"
-- Calculate cost: (X bytes / 1TB) * $6.25
```

---

## 📥 PART 6: DATA LOADING METHODS

### **6.1 Loading from GCS (Cloud Storage)**

```sql
-- Load CSV from GCS
LOAD DATA INTO `project.dataset.table`
FROM FILES (
    format = 'CSV',
    uris = ['gs://bucket/path/*.csv'],
    skip_leading_rows = 1
);

-- Load Parquet (RECOMMENDED for large data)
LOAD DATA INTO `project.dataset.table`
FROM FILES (
    format = 'PARQUET',
    uris = ['gs://bucket/data/*.parquet']
);

-- Load with schema auto-detection
LOAD DATA INTO `project.dataset.table`
FROM FILES (
    format = 'JSON',
    uris = ['gs://bucket/*.json'],
    auto_detect = true
);
```

### **6.2 Streaming Inserts**

**Python Example:**
```python
from google.cloud import bigquery

client = bigquery.Client()
table_id = "project.dataset.table"

rows_to_insert = [
    {"user_id": 1, "event": "click", "timestamp": "2024-01-01 10:00:00"},
    {"user_id": 2, "event": "view", "timestamp": "2024-01-01 10:01:00"}
]

errors = client.insert_rows_json(table_id, rows_to_insert)

if errors:
    print(f"Errors: {errors}")
else:
    print("Data inserted successfully")
```

**Characteristics:**
- Low latency (data available immediately)
- Cost: $0.010 per 200 MB
- Use case: Real-time dashboards, event tracking

### **6.3 Data Transfer Service**

**For scheduled, managed transfers:**
- Cloud Storage → BigQuery
- Other Google services → BigQuery
- External sources (S3, Azure) → BigQuery

```python
from google.cloud import bigquery_datatransfer

client = bigquery_datatransfer.DataTransferServiceClient()

# Schedule daily transfer from GCS
transfer_config = {
    "destination_dataset_id": "my_dataset",
    "display_name": "Daily GCS Import",
    "data_source_id": "google_cloud_storage",
    "params": {
        "data_path_template": "gs://bucket/daily/*.csv",
        "destination_table_name_template": "daily_data",
        "file_format": "CSV",
        "skip_leading_rows": 1
    },
    "schedule": "every day 02:00"  # Cron format
}

created_config = client.create_transfer_config(
    parent=client.common_project_path("project-id"),
    transfer_config=transfer_config
)
```

---

## 🤖 PART 7: BIGQUERY ML BASICS

### **7.1 Creating ML Models**

```sql
-- Create linear regression model
CREATE OR REPLACE MODEL `project.dataset.price_model`
OPTIONS(
    model_type='LINEAR_REG',
    input_label_cols=['price']
) AS
SELECT
    bedrooms,
    bathrooms,
    sqft,
    age,
    price
FROM `project.dataset.houses`;

-- Create classification model
CREATE OR REPLACE MODEL `project.dataset.churn_model`
OPTIONS(
    model_type='LOGISTIC_REG',
    input_label_cols=['churned']
) AS
SELECT
    tenure,
    monthly_charges,
    total_charges,
    churned
FROM `project.dataset.customers`;
```

### **7.2 Making Predictions**
```sql
-- Predict on new data
SELECT
    *,
    predicted_price,
    predicted_price_label
FROM ML.PREDICT(
    MODEL `project.dataset.price_model`,
    (
        SELECT 3 as bedrooms, 2 as bathrooms, 
               1500 as sqft, 10 as age
    )
);
```

---

## 🔐 PART 8: SECURITY & ACCESS CONTROL

### **8.1 IAM Roles**

**Common BigQuery Roles:**
```
bigquery.dataViewer      → Read tables/views
bigquery.dataEditor      → Read + Write
bigquery.dataOwner       → Full control
bigquery.user            → Run queries
bigquery.jobUser         → Run jobs
bigquery.admin           → Full BigQuery admin
```

### **8.2 Column-Level Security**
```sql
-- Create policy tag taxonomy
-- In Console: Data Catalog → Policy Tags

-- Apply to column
ALTER TABLE `project.dataset.customers`
ALTER COLUMN ssn SET OPTIONS (
    policy_tags = ('projects/PROJECT/locations/LOCATION/taxonomies/TAXONOMY/policyTags/TAG')
);

-- Only users with tag permissions can see the column
```

### **8.3 Row-Level Security**
```sql
-- Create row access policy
CREATE ROW ACCESS POLICY regional_filter
ON `project.dataset.sales`
GRANT TO ('user:analyst@company.com')
FILTER USING (region = 'EMEA');

-- User can only see EMEA rows
```

---

## 📊 PART 9: MONITORING & TROUBLESHOOTING

### **9.1 Query Information Schema**

```sql
-- View recent queries
SELECT
    creation_time,
    user_email,
    query,
    total_slot_ms,
    total_bytes_processed,
    total_bytes_billed
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
ORDER BY total_bytes_processed DESC
LIMIT 10;

-- Find expensive queries
SELECT
    user_email,
    SUM(total_bytes_billed) / POW(10, 12) as TB_billed,
    SUM(total_bytes_billed) / POW(10, 12) * 6.25 as estimated_cost_usd
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY user_email
ORDER BY TB_billed DESC;
```

### **9.2 Partition/Cluster Info**
```sql
-- Check partition info
SELECT
    partition_id,
    total_rows,
    total_logical_bytes / POW(10, 9) as size_gb
FROM `project.dataset.INFORMATION_SCHEMA.PARTITIONS`
WHERE table_name = 'events'
ORDER BY partition_id DESC
LIMIT 10;
```

---

## 🎯 INTERVIEW QUESTIONS YOU'LL FACE

### **Technical Questions**

**Q1: How would you optimize a query that's scanning too much data?**
```
ANSWER:
1. Select only needed columns (avoid SELECT *)
2. Add partition filter if table is partitioned
3. Use clustering for additional pruning
4. Consider materialized views for repeated queries
5. Use APPROX functions for aggregations
6. Add LIMIT if you don't need all results
7. Check EXPLAIN plan for bottlenecks

Example: Changed SELECT * to SELECT 5 columns → 95% cost reduction
```

**Q2: Explain partitioning vs clustering in BigQuery.**
```
ANSWER:
Partitioning:
- Divides table into segments (by date, timestamp, or integer)
- Reduces cost by scanning only needed partitions
- Automatic pruning when filtering on partition column
- Example: Daily partitions, filter by date = scan 1 day

Clustering:
- Sorts data within partitions by specified columns
- Improves performance by colocating similar data
- Works best with high-cardinality columns
- Up to 4 clustering columns
- Example: Cluster by user_id → all user's data together

Together: Partition by date, cluster by user_id, region
Query for specific user on specific date → minimal scan
```

**Q3: How do you handle slowly changing dimensions (SCD Type 2) in BigQuery?**
```
ANSWER:
Use snapshot tables with effective/end dates:

CREATE TABLE customer_history (
    customer_id INT64,
    name STRING,
    address STRING,
    effective_date DATE,
    end_date DATE,
    is_current BOOL
)
PARTITION BY effective_date
CLUSTER BY customer_id;

-- Get current records:
SELECT * FROM customer_history WHERE is_current = TRUE;

-- Get historical state:
SELECT * FROM customer_history 
WHERE customer_id = 123 
  AND '2023-01-01' BETWEEN effective_date AND COALESCE(end_date, '9999-12-31');

Benefits: 
- Full history maintained
- Partition by effective_date for performance
- Cluster by customer_id for fast lookups
```

---

**PART 10-17 CONTINUE IN NEXT FILE DUE TO LENGTH...**

---

## 🔑 KEY TAKEAWAYS FOR YOUR INTERVIEW

**Memorize These:**
1. **Partitioning** = Cost savings (scan less data)
2. **Clustering** = Performance (within partitions)
3. **Columnar storage** = Speed (read only needed columns)
4. **Slots** = Compute units
5. **QUALIFY** = BigQuery's unique feature for window functions
6. **Approximate functions** = Fast for large data

**Be Ready to Discuss:**
- Your CDM Next project with BigQuery
- Cost optimization you've done
- Complex queries you've written
- Performance troubleshooting experience

**Have Examples Ready:**
- "I optimized a query from $500 to $5 by adding partitioning and selecting specific columns"
- "I implemented incremental loading using _PARTITIONTIME pseudo-column"
- "I used materialized views to pre-compute daily aggregations"

---

**STATUS:** Part 1/2 Complete - BigQuery Deep Dive  
**Next File:** Python for Data Engineering + Data Management
