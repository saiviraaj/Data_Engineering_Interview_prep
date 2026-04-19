# Topic 8: Streaming & Event-Driven Systems
## Costco Sr. Data Engineer — Exhaustive Interview Textbook

---

## Table of Contents
1. [L1: Core Concepts — Streaming Basics](#l1-core-concepts)
2. [L2: Deep Technical Understanding](#l2-deep-technical-understanding)
3. [L3: Real-World Scenarios — Costco/MarTech Style](#l3-real-world-scenarios)
4. [L4: Hands-On Pipeline Design](#l4-hands-on-pipeline-design)
5. [L5: Edge Cases & Pitfalls](#l5-edge-cases--pitfalls)
6. [L6: Interview Questions — Easy to Very Hard](#l6-interview-questions)

---

## L1: Core Concepts

### 1.1 What is Streaming Processing?

Streaming processes data continuously as events arrive, rather than accumulating them into batches and processing periodically.

```
Batch:
  Events accumulate for N hours → [PROCESS ALL AT ONCE] → results available
  Latency: minutes to hours
  Example: nightly ETL job, daily report at 6 AM

Streaming:
  Event arrives → [PROCESSED IMMEDIATELY] → result available
  Latency: milliseconds to seconds
  Example: real-time fraud detection, live campaign ROAS dashboard
```

**When streaming is the right choice**:
- Business needs results in < 1 minute of an event occurring
- Downstream systems take action based on individual events (fraud block, push notification)
- Event-driven architecture (one service publishes, multiple consume)
- Continuous monitoring (alert when ROAS drops below threshold in real-time)

**When batch is better**:
- Results needed daily, hourly is fine
- Complex transformations that are hard to express incrementally
- Cost sensitivity (streaming infrastructure is always-on = expensive)
- Correctness > latency (batch with reconciliation is more reliable)

---

### 1.2 Core Streaming Concepts

**Event**: An immutable record of something that happened — "user clicked ad X at time T."

**Stream**: An unbounded, ordered sequence of events.

**Consumer group**: Multiple consumers sharing the work of processing a stream. Each event goes to one consumer in the group. Used for parallelism.

**Offset / Position**: Where a consumer is in the stream. Committing an offset = acknowledging "I've processed everything up to here."

**Backpressure**: When consumers can't keep up with producers. The stream buffers messages; if buffer fills, either messages drop or producers slow down.

**Throughput**: Messages processed per second.
**Latency**: Time from event production to event processing.
These are in tension — optimizing for one often hurts the other.

---

### 1.3 Kafka vs Pub/Sub — Comparison at Depth

| Dimension | Apache Kafka | GCP Pub/Sub |
|-----------|-------------|-------------|
| **Architecture** | Log-based (partitioned, replicated) | Push/pull queue (Google-managed) |
| **Retention** | Configurable (hours to forever) | 7 days max |
| **Ordering** | Per-partition guaranteed | Per-ordering-key only |
| **Replay** | Always (seek to any offset) | Within retention window |
| **Throughput** | Very high (millions/sec per broker) | Auto-scales to millions/sec |
| **Latency** | 5-15ms P99 | 100-200ms P99 |
| **Management** | Self-managed or Confluent Cloud | Fully managed (serverless) |
| **Consumer model** | Consumer groups with offsets | Subscriptions (at-least-once) |
| **Exactly-once** | Supported (idempotent producer + transactions) | Best-effort dedup via insertId |
| **Cost** | Cluster cost (~$500-5000/month for managed) | Per-message (~$0.04/1M) |
| **GCP integration** | Via Kafka Connect or manual | Native (Dataflow, BQ, Functions) |
| **Use Kafka when** | Sub-15ms latency, replay > 7 days, Kafka ecosystem | Use PubSub when |
| **Use Pub/Sub when** | On GCP, fully managed, don't need long replay | Use Kafka when |

---

## L2: Deep Technical Understanding

### 2.1 Kafka Architecture — Internals

```
Kafka Cluster
├── Broker 1 (server)
│   ├── Partition 0 of topic "ad-events" (leader)
│   ├── Partition 1 of topic "ad-events" (follower/replica)
│   └── Partition 0 of topic "conversions" (follower)
├── Broker 2
│   ├── Partition 0 of topic "ad-events" (follower)
│   ├── Partition 1 of topic "ad-events" (leader)
│   └── Partition 0 of topic "conversions" (leader)
└── ZooKeeper (or KRaft in newer versions) — cluster coordination
```

**Partition**: The unit of parallelism and ordering. Within a partition, messages are strictly ordered. Across partitions, ordering is not guaranteed.

**Consumer groups**: Allow multiple consumers to share the load of reading a topic. Each partition is assigned to exactly one consumer in a group at a time.

```
Topic: ad-events (3 partitions)

Consumer Group A (3 consumers):
  Consumer 1 → reads Partition 0
  Consumer 2 → reads Partition 1
  Consumer 3 → reads Partition 2
  (Each consumer gets 1 partition — full parallelism)

Consumer Group B (2 consumers):
  Consumer 1 → reads Partitions 0 and 1
  Consumer 2 → reads Partition 2
  (One consumer handles 2 partitions — less parallelism)

Consumer Group C (4 consumers):
  Consumer 1 → reads Partition 0
  Consumer 2 → reads Partition 1
  Consumer 3 → reads Partition 2
  Consumer 4 → idle (more consumers than partitions = waste)
```

**Key insight**: Max parallelism = number of partitions. Adding more consumers than partitions is wasteful.

#### 2.1.1 Kafka Producer — Reliability Settings

```python
from confluent_kafka import Producer

# Production-grade producer config
producer = Producer({
    'bootstrap.servers': 'kafka-broker-1:9092,kafka-broker-2:9092',
    
    # Reliability settings
    'acks': 'all',              # Wait for ALL in-sync replicas to confirm
                                # 'all' = highest durability
                                # '1' = leader only (faster, less durable)
                                # '0' = fire-and-forget (fastest, data loss possible)
    
    'retries': 5,               # Retry on transient failures
    'retry.backoff.ms': 1000,   # Wait 1s between retries
    
    # Idempotent producer: prevents duplicate messages on retry
    'enable.idempotence': True, # Producer assigns sequence numbers; broker deduplicates
    
    # Batching for throughput
    'linger.ms': 5,             # Wait 5ms to batch messages before sending
    'batch.size': 65536,        # 64KB batch size
    'compression.type': 'snappy',
    
    # Message ordering within partition
    'max.in.flight.requests.per.connection': 5,  # Must be <=5 for idempotence
})

def publish_ad_event(event: dict, campaign_id: str):
    """Publish with campaign_id as partition key — ensures ordering per campaign."""
    producer.produce(
        topic='ad-events',
        key=campaign_id.encode('utf-8'),    # key determines partition assignment
        value=json.dumps(event).encode('utf-8'),
        on_delivery=delivery_callback        # async confirmation
    )
    producer.poll(0)    # trigger delivery callbacks without blocking

def delivery_callback(err, msg):
    if err:
        logger.error(f"Message delivery failed: {err}")
        # In production: dead-letter queue or alert
    else:
        logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

# Flush before shutdown to ensure all messages sent
producer.flush()
```

#### 2.1.2 Kafka Consumer — Offset Management

```python
from confluent_kafka import Consumer, KafkaError

consumer = Consumer({
    'bootstrap.servers': 'kafka-broker-1:9092',
    'group.id': 'martech-ad-events-processor',
    'auto.offset.reset': 'earliest',    # start from beginning if no committed offset
    
    # Manual offset commit for exactly-once semantics
    'enable.auto.commit': False,         # CRITICAL: disable auto-commit
    
    # Reliability
    'session.timeout.ms': 30000,        # 30s timeout before rebalance
    'max.poll.interval.ms': 300000,     # 5 min max between polls
    'heartbeat.interval.ms': 3000,
})

consumer.subscribe(['ad-events', 'conversion-events'])

def consume_with_manual_commit():
    """
    Process-then-commit pattern: guarantees at-least-once processing.
    Message is only committed after successful processing.
    """
    while True:
        msg = consumer.poll(timeout=1.0)
        
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue    # End of partition (normal)
            else:
                raise KafkaException(msg.error())
        
        try:
            event = json.loads(msg.value().decode('utf-8'))
            
            # Process the event (write to BigQuery, etc.)
            process_event(event)
            
            # Only commit AFTER successful processing
            # This ensures: if we crash after processing but before commit,
            # we reprocess on restart (at-least-once)
            consumer.commit(message=msg, asynchronous=False)
            
        except ProcessingError as e:
            logger.error(f"Failed to process message: {e}")
            # Don't commit → message will be redelivered
            # Consider: after N failures, send to dead-letter topic
            
        except Exception as e:
            logger.critical(f"Unexpected error: {e}")
            consumer.close()
            raise
```

---

### 2.2 Windowing — The Heart of Stream Processing

Windowing groups the unbounded stream of events into finite time buckets so you can aggregate them.

#### 2.2.1 Window Types

```python
import apache_beam as beam
from apache_beam import window as beam_window

# ============================================================
# FIXED WINDOWS (Tumbling)
# Non-overlapping, equal-sized time buckets
# Each event belongs to exactly ONE window
# ============================================================
# [0:00-1:00) [1:00-2:00) [2:00-3:00) ...
# Event at 1:45 → belongs to [1:00-2:00) window

hourly_windows = events | beam.WindowInto(
    beam_window.FixedWindows(3600)    # 1-hour fixed windows
)
# Use for: hourly ROAS reports, hourly click counts

# ============================================================
# SLIDING WINDOWS
# Overlapping windows — event can belong to MULTIPLE windows
# Defined by (size, slide_period)
# ============================================================
# Window size=1h, slide=15min:
# [0:00-1:00) [0:15-1:15) [0:30-1:30) [0:45-1:45) ...
# Event at 0:45 belongs to: [0:00-1:00), [0:15-1:15), [0:30-1:30), [0:45-1:45)
# Use for: "ROAS over the last 1 hour, updated every 15 minutes"

rolling_roas = events | beam.WindowInto(
    beam_window.SlidingWindows(
        size=3600,    # 1 hour window
        period=900    # slide every 15 minutes
    )
)
# Note: each event is duplicated into size/period = 4 windows → more compute

# ============================================================
# SESSION WINDOWS
# Dynamic size — group events close in time per key
# New session starts when gap > session_gap_duration
# ============================================================
# User clicks at 10:00, 10:02, 10:15 (15m gap), 10:16:
# Session 1: [10:00-10:02], Session 2: [10:15-10:16]

user_sessions = events | beam.WindowInto(
    beam_window.Sessions(gap_size=1800)   # 30-minute inactivity = new session
)
# Use for: user session analytics, conversion path analysis

# ============================================================
# GLOBAL WINDOW
# All events in one infinite window (no time bucketing)
# Requires explicit triggers to fire
# ============================================================
continuous = events | beam.WindowInto(
    beam_window.GlobalWindows(),
    trigger=trigger.Repeatedly(trigger.AfterCount(1000)),  # fire every 1000 elements
    accumulation_mode=trigger.AccumulationMode.DISCARDING
)
# Use for: running totals that never reset, streaming deduplication
```

#### 2.2.2 Triggers — When to Emit Results

```python
from apache_beam.transforms.trigger import (
    AfterWatermark, AfterProcessingTime, AfterCount,
    AfterAll, AfterAny, Repeatedly, AccumulationMode
)

# Trigger after watermark (default: fire once when all data expected arrived)
basic_trigger = AfterWatermark()

# Fire early (before watermark) AND late (after watermark)
production_trigger = AfterWatermark(
    early=AfterProcessingTime(30),   # Fire a preliminary result after 30s of processing
    late=AfterCount(1)               # Fire for each late element after window closes
)

# Fire every N elements received (regardless of time)
count_trigger = Repeatedly(AfterCount(500))

# Combined: fire after 1000 elements OR 5 minutes, whichever comes first
hybrid_trigger = AfterAny(
    AfterCount(1000),
    AfterProcessingTime(5 * 60)
)

# Full window config with trigger
events | beam.WindowInto(
    beam_window.FixedWindows(3600),
    trigger=production_trigger,
    allowed_lateness=beam_window.Duration(seconds=24*3600),  # accept 24h late data
    accumulation_mode=AccumulationMode.ACCUMULATING,  # accumulate = final includes all
)
```

**ACCUMULATING vs DISCARDING**:
```
Window [0:00-1:00), final closes at 1:00, allowed_lateness=1h

At 1:00: emit result {clicks: 100, spend: 50}
At 1:30: late event arrives with 5 more clicks

ACCUMULATING: emit {clicks: 105, spend: 52}  ← includes all data seen
DISCARDING:   emit {clicks: 5, spend: 2}      ← only the late element

Use ACCUMULATING when downstream needs the complete, updated picture
Use DISCARDING when downstream incrementally adds partial results
```

---

### 2.3 Watermarks — Handling Time in Streaming

The **watermark** is the streaming system's estimate of "we've seen all events up to time T." Events older than the watermark are considered late.

```
Real-world event time:   10:00 ──────────────────────────── 11:00
                                        ↑
                              Event created at 10:30

Processing time:         10:05 ────────────────────────────── 11:05
                                                  ↑
                              Event received at 10:35
                              (5 min delay due to mobile batching)

Watermark at 10:35:      Estimates "all events up to ~10:30 have been seen"
                         (lags real time by ~5 minutes)
```

**Watermark lag**: The difference between processing time and event time. Caused by:
- Mobile apps batching events and sending periodically
- Network delays
- Clock skew between devices
- Ad network reporting delays (sometimes 24-48h)

```python
# Managing watermark lag in Dataflow
window.FixedWindows(3600),
allowed_lateness=window.Duration(seconds=7200),  # 2 hours of lateness OK

# If your mobile app batches events for up to 1 hour:
# Set allowed_lateness >= 1 hour
# The watermark should lag by at most 1 hour
# Any event arriving more than 1 hour late: dropped (or routed to side output)
```

**Practical watermark strategy for AdTech**:
```python
# Ad network data (Google, Meta) can arrive up to 48h late (cost adjustments)
# Use:
allowed_lateness = window.Duration(seconds=48 * 3600)  # 48 hours

# But: this means windows don't "close" for 48 hours after their end time
# The final result for yesterday's 10-11 AM window isn't available until today + 48h

# Pragmatic solution: 
# 1. Stream with 30-min allowed lateness → fast approximate results for dashboards
# 2. Daily batch job with 48h lookback → authoritative numbers for reporting
```

---

### 2.4 Exactly-Once Processing — The Hard Problem

**At-most-once**: Message processed 0 or 1 times. Some messages may be lost.
```
Producer → (network fails) → Broker: message NOT delivered
Or: Consumer crashes before processing → message lost (if auto-ack enabled)
```

**At-least-once**: Message processed 1 or more times. No messages lost, but duplicates possible.
```
Consumer processes message → crashes before committing offset
Consumer restarts → reprocesses same message → DUPLICATE
```

**Exactly-once**: Every message processed exactly once. No loss, no duplicates.
```
Requires: distributed transaction coordinating consumer offset commit + downstream write
OR: at-least-once delivery + idempotent consumer
```

#### 2.4.1 Achieving Exactly-Once in Practice

```python
# Approach 1: Kafka Transactions (true exactly-once within Kafka)
from confluent_kafka import Producer

transactional_producer = Producer({
    'bootstrap.servers': 'broker:9092',
    'transactional.id': 'ad-events-processor-1',  # unique per producer instance
    'enable.idempotence': True
})

transactional_producer.init_transactions()

try:
    transactional_producer.begin_transaction()
    
    # Read message, process, produce output — all in one transaction
    # If crash: transaction rolled back, consumer offset not committed
    # On restart: message reprocessed from last committed offset
    
    transactional_producer.send_offsets_to_transaction(
        offsets,
        group_metadata
    )
    transactional_producer.commit_transaction()
    
except Exception:
    transactional_producer.abort_transaction()
    raise

# Approach 2: At-least-once + Idempotent Consumer (most practical)
def process_and_write_to_bigquery(message):
    event_id = message['click_id']   # unique business key
    
    # MERGE on click_id: safe to run multiple times
    bq.query(f"""
        MERGE INTO `staging.clicks` AS target
        USING (SELECT '{event_id}' AS click_id, ...) AS source
        ON target.click_id = source.click_id
        WHEN NOT MATCHED THEN INSERT (...)
        WHEN MATCHED THEN UPDATE SET ...
    """)
    # If this runs twice for the same message: second run is a no-op
    # Result: same as exactly-once
```

---

### 2.5 Late Events — Handling Strategies

```python
# Beam: route late events to a side output for separate handling
from apache_beam.pvalue import TaggedOutput

class ProcessWithLateHandling(beam.DoFn):
    LATE_TAG = 'late_events'
    
    def process(self, element, window=beam.DoFn.WindowParam):
        # Elements in the main output: on-time
        yield element
    
    # This DoFn is called for elements that arrive after window closes
    # but within allowed_lateness

# Route late events to dead-letter or reprocessing queue
windowed = events | beam.WindowInto(
    beam_window.FixedWindows(3600),
    allowed_lateness=beam_window.Duration(seconds=7200),
    trigger=AfterWatermark(late=AfterCount(1)),
    accumulation_mode=AccumulationMode.ACCUMULATING
)

# Main output: on-time events
# Side output 'late_events': events arriving after watermark but within lateness
results_with_late = windowed | beam.ParDo(ProcessWithLateHandling()).with_outputs(
    ProcessWithLateHandling.LATE_TAG,
    main='on_time'
)

# Write on-time to dashboard table
results_with_late.on_time | WriteToBigQuery('project:mart.realtime_roas')

# Write late events to a reconciliation queue
results_with_late.late_events | WriteToBigQuery('project:staging.late_ad_events')
# Batch job picks up late events and corrects historical partitions
```

---

## L3: Real-World Scenarios

### 3.1 Scenario: Real-Time Clickstream Analytics for Costco MarTech

**Requirement**: Real-time ROAS dashboard updated every 5 minutes. Alert when any campaign's hourly ROAS drops below 1.5.

```python
# Complete streaming pipeline

import apache_beam as beam
from apache_beam import window as beam_window
from apache_beam.transforms.trigger import AfterWatermark, AfterProcessingTime

class CalculateHourlyRoas(beam.DoFn):
    def process(self, element, window=beam.DoFn.WindowParam):
        campaign_id, (spend_list, revenue_list) = element
        total_spend = sum(spend_list)
        total_revenue = sum(revenue_list)
        roas = total_revenue / total_spend if total_spend > 0 else 0
        
        yield {
            'campaign_id': campaign_id,
            'window_start': window.start.to_rfc3339(),
            'window_end': window.end.to_rfc3339(),
            'total_spend': total_spend,
            'total_revenue': total_revenue,
            'roas': roas,
            'is_below_threshold': roas < 1.5
        }

with beam.Pipeline(options=streaming_options) as p:
    events = (p
        | 'ReadFromPubSub' >> beam.io.ReadFromPubSub(
            subscription='projects/costco/subscriptions/ad-events-sub',
            with_attributes=True
        )
        | 'ParseEvents' >> beam.Map(lambda msg: json.loads(msg.data))
    )

    # Hourly ROAS with 5-minute early firing for dashboard
    hourly_roas = (events
        | 'WindowIntoHours' >> beam.WindowInto(
            beam_window.FixedWindows(3600),  # 1-hour windows
            trigger=AfterWatermark(
                early=AfterProcessingTime(5 * 60)  # update every 5 minutes
            ),
            allowed_lateness=beam_window.Duration(seconds=3600),
            accumulation_mode=AccumulationMode.ACCUMULATING
        )
        | 'ExtractMetrics' >> beam.Map(
            lambda e: (e['campaign_id'], (e.get('cost_usd', 0), e.get('revenue_usd', 0)))
        )
        | 'GroupByKey' >> beam.GroupByKey()
        | 'CalculateRoas' >> beam.ParDo(CalculateHourlyRoas())
    )

    # Write to BigQuery
    hourly_roas | 'WriteToBQ' >> beam.io.WriteToBigQuery(
        'costco:streaming.hourly_roas',
        write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND
    )

    # Alert on low ROAS via Pub/Sub
    (hourly_roas
        | 'FilterLowRoas' >> beam.Filter(lambda r: r['is_below_threshold'])
        | 'FormatAlert' >> beam.Map(lambda r: json.dumps(r).encode('utf-8'))
        | 'PublishAlert' >> beam.io.WriteToPubSub(
            topic='projects/costco/topics/roas-alerts'
        )
    )
```

---

### 3.2 Scenario: Event-Driven Architecture for Campaign Budget Alerts

**Requirement**: When a campaign exhausts its daily budget, instantly pause related bid adjustments and notify the campaign manager.

```python
# Event-driven pattern: no polling, pure event-driven

# Event 1: budget_exhausted published by billing service
# Consumer A: campaign manager service (pause bids)
# Consumer B: notification service (alert manager)
# Consumer C: analytics service (record event for analysis)

# Publisher: billing service
def publish_budget_exhausted(campaign_id: str, daily_budget: float):
    publisher = pubsub_v1.PublisherClient()
    event = {
        'event_type': 'BUDGET_EXHAUSTED',
        'campaign_id': campaign_id,
        'daily_budget': daily_budget,
        'exhausted_at': datetime.utcnow().isoformat(),
        'event_id': str(uuid.uuid4())
    }
    publisher.publish(
        'projects/costco/topics/campaign-events',
        json.dumps(event).encode(),
        event_type='BUDGET_EXHAUSTED',
        campaign_id=campaign_id
    )

# Consumer A: bid adjustment service (subscribes with filter)
# Pub/Sub filter: attributes.event_type = "BUDGET_EXHAUSTED"
def handle_budget_exhausted(event: dict):
    campaign_id = event['campaign_id']
    # Pause all bid adjustments for this campaign
    bids_service.pause_campaign(campaign_id)
    logger.info(f"Paused bids for {campaign_id} due to budget exhaustion")

# Consumer B: notification service
def notify_campaign_manager(event: dict):
    campaign_id = event['campaign_id']
    manager_email = get_campaign_manager_email(campaign_id)
    send_email(
        to=manager_email,
        subject=f"Campaign {campaign_id} budget exhausted",
        body=f"Daily budget of ${event['daily_budget']} was exhausted at {event['exhausted_at']}"
    )
```

---

## L4: Hands-On Pipeline Design

### 4.1 Design a Kafka Consumer for High-Throughput Ad Events

```python
# Production Kafka consumer with:
# - Multi-threaded processing
# - Dead-letter queue for failures  
# - Metrics emission
# - Graceful shutdown

from concurrent.futures import ThreadPoolExecutor
from threading import Event
import threading

class AdEventConsumer:
    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        topics: list[str],
        num_workers: int = 10,
        max_retries: int = 3
    ):
        self.consumer = Consumer({
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,
            'max.poll.interval.ms': 300000
        })
        self.consumer.subscribe(topics)
        self.executor = ThreadPoolExecutor(max_workers=num_workers)
        self.shutdown_event = Event()
        self.max_retries = max_retries
        self.metrics = {'processed': 0, 'failed': 0, 'dead_lettered': 0}
    
    def process_message(self, msg) -> bool:
        """Returns True if processed successfully."""
        event = json.loads(msg.value().decode('utf-8'))
        
        for attempt in range(self.max_retries):
            try:
                self._write_to_bigquery(event)
                self.metrics['processed'] += 1
                return True
            except TransientError as e:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)   # exponential backoff
                continue
            except Exception as e:
                break
        
        # All retries exhausted → dead-letter
        self._send_to_dead_letter(event, str(e))
        self.metrics['dead_lettered'] += 1
        return False
    
    def _send_to_dead_letter(self, event: dict, error: str):
        """Publish failed events to dead-letter topic for investigation."""
        dl_producer.produce(
            'ad-events-dead-letter',
            json.dumps({'event': event, 'error': error, 'failed_at': datetime.utcnow().isoformat()}).encode()
        )
    
    def run(self):
        """Main consumer loop with parallel processing."""
        batch_size = 100
        
        while not self.shutdown_event.is_set():
            messages = self.consumer.consume(batch_size, timeout=1.0)
            
            if not messages:
                continue
            
            # Submit batch to thread pool
            futures = [
                self.executor.submit(self.process_message, msg)
                for msg in messages
                if msg.error() is None
            ]
            
            # Wait for all in batch to complete
            results = [f.result() for f in futures]
            
            # Only commit up to the last successfully processed message
            # For simplicity: commit all (at-least-once) if all succeeded
            if all(results):
                self.consumer.commit(asynchronous=False)
            else:
                # Partial failure: only commit up to first failure
                # Complex: requires tracking per-partition offsets
                # Simpler approach: don't commit, reprocess entire batch
                pass
    
    def shutdown(self):
        self.shutdown_event.set()
        self.executor.shutdown(wait=True)
        self.consumer.close()
```

---

## L5: Edge Cases & Pitfalls

### 5.1 Consumer Rebalance — The Invisible Performance Killer

```python
# Problem: consumer group rebalance happens when:
# - New consumer joins
# - Consumer crashes or times out
# - Topic partition count changes

# During rebalance: ALL consumers stop processing (stop-the-world)
# Can take 30-60 seconds for large groups

# Symptoms: periodic latency spikes every N minutes
# Root cause: consumer taking too long to process → session timeout → rebalance

# Fix 1: Increase max.poll.interval.ms if processing is slow
consumer = Consumer({
    'max.poll.interval.ms': 600000,   # 10 minutes (default: 5 minutes)
    'session.timeout.ms': 30000,      # heartbeat timeout (default: 45s)
    'heartbeat.interval.ms': 10000    # send heartbeat every 10s (must be < session.timeout / 3)
})

# Fix 2: Process faster (don't block the consumer thread on slow operations)
# BAD: blocking BigQuery write in consumer loop
def bad_process(msg):
    event = json.loads(msg.value())
    bq.query(f"INSERT INTO ... VALUES (...)").result()  # BLOCKS for seconds

# GOOD: batch messages and write asynchronously
buffer = []
def good_process(msg):
    buffer.append(json.loads(msg.value()))
    if len(buffer) >= 100:
        write_batch_to_bq(buffer)
        buffer.clear()

# Fix 3: Use incremental cooperative rebalancing (Kafka 2.4+)
consumer = Consumer({
    'partition.assignment.strategy': 'cooperative-sticky'
    # Moves only CHANGED partitions, not all partitions → no stop-the-world
})
```

### 5.2 Message Ordering Across Partitions

```python
# GUARANTEE: within a partition, messages are ordered
# NO GUARANTEE: across partitions

# Problem: click event for user U published to partition 0
#          conversion event for user U published to partition 2
# Consumer processes conversion BEFORE click → attribution logic breaks

# Solution 1: Use same partition key for related events
producer.produce(
    topic='ad-events',
    key=user_id.encode(),   # user_id as key → all user events to same partition
    value=json.dumps(event).encode()
)
# Guarantee: all events for user U go to same partition → ordered within user

# Solution 2: Downstream ordering using event timestamps
# Don't rely on processing order; sort by event_timestamp before processing
def process_user_journey(user_events: list):
    sorted_events = sorted(user_events, key=lambda e: e['event_timestamp'])
    # Now process in correct order
```

### 5.3 The Thundering Herd — Consumer Group Startup

```python
# Problem: 50 consumers start simultaneously → all fetch from Kafka simultaneously
# → massive load spike on Kafka brokers
# → some brokers become overloaded → timeouts → rebalances → more load

# Solution: stagger consumer startup
import time, random

def start_consumer_with_jitter(consumer_id: int):
    # Random delay 0-30 seconds before starting to consume
    jitter = random.uniform(0, 30)
    time.sleep(jitter)
    consumer.run()

# In practice: Kubernetes readiness probes + rolling deployments handle this
```

### 5.4 Schema Evolution Breaking Consumers

```python
# Problem: producer adds new field to JSON payload
# Consumer code: event['old_field'] → KeyError crash

# BAD consumer code:
def process(msg):
    event = json.loads(msg.value())
    campaign_id = event['campaign_id']   # crashes if field removed or renamed

# GOOD: defensive coding
def process(msg):
    event = json.loads(msg.value())
    campaign_id = event.get('campaign_id') or event.get('campaignId')  # handle rename
    cost = event.get('cost_usd', event.get('cost_micros', 0) / 1e6)    # handle unit change

# BEST: use Schema Registry (Confluent) with Avro
# Schema Registry enforces backwards compatibility
# Old consumers can read new messages (new fields have defaults)
# Producers can't break consumers by removing required fields
```

---

## L6: Interview Questions — Easy to Very Hard

### EASY

**Q1: What is the difference between streaming and batch processing?**

**Answer**: Batch processing collects data over a time period and processes it all at once at scheduled intervals (e.g., daily at 6 AM). Results have hours of latency but are simpler to build and cheaper. Streaming processes each event immediately as it arrives. Results are available within seconds but the system is always running (higher cost) and more complex (windowing, watermarks, state management).

Choose streaming when the business needs results in under a minute and takes action on individual events. Choose batch when daily or hourly reporting is sufficient, and when correctness is more important than latency.

---

**Q2: What is a Kafka consumer group?**

**Answer**: A consumer group is a set of consumers that collectively read from a Kafka topic. Each partition in the topic is assigned to exactly one consumer in the group at any time. This provides parallelism — with N partitions and N consumers, all partitions are read simultaneously, giving N× throughput compared to a single consumer.

Key implications: (1) Max parallelism = number of partitions. Having more consumers than partitions means some consumers are idle. (2) If one consumer fails, Kafka rebalances — its partitions are reassigned to surviving consumers. (3) Different consumer groups are completely independent — each group reads the full topic from its own offset.

---

### MEDIUM

**Q3: Explain windowing in stream processing. What are the different window types?**

**Answer**: Windowing groups the infinite stream of events into finite time buckets for aggregation — since you can't compute "total clicks" on an infinite stream, you compute "total clicks per hour."

Three main window types:

**Fixed windows** (tumbling): Equal-sized, non-overlapping buckets. An event belongs to exactly one window. Use for: hourly/daily reports. "How many clicks in the 2-4 PM hour?"

**Sliding windows**: Overlapping windows defined by size and slide period. An event can belong to multiple windows. Use for: rolling metrics. "Clicks in the last hour, updated every 15 minutes."

**Session windows**: Dynamic size — groups events close in time per key. A new session starts when there's a gap longer than the session timeout. Use for: user session analytics. "Group user events into sessions where inactivity > 30 minutes = new session."

---

**Q4: What is the difference between at-most-once, at-least-once, and exactly-once semantics in messaging systems?**

**Answer**:

**At-most-once**: Messages are delivered 0 or 1 times. A crashed consumer that hadn't processed a message doesn't get it redelivered. Use when: losing occasional messages is acceptable (metrics, logs). Advantage: simplest, lowest overhead.

**At-least-once**: Messages are always delivered, but might be delivered multiple times. If a consumer processes a message but crashes before committing its offset, on restart it reprocesses from the last committed offset. Use when: losing data is unacceptable and you can make the consumer idempotent.

**Exactly-once**: Every message is processed exactly once — no loss, no duplicates. Achieved either via Kafka transactions (offset commit and downstream write are atomic) or via at-least-once delivery with an idempotent consumer (MERGE on business key ensures duplicate processing has no effect).

In practice: most production systems use at-least-once + idempotent consumers because Kafka transactions add complexity, and idempotent MERGE in BigQuery is straightforward. The result is effectively exactly-once behavior.

---

### HARD

**Q5: You have a Dataflow streaming pipeline that computes hourly ROAS per campaign. The pipeline runs fine but the Looker dashboard shows ROAS values jumping between correct and wrong values within the same hour. What's causing this and how do you fix it?**

**What they're testing**: Understanding of accumulating vs discarding mode, trigger behavior.

**Answer**:

**Root cause**: The window has `accumulation_mode=DISCARDING`. When an early trigger fires (every 5 minutes), it emits only the new events since the last trigger — not the cumulative sum. Looker is reading these partial results and displaying them.

Example:
```
10:00-10:05: 100 clicks, $50 spend, $200 revenue → ROAS = 4.0 (emitted)
10:05-10:10: 20 clicks, $5 spend, $15 revenue → ROAS = 3.0 (only these 20 clicks emitted)
```
Looker picks up the latest value → shows ROAS = 3.0 (misleading, based on partial data)

**Fix**: Change to ACCUMULATING mode:
```python
beam.WindowInto(
    FixedWindows(3600),
    trigger=AfterWatermark(early=AfterProcessingTime(5*60)),
    accumulation_mode=AccumulationMode.ACCUMULATING  # include all data seen so far
)
```

Now at 10:10, the emitted result includes all 120 clicks, $55 spend, $215 revenue → ROAS = 3.91 (correct cumulative).

**Additional fix**: Mark results with a `is_final` flag based on whether the watermark has passed the window's end time. Looker only shows `is_final=TRUE` results for closed windows; for open windows, it shows with a "preliminary" indicator.

---

### VERY HARD

**Q6: Design a real-time campaign performance system for Costco MarTech. Requirements: 100M events/day, sub-2-minute latency for ROAS dashboard, < 5% discrepancy vs daily batch numbers, handles 48-hour late data from ad networks. Architecture, trade-offs, and failure handling.**

**What they're testing**: End-to-end streaming system design, latency/accuracy trade-offs.

**Answer**:

**Architecture decision: Lambda Architecture**

The 48-hour late data requirement makes pure streaming impractical (you'd need to keep windows open for 48h → massive state). The solution is two paths:

```
STREAMING PATH (real-time, approximate):
  Ad events → Pub/Sub → Dataflow Streaming
    → FixedWindows(3600), allowed_lateness=3600s (1hr late data only)
    → BigQuery: streaming.roas_realtime (preliminary results)
    → Looker: shows with "preliminary" badge

BATCH PATH (authoritative, T+1):
  Pub/Sub → GCS (Dataflow also writes to GCS)
  → Daily Dataproc/DBT job: reprocesses 3 days of GCS data
  → BigQuery: mart.roas_authoritative (final numbers)
  → Looker: shows as authoritative after T+1 6 AM run
```

**Handling 48h late data**:
- Streaming path: 1-hour allowed lateness (practical for real-time dashboard)
- Batch path: 3-day lookback window with partition overwrite (catches 48h+ late data)
- Any event arriving > 1 hour late but < 48 hours: appears in batch authoritative, not in streaming

**Sub-2-minute latency design**:
```python
# Streaming pipeline triggers every 1 minute (early triggers)
FixedWindows(3600),
trigger=AfterWatermark(
    early=AfterProcessingTime(60),  # fire every 60 seconds
),
accumulation_mode=AccumulationMode.ACCUMULATING
```

**< 5% discrepancy target**:
- Main source of discrepancy: late data not captured by streaming
- Ad events typically arrive within 5 minutes of occurrence
- 1-hour allowed lateness catches >99% of events
- Remaining < 1% late arrivals cause at most 1-2% discrepancy
- Monitor discrepancy daily; if >5% for any campaign, investigate upstream delay

**Failure handling**:
1. Pub/Sub buffers 7 days → if Dataflow fails for hours, no data loss
2. Dataflow checkpoints to GCS → restart from checkpoint on failure (< 1 min data gap)
3. GCS raw events → always-available for batch reprocessing
4. Dead-letter topic for unparseable events → manual investigation
5. Monitoring: alert if streaming pipeline lag > 5 minutes, or if batch job fails

**Scale calculation**:
- 100M events/day = 1,157 events/sec average, ~5,000/sec peak
- Dataflow: 5-10 workers × n1-standard-4 handles 5,000 events/sec comfortably
- BigQuery streaming: 1M rows/sec quota → well within limits
- Cost: ~$300-500/month Dataflow + $50 Pub/Sub + $100 BQ streaming

---

## Summary: Streaming & Event-Driven — Senior Mastery Checklist

| Skill | What Senior Looks Like |
|-------|------------------------|
| Streaming vs batch | Clear decision framework; knows hybrid (Lambda) architectures |
| Kafka internals | Partition/consumer group/offset model; producer acks; consumer rebalance |
| Pub/Sub vs Kafka | Makes crisp trade-off decisions; knows when each fits |
| Window types | Fixed, sliding, session — knows use case for each |
| Triggers | AfterWatermark with early/late; accumulating vs discarding |
| Watermarks | Understands lag; sets allowed_lateness appropriately for use case |
| Exactly-once | Knows it's expensive; uses at-least-once + idempotent consumer in practice |
| Late data | Routes to side outputs; batch reconciliation for very late data |
| Failure handling | Checkpoints, dead letters, backpressure, graceful shutdown |
| System design | Lambda architecture; cost-aware; handles 48h late data requirement |
