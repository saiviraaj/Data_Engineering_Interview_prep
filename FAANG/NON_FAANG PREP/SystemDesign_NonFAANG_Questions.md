# System Design Interview Questions - Non-FAANG Level

Complete system design problems for data engineering roles.

---

## System 1: URL Shortener (like bit.ly)

**Requirements:**
- Shorten long URLs to short codes
- Redirect short URLs to original
- Scale: 1M URLs shortened per day
- Latency: <200ms
- Availability: 99.9%

**High-Level Design:**

```
Client → API Gateway → Service → Database
                     → Cache
```

**Database Design:**

```sql
CREATE TABLE urls (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    short_code VARCHAR(10) UNIQUE,
    long_url VARCHAR(2000),
    created_at TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX idx_short_code ON urls(short_code);
CREATE INDEX idx_created_at ON urls(created_at);
```

**API Design:**

```python
POST /shorten
{
    "long_url": "https://example.com/very/long/path"
}
Response:
{
    "short_code": "abc123",
    "short_url": "https://short.url/abc123"
}

GET /abc123
→ Redirect to original URL
```

**Encoding Strategy:**

```python
import string

def encode(num):
    chars = string.ascii_letters + string.digits
    result = ""
    while num:
        result = chars[num % 62] + result
        num //= 62
    return result or "a"

def decode(code):
    chars = string.ascii_letters + string.digits
    result = 0
    for char in code:
        result = result * 62 + chars.index(char)
    return result
```

**Caching Strategy:**

```
Hot URLs (frequently accessed) → Redis Cache
- Cache hit: ~1ms
- Cache miss: DB query ~10ms + cache write
```

**Sharding Strategy:**

```
Database partitioned by short_code range
Shard 1: a-f
Shard 2: g-l
Shard 3: m-r
Shard 4: s-z, 0-9
```

**Scaling Challenges:**

1. **Handling 1M daily URLs**
   - IDs: Using auto-increment
   - Distribution: Hash-based sharding
   - Replication: Master-slave for reads

2. **Handling Redirects**
   - Cache frequently accessed
   - CDN for static redirects
   - Connection pooling

3. **Data Expiration**
   - Batch delete expired records
   - TTL in cache

**Monitoring:**
- Requests per second
- Cache hit rate
- Database latency
- Short code collision rate

---

## System 2: Design a Data Pipeline

**Requirements:**
- Ingest data from multiple sources
- Transform and validate
- Store in data warehouse
- Real-time monitoring

**Architecture:**

```
Data Sources
    ↓
(Kafka/Pub-Sub)
    ↓
Stream Processor (Spark/Beam)
    ↓
Transformation Layer
    ↓
Data Warehouse (BigQuery/Redshift)
    ↓
BI Tools / Reports
```

**Component Details:**

```python
# 1. Source Ingestion
def ingest_from_api():
    response = requests.get(api_url)
    data = response.json()
    # Publish to Kafka
    producer.send("raw_events", data)

# 2. Stream Processing
def process_stream():
    df = spark.readStream \
        .format("kafka") \
        .option("subscribe", "raw_events") \
        .load()
    
    processed = df.select(
        from_json(col("value"), schema).alias("data")
    ).select("data.*")
    
    return processed

# 3. Transformation
def transform(df):
    transformed = df \
        .withColumn("processed_at", current_timestamp()) \
        .filter(col("status") == "valid") \
        .withColumn("category", 
            when(col("amount") > 100, "high")
            .otherwise("low")
        )
    return transformed

# 4. Storage
def store_in_warehouse(df):
    df.write \
        .partitionBy("date") \
        .mode("append") \
        .parquet("warehouse/events")
```

**Data Quality Checks:**

```python
def quality_checks(df):
    checks = df.select(
        count(when(isnull(col("id")), 1)).alias("null_ids"),
        count(when(col("amount") < 0, 1)).alias("negative"),
        count("*").alias("total")
    )
    
    return checks

# Alert if quality < 95%
quality = quality_checks(df).collect()[0]
if quality['null_ids'] / quality['total'] > 0.05:
    alert("Data quality issue")
```

**Error Handling:**

```python
# Dead Letter Queue for bad records
bad_records = df.filter(quality_score < threshold)
bad_records.write.parquet("dead_letter_queue")

# Retry logic
for attempt in range(3):
    try:
        store_in_warehouse(df)
        break
    except Exception as e:
        if attempt < 2:
            time.sleep(2 ** attempt)
```

---

## System 3: Real-time Analytics Dashboard

**Requirements:**
- Display metrics in real-time
- <2 second latency
- Support 1000 concurrent users
- Show last 24 hours data

**Architecture:**

```
Events → Kafka → Stream Processor → In-Memory Store (Redis)
                                 → Time-Series DB (InfluxDB)
                                 
Browser → API Server → Redis → Response
       → WebSocket → Real-time Updates
```

**Real-time Components:**

```python
# WebSocket for live updates
from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

@socketio.on('connect')
def handle_connect():
    # Subscribe to metrics updates
    emit('connected', {'data': 'Connected'})

# Broadcast updates to connected clients
def broadcast_metrics(metrics):
    socketio.emit('metrics_update', metrics, broadcast=True)
```

**Time-Series Data:**

```python
# Store aggregated metrics
def aggregate_metrics(df):
    metrics = df.groupBy(
        window(col("timestamp"), "1 minute")
    ).agg(
        count("*").alias("events"),
        avg(col("amount")).alias("avg_amount"),
        max(col("amount")).alias("max_amount")
    )
    return metrics

# Write to InfluxDB
def write_influxdb(metrics):
    for row in metrics.collect():
        point = {
            "measurement": "events",
            "time": row.timestamp,
            "fields": {
                "count": row.events,
                "avg_amount": row.avg_amount
            }
        }
        influx_client.write_points([point])
```

**Caching Strategy:**

```python
# Cache recent aggregates in Redis
def cache_metrics(metrics):
    for row in metrics.collect():
        key = f"metrics:{row.timestamp}"
        redis.setex(key, 3600, json.dumps(row))

# Fetch from cache
def get_metrics(timestamp):
    cached = redis.get(f"metrics:{timestamp}")
    return json.loads(cached) if cached else compute()
```

---

## System 4: Notification System

**Requirements:**
- Send email, SMS, push notifications
- Support millions of notifications daily
- Retry failed deliveries
- Track delivery status

**Architecture:**

```
Events → Queue → Worker Pool → Providers (Email, SMS, Push)
      ↓
Database ← Status Updates
```

**Implementation:**

```python
from celery import Celery
import redis

app = Celery('notifications')

# Queue notification
def send_notification(user_id, message, channels):
    task = {
        "user_id": user_id,
        "message": message,
        "channels": channels,
        "created_at": timestamp(),
        "retry_count": 0
    }
    redis.lpush("notification_queue", json.dumps(task))

# Worker processes notifications
@app.task(bind=True, max_retries=3)
def process_notification(self, task):
    try:
        if 'email' in task['channels']:
            send_email(task['user_id'], task['message'])
        if 'sms' in task['channels']:
            send_sms(task['user_id'], task['message'])
        
        update_status(task['id'], 'delivered')
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        else:
            update_status(task['id'], 'failed')

# Database schema
"""
CREATE TABLE notifications (
    id BIGINT PRIMARY KEY,
    user_id BIGINT,
    message TEXT,
    channels VARCHAR(100),
    status ENUM('pending', 'sent', 'failed'),
    created_at TIMESTAMP,
    sent_at TIMESTAMP,
    retry_count INT
);

CREATE INDEX idx_user_id ON notifications(user_id);
CREATE INDEX idx_status ON notifications(status);
"""
```

---

## System 5: User Authentication & Session Management

**Design:**

```
Login Request → Validate → Issue JWT Token
Request + JWT → Verify Token → Authorize

Session stored in Redis for quick access
```

**Implementation:**

```python
import jwt
from datetime import datetime, timedelta

# Issue token
def create_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    
    # Store session
    redis.setex(f"session:{user_id}", 86400, token)
    
    return token

# Verify token
def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
        
        # Check if session still valid
        session = redis.get(f"session:{user_id}")
        if session and session.decode() == token:
            return user_id
        return None
    except jwt.ExpiredSignatureError:
        return None
```

---

## Tips for System Design Interviews

✅ **Approach:**
1. Clarify requirements (QPS, storage, latency)
2. High-level design first
3. Deep dive into components
4. Discuss scaling challenges
5. Trade-offs (consistency vs availability, latency vs cost)

✅ **What they evaluate:**
- Problem-solving approach
- Technical depth
- Communication
- Trade-off awareness
- Real-world considerations

---

