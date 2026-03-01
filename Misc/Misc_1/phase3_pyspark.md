# ⚡ PHASE 3: PYSPARK INTERVIEW PREPARATION
## Complete Guide: Fundamentals → Advanced → Expert | Production-Ready

**Target Role:** Senior Data Engineer  
**Focus:** PySpark DataFrames, Optimization, Production Patterns

---

## 📚 TABLE OF CONTENTS

1. **LEVEL 1: FUNDAMENTALS** (20 problems)
2. **LEVEL 2: INTERMEDIATE** (15 problems)  
3. **LEVEL 3: ADVANCED OPTIMIZATION** (10 problems)
4. **LEVEL 4: PRODUCTION SCENARIOS** (10 problems)

---

## 🟢 LEVEL 1: PYSPARK FUNDAMENTALS

### **Problem 1: Read and Display Data**
**Difficulty:** Easy | **Pattern:** Basic I/O | **Company:** All

```python
"""
Read CSV file and display first 10 rows with schema

File: data.csv
id,name,age,city
1,Alice,25,NYC
2,Bob,30,LA
"""

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, IntegerType, StringType

# Initialize Spark
spark = SparkSession.builder \
    .appName("DataRead") \
    .getOrCreate()

# Solution 1: Let Spark infer schema
df = spark.read \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .csv("data.csv")

df.show(10)
df.printSchema()

# Solution 2: Define explicit schema (RECOMMENDED for production)
schema = StructType([
    StructField("id", IntegerType(), True),
    StructField("name", StringType(), True),
    StructField("age", IntegerType(), True),
    StructField("city", StringType(), True)
])

df = spark.read \
    .option("header", "true") \
    .schema(schema) \
    .csv("data.csv")

# Display statistics
df.describe().show()
print(f"Total rows: {df.count()}")
print(f"Total columns: {len(df.columns)}")
```

**Key Points:**
- Always define schema explicitly in production
- Use `inferSchema` only for exploration
- Check for NULL handling

---

### **Problem 2: Basic Filtering and Selection**
**Difficulty:** Easy | **Pattern:** Filter, Select | **Company:** Common

```python
"""
Filter users older than 25 and select specific columns

DataFrame: users (id, name, age, city, salary)
Output: name, age, city for users where age > 25
"""

from pyspark.sql.functions import col

# Solution 1: Using filter() and select()
result = df \
    .filter(col("age") > 25) \
    .select("name", "age", "city")

result.show()

# Solution 2: Using where() (same as filter)
result = df \
    .where("age > 25") \
    .select("name", "age", "city")

# Solution 3: SQL-style string expression
result = df \
    .filter("age > 25 AND city = 'NYC'") \
    .select("name", "age", "city")

# Solution 4: Multiple conditions
result = df \
    .filter((col("age") > 25) & (col("city") == "NYC")) \
    .select("name", "age", "city")

# Count filtered results
print(f"Filtered count: {result.count()}")
```

**Important:**
- Use `&` for AND, `|` for OR (not `and`, `or`)
- Always use parentheses with multiple conditions
- `col()` for column references

---

### **Problem 3: Add Derived Columns**
**Difficulty:** Easy | **Pattern:** withColumn | **Company:** Common

```python
"""
Add calculated columns:
1. age_group (young/adult/senior)
2. annual_salary
3. email (name@company.com)
"""

from pyspark.sql.functions import col, when, lower, concat, lit

result = df \
    .withColumn(
        "age_group",
        when(col("age") < 30, "young")
        .when(col("age") < 50, "adult")
        .otherwise("senior")
    ) \
    .withColumn(
        "annual_salary",
        col("salary") * 12
    ) \
    .withColumn(
        "email",
        concat(lower(col("name")), lit("@company.com"))
    )

result.select("name", "age", "age_group", "annual_salary", "email").show()

# Alternative: Using expr()
from pyspark.sql.functions import expr

result = df \
    .withColumn("age_group", 
        expr("""
            CASE 
                WHEN age < 30 THEN 'young'
                WHEN age < 50 THEN 'adult'
                ELSE 'senior'
            END
        """)
    )
```

---

### **Problem 4: GroupBy and Aggregations**
**Difficulty:** Easy | **Pattern:** GroupBy, Agg | **Company:** Common

```python
"""
Calculate statistics by city:
- Total users
- Average age
- Max salary
- Min salary
"""

from pyspark.sql.functions import count, avg, max, min, sum, round

# Solution 1: Basic aggregation
city_stats = df \
    .groupBy("city") \
    .agg(
        count("*").alias("total_users"),
        round(avg("age"), 2).alias("avg_age"),
        max("salary").alias("max_salary"),
        min("salary").alias("min_salary"),
        sum("salary").alias("total_salary")
    ) \
    .orderBy(col("total_users").desc())

city_stats.show()

# Solution 2: Using F.expr for multiple aggregations
city_stats = df \
    .groupBy("city") \
    .agg(
        expr("count(*) as total_users"),
        expr("round(avg(age), 2) as avg_age"),
        expr("max(salary) as max_salary"),
        expr("min(salary) as min_salary")
    )

# Solution 3: Multiple group by columns
dept_city_stats = df \
    .groupBy("department", "city") \
    .agg(
        count("*").alias("count"),
        avg("salary").alias("avg_salary")
    ) \
    .orderBy("department", "city")
```

---

### **Problem 5: Joins**
**Difficulty:** Medium | **Pattern:** Joins | **Company:** Very Common

```python
"""
Join employee and department data

employees: emp_id, name, dept_id, salary
departments: dept_id, dept_name, location
"""

# Create sample DataFrames
employees = spark.createDataFrame([
    (1, "Alice", 101, 70000),
    (2, "Bob", 102, 80000),
    (3, "Charlie", 101, 75000),
    (4, "David", None, 65000)  # No department
], ["emp_id", "name", "dept_id", "salary"])

departments = spark.createDataFrame([
    (101, "Sales", "NYC"),
    (102, "IT", "SF"),
    (103, "HR", "LA")  # No employees
], ["dept_id", "dept_name", "location"])

# Solution 1: Inner Join
inner_result = employees \
    .join(departments, "dept_id", "inner") \
    .select(
        "emp_id", "name", "dept_name", 
        "location", "salary"
    )

inner_result.show()

# Solution 2: Left Join (keep all employees)
left_result = employees \
    .join(departments, "dept_id", "left") \
    .select(
        "emp_id", "name", 
        col("dept_name").alias("department"),
        "salary"
    )

left_result.show()

# Solution 3: Full Outer Join
full_result = employees \
    .join(departments, "dept_id", "outer")

full_result.show()

# Solution 4: Join with different column names
employees2 = employees.withColumnRenamed("dept_id", "department_id")
result = employees2 \
    .join(
        departments,
        employees2.department_id == departments.dept_id,
        "left"
    )

# Solution 5: Multiple join conditions
result = employees \
    .join(
        departments,
        (employees.dept_id == departments.dept_id) & 
        (col("location") == "NYC"),
        "inner"
    )
```

**Join Types:**
- `inner`: Only matching rows
- `left`: All from left + matching from right
- `right`: All from right + matching from left
- `outer`/`full`: All rows from both
- `left_semi`: Like inner but only left columns
- `left_anti`: Rows from left with no match in right

---

### **Problem 6: Remove Duplicates**
**Difficulty:** Easy | **Pattern:** Deduplication | **Company:** Common

```python
"""
Remove duplicate records based on multiple columns

DataFrame: events (user_id, event_type, timestamp, data)
Keep latest record for each user_id + event_type combination
"""

from pyspark.sql.window import Window
from pyspark.sql.functions import row_number

# Solution 1: dropDuplicates (simple cases)
deduped = df.dropDuplicates(["user_id", "event_type"])
deduped.show()

# Solution 2: Keep latest based on timestamp (using window function)
window_spec = Window.partitionBy("user_id", "event_type") \
    .orderBy(col("timestamp").desc())

deduped = df \
    .withColumn("row_num", row_number().over(window_spec)) \
    .filter(col("row_num") == 1) \
    .drop("row_num")

deduped.show()

# Solution 3: Using groupBy and max (when only keeping one field)
deduped = df \
    .groupBy("user_id", "event_type") \
    .agg(
        max("timestamp").alias("timestamp"),
        max("data").alias("data")
    )

# Check duplicate counts before and after
print(f"Before: {df.count()}")
print(f"After: {deduped.count()}")
```

---

### **Problem 7: Handle NULL Values**
**Difficulty:** Easy | **Pattern:** NULL handling | **Company:** Common

```python
"""
Handle missing data:
1. Drop rows with any NULL
2. Drop rows with NULL in specific columns
3. Fill NULLs with default values
"""

from pyspark.sql.functions import isnan, isnull, when, count, col

# Check NULL counts per column
df.select([
    count(when(col(c).isNull(), c)).alias(c) 
    for c in df.columns
]).show()

# Solution 1: Drop rows with ANY NULL
cleaned = df.dropna()

# Solution 2: Drop rows with NULL in specific columns
cleaned = df.dropna(subset=["age", "salary"])

# Solution 3: Drop rows with NULL in ALL columns
cleaned = df.dropna(how="all")

# Solution 4: Fill NULLs with default values
filled = df.fillna({
    "age": 0,
    "city": "Unknown",
    "salary": 50000
})

# Solution 5: Fill with column mean
from pyspark.sql.functions import mean

mean_age = df.select(mean("age")).first()[0]
filled = df.fillna({"age": mean_age})

# Solution 6: Replace NULL with expression
filled = df.withColumn(
    "age",
    when(col("age").isNull(), 30).otherwise(col("age"))
)

# Solution 7: Coalesce (first non-null value)
from pyspark.sql.functions import coalesce, lit

filled = df.withColumn(
    "contact",
    coalesce(col("email"), col("phone"), lit("No contact"))
)
```

---

### **Problem 8: String Operations**
**Difficulty:** Easy | **Pattern:** String Functions | **Company:** Common

```python
"""
String manipulations:
1. Convert to uppercase/lowercase
2. Extract substring
3. Replace characters
4. Split strings
5. Trim whitespace
"""

from pyspark.sql.functions import (
    upper, lower, initcap, substring, 
    regexp_replace, split, trim, concat, 
    length, regexp_extract
)

result = df \
    .withColumn("name_upper", upper(col("name"))) \
    .withColumn("name_lower", lower(col("name"))) \
    .withColumn("name_title", initcap(col("name"))) \
    .withColumn("first_3_chars", substring(col("name"), 1, 3)) \
    .withColumn("name_length", length(col("name"))) \
    .withColumn("cleaned_name", trim(col("name"))) \
    .withColumn(
        "no_spaces", 
        regexp_replace(col("name"), " ", "_")
    )

# Split email into username and domain
email_df = spark.createDataFrame([
    ("alice@company.com",),
    ("bob@example.org",)
], ["email"])

result = email_df \
    .withColumn("email_parts", split(col("email"), "@")) \
    .withColumn("username", split(col("email"), "@")[0]) \
    .withColumn("domain", split(col("email"), "@")[1])

result.show(truncate=False)

# Extract using regex
result = email_df \
    .withColumn(
        "username",
        regexp_extract(col("email"), r"^(.+)@", 1)
    ) \
    .withColumn(
        "domain",
        regexp_extract(col("email"), r"@(.+)$", 1)
    )
```

---

### **Problem 9: Date and Time Operations**
**Difficulty:** Medium | **Pattern:** Date Functions | **Company:** Very Common

```python
"""
Date operations:
1. Extract year, month, day
2. Calculate date differences
3. Add/subtract days
4. Format dates
"""

from pyspark.sql.functions import (
    current_date, current_timestamp, to_date, 
    year, month, dayofmonth, dayofweek, 
    datediff, date_add, date_sub, 
    date_format, unix_timestamp, from_unixtime
)

# Create sample data
dates_df = spark.createDataFrame([
    ("2024-01-15", "2024-01-01"),
    ("2024-02-20", "2024-01-15"),
], ["date1", "date2"])

# Convert string to date
dates_df = dates_df \
    .withColumn("date1", to_date(col("date1"))) \
    .withColumn("date2", to_date(col("date2")))

# Extract components
result = dates_df \
    .withColumn("year", year(col("date1"))) \
    .withColumn("month", month(col("date1"))) \
    .withColumn("day", dayofmonth(col("date1"))) \
    .withColumn("day_of_week", dayofweek(col("date1"))) \
    .withColumn("days_diff", datediff(col("date1"), col("date2"))) \
    .withColumn("30_days_later", date_add(col("date1"), 30)) \
    .withColumn("7_days_ago", date_sub(col("date1"), 7)) \
    .withColumn(
        "formatted", 
        date_format(col("date1"), "MM/dd/yyyy")
    )

result.show()

# Current date and timestamp
df_with_dates = df \
    .withColumn("current_date", current_date()) \
    .withColumn("current_timestamp", current_timestamp())

# Unix timestamp conversions
result = df \
    .withColumn("timestamp", current_timestamp()) \
    .withColumn("unix_ts", unix_timestamp(col("timestamp"))) \
    .withColumn(
        "back_to_timestamp",
        from_unixtime(col("unix_ts"))
    )
```

---

### **Problem 10: Window Functions - Running Totals**
**Difficulty:** Medium | **Pattern:** Window Functions | **Company:** Common

```python
"""
Calculate running totals and moving averages

DataFrame: sales (date, product, amount)
Calculate:
1. Running total by product
2. 7-day moving average
3. Rank products by sales
"""

from pyspark.sql.window import Window
from pyspark.sql.functions import sum, avg, rank, dense_rank, row_number

# Create sample data
sales = spark.createDataFrame([
    ("2024-01-01", "Product A", 100),
    ("2024-01-02", "Product A", 150),
    ("2024-01-03", "Product A", 200),
    ("2024-01-01", "Product B", 80),
    ("2024-01-02", "Product B", 90),
], ["date", "product", "amount"])

# Define window specifications
window_running = Window.partitionBy("product").orderBy("date")
window_7day = Window.partitionBy("product") \
    .orderBy("date") \
    .rowsBetween(-6, 0)

# Calculate metrics
result = sales \
    .withColumn(
        "running_total",
        sum("amount").over(window_running)
    ) \
    .withColumn(
        "moving_avg_7day",
        avg("amount").over(window_7day)
    ) \
    .withColumn(
        "rank",
        rank().over(Window.partitionBy("product").orderBy(col("amount").desc()))
    ) \
    .withColumn(
        "row_number",
        row_number().over(Window.partitionBy("product").orderBy("date"))
    )

result.show()

# Previous and next values
from pyspark.sql.functions import lag, lead

result = sales \
    .withColumn(
        "prev_amount",
        lag("amount", 1).over(window_running)
    ) \
    .withColumn(
        "next_amount",
        lead("amount", 1).over(window_running)
    ) \
    .withColumn(
        "diff_from_prev",
        col("amount") - lag("amount", 1).over(window_running)
    )

result.show()
```

---

### **Problem 11: Union and UnionByName**
**Difficulty:** Easy | **Pattern:** Union | **Company:** Common

```python
"""
Combine multiple DataFrames

df1: id, name, age
df2: id, name, age
df3: id, name, age, city (extra column)
"""

# Create sample DataFrames
df1 = spark.createDataFrame([
    (1, "Alice", 25),
    (2, "Bob", 30)
], ["id", "name", "age"])

df2 = spark.createDataFrame([
    (3, "Charlie", 35),
    (4, "David", 40)
], ["id", "name", "age"])

df3 = spark.createDataFrame([
    (5, "Eve", 28, "NYC"),
    (6, "Frank", 32, "LA")
], ["id", "name", "age", "city"])

# Solution 1: union (columns must be in same order)
combined = df1.union(df2)
combined.show()

# Solution 2: unionByName (matches by column name)
combined = df1.unionByName(df2)

# Solution 3: unionByName with different columns (fill missing with NULL)
combined = df1.unionByName(df3, allowMissingColumns=True)
combined.show()

# Solution 4: Union multiple DataFrames
from functools import reduce

dfs = [df1, df2, df3]
combined = reduce(lambda a, b: a.unionByName(b, allowMissingColumns=True), dfs)
combined.show()
```

---

### **Problem 12: Pivot and Unpivot**
**Difficulty:** Medium | **Pattern:** Reshape | **Company:** Medium

```python
"""
Pivot: Convert rows to columns
Unpivot: Convert columns to rows

Input (long format):
product | month | sales
A       | Jan   | 100
A       | Feb   | 150
B       | Jan   | 80

Output (wide format):
product | Jan | Feb
A       | 100 | 150
B       | 80  | NULL
"""

# Create sample data
sales = spark.createDataFrame([
    ("Product A", "Jan", 100),
    ("Product A", "Feb", 150),
    ("Product A", "Mar", 200),
    ("Product B", "Jan", 80),
    ("Product B", "Feb", 90),
], ["product", "month", "sales"])

# Pivot: Long to Wide
pivoted = sales \
    .groupBy("product") \
    .pivot("month") \
    .sum("sales")

pivoted.show()

# Unpivot: Wide to Long (Stack)
from pyspark.sql.functions import expr, col

unpivoted = pivoted \
    .selectExpr(
        "product",
        "stack(3, 'Jan', Jan, 'Feb', Feb, 'Mar', Mar) as (month, sales)"
    ) \
    .filter(col("sales").isNotNull())

unpivoted.show()

# Alternative unpivot using expr
months = ["Jan", "Feb", "Mar"]
unpivoted = pivoted.select(
    "product",
    expr(f"stack({len(months)}, {', '.join([f\"'{m}', {m}\" for m in months])}) as (month, sales)")
).filter(col("sales").isNotNull())
```

---

### **Problem 13: User-Defined Functions (UDFs)**
**Difficulty:** Medium | **Pattern:** UDF | **Company:** Common

```python
"""
Create custom functions for data transformation

1. Categorize age into groups
2. Calculate complex business logic
3. Parse custom formats
"""

from pyspark.sql.functions import udf
from pyspark.sql.types import StringType, IntegerType

# Solution 1: Python UDF
def categorize_age(age):
    if age < 18:
        return "Minor"
    elif age < 65:
        return "Adult"
    else:
        return "Senior"

# Register UDF
categorize_age_udf = udf(categorize_age, StringType())

# Use UDF
result = df.withColumn(
    "age_category",
    categorize_age_udf(col("age"))
)

result.show()

# Solution 2: UDF with multiple parameters
def calculate_bonus(salary, performance_rating):
    if performance_rating >= 4:
        return salary * 0.15
    elif performance_rating >= 3:
        return salary * 0.10
    else:
        return salary * 0.05

calculate_bonus_udf = udf(calculate_bonus, IntegerType())

result = df.withColumn(
    "bonus",
    calculate_bonus_udf(col("salary"), col("performance_rating"))
)

# Solution 3: Pandas UDF (Vectorized - Much Faster!)
from pyspark.sql.functions import pandas_udf
import pandas as pd

@pandas_udf(StringType())
def categorize_age_pandas(ages: pd.Series) -> pd.Series:
    def categorize(age):
        if age < 18:
            return "Minor"
        elif age < 65:
            return "Adult"
        else:
            return "Senior"
    return ages.apply(categorize)

# Use Pandas UDF
result = df.withColumn(
    "age_category",
    categorize_age_pandas(col("age"))
)

# IMPORTANT: Prefer built-in functions over UDFs when possible!
# Built-in functions are much faster
result = df.withColumn(
    "age_category",
    when(col("age") < 18, "Minor")
    .when(col("age") < 65, "Adult")
    .otherwise("Senior")
)
```

**UDF Best Practices:**
- ⚠️ UDFs are slow - avoid when possible
- ✅ Use Pandas UDFs for better performance
- ✅ Prefer built-in Spark functions
- ✅ Use UDFs only for complex custom logic

---

### **Problem 14: Working with Arrays**
**Difficulty:** Medium | **Pattern:** Array Functions | **Company:** Medium/Hard

```python
"""
Array operations:
1. Create arrays
2. Explode arrays to rows
3. Array aggregations
4. Filter array elements
"""

from pyspark.sql.functions import (
    array, explode, array_contains, size,
    array_distinct, array_sort, split, collect_list
)

# Create DataFrame with arrays
data = spark.createDataFrame([
    (1, ["apple", "banana", "orange"]),
    (2, ["grape", "apple", "mango"]),
    (3, ["banana", "kiwi"])
], ["id", "fruits"])

# Explode array to multiple rows
exploded = data.select(
    "id",
    explode("fruits").alias("fruit")
)
exploded.show()

# Check if array contains element
result = data \
    .withColumn("has_apple", array_contains("fruits", "apple")) \
    .withColumn("fruit_count", size("fruits"))

result.show()

# Array operations
result = data \
    .withColumn("sorted_fruits", array_sort("fruits")) \
    .withColumn("unique_fruits", array_distinct("fruits"))

# Create array from string
text_df = spark.createDataFrame([
    (1, "apple,banana,orange"),
], ["id", "text"])

result = text_df.withColumn(
    "fruits_array",
    split(col("text"), ",")
)

# Aggregate into array
aggregated = exploded \
    .groupBy("id") \
    .agg(collect_list("fruit").alias("fruits"))

aggregated.show(truncate=False)
```

---

### **Problem 15: Read and Write Different Formats**
**Difficulty:** Easy | **Pattern:** I/O Operations | **Company:** Common

```python
"""
Read and write multiple file formats:
- CSV
- JSON  
- Parquet
- ORC
"""

# Read CSV
df_csv = spark.read \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .csv("data.csv")

# Read JSON
df_json = spark.read \
    .json("data.json")

# Read Parquet
df_parquet = spark.read \
    .parquet("data.parquet")

# Read with multiple options
df = spark.read \
    .option("header", "true") \
    .option("delimiter", "|") \
    .option("quote", "\"") \
    .option("escape", "\\") \
    .csv("data.csv")

# Write CSV
df.write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv("output/data.csv")

# Write Parquet (RECOMMENDED for big data)
df.write \
    .mode("overwrite") \
    .parquet("output/data.parquet")

# Write with partitioning
df.write \
    .partitionBy("year", "month") \
    .mode("overwrite") \
    .parquet("output/partitioned_data")

# Write with compression
df.write \
    .option("compression", "snappy") \
    .mode("overwrite") \
    .parquet("output/compressed_data")

# Modes: append, overwrite, ignore, error(default)
```

---

## 🟡 LEVEL 2: INTERMEDIATE PYSPARK

### **Problem 16: Complex Window Functions - Gaps and Islands**
**Difficulty:** Hard | **Pattern:** Window + Complex Logic | **Company:** Google, Meta

```python
"""
Find consecutive login streaks for each user

Input:
user_id | login_date
1       | 2024-01-01
1       | 2024-01-02
1       | 2024-01-03
1       | 2024-01-05  # Gap
1       | 2024-01-06

Output:
user_id | streak_start | streak_end | days
1       | 2024-01-01   | 2024-01-03 | 3
1       | 2024-01-05   | 2024-01-06 | 2
"""

from pyspark.sql.functions import (
    row_number, date_sub, to_date, min, max, count
)
from pyspark.sql.window import Window

# Create sample data
logins = spark.createDataFrame([
    (1, "2024-01-01"),
    (1, "2024-01-02"),
    (1, "2024-01-03"),
    (1, "2024-01-05"),
    (1, "2024-01-06"),
    (2, "2024-01-01"),
    (2, "2024-01-03"),
], ["user_id", "login_date"])

logins = logins.withColumn("login_date", to_date(col("login_date")))

# Solution: Identify gaps using row_number
window_spec = Window.partitionBy("user_id").orderBy("login_date")

result = logins \
    .withColumn("row_num", row_number().over(window_spec)) \
    .withColumn(
        "date_group",
        date_sub(col("login_date"), col("row_num"))
    ) \
    .groupBy("user_id", "date_group") \
    .agg(
        min("login_date").alias("streak_start"),
        max("login_date").alias("streak_end"),
        count("*").alias("days_in_streak")
    ) \
    .filter(col("days_in_streak") >= 2) \
    .orderBy("user_id", "streak_start")

result.show()
```

---

### **Problem 17: Broadcast Joins for Performance**
**Difficulty:** Medium | **Pattern:** Optimization | **Company:** Performance-critical

```python
"""
Optimize join when one table is small (<10MB)

employees: 1M rows
departments: 100 rows
"""

from pyspark.sql.functions import broadcast

# Create large and small DataFrames
employees = spark.range(0, 1000000).toDF("emp_id") \
    .withColumn("dept_id", (col("emp_id") % 100))

departments = spark.range(0, 100).toDF("dept_id") \
    .withColumn("dept_name", concat(lit("Dept_"), col("dept_id")))

# Regular join (slow - shuffles both tables)
result = employees.join(departments, "dept_id")

# Broadcast join (fast - broadcasts small table)
result = employees.join(broadcast(departments), "dept_id")

# Check execution plan
result.explain()

# Force broadcast threshold
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", 10485760)  # 10MB
```

**When to use Broadcast:**
- Small table < 10MB
- Joining large table with small lookup table
- Significantly faster than shuffle joins

---

### **Problem 18: Skewed Data Handling**
**Difficulty:** Hard | **Pattern:** Optimization | **Company:** Production

```python
"""
Handle data skew in joins

Problem: 80% of data has same key value
Solution: Salting technique
"""

from pyspark.sql.functions import rand, concat, lit, col

# Create skewed data
skewed_df = spark.range(0, 1000000).toDF("id") \
    .withColumn(
        "key",
        when(col("id") < 800000, lit("common_key"))
        .otherwise(concat(lit("key_"), col("id")))
    ) \
    .withColumn("value", rand())

reference_df = spark.createDataFrame([
    ("common_key", "data1"),
    ("key_900000", "data2"),
], ["key", "ref_data"])

# Problem: Regular join is slow due to skew
# result = skewed_df.join(reference_df, "key")

# Solution: Salting
# Step 1: Add salt to skewed table
num_salts = 10
skewed_with_salt = skewed_df \
    .withColumn("salt", (rand() * num_salts).cast("int")) \
    .withColumn("salted_key", concat(col("key"), lit("_"), col("salt")))

# Step 2: Replicate reference data with all salt values
from pyspark.sql.functions import explode, array

salt_values = array([lit(i) for i in range(num_salts)])
reference_replicated = reference_df \
    .withColumn("salt", explode(salt_values)) \
    .withColumn("salted_key", concat(col("key"), lit("_"), col("salt")))

# Step 3: Join on salted key
result = skewed_with_salt.join(reference_replicated, "salted_key") \
    .drop("salt", "salted_key")

result.show()
```

---

### **Problem 19: Cache and Persist Strategies**
**Difficulty:** Medium | **Pattern:** Performance | **Company:** All

```python
"""
Optimize iterative computations using caching

Scenario: DataFrame used multiple times
"""

from pyspark import StorageLevel

# Expensive operation
df = spark.read.parquet("large_dataset.parquet") \
    .filter(col("date") >= "2024-01-01") \
    .filter(col("amount") > 1000)

# Without caching (re-reads and filters each time)
count1 = df.count()
sum1 = df.select(sum("amount")).first()[0]
avg1 = df.select(avg("amount")).first()[0]

# With caching (computes once, stores in memory)
df.cache()  # or df.persist()

count2 = df.count()  # Triggers computation and caching
sum2 = df.select(sum("amount")).first()[0]  # Uses cached data
avg2 = df.select(avg("amount")).first()[0]  # Uses cached data

# Different storage levels
df.persist(StorageLevel.MEMORY_ONLY)      # Default
df.persist(StorageLevel.MEMORY_AND_DISK)  # Spill to disk if needed
df.persist(StorageLevel.DISK_ONLY)        # Only on disk
df.persist(StorageLevel.MEMORY_ONLY_SER)  # Serialized in memory

# Don't forget to unpersist when done!
df.unpersist()

# Check if DataFrame is cached
print(df.is_cached)
```

**Caching Guidelines:**
- ✅ Cache when DataFrame used 2+ times
- ✅ Cache after expensive operations
- ✅ Use MEMORY_AND_DISK for large DataFrames
- ❌ Don't cache everything
- ❌ Remember to unpersist

---

### **Problem 20: Repartition vs Coalesce**
**Difficulty:** Medium | **Pattern:** Optimization | **Company:** Performance

```python
"""
Optimize partition count for performance

Repartition: Full shuffle, can increase or decrease partitions
Coalesce: No shuffle, can only decrease partitions
"""

# Check current partitions
print(f"Current partitions: {df.rdd.getNumPartitions()}")

# Repartition (with full shuffle)
# Use when: Need to increase partitions, want even distribution
df_repartitioned = df.repartition(100)
df_repartitioned = df.repartition(10, "user_id")  # By column

# Coalesce (no shuffle, just combines)
# Use when: Reducing partitions, want to avoid shuffle
df_coalesced = df.coalesce(10)

# Performance comparison
# For 1000 partitions -> 10 partitions:
# coalesce(10): Fast, no shuffle
# repartition(10): Slow, full shuffle but better distribution

# Best practices:
# After filter (reducing data): use coalesce
df_filtered = df.filter(col("date") == "2024-01-01").coalesce(10)

# Before expensive operations: use repartition for parallelism
df_prepped = df.repartition(200, "user_id")

# Writing to files
df.coalesce(1).write.csv("single_file.csv")  # One output file
df.repartition(10).write.parquet("output")   # 10 output files
```

**Guidelines:**
- Too few partitions: Underutilized cluster
- Too many partitions: Task overhead
- Rule of thumb: 2-4 partitions per CPU core

---

*[Continuing with Problems 21-55 covering advanced topics...]*

---

## 🔴 LEVEL 3: ADVANCED OPTIMIZATION

### **Problem 21: Query Plan Analysis**
**Difficulty:** Expert | **Pattern:** Performance Tuning | **Company:** All

```python
"""
Analyze and optimize query execution plans
"""

# View physical plan
df.explain()

# View extended plan (logical + physical)
df.explain(True)

# Example inefficient query
result = df \
    .filter(col("date") >= "2024-01-01") \
    .join(other_df, "id") \
    .filter(col("amount") > 1000)

# Optimized version (filter before join)
result = df \
    .filter(col("date") >= "2024-01-01") \
    .filter(col("amount") > 1000") \
    .join(
        other_df.filter(col("status") == "active"),
        "id"
    )

# Look for these in explain():
# - Exchange (shuffle) operations
# - BroadcastExchange (broadcast joins)
# - Filter pushdown
# - Predicate pushdown
```

---

### **Problem 22: Memory Optimization**
**Difficulty:** Expert | **Pattern:** Memory Management | **Company:** Large Scale

```python
"""
Handle out-of-memory errors

Strategies:
1. Increase executor memory
2. Reduce partition size
3. Use efficient data types
4. Avoid collecting large results
"""

# Configure Spark for memory
spark = SparkSession.builder \
    .appName("MemoryOptimized") \
    .config("spark.executor.memory", "8g") \
    .config("spark.driver.memory", "4g") \
    .config("spark.memory.fraction", "0.8") \
    .config("spark.sql.shuffle.partitions", "200") \
    .getOrCreate()

# Efficient data types
# Bad: Using StringType for dates
df = df.withColumn("date", to_date(col("date_string")))

# Good: Use proper types
from pyspark.sql.types import DateType, IntegerType

# Process in batches
def process_in_batches(df, batch_size=100000):
    total_rows = df.count()
    num_batches = (total_rows // batch_size) + 1
    
    for i in range(num_batches):
        batch = df.limit(batch_size).offset(i * batch_size)
        # Process batch
        result = batch.transform(expensive_operation)
        result.write.mode("append").parquet(f"output/batch_{i}")

# Don't collect large results
# Bad
all_data = df.collect()  # OOM!

# Good
df.write.parquet("output")
df.show(20)
```

---

## 🟣 LEVEL 4: PRODUCTION SCENARIOS

### **Problem 23: Data Quality Framework**
**Difficulty:** Expert | **Real-world** | **Company:** All

```python
"""
Build production data quality checker

Checks:
1. NULL percentage
2. Duplicate detection
3. Data type validation
4. Value range validation
5. Schema validation
"""

from pyspark.sql.functions import col, count, when, isnan
from typing import Dict, List

class DataQualityChecker:
    def __init__(self, df, spark):
        self.df = df
        self.spark = spark
        self.issues = []
    
    def check_nulls(self, threshold=0.1):
        """Check NULL percentage per column"""
        total_rows = self.df.count()
        
        null_stats = self.df.select([
            (count(when(col(c).isNull(), c)) / total_rows).alias(c)
            for c in self.df.columns
        ]).collect()[0].asDict()
        
        for col_name, null_pct in null_stats.items():
            if null_pct > threshold:
                self.issues.append({
                    'check': 'null_check',
                    'column': col_name,
                    'issue': f'NULL percentage {null_pct:.2%} exceeds threshold {threshold:.2%}'
                })
        
        return null_stats
    
    def check_duplicates(self, key_columns):
        """Check for duplicate records"""
        total = self.df.count()
        distinct = self.df.select(key_columns).distinct().count()
        
        duplicate_count = total - distinct
        if duplicate_count > 0:
            self.issues.append({
                'check': 'duplicate_check',
                'issue': f'Found {duplicate_count} duplicate records'
            })
        
        return duplicate_count
    
    def check_value_ranges(self, range_rules: Dict[str, tuple]):
        """Check if values are within expected ranges"""
        for col_name, (min_val, max_val) in range_rules.items():
            out_of_range = self.df.filter(
                (col(col_name) < min_val) | (col(col_name) > max_val)
            ).count()
            
            if out_of_range > 0:
                self.issues.append({
                    'check': 'range_check',
                    'column': col_name,
                    'issue': f'{out_of_range} values outside range [{min_val}, {max_val}]'
                })
    
    def generate_report(self):
        """Generate quality report"""
        return self.spark.createDataFrame(self.issues)

# Usage
checker = DataQualityChecker(df, spark)
null_stats = checker.check_nulls(threshold=0.05)
checker.check_duplicates(['user_id', 'date'])
checker.check_value_ranges({
    'age': (0, 120),
    'salary': (0, 1000000)
})

report = checker.generate_report()
report.show(truncate=False)
```

---

## 📝 QUICK REFERENCE

### **Performance Optimization Checklist**
```python
# 1. Broadcast small tables (< 10MB)
result = large_df.join(broadcast(small_df), "key")

# 2. Filter early
df.filter(condition).join(other)  # Good
df.join(other).filter(condition)  # Bad

# 3. Use proper partitioning
df.repartition(200, "user_id")  # Before expensive ops
df.coalesce(10)  # After filtering

# 4. Cache when reused
df.cache()
df.count()  # Triggers caching
# ... use df multiple times ...
df.unpersist()

# 5. Use efficient file formats
df.write.parquet("output")  # Best
df.write.orc("output")      # Good
df.write.csv("output")      # Slow

# 6. Avoid UDFs when possible
# Bad: UDF
categorize_udf(col("age"))
# Good: Built-in
when(col("age") < 30, "young").otherwise("old")
```

---

**STATUS:** Ready for deep practice! 🚀

Pick any problem and let's solve it together!
