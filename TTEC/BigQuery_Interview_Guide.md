# BigQuery Complete Interview Guide

## Quick Start: Most Important Concepts

### 1. Partition Pruning (80% of optimization)
```sql
-- GOOD: Scans only needed partitions
SELECT * FROM table WHERE event_date >= CURRENT_DATE() - 30

-- BAD: Scans all partitions (function breaks pruning)
SELECT * FROM table WHERE EXTRACT(YEAR FROM event_date) = 2024
```

### 2. Clustering (Additional 10-50x optimization)
```sql
CREATE TABLE events
PARTITION BY DATE(event_date)
CLUSTER BY user_id, event_type
AS SELECT * FROM source;
```

### 3. Select Specific Columns (10-90% reduction)
```sql
-- GOOD: 100MB scanned
SELECT user_id, name, email FROM users

-- BAD: 2GB scanned
SELECT * FROM users
```

## Key Optimization Techniques

### Partition Pruning Example
```sql
-- Problem: Table is partitioned by event_date
-- Query scans all 1TB of data

-- Solution: Add date filter
SELECT * FROM events
WHERE event_date >= '2024-02-01' 
AND event_date < '2024-03-01'
-- Scans: 1TB → 50GB (50x improvement!)
```

### Clustering Strategy
```sql
-- Create clustered table
CREATE TABLE transactions
PARTITION BY DATE(trans_date)
CLUSTER BY user_id, merchant_id
AS SELECT * FROM source;

-- Query benefits from clustering
SELECT * FROM transactions
WHERE trans_date = '2024-03-15'
AND user_id = 123
AND merchant_id = 456;
-- Scan: 100GB → 1GB (100x improvement!)
```

### Cost Reduction Examples

**Example 1: Simple Partition Filter**
- Original: 500GB × $6.25/TB = $3.125
- Optimized: 50GB × $6.25/TB = $0.3125
- Savings: 90% reduction

**Example 2: Full Optimization (Partition + Cluster + Columns)**
- Original: 500GB scan = $3.125
- Partition filter: 500GB → 50GB = $0.3125
- Clustering: 50GB → 5GB = $0.031
- Column selection: 5GB → 0.5GB = $0.003
- Total: 1000x improvement!

## Data Modeling

### Star Schema Pattern
```sql
-- Fact Table
CREATE TABLE fact_orders
PARTITION BY DATE(order_date)
CLUSTER BY user_id, product_id
AS SELECT order_id, user_id, product_id, order_amount FROM source;

-- Dimension Tables
CREATE TABLE dim_users AS SELECT user_id, name, country FROM source_users;
CREATE TABLE dim_products AS SELECT product_id, name, category FROM source_products;

-- Query
SELECT d.category, COUNT(*) as orders, SUM(f.order_amount) as revenue
FROM fact_orders f
JOIN dim_products d ON f.product_id = d.product_id
WHERE f.order_date >= CURRENT_DATE() - 90
GROUP BY d.category;
```

### Slowly Changing Dimensions

**Type 1: Overwrite (No History)**
```sql
MERGE users T
USING staging S
ON T.user_id = S.user_id
WHEN MATCHED THEN UPDATE SET name = S.name
WHEN NOT MATCHED THEN INSERT VALUES (S.user_id, S.name);
```

**Type 2: Add Row with Dates (Full History)**
```sql
MERGE users T
USING staging S
ON T.user_id = S.user_id AND T.is_current = TRUE
WHEN MATCHED AND T.name != S.name THEN UPDATE SET is_current = FALSE, end_date = CURRENT_DATE()
WHEN NOT MATCHED THEN INSERT (user_id, name, start_date, is_current) 
  VALUES (S.user_id, S.name, CURRENT_DATE(), TRUE);
```

## Real Interview Q&A

### Q: Optimize a 1-hour query that scans 500GB
**Answer:**
1. Add partition filter: 500GB → 50GB (10x)
2. Add clustering filter: 50GB → 5GB (10x)
3. Select specific columns: 5GB → 0.5GB (10x)
4. Result: 100x improvement, <10 second latency, $0.003 cost

### Q: Design a fact table for 1 trillion rows
**Answer:**
```sql
CREATE TABLE fact_transactions
PARTITION BY DATE(transaction_date)
CLUSTER BY user_id, merchant_id
AS SELECT transaction_id, user_id, merchant_id, amount, transaction_date FROM source;
```
- Key: Partition by DATE (daily), not timestamp (hourly)
- Cluster on high-cardinality columns
- Implement retention: 90d hot, 365d warm, archive cold
- Use materialized views for common aggregations

### Q: Fix duplicate records showing 2x revenue
**Answer:**
```sql
CREATE OR REPLACE TABLE orders AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY _PARTITIONTIME DESC) as rn
  FROM orders
)
SELECT * EXCEPT(rn) FROM deduped WHERE rn = 1;
```

## Advanced Concepts

### Window Functions
```sql
-- Running total
SUM(amount) OVER (PARTITION BY user_id ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)

-- Previous value
LAG(amount) OVER (PARTITION BY user_id ORDER BY date)

-- Ranking
ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY amount DESC)
RANK() OVER (...)  -- Ties get same rank
DENSE_RANK() OVER (...)  -- Dense ranking without gaps
```

### Nested Data
```sql
-- Keep JSON structure (avoid joins)
[STRUCT('apple' as item, 1.50 as price), STRUCT('banana' as item, 0.75 as price)] as line_items

-- Query with UNNEST
SELECT order_id, item.item, item.price FROM orders CROSS JOIN UNNEST(line_items) as item;
```

## Pricing & Cost

**Query Cost:** $6.25 per TB scanned
- 100GB = 0.1 TB = $0.625
- 1TB = $6.25
- Cache hits are FREE (24-hour cache)

**Storage Cost:**
- Active: $0.02/GB/month
- Long-term (>90d): $0.01/GB/month

**Cost Optimization:**
1. Partition pruning (80% savings)
2. Clustering (10x more savings)
3. Column selection (5-10x more)
4. Materialized views (cache expensive queries)
5. Set table expiration (auto-delete old data)

## Interview Preparation Checklist

Before optimizing any query:
- [ ] Run EXPLAIN to see execution plan
- [ ] Check partition pruning
- [ ] Verify clustering usage
- [ ] Select specific columns
- [ ] No functions on partition columns
- [ ] Filter before JOINs
- [ ] Consider materialized views

Red flags:
- [ ] SELECT * (never!)
- [ ] Function on partition column (breaks pruning)
- [ ] Multiple JOINs without filtering
- [ ] No LIMIT on exploration queries

## Most Critical Interview Facts

1. **Partition pruning saves 90-99% cost** - Always add date filter first
2. **Clustering gives 10-100x improvement** - For high-cardinality columns
3. **Column selection matters** - SELECT specific columns, never *
4. **Queries are cached 24 hours** - Same query = FREE second time
5. **MERGE is idempotent** - Safe to run multiple times
6. **Window functions are powerful** - LAG, LEAD, ROW_NUMBER for complex logic
7. **Materialized views cache results** - Pre-aggregate for dashboards
8. **Star schema is standard** - Fact tables + Dimension tables
9. **SCD Type 2 tracks history** - For dimension changes
10. **Monitor costs** - Query > 1TB should raise alarms

Good luck with your interview! 🚀
