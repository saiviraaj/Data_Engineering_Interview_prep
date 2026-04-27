# Streaming + SQL Interview Playbook — Complete Deep Dive
## Costco Sr. Data Engineer | Round 2 Preparation
### Built for someone starting from scratch → answering expert-level questions

---

## HOW TO USE THIS FILE

This file is organized as a **learning journey**, not just a reference. Read it front to back the first time. Each concept builds on the previous one. By the end, you should be able to:

- Explain every streaming concept clearly to a panel of senior engineers
- Write correct SQL for every pattern from memory
- Answer any question from easy to very hard with confidence

---

# SECTION 1: STREAMING FUNDAMENTALS

---

## 1.1 What is Streaming? — Teaching It From Scratch

### The Physical World Analogy

Before we write a single line of code, understand streaming through an analogy.

Imagine a **water faucet**:
- Turn it on → water flows continuously
- You don't collect all the water in a giant tank and then process it
- You process it AS IT FLOWS — cup by cup

That is streaming. Data flows continuously and you process each piece as it arrives.

Now imagine **batch processing** with the same water:
- You block the faucet for 24 hours
- At midnight you open the tank and process everything at once
- You get your answer at 1 AM

```
BATCH WORLD:
──────────────────────────────────────────────────────────────────►  time
  Events arrive all day:  ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ●
                          (no processing happens during the day)
  
  At midnight:
  [COLLECT EVERYTHING] ──► [PROCESS 24 HOURS OF DATA] ──► RESULT
  
  Latency: 6 to 30 HOURS between event happening and insight


STREAMING WORLD:
──────────────────────────────────────────────────────────────────►  time
  Event arrives ──► IMMEDIATELY PROCESSED ──► Result updated
         ↑                                          ↑
      2:15:00 PM                               2:15:03 PM
  
  Latency: SECONDS between event happening and insight
```

### What Kind of Data Streams?

Streaming exists because the real world generates data continuously. Examples relevant to your Costco role:

```
AD CLICK EVENTS:
  User clicks an ad → event fires immediately → you need to know NOW
  (not tomorrow morning) if a campaign's ROAS just dropped below 1.0

PURCHASE EVENTS:
  Member makes a purchase → loyalty points should update in seconds
  → email confirmation should fire in < 30 seconds

FRAUD SIGNALS:
  Credit card used twice in different cities in 2 minutes → flag in real-time
  Batch processing means you discover this tomorrow → too late

CAMPAIGN BUDGET EVENTS:
  Campaign has spent 95% of daily budget → pause other campaigns NOW
  → batch means you overspend the budget every day before catching it

WEBSITE EVENTS:
  User abandons cart → send recovery email within 10 minutes
  → batch means you send that email the next morning → terrible conversion
```

### Batch vs Streaming — The Decision Framework

```
USE BATCH WHEN:                          USE STREAMING WHEN:
─────────────────────────────────────    ────────────────────────────────────
✓ Latency > 1 hour is acceptable         ✓ Latency must be < 5-10 minutes
✓ Financial reconciliation               ✓ Fraud detection
✓ Monthly/weekly reports                 ✓ Real-time dashboards
✓ ML model training                      ✓ Alerting (ROAS, budget, errors)
✓ Historical backfills                   ✓ Event-driven actions (emails, push)
✓ Complex multi-join transformations     ✓ Live leaderboards, live inventory
✓ Authoritative final numbers            ✓ Preliminary fast-approximate metrics

IMPORTANT: Streaming is always-on infrastructure.
  You pay for it 24/7 even when no data is flowing.
  It is MORE COMPLEX than batch.
  Only use it when the business GENUINELY needs low latency.
```

---

## 1.2 The Streaming Data Model — Bounded vs Unbounded

This is a concept you must understand before anything else in streaming.

```
BOUNDED DATA (batch):
  Has a beginning AND an end.
  You know when all the data has arrived.
  
  Example: "All ad clicks from January 2024"
  → You can read the entire dataset, process it, declare "done"
  
  ┌─────────────────────────────┐
  │  Data  │  Data  │  Data    │  ← finite set
  └─────────────────────────────┘
  START                       END

UNBOUNDED DATA (streaming):
  Has a beginning but NO end.
  Data keeps arriving forever (as long as the system is running).
  You can never declare "done" — there's always more data coming.
  
  ┌─────────────────────────────────────────────────────────► forever
  │  Click  │  Click  │  Click  │  Click  │  Click  │  ...
  └──────────────────────────────────────────────────────────
  
  This creates the core challenge of streaming:
  HOW DO YOU AGGREGATE INFINITE DATA?
  
  Answer: by cutting it into finite pieces called WINDOWS (Section 1.4)
```

---

## 1.3 Event Time vs Processing Time — The Most Critical Concept

This is **the foundational concept of streaming**. Every other concept (watermarks, late data, windows) exists because of the gap between event time and processing time.

### Definitions

```
EVENT TIME:
  When the event ACTUALLY HAPPENED in the physical world.
  Recorded by the device/app/system that generated the event.
  This is the timestamp that MATTERS for your analytics.
  Example: User clicked the ad at exactly 14:23:07 PM on their phone.
           Event time = 14:23:07 PM

PROCESSING TIME:
  When the event ARRIVED at your streaming processing system.
  This is when your Dataflow job or Kafka consumer actually SAW the event.
  Example: The click event arrived at your Pub/Sub topic at 14:47:32 PM.
           Processing time = 14:47:32 PM
           
  The difference = 24 minutes 25 seconds of DELAY
```

### Why Does This Gap Exist?

```
CAUSES OF GAP BETWEEN EVENT TIME AND PROCESSING TIME:

1. MOBILE APP BATCHING (most common)
   ─────────────────────────────────
   Mobile apps don't send every event immediately.
   They batch events locally and flush when:
   - WiFi becomes available (user was on 4G/offline)
   - App comes to foreground
   - Every N minutes (battery optimization)
   
   Result: An event at 2:15 PM might arrive at 2:47 PM or even next morning.
   
   Impact on your data: A 2:00-3:00 PM window might seem to have 1,000 clicks
   at 3:00 PM, but actually 200 more clicks will arrive over the next 2 hours.
   Your "2 PM hour ROAS" is wrong if you compute it at 3 PM.

2. AD NETWORK REPORTING DELAY
   ────────────────────────────
   Google Ads and Meta have "click spam filtering" that runs AFTER the click.
   They may adjust cost data up to 48 hours after the click.
   
   Result: Today's campaign cost is preliminary — it will change for 2 more days.
   This is a DATA QUALITY issue on top of a latency issue.

3. NETWORK PARTITIONS / SLOW REGIONS
   ────────────────────────────────────
   IoT devices in poor network areas (rural Costco warehouses)
   send data in bursts when connection is restored.

4. SYSTEM FAILURES AND RECOVERY
   ────────────────────────────────
   Your pipeline was down for 2 hours.
   When it recovers, 2 hours of events arrive simultaneously.
   Processing time: they all arrive "now" (3 PM).
   Event time: they happened between 1 PM and 3 PM.

5. PRODUCER SLOWNESS
   ───────────────────
   A log collection agent is slow/overloaded.
   Events pile up in a buffer and release slowly.
```

### The Concrete Problem — Why Wrong Time = Wrong Metrics

```
SCENARIO: Compute "ROAS for the 2:00 PM to 3:00 PM hour" for campaign C001.

USING PROCESSING TIME (WRONG):

  Events processed between 2:00 PM and 3:00 PM in processing time:
  - click at event_time=1:58 PM, arrived at 2:03 PM  ← INCLUDED (wrong hour!)
  - click at event_time=2:15 PM, arrived at 2:47 PM  ← INCLUDED (correct)
  - click at event_time=2:55 PM, arrived at 3:15 PM  ← EXCLUDED (missed!)
  
  Result: Wrong. Includes events from 1 PM hour, misses events from 2 PM hour.

USING EVENT TIME (CORRECT):

  Events where event_time is between 2:00 PM and 3:00 PM:
  - click at event_time=2:15 PM, arrived at 2:47 PM  ← INCLUDED ✓
  - click at event_time=2:55 PM, arrived at 3:15 PM  ← INCLUDED ✓
                                                        (even though it arrived late)
  - click at event_time=1:58 PM, arrived at 2:03 PM  ← EXCLUDED ✓
                                                        (belongs to 1 PM hour)
  
  Result: Correct. Every click is counted in its TRUE time bucket.

THIS IS WHY all production streaming systems use event time.
```

### Visual Timeline

```
REAL WORLD (event time axis):
                  1 PM                 2 PM                 3 PM
─────────────────────┬────────────────────┬────────────────────►
                  ●  │      ●  ●  ●  ●   │  ●                  
              1:58 click  2:15 2:23 2:45 2:55  ← these all belong in "2 PM hour"
                         
YOUR SYSTEM (processing time axis):                  
                  1 PM                 2 PM                 3 PM    4 PM
──────────────────────────────────────────┬─────────────┬────────────►
                                          │             │
                                    2:03 PM: the      3:15 PM: the
                                    1:58 click         2:55 click
                                    ARRIVES            ARRIVES (late!)

The 2:55 click (event time) arrived at 3:15 (processing time).
It is 20 MINUTES LATE relative to processing time.
But its EVENT TIME is correctly 2:55 PM.
A correctly designed system puts it in the 2 PM-3 PM bucket.
```

---

## 1.4 Windows — How You Aggregate Infinite Data

Streaming data never ends. To compute metrics like "clicks per hour" or "spend per 5 minutes," you need to cut the infinite stream into finite, manageable buckets called **windows**.

Think of windows as **time buckets** — every event falls into one (or more) buckets based on its event time, and when a bucket is "closed," you compute the aggregation for everything in it.

### Window Type 1: Fixed Windows (Tumbling Windows)

```
FIXED WINDOWS:
  ─────────────────────────────────────────────────────────────────►
  │   1 hour   │   1 hour   │   1 hour   │   1 hour   │   1 hour  │
  12:00────────13:00─────────14:00────────15:00─────────16:00──────17:00

PROPERTIES:
  • Fixed size (e.g., 1 hour, 5 minutes, 1 day)
  • Non-overlapping: each event belongs to EXACTLY ONE window
  • No gaps: windows tile the entire time axis perfectly
  
EXAMPLE USE CASES:
  "Clicks per hour" → 1-hour fixed windows
  "Spend per 5-minute interval" → 5-minute fixed windows
  "Daily active users" → 24-hour fixed windows
  "Revenue per day" → daily fixed windows

HOW TO THINK ABOUT IT:
  It's like a bucket that fills up for exactly 1 hour.
  At the end of the hour, you count what's in the bucket.
  The bucket empties. A new bucket starts.
  No event can be in two buckets simultaneously.
```

```python
# Apache Beam (Dataflow) code for fixed windows
import apache_beam as beam
from apache_beam.transforms import window

events | "FixedWindow" >> beam.WindowInto(
    window.FixedWindows(5 * 60)  # 5 minutes = 300 seconds
)
# Every event is assigned to the 5-minute bucket containing its event_time
```

### Window Type 2: Sliding Windows

```
SLIDING WINDOWS:
  Window size: 1 hour, Slide interval: 15 minutes

  [12:00───────────────────────────────13:00)
        [12:15──────────────────────────────13:15)
               [12:30───────────────────────────────14:00)
                     [12:45─────────────────────────────13:45)
                            [13:00──────────────────────────────14:00)

PROPERTIES:
  • Fixed size, but windows OVERLAP
  • Each event belongs to MULTIPLE windows
    (size/slide = 60min/15min = 4 windows per event)
  • Slide interval: how often a new window starts
  
EXAMPLE USE CASES:
  "ROAS over the last 1 hour, updated every 15 minutes"
    → users always see a fresh number, but computed over 1 hour of data
  "Rolling average spend over last 30 minutes"
  "Anomaly detection: is this 5-minute rate unusual vs last hour?"

COST:
  Each event is processed size/slide times = 4x in our example.
  More overlap = more compute = more cost.

HOW TO THINK ABOUT IT:
  Like a sliding 1-hour glass window over your data stream.
  Every 15 minutes you slide the window forward.
  You can always see what happened in the last hour.
  But the window advances — you never see ALL history, just last 1 hour.
```

```python
# Sliding window: 1 hour window, updated every 15 minutes
events | "SlidingWindow" >> beam.WindowInto(
    window.SlidingWindows(
        size=60 * 60,    # 1 hour window
        period=15 * 60   # slide every 15 minutes
    )
)
```

### Window Type 3: Session Windows

```
SESSION WINDOWS:
  User A: ●●●      (gap > 30 min)     ●●      (gap > 30 min)   ●●●●●
          ───────                     ──────                     ──────────
          session 1                   session 2                  session 3
  
  User B: ●   (gap > 30 min)   ●●●●●●●●
          ─                    ─────────
          session 1             session 2

PROPERTIES:
  • Variable size: session ends when user is inactive for N minutes
  • Per-user: each user's sessions are computed independently
  • No fixed start or end time: purely determined by user behavior
  
EXAMPLE USE CASES:
  "How long did a user spend browsing before buying?" 
  "Group a user's ad interactions into coherent browsing sessions"
  "What was the user's journey in their session that converted?"
  
HOW TO THINK ABOUT IT:
  Think of a restaurant table.
  Session = from when someone sits down to when they leave.
  If they're gone for > 30 minutes, that's a new visit.
  Each customer (user_id) has their own independent session clock.

COMPLEXITY:
  Session windows are stateful — you must remember the last event time
  per user to decide if the current event continues or starts a new session.
  This requires storing state PER USER in memory.
```

```python
# Session window: new session if gap > 30 minutes
events | "SessionWindow" >> beam.WindowInto(
    window.Sessions(30 * 60)  # 30-minute gap threshold
    # Note: must be partitioned by user_id for this to make sense
)
```

### Window Comparison Table

```
                FIXED (TUMBLING)      SLIDING           SESSION
                ─────────────────     ───────────────   ──────────────────
Size            Fixed                 Fixed             Variable (by user activity)
Overlap         None                  Yes               None (within same user)
Events per wnd  1                     size/slide         1
State required  Minimal               Minimal            High (per-user)
Use for         Hourly reports        Rolling averages  User journey analysis
Example         "Clicks per hour"     "30min avg ROAS"  "Session duration"
Complexity      Simple                Simple            Complex
```

---

## 1.5 Watermarks — The Engine's Clock

### The Fundamental Problem Watermarks Solve

Imagine you're computing "clicks per hour" using event time. You open the 2 PM window. When can you CLOSE it and compute the final answer?

If you close it exactly at 3 PM processing time, you'll miss all events that happened before 3 PM (event time) but arrived late. But if you wait forever, windows never close and your dashboard never updates.

A **watermark** is the streaming engine's best estimate of: *"I am confident that all events with event_time ≤ T have now arrived."*

When the watermark passes 3 PM, it means: "I'm confident all 2 PM-3 PM events have arrived. I can now close that window and give you the final count."

### Watermark Formula and Mechanics

```
WATERMARK FORMULA:
  watermark = max(event_time_seen_so_far) - allowed_lateness
  
  (Note: your uploaded file had "min" — that's incorrect. It's MAX.)
  
  If the latest event I've seen has event_time = 2:55 PM
  And my allowed_lateness = 10 minutes
  Then: watermark = 2:55 PM - 10 min = 2:45 PM
  
  Meaning: "I'm confident all events with event_time ≤ 2:45 PM have arrived.
            Events between 2:45-2:55 PM might still be in transit."

HOW WATERMARK ADVANCES:
  
  Events arrive in processing time order (but not event time order):
  
  Processing time │ Event time │ Watermark (allowed=10 min)
  ────────────────┼────────────┼───────────────────────────
  3:01 PM         │ 2:55 PM    │ 2:45 PM    (max_seen=2:55, watermark=2:45)
  3:02 PM         │ 2:58 PM    │ 2:48 PM    (max_seen=2:58, watermark=2:48)
  3:03 PM         │ 2:30 PM    │ 2:48 PM    (2:30 < 2:58, watermark stays at 2:48)
  3:04 PM         │ 3:05 PM    │ 2:55 PM    (max_seen=3:05, watermark=2:55)
  3:10 PM         │ 3:20 PM    │ 3:10 PM    (max_seen=3:20, watermark=3:10)
                  
  When watermark reaches 3:00 PM → the 2:00-3:00 PM window CLOSES
  The final result for that window is emitted.
```

### What Happens to Each Event Based on Watermark Position

```
THREE ZONES FOR INCOMING EVENTS:

ZONE 1: NORMAL (event_time > watermark)
  ─────────────────────────────────────
  Event has event_time AFTER the current watermark.
  Processed normally. Assigned to its correct window.
  No special handling needed.

ZONE 2: LATE BUT ACCEPTABLE (event_time ≤ watermark, but within allowed_lateness)
  ───────────────────────────────────────────────────────────────────────────────
  Event arrived AFTER its window's watermark passed.
  BUT it arrived within the allowed_lateness window.
  
  Behavior:
  - The engine still accepts this event
  - It triggers a LATE FIRING of the window (updated result)
  - Dashboard shows "updated" value
  
  Example: Window 2-3 PM closed at watermark=3:00 PM.
           allowed_lateness = 1 hour.
           An event with event_time=2:45 PM arrives at 3:30 PM processing time.
           → It's late (window closed) but within 1-hour lateness window.
           → Window fires again with updated count.

ZONE 3: TOO LATE — DROPPED (event_time ≤ watermark, beyond allowed_lateness)
  ────────────────────────────────────────────────────────────────────────────
  Event arrived after allowed_lateness period expired.
  The engine has already cleaned up state for that window.
  
  Behavior:
  - Event is DROPPED from the main pipeline
  - Routed to a SIDE OUTPUT (if configured) for separate handling
  - The window result is NOT updated
  
  Example: Window 2-3 PM closed. allowed_lateness = 1 hour.
           An event with event_time=2:45 PM arrives at 4:30 PM processing time.
           → 1.5 hours after window close, beyond allowed_lateness.
           → Dropped from main pipeline.
           → If side output configured: sent to separate stream for batch handling.
```

### Visual Watermark Timeline

```
EVENT TIME AXIS:
─────────────────────────────────────────────────────────────────────►
     2:00      2:30     3:00      3:30      4:00
      │                  │                   │
      │←── 2PM window ──►│                   │
      │                  │                   │
      │  Normal events   │ Late but ok (1hr)  │ Dropped
      │  processed here  │ ◄──────────────►  │ after this
      
WATERMARK advances:
─────────────────────────────────────────────────────────────────────►
     2:00      2:30     3:00      3:30      4:00
              ▲         ▲         ▲
              │         │         │
         watermark  watermark  watermark
         at 2:30    reaches    at 3:30
                    3:00 →
                    2PM window CLOSES
                    Final result emitted
```

### The Watermark Stall Problem (Critical for Senior Interviews)

```
SCENARIO: Pipeline reads from 3 Pub/Sub partitions (3 regions: US, EU, APAC)

  Watermark = min(max_event_time per partition) - allowed_lateness
  
  US partition:   latest event_time = 3:45 PM  → contributes 3:35 PM to watermark
  EU partition:   latest event_time = 3:43 PM  → contributes 3:33 PM to watermark
  APAC partition: latest event_time = 2:15 PM  → contributes 2:05 PM to watermark
  
  Overall watermark = min(3:35, 3:33, 2:05) = 2:05 PM  ← STALLED!
  
  The APAC pipeline has a problem — no new events are coming in.
  The global watermark is stuck at 2:05 PM, even though it's now 3:45 PM.
  
  CONSEQUENCE: The 2:00 PM - 3:00 PM window has NOT closed.
               Your dashboard hasn't updated since 2:05 PM.
               Users think the real-time dashboard is broken.
               
  HOW TO DETECT:
    Monitor data_freshness metric in Dataflow:
    data_freshness = current_processing_time - watermark
    Normal: < 2 minutes
    Stalled: 1 hour 40 minutes (and growing)
    
  HOW TO FIX:
    1. Immediately investigate the APAC pipeline — why did it stop?
    2. Short-term: if APAC has been silent for > 10 minutes,
       advance the watermark anyway (accept APAC events as "late")
    3. Long-term: separate watermarks per region, combine with MAX not MIN
```

---

## 1.6 Late Data Handling — Complete Strategy

Late data is not an edge case — in production, it is the norm. Here is the complete framework.

### Why Late Data is Inevitable in AdTech

```
LATENESS DISTRIBUTION FOR AD CLICK EVENTS (typical production numbers):

  0 - 5 minutes late:   92% of events
  5 - 30 minutes late:   5% of events
  30 min - 2 hours late: 2% of events  ← mobile app batching
  2 - 48 hours late:   0.9% of events  ← ad cost adjustments (Google, Meta)
  > 48 hours late:     0.1% of events  ← exceptional cases
  
  For a dashboard showing "live ROAS":
  • If you close windows at the watermark: you miss the 8% of late events
  • Your ROAS is permanently 8% off (underestimates spend/conversions)
  
  For financial reporting:
  • The 48-hour window of cost adjustments means YESTERDAY'S cost
    in Google Ads is still changing today
  • You need a batch job to produce "final" numbers after 48 hours
```

### The Four Strategies — Deep Explanation

**Strategy 1: Allowed Lateness**

```
WHAT IT IS:
  Keep the window "alive" for N additional time after the watermark passes.
  Accept late events and re-fire the window with updated results.

HOW IT WORKS:
  Window 2:00-3:00 PM.
  Watermark passes 3:00 PM → window "on-time" result fires.
  allowed_lateness = 60 minutes.
  
  For the next 60 minutes (until 4:00 PM processing time):
  • If late events arrive with event_time in 2:00-3:00 PM → window re-fires.
  • Dashboard updates with new number.
  
  At 4:00 PM processing time: allowed_lateness expires → window state deleted.
  Any events after this with event_time in 2:00-3:00 PM: DROPPED.

WHEN TO USE:
  • Data that is rarely more than N minutes late (95%+ within N minutes)
  • Use case can tolerate "revised" numbers (preliminary → updated)
  
COST:
  Memory: window state kept alive for longer (proportional to allowed_lateness)
  Compute: additional firings for each late event
  Complexity: downstream must handle multiple firings for same window
```

**Strategy 2: Side Outputs (Dead Letter Routing)**

```
WHAT IT IS:
  Events that are "too late" (beyond allowed_lateness) are routed to a
  separate output stream instead of being silently dropped.
  
  This preserves all data for later processing.
  Nothing is ever permanently lost.

HOW IT WORKS:
  Main pipeline:
    Normal and slightly-late events → processed in stream → BigQuery live table
  
  Side output:
    Events beyond allowed_lateness → Pub/Sub dead-letter topic → GCS bucket
    
  Batch reconciliation job (runs nightly):
    Reads side output GCS files
    Reprocesses them with correct event time
    MERGES results into BigQuery (updating affected date partitions)

WHEN TO USE:
  • For the tail of your lateness distribution (0.1% very late events)
  • When you cannot afford to lose ANY event (financial data)
  • For debugging: inspect what's arriving late and why

DIAGRAM:
  Pub/Sub ──► Dataflow ──┬──► Main processing ──► BigQuery (live)
                         │
                         └──► Side output ──► GCS ──► Nightly batch ──► BigQuery (corrected)
```

**Strategy 3: Lambda Architecture — The Production Standard**

```
WHAT IT IS:
  Two parallel pipelines for the SAME data:
  1. Streaming path: fast, approximate, low latency
  2. Batch path: slow, accurate, complete (includes ALL late data)
  
  The dashboard shows BOTH: real-time preliminary + previous day's final.

DETAILED ARCHITECTURE:
  
  Pub/Sub (receives all events)
        │
        ├──────────────────────────────────────────────────────────────────────┐
        │                                                                      │
        ▼                                                                      ▼
  STREAMING PATH                                                    BATCH PATH
  (Dataflow, always running)                                        (Spark/Dataflow, daily at 2 AM)
        │                                                                      │
        │  allowed_lateness = 1 hour                                           │  Reads last 3 days
        │  Processes ~99% of events in real-time                               │  Gets ALL events (incl. 48h late)
        │                                                                      │
        ▼                                                                      ▼
  BigQuery: streaming.campaign_metrics                              BigQuery: batch.campaign_metrics
  (Labeled "Preliminary — updates every 5 min")                    (Labeled "Final — as of 2 AM today")
        │                                                                      │
        └──────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
                                    Looker Dashboard:
                                    Shows BOTH panels:
                                    "Real-time (preliminary)" → streaming
                                    "Yesterday final (authoritative)" → batch

WHY THIS WORKS:
  Marketing team can see live ROAS trends (streaming) for intraday decisions.
  Finance team uses final numbers (batch) for reporting and billing.
  
  Complexity trade-off: You run and maintain TWO pipelines.
  But most large-scale production AdTech systems (including at Meta, Google, Netflix)
  use this pattern because business requirements GENUINELY need both.
```

**Strategy 4: Kappa Architecture**

```
WHAT IT IS:
  A single streaming pipeline that can ALSO do historical reprocessing.
  Eliminates the batch path by making the streaming path powerful enough
  to replay history when needed.

HOW IT WORKS:
  1. All events stored in Kafka/Pub/Sub with LONG retention (e.g., 30 days)
  2. Streaming pipeline always processes events in real-time
  3. When correction is needed: replay the topic from a past offset
     → same pipeline reprocesses history with updated logic
  4. Output MERGES with current data via MERGE INTO on BigQuery/Iceberg

PROS vs LAMBDA:
  Kappa: Single codebase, no batch path to maintain
  Lambda: Two codebases but simpler reasoning (batch and stream separate)
  
IN PRACTICE:
  Lambda is more common in the enterprise (Google, Meta internal systems often lambda)
  Kappa is growing especially with Iceberg tables (fast reprocessing)
  
  FOR YOUR COSTCO INTERVIEW: Lambda is the safer answer.
  "I'd use a Lambda Architecture with a streaming path for real-time
   and a batch path for authoritative daily numbers with full late-data coverage."
```

---

# SECTION 2: EXACTLY-ONCE PROCESSING

---

## 2.1 The Problem — Why Distributed Systems Have Duplicates

This is a fundamental challenge in distributed systems. To understand it, understand what can go wrong.

```
NORMAL FLOW (no failure):
  Pub/Sub ──► Dataflow Worker ──► BigQuery
     │             │                  │
     │  publish     │  process         │  write
     │             │                  │
     └────────────►└─────────────────►└── event written once ✓

FAILURE SCENARIO 1: Worker crashes AFTER processing but BEFORE writing
  
  Pub/Sub ──► Dataflow Worker ──► BigQuery
     │             │                  │
     │  publish     │  process         │
     │             │  💥 CRASH        │  event NOT written
     │             │                  │
     │  message NOT acked to Pub/Sub   │
     │  Pub/Sub redelivers message     │
     │             ▼                  │
     │  message processed AGAIN       │
     │             │                  │
     │             └─────────────────►│  event written AGAIN → DUPLICATE ❌

FAILURE SCENARIO 2: Worker crashes AFTER writing but BEFORE acknowledging
  
  Pub/Sub ──► Dataflow Worker ──► BigQuery
     │             │                  │
     │             │  process          │
     │             └─────────────────►│  event written ✓
     │             │  💥 CRASH        │
     │             │  (before ack)     │
     │  Pub/Sub doesn't know ack'd     │
     │  Pub/Sub redelivers             │
     │             ▼                  │
     │  processed AGAIN               │
     │             └─────────────────►│  event written AGAIN → DUPLICATE ❌

CONCLUSION:
  In any distributed system, if you retry on failure (which you must — for reliability),
  you can get DUPLICATES. This is the fundamental tension:
  
  Reliability (no data loss) requires at-least-once delivery.
  At-least-once delivery allows duplicates.
  Preventing duplicates requires extra work.
```

## 2.2 The Three Delivery Semantics

```
AT-MOST-ONCE:
  ─────────────
  Message delivered 0 or 1 times.
  System does NOT retry on failure.
  
  Guarantee: No duplicates.
  Risk: DATA LOSS. Failed messages are silently dropped.
  
  Implementation: Fire and forget. No acknowledgment tracking.
  
  Use when: Metric collection where losing 0.01% of events is acceptable.
             (e.g., rough visitor count estimates, non-critical logs)
  
  For Costco AdTech: NOT acceptable. Every click has a cost associated with it.

AT-LEAST-ONCE (most common in practice):
  ──────────────────────────────────────
  Message delivered 1 or more times.
  System retries on failure.
  
  Guarantee: No data loss.
  Risk: DUPLICATES. Same message may arrive 2, 3, or more times.
  
  Implementation: Acknowledge message only after successful processing.
                 Unacknowledged messages are redelivered.
  
  Pub/Sub default behavior is at-least-once.
  
  Use when: You need no data loss AND you handle duplicates in your sink.
  
  For Costco AdTech: This is what you use. Handle duplicates with idempotent writes.

EXACTLY-ONCE (ideal but complex):
  ────────────────────────────────
  Message delivered exactly 1 time. No duplicates, no loss.
  
  The truth: TRUE exactly-once across a distributed system is extremely hard.
  It requires: atomic coordination between Pub/Sub + Processing + Sink.
  If any component lacks transactional support, true exactly-once is impossible.
  
  What's achievable in practice:
  AT-LEAST-ONCE + IDEMPOTENT WRITES = EFFECTIVELY EXACTLY-ONCE results
  
  The data in BigQuery looks exactly-once even if the event was delivered twice,
  because the second write is a no-op (MERGE on event_id: "if already exists, do nothing").
  
  Dataflow supports exactly-once semantics for some sinks via two-phase commit.
  Kafka supports exactly-once via transactions (kafka.KafkaConsumer + transactional producer).
```

## 2.3 Checkpointing — How Dataflow Enables Recovery

```
WHAT IS A CHECKPOINT:
  A checkpoint is a snapshot of the pipeline's EXACT state saved to durable storage (GCS).
  
  State includes:
  • Which Pub/Sub message offset was last successfully processed
  • All in-flight window accumulators (partially computed windows)
  • Current watermark position
  • Per-key state (for stateful operators)
  
  Dataflow saves checkpoints to GCS every ~30 seconds automatically.

RECOVERY SCENARIO:
  
  Time 2:00 PM: Dataflow saves checkpoint
    Checkpoint state: "last processed Pub/Sub offset = 12,345,678"
  
  Time 2:20 PM: Worker node crashes (hardware failure)
    20 minutes of processing is in memory — NOT in checkpoint.
  
  Time 2:21 PM: Dataflow detects failure, starts new worker
    New worker reads checkpoint: "resume from offset 12,345,678"
    New worker pulls messages from Pub/Sub starting at that offset.
    The 20 minutes of events since last checkpoint: still in Pub/Sub
    (Pub/Sub has 7-day retention — messages are never lost).
    
  Result:
  • No data is lost (Pub/Sub still has everything)
  • Some events from 2:00-2:20 PM are reprocessed (at-least-once delivery)
  • With idempotent sink (MERGE on event_id): no duplicate rows in BigQuery ✓
```

## 2.4 Idempotent Writes — The Practical Solution to Exactly-Once

```
IDEMPOTENT OPERATION:
  f(f(x)) = f(x)
  
  Doing the operation TWICE gives the same result as doing it ONCE.
  This is the key property that makes at-least-once "safe."

EXAMPLES:

  NOT IDEMPOTENT (dangerous for retries):
    INSERT INTO events VALUES (click_id='C001', cost=1.25)
    Run twice → two rows with click_id='C001' → DUPLICATE
    
  IDEMPOTENT (safe for retries):
    MERGE INTO events USING (SELECT 'C001' AS click_id, 1.25 AS cost) AS source
    ON events.click_id = source.click_id
    WHEN NOT MATCHED THEN INSERT (click_id, cost) VALUES (source.click_id, source.cost)
    
    Run twice → first run inserts the row.
                second run: WHEN NOT MATCHED is FALSE (row exists) → nothing happens.
    Result: exactly one row, regardless of how many times you run it. ✓

IMPLEMENTATION IN BIGQUERY:
  
  Option 1: MERGE on event_id (best)
    MERGE INTO events AS target
    USING batch_of_events AS source
    ON target.event_id = source.event_id
    WHEN NOT MATCHED THEN INSERT *;
    -- Duplicate event_ids are silently ignored
  
  Option 2: INSERT OVERWRITE on partition (for batch-style streaming)
    INSERT INTO events PARTITION BY event_date
    OVERWRITE PARTITIONS ('2024-01-15')
    SELECT * FROM staging_events
    WHERE event_date = '2024-01-15';
    -- Overwrites the partition entirely — running twice gives same result

  Option 3: ROW_NUMBER dedup before loading
    INSERT INTO events
    SELECT * EXCEPT (rn) FROM (
      SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY processed_at DESC) AS rn
      FROM staging_events
    ) WHERE rn = 1;
    -- Deduplicate before inserting
```

---

# SECTION 3: DEDUPLICATION — COMPLETE GUIDE

## 3.1 Why Deduplication is Critical

```
ROOT CAUSES OF DUPLICATES:
  1. At-least-once delivery from Pub/Sub (retries)
  2. Producer sends same event twice (network error → producer retries without knowing if first arrived)
  3. Pipeline recovery from checkpoint (reprocesses last N events)
  4. Click fraud / bot clicks (same click_id generated multiple times)
  5. Double-click (user clicks an ad twice in rapid succession)

BUSINESS IMPACT OF NOT DEDUPLICATING:
  Click count: 10% inflated → CTR looks artificially high
  Spend: double-counted → ROAS appears half its true value
  Conversions: duplicate conversion → ROAS appears 2x inflated
  
  Example: Campaign spends $1,000 and gets $3,000 revenue → ROAS = 3.0
  With duplicates: system counts $2,000 spend and $6,000 revenue → ROAS = 3.0 (still 3.0!)
  But: actual event counts are inflated → downstream reporting is wrong
  Depending on dedup pattern, ROAS can go either direction.
```

## 3.2 Deduplication Approaches

**Approach 1: Stateful Deduplication in Dataflow**

```python
import apache_beam as beam
from apache_beam.transforms import userstate
from apache_beam.coders import BooleanCoder

class DeduplicateByEventId(beam.DoFn):
    """
    Stateful DoFn that tracks seen event_ids.
    For each event, checks if already seen:
      - If NO: emit the event, mark as seen
      - If YES: drop the event (duplicate)
    
    State is PER KEY (per event_id) — stored in Dataflow's state backend.
    """
    
    SEEN_STATE = userstate.BagStateSpec('seen', BooleanCoder())
    
    def process(self, element, seen=beam.DoFn.StateParam(SEEN_STATE)):
        event_id, event_data = element
        
        # Check if we've seen this event_id before
        seen_list = list(seen.read())
        
        if not seen_list:
            # First time seeing this event_id → emit it
            seen.add(True)
            yield event_data
        else:
            # Already seen → duplicate → DROP
            pass  # emit nothing

# How to use it in pipeline:
(events
    | "KeyByEventId" >> beam.Map(lambda e: (e['event_id'], e))
    | "Deduplicate"  >> beam.ParDo(DeduplicateByEventId())
)
```

**Approach 2: External Store Deduplication (Redis)**

```python
import redis
import hashlib

class RedisDeduplicator:
    """
    Use Redis as a fast external store for seen event IDs.
    TTL controls memory usage — events older than TTL are "forgotten"
    (acceptable because very old duplicates are unlikely).
    """
    
    def __init__(self, redis_host: str, ttl_seconds: int = 86400):
        self.redis = redis.Redis(host=redis_host, decode_responses=True)
        self.ttl = ttl_seconds   # default: 24 hours
    
    def is_duplicate(self, event_id: str) -> bool:
        """
        Returns True if this event_id was seen before (duplicate).
        Uses SET NX (set if not exists) — atomic operation.
        """
        # SET event_id "" NX EX ttl_seconds
        # NX = only set if Not eXists
        # Returns True if SET succeeded (key was new) = NOT duplicate
        # Returns None if key already existed = IS duplicate
        
        result = self.redis.set(
            f"dedup:{event_id}",
            "1",
            nx=True,         # only set if not exists
            ex=self.ttl      # auto-expire after TTL
        )
        
        return result is None   # True = already existed = duplicate

# Usage
deduplicator = RedisDeduplicator(redis_host="redis.costco.internal", ttl_seconds=86400)

def process_event(event: dict) -> bool:
    """Returns True if event was processed (not duplicate)."""
    if deduplicator.is_duplicate(event['event_id']):
        return False  # skip duplicate
    
    # Process the event normally
    write_to_bigquery(event)
    return True
```

**Approach 3: BigQuery MERGE (Sink-Level Idempotency)**

```sql
-- This is the simplest and most robust approach for BigQuery sinks.
-- Instead of tracking duplicates in the pipeline,
-- let BigQuery handle deduplication at write time.

MERGE INTO `project.streaming.ad_clicks` AS target
USING (
    SELECT
        event_id,
        campaign_id,
        user_id,
        event_time,
        cost_usd,
        ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY processed_at DESC) AS rn
    FROM `project.streaming.ad_clicks_staging`  -- batch of new events (may have dupes)
) AS source
ON target.event_id = source.event_id
AND source.rn = 1   -- only process latest version of each event_id

WHEN NOT MATCHED AND source.rn = 1 THEN
    INSERT (event_id, campaign_id, user_id, event_time, cost_usd)
    VALUES (source.event_id, source.campaign_id, source.user_id,
            source.event_time, source.cost_usd);
-- If event_id already in target: skip (WHEN MATCHED not defined = no update = no duplicate)
```

---

# SECTION 4: STREAMING JOINS — THE HARD PROBLEM

## 4.1 Why Streaming Joins Are Different from Batch Joins

```
BATCH JOIN (simple):
  Table A (complete) ──┐
                       ├──► JOIN ──► Result (complete)
  Table B (complete) ──┘
  
  Both sides are fully available. Standard hash join or sort-merge join.

STREAMING JOIN (complex):
  Stream A (infinite) ──┐
                         ├──► JOIN ──► ??? 
  Stream B (infinite) ──┘
  
  PROBLEMS:
  1. Both sides are infinite — you can't load them into memory
  2. Matching events may arrive far apart in time:
     click from Stream A at 2:15 PM
     conversion from Stream B at 2:45 PM (30 min later)
     
     How long do you wait for Stream B's matching event?
     If you wait forever: infinite state in memory (OOM)
     If you wait 1 hour: events more than 1 hour apart are never joined
  
  3. Out-of-order: Stream B's event might arrive BEFORE Stream A's event

SOLUTION: Window Join (join within a time window)
  Join events from Stream A with events from Stream B
  IF their event_times fall within the SAME time window
  (e.g., both within the same 1-hour window)
```

## 4.2 Event-Time Window Join

```python
# Join ad clicks with ad conversions within the same 30-minute window
# Use case: attribution — which click led to which conversion?

import apache_beam as beam
from apache_beam.transforms import window

def join_clicks_and_conversions(clicks_stream, conversions_stream):
    """
    For each conversion, find the most recent click within 30 minutes.
    Both streams must be windowed to the same window.
    """
    
    # Apply same 30-minute window to both streams
    windowed_clicks = (
        clicks_stream
        | "WindowClicks" >> beam.WindowInto(window.FixedWindows(30 * 60))
        | "KeyClicksByUser" >> beam.Map(lambda e: (e['user_id'], e))
    )
    
    windowed_conversions = (
        conversions_stream
        | "WindowConversions" >> beam.WindowInto(window.FixedWindows(30 * 60))
        | "KeyConversionsByUser" >> beam.Map(lambda e: (e['user_id'], e))
    )
    
    # CoGroupByKey: for each (window, user_id), group clicks AND conversions together
    joined = (
        (windowed_clicks, windowed_conversions)
        | "CoGroupByKey" >> beam.CoGroupByKey()
    )
    
    # For each group: find which clicks led to conversions
    def match_clicks_to_conversions(element):
        user_id, group = element
        clicks = list(group[0])       # all clicks for this user in this window
        conversions = list(group[1])  # all conversions for this user in this window
        
        for conversion in conversions:
            # Find the most recent click before this conversion
            prior_clicks = [c for c in clicks
                           if c['event_time'] < conversion['event_time']]
            if prior_clicks:
                last_click = max(prior_clicks, key=lambda c: c['event_time'])
                yield {
                    'conversion_id':  conversion['conversion_id'],
                    'user_id':        user_id,
                    'click_id':       last_click['click_id'],
                    'campaign_id':    last_click['campaign_id'],
                    'revenue_usd':    conversion['revenue_usd'],
                    'click_to_conv_seconds': (
                        conversion['event_time'] - last_click['event_time']
                    ).total_seconds()
                }
    
    return joined | "MatchClicksToConversions" >> beam.FlatMap(match_clicks_to_conversions)
```

## 4.3 Stream-to-Static Join (Enrichment Pattern)

```python
# Most common streaming join pattern: enrich events with a dimension table
# Example: add campaign_name, channel, daily_budget to each click event

import apache_beam as beam

def enrich_with_campaign_data(clicks_stream, project_id: str):
    """
    Enrich click events with campaign metadata.
    Campaign table is small (100K rows) → use as side input (broadcast).
    
    Side input: data loaded ONCE at pipeline start, available to all workers.
    Much more efficient than joining a stream with another stream.
    """
    
    # Load campaign dimension table as a Python dict
    # This is a "side input" — small, static, loaded once
    from google.cloud import bigquery
    
    def load_campaigns_as_dict(_):
        """Load all campaigns into a dict keyed by campaign_id."""
        bq = bigquery.Client(project=project_id)
        rows = bq.query("""
            SELECT campaign_id, campaign_name, channel, daily_budget_usd
            FROM `project.marts.dim_campaigns`
            WHERE is_current = TRUE
        """).result()
        return {row.campaign_id: dict(row) for row in rows}
    
    # Create side input: load campaigns dict once, broadcast to all workers
    campaigns_dict = (
        beam.pvalue.AsSingleton(
            beam.Create([None])
            | "LoadCampaigns" >> beam.Map(load_campaigns_as_dict)
        )
    )
    
    def enrich_click(click_event, campaigns):
        """Add campaign info to a click event."""
        campaign_id = click_event.get('campaign_id')
        campaign_info = campaigns.get(campaign_id, {})
        
        return {
            **click_event,   # all original click fields
            'campaign_name':     campaign_info.get('campaign_name', 'UNKNOWN'),
            'channel':           campaign_info.get('channel', 'UNKNOWN'),
            'daily_budget_usd':  campaign_info.get('daily_budget_usd', 0)
        }
    
    return clicks_stream | "EnrichWithCampaign" >> beam.Map(
        enrich_click,
        campaigns=campaigns_dict   # pass campaigns dict as side input
    )
```

---

# SECTION 5: SQL DEEP DIVE

---

## 5.1 DAU (Daily Active Users) — With Full Explanation

```
WHAT IS DAU:
  Number of DISTINCT users who performed at least one event on a given day.
  
  "Active" depends on context:
  - Ad tech: user who saw/clicked an ad
  - App: user who opened the app
  - E-commerce: user who visited the site
  
  Key word: DISTINCT — the same user visiting 10 times counts as 1.
```

```sql
-- Simple DAU
SELECT
    DATE(event_time)          AS event_date,
    COUNT(DISTINCT user_id)   AS dau
FROM user_events
WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY event_date
ORDER BY event_date;

-- DAU with 7-day rolling average (WAU trend)
WITH daily_dau AS (
    SELECT
        DATE(event_time)        AS event_date,
        COUNT(DISTINCT user_id) AS dau
    FROM user_events
    GROUP BY event_date
)
SELECT
    event_date,
    dau,
    ROUND(AVG(dau) OVER (
        ORDER BY event_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 0) AS dau_7day_rolling_avg,
    ROUND(100.0 * (dau - LAG(dau, 7) OVER (ORDER BY event_date))
          / NULLIF(LAG(dau, 7) OVER (ORDER BY event_date), 0), 2) AS wow_pct_change
FROM daily_dau
ORDER BY event_date;

-- DAU by channel (which channel drives most active users?)
SELECT
    DATE(e.event_time)          AS event_date,
    c.channel,
    COUNT(DISTINCT e.user_id)   AS dau
FROM user_events e
JOIN dim_campaigns c ON e.campaign_id = c.campaign_id
GROUP BY event_date, c.channel
ORDER BY event_date, dau DESC;
```

## 5.2 First Login / First Event Per User

```
INTERVIEW TWIST: "Find the first login for each user ON EACH DAY they logged in."
(Different from "find the very first login ever" — read carefully!)
```

```sql
-- First login EVER per user
SELECT
    user_id,
    MIN(event_time) AS first_login_ever
FROM user_events
WHERE event_type = 'login'
GROUP BY user_id;

-- First login PER DAY per user (what your file showed, but with explanation)
SELECT
    user_id,
    DATE(event_time)        AS login_date,
    MIN(event_time)         AS first_login_that_day
FROM user_events
WHERE event_type = 'login'
GROUP BY user_id, DATE(event_time)
ORDER BY user_id, login_date;

-- First login ever + days since acquisition
SELECT
    user_id,
    MIN(event_time) AS first_login_ever,
    DATE_DIFF(CURRENT_DATE(), DATE(MIN(event_time)), DAY) AS days_since_first_login,
    COUNT(DISTINCT DATE(event_time)) AS total_active_days,
    ROUND(COUNT(DISTINCT DATE(event_time)) * 100.0
          / DATE_DIFF(CURRENT_DATE(), DATE(MIN(event_time)), DAY), 2) AS activity_pct
FROM user_events
WHERE event_type = 'login'
GROUP BY user_id
HAVING DATE_DIFF(CURRENT_DATE(), DATE(MIN(event_time)), DAY) > 0
ORDER BY first_login_ever;
```

## 5.3 Consecutive Days — Full Solution with Teaching

```
THE TECHNIQUE: date - row_number = constant for consecutive dates
(This was already covered in DEEP_SQL file, but here's the streaming context version)
```

```sql
-- Users who logged in for 3+ consecutive days (loyalty definition)
WITH daily_logins AS (
    SELECT DISTINCT user_id, DATE(event_time) AS login_date
    FROM user_events
    WHERE event_type = 'login'
),
numbered AS (
    SELECT
        user_id,
        login_date,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS rn
    FROM daily_logins
),
islands AS (
    SELECT
        user_id,
        login_date,
        DATE_SUB(login_date, INTERVAL rn DAY) AS island_key
    FROM numbered
),
streaks AS (
    SELECT
        user_id,
        MIN(login_date) AS streak_start,
        MAX(login_date) AS streak_end,
        COUNT(*)        AS streak_days
    FROM islands
    GROUP BY user_id, island_key
)
SELECT DISTINCT user_id
FROM streaks
WHERE streak_days >= 3;
```

## 5.4 Rolling N-Day Active Users

```
DEFINITION: For each day D, count distinct users who were active
            in the window [D - N + 1, D].
            
This is different from a simple GROUP BY date.
A user active on both Jan 13 and Jan 14 should be counted ONCE
for the 3-day window ending Jan 14 (Jan 12-14).
```

```sql
-- Rolling 7-day active users using self-join (correct approach)
WITH daily_users AS (
    SELECT DISTINCT
        user_id,
        DATE(event_time) AS active_date
    FROM user_events
),
date_spine AS (
    SELECT date_day
    FROM UNNEST(GENERATE_DATE_ARRAY(
        DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY),
        CURRENT_DATE(),
        INTERVAL 1 DAY
    )) AS date_day
)
SELECT
    d.date_day,
    COUNT(DISTINCT du.user_id) AS rolling_7d_users
FROM date_spine d
JOIN daily_users du
    ON du.active_date BETWEEN DATE_SUB(d.date_day, INTERVAL 6 DAY) AND d.date_day
GROUP BY d.date_day
ORDER BY d.date_day;

-- IMPORTANT: the self-join window = [date - 6, date] = 7 days inclusive
-- DATE_SUB(date, INTERVAL 6 DAY) = 6 days before = 7 day window (incl. today)
```

## 5.5 Funnel Conversion — Ordered Steps

```sql
-- Full ordered funnel: impression → click → view → add_to_cart → purchase
-- Steps MUST happen in order (each step after the previous one in time)

WITH user_steps AS (
    SELECT
        user_id,
        MIN(CASE WHEN event_type = 'impression'   THEN event_time END) AS impression_time,
        MIN(CASE WHEN event_type = 'click'        THEN event_time END) AS click_time,
        MIN(CASE WHEN event_type = 'page_view'    THEN event_time END) AS view_time,
        MIN(CASE WHEN event_type = 'add_to_cart'  THEN event_time END) AS cart_time,
        MIN(CASE WHEN event_type = 'purchase'     THEN event_time END) AS purchase_time
    FROM user_events
    WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY user_id
),
funnel AS (
    SELECT
        COUNT(*) AS total_users,
        
        COUNTIF(impression_time IS NOT NULL)
            AS reached_impression,
            
        COUNTIF(click_time IS NOT NULL
                AND click_time >= impression_time)
            AS reached_click,
            
        COUNTIF(view_time IS NOT NULL
                AND view_time >= click_time
                AND click_time >= impression_time)
            AS reached_view,
            
        COUNTIF(cart_time IS NOT NULL
                AND cart_time >= view_time
                AND view_time >= click_time
                AND click_time >= impression_time)
            AS reached_cart,
            
        COUNTIF(purchase_time IS NOT NULL
                AND purchase_time >= cart_time
                AND cart_time >= view_time
                AND view_time >= click_time
                AND click_time >= impression_time)
            AS reached_purchase
    FROM user_steps
)
SELECT
    total_users,
    reached_impression,
    reached_click,
    reached_view,
    reached_cart,
    reached_purchase,
    
    ROUND(100.0 * SAFE_DIVIDE(reached_click,    reached_impression), 2) AS imp_to_click_pct,
    ROUND(100.0 * SAFE_DIVIDE(reached_view,     reached_click),      2) AS click_to_view_pct,
    ROUND(100.0 * SAFE_DIVIDE(reached_cart,     reached_view),       2) AS view_to_cart_pct,
    ROUND(100.0 * SAFE_DIVIDE(reached_purchase, reached_cart),       2) AS cart_to_purchase_pct,
    
    ROUND(100.0 * SAFE_DIVIDE(reached_purchase, reached_impression), 4) AS overall_cvr_pct
FROM funnel;
```

## 5.6 CTR Query — With Ranking

```
CTR = Click-Through Rate = Clicks / Impressions × 100
It measures: of all users who SAW the ad, what % actually CLICKED it?
Industry average: 0.1% for display, 2-5% for search
```

```sql
-- CTR per ad per day, ranked within each day
WITH ad_metrics AS (
    SELECT
        DATE(event_time)                            AS report_date,
        ad_id,
        campaign_id,
        COUNT(CASE WHEN event_type = 'impression' THEN 1 END) AS impressions,
        COUNT(CASE WHEN event_type = 'click'      THEN 1 END) AS clicks,
        SAFE_DIVIDE(
            COUNT(CASE WHEN event_type = 'click' THEN 1 END),
            COUNT(CASE WHEN event_type = 'impression' THEN 1 END)
        ) * 100                                     AS ctr_pct
    FROM ad_events
    WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
    GROUP BY report_date, ad_id, campaign_id
)
SELECT
    report_date,
    ad_id,
    campaign_id,
    impressions,
    clicks,
    ROUND(ctr_pct, 4) AS ctr_pct,
    
    -- Rank within each day: best CTR = rank 1
    -- DENSE_RANK: no gaps if tie (question says "no gaps" → DENSE_RANK)
    DENSE_RANK() OVER (
        PARTITION BY report_date
        ORDER BY ctr_pct DESC
    ) AS ctr_rank_today,
    
    -- Rank within each campaign each day
    DENSE_RANK() OVER (
        PARTITION BY report_date, campaign_id
        ORDER BY ctr_pct DESC
    ) AS ctr_rank_in_campaign
    
FROM ad_metrics
WHERE impressions >= 100  -- minimum 100 impressions for statistical significance
ORDER BY report_date DESC, ctr_rank_today;
```

---

# SECTION 6: STREAMING SYSTEM DESIGN — CTR PIPELINE

## 6.1 Full Architecture: Real-Time CTR Dashboard

```
REQUIREMENT: Compute CTR per ad in real-time. Update every 5 minutes.
Handle late data. Scale to 100M events/day. Cost < $500/month.

FULL ARCHITECTURE:

Ad Server (generates events)
    │
    │  HTTP POST for each impression/click
    ▼
Cloud Pub/Sub Topic: "ad-events"
    │  (durability: 7 days, at-least-once)
    │
    ├──────────────────────────────────────────────────────────────┐
    │  STREAMING PATH                                              │  BATCH PATH
    ▼                                                              ▼
Cloud Dataflow Streaming Job                              Cloud Composer (Airflow)
    │                                                     Runs daily at 2 AM
    │  1. Parse JSON event                                Reads last 3 days from GCS
    │  2. Validate + deduplicate (MERGE on event_id)      Computes authoritative CTR
    │  3. Window: 5-minute Fixed Windows                  Writes to BigQuery batch table
    │  4. Aggregate: (ad_id, window) → clicks, impressions
    │  5. Compute CTR
    │  6. Handle late data (allowed_lateness = 1 hour)
    │  7. Side output for very late events → GCS
    │
    ├──────────────────────────────────────────────────────────────►
    │                                                              │
    ▼                                                              ▼
BigQuery: streaming.ctr_5min                         BigQuery: batch.ctr_daily
(preliminary, updates every 5 min)                   (authoritative, as of 2 AM)
    │
    ▼
Looker Dashboard
    "Real-time CTR" panel → streaming table
    "Daily CTR (final)" panel → batch table
    Alert: IF CTR < 0.1% for any ad in last 5 min → Slack alert
```

## 6.2 Complete Dataflow Pipeline Code for CTR

```python
import apache_beam as beam
from apache_beam.transforms import window, trigger
from apache_beam.io.gcp import bigquery as beam_bq
import json
from datetime import datetime

class ParseAdEvent(beam.DoFn):
    """Parse and validate incoming JSON event from Pub/Sub."""
    
    def process(self, element):
        try:
            event = json.loads(element.decode('utf-8'))
            
            # Validate required fields
            required = ['event_id', 'ad_id', 'event_type', 'event_timestamp']
            if not all(f in event for f in required):
                yield beam.pvalue.TaggedOutput('dead_letter', {
                    'raw': element.decode('utf-8'),
                    'error': 'Missing required fields'
                })
                return
            
            # Validate event_type
            if event['event_type'] not in ('impression', 'click'):
                yield beam.pvalue.TaggedOutput('dead_letter', {
                    'raw': element.decode('utf-8'),
                    'error': f"Unknown event_type: {event['event_type']}"
                })
                return
            
            # Emit clean event with timestamp for windowing
            yield beam.window.TimestampedValue(
                {
                    'event_id':      event['event_id'],
                    'ad_id':         event['ad_id'],
                    'campaign_id':   event.get('campaign_id', 'UNKNOWN'),
                    'event_type':    event['event_type'],
                    'event_timestamp': event['event_timestamp']
                },
                timestamp=event['event_timestamp']   # USE EVENT TIME for windowing
            )
        except Exception as e:
            yield beam.pvalue.TaggedOutput('dead_letter', {
                'raw': element.decode('utf-8'),
                'error': str(e)
            })

class ComputeCTR(beam.DoFn):
    """Compute CTR from aggregated clicks and impressions per window."""
    
    def process(self, element, window=beam.DoFn.WindowParam):
        ad_id, metrics = element
        
        clicks      = metrics['clicks']
        impressions = metrics['impressions']
        ctr         = (clicks / impressions * 100) if impressions > 0 else 0
        
        yield {
            'window_start':  window.start.to_utc_datetime().isoformat(),
            'window_end':    window.end.to_utc_datetime().isoformat(),
            'ad_id':         ad_id,
            'impressions':   impressions,
            'clicks':        clicks,
            'ctr_pct':       round(ctr, 4),
            'processed_at':  datetime.utcnow().isoformat()
        }

def run_ctr_pipeline():
    
    options = beam.options.pipeline_options.PipelineOptions([
        '--runner=DataflowRunner',
        '--project=costco-martech',
        '--region=us-central1',
        '--streaming',
        '--enable_streaming_engine',
        '--autoscaling_algorithm=THROUGHPUT_BASED',
        '--max_num_workers=10',
    ])
    
    with beam.Pipeline(options=options) as p:
        
        # Step 1: Read raw events from Pub/Sub
        raw = p | 'ReadPubSub' >> beam.io.ReadFromPubSub(
            subscription='projects/costco-martech/subscriptions/ad-events-sub'
        )
        
        # Step 2: Parse, validate, emit with event timestamp
        parsed = raw | 'Parse' >> beam.ParDo(
            ParseAdEvent()
        ).with_outputs('dead_letter', main='valid')
        
        # Step 3: Window into 5-minute buckets using EVENT TIME
        windowed = parsed.valid | 'Window' >> beam.WindowInto(
            window.FixedWindows(5 * 60),   # 5-minute windows
            
            allowed_lateness=window.Duration(seconds=3600),  # 1 hour
            
            trigger=trigger.AfterWatermark(
                early=trigger.AfterProcessingTime(30),    # emit preliminary every 30 sec
                late=trigger.AfterCount(1)                # emit update per late event
            ),
            accumulation_mode=trigger.AccumulationMode.ACCUMULATING
        )
        
        # Step 4: Count clicks and impressions per ad per window
        aggregated = (
            windowed
            | 'KeyByAd' >> beam.Map(lambda e: (e['ad_id'], e))
            | 'GroupByAd' >> beam.GroupByKey()
            | 'SumMetrics' >> beam.Map(lambda kv: (
                kv[0],  # ad_id
                {
                    'clicks':      sum(1 for e in kv[1] if e['event_type'] == 'click'),
                    'impressions': sum(1 for e in kv[1] if e['event_type'] == 'impression')
                }
            ))
        )
        
        # Step 5: Compute CTR
        ctr_results = aggregated | 'ComputeCTR' >> beam.ParDo(ComputeCTR())
        
        # Step 6: Write to BigQuery (idempotent MERGE via storage write API)
        ctr_results | 'WriteToBigQuery' >> beam_bq.WriteToBigQuery(
            table='costco-martech:streaming.ctr_5min',
            schema={
                'fields': [
                    {'name': 'window_start',  'type': 'STRING'},
                    {'name': 'window_end',    'type': 'STRING'},
                    {'name': 'ad_id',         'type': 'STRING'},
                    {'name': 'impressions',   'type': 'INTEGER'},
                    {'name': 'clicks',        'type': 'INTEGER'},
                    {'name': 'ctr_pct',       'type': 'FLOAT'},
                    {'name': 'processed_at',  'type': 'STRING'},
                ]
            },
            write_disposition=beam_bq.BigQueryDisposition.WRITE_APPEND,
        )
        
        # Step 7: Dead letter — write to GCS for investigation
        parsed.dead_letter | 'WriteDeadLetter' >> beam_bq.WriteToBigQuery(
            table='costco-martech:monitoring.dead_letter_ad_events'
        )

if __name__ == '__main__':
    run_ctr_pipeline()
```

---

# SECTION 7: INTERVIEW GOLD POINTS — EXPANDED

These are the talking points that distinguish a senior engineer from a mid-level one.

## 7.1 Accuracy vs Latency Tradeoff

```
THE CORE TENSION:
  Lower latency → less time to collect late data → less accurate results
  Higher accuracy → longer windows → higher latency

EXAMPLES:
  5-second window close: very fast, but misses 30% of late mobile events
  1-hour window close:   misses only 1%, but 1 hour old
  Batch (24 hours):      misses < 0.001%, but 6-24 hours old

HOW TO ANSWER IN INTERVIEW:
  "The right answer depends on the use case. For real-time campaign monitoring,
   I accept ~5% inaccuracy to get results in seconds for intraday decisions.
   For financial reporting that drives billing or budget allocation,
   I wait for the batch path which gives authoritative numbers with < 0.01% error.
   Most production systems I've designed use Lambda Architecture:
   streaming for fast/approximate, batch for accurate/complete."
```

## 7.2 Stateful Processing is Core

```
WHAT STATEFULNESS MEANS:
  Some operations require MEMORY across multiple events.
  
  Stateless: each event processed independently (simple transforms, filters)
  Stateful: processing depends on previously seen events (aggregations, dedup, sessions)
  
  Examples of STATEFUL operations:
  - Counting clicks per ad (must remember prior count)
  - Detecting consecutive days (must remember prior login dates)
  - Session detection (must remember last event time per user)
  - Deduplication (must remember seen event IDs)
  
  State in Dataflow:
  - Stored per KEY (e.g., per user_id, per ad_id)
  - Stored in memory + checkpointed to GCS for fault tolerance
  - Has TTL (time-to-live) to prevent unbounded memory growth
  
  State is what makes streaming COMPLEX and EXPENSIVE:
  More keys = more state = more memory = bigger workers = more cost
  Design your keys carefully to avoid state explosion.
```

## 7.3 The "Exactly-Once is Simulated" Point

```
SENIOR ANSWER:
  "True exactly-once requires atomic coordination across the source, processing,
   and sink. In practice, we achieve effectively-exactly-once results through
   two mechanisms: at-least-once delivery (retry until success, no data loss)
   combined with idempotent writes at the sink.
   
   Idempotent write means: writing the same event twice produces the same result
   as writing it once. A MERGE on event_id in BigQuery achieves this —
   the second write is a no-op because the row already exists.
   
   For Costco's ad click pipeline, I'd use MERGE on (event_id, window_start)
   so that even if Dataflow reprocesses a window due to a checkpoint replay,
   the BigQuery CTR table remains accurate — no double-counting of clicks."
```

---

# SECTION 8: INTERVIEW QUESTIONS — EASY TO VERY HARD

---

## EASY QUESTIONS

### E1: "What is streaming and when would you use it over batch?"

**Answer**: Streaming processes data continuously as events arrive, giving results in seconds or minutes. Batch processes data in large chunks at scheduled intervals, giving results in hours.

I'd choose streaming when the business requires low latency: fraud detection (must block a transaction before it's approved), real-time campaign dashboards (marketing team watches ROAS live and pauses campaigns that drop below threshold), or event-driven triggers (send cart abandonment email within 10 minutes).

I'd choose batch when: latency > 1 hour is acceptable (overnight reports), the transformation is too complex for streaming (multi-day joins), or I need authoritative final numbers (financial reconciliation). Streaming is always-on infrastructure — more complex and more expensive — so I only use it when the business genuinely needs sub-5-minute latency.

---

### E2: "Explain event time vs processing time with an example."

**Answer**: Event time is when the event actually happened in the real world. Processing time is when the event arrived at my streaming system.

Example from ad analytics: A user clicks an ad at 2:15 PM on their mobile phone. The phone app batches events and only sends them when the user gets home and connects to WiFi at 2:47 PM. The event's event time is 2:15 PM; its processing time is 2:47 PM — 32 minutes apart.

This matters because if I compute "clicks in the 2 PM hour" using processing time, I'd exclude the 2:15 PM click (it arrived after 2:30 PM). Using event time, it's correctly counted in the 2 PM hour. All production streaming systems use event time for correct aggregations.

---

### E3: "What are the three window types in streaming?"

**Answer**: Fixed (tumbling) windows, sliding windows, and session windows.

Fixed windows divide time into equal non-overlapping buckets — "clicks per hour" means each click belongs to exactly one 1-hour bucket. Simple and memory-efficient.

Sliding windows overlap — "ROAS over the last 30 minutes, updated every 5 minutes" creates overlapping windows where each event belongs to multiple windows (30/5 = 6 windows). Good for rolling metrics but 6x compute cost.

Session windows are dynamic — defined by user inactivity gaps. If a user has a gap > 30 minutes between events, that's a new session. Variable size, independent per user, and requires stateful processing. Used for user journey analysis.

---

## MEDIUM QUESTIONS

### M1: "How does a watermark work? What happens when it stalls?"

**Answer**: A watermark is the streaming engine's estimate of event-time completeness. Specifically: `watermark = max(event_time_seen) - allowed_lateness`. It tells the engine: "I'm confident all events with event_time ≤ watermark have arrived."

When the watermark passes the end of a window (e.g., 3 PM for a 2-3 PM window), the window closes and its final result is emitted. This is what allows infinite streams to produce finite results.

A watermark stall happens when one partition of the source stops producing events — in a multi-partition setup, the global watermark is the minimum across all partitions. If the APAC partition's pipeline is down, the global watermark stays at APAC's last event time even as US and EU advance. Windows never close. The dashboard stops updating.

Detection: monitor `data_freshness` metric (current_time - watermark). If it exceeds 10 minutes, alert.

Fix: investigate the stuck partition. Short-term: configure a maximum lag so the watermark advances anyway (APAC events arriving after this are treated as "late" — some data loss risk, but the pipeline keeps running).

---

### M2: "Write a SQL query to compute CTR per ad per day, ranked from highest to lowest within each day."

**Answer**: *(walk through approach first)*

"I need to: group events by (ad_id, date), count clicks and impressions separately using conditional aggregation, compute CTR as clicks/impressions, then rank with DENSE_RANK partitioned by date ordered by CTR descending."

```sql
WITH ad_metrics AS (
    SELECT
        DATE(event_time)   AS report_date,
        ad_id,
        COUNT(CASE WHEN event_type = 'impression' THEN 1 END) AS impressions,
        COUNT(CASE WHEN event_type = 'click'      THEN 1 END) AS clicks
    FROM ad_events
    WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
    GROUP BY 1, 2
)
SELECT
    report_date,
    ad_id,
    impressions,
    clicks,
    ROUND(SAFE_DIVIDE(clicks, impressions) * 100, 4) AS ctr_pct,
    DENSE_RANK() OVER (
        PARTITION BY report_date
        ORDER BY SAFE_DIVIDE(clicks, impressions) DESC
    ) AS ctr_rank
FROM ad_metrics
WHERE impressions >= 100
ORDER BY report_date DESC, ctr_rank;
```

---

## HARD QUESTIONS

### H1: "Design a streaming system to detect when a campaign's ROAS drops below 1.5 and send a Slack alert within 2 minutes."

**Answer**:

*Architecture overview first*: "I'd use Pub/Sub → Dataflow → BigQuery with a parallel alerting path. Let me walk through each component."

**Ingestion**: Ad click and conversion events published to Pub/Sub topic `ad-events`. At-least-once delivery; I handle deduplication downstream.

**Dataflow pipeline**:
1. Parse and validate events, route malformed to dead letter
2. Apply 5-minute Fixed Windows using event time
3. Separate streams: aggregate clicks + spend per campaign; aggregate conversions + revenue per campaign
4. Join both streams within the same 5-minute window using CoGroupByKey on campaign_id
5. Compute ROAS = total_revenue / total_spend for each (campaign, window)
6. Filter: if ROAS < 1.5 AND spend > $10 (ignore tiny spend campaigns), emit an alert event
7. Route alert events to a separate Pub/Sub topic `roas-alerts`
8. A Cloud Function subscribes to `roas-alerts` → calls Slack API → posts to #campaign-alerts channel

**Late data handling**: 5-minute windows with 30-minute allowed_lateness. The preliminary result fires every 30 seconds (early trigger). If ROAS looks fine at 30 seconds but a late conversion arrives 20 minutes later and ROAS drops below 1.5 → a second alert fires. I'd add de-duplication in the Cloud Function: don't re-alert for the same campaign unless 30 minutes have passed or ROAS recovered above 2.0.

**2-minute SLA**: The early trigger fires every 30 seconds of processing time, so worst case: an event arrives, waits up to 30 seconds, window fires, Dataflow writes to Pub/Sub, Cloud Function receives and calls Slack API. Total: under 1 minute for the alert path.

---

### H2: "What happens if your Dataflow pipeline is down for 3 hours and then recovers? Walk through exactly what happens."

**Answer**:

"Three things happen in sequence: Pub/Sub holds the messages, Dataflow recovers from checkpoint, and the pipeline catches up with backlog — let me walk through each."

**During the 3-hour outage**: Pub/Sub is still running. Every event published during the outage is durably stored in Pub/Sub's message store (7-day retention). Nothing is lost. The Pub/Sub subscription's unacknowledged message backlog grows. At 100K events/hour × 3 hours = 300K messages waiting.

**Recovery**: Dataflow detects the worker failure (within 1-2 minutes). It provisions new workers and reads the last checkpoint from GCS. The checkpoint contains: the exact Pub/Sub offset of the last successfully processed message, all in-flight window accumulators up to that point, and the current watermark position.

New workers resume pulling from Pub/Sub starting at the checkpointed offset. The 300K backlogged messages are available. Dataflow processes them at higher-than-normal throughput (workers process as fast as possible to catch up with the backlog).

**Watermark behavior**: During catchup, the watermark advances rapidly as events with progressively newer event times are processed. Windows that should have closed during the 3-hour outage will close correctly as the watermark passes their end times. The 3-hour gap in the dashboard will fill in progressively.

**Duplicate risk**: The last checkpoint might be 30 seconds before the crash. Events processed in those 30 seconds will be reprocessed (at-least-once). My MERGE-on-event-id in BigQuery handles this — the second write is a no-op.

**Alerting implication**: ROAS alerts that should have fired during the outage will fire during catchup. I need alert de-duplication logic to avoid sending 3 hours of "ROAS is low" messages all at once when the pipeline recovers.

---

## VERY HARD QUESTIONS

### VH1: "You have a streaming CTR pipeline. The marketing team says the real-time CTR numbers look 15% higher than the final daily numbers from the batch pipeline. Diagnose and fix."

**Answer**:

"This is a discrepancy between streaming (preliminary) and batch (final) numbers. 15% higher in streaming suggests the streaming pipeline is overcounting or the batch is undercounting. Let me systematically diagnose."

**Step 1: Confirm the discrepancy is consistent**
```sql
-- Compare streaming vs batch CTR for the same campaigns/dates
SELECT
    s.report_date,
    s.ad_id,
    s.ctr_pct AS streaming_ctr,
    b.ctr_pct AS batch_ctr,
    ROUND(100.0 * (s.ctr_pct - b.ctr_pct) / b.ctr_pct, 2) AS pct_diff
FROM streaming.ctr_5min_daily_agg s
JOIN batch.ctr_daily b USING (report_date, ad_id)
WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND ABS(s.ctr_pct - b.ctr_pct) / b.ctr_pct > 0.1  -- >10% discrepancy
ORDER BY pct_diff DESC;
```

**Step 2: Check if it's clicks or impressions that differ**
```sql
-- Higher streaming CTR = higher click count OR lower impression count
SELECT
    report_date, ad_id,
    s.clicks AS stream_clicks, b.clicks AS batch_clicks,
    s.impressions AS stream_imp, b.impressions AS batch_imp
FROM streaming.ctr_daily_agg s
JOIN batch.ctr_daily b USING (report_date, ad_id)
WHERE report_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY);
```

**Possible Root Cause 1: Streaming has duplicate clicks**

Streaming uses at-least-once + APPEND to BigQuery. If MERGE deduplication isn't working, duplicate click events inflate the click count → higher CTR.

Fix: Verify MERGE logic is using correct key (event_id + ad_id). Check duplicate count in streaming table:
```sql
SELECT event_id, COUNT(*) FROM streaming.ctr_5min GROUP BY event_id HAVING COUNT(*) > 1 LIMIT 10;
```

**Possible Root Cause 2: Late impressions arrive after streaming window closes**

If many impressions arrive late (after the window), streaming shows fewer impressions → higher CTR (clicks ÷ fewer impressions = higher ratio). Batch sees all impressions.

Fix: Increase allowed_lateness on the streaming pipeline's impression count. Or: flag streaming CTR as "preliminary" and explain to users that impressions may increase.

**Possible Root Cause 3: Different time alignment**

Streaming uses event time. Batch might be using a different time zone or different daily cutoff (midnight UTC vs midnight PST). A click at 11:58 PM PST is in "today" for streaming (event time) but might be in "tomorrow" for batch.

Fix: Ensure both pipelines use the same event_time field and the same time zone (UTC).

**Likely answer for 15% consistent gap**: Duplicate events in streaming (most common cause). I'd add a deduplication step before the BigQuery write using MERGE on (event_id, event_date).

---

### VH2: "Design an exactly-once, late-data-aware, multi-channel attribution streaming pipeline for Costco's MarTech platform. Requirements: 100M events/day, < 5 min latency, handles cost adjustments up to 48 hours later, costs < $1,000/month."

**Answer**: *(This is a 10-minute interview answer — hit these points in order)*

**Architecture choice: Lambda Architecture** — streaming for real-time, batch for authoritative.

**Streaming path** (handles 95% of events within 5 minutes):
- Pub/Sub: one topic for all channels (Google, Meta, TikTok clicks/conversions), partition key = user_id for ordering
- Dataflow streaming: 5-min Fixed Windows, event time, allowed_lateness = 1 hour
- Last-touch attribution in window: CoGroupByKey(clicks, conversions) per user per window
- Output: BigQuery streaming table with MERGE on (event_id, window_start) for idempotency
- Latency: < 2 minutes end-to-end

**Batch path** (handles late cost adjustments up to 48 hours):
- Dataflow or Spark batch job, runs at 2 AM daily
- Reads last 3 days from GCS (raw events archived by streaming pipeline)
- Recomputes attribution with COMPLETE data including all late cost adjustments
- Overwrites last 3 days' partitions in BigQuery batch table via INSERT OVERWRITE
- This is the authoritative source for finance/billing

**Deduplication**: MERGE on event_id at BigQuery sink. Streaming pipeline also uses Dataflow's stateful deduplication (BagState per event_id) to avoid writing duplicates to the staging area.

**Late data handling**: 
- 0-1 hour late: streaming allowed_lateness handles it, window re-fires
- 1 hour - 48 hours late: side output → GCS → batch path picks up and includes
- > 48 hours: dead letter queue, alert, manual review

**Cost estimate at 100M events/day**:
- Pub/Sub: 100M msgs × $0.04/1M = $4/day = $120/month
- Dataflow streaming: ~3 n1-standard-2 workers × $0.048/hour × 720 hours = $104/month
- GCS for raw event archive: 100M × 500 bytes = 50GB/day × 30 = 1.5TB → $30/month
- BigQuery streaming inserts: 100M × 1KB = 100GB/day × $0.01/200MB = $5/day = $150/month
- BigQuery batch query (2 AM job): 3 days × 50GB = 150GB × $6.25/TB = ~$1
- Total: ~$404/month → well under $1,000

---

# FINAL INTERVIEW CHEAT SHEET

```
ANY STREAMING QUESTION: MENTION THESE IN ORDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. EVENT TIME vs PROCESSING TIME
   "I always use event time to ensure correctness despite delivery delays."

2. WINDOWING
   "Fixed windows for periodic metrics, sliding for rolling averages,
    session for user journey analysis."

3. WATERMARK
   "Watermark = max(event_time_seen) - allowed_lateness.
    It signals when a window can close. Stalls hurt latency."

4. LATE DATA STRATEGY (TIERED)
   "≤1 hour: allowed_lateness. >1 hour: batch reprocessing.
    Nothing is ever lost — side outputs route late data to GCS."

5. EXACTLY-ONCE
   "At-least-once delivery + idempotent MERGE on event_id = effectively exactly-once."

6. DEDUPLICATION
   "MERGE on event_id at the BigQuery sink. Stateful dedup in Dataflow for hot paths."

7. ARCHITECTURE CHOICE
   "Lambda: streaming for real-time approximate, batch for authoritative.
    This covers both the marketing team's real-time dashboard
    AND the finance team's billing reconciliation."

8. MONITORING
   "data_freshness (should be < 2 min), backlog_bytes (should not grow),
    dead_letter_count (should be near zero)."
```
