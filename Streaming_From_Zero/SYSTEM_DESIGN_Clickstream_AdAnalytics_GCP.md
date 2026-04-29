# System Design: Clickstream Ad Analytics Platform on GCP
## Costco Sr. Data Engineer — Round 2 System Design Reference

---

# HOW TO DELIVER THIS IN AN INTERVIEW

A system design answer has a structure. Never jump straight to architecture.
Follow this exact sequence:

```
1. CLARIFY REQUIREMENTS          (3-5 minutes)  ← most candidates skip this
2. ESTIMATE SCALE                (2-3 minutes)  ← shows you think at scale
3. HIGH-LEVEL ARCHITECTURE       (3-5 minutes)  ← boxes and arrows
4. DEEP DIVE each component      (15-20 minutes) ← the real interview
5. HANDLE EDGE CASES             (5 minutes)    ← late data, failures, scale
6. TRADE-OFFS AND ALTERNATIVES   (3-5 minutes)  ← senior mindset
```

---

# STEP 1: CLARIFY REQUIREMENTS

**Never design without asking these first. It shows senior thinking.**

Say this out loud:

*"Before I start designing, I want to make sure I understand the requirements clearly. Can I ask a few questions?"*

**Functional questions you ask:**
```
Q: What metrics do we need to compute?
A (assume): CTR, ROAS, conversion rate, spend, impressions, revenue per campaign

Q: What is the definition of "conversion"?
A (assume): A purchase that happens within 30 days of an ad click by the same user

Q: What devices/sources produce events?
A (assume): Mobile apps (iOS/Android), web browsers, and potentially 3rd-party
            ad networks (Google Ads, Meta) via their APIs

Q: Who consumes the metrics? (BI dashboards, internal APIs, alerts?)
A (assume): Marketing team dashboards (Looker), automated budget alerts,
            and a daily finance report

Q: Do we need real-time metrics or is batch acceptable?
A (assume): Both. Real-time for live dashboard (< 5 min latency)
            + authoritative daily batch for finance/billing
```

**Non-functional questions you ask:**
```
Q: What is the expected event volume?
A (assume): 100 million events per day, ~10K events per second at peak

Q: What latency is acceptable for the dashboard?
A (assume): < 5 minutes for real-time metrics, daily batch by 8 AM

Q: What's the data retention requirement?
A (assume): 2 years hot (queryable), 5 years archived (restorable)

Q: Any compliance requirements?
A (assume): GDPR — member PII must be masked, right-to-erasure support

Q: Availability SLA?
A (assume): 99.9% for the ingestion pipeline (< 9 hours downtime/year)
```

**After clarifying, summarize:**

*"So to summarize: we need to capture clickstream events from mobile apps, web browsers, and third-party ad networks — about 100 million events per day at peak 10K/sec. We need to compute ad conversion metrics like CTR and ROAS with < 5-minute latency for live dashboards, and an authoritative daily batch for finance. Late data is expected (mobile events can arrive up to 48 hours late). We're on GCP. Did I capture that correctly?"*

---

# STEP 2: SCALE ESTIMATION

**Do this on a whiteboard or out loud. Shows you think in numbers.**

```
EVENT VOLUME:
  100M events/day ÷ 86,400 sec/day = ~1,157 events/sec average
  Peak (business hours, assume 3x average) = ~3,500 events/sec
  Absolute peak (flash sale, campaign launch) = 10,000 events/sec

EVENT SIZE:
  Typical clickstream event JSON = 500 bytes - 2KB
  Assume average: 1KB per event

DAILY DATA VOLUME:
  100M events × 1KB = 100GB raw JSON per day
  Compressed (Parquet, 5:1 ratio) = ~20GB per day
  Yearly: 20GB × 365 = ~7.3TB per year of processed data

STORAGE (2 years hot):
  7.3TB × 2 = ~15TB in BigQuery
  BigQuery storage: $0.02/GB/month = $300/month
  GCS raw archive: 15TB × $0.02/GB = $300/month

COMPUTE ESTIMATE:
  Pub/Sub: 100M msgs × $0.04/1M = $4/day = $120/month
  Dataflow streaming: 3 workers (n1-standard-4) × $0.19/hr × 720hr = $410/month
  BigQuery queries: 10TB/month × $6.25/TB = $62/month
  Total: ~$900/month (well within typical enterprise budget)

LATENCY BUDGET:
  Event happens on device →
  App SDK sends to Pub/Sub: 100ms - 2s (network)
  Pub/Sub → Dataflow consumer: < 500ms
  Dataflow processing (parse + window): 1-5 seconds
  Write to BigQuery: < 2 seconds
  Looker queries BigQuery: 1-3 seconds
  Total end-to-end: < 1 minute for 95% of events ✓ (goal: < 5 minutes)
```

---

# STEP 3: HIGH-LEVEL ARCHITECTURE

Draw this on the whiteboard. Walk through it left to right.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    CLICKSTREAM AD ANALYTICS PLATFORM — GCP                      │
└─────────────────────────────────────────────────────────────────────────────────┘

SOURCES                    INGESTION              PROCESSING           SERVING
──────────────────────     ─────────────────      ─────────────────    ────────────
Mobile App (iOS)    ──►┐
Mobile App (Android)──►├──► Cloud             ┌──► Dataflow     ──►┐
Web Browser JS SDK  ──►│    Pub/Sub           │    (Streaming)      ├──► BigQuery
Server-Side Events  ──►│    Topic:            │    Window/Agg       │    (streaming)
                        │    "ad-events"   ───┤                     │
                        │    (durable 7d)      │                     │──► Looker
Google Ads API  ────►┐  │                      └──► GCS Archive ──►┐│    Dashboard
Meta Ads API    ────►├──► Separate            (raw parquet)        ││
TikTok API      ────►┘   Pub/Sub topic                             ├┘
                          "cost-events"    ───► Dataflow      ──►  │──► Alert System
                                              (Daily Batch)        │    (ROAS drops)
                                                                    │
                                                                    └──► BigQuery
                                                                         (batch/
                                                                          authoritative)
```

**The three paths:**
```
PATH 1 — REAL-TIME STREAMING (< 5 min latency):
  Device → Pub/Sub → Dataflow Streaming → BigQuery streaming tables → Looker

PATH 2 — BATCH REPROCESSING (authoritative, handles late data):
  GCS raw archive → Dataflow Batch (nightly) → BigQuery batch tables → Finance report

PATH 3 — THIRD-PARTY COST INGESTION:
  Google/Meta/TikTok APIs → Separate pipeline → BigQuery → join with click metrics
```

---

# STEP 4: DEEP DIVE — EVERY COMPONENT

---

## COMPONENT 1: EVENT COLLECTION — SOURCES AND SDKs

### Problem to solve
Events come from heterogeneous sources — iOS apps, Android apps, web browsers, server-side systems. Each has different constraints:

```
MOBILE (iOS/Android):
  Constraint: Battery, network availability, user goes offline
  Solution: Client-side SDK with local buffering
  
  How it works:
  1. Ad is displayed to user → SDK records "impression" event locally
  2. User clicks → SDK records "click" event locally
  3. SDK buffers events in memory/local storage (up to 1,000 events or 60 seconds)
  4. When WiFi/4G available: SDK sends batch to ingestion endpoint via HTTPS
  5. On failure: exponential backoff retry (not flood the server)
  6. Each event has a client-generated UUID (for deduplication downstream)
  
  WHY LOCAL BUFFER:
  Sending every event immediately = too many HTTP requests = battery drain
  Buffer and batch = fewer connections = better battery + reliability

WEB BROWSER (JavaScript):
  Constraint: User can close browser mid-session, ad blockers
  Solution: Beacon API + Server-Side Tagging
  
  Traditional pixel/JS tag:
  → Blocked by ad blockers (30% of users)
  → Lost when user navigates away
  
  Better: Server-side tagging via Google Tag Manager Server-Side
  Browser sends one event to YOUR server → your server fans out to all platforms
  Benefits: Not blocked by ad blockers, more reliable, privacy-compliant
  
  Even better for purchase events: fire from your own backend
  (user completes purchase → your order service fires the conversion event)
  → Cannot be blocked, guaranteed delivery

SERVER-SIDE (purchase confirmation, cost updates):
  Most reliable: backend fires event when purchase confirmed
  → Event contains: order_id, member_id, items, revenue
  → This is the AUTHORITATIVE conversion signal
  
THIRD-PARTY (Google Ads, Meta, TikTok APIs):
  Separate polling pipeline:
  Cloud Scheduler triggers Cloud Function every 15 minutes
  → Calls Google Ads API for last-hour cost data
  → Calls Meta API for last-hour impression/click data
  → Publishes to separate Pub/Sub topic "cost-events"
  Note: Cost data from these APIs adjusts for up to 48 hours (fraud filtering)
```

### Event Schema Design

```json
{
  "event_id":        "evt_uuid_v4_here",
  "event_type":      "click",
  "event_timestamp": "2024-01-15T14:23:07.432Z",
  "schema_version":  "2.1",
  
  "device": {
    "type":       "mobile",
    "os":         "iOS",
    "os_version": "17.1",
    "app_version":"3.4.2",
    "device_id":  "dev_uuid_hashed"
  },
  
  "ad": {
    "ad_id":       "ad_123",
    "campaign_id": "camp_456",
    "channel":     "meta_instagram",
    "creative_id": "cr_789",
    "placement":   "feed"
  },
  
  "user": {
    "member_id":      "M_hashed_sha256",  ← PII hashed at SDK level
    "anonymous_id":   "anon_uuid",
    "session_id":     "sess_uuid"
  },
  
  "context": {
    "page_url":    "https://costco.com/membership",
    "referrer":    "https://meta.com",
    "utm_source":  "meta",
    "utm_campaign":"summer_membership_2024"
  },
  
  "_sdk_sent_at":    "2024-01-15T14:23:09.100Z",
  "_received_at":    "2024-01-15T14:23:09.850Z"
}
```

**Why this schema design:**
- `event_id` (UUID): enables idempotent deduplication downstream
- `event_timestamp` vs `_received_at`: event time vs processing time distinction — critical for windowing
- Hashed PII at SDK level: never sends raw member_id — GDPR safe
- `schema_version`: enables schema evolution without breaking consumers
- Nested structure: keeps related fields together (device, ad, user, context)

---

## COMPONENT 2: INGESTION — CLOUD PUB/SUB

### Why Pub/Sub?

```
DIRECT WRITE TO BIGQUERY (naïve approach) — DON'T DO THIS:
  Device → BigQuery Streaming Insert API
  
  Problems:
  × BigQuery streaming insert: $0.01 per 200MB = expensive at 100M events/day
  × No buffering: if BigQuery has an outage, events are lost
  × No fan-out: can't send same events to multiple consumers (ML, monitoring)
  × Tight coupling: devices talking directly to your analytics DB = bad design

PUB/SUB (correct approach):
  Device → Pub/Sub → (multiple consumers)
  
  Benefits:
  ✓ Durable: messages stored up to 7 days (survive outages)
  ✓ Fan-out: one topic, many subscriptions (Dataflow, BigQuery direct, Cloud Function)
  ✓ Decoupling: producers and consumers don't know about each other
  ✓ At-least-once: guaranteed delivery with retry
  ✓ Scales to millions of messages/second automatically
  ✓ Cost: $0.04/1M messages = $4/day for 100M events
```

### Pub/Sub Topic Design

```
TOPIC STRUCTURE:

Topic: "ad-events"
  └── Subscription: "ad-events-dataflow-streaming"  → Dataflow streaming job
  └── Subscription: "ad-events-gcs-archive"         → Dataflow GCS archive job
  └── Subscription: "ad-events-monitoring"          → Cloud Function for real-time alerts

Topic: "ad-cost-events" (from ad platform APIs)
  └── Subscription: "cost-events-dataflow"          → Joins with click data

Topic: "ad-events-dead-letter" (failed messages)
  └── Subscription: "dead-letter-monitoring"        → Alert on dead letters

WHY SEPARATE TOPICS:
  Click/impression events: high volume, low cost per event ($0.04/1M)
  Cost events from APIs: low volume, contain financial data (different retention)
  Dead letter: separate so bad messages don't block good ones
```

### Ingestion API Design

```
OPTION A: Direct SDK → Pub/Sub
  SDK calls Pub/Sub REST API directly
  Problem: requires distributing GCP credentials to client devices (security risk)

OPTION B: Ingestion API Gateway (correct approach)
  SDK → HTTPS → Cloud Run/App Engine ingestion service → Pub/Sub
  
  Benefits:
  + Authentication at API level (API keys, not GCP service accounts)
  + Rate limiting per client (prevent abuse)
  + Validation at edge (reject malformed events early)
  + Schema version routing (v1 events → v1 parser, v2 → v2 parser)
  + Can swap Pub/Sub for Kafka later without changing SDK

INGESTION SERVICE (Cloud Run):
  - Stateless, auto-scales to handle peak load
  - Accepts: POST /events with JSON body or batch of events
  - Validates: schema version, required fields, event_id not null
  - Enriches: adds _received_at timestamp (server time)
  - Publishes: to Pub/Sub with ordering key = campaign_id
  - Returns: 200 OK with event_ids for dedup tracking
  - Handles batch: one HTTP call = up to 1,000 events (mobile SDK optimization)
```

---

## COMPONENT 3: STREAM PROCESSING — CLOUD DATAFLOW

### Architecture Decision: Why Dataflow?

```
ALTERNATIVES CONSIDERED:

Apache Kafka + Flink:
  ✓ Very low latency (milliseconds)
  ✓ Stateful processing, exactly-once
  ✗ Need to manage Kafka cluster (ops burden)
  ✗ Need to size Kafka brokers, Flink TaskManagers
  ✗ Team needs Kafka/Flink expertise
  ✗ Costlier at our scale ($2,000-5,000/month infrastructure)

Spark Streaming (Dataproc):
  ✓ Team knows Spark
  ✓ Micro-batch achieves low latency
  ✗ Not true streaming (micro-batches, not per-event)
  ✗ Cluster management overhead
  ✗ Higher latency than Dataflow

Cloud Dataflow (Apache Beam):
  ✓ Fully managed — no cluster to manage
  ✓ True streaming with watermarks and event time
  ✓ Auto-scales (add workers on high load, remove on low load)
  ✓ Native GCP integration (Pub/Sub → Dataflow → BigQuery)
  ✓ Supports exactly-once semantics with Streaming Engine
  ✓ Built-in checkpointing to GCS (auto-recovery)
  ✗ Higher latency than Kafka/Flink (seconds, not milliseconds)
  ✗ Apache Beam API has learning curve
  → CHOSEN for this design
```

### Streaming Pipeline — Step by Step

```
DATAFLOW PIPELINE FLOW:

Pub/Sub "ad-events"
    │
    ▼ Step 1: READ
    ReadFromPubSub(subscription="ad-events-dataflow-streaming")
    → Emits: raw bytes per message
    
    │
    ▼ Step 2: PARSE AND VALIDATE  
    ParseAndValidate (DoFn)
    → Parse JSON
    → Validate required fields (event_id, event_type, timestamps)
    → Validate event_type in allowed set {impression, click, page_view, add_to_cart, purchase}
    → Attach event_timestamp as Beam timestamp (for event-time windowing)
    → Route malformed events → dead letter output
    
    │
    ▼ Step 3: DEDUPLICATE
    DeduplicateByEventId (Stateful DoFn with BagState)
    → For each event_id: check if seen before (state per event_id key)
    → If first time: emit event, mark as seen
    → If duplicate: drop silently (log counter)
    → State TTL: 24 hours (events older than 24h can't be duplicates)
    
    │
    ▼ Step 4: ENRICH
    EnrichWithCampaignData (side input)
    → Load dim_campaigns from BigQuery as a side input dict (loaded once at startup)
    → Add: campaign_name, channel_category, daily_budget_usd to each event
    → Refresh side input every 5 minutes (campaigns can change)
    
    │
    ▼ Step 5: WINDOW
    WindowInto(FixedWindows(5 * 60))  ← 5-minute windows
    → Uses EVENT TIME (event_timestamp field), not processing time
    → allowed_lateness = 60 minutes
    → Trigger: AfterWatermark(early=AfterProcessingTime(30), late=AfterCount(1))
    → Accumulation: ACCUMULATING (each fire includes all prior data)
    
    │
    ▼ Step 6: AGGREGATE PER WINDOW
    GroupByKey(campaign_id + channel)
    → CombinePerKey: count impressions, clicks, unique_users (approx)
    → Separate pipeline: join with conversions stream
    
    │
    ▼ Step 7: COMPUTE METRICS
    ComputeMetrics (DoFn)
    → CTR = clicks / impressions
    → CVR = conversions / clicks
    → ROAS = revenue / spend (spend from cost-events join)
    → CPC = spend / clicks
    
    │
    ├──► Step 8a: WRITE TO BIGQUERY (streaming table)
    │    WriteToBigQuery("streaming.ad_metrics_5min")
    │    → WRITE_APPEND (new rows per window fire)
    │    → Dedup on (window_start, campaign_id, channel) via MERGE job
    │
    └──► Step 8b: WRITE RAW TO GCS (for batch reprocessing)
         WriteToGCS("gs://costco-data/raw/ad-events/{date}/")
         → Parquet format, snappy compression
         → Partition by event_date
         → These files are the source of truth for batch path
```

### Handling the Conversion Attribution Join

```
CHALLENGE: Matching clicks to purchases for attribution.

A click happens at 2:15 PM.
A purchase happens at 2:45 PM (same user, 30 minutes later).

These arrive as TWO SEPARATE events on TWO SEPARATE streams.
How do you join them?

APPROACH: Stateful session window join

1. When a CLICK event arrives:
   → Store in Beam state keyed by (user_id, campaign_id)
   → State TTL: 30 days (attribution window)

2. When a PURCHASE event arrives:
   → Look up state for (user_id): find most recent click within 30 days
   → If found: emit an ATTRIBUTION event:
     {user_id, campaign_id from click, purchase_value, click_time, purchase_time}
   → If not found: organic purchase (no attribution)

3. The attribution event flows to the metrics aggregation:
   → Increment conversions count for that campaign
   → Add purchase_value to attributed revenue

ALTERNATIVE (simpler, less accurate):
  Don't join in stream.
  Instead: write clicks and purchases separately to BigQuery.
  A BigQuery scheduled query runs every 5 minutes:
  "Find purchases in last 5 minutes, join to clicks within 30 days, compute ROAS"
  Less elegant but much simpler to operate.
  
  For this design: I'd use the BigQuery join approach for ROAS
  (simpler, easier to debug) and reserve the stateful Beam join
  for near-real-time per-user personalization use cases.
```

---

## COMPONENT 4: LATE DATA HANDLING — THE CRITICAL SECTION

This is the section the interviewer MOST wants to hear about for ad data.

### Why Late Data is Especially Severe in AdTech

```
MOBILE APP BATCHING (most common cause):
  User clicks ad at 2:15 PM while offline (subway, airplane mode)
  App stores event locally
  User connects WiFi at 6:30 PM → app sends batch → event arrives 4 hours late
  
  Impact: The 2:00-3:00 PM window closed at 3 PM.
  Without late data handling: this click is lost → CTR understated → wrong ROAS
  
GOOGLE/META COST ADJUSTMENT (most severe cause):
  You click an ad at 2:15 PM.
  The ad platform initially reports cost = $0.50.
  Their fraud detection runs overnight.
  They determine 30% of clicks in that campaign were invalid.
  They REFUND the cost.
  Updated cost at 11:59 PM: $0.35.
  Updated cost next morning: $0.35.
  
  For up to 48 hours after the click, the cost data can change.
  
  Impact: Your real-time ROAS is based on preliminary cost.
  The real cost (and real ROAS) is only known 48 hours later.
  This is why streaming ROAS is always "preliminary."

DOWNSTREAM SYSTEM FAILURES:
  Your ingestion API was down for 2 hours (9-11 AM).
  At 11 AM it recovers.
  2 hours of events arrive simultaneously.
  All with event_time between 9-11 AM, but processing_time = 11 AM.
  
  These look like 2 hours late (relative to processing time).
  But they're not "late" — they were just buffered during the outage.
```

### The Tiered Late Data Strategy

```
TIER 1: 0-5 MINUTES LATE (95% of events)
  ─────────────────────────────────────────
  Handled by: Watermark + normal window
  
  Watermark = max(event_time_seen) - 5 minutes
  When watermark passes 3:00 PM → 2-3 PM window fires
  
  Events up to 5 minutes late: arrive before watermark closes → counted normally
  No special handling needed.
  These are the "normal" late events from network delay.

TIER 2: 5 MINUTES - 1 HOUR LATE (4% of events)
  ─────────────────────────────────────────────────
  Handled by: allowed_lateness = 60 minutes
  
  After window closes at watermark, it remains open for 60 more minutes.
  If a late event arrives with event_time in the closed window:
  → Window re-fires with updated count (ACCUMULATING mode)
  → BigQuery row is MERGED (updated, not duplicated)
  
  Dashboard shows: preliminary → revised → revised again
  Label these as "UPDATING" until 60 minutes after window close.

TIER 3: 1 HOUR - 48 HOURS LATE (1% of events, but includes cost adjustments)
  ───────────────────────────────────────────────────────────────────────────────
  Handled by: Batch reprocessing path (the "Batch" in Lambda Architecture)
  
  Events routed to: side output → GCS → batch job picks up
  Cost adjustments: Google/Meta cost API re-queried every 6 hours for last 3 days
  
  Nightly batch job (Cloud Composer, 2 AM):
  - Reads last 3 days of raw events from GCS
  - Reads updated cost data from Google/Meta APIs
  - Recomputes ALL metrics for last 3 days
  - Overwrites BigQuery partitions via INSERT OVERWRITE
  
  This gives you the AUTHORITATIVE numbers every morning.
  Finance team uses this (not the streaming table) for billing.

TIER 4: > 48 HOURS LATE (0.1% of events)
  ──────────────────────────────────────────
  Handled by: Dead letter queue + manual review
  
  Route to: Pub/Sub dead letter topic → GCS bucket → alert to engineering
  These are genuinely anomalous — investigate WHY they're so late.
  Could indicate: offline device reconnecting after weeks, data pipeline bug,
  replay of old events by mistake.
  
  Don't automatically process these — they can corrupt metrics for historical periods.
  Require manual approval before processing.
```

### Lambda Architecture — The Final Design

```
COMPLETE DATA FLOW WITH LAMBDA:

                    ┌─────────────────────────────────────────────────────────────┐
                    │                    LAMBDA ARCHITECTURE                       │
                    └─────────────────────────────────────────────────────────────┘

Ad Events (100M/day)
        │
        ▼
Pub/Sub "ad-events"
        │
        ├─────────────────────────────────────────────────────────────────────────┐
        │                                                                         │
        ▼ STREAMING PATH                                        BATCH PATH ▼     │
                                                                                  │
Dataflow Streaming                                         Cloud Composer (Airflow)
        │                                                  Runs: 2 AM daily       │
        │  5-min Fixed Windows                                     │              │
        │  allowed_lateness = 1hr                                  │              │
        │  Dedup on event_id                                       │              │
        │  Enrich with campaign dims                               │              │
        ▼                                                          │              │
BigQuery: streaming.ad_metrics_5min                                │              │
(PRELIMINARY — updates every 5 min)                               │              │
        │                                                          │              │
        └─────────────────────────── Also writes ───────────────► │              │
                                                                   │              │
                                    GCS Raw Archive                │              │
                                    gs://costco-data/raw/          │              │
                                    ad-events/{date}/*.parquet ────┘              │
                                            │                                     │
                                            ▼                                     │
                                   Dataflow Batch Job                             │
                                   - Reads last 3 days                            │
                                   - Reads updated API costs                      │
                                   - Recomputes all metrics                       │
                                   - Handles ALL late events                      │
                                            │                                     │
                                            ▼                                     │
                                   BigQuery: batch.ad_metrics_daily               │
                                   (AUTHORITATIVE — as of 2 AM)                   │
                                            │                                     │
                                            │─────────────────────────────────────┘
                                            │
                                            ▼
                                    Looker Dashboard
                               ┌────────────────────────────────┐
                               │  "Real-time" panel:             │
                               │   → reads streaming table       │
                               │   → labeled "Preliminary"       │
                               │                                 │
                               │  "Daily metrics" panel:         │
                               │   → reads batch table           │
                               │   → labeled "Final"             │
                               └────────────────────────────────┘
```

---

## COMPONENT 5: DATA STORAGE — BIGQUERY DESIGN

### Table Design

```sql
-- STREAMING TABLE: Updated every 5 minutes (preliminary)
CREATE TABLE streaming.ad_metrics_5min (
    window_start        TIMESTAMP NOT NULL,
    window_end          TIMESTAMP NOT NULL,
    campaign_id         STRING    NOT NULL,
    channel             STRING    NOT NULL,
    -- Metrics
    impressions         INT64     NOT NULL DEFAULT 0,
    clicks              INT64     NOT NULL DEFAULT 0,
    unique_users        INT64     NOT NULL DEFAULT 0,
    spend_usd           FLOAT64   NOT NULL DEFAULT 0,
    conversions         INT64     NOT NULL DEFAULT 0,
    revenue_usd         FLOAT64   NOT NULL DEFAULT 0,
    -- Derived (computed at write time for dashboard speed)
    ctr_pct             FLOAT64,  -- clicks / impressions * 100
    cvr_pct             FLOAT64,  -- conversions / clicks * 100
    roas                FLOAT64,  -- revenue / spend
    cpc_usd             FLOAT64,  -- spend / clicks
    -- Metadata
    is_preliminary      BOOL      DEFAULT TRUE,  -- TRUE until batch confirms
    processed_at        TIMESTAMP NOT NULL
)
PARTITION BY DATE(window_start)
CLUSTER BY campaign_id, channel;

-- BATCH TABLE: Authoritative daily metrics
CREATE TABLE batch.ad_metrics_daily (
    report_date         DATE      NOT NULL,
    campaign_id         STRING    NOT NULL,
    channel             STRING    NOT NULL,
    -- Same metrics as streaming but FINAL
    impressions         INT64     NOT NULL DEFAULT 0,
    clicks              INT64     NOT NULL DEFAULT 0,
    unique_users        INT64     NOT NULL DEFAULT 0,
    spend_usd           FLOAT64   NOT NULL DEFAULT 0,  -- FINAL cost (post-adjustment)
    conversions         INT64     NOT NULL DEFAULT 0,
    revenue_usd         FLOAT64   NOT NULL DEFAULT 0,
    ctr_pct             FLOAT64,
    cvr_pct             FLOAT64,
    roas                FLOAT64,
    cpc_usd             FLOAT64,
    -- Attribution
    new_member_conversions INT64  DEFAULT 0,  -- first-time buyers
    return_member_conversions INT64 DEFAULT 0,
    -- Metadata
    batch_run_at        TIMESTAMP NOT NULL,
    data_coverage_hours FLOAT64,  -- how many hours of data were included
    includes_late_data  BOOL      DEFAULT TRUE
)
PARTITION BY report_date
CLUSTER BY campaign_id, channel;

-- RAW EVENTS TABLE (for ad hoc analysis and debugging)
CREATE TABLE raw.ad_events (
    event_id            STRING    NOT NULL,
    event_type          STRING    NOT NULL,
    event_timestamp     TIMESTAMP NOT NULL,   -- event time
    received_at         TIMESTAMP NOT NULL,   -- processing time
    campaign_id         STRING,
    ad_id               STRING,
    channel             STRING,
    device_type         STRING,
    member_id_hash      STRING,   -- SHA256 hashed for GDPR
    session_id          STRING,
    cost_usd            FLOAT64,
    raw_payload         JSON,     -- full original event for debugging
    _loaded_at          TIMESTAMP NOT NULL
)
PARTITION BY DATE(event_timestamp)
CLUSTER BY campaign_id, event_type
OPTIONS (partition_expiration_days = 730);  -- 2 year retention
```

### Cost Optimization for BigQuery

```
PARTITION STRATEGY:
  streaming.ad_metrics_5min: partition by DATE(window_start)
    → Queries for "today's metrics" scan only today's partition
    → 99% of dashboard queries hit only 1-2 partitions
  
  raw.ad_events: partition by DATE(event_timestamp)
    → Raw event queries almost always filter by date
    → 2-year retention = 730 partitions total

CLUSTERING STRATEGY:
  CLUSTER BY (campaign_id, channel)
  → Most queries filter by campaign_id + channel
  → BigQuery prunes blocks that don't match these filters
  → Combined with partition: 99.9%+ data pruning for typical queries

REQUIRE PARTITION FILTER:
  ALTER TABLE raw.ad_events SET OPTIONS (require_partition_filter = TRUE);
  → Prevents analysts from accidentally scanning 2 years of raw events
  → "You must provide a date range" — forces cost-conscious querying

MATERIALIZED VIEW for dashboard:
  The Looker dashboard queries the same "last 7 days by campaign" every 5 minutes.
  Create a materialized view that pre-computes this:
  
  CREATE MATERIALIZED VIEW streaming.mv_campaign_last_7d AS
  SELECT
      DATE(window_start) AS report_date,
      campaign_id, channel,
      SUM(impressions) AS impressions,
      SUM(clicks) AS clicks,
      SUM(spend_usd) AS spend_usd,
      SAFE_DIVIDE(SUM(revenue_usd), SUM(spend_usd)) AS roas
  FROM streaming.ad_metrics_5min
  WHERE window_start >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  GROUP BY report_date, campaign_id, channel;
  → Dashboard queries this MV (tiny, fast) not the raw 5-minute table
```

---

## COMPONENT 6: METRICS COMPUTATION — KEY METRICS AND SQL

```sql
-- REAL-TIME ROAS DASHBOARD QUERY
-- (runs every 5 minutes against the streaming table)

SELECT
    campaign_id,
    channel,
    SUM(impressions)                                    AS total_impressions,
    SUM(clicks)                                         AS total_clicks,
    SUM(spend_usd)                                      AS total_spend,
    SUM(conversions)                                    AS total_conversions,
    SUM(revenue_usd)                                    AS total_revenue,
    ROUND(100.0 * SAFE_DIVIDE(SUM(clicks), SUM(impressions)), 4) AS ctr_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(conversions), SUM(clicks)), 4) AS cvr_pct,
    ROUND(SAFE_DIVIDE(SUM(revenue_usd), SUM(spend_usd)), 4)      AS roas,
    ROUND(SAFE_DIVIDE(SUM(spend_usd), SUM(clicks)), 4)            AS cpc_usd,
    ROUND(SAFE_DIVIDE(SUM(spend_usd), SUM(conversions)), 2)       AS cpa_usd
FROM streaming.ad_metrics_5min
WHERE window_start >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
GROUP BY campaign_id, channel
ORDER BY total_spend DESC;

-- ALERTING QUERY: ROAS dropped below 1.5 in last 5 minutes?
SELECT campaign_id, channel, roas, spend_usd
FROM (
    SELECT
        campaign_id, channel,
        SAFE_DIVIDE(SUM(revenue_usd), SUM(spend_usd)) AS roas,
        SUM(spend_usd) AS spend_usd
    FROM streaming.ad_metrics_5min
    WHERE window_start >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE)
    GROUP BY campaign_id, channel
)
WHERE roas < 1.5
  AND spend_usd > 100  -- only alert if meaningful spend
ORDER BY roas ASC;
```

---

## COMPONENT 7: ALERTING SYSTEM

```
ALERTING ARCHITECTURE:

Dataflow pipeline
    ├── After computing CTR/ROAS per window
    ├── If ROAS < 1.5 AND spend > $100: emit alert event
    └── Alert events → Pub/Sub "alert-events"
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       Cloud Function    Cloud Function   Cloud Function
       → Slack alert     → PagerDuty     → Pause campaign
         to marketing      (if ROAS < 1.0  via Google Ads API
         channel           for 2+ windows)

ALERT DEDUPLICATION:
  Don't alert 20 times in a row for same campaign.
  Cloud Function checks: "did I alert for this campaign in last 30 min?"
  Store last-alert-time in Firestore (fast key-value lookup):
  
  key: "alert:{campaign_id}:{metric}"
  value: last_alert_timestamp
  TTL: 30 minutes
  
  If last_alert_timestamp > 30 min ago: send alert
  Else: suppress (campaign still recovering, avoid alert fatigue)

ALERT TYPES:
  Level 1 (WARNING):   ROAS < 1.5 for last 5 minutes  → Slack DM to campaign manager
  Level 2 (CRITICAL):  ROAS < 1.0 for last 15 minutes → Pause campaign automatically
  Level 3 (EMERGENCY): Spend > budget by 20%           → Page on-call engineer
```

---

## COMPONENT 8: HANDLING MULTIPLE DEVICES — IDENTITY RESOLUTION

```
THE PROBLEM:
  Same user clicks an ad on their phone (anonymous) at 2 PM.
  Same user purchases on their laptop (logged in) at 7 PM.
  
  Mobile event: member_id = NULL (not logged in), device_id = "phone_abc"
  Web event:    member_id = "M_001234", device_id = "laptop_xyz"
  
  Without identity resolution: these look like two different users.
  The click gets no conversion credit → ROAS understated.
  
THE SOLUTION: Identity Graph

IDENTITY GRAPH TABLE:
  Maps every anonymous_id/device_id to a canonical member_id.
  
  anonymous_id    │ member_id_hash │ linked_at
  ────────────────┼────────────────┼──────────────────
  anon_phone_abc  │ M_001234       │ 2024-01-15 19:05  ← linked when user logged in on phone
  anon_laptop_xyz │ M_001234       │ 2024-01-10 09:00
  anon_tablet_def │ M_001234       │ 2024-01-12 14:30

BUILDING THE GRAPH:
  When a user LOGS IN on any device:
  → Their browser/app now has both anonymous_id AND member_id
  → Fire an "identity link" event: {anonymous_id: X, member_id: Y, linked_at: T}
  → This updates the identity graph table
  
  "Link first touch to member" job (runs hourly):
  For any click with member_id = NULL:
  → Look up the anonymous_id in the identity graph
  → If found: update the click's member_id_hash to the canonical member_id
  → Now the phone click can be matched to the laptop purchase

ATTRIBUTION WITH IDENTITY RESOLUTION:
  Click (member_id=NULL, anon_id=phone_abc) at 2 PM
  → Identity graph: phone_abc → M_001234
  → Resolved: click attributed to member M_001234
  
  Purchase (member_id=M_001234) at 7 PM
  → Find last click for M_001234 within 30 days
  → Match found: 2 PM click → attribution!
  → ROAS gets credit for this conversion ✓
```

---

## COMPONENT 9: DATA GOVERNANCE AND COMPLIANCE

```
GDPR REQUIREMENTS:

1. PII HANDLING:
   Raw member_id is NEVER stored in plaintext in the pipeline.
   At SDK level: member_id is SHA256 hashed before being sent.
   Storage: only member_id_hash stored in events tables.
   
   PII (name, email, phone) stored ONLY in dim_members table.
   Access to dim_members: restricted to authorized service accounts.
   Column-level masking: analysts see email as ***@domain.com.

2. RIGHT TO ERASURE (GDPR Article 17):
   Member requests deletion → all their data must be removed within 30 days.
   
   Implementation:
   - Use member_id_hash (not raw member_id) as the key in all events tables
   - When deletion requested:
     a. Add member_id_hash to "erasure_list" table
     b. Daily job: DELETE FROM all event tables WHERE member_id_hash IN erasure_list
     c. Archive deletion to "erasure_audit_log" (prove we deleted it)
   - For BigQuery: use DML DELETE for event tables with date partition filter
   - After 30 days: verify deletion complete, send confirmation to member

3. DATA MINIMIZATION:
   Don't store what you don't need.
   raw.ad_events table: expires partitions after 2 years (BigQuery partition expiration)
   streaming tables: keep 90 days, then data moves to batch.daily tables
   
4. AUDIT LOGGING:
   Cloud Audit Logs enabled for BigQuery DATA_READ and DATA_WRITE
   Who accessed PII tables, when, what query they ran → logged automatically
   Retention: 1 year for audit logs
```

---

## COMPONENT 10: MONITORING AND OBSERVABILITY

```
WHAT YOU MONITOR:

PIPELINE HEALTH:
  ├── Pub/Sub backlog size (should not grow unboundedly)
  │    Alert: backlog > 1M messages AND growing → Dataflow is falling behind
  ├── Dataflow system lag (should be < 2 minutes for streaming pipeline)
  │    Alert: system_lag > 5 minutes → watermark is stalling
  ├── Dataflow worker errors per second
  │    Alert: > 100 errors/sec → something is fundamentally broken
  └── Dead letter message count
       Alert: any dead letter → investigate immediately

DATA QUALITY:
  ├── Events per second arriving (baseline: 1,000-10,000 events/sec)
  │    Alert: < 100 events/sec → source is down? SDK bug?
  │    Alert: > 50,000 events/sec → bot traffic? DDoS?
  ├── Null rate on critical fields (campaign_id, event_timestamp)
  │    Alert: > 1% null on event_id → deduplication is broken
  └── Schema validation failure rate
       Alert: > 0.1% schema failures → SDK deployed breaking change

BUSINESS METRICS:
  ├── ROAS per campaign (hourly)
  │    Alert: ROAS < 1.5 → notify campaign manager
  ├── Spend vs budget pacing (hourly)
  │    Alert: > 95% budget used by noon → campaign will overspend
  └── Event volume by device type (should be stable proportions)
       Alert: mobile events drop 50% → iOS SDK update broke something?

MONITORING STACK:
  Cloud Monitoring: infrastructure metrics (Pub/Sub, Dataflow, BigQuery)
  Custom dashboards: Looker (business metrics, data quality)
  Alerting: Cloud Monitoring Alerts → PagerDuty → on-call engineer
```

---

# STEP 5: EDGE CASES

```
EDGE CASE 1: FLASH SALE — SUDDEN 10X TRAFFIC SPIKE
  Costco launches a surprise sale → 10K events/sec instantly
  
  Without design: Pub/Sub backlog grows, Dataflow falls behind, dashboard goes stale
  
  With design:
  - Pub/Sub: auto-scales to millions/sec, buffers the spike (7-day retention)
  - Dataflow: auto-scales workers within 2-3 minutes (THROUGHPUT_BASED autoscaling)
  - Dashboard: might lag for 2-3 minutes during scale-up, then recovers
  - GCS archive: unaffected (just writing files)
  - BigQuery: handles concurrent writes, no impact
  
  Design decision: set MAX_NUM_WORKERS = 50 (enough for 10x spike)
  Cost: peak workers are only running during the spike (Dataflow per-second billing)

EDGE CASE 2: PIPELINE FAILURE — DATAFLOW JOB CRASHES
  Dataflow crashes mid-day. 2 hours of data is unprocessed.
  
  Recovery:
  - Pub/Sub retains all messages for 7 days → no data loss
  - Dataflow auto-restarts from last checkpoint (saved to GCS every 30 seconds)
  - On restart: resumes processing from checkpoint offset
  - 2 hours of backlog: caught up at 2-5x normal speed within 20-40 minutes
  - Deduplication: MERGE on event_id prevents double-counting reprocessed events
  
  Dashboard impact: metrics are stale for 20-40 minutes, then catch up

EDGE CASE 3: BOT TRAFFIC / CLICK FRAUD
  Sudden 100K clicks from 3 IP addresses in 5 minutes on campaign X.
  
  Real-time detection:
  - Dataflow: count clicks per (ip_address, campaign_id) per 1-minute window
  - If > 1,000 clicks from same IP in 1 minute → emit fraud alert
  - Flag those events as "suspected_fraud = true"
  
  Downstream handling:
  - Metrics: exclude suspected_fraud events from ROAS/CTR calculation
  - Alert: notify campaign manager immediately
  - Archive: keep flagged events for 90 days (needed for ad network dispute)
  
  Long-term:
  - Maintain a fraud IP blocklist in Cloud Firestore
  - Check incoming events against blocklist at ingestion layer
  - Block at ingestion if IP is known bad (before even entering pipeline)

EDGE CASE 4: SCHEMA CHANGE IN SDK
  iOS SDK v3.5 renames "click_timestamp" to "event_timestamp".
  Old devices still on v3.4 send "click_timestamp".
  New devices on v3.5 send "event_timestamp".
  Both versions active simultaneously for weeks.
  
  Handling:
  - Ingest raw payload as JSON (no schema enforcement at ingestion)
  - Parsing step handles both:
    event_time = event.get("event_timestamp") or event.get("click_timestamp")
  - Schema version field (schema_version: "2.1") helps route to correct parser
  - Alert: if schema validation failure rate spikes → SDK regression deployed
  
  Design principle: be liberal in what you accept, strict in what you emit
  (accept any valid JSON, emit only validated structured events to downstream)

EDGE CASE 5: GDPR DELETION REQUEST AT SCALE
  1,000 members request data deletion on the same day.
  
  Naïve: DELETE from each partition individually → 1,000 × 730 partitions = 730,000 queries
  
  Better approach:
  1. Add all member_id_hashes to erasure_list table
  2. Nightly batch job:
     DELETE FROM raw.ad_events
     WHERE member_id_hash IN (SELECT member_id_hash FROM erasure_list WHERE status = 'pending')
     AND event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)  -- partition filter!
  3. Partition by partition for last 2 years (2 years × 365 = 730 queries, but batched)
  4. Update erasure_list status to 'completed'
  5. Send confirmation to compliance team
  
  Design principle: use partition filter on DELETE to avoid full table scans.
  BigQuery DML DELETE on a single partition is efficient.
```

---

# STEP 6: TRADE-OFFS AND ALTERNATIVES

```
TRADE-OFF 1: LAMBDA vs KAPPA ARCHITECTURE

Lambda (chosen):
  Streaming for real-time + Batch for authoritative
  Pros: Clear separation, batch is easy to reason about
  Cons: Two codebases to maintain, batch and stream can diverge

Kappa:
  Single streaming pipeline that can also replay history
  Pros: One codebase, simpler in theory
  Cons: Requires Kafka (not Pub/Sub) with 48-hour retention minimum,
        replaying 48 hours of 100M events/day = 200M event replay on demand,
        more complex state management
  
  Decision: Lambda for this design.
  Team has SQL expertise (batch is just DBT/SQL).
  Two codebases is manageable with proper DBT models.

TRADE-OFF 2: STREAMING JOIN vs BIGQUERY JOIN FOR ROAS

Streaming join (in Dataflow):
  Pros: Lower latency (ROAS updated in seconds)
  Cons: Complex stateful code, hard to debug, state explosion if mismanaged

BigQuery join (scheduled query every 5 min):
  Pros: Simple SQL, easy to understand and debug
  Cons: Higher latency (5 minutes, not seconds)
  
  Decision: BigQuery join.
  5-minute ROAS latency is acceptable (requirement was < 5 minutes).
  Simpler code = fewer bugs = easier to maintain.
  "Make the complex part simple; only make the simple part complex when needed."

TRADE-OFF 3: REAL-TIME DEDUP vs SINK-LEVEL DEDUP

Real-time dedup in Dataflow (Stateful DoFn):
  Pros: Prevents duplicates from ever reaching BigQuery
  Cons: State per event_id, high memory, TTL management complex

Sink-level dedup (MERGE on event_id in BigQuery):
  Pros: Simple, uses BigQuery's strength, no Dataflow state overhead
  Cons: Duplicates enter BigQuery temporarily, MERGE adds latency
  
  Decision: Sink-level for simplicity.
  BigQuery MERGE is efficient (partition-level operation).
  Temporary duplicates are acceptable (they're MERGED away within 30 seconds).

WHAT I WOULD DO DIFFERENTLY WITH MORE TIME:
  1. Add ML-based anomaly detection for ROAS drops
     (Z-score anomaly on rolling 7-day baseline)
  2. Build a data quality SLA dashboard
     (% events processed within 5 minutes, % of windows complete)
  3. Implement event replay API
     (ability to replay any time range through the pipeline manually)
  4. Add Dataplex for data lineage and catalog
     (track which Dataflow job wrote which BigQuery partition)
```

---

# FINAL SUMMARY — WHAT TO SAY IN THE INTERVIEW

## The 2-Minute Version

*"At a high level, I'd design this as a Lambda Architecture on GCP with three main components:*

*First, event collection — mobile apps and web SDKs send events to a Cloud Run ingestion API, which validates and publishes to Cloud Pub/Sub. Pub/Sub gives us durability (7-day retention), fan-out to multiple consumers, and automatic scaling to handle traffic spikes.*

*Second, the streaming path — a Dataflow job reads from Pub/Sub, deduplicates on event_id, windows events into 5-minute buckets using event time (not processing time), and computes CTR, ROAS, and conversion metrics. Results go into BigQuery streaming tables that Looker queries every 5 minutes. This gives sub-5-minute latency for the marketing dashboard.*

*Third, the batch path — all raw events are also archived to GCS as Parquet files. A nightly Cloud Composer job reprocesses the last 3 days, incorporating late-arriving mobile events and final cost data from Google and Meta APIs (which adjusts for up to 48 hours). This produces the authoritative numbers that finance uses.*

*For late data specifically: events up to 1 hour late are handled by Dataflow's allowed_lateness. Events up to 48 hours late are handled by the batch path. Events beyond 48 hours go to a dead letter queue for manual review.*

*For identity resolution across devices: we maintain an identity graph that links anonymous device IDs to member IDs when users log in, enabling cross-device attribution.*

*The whole thing runs on Cloud Pub/Sub, Dataflow, BigQuery, GCS, Cloud Composer, and Looker — a fully managed GCP stack with no infrastructure to manage."*

---

## One-Line Answers for Quick Follow-Ups

```
"Why Pub/Sub?" → Durable 7-day buffer, fan-out, fully managed, handles spikes
"Why Dataflow?" → Managed, event-time windowing, auto-scales, native GCP
"Why not Kafka?" → Managed >> self-managed at this scale; Pub/Sub is equivalent for our needs
"Why Lambda not Kappa?" → SQL batch is simpler to maintain; 5-min latency is sufficient
"How do you handle 10x spike?" → Pub/Sub buffers, Dataflow auto-scales in 2-3 min
"How do you prevent duplicate metrics?" → event_id UUID + MERGE at BigQuery sink
"What if Dataflow crashes?" → Checkpoint resumes from last GCS checkpoint; Pub/Sub holds messages
"How do you handle GDPR?" → SHA256 hash at SDK; DELETE by partition for erasure
"What about cost adjustments from Google?" → Batch path re-fetches API cost data for last 3 days nightly
"How do you know ROAS is accurate?" → Streaming = preliminary (labeled); batch = final (authoritative)
```
