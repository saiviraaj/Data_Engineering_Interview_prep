# Mock Interview - 90 Minutes (Non-FAANG Level)

Complete practice interview simulation.

---

## Interview Setup

**Time:** 90 minutes  
**Format:** Technical + Behavioral  
**Position:** Senior Data Engineer  
**Company:** Mid-size tech company

---

# ROUND 1: Data Engineering Question (40 minutes)

## Problem: Design Email Marketing Data Pipeline

**Interviewer:** "We need to build a data pipeline for email marketing. We send 10 million emails daily to customers. We need to track opens, clicks, bounces, unsubscribes. Design the system."

### What the interviewer wants to see:

1. Clarifying questions (5 min)
2. High-level architecture (10 min)
3. Deep dive on components (20 min)
4. Handling edge cases (5 min)

---

### STEP 1: Clarify Requirements (5 minutes)

**Good candidate asks:**

- "What's the volume we're expecting? 10M daily - any spikes?"
- "What's the expected latency? Real-time or batch?"
- "What's the storage requirement? How long to keep data?"
- "What are the failure modes we care about?"
- "Who are the consumers? Marketing team? Data team?"

**Interviewer answers:**
- 10M emails daily, steady
- Real-time updates preferred (< 5 seconds)
- Keep 2 years of historical data
- Occasionally need to backfill
- Marketing team via dashboards + Data team for analytics

---

### STEP 2: High-Level Architecture (10 minutes)

**Candidate sketches:**

```
Email Campaign → Send Service → Event Queue
                                    ↓
                            Stream Processor
                                    ↓
                            Data Warehouse
                                    ↓
                        Dashboard / Analytics
```

**Detailed design:**

```
1. Campaign Service
   - User creates email campaign
   - Stores in database
   - Triggers scheduler

2. Send Service
   - Reads user segment
   - Sends emails via provider (SendGrid, etc)
   - Records in event log

3. Event Collection
   - Email open event
   - Link click event
   - Bounce/unsubscribe event
   - Sent via webhook to Kafka

4. Stream Processing
   - Real-time aggregation
   - Deduplication
   - Enrichment (user data)

5. Storage
   - Raw events in BigQuery
   - Aggregated metrics in Redis
   - Summary tables for dashboards

6. Consumption
   - Marketing dashboards
   - Analytics for DS team
```

---

### STEP 3: Deep Dive - Implementation (20 minutes)

#### Data Model

```sql
-- Events table (partitioned by date)
CREATE TABLE email_events (
    event_id STRING,
    campaign_id STRING,
    user_id STRING,
    email_address STRING,
    event_type STRING,  -- 'send', 'open', 'click', 'bounce', 'unsubscribe'
    event_timestamp TIMESTAMP,
    metadata JSON
)
PARTITION BY DATE(event_timestamp)
CLUSTER BY campaign_id, user_id;

-- Campaign metrics (aggregated)
CREATE TABLE campaign_metrics (
    campaign_id STRING,
    metric_date DATE,
    emails_sent INT64,
    emails_opened INT64,
    emails_bounced INT64,
    unique_clickers INT64,
    open_rate FLOAT64,
    click_rate FLOAT64,
    bounce_rate FLOAT64
);
```

#### Event Processing

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import *

spark = SparkSession.builder.appName("EmailEvents").getOrCreate()

# Read from Kafka
events_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "email-events") \
    .load()

# Parse JSON
parsed_events = events_df.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")

# Deduplication (exactly-once semantics)
deduplicated = parsed_events \
    .dropDuplicates(["event_id"]) \
    .withWatermark("event_timestamp", "1 minute")

# Aggregations
metrics = deduplicated.groupBy(
    window(col("event_timestamp"), "1 minute"),
    col("campaign_id")
).agg(
    count(when(col("event_type") == "send", 1)).alias("sent_count"),
    count(when(col("event_type") == "open", 1)).alias("open_count"),
    count(when(col("event_type") == "click", 1)).alias("click_count"),
    count(when(col("event_type") == "bounce", 1)).alias("bounce_count")
)

# Write to BigQuery
metrics.writeStream \
    .format("bigquery") \
    .option("table", "dataset.campaign_metrics") \
    .option("checkpointLocation", "/checkpoints/email") \
    .start()
```

#### Handling Edge Cases

**Q: What about duplicate events?**
"We use event_id for deduplication. If the same event arrives twice, we keep only first occurrence using Spark's dropDuplicates()."

**Q: What if events arrive out of order?**
"We use watermark of 1 minute. Events older than watermark are dropped. This handles clock skew and network delays."

**Q: What about backfills?**
"For historical data, we have batch job that:
1. Reads from event archive
2. Reprocesses with same logic
3. Updates metrics table with 'overwrite' mode
4. Notifies consumers of update"

---

### STEP 4: Wrap Up (5 minutes)

**Candidate summarizes:**

"To summarize:
1. Events flow through Kafka
2. Stream processor deduplicates and aggregates
3. Data written to BigQuery in real-time
4. Marketing dashboards query aggregated metrics
5. Data team has raw events for deep analysis

**Key design decisions:**
- Kafka for fault tolerance
- Spark Streaming for flexible processing
- BigQuery for analytics scale
- Redis cache for hot metrics
- Deduplication for exactly-once semantics"

**What you'd do next:**
"In implementation, I'd:
1. Set up comprehensive monitoring
2. Create data quality checks
3. Document schema changes process
4. Set up disaster recovery
5. Performance test with realistic load"

---

# ROUND 2: Coding Problem (30 minutes)

## Problem: Top N Items by Revenue

**LeetCode style Medium problem**

### Problem Statement

Given a sales table with columns: [product_id, revenue, date], find the top 3 products by total revenue for each month.

```
Input:
product_id | revenue | date
1          | 100     | 2024-01-05
1          | 150     | 2024-01-10
2          | 200     | 2024-01-15
1          | 120     | 2024-02-05
2          | 180     | 2024-02-10

Output:
month      | product_id | total_revenue | rank
2024-01    | 2          | 200           | 1
2024-01    | 1          | 250           | 2
2024-02    | 2          | 180           | 1
2024-02    | 1          | 120           | 2
```

### Approach

**Time: 5 min - Think**
- Use window functions for ranking
- Need to partition by month
- Need to rank within each month
- Filter for top 3

**Time: 15 min - Code**

```sql
SELECT 
    DATE_TRUNC(date, MONTH) AS month,
    product_id,
    SUM(revenue) AS total_revenue,
    ROW_NUMBER() OVER (
        PARTITION BY DATE_TRUNC(date, MONTH)
        ORDER BY SUM(revenue) DESC
    ) AS rank
FROM sales
GROUP BY DATE_TRUNC(date, MONTH), product_id
HAVING ROW_NUMBER() OVER (
    PARTITION BY DATE_TRUNC(date, MONTH)
    ORDER BY SUM(revenue) DESC
) <= 3
ORDER BY month, rank;
```

**Wait - issue with HAVING on window function!**

**Correct solution with CTE:**

```sql
WITH monthly_revenue AS (
    SELECT 
        DATE_TRUNC(date, MONTH) AS month,
        product_id,
        SUM(revenue) AS total_revenue,
        ROW_NUMBER() OVER (
            PARTITION BY DATE_TRUNC(date, MONTH)
            ORDER BY SUM(revenue) DESC
        ) AS rank
    FROM sales
    GROUP BY DATE_TRUNC(date, MONTH), product_id
)
SELECT *
FROM monthly_revenue
WHERE rank <= 3
ORDER BY month, rank;
```

**Time: 5 min - Verify & Optimize**

"Let me verify with the sample data:
- Jan 2024: Product 2 ($200), Product 1 ($250) ✓
- Feb 2024: Product 2 ($180), Product 1 ($120) ✓

Complexity: O(n log n) due to sorting for window function. Could optimize with streaming if data is huge, but for typical analytics this is good."

---

# ROUND 3: Behavioral Question (20 minutes)

## Question: "Tell me about a complex data problem you solved"

### STAR Answer Structure

**Situation (3 min):**
"At my current company, we were running a large-scale data migration from on-premise Teradata to Google BigQuery. We had 500+ tables, 40PB of data, and needed to minimize downtime while maintaining data integrity. I was responsible for the technical architecture."

**Task (2 min):**
"The challenge was not just moving data, but ensuring:
1. Zero data loss
2. Minimal impact on 60+ downstream consumers
3. Ability to rollback if needed
4. Running parallel systems during migration
5. Validation at every step"

**Action (12 min):**
"I designed and implemented a three-phase approach:

**Phase 1: Full Copy (Weeks 1-2)**
- Extracted full data from Teradata
- Transformed and loaded to BigQuery
- Validation: row counts, column types, sample data checks
- Result: 400/500 tables validated

**Phase 2: Incremental Sync (Weeks 2-4)**
- Used CDC (Change Data Capture) for ongoing changes
- Ran parallel reads from both systems
- Compared results for consistency
- Identified 2 schema mismatches (fixed in ETL)

**Phase 3: Cutover**
- Switched traffic to BigQuery
- Kept Teradata online for 2 weeks as rollback plan
- Monitored real user queries for performance
- Found 5 queries that needed optimization

**Key technical decisions:**
- Used Apache Airflow for orchestration
- Implemented data quality checks at each stage
- Created monitoring dashboard for stakeholders
- Automated rollback procedures
- Documented every transformation"

**Result (2 min):**
"Successfully migrated 40PB with:
- 99.99% data accuracy
- Zero downtime to users
- 60% cost savings on compute
- Improved query performance (5x faster on some queries)
- Completed 2 weeks ahead of schedule"

**Learning (1 min):**
"Key lessons:
- Importance of testing at scale
- Communication with stakeholders crucial
- Over-engineer safety mechanisms
- Documentation enables troubleshooting
- Small bugs can compound at scale"

### Interviewer Follow-ups (likely questions)

**Q: "How did you handle schema mismatches?"**
"Found them during validation phase. Updated ETL transformations to handle both formats during parallel run period. This gave time to fix source systems without rushed migration."

**Q: "What if something went wrong during cutover?"**
"We kept Teradata running for 2 weeks. Any critical issues could be reverted. Also had automated rollback scripts that would redirect traffic back if needed."

**Q: "How did you measure success?"**
"Tracked: data accuracy %, query latency improvement, cost savings, number of successful queries on day 1, stakeholder satisfaction."

---

## Interview Tips Summary

✅ **For Data Engineering Questions:**
- Ask clarifying questions first
- Start simple, add complexity
- Discuss trade-offs
- Show you think about edge cases

✅ **For Coding:**
- Write correct solution first
- Test with examples
- Optimize only if time
- Explain trade-offs

✅ **For Behavioral:**
- Use STAR method
- Include specific numbers
- Show growth mindset
- Discuss what you learned

---

