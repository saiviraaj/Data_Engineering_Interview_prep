# Python Practice — DSA & LeetCode-Style Questions
## Costco Sr. Data Engineer Interview Prep

> Focus: Data structures, algorithms, and Python patterns that come up in DE interviews.
> Not pure algorithmic puzzles — every problem has a data engineering context.

---

## SECTION 1: EASY

---

### E1. Two Sum — find pair with target (classic, but know it cold)

```python
def two_sum(nums: list[int], target: int) -> list[int]:
    """
    Find two indices such that nums[i] + nums[j] == target.
    Return [i, j].
    
    DE context: find two campaign IDs whose combined budget equals target.
    """
    seen = {}   # value → index
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []

# Time: O(n) | Space: O(n)

# Test
assert two_sum([2, 7, 11, 15], 9) == [0, 1]
assert two_sum([3, 2, 4], 6) == [1, 2]
print("two_sum: OK")
```

---

### E2. Valid parentheses — validate expression string

```python
def is_valid_expression(s: str) -> bool:
    """
    Check if brackets/parens are balanced.
    DE context: validate SQL expression syntax, JSON structure,
    nested function calls in pipeline configs.
    """
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}

    for char in s:
        if char in mapping.values():    # opening bracket
            stack.append(char)
        elif char in mapping:           # closing bracket
            if not stack or stack[-1] != mapping[char]:
                return False
            stack.pop()

    return len(stack) == 0

# Time: O(n) | Space: O(n)

assert is_valid_expression("(SELECT * FROM t WHERE (a=1 AND b=2))") == True
assert is_valid_expression("((a+b)*(c-d)") == False
assert is_valid_expression("{\"key\": [1, 2, 3]}") == True
print("valid_expression: OK")
```

---

### E3. Merge sorted arrays — two-pointer technique

```python
def merge_sorted_events(events1: list, events2: list) -> list:
    """
    Merge two sorted lists of events (by timestamp) into one sorted list.
    DE context: merge event streams from two data sources,
    merge sorted Parquet file chunks.
    
    Time: O(m+n) | Space: O(m+n)
    """
    result = []
    i = j = 0

    while i < len(events1) and j < len(events2):
        if events1[i]['timestamp'] <= events2[j]['timestamp']:
            result.append(events1[i])
            i += 1
        else:
            result.append(events2[j])
            j += 1

    # Append remaining elements
    result.extend(events1[i:])
    result.extend(events2[j:])
    return result

# Test
e1 = [{'id': 1, 'timestamp': 1}, {'id': 3, 'timestamp': 3}]
e2 = [{'id': 2, 'timestamp': 2}, {'id': 4, 'timestamp': 4}]
merged = merge_sorted_events(e1, e2)
assert [e['id'] for e in merged] == [1, 2, 3, 4]
print("merge_sorted: OK")
```

---

### E4. Find duplicates in a list

```python
from collections import Counter

def find_duplicate_ids(ids: list) -> list:
    """
    Find all IDs that appear more than once.
    DE context: find duplicate click_ids, transaction_ids, etc.
    """
    counts = Counter(ids)
    return [id_ for id_, cnt in counts.items() if cnt > 1]

def find_duplicate_ids_optimized(ids: list) -> set:
    """Faster: stop after first encounter of a duplicate."""
    seen = set()
    duplicates = set()
    for id_ in ids:
        if id_ in seen:
            duplicates.add(id_)
        seen.add(id_)
    return duplicates

# Test
ids = ["C001", "C002", "C001", "C003", "C002", "C004"]
assert set(find_duplicate_ids(ids)) == {"C001", "C002"}
print("find_duplicates: OK")
```

---

### E5. Group by and aggregate (without pandas/Spark)

```python
from collections import defaultdict
from typing import Dict, List

def group_and_aggregate(records: List[Dict]) -> Dict:
    """
    Group click records by campaign_id, compute total spend and click count.
    DE context: lightweight aggregation without a distributed framework.
    """
    agg = defaultdict(lambda: {'clicks': 0, 'spend': 0.0})

    for record in records:
        cid = record['campaign_id']
        agg[cid]['clicks'] += 1
        agg[cid]['spend'] += record.get('cost_usd', 0.0)

    # Compute derived metrics
    for cid in agg:
        spend = agg[cid]['spend']
        clicks = agg[cid]['clicks']
        agg[cid]['avg_cpc'] = round(spend / clicks, 4) if clicks > 0 else 0.0

    return dict(agg)

# Test
records = [
    {'campaign_id': 'C1', 'cost_usd': 1.5},
    {'campaign_id': 'C1', 'cost_usd': 2.0},
    {'campaign_id': 'C2', 'cost_usd': 3.0},
]
result = group_and_aggregate(records)
assert result['C1']['clicks'] == 2
assert result['C1']['spend'] == 3.5
print("group_aggregate: OK")
```

---

## SECTION 2: MEDIUM

---

### M1. LRU Cache — implement from scratch

```python
from collections import OrderedDict

class LRUCache:
    """
    Least Recently Used cache.
    DE context: caching lookup results (campaign configs, exchange rates),
    preventing repeated DB calls.
    """

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = OrderedDict()  # maintains insertion/access order

    def get(self, key) -> int:
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)   # mark as recently used
        return self.cache[key]

    def put(self, key, value) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)   # remove least recently used

# Time: O(1) for get and put | Space: O(capacity)

# Test
cache = LRUCache(3)
cache.put("C001", 500)
cache.put("C002", 750)
cache.put("C003", 1000)
assert cache.get("C001") == 500     # access C001 (now most recent)
cache.put("C004", 1250)             # C002 should be evicted (LRU)
assert cache.get("C002") == -1      # evicted
assert cache.get("C004") == 1250
print("LRU cache: OK")
```

---

### M2. Sliding window maximum — max value in window of size k

```python
from collections import deque

def max_in_window(values: list, k: int) -> list:
    """
    Find maximum in every sliding window of size k.
    DE context: rolling maximum ROAS, rolling max spend for anomaly detection.
    O(n) using monotonic deque vs O(n*k) brute force.
    """
    if not values or k == 0:
        return []

    dq = deque()   # stores indices, decreasing order of values
    result = []

    for i, val in enumerate(values):
        # Remove elements outside the window
        while dq and dq[0] <= i - k:
            dq.popleft()

        # Maintain decreasing order (remove smaller elements from back)
        while dq and values[dq[-1]] <= val:
            dq.pop()

        dq.append(i)

        # Window is full starting at index k-1
        if i >= k - 1:
            result.append(values[dq[0]])

    return result

# Time: O(n) | Space: O(k)

daily_roas = [3.0, 1.5, 4.2, 2.1, 5.0, 3.8, 2.5]
assert max_in_window(daily_roas, 3) == [4.2, 4.2, 5.0, 5.0, 5.0]
print("sliding_window_max: OK")

# DE application: 7-day rolling max ROAS
# max_in_window(campaign_roas_series, 7)
```

---

### M3. Top K frequent elements

```python
import heapq
from collections import Counter

def top_k_campaigns(events: list, k: int) -> list:
    """
    Find k campaigns with most events.
    DE context: find top-k performing campaigns, top-k users, top-k keywords.
    """
    counts = Counter(e['campaign_id'] for e in events)

    # Method 1: heapq.nlargest — O(n log k)
    return heapq.nlargest(k, counts, key=lambda x: counts[x])

    # Method 2: sort — O(n log n)
    # return sorted(counts, key=counts.get, reverse=True)[:k]

    # Method 3: bucket sort — O(n) when range of counts is bounded
    # bucket[i] = list of campaigns with i occurrences
    # iterate buckets from high to low

# Test
events = [
    {'campaign_id': 'C1'},
    {'campaign_id': 'C2'},
    {'campaign_id': 'C1'},
    {'campaign_id': 'C3'},
    {'campaign_id': 'C1'},
    {'campaign_id': 'C2'},
]
assert top_k_campaigns(events, 2) == ['C1', 'C2']
print("top_k_campaigns: OK")
```

---

### M4. Merge intervals — find gaps and overlaps in schedules

```python
def merge_campaign_intervals(intervals: list) -> list:
    """
    Given campaign active periods [(start, end), ...], merge overlapping ones.
    DE context: merge time ranges for deduplication, find coverage gaps,
    detect overlapping ad schedules.
    """
    if not intervals:
        return []

    # Sort by start time
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]

    for start, end in intervals[1:]:
        # Check if current interval overlaps with last merged
        if start <= merged[-1][1]:
            # Overlapping: extend end if needed
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            # No overlap: add new interval
            merged.append((start, end))

    return merged

# Find gaps between intervals
def find_gaps(intervals: list, range_start, range_end) -> list:
    """Find periods NOT covered by any interval."""
    merged = merge_campaign_intervals(intervals)
    gaps = []

    current = range_start
    for start, end in merged:
        if current < start:
            gaps.append((current, start))
        current = max(current, end)

    if current < range_end:
        gaps.append((current, range_end))

    return gaps

# Time: O(n log n) | Space: O(n)

intervals = [(1,3), (2,6), (8,10), (15,18)]
assert merge_campaign_intervals(intervals) == [(1,6), (8,10), (15,18)]
gaps = find_gaps(intervals, 0, 20)
assert gaps == [(0,1), (6,8), (10,15), (18,20)]
print("merge_intervals: OK")
```

---

### M5. Binary search on answer — find minimum batch size

```python
def min_batch_size_to_process_within_time(
    events_per_day: list,  # events for each day
    max_days: int,         # max days to complete processing
) -> int:
    """
    Find the minimum batch size such that all events can be processed
    within max_days, where each day you can process at most batch_size events.

    DE context: capacity planning — given N days of events and deadline,
    what minimum throughput (events/day) do we need?
    
    Binary search on the answer: O(n log(sum)) where n = len(events_per_day)
    """

    def can_finish(batch_size: int) -> bool:
        """Can we process all events within max_days using batch_size per day?"""
        days_needed = 0
        for events in events_per_day:
            import math
            days_needed += math.ceil(events / batch_size)
        return days_needed <= max_days

    # Binary search: find minimum batch_size that allows completion
    lo, hi = 1, max(events_per_day)  # min=1, max=largest single day

    while lo < hi:
        mid = (lo + hi) // 2
        if can_finish(mid):
            hi = mid       # can finish → try smaller batch
        else:
            lo = mid + 1   # can't finish → need larger batch

    return lo

# Time: O(n log max_val) | Space: O(1)

# Example: [30M, 11M, 23M, 4M, 20M] events over 5 days,
# must complete in 8 days total — what's min daily capacity?
events = [30_000_000, 11_000_000, 23_000_000, 4_000_000, 20_000_000]
result = min_batch_size_to_process_within_time(events, 8)
print(f"Min batch size: {result:,}")  # should be 15M
```

---

### M6. Graph BFS/DFS — pipeline dependency resolution

```python
from collections import defaultdict, deque

class PipelineDAG:
    """
    Represent pipeline dependencies as a DAG.
    Operations: detect cycles, topological sort, find all upstream deps.
    DE context: Airflow DAG validation, DBT dependency resolution.
    """

    def __init__(self):
        self.graph = defaultdict(list)      # node → [children]
        self.reverse = defaultdict(list)    # node → [parents]

    def add_dependency(self, task: str, depends_on: str):
        """task depends on depends_on."""
        self.graph[depends_on].append(task)
        self.reverse[task].append(depends_on)

    def has_cycle(self) -> bool:
        """Detect cycle using DFS with coloring."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = defaultdict(int)

        def dfs(node) -> bool:
            color[node] = GRAY
            for neighbor in self.graph[node]:
                if color[neighbor] == GRAY:
                    return True   # back edge = cycle
                if color[neighbor] == WHITE and dfs(neighbor):
                    return True
            color[node] = BLACK
            return False

        return any(dfs(n) for n in self.graph if color[n] == WHITE)

    def topological_sort(self) -> list:
        """
        Kahn's algorithm: BFS-based topological sort.
        Returns execution order (upstream tasks first).
        """
        in_degree = defaultdict(int)
        all_nodes = set(self.graph.keys()) | set(self.reverse.keys())

        for node in all_nodes:
            for child in self.graph[node]:
                in_degree[child] += 1

        # Start with nodes that have no dependencies
        queue = deque([n for n in all_nodes if in_degree[n] == 0])
        order = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for child in self.graph[node]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(order) != len(all_nodes):
            raise ValueError("Cycle detected in DAG!")

        return order

    def all_upstream(self, task: str) -> set:
        """BFS to find all transitive upstream dependencies."""
        visited = set()
        queue = deque(self.reverse[task])

        while queue:
            node = queue.popleft()
            if node not in visited:
                visited.add(node)
                queue.extend(self.reverse[node])

        return visited

# Test
dag = PipelineDAG()
dag.add_dependency("stg_clicks", "raw_clicks")
dag.add_dependency("stg_campaigns", "raw_campaigns")
dag.add_dependency("int_attributed", "stg_clicks")
dag.add_dependency("int_attributed", "stg_campaigns")
dag.add_dependency("mart_roas", "int_attributed")

assert not dag.has_cycle()
order = dag.topological_sort()
print(f"Execution order: {order}")
assert order.index("raw_clicks") < order.index("stg_clicks")
assert order.index("stg_clicks") < order.index("mart_roas")

upstream = dag.all_upstream("mart_roas")
assert "raw_clicks" in upstream
assert "stg_campaigns" in upstream
print("DAG: OK")
```

---

## SECTION 3: HARD

---

### H1. Design a streaming word count (simulated)

```python
from collections import defaultdict
from typing import Iterator

class StreamingWordCount:
    """
    Count word (or event type) frequencies in a sliding window.
    DE context: real-time event frequency tracking without storing all events.
    Uses a circular buffer approach.
    """

    def __init__(self, window_size_seconds: int, bucket_size_seconds: int = 1):
        self.window_size = window_size_seconds
        self.bucket_size = bucket_size_seconds
        self.n_buckets = window_size_seconds // bucket_size_seconds
        self.buckets = [defaultdict(int) for _ in range(self.n_buckets)]
        self.bucket_timestamps = [0] * self.n_buckets
        self.current_time = 0

    def _get_bucket_idx(self, timestamp: int) -> int:
        return (timestamp // self.bucket_size) % self.n_buckets

    def record_event(self, event_type: str, timestamp: int):
        idx = self._get_bucket_idx(timestamp)

        # If bucket is from a different window: reset it
        if self.bucket_timestamps[idx] != timestamp // self.bucket_size:
            self.buckets[idx].clear()
            self.bucket_timestamps[idx] = timestamp // self.bucket_size

        self.buckets[idx][event_type] += 1
        self.current_time = max(self.current_time, timestamp)

    def get_count(self, event_type: str) -> int:
        """Return count of event_type in the last window_size seconds."""
        cutoff = self.current_time - self.window_size
        total = 0

        for i, bucket in enumerate(self.buckets):
            bucket_ts = self.bucket_timestamps[i] * self.bucket_size
            if bucket_ts > cutoff:
                total += bucket.get(event_type, 0)

        return total

# Test
counter = StreamingWordCount(window_size_seconds=10, bucket_size_seconds=1)
for t in range(5):
    counter.record_event("click", t)      # 5 clicks at t=0..4
counter.record_event("click", 15)         # click at t=15 (outside 10s window)

# At current_time=15, window is (5,15) — only the t=15 click is in window
assert counter.get_count("click") == 1
print("StreamingWordCount: OK")
```

---

### H2. Serialize / Deserialize a pipeline configuration tree

```python
import json
from typing import Optional

class PipelineNode:
    def __init__(self, name: str, task_type: str, children=None):
        self.name = name
        self.task_type = task_type
        self.children = children or []

def serialize(root: Optional[PipelineNode]) -> str:
    """
    Serialize a pipeline tree to JSON string.
    DE context: save/restore pipeline configurations,
    serialize DAG structures for storage or network transfer.
    """
    def node_to_dict(node):
        if not node:
            return None
        return {
            'name': node.name,
            'task_type': node.task_type,
            'children': [node_to_dict(c) for c in node.children]
        }
    return json.dumps(node_to_dict(root))

def deserialize(data: str) -> Optional[PipelineNode]:
    def dict_to_node(d):
        if not d:
            return None
        node = PipelineNode(d['name'], d['task_type'])
        node.children = [dict_to_node(c) for c in d.get('children', [])]
        return node
    return dict_to_node(json.loads(data))

# Test
root = PipelineNode("ingest", "source")
stg = PipelineNode("staging", "transform")
mart = PipelineNode("mart", "aggregate")
stg.children = [mart]
root.children = [stg]

serialized = serialize(root)
restored = deserialize(serialized)
assert restored.name == "ingest"
assert restored.children[0].name == "staging"
assert restored.children[0].children[0].name == "mart"
print("serialize/deserialize: OK")
```

---

### H3. Rate limiter — token bucket algorithm

```python
import time
import threading

class TokenBucketRateLimiter:
    """
    Token bucket rate limiter.
    DE context: rate-limit API calls to Google Ads API, Meta API.
    Allows bursts up to capacity, refills at rate tokens/second.
    """

    def __init__(self, rate: float, capacity: int):
        """
        rate: tokens added per second
        capacity: max tokens (burst capacity)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now

    def acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens. Returns True if acquired, False if rate limited.
        Non-blocking.
        """
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def acquire_blocking(self, tokens: int = 1):
        """Block until tokens are available."""
        while not self.acquire(tokens):
            time.sleep(0.01)

class RateLimitedAPIClient:
    """Wrap API calls with rate limiting."""

    def __init__(self, calls_per_second: int, burst: int = None):
        self.limiter = TokenBucketRateLimiter(
            rate=calls_per_second,
            capacity=burst or calls_per_second * 2
        )

    def call_api(self, endpoint: str, params: dict) -> dict:
        self.limiter.acquire_blocking()
        # actual API call here
        return {"status": "ok", "endpoint": endpoint}

# Test
limiter = TokenBucketRateLimiter(rate=10, capacity=10)
results = []
for _ in range(15):
    results.append(limiter.acquire())
# First 10 succeed, next 5 fail (tokens exhausted without refill)
assert sum(results[:10]) == 10
assert sum(results[10:]) == 0
print("RateLimiter: OK")

# Usage:
api_client = RateLimitedAPIClient(calls_per_second=100, burst=200)
```

---

### H4. Implement a simple in-memory event store (append-only log)

```python
import threading
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class Event:
    event_id: str
    event_type: str
    payload: dict
    timestamp: datetime = field(default_factory=datetime.utcnow)
    offset: int = 0

class EventStore:
    """
    Append-only in-memory event store with consumer offset tracking.
    DE context: simplified version of Kafka topic / Pub/Sub subscription.
    Supports: publish, subscribe, seek to offset, replay from any point.
    """

    def __init__(self, max_events: int = 100_000):
        self._events: List[Event] = []
        self._consumer_offsets: dict = {}
        self._lock = threading.RLock()
        self._max_events = max_events

    def publish(self, event_type: str, payload: dict) -> Event:
        """Append event to the log. Returns the event with its offset."""
        with self._lock:
            if len(self._events) >= self._max_events:
                raise OverflowError("Event store is full")

            event = Event(
                event_id=f"evt_{len(self._events):08d}",
                event_type=event_type,
                payload=payload,
                offset=len(self._events)
            )
            self._events.append(event)
            return event

    def subscribe(self, consumer_id: str, from_beginning: bool = False) -> None:
        """Register a consumer. Defaults to reading from the end (new events only)."""
        with self._lock:
            if consumer_id not in self._consumer_offsets or from_beginning:
                self._consumer_offsets[consumer_id] = 0 if from_beginning else len(self._events)

    def poll(self, consumer_id: str, max_events: int = 100) -> List[Event]:
        """Read next batch of events for consumer. Advances consumer offset."""
        with self._lock:
            if consumer_id not in self._consumer_offsets:
                raise ValueError(f"Consumer {consumer_id} not subscribed")

            offset = self._consumer_offsets[consumer_id]
            batch = self._events[offset: offset + max_events]
            self._consumer_offsets[consumer_id] = offset + len(batch)
            return batch

    def seek(self, consumer_id: str, offset: int) -> None:
        """Seek to a specific offset (for replay)."""
        with self._lock:
            if offset < 0 or offset > len(self._events):
                raise ValueError(f"Invalid offset {offset}")
            self._consumer_offsets[consumer_id] = offset

    def get_lag(self, consumer_id: str) -> int:
        """How many events the consumer is behind."""
        with self._lock:
            offset = self._consumer_offsets.get(consumer_id, 0)
            return len(self._events) - offset

# Test
store = EventStore()

# Publish events
for i in range(10):
    store.publish("click", {"campaign_id": f"C{i}", "cost": i * 0.5})

# Subscribe consumer
store.subscribe("analytics", from_beginning=True)

# Poll in batches
batch1 = store.poll("analytics", max_events=5)
assert len(batch1) == 5
assert batch1[0].offset == 0

batch2 = store.poll("analytics", max_events=5)
assert len(batch2) == 5
assert batch2[0].offset == 5

# Lag should be 0 now
assert store.get_lag("analytics") == 0

# Replay from beginning
store.seek("analytics", 0)
assert store.get_lag("analytics") == 10
print("EventStore: OK")
```

---

## SECTION 4: PYTHON PERFORMANCE & BEST PRACTICES

---

### P1. Generator vs List — memory-efficient data processing

```python
# BAD: loads everything into memory
def process_all_clicks_bad(filename: str) -> list:
    with open(filename) as f:
        return [parse_click(line) for line in f.readlines()]
    # If file is 10GB: 10GB in memory!

# GOOD: generator — lazy evaluation
def process_clicks_streaming(filename: str):
    """Yields one click at a time — O(1) memory."""
    with open(filename) as f:
        for line in f:
            yield parse_click(line.strip())

# Usage:
total_spend = sum(
    click['cost_usd']
    for click in process_clicks_streaming("clicks.jsonl")
    if click['campaign_id'] == "C001"
)
# Never more than one click in memory at a time

# Generator pipeline:
def read_file(path):
    with open(path) as f:
        for line in f:
            yield line.strip()

def parse_json(lines):
    import json
    for line in lines:
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue  # skip malformed

def filter_active(records):
    for r in records:
        if r.get('status') == 'active':
            yield r

# Compose pipeline without ever loading all data
pipeline = filter_active(parse_json(read_file("events.jsonl")))
for record in pipeline:
    process(record)
```

---

### P2. Context manager — safe resource handling

```python
from contextlib import contextmanager
from google.cloud import bigquery

@contextmanager
def bq_transaction(project_id: str):
    """
    Context manager for BigQuery operations with cleanup.
    Ensures temp tables are deleted even on failure.
    """
    client = bigquery.Client(project=project_id)
    temp_tables = []

    try:
        yield client, temp_tables
    except Exception as e:
        print(f"Error in BQ transaction: {e}")
        raise
    finally:
        # Always cleanup temp tables
        for table_id in temp_tables:
            try:
                client.delete_table(table_id, not_found_ok=True)
                print(f"Cleaned up temp table: {table_id}")
            except Exception as cleanup_err:
                print(f"Failed to cleanup {table_id}: {cleanup_err}")

# Usage:
with bq_transaction("costco-project") as (bq, temps):
    # Create staging table
    staging = "costco-project.temp.staging_clicks_20240115"
    temps.append(staging)   # register for cleanup

    bq.load_table_from_json(data, staging).result()
    bq.query(f"MERGE INTO target USING `{staging}` ...").result()
    # If error here: staging table still gets cleaned up
```

---

### P3. Decorator — retry with exponential backoff

```python
import time
import functools
import logging
from typing import Type

logger = logging.getLogger(__name__)

def retry(
    max_attempts: int = 3,
    exceptions: tuple = (Exception,),
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0
):
    """
    Decorator for retrying functions with exponential backoff + jitter.
    DE context: retry API calls, BigQuery jobs, GCS operations.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}: {e}")
                        raise

                    delay = min(
                        max_delay,
                        base_delay * (exponential_base ** (attempt - 1))
                    )
                    # Add jitter: ±10% randomness to prevent thundering herd
                    import random
                    jitter = delay * 0.1 * (random.random() * 2 - 1)
                    actual_delay = delay + jitter

                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {actual_delay:.1f}s"
                    )
                    time.sleep(actual_delay)

            raise last_exception

        return wrapper
    return decorator

# Usage:
@retry(max_attempts=5, exceptions=(ConnectionError, TimeoutError), base_delay=2.0)
def fetch_google_ads_report(campaign_id: str, date: str) -> dict:
    """Fetch campaign report from Google Ads API."""
    # API call that might fail transiently
    response = google_ads_client.get_report(campaign_id, date)
    return response.to_dict()

@retry(max_attempts=3, exceptions=(Exception,), base_delay=1.0)
def write_to_bigquery(rows: list, table_id: str):
    bq_client.insert_rows_json(table_id, rows)
```

---

### P4. Dataclass — clean pipeline configuration

```python
from dataclasses import dataclass, field
from typing import List, Optional
import yaml

@dataclass
class QualityCheck:
    column: str
    rule: str           # "not_null", "unique", "range_0_1"
    severity: str = "ERROR"
    threshold: float = 0.0

@dataclass
class PipelineConfig:
    name: str
    source_path: str
    destination_table: str
    partition_column: str
    cluster_columns: List[str]
    quality_checks: List[QualityCheck] = field(default_factory=list)
    lookback_days: int = 3
    enabled: bool = True

    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'PipelineConfig':
        with open(yaml_path) as f:
            raw = yaml.safe_load(f)

        checks = [
            QualityCheck(**check)
            for check in raw.pop('quality_checks', [])
        ]
        return cls(**raw, quality_checks=checks)

    def validate(self):
        """Validate configuration before pipeline runs."""
        assert self.name, "Pipeline name is required"
        assert self.source_path.startswith("gs://"), "Source must be GCS path"
        assert self.lookback_days > 0, "lookback_days must be positive"

        for check in self.quality_checks:
            valid_rules = {"not_null", "unique", "range_0_1", "positive"}
            assert check.rule in valid_rules, f"Unknown rule: {check.rule}"

# Test
config = PipelineConfig(
    name="ad_clicks_daily",
    source_path="gs://costco-data/raw/ad_clicks/",
    destination_table="costco-project.marts.ad_clicks",
    partition_column="click_date",
    cluster_columns=["campaign_id", "channel"],
    quality_checks=[
        QualityCheck(column="click_id", rule="not_null", severity="ERROR"),
        QualityCheck(column="cost_usd", rule="positive", threshold=0.0)
    ],
    lookback_days=3
)

config.validate()
print(f"Config loaded: {config.name}")
print(f"Quality checks: {len(config.quality_checks)}")
```

---

## QUICK REFERENCE: Python for DE

```python
# Collections
from collections import Counter, defaultdict, deque, OrderedDict

# Counter
Counter(['a','b','a','c','a'])  # Counter({'a': 3, 'b': 1, 'c': 1})
counter.most_common(3)          # top 3
counter.update(['a', 'd'])      # add more counts

# defaultdict
dd = defaultdict(list)
dd['key'].append(1)             # no KeyError
dd = defaultdict(lambda: {'count': 0, 'sum': 0.0})

# deque: O(1) append/pop from both ends (vs list O(n) for left operations)
dq = deque(maxlen=7)            # auto-evicts oldest when full (sliding window)
dq.appendleft(x)                # O(1) vs list.insert(0, x) = O(n)

# Comprehensions
{k: v for k, v in items if v > 0}          # dict comprehension with filter
[f(x) for x in data if condition(x)]       # list comprehension
{x for x in data}                           # set comprehension
(f(x) for x in data)                        # generator (lazy)

# Itertools
from itertools import groupby, chain, islice, combinations, product
[(k, list(g)) for k, g in groupby(sorted_data, key=lambda x: x['date'])]
chain(list1, list2, list3)      # combine iterables without copy
islice(iterator, 100)           # take first 100 from any iterable

# Functional
from functools import reduce, partial, lru_cache
reduce(lambda acc, x: acc + x, [1,2,3,4,5])   # fold left
double = partial(pow, 2)                        # partial application
@lru_cache(maxsize=1024)                        # memoize expensive functions

# Sorting
sorted(data, key=lambda x: (x['date'], -x['spend']))  # multi-key, mixed order
data.sort(key=lambda x: x['timestamp'])               # in-place

# Context managers
with open(path) as f, open(out) as g:  # multiple context managers
    ...
```
