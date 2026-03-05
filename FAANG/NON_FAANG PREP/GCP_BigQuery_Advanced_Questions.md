# GCP & BigQuery Interview Questions

Complete BigQuery and GCP data platform interview prep.

---

## BigQuery Optimization (1-20)

### Q1: Partition Strategy

```sql
-- Time-based partition (most common for data lakes)
CREATE TABLE events (
    event_id STRING,
    event_timestamp TIMESTAMP,
    user_id STRING,
    amount FLOAT64
)
PARTITION BY DATE(event_timestamp)
CLUSTER BY user_id;

-- Partition benefits:
-- - Prunes partitions in WHERE clause
-- - 90%+ cost savings with filters
-- - Automatic TTL with REQUIRE_PARTITION_FILTER

-- Query example (scans only 1 day of data):
SELECT COUNT(*) FROM events
WHERE event_timestamp >= '2024-03-01' 
  AND event_timestamp < '2024-03-02';
```

### Q2: Clustering Impact

```sql
-- Without clustering
SELECT * FROM events
WHERE user_id = '12345'
-- Scans entire table

-- With clustering
CREATE TABLE events (
    event_id STRING,
    event_timestamp TIMESTAMP,
    user_id STRING,
    amount FLOAT64
)
PARTITION BY DATE(event_timestamp)
CLUSTER BY user_id, category;

-- Query now scans only blocks with user_id='12345'
-- 10-100x scan reduction
```

### Q3: Cost Optimization

```sql
-- 1. Use approximate aggregates when possible
SELECT APPROX_COUNT_DISTINCT(user_id)  -- ~100x faster
FROM events;

-- 2. Sample data for exploration
SELECT *
FROM events
WHERE RAND() < 0.01  -- 1% sample

-- 3. Use materialized views for common queries
CREATE MATERIALIZED VIEW daily_summary AS
SELECT DATE(event_timestamp) as date,
       user_id,
       COUNT(*) as events,
       SUM(amount) as total
FROM events
GROUP BY date, user_id;

-- 4. Column selection matters
SELECT user_id, amount  -- Only needed columns
FROM events

-- 5. Avoid SELECT * in production
```

### Q4: Query Optimization

```sql
-- Slow: Multiple scans
SELECT a.user_id, b.order_count
FROM users a
LEFT JOIN (
    SELECT user_id, COUNT(*) as order_count
    FROM orders
    GROUP BY user_id
) b ON a.user_id = b.user_id
WHERE a.status = 'active';

-- Fast: Join before group
SELECT a.user_id, COUNT(b.order_id) as order_count
FROM users a
LEFT JOIN orders b ON a.user_id = b.user_id
WHERE a.status = 'active'
GROUP BY a.user_id;
```

### Q5: Streaming Inserts Best Practices

```python
# Best: Batch inserts (not single row)
def stream_data_efficient():
    rows = []
    for i in range(100):
        rows.append({
            'event_id': str(uuid.uuid4()),
            'timestamp': datetime.now(),
            'value': random.random()
        })
    
    # Insert batch
    errors = client.insert_rows_json(
        table_id,
        rows,
        skip_invalid_rows=True
    )

# Cost: Each insert_rows() call costs ~$0.06 for 10K rows
# So batch 1000 rows per call: $0.00006 per row
```

### Q6-20: Additional Topics
**6. Time Travel / Table Snapshots**
**7. Federated Queries**
**8. BI Engine**
**9. Query Result Caching**
**10. Scheduled Queries**
**11. Data Transfer Service**
**12. Dataflow Integration**
**13. RI and Capacity Planning**
**14. IAM and Row-Level Security**
**15. Data Residency**
**16. Disaster Recovery**
**17. CTAS Performance**
**18. DML Performance**
**19. Temporary vs Permanent Tables**
**20. Table Expiration**

---

## GCP Data Platform (21-30)

### Q21: Dataflow vs Cloud Composer

```
Dataflow (Apache Beam):
+ Parallel data processing
+ Streaming and batch
+ Exactly-once semantics
- Complex infrastructure

Cloud Composer (Airflow):
+ Workflow orchestration
+ Complex dependencies
+ Data quality checks
- Not for heavy processing

Example:
Cloud Composer → Trigger Dataflow Job → Write to BigQuery
```

### Q22: Pub/Sub Architecture

```python
# Publisher
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path('project', 'topic')

for i in range(10):
    data = f"message {i}".encode('utf-8')
    publisher.publish(topic_path, data)

# Subscriber
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path('project', 'sub')

def callback(message):
    print(f"Received: {message.data}")
    message.ack()

subscriber.subscribe(subscription_path, callback=callback)
```

### Q23-30: Advanced GCP Topics
**23. Cloud Storage Lifecycle Policies**
**24. VPC and Private Endpoints**
**25. Cloud KMS for Encryption**
**26. Cloud Audit Logs**
**27. Resource Hierarchy**
**28. Service Accounts**
**29. Cross-project Queries**
**30. Billing and Cost Control**

---

