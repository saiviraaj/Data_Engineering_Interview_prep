# ⚡ COMPLETE PYSPARK INTERVIEW PATTERNS & CONCEPTS
## Every Real-World Pattern for Data Engineering Interviews

**CRITICAL:** Covers sessionization, CDC, complex window functions, and production patterns  
**Level:** Senior Data Engineer interviews  
**Focus:** Real interview questions with complete solutions

---

## 📚 TABLE OF CONTENTS

1. **SESSIONIZATION PATTERNS** - Time-based grouping with LAG
2. **WINDOW FUNCTIONS ADVANCED** - LAG, LEAD, running calculations
3. **CDC PATTERNS** - Change data capture, snapshot comparison
4. **DEDUPLICATION STRATEGIES** - SCD Type 2, keeping latest/first
5. **COMPLEX JOINS** - Broadcast, skewed data, inequality joins
6. **AGGREGATION PATTERNS** - Conditional, pivot, rollup
7. **DATE/TIME OPERATIONS** - Business days, time zones, intervals
8. **STRING MANIPULATION** - Parsing, regex, complex transformations
9. **ARRAY/STRUCT OPERATIONS** - Nested data, explode, complex types
10. **PERFORMANCE OPTIMIZATION** - Salting, bucketing, caching strategies
11. **DATA QUALITY PATTERNS** - Validation, reconciliation, profiling
12. **STREAMING PATTERNS** - Window operations, watermarks
13. **FILE FORMAT STRATEGIES** - Parquet optimization, partitioning
14. **PRODUCTION PATTERNS** - Error handling, checkpointing, idempotency
15. **TESTING PATTERNS** - Unit tests, data validation

---

## ⏱️ PART 1: SESSIONIZATION PATTERNS

### **1.1 The Pattern - Time-Based Grouping**

**Problem:** Group events into sessions where gap > N minutes starts new session

```python
from pyspark.sql import SparkSession
from pyspark.sql.window import Window
from pyspark.sql.functions import *

spark = SparkSession.builder.appName("Sessionization").getOrCreate()

# Sample data
data = [
    (1, "2024-01-01 10:00:00", 10),
    (1, "2024-01-01 10:10:00", 20),
    (1, "2024-01-01 11:00:00", 5),   # 50 min gap - new session
    (2, "2024-01-01 09:00:00", 7),
    (2, "2024-01-01 09:20:00", None)
]

df = spark.createDataFrame(data, ["user_id", "event_ts", "time_spent_mins"])
df = df.withColumn("event_ts", to_timestamp("event_ts"))
```

### **1.2 Complete Sessionization Solution**

```python
# ========== STEP 1: Calculate time gap from previous event ==========
window_spec = Window.partitionBy("user_id").orderBy("event_ts")

df_with_lag = df.withColumn(
    "prev_event_ts",
    lag("event_ts", 1).over(window_spec)
).withColumn(
    "minutes_since_last",
    (unix_timestamp("event_ts") - unix_timestamp("prev_event_ts")) / 60
)

# ========== STEP 2: Flag new sessions (gap > 30 or first event) ==========
df_with_flags = df_with_lag.withColumn(
    "is_new_session",
    when(
        (col("minutes_since_last").isNull()) | (col("minutes_since_last") > 30),
        1
    ).otherwise(0)
)

# ========== STEP 3: Create session_id using cumulative sum ==========
df_with_sessions = df_with_flags.withColumn(
    "session_id",
    sum("is_new_session").over(window_spec)
)

# ========== STEP 4: Aggregate by session ==========
result = df_with_sessions.groupBy("user_id", "session_id").agg(
    min("event_ts").alias("session_start_ts"),
    max("event_ts").alias("session_end_ts"),
    count("*").alias("total_events"),
    sum(coalesce(col("time_spent_mins"), lit(0))).alias("total_time_spent")
).orderBy("user_id", "session_id")

result.show(truncate=False)

# Output:
# +-------+----------+-------------------+-------------------+------------+-----------------+
# |user_id|session_id|session_start_ts   |session_end_ts     |total_events|total_time_spent |
# +-------+----------+-------------------+-------------------+------------+-----------------+
# |1      |1         |2024-01-01 10:00:00|2024-01-01 10:10:00|2           |30               |
# |1      |2         |2024-01-01 11:00:00|2024-01-01 11:00:00|1           |5                |
# |2      |1         |2024-01-01 09:00:00|2024-01-01 09:20:00|2           |7                |
# +-------+----------+-------------------+-------------------+------------+-----------------+
```

### **1.3 Sessionization Function (Reusable)**

```python
def sessionize_events(df, user_col, timestamp_col, timeout_minutes=30, metric_cols=None):
    """
    Generic sessionization function
    
    Args:
        df: Input DataFrame
        user_col: Column name for user/entity ID
        timestamp_col: Column name for timestamp
        timeout_minutes: Session timeout in minutes
        metric_cols: List of columns to aggregate (sum)
    
    Returns:
        DataFrame with sessions
    """
    from pyspark.sql.window import Window
    from pyspark.sql.functions import lag, unix_timestamp, sum, when, col, min, max, count
    
    window_spec = Window.partitionBy(user_col).orderBy(timestamp_col)
    
    # Calculate time gaps
    df_gaps = df.withColumn(
        "prev_ts",
        lag(timestamp_col).over(window_spec)
    ).withColumn(
        "minutes_gap",
        (unix_timestamp(timestamp_col) - unix_timestamp("prev_ts")) / 60
    )
    
    # Flag new sessions
    df_flagged = df_gaps.withColumn(
        "is_new_session",
        when(col("minutes_gap").isNull() | (col("minutes_gap") > timeout_minutes), 1)
        .otherwise(0)
    )
    
    # Create session IDs
    df_sessions = df_flagged.withColumn(
        "session_id",
        sum("is_new_session").over(window_spec)
    )
    
    # Build aggregation
    agg_exprs = [
        min(timestamp_col).alias("session_start"),
        max(timestamp_col).alias("session_end"),
        count("*").alias("event_count")
    ]
    
    # Add metric aggregations
    if metric_cols:
        for col_name in metric_cols:
            agg_exprs.append(
                sum(coalesce(col(col_name), lit(0))).alias(f"total_{col_name}")
            )
    
    # Aggregate
    result = df_sessions.groupBy(user_col, "session_id").agg(*agg_exprs)
    
    return result

# Usage
sessions = sessionize_events(
    df,
    user_col="user_id",
    timestamp_col="event_ts",
    timeout_minutes=30,
    metric_cols=["time_spent_mins"]
)

sessions.show()
```

### **1.4 Variable Timeout by User Type**

```python
"""
Premium users: 60 min timeout
Regular users: 30 min timeout
"""

# Join with user metadata
df_with_type = df.join(
    users_df.select("user_id", "user_type"),
    "user_id"
)

# Calculate timeout per user
df_with_timeout = df_with_type.withColumn(
    "timeout_mins",
    when(col("user_type") == "premium", 60).otherwise(30)
)

window_spec = Window.partitionBy("user_id").orderBy("event_ts")

result = df_with_timeout.withColumn(
    "prev_ts",
    lag("event_ts").over(window_spec)
).withColumn(
    "minutes_gap",
    (unix_timestamp("event_ts") - unix_timestamp("prev_ts")) / 60
).withColumn(
    "is_new_session",
    when(
        col("minutes_gap").isNull() | (col("minutes_gap") > col("timeout_mins")),
        1
    ).otherwise(0)
).withColumn(
    "session_id",
    sum("is_new_session").over(window_spec)
)
```

---

## 🪟 PART 2: WINDOW FUNCTIONS ADVANCED

### **2.1 LAG and LEAD Complete Guide**

```python
from pyspark.sql.window import Window
from pyspark.sql.functions import lag, lead

window = Window.partitionBy("user_id").orderBy("date")

df_with_prev_next = df.withColumn(
    # Previous value (1 row back)
    "prev_value", lag("amount", 1).over(window)
).withColumn(
    # Previous value with default
    "prev_value_default", lag("amount", 1, 0).over(window)
).withColumn(
    # 2 rows back
    "prev_2", lag("amount", 2).over(window)
).withColumn(
    # Next value
    "next_value", lead("amount", 1).over(window)
).withColumn(
    # Calculate change from previous
    "change_from_prev",
    col("amount") - lag("amount", 1).over(window)
).withColumn(
    # Percentage change
    "pct_change",
    ((col("amount") - lag("amount", 1).over(window)) / 
     lag("amount", 1).over(window) * 100)
)
```

### **2.2 Running Calculations**

```python
# Running total
df.withColumn(
    "running_total",
    sum("amount").over(Window.orderBy("date"))
)

# Running average
df.withColumn(
    "running_avg",
    avg("amount").over(Window.orderBy("date"))
)

# Running max (high water mark)
df.withColumn(
    "running_max",
    max("amount").over(Window.orderBy("date"))
)

# Cumulative distinct count (tricky!)
window_running = Window.orderBy("date").rowsBetween(Window.unboundedPreceding, Window.currentRow)

df.withColumn(
    "cumulative_products",
    size(collect_set("product").over(window_running))
)
```

### **2.3 Moving Averages**

```python
# 7-day moving average
window_7day = Window.orderBy("date").rowsBetween(-6, 0)

df.withColumn(
    "ma_7day",
    avg("amount").over(window_7day)
)

# Centered moving average (3 before, current, 3 after)
window_centered = Window.orderBy("date").rowsBetween(-3, 3)

df.withColumn(
    "ma_centered",
    avg("amount").over(window_centered)
)

# Exponential moving average (custom)
from pyspark.sql.functions import pandas_udf, PandasUDFType
import pandas as pd

@pandas_udf("double")
def ema_udf(values: pd.Series) -> pd.Series:
    return values.ewm(span=7).mean()

df.withColumn(
    "ema_7",
    ema_udf("amount").over(Window.orderBy("date"))
)
```

---

## 🔄 PART 3: CDC PATTERNS (CHANGE DATA CAPTURE)

### **3.1 Snapshot Comparison**

```python
"""
Problem: Compare two snapshots and identify inserted, deleted, updated records
"""

# Sample data
snapshot_a = spark.createDataFrame([
    (1, "Alice", "Calgary"),
    (2, "Bob", "Toronto"),
    (3, "Charlie", "Vancouver")
], ["id", "name", "city"])

snapshot_b = spark.createDataFrame([
    (1, "Alice", "Edmonton"),    # Updated
    (3, "Charlie", "Vancouver"),  # Unchanged
    (4, "David", "Montreal")      # Inserted
], ["id", "name", "city"])         # id=2 deleted

# ========== SOLUTION 1: Using Joins ==========

# Find inserted (in B, not in A)
inserted = snapshot_b.join(
    snapshot_a,
    snapshot_b.id == snapshot_a.id,
    "left_anti"
)

# Find deleted (in A, not in B)
deleted = snapshot_a.join(
    snapshot_b,
    snapshot_a.id == snapshot_b.id,
    "left_anti"
)

# Find updated (in both but different)
# Join and compare all columns
joined = snapshot_a.alias("a").join(
    snapshot_b.alias("b"),
    col("a.id") == col("b.id"),
    "inner"
)

updated = joined.filter(
    (col("a.name") != col("b.name")) |
    (col("a.city") != col("b.city"))
).select(
    col("a.id"),
    struct(col("a.name"), col("a.city")).alias("old"),
    struct(col("b.name"), col("b.city")).alias("new")
)

# Show results
print("INSERTED:")
inserted.show()

print("DELETED:")
deleted.show()

print("UPDATED:")
updated.show()
```

### **3.2 CDC Function (Reusable)**

```python
def compare_snapshots(df_old, df_new, key_cols, compare_cols=None):
    """
    Compare two snapshots and identify changes
    
    Args:
        df_old: Old snapshot DataFrame
        df_new: New snapshot DataFrame
        key_cols: List of key column names
        compare_cols: List of columns to compare (None = all except keys)
    
    Returns:
        Dictionary with 'inserted', 'deleted', 'updated' DataFrames
    """
    from pyspark.sql.functions import col, struct, lit
    
    # Determine columns to compare
    if compare_cols is None:
        compare_cols = [c for c in df_old.columns if c not in key_cols]
    
    # Create join condition
    if len(key_cols) == 1:
        join_condition = col(f"old.{key_cols[0]}") == col(f"new.{key_cols[0]}")
    else:
        join_condition = None
        for key in key_cols:
            condition = col(f"old.{key}") == col(f"new.{key}")
            join_condition = condition if join_condition is None else join_condition & condition
    
    # Inserted: in new, not in old
    inserted = df_new.join(
        df_old,
        key_cols,
        "left_anti"
    )
    
    # Deleted: in old, not in new
    deleted = df_old.join(
        df_new,
        key_cols,
        "left_anti"
    )
    
    # Updated: in both but different
    joined = df_old.alias("old").join(
        df_new.alias("new"),
        [col(f"old.{k}") == col(f"new.{k}") for k in key_cols],
        "inner"
    )
    
    # Build comparison condition
    comparison = None
    for col_name in compare_cols:
        cond = col(f"old.{col_name}") != col(f"new.{col_name}")
        comparison = cond if comparison is None else comparison | cond
    
    updated = joined.filter(comparison).select(
        *[col(f"old.{k}").alias(k) for k in key_cols],
        struct(*[col(f"old.{c}").alias(c) for c in compare_cols]).alias("old_values"),
        struct(*[col(f"new.{c}").alias(c) for c in compare_cols]).alias("new_values")
    )
    
    return {
        "inserted": inserted,
        "deleted": deleted,
        "updated": updated
    }

# Usage
result = compare_snapshots(
    snapshot_a,
    snapshot_b,
    key_cols=["id"],
    compare_cols=["name", "city"]
)

result["inserted"].show()
result["deleted"].show()
result["updated"].show()
```

### **3.3 SCD Type 2 Implementation**

```python
"""
Slowly Changing Dimension Type 2
Maintain history of changes with effective dates
"""

def apply_scd_type2(current_df, new_df, key_cols, effective_date_col="effective_date"):
    """
    Apply SCD Type 2 logic
    
    Current table has: key_cols + data_cols + effective_date + end_date + is_current
    New data has: key_cols + data_cols
    """
    from pyspark.sql.functions import current_date, lit, when
    
    # Get changes
    changes = compare_snapshots(current_df, new_df, key_cols)
    
    # 1. Close old records that were updated
    updated_keys = changes["updated"].select(*key_cols)
    
    current_closed = current_df.join(
        updated_keys,
        key_cols,
        "left"
    ).withColumn(
        "end_date",
        when(
            updated_keys[key_cols[0]].isNotNull(),
            current_date()
        ).otherwise(col("end_date"))
    ).withColumn(
        "is_current",
        when(
            updated_keys[key_cols[0]].isNotNull(),
            False
        ).otherwise(col("is_current"))
    )
    
    # 2. Add new versions of updated records
    updated_new = changes["updated"].select(
        *key_cols,
        "new_values.*"
    ).withColumn(
        "effective_date",
        current_date()
    ).withColumn(
        "end_date",
        lit(None).cast("date")
    ).withColumn(
        "is_current",
        lit(True)
    )
    
    # 3. Add inserted records
    inserted_new = changes["inserted"].withColumn(
        "effective_date",
        current_date()
    ).withColumn(
        "end_date",
        lit(None).cast("date")
    ).withColumn(
        "is_current",
        lit(True)
    )
    
    # 4. Union all
    result = current_closed.union(updated_new).union(inserted_new)
    
    return result
```

---

## 🎯 PART 4: DEDUPLICATION STRATEGIES

### **4.1 Keep Latest Record**

```python
from pyspark.sql.window import Window
from pyspark.sql.functions import row_number, col

# Method 1: Using ROW_NUMBER
window = Window.partitionBy("user_id").orderBy(col("updated_at").desc())

deduped = df.withColumn(
    "rn",
    row_number().over(window)
).filter(
    col("rn") == 1
).drop("rn")

# Method 2: Using dropDuplicates (if just need one)
deduped = df.orderBy(col("updated_at").desc()).dropDuplicates(["user_id"])

# Method 3: Using aggregation (when you can use max/min)
deduped = df.groupBy("user_id").agg(
    max("updated_at").alias("updated_at"),
    max(struct("updated_at", "*")).alias("latest")
).select("user_id", "latest.*")
```

### **4.2 Keep First and Last**

```python
"""
Keep both first and last occurrence
"""

window = Window.partitionBy("user_id").orderBy("event_date")

df.withColumn(
    "is_first",
    row_number().over(window) == 1
).withColumn(
    "is_last",
    row_number().over(Window.partitionBy("user_id").orderBy(col("event_date").desc())) == 1
).filter(
    col("is_first") | col("is_last")
)
```

---

## 🔗 PART 5: COMPLEX JOINS

### **5.1 Inequality Joins**

```python
"""
Find overlapping time ranges
"""

# Overlapping bookings
overlaps = bookings.alias("b1").join(
    bookings.alias("b2"),
    (col("b1.room_id") == col("b2.room_id")) &
    (col("b1.booking_id") < col("b2.booking_id")) &
    (col("b1.start_time") < col("b2.end_time")) &
    (col("b2.start_time") < col("b1.end_time"))
).select(
    col("b1.booking_id").alias("booking1"),
    col("b2.booking_id").alias("booking2"),
    "b1.room_id"
)
```

### **5.2 Broadcast Join Optimization**

```python
from pyspark.sql.functions import broadcast

# When one DataFrame is small (< 10MB)
result = large_df.join(
    broadcast(small_df),
    "key"
)

# Check size before broadcasting
small_df.cache()
size_bytes = small_df.count() * small_df.schema.__len__() * 8  # Rough estimate
if size_bytes < 10 * 1024 * 1024:  # 10MB
    result = large_df.join(broadcast(small_df), "key")
```

### **5.3 Skewed Join with Salting**

```python
"""
Handle data skew where one key has too many records
"""

from pyspark.sql.functions import rand, explode, array, lit

# Add salt to large table
num_salts = 10
large_salted = large_df.withColumn(
    "salt",
    (rand() * num_salts).cast("int")
).withColumn(
    "salted_key",
    concat(col("key"), lit("_"), col("salt"))
)

# Replicate small table with all salt values
salt_array = array([lit(i) for i in range(num_salts)])
small_replicated = small_df.withColumn(
    "salt",
    explode(salt_array)
).withColumn(
    "salted_key",
    concat(col("key"), lit("_"), col("salt"))
)

# Join on salted key
result = large_salted.join(
    small_replicated,
    "salted_key"
).drop("salt", "salted_key")
```

---

## 📊 PART 6: ADVANCED AGGREGATIONS

### **6.1 Conditional Aggregation**

```python
# Multiple conditions in one pass
result = df.groupBy("category").agg(
    sum(when(col("status") == "active", col("amount")).otherwise(0)).alias("active_total"),
    sum(when(col("status") == "inactive", col("amount")).otherwise(0)).alias("inactive_total"),
    count(when(col("status") == "active", 1)).alias("active_count"),
    avg(when(col("amount") > 1000, col("amount"))).alias("high_value_avg")
)
```

### **6.2 Pivot Operations**

```python
# Pivot with aggregation
pivoted = df.groupBy("product").pivot("month").agg(
    sum("sales").alias("total_sales"),
    avg("price").alias("avg_price")
)

# Pivot with predefined values (faster!)
pivoted = df.groupBy("product").pivot(
    "month",
    ["Jan", "Feb", "Mar", "Apr"]
).sum("sales")
```

---

## 🎯 QUICK PATTERN REFERENCE

```
PROBLEM → PATTERN → KEY FUNCTIONS
├─ Time-based sessions → LAG + SUM window → lag(), sum().over()
├─ Snapshot comparison → CDC pattern → left_anti joins
├─ Keep latest → Deduplication → row_number().over()
├─ Running total → Window function → sum().over(orderBy)
├─ Moving average → Window with frame → avg().over(rowsBetween)
├─ Skewed join → Salting → Random salt + explode
├─ Small table join → Broadcast → broadcast()
└─ Overlapping ranges → Inequality join → Multiple conditions
```

---

**STATUS:** Complete PySpark patterns with sessionization, CDC, and advanced techniques! ⚡

Next: Python patterns with CDC logic...
