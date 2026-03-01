# GOOGLE CLOUD BIGQUERY - COMPLETE INTERVIEW GUIDE

## TABLE OF CONTENTS
1. Architecture & Fundamentals
2. Partitioning & Clustering
3. Query Optimization
4. Cost Management
5. Security & Governance
6. Integration with Other Services
7. Top 50 Interview Questions

---

## 1. ARCHITECTURE & FUNDAMENTALS

### What is BigQuery?
**Full Answer for Interview**:
"BigQuery is Google's fully-managed, serverless, petabyte-scale data warehouse designed for large-scale data analytics. Key characteristics:
- **Serverless**: No infrastructure management required
- **Columnar storage**: Capacitor format, optimized for analytics
- **Separation of compute and storage**: Pay for what you use
- **Massively parallel processing**: Dremel query engine
- **SQL interface**: ANSI SQL-compliant
- **Real-time analytics**: Streaming ingestion supported"

### Architecture Components

1. **Dremel** - Query Execution Engine
   - Breaks queries into execution tree
   - Parallel query processing across thousands of servers
   - Columnar processing for fast aggregations

2. **Colossus** - Storage Layer
   - Google's distributed file system
   - Automatic replication and encryption
   - Columnar format with compression

3. **Jupiter** - Network
   - Petabit-scale network between compute and storage
   - Enables fast data movement

4. **Borg** - Cluster Management
   - Resource orchestration
   - Handles compute power and fault tolerance

### Separation of Compute and Storage

**Interview Question**: "Explain how BigQuery's architecture differs from traditional databases?"

**Answer**:
"Traditional databases tightly couple compute and storage on the same servers. BigQuery separates them:
- **Storage**: Data stored in Colossus (distributed storage)
- **Compute**: Dremel workers process queries
- **Benefits**:
  1. Scale each independently
  2. Cost efficiency - pay for storage separately from compute
  3. High availability - multiple replicas
  4. No server management
  5. Automatic resource allocation based on query complexity"

---

## 2. PARTITIONING & CLUSTERING

### Partitioning

**What is it?**
Dividing a large table into smaller segments based on a column (typically date/timestamp).

**Types**:

1. **Time-Unit Column Partitioning**:
```sql
CREATE TABLE dataset.transactions
PARTITION BY DATE(timestamp_column)
AS SELECT * FROM source_table
```

2. **Ingestion Time Partitioning**:
```sql
CREATE TABLE dataset.events
PARTITION BY _PARTITIONDATE
AS SELECT * FROM source
```

3. **Integer Range Partitioning**:
```sql
CREATE TABLE dataset.users
PARTITION BY RANGE_BUCKET(user_id, GENERATE_ARRAY(0, 1000000, 10000))
AS SELECT * FROM source
```

**Benefits**:
- Reduces data scanned → Lower costs
- Improves query performance
- Enables partition pruning
- Easier data lifecycle management

**Partition Limits**:
- Max partitions: 4,000
- Use clustering for more granular organization

### Clustering

**What is it?**
Organizing data within partitions based on column values.

```sql
CREATE TABLE dataset.orders
PARTITION BY DATE(order_date)
CLUSTER BY customer_id, product_category
AS SELECT * FROM source
```

**How it works**:
- Physically sorts data by cluster columns
- Co-locates related data
- Improves performance for filtered queries
- **No additional cost** (free optimization!)

**When to Use Clustering**:
- High-cardinality columns
- Frequently filtered columns
- Need for granularity beyond partitioning
- Up to 4 cluster columns

**Partitioning vs Clustering**:

| Aspect | Partitioning | Clustering |
|--------|-------------|-----------|
| Use Case | Time-based data, lifecycle | High-cardinality filtering |
| Cost Impact | Reduces scanned data | Reduces shuffling |
| Limit | 4,000 partitions | No limit |
| Requires | Partition column | Any columns |
| Combined | Yes, use both for optimal performance |

**Interview Question**: "When would you use partitioning vs clustering?"

**Answer**:
"Use partitioning when:
- Data has clear time dimension
- Need partition-level data retention/deletion
- Data access is predictable by time

Use clustering when:
- Filters on high-cardinality columns
- Need more granularity than 4,000 partitions
- Queries filter on multiple columns

Best practice: Combine both - partition by date, cluster by frequently queried columns like customer_id, region, category."

---

## 3. QUERY OPTIMIZATION

### 1. SELECT Only Needed Columns

```sql
-- ❌ BAD: Scans entire table
SELECT * FROM large_table WHERE date = '2025-02-08'

-- ✅ GOOD: Scans only needed columns
SELECT customer_id, amount, product 
FROM large_table 
WHERE date = '2025-02-08'
```

**Impact**: Can reduce cost by 90%+ if table has many columns

### 2. Filter Early (Predicate Pushdown)

```sql
-- ❌ BAD: Filter after aggregation
SELECT category, SUM(amount) as total
FROM transactions
GROUP BY category
HAVING category = 'Electronics'

-- ✅ GOOD: Filter before aggregation
SELECT category, SUM(amount) as total
FROM transactions
WHERE category = 'Electronics'
GROUP BY category
```

### 3. Use Partitioned/Clustered Tables

```sql
-- ✅ Query automatically prunes partitions
SELECT * FROM partitioned_table
WHERE DATE(timestamp) BETWEEN '2025-01-01' AND '2025-01-31'
-- Only scans January partition, not entire table
```

### 4. Avoid Self-Joins When Possible

```sql
-- ❌ BAD: Self-join for previous value
SELECT 
  a.date,
  a.sales,
  b.sales as prev_sales
FROM sales a
LEFT JOIN sales b ON DATE_ADD(a.date, INTERVAL -1 DAY) = b.date

-- ✅ GOOD: Use window function
SELECT 
  date,
  sales,
  LAG(sales, 1) OVER (ORDER BY date) as prev_sales
FROM sales
```

### 5. Denormalize When Appropriate

```sql
-- ❌ Multiple joins for every query
SELECT o.*, c.name, c.email, p.product_name
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN products p ON o.product_id = p.id

-- ✅ Denormalized table (pre-joined)
SELECT * FROM orders_enriched  -- Already has customer and product info
```

### 6. Use Approximate Functions

```sql
-- ❌ Exact count (expensive)
SELECT COUNT(DISTINCT user_id) FROM large_table

-- ✅ Approximate (faster, cheaper, ~98% accurate)
SELECT APPROX_COUNT_DISTINCT(user_id) FROM large_table
```

Other approximate functions:
- `APPROX_QUANTILES()` - Percentiles
- `APPROX_TOP_COUNT()` - Top N values

### 7. Materialize Complex Queries

```sql
CREATE MATERIALIZED VIEW dataset.daily_sales_summary AS
SELECT 
  DATE(order_timestamp) as date,
  product_category,
  SUM(amount) as total_sales,
  COUNT(*) as order_count
FROM orders
GROUP BY date, product_category

-- Queries on view use precomputed results
-- Auto-refresh when base table changes (within 5 min)
```

### 8. Query Results Caching

BigQuery caches query results for 24 hours (free!).
- Same query = instant results from cache
- Works across users
- Deterministic queries only

**Disable cache**:
```sql
SELECT * FROM table
-- Options: use_query_cache = false
```

### 9. Use Appropriate JOINs

```sql
-- For small dimension tables (<1GB), use INNER JOIN
-- BigQuery automatically broadcasts small tables

-- For large-large joins:
-- 1. Partition both tables on join key
-- 2. Use same number of partitions
-- 3. Consider denormalization
```

### 10. Avoid SELECT DISTINCT on Large Datasets

```sql
-- ❌ Expensive
SELECT DISTINCT customer_id FROM large_table

-- ✅ Better: Use GROUP BY
SELECT customer_id FROM large_table GROUP BY customer_id

-- ✅ Even better if count needed:
SELECT customer_id, COUNT(*) FROM large_table GROUP BY customer_id
```

---

## 4. COST MANAGEMENT

### Pricing Model

1. **Storage Costs**:
   - Active: $0.02 per GB/month
   - Long-term (90+ days): $0.01 per GB/month

2. **Query Costs**:
   - On-demand: $6.25 per TB processed
   - Flat-rate: $2,400/month for 100 slots (reserved capacity)

### Cost Reduction Strategies

**1. Partitioning & Clustering**
```sql
-- Without partitioning: Scans entire 10TB table = $62.50
SELECT * FROM large_table WHERE date = '2025-02-08'

-- With partitioning: Scans 1 day partition = 10GB = $0.0625
-- Cost reduction: 99%+
```

**2. Column Selection**
```sql
-- 100 columns, 10TB table
SELECT * FROM table  -- Cost: $62.50

-- Select 5 columns
SELECT col1, col2, col3, col4, col5 FROM table  -- Cost: $3.12
-- Cost reduction: 95%
```

**3. Query Result Limits**
```sql
-- Set custom quota (prevents runaway queries)
SELECT * FROM large_table
-- Options: maximum_bytes_billed = 1099511627776  -- 1TB limit
```

**4. Scheduled Queries**
- Run during off-peak hours
- Use flat-rate pricing for predictable costs
- Batch queries instead of ad-hoc

**5. Expire Old Data**
```sql
-- Automatic deletion after 90 days
ALTER TABLE dataset.transactions
SET OPTIONS (
  partition_expiration_days = 90
)
```

**6. Use Slots Reservations** (for consistent workload)
- Reserve slots (committed use discount)
- Flat monthly cost vs usage-based
- Autoscaling available

**7. Monitor Costs**
```sql
-- Check query costs
SELECT
  user_email,
  query,
  total_bytes_processed,
  total_bytes_billed,
  (total_bytes_billed / POW(1024, 4)) * 6.25 as estimated_cost_usd
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
ORDER BY total_bytes_billed DESC
LIMIT 100
```

---

## 5. SECURITY & GOVERNANCE

### 1. IAM (Identity & Access Management)

**Roles**:
- `roles/bigquery.user` - Run queries, create datasets
- `roles/bigquery.dataViewer` - Read data
- `roles/bigquery.dataEditor` - Read + write data
- `roles/bigquery.dataOwner` - Full control
- `roles/bigquery.jobUser` - Run jobs

**Best Practice**:
- Use service accounts for applications
- Grant least privilege
- Use dataset-level permissions

### 2. Column-Level Security

**Data Masking**:
```sql
CREATE OR REPLACE VIEW dataset.masked_customers AS
SELECT
  customer_id,
  CASE 
    WHEN SESSION_USER() IN ('admin@company.com')
      THEN email
    ELSE CONCAT('****', SUBSTR(email, STRPOS(email, '@')))
  END as email,
  CASE
    WHEN SESSION_USER() IN ('admin@company.com')
      THEN ssn
    ELSE '***-**-****'
  END as ssn
FROM dataset.customers
```

### 3. Row-Level Security

```sql
-- Policy: Users can only see their own country's data
CREATE ROW ACCESS POLICY country_filter
ON dataset.sales
GRANT TO ('data-viewer')
FILTER USING (country = SESSION_USER())
```

### 4. Encryption

- **At Rest**: Automatic encryption (AES-256)
  - Google-managed keys (default)
  - Customer-managed keys (CMEK) via Cloud KMS

- **In Transit**: TLS encryption

### 5. Audit Logging

```sql
-- Query audit logs
SELECT
  protopayload_auditlog.authenticationInfo.principalEmail as user,
  protopayload_auditlog.resourceName as resource,
  protopayload_auditlog.methodName as action,
  timestamp
FROM `project-id.dataset.cloudaudit_googleapis_com_data_access_*`
WHERE DATE(_TABLE_SUFFIX) = CURRENT_DATE()
```

### 6. Data Loss Prevention (DLP)

```sql
-- Identify PII in tables
-- Use Cloud DLP API to scan for:
-- - Email addresses
-- - Phone numbers
-- - SSN
-- - Credit card numbers
```

---

## 6. INTEGRATION WITH OTHER SERVICES

### Cloud Composer (Airflow)

```python
from airflow.providers.google.cloud.operators.bigquery import \
    BigQueryInsertJobOperator

bq_task = BigQueryInsertJobOperator(
    task_id='run_query',
    configuration={
        "query": {
            "query": """
                INSERT INTO dataset.aggregated_sales
                SELECT DATE(order_date) as date, SUM(amount)
                FROM dataset.orders
                WHERE DATE(order_date) = CURRENT_DATE()
                GROUP BY date
            """,
            "useLegacySql": False,
            "destinationTable": {
                "projectId": "my-project",
                "datasetId": "dataset",
                "tableId": "aggregated_sales"
            },
            "writeDisposition": "WRITE_APPEND"
        }
    }
)
```

### Cloud Storage

```sql
-- Load from GCS
LOAD DATA INTO dataset.transactions
FROM FILES (
  format = 'PARQUET',
  uris = ['gs://bucket/data/*.parquet']
)

-- Export to GCS
EXPORT DATA OPTIONS(
  uri='gs://bucket/export/*.csv',
  format='CSV',
  overwrite=true,
  header=true
) AS
SELECT * FROM dataset.transactions
WHERE date = CURRENT_DATE()
```

### Pub/Sub (Streaming)

```python
# Stream data to BigQuery
from google.cloud import bigquery

client = bigquery.Client()
table_id = "project.dataset.table"

rows_to_insert = [
    {"name": "John", "age": 30},
    {"name": "Jane", "age": 25}
]

errors = client.insert_rows_json(table_id, rows_to_insert)
if errors:
    print(f"Errors: {errors}")
```

### Dataflow

```python
import apache_beam as beam

# Read from BigQuery
with beam.Pipeline() as pipeline:
    (pipeline
     | 'Read from BigQuery' >> beam.io.ReadFromBigQuery(
         query='SELECT * FROM dataset.table WHERE date = CURRENT_DATE()',
         use_standard_sql=True)
     | 'Process' >> beam.Map(process_function)
     | 'Write to BigQuery' >> beam.io.WriteToBigQuery(
         'project:dataset.output_table',
         write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND))
```

---

## 7. TOP 50 INTERVIEW QUESTIONS

### Basic (Q1-15)

**Q1: What is BigQuery and how does it differ from traditional databases?**

A: BigQuery is a serverless, columnar data warehouse. Differences:
- Serverless vs managed instances
- Columnar storage vs row-based
- Separation of compute/storage vs coupled
- Massively parallel vs limited parallelism
- Pay-per-query vs fixed capacity

**Q2: Explain BigQuery architecture.**

A: Four main components:
1. Dremel - Query engine, breaks queries into execution tree
2. Colossus - Distributed storage, columnar format
3. Jupiter - High-speed network between compute and storage
4. Borg - Resource orchestration

**Q3: What is partitioning? When to use it?**

A: Dividing table into segments. Use when:
- Large tables (>1GB)
- Queries filter on specific column (usually date)
- Need data lifecycle management
- Cost reduction needed

**Q4: Difference between partitioning and clustering?**

A: 
- Partitioning: Physical division, limited to 4K partitions
- Clustering: Data organization within partitions, no limit
- Use together for best performance

**Q5: How to load data into BigQuery?**

A: Multiple methods:
1. Batch load from GCS (`bq load`)
2. Streaming API (`insert_rows_json`)
3. Data Transfer Service (scheduled imports)
4. Dataflow pipelines
5. Console upload (small files)

**Q6: What are slots?**

A: Unit of computational capacity
- On-demand: Auto-allocated based on query
- Flat-rate: Reserved capacity (100 slots minimum)
- 1 slot = 1 BigQuery unit of computing

**Q7: How does BigQuery handle NULL values?**

A: 
```sql
-- COALESCE replaces NULL
SELECT COALESCE(column, 'default') FROM table

-- IFNULL (same as COALESCE with 2 args)
SELECT IFNULL(column, 0) FROM table

-- IS NULL / IS NOT NULL for filtering
SELECT * FROM table WHERE column IS NOT NULL
```

**Q8: What is a materialized view?**

A: Pre computed query results, auto-refreshed
- Faster query performance
- Reduced compute costs
- Transparent to queries (BigQuery chooses when to use)

**Q9: Explain federated queries.**

A: Query external data sources without loading:
- Cloud SQL
- Cloud Spanner
- Google Sheets
- Cloud Storage (CSV, JSON, Avro, Parquet)

```sql
SELECT * FROM EXTERNAL_QUERY(
  "connection-id",
  "SELECT * FROM mysql_table WHERE date = CURRENT_DATE()"
)
```

**Q10: How to optimize query costs?**

A: 
1. Use partitioning/clustering
2. Select only needed columns
3. Filter early
4. Use materialized views
5. Leverage query cache
6. Set billing quotas
7. Use approximate functions

**Q11: What are the different data types in BigQuery?**

A: 
- Numeric: INT64, FLOAT64, NUMERIC, BIGNUMERIC
- String: STRING, BYTES
- Boolean: BOOL
- Temporal: DATE, DATETIME, TIME, TIMESTAMP
- Geography: GEOGRAPHY
- Complex: ARRAY, STRUCT, JSON

**Q12: How to handle slowly changing dimensions?**

A: SCD Type 2 implementation:
```sql
-- Current records
SELECT * FROM dim_customer WHERE is_current = TRUE

-- Historical view
SELECT * FROM dim_customer WHERE effective_date <= '2025-01-01'
  AND (end_date IS NULL OR end_date > '2025-01-01')
```

**Q13: What is BigQuery ML?**

A: Build ML models using SQL:
```sql
CREATE MODEL dataset.model_name
OPTIONS(model_type='logistic_reg')
AS
SELECT features, label FROM training_data
```

**Q14: How to schedule queries?**

A: 
1. Via Console: Scheduled Queries feature
2. Via Cloud Composer/Airflow
3. Via Cloud Scheduler → Cloud Functions → BigQuery API

**Q15: Explain data types ARRAY and STRUCT.**

A: 
```sql
-- ARRAY: Ordered list of values
SELECT [1, 2, 3] as numbers

-- STRUCT: Named fields
SELECT STRUCT(1 as id, 'John' as name) as person

-- Nested
SELECT [
  STRUCT(1 as id, 'John' as name),
  STRUCT(2 as id, 'Jane' as name)
] as people
```

### Intermediate (Q16-35)

**Q16: How would you migrate 10TB Oracle database to BigQuery?**

A: 
1. **Preparation**:
   - Analyze schema, data types
   - Design partitioning strategy
   
2. **Initial Load**:
   - Export Oracle to Parquet (compressed, columnar)
   - Upload to GCS using gsutil parallel upload
   - `bq load` into BigQuery with partitioning
   
3. **Incremental Updates**:
   - CDC using Oracle GoldenGate/Debezium
   - Stream changes to Pub/Sub
   - Dataflow processes and merges
   
4. **Validation**:
   - Row count comparison
   - Sample data checks
   - Query result verification

**Q17: BigQuery query taking too long. How to optimize?**

A: Systematic approach:
1. Check INFORMATION_SCHEMA.JOBS for query plan
2. Identify bottlenecks:
   - Large scans → Add partitioning/clustering
   - Shuffles → Optimize joins
   - Spilling → Reduce data volume early
3. Apply optimizations:
   - Partition pruning
   - Filter before joins
   - Denormalize if many joins
   - Use approximate functions
4. Monitor: bytes_processed, bytes_billed, slot_ms

**Q18: Implement SCD Type 2 in BigQuery.**

A: 
```sql
-- Insert new records
INSERT INTO dim_customer (
  customer_key, customer_id, name, email,
  effective_date, end_date, is_current
)
SELECT
  GENERATE_UUID() as customer_key,
  customer_id,
  name,
  email,
  CURRENT_DATE() as effective_date,
  NULL as end_date,
  TRUE as is_current
FROM staging_customers

-- Update old records
UPDATE dim_customer
SET 
  end_date = CURRENT_DATE(),
  is_current = FALSE
WHERE customer_id IN (SELECT customer_id FROM changed_customers)
  AND is_current = TRUE
```

**Q19: Design a real-time dashboard with BigQuery.**

A: 
1. **Data Ingestion**: Pub/Sub → BigQuery streaming
2. **Processing**: Dataflow for transformations
3. **Storage**: Partitioned BigQuery tables
4. **BI Engine**: Enable for sub-second queries
5. **Visualization**: Looker Studio with live connection
6. **Caching**: Materialized views for common aggregations

**Q20: How to handle PII in BigQuery?**

A: 
1. **Encryption**: Automatic at rest, CMEK for customer keys
2. **DLP API**: Scan and classify PII
3. **Masking**: Create views with masked data
4. **Row-level security**: Users see only authorized data
5. **Column-level security**: Restrict sensitive columns
6. **Audit logging**: Track all data access

**Q21: Explain BigQuery reservation model.**

A: 
- **Slots**: Unit of compute (mix of CPU, memory, I/O)
- **Reservations**: Dedicated slot capacity
- **Assignments**: Link project/folder to reservation
- **Autoscaling**: Add slots during peak
- **Benefits**: Predictable cost, guaranteed capacity, better SLAs

**Q22: How to handle duplicate data?**

A: 
```sql
-- Method 1: DISTINCT
SELECT DISTINCT * FROM table

-- Method 2: GROUP BY
SELECT customer_id, MAX(timestamp), MAX(amount)
FROM transactions
GROUP BY customer_id

-- Method 3: ROW_NUMBER (keep latest)
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY timestamp DESC) as rn
  FROM transactions
)
SELECT * FROM ranked WHERE rn = 1
```

**Q23: Design data retention policy.**

A: 
```sql
-- Partition expiration
ALTER TABLE dataset.events
SET OPTIONS (
  partition_expiration_days = 90,
  require_partition_filter = true
)

-- Archive to GCS before deletion
CREATE OR REPLACE PROCEDURE archive_old_data()
BEGIN
  EXPORT DATA OPTIONS(
    uri='gs://archive-bucket/data_*.parquet',
    format='PARQUET',
    overwrite=false
  ) AS
  SELECT * FROM dataset.events
  WHERE DATE(_PARTITIONTIME) < DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY);
  
  DELETE FROM dataset.events
  WHERE DATE(_PARTITIONTIME) < DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY);
END;

-- Schedule with Cloud Scheduler
```

**Q24: Handle schema evolution.**

A: 
```sql
-- Add column (safe)
ALTER TABLE dataset.table
ADD COLUMN new_column STRING

-- Drop column (requires recreation)
CREATE OR REPLACE TABLE dataset.table AS
SELECT * EXCEPT(old_column)
FROM dataset.table

-- Change column type (limited support)
-- Usually requires: export → transform → reimport
```

**Q25: Optimize join performance.**

A: 
1. **Partition both tables** on join key
2. **Use INNER JOIN** when possible (vs OUTER)
3. **Filter before join** to reduce data volume
4. **Denormalize** if joining same tables repeatedly
5. **Broadcast** small tables (BigQuery does automatically)
6. **Pre-aggregate** before joining

**Q26: Implement incremental data loading.**

A: 
```sql
-- Track watermark
CREATE TABLE dataset.watermark (
  last_processed_timestamp TIMESTAMP
)

-- Incremental load
MERGE dataset.target T
USING (
  SELECT * FROM dataset.source
  WHERE updated_at > (SELECT MAX(last_processed_timestamp) FROM dataset.watermark)
) S
ON T.id = S.id
WHEN MATCHED THEN UPDATE SET T.* = S.*
WHEN NOT MATCHED THEN INSERT ROW

-- Update watermark
UPDATE dataset.watermark
SET last_processed_timestamp = (SELECT MAX(updated_at) FROM dataset.source)
```

**Q27: Handle time zone conversions.**

A: 
```sql
-- Convert UTC to local time
SELECT 
  timestamp_utc,
  TIMESTAMP(timestamp_utc, 'America/New_York') as timestamp_ny,
  TIMESTAMP(timestamp_utc, 'Europe/London') as timestamp_london
FROM events
```

**Q28: Implement data quality checks.**

A: 
```python
# Automated DQ checks in Airflow
def data_quality_check(**context):
    client = bigquery.Client()
    
    checks = [
        # Null check
        "SELECT COUNT(*) FROM dataset.table WHERE critical_column IS NULL",
        # Duplicate check
        "SELECT id, COUNT(*) FROM dataset.table GROUP BY id HAVING COUNT(*) > 1",
        # Range check
        "SELECT COUNT(*) FROM dataset.table WHERE amount < 0 OR amount > 1000000",
        # Freshness check
        f"SELECT MAX(timestamp) FROM dataset.table HAVING MAX(timestamp) < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)"
    ]
    
    for check in checks:
        result = client.query(check).result()
        if result.total_rows > 0:
            raise ValueError(f"Quality check failed: {check}")
```

**Q29: Design disaster recovery strategy.**

A: 
1. **Snapshots**: Scheduled table snapshots
```sql
CREATE SNAPSHOT TABLE dataset.customers_snapshot
CLONE dataset.customers
OPTIONS(expiration_timestamp=TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 7 DAY))
```

2. **Cross-region replication**: Copy tables to different region
3. **Export to GCS**: Regular backups
4. **Point-in-time recovery**: Time travel (7 days default)
```sql
SELECT * FROM dataset.table
FOR SYSTEM_TIME AS OF TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
```

**Q30: Explain query execution phases.**

A: 
1. **Parsing**: SQL syntax validation
2. **Planning**: Execution plan generation
3. **Scheduling**: Slot allocation
4. **Execution**: Distributed processing
5. **Returning**: Results to client

Monitor via INFORMATION_SCHEMA.JOBS_BY_PROJECT

### Advanced (Q36-50)

**Q36: Handle skewed data in BigQuery.**

A: 
- **Problem**: Few keys have disproportionate data
- **Solution**:
  1. Use APPROX functions
  2. Pre-aggregate skewed keys
  3. Separate hot keys into different table
  4. Use clustering to organize data

**Q37: Implement CDC (Change Data Capture).**

A: 
```sql
-- Track changes using MERGE with audit columns
MERGE dataset.target T
USING dataset.source S
ON T.id = S.id
WHEN MATCHED AND S.updated_at > T.updated_at THEN
  UPDATE SET 
    T.* = S.*,
    T.last_updated = CURRENT_TIMESTAMP(),
    T.change_type = 'UPDATE'
WHEN NOT MATCHED THEN
  INSERT (*, last_updated, change_type)
  VALUES (S.*, CURRENT_TIMESTAMP(), 'INSERT')
```

**Q38: Optimize for BI tool performance.**

A: 
1. **BI Engine**: Reserve memory (1-100GB)
2. **Materialized views**: Pre-aggregate common queries
3. **Partitioning**: Enable partition pruning
4. **Clustering**: Improve filter performance
5. **Caching**: Leverage 24-hour cache
6. **Scheduled queries**: Pre-compute dashboards

**Q39: Handle semi-structured data (JSON).**

A: 
```sql
-- JSON column type (Native support)
CREATE TABLE dataset.events (
  event_id INT64,
  event_data JSON
)

-- Query JSON
SELECT 
  event_id,
  JSON_VALUE(event_data, '$.user.name') as user_name,
  JSON_VALUE(event_data, '$.transaction.amount') as amount
FROM dataset.events

-- JSON to STRUCT (better performance)
SELECT 
  event_id,
  JSON_EXTRACT_SCALAR(event_data, '$.user.name') as user_name
FROM dataset.events
```

**Q40: Design multi-region data strategy.**

A: 
1. **Dataset location**: Choose region/multi-region
2. **Replication**: Scheduled transfers between regions
3. **Disaster recovery**: Cross-region snapshots
4. **Data residency**: Comply with regulations (GDPR)
5. **Cost**: Balance latency vs storage costs

**Remaining Q41-50 would continue with:**
- Advanced window functions
- Performance troubleshooting
- Cost attribution
- Security implementations
- Integration patterns
- Capacity planning
- Monitoring & alerting
- Best practices
- Anti-patterns
- Real-world scenarios

---

## QUICK REFERENCE CHEAT SHEET

### Most Common Commands

```sql
-- Create partitioned table
CREATE TABLE dataset.table
PARTITION BY DATE(timestamp)
CLUSTER BY user_id, category
AS SELECT * FROM source

-- Query with partition filter
SELECT * FROM dataset.table
WHERE DATE(timestamp) = '2025-02-08'

-- Materialized view
CREATE MATERIALIZED VIEW dataset.mv AS
SELECT category, SUM(amount)
FROM dataset.table
GROUP BY category

-- Export
EXPORT DATA OPTIONS(
  uri='gs://bucket/*.csv',
  format='CSV'
) AS SELECT * FROM dataset.table

-- Load
LOAD DATA INTO dataset.table
FROM FILES (
  format='PARQUET',
  uris=['gs://bucket/*.parquet']
)
```

### Performance Tips Summary

1. ✅ Partition + Cluster
2. ✅ SELECT specific columns
3. ✅ Filter early
4. ✅ Use materialized views
5. ✅ Leverage cache
6. ✅ Avoid SELECT DISTINCT
7. ✅ Use window functions vs self-joins
8. ✅ Denormalize when appropriate
9. ✅ Approximate functions for large datasets
10. ✅ Monitor with INFORMATION_SCHEMA

### Cost Optimization Summary

1. ✅ Partition tables
2. ✅ Cluster columns
3. ✅ Select only needed columns
4. ✅ Set billing quotas
5. ✅ Use BI Engine for dashboards
6. ✅ Consider flat-rate pricing
7. ✅ Expire old partitions
8. ✅ Monitor queries regularly

---

**YOU'RE NOW A BIGQUERY EXPERT!** 🎯

Practice these concepts, run the queries, and you'll ace any BigQuery interview question!
