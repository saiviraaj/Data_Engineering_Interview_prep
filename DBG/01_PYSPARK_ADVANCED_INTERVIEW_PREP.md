# PySpark Advanced Interview Preparation
## Deutsche Börse Group - Principal Data Engineer

**Author**: Prepared for Senior Data Engineer / Principal Data Engineer Interview  
**Experience Level**: 10+ years, targeting Principal level questions  
**Focus**: Production-scale PySpark, optimization, and real-world financial data pipelines

---

## Table of Contents

1. [Core PySpark Architecture](#core-pyspark-architecture)
2. [Performance Optimization & Tuning](#performance-optimization--tuning)
3. [Data Skew - The Critical Problem](#data-skew---the-critical-problem)
4. [Advanced Transformations](#advanced-transformations)
5. [Streaming with Structured Streaming](#streaming-with-structured-streaming)
6. [Join Strategies & Optimization](#join-strategies--optimization)
7. [Memory Management & Execution](#memory-management--execution)
8. [Production Patterns & Debugging](#production-patterns--debugging)

---

## Core PySpark Architecture

### Q1: Explain Spark's Architecture - Driver vs Executors

**Question**: Describe the master-slave architecture in Spark. What are the roles of the driver and executors?

**Answer**:

Spark uses a master-slave (or master-worker) distributed computing architecture:

**Driver Program**:
- Single JVM process that runs the Spark application
- Coordinates execution across the cluster
- Maintains SparkSession and SparkContext
- Splits data into partitions and assigns tasks
- Collects results from executors
- Can be a bottleneck if it receives too much data (e.g., collect() operations)

**Executor Processes**:
- Run on worker nodes in the cluster
- Execute tasks assigned by the driver
- Store data in memory (cache/broadcast)
- Communicate results back to driver
- Multiple executors can run in parallel on different nodes

**Task Scheduling Flow**:
```
Driver → Task Scheduler → DAG Scheduler → Physical Executor
         ↑                                   ↓
         ← Heartbeat & Results ←────────────
```

**Key Interview Points**:
- Driver is single point of coordination (not scalable)
- Executors are independent and can fail without failing entire app
- Number of executors, memory, and cores are configurable
- Driver memory ≠ Executor memory (common mistake)

---

### Q2: What is Lazy Evaluation and Why Does It Matter?

**Question**: Explain lazy evaluation in Spark. How does it impact performance and debugging?

**Answer**:

**Lazy Evaluation Principle**:
- Spark doesn't compute results immediately when you define a transformation
- Instead, it builds a DAG (Directed Acyclic Graph) of operations
- Computation only happens when an **action** is called

**Transformations vs Actions**:

```python
# TRANSFORMATIONS (Lazy - not executed)
df_transformed = df.filter(col("age") > 25)  # Not executed yet
df_grouped = df_transformed.groupBy("city").count()  # Still not executed

# ACTION (Triggers execution)
result = df_grouped.show()  # Now everything executes
result = df_grouped.collect()  # Pulls all data to driver
```

**Why Lazy Evaluation Matters**:

1. **Optimization Opportunities**:
   - Catalyst optimizer can analyze entire DAG before execution
   - Can reorder operations for efficiency
   - Can eliminate unnecessary transformations

2. **Performance**:
   - Allows Spark to skip unnecessary partitions (predicate pushdown)
   - Can combine operations to reduce memory requirements
   - Avoids computing unnecessary intermediate results

3. **Debugging Challenge**:
   - Errors appear only when action is called, not when transformation is defined
   - Can be confusing for beginners

**Example - Predicate Pushdown**:
```python
# Without Spark optimization, this would read entire table, then filter
df = spark.read.parquet("large_table")
filtered = df.filter(col("date") == "2024-01-01")
result = filtered.select("user_id", "amount").show()

# Catalyst optimizer pushes filter to read time - only reads matching partitions
# This is why partitioning strategy is critical
```

**Production Pattern**:
```python
# GOOD: Multiple actions on same dataset
df_cached = df.filter(...).cache()
count = df_cached.count()  # Action 1
stats = df_cached.groupBy(...).agg(...).show()  # Action 2
# Reuses cached data

# BAD: Recomputing same transformation
df.filter(...).count()  # Recomputes
df.filter(...).groupBy(...).show()  # Recomputes again
```

---

### Q3: RDDs vs DataFrames vs Datasets - When to Use Each?

**Question**: Compare RDDs, DataFrames, and Datasets. When would you use each in a financial data pipeline?

**Answer**:

| Aspect | RDDs | DataFrames | Datasets |
|--------|------|-----------|----------|
| **API Level** | Low-level | High-level abstraction | Type-safe abstraction |
| **Optimization** | Manual tuning | Catalyst optimizer | Catalyst + Type safety |
| **Schema** | Untyped | Typed at runtime | Compile-time typed (Scala) |
| **Performance** | Slower (serialization) | Faster (optimized) | Fast + Type safe |
| **Serialization** | Java/Python pickling | Binary format | Encoders |
| **Use Case** | Unstructured data | Structured/semi-structured | Scala/Java type safety |

**When to Use RDDs**:

```python
# 1. Unstructured text data
rdd = sc.textFile("logs.txt")
parsed_rdd = rdd.flatMap(lambda x: x.split("\n"))

# 2. Complex nested/recursive logic Catalyst can't optimize
from pyspark.rdd import RDD
def complex_logic(partition):
    for record in partition:
        # Complex recursive or stateful logic
        yield process_record(record)

rdd_result = rdd.mapPartitions(complex_logic)

# 3. Need access to individual records without schema
```

**When to Use DataFrames** (90% of use cases):

```python
# 1. Structured data with known schema
df = spark.read.parquet("financial_transactions")

# 2. SQL operations
df_result = df.filter(col("amount") > 1000).groupBy("account_id").sum("amount")

# 3. Leveraging Catalyst optimizer for complex joins
# Catalyst will automatically choose best join strategy

# 4. Working with semi-structured data (JSON, Avro)
df = spark.read.json("events.json")
```

**When to Use Datasets** (Scala/Java only):

```scala
// Type-safe operations at compile time
case class Transaction(id: Long, amount: Double, account: String)
val ds: Dataset[Transaction] = spark.read.json("transactions.json").as[Transaction]

// Compile-time type checking - catches errors before runtime
ds.filter(_.amount > 1000).show()

// Better for Scala/Java, Python doesn't have true Datasets
```

**Financial Pipeline Example**:

```python
# Read trades as DataFrame (structured)
trades_df = spark.read.parquet("trades")

# Use DataFrame for structured operations
trades_by_trader = (trades_df
    .filter(col("trade_date") == "2024-01-15")
    .groupBy("trader_id")
    .agg(sum("amount"), avg("price")))

# If we needed complex validation logic, could drop to RDD
# But usually DataFrame is sufficient + faster

# Modern practice: 99% DataFrames, 1% RDDs for edge cases
```

---

## Performance Optimization & Tuning

### Q4: The Spark UI - What to Monitor?

**Question**: You're told a PySpark job is slow. Walk me through how you'd diagnose it using Spark UI.

**Answer**:

**Spark UI Access**:
- Default: `http://localhost:4040` (driver host)
- In production: Available during and after job execution

**Critical Tabs to Check**:

**1. Jobs Tab** (Overall picture):
```
What to look for:
- Job duration: Total time including waiting
- Status: Succeeded vs Failed
- Tasks: Total tasks and failed tasks

Example finding: "Job took 5min but 4min was waiting for resources"
→ Investigate: Insufficient executors, not a code issue
```

**2. Stages Tab** (Where time is spent):
```
What to look for:
- Stage duration breakdown
- Shuffle read/write bytes
- Input/output records

Example: 
Stage 0: 30s (read + filter) → Likely issue
Stage 1: 120s (shuffle) → Shuffle expensive
Stage 2: 5s (final aggregation) → Efficient

→ Investigate Stage 1: Are we shuffling too much data?
```

**3. Tasks Tab** (Task-level details):
```
Look at task duration histogram:
- Most tasks: 100ms
- Few tasks: 10,000ms → DATA SKEW!

→ Investigate: Is one partition much larger than others?
```

**4. Executors Tab** (Resource utilization):
```
Metrics:
- Executor Memory: Used vs Available
- Peak Memory Usage
- GC Time: If high (>20%), memory pressure

Example: 
Executor 1: Using 5GB of 8GB → Normal
Executor 2: Using 7.5GB of 8GB → OOM risk, or skewed data on this executor

→ Investigate: Repartition or add memory
```

**5. Storage Tab** (Cache/Persist):
```
Show cached datasets and their size
- Is cached data efficient?
- Are we caching unnecessary DataFrames?

Example:
"Cached df_trades: 45GB" → Is this the biggest bottleneck?
→ Are we querying this cache enough to justify 45GB?
```

**Real Production Diagnosis Example**:

```python
# Hypothetical slow job:
spark.conf.set("spark.sql.shuffle.partitions", "200")

df = spark.read.parquet("trades")
result = (df
    .filter(col("date") >= "2024-01-01")
    .groupBy("account_id")
    .agg(sum("amount"))
    .show())

# Spark UI shows:
# - 120s total (5min job takes 2min execution)
# - Stage 0 (filter): 2s ✓ Fast
# - Stage 1 (shuffle): 118s ✗ Slow - CHECK THIS
# - Task histogram: Most tasks 300ms, one task 80,000ms → SKEW

# Diagnosis: Data skew on shuffle
# Fix: Salt the groupBy key
```

**Monitoring Checklist**:
- [ ] Total job time reasonable?
- [ ] Any stages taking >80% of time? (Investigate that stage)
- [ ] Task duration histogram balanced or skewed?
- [ ] Executor memory usage balanced?
- [ ] Shuffle bytes excessive relative to input?
- [ ] GC time >20%? (Memory pressure)

---

### Q5: Data Skew - Detection and Solutions

**Question**: How do you detect and handle data skew in PySpark? Describe 3+ solutions with code.

**Answer**:

**Data Skew Definition**:
- Data distributed unevenly across partitions
- Some executors process much more data than others
- Causes some tasks to take 100x longer than others
- Common in financial data: Customer IDs, trader IDs often skewed

**Detection Method 1: Partition Row Counts**:

```python
from pyspark.sql.functions import spark_partition_id

# Count rows per partition
partition_stats = df.groupBy(spark_partition_id()).count().collect()

# Analyze
row_counts = [row[1] for row in partition_stats]
max_count = max(row_counts)
min_count = min(row_counts)
skew_ratio = max_count / min_count if min_count > 0 else float('inf')

print(f"Skew Ratio: {skew_ratio:.2f}x")
# Ratio > 2.0 indicates skew
```

**Detection Method 2: Analyze Specific Columns**:

```python
# Which keys are causing skew?
skew_analysis = (df
    .groupBy("account_id")
    .agg(count("*").alias("record_count"))
    .orderBy(desc("record_count"))
    .show(10))

# If top key has 80% of data → SKEW
```

**Detection Method 3: Spark UI (Task Duration Histogram)**:
- View Jobs → Stages → Task Details
- If histogram is skewed (most tasks 100ms, some 10,000ms) → Skew

**Solution 1: Salting**:

```python
from pyspark.sql.functions import rand, concat, lit

# Add random salt to skewed column
def salt_dataframe(df, salt_column, num_salts=10):
    return df.withColumn(
        f"{salt_column}_salted",
        concat(col(salt_column), lit("_"), (rand() * num_salts).cast("int"))
    )

df_salted = salt_dataframe(df, "account_id", num_salts=10)

# Now groupBy uses salted column
result = (df_salted
    .groupBy("account_id_salted")
    .agg(sum("amount").alias("total"))
    .withColumn("account_id", regexp_replace("account_id_salted", "_\\d+$", ""))
    .groupBy("account_id")
    .agg(sum("total"))
)

# Pros: Works well, flexible
# Cons: Need to un-salt results, adds complexity
```

**Solution 2: Repartitioning**:

```python
# Increase partitions for better distribution
# Rule: 2-4 partitions per core

df_repartitioned = df.repartition(200, "account_id")

result = (df_repartitioned
    .groupBy("account_id")
    .agg(sum("amount"))
)

# Pros: Simple
# Cons: Full shuffle (expensive), may not help if key naturally skewed
```

**Solution 3: Use Skew Hint (Spark 3.0+)**:

```python
from pyspark.sql.functions import hint

# Tell Spark to handle skew
left = df1.hint("skew", "account_id")
right = df2

result = left.join(right, "account_id")

# For joins specifically - Spark 3+ AQE handles automatically
# Adaptive Query Execution (AQE) detects and handles skew

spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
```

**Solution 4: Broadcast Small DataFrame**:

```python
from pyspark.sql.functions import broadcast

# For joins where one side is small
small_df = spark.read.parquet("small_lookup_table")  # < 1GB
large_df = spark.read.parquet("large_trades")

# Broadcast small table to all executors
result = large_df.join(broadcast(small_df), "account_id")

# Avoids shuffle, extremely efficient
# Use when join creates skew
```

**Production Pattern - Holistic Skew Handling**:

```python
# Configuration
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
spark.conf.set("spark.sql.shuffle.partitions", "200")  # Default partitions after shuffle

# Load data
trades = spark.read.parquet("trades")

# Pre-aggregation if needed to reduce skew before groupBy
trades_reduced = trades.groupBy("account_id").agg(sum("amount"), count("*"))

# Use hints for known skew
trades_skewed = trades.hint("skew", "account_id")

# Execute
result = trades_skewed.groupBy("account_id").agg(sum("amount"))

# Monitor with Spark UI
```

**Interview Points**:
- Skew is #1 production issue in PySpark
- Multiple solutions, choose based on situation
- Salting works for groupBy, broadcast works for joins
- AQE (Spark 3.0+) automates much of this
- Always monitor Spark UI for skew

---

### Q6: Catalyst Optimizer - How It Helps You

**Question**: Explain Catalyst optimizer and 2-3 ways it optimizes queries that you rely on.

**Answer**:

**Catalyst Purpose**:
- Spark's SQL query optimizer
- Applies rule-based and cost-based optimizations
- Works on DataFrames/Spark SQL, not RDDs
- Key reason DataFrames are faster than RDDs

**Optimization 1: Predicate Pushdown**:

```python
# Original query (without pushdown)
df = spark.read.parquet("huge_table")  # Read entire table
filtered = df.filter(col("date") == "2024-01-15")  # Filter after
result = filtered.select("user_id", "amount")

# What Catalyst does
# Pushed filter to Parquet reader → Only reads partitions matching date=2024-01-15
# Reads 1 partition instead of 365 partitions!

# Cost savings: 99% less data scanned
```

**Optimization 2: Column Pruning**:

```python
# Original
df = spark.read.parquet("table")
result = df.select("user_id", "amount")

# Catalyst recognizes you only need 2 columns
# Doesn't read other 50 columns from Parquet
# Parquet is columnar, so this is huge!

# Benefit: 98% less I/O for 2 column selection from 100-column table
```

**Optimization 3: Constant Folding & Early Filtering**:

```python
# Original
df = df.filter((col("price") > 100) | (col("price") < -50))
df = df.filter(col("amount") > 0)  # Amount can't be < -50

# Catalyst simplifies:
# - Recognizes amount > 0 always removes the col("price") < -50 branch
# - Folds constants: evaluates col("price") > 100 decision at optimization time

df_optimized = df.filter(col("price") > 100)
```

**Optimization 4: Join Reordering**:

```python
# Your query
result = (trades
    .join(accounts, "account_id")  # 1M records × 50k records
    .join(transactions, "transaction_id")  # 50k records × 100k records
)

# Catalyst reorders:
# - First join: transactions × accounts (smaller × medium) 
# - Then join with trades (result × 1M)
# Orders joins for minimal intermediate data size

# Impact: 10x-100x faster for same result
```

**Optimization 5: Common Sub-expression Elimination**:

```python
# You write:
df_a = df.filter(col("status") == "ACTIVE").select("user_id", "amount")
df_b = df.filter(col("status") == "ACTIVE").select("user_id", "amount")
result = df_a.union(df_b)

# Catalyst recognizes same filter and select appear twice
# Executes once, reuses result

# Without this: Filter executed twice
```

**Watching Catalyst in Action**:

```python
# Explain plan shows optimizations
df_plan = (spark.read.parquet("trades")
    .filter(col("date") > "2024-01-01")
    .select("account_id", "amount")
)

# Show logical plan (before optimization)
df_plan.explain(mode="simple")

# Show optimized plan
df_plan.explain(mode="extended")

# Output shows:
# LogicalPlan: Raw SQL-like plan
# OptimizedLogicalPlan: After Catalyst optimizations
# PhysicalPlan: How it executes on cluster
```

**Output example**:
```
OptimizedLogicalPlan shows:
- PushedFilters: [date > 2024-01-01]  # Predicate pushed to source
- PushedProjection: [account_id, amount]  # Column pruning
```

**Production Pattern - Leverage Catalyst**:

```python
# GOOD: Use DataFrames, Catalyst handles optimization
df = spark.read.parquet("trades")
result = df.filter(col("date") >= "2024-01-01").select("account_id", "amount")

# AVOID: Custom RDD logic that bypasses Catalyst
trades_rdd = spark.read.parquet("trades").rdd
# Now Catalyst can't optimize - manual tuning required

# PREFER: Let Spark SQL optimize
df.createOrReplaceTempView("trades")
spark.sql("SELECT account_id, amount FROM trades WHERE date >= '2024-01-01'")
# Catalyst optimizes this
```

**Interview Points**:
- Catalyst is why DataFrames > RDDs for performance
- Predicate pushdown: Critical for partitioned tables
- Column pruning: Essential for large column count tables
- Cost-based optimization: Chooses best join strategy
- Don't try to outthink Catalyst - usually wrong

---

## Data Skew - The Critical Problem

(See Q5 for comprehensive treatment)

---

## Advanced Transformations

### Q7: Window Functions - Real World Financial Example

**Question**: Write a window function query to detect anomalies in transaction patterns. Calculate 30-day rolling average and flag transactions >2 std devs from average.

**Answer**:

```python
from pyspark.sql.functions import (
    window, avg, stddev, row_number, lag, lead,
    sum as spark_sum, count as spark_count
)
from pyspark.sql import Window as WindowSpec

# Sample transaction data
transactions = spark.read.parquet("transactions")

# 1. Calculate 30-day rolling window metrics
spec_30d = WindowSpec.partitionBy("account_id").orderBy("transaction_date").rangeBetween(-30*24*3600, 0)

rolling_stats = transactions.withColumn(
    "amt_30d_avg", avg("amount").over(spec_30d)
).withColumn(
    "amt_30d_stddev", stddev("amount").over(spec_30d)
)

# 2. Flag anomalies (>2 stddev from mean)
anomalies = rolling_stats.withColumn(
    "z_score", (col("amount") - col("amt_30d_avg")) / col("amt_30d_stddev")
).withColumn(
    "is_anomaly", col("z_score").between(-2, 2) == False
)

# 3. Include previous and next transaction for context
context_spec = WindowSpec.partitionBy("account_id").orderBy("transaction_date")

with_context = anomalies.withColumn(
    "prev_amount", lag("amount").over(context_spec)
).withColumn(
    "next_amount", lead("amount").over(context_spec)
).withColumn(
    "prev_date", lag("transaction_date").over(context_spec)
)

# 4. Filter to anomalies and select relevant columns
anomaly_report = (with_context
    .filter(col("is_anomaly"))
    .select(
        "account_id",
        "transaction_date",
        "amount",
        col("amt_30d_avg").alias("rolling_avg"),
        col("amt_30d_stddev").alias("rolling_stddev"),
        col("z_score").alias("zscore"),
        col("prev_amount").alias("prev_transaction_amount"),
        col("prev_date").alias("days_since_prev")
    )
)

anomaly_report.show()
```

**Key Window Function Concepts**:

```python
# PARTITION BY: Group rows
# ORDER BY: Order within partition
# rangeBetween/rowsBetween: Define window frame

# Common patterns:

# 1. Running total
spec = WindowSpec.partitionBy("account_id").orderBy("date").rowsBetween(
    WindowSpec.unboundedPreceding, 0
)
running_total = df.withColumn("cumulative_amount", spark_sum("amount").over(spec))

# 2. Moving average (last 7 rows)
spec = WindowSpec.partitionBy("account_id").orderBy("date").rowsBetween(-7, 0)
moving_avg = df.withColumn("7day_avg", avg("amount").over(spec))

# 3. Time-based window (last 30 days)
# Use rangeBetween with unix_timestamp
spec = WindowSpec.partitionBy("account_id").orderBy("timestamp").rangeBetween(
    -30*24*3600, 0
)

# 4. Rank and row_number
spec = WindowSpec.partitionBy("account_id").orderBy(desc("amount"))
ranked = df.withColumn("rank", row_number().over(spec))
```

**Performance Considerations**:

```python
# Window functions trigger shuffle if PARTITION BY is used
# For each partition, calculates expensive aggregations
# Large partitions → Slow

# Optimization:
# 1. Filter before window (reduce data)
trades_recent = trades.filter(col("date") >= "2024-01-01")

# 2. Partition on key that balances data
# Bad: df.withColumn(...).over(WindowSpec.partitionBy("rare_key"))
# Good: df.withColumn(...).over(WindowSpec.partitionBy("balanced_key"))

# 3. Use rangeBetween carefully (expensive for large ranges)
# Bad: rangeBetween(-365*24*3600, 0)  # 1 year rolling
# Good: rangeBetween(-30*24*3600, 0)  # 30 day rolling

# 4. Cache if reusing multiple window specs
df_cached = df.cache()
```

---

### Q8: Handling Semi-Structured Data (JSON)

**Question**: You receive JSON trading data with nested structures. Write code to flatten, validate, and load into a relational structure.

**Answer**:

```python
from pyspark.sql.functions import (
    col, from_json, schema_of_json, explode, 
    when, coalesce, get_json_object
)
from pyspark.sql.types import *

# Sample JSON trading data:
# {
#   "trade_id": "T123",
#   "trader": {"id": "TRADER_01", "name": "John"},
#   "details": {
#     "symbol": "AAPL",
#     "quantity": 1000,
#     "price": 150.25
#   },
#   "fees": [
#     {"type": "commission", "amount": 25.00},
#     {"type": "tax", "amount": 10.00}
#   ]
# }

# 1. Define explicit schema for validation
trade_schema = StructType([
    StructField("trade_id", StringType(), False),
    StructField("timestamp", TimestampType(), True),
    StructField("trader", StructType([
        StructField("id", StringType(), False),
        StructField("name", StringType(), True)
    ]), False),
    StructField("details", StructType([
        StructField("symbol", StringType(), False),
        StructField("quantity", IntegerType(), False),
        StructField("price", DoubleType(), False)
    ]), False),
    StructField("fees", ArrayType(StructType([
        StructField("type", StringType(), False),
        StructField("amount", DoubleType(), False)
    ])), True)
])

# 2. Read JSON with schema
raw_trades = spark.read.schema(trade_schema).json("trades.json")

# 3. Flatten nested structures
flattened_trades = raw_trades.select(
    col("trade_id"),
    col("timestamp"),
    col("trader.id").alias("trader_id"),
    col("trader.name").alias("trader_name"),
    col("details.symbol").alias("symbol"),
    col("details.quantity").alias("quantity"),
    col("details.price").alias("price"),
    col("details.quantity") * col("details.price"),
    col("details.price").alias("gross_amount")
)

# 4. Handle array fields (fees) - explode and pivot
fees_exploded = raw_trades.select(
    col("trade_id"),
    explode("fees").alias("fee")
).select(
    col("trade_id"),
    col("fee.type").alias("fee_type"),
    col("fee.amount").alias("fee_amount")
)

# Pivot fees into columns
fees_pivoted = fees_exploded.groupBy("trade_id").pivot("fee_type").sum("fee_amount")

# 5. Join back to main table
final_trades = flattened_trades.join(
    fees_pivoted,
    "trade_id",
    "left"
).select(
    col("trade_id"),
    col("timestamp"),
    col("trader_id"),
    col("trader_name"),
    col("symbol"),
    col("quantity"),
    col("price"),
    col("gross_amount"),
    coalesce(col("commission"), lit(0)).alias("commission_fee"),
    coalesce(col("tax"), lit(0)).alias("tax_fee")
)

# 6. Validation checks
invalid_trades = final_trades.filter(
    (col("quantity") <= 0) |
    (col("price") <= 0) |
    (col("trader_id").isNull())
)

valid_trades = final_trades.filter(
    (col("quantity") > 0) &
    (col("price") > 0) &
    (col("trader_id").isNotNull())
)

print(f"Valid: {valid_trades.count()}, Invalid: {invalid_trades.count()}")

# 7. Load to warehouse
valid_trades.write.mode("append").parquet("trades_warehouse")
invalid_trades.write.mode("append").parquet("trades_invalid_log")
```

**Handling Malformed JSON**:

```python
# Option 1: Permissive mode (skip errors)
df = spark.read.option("mode", "PERMISSIVE").json("trades.json")

# Option 2: Strict mode (fail on error)
df = spark.read.option("mode", "FAILFAST").json("trades.json")

# Option 3: Use try-catch with from_json
from pyspark.sql.functions import from_json, col

json_strings = spark.read.text("trades_raw.txt")

parsed = json_strings.select(
    from_json(col("value"), trade_schema).alias("trade")
)

# Handle null (parsing failures)
valid_trades = parsed.filter(col("trade").isNotNull()).select("trade.*")
```

---

## Streaming with Structured Streaming

### Q9: Real-Time Streaming Pipeline - Deutsche Börse Use Case

**Question**: Design a real-time streaming pipeline for market tick data. Handle late arriving events, exactly-once semantics, and state management.

**Answer**:

```python
from pyspark.sql.functions import (
    col, from_json, window, sum as spark_sum,
    last, count as spark_count, avg, desc
)
from pyspark.sql.types import *

# Schema for market ticks
tick_schema = StructType([
    StructField("timestamp", TimestampType(), False),
    StructField("symbol", StringType(), False),
    StructField("bid_price", DoubleType(), False),
    StructField("ask_price", DoubleType(), False),
    StructField("bid_size", IntegerType(), False),
    StructField("ask_size", IntegerType(), False),
    StructField("exchange", StringType(), False)
])

# 1. Read from Kafka (streaming source)
ticks = spark.readStream.format("kafka").option(
    "kafka.bootstrap.servers", "kafka:9092"
).option(
    "subscribe", "market_ticks"
).option(
    "startingOffsets", "latest"
).load().select(
    from_json(col("value").cast("string"), tick_schema).alias("tick")
).select(
    col("tick.*")
)

# 2. Handle late arriving data
# Watermark: Allow 10 minutes late data, drop after
ticks_watermarked = ticks.withWatermark("timestamp", "10 minutes")

# 3. Time window aggregation (1-minute OHLC)
ohlc = ticks_watermarked.groupBy(
    window(col("timestamp"), "1 minute", "30 seconds"),  # 1 min window, slide every 30s
    col("symbol")
).agg(
    first(col("bid_price")).alias("open"),
    max(col("ask_price")).alias("high"),
    min(col("bid_price")).alias("low"),
    last(col("ask_price")).alias("close"),
    spark_sum(col("bid_size")).alias("total_bid_volume"),
    spark_sum(col("ask_size")).alias("total_ask_volume"),
    spark_count("*").alias("tick_count")
)

# 4. Stateful aggregation - tracking price changes per symbol
# Track the spread over time
spread_trend = ticks_watermarked.withColumn(
    "spread", col("ask_price") - col("bid_price")
).groupBy(
    window(col("timestamp"), "5 minutes"),
    col("symbol")
).agg(
    avg(col("spread")).alias("avg_spread"),
    col("spread").alias("current_spread")  # Gets last value
)

# 5. Anomaly detection - flag unusual spreads
anomalies = spread_trend.filter(
    col("current_spread") > col("avg_spread") * 2  # >2x spread
)

# 6. Write outputs

# Output 1: OHLC to Kafka for downstream processing
ohlc_query = (ohlc.select("window", "symbol", "open", "high", "low", "close")
    .writeStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "kafka:9092")
    .option("topic", "ohlc_1min")
    .option("checkpointLocation", "/path/checkpoint_ohlc")
    .start()
)

# Output 2: Anomalies to real-time DB (e.g., Redis)
anomalies_query = (anomalies
    .writeStream
    .foreachBatch(lambda df, batch_id: write_to_redis(df))
    .option("checkpointLocation", "/path/checkpoint_anomalies")
    .start()
)

# Output 3: Dashboard materialized view
ohlc_latest = (ohlc.select("symbol", "window.end", "close", "total_bid_volume")
    .writeStream
    .format("parquet")
    .option("path", "hdfs://data/ohlc_latest")
    .option("checkpointLocation", "/path/checkpoint_dashboard")
    .outputMode("update")  # Only write updates
    .partitionBy("symbol")
    .start()
)

# 7. Await all queries
spark.streams.awaitAnyTermination()

def write_to_redis(df):
    """Write DataFrame to Redis for real-time dashboard"""
    for row in df.collect():
        redis_client.hset(
            f"anomaly:{row.symbol}",
            mapping={
                "spread": row.current_spread,
                "avg_spread": row.avg_spread,
                "timestamp": str(row.window)
            }
        )
```

**Key Streaming Concepts**:

```python
# 1. Watermarking: Allow late data within window
df.withWatermark("timestamp", "10 minutes")
# Allows data 10 minutes late, then drops

# 2. Output modes:
# - append: Only new rows (default)
# - update: Changed rows
# - complete: All rows

# 3. Trigger modes:
.option("trigger.processingTime", "10 seconds")  # Trigger every 10s
.option("trigger.once", True)  # Single batch
.option("trigger.continuous", "1 second")  # Continuous (experimental)

# 4. Checkpointing: Exactly-once semantics
.option("checkpointLocation", "/path/checkpoint")
# Stores offset, state information

# 5. Stateless vs Stateful:
# Stateless: map, filter (no state needed)
# Stateful: groupBy, window (maintains state across batches)
```

---

## Join Strategies & Optimization

### Q10: Join Optimization - Broadcast vs Shuffle vs SortMerge

**Question**: Compare broadcast join, shuffle join, and sort-merge join. For a 1TB trades table and 50MB accounts table, which would you use and why?

**Answer**:

**Join Strategy Comparison**:

| Strategy | Data Movement | Memory | Best For |
|----------|---------------|--------|----------|
| **Broadcast** | Small table → executors | < 2GB | One table very small |
| **Hash Join** | Full shuffle | Both tables | Medium datasets |
| **Sort-Merge** | Pre-sorted shuffle | Low | Large tables, both similar size |

**Scenario: 1TB trades × 50MB accounts**

```python
from pyspark.sql.functions import broadcast

trades = spark.read.parquet("trades_1tb")  # 1TB
accounts = spark.read.parquet("accounts_50mb")  # 50MB

# CORRECT APPROACH 1: Broadcast (accounts is small)
result = trades.join(
    broadcast(accounts),
    trades.account_id == accounts.account_id
)

# Why: 
# - Accounts (50MB) sent once to each executor
# - Trades (1TB) stays in place
# - No shuffle needed!
# - Performance: Seconds

# AVOID - Full shuffle:
result = trades.join(accounts, "account_id")
# Would shuffle both tables (1TB + 50MB) across network
# Performance: Minutes
```

**Broadcast Join Details**:

```python
# Broadcasting works when:
# 1. Small table < 2GB (configurable with spark.sql.broadcastTimeout)
# 2. Fits in executor memory
# 3. Can afford network cost of sending to all executors

# Spark auto-broadcasts tables < broadcast threshold
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "100M")

# Auto broadcast happens:
trades.join(small_lookup, "key")  # Automatic broadcast

# Manual broadcast (if auto didn't work):
trades.join(broadcast(small_lookup), "key")

# Check execution plan:
trades.join(broadcast(accounts), "key").explain()
# Should show "BroadcastHashJoin" in plan
```

**Sort-Merge Join** (When both tables are large):

```python
# Scenario: 1TB trades × 500GB reference_data
trades = spark.read.parquet("trades")
ref_data = spark.read.parquet("ref_data")

# Pre-sort both tables on join key
trades_sorted = trades.sortBy("symbol")
ref_sorted = ref_data.sortBy("symbol")

# Join (exploits sorted order)
result = trades_sorted.join(ref_sorted, "symbol")

# Why:
# - Both tables already sorted on join key
# - No shuffle needed (if co-partitioned)
# - Merges already-sorted sequences
# - Memory efficient

# Cost: Pre-sorting + merge
```

**Hash Join** (Shuffle-based):

```python
# Default join strategy for medium-sized tables
trades = spark.read.parquet("trades")  # 100GB
daily_stats = spark.read.parquet("stats")  # 50GB

result = trades.join(daily_stats, "account_id")

# What happens:
# 1. Shuffle trades by account_id (100GB across network)
# 2. Shuffle daily_stats by account_id (50GB across network)
# 3. Co-locate matching records on same executors
# 4. Join hashed buckets

# Very expensive for large tables!
```

**Join Optimization Strategy Guide**:

```python
# Step 1: Check if one side is < broadcast threshold
if large_table.rdd.getNumPartitions() > small_table.rdd.getNumPartitions() * 100:
    # Very skewed sizes - likely broadcast candidate
    result = large_table.join(broadcast(small_table), key)

# Step 2: Check if tables are pre-partitioned
if trades.partitions == accounts.partitions:
    # Same partition scheme - sort-merge more efficient
    result = trades.join(accounts, "key")  # Avoids shuffle

# Step 3: For complex joins, use hints
from pyspark.sql.functions import hint

result = (trades
    .hint("broadcast")  # Force broadcast
    .join(accounts, "key")
)

result = (trades
    .hint("merge")  # Force sort-merge
    .join(accounts, "key")
)

# Step 4: Monitor Spark UI
# - Exchange (shuffle): Expensive
# - BroadcastExchange: Cheap
# - SortMergeJoin: Efficient if pre-sorted
```

**Real Financial Pipeline Example**:

```python
# Trade execution system
trades = spark.read.parquet("live_trades")  # Hot table, hundreds of GB
pricing = spark.read.parquet("current_pricing")  # 100MB lookup
risk_limits = spark.read.parquet("risk_rules")  # 50MB lookup
trader_info = spark.read.parquet("traders")  # 10MB lookup

# Optimization:
# 1. Broadcast all small tables
# 2. Hash join with trades (large table)

enriched = (trades
    .join(broadcast(pricing), "symbol")
    .join(broadcast(risk_limits), "product_type")
    .join(broadcast(trader_info), "trader_id")
)

# Result: Single broadcast per small table
# vs. Shuffling entire 500GB trades table multiple times
```

---

## Memory Management & Execution

### Q11: Out of Memory (OOM) Errors - Root Causes and Fixes

**Question**: Your Spark job fails with "OutOfMemoryError: Java heap space". Walk through diagnostics and fixes.

**Answer**:

**Root Causes of OOM**:

1. **Too Many Partitions Per Executor**:
```python
# Problem: 1000 partitions, 4 executors
# 250 tasks per executor in memory simultaneously
df.repartition(1000)  # Too aggressive

# Each partition data + task overhead + shuffle buffers
# → Executor heap fills up

# Fix:
optimal_partitions = num_executors * cores_per_executor * 3
# Example: 4 executors × 4 cores × 3 = 48 partitions
df.repartition(48)
```

2. **Collect() on Large DataFrames**:
```python
# PROBLEM - collects all data to driver
large_df.collect()  # If large_df is 100GB, driver needs 100GB+ heap

# Driver is single JVM, usually 4GB-8GB memory
# Cannot hold more than driver's max memory

# Fix:
# Option 1: Take sample
large_df.limit(1000).collect()

# Option 2: Use foreach/foreachPartition
large_df.foreach(lambda row: process(row))

# Option 3: Write to storage instead
large_df.write.parquet("output")
```

3. **Shuffle Memory Pressure**:
```python
# Shuffle happens during:
# - groupBy, reduceByKey
# - join (unless broadcast)
# - repartition

# During shuffle, Spark holds data in hash tables
# If too much data → memory overflow

df.groupBy("key").agg(sum("value"))  # Shuffle

# Fix: Increase executor memory
spark.executor.memory = "8g"  # Default 1g, increase if OOM

# Or reduce data before shuffle:
df.filter(col("date") > "2024-01-01").groupBy(...).agg(...)  # Filter first!
```

4. **Broadcast Variable Too Large**:
```python
# Problem
lookup = large_df.collect()  # 500MB
broadcast_var = sc.broadcast(lookup)  # Broadcast to executors

# Executor memory = base + broadcast + partition data
# 500MB broadcast × 10 executors = 5GB memory needed

# Fix:
# Option 1: Don't broadcast, use join instead
trades.join(broadcast(small_lookup), "key")

# Option 2: Broadcast smarter - only needed data
needed_cols = large_df.select("id", "value")
broadcast_var = sc.broadcast(needed_cols.collect())
```

5. **Cache/Persist Accumulation**:
```python
# Problem
df1.cache()
df2.cache()
df3.cache()
df4.cache()
df5.cache()  # Each cached, all in memory

# Fix: Only cache what you reuse
df_frequently_used.cache()

# Clear cache when done
df_frequently_used.unpersist()
spark.catalog.clearCache()
```

**Diagnostic Steps**:

```python
# Step 1: Check Spark UI - Executors tab
# - Memory Used vs Memory Available
# - If executor shows 7GB used with 8GB allocated → OOM soon

# Step 2: Examine Spark logs
# Look for:
# - "OutOfMemoryError: Java heap space"
# - Which executor failed?
# - What operation?

# Step 3: Check memory config
spark.conf.get("spark.executor.memory")  # Should be 2g+ for real workloads

# Step 4: Analyze partition count
df.getNumPartitions()  # Too high?

# Step 5: Check for large collect()
grep "collect()" code  # Any collect on large DataFrames?
```

**Fix Strategy**:

```python
# Before running large job:

# 1. Configure executor memory
spark.conf.set("spark.executor.memory", "4g")

# 2. Adjust shuffle memory
spark.conf.set("spark.shuffle.memoryFraction", "0.3")  # 30% for shuffle

# 3. Set appropriate partitions
optimal_partitions = 4 * 4 * 3  # Assuming 4 executors, 4 cores
df = spark.read.parquet(...).repartition(optimal_partitions)

# 4. Filter early
df = df.filter(col("date") > "2024-01-01")  # Reduce data before shuffle

# 5. Avoid collect()
# Instead of:
#   results = df.collect()
# Use:
#   df.write.parquet("results")

# 6. Cache selectively
df_hot = df.cache()  # Only if reused 3+ times

# 7. Monitor
df.explain()  # Check physical plan for expensive operations
```

---

### Q12: Executor Configuration - Getting it Right

**Question**: Configure Spark for optimal performance given: 4 nodes, 16 cores/node, 64GB RAM/node. Explain trade-offs.

**Answer**:

**Available Resources**:
```
Total: 4 nodes × 16 cores × 64GB = 64 cores, 256GB RAM
```

**Configuration**:

```python
spark = SparkSession.builder \
    .config("spark.executor.instances", "8") \
    .config("spark.executor.cores", "4") \
    .config("spark.executor.memory", "12g") \
    .config("spark.driver.cores", "4") \
    .config("spark.driver.memory", "2g") \
    .config("spark.dynamicAllocation.enabled", "false") \
    .getOrCreate()
```

**Explanation of Configuration**:

**Executor Count: 8**
```
Calculation:
- 4 nodes × 16 cores/node = 64 total cores
- 1-2 cores reserved for OS → 62-63 usable cores
- 1 executor left for driver → 62/8 = 7-8 executors/node → 56-64 total

Option 1: 8 executors × 4 cores each = 32 cores parallelism
Option 2: 4 executors × 8 cores each = 32 cores parallelism

Choose: 8 executors (better parallelism distribution)
```

**Cores per Executor: 4**
```
Why not 16?
- Too many cores → CPU context switching
- Threshold: 4-8 cores per executor ideal
- More cores doesn't help if threads can't all run

With 4 cores: 8 executors × 4 cores = 32 concurrent tasks
- Good parallelism for 64 cores total
- Each task gets dedicated CPU time
```

**Memory per Executor: 12GB**
```
Calculation:
- Total available: 64GB/node × 4 nodes = 256GB
- Driver: ~2GB
- Available for executors: ~254GB
- Per executor: 254GB / 8 = ~32GB
- But leave headroom for OS, shuffle, GC
- Practical: 12GB per executor

Why not 32GB?
- Large heaps → longer GC pauses
- 12GB is reasonable balance
```

**Driver Configuration**:
```
- Cores: 4 (driver doesn't do heavy computation)
- Memory: 2g (enough for orchestration, metadata)
- Should not receive large data (avoid collect())
```

**Alternative Configurations**:

```python
# Configuration A: Fewer large executors
spark.executor.instances = 4
spark.executor.cores = 8
spark.executor.memory = "16g"
# Pros: Simpler, easier to manage
# Cons: Less parallelism if tasks are small

# Configuration B: Many small executors (Hadoop style)
spark.executor.instances = 16
spark.executor.cores = 2
spark.executor.memory = "8g"
# Pros: Maximum parallelism
# Cons: More shuffling overhead, more executors to manage

# Configuration C: Dynamic allocation
spark.dynamicAllocation.enabled = True
spark.dynamicAllocation.minExecutors = 2
spark.dynamicAllocation.maxExecutors = 16
spark.dynamicAllocation.executorIdleTimeout = 60s
# Pros: Scales with load, cost-efficient
# Cons: Adds scheduling overhead
```

**Recommended Configuration for Deutsche Börse**:

```python
# Financial institution - requires reliability + performance

spark = SparkSession.builder \
    .appName("DBG_DataPipeline") \
    .config("spark.executor.instances", "7") \  # 1 reserved for driver
    .config("spark.executor.cores", "4") \
    .config("spark.executor.memory", "12g") \
    .config("spark.driver.cores", "4") \
    .config("spark.driver.memory", "3g") \
    .config("spark.sql.shuffle.partitions", "200") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.dynamicAllocation.enabled", "false") \
    .config("spark.memory.fraction", "0.6") \  # 60% heap for Spark
    .config("spark.memory.storageFraction", "0.5") \  # 50% of Spark mem for cache
    .getOrCreate()

# Tuning explanation:
# - Fixed allocation (financial trading needs predictability)
# - 7 executors × 4 cores = 28 concurrent tasks
# - 12GB per executor allows 2-3 tasks concurrently
# - AQE enabled for adaptive optimization
```

**Monitoring the Configuration**:

```python
# In Spark UI - Executors tab:
# - Check if all executors are active
# - Monitor memory usage (should be < 90%)
# - Check if GC time is high (>20% bad)

# Adjust if:
# 1. Consistently running out of memory
#    → Reduce executor count, increase memory per executor
# 2. Executors idling
#    → Enable dynamic allocation or reduce executor count
# 3. High GC time
#    → Reduce memory per executor (smaller heap = faster GC)
```

---

## Production Patterns & Debugging

### Q13: Production Debugging - A Real Failure Scenario

**Question**: A Spark job runs fine in dev (100GB), fails in prod (10TB) with timeout after 6 hours. Diagnose and fix.

**Answer**:

**Investigation Steps**:

```python
# Step 1: Gather information
# - Original dev data: 100GB
# - Production data: 10TB (100x larger!)
# - Timeout: 6 hours
# - Error: Likely timeout, not OOM

# Step 2: Analyze Spark UI
# Look for:
# - Stages taking progressively longer
# - Specific stage consuming all time (e.g., shuffle)
# - Task failures and retries

# Step 3: Check logs for patterns
# - OutOfMemoryError? No → Not memory
# - Timeout exceptions? Yes → Slow execution
# - Shuffle output too large? Check shuffle metrics
```

**Hypothesis**: Shuffle taking too long due to 100x more data

```python
# Original logic
trades = spark.read.parquet("trades")
result = trades.groupBy("account_id").agg(sum("amount"))

# Problem:
# - Dev: 100GB / 200 partitions = 500MB per partition
# - Prod: 10TB / 200 partitions = 50GB per partition!!!
# - 50GB per partition → Shuffle is slow

# Fix: Scale partitions with data
# Rule: 2-4 partitions per core
# With 64 cores: 128-256 partitions optimal

# Calculate optimal partitions
data_size_gb = 10000  # 10TB
partition_size_mb = 200  # 200MB ideal per partition
optimal_partitions = (data_size_gb * 1024) // partition_size_mb  # ~51,000? Too many

# Better calculation:
num_cores = 64
partitions_per_core = 3
optimal_partitions = num_cores * partitions_per_core  # 192

# Optimized
trades = spark.read.parquet("trades").repartition(192)
result = trades.groupBy("account_id").agg(sum("amount"))
# Now: 10TB / 192 = 52GB per partition (still large but manageable)
```

**Root Cause**: Insufficient partitioning for data scale

```python
# Dev didn't hit this because:
# - 100GB with 200 partitions = OK
# - 10TB with 200 partitions = Bad (50GB per partition)

# The fix scales automatically
trades = spark.read.parquet("trades")
# Parquet has built-in partitions
# But groupBy creates new partitions based on spark.sql.shuffle.partitions (default 200)

# Solution 1: Increase shuffle partitions
spark.conf.set("spark.sql.shuffle.partitions", "500")
result = trades.groupBy("account_id").agg(sum("amount"))

# Solution 2: Pre-repartition
trades_repartitioned = trades.repartition(500, "account_id")
result = trades_repartitioned.groupBy("account_id").agg(sum("amount"))
# Combine with AQE
spark.conf.set("spark.sql.adaptive.enabled", "true")

# Solution 3: Adjust shuffle memory
spark.conf.set("spark.shuffle.memoryFraction", "0.4")  # 40% of memory for shuffle
# Allows bigger shuffle buffers

# Solution 4: Coalesce instead of repartition (if applicable)
# Repartition: Full shuffle
# Coalesce: Merge adjacent partitions (no shuffle)
if num_partitions > 1000:
    trades = trades.coalesce(500)  # Reduce partitions without shuffle
```

**Testing the Fix**:

```python
# Create 1TB test dataset (subset of prod)
test_trades = spark.read.parquet("trades").limit(1_000_000_000)

# Run with new config
spark.conf.set("spark.sql.shuffle.partitions", "500")
spark.conf.set("spark.sql.adaptive.enabled", "true")

result = test_trades.groupBy("account_id").agg(sum("amount"))

# Measure:
import time
start = time.time()
result.show()
elapsed = time.time() - start

# If 1TB takes ~30 seconds, 10TB should take ~300 seconds (5 min)
# Much better than 6-hour timeout!
```

**Production Deployment**:

```python
# Update Spark configuration for prod
# In spark-submit:

spark-submit \
    --conf spark.sql.shuffle.partitions=500 \
    --conf spark.sql.adaptive.enabled=true \
    --conf spark.sql.adaptive.skewJoin.enabled=true \
    --executor-memory 12g \
    --num-executors 8 \
    --executor-cores 4 \
    my_job.py

# Or in code:
spark = SparkSession.builder \
    .config("spark.sql.shuffle.partitions", "500") \
    .config("spark.sql.adaptive.enabled", "true") \
    .getOrCreate()
```

**Lessons for Principal Level**:
- Dev ≠ Prod: Always test with production-scale data
- Partitioning scales linearly: 10x data needs ~10x partitions
- AQE helps but isn't magic: Still need reasonable baseline config
- Monitor from day 1: Catch scaling issues early

---

### Q14: Data Quality & Validation in PySpark

**Question**: Design a data quality framework for market data pipelines. Include schema validation, anomaly detection, and error handling.

**Answer**:

```python
from pyspark.sql.functions import (
    col, when, count, sum as spark_sum, 
    min, max, stddev, row_number, isnan
)
from pyspark.sql.window import Window
from datetime import datetime

class DataQualityFramework:
    """Production-grade data quality validation"""
    
    def __init__(self, spark):
        self.spark = spark
        self.metrics = {}
    
    # 1. Schema Validation
    def validate_schema(self, df, expected_schema):
        """Ensure DataFrame matches expected schema"""
        actual_schema = df.schema
        errors = []
        
        for field in expected_schema:
            actual_field = next(
                (f for f in actual_schema if f.name == field.name),
                None
            )
            if not actual_field:
                errors.append(f"Missing column: {field.name}")
            elif actual_field.dataType != field.dataType:
                errors.append(
                    f"Wrong type for {field.name}: "
                    f"expected {field.dataType}, got {actual_field.dataType}"
                )
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    # 2. Null/Missing Value Checks
    def check_nulls(self, df, required_columns):
        """Detect missing values in critical columns"""
        null_stats = {}
        
        for col_name in required_columns:
            null_count = df.filter(col(col_name).isNull()).count()
            null_pct = (null_count / df.count()) * 100 if df.count() > 0 else 0
            
            null_stats[col_name] = {
                "null_count": null_count,
                "null_percentage": null_pct,
                "valid": null_pct < 1.0  # Allow <1% nulls
            }
        
        return null_stats
    
    # 3. Range & Bounds Checking
    def check_bounds(self, df, column, min_val, max_val):
        """Verify numeric values are within acceptable range"""
        out_of_bounds = df.filter(
            (col(column) < min_val) | (col(column) > max_val)
        )
        
        return {
            "column": column,
            "expected_min": min_val,
            "expected_max": max_val,
            "out_of_bounds_count": out_of_bounds.count(),
            "valid": out_of_bounds.count() == 0
        }
    
    # 4. Uniqueness Check
    def check_uniqueness(self, df, unique_columns):
        """Detect duplicate records"""
        total_count = df.count()
        unique_count = df.select(unique_columns).distinct().count()
        
        return {
            "columns": unique_columns,
            "total_records": total_count,
            "unique_records": unique_count,
            "duplicates": total_count - unique_count,
            "valid": total_count == unique_count
        }
    
    # 5. Statistical Anomaly Detection
    def detect_outliers(self, df, column, z_score_threshold=3.0):
        """Detect values beyond standard deviations"""
        stats = df.select(
            avg(col(column)).alias("mean"),
            stddev(col(column)).alias("stddev")
        ).collect()[0]
        
        mean = stats["mean"]
        stddev = stats["stddev"]
        
        if stddev is None or stddev == 0:
            return {
                "column": column,
                "status": "INVALID",
                "reason": "No variance in data"
            }
        
        outliers = df.withColumn(
            "z_score",
            (col(column) - mean) / stddev
        ).filter(
            abs(col("z_score")) > z_score_threshold
        )
        
        return {
            "column": column,
            "mean": mean,
            "stddev": stddev,
            "z_score_threshold": z_score_threshold,
            "outlier_count": outliers.count(),
            "outlier_percentage": (outliers.count() / df.count()) * 100
        }
    
    # 6. Timeliness Check
    def check_freshness(self, df, timestamp_column, max_lag_hours=1):
        """Verify data is recent (not stale)"""
        from pyspark.sql.functions import max as spark_max, current_timestamp
        
        latest = df.select(spark_max(col(timestamp_column))).collect()[0][0]
        now = datetime.now()
        lag_hours = (now - latest).total_seconds() / 3600
        
        return {
            "timestamp_column": timestamp_column,
            "latest_record": latest,
            "lag_hours": lag_hours,
            "max_allowed_lag_hours": max_lag_hours,
            "valid": lag_hours <= max_lag_hours
        }
    
    # 7. Referential Integrity
    def check_referential_integrity(self, df, column, reference_df, ref_column):
        """Verify foreign key relationships"""
        valid_keys = reference_df.select(col(ref_column)).distinct()
        
        invalid_records = df.join(
            valid_keys,
            df[column] == valid_keys[ref_column],
            "left_anti"
        )
        
        return {
            "foreign_key_column": column,
            "reference_table_column": ref_column,
            "invalid_count": invalid_records.count(),
            "valid": invalid_records.count() == 0
        }
    
    # 8. Comprehensive Quality Report
    def generate_quality_report(self, df, config):
        """Run all checks and generate report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "record_count": df.count(),
            "checks": {}
        }
        
        # Schema check
        schema_result = self.validate_schema(df, config["schema"])
        report["checks"]["schema"] = schema_result
        
        # Null checks
        null_results = self.check_nulls(df, config["required_columns"])
        report["checks"]["nulls"] = null_results
        
        # Bounds checks
        for col_name, bounds in config["bounds"].items():
            bounds_result = self.check_bounds(
                df, col_name, bounds["min"], bounds["max"]
            )
            report["checks"][f"bounds_{col_name}"] = bounds_result
        
        # Outliers
        for col_name in config["outlier_check_columns"]:
            outlier_result = self.detect_outliers(df, col_name)
            report["checks"][f"outliers_{col_name}"] = outlier_result
        
        # Overall status
        report["status"] = "VALID" if self._is_valid(report) else "INVALID"
        
        return report
    
    def _is_valid(self, report):
        """Determine overall validity"""
        for check_name, check_result in report["checks"].items():
            if isinstance(check_result, dict) and "valid" in check_result:
                if not check_result["valid"]:
                    return False
        return True

# Usage Example
config = {
    "schema": StructType([
        StructField("trade_id", StringType(), False),
        StructField("amount", DoubleType(), False),
        StructField("timestamp", TimestampType(), False),
    ]),
    "required_columns": ["trade_id", "amount"],
    "bounds": {
        "amount": {"min": 0, "max": 1e9},
        "quantity": {"min": 1, "max": 1e8}
    },
    "outlier_check_columns": ["amount"],
}

# Run quality framework
trades = spark.read.parquet("trades")
qc = DataQualityFramework(spark)
report = qc.generate_quality_report(trades, config)

# Log results
if report["status"] == "INVALID":
    print(f"Quality check FAILED: {report['checks']}")
    # Optionally: Skip this batch, alert team
else:
    print("Quality check PASSED")
    # Load to production warehouse
```

**Integration with Pipeline**:

```python
# Validate before loading to warehouse
trades = spark.read.parquet("raw_trades")
qc = DataQualityFramework(spark)
report = qc.generate_quality_report(trades, config)

if report["status"] == "VALID":
    trades.write.mode("append").parquet("trades_warehouse")
else:
    # Log invalid records
    invalid_records = trades.filter(...)  # Filter based on failures
    invalid_records.write.mode("append").parquet("trades_invalid")
    raise Exception(f"Data quality check failed: {report}")
```

---

## Summary of Key Concepts for Deutsche Börse Interview

**Must Know**:
1. ✅ Spark architecture: Driver/Executors
2. ✅ Lazy evaluation & Catalyst optimizer
3. ✅ DataFrame > RDD (almost always)
4. ✅ Data skew detection and solutions
5. ✅ Join strategies (broadcast, hash, sort-merge)
6. ✅ Window functions for time-series
7. ✅ Streaming with watermarks
8. ✅ Memory tuning & OOM debugging
9. ✅ Production patterns & monitoring
10. ✅ Data quality frameworks

**Advanced Topics**:
- Adaptive Query Execution (AQE)
- Delta Lake for ACID transactions
- ML feature stores
- Real-time streaming at scale

**For Principal Level**:
- Architecture thinking, not just coding
- Trade-off awareness
- Production insights
- Team mentorship & knowledge sharing

---

**Good luck with Deutsche Börse interview!** This material covers the depth expected at Principal level. Focus on understanding trade-offs and production realities, not just mechanics.
