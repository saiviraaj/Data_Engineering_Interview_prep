# Topic 5: Python for Data Engineering — Complete Interview Textbook
## Costco Sr. Data Engineer Prep

---

## TABLE OF CONTENTS

1. [Python Data Structures — Deep Dive](#1-python-data-structures)
2. [Comprehensions & Functional Programming](#2-comprehensions-and-functional)
3. [File & I/O Handling — All Formats](#3-file-and-io-handling)
4. [REST APIs & HTTP Ingestion](#4-rest-apis-and-http)
5. [Data Wrangling with Pandas](#5-pandas-deep-dive)
6. [Data Cleaning with Pandas](#6-data-cleaning-pandas)
7. [Pandas — Advanced Transformations & Metrics](#7-pandas-advanced-transformations)
8. [Working with Dates and Times](#8-dates-and-times)
9. [Regular Expressions for Data Extraction](#9-regular-expressions)
10. [Logging, Error Handling & Retry Logic](#10-logging-and-error-handling)
11. [Configuration-Driven Pipelines](#11-configuration-driven-pipelines)
12. [Concurrency — Multithreading & Multiprocessing](#12-concurrency)
13. [OOP Patterns for Data Engineering](#13-oop-patterns)
14. [Testing Data Pipelines](#14-testing)
15. [GCP SDK in Python](#15-gcp-sdk)
16. [Interview Q&A Bank](#16-interview-qa)

---

## 1. Python Data Structures — Deep Dive

### Lists

```python
# Creation
lst = [1, 2, 3, 4, 5]
lst = list(range(1, 101))       # [1, 2, ..., 100]
lst = [0] * 10                  # [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

# Slicing [start:stop:step]
lst[2:5]      # [3, 4, 5] (index 2 inclusive to 5 exclusive)
lst[:3]       # [1, 2, 3] (first 3)
lst[-3:]      # [3, 4, 5] (last 3)
lst[::2]      # [1, 3, 5, ...] (every other)
lst[::-1]     # Reversed list

# Mutation methods
lst.append(6)           # Add to end
lst.extend([7, 8, 9])   # Add multiple
lst.insert(0, 0)        # Insert at index
lst.remove(5)           # Remove first occurrence of value
lst.pop()               # Remove and return last
lst.pop(2)              # Remove and return at index 2
lst.sort()              # In-place sort
lst.sort(key=lambda x: -x)  # Sort descending
sorted_copy = sorted(lst)    # Returns new sorted list
lst.reverse()           # In-place reverse
lst.index(3)            # Find index of value
lst.count(3)            # Count occurrences

# List as stack (LIFO)
stack = []
stack.append("a")  # push
stack.pop()        # pop

# List as queue (FIFO) — use deque for O(1) operations
from collections import deque
q = deque()
q.append("a")      # enqueue
q.popleft()        # dequeue O(1)
```

### Dictionaries

```python
# Creation
d = {"key": "value", "age": 30}
d = dict(zip(keys_list, values_list))
d = {k: v for k, v in zip(keys, values)}

# Access
d["key"]              # KeyError if missing
d.get("key")          # None if missing
d.get("key", "default")  # Default if missing

# Modification
d["new_key"] = "new_value"
d.update({"k1": "v1", "k2": "v2"})  # Merge dicts
d.setdefault("key", []).append("value")  # Create if not exists

# Iteration
for k in d:               # Keys
for v in d.values():      # Values
for k, v in d.items():    # Key-value pairs

# Dict methods
d.keys()   # dict_keys view
d.values() # dict_values view
d.items()  # dict_items view
d.pop("key")         # Remove and return
d.pop("key", None)   # Safe removal
del d["key"]         # Remove (KeyError if missing)

# Merging (Python 3.9+)
merged = d1 | d2        # New merged dict
d1 |= d2                # In-place merge

# defaultdict — auto-creates default values
from collections import defaultdict
dd = defaultdict(list)
dd["key"].append("value")  # No KeyError — creates empty list

dd = defaultdict(int)
for word in words:
    dd[word] += 1  # Word frequency counter

dd = defaultdict(lambda: {"count": 0, "total": 0})

# Counter
from collections import Counter
c = Counter(["a", "b", "a", "c", "a", "b"])
# Counter({'a': 3, 'b': 2, 'c': 1})
c.most_common(2)    # [('a', 3), ('b', 2)]
c["x"]              # 0 (not KeyError)
c1 + c2             # Combine counts
c1 - c2             # Subtract counts

# OrderedDict (Python 3.7+ regular dicts are ordered, but use for explicit ordering)
from collections import OrderedDict
od = OrderedDict()
od.move_to_end("key")    # Move to end
od.move_to_end("key", last=False)  # Move to beginning
```

### Sets

```python
s = {1, 2, 3, 4, 5}
s = set([1, 2, 2, 3, 3])  # {1, 2, 3} — deduplicates

# Operations
s.add(6)
s.remove(5)    # KeyError if not present
s.discard(5)   # No error if not present

# Set operations
s1 | s2        # Union
s1 & s2        # Intersection
s1 - s2        # Difference (in s1 but not s2)
s1 ^ s2        # Symmetric difference (in either but not both)
s1.issubset(s2)
s1.issuperset(s2)
s1.isdisjoint(s2)  # True if no common elements

# Practical use: deduplication and membership testing
unique_ids = set(id_list)
if user_id in unique_ids:  # O(1) lookup vs O(n) for list
    process()
```

### Tuples & NamedTuples

```python
# Tuple: immutable, hashable, usable as dict key
t = (1, 2, 3)
t = 1, 2, 3    # Packing
a, b, c = t    # Unpacking
a, *rest = t   # Extended unpacking

# namedtuple — lightweight data container
from collections import namedtuple
Event = namedtuple("Event", ["user_id", "event_type", "timestamp", "revenue"])
e = Event(user_id=123, event_type="purchase", timestamp="2024-01-15", revenue=49.99)
e.user_id   # Access by name
e[0]        # Access by index

# Better: Python 3.7+ dataclass
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Event:
    user_id: int
    event_type: str
    timestamp: str
    revenue: float = 0.0
    metadata: dict = field(default_factory=dict)

    def is_purchase(self) -> bool:
        return self.event_type == "purchase"

e = Event(user_id=123, event_type="purchase", timestamp="2024-01-15 10:00:00", revenue=49.99)
```

---

## 2. Comprehensions & Functional Programming

### List, Dict, Set Comprehensions

```python
# List comprehension
squares = [x**2 for x in range(10)]
evens = [x for x in range(100) if x % 2 == 0]
flat = [item for sublist in nested_list for item in sublist]  # Flatten

# Dict comprehension
{k: v for k, v in zip(keys, values)}
{k: v for k, v in d.items() if v > 0}
word_lengths = {word: len(word) for word in words}
inverted = {v: k for k, v in d.items()}

# Set comprehension
unique_domains = {email.split("@")[1] for email in emails if "@" in email}

# Generator expression (lazy — doesn't hold all in memory)
total = sum(x**2 for x in range(1_000_000))  # Memory efficient
gen = (x**2 for x in range(10))              # Generator object
next(gen)                                    # Lazy evaluation

# Conditional expression (ternary)
label = "high" if revenue > 1000 else "low"
```

### map, filter, reduce

```python
from functools import reduce

# map: apply function to each element
doubled = list(map(lambda x: x * 2, numbers))
cleaned = list(map(str.strip, raw_strings))

# filter: keep elements where function returns True
positives = list(filter(lambda x: x > 0, numbers))
non_empty = list(filter(None, strings))  # Filter falsy values

# reduce: fold into single value
total = reduce(lambda acc, x: acc + x, numbers, 0)
product = reduce(lambda acc, x: acc * x, numbers, 1)

# zip: combine iterables
for name, score in zip(names, scores):
    print(f"{name}: {score}")

pairs = list(zip(list1, list2))
dict_from_pairs = dict(zip(keys, values))

# enumerate: index + value
for i, row in enumerate(data_rows, start=1):
    print(f"Row {i}: {row}")

# sorted with key function
sorted_by_revenue = sorted(customers, key=lambda c: c["revenue"], reverse=True)
sorted_by_multi = sorted(data, key=lambda x: (x["region"], -x["revenue"]))

# itertools — powerful combinatorics
from itertools import chain, groupby, product, combinations, islice

# chain: flatten one level
flat = list(chain(*nested_list))
flat = list(chain.from_iterable(nested_list))

# groupby (must be sorted first)
data = sorted(data, key=lambda x: x["category"])
for category, items in groupby(data, key=lambda x: x["category"]):
    items_list = list(items)

# product: cartesian product
combos = list(product(regions, quarters))  # All region-quarter combinations

# islice: lazy slice of iterator
first_1000 = list(islice(large_generator, 1000))
```

### Closures & Higher-Order Functions

```python
# Factory function pattern (used in pipeline config)
def make_transformation(field, multiplier):
    def transform(record):
        record[field] = record.get(field, 0) * multiplier
        return record
    return transform

apply_tax = make_transformation("price", 1.1)

# Decorator pattern (used for timing, retries, logging)
import functools
import time

def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} took {elapsed:.4f}s")
        return result
    return wrapper

@timer
def process_data(df):
    return df.groupby("region").agg({"revenue": "sum"})

# Parametrized decorator
def retry(max_attempts=3, exceptions=(Exception,)):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        raise
                    time.sleep(2 ** attempt)  # Exponential backoff
            return wrapper
    return decorator

@retry(max_attempts=3, exceptions=(ConnectionError, TimeoutError))
def call_api(endpoint):
    response = requests.get(endpoint, timeout=30)
    response.raise_for_status()
    return response.json()
```

---

## 3. File & I/O Handling — All Formats

### CSV

```python
import csv

# Read CSV
with open("data.csv", "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # row is OrderedDict
        process(row["customer_id"], row["amount"])

# Read with custom delimiter
with open("data.tsv", "r") as f:
    reader = csv.DictReader(f, delimiter="\t")
    data = list(reader)

# Write CSV
fieldnames = ["id", "name", "amount"]
with open("output.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in data:
        writer.writerow(row)

# Using Pandas (preferred for large files)
import pandas as pd

df = pd.read_csv(
    "data.csv",
    dtype={"customer_id": str, "amount": float},
    parse_dates=["order_date"],
    usecols=["customer_id", "order_date", "amount"],
    chunksize=None  # Set to int for chunked reading
)

# Chunked reading for large files
for chunk in pd.read_csv("large_file.csv", chunksize=100_000):
    process_chunk(chunk)
    
df.to_csv("output.csv", index=False, encoding="utf-8")
```

### JSON & JSONL

```python
import json

# Read JSON file
with open("data.json", "r") as f:
    data = json.load(f)

# Write JSON file
with open("output.json", "w") as f:
    json.dump(data, f, indent=2, default=str)  # default=str handles dates

# JSON strings
json_str = json.dumps({"key": "value"}, indent=2)
obj = json.loads(json_str)

# JSONL (JSON Lines — one JSON object per line, great for streaming)
# Read JSONL
records = []
with open("events.jsonl", "r") as f:
    for line in f:
        line = line.strip()
        if line:  # Skip empty lines
            records.append(json.loads(line))

# Write JSONL
with open("output.jsonl", "w") as f:
    for record in records:
        f.write(json.dumps(record) + "\n")

# Streaming JSONL (memory efficient)
def process_jsonl(filepath):
    with open(filepath, "r") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

for event in process_jsonl("events.jsonl"):
    process_event(event)

# Handle nested JSON safely
def safe_get(d, *keys, default=None):
    """Safely navigate nested dict."""
    current = d
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        elif isinstance(current, list) and isinstance(key, int):
            current = current[key] if key < len(current) else default
        else:
            return default
    return current

revenue = safe_get(event, "transaction", "payment", "amount", default=0.0)
```

### Parquet & Arrow

```python
import pyarrow as pa
import pyarrow.parquet as pq

# Read Parquet
table = pq.read_table("data.parquet")
df = table.to_pandas()

# Read with column selection (pushdown)
table = pq.read_table("data.parquet", columns=["id", "amount", "date"])

# Read with filter pushdown (row groups)
import pyarrow.compute as pc
filters = [("date", ">=", "2024-01-01"), ("amount", ">", 0)]
table = pq.read_table("data.parquet", filters=filters)

# Write Parquet
df = pd.DataFrame({"id": [1, 2, 3], "amount": [10.5, 20.3, 15.0]})
pq.write_table(pa.Table.from_pandas(df), "output.parquet", compression="snappy")

# Pandas to/from Parquet
df.to_parquet("output.parquet", engine="pyarrow", compression="snappy", index=False)
df = pd.read_parquet("data.parquet", engine="pyarrow")

# GCS Parquet reading with fsspec
import gcsfs
fs = gcsfs.GCSFileSystem(project="my-project")
with fs.open("gs://bucket/data.parquet", "rb") as f:
    df = pd.read_parquet(f)
```

### GCS File Operations

```python
from google.cloud import storage

def upload_file(bucket_name, source_path, destination_blob):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob)
    blob.upload_from_filename(source_path)
    print(f"Uploaded {source_path} to gs://{bucket_name}/{destination_blob}")

def download_file(bucket_name, blob_name, dest_path):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(dest_path)

def list_blobs(bucket_name, prefix="", suffix=""):
    client = storage.Client()
    blobs = client.list_blobs(bucket_name, prefix=prefix)
    return [b.name for b in blobs if b.name.endswith(suffix)]

def read_gcs_json(bucket_name, blob_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    content = blob.download_as_text()
    return json.loads(content)

def write_gcs_json(bucket_name, blob_name, data):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(json.dumps(data, default=str), content_type="application/json")

# Stream large files from GCS
def stream_gcs_csv(bucket_name, blob_name, chunksize=100_000):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    with blob.open("rt") as f:
        for chunk in pd.read_csv(f, chunksize=chunksize):
            yield chunk
```

---

## 4. REST APIs & HTTP Ingestion

### requests Library — Complete Patterns

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time

# Session with retry logic (production pattern)
def create_session(max_retries=3, backoff_factor=0.3):
    session = requests.Session()
    retry = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

session = create_session()

# GET request with pagination
def fetch_paginated_api(base_url, headers, params, page_size=1000):
    all_records = []
    page = 1

    while True:
        params_with_page = {**params, "page": page, "per_page": page_size}
        response = session.get(
            base_url,
            headers=headers,
            params=params_with_page,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        records = data.get("results", data.get("data", []))

        if not records:
            break

        all_records.extend(records)
        page += 1

        # Check for "next" URL pattern
        if not data.get("next"):
            break

        # Rate limiting
        time.sleep(0.1)

    return all_records

# POST with JSON body
def call_api_post(endpoint, payload, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    response = session.post(
        endpoint,
        headers=headers,
        json=payload,
        timeout=60
    )
    response.raise_for_status()
    return response.json()

# Handle rate limiting (429 with Retry-After header)
def fetch_with_rate_limit(url, headers):
    while True:
        response = session.get(url, headers=headers, timeout=30)

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "60"))
            print(f"Rate limited. Sleeping {retry_after}s")
            time.sleep(retry_after)
            continue

        response.raise_for_status()
        return response.json()

# Stream large API response
def stream_large_response(url, output_path):
    with session.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
```

### Calling AdTech/MarTech APIs (Google Ads, Meta Ads)

```python
# Google Ads API pattern
from google.ads.googleads.client import GoogleAdsClient

def fetch_google_ads_performance(customer_id, start_date, end_date):
    client = GoogleAdsClient.load_from_env()
    ga_service = client.get_service("GoogleAdsService")

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversion_value,
            segments.date
        FROM campaign
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
    """

    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    records = []
    for batch in stream:
        for row in batch.results:
            records.append({
                "campaign_id": row.campaign.id,
                "campaign_name": row.campaign.name,
                "date": row.segments.date,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "spend": row.metrics.cost_micros / 1_000_000,  # Micros to dollars
                "conversions": row.metrics.conversions,
                "revenue": row.metrics.conversion_value
            })
    return pd.DataFrame(records)

# Generic API response to DataFrame
def api_to_dataframe(endpoint, headers, params, records_key="data", dtype_map=None):
    """Fetch API data, normalize, return cleaned DataFrame."""
    records = fetch_paginated_api(endpoint, headers, params)
    df = pd.json_normalize(records)  # Flatten nested JSON

    if dtype_map:
        for col, dtype in dtype_map.items():
            if col in df.columns:
                df[col] = df[col].astype(dtype)

    return df
```

---

## 5. Pandas Deep Dive

### DataFrame Creation & Inspection

```python
import pandas as pd
import numpy as np

# Creation patterns
df = pd.DataFrame({
    "id": [1, 2, 3],
    "name": ["Alice", "Bob", "Charlie"],
    "revenue": [100.0, 200.0, 150.0]
})

df = pd.read_csv("data.csv", dtype={"id": str})
df = pd.read_json("data.json", orient="records")
df = pd.read_parquet("data.parquet")
df = pd.DataFrame(records)  # From list of dicts

# Inspection
df.shape          # (rows, cols)
df.dtypes         # Column types
df.info()         # Memory usage, dtypes, non-nulls
df.describe()     # Stats
df.head(10)       # First 10 rows
df.sample(5)      # Random 5 rows
df.value_counts() # Value frequency (for Series)
df["col"].nunique() # Unique count
df.isnull().sum()   # Null count per column

# Column access
df["col"]         # Returns Series
df[["col1", "col2"]]  # Returns DataFrame
df.col            # Attribute access (works if valid Python name)

# Filtering
df[df["amount"] > 100]
df[(df["status"] == "active") & (df["age"] > 25)]
df[df["country"].isin(["US", "CA"])]
df[~df["is_deleted"]]  # NOT
df[df["email"].str.contains("@costco.com", na=False)]
df[df["amount"].between(100, 500)]
```

### Indexing — loc vs iloc

```python
# loc: label-based (uses index labels and column names)
df.loc[0]             # Row with label 0
df.loc[0:2]           # Rows with labels 0, 1, 2 (INCLUSIVE)
df.loc[:, "name"]     # Column "name"
df.loc[df["age"] > 25, ["name", "email"]]  # Conditional selection

# iloc: position-based (pure integer positions)
df.iloc[0]            # First row
df.iloc[0:2]          # Rows 0, 1 (exclusive end like Python slicing)
df.iloc[:, 1]         # Second column
df.iloc[[0, 2, 4]]    # Rows at positions 0, 2, 4

# Setting values
df.loc[0, "status"] = "active"
df.loc[df["age"] > 65, "tier"] = "senior"

# at / iat: single value access (faster)
df.at[0, "name"]      # Single value by label
df.iat[0, 1]          # Single value by position
```

---

## 6. Data Cleaning with Pandas

### Handling Missing Data

```python
# Detect
df.isnull()           # Boolean DataFrame
df.isnull().sum()     # Missing count per column
df.isnull().mean()    # Missing fraction per column
df.isnull().sum().sort_values(ascending=False)  # Sorted by most missing

# Drop
df.dropna()                             # Drop rows with any null
df.dropna(how="all")                    # Drop rows where ALL values null
df.dropna(subset=["email", "name"])     # Drop if specific columns null
df.dropna(thresh=5)                     # Keep rows with ≥5 non-null values
df.dropna(axis=1)                       # Drop columns with any null

# Fill
df.fillna(0)                            # Fill all nulls with 0
df.fillna(method="ffill")               # Forward fill (propagate last valid)
df.fillna(method="bfill")               # Backward fill
df["col"].fillna(df["col"].mean())      # Fill with column mean
df["col"].fillna(df["col"].median())    # Fill with median
df.fillna({"age": 0, "name": "unknown", "status": "active"})  # Per-column

# Replace specific values with NaN
df.replace({"N/A": np.nan, "NULL": np.nan, "": np.nan})
df["col"].replace(0, np.nan)

# Interpolate (for time series)
df["price"].interpolate(method="linear")
df["price"].interpolate(method="time")  # Uses datetime index
```

### Deduplication

```python
# Drop exact duplicates
df.drop_duplicates()
df.drop_duplicates(subset=["email"])            # Key-based
df.drop_duplicates(subset=["customer_id", "order_date"])  # Multi-key
df.drop_duplicates(keep="first")                # Keep first (default)
df.drop_duplicates(keep="last")                 # Keep last
df.drop_duplicates(keep=False)                  # Drop all duplicates

# View duplicates
df[df.duplicated(subset=["email"])]
df[df.duplicated(subset=["email"], keep=False)]  # All copies
df.duplicated(subset=["email"]).sum()            # Count of duplicates
```

### Type Conversion & Standardization

```python
# Convert types
df["amount"] = df["amount"].astype(float)
df["id"] = df["id"].astype(str)
df["count"] = df["count"].astype(int)
df["is_active"] = df["is_active"].astype(bool)

# Safe conversion (returns NaN for failed conversions)
df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
df["date"] = pd.to_datetime(df["date_str"], errors="coerce", format="%Y-%m-%d")

# String operations
df["email"] = df["email"].str.lower().str.strip()
df["name"] = df["name"].str.title()
df["phone"] = df["phone"].str.replace(r"[^0-9]", "", regex=True)
df["domain"] = df["email"].str.split("@").str[1]

# Categorical (memory efficient for low-cardinality columns)
df["status"] = df["status"].astype("category")
df["status"].cat.categories  # ['active', 'inactive', 'pending']

# Normalize categorical
status_map = {"A": "active", "I": "inactive", "1": "active", "0": "inactive"}
df["status"] = df["status"].map(status_map).fillna("unknown")

# Using cut/qcut for binning
df["age_group"] = pd.cut(
    df["age"],
    bins=[0, 18, 35, 50, 65, 100],
    labels=["under_18", "18-35", "35-50", "50-65", "65+"]
)

df["revenue_quartile"] = pd.qcut(df["revenue"], q=4, labels=["Q1", "Q2", "Q3", "Q4"])
```

---

## 7. Pandas Advanced Transformations & Metrics

### apply, map, applymap

```python
# apply: applies function to each row or column
df["full_name"] = df.apply(
    lambda row: f"{row['first_name']} {row['last_name']}",
    axis=1  # axis=1 for row-wise
)

# apply with complex logic
def classify_customer(row):
    if row["spend"] >= 10000 and row["recency_days"] < 30:
        return "VIP"
    elif row["spend"] >= 1000:
        return "Regular"
    elif row["recency_days"] > 365:
        return "Churned"
    return "New"

df["segment"] = df.apply(classify_customer, axis=1)

# map: element-wise for Series
df["status_code"] = df["status"].map({"active": 1, "inactive": 0})
df["country_name"] = df["country_code"].map(country_code_dict)

# applymap / map (DataFrame): element-wise for all cells (Pandas 2.1+: map)
df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

# Vectorized operations (MUCH faster than apply — use when possible)
df["total"] = df["price"] * df["qty"]                    # Vectorized
df["revenue_log"] = np.log1p(df["revenue"])
df["is_weekend"] = df["day_of_week"].isin([5, 6])
df["name_upper"] = df["name"].str.upper()               # str accessor — vectorized
```

### GroupBy & Aggregation

```python
# Basic groupby
df.groupby("region")["revenue"].sum()
df.groupby(["region", "channel"])["revenue"].sum().reset_index()

# Multiple aggregations
result = df.groupby("customer_id").agg(
    total_orders=("order_id", "count"),
    total_revenue=("amount", "sum"),
    avg_order_value=("amount", "mean"),
    first_order=("order_date", "min"),
    last_order=("order_date", "max"),
    unique_products=("product_id", "nunique")
).reset_index()

# Named aggregation with lambda
result = df.groupby("region").agg(
    revenue=("amount", "sum"),
    orders=("order_id", "count"),
    cvr=("converted", lambda x: x.mean()),
    p95_value=("order_value", lambda x: x.quantile(0.95))
)

# Transform: apply aggregation and keep original index (for creating group-level columns)
df["region_total"] = df.groupby("region")["revenue"].transform("sum")
df["pct_of_region"] = df["revenue"] / df["region_total"]
df["region_rank"] = df.groupby("region")["revenue"].rank(ascending=False)

# filter: keep groups meeting a condition
high_revenue_regions = df.groupby("region").filter(
    lambda g: g["revenue"].sum() > 100_000
)

# apply on groups (most flexible)
def compute_rfm(group):
    today = pd.Timestamp("today")
    return pd.Series({
        "recency": (today - group["order_date"].max()).days,
        "frequency": group["order_id"].nunique(),
        "monetary": group["amount"].sum()
    })

rfm = df.groupby("customer_id").apply(compute_rfm).reset_index()
```

### Window Functions in Pandas

```python
# Rolling windows
df.sort_values("date", inplace=True)

df["rolling_7d_avg"] = df["revenue"].rolling(window=7, min_periods=1).mean()
df["rolling_30d_sum"] = df["revenue"].rolling(window=30, min_periods=1).sum()
df["rolling_7d_max"] = df["revenue"].rolling(window=7).max()
df["rolling_7d_std"] = df["revenue"].rolling(window=7).std()

# Expanding (cumulative from start)
df["cumulative_revenue"] = df["revenue"].expanding().sum()
df["running_max"] = df["revenue"].expanding().max()

# Shift (lag/lead)
df["prev_day_revenue"] = df["revenue"].shift(1)   # Lag 1
df["next_day_revenue"] = df["revenue"].shift(-1)  # Lead 1
df["mom_change"] = df["revenue"] - df["revenue"].shift(1)
df["mom_pct_change"] = df["revenue"].pct_change()

# Per-group window functions
df["group_cum_revenue"] = df.groupby("customer_id")["revenue"].cumsum()
df["group_rolling_avg"] = df.groupby("customer_id")["revenue"] \
    .transform(lambda x: x.rolling(7, min_periods=1).mean())
df["group_rank"] = df.groupby("region")["revenue"].rank(ascending=False)
df["group_pct_rank"] = df.groupby("region")["revenue"].rank(pct=True)

# Percentile with shift (MoM change with lag per group)
df = df.sort_values(["customer_id", "order_month"])
df["prev_month_spend"] = df.groupby("customer_id")["spend"].shift(1)
df["mom_pct_change"] = (
    (df["spend"] - df["prev_month_spend"]) / df["prev_month_spend"] * 100
)
```

### Pivot Tables & Reshaping

```python
# pivot_table (most powerful)
pivot = pd.pivot_table(
    df,
    values="revenue",
    index="region",
    columns="channel",
    aggfunc="sum",
    fill_value=0,
    margins=True,     # Add totals row/col
    margins_name="Total"
)

# pivot (simple, no aggregation — requires unique values)
pivot = df.pivot(index="date", columns="region", values="revenue")

# melt: wide to long
long_df = pd.melt(
    wide_df,
    id_vars=["customer_id", "date"],
    value_vars=["jan_rev", "feb_rev", "mar_rev"],
    var_name="month",
    value_name="revenue"
)

# stack / unstack (multi-level indexes)
df_stacked = df.set_index(["region", "channel"]).stack()  # Columns → rows
df_unstacked = df_stacked.unstack()                        # Rows → columns
df_unstacked = df_stacked.unstack(level=0)                 # Unstack specific level

# crosstab
pd.crosstab(df["region"], df["channel"])                    # Frequency
pd.crosstab(df["region"], df["channel"], values=df["revenue"], aggfunc="sum")
```

### Merging & Joining DataFrames

```python
# merge (SQL-style joins)
result = pd.merge(left, right, on="customer_id", how="inner")
result = pd.merge(left, right, on="customer_id", how="left")
result = pd.merge(left, right, left_on="cust_id", right_on="customer_id")
result = pd.merge(left, right, on=["customer_id", "order_date"])

# Merge with suffixes for duplicate column names
result = pd.merge(
    left, right, on="id",
    how="outer",
    suffixes=("_left", "_right"),
    indicator=True  # Adds _merge column: left_only, right_only, both
)

# Anti-join pattern
merged = pd.merge(left, right, on="customer_id", how="left", indicator=True)
anti_join = merged[merged["_merge"] == "left_only"].drop("_merge", axis=1)

# concat (vertical stack)
combined = pd.concat([df1, df2, df3], ignore_index=True)
combined = pd.concat([df1, df2], ignore_index=True, sort=False)

# concat horizontal (side by side)
side_by_side = pd.concat([df1, df2], axis=1)

# join (index-based)
result = left.set_index("customer_id").join(
    right.set_index("customer_id"),
    how="left"
)
```

### Building MarTech Metrics in Pandas

```python
import pandas as pd
import numpy as np

def compute_ad_metrics(df_impressions, df_clicks, df_conversions):
    """Compute full ad performance metrics table."""

    # Aggregate each event type
    imp = df_impressions.groupby(["campaign_id", "date"]).agg(
        impressions=("event_id", "count")
    ).reset_index()

    clk = df_clicks.groupby(["campaign_id", "date"]).agg(
        clicks=("event_id", "count")
    ).reset_index()

    conv = df_conversions.groupby(["campaign_id", "date"]).agg(
        conversions=("event_id", "count"),
        revenue=("revenue", "sum"),
        spend=("ad_spend", "sum")
    ).reset_index()

    # Join all
    metrics = imp \
        .merge(clk, on=["campaign_id", "date"], how="left") \
        .merge(conv, on=["campaign_id", "date"], how="left") \
        .fillna({"clicks": 0, "conversions": 0, "revenue": 0.0, "spend": 0.0})

    # Compute derived metrics
    metrics["ctr"] = metrics["clicks"] / metrics["impressions"].replace(0, np.nan)
    metrics["cvr"] = metrics["conversions"] / metrics["clicks"].replace(0, np.nan)
    metrics["cpm"] = metrics["spend"] / metrics["impressions"].replace(0, np.nan) * 1000
    metrics["cpc"] = metrics["spend"] / metrics["clicks"].replace(0, np.nan)
    metrics["cpa"] = metrics["spend"] / metrics["conversions"].replace(0, np.nan)
    metrics["roas"] = metrics["revenue"] / metrics["spend"].replace(0, np.nan)

    # Rolling 7-day metrics per campaign
    metrics = metrics.sort_values(["campaign_id", "date"])
    metrics["rolling_7d_roas"] = metrics.groupby("campaign_id")["roas"] \
        .transform(lambda x: x.rolling(7, min_periods=1).mean())

    return metrics.round(4)


def compute_rfm_segments(df_orders, analysis_date=None):
    """Full RFM segmentation pipeline."""
    if analysis_date is None:
        analysis_date = pd.Timestamp.today()

    rfm = df_orders.groupby("customer_id").agg(
        recency=("order_date", lambda x: (analysis_date - x.max()).days),
        frequency=("order_id", "nunique"),
        monetary=("amount", "sum")
    ).reset_index()

    # Quartile scoring
    rfm["r_score"] = pd.qcut(rfm["recency"].rank(method="first"), 5,
                              labels=[5, 4, 3, 2, 1])  # Lower recency = higher score
    rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 5,
                              labels=[1, 2, 3, 4, 5])
    rfm["m_score"] = pd.qcut(rfm["monetary"].rank(method="first"), 5,
                              labels=[1, 2, 3, 4, 5])

    rfm["rfm_score"] = (rfm["r_score"].astype(int)
                       + rfm["f_score"].astype(int)
                       + rfm["m_score"].astype(int))

    def segment(row):
        r, f, m = int(row["r_score"]), int(row["f_score"]), int(row["m_score"])
        if r >= 4 and f >= 4 and m >= 4: return "Champions"
        if r >= 3 and f >= 3: return "Loyal"
        if r >= 4 and f <= 2: return "Recent"
        if r <= 2 and f >= 3: return "At Risk"
        if r <= 2 and f <= 2: return "Lost"
        return "Potential"

    rfm["segment"] = rfm.apply(segment, axis=1)
    return rfm
```

---

## 8. Dates and Times

### Core datetime Operations

```python
from datetime import datetime, date, timedelta, timezone
import pandas as pd
from dateutil.relativedelta import relativedelta

# Creating dates
today = date.today()
now = datetime.now()
utc_now = datetime.now(timezone.utc)

d = date(2024, 1, 15)
dt = datetime(2024, 1, 15, 10, 30, 0)
dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

# Parsing from strings
dt = datetime.strptime("2024-01-15 10:30:00", "%Y-%m-%d %H:%M:%S")
dt = datetime.fromisoformat("2024-01-15T10:30:00")  # Python 3.7+

# Formatting
dt.strftime("%Y-%m-%d")         # "2024-01-15"
dt.strftime("%B %d, %Y")        # "January 15, 2024"
dt.strftime("%Y%m%d_%H%M%S")    # "20240115_103000"
dt.isoformat()                   # "2024-01-15T10:30:00"

# Arithmetic
tomorrow = today + timedelta(days=1)
last_week = today - timedelta(weeks=1)
last_month = today - relativedelta(months=1)
next_quarter = today + relativedelta(months=3)

# Difference
delta = datetime(2024, 12, 31) - datetime(2024, 1, 1)
days = delta.days               # 365
total_seconds = delta.total_seconds()

# Date components
dt.year, dt.month, dt.day
dt.hour, dt.minute, dt.second
dt.weekday()  # 0=Monday, 6=Sunday
dt.isoweekday()  # 1=Monday, 7=Sunday

# Truncate to period
from datetime import datetime
def truncate_to_month(dt):
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

def truncate_to_week(dt):
    return dt - timedelta(days=dt.weekday())
```

### Pandas DateTime

```python
# Parse
df["order_date"] = pd.to_datetime(df["date_str"], format="%Y-%m-%d", errors="coerce")
df["order_date"] = pd.to_datetime(df["date_str"])  # Auto-detect (slower)

# DatetimeIndex operations
df = df.set_index("order_date")
df["2024"]              # All of 2024
df["2024-01"]           # January 2024
df["2024-01-01":"2024-03-31"]  # Date range

# dt accessor
df["year"] = df["order_date"].dt.year
df["month"] = df["order_date"].dt.month
df["day"] = df["order_date"].dt.day
df["weekday"] = df["order_date"].dt.weekday       # 0=Mon
df["day_name"] = df["order_date"].dt.day_name()
df["quarter"] = df["order_date"].dt.quarter
df["week"] = df["order_date"].dt.isocalendar().week
df["is_weekend"] = df["order_date"].dt.weekday >= 5

# Period operations
df["month_period"] = df["order_date"].dt.to_period("M")  # 2024-01
df["week_period"] = df["order_date"].dt.to_period("W")
df["month_start"] = df["order_date"].dt.to_period("M").dt.to_timestamp()

# Timezone
df["utc_ts"] = df["ts"].dt.tz_localize("UTC")
df["local_ts"] = df["utc_ts"].dt.tz_convert("America/Los_Angeles")
df["local_date"] = df["local_ts"].dt.date

# Date spine (generate date range)
date_spine = pd.DataFrame({
    "date": pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")
})
df_filled = date_spine.merge(df_daily, on="date", how="left").fillna(0)
```

---

## 9. Regular Expressions for Data Extraction

```python
import re

# Core functions
re.match(pattern, string)     # Match at START of string
re.search(pattern, string)    # Match ANYWHERE in string
re.findall(pattern, string)   # All non-overlapping matches (list)
re.finditer(pattern, string)  # Iterator of match objects
re.sub(pattern, repl, string) # Replace matches
re.split(pattern, string)     # Split on pattern

# Patterns for data engineering
# Email
EMAIL = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Phone (US)
PHONE = r'^\+?1?\s?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}$'

# URL
URL = r'https?://[^\s<>"{}|\\^`\[\]]+'

# IP Address
IP = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'

# Date formats
DATE_YMD = r'\d{4}-\d{2}-\d{2}'
DATE_MDY = r'\d{1,2}/\d{1,2}/\d{2,4}'

# Credit card (masked)
CC = r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'

# SKU / Product codes
SKU = r'\b[A-Z]{2,4}\d{4,8}\b'

# UTM parameters
def extract_utm_params(url):
    params = {}
    for param in ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"]:
        match = re.search(rf'[?&]{param}=([^&]+)', url)
        params[param] = match.group(1) if match else None
    return params

# Named groups
pattern = r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'
match = re.search(pattern, "Order date: 2024-01-15")
if match:
    print(match.group("year"), match.group("month"))
    print(match.groupdict())  # {'year': '2024', 'month': '01', 'day': '15'}

# Compile for reuse (performance)
email_re = re.compile(EMAIL)
def is_valid_email(email):
    return bool(email_re.match(email.lower().strip())) if email else False

# Non-greedy matching
# Greedy (default): .*
# Non-greedy: .*?
html = "<b>bold</b> and <i>italic</i>"
re.findall(r'<.*?>', html)  # ['<b>', '</b>', '<i>', '</i>']

# Lookahead / lookbehind
re.findall(r'\d+(?= dollars)', "I have 50 dollars and 30 euros")  # ['50']
re.findall(r'(?<=\$)\d+', "$50 and $30")  # ['50', '30']
```

---

## 10. Logging, Error Handling & Retry Logic

### Production-Grade Logging

```python
import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logger(name, level=logging.INFO, log_file=None):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler with rotation
    if log_file:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# Usage
logger = setup_logger(__name__)
logger.info("Starting pipeline for date: %s", run_date)
logger.warning("Missing values in column: %s — count: %d", col_name, null_count)
logger.error("Failed to load data: %s", str(e), exc_info=True)
logger.debug("Processed %d records in %.2fs", count, elapsed)
```

### Exception Handling

```python
# Custom exceptions
class DataPipelineError(Exception):
    """Base exception for pipeline errors."""
    pass

class DataValidationError(DataPipelineError):
    """Raised when data quality checks fail."""
    def __init__(self, check_name, failing_count, total_count):
        self.check_name = check_name
        self.failing_count = failing_count
        self.total_count = total_count
        super().__init__(
            f"Validation failed: {check_name} — {failing_count}/{total_count} rows invalid"
        )

class DataLoadError(DataPipelineError):
    pass

# Error handling patterns
try:
    df = read_from_bigquery(query)
    validate_schema(df)
    result = transform(df)
    write_output(result)

except DataValidationError as e:
    logger.error("Validation failed: %s", e)
    send_alert(f"Pipeline validation error: {e.check_name}")
    raise  # Re-raise after alerting

except (ConnectionError, TimeoutError) as e:
    logger.error("Network error: %s", e)
    raise DataLoadError(f"Failed to connect: {e}") from e

except Exception as e:
    logger.exception("Unexpected error in pipeline: %s", type(e).__name__)
    raise

finally:
    cleanup_temp_files()
    logger.info("Pipeline cleanup complete")

# Context managers for resource management
class BigQueryJob:
    def __init__(self, client, query):
        self.client = client
        self.query = query
        self.job = None

    def __enter__(self):
        self.job = self.client.query(self.query)
        return self.job

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logger.error("BigQuery job failed: %s — %s", exc_type.__name__, exc_val)
            try:
                self.job.cancel()
            except:
                pass
        return False  # Don't suppress exception

with BigQueryJob(bq_client, query) as job:
    results = job.result()
```

### Retry with Exponential Backoff

```python
import time
import functools
import random
from typing import Type, Tuple

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Exponential backoff decorator with jitter."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_retries - 1:
                        logger.error("Max retries reached for %s: %s", func.__name__, e)
                        raise

                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    if jitter:
                        delay *= (0.5 + random.random())  # Add ±50% jitter

                    logger.warning(
                        "Attempt %d/%d failed for %s: %s. Retrying in %.1fs",
                        attempt + 1, max_retries, func.__name__, e, delay
                    )
                    time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator

@retry_with_backoff(max_retries=3, retryable_exceptions=(ConnectionError, TimeoutError))
def fetch_api_data(endpoint):
    response = requests.get(endpoint, timeout=30)
    response.raise_for_status()
    return response.json()
```

---

## 11. Configuration-Driven Pipelines

### Config Pattern (used in CDM Next-style platforms)

```python
import json
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# YAML config
config_yaml = """
pipeline:
  name: costco_ad_events_pipeline
  schedule: "0 4 * * *"
  source:
    type: bigquery
    project: costco-prod
    dataset: raw_martech
    table: ad_events
    partition_column: event_date
    lookback_days: 1
  transforms:
    - type: filter
      condition: "amount > 0 AND user_id IS NOT NULL"
    - type: deduplicate
      key: ["event_id"]
      keep: "latest"
      order_col: "processed_at"
    - type: enrich
      lookup_table: dim_members
      join_key: user_id
      columns: ["membership_tier", "signup_date"]
  destination:
    type: bigquery
    project: costco-prod
    dataset: curated
    table: ad_events_enriched
    partition_column: event_date
    write_mode: overwrite_partitions
  quality_checks:
    - column: user_id
      check: not_null
      threshold: 0.99
    - column: amount
      check: positive
      threshold: 1.0
"""

# Load and validate config
@dataclass
class SourceConfig:
    type: str
    project: str
    dataset: str
    table: str
    partition_column: str = None
    lookback_days: int = 1

@dataclass
class PipelineConfig:
    name: str
    schedule: str
    source: SourceConfig
    destination: dict
    transforms: List[dict] = field(default_factory=list)
    quality_checks: List[dict] = field(default_factory=list)

def load_config(config_path: str) -> PipelineConfig:
    with open(config_path) as f:
        raw = yaml.safe_load(f)

    pipeline = raw["pipeline"]
    source = SourceConfig(**pipeline["source"])
    return PipelineConfig(
        name=pipeline["name"],
        schedule=pipeline["schedule"],
        source=source,
        destination=pipeline["destination"],
        transforms=pipeline.get("transforms", []),
        quality_checks=pipeline.get("quality_checks", [])
    )

# Config-driven transformation executor
class TransformExecutor:
    def __init__(self, transforms: List[dict]):
        self.transforms = transforms

    def execute(self, df: pd.DataFrame) -> pd.DataFrame:
        for transform in self.transforms:
            t_type = transform["type"]
            if t_type == "filter":
                df = df.query(transform["condition"])
            elif t_type == "deduplicate":
                df = df.sort_values(transform["order_col"], ascending=False) \
                       .drop_duplicates(subset=transform["key"]) \
                       .reset_index(drop=True)
            elif t_type == "cast":
                for col, dtype in transform["columns"].items():
                    df[col] = pd.to_numeric(df[col], errors="coerce") if "numeric" in dtype else df[col].astype(dtype)
            logger.info("Applied transform: %s", t_type)
        return df
```

---

## 12. Concurrency — Multithreading & Multiprocessing

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Callable

# ThreadPoolExecutor — I/O bound (API calls, file reads)
def fetch_all_campaigns(campaign_ids: List[str], max_workers=10) -> List[dict]:
    results = []
    errors = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {
            executor.submit(fetch_campaign_data, cid): cid
            for cid in campaign_ids
        }

        for future in as_completed(future_to_id):
            campaign_id = future_to_id[future]
            try:
                data = future.result(timeout=60)
                results.append(data)
            except Exception as e:
                logger.error("Failed to fetch campaign %s: %s", campaign_id, e)
                errors.append({"id": campaign_id, "error": str(e)})

    logger.info("Fetched %d/%d campaigns successfully", len(results), len(campaign_ids))
    return results, errors

# ProcessPoolExecutor — CPU bound (transformations, ML scoring)
def transform_partition(partition_data):
    """Runs in separate process — no GIL."""
    return pd.DataFrame(partition_data).pipe(apply_complex_transforms)

def parallel_transform(df: pd.DataFrame, n_partitions=4) -> pd.DataFrame:
    partitions = np.array_split(df, n_partitions)

    with ProcessPoolExecutor(max_workers=n_partitions) as executor:
        results = list(executor.map(transform_partition, [p.to_dict("records") for p in partitions]))

    return pd.concat(results, ignore_index=True)

# Async approach (for high-concurrency API ingestion)
import asyncio
import aiohttp

async def fetch_async(session, url, params):
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
        response.raise_for_status()
        return await response.json()

async def fetch_all_async(urls_params: List[tuple], max_concurrent=20) -> List:
    semaphore = asyncio.Semaphore(max_concurrent)
    results = []

    async def bounded_fetch(session, url, params):
        async with semaphore:
            return await fetch_async(session, url, params)

    async with aiohttp.ClientSession() as session:
        tasks = [bounded_fetch(session, url, params) for url, params in urls_params]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    return [r for r in results if not isinstance(r, Exception)]

# Run async from sync context
results = asyncio.run(fetch_all_async(urls_params))
```

---

## 13. OOP Patterns for Data Engineering

### Base Pipeline Class Pattern

```python
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd

class BasePipeline(ABC):
    """Abstract base class for all data pipelines."""

    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._metrics = {}

    @abstractmethod
    def extract(self) -> pd.DataFrame:
        """Extract data from source."""
        pass

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply business transformations."""
        pass

    @abstractmethod
    def load(self, df: pd.DataFrame) -> None:
        """Load data to destination."""
        pass

    def validate(self, df: pd.DataFrame) -> bool:
        """Override for custom validation."""
        return True

    def run(self) -> dict:
        """Execute full ETL pipeline with instrumentation."""
        start_time = time.time()
        try:
            self.logger.info("Starting pipeline: %s", self.config["name"])

            df = self.extract()
            self._metrics["extract_count"] = len(df)

            if not self.validate(df):
                raise DataValidationError("pre_transform", 0, len(df))

            df = self.transform(df)
            self._metrics["transform_count"] = len(df)

            self.load(df)
            self._metrics["status"] = "success"
            self._metrics["duration_sec"] = round(time.time() - start_time, 2)

        except Exception as e:
            self._metrics["status"] = "failed"
            self._metrics["error"] = str(e)
            self.logger.exception("Pipeline failed: %s", e)
            raise

        finally:
            self.logger.info("Pipeline metrics: %s", self._metrics)

        return self._metrics


class AdEventsPipeline(BasePipeline):
    """Concrete pipeline for ad events."""

    def extract(self) -> pd.DataFrame:
        bq = bigquery.Client()
        query = f"""
            SELECT *
            FROM `{self.config['source_table']}`
            WHERE DATE(event_timestamp) = '{self.config['run_date']}'
        """
        return bq.query(query).to_dataframe()

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return df \
            .dropna(subset=["user_id", "event_timestamp"]) \
            .drop_duplicates(subset=["event_id"]) \
            .assign(
                event_date=lambda x: pd.to_datetime(x["event_timestamp"]).dt.date,
                utm_source=lambda x: x["page_url"].str.extract(r"utm_source=([^&]+)"),
                is_purchase=lambda x: (x["event_type"] == "purchase").astype(int)
            )

    def validate(self, df: pd.DataFrame) -> bool:
        null_rate = df["user_id"].isnull().mean()
        if null_rate > 0.05:
            self.logger.error("Too many null user_ids: %.2f%%", null_rate * 100)
            return False
        return True

    def load(self, df: pd.DataFrame) -> None:
        df.to_gbq(
            self.config["destination_table"],
            project_id=self.config["project"],
            if_exists="replace"
        )
```

---

## 14. Testing Data Pipelines

```python
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

# Unit test for transformation function
def test_clean_events():
    input_data = pd.DataFrame({
        "event_id": ["e1", "e1", "e2", None],  # Duplicate + null
        "user_id": [1, 1, 2, 3],
        "amount": [10.5, 10.5, -5.0, 20.0],
        "event_type": ["purchase", "purchase", "click", "purchase"]
    })

    result = clean_events(input_data)

    # Assertions
    assert len(result) == 3, "Should remove duplicate event_id"
    assert result["event_id"].notna().all(), "Should remove null event_ids"
    assert (result["amount"] >= 0).all(), "Should remove negative amounts"

def test_compute_rfm_segments():
    orders = pd.DataFrame({
        "customer_id": [1, 1, 2, 3],
        "order_id": ["o1", "o2", "o3", "o4"],
        "order_date": pd.to_datetime(["2024-01-01", "2024-01-15", "2023-06-01", "2024-01-10"]),
        "amount": [100.0, 200.0, 50.0, 500.0]
    })

    result = compute_rfm_segments(orders, analysis_date=pd.Timestamp("2024-02-01"))

    assert "r_score" in result.columns
    assert "f_score" in result.columns
    assert "segment" in result.columns
    assert len(result) == 3  # One row per customer
    # Customer 1 should have higher frequency than customers 2 and 3
    c1 = result[result["customer_id"] == 1].iloc[0]
    assert c1["frequency"] == 2

# Parametrized tests
@pytest.mark.parametrize("url,expected_source", [
    ("https://example.com?utm_source=google&utm_medium=cpc", "google"),
    ("https://example.com?page=1", None),
    ("https://example.com?utm_source=", ""),
])
def test_extract_utm_source(url, expected_source):
    result = extract_utm_params(url)
    assert result.get("utm_source") == expected_source

# Mock external dependencies
def test_pipeline_with_mocked_bigquery():
    mock_df = pd.DataFrame({
        "user_id": [1, 2, 3],
        "event_type": ["purchase", "click", "purchase"],
        "revenue": [50.0, 0.0, 100.0]
    })

    with patch("google.cloud.bigquery.Client") as mock_bq:
        mock_bq.return_value.query.return_value.to_dataframe.return_value = mock_df
        pipeline = AdEventsPipeline({"run_date": "2024-01-15"})
        df = pipeline.extract()

    assert len(df) == 3

# Data contract test
def test_output_schema():
    """Ensure output DataFrame has required columns and types."""
    expected_schema = {
        "campaign_id": str,
        "event_date": "datetime64[ns]",
        "impressions": np.int64,
        "clicks": np.int64,
        "revenue": np.float64,
        "ctr": np.float64
    }

    result = run_pipeline_under_test()

    for col, dtype in expected_schema.items():
        assert col in result.columns, f"Missing column: {col}"
        if dtype == str:
            assert result[col].dtype == object
        else:
            assert result[col].dtype == np.dtype(dtype), f"Wrong dtype for {col}"
```

---

## 15. GCP SDK in Python

### BigQuery Client

```python
from google.cloud import bigquery
import pandas as pd

bq = bigquery.Client(project="costco-prod")

# Run query
query = """
    SELECT customer_id, SUM(revenue) AS total
    FROM `costco-prod.analytics.orders`
    WHERE DATE(created_at) = CURRENT_DATE() - 1
    GROUP BY customer_id
"""
df = bq.query(query).to_dataframe()

# Query with job config
job_config = bigquery.QueryJobConfig(
    destination="costco-prod.staging.temp_results",
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    use_query_cache=False,
    labels={"pipeline": "martech", "env": "prod"}
)
job = bq.query(query, job_config=job_config)
job.result()  # Wait for completion

# Load DataFrame to BigQuery
job_config = bigquery.LoadJobConfig(
    schema=[
        bigquery.SchemaField("campaign_id", "STRING"),
        bigquery.SchemaField("date", "DATE"),
        bigquery.SchemaField("impressions", "INTEGER"),
        bigquery.SchemaField("revenue", "FLOAT")
    ],
    write_disposition="WRITE_APPEND",
    time_partitioning=bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="date"
    )
)
table_ref = bq.dataset("analytics").table("campaign_metrics")
job = bq.load_table_from_dataframe(df, table_ref, job_config=job_config)
job.result()

# Table operations
table = bq.get_table("project.dataset.table")
bq.delete_table("project.dataset.table", not_found_ok=True)
bq.copy_table("src.dataset.table", "dest.dataset.table")

# List tables in dataset
dataset = bq.get_dataset("project.dataset")
for table in bq.list_tables(dataset):
    print(table.table_id, table.num_rows, table.num_bytes)
```

### Pub/Sub

```python
from google.cloud import pubsub_v1
import json

# Publisher
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path("project", "topic-name")

def publish_message(data: dict, attributes: dict = None):
    message = json.dumps(data).encode("utf-8")
    future = publisher.publish(
        topic_path,
        data=message,
        **(attributes or {})
    )
    message_id = future.result()
    return message_id

# Subscriber (pull)
subscriber = pubsub_v1.SubscriberClient()
sub_path = subscriber.subscription_path("project", "subscription-name")

def pull_messages(max_messages=10):
    response = subscriber.pull(
        request={"subscription": sub_path, "max_messages": max_messages},
        timeout=30
    )
    ack_ids = []
    messages = []
    for msg in response.received_messages:
        data = json.loads(msg.message.data.decode("utf-8"))
        messages.append(data)
        ack_ids.append(msg.ack_id)

    # Acknowledge
    if ack_ids:
        subscriber.acknowledge(request={"subscription": sub_path, "ack_ids": ack_ids})

    return messages

# Streaming subscriber
def callback(message):
    data = json.loads(message.data.decode("utf-8"))
    process_event(data)
    message.ack()

streaming_pull = subscriber.subscribe(sub_path, callback=callback)
with subscriber:
    try:
        streaming_pull.result(timeout=300)
    except TimeoutError:
        streaming_pull.cancel()
```

---

## 16. Interview Q&A Bank

**Q: What is the GIL in Python and how does it affect data engineering?**
A: The Global Interpreter Lock (GIL) prevents multiple Python threads from executing bytecode simultaneously. For CPU-bound tasks (transformations, number crunching), use `ProcessPoolExecutor` or PySpark. For I/O-bound tasks (API calls, file reads), `ThreadPoolExecutor` works well since threads release the GIL during I/O. In practice, PySpark runs on JVM workers — GIL doesn't affect PySpark transformations. Pandas Vectorized/UDF operations via pandas_udf also bypass the GIL.

**Q: When would you use a generator vs a list in a data pipeline?**
A: Generators for large datasets — they produce values lazily, constant O(1) memory regardless of size. Use for: streaming processing of large files, creating infinite sequences, chained pipeline stages. Lists when: random access needed, data small enough to hold in memory, need to iterate multiple times. Example: `(json.loads(line) for line in open("events.jsonl"))` — process 10GB file with constant memory.

**Q: How do you handle schema evolution in a Python data pipeline?**
A: (1) Define explicit schemas (dataclasses, Pydantic) — validate on ingestion. (2) Use `pd.json_normalize()` for API responses — handles added fields automatically. (3) For Parquet/BigQuery — schema registry or schema inference with `mergeSchema=true`. (4) Additive changes (new columns) are backward-compatible; breaking changes (column removal, type changes) require versioning. (5) Implement schema drift detection: compare incoming schema to expected schema, alert or fail on breaking changes.

**Q: Explain how you would implement idempotent pipeline runs.**
A: Write to partition-based storage with `overwrite` mode on the partition. Track processed dates/runs in a metadata table. Use unique IDs for deduplication. Each run should produce identical results regardless of how many times it's executed. Example: always write to `gs://bucket/data/dt=YYYY-MM-DD/` with `mode="overwrite"` — re-running the same date always produces the same output.

**Q: How do you optimize a slow Python data pipeline?**
A: Profile first: `cProfile`, `line_profiler`, `memory_profiler`. Common fixes: (1) Vectorize — replace `apply()` with Pandas vectorized ops or NumPy. (2) Chunk large files — `pd.read_csv(chunksize=100000)`. (3) Use efficient types — `category` for low cardinality strings, `int32` vs `int64`. (4) Parallelize I/O — `ThreadPoolExecutor` for API calls. (5) Use PyArrow for file I/O — much faster than pure Python. (6) Move heavy computation to PySpark. (7) Cache intermediate results to avoid re-computation.

**Q: What is the difference between deep copy and shallow copy?**
A: Shallow copy: creates new container but references same nested objects. Deep copy: recursively copies all objects.
```python
import copy
original = {"a": [1, 2, 3]}
shallow = copy.copy(original)
deep = copy.deepcopy(original)

shallow["a"].append(4)   # Modifies original["a"] too!
deep["a"].append(4)      # Does NOT modify original — independent copy
```
In data engineering, use deep copy for configs/schemas you'll mutate. For DataFrames, `df.copy()` returns deep copy by default.
