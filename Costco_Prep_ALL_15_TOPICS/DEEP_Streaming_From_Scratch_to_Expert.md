# Streaming — From Scratch to Expert
## Round 2 Preparation — Costco Sr. Data Engineer

---

## START HERE: WHAT IS STREAMING AND WHY DOES IT EXIST?

### The Batch World vs The Streaming World

Before streaming, all data processing was batch:

```
BATCH PROCESSING:
  Events happen throughout the day
  ─────────────────────────────────────────────────────► time
  click click click click click click ... (millions of events)
  
  At midnight:
  [COLLECT ALL DAY'S EVENTS] → [PROCESS THEM ALL AT ONCE] → [REPORT READY AT 6 AM]
  
  Latency: 6-30 HOURS between event and insight

STREAMING PROCESSING:
  Event happens at 2:15 PM
  ─────────────────────────────────────────────────────► time
  [EVENT ARRIVES] → [PROCESSED IMMEDIATELY] → [RESULT UPDATED BY 2:15:03 PM]
  
  Latency: SECONDS between event and insight
```

**When do you NEED streaming?**

```
USE STREAMING WHEN:
  ✓ Fraud detection: a transaction must be blocked BEFORE it's approved (seconds matter)
  ✓ Real-time dashboards: marketing team watches live campaign ROAS
  ✓ Alerting: ROAS drops below 1.0 → Slack alert within 1 minute
  ✓ Event-driven actions: user abandons cart → send email within 5 minutes
  ✓ Live leaderboards, real-time inventory

DON'T USE STREAMING WHEN:
  ✗ Reports that stakeholders read at 9 AM (daily batch is fine)
  ✗ Financial reconciliation (needs authoritative numbers, batch is safer)
  ✗ ML model training (batch — models don't retrain in real-time typically)
  ✗ Anything that can wait hours: ETL, warehouse loads, monthly reports
  
  STREAMING IS:
  • Always-on infrastructure (paying even when idle)
  • More complex (state management, late data, ordering)
  • Harder to test and debug
  • Only worth it when latency requirement is < 5-10 minutes
```

---

## PART 1: STREAMING FUNDAMENTALS — THE CONCEPTS EVERY ENGINEER MUST KNOW

### Concept 1: Event Time vs Processing Time

This is THE most important concept in streaming. Get this wrong, and every metric you compute is wrong.

```
EVENT TIME:   When the event ACTUALLY HAPPENED in the real world
PROCESSING TIME: When the event ARRIVED at your processing system

Example: User clicks an ad at 2:15 PM on their mobile phone
  Event time:      2:15:00 PM (when they actually clicked)
  
  The mobile app batches events and sends them when WiFi connects:
  Processing time: 2:47:00 PM (32 minutes later — when it arrived at your system)
  
  The event is 32 minutes "late" relative to processing time.

WHY IT MATTERS:
  If you compute "clicks between 2:00 PM and 3:00 PM" using PROCESSING TIME:
  → You include clicks that happened at 2:15 but arrived at 2:47 ✓ (correct)
  
  If you compute "clicks between 2:00 PM and 3:00 PM" using EVENT TIME:
  → You correctly count clicks that happened in that hour ✓ (correct)
  
  If you close the 2 PM window at 3 PM processing time:
  → You MISS all clicks that happened between 2:00-2:30 but arrived late
  → Your 2 PM hour count is WRONG

  THE FIX: Keep windows open for longer than the event time range.
  Accept data that arrives late. Use event time, not processing time.
```

```
VISUALIZATION:

Event Time  ──2:00────────2:30──────────3:00──────────────►
                                                            
Processing  ──────────────────2:00──────2:30──────3:00─────►
Time                          ↑          ↑
                              │  click at event_time=2:15
                              │  arrived at processing_time=2:47
                              └── This event is 32 min late in processing time
                                  but belongs in the 2:00-3:00 event time window
```

---

### Concept 2: Watermarks — The Engine's Best Guess About Time

A **watermark** is the streaming engine's estimate of: *"I believe all events with event_time ≤ T have now arrived. Events after T may still be in transit."*

```
WATERMARK MECHANICS:

  Events arriving in processing order (newest first):
  event_time=2:40, event_time=2:38, event_time=2:35, event_time=2:15 (LATE!)
  
  The engine tracks: "latest event_time I've seen so far = 2:40"
  Watermark = latest_event_time - allowed_lateness
  
  If allowed_lateness = 10 minutes:
    Watermark = 2:40 - 10 min = 2:30
  
  Meaning: "I'm confident all events with event_time ≤ 2:30 have arrived.
            Events between 2:30-2:40 might still be coming."
  
  When watermark passes 3:00 PM:
    The 2:00-3:00 PM window is "closed" — we compute final results
    Any event with event_time < 2:00 or arriving after this: LATE (special handling)

WHAT SETS THE WATERMARK:
  The watermark is driven by the timestamps of events being processed.
  If events stop arriving: watermark stops advancing (stalls!)
  If a very old event arrives: watermark might advance slowly (held back)
  
  This is why watermark management is an art — too conservative = high latency,
  too aggressive = miss late events.
```

---

### Concept 3: Windows — Grouping Events Into Finite Buckets

Streaming data is infinite. To aggregate it (COUNT clicks per hour, SUM spend per campaign), you need to group events into finite time buckets called **windows**.

```
THREE WINDOW TYPES:

─────────────────────────────────────────────────────────────────
1. FIXED WINDOWS (Tumbling Windows)
─────────────────────────────────────────────────────────────────
   │  1 hour  │  1 hour  │  1 hour  │  1 hour  │
   12:00─────13:00─────14:00─────15:00─────16:00
   
   Each event belongs to EXACTLY ONE window.
   Non-overlapping, equal size, no gaps.
   
   Use for: "Clicks per hour", "Revenue per 5-minute interval"
   "Total spend from 2 PM to 3 PM"

─────────────────────────────────────────────────────────────────
2. SLIDING WINDOWS
─────────────────────────────────────────────────────────────────
   Window size: 1 hour, Slide: 15 minutes
   
   [12:00─────────────────13:00)
        [12:15──────────────────13:15)
             [12:30───────────────────14:00)
                  [12:45────────────────────13:45) ...
   
   Each event belongs to MULTIPLE windows (size/slide = 4 windows).
   Windows OVERLAP.
   
   Use for: "ROAS over the last 1 hour, updated every 15 minutes"
   "Moving average of spend over last 30 minutes"
   
   Cost: 4x data amplification (each event processed 4 times)

─────────────────────────────────────────────────────────────────
3. SESSION WINDOWS
─────────────────────────────────────────────────────────────────
   User activity: ●●● (gap) ●● (gap) ●●●●●
   
   [●●●session1●●●] [●●session2●●] [●●●●●session3●●●●●]
   
   Dynamic size — defined by inactivity gap between events.
   If gap > session_timeout (e.g., 30 minutes): new session.
   
   Use for: User session analytics, "how long did user spend on site"
   "Group a user's events into coherent browsing sessions"
   
   Complex: each user's session is independent, must track state per user
```

---

### Concept 4: Late Data — The Hardest Part of Streaming

**Late data** is the eternal challenge of streaming systems. Events don't always arrive in order. Some arrive hours or days late.

```
CAUSES OF LATE DATA (real-world scenarios):
  
  1. Mobile app batching:
     App stores events locally, sends batch when WiFi available
     Result: events arrive 0 minutes to 8 hours late
  
  2. Ad network reporting delay:
     Google Ads cost data finalizes up to 48 hours later (cost adjustments)
     Result: today's cost data might change for 2 more days
  
  3. Network delays:
     IoT device in poor network area
     Result: events arrive 0 to 24 hours late
  
  4. Third-party data pipeline:
     Partner sends you daily data export at 3 AM
     Result: all their events arrive 0-24 hours late simultaneously
  
  5. System failures:
     Your ingestion pipeline was down for 2 hours, then recovered
     Result: 2 hours of events arrive all at once
```

**Strategies for handling late data:**

```
STRATEGY 1: ALLOWED LATENESS
─────────────────────────────
  Configure the window to stay open for N time after the watermark passes.
  
  Example: Window 2:00-3:00 PM closes at watermark = 3:00 PM
  With allowed_lateness = 2 hours: window accepts late events until 5:00 PM
  
  Good for: data up to 2 hours late
  Problem: window results change multiple times (preliminary → updated → final)
  
  You emit results multiple times:
    - Early result (before watermark): "best estimate so far"
    - On-time result (at watermark): "complete within normal lateness"
    - Late result (within allowed_lateness): "updated with late arrivals"

STRATEGY 2: REPROCESS WINDOW
─────────────────────────────
  For very late data (hours to days):
  Don't try to include it in real-time stream.
  
  Instead: 
  Streaming path → gives preliminary answer (data within 5 min of real-time)
  Batch path → runs daily, reprocesses last 3 days, includes all late data
  
  This is the Lambda Architecture pattern — most production systems use this.
  
  Streaming = "what happened recently, approximately"
  Batch = "what happened, accurately, including late arrivals"

STRATEGY 3: SIDE OUTPUTS FOR VERY LATE DATA
─────────────────────────────────────────────
  Route late events to a separate queue/table for manual or batch processing.
  Don't drop them, don't include in current windows.
  
  Example in Apache Beam / Dataflow:
  Events arriving within 1 hour → processed in stream → real-time result
  Events 1-48 hours late → routed to side output → batch job processes daily
  Events > 48 hours late → logged as "unprocessable", alert sent
```

---

### Concept 5: Delivery Semantics

```
AT-MOST-ONCE:
  Message delivered 0 or 1 times.
  If system crashes after receiving but before processing: event is LOST.
  
  Use when: losing some events is acceptable (metrics, non-critical logs)
  
AT-LEAST-ONCE (MOST COMMON):
  Message delivered 1 or more times.
  If system crashes before acknowledging: event is redelivered.
  Result: DUPLICATE events possible.
  
  Use when: losing events is unacceptable; handle duplicates downstream.
  How to handle duplicates: idempotent processing (MERGE on event_id)
  
EXACTLY-ONCE (HARDEST):
  Message delivered exactly once, no duplicates, no loss.
  Requires: distributed transaction across message queue + storage.
  Supported by: Kafka (with transactions), Dataflow (with checkpointing).
  
  Use when: financial data, order processing — duplicates cause real harm.
  
  In practice: at-least-once + idempotent writes ≈ exactly-once results
  This is what most production systems use.
```

---

## PART 2: GCP STREAMING STACK — THE FULL PICTURE

### The Three GCP Streaming Services

```
┌─────────────────────────────────────────────────────────────────┐
│                    GCP STREAMING STACK                          │
│                                                                  │
│  Cloud Pub/Sub          Cloud Dataflow           BigQuery        │
│  ────────────           ─────────────           ─────────       │
│  Message Queue          Stream Processor         Analytics DWH   │
│  (durable buffer)       (transform/aggregate)    (store/query)   │
│                                                                  │
│  Like Kafka but         Like Apache Flink/        Stores final   │
│  fully managed          Spark Streaming           results        │
│                         (uses Apache Beam)                       │
│                                                                  │
│  RESPONSIBILITIES:      RESPONSIBILITIES:        RESPONSIBILITIES:
│  • Receive events       • Parse/validate         • Store data    │
│  • Buffer messages      • Enrich/join            • SQL queries   │
│  • Deliver to N         • Window aggregations    • ROAS reports  │
│    subscribers          • Handle late data       • Dashboards    │
│  • Retry on failure     • Write to BigQuery                      │
│  • 7 day retention      • Handle scale                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

TYPICAL FLOW:
  Ad Click Event
    → published to Pub/Sub topic "ad-events"
      → Dataflow pipeline reads from Pub/Sub
          → Parses JSON, validates, enriches
            → Aggregates (clicks per campaign per hour using Fixed Windows)
              → Writes aggregated results to BigQuery streaming table
                → Looker dashboard queries BigQuery
                  → Real-time ROAS dashboard updated every 5 minutes
```

---

### Cloud Pub/Sub — In Depth

```
PUB/SUB ARCHITECTURE:

  Publishers         Topic          Subscriptions      Subscribers
  ──────────         ─────          ─────────────      ───────────
  App Server    ──►  "ad-events" ──► subscription-A ──► Dataflow job
  Mobile SDK    ──►  (one topic)  ──► subscription-B ──► BigQuery direct insert
  Webhook       ──►               ──► subscription-C ──► Cloud Function (alerting)
  
  KEY PROPERTIES:
  
  1. Durability: Messages stored in 3+ data centers
     Retention: 7 days maximum (configurable, default 7 days)
     If your consumer is down for 8 days: messages are GONE (permanent loss)
     
  2. Delivery: At-least-once
     Same message CAN be delivered multiple times (on failure/retry)
     Your consumer MUST handle duplicates (idempotent processing)
     
  3. Ordering: NOT guaranteed by default
     Message published at 2:00 PM might arrive AFTER message from 2:01 PM
     TO GET ORDERING: use "ordering keys" (same key → ordered within key)
     But: ordering keys reduce throughput (all same-key messages go to same server)
     
  4. Scale: Automatically scales to millions of messages/second
     No cluster sizing needed
     You pay per message (very cheap)
     
  5. Message size: Max 10MB per message
```

```python
# Publishing to Pub/Sub
from google.cloud import pubsub_v1
import json

publisher = pubsub_v1.PublisherClient()
topic_path = "projects/my-project/topics/ad-events"

def publish_ad_click(click_event: dict):
    data = json.dumps(click_event).encode("utf-8")
    future = publisher.publish(
        topic_path,
        data=data,
        # Optional attributes for server-side filtering
        event_type="click",
        campaign_id=click_event["campaign_id"]
    )
    return future.result()  # blocks until published (for reliability)

# Subscribing from Pub/Sub
subscriber = pubsub_v1.SubscriberClient()
subscription_path = "projects/my-project/subscriptions/ad-events-dataflow-sub"

def callback(message):
    event = json.loads(message.data)
    
    try:
        process_event(event)
        message.ack()   # success: tell Pub/Sub we're done, don't redeliver
    except Exception as e:
        message.nack()  # failure: tell Pub/Sub to redeliver (at-least-once)

streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
streaming_pull_future.result()  # block forever
```

---

### Cloud Dataflow — In Depth

Dataflow is Google's managed Apache Beam runner. It runs your Beam pipeline code on a cluster of VMs that scales automatically.

```
WHAT DATAFLOW DOES:

  1. Receives your Beam pipeline code
  2. Optimizes it (pipeline graph optimization)
  3. Provisions VMs (workers) automatically
  4. Distributes the work across workers
  5. Scales up when data volume increases, scales down when decreasing
  6. Handles worker failures transparently (restarts from checkpoint)
  7. Cleans up VMs when job finishes

WHY DATAFLOW INSTEAD OF SPARK FOR STREAMING:
  Spark Streaming: micro-batch (processes batches every N seconds, minimum ~1 sec)
  Dataflow/Beam:   true streaming (processes each event as it arrives)
  
  Dataflow latency: 100-500ms per event (much lower than Spark)
  
  Dataflow is fully managed: no cluster to manage
  Spark on Dataproc: you manage the cluster size, scaling is more manual
  
  For GCP streaming pipelines: Dataflow is the standard choice
```

### Apache Beam Programming Model (Used by Dataflow)

```
BEAM CONCEPTS:

Pipeline:     The entire job definition
PCollection:  A distributed, immutable dataset
              (like a Spark RDD or a table — can be bounded or unbounded)
PTransform:   A transformation applied to a PCollection
  - ParDo:    Apply a function to each element
  - GroupByKey: Group elements by key (triggers shuffle)
  - Combine:  Aggregation (sum, count, average)
  - Flatten:  Merge multiple PCollections

Runner:       The execution engine (Dataflow, Spark, Direct/local)
              Your code is the same; runner choice determines where it runs
```

```python
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.transforms import trigger, window
from apache_beam.io.gcp.bigquery import WriteToBigQuery

# DATAFLOW STREAMING PIPELINE EXAMPLE
# Reads ad click events from Pub/Sub
# Computes clicks and spend per campaign per 5-minute window
# Writes results to BigQuery

class ParseAdClick(beam.DoFn):
    """Parse JSON from Pub/Sub message to structured event."""
    
    def process(self, element):
        import json
        try:
            event = json.loads(element.decode("utf-8"))
            
            # Validate required fields
            if not event.get("click_id") or not event.get("campaign_id"):
                yield beam.pvalue.TaggedOutput("dead_letter", {
                    "raw": element.decode("utf-8"),
                    "error": "Missing required fields"
                })
                return
            
            # Emit structured event
            yield {
                "click_id":     event["click_id"],
                "campaign_id":  event["campaign_id"],
                "channel":      event.get("channel", "unknown"),
                "cost_usd":     event.get("cost_micros", 0) / 1_000_000,
                "event_time":   event["timestamp"],  # event time from message
            }
        except Exception as e:
            yield beam.pvalue.TaggedOutput("dead_letter", {
                "raw": element.decode("utf-8"),
                "error": str(e)
            })

class ExtractCampaignMetrics(beam.DoFn):
    """Extract (campaign_id, metrics) tuple for aggregation."""
    
    def process(self, element):
        yield (element["campaign_id"], {
            "clicks":    1,
            "spend_usd": element["cost_usd"]
        })

class SumMetrics(beam.CombineFn):
    """Combine metrics for the same campaign within a window."""
    
    def create_accumulator(self):
        return {"clicks": 0, "spend_usd": 0.0}
    
    def add_input(self, accumulator, input_element):
        return {
            "clicks":    accumulator["clicks"]    + input_element["clicks"],
            "spend_usd": accumulator["spend_usd"] + input_element["spend_usd"]
        }
    
    def merge_accumulators(self, accumulators):
        result = {"clicks": 0, "spend_usd": 0.0}
        for acc in accumulators:
            result["clicks"]    += acc["clicks"]
            result["spend_usd"] += acc["spend_usd"]
        return result
    
    def extract_output(self, accumulator):
        return accumulator

def format_for_bigquery(element, window=beam.DoFn.WindowParam):
    """Format aggregated result as BigQuery row."""
    campaign_id, metrics = element
    return {
        "window_start":  window.start.to_rfc3339(),
        "window_end":    window.end.to_rfc3339(),
        "campaign_id":   campaign_id,
        "clicks":        metrics["clicks"],
        "spend_usd":     metrics["spend_usd"],
        "cpc_usd":       metrics["spend_usd"] / metrics["clicks"] if metrics["clicks"] > 0 else 0
    }

# Main pipeline definition
def run():
    options = PipelineOptions([
        "--runner=DataflowRunner",
        "--project=costco-martech",
        "--region=us-central1",
        "--streaming",                              # this is a streaming job
        "--enable_streaming_engine",                # use Dataflow Streaming Engine
        "--autoscaling_algorithm=THROUGHPUT_BASED", # auto-scale based on throughput
        "--max_num_workers=20",
        "--min_num_workers=2"
    ])
    
    with beam.Pipeline(options=options) as p:
        
        # Step 1: Read from Pub/Sub
        raw_messages = p | "ReadFromPubSub" >> beam.io.ReadFromPubSub(
            subscription="projects/costco/subscriptions/ad-clicks-sub",
            with_attributes=True
        )
        
        # Step 2: Parse and validate
        parsed = raw_messages | "Parse" >> beam.ParDo(
            ParseAdClick()
        ).with_outputs("dead_letter", main="valid")
        
        # Step 3: Window into 5-minute fixed windows
        # WITH late data handling (accept up to 1 hour late)
        windowed = parsed.valid | "Window" >> beam.WindowInto(
            window.FixedWindows(5 * 60),  # 5-minute windows (300 seconds)
            
            # LATE DATA HANDLING:
            allowed_lateness=window.Duration(seconds=3600),  # accept up to 1 hour late
            
            # TRIGGERS:
            # Fire early (every 30 seconds) for real-time dashboard
            # Fire again when watermark passes (on-time result)
            # Fire again for each late element
            trigger=trigger.AfterWatermark(
                early=trigger.AfterProcessingTime(30),   # preliminary every 30s
                late=trigger.AfterCount(1)               # update for each late event
            ),
            
            # ACCUMULATION:
            # ACCUMULATING: later fires include all prior data + new data (final = complete)
            # DISCARDING:   later fires include ONLY the new data (must add up yourself)
            accumulation_mode=trigger.AccumulationMode.ACCUMULATING
        )
        
        # Step 4: Aggregate per campaign per window
        aggregated = (windowed
            | "ExtractKey"     >> beam.ParDo(ExtractCampaignMetrics())
            | "GroupByKey"     >> beam.GroupByKey()
            | "SumMetrics"     >> beam.CombinePerKey(SumMetrics())
        )
        
        # Step 5: Format and write to BigQuery
        (aggregated
            | "Format"         >> beam.Map(format_for_bigquery)
            | "WriteToBQ"      >> WriteToBigQuery(
                table="costco-martech:streaming.campaign_metrics_5min",
                schema={
                    "fields": [
                        {"name": "window_start", "type": "STRING"},
                        {"name": "window_end",   "type": "STRING"},
                        {"name": "campaign_id",  "type": "STRING"},
                        {"name": "clicks",       "type": "INTEGER"},
                        {"name": "spend_usd",    "type": "FLOAT"},
                        {"name": "cpc_usd",      "type": "FLOAT"}
                    ]
                },
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED
            )
        )
        
        # Dead letter: write failed messages for debugging
        (parsed.dead_letter
            | "WriteDeadLetter" >> WriteToBigQuery(
                table="costco-martech:monitoring.dead_letter_ad_clicks"
            )
        )

if __name__ == "__main__":
    run()
```

---

## PART 3: LATE ARRIVING DATA — THE INTERVIEW DEEP DIVE

### The Complete Late Data Handling Strategy (What Round 2 Will Test)

```
QUESTION: "How do you handle late arriving data in a streaming pipeline?"

WRONG ANSWER: "We set allowed_lateness to 24 hours and accept all late data"
  (This means windows never close and memory grows forever)

WRONG ANSWER: "We ignore late data"
  (This means metrics are wrong — missing real events)

RIGHT ANSWER: A tiered strategy based on business requirements.

VIRAAJ'S ANSWER FRAMEWORK:

1. FIRST, UNDERSTAND THE LATENESS DISTRIBUTION:
   "Before designing the handling strategy, I'd measure: what % of events arrive
   within 5 min, 30 min, 1 hour, 24 hours, 48 hours of their event time?
   For most ad click data: 95% arrive within 5 minutes, 99% within 1 hour,
   99.9% within 24 hours, and the last 0.1% arrive within 48 hours (cost adjustments)."

2. TIER THE RESPONSE BASED ON LATENESS:
   
   Tier 1: ≤ 5 minutes late → process in real-time stream normally
   Tier 2: 5 min - 1 hour late → process via stream with allowed_lateness
   Tier 3: 1 hour - 48 hours late → batch job reprocesses last 3 days nightly
   Tier 4: > 48 hours late → dead letter queue, alert, manual investigation

3. TWO PATHS IN THE ARCHITECTURE (Lambda Architecture):
   
   STREAMING PATH (approximate, low latency):
     allowed_lateness = 1 hour
     Provides: preliminary real-time ROAS for dashboards
     Labeled: "Preliminary — may change"
   
   BATCH PATH (authoritative, high latency):
     Runs nightly at 2 AM
     Reprocesses last 3 days with complete data
     Provides: final, authoritative ROAS
     Labeled: "Final"
   
   Business stakeholders see:
   - During the day: streaming (preliminary, fast)
   - Morning report: batch (accurate, complete)
```

### Allowed Lateness Code Pattern

```python
# Pattern: Stream with tiered lateness handling

# Window with allowed lateness
window.FixedWindows(3600),  # 1-hour windows
allowed_lateness=window.Duration(seconds=7200),  # accept 2-hour-late events

# Trigger strategy: fire multiple times
trigger=trigger.AfterWatermark(
    # Fire preliminary results before watermark (every minute)
    early=trigger.AfterProcessingTime(60),
    
    # Fire final result when watermark passes (on-time)
    # (implicitly at watermark)
    
    # Fire again for late events (after watermark)
    late=trigger.AfterCount(1)  # fire for each late event
),

# ACCUMULATING: each firing includes ALL data (including prior firings)
# Use this for metrics that should show the COMPLETE picture
accumulation_mode=trigger.AccumulationMode.ACCUMULATING
```

### The Watermark Stall Problem

```
PROBLEM: Watermark stops advancing

Scenario: You have a streaming pipeline processing events from 3 regions.
  US events: arriving steadily at 2:30 PM events by 2:31 PM
  EU events: normal
  APAC events: STOPPED (pipeline for APAC is down)

  Watermark = min(latest event time across all partitions)
  US latest = 2:30 PM
  EU latest = 2:30 PM
  APAC latest = 1:45 PM (stuck! pipeline is down)
  
  WATERMARK = 1:45 PM (held back by APAC)
  
  Result: Windows for 2:00 PM - 2:30 PM NEVER CLOSE
  → Dashboard never shows results for the last 45 minutes!
  → Latency appears to grow forever

DETECTION:
  Monitor: data_freshness metric in Dataflow
  (data_freshness = current_time - watermark = how far behind you are)
  Alert when data_freshness > 10 minutes

FIX:
  1. Immediately investigate the stuck partition/APAC pipeline
  2. Short-term: set a maximum watermark lag
     -- If no events from APAC for 10 min, advance watermark anyway
     -- Accept that APAC events arriving after this will be "late"
  3. In Dataflow: configure allowed_lateness and the watermark will advance
     even if some partitions are stuck
```

---

## PART 4: STREAMING INTERVIEW QUESTIONS WITH FULL ANSWERS

### Q1 (EASY): "What is the difference between event time and processing time?"

*"Event time is when the event actually occurred in the real world — for example, the timestamp when a user clicked an ad. Processing time is when the event arrived at the streaming system. These are different because events don't travel instantaneously. A mobile app might batch events and send them when the user gets WiFi — so a click that happened at 2:15 PM might arrive at the processing system at 2:47 PM. The event's event time is 2:15 PM; its processing time is 2:47 PM.*

*For accurate analytics, you always want to aggregate by event time, not processing time. If you count 'clicks in the 2 PM hour' using processing time, you'd count events that actually happened before 2 PM but arrived during that hour. Using event time gives you the true picture of what happened in that time period. The challenge is that you can't know for sure when all events for a given event time have arrived — some might be 48 hours late — so you need strategies like watermarks and allowed lateness to handle this."*

---

### Q2 (MEDIUM): "What is a watermark and why is it needed?"

*"A watermark is the streaming engine's estimate of how far in event time it has processed. Specifically, it's a lower bound: 'I'm confident all events with event time before T have now arrived.' This is needed because events can arrive out of order — you might see an event from 2:45 PM arrive before an event from 2:30 PM due to network delays.*

*The watermark allows the engine to decide when to close a time window and compute final results. For example, if I have a 2 PM to 3 PM window and my watermark advances past 3 PM, I know (with some confidence) that all events for that window have arrived, so I can emit the final aggregated result.*

*The watermark is typically set as: max(event_time_seen) minus some lag factor. If the latest event I've seen has event_time of 2:55 PM and I know events are at most 10 minutes late, my watermark would be 2:45 PM. As the watermark advances past 3:00 PM, the 2-3 PM window closes.*

*In Dataflow/Beam, the allowed_lateness parameter controls what happens to events that arrive after the watermark has passed their window — they can be accepted and cause the window to fire again with updated results, up to allowed_lateness duration after the window's end time."*

---

### Q3 (HARD): "Design a real-time ROAS monitoring system for Costco's marketing team. Requirements: sub-5-minute latency, handles 100M events/day, alerts when ROAS drops below 1.5 for any campaign. Discuss how you handle late data."

*"I'd design this as a Lambda Architecture — a streaming path for real-time approximate results and a batch path for authoritative daily numbers.*

*For the streaming path: Ad click events from Google and Meta arrive via Pub/Sub. A Dataflow pipeline reads from the subscription, parses JSON, and validates the schema. I'd use 5-minute Fixed Windows to compute click count and spend per campaign. For conversions, I'd join a separate conversions Pub/Sub stream — but since there's always a delay between click and conversion, I'd use a 30-minute sliding window with 5-minute slides for the ROAS calculation, giving us a trailing 30-minute ROAS that's meaningful for real-time monitoring.*

*For late data: mobile events can arrive up to 1 hour late. I'd set allowed_lateness to 60 minutes. The trigger would fire preliminary results every 30 seconds (early trigger), a more complete result at the watermark, and updated results for each late arrival. I'd mark each result as 'preliminary' vs 'on-time' in the BigQuery row, so the dashboard can distinguish them.*

*For the alerting: a separate Dataflow step filters the output — if ROAS < 1.5 for any campaign in the current 5-minute window, publish to a Pub/Sub alert topic, which triggers a Cloud Function that sends a Slack notification. I'd add de-duplication: don't alert again for the same campaign until ROAS recovers above 1.5 or 30 minutes pass, whichever comes first.*

*For cost data from Google Ads (which can adjust up to 48 hours later): the streaming path shows the current best estimate. A nightly batch job runs at 2 AM, reads 3 days of data from GCS (where Dataflow also writes all raw events), recomputes authoritative ROAS with final costs, and overwrites those partitions in BigQuery. The morning dashboard shows the authoritative numbers.*"

---

### Q4 (VERY HARD): "What happens if your Dataflow pipeline is down for 2 hours? How do you recover with no data loss?"

*"This is where Pub/Sub's durability becomes critical. Pub/Sub retains messages for up to 7 days. When the Dataflow pipeline restarts, it resumes pulling from Pub/Sub where it left off — specifically, from the last acknowledged message offset. Since the 2 hours of messages are still in Pub/Sub (within the 7-day retention), Dataflow will catch up by processing the backlog.*

*The recovery process: Dataflow automatically handles this via checkpointing. Every few seconds, Dataflow checkpoints its state to GCS — including the Pub/Sub offset it has processed up to. On restart, it reads the latest checkpoint and resumes from exactly that offset. The 2-hour backlog is processed quickly because the pipeline can run at much higher throughput when catching up (more events are available to process in parallel).*

*What about windowed aggregations during the recovery? The events from the 2-hour gap have real event times (2 PM - 4 PM), so they'll be processed with correct event time attribution. Any windows that should have closed during the outage (say, the 3 PM window) will close correctly once the watermark catches up past 3 PM. The results will appear 'late' in the dashboard during recovery, but will be accurate once processing catches up.*

*One important nuance: if the allowed_lateness on the windows is shorter than the 2-hour outage, some events might be considered 'too late' and routed to side outputs. This is why I'd design the allowed_lateness to be at least equal to the maximum expected downtime — in this case, at least 2-3 hours — or rely on the nightly batch job to capture any events that fall outside the streaming late window."*

---

## PART 5: STREAMING PATTERNS QUICK REFERENCE

```
PATTERN                    SOLUTION
─────────────────────────────────────────────────────────────────────
Real-time counts           Fixed Windows + CombinePerKey(count)
Rolling average            Sliding Windows + CombinePerKey(mean)
Session detection          Session Windows by user_id
Late data (< 1 hour)       allowed_lateness + ACCUMULATING mode
Late data (> 1 hour)       Batch reprocessing path (Lambda Architecture)
Deduplication              State API per key, track seen event IDs
Join two streams            CoGroupByKey on common key (e.g., user_id)
Enrich with dimension data  Broadcast side input (join small dim table to stream)
Alerting                   Filter output → Pub/Sub → Cloud Function → Slack
Exactly-once               at-least-once + idempotent MERGE on event_id in BQ
Stuck watermark             Monitor data_freshness metric, alert, fix upstream
Pipeline down → recovery    Pub/Sub retention (7 days) + Dataflow checkpoint
Cost optimization           Batch more events before writing to BQ (reduce API calls)
Schema evolution            Use VARIANT/JSON column or BigQuery schema update with defaults
```

---

## PART 6: STREAMING MONITORING (What Sr. Engineers Know)

```python
# Dataflow metrics to monitor in production:

KEY METRICS:
  system_lag:       Difference between current time and max event time processed
                    (how far behind real-time are we?)
                    Alert: > 5 minutes for real-time pipeline
  
  data_freshness:   How old is the watermark?
                    Alert: > 10 minutes (could indicate stuck watermark)
  
  backlog_bytes:    How many bytes are in Pub/Sub waiting to be processed?
                    Alert: growing continuously (pipeline can't keep up)
  
  worker_utilization: CPU and memory of workers
                    Alert: > 85% CPU (need to scale up)
  
  elements_dropped: Events dropped due to expired allowed_lateness
                    Alert: > 0.1% of total events
  
  dead_letter_count: Events routed to dead letter (failed to process)
                    Alert: > 0.01% of total events

CLOUD MONITORING DASHBOARD FOR STREAMING:
  Panel 1: system_lag (goal: < 2 minutes)
  Panel 2: Pub/Sub backlog size (goal: decreasing or stable)
  Panel 3: Messages delivered per second (volume trend)
  Panel 4: Dead letter count (goal: near zero)
  Panel 5: BigQuery write latency (goal: < 5 seconds)
```
