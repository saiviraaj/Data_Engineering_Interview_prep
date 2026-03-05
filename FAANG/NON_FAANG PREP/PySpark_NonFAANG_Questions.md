# PySpark Interview Questions - Non-FAANG Level

Complete PySpark preparation for data engineer interviews.

---

## EASY QUESTIONS (1-8)

### Question 1: Create RDD and DataFrame

```python
# Create RDD
rdd = sc.parallelize([1, 2, 3, 4, 5])
rdd2 = sc.textFile("path/to/file.txt")

# Create DataFrame
df = spark.createDataFrame([(1, "a"), (2, "b")], ["id", "value"])
df2 = spark.read.csv("path.csv", header=True)
```

### Question 2: Basic Transformations

```python
# map: transform each element
rdd.map(lambda x: x * 2).collect()

# filter: keep elements matching condition
rdd.filter(lambda x: x > 2).collect()

# flatMap: map then flatten
rdd.flatMap(lambda x: [x, x*2]).collect()

# DataFrame operations
df.select("id").show()
df.where(df.id > 1).show()
```

### Question 3: Aggregations

```python
# RDD aggregations
rdd.sum()
rdd.mean()
rdd.max()
rdd.min()
rdd.count()

# DataFrame aggregations
from pyspark.sql.functions import sum, avg, max, min
df.agg(sum("id")).show()
df.agg(avg("id"), max("id")).show()
```

### Question 4: Read/Write CSV

```python
# Read CSV
df = spark.read.csv("data.csv", header=True, inferSchema=True)

# Write CSV
df.write.csv("output.csv", header=True)
df.write.mode("overwrite").csv("output.csv")

# Write Parquet (better compression)
df.write.parquet("output.parquet")
```

### Question 5: GroupBy and Aggregations

```python
# Simple groupBy
df.groupBy("category").count().show()

# Multiple aggregations
df.groupBy("category").agg({
    "price": "sum",
    "quantity": "avg"
}).show()

# Using functions
from pyspark.sql.functions import col, sum as spark_sum
df.groupBy("category").agg(
    spark_sum(col("price")).alias("total_price")
).show()
```

### Question 6: Join Operations

```python
# Inner Join
df1.join(df2, df1.id == df2.id, "inner").show()

# Left Join
df1.join(df2, df1.id == df2.id, "left").show()

# Join types
# "inner", "outer", "left", "right", "left_semi", "left_anti"
```

### Question 7: Window Functions

```python
from pyspark.sql.window import Window
from pyspark.sql.functions import row_number, rank, dense_rank

windowSpec = Window.partitionBy("category").orderBy("price")

df.withColumn("row_num", row_number().over(windowSpec)).show()
df.withColumn("rank", rank().over(windowSpec)).show()
```

### Question 8: Column Operations and CASE

```python
from pyspark.sql.functions import col, when, lit

# Column operations
df.withColumn("price_double", col("price") * 2).show()
df.withColumn("name_upper", upper(col("name"))).show()

# CASE statement
df.withColumn("price_category",
    when(col("price") > 100, "expensive")
    .when(col("price") > 50, "moderate")
    .otherwise("cheap")
).show()
```

---

## MEDIUM QUESTIONS (9-18)

### Question 9: Partition Strategy

```python
# Repartition by number of partitions
df.repartition(10).write.parquet("output")

# Partition by column (creates directory structure)
df.write.partitionBy("year", "month").parquet("output")

# Coalesce (reduce partitions)
df.coalesce(1).write.parquet("output")
```

### Question 10: UDF (User Defined Functions)

```python
from pyspark.sql.functions import udf
from pyspark.sql.types import IntegerType

# Python UDF
def multiply_by_two(x):
    return x * 2

multiply_udf = udf(multiply_by_two, IntegerType())
df.withColumn("doubled", multiply_udf(col("value"))).show()

# Pandas UDF (faster)
import pandas as pd
@pandas_udf(IntegerType())
def pandas_multiply(s):
    return s * 2

df.withColumn("doubled", pandas_multiply(col("value"))).show()
```

### Question 11: Broadcast Variables

```python
from pyspark.sql.functions import broadcast

small_df = spark.createDataFrame([(1, "a"), (2, "b")], ["id", "val"])

# Broadcast small table
broadcasted = broadcast(small_df)
result = large_df.join(broadcasted, "id").show()

# Manual broadcast
lookup = sc.broadcast({"1": "a", "2": "b"})
```

### Question 12: Caching and Persistence

```python
# Cache in memory
df.cache()
df.persist()

# Different storage levels
from pyspark import StorageLevel
df.persist(StorageLevel.MEMORY_AND_DISK)
df.persist(StorageLevel.DISK_ONLY)

# Remove cache
df.unpersist()
```

### Question 13: SQL Queries on DataFrames

```python
# Register temporary table
df.createOrReplaceTempView("users")

# SQL query
result = spark.sql("""
    SELECT id, name, SUM(amount) as total
    FROM users
    GROUP BY id, name
    HAVING total > 100
""")

result.show()
```

### Question 14: Handle Missing Values

```python
# Drop rows with null
df.dropna().show()
df.dropna(how='any').show()

# Fill null values
df.fillna(0).show()
df.fillna({"age": 0, "name": "Unknown"}).show()

# Drop nulls in specific columns
df.dropna(subset=["id", "name"]).show()
```

### Question 15: Distinct and Deduplication

```python
# Remove duplicate rows
df.distinct().show()

# Remove duplicates based on specific columns
df.dropDuplicates(["id"]).show()

# Count unique values
df.select("category").distinct().count()
```

### Question 16: String Operations

```python
from pyspark.sql.functions import (
    concat, substring, length, 
    trim, lower, upper, replace
)

df.withColumn("full_name", concat(col("first"), lit(" "), col("last")))
df.withColumn("first_3", substring(col("name"), 1, 3))
df.withColumn("name_lower", lower(col("name")))
```

### Question 17: Date Operations

```python
from pyspark.sql.functions import (
    to_date, to_timestamp, 
    datediff, date_add, date_format
)

df.withColumn("date", to_date(col("date_str"), "yyyy-MM-dd"))
df.withColumn("days_diff", datediff(col("end_date"), col("start_date")))
df.withColumn("formatted", date_format(col("date"), "dd-MM-yyyy"))
```

### Question 18: Complex Aggregations

```python
from pyspark.sql.functions import (
    collect_list, collect_set, 
    concat_ws, first, last
)

df.groupBy("category").agg(
    collect_list("item").alias("all_items"),
    collect_set("item").alias("unique_items"),
    first("price").alias("first_price"),
    last("price").alias("last_price")
).show()
```

---

## HARD QUESTIONS (19-25)

### Question 19: Complex Joins

```python
# Multiple join conditions
result = df1.join(
    df2,
    (df1.id == df2.id) & (df1.date == df2.date),
    "left"
).show()

# Chain joins
result = df1.join(df2, "id").join(df3, "id").show()
```

### Question 20: Window Functions - Advanced

```python
from pyspark.sql.functions import (
    lag, lead, sum as spark_sum, 
    avg as spark_avg, ntile
)

windowSpec = Window.partitionBy("group").orderBy("value")

df.withColumn("prev_value", lag(col("value")).over(windowSpec))
df.withColumn("next_value", lead(col("value")).over(windowSpec))
df.withColumn("running_sum", spark_sum(col("value")).over(windowSpec))
df.withColumn("percentile", ntile(4).over(windowSpec))
```

### Question 21: Data Skew Handling

```python
# Salting technique for skewed joins
salt_df1 = df1.withColumn("salt", (rand() * 100).cast("int"))
salt_df2 = df2.crossJoin(spark.range(100).withColumnRenamed("id", "salt"))

result = salt_df1.join(salt_df2, ["id", "salt"]).show()
```

### Question 22: Incremental Load Pattern

```python
# Check for new/modified records
last_run = spark.sql("SELECT MAX(update_time) FROM tracking")
max_time = last_run.collect()[0][0]

# Load only new data
new_data = spark.read.parquet(source_path).filter(
    col("update_time") > max_time
)

# Merge with existing
existing = spark.read.parquet(target_path)
merged = existing.union(new_data).dropDuplicates(["id"])

merged.write.mode("overwrite").parquet(target_path)
```

### Question 23: Schema Evolution

```python
from pyspark.sql.types import StructType, StructField, StringType

# Define schema
schema = StructType([
    StructField("id", IntegerType(), True),
    StructField("name", StringType(), True),
])

df = spark.read.schema(schema).parquet("data")

# Add new column with default
df_evolved = df.withColumn("new_col", lit(None).cast(StringType()))
```

### Question 24: Performance Optimization

```python
# Select only needed columns early
df.select("id", "name").filter(col("id") > 100)

# Broadcast small tables
from pyspark.sql.functions import broadcast
df.join(broadcast(small_df), "id")

# Use partitioning strategically
df.write.partitionBy("year", "month").parquet(output)

# Persist intermediate results
intermediate = df.groupBy("category").agg(count("*"))
intermediate.persist()
```

### Question 25: Error Handling and Data Quality

```python
# Check data quality
quality_check = df.select(
    count(when(isnull(col("id")), 1)).alias("null_ids"),
    count(when(col("price") < 0, 1)).alias("negative_prices"),
    count("*").alias("total_rows")
)

quality_check.show()

# Log problems
error_df = df.filter((col("price") < 0) | (isnull(col("id"))))
error_df.write.parquet("data_quality_errors")
```

---

## Key PySpark Concepts

✅ **Lazy evaluation** - Transformations don't execute until action
✅ **Partitioning** - Data distributed across nodes
✅ **Broadcast** - Send small data to all nodes
✅ **Caching** - Store intermediate results
✅ **Window functions** - Analyze over groups
✅ **UDFs** - Custom transformation functions

---

