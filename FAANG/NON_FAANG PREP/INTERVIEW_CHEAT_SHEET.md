# GCP Data Engineer Interview: Quick Reference

## 🎯 Top 10 Interview Facts

1. **Partition Pruning** = 90-99% cost savings (always add date filter)
2. **Clustering** = 10-100x scan reduction (on high-cardinality columns)
3. **SELECT Columns** = 50-90% improvement (never SELECT *)
4. **Cache Hits** = FREE for 24 hours (same query)
5. **MERGE** = Idempotent (safe to run multiple times)
6. **Window Functions** > Self-Joins (better performance)
7. **Star Schema** = Standard data model (fact + dimension tables)
8. **SCD Type 2** = Tracks dimension history (with dates)
9. **Dataflow** > Spark (for streaming)
10. **Real-time < 5min latency** requires streaming architecture

---

## Query Optimization Checklist

### Before submitting ANY query:
```
☐ Run EXPLAIN to check execution plan
☐ Partition pruning happening? (WHERE on partition column)
☐ Clustering being used? (WHERE on cluster keys)
☐ Selecting specific columns? (not SELECT *)
☐ No functions on partition column? (breaks pruning)
☐ Filtering before JOINs? (reduce join input)
☐ Necessary JOINs? (can denormalize instead)
☐ Can use APPROX function? (faster estimate)
☐ Is result set small? (add LIMIT for exploration)
☐ Could this be materialized view? (cache expensive query)
```

---

## Most Important SQL Patterns

### Window Functions
```sql
-- Ranking
ROW_NUMBER() OVER (PARTITION BY col ORDER BY col)  -- Always unique
RANK() OVER (...)                                   -- Ties get same
DENSE_RANK() OVER (...)                            -- Dense ranking

-- Offset
LAG(col) OVER (PARTITION BY col ORDER BY col)     -- Previous
LEAD(col) OVER (...)                               -- Next

-- Aggregates
SUM(col) OVER (... ROWS BETWEEN ...)               -- Running total
AVG(col) OVER (...)                                -- Moving average

-- Distribution
PERCENT_RANK() OVER (...)                          -- Percentile
CUME_DIST() OVER (...)                             -- Cumulative %
NTILE(4) OVER (...)                                -- Quartiles
```

### Deduplication
```sql
CREATE OR REPLACE TABLE table AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY id ORDER BY ts DESC) as rn
  FROM table
)
SELECT * EXCEPT(rn) FROM deduped WHERE rn = 1;
```

### Aggregation
```sql
SELECT 
  user_id,
  COUNT(*) as total,
  COUNTIF(event_type = 'purchase') as purchases,
  SUM(amount) as total_amount,
  AVG(amount) as avg_amount
FROM events
GROUP BY user_id;
```

---

## Data Modeling Patterns

### Star Schema
```
Fact Table: One row per transaction
- Foreign keys to dimensions
- Measures (aggregatable values)

Dimension Tables: Descriptive data
- Primary key
- Attributes
- Slowly changing attributes
```

### Slowly Changing Dimensions
```
Type 1 (Overwrite): No history
- Simple MERGE, update in place

Type 2 (Add Row): Full history
- Add start_date, end_date, is_current
- Query latest: WHERE is_current = TRUE

Type 3 (Add Column): Limited history
- Keep current_value, previous_value
- Only need previous value
```

---

## Partition & Clustering Strategy

### Partitioning
```sql
-- Good: DATE (daily partition)
PARTITION BY DATE(event_date)

-- Avoid: TIMESTAMP (creates too many partitions)
PARTITION BY TIMESTAMP(event_timestamp)  -- Don't!

-- Range: For ID-based sharding
PARTITION BY RANGE_BUCKET(user_id, GENERATE_ARRAY(0, 1M, 10K))
```

### Clustering
```sql
-- Good: High-cardinality filtered columns
CLUSTER BY user_id, product_id, event_type

-- Avoid: Unique columns (no benefit)
CLUSTER BY user_id_uuid  -- Don't!

-- Order: Frequently filtered first, low-cardinality last
```

---

## Pricing & Cost Quick Facts

```
Query: $6.25/TB scanned (minimum 1MB = $0.000001)
Storage (active): $0.02/GB/month
Storage (long-term, >90d): $0.01/GB/month

Cost reduction ranking:
1. Partition pruning: 90-99% savings
2. Clustering: 10-100x improvement
3. Column selection: 50-90% improvement
4. Materialized views: Cache expensive queries
5. Set expiration: Auto-delete old data

Example: 100GB query
- Original: $0.625
- With partition: $0.0625 (90% savings)
- With clustering: $0.00625 (900x total!)
- With columns: $0.000625 (1000x total!)
```

---

## Data Pipeline Quick Facts

### Batch vs Streaming
```
Batch:
- Cost: Low ($0/query if using slots)
- Latency: Hours/days
- Complexity: Simple
- Use: Historical analysis, data warehouse

Streaming:
- Cost: High ($6.25/TB streamed)
- Latency: Seconds
- Complexity: Complex
- Use: Real-time dashboards, alerts

Hybrid:
- Streaming for real-time (last 1-24h)
- Batch for history (older data)
- Best practice for dashboards
```

### GCP Services
```
Pub/Sub: Event queue
Dataflow: Stream/batch processing (Beam)
Dataproc: Hadoop/Spark clusters
Cloud Composer: Orchestration (Airflow)
Cloud Storage: Data lake
BigQuery: Data warehouse
Datastream: Change data capture (CDC)
```

---

## System Design Interview Framework

### Step 1: Clarify
- Data volume? (GB, TB, PB?)
- Throughput? (events/sec?)
- Latency requirement? (real-time? batch?)
- Consistency? (strong? eventual?)
- Cost budget?

### Step 2: High-Level
- Data sources
- Ingestion
- Processing
- Storage
- Serving

### Step 3: Technology Choices
- Why BigQuery? (for SQL queries, OLAP, managed)
- Why Dataflow? (for streaming, auto-scale, Beam)
- Why Dataproc? (for Spark, Python, complex)
- Why Cloud Composer? (for orchestration, Airflow)

### Step 4: Handle Edge Cases
- Failures: Retries, DLQ, idempotency
- Late data: Window grace period, re-trigger
- Duplicates: MERGE, deduplication
- Data quality: Validation, testing, monitoring

### Step 5: Discuss Trade-offs
- Cost vs Latency
- Consistency vs Availability
- Complexity vs Maintainability
- Strong vs Eventual consistency

---

## Red Flags to Avoid

❌ SELECT * (always!)
❌ Function on partition column (breaks pruning)
❌ No error handling
❌ Ignoring data quality
❌ Single point of failure
❌ No monitoring/alerting
❌ Picks complex solution when simple works
❌ Forgets about security/compliance
❌ Can't explain trade-offs
❌ No cost analysis

---

## Interview Q&A One-Liners

**Q: Optimize slow query**
A: "Add partition filter, clustering, select specific columns"

**Q: Design billion-row table**
A: "Partition by DATE, cluster by (user_id, product_id), set retention policy"

**Q: Handle data quality**
A: "Implement validation in pipeline, log to DLQ, alert on anomalies"

**Q: Real-time vs batch**
A: "Streaming for <5min latency, batch for cost, hybrid for dashboards"

**Q: 1 trillion row fact table**
A: "Partition daily, cluster on filtered columns, materialized views for aggs"

**Q: Deduplicate 1B rows**
A: "Use ROW_NUMBER() window function, keep rn=1, 10x faster than DISTINCT"

**Q: Handle late-arriving data**
A: "Allow grace period in window, re-trigger on updates, MERGE for idempotency"

**Q: Data warehouse cost**
A: "Partition + cluster = 100x cost reduction, set retention policies"

---

## Last-Hour Review

If you have 60 minutes:
- Read this cheat sheet (15 min)
- Review your project stories (15 min)
- Practice 2-3 SQL queries (20 min)
- Relax and breathe (10 min)

If you have 30 minutes:
- Skim this cheat sheet (10 min)
- Review project stories (10 min)
- Breathe (10 min)

If you have 10 minutes:
- Read top 10 facts above
- Deep breath
- Walk in confident!

---

## Your Unique Strengths

✅ 10+ years data engineering experience
✅ Led 40PB Teradata→BigQuery migration
✅ Experience with enterprise-scale pipelines
✅ Familiar with data governance & security
✅ Proven track record (CDM Next, 60+ teams)

Use these in interview! Tell your migration story:
- "I owned end-to-end Teradata migration..."
- "Designed schema transformation for 40PB..."
- "Optimized Dataflow jobs for performance..."
- "Enabled 60+ teams to migrate with framework..."

---

**Good luck! 🚀**

You've got this. You're already qualified. Interview is just a conversation about data engineering.

Be confident, explain your thinking, discuss trade-offs, and you'll nail it.

