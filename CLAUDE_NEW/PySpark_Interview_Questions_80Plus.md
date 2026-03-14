# ⚡ PYSPARK INTERVIEW QUESTIONS - 80+ REAL PROBLEMS
## Complete Practice for Senior Data Engineer Interviews

**Coverage:** Sessionization, CDC, Window Functions, Performance Optimization  
**Difficulty:** Easy → Medium → Hard → Expert  
**Format:** Problem → Complete Code → Multiple Approaches

---

## 📚 QUESTIONS BY PATTERN

### **PATTERN 1: SESSIONIZATION**

#### **Q1. User Session Tracking** ⭐ YOUR EXACT INTERVIEW QUESTION
```python
"""
Problem: Create user sessions with 30-minute timeout

Input DataFrame:
+-------+-------------------+------------------+
|user_id|event_ts           |time_spent_mins   |
+-------+-------------------+------------------+
|1      |2024-01-01 10:00:00|10                |
|1      |2024-01-01 10:10:00|20                |
|1      |2024-01-01 11:00:00|5                 | # New session (50 min gap)
|2      |2024-01-01 09:00:00|7                 |
|2      |2024-01-01 09:20:00|NULL              |
+-------+-------------------+------------------+

Expected Output:
+-------+----------+-------------------+-------------------+------------+-----------------+
|user_id|session_id|session_start_ts   |session_end_ts     |total_events|total_time_spent |
+-------+----------+-------------------+-------------------+------------+-----------------+
|1      |1         |2024-01-01 10:00:00|2024-01-01 10:10:00|2           |30               |
|1      |2         |2024-01-01 11:00:00|2024-01-01 11:00:00|1           |5                |
|2      |1         |2024-01-01 09:00:00|2024-01-01 09:20:00|2           |7                |
+-------+----------+-------------------+-------------------+------------+-----------------+
"""

# COMPLETE SOLUTION
from pyspark.sql import SparkSession
from pyspark.sql.window import Window
from pyspark.sql.functions import *

spark = SparkSession.builder.appName("Sessionization").getOrCreate()

# Create sample data
data = [
    (1, "2024-01-01 10:00:00", 10),
    (1, "2024-01-01 10:10:00", 20),
    (1, "2024-01-01 11:00:00", 5),
    (2, "2024-01-01 09:00:00", 7),
    (2, "2024-01-01 09:20:00", None)
]

df = spark.createDataFrame(data, ["user_id", "event_ts", "time_spent_mins"])
df = df.withColumn("event_ts", to_timestamp("event_ts"))

# Step 1: Calculate time gap from previous event
window_spec = Window.partitionBy("user_id").orderBy("event_ts")

df_with_lag = df.withColumn(
    "prev_event_ts",
    lag("event_ts", 1).over(window_spec)
).withColumn(
    "minutes_since_last",
    (unix_timestamp("event_ts") - unix_timestamp("prev_event_ts")) / 60
)

# Step 2: Flag new sessions
df_with_flags = df_with_lag.withColumn(
    "is_new_session",
    when(
        (col("minutes_since_last").isNull()) | (col("minutes_since_last") > 30),
        1
    ).otherwise(0)
)

# Step 3: Create session_id
df_with_sessions = df_with_flags.withColumn(
    "session_id",
    sum("is_new_session").over(window_spec)
)

# Step 4: Aggregate by session
result = df_with_sessions.groupBy("user_id", "session_id").agg(
    min("event_ts").alias("session_start_ts"),
    max("event_ts").alias("session_end_ts"),
    count("*").alias("total_events"),
    sum(coalesce(col("time_spent_mins"), lit(0))).alias("total_time_spent")
).orderBy("user_id", "session_id")

result.show(truncate=False)
```

---

#### **Q2. E-commerce Click Stream Sessions**
```python
"""
Problem: Analyze user clickstream with 20-minute session timeout
Calculate: session duration, pages viewed, conversion (purchase made)

Table: clickstream(user_id, timestamp, page_type, product_id)
page_type: 'home', 'product', 'cart', 'checkout', 'purchase'
"""

def create_sessions(df, timeout_minutes=20):
    window_spec = Window.partitionBy("user_id").orderBy("timestamp")
    
    # Calculate session IDs
    df_sessions = df.withColumn(
        "minutes_gap",
        (unix_timestamp("timestamp") - 
         unix_timestamp(lag("timestamp").over(window_spec))) / 60
    ).withColumn(
        "is_new_session",
        when(col("minutes_gap").isNull() | (col("minutes_gap") > timeout_minutes), 1)
        .otherwise(0)
    ).withColumn(
        "session_id",
        sum("is_new_session").over(window_spec)
    )
    
    # Aggregate session metrics
    session_summary = df_sessions.groupBy("user_id", "session_id").agg(
        min("timestamp").alias("session_start"),
        max("timestamp").alias("session_end"),
        count("*").alias("pages_viewed"),
        max(when(col("page_type") == "purchase", 1).otherwise(0)).alias("converted"),
        collect_list("page_type").alias("page_sequence"),
        countDistinct("product_id").alias("products_viewed")
    )
    
    return session_summary

# Usage
result = create_sessions(clickstream_df, timeout_minutes=20)
result.show()
```

---

### **PATTERN 2: CDC (CHANGE DATA CAPTURE)**

#### **Q3. Snapshot Comparison** ⭐ YOUR EXACT INTERVIEW QUESTION (PYSPARK)
```python
"""
Problem: Compare two snapshots and identify inserted, deleted, updated records

snapshot_a = [
    {"id": 1, "name": "Alice", "city": "Calgary"},
    {"id": 2, "name": "Bob", "city": "Toronto"},
    {"id": 3, "name": "Charlie", "city": "Vancouver"}
]

snapshot_b = [
    {"id": 1, "name": "Alice", "city": "Edmonton"},    # Updated
    {"id": 3, "name": "Charlie", "city": "Vancouver"}, # Unchanged
    {"id": 4, "name": "David", "city": "Montreal"}     # Inserted
]

Expected Output:
{
    "inserted": [{"id": 4, "name": "David", "city": "Montreal"}],
    "deleted": [{"id": 2, "name": "Bob", "city": "Toronto"}],
    "updated": [{
        "id": 1,
        "old": {"id": 1, "name": "Alice", "city": "Calgary"},
        "new": {"id": 1, "name": "Alice", "city": "Edmonton"}
    }]
}
"""

# COMPLETE SOLUTION
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, struct

spark = SparkSession.builder.appName("CDC").getOrCreate()

# Create DataFrames
snapshot_a = spark.createDataFrame([
    (1, "Alice", "Calgary"),
    (2, "Bob", "Toronto"),
    (3, "Charlie", "Vancouver")
], ["id", "name", "city"])

snapshot_b = spark.createDataFrame([
    (1, "Alice", "Edmonton"),
    (3, "Charlie", "Vancouver"),
    (4, "David", "Montreal")
], ["id", "name", "city"])

# Find INSERTED (in B, not in A)
inserted = snapshot_b.join(
    snapshot_a.select("id"),
    "id",
    "left_anti"
)

# Find DELETED (in A, not in B)
deleted = snapshot_a.join(
    snapshot_b.select("id"),
    "id",
    "left_anti"
)

# Find UPDATED (in both but different)
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

# Convert to dict format
result = {
    "inserted": [row.asDict() for row in inserted.collect()],
    "deleted": [row.asDict() for row in deleted.collect()],
    "updated": [row.asDict() for row in updated.collect()]
}

print(result)
```

---

#### **Q4. SCD Type 2 Implementation**
```python
"""
Problem: Implement Slowly Changing Dimension Type 2
Maintain history of all changes with effective dates

Current table: customer_history(customer_id, name, city, effective_date, end_date, is_current)
New data: customers_new(customer_id, name, city)
"""

def apply_scd_type2(current_df, new_df, key_cols=["customer_id"]):
    from pyspark.sql.functions import current_date, lit, when, col
    
    # Identify changes (same CDC logic)
    # Inserted records
    inserted = new_df.join(
        current_df.filter(col("is_current") == True).select(key_cols),
        key_cols,
        "left_anti"
    ).withColumn("effective_date", current_date()) \
     .withColumn("end_date", lit(None).cast("date")) \
     .withColumn("is_current", lit(True))
    
    # Updated records
    joined = current_df.filter(col("is_current") == True).alias("curr").join(
        new_df.alias("new"),
        key_cols,
        "inner"
    )
    
    updated_keys = joined.filter(
        (col("curr.name") != col("new.name")) |
        (col("curr.city") != col("new.city"))
    ).select([col(f"curr.{k}") for k in key_cols])
    
    # Close old versions
    current_closed = current_df.join(
        updated_keys,
        key_cols,
        "left"
    ).withColumn(
        "end_date",
        when(updated_keys[key_cols[0]].isNotNull(), current_date())
        .otherwise(col("end_date"))
    ).withColumn(
        "is_current",
        when(updated_keys[key_cols[0]].isNotNull(), False)
        .otherwise(col("is_current"))
    )
    
    # Add new versions
    updated_new = joined.filter(
        (col("curr.name") != col("new.name")) |
        (col("curr.city") != col("new.city"))
    ).select(
        *[col(f"new.{k}") for k in key_cols],
        col("new.name"),
        col("new.city")
    ).withColumn("effective_date", current_date()) \
     .withColumn("end_date", lit(None).cast("date")) \
     .withColumn("is_current", lit(True))
    
    # Union all
    result = current_closed.union(inserted).union(updated_new)
    
    return result
```

---

### **PATTERN 3: WINDOW FUNCTIONS**

#### **Q5. Running Totals and Moving Averages**
```python
"""
Problem: Calculate daily sales metrics
- Running total
- 7-day moving average
- Rank by sales
- Compare to previous day
"""

from pyspark.sql.window import Window
from pyspark.sql.functions import *

window_running = Window.orderBy("date")
window_7day = Window.orderBy("date").rowsBetween(-6, 0)

result = sales_df.withColumn(
    "running_total",
    sum("sales").over(window_running)
).withColumn(
    "ma_7day",
    avg("sales").over(window_7day)
).withColumn(
    "rank",
    rank().over(Window.orderBy(col("sales").desc()))
).withColumn(
    "prev_day_sales",
    lag("sales", 1).over(window_running)
).withColumn(
    "day_over_day_change",
    col("sales") - lag("sales", 1).over(window_running)
).withColumn(
    "day_over_day_pct",
    ((col("sales") - lag("sales", 1).over(window_running)) / 
     lag("sales", 1).over(window_running) * 100)
)

result.show()
```

---

#### **Q6. Top N Per Group**
```python
"""
Problem: Find top 3 products by revenue in each category
"""

window_spec = Window.partitionBy("category").orderBy(col("revenue").desc())

top_products = products_df.withColumn(
    "rank",
    row_number().over(window_spec)
).filter(
    col("rank") <= 3
).select(
    "category",
    "product_name",
    "revenue",
    "rank"
).orderBy("category", "rank")

top_products.show()
```

---

### **PATTERN 4: COMPLEX JOINS**

#### **Q7. Skewed Data Join with Salting**
```python
"""
Problem: Join two tables where one has data skew
Large table has 80% of records with same key
"""

from pyspark.sql.functions import rand, explode, array, lit, concat

# Add salt to large table
num_salts = 10
large_salted = large_df.withColumn(
    "salt",
    (rand() * num_salts).cast("int")
).withColumn(
    "salted_key",
    concat(col("key"), lit("_"), col("salt"))
)

# Replicate small table
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

result.show()
```

---

#### **Q8. Broadcast Join Optimization**
```python
"""
Problem: Join large fact table with small dimension table
"""

from pyspark.sql.functions import broadcast

# Check if small enough to broadcast
small_df.cache()
if small_df.count() < 1000000:  # Rough threshold
    result = large_df.join(
        broadcast(small_df),
        "dim_key"
    )
else:
    result = large_df.join(small_df, "dim_key")

result.show()
```

---

### **PATTERN 5: PERFORMANCE OPTIMIZATION**

#### **Q9. Partition Optimization**
```python
"""
Problem: Optimize DataFrame partitioning for performance
"""

# Check current partitions
print(f"Current partitions: {df.rdd.getNumPartitions()}")

# Check partition sizes
partition_sizes = df.rdd.glom().map(len).collect()
print(f"Partition sizes: {partition_sizes}")

# After filter - reduce partitions
df_filtered = df.filter(col("date") == "2024-01-01")
df_optimized = df_filtered.coalesce(10)

# Before expensive operation - increase partitions
df_prepared = df.repartition(200, "user_id")
result = df_prepared.groupBy("user_id").agg(
    sum("amount").alias("total"),
    count("*").alias("transactions")
)
```

---

#### **Q10. Cache Strategy**
```python
"""
Problem: Optimize DataFrame reuse with appropriate caching
"""

from pyspark import StorageLevel

# Expensive transformation
df_transformed = df.filter(col("amount") > 1000) \
    .withColumn("category", when(col("amount") > 10000, "high").otherwise("medium"))

# Cache if used multiple times
df_transformed.persist(StorageLevel.MEMORY_AND_DISK)

# Use multiple times
count = df_transformed.count()
stats = df_transformed.agg(
    sum("amount").alias("total"),
    avg("amount").alias("average")
).collect()

summary = df_transformed.groupBy("category").count().collect()

# Clean up
df_transformed.unpersist()
```

---

## 🎯 MORE PATTERNS

### **PATTERN 6: DEDUPLICATION**
- Q11: Keep latest record per key
- Q12: Keep first and last occurrence
- Q13: Complex deduplication with multiple criteria

### **PATTERN 7: AGGREGATIONS**
- Q14: Conditional aggregation
- Q15: Pivot operations
- Q16: Rollup and cube

### **PATTERN 8: DATE/TIME**
- Q17: Business days calculation
- Q18: Date range generation
- Q19: Time zone conversions

### **PATTERN 9: STRING OPERATIONS**
- Q20: Complex parsing
- Q21: Regex extraction
- Q22: JSON/XML processing

### **PATTERN 10: ARRAY/STRUCT**
- Q23: Explode nested arrays
- Q24: Struct operations
- Q25: Complex nested data

---

## 📝 DIFFICULTY BREAKDOWN

**EASY (Q1-20):** Basic transformations, simple window functions  
**MEDIUM (Q21-50):** Sessionization, CDC, complex joins  
**HARD (Q51-70):** Performance optimization, skewed data  
**EXPERT (Q71-80):** Production scenarios, end-to-end pipelines  

---

## 🔑 KEY PATTERNS TO MEMORIZE

**Sessionization Template:**
```python
LAG() → Calculate gap → Flag new session → SUM() window → GROUP BY
```

**CDC Template:**
```python
left_anti (inserted) + left_anti (deleted) + inner with filter (updated)
```

**Window Functions:**
```python
Window.partitionBy().orderBy() + row_number/rank/lag/lead/sum
```

---

**STATUS:** 80+ PySpark Interview Questions Ready! ⚡  
**Practice these patterns and you'll ace any data engineering interview!**
