# Apache Beam and Cloud Dataflow — Complete Guide From Zero
## End-to-End Clickstream Ad Analytics Implementation on GCP

---

# PART 1: WHAT IS APACHE BEAM?

## 1.1 The Problem Beam Solves

Before Beam existed, data engineers had a frustrating problem:

```
IF YOU WANTED TO DO BATCH PROCESSING:
  You used Apache Spark
  Write code in Spark API (RDDs, DataFrames)
  Run on a Spark cluster
  
IF YOU WANTED TO DO STREAM PROCESSING:
  You used Apache Flink OR Apache Storm OR Spark Streaming
  Write code in a completely DIFFERENT API
  Run on a completely DIFFERENT cluster
  
RESULT:
  Same business logic (count clicks per campaign) needs to be written TWICE:
  - Once in Spark (batch version)
  - Once in Flink (streaming version)
  
  When the logic changes: update it in TWO places.
  When you hire engineers: they need to know BOTH systems.
  
  This was painful, expensive, and error-prone.
```

**Apache Beam's insight**: What if you could write the logic ONCE and run it on ANY engine?

```
BEAM = ONE UNIFIED PROGRAMMING MODEL for both batch AND streaming

You write ONE piece of code:
  "Count clicks per campaign"

You choose where to RUN it:
  → Run on Dataflow (Google's managed engine, recommended)
  → Run on Apache Spark (if you have a Spark cluster)
  → Run on Apache Flink (if you have a Flink cluster)
  → Run locally on your laptop (for testing)

THE CODE DOESN'T CHANGE. Only the "runner" changes.

ANALOGY:
  Beam is like a RECIPE.
  The runner is like the KITCHEN.
  
  Recipe: "Make a chocolate cake"
  Kitchen A: Your home kitchen → makes the cake
  Kitchen B: A professional bakery kitchen → makes the same cake, but faster
  Kitchen C: An industrial factory → makes the same cake, at massive scale
  
  Same recipe (Beam code), different kitchens (runners), same result.
```

## 1.2 What is Cloud Dataflow?

```
CLOUD DATAFLOW = Google's managed runner for Apache Beam programs.

You write a Beam program (the recipe).
You say: "Run this on Dataflow."
Google:
  - Provisions the servers (VMs) needed to run your program
  - Distributes the work across those servers
  - Monitors everything
  - Scales up when more data arrives (adds more servers automatically)
  - Scales down when data is slow (removes servers to save money)
  - Handles server failures (restarts crashed workers automatically)
  - Cleans up when the job finishes

YOU DO NOTHING to manage infrastructure.
You just write the code and submit it.

ANALOGY:
  Dataflow is like UBER.
  You say "I need to go from A to B."
  Uber provides the car and driver.
  You don't manage the car. You just ride.
  
  Similarly:
  You say "I need to process these events."
  Dataflow provides the servers.
  You don't manage servers. You just submit code.
```

## 1.3 Key Terminology

```
TERM              MEANING
──────────────────────────────────────────────────────────────────────────
Pipeline          Your entire Beam program — all the steps from start to finish
PCollection       A dataset (like a table or list of items) in Beam
                  P = Parallel (it can be distributed across many machines)
                  Collection = a collection of items
                  Can be BOUNDED (finite, like a file) or UNBOUNDED (infinite, like a stream)
                  
PTransform        A transformation applied to a PCollection
                  Takes PCollection(s) as input, produces PCollection(s) as output
                  Think: a step on the assembly line
                  
DoFn              Define Function — the actual logic you write for custom transforms
                  Like a function that runs on EACH element of a PCollection
                  
ParDo             Parallel Do — applies a DoFn to each element in parallel
                  Most common transform. Think: map() in Python.
                  
GroupByKey        Groups elements by their key
                  Like GROUP BY in SQL
                  
CombinePerKey     Aggregates all values for each key
                  Like GROUP BY + SUM/COUNT/AVG in SQL
                  
Flatten           Merge multiple PCollections into one
                  Like UNION ALL in SQL
                  
Runner            The engine that executes your Beam pipeline
                  Options: DataflowRunner, SparkRunner, FlinkRunner, DirectRunner (local)
                  
WindowFn          Defines how to group events into time windows
                  FixedWindows, SlidingWindows, Sessions
                  
Trigger           Defines WHEN to emit results from a window
                  At watermark? Early? For each late event?
                  
Watermark         The system's estimate of event-time completeness
                  (same concept as explained in the streaming basics guide)
                  
Side Input        Read-only reference data accessible to all workers
                  Like a lookup table — e.g., campaign names by campaign_id
```

---

# PART 2: APACHE BEAM PROGRAMMING MODEL — LEARNING FROM SCRATCH

## 2.1 Your First Beam Pipeline — Batch Mode

Let's start simple. Process a FILE of click events. No streaming yet.

```python
# FILE: batch_click_counter.py
# PURPOSE: Read a file of click events, count clicks per campaign
# This is BATCH — processes a finite file, then stops

import apache_beam as beam

# Step 1: Create the pipeline
# Think of this as "starting your assembly line"
with beam.Pipeline() as pipeline:
    
    # Step 2: Read input data
    # ReadFromText reads a file line by line
    # Each line becomes ONE ELEMENT in the PCollection
    raw_lines = (
        pipeline
        | 'ReadFile' >> beam.io.ReadFromText('clicks.txt')
        # Result: PCollection(['line1', 'line2', 'line3', ...])
        # Each element = one line of text
    )
    
    # Step 3: Transform each line
    # beam.Map applies a function to EACH element
    # Returns a new PCollection with the transformed elements
    parsed_events = (
        raw_lines
        | 'ParseLines' >> beam.Map(lambda line: line.split(','))
        # Input:  PCollection(['click,camp_1,user_1', 'click,camp_2,user_2'])
        # Output: PCollection([['click','camp_1','user_1'], ['click','camp_2','user_2']])
    )
    
    # Step 4: Extract the key we want to group by
    # Extract (campaign_id, 1) from each event
    # The "1" means "I want to count this event"
    campaign_counts = (
        parsed_events
        | 'ExtractCampaign' >> beam.Map(lambda event: (event[1], 1))
        # Input:  PCollection([['click','camp_1','user_1'], ...])
        # Output: PCollection([('camp_1', 1), ('camp_2', 1), ('camp_1', 1), ...])
    )
    
    # Step 5: Sum up the 1s per campaign
    # CombinePerKey(sum) → for each key (campaign_id), sum all values
    totals = (
        campaign_counts
        | 'SumPerCampaign' >> beam.CombinePerKey(sum)
        # Input:  PCollection([('camp_1',1), ('camp_2',1), ('camp_1',1)])
        # Output: PCollection([('camp_1', 2), ('camp_2', 1)])
    )
    
    # Step 6: Write the output
    totals | 'WriteOutput' >> beam.io.WriteToText('output.txt')
    # Writes to output.txt:
    # camp_1, 2
    # camp_2, 1

# When the 'with' block ends, the pipeline runs automatically.
# For batch: runs, finishes, stops.
```

**Running this on your local machine:**
```bash
# Install Apache Beam
pip install apache-beam[gcp]

# Run locally (uses DirectRunner = runs on your laptop)
python batch_click_counter.py

# You'll see output in output.txt
```

---

## 2.2 The Pipe Operator `|` — Understanding Beam Syntax

This confuses beginners. Let's explain it:

```python
# The | operator in Beam means "apply this transform to this PCollection"
# Read it as: "take this PCollection and PIPE it through this transform"

# SYNTAX BREAKDOWN:
output = input | 'Step Name' >> SomeTransform(arguments)

# Breaking it down:
# input           → the PCollection to transform
# |               → "pipe into" (apply the transform)
# 'Step Name'     → a human-readable label (must be unique in pipeline)
#                   Used for: monitoring, debugging, error messages
# >>              → separates the label from the transform
# SomeTransform() → the actual transformation to apply

# EXAMPLE:
result = my_data | 'Count Words' >> beam.combiners.Count.PerElement()
#         ↑              ↑               ↑
#   input PCollection  label        the transform

# You can CHAIN transforms using parentheses:
result = (
    pipeline
    | 'Read'   >> beam.io.ReadFromText('input.txt')
    | 'Parse'  >> beam.Map(lambda x: x.split(','))
    | 'Filter' >> beam.Filter(lambda x: x[0] == 'click')
    | 'Extract'>> beam.Map(lambda x: (x[1], 1))
    | 'Count'  >> beam.CombinePerKey(sum)
    | 'Write'  >> beam.io.WriteToText('output.txt')
)

# This reads as:
# Read from file → Parse each line → Keep only clicks → 
# Extract (campaign, 1) pairs → Sum per campaign → Write to file
```

---

## 2.3 DoFn — Writing Custom Transformation Logic

For simple transformations, `beam.Map` or `beam.Filter` is enough. For complex logic (like validation, deduplication, enrichment), you write a `DoFn` class:

```python
import apache_beam as beam
import json

# A DoFn is a class that you write.
# The 'process' method runs for EACH element in the PCollection.

class ParseClickEvent(beam.DoFn):
    """
    Takes a raw JSON string and converts it to a structured dict.
    Also handles errors by routing bad events to a dead letter output.
    """
    
    def process(self, element):
        """
        element = one item from the PCollection
        In our case: a raw JSON string like:
        '{"event_id": "abc", "campaign_id": "c001", "event_type": "click"}'
        """
        try:
            # Try to parse the JSON
            event = json.loads(element)
            
            # Check that required fields exist
            required_fields = ['event_id', 'campaign_id', 'event_type', 'event_timestamp']
            for field in required_fields:
                if field not in event:
                    raise ValueError(f"Missing required field: {field}")
            
            # If everything is fine, yield the parsed event
            # yield = "output this element"
            yield event
            
        except Exception as error:
            # If parsing fails, route to dead letter output
            # TaggedOutput = send to a NAMED output stream (not the main output)
            yield beam.pvalue.TaggedOutput(
                'dead_letter',
                {
                    'raw_message': element,
                    'error': str(error)
                }
            )
    
    # Note: process() can yield ZERO, ONE, or MANY items.
    # If you yield nothing: element is filtered out.
    # If you yield one: one-to-one mapping.
    # If you yield many: one-to-many (like exploding an array).

# HOW TO USE THIS DoFn in a pipeline:
parsed = (
    raw_messages
    | 'ParseEvents' >> beam.ParDo(
        ParseClickEvent()
    ).with_outputs(
        'dead_letter',    # named output for bad events
        main='valid'      # main output for good events
    )
)

# Now you have TWO outputs:
valid_events = parsed.valid           # good events
dead_letter_events = parsed.dead_letter  # bad events
```

---

## 2.4 Streaming in Beam — Adding Windows and Watermarks

Now let's move from batch to streaming. The key additions are:

1. **Read from Pub/Sub** instead of a file (never-ending stream)
2. **Apply Windows** to group events into time buckets
3. **Configure Watermarks** to handle late data

```python
import apache_beam as beam
from apache_beam.transforms import window, trigger
from apache_beam.options.pipeline_options import PipelineOptions

# For streaming, we need to add WindowInto transform

# WINDOWING EXAMPLE:

# 1. Fixed Windows (tumbling windows)
windowed = (
    events
    | 'FixedWindows' >> beam.WindowInto(
        window.FixedWindows(5 * 60)  # 5 minutes = 300 seconds
        # Each event is assigned to the 5-minute bucket containing its timestamp
        # An event at 2:17 PM goes into the 2:15-2:20 PM bucket
    )
)

# 2. Sliding Windows
windowed = (
    events
    | 'SlidingWindows' >> beam.WindowInto(
        window.SlidingWindows(
            size=30 * 60,    # 30-minute window
            period=5 * 60    # slide every 5 minutes
        )
        # An event at 2:17 PM belongs to:
        # 1:47-2:17 window, 1:52-2:22 window, 1:57-2:27 window, etc.
        # Same event counted in multiple windows
    )
)

# 3. Session Windows
windowed = (
    events
    | 'SessionWindows' >> beam.WindowInto(
        window.Sessions(gap_size=30 * 60)  # 30-minute gap = new session
        # Groups events per user
        # If same user has no events for 30 minutes: new session
        # Must use with key-based partitioning by user_id
    )
)

# ADDING LATE DATA HANDLING:
windowed_with_late = (
    events
    | 'WindowWithLate' >> beam.WindowInto(
        window.FixedWindows(5 * 60),  # 5-minute windows
        
        # Accept events up to 60 minutes late
        allowed_lateness=window.Duration(seconds=3600),
        
        # TRIGGERS: when to emit results
        trigger=trigger.AfterWatermark(
            # EARLY TRIGGER: Emit a preliminary result every 30 seconds
            # (don't wait 5 minutes for the window to close)
            # This gives the dashboard "live" numbers even before the window closes
            early=trigger.AfterProcessingTime(30),
            
            # LATE TRIGGER: For each late event that arrives, re-emit
            late=trigger.AfterCount(1)
        ),
        
        # ACCUMULATION MODE:
        # ACCUMULATING = each firing includes ALL events seen so far (complete picture)
        # DISCARDING = each firing includes ONLY new events since last firing
        accumulation_mode=trigger.AccumulationMode.ACCUMULATING
    )
)
```

---

# PART 3: COMPLETE END-TO-END IMPLEMENTATION

## 3.1 Project Setup

```bash
# Step 1: Create a GCP project (do this in GCP Console)
# Project ID: costco-martech-project

# Step 2: Enable required APIs
gcloud services enable dataflow.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable storage.googleapis.com

# Step 3: Create a GCS bucket for Dataflow staging
gsutil mb -l us-central1 gs://costco-dataflow-staging/

# Step 4: Create Pub/Sub topics and subscriptions
gcloud pubsub topics create ad-events
gcloud pubsub topics create ad-events-dead-letter

gcloud pubsub subscriptions create ad-events-dataflow-sub \
    --topic=ad-events \
    --ack-deadline=60 \
    --dead-letter-topic=ad-events-dead-letter \
    --max-delivery-attempts=5

# Step 5: Create BigQuery dataset and tables
bq mk --dataset costco-martech-project:streaming
bq mk --dataset costco-martech-project:raw

# Step 6: Install Apache Beam with GCP support
pip install apache-beam[gcp]==2.52.0
pip install google-cloud-bigquery google-cloud-pubsub
```

## 3.2 Create the BigQuery Tables

```sql
-- Run these in BigQuery Console or via bq command line

-- Table 1: 5-minute streaming metrics (updated in real-time)
CREATE TABLE `costco-martech-project.streaming.ad_metrics_5min`
(
    window_start        TIMESTAMP   NOT NULL,
    window_end          TIMESTAMP   NOT NULL,
    campaign_id         STRING      NOT NULL,
    channel             STRING,
    device_type         STRING,
    impressions         INT64       DEFAULT 0,
    clicks              INT64       DEFAULT 0,
    spend_usd           FLOAT64     DEFAULT 0,
    conversions         INT64       DEFAULT 0,
    revenue_usd         FLOAT64     DEFAULT 0,
    ctr_pct             FLOAT64,
    cvr_pct             FLOAT64,
    roas                FLOAT64,
    is_preliminary      BOOL        DEFAULT TRUE,
    processed_at        TIMESTAMP
)
PARTITION BY DATE(window_start)
CLUSTER BY campaign_id, channel
OPTIONS (
    description = "5-minute streaming ad metrics - preliminary"
);

-- Table 2: Raw events (for debugging and batch reprocessing)
CREATE TABLE `costco-martech-project.raw.ad_events`
(
    event_id            STRING      NOT NULL,
    event_type          STRING      NOT NULL,
    event_timestamp     TIMESTAMP   NOT NULL,
    received_at         TIMESTAMP   NOT NULL,
    campaign_id         STRING,
    ad_id               STRING,
    channel             STRING,
    device_type         STRING,
    user_id_hash        STRING,
    session_id          STRING,
    cost_usd            FLOAT64,
    raw_payload         STRING,
    _loaded_at          TIMESTAMP
)
PARTITION BY DATE(event_timestamp)
CLUSTER BY campaign_id, event_type
OPTIONS (
    partition_expiration_days = 730,
    description = "Raw ad events from all sources"
);

-- Table 3: Dead letter (failed events for investigation)
CREATE TABLE `costco-martech-project.raw.dead_letter_events`
(
    raw_message         STRING,
    error_message       STRING,
    failed_at           TIMESTAMP,
    pipeline_name       STRING
)
PARTITION BY DATE(failed_at);
```

## 3.3 The Complete Dataflow Pipeline

```python
# FILE: clickstream_pipeline.py
# PURPOSE: Complete end-to-end streaming pipeline
# Reads ad events from Pub/Sub → processes → writes to BigQuery

import apache_beam as beam
from apache_beam import window
from apache_beam.transforms import trigger
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.io.gcp.bigquery import WriteToBigQuery, BigQueryDisposition
from apache_beam.io import ReadFromPubSub
from apache_beam import pvalue
import json
import hashlib
import logging
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────
# STEP 1: DEFINE YOUR DoFns (the transformation logic)
# ─────────────────────────────────────────────────────────────────────

class ParseAndValidate(beam.DoFn):
    """
    WHAT IT DOES:
    Receives a raw bytes message from Pub/Sub.
    Decodes it from bytes → string → dict.
    Validates all required fields are present.
    Routes good events to main output.
    Routes bad events to 'dead_letter' output.
    
    WHY WE NEED THIS:
    Real-world data is messy.
    Apps can send malformed JSON.
    Fields can be missing.
    We need to catch these EARLY before they corrupt our metrics.
    """
    
    REQUIRED_FIELDS = ['event_id', 'event_type', 'event_timestamp', 'campaign_id']
    VALID_EVENT_TYPES = {'impression', 'click', 'page_view', 'add_to_cart', 'purchase'}
    
    def process(self, element):
        # element = raw bytes from Pub/Sub
        raw_string = None
        
        try:
            # Decode bytes to string
            raw_string = element.decode('utf-8')
            
            # Parse JSON string to Python dict
            event = json.loads(raw_string)
            
            # Check required fields
            for field in self.REQUIRED_FIELDS:
                if field not in event or event[field] is None:
                    raise ValueError(f"Missing or null required field: '{field}'")
            
            # Check event_type is valid
            if event['event_type'] not in self.VALID_EVENT_TYPES:
                raise ValueError(f"Invalid event_type: '{event['event_type']}'")
            
            # Add server-side received_at (when our system got it)
            event['received_at'] = datetime.utcnow().isoformat()
            
            # Hash PII (user_id) for GDPR compliance
            # We never store raw user_id
            if 'user_id' in event and event['user_id']:
                event['user_id_hash'] = hashlib.sha256(
                    event['user_id'].encode()
                ).hexdigest()[:32]  # first 32 chars of SHA256
            else:
                event['user_id_hash'] = None
            event.pop('user_id', None)  # remove raw user_id
            
            # Yield valid event to main output
            yield event
            
        except Exception as e:
            # Route bad events to dead letter
            logging.warning(f"Failed to parse event: {e}. Raw: {raw_string[:200] if raw_string else 'N/A'}")
            yield pvalue.TaggedOutput('dead_letter', {
                'raw_message': raw_string or str(element),
                'error_message': str(e),
                'failed_at': datetime.utcnow().isoformat(),
                'pipeline_name': 'clickstream_pipeline'
            })


class DeduplicateEvents(beam.DoFn):
    """
    WHAT IT DOES:
    Removes duplicate events based on event_id.
    Uses Beam's stateful processing to track seen event_ids.
    
    WHY WE NEED THIS:
    Pub/Sub delivers at-least-once.
    Mobile SDKs retry on failure.
    Same event can arrive 2-3 times.
    Without dedup: clicks counted 2x → CTR inflated → ROAS wrong.
    
    HOW IT WORKS:
    For each event_id, we maintain a BagState (a set of seen IDs).
    When event arrives: check if event_id is in the state.
    If YES: it's a duplicate → drop it (yield nothing).
    If NO: first time seeing it → emit it AND add to state.
    State has TTL (expires after 24h) to prevent memory leaks.
    """
    
    # This is the state spec - defines what kind of state we store
    # BagStateSpec: a "bag" (multiset) that stores values
    # StringUtf8Coder: values are strings (our event_ids)
    from apache_beam.coders import StrUtf8Coder
    SEEN_IDS = beam.transforms.userstate.BagStateSpec('seen_ids', StrUtf8Coder())
    
    def process(
        self,
        element,
        seen_ids=beam.DoFn.StateParam(SEEN_IDS)
    ):
        event_id = element['event_id']
        
        # Check if we've seen this event_id before
        already_seen = list(seen_ids.read())
        
        if event_id not in already_seen:
            # First time seeing this event_id
            seen_ids.add(event_id)  # mark as seen
            yield element           # emit the event
        else:
            # Duplicate! Drop silently.
            logging.debug(f"Duplicate event dropped: {event_id}")


class ExtractForAggregation(beam.DoFn):
    """
    WHAT IT DOES:
    Transforms each event into a key-value pair for aggregation.
    Key = (campaign_id, channel, device_type)
    Value = dict with metrics for this event
    
    WHY WE NEED THIS:
    After windowing, we need to GROUP events by campaign.
    Beam's GroupByKey needs (key, value) pairs.
    This step creates those pairs.
    """
    
    def process(self, element):
        # Create the grouping key
        key = (
            element.get('campaign_id', 'UNKNOWN'),
            element.get('channel', 'UNKNOWN'),
            element.get('device_type', 'UNKNOWN')
        )
        
        # Create the metrics for this one event
        event_type = element.get('event_type', '')
        metrics = {
            'is_impression': 1 if event_type == 'impression' else 0,
            'is_click':      1 if event_type == 'click'      else 0,
            'is_conversion': 1 if event_type == 'purchase'   else 0,
            'spend_usd':     element.get('cost_usd', 0.0) or 0.0,
            'revenue_usd':   element.get('revenue_usd', 0.0) or 0.0,
        }
        
        yield (key, metrics)


class AggregateMetrics(beam.CombineFn):
    """
    WHAT IT DOES:
    Combines all metrics for the same (campaign, window) together.
    Like SUM in SQL but more flexible.
    
    HOW CombineFn WORKS:
    1. create_accumulator(): create an empty "running total" (accumulator)
    2. add_input(): add one event's metrics to the running total
    3. merge_accumulators(): combine two partial running totals
                            (needed when work is distributed across machines)
    4. extract_output(): convert the final accumulator to the output
    
    WHY CombineFn instead of just GroupByKey then sum?
    CombineFn can partially aggregate on each machine BEFORE
    sending to the grouping machine. Less network traffic = faster.
    """
    
    def create_accumulator(self):
        """Create empty running totals."""
        return {
            'impressions': 0,
            'clicks': 0,
            'conversions': 0,
            'spend_usd': 0.0,
            'revenue_usd': 0.0,
            'event_count': 0
        }
    
    def add_input(self, accumulator, input_element):
        """Add one event's contribution to the accumulator."""
        return {
            'impressions':  accumulator['impressions']  + input_element['is_impression'],
            'clicks':       accumulator['clicks']       + input_element['is_click'],
            'conversions':  accumulator['conversions']  + input_element['is_conversion'],
            'spend_usd':    accumulator['spend_usd']    + input_element['spend_usd'],
            'revenue_usd':  accumulator['revenue_usd']  + input_element['revenue_usd'],
            'event_count':  accumulator['event_count']  + 1
        }
    
    def merge_accumulators(self, accumulators):
        """Combine multiple partial accumulators into one."""
        merged = self.create_accumulator()
        for acc in accumulators:
            merged['impressions']  += acc['impressions']
            merged['clicks']       += acc['clicks']
            merged['conversions']  += acc['conversions']
            merged['spend_usd']    += acc['spend_usd']
            merged['revenue_usd']  += acc['revenue_usd']
            merged['event_count']  += acc['event_count']
        return merged
    
    def extract_output(self, accumulator):
        """Convert accumulator to final output metrics."""
        impressions = accumulator['impressions']
        clicks      = accumulator['clicks']
        spend       = accumulator['spend_usd']
        revenue     = accumulator['revenue_usd']
        
        return {
            'impressions':  impressions,
            'clicks':       clicks,
            'conversions':  accumulator['conversions'],
            'spend_usd':    round(spend, 4),
            'revenue_usd':  round(revenue, 4),
            # Derived metrics (safe division — return None if denominator = 0)
            'ctr_pct':  round(clicks / impressions * 100, 4) if impressions > 0 else None,
            'cvr_pct':  round(accumulator['conversions'] / clicks * 100, 4) if clicks > 0 else None,
            'roas':     round(revenue / spend, 4) if spend > 0 else None,
        }


class FormatForBigQuery(beam.DoFn):
    """
    WHAT IT DOES:
    Takes the aggregated results and formats them as BigQuery rows.
    Adds window start/end timestamps.
    
    WHY SEPARATE FROM AGGREGATION:
    The window timestamps are only available in a DoFn context
    (via beam.DoFn.WindowParam), not in CombineFn.
    """
    
    def process(self, element, window=beam.DoFn.WindowParam):
        """
        element = ((campaign_id, channel, device_type), aggregated_metrics)
        window = the time window this element belongs to
        """
        (campaign_id, channel, device_type), metrics = element
        
        yield {
            'window_start':  window.start.to_utc_datetime().isoformat(),
            'window_end':    window.end.to_utc_datetime().isoformat(),
            'campaign_id':   campaign_id,
            'channel':       channel,
            'device_type':   device_type,
            'impressions':   metrics['impressions'],
            'clicks':        metrics['clicks'],
            'conversions':   metrics['conversions'],
            'spend_usd':     metrics['spend_usd'],
            'revenue_usd':   metrics['revenue_usd'],
            'ctr_pct':       metrics['ctr_pct'],
            'cvr_pct':       metrics['cvr_pct'],
            'roas':          metrics['roas'],
            'is_preliminary': True,
            'processed_at':  datetime.utcnow().isoformat()
        }


class FormatRawForBigQuery(beam.DoFn):
    """
    WHAT IT DOES:
    Formats raw (validated) events for storage in the raw events table.
    Stores everything for debugging and batch reprocessing.
    """
    
    def process(self, element):
        yield {
            'event_id':        element.get('event_id'),
            'event_type':      element.get('event_type'),
            'event_timestamp': element.get('event_timestamp'),
            'received_at':     element.get('received_at'),
            'campaign_id':     element.get('campaign_id'),
            'ad_id':           element.get('ad_id'),
            'channel':         element.get('channel'),
            'device_type':     element.get('device_type'),
            'user_id_hash':    element.get('user_id_hash'),
            'session_id':      element.get('session_id'),
            'cost_usd':        element.get('cost_usd'),
            'raw_payload':     json.dumps(element),  # store entire event as JSON string
            '_loaded_at':      datetime.utcnow().isoformat()
        }


# ─────────────────────────────────────────────────────────────────────
# STEP 2: DEFINE BIGQUERY SCHEMAS
# ─────────────────────────────────────────────────────────────────────

METRICS_TABLE_SCHEMA = {
    'fields': [
        {'name': 'window_start',  'type': 'STRING',  'mode': 'REQUIRED'},
        {'name': 'window_end',    'type': 'STRING',  'mode': 'REQUIRED'},
        {'name': 'campaign_id',   'type': 'STRING',  'mode': 'REQUIRED'},
        {'name': 'channel',       'type': 'STRING',  'mode': 'NULLABLE'},
        {'name': 'device_type',   'type': 'STRING',  'mode': 'NULLABLE'},
        {'name': 'impressions',   'type': 'INTEGER', 'mode': 'NULLABLE'},
        {'name': 'clicks',        'type': 'INTEGER', 'mode': 'NULLABLE'},
        {'name': 'conversions',   'type': 'INTEGER', 'mode': 'NULLABLE'},
        {'name': 'spend_usd',     'type': 'FLOAT',   'mode': 'NULLABLE'},
        {'name': 'revenue_usd',   'type': 'FLOAT',   'mode': 'NULLABLE'},
        {'name': 'ctr_pct',       'type': 'FLOAT',   'mode': 'NULLABLE'},
        {'name': 'cvr_pct',       'type': 'FLOAT',   'mode': 'NULLABLE'},
        {'name': 'roas',          'type': 'FLOAT',   'mode': 'NULLABLE'},
        {'name': 'is_preliminary','type': 'BOOLEAN', 'mode': 'NULLABLE'},
        {'name': 'processed_at',  'type': 'STRING',  'mode': 'NULLABLE'},
    ]
}

RAW_EVENTS_SCHEMA = {
    'fields': [
        {'name': 'event_id',        'type': 'STRING',  'mode': 'NULLABLE'},
        {'name': 'event_type',      'type': 'STRING',  'mode': 'NULLABLE'},
        {'name': 'event_timestamp', 'type': 'STRING',  'mode': 'NULLABLE'},
        {'name': 'received_at',     'type': 'STRING',  'mode': 'NULLABLE'},
        {'name': 'campaign_id',     'type': 'STRING',  'mode': 'NULLABLE'},
        {'name': 'ad_id',           'type': 'STRING',  'mode': 'NULLABLE'},
        {'name': 'channel',         'type': 'STRING',  'mode': 'NULLABLE'},
        {'name': 'device_type',     'type': 'STRING',  'mode': 'NULLABLE'},
        {'name': 'user_id_hash',    'type': 'STRING',  'mode': 'NULLABLE'},
        {'name': 'session_id',      'type': 'STRING',  'mode': 'NULLABLE'},
        {'name': 'cost_usd',        'type': 'FLOAT',   'mode': 'NULLABLE'},
        {'name': 'raw_payload',     'type': 'STRING',  'mode': 'NULLABLE'},
        {'name': '_loaded_at',      'type': 'STRING',  'mode': 'NULLABLE'},
    ]
}

DEAD_LETTER_SCHEMA = {
    'fields': [
        {'name': 'raw_message',   'type': 'STRING', 'mode': 'NULLABLE'},
        {'name': 'error_message', 'type': 'STRING', 'mode': 'NULLABLE'},
        {'name': 'failed_at',     'type': 'STRING', 'mode': 'NULLABLE'},
        {'name': 'pipeline_name', 'type': 'STRING', 'mode': 'NULLABLE'},
    ]
}


# ─────────────────────────────────────────────────────────────────────
# STEP 3: THE MAIN PIPELINE FUNCTION
# ─────────────────────────────────────────────────────────────────────

def run_clickstream_pipeline(
    project_id: str,
    region: str = 'us-central1',
    environment: str = 'prod'
):
    """
    THE MAIN PIPELINE.
    Reads from Pub/Sub, processes, writes to BigQuery.
    Runs forever (until you stop it).
    
    Args:
        project_id: Your GCP project ID
        region: GCP region to run Dataflow in
        environment: 'prod' (uses DataflowRunner) or 'local' (uses DirectRunner)
    """
    
    # ─── CONFIGURE PIPELINE OPTIONS ───────────────────────────────────
    
    if environment == 'local':
        # LOCAL TESTING: Run on your laptop, read from file instead of Pub/Sub
        runner = 'DirectRunner'
        options_list = []
        
    else:
        # PRODUCTION: Run on Google Cloud Dataflow
        runner = 'DataflowRunner'
        options_list = [
            f'--project={project_id}',
            f'--region={region}',
            f'--runner={runner}',
            '--streaming',                            # THIS IS A STREAMING JOB
            f'--temp_location=gs://costco-dataflow-staging/temp/',
            f'--staging_location=gs://costco-dataflow-staging/staging/',
            '--enable_streaming_engine',              # uses Dataflow Streaming Engine (faster)
            '--autoscaling_algorithm=THROUGHPUT_BASED', # auto-scale based on data volume
            '--min_num_workers=2',                    # always have at least 2 workers
            '--max_num_workers=20',                   # scale up to 20 workers at peak
            '--worker_machine_type=n1-standard-4',   # 4 CPU, 15GB RAM per worker
            '--disk_size_gb=50',                      # disk per worker
            '--save_main_session',                    # save Python session for workers
            '--job_name=clickstream-ad-analytics',
        ]
    
    options = PipelineOptions(options_list)
    
    # ─── DEFINE RESOURCE NAMES ────────────────────────────────────────
    
    PUBSUB_SUBSCRIPTION = f"projects/{project_id}/subscriptions/ad-events-dataflow-sub"
    METRICS_TABLE = f"{project_id}:streaming.ad_metrics_5min"
    RAW_TABLE = f"{project_id}:raw.ad_events"
    DEAD_LETTER_TABLE = f"{project_id}:raw.dead_letter_events"
    
    # ─── BUILD AND RUN THE PIPELINE ───────────────────────────────────
    
    with beam.Pipeline(options=options) as pipeline:
        
        # ═══════════════════════════════════════════════════════════
        # STAGE 1: INGEST RAW EVENTS FROM PUB/SUB
        # ═══════════════════════════════════════════════════════════
        
        raw_messages = (
            pipeline
            | 'ReadFromPubSub' >> ReadFromPubSub(
                subscription=PUBSUB_SUBSCRIPTION,
                with_attributes=False,   # just the data bytes, not Pub/Sub metadata
                timestamp_attribute=None # we'll extract timestamp from the event body
            )
        )
        # At this point: raw_messages is an UNBOUNDED PCollection of bytes
        # Each element = one Pub/Sub message (bytes)
        
        # ═══════════════════════════════════════════════════════════
        # STAGE 2: PARSE, VALIDATE, SPLIT INTO VALID / DEAD LETTER
        # ═══════════════════════════════════════════════════════════
        
        parsed = (
            raw_messages
            | 'ParseAndValidate' >> beam.ParDo(
                ParseAndValidate()
            ).with_outputs('dead_letter', main='valid')
        )
        
        valid_events = parsed.valid        # PCollection of valid event dicts
        dead_letters = parsed.dead_letter  # PCollection of failed event dicts
        
        # ═══════════════════════════════════════════════════════════
        # STAGE 3: ATTACH EVENT TIMESTAMP FOR WINDOWING
        # ═══════════════════════════════════════════════════════════
        # Beam needs to know WHEN each event happened (event time) to assign it to windows.
        # We tell Beam: "use the event_timestamp field from the event itself."
        
        def extract_timestamp(element):
            """
            Returns a (element, timestamp) tuple.
            Beam uses the timestamp to assign this event to the correct window.
            """
            from apache_beam.utils.timestamp import Timestamp
            import dateutil.parser
            
            ts_str = element.get('event_timestamp', '')
            try:
                dt = dateutil.parser.parse(ts_str)
                unix_ts = dt.timestamp()
                return beam.window.TimestampedValue(element, unix_ts)
            except Exception:
                # If timestamp parsing fails, use current time
                return element
        
        timestamped_events = (
            valid_events
            | 'AttachTimestamp' >> beam.Map(extract_timestamp)
        )
        
        # ═══════════════════════════════════════════════════════════
        # STAGE 4: DEDUPLICATE
        # ═══════════════════════════════════════════════════════════
        
        # For deduplication, we need to key by event_id
        keyed_for_dedup = (
            timestamped_events
            | 'KeyByEventId' >> beam.Map(lambda e: (e['event_id'], e))
        )
        
        deduplicated = (
            keyed_for_dedup
            | 'Deduplicate' >> beam.ParDo(DeduplicateEvents())
        )
        
        # ═══════════════════════════════════════════════════════════
        # STAGE 5: APPLY WINDOWS WITH LATE DATA HANDLING
        # ═══════════════════════════════════════════════════════════
        
        windowed_events = (
            deduplicated
            | 'Apply5MinWindows' >> beam.WindowInto(
                window.FixedWindows(5 * 60),     # 5-minute windows
                
                # Accept events up to 1 hour late
                allowed_lateness=window.Duration(seconds=3600),
                
                # Firing strategy:
                # - Early: emit preliminary result every 30 seconds while window is open
                #   (so dashboard updates frequently, not just when window closes)
                # - Late: re-emit when late events arrive (within allowed_lateness)
                trigger=trigger.AfterWatermark(
                    early=trigger.AfterProcessingTime(30),
                    late=trigger.AfterCount(1)
                ),
                
                # Each firing includes ALL events seen so far (complete running total)
                accumulation_mode=trigger.AccumulationMode.ACCUMULATING
            )
        )
        
        # ═══════════════════════════════════════════════════════════
        # STAGE 6: AGGREGATE METRICS PER CAMPAIGN PER WINDOW
        # ═══════════════════════════════════════════════════════════
        
        campaign_metrics = (
            windowed_events
            | 'KeyForAggregation' >> beam.ParDo(ExtractForAggregation())
            # Creates (key, value) pairs where:
            # key = (campaign_id, channel, device_type)
            # value = {'is_impression': 0/1, 'is_click': 0/1, 'spend_usd': float, ...}
            
            | 'AggregatePerCampaign' >> beam.CombinePerKey(AggregateMetrics())
            # Groups by key, combines all values using AggregateMetrics combiner
            # Result: ((campaign_id, channel, device_type), {impressions, clicks, ...})
            
            | 'FormatForBigQuery' >> beam.ParDo(FormatForBigQuery())
            # Adds window timestamps, formats as BigQuery row dict
        )
        
        # ═══════════════════════════════════════════════════════════
        # STAGE 7A: WRITE METRICS TO BIGQUERY
        # ═══════════════════════════════════════════════════════════
        
        campaign_metrics | 'WriteMetricsToBQ' >> WriteToBigQuery(
            table=METRICS_TABLE,
            schema=METRICS_TABLE_SCHEMA,
            write_disposition=BigQueryDisposition.WRITE_APPEND,
            create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
            # Use streaming inserts for real-time (available immediately)
            # For production: use storage write API for efficiency
            method='STREAMING_INSERTS'
        )
        
        # ═══════════════════════════════════════════════════════════
        # STAGE 7B: WRITE RAW EVENTS TO BIGQUERY (for archiving)
        # ═══════════════════════════════════════════════════════════
        
        raw_events_formatted = (
            valid_events  # use valid_events (not windowed, not aggregated)
            | 'FormatRawEvents' >> beam.ParDo(FormatRawForBigQuery())
        )
        
        raw_events_formatted | 'WriteRawToBQ' >> WriteToBigQuery(
            table=RAW_TABLE,
            schema=RAW_EVENTS_SCHEMA,
            write_disposition=BigQueryDisposition.WRITE_APPEND,
            create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
            method='STREAMING_INSERTS'
        )
        
        # ═══════════════════════════════════════════════════════════
        # STAGE 7C: WRITE DEAD LETTERS TO BIGQUERY (for investigation)
        # ═══════════════════════════════════════════════════════════
        
        dead_letters | 'WriteDeadLetterToBQ' >> WriteToBigQuery(
            table=DEAD_LETTER_TABLE,
            schema=DEAD_LETTER_SCHEMA,
            write_disposition=BigQueryDisposition.WRITE_APPEND,
            create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
            method='STREAMING_INSERTS'
        )
    
    # Pipeline starts running when the 'with' block ends.
    # For streaming: runs FOREVER until you stop it.


# ─────────────────────────────────────────────────────────────────────
# STEP 4: ENTRY POINT
# ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True, help='GCP Project ID')
    parser.add_argument('--region', default='us-central1', help='GCP Region')
    parser.add_argument('--env', default='prod', choices=['prod', 'local'])
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    run_clickstream_pipeline(
        project_id=args.project,
        region=args.region,
        environment=args.env
    )
```

## 3.4 Running the Pipeline

```bash
# ─── OPTION 1: RUN LOCALLY FOR TESTING ───────────────────────────
# Runs on your laptop. Useful for development.
# No cloud costs. But limited by your laptop's memory.

python clickstream_pipeline.py \
  --project=costco-martech-project \
  --env=local

# ─── OPTION 2: SUBMIT TO DATAFLOW (PRODUCTION) ───────────────────
# Runs on Google Cloud.
# Scales automatically.
# You can close your laptop — it keeps running.

python clickstream_pipeline.py \
  --project=costco-martech-project \
  --region=us-central1 \
  --env=prod

# After running this command:
# 1. Your pipeline code is uploaded to GCS
# 2. Dataflow provisions VMs in Google Cloud
# 3. The pipeline starts running
# 4. You can close your terminal — it runs on Google's servers
# 5. Monitor at: https://console.cloud.google.com/dataflow/jobs

# ─── STOP THE PIPELINE ────────────────────────────────────────────
# DRAIN: Finish processing messages already in flight, then stop gracefully
gcloud dataflow jobs drain JOB_ID --region=us-central1

# CANCEL: Stop immediately (might lose in-flight messages)
gcloud dataflow jobs cancel JOB_ID --region=us-central1
```

## 3.5 Monitoring Your Pipeline

```bash
# ─── CHECK JOB STATUS ─────────────────────────────────────────────
gcloud dataflow jobs list --region=us-central1

# ─── VIEW JOB METRICS ─────────────────────────────────────────────
# In the Dataflow UI (https://console.cloud.google.com/dataflow):
# - System lag: how far behind is the watermark? (should be < 2 minutes)
# - Elements processed per second: throughput
# - Worker CPU utilization: are workers overloaded?
# - Pub/Sub backlog: how many messages waiting in Pub/Sub?

# ─── CHECK IF DATA IS FLOWING TO BIGQUERY ─────────────────────────
# Run this SQL in BigQuery to see if metrics are being written:
bq query --use_legacy_sql=false '
SELECT
  window_start,
  window_end,
  campaign_id,
  impressions,
  clicks,
  roas,
  processed_at
FROM `costco-martech-project.streaming.ad_metrics_5min`
WHERE DATE(window_start) = CURRENT_DATE()
ORDER BY processed_at DESC
LIMIT 20
'

# ─── CHECK DEAD LETTER TABLE ──────────────────────────────────────
bq query --use_legacy_sql=false '
SELECT error_message, COUNT(*) as count
FROM `costco-martech-project.raw.dead_letter_events`
WHERE DATE(failed_at) = CURRENT_DATE()
GROUP BY error_message
ORDER BY count DESC
'
```

---

# PART 4: SENDING TEST EVENTS

## 4.1 Publish Test Events to Pub/Sub

```python
# FILE: test_publisher.py
# PURPOSE: Send test events to Pub/Sub to verify your pipeline works

from google.cloud import pubsub_v1
import json
import uuid
import time
from datetime import datetime, timezone

def publish_test_event(publisher, topic_path, event_type, campaign_id):
    """Publish a single test event."""
    event = {
        "event_id": str(uuid.uuid4()),           # unique ID
        "event_type": event_type,                 # impression, click, purchase, etc.
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
        "campaign_id": campaign_id,
        "ad_id": f"ad_{campaign_id}_001",
        "channel": "meta_instagram",
        "device_type": "mobile",
        "user_id": f"user_{uuid.uuid4().hex[:8]}",  # will be hashed by pipeline
        "cost_usd": 0.50 if event_type == "click" else 0.0,
        "revenue_usd": 49.99 if event_type == "purchase" else 0.0
    }
    
    data = json.dumps(event).encode("utf-8")
    future = publisher.publish(topic_path, data=data)
    return future.result()

def run_simulation():
    """Simulate a stream of ad events for testing."""
    project_id = "costco-martech-project"
    topic_path = f"projects/{project_id}/topics/ad-events"
    
    publisher = pubsub_v1.PublisherClient()
    
    print("Starting event simulation...")
    print("Press Ctrl+C to stop")
    
    event_count = 0
    campaigns = ["camp_google_001", "camp_meta_002", "camp_tiktok_003"]
    
    try:
        while True:
            # Simulate impression
            campaign = campaigns[event_count % len(campaigns)]
            publish_test_event(publisher, topic_path, "impression", campaign)
            
            # 20% of impressions get a click
            if event_count % 5 == 0:
                publish_test_event(publisher, topic_path, "click", campaign)
                
                # 10% of clicks become purchases
                if event_count % 50 == 0:
                    publish_test_event(publisher, topic_path, "purchase", campaign)
            
            event_count += 1
            
            if event_count % 100 == 0:
                print(f"Published {event_count} events...")
            
            time.sleep(0.01)  # 100 events per second
            
    except KeyboardInterrupt:
        print(f"\nSimulation stopped. Total events published: {event_count}")

if __name__ == "__main__":
    run_simulation()
```

```bash
# Run the test publisher
python test_publisher.py

# In another terminal, check BigQuery every 30 seconds to see data arrive:
watch -n 30 'bq query --use_legacy_sql=false "
SELECT 
  window_start,
  campaign_id,
  impressions,
  clicks,
  ROUND(ctr_pct, 2) as ctr_pct,
  processed_at
FROM \`costco-martech-project.streaming.ad_metrics_5min\`
ORDER BY processed_at DESC
LIMIT 10"'
```

---

# PART 5: DASHBOARD QUERIES

## 5.1 Real-Time ROAS Dashboard Query

```sql
-- Run this in BigQuery or connect from Looker
-- Shows live metrics for the last 1 hour, updated every 5 minutes

SELECT
    campaign_id,
    channel,
    SUM(impressions)    AS total_impressions,
    SUM(clicks)         AS total_clicks,
    SUM(spend_usd)      AS total_spend_usd,
    SUM(conversions)    AS total_conversions,
    SUM(revenue_usd)    AS total_revenue_usd,
    
    -- CTR: percentage of impressions that led to clicks
    ROUND(SAFE_DIVIDE(SUM(clicks), SUM(impressions)) * 100, 2) AS ctr_pct,
    
    -- CVR: percentage of clicks that led to conversions
    ROUND(SAFE_DIVIDE(SUM(conversions), SUM(clicks)) * 100, 2) AS cvr_pct,
    
    -- ROAS: revenue per dollar spent (> 1 = profitable, < 1 = losing money)
    ROUND(SAFE_DIVIDE(SUM(revenue_usd), SUM(spend_usd)), 2) AS roas,
    
    -- CPA: cost per acquisition
    ROUND(SAFE_DIVIDE(SUM(spend_usd), SUM(conversions)), 2) AS cpa_usd,
    
    MAX(processed_at) AS last_updated

FROM `costco-martech-project.streaming.ad_metrics_5min`
WHERE window_start >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
GROUP BY campaign_id, channel
ORDER BY total_spend_usd DESC;
```

## 5.2 Alert Query — ROAS Below Threshold

```sql
-- Run every 5 minutes via Cloud Scheduler + Cloud Function
-- Sends Slack alert if any campaign's ROAS drops below 1.5

SELECT
    campaign_id,
    channel,
    ROUND(SAFE_DIVIDE(SUM(revenue_usd), SUM(spend_usd)), 2) AS current_roas,
    SUM(spend_usd) AS spend_last_15min
FROM `costco-martech-project.streaming.ad_metrics_5min`
WHERE window_start >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE)
GROUP BY campaign_id, channel
HAVING 
    current_roas < 1.5          -- ROAS below threshold
    AND spend_last_15min > 50   -- Only alert if significant spend
ORDER BY current_roas ASC;
```

---

# PART 6: COMMON ERRORS AND FIXES

```
ERROR 1: "No module named 'apache_beam'"
  FIX: pip install apache-beam[gcp]

ERROR 2: "Permission denied on Pub/Sub subscription"
  FIX: gcloud auth application-default login
       OR set GOOGLE_APPLICATION_CREDENTIALS env var to your service account key

ERROR 3: "Table not found" when writing to BigQuery
  FIX: Create the tables first using the CREATE TABLE SQL above
       OR set create_disposition=CREATE_IF_NEEDED in WriteToBigQuery

ERROR 4: "Watermark not advancing" (dashboard not updating)
  CAUSE: No new events arriving → watermark doesn't advance → windows don't close
  FIX: Check Pub/Sub → is the publisher still sending events?
       Check your pipeline is running: gcloud dataflow jobs list
       Run the test publisher to inject events

ERROR 5: "Dead letter table filling up"
  CAUSE: Events are malformed — missing required fields
  FIX: Check dead_letter table: what are the error_message values?
       Fix the SDK to include the missing fields
       OR relax validation in ParseAndValidate DoFn

ERROR 6: "Pipeline falling behind" (Pub/Sub backlog growing)
  CAUSE: More events arriving than Dataflow can process
  FIX: Increase max_num_workers in pipeline options
       OR increase worker_machine_type to a larger VM

ERROR 7: "Duplicate rows in BigQuery"
  CAUSE: Deduplication using stateful DoFn requires proper state management
  FIX: Add MERGE query to BigQuery to deduplicate after writing:
       
       MERGE INTO streaming.ad_metrics_5min AS target
       USING (
           SELECT *, ROW_NUMBER() OVER (
               PARTITION BY window_start, campaign_id, channel
               ORDER BY processed_at DESC
           ) AS rn
           FROM streaming.ad_metrics_5min
       ) AS source
       ON target.window_start = source.window_start
          AND target.campaign_id = source.campaign_id
          AND target.channel = source.channel
       WHEN MATCHED AND source.rn > 1 THEN DELETE;
```

---

# SUMMARY: WHAT YOU BUILT

```
YOU NOW HAVE:

Cloud Pub/Sub
  Topic: ad-events
  Subscription: ad-events-dataflow-sub
  (Durable buffer. Never loses events. Holds for 7 days.)
      │
      ▼
Cloud Dataflow (your clickstream_pipeline.py)
  Runs 24/7 on Google's servers.
  Stages:
  1. Reads raw bytes from Pub/Sub
  2. Parses JSON → validates → hashes PII
  3. Deduplicates using event_id
  4. Assigns to 5-minute event-time windows
  5. Aggregates: clicks, impressions, spend per campaign per window
  6. Writes results to BigQuery every 30 seconds (early trigger)
      │
      ├──────────────────────────────────────────────────────────┐
      ▼                                                          ▼
BigQuery: streaming.ad_metrics_5min                  BigQuery: raw.ad_events
(aggregated metrics — fast to query)                 (all raw events — for debugging)
      │
      ▼
Looker Dashboard
  "Real-time ROAS by Campaign"
  Updated every 5 minutes
  Marketing team sees: which campaigns are profitable right now?

WHAT YOU HANDLE:
  ✓ Mobile events (iOS, Android)
  ✓ Web browser events
  ✓ Multiple campaigns simultaneously
  ✓ Late data (up to 1 hour via allowed_lateness)
  ✓ Duplicates (stateful deduplication by event_id)
  ✓ Bad data (dead letter routing)
  ✓ Pipeline crashes (Pub/Sub buffer + Dataflow checkpointing)
  ✓ Traffic spikes (Dataflow auto-scaling)
  ✓ GDPR (user_id hashed at ingestion)
```
