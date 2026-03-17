# System Design for Data Platforms
## Deutsche Börse Group - Principal Data Engineer

**Author**: Prepared for Principal/Senior Architect Interview  
**Level**: Architecture & system thinking  
**Focus**: Real-time financial data platforms, scalability, reliability

---

## Core System Design Principles

### 1. Financial Data Platform Requirements

**Functional Requirements**:
- Ingest market data from multiple exchanges (100K+ events/sec)
- Process trades in real-time (sub-second latency)
- Support analytics on 10+ years historical data (petabyte-scale)
- Enable real-time dashboards for 1000+ concurrent traders
- Maintain audit trail (regulatory compliance)

**Non-Functional Requirements**:
- Availability: 99.99% (high-frequency trading)
- Latency: < 100ms for real-time data, < 5 seconds for analytics
- Consistency: Eventually consistent acceptable, no data loss
- Durability: 100% data retention, multiple replicas
- Cost: $100K - $500K/month budget
- Scalability: Handle 10x growth in 12 months

---

## System Design: Real-Time Market Data Platform

### Design 1: High-Throughput Event Streaming

**Architecture**:

```
┌─────────────────────────────────────────────────────┐
│         Exchange APIs (Multiple Exchanges)          │
│  EUREX, LSEG, CME, NYSE (100K+ events/sec total)   │
└──────────────────┬──────────────────────────────────┘
                   │
                   ↓
        ┌──────────────────────┐
        │   API Gateway        │
        │ (Traffic shaping)    │
        └──────────┬───────────┘
                   │
                   ↓
     ┌─────────────────────────────────┐
     │   Apache Kafka Cluster          │
     │ (Multi-partition, replication=3)│
     │ - market-ticks topic            │
     │ - trades topic                  │
     │ - alerts topic                  │
     └────┬────────────────────────────┘
          │
    ┌─────┴─────┬──────────────┬──────────┐
    │            │              │          │
    ↓            ↓              ↓          ↓
  ┌──────┐  ┌──────────┐  ┌──────────┐ ┌──────────┐
  │ Spark│  │Dataflow  │  │Clickhouse│ │ BigQuery │
  │Struct│  │ (Beam)   │  │(Analytics)  │(Historical)
  │ Str  │  │          │  │          │ │          │
  └──┬───┘  └────┬─────┘  └────┬─────┘ └────┬─────┘
     │           │             │            │
     ↓           ↓             ↓            ↓
  ┌────────────────────────────────────────────┐
  │         Event Store (Delta Lake)           │
  │ Immutable append-only log, partitioned     │
  │ by date, clustered by symbol               │
  └────────────────────────────────────────────┘
     │
     ├─→ Materialized Views (Real-time aggregates)
     ├─→ Feature Store (ML features)
     └─→ Warehouse (Analytics)
```

**Component Details**:

**1. API Gateway Layer** (100K events/sec):
```python
# Rate limiting & batching
class APIGateway:
    def __init__(self, kafka_producer):
        self.producer = kafka_producer
        self.batch_size = 1000
        self.batch_timeout = 1  # second
        self.buffer = []
    
    def ingest_tick(self, tick_event):
        # Validation
        if not self.is_valid(tick_event):
            self.metrics.increment('invalid_events')
            return
        
        # Deduplication (exactly-once)
        if self.is_duplicate(tick_event):
            return
        
        # Batching for throughput
        self.buffer.append(tick_event)
        if len(self.buffer) >= self.batch_size:
            self.flush()
    
    def flush(self):
        # Async write to Kafka
        self.producer.send_batch(
            topic='market-ticks',
            messages=self.buffer,
            key_extractor=lambda e: e['symbol']  # Partition by symbol
        )
        self.buffer.clear()
    
    def is_duplicate(self, event):
        # Use Redis for quick dedup check
        key = f"{event['timestamp']}_{event['symbol']}_{event['price']}"
        if redis.exists(key):
            return True
        redis.setex(key, 3600, 1)  # Expire after 1 hour
        return False
```

**2. Kafka Cluster Configuration**:
```ini
# topic: market-ticks
partitions: 64  # 64 parallel consumers
replication_factor: 3
min_insync_replicas: 2
retention_ms: 604800000  # 7 days hot
segment_ms: 86400000  # 1 day segments

# Topic: trades
partitions: 128  # High volume of trades
replication_factor: 3
min_insync_replicas: 2

# Broker configuration
# 3 brokers across 3 AZs
# Each broker: 32 cores, 256GB RAM, 10TB SSD
```

**3. Stream Processing (Spark Structured Streaming)**:
```python
from pyspark.sql import functions as F
from pyspark.sql.types import *

# Read from Kafka
ticks = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "kafka:9092")
    .option("subscribe", "market-ticks")
    .load()
    .select(F.from_json(F.col("value").cast("string"), tick_schema).alias("tick"))
    .select("tick.*")
)

# 1. Real-time aggregations
ohlc_1min = (
    ticks
    .withWatermark("timestamp", "10 seconds")  # Allow 10s late data
    .groupBy(
        F.window("timestamp", "1 minute", "30 seconds"),
        "symbol"
    )
    .agg(
        F.first("bid_price").alias("open"),
        F.max("ask_price").alias("high"),
        F.min("bid_price").alias("low"),
        F.last("ask_price").alias("close"),
        F.sum("bid_size").alias("volume")
    )
)

# 2. Anomaly detection
anomalies = (
    ticks
    .groupBy("symbol")
    .agg(
        F.avg("price").alias("avg_price"),
        F.stddev("price").alias("stddev_price")
    )
    .join(ticks, "symbol")
    .filter(
        (F.abs(F.col("price") - F.col("avg_price")) / F.col("stddev_price")) > 3
    )
)

# 3. Write outputs
ohlc_1min.writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("topic", "ohlc-1min") \
    .option("checkpointLocation", "s3://checkpoint/ohlc") \
    .start()

# Delta Lake for immutable event store
ticks.writeStream \
    .format("delta") \
    .mode("append") \
    .option("checkpointLocation", "s3://checkpoint/ticks") \
    .partitionBy("date") \
    .option("mergeSchema", "true") \
    .start("s3://lake/market-ticks")
```

**4. Delta Lake - Event Store**:
```sql
-- Immutable, time-travel enabled event store
CREATE TABLE market_ticks (
    tick_id STRING,
    timestamp TIMESTAMP,
    symbol STRING,
    bid_price DOUBLE,
    ask_price DOUBLE,
    bid_size INT,
    ask_size INT,
    exchange STRING,
    _ingestion_time TIMESTAMP
)
PARTITIONED BY (DATE(timestamp))
CLUSTERED BY symbol INTO 64 BUCKETS;

-- Enable time-travel
ALTER TABLE market_ticks SET TBLPROPERTIES (
    'delta.logRetentionDuration' = 'interval 30 days'
);

-- Point-in-time query (for auditing)
SELECT * FROM market_ticks 
VERSION AS OF 12345;  -- Get data as of version 12345

-- Replay from specific timestamp
SELECT * FROM market_ticks 
TIMESTAMP AS OF '2024-01-15 10:00:00';
```

---

### Design 2: Handling the CAP Theorem

**Trade-off Analysis for Financial Data**:

| Requirement | Choice | Why |
|-----------|--------|-----|
| **Consistency** | Eventual | Real-time data → eventual consistency acceptable |
| **Availability** | High | Cannot lose trades |
| **Partition Tolerance** | High | Multi-region required |

**Implementation**:

```
CP (Consistency + Partition)
├─ Strict serialization
├─ Leader-follower Kafka
├─ All writes acknowledged before response
└─ Acceptable for: Risk calculations, regulatory reporting

AP (Availability + Partition)
├─ Async replication
├─ Accept stale reads
├─ Partition → reads from any replica
└─ Acceptable for: Dashboard, real-time analytics

Recommended for DBG: Hybrid approach
├─ Critical writes: CP (trades → event store)
├─ Analytics reads: AP (eventual consistency)
└─ Risk reads: CP
```

---

### Design 3: Partitioning Strategy for 100K Events/Sec

**By Symbol (Recommended)**:
```
Kafka partition key = symbol

Advantage:
- All trades for AAPL → partition 1 (ordering maintained)
- Consumer group can have dedicated consumer per partition
- Balances load if symbols have similar volume

Challenge:
- Skew if one symbol dominates (e.g., EURUSD 50% of volume)
- Solution: Use salting for skewed symbols
```

**By Time Window**:
```
Kafka partition key = timestamp_bucket (every 60 seconds)

Advantage:
- Even distribution across time
- Time-based aggregations simple

Disadvantage:
- Symbol data scattered across partitions
- Ordering lost within symbol
```

**Recommended: Hybrid**:
```python
def partition_key(event):
    # Detect skew
    if event['symbol'] in SKEWED_SYMBOLS:
        # Add salt for balanced distribution
        salt = hash(event['timestamp']) % 5
        return f"{event['symbol']}_{salt}"
    else:
        return event['symbol']
```

---

### Design 4: Handling Late/Out-of-Order Data

**Watermarking Strategy**:

```
Time ----→
         
Window: [10:00, 10:01)
Data arrival:
10:00:15 (on-time)
10:00:45 (on-time)
10:01:05 (late, 5 seconds)
10:00:20 (very late, 45 seconds!)

Watermark = max_timestamp - allowed_lateness
If watermark reached → close window, don't accept more data
```

**Implementation**:

```python
# Structured Streaming with watermark
from pyspark.sql import functions as F

ticks = spark.readStream.from_kafka(...)

# Allow 30 seconds late data
result = (
    ticks
    .withWatermark("timestamp", "30 seconds")  # Allow 30s late
    .groupBy(
        F.window("timestamp", "1 minute"),
        "symbol"
    )
    .agg(...)
)

# Behavior:
# Window [10:00, 10:01] watermark at 10:01:30
# - Accept events before 10:01:30
# - Close window at 10:01:30
# - Events arriving after 10:01:30 for this window dropped
```

---

### Design 5: Multi-Region for Disaster Recovery

**Architecture**:

```
Primary Region: Europe-West2 (London)
├─ Kafka brokers (3)
├─ Spark cluster (20 nodes)
├─ BigQuery dataset
└─ Monitoring

Replica Region: Europe-West1 (Frankfurt)
├─ Kafka mirror (Confluent MirrorMaker)
├─ Read-only Spark cluster
├─ BigQuery cross-region replica
└─ Standby

Cold Region: US-East1
├─ Deep archive storage
├─ Historical backups
└─ Disaster recovery
```

**Failover Procedure** (RTO: 5 minutes, RPO: < 1 minute):

```python
# Active-passive failover
class FailoverManager:
    def __init__(self):
        self.current_region = "europe-west2"
        self.health_check_interval = 10  # seconds
    
    def monitor_health(self):
        while True:
            if not self.is_healthy(self.current_region):
                self.trigger_failover()
                break
            time.sleep(self.health_check_interval)
    
    def trigger_failover(self):
        # 1. Promote read-only replica to primary
        self.current_region = "europe-west1"
        
        # 2. Redirect all traffic
        dns.update_cname("data.dbg.com", "replica.eu-west1.gcp")
        
        # 3. Resume writes (Kafka producer now targets new primary)
        kafka_producer.update_brokers(self.get_brokers(self.current_region))
        
        # 4. Verify consistency
        self.verify_replication_lag()  # Should be < 10s
        
        # 5. Alert team
        self.notify_ops("Failover to EU-West1 complete")
```

---

### Design 6: Data Quality & Validation

**Multi-Layer Validation**:

```
┌──────────────────────────────────────────────┐
│   Layer 1: Schema Validation (API Gateway)    │
│ - Required fields present                     │
│ - Data types correct                          │
│ - Timestamp format valid                      │
└──────────┬───────────────────────────────────┘
           │
           ↓
┌──────────────────────────────────────────────┐
│   Layer 2: Business Logic (Dataflow)          │
│ - Price > 0                                   │
│ - Bid < Ask                                   │
│ - Volume > 0                                  │
│ - Timestamp recent (< 60 sec old)             │
└──────────┬───────────────────────────────────┘
           │
           ↓
┌──────────────────────────────────────────────┐
│   Layer 3: Consistency (BigQuery)             │
│ - No duplicates                               │
│ - No gaps in time-series                      │
│ - Volume changes reasonable                   │
└──────────┬───────────────────────────────────┘
           │
           ↓
┌──────────────────────────────────────────────┐
│   Layer 4: Alerts (Monitoring)                │
│ - Missing symbol data for > 5 min             │
│ - 10%+ price move in < 1 sec                  │
│ - Unusual volume patterns                     │
└──────────────────────────────────────────────┘
```

**Implementation**:

```python
from great_expectations.core.batch import Batch
from great_expectations import expectations as gx

# Data quality checks
expectations = {
    'market_ticks': [
        {'column': 'timestamp', 'expectation': 'to_be_in_the_last_hour'},
        {'column': 'bid_price', 'expectation': 'to_be_between', 'min': 0, 'max': 1000000},
        {'column': 'ask_price', 'expectation': 'to_be_between', 'min': 0, 'max': 1000000},
        {'column': 'bid_price', 'expectation': 'to_be_less_than', 'other_column': 'ask_price'},
        {'column': 'symbol', 'expectation': 'to_not_be_null'},
    ]
}

# Monitor violations
def validate_batch(df, batch_name):
    suite = gx.ExpectationSuite(name=batch_name)
    
    for check in expectations[batch_name]:
        violation_rate = run_expectation(df, check)
        
        if violation_rate > 0.01:  # > 1% violations
            alert(f"Quality issue: {batch_name} {check} failed at {violation_rate}%")
            
            # Route to quarantine
            df.filter(...).write.parquet("s3://quarantine/")
```

---

## Production Patterns & Trade-Offs

### Trade-Off 1: Real-Time vs. Batch Processing

**Real-Time Streaming**:
- ✅ Sub-second latency
- ✅ Immediate alerts
- ❌ Higher costs (24/7 compute)
- ❌ More complex (state management)
- ❌ Harder to debug

**Batch Processing**:
- ✅ Lower costs (scheduled runs)
- ✅ Simpler (stateless)
- ✅ Easier to reprocess
- ❌ Higher latency (hours)
- ❌ Can't detect real-time anomalies

**Recommendation for DBG**:
```
Real-time for:
├─ Risk monitoring (< 1 second)
├─ Real-time dashboards
└─ Anomaly detection

Batch for:
├─ Historical analytics
├─ Nightly aggregations
└─ Regulatory reporting
```

---

### Trade-Off 2: Cost vs. Latency

**Aggressive Optimization** (Cost: $100K/month):
```
- High compression (10:1)
- Partitioning + clustering
- Materialized views (pre-aggregated)
- Batch writes (1 hour windows)
- Latency: 1-5 minutes
```

**Performance Optimization** (Cost: $500K/month):
```
- No compression
- Streaming inserts (real-time)
- No pre-aggregation
- Multiple replicas
- Latency: < 1 second
```

**Balanced (DBG Recommendation - $250K/month)**:
```
- Selective compression
- Partitioning only (no clustering)
- Limited materialized views
- Hybrid batch + streaming
- Latency: 10-30 seconds
```

---

### Trade-Off 3: Consistency vs. Availability

**For Financial Trades**:
```
Requirement: No lost trades (CP)
├─ Kafka min_insync_replicas=2
├─ Acknowledgement required before response
├─ Slight latency increase (10-100ms) acceptable
└─ Result: 99.99% durability

For Analytics Queries:
Requirement: High availability (AP)
├─ Read replicas in multiple regions
├─ Eventual consistency acceptable
├─ Cache frequently accessed data
└─ Result: 99.95% availability
```

---

## Monitoring & Alerting

**Key Metrics**:

```python
class PlatformMetrics:
    def __init__(self):
        self.metrics = {
            # Latency
            'ingestion_latency_p99': 'Must be < 500ms',
            'streaming_lag': 'Must be < 1 second',
            
            # Throughput
            'events_per_second': 'Target: 100K',
            'bytes_per_second': 'Target: 200MB',
            
            # Quality
            'duplicate_rate': 'Must be < 0.01%',
            'error_rate': 'Must be < 0.1%',
            
            # Reliability
            'broker_availability': 'Must be 99.99%',
            'replication_lag': 'Must be < 10s',
            
            # Cost
            'cost_per_event': 'Target: < $0.001',
            'bytes_scanned_per_query': 'Minimize',
        }
```

**Alerting Rules**:

```yaml
alerts:
  - name: HighIngestionLatency
    condition: ingestion_latency_p99 > 500ms for 5 minutes
    action: Page on-call engineer
  
  - name: ReplicationLag
    condition: replication_lag > 30s
    action: Alert but not page (non-critical)
  
  - name: DataQualityViolation
    condition: duplicate_rate > 0.01%
    action: Page + quarantine data
  
  - name: HighCost
    condition: daily_cost > 20000 (abnormal)
    action: Email team for investigation
```

---

## Summary: Decision Matrix for Deutsche Börse

```
Component         | Choice           | Why
-----------------|------------------|------------------------------------------
Message Queue     | Apache Kafka     | High throughput, durability, multi-consumer
Processing        | Spark Streaming  | Exactly-once, windowing, aggregation
Warehousing       | BigQuery         | Petabyte scale, cost-effective, SQL interface
Storage           | Delta Lake       | ACID, time-travel, schema evolution
Analytics         | Looker           | Real-time + historical, self-service
Cost Model        | Slots + On-demand | Predictable costs + flexibility
Failover          | Active-passive   | 5-minute RTO, < 1min RPO
Latency Target    | 10-30 seconds    | Real-time enough for operations
Availability      | 99.99%           | High-frequency trading requirement
```

---

**Principal-Level Talking Points**:

1. **Architecture**: End-to-end design, not just components
2. **Trade-offs**: Cost vs. latency, consistency vs. availability
3. **Scalability**: Handle 10x growth, not just 100K events/sec
4. **Reliability**: Failover, disaster recovery, data integrity
5. **Operations**: Monitoring, alerting, runbooks
6. **Team**: How you'd mentor engineers, communicate with stakeholders

---

Good luck with Deutsche Börse! This system design demonstrates the thinking expected at Principal level.
