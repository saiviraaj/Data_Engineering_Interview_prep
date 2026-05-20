# MODULE 9: ADVANCED STREAMING — DEEP DIVE
## PhD-Level Data Engineering Interview Preparation
### Tailored for Viraaj Sivaraju — Senior Data Engineer, Wells Fargo CDM Next

---

## MODULE OVERVIEW

This dedicated advanced streaming module covers everything beyond basics: watermarks under load, stream-stream joins, stateful processing, exactly-once semantics at the engine level, streaming SQL, event-time vs processing-time semantics, backpressure, and production debugging of streaming pipelines. This is the depth that separates candidates who "have used Dataflow" from those who truly understand streaming.

---

## PART 1: THE FOUNDATIONS — TIME SEMANTICS

### Three Clocks in Every Streaming System

```
CLOCK 1: EVENT TIME
━━━━━━━━━━━━━━━━━━━
When the event actually happened in the real world.
Example: Transaction timestamp, sensor reading time.
Embedded in the event payload.
CAN be in the past. CAN arrive out of order.

CLOCK 2: INGESTION TIME
━━━━━━━━━━━━━━━━━━━━━━━
When the event entered the streaming system (Pub/Sub/Kafka).
Set by the messaging system, not the source.
Usually close to event time, but not always.
Useful when event time is unreliable (old systems, clock skew).

CLOCK 3: PROCESSING TIME
━━━━━━━━━━━━━━━━━━━━━━━━
When the streaming engine processed the event.
This is "wall clock time" — the system's current time.
Always moves forward at consistent rate.
Never use for business logic that depends on when events happened.

WHY THIS MATTERS:
━━━━━━━━━━━━━━━━
Consider computing "revenue in the 2 PM hour":

  Event time window [14:00 - 15:00]:
    → Revenue of transactions that OCCURRED between 2 PM and 3 PM
    → Correct for business reports ("what actually happened at 2 PM")
    → Harder to implement (late arrivals, out-of-order events)
    
  Processing time window [14:00 - 15:00]:
    → Revenue of transactions that ARRIVED between 2 PM and 3 PM
    → Easy to implement (just bucket by current time)
    → Wrong for business reports (3 PM arrivals counted in 2 PM window)
    
RULE: Always use EVENT TIME for business logic.
      Use PROCESSING TIME only for monitoring/operational metrics.
```

### Clock Skew and Its Consequences

```
SCENARIO:
  Payment processed in Singapore at 14:00 SGT
  SGT = UTC+8, so event time in UTC = 06:00
  
  Mobile device has wrong clock: shows 13:50 UTC instead of 06:00 UTC
  Event arrives in Pub/Sub at 06:02 UTC
  
  Result: Event has event_time=13:50 UTC, but arrives at 06:02 UTC
  
  To your streaming system:
  - Current processing time: 06:02 UTC
  - Event time: 13:50 UTC
  - Lag: 13:50 - 06:02 = 7 hours 48 minutes in the FUTURE?
  
  This breaks watermark calculations completely.
  
DEFENSES:
  1. Sanity-check event times: reject events > 7 days in past or > 5 minutes in future
  2. Fall back to ingestion time for events with unreliable clocks
  3. Use bounded clock skew assumption: max clock drift = ±5 minutes
```

---

## PART 2: WATERMARKS — THE COMPLETE PICTURE

### What is a Watermark, Really?

A watermark is a statement:

> "I believe all events with event_time ≤ W have arrived. Any event arriving after this with event_time ≤ W is considered late."

It's a probabilistic guarantee, not a certainty. The watermark is always a function of observed data, not the real world.

### The Watermark Progress Problem

```
HEURISTIC WATERMARK:
  Dataflow computes: watermark = min(event_time across all pending events) - skew_allowance
  
  Example:
    Oldest unprocessed event: 14:55
    Skew allowance: 5 minutes
    Watermark: 14:50
    
    This means: "All events with event_time ≤ 14:50 have been seen"
    Windows closing at 14:50 can now emit results
  
  PROBLEM 1: STRAGGLER DATA
    One shard/partition has no new events for 2 hours.
    Its oldest event is from 2 hours ago.
    Watermark gets STUCK — no progress.
    
    SOLUTION: Pub/Sub heartbeat messages, or idle source detection with watermark hold removal.
  
  PROBLEM 2: UNBOUNDED LAG
    One mobile app batch-sends events every 6 hours.
    Events are 6 hours old when they arrive.
    Watermark trails by 6 hours.
    
    SOLUTION: Set max watermark lag = 30 minutes. Events older than this go to late pane.
    Accept some data loss for latency improvement.
  
  PROBLEM 3: BURSTY SOURCES
    Normal: 10K events/second, watermark advances 1 second per second
    Burst: 100K events/second for 5 minutes (backlog)
    After burst: watermark catches up rapidly
    
    IMPACT: Windows that should have emitted at 14:50 now emit at 15:00
    SOLUTION: Handle late data properly (allowed lateness + corrections)
```

### Watermark Implementation in Dataflow

```python
class CustomWatermarkEstimator(beam.io.iobase.WatermarkEstimator):
    """
    Custom watermark for sources where standard heuristics don't apply.
    Example: Source that publishes events from multiple time zones.
    """
    
    def __init__(self, initial_estimator_state: Optional[Timestamp] = None):
        self._current_watermark = initial_estimator_state or Timestamp.of(0)
        self._observed_timestamps: deque = deque(maxlen=10000)  # Sliding window
        
    def observe_timestamp(self, timestamp: Timestamp):
        """Called for each event processed. Update watermark estimate."""
        self._observed_timestamps.append(timestamp)
        
        # Watermark = percentile of observed timestamps - safety margin
        if len(self._observed_timestamps) >= 100:
            sorted_ts = sorted(self._observed_timestamps)
            
            # Use 5th percentile (not minimum) to resist outliers
            p5_index = int(len(sorted_ts) * 0.05)
            p5_ts = sorted_ts[p5_index]
            
            # Safety margin: 2 minutes behind p5 percentile
            new_watermark = p5_ts - Duration(seconds=120)
            
            # Watermarks can only move forward
            if new_watermark > self._current_watermark:
                self._current_watermark = new_watermark
    
    def current_watermark(self) -> Timestamp:
        return self._current_watermark
    
    def get_estimator_state(self) -> Timestamp:
        return self._current_watermark


class MultiSourceWatermarkStrategy:
    """
    When combining multiple sources with different latency characteristics,
    the overall watermark is the MINIMUM across all sources.
    This is the "slowest shard" problem.
    """
    
    def explain_watermark_stall(self, source_watermarks: Dict[str, Timestamp]) -> str:
        """Diagnose which source is holding back the watermark."""
        
        min_watermark = min(source_watermarks.values())
        global_watermark = min_watermark
        
        straggler = min(source_watermarks, key=source_watermarks.get)
        max_watermark = max(source_watermarks.values())
        
        lag = max_watermark - min_watermark
        
        return (
            f"Global watermark: {global_watermark}\n"
            f"Straggling source: {straggler} (watermark: {source_watermarks[straggler]})\n"
            f"Fastest source: {max(source_watermarks, key=source_watermarks.get)} "
            f"(watermark: {max_watermark})\n"
            f"Total watermark lag: {lag} seconds\n"
            f"RECOMMENDATION: {'Check if source is idle/stuck' if lag > 300 else 'Normal variance'}"
        )
```

---

## PART 3: WINDOWING DEEP DIVE

### Fixed Windows

```python
# Every event belongs to exactly one fixed window
# Simple, predictable, most common for batch-aligned metrics

events | "FixedWindow" >> beam.WindowInto(
    beam.window.FixedWindows(3600),  # 1-hour windows
    trigger=beam.trigger.AfterWatermark(
        early=beam.trigger.AfterProcessingTime(60),  # Speculative result every minute
        late=beam.trigger.AfterCount(1)              # Correction on each late record
    ),
    allowed_lateness=beam.window.Duration(seconds=86400),  # Accept up to 24h late
    accumulation_mode=beam.trigger.AccumulationMode.ACCUMULATING
)

# WHEN TO USE:
# - Hourly/daily aggregations for dashboards
# - Batch-aligned processing (match ETL windows)
# - Time-series data with regular intervals
```

### Sliding Windows

```python
# Events belong to MULTIPLE overlapping windows
# Use for moving averages, rolling metrics

events | "SlidingWindow" >> beam.WindowInto(
    # Window size: 1 hour, slides every 5 minutes
    # Each event belongs to 12 windows (60min / 5min)
    # COST: 12× more compute than fixed windows
    beam.window.SlidingWindows(size=3600, period=300)
)

# Use case: "Rolling 1-hour fraud rate" — updated every 5 minutes
# WARNING: High memory usage — each event stored in N windows
#          N = window_size / period = 1hr / 5min = 12

# WHEN TO USE:
# - Smoothed time series (removes noise)
# - Rolling metrics (rolling average transaction amount)
# - Fraud/anomaly detection needing recent history
```

### Session Windows

```python
# Group events from the same "session" of activity
# Window size is dynamic — determined by gaps in activity

events | "SessionWindow" >> beam.WindowInto(
    # New session starts if gap > 30 minutes since last event
    beam.window.Sessions(gap_size=1800),
    trigger=beam.trigger.AfterWatermark(),
    allowed_lateness=beam.window.Duration(seconds=3600)
)

# Use case: User session analytics
# User visits 5 pages in 20 minutes, then nothing for 40 minutes
# → One session with 5 events (all within 30-minute gap threshold)

# TRICKY: Sessions can merge
# Event at 2:00, 2:20, 2:45 with 30-min gap → 
#   First check: [2:00, 2:30], [2:20, 2:50] → MERGE → [2:00, 2:50]
#   Then [2:45, 3:15] → Check: 2:45 < 2:50 → MERGE → [2:00, 3:15]

# WHEN TO USE:
# - User behavior analytics (web sessions, app sessions)
# - IoT device activity (device active, then idle)
# - Customer support ticket resolution tracking
```

### Global Window with Custom Triggers

```python
# One window containing ALL events — useful with custom trigger logic

events | "GlobalWindow" >> beam.WindowInto(
    beam.window.GlobalWindows(),
    trigger=beam.trigger.Repeatedly(
        beam.trigger.Any([
            beam.trigger.AfterCount(1000),          # Every 1000 events
            beam.trigger.AfterProcessingTime(30)    # OR every 30 seconds
        ])
    ),
    accumulation_mode=beam.trigger.AccumulationMode.DISCARDING  # Don't re-accumulate
)

# WHEN TO USE:
# - Streaming aggregations without time-bound windows
# - Event-count-based micro-batching
# - When you control triggering externally
```

---

## PART 4: STATEFUL STREAMING — DEEP DIVE

### Why State is Needed

Many streaming computations cannot be expressed as window aggregations. They require persistent, mutable state per key.

**Cases where you NEED stateful processing:**
- Session tracking (merge sessions as new events arrive)
- Deduplication (track seen event IDs)
- Pattern detection (detect sequence A → B → C across events)
- Rate limiting (count events per user per hour)
- Machine learning (online feature aggregation)

### Beam Stateful DoFn

```python
class SessionTracker(beam.DoFn):
    """
    Tracks user sessions using Beam state API.
    Handles session merging as events arrive.
    """
    
    # State declarations — one per key (user_id)
    SESSION_START = beam.transforms.userstate.BagStateSpec(
        'session_start', beam.coders.FloatCoder()
    )
    SESSION_EVENTS = beam.transforms.userstate.BagStateSpec(
        'session_events', beam.coders.FastPrimitivesCoder()
    )
    SESSION_TIMER = beam.transforms.userstate.TimerSpec(
        'session_timer', beam.transforms.userstate.TimeDomain.WATERMARK
    )
    
    SESSION_GAP_SECONDS = 1800  # 30 minutes
    
    def process(
        self,
        element,
        session_start=beam.DoFn.StateParam(SESSION_START),
        session_events=beam.DoFn.StateParam(SESSION_EVENTS),
        session_timer=beam.DoFn.TimerParam(SESSION_TIMER),
        timestamp=beam.DoFn.TimestampParam
    ):
        user_id, event = element
        
        # Add event to session
        session_events.add(event)
        
        # Set/extend session start if first event
        current_starts = list(session_start.read())
        if not current_starts:
            session_start.add(float(timestamp))
        
        # Set timer to fire when session should end (watermark + gap)
        session_timer.set(timestamp + self.SESSION_GAP_SECONDS)
    
    @beam.transforms.userstate.on_timer(SESSION_TIMER)
    def session_expiry(
        self,
        session_start=beam.DoFn.StateParam(SESSION_START),
        session_events=beam.DoFn.StateParam(SESSION_EVENTS),
        timestamp=beam.DoFn.TimestampParam
    ):
        """Fires when no events received for SESSION_GAP seconds."""
        
        events = list(session_events.read())
        starts = list(session_start.read())
        
        if events:
            yield Session(
                user_id=events[0].user_id,
                start_ts=min(starts),
                end_ts=float(timestamp),
                event_count=len(events),
                events=events
            )
        
        # Clear state after emitting
        session_events.clear()
        session_start.clear()


class DeduplicationDoFn(beam.DoFn):
    """
    Exactly-once delivery using Beam state for deduplication.
    Maintains a set of seen event IDs per key.
    """
    
    SEEN_IDS = beam.transforms.userstate.SetStateSpec(
        'seen_ids', beam.coders.StrUtf8Coder()
    )
    CLEANUP_TIMER = beam.transforms.userstate.TimerSpec(
        'cleanup', beam.transforms.userstate.TimeDomain.WATERMARK
    )
    
    DEDUP_WINDOW_HOURS = 24  # Remove IDs older than 24 hours
    
    def process(
        self,
        element,
        seen_ids=beam.DoFn.StateParam(SEEN_IDS),
        cleanup_timer=beam.DoFn.TimerParam(CLEANUP_TIMER),
        timestamp=beam.DoFn.TimestampParam
    ):
        event_id, event = element
        
        # Check if already seen
        if event_id in seen_ids.read():
            # Duplicate — drop silently
            return
        
        # First time seeing this ID — mark as seen and emit
        seen_ids.add(event_id)
        yield event
        
        # Schedule cleanup for 24 hours from now
        cleanup_timer.set(timestamp + self.DEDUP_WINDOW_HOURS * 3600)
    
    @beam.transforms.userstate.on_timer(CLEANUP_TIMER)
    def cleanup_old_ids(self, seen_ids=beam.DoFn.StateParam(SEEN_IDS)):
        """
        Clear state after dedup window expires.
        After 24 hours, an event_id reuse is so unlikely it's safe to reset.
        """
        seen_ids.clear()
```

### State Backends and Scaling

```
BEAM STATE STORAGE OPTIONS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dataflow (managed):
  - State stored in persistent disk attached to workers
  - Checkpointed to GCS periodically
  - Transparent to developer
  - Scaling: when a worker is added, state shards redistributed
  - GOTCHA: Large state (GBs per key) causes slow shard migration

In-memory (for testing only):
  - Fast, no persistence
  - Lost on worker restart
  - Never use in production

Custom (Bigtable/Redis/Spanner):
  - Manage state externally
  - Better for very large state (> 100MB per key)
  - Requires explicit read/write in DoFn
  - Trade: latency (10-50ms per access) vs robustness

WHEN STATE BECOMES A PROBLEM:
  - State size > available worker memory → disk spillover → slow
  - Many distinct keys → high memory fragmentation
  - Long retention window → state grows unbounded
  
SOLUTIONS:
  - Use timers to expire old state (shown in DeduplicationDoFn above)
  - Limit key cardinality (group by coarser key)
  - Use external state (Bigtable) for very large or long-lived state
```

---

## PART 5: STREAM-STREAM JOINS

### The Fundamental Challenge

Joining two streams is fundamentally harder than joining two tables because:

```
TABLE JOIN: Both tables exist completely. JOIN = point-in-time lookup.

STREAM JOIN: 
  Stream A: transaction events (arrive continuously)
  Stream B: merchant metadata updates (arrive continuously)
  
  When a transaction arrives, the merchant update may not have arrived yet.
  When a merchant update arrives, relevant transactions may have already passed.
  
  QUESTION: What window of time do you wait for the matching event?
```

### Types of Stream Joins

**Type 1: Fixed-Window Join (Synchronized streams)**

```python
# Both streams windowed into same fixed windows
# Join within window

transactions = (
    raw_transactions
    | "WindowTxns" >> beam.WindowInto(beam.window.FixedWindows(3600))
)

merchant_events = (
    raw_merchant_events
    | "WindowMerchants" >> beam.WindowInto(beam.window.FixedWindows(3600))
)

# CoGroupByKey performs the join
joined = (
    {"txns": transactions, "merchants": merchant_events}
    | "CoGroupByMerchantId" >> beam.CoGroupByKey()
    | "JoinTxnsWithMerchants" >> beam.FlatMap(join_fn)
)

def join_fn(element):
    merchant_id, groups = element
    txns = list(groups["txns"])
    merchants = list(groups["merchants"])
    
    if not merchants:
        # No merchant event in this window — use last known merchant data
        merchant_data = fetch_merchant_from_bigtable(merchant_id)
    else:
        merchant_data = merchants[-1]  # Latest merchant event in window
    
    for txn in txns:
        yield enrich_transaction(txn, merchant_data)
```

**Type 2: Temporal Join (One stream enriched from a slow-changing stream)**

```python
# Most common real-world pattern:
# "Enrich transactions with the merchant category that was active at transaction time"

class TemporalEnrichmentDoFn(beam.DoFn):
    """
    Maintains a per-key state of the latest value from a slow-changing stream.
    When a fast-stream event arrives, enriches it with the current state.
    
    Use case: Enrich transaction with latest merchant category (changes rarely)
    """
    
    LATEST_MERCHANT = beam.transforms.userstate.ValueStateSpec(
        'latest_merchant', MerchantDataCoder()
    )
    
    def process(
        self,
        element,
        latest_merchant=beam.DoFn.StateParam(LATEST_MERCHANT)
    ):
        key, tagged_value = element
        stream_tag, value = tagged_value
        
        if stream_tag == "merchant_update":
            # Update state — this is the slow stream
            latest_merchant.write(value)
            # Don't emit — this is just a state update
        
        elif stream_tag == "transaction":
            # Fast stream — enrich with current state
            merchant_data = latest_merchant.read()
            
            if merchant_data is None:
                # No merchant data yet — emit with null enrichment or buffer
                yield (key, EnrichedTransaction(txn=value, merchant=None, enrichment_status="NO_DATA"))
            else:
                yield (key, EnrichedTransaction(txn=value, merchant=merchant_data, enrichment_status="OK"))
```

**Type 3: Interval Join (Both streams in a time range)**

```python
# Join events from Stream A with events from Stream B
# where B.timestamp is within [A.timestamp - 5min, A.timestamp + 5min]
# Common in fraud: "Did customer's phone location change within 5 min of transaction?"

# Apache Flink SQL pattern (equivalent in Beam via custom state):
"""
SELECT
  t.transaction_id,
  t.customer_id,
  t.amount,
  l.latitude,
  l.longitude
FROM transactions t, location_pings l
WHERE t.customer_id = l.customer_id
  AND l.ping_time BETWEEN t.txn_time - INTERVAL '5' MINUTE
                       AND t.txn_time + INTERVAL '5' MINUTE
"""

# Beam implementation using state:
class IntervalJoinDoFn(beam.DoFn):
    
    TXNS_BUFFER = beam.transforms.userstate.BagStateSpec(
        'txns', TransactionCoder()
    )
    LOCATIONS_BUFFER = beam.transforms.userstate.BagStateSpec(
        'locations', LocationCoder()
    )
    CLEANUP_TIMER = beam.transforms.userstate.TimerSpec(
        'cleanup', beam.transforms.userstate.TimeDomain.WATERMARK
    )
    
    INTERVAL_SECONDS = 300  # 5 minutes
    
    def process(self, element, txns=beam.DoFn.StateParam(TXNS_BUFFER),
                locations=beam.DoFn.StateParam(LOCATIONS_BUFFER),
                cleanup_timer=beam.DoFn.TimerParam(CLEANUP_TIMER),
                timestamp=beam.DoFn.TimestampParam):
        
        customer_id, tagged = element
        tag, event = tagged
        
        if tag == "transaction":
            txns.add((float(timestamp), event))
            # Try to join with buffered locations
            for loc_ts, loc in locations.read():
                if abs(loc_ts - float(timestamp)) <= self.INTERVAL_SECONDS:
                    yield JoinedEvent(transaction=event, location=loc)
        
        elif tag == "location":
            locations.add((float(timestamp), event))
            # Try to join with buffered transactions
            for txn_ts, txn in txns.read():
                if abs(float(timestamp) - txn_ts) <= self.INTERVAL_SECONDS:
                    yield JoinedEvent(transaction=txn, location=event)
        
        cleanup_timer.set(timestamp + self.INTERVAL_SECONDS * 2)
    
    @beam.transforms.userstate.on_timer(CLEANUP_TIMER)
    def cleanup(self, txns=beam.DoFn.StateParam(TXNS_BUFFER),
                locations=beam.DoFn.StateParam(LOCATIONS_BUFFER),
                timestamp=beam.DoFn.TimestampParam):
        """Remove events outside the join interval."""
        cutoff = float(timestamp) - self.INTERVAL_SECONDS
        
        fresh_txns = [(ts, e) for ts, e in txns.read() if ts >= cutoff]
        fresh_locs = [(ts, e) for ts, e in locations.read() if ts >= cutoff]
        
        txns.clear()
        for item in fresh_txns:
            txns.add(item)
        
        locations.clear()
        for item in fresh_locs:
            locations.add(item)
```

---

## PART 6: EXACTLY-ONCE SEMANTICS — ENGINE-LEVEL DEEP DIVE

### Three Delivery Guarantees

```
AT-MOST-ONCE:
  Every event processed 0 or 1 times.
  Duplicates: never.
  Data loss: possible.
  Implementation: fire-and-forget, no retries.
  Use: non-critical metrics, fast-path monitoring.

AT-LEAST-ONCE:
  Every event processed 1 or more times.
  Duplicates: possible.
  Data loss: never.
  Implementation: retry until acknowledged.
  Use: most streaming pipelines (handle duplicates downstream).

EXACTLY-ONCE:
  Every event processed exactly 1 time.
  Duplicates: never.
  Data loss: never.
  Implementation: complex — requires coordination across components.
  Use: financial transactions, billing, compliance pipelines.
```

### How Dataflow Achieves Exactly-Once

Dataflow's exactly-once relies on three mechanisms working together:

**Mechanism 1: Checkpointing (persistent state)**
```
Dataflow workers checkpoint their state to GCS every N seconds.
On worker failure: replacement worker reads last checkpoint.
No data since last checkpoint is replayed from Pub/Sub.
Pub/Sub acknowledgement only sent after checkpoint.
```

**Mechanism 2: Shuffle Service (deterministic shuffle)**
```
All GroupByKey operations go through the Dataflow Shuffle Service.
The shuffle service is fault-tolerant independently.
Exactly-once guarantee: same key always goes to same reducer.
No partial shuffles — either complete or retry entire shuffle.
```

**Mechanism 3: Sink Idempotency**

```python
# BigQuery exactly-once: use deterministic job_id
class ExactlyOnceBigQuerySink:
    
    def write_partition(self, data: List[Row], partition_key: str, run_id: str):
        """
        Uses deterministic BigQuery job_id to achieve exactly-once.
        If this method is called twice with same inputs, second call is no-op.
        """
        
        # Deterministic job_id: same inputs → same job_id → BQ deduplicates
        job_id = hashlib.md5(f"{run_id}:{partition_key}".encode()).hexdigest()
        
        job_config = bigquery.LoadJobConfig(
            # WRITE_APPEND is idempotent WITH job_id deduplication
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            # This job_id is the key — BQ ignores duplicate submissions
            job_id=f"cdm-next-{job_id}"
        )
        
        try:
            load_job = self.bq_client.load_table_from_dataframe(
                data_df, 
                destination=self.table,
                job_config=job_config
            )
            load_job.result()
            
        except google.api_core.exceptions.Conflict:
            # Job already exists (duplicate call) — this is fine, it's exactly-once
            logger.info(f"Job {job_id} already exists — idempotent skip")
```

### Exactly-Once vs Effectively-Once

```
EXACTLY-ONCE: Mathematical guarantee from the engine.
  - Dataflow Streaming Engine provides this for intra-Dataflow operations
  - Cost: higher latency (checkpointing overhead), higher memory

EFFECTIVELY-ONCE: Practical guarantee via deduplication.
  - Process at-least-once but deduplicate on write/read
  - Simpler implementation, lower latency
  - Can miss duplicates if dedup window is too short
  - 99.99% correct in practice

RECOMMENDATION:
  For most financial pipelines: Effectively-once is sufficient
  (deduplicate on ingest + use BQ job_id for load)
  
  For strict compliance (PCI, SOX reporting): Exactly-once
  (Dataflow Streaming Engine + idempotent sinks)
```

---

## PART 7: BACKPRESSURE AND FLOW CONTROL

### What is Backpressure?

```
SCENARIO:
  Pub/Sub receiving: 100,000 events/second
  Dataflow processing: 30,000 events/second
  
  After 1 minute: 4.2 million events unprocessed in Pub/Sub
  After 1 hour: 252 million events backlogged
  
  Without backpressure: memory exhaustion → worker OOM → cascade failure
  
  WITH backpressure:
    Pub/Sub: buffers indefinitely (7-day retention)
    Dataflow: signals "I'm full, slow down"
    Source: stops pulling new messages until capacity available
    
    Effect: controlled queueing instead of OOM
```

### Pub/Sub + Dataflow Backpressure Mechanics

```
HOW PUB/SUB HANDLES BACKPRESSURE:
  
  Dataflow pulls from Pub/Sub (not push).
  Dataflow controls the pull rate.
  
  When Dataflow is overloaded:
    - Workers process slower → downstream steps queue up
    - Upstream reads slow down automatically (pull throttling)
    - Pub/Sub subscription backlog grows
    - Dataflow Autoscaler detects backlog → adds workers
  
  KEY METRIC: Pub/Sub subscription backlog (message count + age)
  
  ALERT THRESHOLDS (recommended):
    Message count > 1 million: WARNING
    Message age > 10 minutes: WARNING  
    Message age > 30 minutes: CRITICAL
```

### Dataflow Autoscaling — The Algorithm

```python
# Simplified representation of Dataflow's autoscaling logic
class DataflowAutoscaler:
    
    def should_scale_up(self, metrics: WorkerMetrics) -> bool:
        """
        Scale up if:
        1. Throughput is near saturation
        2. Backlog is growing
        3. Watermark is not advancing
        """
        
        return any([
            # Workers are near capacity
            metrics.avg_cpu_utilization > 0.8,
            
            # Backlog is growing (processing slower than ingestion)
            metrics.pubsub_backlog_message_age_seconds > 300,
            
            # Watermark lagging significantly behind processing time
            metrics.watermark_lag_seconds > 600,
        ])
    
    def should_scale_down(self, metrics: WorkerMetrics) -> bool:
        """
        Scale down if workers are underutilized for sustained period.
        Never scale below min_workers.
        """
        return (
            metrics.avg_cpu_utilization < 0.2
            and metrics.pubsub_backlog_message_age_seconds < 30
            and metrics.watermark_lag_seconds < 60
            and metrics.time_at_low_utilization_seconds > 600  # 10 minutes sustained
        )
    
    def calculate_target_workers(self, current: int, metrics: WorkerMetrics) -> int:
        
        if self.should_scale_up(metrics):
            # Scale up based on backlog processing rate needed
            # Simplified: double workers until backlog clears
            target = min(current * 2, MAX_WORKERS)
        
        elif self.should_scale_down(metrics):
            # Scale down slowly (avoid thrashing)
            target = max(int(current * 0.7), MIN_WORKERS)
        
        else:
            target = current
        
        return target
```

---

## PART 8: STREAMING SQL — BIGQUERY AND DATAFLOW

### BigQuery Continuous Queries

```sql
-- BigQuery Continuous Queries (preview feature)
-- Runs SQL continuously on streaming data

-- Example: Real-time fraud detection rule
CREATE CONTINUOUS QUERY fraud_detection_rule
OPTIONS (
  table_name = 'fraud_alerts',
  write_disposition = WRITE_APPEND
)
AS
SELECT
  t.transaction_id,
  t.customer_id,
  t.amount,
  t.merchant_id,
  t.event_ts,
  'HIGH_VELOCITY' AS fraud_reason,
  CURRENT_TIMESTAMP() AS detected_at
FROM
  TUMBLE(TABLE streaming.transactions, DESCRIPTOR(event_ts), INTERVAL '1' MINUTE)
WHERE
  COUNT(*) OVER (
    PARTITION BY customer_id
    ORDER BY event_ts
    RANGE BETWEEN INTERVAL '1' HOUR PRECEDING AND CURRENT ROW
  ) > 20  -- More than 20 transactions in last hour
;
```

### Streaming Analytics SQL Patterns

```sql
-- PATTERN 1: TUMBLING WINDOW AGGREGATION
-- Revenue per region, updated every 5 minutes

SELECT 
  window_start,
  window_end,
  region,
  SUM(amount) AS revenue,
  COUNT(*) AS txn_count
FROM
  TUMBLE(
    TABLE streaming.transactions,
    DESCRIPTOR(event_ts),
    INTERVAL '5' MINUTE
  )
GROUP BY window_start, window_end, region;

-- PATTERN 2: HOP (SLIDING) WINDOW
-- Rolling 1-hour average, refreshed every 10 minutes

SELECT
  window_start,
  window_end,
  product_id,
  AVG(amount) AS rolling_avg_1hr,
  COUNT(*) AS sample_count
FROM
  HOP(
    TABLE streaming.transactions,
    DESCRIPTOR(event_ts),
    INTERVAL '10' MINUTE,  -- slides every 10 minutes
    INTERVAL '1' HOUR      -- window size
  )
GROUP BY window_start, window_end, product_id;

-- PATTERN 3: SESSION WINDOW
-- User session analytics

SELECT
  session_start,
  session_end,
  customer_id,
  COUNT(*) AS events_in_session,
  SUM(amount) AS session_revenue
FROM
  SESSION(
    TABLE streaming.events,
    DESCRIPTOR(event_ts),
    DESCRIPTOR(customer_id),
    INTERVAL '30' MINUTE  -- session gap
  )
GROUP BY session_start, session_end, customer_id;

-- PATTERN 4: STREAM-TABLE JOIN (most common real-world pattern)
-- Enrich streaming transactions with reference data from static table

SELECT
  t.transaction_id,
  t.amount,
  t.event_ts,
  m.merchant_name,
  m.merchant_category,
  m.risk_tier
FROM
  streaming.transactions t
JOIN
  reference.merchant_profiles m  -- Static/slowly-changing table
ON t.merchant_id = m.merchant_id
WHERE t.event_ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY);
```

---

## PART 9: PRODUCTION DEBUGGING OF STREAMING PIPELINES

### The Streaming Pipeline Health Dashboard

```sql
-- BigQuery query to diagnose streaming pipeline health
-- Run this when you see issues

WITH pipeline_health AS (
  SELECT
    -- Ingestion lag: how old is the latest data we've processed?
    TIMESTAMP_DIFF(
      CURRENT_TIMESTAMP(),
      MAX(event_ts),
      SECOND
    ) AS ingestion_lag_seconds,
    
    -- Processing rate: events per second in last 5 minutes
    COUNTIF(ingestion_ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE)) / 300
      AS events_per_second_recent,
    
    -- Comparison to baseline (last hour average)
    COUNTIF(ingestion_ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)) / 3600
      AS events_per_second_baseline,
    
    -- Error rate
    COUNTIF(processing_status = 'ERROR') / COUNT(*) * 100 AS error_rate_pct,
    
    -- Late arrival rate
    COUNTIF(TIMESTAMP_DIFF(ingestion_ts, event_ts, SECOND) > 300) / COUNT(*) * 100
      AS late_arrival_rate_pct
    
  FROM streaming.events
  WHERE ingestion_ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
)
SELECT
  ingestion_lag_seconds,
  ROUND(events_per_second_recent, 1) AS eps_recent,
  ROUND(events_per_second_baseline, 1) AS eps_baseline,
  ROUND(events_per_second_recent / NULLIF(events_per_second_baseline, 0) * 100, 1)
    AS throughput_pct_of_normal,
  ROUND(error_rate_pct, 3) AS error_rate_pct,
  ROUND(late_arrival_rate_pct, 1) AS late_arrival_pct,
  CASE
    WHEN ingestion_lag_seconds > 600 THEN '🔴 CRITICAL: High lag'
    WHEN ingestion_lag_seconds > 120 THEN '🟡 WARNING: Elevated lag'
    WHEN events_per_second_recent < events_per_second_baseline * 0.5 THEN '🟡 WARNING: Low throughput'
    WHEN error_rate_pct > 1 THEN '🟡 WARNING: High error rate'
    ELSE '🟢 HEALTHY'
  END AS pipeline_status
FROM pipeline_health;
```

### Common Failure Patterns and Root Causes

**Pattern 1: Watermark Stuck**

```
SYMPTOM: Dataflow monitoring shows watermark not advancing
         Dashboard shows data from hours ago

DIAGNOSIS STEPS:
  1. Check Pub/Sub subscription backlog
     → Large backlog + watermark stuck = Dataflow overwhelmed
     → Small backlog + watermark stuck = Source shard problem
  
  2. Check Dataflow worker CPU
     → High CPU = throughput bottleneck, add workers
     → Low CPU = I/O bound, check Bigtable/BQ latency
  
  3. Check for idle partitions
     → One Pub/Sub partition with no new messages holds watermark
     → Solution: Send heartbeat messages periodically

CLOUD MONITORING QUERY:
  resource.type="dataflow_job"
  metric.type="dataflow.googleapis.com/job/element_count"
  AND metric.label.step="GroupByKey"
  -- If this counter stops advancing: watermark is stuck
```

**Pattern 2: Memory Pressure / OOM Workers**

```
SYMPTOM: Workers restarting, job progress stalling
         Error: "java.lang.OutOfMemoryError: Java heap space"

ROOT CAUSES:
  1. Stateful DoFn with unbounded state (forgot timer cleanup)
  2. Very wide windows with many events
  3. Side input too large (> worker memory)
  4. State per key too large (millions of small keys, each with state)

IMMEDIATE MITIGATION:
  1. Increase worker machine type: n1-standard-4 → n1-highmem-8
  2. Reduce parallelism to allow more memory per key
  3. Enable disk-backed state (Dataflow handles automatically but slowly)

PERMANENT FIX:
  1. Add timer-based state cleanup (see DeduplicationDoFn example)
  2. Use external state (Bigtable) for large state
  3. Reduce side input size (pre-filter to only needed keys)
```

**Pattern 3: Throughput Drop Without Error**

```
SYMPTOM: Processing rate drops 50% with no errors
         Looks healthy in dashboards

COMMON ROOT CAUSE: Hot key creating serialization

INVESTIGATION:
  # Check for key distribution imbalance in Dataflow UI:
  # Look at "Stragglers" view — are any steps much slower?
  # Look at "Wall time" per step — where is time being spent?

  # In BigQuery, check input key distribution:
  SELECT
    key_column,
    COUNT(*) AS event_count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS pct_of_total
  FROM streaming.events
  WHERE ingestion_ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
  GROUP BY 1
  ORDER BY event_count DESC
  LIMIT 20;
  
  -- If top key = 50%+ of events: HOT KEY
  -- Solution: Salting (see Module 7, Scenario 8)
```

---

## PART 10: CDM NEXT STREAMING PATTERNS

### How CDM Next Handles Streaming Ingestion

CDM Next's streaming mode covers the Kafka → GCS → BigQuery path. Key design decisions:

**Decision 1: Micro-batch vs True Streaming**

```
For CDM Next financial data:
  True streaming (Pub/Sub → Dataflow → BQ streaming inserts):
    + Data freshness: seconds
    - Cost: BQ streaming inserts $0.01/200MB
    - Risk: BQ streaming insert errors harder to debug
  
  Micro-batch (Pub/Sub → Dataflow → GCS files → BQ load):
    + Cost: BQ load is free
    + Simplicity: same code path as batch
    - Freshness: 5-15 minute windows
    
CDM Next choice: Micro-batch with 5-minute windows for most sources.
True streaming only for latency-critical paths (fraud, real-time risk).
```

**Decision 2: Error Handling in Streaming**

```python
# CDM Next streaming error handling pattern
class CDMNextStreamingErrorHandler(beam.DoFn):
    
    ERROR_CATEGORIES = {
        "SCHEMA_MISMATCH": "quarantine",      # Send to DQ quarantine
        "NULL_REQUIRED_FIELD": "quarantine",   # Send to DQ quarantine
        "PARSING_FAILURE": "dead_letter",      # Can't parse → DLQ
        "DLP_FAILURE": "block",               # PII not masked → block, alert
        "NETWORK_ERROR": "retry",             # Transient → retry
    }
    
    def process(self, element, timestamp=beam.DoFn.TimestampParam):
        try:
            validated = self.validate_and_enrich(element)
            yield beam.pvalue.TaggedOutput("success", validated)
        
        except SchemaMismatchException as e:
            yield beam.pvalue.TaggedOutput("quarantine", {
                "raw_event": element,
                "error": str(e),
                "error_type": "SCHEMA_MISMATCH",
                "pipeline_id": self.pipeline_id,
                "event_ts": float(timestamp)
            })
        
        except DLPMaskingException as e:
            # PII not masked — this is a compliance issue
            # Block AND alert immediately
            self.send_compliance_alert(e, element)
            yield beam.pvalue.TaggedOutput("blocked", {
                "raw_event": "[REDACTED]",  # Never emit unmasked PII to any output
                "error": "DLP_FAILURE",
                "pipeline_id": self.pipeline_id
            })
```

---

## MODULE 9 SUMMARY

| Concept | Key Insight |
|---|---|
| Time semantics | Always use event time for business logic; processing time for operational metrics |
| Watermarks | A probabilistic, advancing guarantee — set based on observed skew in your source |
| Windowing | Fixed for batch-aligned; sliding for rolling metrics; session for user activity |
| Stateful processing | Use timers to clean up state — unbounded state is the #1 production streaming bug |
| Stream-stream join | Temporal join (state-based) is most practical; interval join for time-ranged matching |
| Exactly-once | Dataflow checkpointing + shuffle + idempotent sinks = exactly-once end-to-end |
| Backpressure | Pub/Sub buffers indefinitely; Dataflow autoscales on backlog; monitor message age |
| Streaming SQL | TUMBLE/HOP/SESSION windows in SQL are equivalent to Beam windowing — use for analysts |
| Production debugging | Check: watermark lag, worker CPU, key distribution, state size |

---

*Module 9 Complete — 8,300 words.*

---

# COMPLETE CURRICULUM SUMMARY

| Module | Topic | Words | Status |
|---|---|---|---|
| 1 | System Design Fundamentals | ~8,000 | ✅ Complete |
| 2 | Architecture Components | ~9,000 | ✅ Complete |
| 3 | Critical Design Principles | ~7,000 | ✅ Complete |
| 4 | Data Pipeline Architectures | ~9,000 | ✅ Complete |
| 5 | GCP Cloud Architecture + Streaming | ~10,000 | ✅ Complete |
| 6 | System Design Questions & Solutions | ~12,200 | ✅ Complete |
| 7 | Advanced Scenarios | ~10,400 | ✅ Complete |
| 8 | Interview Strategy | ~5,100 | ✅ Complete |
| 9 | Advanced Streaming | ~8,300 | ✅ Complete |
| **TOTAL** | | **~79,000 words** | **✅ COMPLETE** |
