# System Design for Senior Data Engineers

## DESIGN PRINCIPLES

### CAP Theorem

```
Choose 2 of 3:
- Consistency: All nodes see same data
- Availability: System always responds
- Partition tolerance: Works despite network splits

BigQuery: CP (Consistency + Partition tolerance)
- Data always correct, but network issues can block

Firestore: AP (Availability + Partition tolerance)
- Always responds, but may return stale data
```

### Lambda vs Kappa Architecture

```
LAMBDA (Batch + Streaming):
Raw → Batch Layer → Batch Views
   → Speed Layer → Real-time Views
   → Combined View

Pros: Accurate + fast
Cons: Complex, maintain 2 codebases

KAPPA (Streaming Only):
Raw → Stream Processing → Views
   → Replay Log (for recomputation)

Pros: Simple, single codebase
Cons: Requires replayable log
```

---

## REAL-WORLD DESIGNS

### Design 1: Real-Time Dashboard (10M events/day)

```
Requirements:
- <5 min latency for metrics
- 500 concurrent users
- Cost-effective

Architecture:

Event Sources
    ↓
Pub/Sub (1M events/day threshold)
    ├─ Dataflow streaming
    │  - 1-min tumbling window
    │  - Compute: COUNT, SUM by category
    │  - Write to BigQuery (append)
    │
    ├─ Redis cache (5 min TTL)
    │  - Latest metrics
    │  - For dashboard real-time tiles
    │
    └─ BigQuery hourly aggregations
       - Run nightly job
       - Pre-aggregate common metrics

Dashboard Query:
SELECT * FROM agg_daily        -- Last 90 days (batch)
UNION ALL
SELECT * FROM stream_1min       -- Last 24h (streaming)
WHERE date >= CURRENT_DATE() - 1

Cost: ~$1K/month
Latency: <1 minute
```

### Design 2: Fact Table for 1 Trillion Rows

```
Challenge:
- 1T rows = 365B rows/year
- 1000 concurrent queries
- <10 second latency
- Hourly updates

Solution:

CREATE TABLE fact_transactions
PARTITION BY DATE(transaction_date)
CLUSTER BY user_id, merchant_id, transaction_type

Storage Strategy:
- Hot (90 days): STANDARD = $620K/month
- Warm (365 days): COLDLINE = $242K/month
- Archive (>1 year): ARCHIVE = $183K/month

Query optimization:
- Partition: 1T → 100GB (scanning 90 days)
- Cluster: 100GB → 10GB (filtering by user_id)
- Column select: 10GB → 2GB (5 columns)
- Materialized views: 2GB → 100MB (pre-aggregated)

Expected cost per query:
- Raw table: 0.1TB × $6.25 = $0.625
- Materialized view: 0.1GB × $6.25 = $0.0006 (1000x cheaper!)
```

### Design 3: Real-Time Fraud Detection

```
Requirements:
- Detect fraud in <500ms
- 50M transactions/day (600 tx/sec)
- 99.9% uptime SLA
- <5% false negative rate

Architecture:

Transaction Stream
    ↓
Dataflow Processing
├─ Enrich with Redis cache
│  - User history
│  - Risk signals
│
├─ ML Model Score
│  - 50+ features
│  - LightGBM (~5ms inference)
│
└─ Decision Logic
   - Score > 0.9: BLOCK
   - Score 0.7-0.9: CHALLENGE (OTP)
   - Score < 0.7: APPROVE
   - Write decision log to BigQuery

Latency Breakdown:
- Pub/Sub → Dataflow: 50ms
- Enrich from Redis: 5ms
- Feature computation: 20ms
- ML inference: 5ms
- Write decision: 70ms
- Total: ~200ms (well under 500ms!)

Cost:
- Pub/Sub: $300/month
- Dataflow streaming: $2000/month
- Redis: $500/month
- BigQuery: $200/month
- Total: ~$3K/month
```

### Design 4: Data Migration (Teradata → BigQuery)

```
Challenge:
- 40PB of data
- 100+ tables
- Multiple teams
- Maintain data quality

Phases:

1. Discovery (Weeks 1-4)
   - Inventory all tables
   - Identify dependencies
   - Profile data

2. Schema Migration (Weeks 5-8)
   - Design star schema
   - Plan partitioning/clustering
   - Map data types

3. Data Migration (Weeks 9-14)
   - Initial full load (Datastream)
   - Setup incremental sync (CDC)
   - Data validation

4. App Readiness (Weeks 15-20)
   - Update queries
   - Performance testing
   - User training

5. Cutover (Weeks 21-24)
   - Parallel run period
   - Switchover
   - Decommission source

Key Technologies:
- Datastream: CDC from Teradata
- Dataflow: Transform + enrichment
- Cloud Composer: Orchestration
- BigQuery: Target warehouse

Expected timeline: 6 months
Cost: ~$500K (licensing + compute)
```

---

## FAILURE HANDLING

### Retry Strategy

```python
import time

def exponential_backoff_retry(max_retries=3, base_delay=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        raise
                    if not is_transient_error(e):
                        raise
                    
                    time.sleep(delay)
                    delay = min(delay * 2, 32)  # Exponential backoff
        return wrapper
    return decorator

@exponential_backoff_retry(max_retries=3)
def call_external_api():
    response = requests.get('https://api.example.com/data')
    if response.status_code >= 400:
        raise Exception(f"API error: {response.status_code}")
    return response.json()
```

### Idempotency Pattern

```sql
-- Bad: Not idempotent (double-counts if runs twice)
INSERT INTO orders SELECT * FROM staging;

-- Good: Idempotent (safe to run multiple times)
MERGE dataset.orders T
USING staging S
ON T.order_id = S.order_id
WHEN MATCHED THEN
  UPDATE SET amount = S.amount
WHEN NOT MATCHED THEN
  INSERT (order_id, amount) VALUES (S.order_id, S.amount);
```

### Dead Letter Queue

```python
def process_event(message, dlq_topic):
    try:
        event = json.loads(message.data.decode('utf-8'))
        validate_event(event)
        load_to_bigquery(event)
        message.ack()  # Success
    
    except ValueError as e:
        # Bad data: send to DLQ, don't retry
        send_to_dlq(event, dlq_topic, error=str(e))
        message.ack()
    
    except Exception as e:
        # Transient error: retry
        message.nack()
```

---

## MONITORING

### Key Metrics

```
Data Quality:
- Row count (actual vs expected)
- Null percentage per column
- Duplicate rows

Pipeline:
- Throughput (rows/sec)
- Latency (p50, p95, p99)
- Error rate
- Processing time

System:
- CPU utilization
- Memory usage
- Disk I/O
- Network bandwidth

Business:
- Records processed per day
- Query latency
- Cache hit rate
- SLA compliance
```

### Alerting Tiers

```
CRITICAL (immediate response):
- Pipeline failure (0 rows in 2 hours)
- Data warehouse unreachable
- >50% error rate

WARNING (4 hour response):
- 10-50% error rate
- Data freshness > 1 hour
- Query latency > baseline

INFO (for debugging):
- Processing counts
- Cache hit rates
- Volume spikes
```

---

## INTERVIEW TIPS

When asked to design a system:

1. **Ask clarifying questions**
   - Data volume (GB, TB, PB)?
   - Latency requirement (<1 sec, < 1 min)?
   - Consistency needs (strong, eventual)?
   - Cost constraints?

2. **Draw architecture**
   - Data sources → Ingestion → Processing → Storage → Analytics
   - Show clear flow

3. **Discuss trade-offs**
   - Real-time vs batch (cost, latency, complexity)
   - Strong vs eventual consistency
   - Vertical vs horizontal scaling

4. **Mention non-functional requirements**
   - High availability (replicas, failover)
   - Monitoring and alerting
   - Disaster recovery plan

5. **Estimate costs and scalability**
   - What's the cost per month?
   - Can it handle 10x growth?
   - What's the bottleneck?

6. **Discuss failure scenarios**
   - What if a service goes down?
   - How do you recover?
   - Any data loss?

---

## FINAL CHECKLIST

Before your interview:

- [ ] Know BigQuery architecture deeply
- [ ] Understand query optimization (partition, cluster, columns)
- [ ] Can explain window functions
- [ ] Comfortable with data modeling (star schema, SCD)
- [ ] Know GCP services (Dataflow, Dataproc, Composer)
- [ ] Can design 3 different systems (batch, streaming, hybrid)
- [ ] Understand CAP theorem and trade-offs
- [ ] Can discuss failure handling and monitoring
- [ ] Have project stories ready to tell

You're ready! 🚀
