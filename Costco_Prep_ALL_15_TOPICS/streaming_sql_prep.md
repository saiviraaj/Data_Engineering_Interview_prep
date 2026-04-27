# Streaming + SQL Interview Preparation Notes

## 1. Streaming Fundamentals

### What is Streaming?
Streaming is continuous processing of unbounded data in real-time or near real-time.

### Event Time vs Processing Time
- Event Time: When event occurred
- Processing Time: When system processes it

### Windowing
- Tumbling: Fixed, non-overlapping
- Sliding: Overlapping
- Session: Based on inactivity

### Watermark
Watermark indicates event-time completeness.
- Moves based on minimum event time seen
- Used to close windows

### Late Data Handling
- Within allowed lateness → processed
- Beyond allowed lateness → dropped or side output

---

## 2. Streaming System Design

### Architecture
Producer → Pub/Sub → Dataflow → Sink (BigQuery)

### CTR Pipeline
- Key by (ad_id, window)
- Maintain state:
  - click_count
  - impression_count
- Compute CTR after aggregation

### Deduplication
- Use event_id (UUID)
- Store processed IDs
- Apply TTL
- Ensure idempotent sinks

### Exactly Once
Not truly guaranteed end-to-end.
Achieved using:
- Checkpointing
- Idempotent writes
- Deduplication

---

## 3. SQL Practice

### DAU
```sql
SELECT DATE(event_time), COUNT(DISTINCT user_id)
FROM user_events
GROUP BY DATE(event_time);
```

### First Login Per Day
```sql
SELECT user_id, DATE(event_time), MIN(event_time)
FROM user_events
GROUP BY user_id, DATE(event_time);
```

### Consecutive Days (Row Number Trick)
```sql
event_date - row_number()
```

### Rolling 3 Day Users
Use self-join on date range.

---

## 4. Funnel Conversion

Steps:
1. Get first view
2. Get first cart after view
3. Get first purchase after cart
4. Join sequentially

---

## 5. Streaming Joins

- Use event-time window joins
- Key by user_id/session_id
- Maintain state
- Use watermark for cleanup

---

## 6. Interview Key Concepts

- Accuracy vs Latency tradeoff
- Stateful processing is core
- Windowing is mandatory
- Dedup + idempotency = reliability

