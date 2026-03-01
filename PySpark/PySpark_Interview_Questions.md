# PySpark Interview Questions & Answers - Complete Guide

> **Last Updated:** 2024  
> **Total Questions:** 80+  
> **Focus:** DataFrame API, RDD, Transformations, Performance Optimization  
> **Level:** Data Engineer, Big Data Developer

---

## Table of Contents

1. [PySpark Fundamentals](#1-pyspark-fundamentals)
2. [DataFrame Creation & Schema](#2-dataframe-creation--schema)
3. [Basic Transformations](#3-basic-transformations)
4. [Filtering & Selection](#4-filtering--selection)
5. [Aggregations & GROUP BY](#5-aggregations--group-by)
6. [JOIN Operations](#6-join-operations)
7. [Window Functions](#7-window-functions)
8. [Built-in Functions](#8-built-in-functions)
9. [User-Defined Functions (UDFs)](#9-user-defined-functions-udfs)
10. [Advanced Transformations](#10-advanced-transformations)
11. [Performance Optimization](#11-performance-optimization)
12. [RDD Operations](#12-rdd-operations)
13. [Spark Streaming](#13-spark-streaming)
14. [Machine Learning (MLlib)](#14-machine-learning-mllib)
15. [Real-World Scenarios](#15-real-world-scenarios)

---

## 1. PySpark Fundamentals

### Q1: What is PySpark and its architecture?

**Answer:**

PySpark is the Python API for Apache Spark, enabling Python developers to leverage Spark's distributed computing capabilities.

**Key Components:**
```python
from pyspark.sql import SparkSession

# Initialize Spark Session
spark = SparkSession.builder \
    .appName("MyApp") \
    .master("local[*]") \
    .config("spark.executor.memory", "4g") \
    .config("spark.driver.memory", "2g") \
    .getOrCreate()

# Get Spark Context
sc = spark.sparkContext
```

**Architecture:**
- **Driver:** Orchestrates execution
- **Executor:** Executes tasks on worker nodes
- **Cluster Manager:** Allocates resources (YARN, Mesos, Standalone)

---

### Q2: Explain lazy evaluation in PySpark

**Answer:**

Transformations are not executed immediately; Spark builds a DAG and executes only when an action is called.

```python
# Transformations (lazy)
df = spark.read.csv("data.csv")
df_filtered = df.filter(df.age > 25)  # Not executed yet
df_selected = df_filtered.select("name", "age")  # Still not executed

# Action (triggers execution)
df_selected.show()  # Now the entire DAG executes
df_selected.count()  # Another action
```

**Benefits:**
- Query optimization
- Reduced I/O operations
- Better resource utilization

---

### Q3: RDD vs DataFrame vs Dataset

**Answer:**

```python
# 1. RDD (Low-level, immutable)
rdd = sc.parallelize([1, 2, 3, 4, 5])
rdd_squared = rdd.map(lambda x: x ** 2)

# 2. DataFrame (High-level, schema-based)
data = [(1, "Alice"), (2, "Bob")]
df = spark.createDataFrame(data, ["id", "name"])

# 3. Dataset (Type-safe, not available in Python)
# Only available in Scala/Java
```

**Comparison:**

| Feature | RDD | DataFrame | Dataset |
|---------|-----|-----------|---------|
| API Level | Low | High | High |
| Type Safety | No | No | Yes (Scala/Java) |
| Optimization | No | Yes (Catalyst) | Yes |
| Schema | No | Yes | Yes |
| Language | All | All | Scala/Java |

---

## 2. DataFrame Creation & Schema

### Q4: Creating DataFrames from various sources

**Answer:**

```python
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

# 1. From list of tuples
data = [("Alice", 25), ("Bob", 30)]
df1 = spark.createDataFrame(data, ["name", "age"])

# 2. From list of Row objects
from pyspark.sql import Row
rows = [Row(name="Alice", age=25), Row(name="Bob", age=30)]
df2 = spark.createDataFrame(rows)

# 3. With explicit schema
schema = StructType([
    StructField("name", StringType(), True),
    StructField("age", IntegerType(), True)
])
df3 = spark.createDataFrame(data, schema)

# 4. From CSV
df_csv = spark.read \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .csv("path/to/file.csv")

# 5. From JSON
df_json = spark.read.json("path/to/file.json")

# 6. From Parquet
df_parquet = spark.read.parquet("path/to/file.parquet")

# 7. From Hive table
df_hive = spark.sql("SELECT * FROM database.table")

# 8. From JDBC
df_jdbc = spark.read \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://localhost:5432/db") \
    .option("dbtable", "schema.table") \
    .option("user", "username") \
    .option("password", "password") \
    .load()
```

---

### Q5: Schema operations and manipulation

**Answer:**

```python
# View schema
df.printSchema()
df.schema
df.dtypes  # List of (column_name, type)

# Rename columns
df_renamed = df.withColumnRenamed("old_name", "new_name")

# Cast column types
from pyspark.sql.functions import col
df_cast = df.withColumn("age", col("age").cast("double"))

# Add new column
df_new = df.withColumn("age_plus_10", col("age") + 10)

# Drop columns
df_dropped = df.drop("column_name")

# Select specific columns
df_selected = df.select("name", "age")

# Select with expressions
df.selectExpr("name", "age * 2 as double_age")
```

---

## 3. Basic Transformations

### Q6: Select, SelectExpr, and Column Operations

**Answer:**

```python
from pyspark.sql.functions import col, lit, expr

# Basic select
df.select("name", "age")

# Select with col()
df.select(col("name"), col("age"))

# Select with expressions
df.select(
    col("name"),
    (col("age") + 5).alias("age_plus_5"),
    (col("salary") * 1.1).alias("salary_increased")
)

# SelectExpr - SQL expressions
df.selectExpr(
    "name",
    "age * 2 as double_age",
    "CASE WHEN age > 30 THEN 'Senior' ELSE 'Junior' END as category"
)

# Adding literal columns
df.select(
    col("name"),
    lit("USA").alias("country"),
    lit(2024).alias("year")
)

# Using expr() for complex expressions
df.select(
    expr("CASE WHEN salary > 50000 THEN 'High' ELSE 'Low' END as salary_category")
)
```

---

## 4. Filtering & Selection

### Q7: Filter and WHERE operations

**Answer:**

```python
from pyspark.sql.functions import col

# Simple filter
df.filter(col("age") > 25)
df.where(col("age") > 25)  # Same as filter

# Multiple conditions (AND)
df.filter((col("age") > 25) & (col("salary") > 50000))

# OR conditions
df.filter((col("age") > 25) | (col("age") < 20))

# IN clause
df.filter(col("name").isin(["Alice", "Bob", "Charlie"]))

# NOT IN
df.filter(~col("name").isin(["Alice", "Bob"]))

# NULL checks
df.filter(col("age").isNull())
df.filter(col("age").isNotNull())

# LIKE pattern matching
df.filter(col("name").like("A%"))  # Starts with A
df.filter(col("name").rlike("^A.*"))  # Regex

# BETWEEN
df.filter(col("age").between(20, 30))

# Using SQL expression
df.filter("age > 25 AND salary > 50000")

# Complex nested conditions
df.filter(
    ((col("age") > 25) & (col("dept") == "IT")) |
    ((col("salary") > 60000) & (col("dept") == "Sales"))
)
```

---

## 5. Aggregations & GROUP BY

### Q8: GroupBy and aggregation functions

**Answer:**

```python
from pyspark.sql.functions import (
    count, sum, avg, max, min, stddev, variance,
    collect_list, collect_set, countDistinct, approx_count_distinct
)

# Basic aggregations
df.groupBy("department").agg(
    count("*").alias("employee_count"),
    avg("salary").alias("avg_salary"),
    max("salary").alias("max_salary"),
    min("salary").alias("min_salary"),
    sum("salary").alias("total_salary")
)

# Multiple groupBy columns
df.groupBy("department", "gender").agg(
    count("*").alias("count"),
    avg("salary").alias("avg_salary")
)

# Collect operations
df.groupBy("department").agg(
    collect_list("name").alias("all_names"),
    collect_set("skill").alias("unique_skills")
)

# Count distinct
df.groupBy("department").agg(
    countDistinct("job_title").alias("unique_jobs")
)

# Approximate count distinct (faster for large datasets)
df.groupBy("department").agg(
    approx_count_distinct("employee_id", rsd=0.05).alias("approx_count")
)

# Statistical aggregations
df.groupBy("department").agg(
    stddev("salary").alias("salary_stddev"),
    variance("salary").alias("salary_variance")
)

# Using agg with dictionary
df.groupBy("department").agg({
    "salary": "avg",
    "age": "max",
    "employee_id": "count"
})

# HAVING clause equivalent
df.groupBy("department") \
    .agg(avg("salary").alias("avg_salary")) \
    .filter(col("avg_salary") > 60000)
```

---

## 6. JOIN Operations

### Q9: All types of JOINs in PySpark

**Answer:**

```python
# Sample DataFrames
employees = spark.createDataFrame([
    (1, "Alice", 101),
    (2, "Bob", 102),
    (3, "Charlie", None),
    (4, "David", 103)
], ["emp_id", "name", "dept_id"])

departments = spark.createDataFrame([
    (101, "HR"),
    (102, "IT"),
    (103, "Finance"),
    (104, "Marketing")
], ["dept_id", "dept_name"])

# 1. INNER JOIN (default)
inner_join = employees.join(
    departments,
    employees.dept_id == departments.dept_id,
    "inner"
)

# 2. LEFT (OUTER) JOIN
left_join = employees.join(departments, "dept_id", "left")

# 3. RIGHT (OUTER) JOIN
right_join = employees.join(departments, "dept_id", "right")

# 4. FULL OUTER JOIN
full_join = employees.join(departments, "dept_id", "outer")

# 5. LEFT SEMI JOIN (returns only left side rows that match)
semi_join = employees.join(departments, "dept_id", "left_semi")

# 6. LEFT ANTI JOIN (returns left side rows that don't match)
anti_join = employees.join(departments, "dept_id", "left_anti")

# 7. CROSS JOIN (Cartesian product)
cross_join = employees.crossJoin(departments)

# Join on multiple columns
result = df1.join(
    df2,
    (df1.col1 == df2.col1) & (df1.col2 == df2.col2),
    "inner"
)

# Join on column with same name
result = df1.join(df2, ["id", "date"], "inner")

# Self join with aliases
from pyspark.sql.functions import col

emp1 = employees.alias("e1")
emp2 = employees.alias("e2")
self_join = emp1.join(
    emp2,
    col("e1.manager_id") == col("e2.emp_id"),
    "left"
).select(
    col("e1.name").alias("employee"),
    col("e2.name").alias("manager")
)
```

---

### Q10: Broadcast JOIN for performance

**Answer:**

```python
from pyspark.sql.functions import broadcast

# Regular join (shuffles both sides)
large_df = spark.read.parquet("large_data.parquet")
small_df = spark.read.parquet("small_lookup.parquet")

regular_join = large_df.join(small_df, "key")

# Broadcast join (no shuffle for small table)
broadcast_join = large_df.join(
    broadcast(small_df),
    "key"
)

# Configure auto-broadcast threshold
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", 10 * 1024 * 1024)  # 10MB

# Disable auto-broadcast
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", -1)
```

**When to use:**
- Small dimension tables (< 100MB)
- Lookup/reference data
- One side fits in memory

---

## 7. Window Functions

### Q11: ROW_NUMBER, RANK, DENSE_RANK

**Answer:**

```python
from pyspark.sql.window import Window
from pyspark.sql.functions import row_number, rank, dense_rank, ntile

# Define window specification
window_spec = Window.partitionBy("department").orderBy(col("salary").desc())

# Apply ranking functions
df.select(
    col("name"),
    col("department"),
    col("salary"),
    row_number().over(window_spec).alias("row_num"),
    rank().over(window_spec).alias("rank"),
    dense_rank().over(window_spec).alias("dense_rank")
).show()

# NTILE - divide into n groups
df.select(
    col("name"),
    col("salary"),
    ntile(4).over(Window.orderBy("salary")).alias("quartile")
).show()
₹\
# Get top N per group
from pyspark.sql.functions import col

top_earners = df.select(
    col("*"),
    row_number().over(window_spec).alias("rank")
).filter(col("rank") <= 3)
```

---

### Q12: LAG, LEAD, and offset functions

**Answer:**

```python
from pyspark.sql.functions import lag, lead, first, last
from pyspark.sql.window import Window

window_spec = Window.partitionBy("employee_id").orderBy("date")

# LAG - previous row value
df.select(
    col("employee_id"),
    col("date"),
    col("salary"),
    lag(col("salary"), 1).over(window_spec).alias("prev_salary"),
    lag(col("salary"), 1, 0).over(window_spec).alias("prev_salary_default")
).show()

# LEAD - next row value
df.select(
    col("employee_id"),
    col("date"),
    col("salary"),
    lead(col("salary"), 1).over(window_spec).alias("next_salary")
).show()

# Calculate change from previous
df.select(
    col("employee_id"),
    col("date"),
    col("salary"),
    (col("salary") - lag(col("salary"), 1).over(window_spec)).alias("salary_change")
).show()

# FIRST and LAST value in window
dept_window = Window.partitionBy("department").orderBy("hire_date")

df.select(
    col("department"),
    col("name"),
    col("salary"),
    first(col("salary")).over(dept_window).alias("first_hire_salary"),
    last(col("salary")).over(dept_window).alias("last_hire_salary")
).show()
```

---

### Q13: Running totals and moving averages

**Answer:**

```python
from pyspark.sql.functions import sum, avg
from pyspark.sql.window import Window

# Running total (cumulative sum)
window_spec = Window.partitionBy("department") \
    .orderBy("date") \
    .rowsBetween(Window.unboundedPreceding, Window.currentRow)

df.select(
    col("department"),
    col("date"),
    col("sales"),
    sum(col("sales")).over(window_spec).alias("running_total")
).show()

# Moving average (last 3 rows)
moving_window = Window.partitionBy("department") \
    .orderBy("date") \
    .rowsBetween(-2, 0)

df.select(
    col("department"),
    col("date"),
    col("sales"),
    avg(col("sales")).over(moving_window).alias("moving_avg_3")
).show()

# Cumulative percentage
total_window = Window.partitionBy("department")
cumulative_window = Window.partitionBy("department") \
    .orderBy("date") \
    .rowsBetween(Window.unboundedPreceding, 0)

df.select(
    col("department"),
    col("date"),
    col("sales"),
    (sum(col("sales")).over(cumulative_window) / 
     sum(col("sales")).over(total_window) * 100).alias("cumulative_pct")
).show()

# Range-based window (time-based)
time_window = Window.partitionBy("product") \
    .orderBy("timestamp") \
    .rangeBetween(-86400, 0)  # Last 24 hours in seconds

df.select(
    col("product"),
    col("timestamp"),
    col("sales"),
    sum(col("sales")).over(time_window).alias("sales_last_24h")
).show()
```

---

## 8. Built-in Functions

### Q14: String functions

**Answer:**

```python
from pyspark.sql.functions import (
    upper, lower, initcap, length, trim, ltrim, rtrim,
    substring, concat, concat_ws, split, regexp_replace,
    regexp_extract, lpad, rpad, reverse, translate
)

# Case conversion
df.select(
    upper(col("name")).alias("upper_name"),
    lower(col("name")).alias("lower_name"),
    initcap(col("name")).alias("title_case")
).show()

# Length and trimming
df.select(
    length(col("name")).alias("name_length"),
    trim(col("name")).alias("trimmed"),
    ltrim(col("name")).alias("left_trimmed"),
    rtrim(col("name")).alias("right_trimmed")
).show()

# Substring
df.select(
    substring(col("name"), 1, 3).alias("first_3_chars")
).show()

# Concatenation
df.select(
    concat(col("first_name"), lit(" "), col("last_name")).alias("full_name"),
    concat_ws("-", col("first_name"), col("last_name")).alias("hyphenated")
).show()

# Split
df.select(
    split(col("name"), " ").alias("name_parts")
).show()

# Regex replace
df.select(
    regexp_replace(col("phone"), "[^0-9]", "").alias("clean_phone")
).show()

# Regex extract
df.select(
    regexp_extract(col("email"), "([a-zA-Z0-9._-]+)@", 1).alias("username")
).show()

# Padding
df.select(
    lpad(col("id"), 5, "0").alias("padded_id"),
    rpad(col("name"), 10, "_").alias("padded_name")
).show()
```

---

### Q15: Date and timestamp functions

**Answer:**

```python
from pyspark.sql.functions import (
    current_date, current_timestamp, date_add, date_sub, datediff,
    year, month, dayofmonth, dayofweek, dayofyear, weekofyear,
    hour, minute, second, to_date, to_timestamp, date_format,
    months_between, add_months, next_day, last_day, trunc,
    from_unixtime, unix_timestamp
)

# Current date and timestamp
df.select(
    current_date().alias("today"),
    current_timestamp().alias("now")
).show()

# Date arithmetic
df.select(
    date_add(col("date"), 7).alias("week_later"),
    date_sub(col("date"), 7).alias("week_before"),
    datediff(current_date(), col("date")).alias("days_diff")
).show()

# Extract date parts
df.select(
    year(col("date")).alias("year"),
    month(col("date")).alias("month"),
    dayofmonth(col("date")).alias("day"),
    dayofweek(col("date")).alias("day_of_week"),
    dayofyear(col("date")).alias("day_of_year"),
    weekofyear(col("date")).alias("week_num")
).show()

# Extract time parts
df.select(
    hour(col("timestamp")).alias("hour"),
    minute(col("timestamp")).alias("minute"),
    second(col("timestamp")).alias("second")
).show()

# Date conversions
df.select(
    to_date(col("date_string"), "yyyy-MM-dd").alias("date"),
    to_timestamp(col("ts_string"), "yyyy-MM-dd HH:mm:ss").alias("timestamp")
).show()

# Date formatting
df.select(
    date_format(col("date"), "dd/MM/yyyy").alias("formatted_date")
).show()

# Advanced date functions
df.select(
    months_between(col("end_date"), col("start_date")).alias("months_diff"),
    add_months(col("date"), 3).alias("3_months_later"),
    next_day(col("date"), "Monday").alias("next_monday"),
    last_day(col("date")).alias("last_day_of_month"),
    trunc(col("date"), "month").alias("first_day_of_month")
).show()

# Unix timestamp conversions
df.select(
    unix_timestamp(col("timestamp")).alias("unix_time"),
    from_unixtime(col("unix_time")).alias("timestamp")
).show()
```

---

### Q16: Mathematical and aggregate functions

**Answer:**

```python
from pyspark.sql.functions import (
    abs, sqrt, pow, exp, log, log10, sin, cos, tan,
    ceil, floor, round, rand, randn, greatest, least,
    mean, stddev_pop, stddev_samp, var_pop, var_samp
)

# Basic math
df.select(
    abs(col("value")).alias("absolute"),
    sqrt(col("value")).alias("square_root"),
    pow(col("value"), 2).alias("squared"),
    exp(col("value")).alias("exponential")
).show()

# Logarithms
df.select(
    log(col("value")).alias("natural_log"),
    log10(col("value")).alias("log_base_10")
).show()

# Trigonometric
df.select(
    sin(col("angle")).alias("sine"),
    cos(col("angle")).alias("cosine"),
    tan(col("angle")).alias("tangent")
).show()

# Rounding
df.select(
    ceil(col("value")).alias("ceiling"),
    floor(col("value")).alias("floor"),
    round(col("value"), 2).alias("rounded_2_decimals")
).show()

# Random numbers
df.select(
    rand(seed=42).alias("random_uniform"),
    randn(seed=42).alias("random_normal")
).show()

# Min/Max across columns
df.select(
    greatest(col("val1"), col("val2"), col("val3")).alias("maximum"),
    least(col("val1"), col("val2"), col("val3")).alias("minimum")
).show()
```

---

### Q17: Conditional functions (when, otherwise)

**Answer:**

```python
from pyspark.sql.functions import when, col, coalesce, lit

# Simple when-otherwise
df.select(
    col("age"),
    when(col("age") < 18, "Minor")
    .when(col("age") < 65, "Adult")
    .otherwise("Senior").alias("category")
).show()

# Multiple conditions
df.select(
    when((col("age") > 25) & (col("salary") > 50000), "High Earner")
    .when((col("age") > 25) & (col("salary") <= 50000), "Experienced")
    .otherwise("Junior").alias("classification")
).show()

# Coalesce (first non-null value)
df.select(
    coalesce(col("phone"), col("mobile"), lit("No contact")).alias("contact")
).show()

# Nested when statements
df.select(
    when(col("status") == "active",
         when(col("premium") == True, "Premium Active")
         .otherwise("Regular Active"))
    .otherwise("Inactive").alias("account_type")
).show()

# Using when with multiple columns
df.withColumn("bonus",
    when(col("performance") == "excellent", col("salary") * 0.2)
    .when(col("performance") == "good", col("salary") * 0.1)
    .otherwise(0)
).show()

# Multiple conditions with complex logic
df.select(
    when(
        (col("dept") == "IT") & (col("experience") > 5),
        lit("Senior Developer")
    ).when(
        (col("dept") == "IT") & (col("experience").between(2, 5)),
        lit("Mid-level Developer")
    ).when(
        col("dept") == "IT",
        lit("Junior Developer")
    ).otherwise(
        lit("Other")
    ).alias("role")
).show()
```

---

## 9. User-Defined Functions (UDFs)

### Q18: Creating and using UDFs

**Answer:**

```python
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType, IntegerType, ArrayType, StructType, StructField

# 1. Simple UDF
def categorize_age(age):
    if age < 18:
        return "Minor"
    elif age < 65:
        return "Adult"
    else:
        return "Senior"

age_category_udf = udf(categorize_age, StringType())
df.withColumn("category", age_category_udf(col("age"))).show()

# 2. UDF with decorator
@udf(returnType=IntegerType())
def square(x):
    return x * x

df.withColumn("age_squared", square(col("age"))).show()

# 3. UDF returning array
@udf(returnType=ArrayType(StringType()))
def split_name(full_name):
    return full_name.split(" ") if full_name else []

df.withColumn("name_parts", split_name(col("full_name"))).show()

# 4. UDF with multiple inputs
def calculate_bmi(height, weight):
    if height and weight and height > 0:
        return round(weight / (height ** 2), 2)
    return None

bmi_udf = udf(calculate_bmi, StringType())
df.withColumn("bmi", bmi_udf(col("height"), col("weight"))).show()

# 5. UDF returning struct
schema = StructType([
    StructField("first", StringType()),
    StructField("last", StringType())
])

@udf(returnType=schema)
def parse_name(full_name):
    parts = full_name.split(" ", 1)
    return (parts[0], parts[1] if len(parts) > 1 else "")

df.withColumn("name_struct", parse_name(col("full_name"))).show()
```

---

### Q19: Pandas UDF (Vectorized UDF)

**Answer:**

```python
from pyspark.sql.functions import pandas_udf, PandasUDFType
import pandas as pd

# 1. Scalar Pandas UDF (much faster than regular UDF)
@pandas_udf(IntegerType())
def pandas_square(s: pd.Series) -> pd.Series:
    return s * s

df.withColumn("age_squared", pandas_square(col("age"))).show()

# 2. Grouped Map Pandas UDF
schema = StructType([
    StructField("department", StringType()),
    StructField("avg_salary", IntegerType())
])

@pandas_udf(schema, PandasUDFType.GROUPED_MAP)
def normalize_salary(pdf):
    pdf['avg_salary'] = pdf['salary'].mean()
    return pdf[['department', 'avg_salary']].drop_duplicates()

df.groupby("department").apply(normalize_salary).show()

# 3. Grouped Aggregate Pandas UDF
@pandas_udf(IntegerType(), PandasUDFType.GROUPED_AGG)
def median_udf(v: pd.Series) -> int:
    return int(v.median())

df.groupby("department").agg(
    median_udf(col("salary")).alias("median_salary")
).show()

# 4. Window Pandas UDF
from pyspark.sql.window import Window

@pandas_udf(IntegerType(), PandasUDFType.GROUPED_AGG)
def mean_udf(v: pd.Series) -> int:
    return int(v.mean())

w = Window.partitionBy("department")
df.withColumn("dept_avg", mean_udf(col("salary")).over(w)).show()
```

---

## 10. Advanced Transformations

### Q20: Pivot and Unpivot

**Answer:**

```python
# Sample data
data = [
    ("Product1", "2024-01", 100),
    ("Product1", "2024-02", 150),
    ("Product2", "2024-01", 200),
    ("Product2", "2024-02", 250)
]
df = spark.createDataFrame(data, ["product", "month", "sales"])

# PIVOT - long to wide
pivot_df = df.groupBy("product").pivot("month").sum("sales")
pivot_df.show()

# Pivot with aggregation
pivot_agg = df.groupBy("product").pivot("month").agg(
    sum("sales").alias("total_sales"),
    avg("sales").alias("avg_sales")
)

# UNPIVOT - wide to long
from pyspark.sql.functions import expr, array, explode, lit, struct

# Method 1: Using stack
unpivot_df = pivot_df.selectExpr(
    "product",
    "stack(2, '2024-01', `2024-01`, '2024-02', `2024-02`) as (month, sales)"
)
unpivot_df.show()

# Method 2: Using array and explode
cols_to_unpivot = ["2024-01", "2024-02"]
unpivot_df2 = pivot_df.select(
    "product",
    explode(array([
        struct(lit(c).alias("month"), col(c).alias("sales"))
        for c in cols_to_unpivot
    ])).alias("unpivoted")
).select("product", "unpivoted.*")

unpivot_df2.show()
```

---

### Q21: Explode and array functions

**Answer:**

```python
from pyspark.sql.functions import (
    explode, explode_outer, posexplode, array, array_contains,
    array_distinct, array_intersect, array_union, array_except,
    array_sort, array_max, array_min, size, slice, element_at
)

# Create array column
df = df.withColumn("skills", array(lit("Python"), lit("SQL"), lit("Spark")))

# Explode array to rows
df.select(col("name"), explode(col("skills")).alias("skill")).show()

# Explode with position
df.select(col("name"), posexplode(col("skills")).alias("pos", "skill")).show()

# Explode outer (keeps null arrays)
df.select(col("name"), explode_outer(col("skills")).alias("skill")).show()

# Array operations
df.select(
    col("skills"),
    array_contains(col("skills"), "Python").alias("has_python"),
    size(col("skills")).alias("num_skills"),
    array_sort(col("skills")).alias("sorted_skills"),
    array_distinct(col("skills")).alias("unique_skills")
).show()

# Array set operations
df1 = df.withColumn("skills1", array(lit("Python"), lit("SQL")))
df2 = df1.withColumn("skills2", array(lit("SQL"), lit("Java")))

df2.select(
    array_intersect(col("skills1"), col("skills2")).alias("common"),
    array_union(col("skills1"), col("skills2")).alias("all"),
    array_except(col("skills1"), col("skills2")).alias("unique_to_1")
).show()

# Slice array
df.select(
    slice(col("skills"), 1, 2).alias("first_two_skills")
).show()

# Array max/min
df.withColumn("numbers", array(lit(1), lit(5), lit(3))).select(
    array_max(col("numbers")).alias("max"),
    array_min(col("numbers")).alias("min")
).show()

# Element at index
df.select(
    element_at(col("skills"), 1).alias("first_skill")
).show()
```

---

### Q22: Handling NULL values

**Answer:**

```python
from pyspark.sql.functions import col, isnan, isnull, when, coalesce

# Filter NULL values
df.filter(col("age").isNull())
df.filter(col("age").isNotNull())

# Drop rows with NULL
df.dropna()  # Drop rows with any NULL
df.dropna(how='all')  # Drop only if all columns are NULL
df.dropna(subset=['age', 'salary'])  # Drop if specified columns have NULL
df.dropna(thresh=2)  # Keep rows with at least 2 non-null values

# Fill NULL values
df.fillna(0)  # Fill all numeric NULLs with 0
df.fillna({'age': 0, 'name': 'Unknown'})  # Fill specific columns
df.na.fill({'age': 0, 'salary': 50000})  # Alternative syntax

# Replace specific values
df.replace(0, None, ['age'])  # Replace 0 with NULL in age column
df.replace(['UNKNOWN', 'N/A'], None)  # Replace multiple values with NULL

# Coalesce (first non-null value)
df.select(
    coalesce(col("primary_phone"), col("secondary_phone"), lit("No phone")).alias("phone")
).show()

# Using when for NULL handling
df.withColumn("age_filled",
    when(col("age").isNull(), 0).otherwise(col("age"))
).show()

# Check for NaN (Not a Number)
df.filter(isnan(col("value"))).show()

# Replace NaN with NULL or value
from pyspark.sql.functions import nanvl
df.withColumn("value_clean", nanvl(col("value"), lit(0))).show()

# Count NULLs
from pyspark.sql.functions import sum as spark_sum

df.select([
    spark_sum(when(col(c).isNull(), 1).otherwise(0)).alias(c)
    for c in df.columns
]).show()
```

---

## 11. Performance Optimization

### Q23: Caching and persistence

**Answer:**

```python
from pyspark import StorageLevel

# Cache in memory
df.cache()
df.count()  # Triggers caching

# Persist with storage level
df.persist(StorageLevel.MEMORY_AND_DISK)
df.persist(StorageLevel.MEMORY_ONLY)
df.persist(StorageLevel.DISK_ONLY)
df.persist(StorageLevel.MEMORY_AND_DISK_SER)  # Serialized
df.persist(StorageLevel.OFF_HEAP)

# Unpersist
df.unpersist()

# Check if cached
df.is_cached

# Best practices
expensive_df = df.filter(...).join(...).groupBy(...).agg(...)
expensive_df.cache()

# Use it multiple times
result1 = expensive_df.filter(col("age") > 30)
result2 = expensive_df.filter(col("salary") > 50000)

# Don't forget to unpersist when done
expensive_df.unpersist()
```

---

### Q24: Partitioning and repartitioning

**Answer:**

```python
# Check number of partitions
df.rdd.getNumPartitions()

# Repartition (full shuffle)
df_repartitioned = df.repartition(10)  # 10 partitions
df_repartitioned = df.repartition(10, "department")  # By column

# Coalesce (reduce partitions without full shuffle)
df_coalesced = df.coalesce(5)

# Partition by column when writing
df.write.partitionBy("year", "month").parquet("output/path")

# Repartition before expensive operations
df.repartition("department").groupBy("department").agg(...)

# Check partition distribution
from pyspark.sql.functions import spark_partition_id

df.select(spark_partition_id()).groupBy(spark_partition_id()).count().show()

# Repartition range
df.repartitionByRange(10, "id")

# Best practices
# - Repartition before wide transformations (groupBy, join)
# - Coalesce to reduce partitions before writing
# - Partition on columns used in WHERE clauses
# - Target: 128MB - 1GB per partition
```

---

### Q25: Broadcast variables and accumulators

**Answer:**

```python
# Broadcast variables (read-only shared data)
lookup_data = {"CA": "California", "NY": "New York", "TX": "Texas"}
broadcast_var = sc.broadcast(lookup_data)

# Use in UDF
@udf(StringType())
def get_state_name(code):
    return broadcast_var.value.get(code, "Unknown")

df.withColumn("state_name", get_state_name(col("state_code"))).show()

# Accumulators (write-only shared counters)
error_counter = sc.accumulator(0)
valid_counter = sc.accumulator(0)

def process_row(row):
    try:
        # Process row
        valid_counter.add(1)
        return row
    except Exception:
        error_counter.add(1)
        return None

# Note: Accumulators only guaranteed in actions
df.foreach(process_row)

print(f"Valid: {valid_counter.value}, Errors: {error_counter.value}")
```

---

## 12. RDD Operations

### Q26: RDD transformations and actions

**Answer:**

```python
# Create RDD
rdd = sc.parallelize([1, 2, 3, 4, 5])

# Transformations (lazy)
rdd_squared = rdd.map(lambda x: x ** 2)
rdd_filtered = rdd.filter(lambda x: x > 2)
rdd_flat = sc.parallelize([[1, 2], [3, 4]]).flatMap(lambda x: x)

# Key-value transformations
kv_rdd = sc.parallelize([("a", 1), ("b", 2), ("a", 3)])
kv_reduced = kv_rdd.reduceByKey(lambda x, y: x + y)
kv_grouped = kv_rdd.groupByKey()
kv_sorted = kv_rdd.sortByKey()

# Actions (trigger execution)
result = rdd.collect()
count = rdd.count()
first = rdd.first()
take_3 = rdd.take(3)
sum_all = rdd.reduce(lambda x, y: x + y)

# RDD to DataFrame
rdd_data = sc.parallelize([("Alice", 25), ("Bob", 30)])
df = rdd_data.toDF(["name", "age"])

# DataFrame to RDD
rdd_from_df = df.rdd
rdd_from_df.map(lambda row: row.name).collect()
```

---

## 13. Spark Streaming

### Q27: Structured Streaming basics

**Answer:**

```python
# Read from Kafka
df_stream = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "topic_name") \
    .load()

# Parse JSON data
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

schema = StructType([
    StructField("id", IntegerType()),
    StructField("name", StringType()),
    StructField("value", IntegerType())
])

df_parsed = df_stream.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")

# Transformations on streaming DataFrame
df_filtered = df_parsed.filter(col("value") > 100)

# Aggregations with watermark
from pyspark.sql.functions import window

df_windowed = df_filtered \
    .withWatermark("timestamp", "10 minutes") \
    .groupBy(
        window(col("timestamp"), "5 minutes"),
        col("name")
    ) \
    .agg(sum("value").alias("total_value"))

# Write stream
query = df_windowed \
    .writeStream \
    .outputMode("append") \
    .format("parquet") \
    .option("checkpointLocation", "/tmp/checkpoint") \
    .option("path", "/tmp/output") \
    .start()

query.awaitTermination()
```

---

## 14. Machine Learning (MLlib)

### Q28: Feature engineering and ML pipeline

**Answer:**

```python
from pyspark.ml.feature import (
    VectorAssembler, StandardScaler, StringIndexer,
    OneHotEncoder, Tokenizer, HashingTF, IDF
)
from pyspark.ml.classification import LogisticRegression
from pyspark.ml import Pipeline

# Feature engineering
# 1. String Indexer (categorical to numeric)
indexer = StringIndexer(inputCol="category", outputCol="category_index")

# 2. One-Hot Encoding
encoder = OneHotEncoder(inputCol="category_index", outputCol="category_vec")

# 3. Vector Assembler (combine features)
assembler = VectorAssembler(
    inputCols=["age", "salary", "category_vec"],
    outputCol="features"
)

# 4. Standard Scaler
scaler = StandardScaler(inputCol="features", outputCol="scaled_features")

# 5. Text processing
tokenizer = Tokenizer(inputCol="text", outputCol="words")
hashing_tf = HashingTF(inputCol="words", outputCol="raw_features")
idf = IDF(inputCol="raw_features", outputCol="features")

# Create ML Pipeline
lr = LogisticRegression(labelCol="label", featuresCol="scaled_features")

pipeline = Pipeline(stages=[
    indexer,
    encoder,
    assembler,
    scaler,
    lr
])

# Split data
train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)

# Train model
model = pipeline.fit(train_df)

# Make predictions
predictions = model.transform(test_df)

# Evaluate
from pyspark.ml.evaluation import BinaryClassificationEvaluator

evaluator = BinaryClassificationEvaluator(labelCol="label")
auc = evaluator.evaluate(predictions)
print(f"AUC: {auc}")
```

---

## 15. Real-World Scenarios

### Q29: Deduplication strategies

**Answer:**

```python
from pyspark.sql.functions import col, row_number
from pyspark.sql.window import Window

# 1. Simple distinct
df_distinct = df.distinct()

# 2. Drop duplicates on specific columns
df_dedup = df.dropDuplicates(["email"])

# 3. Keep last occurrence
window = Window.partitionBy("email").orderBy(col("timestamp").desc())
df_last = df.withColumn("row_num", row_number().over(window)) \
          .filter(col("row_num") == 1) \
          .drop("row_num")

# 4. Keep record with max value
window_max = Window.partitionBy("email").orderBy(col("amount").desc())
df_max = df.withColumn("rank", row_number().over(window_max)) \
          .filter(col("rank") == 1) \
          .drop("rank")

# 5. Keep most complete record (fewest nulls)
from pyspark.sql.functions import sum as spark_sum, when

df_completeness = df.withColumn(
    "null_count",
    sum([when(col(c).isNull(), 1).otherwise(0) for c in df.columns])
)

window_complete = Window.partitionBy("email").orderBy("null_count")
df_most_complete = df_completeness \
    .withColumn("rank", row_number().over(window_complete)) \
    .filter(col("rank") == 1) \
    .drop("null_count", "rank")
```

---

### Q30: Slowly Changing Dimensions (SCD Type 2)

**Answer:**

```python
from pyspark.sql.functions import current_date, lit, when, col

# Existing dimension table
existing = spark.read.parquet("dimension_table")

# New incoming data
new_data = spark.read.parquet("new_data")

# Identify changes
changes = new_data.alias("new").join(
    existing.filter(col("is_current") == True).alias("old"),
    "id",
    "left"
).select(
    col("new.id"),
    col("new.name"),
    col("new.address"),
    when(
        (col("old.name") != col("new.name")) | 
        (col("old.address") != col("new.address")),
        True
    ).otherwise(False).alias("has_changed"),
    col("old.start_date")
)

# Close old records
updated_old = existing.alias("old").join(
    changes.filter(col("has_changed") == True).alias("chg"),
    "id",
    "left"
).select(
    col("old.*")
).withColumn(
    "end_date",
    when(col("chg.id").isNotNull(), current_date()).otherwise(col("old.end_date"))
).withColumn(
    "is_current",
    when(col("chg.id").isNotNull(), False).otherwise(col("old.is_current"))
)

# Create new records
new_records = changes.filter(col("has_changed") == True).select(
    col("id"),
    col("name"),
    col("address"),
    current_date().alias("start_date"),
    lit(None).alias("end_date"),
    lit(True).alias("is_current")
)

# Union all records
result = updated_old.union(new_records)

# Write back
result.write.mode("overwrite").parquet("dimension_table")
```

---

## Conclusion

This comprehensive PySpark guide covers:

1. **Fundamentals:** Architecture, lazy evaluation, RDD vs DataFrame
2. **DataFrame API:** Creation, transformations, actions
3. **Advanced Features:** Window functions, UDFs, ML pipelines
4. **Performance:** Caching, partitioning, broadcast joins
5. **Real-World:** Deduplication, SCD, streaming

**Key Takeaways:**
- Use DataFrame API over RDD when possible
- Leverage Catalyst optimizer with built-in functions
- Cache strategically for reused DataFrames
- Partition data appropriately (128MB-1GB per partition)
- Broadcast small lookup tables
- Use Pandas UDF for vectorized operations
- Monitor Spark UI for optimization opportunities

**Interview Tips:**
- Explain lazy evaluation and DAG
- Discuss partitioning strategies
- Know when to use broadcast joins
- Understand narrow vs wide transformations
- Be familiar with Spark architecture

**Practice Resources:**
- Databricks Community Edition
- Apache Spark Documentation
- PySpark tutorials on GitHub
- Real datasets: Kaggle, UCI ML Repository

Good luck with your PySpark interviews!
