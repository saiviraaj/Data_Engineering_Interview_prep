# 🎯 COMPLETE PYSPARK PATTERNS & STRATEGIES GUIDE
## Master Every PySpark Pattern for Senior Data Engineer Interviews

**Purpose:** Exhaustive reference for solving ANY PySpark problem  
**Level:** Senior Data Engineer and above  
**Coverage:** All functions, patterns, optimization techniques, when to use what

---

## 📚 TABLE OF CONTENTS

1. **PATTERN RECOGNITION FRAMEWORK** - How to identify which approach to use
2. **DATAFRAME OPERATIONS** - Complete function reference
3. **TRANSFORMATIONS** - Narrow vs Wide, when to use each
4. **WINDOW FUNCTIONS** - All patterns with examples
5. **JOINS** - All types, optimization strategies
6. **AGGREGATIONS** - GroupBy, pivot, complex aggregations
7. **PERFORMANCE OPTIMIZATION** - Comprehensive tuning guide
8. **CACHING & PERSISTENCE** - Storage levels, when to use
9. **PARTITIONING STRATEGIES** - Repartition vs coalesce
10. **BROADCAST & SKEW** - Handling data distribution issues
11. **UDF STRATEGIES** - When to use, how to optimize
12. **FILE FORMATS** - Parquet, ORC, CSV, JSON comparison
13. **MEMORY MANAGEMENT** - OOM errors, tuning
14. **REAL-WORLD PATTERNS** - Production scenarios

---

## 🎯 PART 1: PATTERN RECOGNITION FRAMEWORK

### **How to Identify Which Pattern to Use**

```
PROBLEM TYPE → PYSPARK PATTERN → KEY FUNCTIONS
```

#### **Recognition Decision Tree:**

```
├─ Need to compare rows within groups?
│  └─ YES → **WINDOW FUNCTIONS** (lag, lead, rank, row_number)
│
├─ Need to combine two DataFrames?
│  ├─ Small + Large → **BROADCAST JOIN**
│  ├─ Skewed data → **SALTING + JOIN**
│  └─ Regular → **STANDARD JOIN**
│
├─ Need to aggregate by groups?
│  ├─ Simple sum/count → **groupBy().agg()**
│  ├─ Multiple aggregations → **agg() with multiple funcs**
│  └─ Custom logic → **Pandas UDF**
│
├─ Need to transform each row independently?
│  ├─ Built-in function exists → **USE BUILT-IN** (fastest)
│  ├─ Simple logic → **when().otherwise()**
│  └─ Complex logic → **UDF (last resort)**
│
├─ DataFrame used multiple times?
│  └─ YES → **CACHE or PERSIST**
│
├─ Too many/few partitions?
│  ├─ Reduce partitions (after filter) → **coalesce()**
│  └─ Increase partitions (before heavy ops) → **repartition()**
│
├─ Memory issues?
│  ├─ Check partition sizes → **df.rdd.glom().map(len).collect()**
│  ├─ Reduce shuffle → **Broadcast, filter early**
│  └─ Increase executor memory → **spark.executor.memory**
│
└─ Reading/writing data?
   ├─ Big Data → **Parquet** (always)
   ├─ Human readable → **CSV, JSON**
   └─ Archive/compliance → **ORC, Avro**
```

### **Keywords to Pattern Mapping**

| **Keywords in Problem** | **Pattern to Use** | **Primary Functions** |
|------------------------|-------------------|---------------------|
| "filter", "where", "subset" | Filter | `filter()`, `where()` |
| "add column", "derive", "calculate" | Transform | `withColumn()`, `select()` |
| "join", "merge", "combine" | Join | `join()`, `broadcast()` |
| "group", "aggregate", "sum by" | GroupBy | `groupBy().agg()` |
| "rank", "top N", "order within group" | Window | `row_number()`, `rank()` |
| "running total", "cumulative" | Window | `sum().over()` |
| "previous", "next", "compare to last" | Window | `lag()`, `lead()` |
| "pivot", "cross-tab" | Pivot | `pivot()` |
| "deduplicate", "remove duplicates" | Dedup | `dropDuplicates()`, `row_number()` |
| "slow", "optimize", "performance" | Optimization | Cache, broadcast, partition |
| "out of memory", "OOM" | Memory | Partition size, cache, coalesce |
| "skewed", "unbalanced" | Skew | Salting, repartition |

---

## 📊 PART 2: DATAFRAME OPERATIONS - COMPLETE REFERENCE

### **2.1 Reading Data**

```python
from pyspark.sql import SparkSession
from pyspark.sql.types import *

spark = SparkSession.builder \
    .appName("DataEngineering") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .getOrCreate()

# ========== CSV ==========
# Basic read
df = spark.read.csv("data.csv", header=True, inferSchema=True)

# Production-ready (with schema)
schema = StructType([
    StructField("id", IntegerType(), False),  # False = NOT NULL
    StructField("name", StringType(), True),
    StructField("age", IntegerType(), True),
    StructField("salary", DoubleType(), True),
    StructField("hire_date", DateType(), True)
])

df = spark.read \
    .option("header", "true") \
    .option("delimiter", ",") \
    .option("quote", "\"") \
    .option("escape", "\\") \
    .option("mode", "DROPMALFORMED")  # Or PERMISSIVE, FAILFAST
    .schema(schema) \
    .csv("s3://bucket/data.csv")

# ========== Parquet (BEST for Big Data) ==========
df = spark.read.parquet("s3://bucket/data.parquet")

# With partition pruning
df = spark.read \
    .parquet("s3://bucket/partitioned_data") \
    .filter("year = 2024 AND month = 1")  # Pushes down to read

# ========== JSON ==========
df = spark.read.json("data.json")

# With schema
df = spark.read.schema(schema).json("data.json")

# Multi-line JSON
df = spark.read.option("multiline", "true").json("data.json")

# ========== Delta Lake (if available) ==========
df = spark.read.format("delta").load("s3://bucket/delta_table")

# ========== JDBC (Database) ==========
df = spark.read \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://host:5432/db") \
    .option("dbtable", "schema.table") \
    .option("user", "username") \
    .option("password", "password") \
    .option("driver", "org.postgresql.Driver") \
    .load()

# JDBC with partitioning (parallel reads)
df = spark.read \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://host:5432/db") \
    .option("dbtable", "sales") \
    .option("user", "user") \
    .option("password", "pass") \
    .option("partitionColumn", "id") \
    .option("lowerBound", "1") \
    .option("upperBound", "1000000") \
    .option("numPartitions", "10") \
    .load()
```

**When to use each format:**
- **Parquet**: Always for production (columnar, compressed, fast)
- **CSV**: Legacy systems, human-readable exports
- **JSON**: Semi-structured data, APIs
- **ORC**: Hive integration, write-heavy workloads
- **Delta**: ACID transactions, time travel, upserts

### **2.2 Selection & Projection**

```python
from pyspark.sql.functions import col, lit, concat

# ========== Select columns ==========
# Method 1: By name
df.select("name", "age", "salary")

# Method 2: Using col()
df.select(col("name"), col("age"), col("salary"))

# Method 3: Star expansion with additional columns
df.select("*", (col("salary") * 1.1).alias("increased_salary"))

# ========== Rename columns ==========
df.select(
    col("name").alias("employee_name"),
    col("age").alias("employee_age")
)

# Rename with withColumnRenamed
df.withColumnRenamed("old_name", "new_name")

# ========== Drop columns ==========
df.drop("column1", "column2")

# ========== Add/modify columns ==========
df.withColumn("bonus", col("salary") * 0.1)
df.withColumn("full_name", concat(col("first_name"), lit(" "), col("last_name")))

# Multiple columns at once
df.withColumns({
    "bonus": col("salary") * 0.1,
    "tax": col("salary") * 0.2,
    "net": col("salary") * 0.7
})
```

### **2.3 Filtering**

```python
from pyspark.sql.functions import col

# ========== Basic filtering ==========
df.filter(col("age") > 30)
df.where(col("age") > 30)  # Same as filter

# SQL string expression
df.filter("age > 30 AND city = 'NYC'")

# ========== Multiple conditions ==========
# AND
df.filter((col("age") > 30) & (col("city") == "NYC"))

# OR
df.filter((col("age") > 30) | (col("city") == "NYC"))

# NOT
df.filter(~(col("age") > 30))

# ========== IN / NOT IN ==========
df.filter(col("city").isin(["NYC", "LA", "SF"]))
df.filter(~col("city").isin(["NYC", "LA", "SF"]))

# ========== NULL filtering ==========
df.filter(col("email").isNull())
df.filter(col("email").isNotNull())

# ========== Between ==========
df.filter(col("age").between(25, 35))

# ========== String matching ==========
from pyspark.sql.functions import lower

df.filter(col("name").like("%John%"))  # SQL LIKE
df.filter(col("name").rlike("^John.*"))  # Regex
df.filter(col("name").startswith("John"))
df.filter(col("name").endswith("son"))
df.filter(col("name").contains("oh"))

# Case-insensitive
df.filter(lower(col("name")).contains("john"))
```

**⚡ Performance Tip:**
- Filter **EARLY** and **OFTEN** - pushes predicates down to source
- Use partition columns in filter for partition pruning
- Avoid UDFs in filters (breaks catalyst optimization)

---

## 🔄 PART 3: TRANSFORMATIONS - NARROW VS WIDE

### **3.1 Understanding Transformation Types**

**NARROW Transformations:**
- Each input partition contributes to **at most one** output partition
- No shuffle required
- Fast and efficient
- Examples: `map()`, `filter()`, `select()`, `withColumn()`

**WIDE Transformations:**
- Input partitions contribute to **multiple** output partitions
- Requires shuffle (expensive!)
- Data moves across network
- Examples: `groupBy()`, `join()`, `distinct()`, `repartition()`

```python
# ========== NARROW (Fast - No Shuffle) ==========
df.filter(col("age") > 30)              # Narrow
df.select("name", "age")                 # Narrow
df.withColumn("bonus", col("salary")*0.1) # Narrow
df.drop("column")                        # Narrow

# ========== WIDE (Slow - Requires Shuffle) ==========
df.groupBy("department").count()         # Wide - shuffle
df.join(other_df, "id")                  # Wide - shuffle
df.distinct()                            # Wide - shuffle
df.repartition(100)                      # Wide - shuffle
df.orderBy("salary")                     # Wide - shuffle
```

### **3.2 Complete Transformation Catalog**

```python
from pyspark.sql.functions import *

# ========== Map-like (1:1) ==========
df.withColumn("age_squared", col("age") ** 2)
df.withColumn("age_group", when(col("age") < 30, "young").otherwise("old"))

# ========== Filter (1:0 or 1:1) ==========
df.filter(col("salary") > 50000)

# ========== Union (N:N) ==========
df1.union(df2)  # All columns
df1.unionByName(df2)  # By column name
df1.unionByName(df2, allowMissingColumns=True)

# ========== Sample ==========
df.sample(fraction=0.1, seed=42)  # Random 10% sample
df.sample(withReplacement=True, fraction=0.1)

# ========== Limit ==========
df.limit(100)  # First 100 rows

# ========== Distinct ==========
df.distinct()  # All columns
df.dropDuplicates(["email"])  # Specific columns

# ========== Sort ==========
df.orderBy("salary")
df.orderBy(col("salary").desc())
df.orderBy(col("dept").asc(), col("salary").desc())
```

---

## 🪟 PART 4: WINDOW FUNCTIONS - COMPLETE GUIDE

### **4.1 All Window Function Patterns**

```python
from pyspark.sql.window import Window
from pyspark.sql.functions import *

# ========== RANKING FUNCTIONS ==========
window_rank = Window.partitionBy("department").orderBy(col("salary").desc())

df.withColumn("row_num", row_number().over(window_rank))
df.withColumn("rank", rank().over(window_rank))
df.withColumn("dense_rank", dense_rank().over(window_rank))
df.withColumn("quartile", ntile(4).over(window_rank))
df.withColumn("percent_rank", percent_rank().over(window_rank))

# ========== VALUE FUNCTIONS ==========
window_order = Window.partitionBy("user_id").orderBy("timestamp")

df.withColumn("prev_value", lag("amount", 1).over(window_order))
df.withColumn("next_value", lead("amount", 1).over(window_order))
df.withColumn("prev_2_values", lag("amount", 2, 0).over(window_order))  # Default 0

# FIRST_VALUE / LAST_VALUE (CRITICAL: Need full window!)
window_full = Window.partitionBy("user_id") \
    .orderBy("timestamp") \
    .rowsBetween(Window.unboundedPreceding, Window.unboundedFollowing)

df.withColumn("first_purchase", first_value("amount").over(window_full))
df.withColumn("last_purchase", last_value("amount").over(window_full))
df.withColumn("second_value", nth_value("amount", 2).over(window_full))

# ========== AGGREGATE FUNCTIONS ==========
# Running total
window_running = Window.partitionBy("user_id").orderBy("date")
df.withColumn("running_total", sum("amount").over(window_running))

# Moving average (7 days)
window_7day = Window.partitionBy("user_id") \
    .orderBy("date") \
    .rowsBetween(-6, 0)  # 6 preceding + current
df.withColumn("moving_avg_7day", avg("amount").over(window_7day))

# Centered moving average
window_centered = Window.orderBy("date").rowsBetween(-3, 3)
df.withColumn("centered_avg", avg("value").over(window_centered))

# Cumulative aggregations
df.withColumn("cumulative_sum", sum("amount").over(window_running))
df.withColumn("cumulative_avg", avg("amount").over(window_running))
df.withColumn("cumulative_max", max("amount").over(window_running))
df.withColumn("cumulative_count", count("*").over(window_running))
```

### **4.2 Common Window Patterns**

```python
# ========== Pattern 1: Running Totals ==========
window = Window.partitionBy("product").orderBy("date")
df.withColumn("running_sales", sum("sales").over(window))

# ========== Pattern 2: Moving Average ==========
window_ma = Window.partitionBy("stock").orderBy("date").rowsBetween(-29, 0)
df.withColumn("ma_30day", avg("price").over(window_ma))

# ========== Pattern 3: Rank Top N Per Group ==========
window_rank = Window.partitionBy("category").orderBy(col("revenue").desc())
df.withColumn("rank", row_number().over(window_rank)) \
    .filter(col("rank") <= 5)

# ========== Pattern 4: Compare to Previous ==========
window_lag = Window.partitionBy("product").orderBy("month")
df.withColumn("prev_month_sales", lag("sales").over(window_lag)) \
    .withColumn("mom_growth", 
        (col("sales") - col("prev_month_sales")) / col("prev_month_sales") * 100
    )

# ========== Pattern 5: Deduplication (Keep Latest) ==========
window_dedup = Window.partitionBy("user_id").orderBy(col("updated_at").desc())
df.withColumn("rn", row_number().over(window_dedup)) \
    .filter(col("rn") == 1) \
    .drop("rn")

# ========== Pattern 6: Gaps and Islands (Consecutive Sequences) ==========
from pyspark.sql.functions import date_sub

window_seq = Window.partitionBy("user_id").orderBy("login_date")
df.withColumn("rn", row_number().over(window_seq)) \
    .withColumn("date_diff", date_sub(col("login_date"), col("rn"))) \
    .groupBy("user_id", "date_diff") \
    .agg(
        min("login_date").alias("streak_start"),
        max("login_date").alias("streak_end"),
        count("*").alias("days_in_streak")
    )
```

---

## 🔗 PART 5: JOINS - ALL TYPES & OPTIMIZATION

### **5.1 Join Types**

```python
# ========== INNER JOIN (Default) ==========
df1.join(df2, "common_column")
df1.join(df2, df1.id == df2.id)

# ========== LEFT (LEFT OUTER) JOIN ==========
df1.join(df2, "common_column", "left")
# Keeps all rows from df1

# ========== RIGHT (RIGHT OUTER) JOIN ==========
df1.join(df2, "common_column", "right")
# Keeps all rows from df2

# ========== FULL (FULL OUTER) JOIN ==========
df1.join(df2, "common_column", "outer")
# Keeps all rows from both

# ========== SEMI JOIN (like SQL IN) ==========
df1.join(df2, "common_column", "semi")
# Returns rows from df1 where match exists in df2
# ONLY columns from df1

# ========== ANTI JOIN (like SQL NOT IN) ==========
df1.join(df2, "common_column", "anti")
# Returns rows from df1 with NO match in df2

# ========== CROSS JOIN (Cartesian Product) ==========
df1.crossJoin(df2)
# Every row in df1 × every row in df2
# USE WITH CAUTION!
```

### **5.2 Join Optimization Strategies**

```python
from pyspark.sql.functions import broadcast, col

# ========== 1. BROADCAST JOIN (Small table < 10MB) ==========
# Fastest join when one side is small
large_df.join(broadcast(small_df), "key")

# Check broadcast threshold
spark.conf.get("spark.sql.autoBroadcastJoinThreshold")  # Default: 10MB

# Manual control
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", 104857600)  # 100MB

# ========== 2. FILTER BEFORE JOIN ==========
# ❌ BAD
result = df1.join(df2, "key").filter("date >= '2024-01-01'")

# ✅ GOOD
df1_filtered = df1.filter("date >= '2024-01-01'")
result = df1_filtered.join(df2, "key")

# ========== 3. BUCKETING (Pre-shuffle) ==========
# Write with bucketing
df1.write \
    .bucketBy(100, "join_key") \
    .sortBy("join_key") \
    .saveAsTable("table1")

# Bucketed join (no shuffle!)
bucketed_df1 = spark.table("table1")
bucketed_df2 = spark.table("table2")
result = bucketed_df1.join(bucketed_df2, "join_key")

# ========== 4. SKEWED JOIN (Salting Technique) ==========
# When one key has too much data (skew)
from pyspark.sql.functions import rand, explode, array, lit

# Add salt to large table
large_df_salted = large_df.withColumn("salt", (rand() * 10).cast("int"))

# Replicate small table with all salt values
salt_values = array([lit(i) for i in range(10)])
small_df_replicated = small_df.withColumn("salt", explode(salt_values))

# Join on salted key
result = large_df_salted.join(
    small_df_replicated,
    (large_df_salted.id == small_df_replicated.id) & 
    (large_df_salted.salt == small_df_replicated.salt)
).drop("salt")

# ========== 5. COALESCE NULL KEYS BEFORE JOIN ==========
# Avoid shuffling NULLs
from pyspark.sql.functions import coalesce

df1_clean = df1.withColumn("join_key", 
    coalesce(col("join_key"), lit("__NULL__"))
)
```

### **5.3 Join Performance Decision Matrix**

```
SCENARIO → JOIN STRATEGY
├─ One table < 10MB → Broadcast Join
├─ Both tables large, well distributed → Standard Join
├─ One table small (<100MB), many executors → Increase broadcast threshold
├─ Data skewed on join key → Salting technique
├─ Joining on NULL values → Filter/coalesce NULLs first
├─ Multiple joins on same key → Bucket tables
└─ Self-join on large table → Consider window functions instead
```

---

## 📦 PART 6: AGGREGATIONS - GROUPBY & PIVOT

### **6.1 GroupBy Aggregations**

```python
from pyspark.sql.functions import *

# ========== Simple Aggregation ==========
df.groupBy("department").count()
df.groupBy("department").sum("salary")
df.groupBy("department").avg("salary")
df.groupBy("department").max("salary")
df.groupBy("department").min("salary")

# ========== Multiple Aggregations ==========
df.groupBy("department").agg(
    count("*").alias("employee_count"),
    sum("salary").alias("total_salary"),
    avg("salary").alias("avg_salary"),
    min("salary").alias("min_salary"),
    max("salary").alias("max_salary"),
    stddev("salary").alias("salary_stddev")
)

# ========== Conditional Aggregation ==========
df.groupBy("department").agg(
    sum(when(col("gender") == "M", 1).otherwise(0)).alias("male_count"),
    sum(when(col("gender") == "F", 1).otherwise(0)).alias("female_count"),
    sum(when(col("salary") > 100000, col("salary")).otherwise(0)).alias("high_earner_total")
)

# ========== Collect to Arrays/Lists ==========
df.groupBy("department").agg(
    collect_list("employee_name").alias("all_employees"),
    collect_set("skill").alias("unique_skills"),
    array_join(collect_list("name"), ", ").alias("names_comma_separated")
)

# ========== First/Last Values ==========
df.groupBy("user_id").agg(
    first("purchase_date").alias("first_purchase"),
    last("purchase_date").alias("last_purchase"),
    max("purchase_amount").alias("max_purchase")
)

# ========== Approximate Aggregations (Faster for large data) ==========
df.groupBy("category").agg(
    approx_count_distinct("user_id").alias("approx_unique_users"),
    count_distinct("user_id").alias("exact_unique_users")  # Compare
)
```

### **6.2 Pivot Operations**

```python
# ========== Basic Pivot ==========
# Long to wide format
df.groupBy("product").pivot("month").sum("sales")

# ========== Pivot with Values (Faster!) ==========
# Pre-define pivot values to avoid extra scan
df.groupBy("product") \
    .pivot("month", ["Jan", "Feb", "Mar", "Apr"]) \
    .sum("sales")

# ========== Multiple Aggregations in Pivot ==========
df.groupBy("product").pivot("month").agg(
    sum("sales").alias("total_sales"),
    avg("price").alias("avg_price"),
    count("*").alias("transaction_count")
)

# ========== Unpivot (Wide to long) ==========
from pyspark.sql.functions import expr

# Stack columns into rows
df.selectExpr(
    "product",
    "stack(4, 'Jan', Jan, 'Feb', Feb, 'Mar', Mar, 'Apr', Apr) as (month, sales)"
)
```

---

## ⚡ PART 7: PERFORMANCE OPTIMIZATION - COMPLETE GUIDE

### **7.1 Optimization Checklist**

```
OPTIMIZATION CATEGORY → TECHNIQUES
├─ Data Reading
│  ├─ Use Parquet (columnar, compressed)
│  ├─ Partition pruning (filter on partition columns)
│  └─ Predicate pushdown (filter early)
│
├─ Transformations
│  ├─ Use built-in functions (NOT UDFs)
│  ├─ Filter before join
│  └─ Avoid wide transformations when possible
│
├─ Joins
│  ├─ Broadcast small tables
│  ├─ Handle skew with salting
│  └─ Bucket for repeated joins
│
├─ Partitioning
│  ├─ Optimal partition count (2-4x cores)
│  ├─ Coalesce after filtering
│  └─ Repartition before expensive operations
│
├─ Caching
│  ├─ Cache DataFrames used 2+ times
│  ├─ Use appropriate storage level
│  └─ Unpersist when done
│
└─ Memory
   ├─ Proper executor memory config
   ├─ Avoid collect() on large data
   └─ Monitor Spark UI for spills
```

### **7.2 Spark Configuration Tuning**

```python
# ========== Essential Configurations ==========
spark = SparkSession.builder \
    .appName("OptimizedApp") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .config("spark.sql.adaptive.skewJoin.enabled", "true") \
    .config("spark.sql.shuffle.partitions", "200") \
    .config("spark.executor.memory", "8g") \
    .config("spark.driver.memory", "4g") \
    .config("spark.executor.cores", "5") \
    .config("spark.dynamicAllocation.enabled", "true") \
    .config("spark.dynamicAllocation.minExecutors", "2") \
    .config("spark.dynamicAllocation.maxExecutors", "20") \
    .config("spark.sql.autoBroadcastJoinThreshold", "10485760")  # 10MB
    .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
    .getOrCreate()

# ========== Check Current Settings ==========
spark.conf.get("spark.sql.shuffle.partitions")
spark.sparkContext.getConf().getAll()
```

### **7.3 Partition Sizing Guide**

```python
# ========== Check Partition Count ==========
df.rdd.getNumPartitions()

# ========== Check Partition Sizes ==========
df.rdd.glom().map(len).collect()  # Rows per partition

# ========== Optimal Partition Count ==========
# Rule of thumb: 2-4 partitions per CPU core
# Partition size: 100-200MB per partition

# Example: 100GB data / 200MB per partition = 500 partitions
optimal_partitions = 500

# ========== Repartition (increases or decreases, full shuffle) ==========
df_repartitioned = df.repartition(200)
df_repartitioned = df.repartition(200, "user_id")  # By column

# ========== Coalesce (only decreases, minimal shuffle) ==========
df_coalesced = df.coalesce(50)

# ========== When to use which ==========
# After filter (data reduced): coalesce
filtered_df = df.filter(col("date") == "2024-01-01").coalesce(10)

# Before expensive operation: repartition
df_prepared = df.repartition(200, "user_id")
result = df_prepared.groupBy("user_id").agg(...)
```

---

## 💾 PART 8: CACHING & PERSISTENCE STRATEGIES

### **8.1 Storage Levels**

```python
from pyspark import StorageLevel

# ========== Cache (Memory Only) ==========
df.cache()  # Same as persist(StorageLevel.MEMORY_ONLY)

# ========== Persist with Storage Level ==========
df.persist(StorageLevel.MEMORY_ONLY)        # Default, deserialized
df.persist(StorageLevel.MEMORY_ONLY_SER)    # Serialized (more compact)
df.persist(StorageLevel.MEMORY_AND_DISK)    # Spill to disk if needed
df.persist(StorageLevel.MEMORY_AND_DISK_SER)
df.persist(StorageLevel.DISK_ONLY)          # Store only on disk
df.persist(StorageLevel.OFF_HEAP)           # Use off-heap memory

# ========== Unpersist ==========
df.unpersist()

# ========== Check if Cached ==========
df.is_cached
```

### **8.2 When to Cache**

```python
# ========== Good Use Cases for Caching ==========

# 1. DataFrame used multiple times
df_filtered = df.filter(col("date") >= "2024-01-01")
df_filtered.cache()  # Cache AFTER filtering

count = df_filtered.count()  # Triggers caching
stats = df_filtered.agg(...)  # Uses cache
summary = df_filtered.groupBy(...)  # Uses cache

df_filtered.unpersist()  # Clean up

# 2. Iterative ML algorithms
training_data = df.filter(col("label").isNotNull()).cache()
for iteration in range(10):
    # Training code using training_data
    pass
training_data.unpersist()

# 3. Interactive analysis (notebooks)
user_data = spark.read.parquet("users").cache()
# Run multiple queries interactively
```

**⚠️ When NOT to Cache:**
- DataFrame used only once
- Very large DataFrames that don't fit in memory
- After every transformation (cache strategically!)

### **8.3 Cache Decision Matrix**

```
SCENARIO → ACTION
├─ Used 1 time → Don't cache
├─ Used 2-3 times → Cache with MEMORY_AND_DISK
├─ Used 10+ times → Cache with MEMORY_ONLY
├─ Large DataFrame → Cache with MEMORY_AND_DISK_SER
├─ Small DataFrame → Cache with MEMORY_ONLY
├─ Not enough memory → Use MEMORY_AND_DISK or don't cache
└─ Done with DataFrame → Always unpersist()
```

---

## 🎯 PART 9: UDF STRATEGIES & OPTIMIZATION

### **9.1 UDF Hierarchy (Use in This Order)**

```
PREFERENCE ORDER (Best to Worst):
1. ✅ Built-in PySpark functions (ALWAYS check first)
2. ✅ Pandas UDF (vectorized, much faster than Python UDF)
3. ⚠️ Python UDF (slow, breaks optimization)
4. ❌ UDF calling external APIs (very slow)
```

### **9.2 Built-in Functions (ALWAYS PREFER)**

```python
from pyspark.sql.functions import *

# ❌ BAD: Using UDF
def upper_case(s):
    return s.upper()

upper_udf = udf(upper_case, StringType())
df.withColumn("name_upper", upper_udf(col("name")))

# ✅ GOOD: Using built-in
df.withColumn("name_upper", upper(col("name")))

# ❌ BAD: UDF for date arithmetic
def add_days(date, days):
    from datetime import timedelta
    return date + timedelta(days=days)

add_days_udf = udf(add_days, DateType())
df.withColumn("future_date", add_days_udf(col("date"), lit(7)))

# ✅ GOOD: Using built-in
df.withColumn("future_date", date_add(col("date"), 7))

# ======== Common built-in alternatives ========
# String operations
upper(), lower(), trim(), ltrim(), rtrim()
substring(), length(), concat(), concat_ws()
split(), regexp_extract(), regexp_replace()

# Date/time operations
date_add(), date_sub(), datediff(), months_between()
year(), month(), dayofmonth(), dayofweek()
to_date(), to_timestamp(), date_format()

# Math operations
abs(), ceil(), floor(), round(), sqrt(), pow()
log(), exp(), sin(), cos(), tan()

# Conditional logic
when().otherwise()
coalesce()
if(), case()

# Aggregations
sum(), avg(), min(), max(), count(), stddev()
collect_list(), collect_set()
```

### **9.3 Pandas UDF (When built-in won't work)**

```python
from pyspark.sql.functions import pandas_udf, PandasUDFType
import pandas as pd

# ========== Scalar Pandas UDF (Element-wise) ==========
@pandas_udf("double")
def complex_calculation(series: pd.Series) -> pd.Series:
    # Operates on entire column at once (vectorized)
    return series.apply(lambda x: x ** 2 + x ** 0.5)

df.withColumn("result", complex_calculation(col("value")))

# ========== Grouped Map Pandas UDF ==========
@pandas_udf("id long, avg_value double", PandasUDFType.GROUPED_MAP)
def calculate_group_stats(pdf: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        'id': [pdf['id'].iloc[0]],
        'avg_value': [pdf['value'].mean()]
    })

df.groupBy("id").apply(calculate_group_stats)

# ========== Series to Scalar (Aggregation) ==========
@pandas_udf("double", PandasUDFType.GROUPED_AGG)
def weighted_avg(values: pd.Series, weights: pd.Series) -> float:
    return (values * weights).sum() / weights.sum()

df.groupBy("category").agg(
    weighted_avg(col("price"), col("quantity")).alias("weighted_price")
)
```

### **9.4 Regular Python UDF (Last Resort)**

```python
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType, IntegerType

# ========== Define UDF ==========
def categorize_age(age):
    if age < 18:
        return "Minor"
    elif age < 65:
        return "Adult"
    else:
        return "Senior"

# Register UDF with return type
categorize_udf = udf(categorize_age, StringType())

# ========== Use UDF ==========
df.withColumn("age_category", categorize_udf(col("age")))

# ========== UDF with Multiple Parameters ==========
def calculate_bonus(salary, rating):
    if rating >= 4:
        return salary * 0.15
    elif rating >= 3:
        return salary * 0.10
    else:
        return salary * 0.05

bonus_udf = udf(calculate_bonus, DoubleType())
df.withColumn("bonus", bonus_udf(col("salary"), col("rating")))
```

**⚠️ UDF Performance Impact:**
- Python UDF: 10-100x slower than built-in
- Pandas UDF: 3-10x slower than built-in
- Built-in: Optimized by Catalyst, fastest

---

## 📁 PART 10: FILE FORMATS & WHEN TO USE

### **10.1 Format Comparison**

| Format | Use Case | Compression | Schema Evolution | Read Speed | Write Speed |
|--------|----------|-------------|------------------|------------|-------------|
| **Parquet** | Production (Best) | Excellent | Yes | Very Fast | Fast |
| **ORC** | Hive, write-heavy | Excellent | Limited | Fast | Very Fast |
| **Avro** | Streaming, schema evolution | Good | Excellent | Medium | Medium |
| **CSV** | Human-readable, legacy | Poor | No | Slow | Fast |
| **JSON** | APIs, semi-structured | Poor | Yes | Slow | Medium |

### **10.2 Parquet (Recommended for Production)**

```python
# ========== Write Parquet ==========
df.write \
    .mode("overwrite") \
    .option("compression", "snappy")  # snappy, gzip, lzo, zstd
    .partitionBy("year", "month") \
    .parquet("s3://bucket/data/")

# ========== Read Parquet ==========
df = spark.read.parquet("s3://bucket/data/")

# With partition pruning
df = spark.read \
    .parquet("s3://bucket/data/") \
    .filter("year = 2024 AND month = 1")  # Only reads those partitions!

# ========== Parquet Schema Merging ==========
df = spark.read \
    .option("mergeSchema", "true") \
    .parquet("s3://bucket/data/")
```

**Why Parquet:**
- ✅ Columnar format (only read needed columns)
- ✅ Excellent compression
- ✅ Predicate pushdown
- ✅ Schema evolution
- ✅ Efficient for analytics

### **10.3 Writing Strategies**

```python
# ========== Partitioning ==========
# Partition by low-cardinality columns
df.write \
    .partitionBy("year", "month", "day") \
    .parquet("output/")

# ⚠️ Don't partition by high-cardinality columns (user_id, timestamp)

# ========== Bucketing (for joins) ==========
df.write \
    .bucketBy(100, "user_id") \
    .sortBy("user_id") \
    .saveAsTable("bucketed_users")

# ========== Compression ==========
# snappy: Fast, moderate compression (default)
# gzip: Slower, better compression
# zstd: Good balance (Spark 3.2+)
df.write.option("compression", "zstd").parquet("output/")

# ========== Coalesce for Small Files ==========
# Avoid many small files (bad for HDFS/S3)
df.coalesce(10).write.parquet("output/")

# ========== Write Modes ==========
df.write.mode("overwrite").parquet("output/")  # Replace all
df.write.mode("append").parquet("output/")     # Add to existing
df.write.mode("ignore").parquet("output/")     # Skip if exists
df.write.mode("error").parquet("output/")      # Fail if exists (default)
```

---

## 🧠 PART 11: MEMORY MANAGEMENT & OOM ERRORS

### **11.1 Common OOM Causes & Solutions**

```python
# ========== Cause 1: Large Partitions ==========
# Check partition sizes
df.rdd.glom().map(len).collect()

# Solution: Repartition
df_fixed = df.repartition(200)

# ========== Cause 2: collect() on Large Data ==========
# ❌ BAD
result = df.collect()  # Brings all data to driver!

# ✅ GOOD
df.write.parquet("output/")  # Write to storage
df.show(20)  # Show sample
df.limit(1000).collect()  # Collect small subset

# ========== Cause 3: Broadcast Too Large ==========
# Check broadcast threshold
spark.conf.get("spark.sql.autoBroadcastJoinThreshold")

# Disable auto-broadcast for large tables
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "-1")

# ========== Cause 4: Insufficient Executor Memory ==========
# Increase executor memory
spark.conf.set("spark.executor.memory", "16g")

# Increase memory fraction
spark.conf.set("spark.memory.fraction", "0.8")  # Default 0.6

# ========== Cause 5: Too Many Cached DataFrames ==========
# Unpersist when done
df1.cache()
# ... use df1 ...
df1.unpersist()

# Check cached data
spark.catalog.listTables()
```

### **11.2 Memory Configuration**

```python
# ========== Executor Configuration ==========
spark.executor.memory = 8g          # Total executor memory
spark.executor.cores = 5            # Cores per executor
spark.executor.instances = 10       # Number of executors

# Memory breakdown:
# Reserved: 300MB (fixed)
# Spark Memory: (executor.memory - 300MB) * spark.memory.fraction
#   ├─ Storage (caching): 50% (adjustable)
#   └─ Execution (shuffles): 50% (adjustable)
# User Memory: Remaining

# ========== Driver Configuration ==========
spark.driver.memory = 4g            # Driver memory
spark.driver.cores = 4              # Driver cores

# ========== Memory Tuning ==========
# For cache-heavy workloads
spark.memory.storageFraction = 0.7  # More for caching

# For shuffle-heavy workloads
spark.memory.storageFraction = 0.3  # More for execution
```

---

## 🎓 PART 12: REAL-WORLD PRODUCTION PATTERNS

### **12.1 ETL Pipeline Pattern**

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import *

class ETLPipeline:
    def __init__(self):
        self.spark = SparkSession.builder \
            .appName("Production ETL") \
            .config("spark.sql.adaptive.enabled", "true") \
            .getOrCreate()
    
    def extract(self, path):
        """Extract with error handling"""
        try:
            return self.spark.read \
                .option("mode", "PERMISSIVE") \
                .option("columnNameOfCorruptRecord", "_corrupt_record") \
                .parquet(path)
        except Exception as e:
            raise Exception(f"Extract failed: {str(e)}")
    
    def transform(self, df):
        """Transform with data quality checks"""
        # Remove nulls
        df_clean = df.na.drop(subset=["user_id", "timestamp"])
        
        # Deduplicate
        window = Window.partitionBy("user_id", "event_type") \
            .orderBy(col("timestamp").desc())
        df_dedup = df_clean \
            .withColumn("rn", row_number().over(window)) \
            .filter(col("rn") == 1) \
            .drop("rn")
        
        # Add derived columns
        df_transformed = df_dedup \
            .withColumn("date", to_date(col("timestamp"))) \
            .withColumn("hour", hour(col("timestamp")))
        
        return df_transformed
    
    def load(self, df, output_path):
        """Load with partitioning"""
        df.write \
            .mode("overwrite") \
            .partitionBy("date") \
            .option("compression", "snappy") \
            .parquet(output_path)
    
    def run(self, input_path, output_path):
        """Run full pipeline"""
        df_raw = self.extract(input_path)
        df_transformed = self.transform(df_raw)
        self.load(df_transformed, output_path)
        
        return {
            "input_records": df_raw.count(),
            "output_records": df_transformed.count()
        }
```

### **12.2 Incremental Processing Pattern**

```python
def incremental_process(spark, input_path, checkpoint_path, output_path):
    """Process only new data since last run"""
    
    # Read last processed timestamp
    try:
        last_processed = spark.read.parquet(checkpoint_path) \
            .select(max("timestamp")).first()[0]
    except:
        last_processed = "1970-01-01"
    
    # Read only new data
    df_new = spark.read \
        .parquet(input_path) \
        .filter(col("timestamp") > last_processed)
    
    if df_new.count() == 0:
        print("No new data to process")
        return
    
    # Process new data
    df_processed = df_new.withColumn("processed_at", current_timestamp())
    
    # Append to output
    df_processed.write \
        .mode("append") \
        .partitionBy("date") \
        .parquet(output_path)
    
    # Update checkpoint
    df_processed.select(max("timestamp").alias("timestamp")) \
        .write.mode("overwrite").parquet(checkpoint_path)
```

### **12.3 Data Quality Framework**

```python
from pyspark.sql.functions import *

def data_quality_checks(df, checks_config):
    """
    Run data quality checks
    
    checks_config = {
        'null_checks': ['user_id', 'email'],
        'range_checks': {'age': (0, 120), 'salary': (0, 1000000)},
        'unique_checks': ['user_id'],
        'regex_checks': {'email': r'^[\w\.-]+@[\w\.-]+\.\w+$'}
    }
    """
    issues = []
    
    # NULL checks
    for col_name in checks_config.get('null_checks', []):
        null_count = df.filter(col(col_name).isNull()).count()
        if null_count > 0:
            issues.append({
                'check': 'null_check',
                'column': col_name,
                'issue': f'{null_count} null values found'
            })
    
    # Range checks
    for col_name, (min_val, max_val) in checks_config.get('range_checks', {}).items():
        out_of_range = df.filter(
            (col(col_name) < min_val) | (col(col_name) > max_val)
        ).count()
        if out_of_range > 0:
            issues.append({
                'check': 'range_check',
                'column': col_name,
                'issue': f'{out_of_range} values outside [{min_val}, {max_val}]'
            })
    
    # Uniqueness checks
    for col_name in checks_config.get('unique_checks', []):
        total = df.count()
        distinct = df.select(col_name).distinct().count()
        if total != distinct:
            issues.append({
                'check': 'unique_check',
                'column': col_name,
                'issue': f'{total - distinct} duplicate values'
            })
    
    return issues
```

---

## 📋 QUICK DECISION MATRIX

```
PROBLEM → SOLUTION → KEY FUNCTIONS
├─ Read data → Format choice → parquet (best), csv, json
├─ Filter rows → Filter early → filter(), where()
├─ Select columns → Project early → select()
├─ Add columns → Transform → withColumn(), select()
├─ Remove nulls → Clean data → na.drop(), na.fill()
├─ Remove duplicates → Deduplicate → dropDuplicates(), row_number()
├─ Combine DataFrames → Union → union(), unionByName()
├─ Join tables → Choose strategy → join(), broadcast()
├─ Aggregate → GroupBy → groupBy().agg()
├─ Rank/Order → Window function → row_number(), rank()
├─ Compare rows → Window function → lag(), lead()
├─ Running total → Window function → sum().over()
├─ Pivot data → Reshape → pivot(), stack()
├─ Custom logic → UDF (last resort) → udf(), pandas_udf()
├─ Slow performance → Optimize → cache(), broadcast(), repartition()
├─ OOM error → Memory → repartition(), unpersist(), increase memory
├─ Skewed data → Rebalance → salting, repartition()
└─ Write data → Partition → partitionBy(), write.parquet()
```

---

## 🎯 INTERVIEW STRATEGY

**When given a PySpark problem:**

1. **Identify the pattern** (filter, join, aggregate, window)
2. **Choose built-in over UDF** (always check pyspark.sql.functions first)
3. **Consider optimization** (broadcast, cache, partition)
4. **Explain trade-offs** (memory vs speed, shuffle vs broadcast)
5. **Discuss scalability** (will this work with 1TB? 100TB?)
6. **Test edge cases** (empty partitions, nulls, skew)

**Always explain:**
- Why this approach is optimal
- What could go wrong at scale
- How to monitor and debug
- Alternative approaches

---

**STATUS:** Complete! 🎉

This guide covers EVERY PySpark pattern, function, and optimization technique needed for senior data engineer interviews. Use the pattern recognition framework to quickly identify the right approach for any problem.
