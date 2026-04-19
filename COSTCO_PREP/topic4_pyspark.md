# Topic 4: PySpark Deep Dive — Transformations, Metrics & Data Engineering
## Complete Interview Textbook — Costco Sr. Data Engineer

---

## TABLE OF CONTENTS

1. [PySpark Architecture & Execution Model](#1-pyspark-architecture)
2. [SparkSession & Configuration](#2-sparksession-and-configuration)
3. [DataFrame API — Core Operations](#3-dataframe-api)
4. [Schema Definition & Enforcement](#4-schema-definition)
5. [Data Ingestion — Reading All Source Types](#5-data-ingestion)
6. [Column Operations & Expressions](#6-column-operations)
7. [Filtering, Selecting & Projections](#7-filtering-and-selecting)
8. [Grouping & Aggregations](#8-grouping-and-aggregations)
9. [Window Functions in PySpark](#9-window-functions)
10. [Joins — Deep Dive with Performance](#10-joins)
11. [Data Mangling & Complex Transformations](#11-data-mangling)
12. [String, Date & JSON Transformations](#12-string-date-json)
13. [UDFs — User Defined Functions](#13-udfs)
14. [Performance Optimization](#14-performance-optimization)
15. [Writing & Output Patterns](#15-writing-and-output)
16. [Spark SQL](#16-spark-sql)
17. [Streaming with Structured Streaming](#17-structured-streaming)
18. [Common Pipeline Patterns](#18-pipeline-patterns)
19. [Interview Q&A Bank](#19-interview-qa)

---

## 1. PySpark Architecture & Execution Model

Understanding the architecture is fundamental for interviews — every optimization question traces back to this.

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    DRIVER PROGRAM                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │  SparkContext / SparkSession                      │   │
│  │  - Job scheduling                                 │   │
│  │  - DAG construction                               │   │
│  │  - Task distribution                              │   │
│  └────────────────────────┬─────────────────────────┘   │
└───────────────────────────│─────────────────────────────┘
                            │ (sends tasks)
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
   ┌──────────┐       ┌──────────┐       ┌──────────┐
   │ Executor │       │ Executor │       │ Executor │
   │ ┌──────┐ │       │ ┌──────┐ │       │ ┌──────┐ │
   │ │Task 1│ │       │ │Task 3│ │       │ │Task 5│ │
   │ │Task 2│ │       │ │Task 4│ │       │ │Task 6│ │
   │ └──────┘ │       │ └──────┘ │       │ └──────┘ │
   │  [Cache] │       │  [Cache] │       │  [Cache] │
   └──────────┘       └──────────┘       └──────────┘
      Worker 1           Worker 2           Worker 3
```

### Lazy Evaluation — The Core Concept

```
Transformations (LAZY):        Actions (EAGER — trigger execution):
- filter()                     - collect()
- select()                     - show()
- groupBy()                    - count()
- join()                       - first()
- map()                        - take(n)
- withColumn()                 - write()
- union()                      - save()
                               - foreach()
                               - reduce()
```

**Nothing executes until an action is called.** Spark builds a DAG (Directed Acyclic Graph) of transformations, optimizes it using the Catalyst optimizer, and then executes.

### DAG, Jobs, Stages, Tasks

```
Action → Job
  Job → Stages (split at shuffle boundaries: groupBy, join, repartition)
    Stage → Tasks (one per partition)

Example:
df.filter(...).groupBy(...).agg(...).write()
  Job 1:
    Stage 1: filter() → map to (key, value) pairs — N tasks (N partitions)
             [SHUFFLE — data redistributed by key]
    Stage 2: groupBy/agg reduce — M tasks (M reducers)
    Stage 3: write — M tasks
```

### Catalyst Optimizer & Tungsten Engine

- **Catalyst**: logical plan → optimized logical plan → physical plan. Applies predicate pushdown, column pruning, constant folding, join reordering.
- **Tungsten**: binary memory management, code generation. Avoids Java object overhead.

```python
# View the execution plan
df.explain()             # Simple plan
df.explain(True)         # Extended plan (logical + physical)
df.explain("formatted")  # Most readable (Spark 3+)
```

---

## 2. SparkSession & Configuration

### Creating SparkSession

```python
from pyspark.sql import SparkSession

# Local mode (for testing)
spark = SparkSession.builder \
    .appName("CostcoDataPipeline") \
    .master("local[*]") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .config("spark.sql.shuffle.partitions", "200") \
    .config("spark.executor.memory", "4g") \
    .config("spark.driver.memory", "2g") \
    .getOrCreate()

# On GCP Dataproc
spark = SparkSession.builder \
    .appName("CostcoMarTechPipeline") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.skewJoin.enabled", "true") \
    .config("spark.sql.extensions", "com.google.cloud.spark.bigquery.BigQuerySparkSqlExtension") \
    .getOrCreate()

# Get or create (idempotent)
spark = SparkSession.getActiveSession() or SparkSession.builder.getOrCreate()

# Access SparkContext from session
sc = spark.sparkContext
sc.setLogLevel("WARN")  # Reduce log noise
```

### Key Configuration Parameters

```python
# Shuffle partitions (default 200, tune based on data size)
spark.conf.set("spark.sql.shuffle.partitions", "400")

# Adaptive Query Execution (AQE) — Spark 3.0+
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")

# Broadcast join threshold
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "100m")  # 100MB default is 10MB

# Kryo serialization (faster than Java)
spark.conf.set("spark.serializer", "org.apache.spark.serializer.KryoSerializer")

# Dynamic allocation
spark.conf.set("spark.dynamicAllocation.enabled", "true")
spark.conf.set("spark.dynamicAllocation.minExecutors", "2")
spark.conf.set("spark.dynamicAllocation.maxExecutors", "20")

# Reading config
val = spark.conf.get("spark.sql.shuffle.partitions")
```

---

## 3. DataFrame API — Core Operations

### Creating DataFrames

```python
from pyspark.sql import Row
from pyspark.sql.types import *

# From Python list
data = [
    (1, "Alice", 28, 75000.0),
    (2, "Bob", 35, 85000.0),
    (3, "Charlie", None, 92000.0)
]
schema = ["id", "name", "age", "salary"]
df = spark.createDataFrame(data, schema)

# With explicit schema
schema = StructType([
    StructField("id", IntegerType(), nullable=False),
    StructField("name", StringType(), nullable=True),
    StructField("age", IntegerType(), nullable=True),
    StructField("salary", DoubleType(), nullable=True)
])
df = spark.createDataFrame(data, schema)

# From Row objects
rows = [Row(id=1, name="Alice", age=28), Row(id=2, name="Bob", age=35)]
df = spark.createDataFrame(rows)

# From Pandas DataFrame
import pandas as pd
pdf = pd.DataFrame({"id": [1,2,3], "name": ["a","b","c"]})
df = spark.createDataFrame(pdf)

# Empty DataFrame
empty_df = spark.createDataFrame([], schema)
```

### Basic Inspection

```python
df.show()                 # Display top 20 rows
df.show(50, truncate=False) # Show 50 rows, no truncation
df.printSchema()          # Print schema as tree
df.schema                 # StructType object
df.dtypes                 # List of (col_name, type_str) tuples
df.columns                # List of column names
df.count()                # Row count (triggers action)
df.describe()             # Basic stats (count, mean, stddev, min, max)
df.summary()              # Extended stats including percentiles
df.isEmpty()              # Boolean (Spark 3.3+)

# Column access
df["column_name"]         # Column object
df.column_name            # Attribute access (only if valid Python identifier)

# Get single value
df.first()                # First Row object
df.head(5)                # First 5 Row objects
df.collect()              # All rows as list of Row objects (CAUTION: pulls to driver)
df.take(100)              # First 100 Row objects
```

---

## 4. Schema Definition & Enforcement

### Schema Types Reference

```python
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, LongType, FloatType, DoubleType,
    BooleanType, DateType, TimestampType, DecimalType,
    ArrayType, MapType, BinaryType, NullType
)

# Complex schema with nested types
schema = StructType([
    StructField("order_id", LongType(), nullable=False),
    StructField("customer_id", LongType(), nullable=True),
    StructField("order_date", DateType(), nullable=True),
    StructField("total_amount", DecimalType(12, 2), nullable=True),
    StructField("tags", ArrayType(StringType()), nullable=True),
    StructField("metadata", MapType(StringType(), StringType()), nullable=True),
    StructField("line_items", ArrayType(
        StructType([
            StructField("product_id", StringType(), nullable=True),
            StructField("qty", IntegerType(), nullable=True),
            StructField("price", DoubleType(), nullable=True)
        ])
    ), nullable=True),
    StructField("shipping", StructType([
        StructField("address", StringType(), nullable=True),
        StructField("city", StringType(), nullable=True),
        StructField("zip", StringType(), nullable=True)
    ]), nullable=True)
])

# Parse from JSON schema string
import json
schema_json = """{"type":"struct","fields":[{"name":"id","type":"long","nullable":true}]}"""
schema = StructType.fromJson(json.loads(schema_json))

# Schema evolution — merge schemas
df1.schema.merge(df2.schema)
```

### Schema Enforcement

```python
# Read with schema (no inference = faster + enforced)
df = spark.read.schema(schema).parquet("gs://bucket/path/")

# Enforce schema on existing DF
df_enforced = spark.createDataFrame(df.rdd, schema)

# Add/change column types
from pyspark.sql.functions import col
df = df.withColumn("amount", col("amount").cast(DoubleType()))
df = df.withColumn("event_date", col("event_date_str").cast(DateType()))
```

---

## 5. Data Ingestion — Reading All Source Types

### Reading Parquet (Primary Format for Data Lakes)

```python
# Basic read
df = spark.read.parquet("gs://bucket/data/events/")

# With options
df = spark.read \
    .option("mergeSchema", "true") \
    .option("basePath", "gs://bucket/data/events/") \
    .parquet("gs://bucket/data/events/year=2024/month=01/")

# Partition discovery
df = spark.read \
    .option("recursiveFileLookup", "true") \
    .parquet("gs://bucket/data/events/")

# Print discovered partitions
df.select("year", "month").distinct().show()
```

### Reading CSV

```python
df = spark.read \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .option("sep", ",") \
    .option("quote", '"') \
    .option("escape", "\\") \
    .option("nullValue", "NULL") \
    .option("emptyValue", "") \
    .option("dateFormat", "yyyy-MM-dd") \
    .option("timestampFormat", "yyyy-MM-dd HH:mm:ss") \
    .option("multiLine", "true") \
    .option("encoding", "UTF-8") \
    .option("ignoreLeadingWhiteSpace", "true") \
    .option("ignoreTrailingWhiteSpace", "true") \
    .csv("gs://bucket/data/uploads/*.csv")

# With explicit schema (preferred for production)
df = spark.read \
    .schema(schema) \
    .option("header", "true") \
    .csv("gs://bucket/data/")
```

### Reading JSON

```python
# Single-line JSON (one record per line — default)
df = spark.read.json("gs://bucket/data/events.json")

# Multi-line JSON (object spans multiple lines)
df = spark.read.option("multiLine", "true").json("gs://bucket/data/events.json")

# With schema
df = spark.read.schema(schema).json("gs://bucket/data/")

# From string column (parse embedded JSON)
from pyspark.sql.functions import from_json, col
df_parsed = df.withColumn(
    "props_parsed",
    from_json(col("properties_json_string"), schema)
)
```

### Reading from BigQuery (Dataproc + BigQuery Connector)

```python
# Read entire table
df = spark.read \
    .format("bigquery") \
    .option("table", "project.dataset.table") \
    .load()

# Read with SQL
df = spark.read \
    .format("bigquery") \
    .option("query", """
        SELECT customer_id, SUM(revenue) AS total_revenue
        FROM `project.dataset.orders`
        WHERE order_date >= '2024-01-01'
        GROUP BY customer_id
    """) \
    .load()

# With partitioning for parallel reads
df = spark.read \
    .format("bigquery") \
    .option("table", "project.dataset.large_table") \
    .option("filter", "date >= '2024-01-01'") \
    .option("parallelism", "400") \
    .load()
```

### Reading from GCS with Various Formats

```python
# ORC
df = spark.read.orc("gs://bucket/data/*.orc")

# Delta Lake
df = spark.read.format("delta").load("gs://bucket/delta/table/")

# Avro
df = spark.read.format("avro").load("gs://bucket/data/*.avro")

# Text (one row = one line)
df = spark.read.text("gs://bucket/data/logfile.txt")

# Binary files
df = spark.read.format("binaryFile").load("gs://bucket/images/")
```

### Reading from Databases (JDBC)

```python
# From Oracle/PostgreSQL/MySQL
df = spark.read \
    .format("jdbc") \
    .option("url", "jdbc:oracle:thin:@hostname:1521:orcl") \
    .option("dbtable", "schema.tablename") \
    .option("user", "username") \
    .option("password", "password") \
    .option("driver", "oracle.jdbc.driver.OracleDriver") \
    .option("numPartitions", "10") \
    .option("partitionColumn", "id") \
    .option("lowerBound", "1") \
    .option("upperBound", "1000000") \
    .load()

# With pushdown query
df = spark.read \
    .format("jdbc") \
    .option("url", jdbc_url) \
    .option("query", "SELECT * FROM orders WHERE order_date >= '2024-01-01'") \
    .load()
```

---

## 6. Column Operations & Expressions

### Functions Import — Know These by Heart

```python
from pyspark.sql import functions as F
from pyspark.sql.functions import (
    col, lit, expr,
    when, coalesce, isnull, isnotnull, nullif,
    # String
    upper, lower, trim, ltrim, rtrim, lpad, rpad,
    concat, concat_ws, substring, length, instr, locate,
    split, regexp_replace, regexp_extract,
    # Math
    abs, ceil, floor, round, sqrt, pow, log, exp,
    greatest, least, rand, randn,
    # Date/Time
    current_date, current_timestamp,
    date_add, date_sub, datediff, months_between,
    year, month, dayofmonth, dayofweek, dayofyear,
    quarter, weekofyear, hour, minute, second,
    date_trunc, date_format, to_date, to_timestamp,
    unix_timestamp, from_unixtime,
    # Aggregate
    count, countDistinct, sum, avg, min, max,
    first, last, collect_list, collect_set,
    approx_count_distinct, stddev, variance,
    # Array
    array, array_contains, array_distinct, array_intersect,
    array_union, array_except, array_join, array_max,
    array_min, array_size, array_sort, explode, posexplode,
    flatten, zip_with, transform, filter, aggregate,
    # Struct
    struct, create_map,
    # JSON
    from_json, to_json, json_tuple, get_json_object,
    # Window
    row_number, rank, dense_rank, ntile,
    lag, lead, first, last,
    # Misc
    md5, sha1, sha2, hash, xxhash64,
    monotonically_increasing_id,
    broadcast, udf
)
```

### Column Creation and Modification

```python
# withColumn — add or replace column
df = df.withColumn("full_name", F.concat_ws(" ", col("first_name"), col("last_name")))
df = df.withColumn("revenue_usd", col("revenue") * 1.1)
df = df.withColumn("processed_at", F.current_timestamp())
df = df.withColumn("is_valid", col("amount") > 0)

# withColumnRenamed — rename
df = df.withColumnRenamed("oldName", "newName")

# drop columns
df = df.drop("unnecessary_col1", "unnecessary_col2")
df = df.drop(*["col1", "col2", "col3"])

# Select with rename
df = df.select(
    col("id"),
    col("name").alias("customer_name"),
    (col("price") * col("qty")).alias("line_total"),
    F.lit("costco").alias("source")
)

# select with selectExpr (SQL expressions as strings)
df = df.selectExpr(
    "id",
    "name AS customer_name",
    "price * qty AS line_total",
    "'costco' AS source",
    "CURRENT_TIMESTAMP() AS loaded_at"
)
```

### CASE WHEN (when/otherwise)

```python
from pyspark.sql.functions import when

# Single condition
df = df.withColumn(
    "status_flag",
    when(col("status") == "active", 1).otherwise(0)
)

# Multiple conditions (chained)
df = df.withColumn(
    "customer_tier",
    when(col("annual_spend") >= 10000, "Platinum")
    .when(col("annual_spend") >= 5000, "Gold")
    .when(col("annual_spend") >= 1000, "Silver")
    .otherwise("Bronze")
)

# Null handling in CASE
df = df.withColumn(
    "clean_status",
    when(col("status").isNull(), "unknown")
    .when(col("status").isin("A", "active", "ACTIVE"), "active")
    .when(col("status").isin("I", "inactive", "INACTIVE"), "inactive")
    .otherwise("other")
)

# Boolean expression
df = df.withColumn(
    "is_high_value",
    (col("spend") > 1000) & (col("recency_days") < 30)
)

# Nested when
df = df.withColumn(
    "segment",
    when(col("is_member"),
         when(col("is_premium"), "premium_member").otherwise("standard_member")
    ).otherwise("non_member")
)
```

### expr() — SQL Expressions in DataFrame API

```python
from pyspark.sql.functions import expr

# Reuse SQL knowledge in PySpark
df = df.withColumn("total", expr("price * quantity * (1 - discount_pct)"))
df = df.filter(expr("datediff(current_date(), order_date) <= 30"))
df = df.withColumn("category_rank", expr("RANK() OVER (PARTITION BY category ORDER BY sales DESC)"))
df = df.select(expr("* EXCEPT (internal_id, temp_col)"))  -- Note: * EXCEPT is BigQuery SQL, not standard Spark

# Use expr for complex conditions
df = df.filter(expr("""
    amount > 0
    AND status IN ('completed', 'shipped')
    AND order_date >= DATE_SUB(CURRENT_DATE(), 90)
"""))
```

---

## 7. Filtering and Selecting

### Filter / Where Patterns

```python
# Basic filters (filter and where are identical)
df.filter(col("age") > 25)
df.where(col("age") > 25)

# Multiple conditions
df.filter((col("age") > 25) & (col("salary") > 50000))
df.filter((col("age") > 25) | (col("status") == "senior"))
df.filter(~col("is_deleted"))  # NOT

# isin / isnot
df.filter(col("country").isin(["US", "CA", "GB"]))
df.filter(~col("country").isin(["XX", "YY"]))

# Null checks
df.filter(col("email").isNull())
df.filter(col("email").isNotNull())

# String patterns
df.filter(col("email").endswith("@costco.com"))
df.filter(col("product_name").startswith("KIRKLAND"))
df.filter(col("description").contains("organic"))
df.filter(col("product_name").like("%SIGNATURE%"))  # SQL LIKE
df.filter(col("sku").rlike(r"^KS\d{6}$"))  # Regex

# Between
df.filter(col("amount").between(100, 500))
df.filter(col("order_date").between("2024-01-01", "2024-12-31"))

# Filter on array column
from pyspark.sql.functions import array_contains
df.filter(array_contains(col("tags"), "organic"))

# Filter using SQL expression
df.filter(expr("amount > 0 AND status = 'active'"))
```

### Select Patterns

```python
# Select specific columns
df.select("id", "name", "email")
df.select(col("id"), col("name"), col("email"))

# Select with transformations
df.select(
    "id",
    F.upper(col("name")).alias("name_upper"),
    (col("price") * 1.1).alias("price_with_tax"),
    F.coalesce(col("preferred_email"), col("work_email")).alias("email")
)

# Select all + new column (PySpark 3+)
df.select("*", F.current_timestamp().alias("extracted_at"))

# Dynamic column selection
cols_to_keep = ["id", "name", "amount"]
df.select([col(c) for c in cols_to_keep])

# Select by data type
from pyspark.sql import types as T
numeric_cols = [f.name for f in df.schema.fields if isinstance(f.dataType, (T.IntegerType, T.DoubleType, T.LongType))]
df.select(*numeric_cols).show()

# Exclude columns
cols_to_drop = ["internal_id", "created_by"]
df.select([c for c in df.columns if c not in cols_to_drop])
```

---

## 8. Grouping & Aggregations

### groupBy + agg

```python
from pyspark.sql.functions import (
    count, countDistinct, sum, avg, min, max,
    first, last, collect_list, collect_set,
    stddev, variance, percentile_approx
)

# Basic aggregation
df.groupBy("region").agg(
    count("*").alias("total_rows"),
    countDistinct("customer_id").alias("unique_customers"),
    sum("revenue").alias("total_revenue"),
    avg("order_value").alias("avg_order_value"),
    min("order_date").alias("first_order"),
    max("order_date").alias("last_order"),
    stddev("revenue").alias("revenue_stddev")
).show()

# Multi-column group by
df.groupBy("region", "product_category", F.year(col("order_date")).alias("year")) \
  .agg(
      sum("revenue").alias("revenue"),
      countDistinct("customer_id").alias("customers")
  )

# Conditional aggregation (replaces SQL CASE WHEN in SUM)
df.groupBy("customer_id").agg(
    count("*").alias("total_orders"),
    sum(when(col("channel") == "web", col("revenue")).otherwise(0)).alias("web_revenue"),
    sum(when(col("channel") == "mobile", col("revenue")).otherwise(0)).alias("mobile_revenue"),
    sum(when(col("status") == "returned", col("revenue")).otherwise(0)).alias("returned_revenue"),
    (sum(when(col("converted"), 1).otherwise(0)) / count("*")).alias("cvr")
)

# Collect into arrays
df.groupBy("customer_id").agg(
    collect_list("product_id").alias("product_history"),
    collect_set("category").alias("unique_categories"),
    F.concat_ws(",", collect_list("product_name")).alias("product_list")
)

# Percentile
df.groupBy("campaign_id").agg(
    percentile_approx("order_value", 0.5).alias("median_order_value"),
    percentile_approx("order_value", [0.25, 0.75]).alias("iqr_bounds"),
    percentile_approx("order_value", 0.95).alias("p95_order_value")
)
```

### Pivot

```python
# Pivot: rows to columns
df.groupBy("product_id") \
  .pivot("month", ["Jan", "Feb", "Mar", "Apr"]) \
  .agg(sum("revenue"))

# Dynamic pivot (discover values from data — can be slow)
months = df.select("month").distinct().rdd.flatMap(lambda x: x).collect()
df.groupBy("product_id").pivot("month", months).agg(sum("revenue"))
```

### rollup and cube

```python
# rollup: hierarchical subtotals
df.rollup("year", "region", "product_category") \
  .agg(sum("revenue").alias("revenue")) \
  .show()

# cube: all combinations
df.cube("year", "region", "product_category") \
  .agg(sum("revenue").alias("revenue")) \
  .show()

# Identify subtotal rows using grouping_id
from pyspark.sql.functions import grouping_id
df.cube("year", "region") \
  .agg(
      sum("revenue").alias("revenue"),
      grouping_id().alias("grouping_level")
  ) \
  .show()
```

---

## 9. Window Functions in PySpark

### Window Spec Setup

```python
from pyspark.sql.window import Window
from pyspark.sql.functions import (
    row_number, rank, dense_rank, ntile,
    lag, lead, first, last,
    sum, avg, min, max, count
)

# Partition only
w_region = Window.partitionBy("region")

# Partition + order
w_region_revenue = Window.partitionBy("region").orderBy(col("revenue").desc())

# Partition + order + frame (rows)
w_rolling_30d = Window.partitionBy("user_id") \
    .orderBy("event_date") \
    .rowsBetween(-29, Window.currentRow)

# Partition + order + range (value-based)
w_range = Window.partitionBy("user_id") \
    .orderBy("unix_date") \
    .rangeBetween(-6, Window.currentRow)

# Entire partition (no order, all rows)
w_all = Window.partitionBy("region").rowsBetween(
    Window.unboundedPreceding, Window.unboundedFollowing
)

# Running total (from start to current row)
w_running = Window.partitionBy("user_id") \
    .orderBy("order_date") \
    .rowsBetween(Window.unboundedPreceding, Window.currentRow)
```

### Ranking Functions

```python
# ROW_NUMBER, RANK, DENSE_RANK, NTILE
df = df.withColumn("row_num", row_number().over(w_region_revenue))
df = df.withColumn("rank", rank().over(w_region_revenue))
df = df.withColumn("dense_rank", dense_rank().over(w_region_revenue))
df = df.withColumn("quartile", ntile(4).over(Window.orderBy("revenue")))

# Top N per group
top3_per_region = df.withColumn(
    "rn", row_number().over(Window.partitionBy("region").orderBy(col("revenue").desc()))
).filter(col("rn") <= 3).drop("rn")
```

### LAG / LEAD

```python
# Month-over-month change
w_customer_time = Window.partitionBy("customer_id").orderBy("order_month")

df = df.withColumn("prev_month_revenue", lag("revenue", 1).over(w_customer_time)) \
       .withColumn("next_month_revenue", lead("revenue", 1).over(w_customer_time)) \
       .withColumn("mom_change", col("revenue") - lag("revenue", 1).over(w_customer_time)) \
       .withColumn(
           "mom_pct_change",
           (col("revenue") - lag("revenue", 1).over(w_customer_time))
           / lag("revenue", 1).over(w_customer_time) * 100
       )

# Detect churn: 30 days of inactivity
w_user = Window.partitionBy("user_id").orderBy("event_date")
df = df.withColumn(
    "days_since_last_event",
    F.datediff(col("event_date"), lag("event_date", 1).over(w_user))
).withColumn(
    "is_churn_signal",
    when(col("days_since_last_event") > 30, True).otherwise(False)
)
```

### Aggregate Window Functions

```python
# Running total
df = df.withColumn(
    "running_revenue",
    sum("revenue").over(
        Window.partitionBy("customer_id")
        .orderBy("order_date")
        .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    )
)

# 7-day rolling average
df = df.withColumn(
    "rolling_7d_avg",
    avg("daily_revenue").over(
        Window.partitionBy("region")
        .orderBy("event_date")
        .rowsBetween(-6, Window.currentRow)
    )
)

# Percentage of total per group
df = df.withColumn(
    "pct_of_region_total",
    col("revenue") / sum("revenue").over(Window.partitionBy("region"))
)

# First and last value in partition
df = df.withColumn(
    "first_purchase_amount",
    first("amount").over(
        Window.partitionBy("customer_id")
        .orderBy("purchase_date")
        .rowsBetween(Window.unboundedPreceding, Window.unboundedFollowing)
    )
)
```

### Sessionization Pattern

```python
# Full sessionization pipeline in PySpark
from pyspark.sql.functions import *
from pyspark.sql.window import Window

w_user = Window.partitionBy("user_id").orderBy("event_timestamp")

# Step 1: Flag new sessions (gap > 30 min)
df_with_gap = df.withColumn(
    "prev_event_time",
    lag("event_timestamp", 1).over(w_user)
).withColumn(
    "gap_minutes",
    (col("event_timestamp").cast("long") - col("prev_event_time").cast("long")) / 60
).withColumn(
    "is_new_session",
    when(
        col("gap_minutes").isNull() | (col("gap_minutes") > 30),
        1
    ).otherwise(0)
)

# Step 2: Cumulative sum of new_session flags = session_id
df_with_session = df_with_gap.withColumn(
    "session_id",
    sum("is_new_session").over(
        Window.partitionBy("user_id")
        .orderBy("event_timestamp")
        .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    )
)

# Step 3: Session-level aggregation
session_metrics = df_with_session.groupBy("user_id", "session_id").agg(
    min("event_timestamp").alias("session_start"),
    max("event_timestamp").alias("session_end"),
    count("*").alias("event_count"),
    max(when(col("event_type") == "purchase", 1).otherwise(0)).alias("converted"),
    first("campaign_id", ignorenulls=True).alias("attributed_campaign")
).withColumn(
    "session_duration_min",
    (col("session_end").cast("long") - col("session_start").cast("long")) / 60
)
```

---

## 10. Joins — Deep Dive with Performance

### Join Types

```python
# Inner join (default)
df_joined = df_orders.join(df_customers, on="customer_id", how="inner")

# Left join
df_joined = df_orders.join(df_customers, on="customer_id", how="left")
# Aliases: left_outer, left

# Right join
df_joined = df_orders.join(df_customers, on="customer_id", how="right")

# Full outer
df_joined = df_orders.join(df_customers, on="customer_id", how="full")
# Alias: outer, full_outer

# Cross join (DANGEROUS — Cartesian product)
df_cross = df_a.crossJoin(df_b)

# Left anti-join: rows in left NOT in right
df_no_orders = df_customers.join(df_orders, on="customer_id", how="left_anti")

# Left semi-join: rows in left that have match in right (no right columns)
df_has_orders = df_customers.join(df_orders, on="customer_id", how="left_semi")
```

### Join Conditions

```python
# Single column (names match)
df_a.join(df_b, on="customer_id")

# Multiple columns
df_a.join(df_b, on=["customer_id", "order_date"])

# Different column names
df_a.join(df_b, df_a["cust_id"] == df_b["customer_id"])

# Complex condition
df_orders.join(
    df_prices,
    on=(df_orders["product_id"] == df_prices["product_id"])
    & (df_orders["order_date"] >= df_prices["effective_from"])
    & (df_orders["order_date"] < df_prices["effective_to"])
)

# Handle ambiguous columns after join
df_joined = df_a.join(df_b, df_a["id"] == df_b["a_id"]) \
    .select(df_a["*"], df_b["value"].alias("b_value"))
```

### Join Performance Strategies

```python
# 1. Broadcast Join (best for small tables < 10MB default, up to 100MB)
from pyspark.sql.functions import broadcast

# Hint approach
df_large.join(broadcast(df_small), "key")

# Config approach (auto-broadcast up to threshold)
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "104857600")  # 100MB

# 2. Partition before joining (avoid shuffle)
# If both tables need to join on same key repeatedly:
df_orders_partitioned = df_orders.repartition(200, "customer_id")
df_customers_partitioned = df_customers.repartition(200, "customer_id")
df_joined = df_orders_partitioned.join(df_customers_partitioned, "customer_id")

# 3. Sort-Merge Join (SortMergeJoin) — default for large tables
# Ensure both tables are sorted and partitioned on join key
# Spark does this automatically, but you can hint:
df_a.hint("MERGE").join(df_b, "key")

# 4. Skew handling — salt technique
import random
SALT_NUM = 50

# Salt the large skewed table
df_skewed = df_skewed.withColumn("salt", (rand() * SALT_NUM).cast("int"))
df_skewed = df_skewed.withColumn("salted_key", concat(col("join_key"), lit("_"), col("salt")))

# Explode the small table
df_small_exploded = df_small.withColumn(
    "salt_array",
    array([lit(i) for i in range(SALT_NUM)])
).withColumn("salt", explode(col("salt_array"))) \
 .withColumn("salted_key", concat(col("join_key"), lit("_"), col("salt")))

# Now join on salted key
df_result = df_skewed.join(df_small_exploded, "salted_key")
```

---

## 11. Data Mangling & Complex Transformations

### Deduplication

```python
# Method 1: dropDuplicates
df.dropDuplicates()  # All columns
df.dropDuplicates(["email"])  # Based on specific columns
df.dropDuplicates(["customer_id", "order_date"])

# Method 2: Window + ROW_NUMBER (keep most recent)
w = Window.partitionBy("customer_id").orderBy(col("updated_at").desc())
df_deduped = df.withColumn("rn", row_number().over(w)) \
               .filter(col("rn") == 1) \
               .drop("rn")

# Method 3: Aggregate to get canonical record
df_canonical = df.groupBy("email").agg(
    min("customer_id").alias("customer_id"),
    max("updated_at").alias("last_updated"),
    first("name", ignorenulls=True).alias("name")
)
```

### Null Handling

```python
# Fill nulls
df.fillna(0)                           # All numeric columns
df.fillna("unknown")                   # All string columns
df.fillna({"age": 0, "name": "unknown", "email": "no-email@na.com"})

# Drop rows with nulls
df.dropna()                            # Any null
df.dropna(how="all")                   # All columns null
df.dropna(subset=["email", "name"])    # Specific columns
df.dropna(thresh=3)                    # At least 3 non-null values required

# Replace specific values
df.replace(0, None, subset=["age"])    # Replace 0 with null
df.replace({"N/A": None, "null": None, "NULL": None})

# Coalesce (first non-null)
df.withColumn("email", coalesce(col("email"), col("backup_email"), lit("unknown")))

# Forward fill pattern (PySpark)
w_ff = Window.partitionBy("sensor_id").orderBy("timestamp").rowsBetween(Window.unboundedPreceding, 0)
df = df.withColumn("temp_filled", last("temperature", ignorenulls=True).over(w_ff))
```

### Type Casting & Coercion

```python
# Cast with error handling
from pyspark.sql.functions import col, when, regexp_replace

# Safe string to number
df = df.withColumn(
    "amount_clean",
    when(
        col("amount_str").rlike(r"^\d+\.?\d*$"),
        col("amount_str").cast("double")
    ).otherwise(None)
)

# Strip currency symbols and convert
df = df.withColumn(
    "price_numeric",
    regexp_replace(
        regexp_replace(col("price_str"), r"[\$,£€]", ""),
        r"\s", ""
    ).cast("double")
)

# Date parsing with multiple formats
from pyspark.sql.functions import to_date, coalesce
df = df.withColumn(
    "parsed_date",
    coalesce(
        to_date(col("date_str"), "yyyy-MM-dd"),
        to_date(col("date_str"), "MM/dd/yyyy"),
        to_date(col("date_str"), "dd-MMM-yyyy")
    )
)
```

### Flattening Nested/Struct Data

```python
# Flatten StructType columns
from pyspark.sql.functions import col

# Method 1: Dot notation
df.select(
    col("order_id"),
    col("shipping.address").alias("ship_address"),
    col("shipping.city").alias("ship_city"),
    col("shipping.zip").alias("ship_zip")
)

# Method 2: Programmatic flattening
def flatten_struct(schema, prefix=""):
    fields = []
    for field in schema.fields:
        col_name = f"{prefix}.{field.name}" if prefix else field.name
        if isinstance(field.dataType, StructType):
            fields.extend(flatten_struct(field.dataType, col_name))
        else:
            alias = col_name.replace(".", "_")
            fields.append(col(col_name).alias(alias))
    return fields

df_flat = df.select(flatten_struct(df.schema))

# Explode arrays
from pyspark.sql.functions import explode, posexplode

# explode: one row per array element
df_items = df.withColumn("item", explode(col("line_items"))) \
             .select("order_id", "item.product_id", "item.qty", "item.price")

# posexplode: adds position index
df_items = df.select(
    "order_id",
    posexplode("line_items").alias("pos", "item")
).select("order_id", "pos", "item.*")

# explode_outer: keeps rows with null/empty arrays
from pyspark.sql.functions import explode_outer
df.withColumn("tag", explode_outer(col("tags")))
```

### SCD Type 2 Pattern

```python
# Slowly Changing Dimension Type 2 merge
# Expire old records and insert new versions

from pyspark.sql.functions import *
from pyspark.sql.window import Window

def apply_scd2(existing_df, updates_df, key_cols, tracked_cols, effective_date):
    """
    existing_df: current SCD2 table with effective_from, effective_to, is_current
    updates_df: incoming changes
    """
    FUTURE_DATE = "9999-12-31"

    # Find records that changed
    joined = existing_df.filter(col("is_current") == True) \
        .join(updates_df, on=key_cols, how="left") \
        .withColumn(
            "has_changed",
            reduce(lambda a, b: a | b, [
                col(f"new_{c}") != col(c)
                for c in tracked_cols
            ])
        )

    # Close expired records
    closed = joined.filter(col("has_changed") == True) \
        .withColumn("effective_to", lit(effective_date)) \
        .withColumn("is_current", lit(False)) \
        .select(existing_df.columns)

    # New versions for changed records
    new_versions = joined.filter(col("has_changed") == True) \
        .select(
            *key_cols,
            *[col(f"new_{c}").alias(c) for c in tracked_cols],
            lit(effective_date).alias("effective_from"),
            lit(FUTURE_DATE).alias("effective_to"),
            lit(True).alias("is_current")
        )

    # Net-new records (not in existing)
    net_new = updates_df.join(
        existing_df.filter(col("is_current")),
        on=key_cols,
        how="left_anti"
    ).withColumn("effective_from", lit(effective_date)) \
     .withColumn("effective_to", lit(FUTURE_DATE)) \
     .withColumn("is_current", lit(True))

    # Unchanged records
    unchanged = joined.filter(
        col("has_changed").isNull() | (col("has_changed") == False)
    ).select(existing_df.columns)

    return unchanged.union(closed).union(new_versions).union(net_new)
```

---

## 12. String, Date & JSON Transformations

### String Functions

```python
from pyspark.sql.functions import *

# Case
df.withColumn("name_upper", upper(col("name")))
df.withColumn("name_lower", lower(col("name")))

# Trim
df.withColumn("name_clean", trim(col("name")))
df.withColumn("name_ltrim", ltrim(col("name")))

# Concat
df.withColumn("full_name", concat_ws(" ", col("first_name"), col("last_name")))
df.withColumn("code", concat(col("region"), lit("_"), col("dept_id")))

# Substring
df.withColumn("first_5", substring(col("text"), 1, 5))  # 1-indexed
df.withColumn("area_code", substring(col("phone"), 1, 3))

# Split
df.withColumn("name_parts", split(col("full_name"), " "))
df.withColumn("first_name", split(col("full_name"), " ").getItem(0))

# Regex
df.withColumn("digits_only", regexp_replace(col("phone"), r"[^0-9]", ""))
df.withColumn("campaign_id", regexp_extract(col("url"), r"campaign=([^&]+)", 1))

# Pad
df.withColumn("padded_id", lpad(col("id").cast("string"), 10, "0"))

# Length
df.withColumn("name_length", length(col("name")))

# Contains / locate
df.filter(col("description").contains("organic"))
df.withColumn("keyword_pos", locate("sale", col("title")))

# URL parsing
df.withColumn("utm_source", regexp_extract(col("url"), r"[?&]utm_source=([^&]+)", 1))
df.withColumn("utm_medium", regexp_extract(col("url"), r"[?&]utm_medium=([^&]+)", 1))
```

### Date Functions

```python
from pyspark.sql.functions import *

# Current
df.withColumn("today", current_date())
df.withColumn("now", current_timestamp())

# Parsing
df.withColumn("parsed_date", to_date(col("date_str"), "yyyy-MM-dd"))
df.withColumn("parsed_ts", to_timestamp(col("ts_str"), "yyyy-MM-dd HH:mm:ss"))

# Formatting
df.withColumn("formatted_date", date_format(col("order_date"), "MMMM dd, yyyy"))
df.withColumn("yyyymmdd", date_format(col("order_date"), "yyyyMMdd"))

# Arithmetic
df.withColumn("next_week", date_add(col("order_date"), 7))
df.withColumn("prev_month", date_sub(col("order_date"), 30))
df.withColumn("age_days", datediff(current_date(), col("order_date")))
df.withColumn("months_old", months_between(current_date(), col("created_at")).cast("int"))

# Extraction
df.withColumn("yr", year(col("order_date")))
df.withColumn("mo", month(col("order_date")))
df.withColumn("dy", dayofmonth(col("order_date")))
df.withColumn("dow", dayofweek(col("order_date")))  # 1=Sun, 7=Sat
df.withColumn("doy", dayofyear(col("order_date")))
df.withColumn("qtr", quarter(col("order_date")))
df.withColumn("wk", weekofyear(col("order_date")))
df.withColumn("hr", hour(col("event_timestamp")))

# Truncate
df.withColumn("week_start", date_trunc("week", col("order_date")))
df.withColumn("month_start", date_trunc("month", col("order_date")))
df.withColumn("hour_bucket", date_trunc("hour", col("event_timestamp")))

# Unix timestamp conversion
df.withColumn("unix_ts", unix_timestamp(col("event_datetime"), "yyyy-MM-dd HH:mm:ss"))
df.withColumn("ts_from_unix", from_unixtime(col("epoch_ms") / 1000, "yyyy-MM-dd HH:mm:ss"))

# Timezone
df.withColumn("local_ts", from_utc_timestamp(col("utc_ts"), "America/Los_Angeles"))
df.withColumn("utc_ts", to_utc_timestamp(col("local_ts"), "America/Los_Angeles"))
```

### JSON Handling

```python
from pyspark.sql.functions import from_json, to_json, json_tuple, get_json_object
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

# Define schema for JSON column
json_schema = StructType([
    StructField("user_id", StringType()),
    StructField("page", StringType()),
    StructField("campaign", StructType([
        StructField("id", StringType()),
        StructField("name", StringType())
    ])),
    StructField("revenue", DoubleType())
])

# Parse JSON string column
df = df.withColumn("props", from_json(col("properties_json"), json_schema))
df.select("event_id", "props.user_id", "props.campaign.id", "props.revenue").show()

# json_tuple: extract multiple values at once
df = df.select(
    "event_id",
    *[json_tuple(col("properties"), "user_id", "page", "campaign")
      .alias("user_id", "page", "campaign")]
)

# get_json_object: single value with JSONPath
df = df.withColumn("user_id", get_json_object(col("props"), "$.user_id"))
df = df.withColumn("campaign_id", get_json_object(col("props"), "$.campaign.id"))

# Convert struct back to JSON string
df = df.withColumn("campaign_json", to_json(col("campaign_struct")))

# Handle variable/unknown JSON schema
# Read as string, parse what you know
df = spark.read.text("gs://bucket/events.jsonl") \
    .withColumn("user_id", get_json_object(col("value"), "$.user_id")) \
    .withColumn("event_type", get_json_object(col("value"), "$.event_type")) \
    .withColumn("timestamp", get_json_object(col("value"), "$.timestamp").cast("timestamp"))
```

---

## 13. UDFs — User Defined Functions

### Python UDFs (Use with Caution — Performance Cost)

```python
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType, IntegerType, DoubleType

# Simple UDF
def normalize_phone(phone_str):
    if phone_str is None:
        return None
    import re
    digits = re.sub(r'[^0-9]', '', phone_str)
    return digits if len(digits) >= 10 else None

normalize_phone_udf = udf(normalize_phone, StringType())
df = df.withColumn("phone_clean", normalize_phone_udf(col("phone_raw")))

# Decorator syntax
@udf(returnType=StringType())
def classify_customer(spend, recency_days):
    if spend is None or recency_days is None:
        return "unknown"
    if spend >= 5000 and recency_days <= 30:
        return "VIP Active"
    elif spend >= 1000:
        return "Regular"
    elif recency_days > 365:
        return "Dormant"
    else:
        return "New"

df = df.withColumn(
    "customer_class",
    classify_customer(col("annual_spend"), col("days_since_purchase"))
)

# Register for Spark SQL
spark.udf.register("normalize_phone", normalize_phone, StringType())
df = spark.sql("SELECT normalize_phone(phone_raw) FROM customers")
```

### Pandas UDFs (Vectorized — Much Faster than Python UDFs)

```python
from pyspark.sql.functions import pandas_udf, PandasUDFType
import pandas as pd

# Scalar Pandas UDF (element-wise)
@pandas_udf(DoubleType())
def calculate_discount(prices: pd.Series, member_status: pd.Series) -> pd.Series:
    discounts = pd.Series(0.0, index=prices.index)
    discounts[member_status == "premium"] = prices[member_status == "premium"] * 0.1
    discounts[member_status == "standard"] = prices[member_status == "standard"] * 0.05
    return discounts

df = df.withColumn("discount", calculate_discount(col("price"), col("member_status")))

# Iterator Pandas UDF (batch processing)
from typing import Iterator
@pandas_udf(DoubleType())
def vectorized_score(batch_iter: Iterator[pd.Series]) -> Iterator[pd.Series]:
    import numpy as np
    for series in batch_iter:
        yield np.log1p(series.fillna(0))

# Grouped Map Pandas UDF (apply function per group)
from pyspark.sql.functions import pandas_udf
@pandas_udf(df.schema)
def normalize_within_group(group_df: pd.DataFrame) -> pd.DataFrame:
    group_df["normalized_spend"] = (
        (group_df["spend"] - group_df["spend"].mean())
        / group_df["spend"].std()
    )
    return group_df

df = df.groupBy("region").applyInPandas(normalize_within_group, schema=df.schema)
```

---

## 14. Performance Optimization

### Partitioning Strategy

```python
# Check current partitioning
df.rdd.getNumPartitions()  # Current number of partitions

# Repartition (full shuffle — use for increasing partitions or changing partition key)
df = df.repartition(200)                    # By count
df = df.repartition(200, "customer_id")     # By column
df = df.repartition("customer_id", "date")  # By multiple columns

# Coalesce (no shuffle — only for reducing partitions)
df = df.coalesce(10)  # Reduce to 10 partitions (e.g., before writing small files)

# Rule of thumb: ~128MB per partition
# total_data_size_bytes / (128 * 1024 * 1024) = target_partitions
```

### Caching & Persistence

```python
from pyspark import StorageLevel

# Cache (in memory, MEMORY_AND_DISK by default for DataFrames)
df.cache()   # Lazy — only caches when action is called
df.persist() # Same as cache()

# Custom storage levels
df.persist(StorageLevel.MEMORY_ONLY)         # Risk OOM on large data
df.persist(StorageLevel.MEMORY_AND_DISK)     # Safe default
df.persist(StorageLevel.DISK_ONLY)           # For very large data
df.persist(StorageLevel.MEMORY_AND_DISK_SER) # Serialized — less memory, more CPU

# Force cache evaluation
df.cache().count()  # Action to trigger caching

# Unpersist when done
df.unpersist()

# When to cache:
# - DataFrame used multiple times (3+ actions)
# - Expensive to recompute (many joins, complex aggregations)
# When NOT to cache:
# - Used only once
# - Fits in a single scan
# - Very large data with limited memory
```

### Avoiding Common Performance Pitfalls

```python
# PITFALL 1: Collect on large datasets
df.collect()  # ❌ Pulls ALL data to driver — OOM risk
df.limit(100).collect()  # ✅ Safe sample
df.take(100)  # ✅ Safe

# PITFALL 2: UDFs on large data (breaks Tungsten optimization)
# Prefer built-in functions over Python UDFs
# Bad: Python UDF for simple string operation
@udf(StringType())
def to_upper(s): return s.upper() if s else None
# Good: built-in function
from pyspark.sql.functions import upper
df.withColumn("name_upper", upper(col("name")))

# PITFALL 3: Iterating in driver code over large DF
for row in df.collect():  # ❌ Never do this
    process(row)
# Instead, use transformations or pandas_udf

# PITFALL 4: Creating many small files
df.write.parquet("gs://bucket/output/")  # Default: one file per partition
# Better:
df.coalesce(10).write.parquet("gs://bucket/output/")  # Control file count

# PITFALL 5: Skew in joins
# Check for skew:
df.groupBy("join_key").count().orderBy(col("count").desc()).show(20)

# PITFALL 6: Wrong shuffle partition count
spark.conf.set("spark.sql.shuffle.partitions", "200")  # Default: often wrong
# Rule: max(8, data_gb * 4) partitions
# For 50GB data: max(8, 200) = 200 partitions
```

### Broadcast Hash Join Deep Dive

```python
# When to broadcast:
# - Small table < autoBroadcastJoinThreshold (default 10MB, set to 100MB)
# - Lookup table (country codes, product categories)
# - Dimension tables in star schema

# Force broadcast
from pyspark.sql.functions import broadcast
result = large_df.join(broadcast(small_lookup_df), "key")

# Verify join strategy in execution plan
result.explain()
# Look for: BroadcastHashJoin in physical plan

# Disable broadcast (if you don't want it)
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "-1")
```

### AQE — Adaptive Query Execution (Spark 3.0+)

```python
# Enable all AQE features
spark.conf.set("spark.sql.adaptive.enabled", "true")

# Auto-coalesce shuffle partitions (reduces empty/small partitions)
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.minPartitionNum", "1")
spark.conf.set("spark.sql.adaptive.advisoryPartitionSizeInBytes", "134217728")  # 128MB

# Auto skew join handling
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.skewedPartitionFactor", "5")  # 5x median = skewed

# Convert sort-merge join to broadcast join at runtime
spark.conf.set("spark.sql.adaptive.localShuffleReader.enabled", "true")
```

---

## 15. Writing & Output Patterns

### Writing to GCS / Data Lake

```python
# Write Parquet (preferred format)
df.write \
    .mode("overwrite") \
    .option("compression", "snappy") \
    .parquet("gs://bucket/output/table/")

# Partition by date for efficient querying
df.write \
    .mode("overwrite") \
    .partitionBy("year", "month", "day") \
    .parquet("gs://bucket/output/events/")

# Append mode
df.write \
    .mode("append") \
    .partitionBy("date") \
    .parquet("gs://bucket/output/events/")

# Ignore if exists
df.write \
    .mode("ignore") \
    .parquet("gs://bucket/output/table/")

# Write modes:
# overwrite — replace all data
# append — add new data
# ignore — skip if exists
# error (default) — fail if exists
```

### Writing to BigQuery

```python
# Direct write to BigQuery
df.write \
    .format("bigquery") \
    .option("table", "project.dataset.table_name") \
    .option("temporaryGcsBucket", "my-temp-bucket") \
    .mode("overwrite") \
    .save()

# Append
df.write \
    .format("bigquery") \
    .option("table", "project.dataset.table_name") \
    .option("temporaryGcsBucket", "temp-bucket") \
    .mode("append") \
    .save()

# Control partitioning
df.write \
    .format("bigquery") \
    .option("table", "project.dataset.table_name") \
    .option("temporaryGcsBucket", "temp-bucket") \
    .option("partitionField", "event_date") \
    .option("clusteredFields", "user_id,event_type") \
    .save()
```

### File Count Control

```python
# Control number of output files
df.coalesce(1).write.csv("output/")     # Single file (use for small data)
df.repartition(10).write.parquet("out/") # 10 files
df.coalesce(5).write.parquet("out/")    # Reduce to 5 files (no shuffle)

# Write with controlled file size using maxRecordsPerFile
df.write \
    .option("maxRecordsPerFile", 1000000) \
    .parquet("output/")
```

---

## 16. Spark SQL

### Using Spark SQL

```python
# Register DataFrame as temp view
df.createOrReplaceTempView("orders")
df.createGlobalTempView("global_orders")  # Available across sessions

# Run SQL
result = spark.sql("""
    SELECT
        customer_id,
        SUM(amount) AS total_spend,
        COUNT(DISTINCT order_id) AS order_count,
        MAX(order_date) AS last_order
    FROM orders
    WHERE order_date >= DATE_SUB(CURRENT_DATE(), 365)
    GROUP BY customer_id
    HAVING SUM(amount) > 1000
    ORDER BY total_spend DESC
""")

# Window functions in Spark SQL
result = spark.sql("""
    SELECT
        customer_id,
        order_date,
        amount,
        SUM(amount) OVER (
            PARTITION BY customer_id
            ORDER BY order_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_total,
        LAG(amount, 1) OVER (PARTITION BY customer_id ORDER BY order_date) AS prev_order
    FROM orders
""")

# Mix DataFrames and SQL
df.createOrReplaceTempView("raw_events")
df_sessions = spark.sql("""
    WITH sessions AS (
        SELECT
            user_id,
            event_time,
            SUM(CASE WHEN TIMESTAMPDIFF(MINUTE, LAG(event_time)
                OVER (PARTITION BY user_id ORDER BY event_time), event_time) > 30
                OR LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time) IS NULL
                THEN 1 ELSE 0 END)
            OVER (PARTITION BY user_id ORDER BY event_time) AS session_id
        FROM raw_events
    )
    SELECT user_id, session_id, COUNT(*) AS events,
           MIN(event_time) AS start_time, MAX(event_time) AS end_time
    FROM sessions
    GROUP BY user_id, session_id
""")
```

---

## 17. Structured Streaming (Brief Overview)

### Micro-batch Processing

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import *

# Read from Kafka
df_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "broker1:9092,broker2:9092") \
    .option("subscribe", "ad_events") \
    .option("startingOffsets", "latest") \
    .load()

# Parse Kafka message
df_parsed = df_stream.select(
    col("key").cast("string"),
    from_json(col("value").cast("string"), event_schema).alias("event"),
    col("timestamp").alias("kafka_timestamp")
).select("key", "event.*", "kafka_timestamp")

# Stateful aggregation with watermark
df_agg = df_parsed \
    .withWatermark("event_time", "10 minutes") \
    .groupBy(
        window(col("event_time"), "5 minutes"),
        col("campaign_id")
    ) \
    .agg(
        count("*").alias("event_count"),
        sum("revenue").alias("total_revenue"),
        approx_count_distinct("user_id").alias("unique_users")
    )

# Write to BigQuery
query = df_agg.writeStream \
    .format("bigquery") \
    .option("table", "project.dataset.streaming_metrics") \
    .option("temporaryGcsBucket", "temp-bucket") \
    .option("checkpointLocation", "gs://bucket/checkpoints/ad_metrics") \
    .trigger(processingTime="1 minute") \
    .outputMode("append") \
    .start()

query.awaitTermination()
```

---

## 18. Common Pipeline Patterns

### Full ETL Pipeline

```python
def run_martech_etl(spark, run_date):
    """Full ETL: raw clickstream → enriched events → campaign metrics"""

    # Step 1: Ingest
    raw = spark.read \
        .schema(CLICKSTREAM_SCHEMA) \
        .option("basePath", "gs://raw/clickstream/") \
        .parquet(f"gs://raw/clickstream/dt={run_date}/")

    # Step 2: Clean
    cleaned = raw \
        .filter(col("user_id").isNotNull()) \
        .filter(col("event_timestamp").isNotNull()) \
        .withColumn("event_date", to_date(col("event_timestamp"))) \
        .withColumn("utm_source", regexp_extract(col("page_url"), r"utm_source=([^&]+)", 1)) \
        .withColumn("utm_campaign", regexp_extract(col("page_url"), r"utm_campaign=([^&]+)", 1)) \
        .dropDuplicates(["event_id"]) \
        .cache()

    cleaned.count()  # Force cache

    # Step 3: Enrich with member data
    members = spark.read.parquet("gs://curated/members/")
    enriched = cleaned.join(
        broadcast(members.select("member_id", "membership_tier", "signup_date")),
        on=cleaned["user_id"] == members["member_id"],
        how="left"
    )

    # Step 4: Create metrics
    metrics = enriched \
        .groupBy("utm_campaign", "event_date", "membership_tier") \
        .agg(
            countDistinct("user_id").alias("unique_users"),
            count("*").alias("total_events"),
            sum(when(col("event_type") == "purchase", col("revenue")).otherwise(0)).alias("revenue"),
            sum(when(col("event_type") == "purchase", 1).otherwise(0)).alias("conversions"),
            countDistinct(when(col("event_type") == "purchase", col("user_id"))).alias("converting_users")
        ) \
        .withColumn("cvr", col("conversions") / col("unique_users")) \
        .withColumn("rpc", col("revenue") / col("unique_users"))

    # Step 5: Write
    metrics.write \
        .mode("overwrite") \
        .partitionBy("event_date") \
        .parquet(f"gs://curated/campaign_metrics/")

    # Write to BigQuery for reporting
    metrics.write \
        .format("bigquery") \
        .option("table", "analytics.campaign_daily_metrics") \
        .option("temporaryGcsBucket", "temp-bucket") \
        .mode("append") \
        .save()

    cleaned.unpersist()
    return metrics.count()
```

### Data Quality Validation in PySpark

```python
def validate_dataframe(df, rules):
    """
    rules = [
        {"name": "no_null_user_id", "condition": col("user_id").isNotNull()},
        {"name": "positive_revenue", "condition": col("revenue") >= 0},
        {"name": "valid_event_type", "condition": col("event_type").isin(VALID_EVENT_TYPES)}
    ]
    """
    total_rows = df.count()
    results = []

    for rule in rules:
        failing = df.filter(~rule["condition"]).count()
        pass_rate = (total_rows - failing) / total_rows * 100
        results.append({
            "rule": rule["name"],
            "total": total_rows,
            "failing": failing,
            "pass_rate": round(pass_rate, 4)
        })

    # Create summary DataFrame
    schema = StructType([
        StructField("rule", StringType()),
        StructField("total", LongType()),
        StructField("failing", LongType()),
        StructField("pass_rate", DoubleType())
    ])
    return spark.createDataFrame(results, schema)
```

---

## 19. Interview Q&A Bank

### Architecture Questions

**Q: Explain the difference between transformations and actions in Spark.**
A: Transformations are lazy — they define what to compute but don't execute until an action is called. Spark builds a DAG of transformations (logical plan) and optimizes it using Catalyst. Actions trigger physical execution: count(), collect(), write(), show(). This model allows Spark to optimize the entire computation graph rather than executing each step sequentially.

**Q: What is a shuffle and why is it expensive?**
A: A shuffle occurs when data must be redistributed across partitions — happens with groupBy, join, repartition, distinct. It's expensive because: (1) data must be written to disk (spill), (2) transferred over network, (3) read from disk by reducers. Strategies to minimize: broadcast joins, partition pruning, choosing right join types.

**Q: Explain the difference between repartition() and coalesce().**
A: `repartition(n)` — full shuffle, can increase or decrease partitions, data evenly distributed. `coalesce(n)` — no shuffle, can only decrease partitions by merging, may result in uneven partition sizes. Use `repartition` when you need balanced partitions or want to change partition key; use `coalesce` when reducing partition count before writing to avoid small files.

**Q: What is data skew and how do you handle it?**
A: Data skew occurs when partition sizes are unbalanced — one executor processes 100x more data than others, creating a bottleneck. Detection: `df.groupBy("join_key").count().sort("count", ascending=False).show(20)`. Solutions: (1) Salting — add random prefix to hot keys in both tables; (2) Broadcast join if skewed table is the smaller one; (3) Skew hints in Spark 3; (4) Two-phase aggregation (pre-aggregate locally then globally); (5) AQE skewJoin enabled.

**Q: What caching strategy would you use for a multi-step ML feature pipeline?**
A: Cache DataFrames that are reused in multiple downstream transformations. Use `MEMORY_AND_DISK` to avoid OOM. Cache after expensive operations (joins, groupBy) that are computed once but read multiple times. Unpersist after the last use to free memory. Avoid caching very large DataFrames (> 30% of executor memory) as they cause GC pressure.

**Q: How does the Catalyst optimizer work?**
A: Catalyst takes the logical query plan through 4 phases: (1) Analysis — resolve references using catalog; (2) Logical optimization — apply rules like predicate pushdown, constant folding, column pruning; (3) Physical planning — generate multiple physical plans and select cheapest based on cost model; (4) Code generation — Tungsten generates bytecode for CPU efficiency.

**Q: Explain narrow vs wide transformations.**
A: Narrow: each input partition contributes to at most one output partition — no shuffle. Examples: filter(), select(), map(), withColumn(). Wide: input partitions may contribute to multiple output partitions — requires shuffle. Examples: groupBy(), join(), repartition(), distinct(). Wide transformations create stage boundaries in the DAG.

### Practical/Coding Questions

**Q: How do you handle late-arriving data in a daily batch pipeline?**
A: Use partitioned writes with `mode("append")` and a `_dt` partition for processing date separate from event date. Implement lookback logic — on each run, reprocess last N days to catch late data. Track processed event timestamps in a metadata table. Example: `df.write.partitionBy("event_date").mode("overwrite").save()` reprocesses each partition independently.

**Q: De-duplicate a large dataset keeping the most recent version by customer_id.**
```python
from pyspark.sql.window import Window
from pyspark.sql.functions import row_number, col

w = Window.partitionBy("customer_id").orderBy(col("updated_at").desc())
df_deduped = df.withColumn("rn", row_number().over(w)).filter(col("rn") == 1).drop("rn")
```

**Q: Calculate a 7-day rolling average of revenue per campaign in PySpark.**
```python
from pyspark.sql.window import Window
from pyspark.sql.functions import avg, col

w = Window.partitionBy("campaign_id").orderBy("event_date").rowsBetween(-6, 0)
df = df.withColumn("rolling_7d_avg_revenue", avg("revenue").over(w))
```

**Q: Find the first and last purchase for each customer, and their total spend.**
```python
from pyspark.sql.functions import min, max, sum, col

result = df.groupBy("customer_id").agg(
    min("purchase_date").alias("first_purchase"),
    max("purchase_date").alias("last_purchase"),
    sum("amount").alias("total_spend"),
    (max("purchase_date").cast("long") - min("purchase_date").cast("long")) / 86400
        .alias("customer_tenure_days")
)
```
