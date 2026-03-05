# PySpark Interview Questions - FAANG Level

Advanced PySpark for large-scale data processing at FAANG companies.

---

## ADVANCED QUESTIONS (1-25)

### Question 1: Streaming DataFrames

```python
# Read streaming data
df_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "topic") \
    .load()

# Process streaming data
processed = df_stream.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")

# Write streaming data
query = processed.writeStream \
    .format("parquet") \
    .option("path", "output_path") \
    .option("checkpointLocation", "checkpoint") \
    .start()

query.awaitTermination()
```

### Question 2: Structured Streaming with Watermark

```python
from pyspark.sql.functions import window, col

# Add watermark for late data
streaming_df = streaming_df.withWatermark("timestamp", "10 minutes")

# Window aggregation
windowed_agg = streaming_df.groupBy(
    window(col("timestamp"), "5 minutes", "1 minute"),
    col("category")
).agg(count("*").alias("count"))

# Write with trigger
query = windowed_agg.writeStream \
    .format("console") \
    .trigger(processingTime="30 seconds") \
    .start()
```

### Question 3: Catalyst Optimizer Understanding

```python
# Explain query plan
df.filter(col("age") > 30) \
    .select("name", "age") \
    .explain(extended=True)

# Physical plan shows:
# - Filter pushdown (filters applied early)
# - Column projection (only needed columns)
# - Join optimization (broadcast joins for small tables)

# Hint optimizer
df1.hint("broadcast").join(df2, "id")
```

### Question 4: Partition and Bucketing

```python
# Partition by column (creates directory structure)
df.write \
    .partitionBy("year", "month") \
    .bucketBy(10, "id") \
    .mode("overwrite") \
    .parquet("output")

# Sort within partitions (helps with joins)
df.write \
    .partitionBy("year") \
    .sortBy("id") \
    .parquet("output")

# Read only specific partitions
specific = spark.read \
    .parquet("output") \
    .filter((col("year") == 2024) & (col("month") == 3))
```

### Question 5: Custom Partitioner

```python
from pyspark import RDD

class CustomPartitioner:
    def __init__(self, num_partitions):
        self.num_partitions = num_partitions
    
    def __call__(self, key):
        # Hash-based partitioning
        return hash(key) % self.num_partitions

rdd = sc.parallelize(data)
partitioned = rdd.partitionBy(100, CustomPartitioner(100))
```

### Question 6: Skew Handling with Salting

```python
from pyspark.sql.functions import rand, floor

# Detect skewed keys
skew_keys = df.groupBy("key").count() \
    .filter(col("count") > threshold) \
    .select("key")

# Salt skewed keys
salted_df = df.withColumn(
    "salt",
    when(
        col("key").isin(skew_keys),
        floor(rand() * num_salt_buckets)
    ).otherwise(0)
)

# Join with salted data
result = salted_df.join(
    broadcast_df.withColumn("salt", explode(array(*[lit(i) for i in range(num_salt_buckets)]))),
    ["key", "salt"]
)
```

### Question 7: Accumulator and Shared Variables

```python
from pyspark.sql.functions import udf

# Create accumulator for metrics
error_count = sc.accumulator(0)
processed_count = sc.accumulator(0)

def process_row(row):
    global error_count, processed_count
    try:
        # Process
        processed_count += 1
        return row
    except:
        error_count += 1
        return None

# Use in UDF
processed = df.rdd.map(process_row).toDF()

print(f"Processed: {processed_count.value}, Errors: {error_count.value}")
```

### Question 8: Columnar Storage - Parquet Optimization

```python
# Write with optimal settings
df.write \
    .option("compression", "snappy") \
    .option("parquet.block.size", 134217728) \
    .parquet("output")

# Read with pushdown
df = spark.read \
    .parquet("data") \
    .filter(col("date") >= "2024-01-01") \
    .select("id", "name")

# Parquet predicate pushdown automatically filters at storage level
```

### Question 9: Delta Lake Optimization

```python
# Write as Delta
df.write.format("delta").mode("overwrite").save("delta_table")

# OPTIMIZE - compact small files
spark.sql("OPTIMIZE delta_table")

# Z-ORDER - co-locate related data
spark.sql("OPTIMIZE delta_table ZORDER BY (id, date)")

# Time travel
history = spark.sql("DESCRIBE HISTORY delta_table")
old_version = spark.read.format("delta") \
    .option("versionAsOf", 5) \
    .load("delta_table")
```

### Question 10: Complex Data Types

```python
from pyspark.sql.types import *

# Array operations
df.withColumn("first_item", col("items")[0])
df.withColumn("item_count", size(col("items")))
df.withColumn("contains_id", array_contains(col("items"), 123))

# Map operations
df.withColumn("value", col("map_col")["key"])
df.withColumn("keys", map_keys(col("map_col")))

# Struct operations
df.withColumn("name", col("person.name"))
```

### Question 11: Performance Tuning at Scale

```python
# Set parallel tasks
spark.conf.set("spark.default.parallelism", 200)
spark.conf.set("spark.sql.shuffle.partitions", 200)

# Memory optimization
spark.conf.set("spark.executor.memory", "16g")
spark.conf.set("spark.executor.cores", 8)

# Broadcast threshold
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", 50 * 1024 * 1024)

# Adaptive query execution
spark.conf.set("spark.sql.adaptive.enabled", true)
```

### Question 12: Handling Late Data in Streaming

```python
from pyspark.sql.functions import window, col

streaming_df = streaming_df.withWatermark("event_time", "10 minutes")

result = streaming_df \
    .groupBy(window(col("event_time"), "5 minutes")) \
    .agg(count("*")) \
    .filter(col("window").isNotNull())

# Output mode controls how late data is handled
query = result.writeStream \
    .outputMode("update") \  # Update changed rows
    .format("parquet") \
    .option("path", "output") \
    .option("checkpointLocation", "checkpoint") \
    .start()
```

### Question 13: Exactly-Once Semantics

```python
# Idempotent writes with checkpoints
query = processed_df.writeStream \
    .format("delta") \
    .option("checkpointLocation", "/checkpoints/path") \
    .outputMode("append") \
    .start()

# Deduplication within window
deduped = streaming_df \
    .dropDuplicates(["id"]) \
    .withWatermark("timestamp", "1 hour")
```

### Question 14: Data Lineage and Governance

```python
# Track data lineage
df = spark.read.parquet("source")
df = df.filter(col("status") == "active")
df = df.select("id", "name", "value")

# Log metadata
metadata = {
    "source": "raw_events",
    "transformations": ["filter", "select"],
    "output": "processed_data",
    "timestamp": current_timestamp()
}

# Write with metadata
df.write \
    .option("user_metadata", str(metadata)) \
    .parquet("output")
```

### Question 15: Complex ETL Pipeline

```python
# Multi-source ingestion with error handling
sources = [
    spark.read.parquet("source1"),
    spark.read.parquet("source2"),
    spark.read.parquet("source3")
]

# Union with type alignment
combined = reduce(lambda df1, df2: df1.union(df2), sources)

# Quality checks
quality_df = combined \
    .withColumn("quality_score", 
        (when(isnull(col("id")), 0).otherwise(1) +
         when(isnull(col("date")), 0).otherwise(1) +
         when(col("amount") > 0, 1).otherwise(0))
    ) \
    .filter(col("quality_score") >= 2)

# Partition and write
quality_df.write \
    .partitionBy("year", "month") \
    .mode("overwrite") \
    .parquet("processed_data")
```

---

## FAANG Interview Tips

✅ **What they test:**
- Large-scale data handling
- Performance optimization
- Distributed computing understanding
- Error handling and data quality
- Real-time processing
- Cost optimization

✅ **Performance discussions:**
- Explain query execution plans
- Partition strategies
- Broadcasting vs shuffling
- Memory management
- Network I/O optimization

---

