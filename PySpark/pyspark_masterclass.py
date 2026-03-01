# PYSPARK TRANSFORMATIONS MASTERCLASS
# Complete Interview Preparation Guide
# Author: Viraaj Sivaraju

"""
This guide covers ALL PySpark transformations commonly asked in interviews.
Each section has:
1. Concept explanation
2. Working code examples
3. Common interview questions
4. Performance tips
"""

# ============================================================================
# SECTION 1: SETUP AND BASICS
# ============================================================================

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.window import Window
from pyspark.sql.types import *

# Initialize Spark Session
spark = SparkSession.builder \
    .appName("PySpark_Transformations_Master") \
    .config("spark.sql.shuffle.partitions", "4") \
    .getOrCreate()

# ============================================================================
# SECTION 2: SAMPLE DATA SETUP (Common Interview Datasets)
# ============================================================================

# Dataset 1: Employee Data (Most Common in Interviews)
employees_data = [
    (1, "John", "Sales", 50000, "2020-01-15", "USA"),
    (2, "Sarah", "Engineering", 75000, "2019-06-20", "USA"),
    (3, "Mike", "Sales", 55000, "2021-03-10", "UK"),
    (4, "Emma", "Engineering", 80000, "2018-11-05", "UK"),
    (5, "Alex", "HR", 45000, "2022-02-01", "India"),
    (6, "Lisa", "Engineering", 72000, "2020-08-15", "USA"),
    (7, "David", "Sales", 52000, "2021-07-22", "India"),
    (8, "Nina", "HR", 48000, "2019-12-10", "UK"),
    (9, "Chris", "Engineering", 85000, "2017-05-30", "USA"),
    (10, "Anna", "Sales", 58000, "2020-10-18", "India")
]

employees_schema = ["emp_id", "name", "department", "salary", "join_date", "country"]
df_employees = spark.createDataFrame(employees_data, employees_schema)

# Dataset 2: Sales Transactions
sales_data = [
    (101, 1, "2024-01-15", 1200, "Electronics"),
    (102, 2, "2024-01-16", 800, "Clothing"),
    (103, 1, "2024-01-17", 1500, "Electronics"),
    (104, 3, "2024-01-18", 600, "Books"),
    (105, 2, "2024-01-19", 900, "Clothing"),
    (106, 4, "2024-01-20", 2000, "Electronics"),
    (109, 1, "2024-01-21", 1100, "Electronics"),
    (110, 5, "2024-01-22", 450, "Books"),
]

sales_schema = ["order_id", "emp_id", "order_date", "amount", "category"]
df_sales = spark.createDataFrame(sales_data, sales_schema)

# Dataset 3: Product Data
products_data = [
    ("P001", "Laptop", "Electronics", 1200, 50),
    ("P002", "Shirt", "Clothing", 40, 200),
    ("P003", "Phone", "Electronics", 800, 100),
    ("P004", "Book", "Books", 25, 300),
    ("P005", "Pants", "Clothing", 60, 150),
]

products_schema = ["product_id", "product_name", "category", "price", "stock"]
df_products = spark.createDataFrame(products_data, products_schema)

# ============================================================================
# SECTION 3: BASIC TRANSFORMATIONS (Must Know)
# ============================================================================

print("="*80)
print("SECTION 3: BASIC TRANSFORMATIONS")
print("="*80)

# 3.1 SELECT - Choose specific columns
print("\n3.1 SELECT specific columns:")
df_employees.select("name", "department", "salary").show()

# Select with expressions
df_employees.select(
    col("name"),
    col("salary"),
    (col("salary") * 1.1).alias("salary_with_bonus")
).show()

# 3.2 FILTER / WHERE - Filter rows based on conditions
print("\n3.2 FILTER rows:")
# Single condition
df_employees.filter(col("salary") > 60000).show()

# Multiple conditions
df_employees.filter(
    (col("salary") > 60000) & 
    (col("department") == "Engineering")
).show()

# Using SQL-like WHERE
df_employees.where("department = 'Sales' AND country = 'USA'").show()

# 3.3 WITHCOLUMN - Add or modify columns
print("\n3.3 WITHCOLUMN - Add/modify columns:")
df_employees.withColumn("tax", col("salary") * 0.3) \
    .withColumn("net_salary", col("salary") - col("tax")) \
    .show()

# 3.4 WITHCOLUMNRENAMED - Rename columns
print("\n3.4 WITHCOLUMNRENAMED:")
df_employees.withColumnRenamed("name", "employee_name") \
    .withColumnRenamed("salary", "annual_salary") \
    .show(5)

# 3.5 DROP - Remove columns
print("\n3.5 DROP columns:")
df_employees.drop("country").show(5)

# 3.6 DISTINCT - Remove duplicates
print("\n3.6 DISTINCT values:")
df_employees.select("department").distinct().show()
df_employees.select("country").distinct().show()

# 3.7 ORDERBY / SORT - Sort data
print("\n3.7 ORDERBY / SORT:")
# Ascending
df_employees.orderBy("salary").show(5)

# Descending
df_employees.orderBy(col("salary").desc()).show(5)

# Multiple columns
df_employees.orderBy(col("department"), col("salary").desc()).show()

# 3.8 LIMIT - Limit number of rows
print("\n3.8 LIMIT rows:")
df_employees.orderBy(col("salary").desc()).limit(3).show()

# ============================================================================
# SECTION 4: AGGREGATIONS (Very Important for Interviews)
# ============================================================================

print("\n" + "="*80)
print("SECTION 4: AGGREGATIONS")
print("="*80)

# 4.1 Basic Aggregations
print("\n4.1 Basic Aggregations:")
df_employees.agg(
    count("*").alias("total_employees"),
    sum("salary").alias("total_salary"),
    avg("salary").alias("avg_salary"),
    min("salary").alias("min_salary"),
    max("salary").alias("max_salary")
).show()

# 4.2 GROUPBY - Most common interview question!
print("\n4.2 GROUPBY:")

# Group by single column
df_employees.groupBy("department") \
    .agg(
        count("*").alias("emp_count"),
        avg("salary").alias("avg_salary"),
        max("salary").alias("max_salary")
    ) \
    .show()

# Group by multiple columns
df_employees.groupBy("department", "country") \
    .agg(
        count("*").alias("emp_count"),
        sum("salary").alias("total_salary")
    ) \
    .orderBy("department", "country") \
    .show()

# 4.3 COLLECT_LIST and COLLECT_SET
print("\n4.3 COLLECT_LIST and COLLECT_SET:")
df_employees.groupBy("department") \
    .agg(
        collect_list("name").alias("employees_list"),
        collect_set("country").alias("unique_countries")
    ) \
    .show(truncate=False)

# ============================================================================
# SECTION 5: JOINS (Critical for Interviews!)
# ============================================================================

print("\n" + "="*80)
print("SECTION 5: JOINS")
print("="*80)

# 5.1 INNER JOIN
print("\n5.1 INNER JOIN:")
df_emp_sales = df_employees.join(
    df_sales,
    df_employees.emp_id == df_sales.emp_id,
    "inner",
).select(
    df_employees["*"],
    df_sales["order_id"],
    df_sales["order_date"],
    df_sales["amount"]
)
df_emp_sales.show()

# 5.2 LEFT JOIN (LEFT OUTER JOIN)
print("\n5.2 LEFT JOIN:")
df_employees.join(
    df_sales,
    df_employees.emp_id == df_sales.emp_id,
    "left"
).show()

# 5.3 RIGHT JOIN
print("\n5.3 RIGHT JOIN:")
df_employees.join(
    df_sales,
    df_employees.emp_id == df_sales.emp_id,
    "right"
).show()

# 5.4 FULL OUTER JOIN
print("\n5.4 FULL OUTER JOIN:")
df_employees.join(
    df_sales,
    df_employees.emp_id == df_sales.emp_id,
    "outer"
).show()

# 5.5 CROSS JOIN (Cartesian Product)
print("\n5.5 CROSS JOIN:")
df_small1 = spark.createDataFrame([(1, "A"), (2, "B")], ["id", "val"])
df_small2 = spark.createDataFrame([(10, "X"), (20, "Y")], ["num", "char"])
df_small1.crossJoin(df_small2).show()

# 5.6 ANTI JOIN (rows in left but not in right)
print("\n5.6 LEFT ANTI JOIN:")
df_employees.join(
    df_sales,
    df_employees.emp_id == df_sales.emp_id,
    "left_anti"
).show()

# 5.7 SEMI JOIN (rows in left that have match in right)
print("\n5.7 LEFT SEMI JOIN:")
df_employees.join(
    df_sales,
    df_employees.emp_id == df_sales.emp_id,
    "left_semi"
).show()

# ============================================================================
# SECTION 6: WINDOW FUNCTIONS (Advanced - High-Value in Interviews!)
# ============================================================================

print("\n" + "="*80)
print("SECTION 6: WINDOW FUNCTIONS")
print("="*80)

# 6.1 ROW_NUMBER - Assign sequential number
print("\n6.1 ROW_NUMBER:")
window_spec_rownum = Window.partitionBy("department").orderBy(col("salary").desc())

df_employees.withColumn(
    "row_num",
    row_number().over(window_spec_rownum)
).show()

# 6.2 RANK and DENSE_RANK
print("\n6.2 RANK and DENSE_RANK:")
df_employees.withColumn(
    "rank",
    rank().over(window_spec_rownum)
).withColumn(
    "dense_rank",
    dense_rank().over(window_spec_rownum)
).show()

# 6.3 LAG and LEAD (Access previous/next row)
print("\n6.3 LAG and LEAD:")
window_spec_order = Window.partitionBy("department").orderBy("join_date")

df_employees.withColumn(
    "previous_salary",
    lag("salary", 1).over(window_spec_order)
).withColumn(
    "next_salary",
    lead("salary", 1).over(window_spec_order)
).withColumn(
    "salary_diff_from_prev",
    col("salary") - lag("salary", 1).over(window_spec_order)
).show()

# 6.4 CUMULATIVE SUM
print("\n6.4 CUMULATIVE SUM:")
window_spec_cumsum = Window.partitionBy("department").orderBy("join_date") \
    .rowsBetween(Window.unboundedPreceding, Window.currentRow)

df_employees.withColumn(
    "cumulative_salary",
    sum("salary").over(window_spec_cumsum)
).show()

# 6.5 MOVING AVERAGE
print("\n6.5 MOVING AVERAGE (3-row window):")
window_spec_moving = Window.partitionBy("department").orderBy("join_date") \
    .rowsBetween(-1, 1)  # 1 before, current, 1 after

df_employees.withColumn(
    "moving_avg_salary",
    avg("salary").over(window_spec_moving)
).show()

# 6.6 NTILE - Divide into N buckets
print("\n6.6 NTILE - Divide into quartiles:")
window_spec_ntile = Window.orderBy("salary")

df_employees.withColumn(
    "salary_quartile",
    ntile(4).over(window_spec_ntile)
).show()

# 6.7 FIRST and LAST
print("\n6.7 FIRST and LAST value in window:")
window_spec_first_last = Window.partitionBy("department").orderBy("salary")

df_employees.withColumn(
    "first_salary_in_dept",
    first("salary").over(window_spec_first_last)
).withColumn(
    "last_salary_in_dept",
    last("salary").over(window_spec_first_last)
).show()

# ============================================================================
# SECTION 7: STRING OPERATIONS
# ============================================================================

print("\n" + "="*80)
print("SECTION 7: STRING OPERATIONS")
print("="*80)

# 7.1 Basic String Functions
print("\n7.1 Basic String Functions:")
df_employees.select(
    col("name"),
    upper(col("name")).alias("upper_name"),
    lower(col("name")).alias("lower_name"),
    length(col("name")).alias("name_length"),
    concat(col("name"), lit(" - "), col("department")).alias("full_info")
).show()

# 7.2 SUBSTRING and SPLIT
print("\n7.2 SUBSTRING and SPLIT:")
df_employees.select(
    col("join_date"),
    substring(col("join_date"), 1, 4).alias("year"),
    substring(col("join_date"), 6, 2).alias("month"),
    split(col("join_date"), "-").alias("date_parts"),
    split(col("join_date"), "-").getItem(0).alias("year_from_split")
).show()

# 7.3 TRIM, LTRIM, RTRIM
test_df = spark.createDataFrame([("  hello  ",), ("world   ",)], ["text"])
test_df.select(
    col("text"),
    trim(col("text")).alias("trimmed"),
    ltrim(col("text")).alias("ltrimmed"),
    rtrim(col("text")).alias("rtrimmed")
).show(truncate=False)

# 7.4 REGEXP_EXTRACT and REGEXP_REPLACE
print("\n7.4 REGEXP operations:")
email_df = spark.createDataFrame([
    ("john.doe@example.com",),
    ("sarah.smith@company.org",)
], ["email"])

email_df.select(
    col("email"),
    regexp_extract(col("email"), "(.+)@", 1).alias("username"),
    regexp_extract(col("email"), "@(.+)", 1).alias("domain"),
    regexp_replace(col("email"), "@.*", "@hidden.com").alias("masked_email")
).show(truncate=False)

# ============================================================================
# SECTION 8: DATE AND TIME OPERATIONS
# ============================================================================

print("\n" + "="*80)
print("SECTION 8: DATE AND TIME OPERATIONS")
print("="*80)

# 8.1 Date Extraction
print("\n8.1 Date Extraction:")
df_employees.select(
    col("join_date"),
    year(col("join_date")).alias("year"),
    month(col("join_date")).alias("month"),
    dayofmonth(col("join_date")).alias("day"),
    dayofweek(col("join_date")).alias("day_of_week"),
    dayofyear(col("join_date")).alias("day_of_year"),
    weekofyear(col("join_date")).alias("week_of_year"),
    quarter(col("join_date")).alias("quarter")
).show()

# 8.2 Date Arithmetic
print("\n8.2 Date Arithmetic:")
df_employees.select(
    col("join_date"),
    date_add(col("join_date"), 30).alias("date_plus_30_days"),
    date_sub(col("join_date"), 30).alias("date_minus_30_days"),
    add_months(col("join_date"), 6).alias("date_plus_6_months"),
    datediff(current_date(), col("join_date")).alias("days_since_joining"),
    months_between(current_date(), col("join_date")).alias("months_since_joining")
).show()

# 8.3 Date Formatting
print("\n8.3 Date Formatting:")
df_employees.select(
    col("join_date"),
    date_format(col("join_date"), "yyyy-MM-dd").alias("standard_format"),
    date_format(col("join_date"), "dd/MM/yyyy").alias("dd_mm_yyyy"),
    date_format(col("join_date"), "MMMM dd, yyyy").alias("long_format"),
    to_date(col("join_date"), "yyyy-MM-dd").alias("as_date")
).show()

# 8.4 Current Date and Timestamp
print("\n8.4 Current Date and Timestamp:")
spark.range(1).select(
    current_date().alias("current_date"),
    current_timestamp().alias("current_timestamp"),
    unix_timestamp().alias("unix_timestamp")
).show(truncate=False)

# ============================================================================
# SECTION 9: NULL HANDLING
# ============================================================================

print("\n" + "="*80)
print("SECTION 9: NULL HANDLING")
print("="*80)

# Create data with nulls
null_data = [
    (1, "John", 50000, "USA"),
    (2, "Sarah", None, "UK"),
    (3, None, 60000, "India"),
    (4, "Mike", 55000, None),
    (5, None, None, None)
]
df_nulls = spark.createDataFrame(null_data, ["id", "name", "salary", "country"])

print("\n9.1 Original data with nulls:")
df_nulls.show()

# 9.2 ISNULL and ISNOTNULL
print("\n9.2 Check for nulls:")
df_nulls.filter(col("salary").isNull()).show()
df_nulls.filter(col("salary").isNotNull()).show()

# 9.3 FILLNA - Fill null values
print("\n9.3 FILLNA:")
df_nulls.fillna({
    "name": "Unknown",
    "salary": 0,
    "country": "Not Specified"
}).show()

# 9.4 DROPNA - Drop rows with nulls
print("\n9.4 DROPNA:")
# Drop rows where ANY column is null
df_nulls.dropna(how='any').show()

# Drop rows where ALL columns are null
df_nulls.dropna(how='all').show()

# Drop rows where specific columns have nulls
df_nulls.dropna(subset=["salary"]).show()

# 9.5 COALESCE - Return first non-null value
print("\n9.5 COALESCE:")
df_nulls.select(
    col("name"),
    col("salary"),
    coalesce(col("salary"), lit(0)).alias("salary_with_default"),
    coalesce(col("name"), lit("Unknown")).alias("name_with_default")
).show()

# 9.6 WHEN - Conditional replacement
print("\n9.6 WHEN for conditional logic:")
df_nulls.select(
    col("name"),
    col("salary"),
    when(col("salary").isNull(), 0)
        .when(col("salary") < 55000, col("salary") * 1.2)
        .otherwise(col("salary"))
        .alias("adjusted_salary")
).show()

# ============================================================================
# SECTION 10: ADVANCED TRANSFORMATIONS
# ============================================================================

print("\n" + "="*80)
print("SECTION 10: ADVANCED TRANSFORMATIONS")
print("="*80)

# 10.1 PIVOT - Convert rows to columns
print("\n10.1 PIVOT:")
df_employees.groupBy("department") \
    .pivot("country") \
    .agg(count("emp_id")) \
    .show()

# With aggregations
df_employees.groupBy("department") \
    .pivot("country") \
    .agg(
        count("emp_id").alias("count"),
        avg("salary").alias("avg_salary")
    ) \
    .show()

# 10.2 UNPIVOT (using stack)
print("\n10.2 UNPIVOT (using stack):")
pivoted = df_employees.groupBy("department") \
    .pivot("country") \
    .agg(count("emp_id"))

# Unpivot back
unpivoted = pivoted.selectExpr(
    "department",
    "stack(3, 'India', India, 'UK', UK, 'USA', USA) as (country, count)"
)
unpivoted.show()

# 10.3 EXPLODE - Convert array to rows
print("\n10.3 EXPLODE:")
array_data = [
    (1, "John", ["Python", "Spark", "SQL"]),
    (2, "Sarah", ["Java", "Kafka"]),
    (3, "Mike", ["Python", "Airflow", "AWS"])
]
df_skills = spark.createDataFrame(array_data, ["id", "name", "skills"])

df_skills.show(truncate=False)

df_skills.select(
    col("id"),
    col("name"),
    explode(col("skills")).alias("skill")
).show()

# 10.4 EXPLODE with position
print("\n10.4 POSEXPLODE:")
df_skills.select(
    col("id"),
    col("name"),
    posexplode(col("skills")).alias("position", "skill")
).show()

# 10.5 ARRAY and MAP operations
print("\n10.5 ARRAY operations:")
df_skills.select(
    col("name"),
    col("skills"),
    size(col("skills")).alias("num_skills"),
    array_contains(col("skills"), "Python").alias("knows_python"),
    col("skills").getItem(0).alias("first_skill")
).show(truncate=False)

# 10.6 STRUCT - Create nested structure
print("\n10.6 STRUCT:")
df_employees.select(
    col("name"),
    struct(
        col("department"),
        col("salary"),
        col("country")
    ).alias("employee_info")
).show(truncate=False)

# ============================================================================
# SECTION 11: UNION, UNIONALL, INTERSECT, EXCEPT
# ============================================================================

print("\n" + "="*80)
print("SECTION 11: SET OPERATIONS")
print("="*80)

# Create two sample datasets
df1 = spark.createDataFrame([(1, "A"), (2, "B"), (3, "C")], ["id", "val"])
df2 = spark.createDataFrame([(2, "B"), (3, "C"), (4, "D")], ["id", "val"])

print("\nDataFrame 1:")
df1.show()
print("DataFrame 2:")
df2.show()

# 11.1 UNION (removes duplicates in Spark 3.x)
print("\n11.1 UNION:")
df1.union(df2).show()

# 11.2 UNIONALL (deprecated, use unionByName)
print("\n11.2 UNION ALL (with distinct to show difference):")
df1.union(df2).distinct().show()

# 11.3 INTERSECT
print("\n11.3 INTERSECT:")
df1.intersect(df2).show()

# 11.4 EXCEPT (MINUS)
print("\n11.4 EXCEPT:")
df1.exceptAll(df2).show()

# ============================================================================
# SECTION 12: PERFORMANCE OPTIMIZATION TECHNIQUES
# ============================================================================

print("\n" + "="*80)
print("SECTION 12: PERFORMANCE OPTIMIZATION")
print("="*80)

# 12.1 CACHE and PERSIST
print("\n12.1 CACHE and PERSIST:")
# Cache in memory
# df_employees.cache()
# df_employees.count()  # Triggers caching

# Persist with storage level
from pyspark import StorageLevel
# df_employees.persist(StorageLevel.MEMORY_AND_DISK)

# Unpersist when done
# df_employees.unpersist()

# 12.2 REPARTITION and COALESCE
print("\n12.2 REPARTITION and COALESCE:")
print(f"Original partitions: {df_employees.rdd.getNumPartitions()}")

# Increase partitions (full shuffle)
df_repartitioned = df_employees.repartition(8)
print(f"After repartition: {df_repartitioned.rdd.getNumPartitions()}")

# Decrease partitions (no shuffle, more efficient)
df_coalesced = df_repartitioned.coalesce(2)
print(f"After coalesce: {df_coalesced.rdd.getNumPartitions()}")

# Repartition by column (for joins and groupBy)
df_by_dept = df_employees.repartition("department")
print(f"Repartitioned by department: {df_by_dept.rdd.getNumPartitions()}")

# 12.3 BROADCAST JOIN (for small tables)
print("\n12.3 BROADCAST JOIN:")
from pyspark.sql.functions import broadcast

# Regular join
# result1 = df_employees.join(df_products, "category")

# # Broadcast join (much faster when one table is small)
# result2 = df_employees.join(broadcast(df_products), "category")

# # 12.4 PARTITION PRUNING
# print("\n12.4 Partition Pruning (concept):")
# # When writing data partitioned by a column
# df_employees.write.partitionBy("department").parquet("/tmp/employees_partitioned")

# When reading, filters on partition column are very efficient
# spark.read.parquet("/tmp/employees_partitioned").filter("department = 'Sales'")

# ============================================================================
# SECTION 13: USER DEFINED FUNCTIONS (UDFs)
# ============================================================================

print("\n" + "="*80)
print("SECTION 13: USER DEFINED FUNCTIONS (UDFs)")
print("="*80)

# 13.1 Simple UDF
from pyspark.sql.types import StringType

def categorize_salary(salary):
    if salary < 50000:
        return "Low"
    elif salary < 70000:
        return "Medium"
    else:
        return "High"

# Register UDF
categorize_salary_udf = udf(categorize_salary, StringType())

# Use UDF
df_employees.withColumn(
    "salary_category",
    categorize_salary_udf(col("salary"))
).show()

# 13.2 UDF with multiple inputs
def full_info(name, department, salary):
    return f"{name} works in {department} with salary ${salary}"

full_info_udf = udf(full_info, StringType())

df_employees.withColumn(
    "full_info",
    full_info_udf(col("name"), col("department"), col("salary"))
).show(truncate=False)

# 13.3 Pandas UDF (vectorized - much faster!)
from pyspark.sql.functions import pandas_udf
import pandas as pd

@pandas_udf(IntegerType())
def bonus_calculation(salary: pd.Series) -> pd.Series:
    return (salary * 0.1).astype(int)

df_employees.withColumn(
    "bonus",
    bonus_calculation(col("salary"))
).show()

# ============================================================================
# SECTION 14: COMMON INTERVIEW QUESTIONS - SOLUTIONS
# ============================================================================

print("\n" + "="*80)
print("SECTION 14: COMMON INTERVIEW QUESTIONS")
print("="*80)

# Q1: Find second highest salary by department
print("\nQ1: Second highest salary by department:")
window_rank = Window.partitionBy("department").orderBy(col("salary").desc())
df_employees.withColumn("rank", dense_rank().over(window_rank)) \
    .filter(col("rank") == 2) \
    .select("department", "name", "salary") \
    .show()

# Q2: Find employees with salary above department average
print("\nQ2: Employees with salary above department average:")
window_avg = Window.partitionBy("department")
df_employees.withColumn("dept_avg_salary", avg("salary").over(window_avg)) \
    .filter(col("salary") > col("dept_avg_salary")) \
    .select("name", "department", "salary", "dept_avg_salary") \
    .show()

# Q3: Running total of sales by employee
print("\nQ3: Running total of sales:")
window_cumsum = Window.partitionBy("emp_id").orderBy("order_date") \
    .rowsBetween(Window.unboundedPreceding, Window.currentRow)

df_sales.withColumn(
    "running_total",
    sum("amount").over(window_cumsum)
).show()

# Q4: Find duplicate records
print("\nQ4: Find duplicates:")
df_emp_sales.groupBy("emp_id", "order_id") \
    .count() \
    .filter(col("count") > 1) \
    .show()

# Q5: Calculate percentage contribution by department
print("\nQ5: Percentage contribution by department:")
total_salary = df_employees.agg(sum("salary")).collect()[0][0]

df_employees.groupBy("department") \
    .agg(sum("salary").alias("dept_salary")) \
    .withColumn("total_salary", lit(total_salary)) \
    .withColumn("percentage", (col("dept_salary") / col("total_salary") * 100)) \
    .show()

# Q6: Find gap in sequence
print("\nQ6: Find gaps in order IDs:")
df_sales.select("order_id").orderBy("order_id").show()

window_lead = Window.orderBy("order_id")

print("+"*80)
df_sales.withColumn("new",lead("order_id").over(window_lead))\
.withColumn("difference",col("new")-col("order_id"))\
.show()
print("+"*80)

df_sales.withColumn(
    "next_id",
    lead("order_id").over(window_lead)
).withColumn(
    "gap",
    col("next_id") - col("order_id")
).filter(col("gap") > 1).show()

# Q7: Transpose data (pivot)
print("\nQ7: Transpose - employees per country by department:")
df_employees.show()
df_employees.groupBy("department") \
    .pivot("country") \
    .count() \
    .show()

# Q8: Self Join - find employees in same department
print("\nQ8: Find colleagues in same department:")
df_emp1 = df_employees.alias("emp1")
df_emp2 = df_employees.alias("emp2")

df_emp1.join(
    df_emp2,
    (col("emp1.department") == col("emp2.department")) &
    (col("emp1.emp_id") < col("emp2.emp_id"))
).select(
    col("emp1.name").alias("employee1"),
    col("emp2.name").alias("employee2"),
    col("emp1.department")
).show()

# Q9: Dense rank vs Rank difference
print("\nQ9: Difference between RANK and DENSE_RANK:")
salary_data = [
    ("John", 50000),
    ("Sarah", 60000),
    ("Mike", 60000),
    ("Emma", 70000),
    ("Alex", 70000),
    ("Lisa", 80000)
]
df_salaries = spark.createDataFrame(salary_data, ["name", "salary"])

window_spec = Window.orderBy(col("salary").desc())

df_salaries.withColumn("rank", rank().over(window_spec)) \
    .withColumn("dense_rank", dense_rank().over(window_spec)) \
    .withColumn("row_number", row_number().over(window_spec)) \
    .show()

# Q10: Calculate year-over-year growth
print("\nQ10: Calculate previous row difference (YoY growth concept):")
window_lag = Window.orderBy("join_date")

df_employees.withColumn(
    "prev_salary",
    lag("salary").over(window_lag)
).withColumn(
    "salary_change",
    when(col("prev_salary").isNotNull(),
         col("salary") - col("prev_salary"))
    .otherwise(0)
).show()

# ============================================================================
# SECTION 15: BEST PRACTICES AND TIPS
# ============================================================================

print("\n" + "="*80)
print("SECTION 15: BEST PRACTICES")
print("="*80)

"""
BEST PRACTICES FOR INTERVIEWS:

1. ALWAYS USE col() or F.col() for column references
   - Better: col("salary")
   - Avoid: df["salary"] or df.salary

2. Use ALIASES for readability
   - .withColumn("new_col", col("old_col") * 2).alias("doubled")

3. CHAIN transformations for clarity
   df.filter(...) \
     .select(...) \
     .groupBy(...) \
     .agg(...)

4. OPTIMIZE joins:
   - Use broadcast() for small tables
   - Repartition on join keys for large tables
   - Filter before join when possible

5. CACHE wisely:
   - Cache when DataFrame is used multiple times
   - Unpersist when done

6. AVOID UDFs when possible:
   - Use built-in functions (much faster)
   - Use Pandas UDFs if you must use UDFs

7. WINDOW functions are powerful:
   - Master row_number, rank, dense_rank
   - Understand lag/lead for sequential data
   - Know cumulative and moving averages

8. NULL handling:
   - Always consider nulls in your logic
   - Use coalesce, fillna, dropna appropriately

9. PARTITION data appropriately:
   - Too few partitions = poor parallelism
   - Too many partitions = overhead
   - Rule of thumb: 2-3 tasks per core

10. EXPLAIN your approach:
    - In interviews, explain WHY you chose a method
    - Discuss performance implications
    - Show alternative approaches
"""

print("\n" + "="*80)
print("MASTERCLASS COMPLETE!")
print("="*80)
print("\nKey Takeaways:")
print("1. Practice window functions - they're critical!")
print("2. Master different join types")
print("3. Understand aggregations and groupBy")
print("4. Know performance optimization (cache, broadcast, partitioning)")
print("5. Be comfortable with null handling")
print("6. Practice common interview questions")
print("\nGood luck with your interviews!")
print("="*80)

# Stop Spark session
spark.stop()
