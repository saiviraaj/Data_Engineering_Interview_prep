# 📘 Streaming + SQL Interview Playbook (Detailed)

---

# 🔷 SECTION 1: STREAMING FUNDAMENTALS

## What is Streaming?
Streaming is continuous processing of unbounded data in real-time.

### Interview Answer:
Streaming processes data as it arrives, unlike batch which processes data in chunks.

---

## Event Time vs Processing Time

| Type | Meaning |
|------|--------|
| Event Time | When event occurred |
| Processing Time | When system processes it |

### Why important?
Processing delays → incorrect aggregations

### Interview Answer:
Event time ensures correctness in distributed systems with delays.

---

## Windowing

### Types:
- Tumbling → fixed, non-overlapping
- Sliding → overlapping
- Session → based on inactivity

### Why needed?
Streaming data is infinite → needs grouping

---

## Watermark (Deep)

Watermark = estimate of completeness of event-time data

### Formula:
Watermark = min(event_time_seen) - delay

### Key Points:
- Not exact guarantee
- Driven by slowest partition

### Behavior:
- Before watermark → normal
- After watermark → late
- Beyond allowed lateness → dropped

---

## Late Data Handling

### Types:
1. Within allowed lateness → update window
2. Beyond → drop or side output

### Strategies:
- Allowed lateness
- Side output
- Batch reprocessing
- Lambda/Kappa architecture

---

# 🔷 SECTION 2: EXACTLY-ONCE PROCESSING

## Problem:
Distributed failures cause:
- duplicates
- retries

## Why hard?
No atomic transaction across:
Source → Processing → Sink

## Solution:
- Checkpointing
- Idempotent writes
- Deduplication

### Interview Answer:
Exactly-once is simulated using at-least-once + idempotency.

---

# 🔷 SECTION 3: DEDUPLICATION

## Basic Idea:
Use unique event_id (UUID)

## But also need:
- Storage of seen IDs
- TTL

## Approaches:
- Stateful dedup (Dataflow)
- External store (Redis/Bigtable)
- Idempotent sink

---

# 🔷 SECTION 4: STREAMING JOINS

## Incorrect idea:
Broadcast join ❌

## Correct:
- Event-time window join
- Stateful join

## Steps:
1. Key by user_id
2. Apply window
3. Store state
4. Match events

---

# 🔷 SECTION 5: SQL QUESTIONS

## DAU
SELECT DATE(event_time), COUNT(DISTINCT user_id)
FROM user_events
GROUP BY DATE(event_time);

---

## First Login
SELECT user_id, DATE(event_time), MIN(event_time)
FROM user_events
GROUP BY user_id, DATE(event_time);

---

## Consecutive Days
Use:
event_date - row_number()

---

## Rolling 3 Day Users
Use self join:
date between current_date - 2 and current_date

---

## Funnel Conversion

Steps:
1. First view
2. First cart after view
3. First purchase after cart
4. Join sequentially

---

## CTR Query

Steps:
1. Aggregate per ad + date
2. Count clicks & impressions
3. Compute CTR
4. Rank using DENSE_RANK

---

# 🔷 SECTION 6: STREAMING DESIGN (CTR)

## Pipeline:
Pub/Sub → Dataflow → BigQuery

## Steps:
1. Event-time processing
2. Windowing
3. Key by ad_id
4. Maintain state (click/impression)
5. Compute CTR
6. Rank Top N

---

## Edge Cases:
- duplicates → dedup
- late data → watermark
- failures → checkpointing

---

# 🔷 SECTION 7: INTERVIEW GOLD POINTS

- Accuracy vs latency tradeoff
- Stateful processing is core
- Windowing is mandatory
- Exactly-once is simulated
- Deduplication is critical

---

# 🔥 FINAL INTERVIEW SUMMARY

If asked ANY streaming question:

Say:
- Event-time
- Windowing
- Watermark
- Stateful aggregation
- Deduplication
- Idempotent sink

👉 This covers 90% of answers

---

# 🚀 END
