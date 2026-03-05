# Mock Interview - 90 Minutes (FAANG Level)

Hardcore technical interview simulation.

---

## Interview: Design Real-time Analytics at Scale

**Company:** Google/Facebook Level  
**Role:** Senior Staff Data Engineer  
**Time:** 90 minutes  

---

# PROBLEM: Real-Time Analytics Dashboard for 10B Events/Day

## Context
"We process 10 billion events per day from user interactions. We need a real-time analytics dashboard that shows metrics with <2 second latency to 1000 concurrent users. Metrics include: active users, top products, trending topics, geo distribution. Design the system."

---

## ROUND 1: System Architecture (35 minutes)

### Requirements Clarification (5 min)

**Candidate asks:**
- "What's the event volume distribution? Bursty or steady?"
- "What's acceptable accuracy? Real-time vs eventual?"
- "Which metrics are most critical?"
- "Geographic regions? Single region or global?"
- "Historical data requirements? Just real-time?"

**Interviewer answers:**
- Peak: 200K events/second (steady)
- Near real-time acceptable (< 5 seconds for top 99%)
- Active users, top-10 products, top-20 regions most critical
- Global with regional aggregation
- Keep 90 days detail, 2 years summary

---

### High-Level Architecture (10 min)

```
Events (200K/sec) → Kafka → Stream Processor → Cache Layer → API
                  ↓
             Batch Processor → Data Warehouse
                  ↓
              Dashboard
```

**Detailed design:**

```
Frontend (React Dashboard)
    ↓
API Server (Load balanced)
    ↓
Redis Cache Layer (Multi-region)
    ↓
Kafka (Event Topic)
    ↓
Flink/Spark Streaming (Real-time)
    ↓
HBase/Cassandra (Time-series DB)
    ↓
Batch Layer (Nightly aggregations)
    ↓
Data Warehouse (BigQuery/Redshift)
```

---

### Deep Dive: Event Ingestion & Streaming (15 min)

```python
# 1. Event Ingestion
class EventCollector:
    def __init__(self):
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            batch_size=1000,  # Batch for efficiency
            acks='all'  # Wait for all replicas
        )
    
    def collect(self, event):
        # Add metadata
        enriched_event = {
            'event_id': uuid.uuid4(),
            'event_type': event['type'],
            'timestamp': datetime.now(),
            'user_id': event['user_id'],
            'product_id': event.get('product_id'),
            'region': event.get('region'),
            'device': event.get('device')
        }
        
        # Send to Kafka with user_id as key (partitioning)
        self.kafka_producer.send(
            'events',
            key=event['user_id'].encode(),
            value=json.dumps(enriched_event).encode()
        )

# 2. Real-time Processing (Flink)
class RealTimeProcessor:
    def process(self):
        env = StreamExecutionEnvironment.get_execution_environment()
        
        # Read from Kafka
        kafka_stream = FlinkKafkaConsumer(
            'events',
            SimpleStringSchema(),
            {'bootstrap.servers': 'localhost:9092'}
        )
        
        # Parse and process
        processed = env.add_source(kafka_stream) \
            .map(lambda x: json.loads(x)) \
            .filter(lambda x: x['event_type'] in ['view', 'click', 'purchase'])
        
        # Window aggregations (Tumbling 10-second windows)
        active_users = processed \
            .key_by(lambda x: x['region']) \
            .time_window(Time.seconds(10)) \
            .aggregate(
                AggregateFunction_ActiveUsers(),
                lambda window_result: (window_result.region, window_result.active_users)
            )
        
        # Write to Redis for real-time metrics
        active_users.add_sink(RedisSink())
        
        # Also write to Druid for historical queries
        active_users.add_sink(DruidSink())
        
        env.execute("RealTimeMetrics")

# 3. Aggregation for Dashboard
class MetricsAggregator:
    def __init__(self):
        self.redis = redis.Redis(host='localhost')
    
    def get_active_users(self):
        # Check cache first
        cached = self.redis.get('active_users:global')
        if cached:
            return json.loads(cached)
        
        # Fallback to compute
        return self.compute_active_users()
    
    def get_top_products(self, limit=10):
        key = f'top_products:limit_{limit}'
        cached = self.redis.zrevrange(key, 0, limit-1, withscores=True)
        if cached:
            return cached
        
        return self.compute_top_products(limit)

# 4. Caching Strategy
class CachingStrategy:
    """
    Hot data (99% of queries) → Redis cache
    Warm data → Druid + local cache
    Cold data → Data warehouse
    """
    
    def get_metric(self, metric_name, filters):
        # Redis: 1-2ms
        if metric_name in ['active_users', 'top_products']:
            return self.redis.get(metric_name)
        
        # Druid: 50-200ms (aggregated time-series)
        elif metric_name in ['hourly_trends']:
            return self.druid.query(metric_name, filters)
        
        # BigQuery: 1-5s (detailed historical)
        else:
            return self.bigquery.query(metric_name, filters)
```

### Scaling Strategy (10 min)

**Handling 200K events/second:**

```
Kafka Partitioning:
- 200 partitions (2-3 events per partition per second)
- Partition by user_id for state affinity
- Replication factor: 3

Stream Processor:
- 200 parallel tasks (one per partition)
- Auto-scaling based on lag
- Memory: 2GB per task

Cache Consistency:
- Cache invalidation: TTL + event-driven
- Cross-region sync: eventual consistency
- Monitoring: Lag tracking
```

**Multi-region Challenges:**

```
Problem: Dashboard users in NY, Tokyo, Mumbai
Solution:
1. Local Redis in each region (caching)
2. Kafka cluster replication across regions
3. Eventually consistent aggregations
4. Conflict resolution: "Last write wins" + timestamps

Network costs: ~$500K/month for cross-region replication
Tradeoff: Accept eventual consistency for cost
```

---

## ROUND 2: Advanced Coding Question (35 minutes)

### Problem: Implement Distributed Counter with Exactly-Once

**Problem Statement:**

Implement a distributed counter for unique active users. Handle:
1. Exactly-once semantics (no double counts)
2. Late-arriving events (24-hour window)
3. Support 200K updates/second
4. <100ms query latency

### Solution Architecture

```python
from hyperloglog import HyperLogLog  # Probabilistic counting
import redis

class DistributedActiveUserCounter:
    """
    Uses HyperLogLog for cardinality estimation (99.9% accuracy)
    Memory: ~12KB per 1 billion unique items
    Actual users: 100M-1B → memory: 100MB-1GB
    """
    
    def __init__(self):
        self.redis = redis.Redis(host='localhost')
        self.hll_precision = 14  # 99.9% accuracy
    
    def add_user(self, user_id, timestamp):
        """Add user for today"""
        today = datetime.now().strftime('%Y-%m-%d')
        key = f'hll:active_users:{today}'
        
        # Add to HyperLogLog (idempotent)
        self.redis.pfadd(key, user_id)
        
        # Set TTL: 25 hours (handle late arrivals by 1 hour)
        self.redis.expire(key, 90000)
    
    def get_unique_count(self):
        """Get approximate unique count for today"""
        today = datetime.now().strftime('%Y-%m-%d')
        key = f'hll:active_users:{today}'
        
        count = self.redis.pfcount(key)
        return count
    
    def get_count_for_date(self, date):
        """Historical count with eventual consistency"""
        key = f'hll:active_users:{date}'
        count = self.redis.pfcount(key)
        return count

# Verification with streaming
class CounterValidator:
    def validate(self):
        # Exact count from database
        exact = self.db.query("SELECT COUNT(DISTINCT user_id) FROM events WHERE date = today()")
        
        # Approximate count from HLL
        approx = counter.get_unique_count()
        
        # Check accuracy
        error = abs(exact - approx) / exact
        assert error < 0.01, f"Error too high: {error}"
        
        print(f"Exact: {exact}, Approx: {approx}, Error: {error:.2%}")

# Performance test
class PerformanceTest:
    def test_throughput(self):
        import time
        
        counter = DistributedActiveUserCounter()
        start = time.time()
        
        # Simulate 200K events/sec
        for i in range(200_000):
            counter.add_user(f'user_{i}', datetime.now())
        
        elapsed = time.time() - start
        throughput = 200_000 / elapsed
        
        print(f"Throughput: {throughput:.0f} ops/sec")
        assert throughput > 100_000, "Too slow"  # Need > 200K
```

### Follow-up: Regional Aggregation

```python
class RegionalCounter:
    """
    Challenge: Merge counts from 10 regions
    Solution: Merge HyperLogLog structures
    """
    
    def merge_regions(self, regions=['us', 'eu', 'asia']):
        """Merge HLL from all regions"""
        keys = [f'hll:active_users:{region}' for region in regions]
        
        # Merge HLLs (commutative)
        temp_key = 'hll:merged:temp'
        self.redis.pfmerge(temp_key, *keys)
        
        count = self.redis.pfcount(temp_key)
        self.redis.delete(temp_key)
        
        return count
    
    def accuracy_loss(self):
        """
        Merging 10 HLLs introduces ~sqrt(10) = 3.16x more error
        Original: 0.1% error
        After merge: 0.31% error
        Still acceptable for analytics
        """
        pass
```

### Complexity Discussion (5 min)

**Time:**
- Add: O(1) Redis operation
- Query: O(k) where k = regions, typically 10

**Space:**
- Per HLL: ~12KB
- Per region per day: ~12KB
- 365 days × 10 regions: ~43MB
- Excellent for scaling

---

## ROUND 3: System Design Deep Dive & Trade-offs (15 minutes)

### Design Decisions & Rationale

```
1. HyperLogLog vs Exact Set
   ✅ HyperLogLog: 12KB, 99.9% accurate, can merge
   ❌ Exact Set: 8 bytes * 1B users = 8GB memory

2. Redis vs Cassandra
   ✅ Redis: Sub-millisecond, in-memory
   ❌ Cassandra: Better durability but slower

3. Stream Processor: Flink vs Spark
   ✅ Flink: True streaming, exactly-once
   ❌ Spark: Micro-batches, higher latency

4. Caching: Where to put it?
   ✅ Redis Layer: Hot metrics, fast access
   ❌ Every query goes to Flink: Slow

5. Consistency: Strong vs Eventual
   ✅ Eventual: Fast, scalable, good enough for analytics
   ❌ Strong: Complex, slower, unnecessary
```

### Failure Scenarios

```
1. Redis goes down
   Impact: 2-5 second latency spike
   Fix: Fallback to Druid/in-memory cache

2. Late arriving events (24h delayed)
   Impact: Yesterday's count changes
   Fix: 25-hour TTL, re-aggregation window

3. Regional network partition
   Impact: Regional counts diverge
   Fix: Accept temporary inconsistency, reconcile on heal

4. Flink job crashes
   Impact: Real-time metrics frozen
   Fix: Upstream events go to Kafka, replay from checkpoint
```

---

## Summary

**What FAANG looks for:**
✅ Handling extreme scale (10B events/day)
✅ Trade-offs between consistency, availability, latency
✅ Understanding of probabilistic data structures
✅ Real-world considerations (late data, failures, costs)
✅ Can discuss without implementation details

---

