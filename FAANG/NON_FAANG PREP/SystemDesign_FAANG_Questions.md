# System Design - FAANG Level

Ultra-large scale systems for FAANG interviews.

---

## System 1: YouTube (Video Streaming at Scale)

**Scale:** Billions of users, Petabytes of video

**Requirements:**
- Upload videos (1000s per minute)
- Stream to billions concurrently
- Real-time view counts
- Recommendations based on watch history
- Latency: <200ms for video start
- 99.99% availability

**High-Level Architecture:**

```
Upload Pipeline:
User → Upload Service → Queue → Transcoding Service 
    → Multiple Formats (720p, 480p, 360p)
    → Distributed Storage (S3)
    → CDN Edge Locations

Streaming:
User → CDN (closest edge) → Origin Server
    → Load Balancer → Multiple Regions

Metadata Service:
Video Info → Database (Sharded)
Comments → NoSQL (MongoDB)
Recommendations → ML Pipeline
View Counts → Real-time Counter (Redis)
```

**Key Components:**

```python
# 1. Upload & Transcoding
class TranscodingService:
    def upload_video(self, video_id, file):
        # Store original
        original_path = s3.put(video_id, file)
        
        # Queue transcoding
        queue.enqueue({
            'video_id': video_id,
            'original_path': original_path,
            'formats': ['1080p', '720p', '480p']
        })
        
        return video_id
    
    def transcode(self, job):
        for format in job['formats']:
            # Parallel transcoding
            process_with_ffmpeg(job['original_path'], format)
            # Upload to CDN
            cdn.upload(job['video_id'], format, transcoded)

# 2. Streaming with Adaptive Bitrate
class StreamingService:
    def get_stream(self, video_id, user_bandwidth):
        # Select format based on bandwidth
        if user_bandwidth > 10_000:
            format = '1080p'
        elif user_bandwidth > 5_000:
            format = '720p'
        else:
            format = '480p'
        
        # Get from CDN closest to user
        return cdn.get_url(video_id, format, user_location)

# 3. Real-time View Counts
class ViewCounter:
    def view(self, video_id):
        # Increment in Redis
        redis.incr(f"views:{video_id}")
        
        # Batch write to DB every 5 seconds
        if redis.exists(f"batch_timer:{video_id}"):
            batch_write(video_id)
    
    def get_views(self, video_id):
        # Check Redis first (hot count)
        views_redis = redis.get(f"views:{video_id}")
        if views_redis:
            return views_redis
        # Fall back to DB
        return db.query(f"SELECT views FROM videos WHERE id = {video_id}")

# 4. Recommendations Engine
class RecommendationEngine:
    def get_recommendations(self, user_id):
        # Fetch user watch history
        history = db.query(f"SELECT videos FROM watch_history WHERE user_id = {user_id}")
        
        # Use ML model (trained offline)
        embeddings = ml_model.get_embeddings(history)
        
        # Find similar videos using vector DB
        recommendations = vector_db.nearest(embeddings, k=20)
        
        # Filter and personalize
        return personalize_recommendations(recommendations, user_id)
```

**Scaling Strategy:**

```
Database:
- Shard by video_id
- Replicate for read scaling
- Cache metadata in Redis

CDN:
- Edge locations in 6 continents
- Cache video content
- Origin failover

Real-time:
- Stream processors for live counts
- WebSocket for live updates
```

---

## System 2: Twitter (Real-time Feed Generation)

**Scale:** 400 million tweets daily, 1 billion users

**Requirements:**
- Post tweets instantly
- See tweets from followed users in real-time
- Timeline load in <500ms
- Handle celebrity with 100M followers
- 99.9% availability

**Architecture:**

```
Tweet Creation:
User → Write Service → Queue → Database
                    → Message Queue (Kafka)

Timeline Generation:
Message Queue → Feed Builder → Cache (Redis)
                            → Fan-out Service
                            
Timeline Read:
User → API → Cache (check first)
         → Database (if miss)
         → Rebuild Feed
```

**Tweet Creation:**

```python
class TweetService:
    def create_tweet(self, user_id, content):
        tweet = {
            'id': generate_uuid(),
            'user_id': user_id,
            'content': content,
            'created_at': now(),
            'likes': 0,
            'retweets': 0
        }
        
        # Write to DB
        tweet_db.insert(tweet)
        
        # Publish event
        kafka.publish('tweet_created', tweet)
        
        return tweet

class FanOutService:
    def fanout(self, tweet):
        user_id = tweet['user_id']
        
        # Get followers
        followers = db.query(f"SELECT follower_id FROM follows WHERE user_id = {user_id}")
        
        # Push to each follower's timeline (async)
        for follower_id in followers:
            redis.lpush(f"timeline:{follower_id}", tweet['id'])
            redis.ltrim(f"timeline:{follower_id}", 0, 999)  # Keep last 1000
        
        # For celebrity accounts (huge follower count):
        if len(followers) > 10_000_000:
            # Don't fanout - compute on read
            cache.mark_needs_rebuild(user_id)
```

**Timeline Read:**

```python
class TimelineService:
    def get_timeline(self, user_id, page=0):
        cache_key = f"timeline:{user_id}:{page}"
        
        # Try cache first
        cached = redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Cache miss - read from DB
        tweets = db.query(f"""
            SELECT t.* FROM tweets t
            JOIN follows f ON t.user_id = f.user_id
            WHERE f.follower_id = {user_id}
            ORDER BY t.created_at DESC
            LIMIT 20 OFFSET {page * 20}
        """)
        
        # Cache result for 1 minute
        redis.setex(cache_key, 60, json.dumps(tweets))
        
        return tweets
```

**Celebrity Handling:**

```python
class CelebrityTimelineService:
    def get_timeline(self, user_id):
        # For celebrities: compute intersection of followers' tweets
        # Merge with own tweets
        
        # Get own tweets
        own_tweets = db.query(f"SELECT * FROM tweets WHERE user_id = {user_id}")
        
        # Get random sample of follows' tweets
        followed = db.query(f"SELECT following_id FROM follows WHERE follower_id = {user_id}")
        
        # Sample strategy to avoid full join
        sample = random.sample(followed, min(1000, len(followed)))
        
        timeline = merge_and_sort(own_tweets, sample)
        return timeline[:20]
```

---

## System 3: Google Search (Index & Query)

**Scale:** Trillions of web pages, billions of queries daily

**Architecture:**

```
Crawl:
Crawler → Fetch Pages → Parse Content → Build Inverted Index
       → Store in Distributed File System

Index:
Inverted Index → Shard by Word
              → Replicate across Data Centers

Query:
Query → Distributed Query Processor
     → Each Shard Searches
     → Merge Results
     → Rank with PageRank + ML
     → Return Top 10
```

**Inverted Index:**

```python
# Shard 1: Words A-E
# Shard 2: Words F-J
# etc.

class IndexBuilder:
    def build_index(self, documents):
        inverted_index = defaultdict(list)
        
        for doc_id, content in documents:
            words = tokenize(content)
            
            for position, word in enumerate(words):
                # Normalize word
                word = normalize(word)
                
                # Add to index
                inverted_index[word].append({
                    'doc_id': doc_id,
                    'position': position,
                    'tf': term_frequency(word, content)
                })
        
        # Write to distributed store
        for word, postings in inverted_index.items():
            shard_id = hash(word) % num_shards
            store_to_shard(shard_id, word, postings)
```

**Query Processing:**

```python
class QueryProcessor:
    def search(self, query, top_k=10):
        # Parse query
        terms = tokenize(query)
        
        # Get postings from each shard
        all_postings = []
        for term in terms:
            shard_id = hash(term) % num_shards
            postings = query_shard(shard_id, term)
            all_postings.append(postings)
        
        # Intersect postings
        result_docs = intersect_postings(all_postings)
        
        # Score and rank
        scores = {}
        for doc_id in result_docs:
            # BM25 + PageRank + ML signals
            score = bm25_score(doc_id, terms)
            score += pagerank_score(doc_id) * 0.3
            score += ml_ranking_score(doc_id, query) * 0.2
            scores[doc_id] = score
        
        # Sort and return
        top_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [{'id': doc_id, 'score': score} for doc_id, score in top_docs]
```

---

## System 4: WhatsApp (Real-time Messaging at Scale)

**Scale:** 100 billion messages daily, 2 billion users

**Requirements:**
- Instant message delivery (<1 second)
- Delivery guarantees (exactly once)
- Support groups with 1000+ members
- Availability: 99.99%
- End-to-end encryption

**Architecture:**

```
Client → WebSocket → Message Service → Message Queue
                                   → Delivery Service
                                   → Notification Service
```

**Message Delivery:**

```python
class MessageService:
    def send_message(self, sender_id, recipient_id, message):
        msg_id = uuid.uuid4()
        msg_obj = {
            'id': msg_id,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'content': message,
            'status': 'sent',
            'timestamp': now()
        }
        
        # Store for persistence
        db.insert(msg_obj)
        
        # Try immediate delivery
        if user_online(recipient_id):
            send_via_websocket(recipient_id, msg_obj)
            update_status(msg_id, 'delivered')
        else:
            # Queue for later delivery
            queue.enqueue(msg_id, recipient_id)

class DeliveryService:
    def deliver_queued_messages(self, recipient_id):
        messages = queue.get_for_user(recipient_id)
        
        for msg_id in messages:
            try:
                send_via_websocket(recipient_id, msg_id)
                update_status(msg_id, 'delivered')
                queue.remove(msg_id)
            except Exception:
                queue.retry(msg_id)  # Retry logic
```

**Group Messages:**

```python
class GroupMessageService:
    def send_group_message(self, sender_id, group_id, message):
        # Store message
        msg = store_message(sender_id, group_id, message)
        
        # Get group members
        members = db.query(f"SELECT member_id FROM group_members WHERE group_id = {group_id}")
        
        # Send to each member asynchronously
        for member_id in members:
            if member_id != sender_id:
                queue.enqueue({
                    'type': 'deliver_group_message',
                    'msg_id': msg['id'],
                    'recipient': member_id
                })
```

---

**Interview Tips for System Design:**

✅ **What FAANG looks for:**
- Handling massive scale (billions of users)
- Trade-offs between consistency and availability
- Real-time processing at scale
- Data partitioning and replication
- Caching strategies
- Communication patterns

✅ **Common Questions:**
- "How would you handle 10x growth?"
- "What's the single point of failure?"
- "How do you ensure data consistency?"
- "What about regional latency?"

---

