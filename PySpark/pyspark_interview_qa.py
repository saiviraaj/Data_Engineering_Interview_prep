# PYSPARK INTERVIEW QUESTIONS & ANSWERS
# 50 Most Common Questions with Detailed Solutions

"""
This document contains the most frequently asked PySpark transformation questions
in data engineering interviews, organized by difficulty level.
"""

# ==============================================================================
# EASY LEVEL (Questions 1-15)
# ==============================================================================

# Q1: How do you select specific columns from a DataFrame?
"""
Answer:
"""
from pyspark.sql.functions import col

# Method 1: Using select with column names
df.select("col1", "col2", "col3")

# Method 2: Using select with col()
df.select(col("col1"), col("col2"))

# Method 3: Using select with list
columns_list = ["col1", "col2"]
df.select(columns_list)

# Method 4: Select with expressions
df.select(col("col1"), (col("col2") * 2).alias("col2_doubled"))


# Q2: How do you filter rows based on a condition?
"""
Answer:
"""
# Method 1: Using filter
df.filter(col("age") > 25)

# Method 2: Using where (same as filter)
df.where(col("salary") > 50000)

# Method 3: Multiple conditions with AND
df.filter((col("age") > 25) & (col("country") == "USA"))

# Method 4: Multiple conditions with OR
df.filter((col("department") == "Sales") | (col("department") == "Marketing"))

# Method 5: SQL-like string expression
df.where("age > 25 AND country = 'USA'")

# Method 6: Using isin for multiple values
df.filter(col("department").isin(["Sales", "Marketing", "Engineering"]))


# Q3: How do you add a new column to a DataFrame?
"""
Answer:
"""
# Method 1: Simple calculation
df.withColumn("bonus", col("salary") * 0.1)

# Method 2: Conditional logic using when
from pyspark.sql.functions import when

df.withColumn(
    "salary_grade",
    when(col("salary") < 50000, "Low")
    .when(col("salary") < 80000, "Medium")
    .otherwise("High")
)

# Method 3: Multiple columns at once
df.withColumn("tax", col("salary") * 0.3) \
  .withColumn("net_salary", col("salary") - col("tax"))

# Method 4: Using literal values
from pyspark.sql.functions import lit
df.withColumn("country", lit("USA"))


# Q4: How do you rename a column?
"""
Answer:
"""
# Method 1: withColumnRenamed (single column)
df.withColumnRenamed("old_name", "new_name")

# Method 2: Using alias in select
df.select(col("old_name").alias("new_name"))

# Method 3: Rename multiple columns using select
df.select(
    col("emp_id").alias("employee_id"),
    col("dept").alias("department"),
    col("sal").alias("salary")
)

# Method 4: Using toDF (rename all columns)
df.toDF("new_col1", "new_col2", "new_col3")


# Q5: How do you remove duplicates?
"""
Answer:
"""
# Method 1: Remove complete duplicates
df.distinct()

# Method 2: Remove duplicates based on specific columns
df.dropDuplicates(["emp_id", "email"])

# Method 3: Keep first occurrence only
df.dropDuplicates()

# Method 4: Using groupBy to find and count duplicates
df.groupBy("emp_id").count().filter(col("count") > 1)


# Q6: How do you sort a DataFrame?
"""
Answer:
"""
# Method 1: Ascending order
df.orderBy("salary")

# Method 2: Descending order
df.orderBy(col("salary").desc())

# Method 3: Multiple columns
df.orderBy(col("department"), col("salary").desc())

# Method 4: Using sort (same as orderBy)
df.sort(col("age").desc(), col("name"))

# Method 5: Nulls first or last
df.orderBy(col("salary").desc_nulls_last())


# Q7: How do you perform aggregations?
"""
Answer:
"""
from pyspark.sql.functions import sum, avg, count, min, max

# Method 1: Simple aggregations
df.agg(
    count("*").alias("total_count"),
    sum("salary").alias("total_salary"),
    avg("salary").alias("avg_salary"),
    min("salary").alias("min_salary"),
    max("salary").alias("max_salary")
)

# Method 2: Using groupBy
df.groupBy("department").agg(
    count("*").alias("emp_count"),
    avg("salary").alias("avg_salary")
)

# Method 3: Multiple groupBy columns
df.groupBy("department", "country").agg(
    count("*").alias("emp_count"),
    sum("salary").alias("total_salary")
)


# Q8: What's the difference between count() and count(column_name)?
"""
Answer:
count() - counts total rows including nulls
count(column_name) - counts non-null values in that column
"""
from pyspark.sql.functions import count

# Count all rows
df.select(count("*")).show()  # or df.count()

# Count non-null values in a column
df.select(count("email")).show()

# Example showing difference
# If email column has nulls:
df.select(
    count("*").alias("total_rows"),
    count("email").alias("non_null_emails")
).show()


# Q9: How do you handle null values?
"""
Answer:
"""
from pyspark.sql.functions import coalesce, isnull, isnotnull

# Method 1: Fill nulls with default values
df.fillna({"salary": 0, "department": "Unknown"})

# Method 2: Drop rows with any null
df.dropna()

# Method 3: Drop rows with all nulls
df.dropna(how='all')

# Method 4: Drop rows where specific columns have nulls
df.dropna(subset=["salary", "email"])

# Method 5: Replace null with first non-null value
df.select(
    coalesce(col("salary"), lit(0)).alias("salary")
)

# Method 6: Filter null rows
df.filter(col("salary").isNull())
df.filter(col("salary").isNotNull())


# Q10: How do you perform different types of joins?
"""
Answer:
"""
# Sample data
df1 = employees  # has emp_id, name, dept_id
df2 = departments  # has dept_id, dept_name

# Method 1: Inner Join (default)
df1.join(df2, df1.dept_id == df2.dept_id, "inner")

# Method 2: Left Join
df1.join(df2, "dept_id", "left")  # When column names are same

# Method 3: Right Join
df1.join(df2, df1.dept_id == df2.dept_id, "right")

# Method 4: Full Outer Join
df1.join(df2, "dept_id", "outer")

# Method 5: Left Anti Join (rows in df1 not in df2)
df1.join(df2, "dept_id", "left_anti")

# Method 6: Left Semi Join (rows in df1 that have match in df2)
df1.join(df2, "dept_id", "left_semi")

# Method 7: Cross Join
df1.crossJoin(df2)


# Q11: How do you concatenate strings?
"""
Answer:
"""
from pyspark.sql.functions import concat, concat_ws, lit

# Method 1: concat (simple concatenation)
df.select(concat(col("first_name"), lit(" "), col("last_name")).alias("full_name"))

# Method 2: concat_ws (with separator)
df.select(concat_ws(" ", col("first_name"), col("last_name")).alias("full_name"))

# Method 3: concat_ws with multiple columns
df.select(concat_ws("-", col("country"), col("city"), col("zip_code")).alias("address"))


# Q12: How do you extract year, month, day from a date column?
"""
Answer:
"""
from pyspark.sql.functions import year, month, dayofmonth, dayofweek

df.select(
    col("date_column"),
    year(col("date_column")).alias("year"),
    month(col("date_column")).alias("month"),
    dayofmonth(col("date_column")).alias("day"),
    dayofweek(col("date_column")).alias("day_of_week")
)


# Q13: How do you convert a string to date?
"""
Answer:
"""
from pyspark.sql.functions import to_date, to_timestamp

# Method 1: to_date (without format, uses default)
df.withColumn("date", to_date(col("date_string")))

# Method 2: to_date with format
df.withColumn("date", to_date(col("date_string"), "yyyy-MM-dd"))

# Method 3: to_timestamp
df.withColumn("timestamp", to_timestamp(col("datetime_string"), "yyyy-MM-dd HH:mm:ss"))


# Q14: How do you find the length of a string?
"""
Answer:
"""
from pyspark.sql.functions import length

df.select(
    col("name"),
    length(col("name")).alias("name_length")
)


# Q15: How do you convert column to uppercase/lowercase?
"""
Answer:
"""
from pyspark.sql.functions import upper, lower, initcap

df.select(
    col("name"),
    upper(col("name")).alias("upper_name"),
    lower(col("name")).alias("lower_name"),
    initcap(col("name")).alias("title_case")  # First letter of each word capitalized
)


# ==============================================================================
# MEDIUM LEVEL (Questions 16-35)
# ==============================================================================

# Q16: Find the second highest salary
"""
Answer: Multiple approaches
"""
from pyspark.sql.functions import dense_rank, row_number
from pyspark.sql.window import Window

# Method 1: Using dense_rank
window_spec = Window.orderBy(col("salary").desc())
df.withColumn("rank", dense_rank().over(window_spec)) \
  .filter(col("rank") == 2) \
  .select("name", "salary")

# Method 2: Using limit and offset concept
df.select("salary").distinct().orderBy(col("salary").desc()).limit(2).collect()[1]


# Q17: Find nth highest salary by department
"""
Answer:
"""
n = 3  # for 3rd highest
window_spec = Window.partitionBy("department").orderBy(col("salary").desc())

df.withColumn("rank", dense_rank().over(window_spec)) \
  .filter(col("rank") == n) \
  .select("department", "name", "salary")


# Q18: Calculate running total
"""
Answer:
"""
from pyspark.sql.window import Window

window_spec = Window.partitionBy("emp_id") \
                    .orderBy("order_date") \
                    .rowsBetween(Window.unboundedPreceding, Window.currentRow)

df.withColumn("running_total", sum("amount").over(window_spec))


# Q19: Calculate difference from previous row (lag)
"""
Answer:
"""
from pyspark.sql.functions import lag

window_spec = Window.partitionBy("emp_id").orderBy("date")

df.withColumn("prev_salary", lag("salary", 1).over(window_spec)) \
  .withColumn("salary_change", col("salary") - col("prev_salary"))


# Q20: Calculate moving average (3-row window)
"""
Answer:
"""
window_spec = Window.partitionBy("product_id") \
                    .orderBy("date") \
                    .rowsBetween(-1, 1)  # 1 before, current, 1 after

df.withColumn("moving_avg_sales", avg("sales").over(window_spec))


# Q21: Pivot data (rows to columns)
"""
Answer:
"""
# Convert this:
# dept    | country | count
# Sales   | USA     | 5
# Sales   | UK      | 3

# To this:
# dept    | USA | UK
# Sales   | 5   | 3

df.groupBy("dept") \
  .pivot("country") \
  .agg(count("emp_id"))

# With specific values (better performance)
df.groupBy("dept") \
  .pivot("country", ["USA", "UK", "India"]) \
  .agg(count("emp_id"))


# Q22: Unpivot data (columns to rows)
"""
Answer:
"""
# Using stack function
df.selectExpr(
    "emp_id",
    "stack(3, 'Jan', jan_sales, 'Feb', feb_sales, 'Mar', mar_sales) as (month, sales)"
)


# Q23: Find employees earning more than department average
"""
Answer:
"""
window_spec = Window.partitionBy("department")

df.withColumn("dept_avg_salary", avg("salary").over(window_spec)) \
  .filter(col("salary") > col("dept_avg_salary"))


# Q24: Remove duplicates keeping latest record
"""
Answer:
"""
window_spec = Window.partitionBy("emp_id").orderBy(col("updated_date").desc())

df.withColumn("row_num", row_number().over(window_spec)) \
  .filter(col("row_num") == 1) \
  .drop("row_num")


# Q25: Split a column into multiple columns
"""
Answer:
"""
from pyspark.sql.functions import split

# Split "John,Doe,30" into separate columns
df.withColumn("split_col", split(col("full_info"), ",")) \
  .withColumn("first_name", col("split_col").getItem(0)) \
  .withColumn("last_name", col("split_col").getItem(1)) \
  .withColumn("age", col("split_col").getItem(2))


# Q26: Explode an array column
"""
Answer:
"""
from pyspark.sql.functions import explode

# If you have: emp_id | skills (array)
#              1      | [Python, Spark, SQL]

# Convert to: emp_id | skill
#             1      | Python
#             1      | Spark
#             1      | SQL

df.select("emp_id", explode("skills").alias("skill"))


# Q27: Find employees who joined in the same month
"""
Answer:
"""
from pyspark.sql.functions import month, year

df_with_month = df.withColumn("join_month", month("join_date")) \
                  .withColumn("join_year", year("join_date"))

df1 = df_with_month.alias("df1")
df2 = df_with_month.alias("df2")

df1.join(
    df2,
    (col("df1.join_month") == col("df2.join_month")) &
    (col("df1.join_year") == col("df2.join_year")) &
    (col("df1.emp_id") < col("df2.emp_id"))
).select(
    col("df1.name").alias("emp1"),
    col("df2.name").alias("emp2"),
    col("df1.join_date")
)


# Q28: Calculate percentage of total
"""
Answer:
"""
# Find each department's percentage of total salary

total_salary = df.agg(sum("salary")).collect()[0][0]

df.groupBy("department") \
  .agg(sum("salary").alias("dept_salary")) \
  .withColumn("percentage", (col("dept_salary") / total_salary * 100))


# Q29: Find gaps in sequence
"""
Answer:
"""
from pyspark.sql.functions import lead

window_spec = Window.orderBy("order_id")

df.withColumn("next_id", lead("order_id").over(window_spec)) \
  .withColumn("gap", col("next_id") - col("order_id")) \
  .filter(col("gap") > 1)


# Q30: Cumulative sum by group
"""
Answer:
"""
window_spec = Window.partitionBy("category") \
                    .orderBy("date") \
                    .rowsBetween(Window.unboundedPreceding, Window.currentRow)

df.withColumn("cumulative_sales", sum("sales").over(window_spec))


# Q31: Rank with ties (dense_rank vs rank)
"""
Answer:
RANK: 1, 2, 2, 4, 5 (skips 3)
DENSE_RANK: 1, 2, 2, 3, 4 (no skip)
ROW_NUMBER: 1, 2, 3, 4, 5 (unique even for ties)
"""
window_spec = Window.orderBy(col("score").desc())

df.withColumn("rank", rank().over(window_spec)) \
  .withColumn("dense_rank", dense_rank().over(window_spec)) \
  .withColumn("row_number", row_number().over(window_spec))


# Q32: First and last value in group
"""
Answer:
"""
from pyspark.sql.functions import first, last

window_spec = Window.partitionBy("department").orderBy("join_date")

df.withColumn("first_joiner", first("name").over(window_spec)) \
  .withColumn("last_joiner", last("name").over(window_spec))


# Q33: Calculate age from date of birth
"""
Answer:
"""
from pyspark.sql.functions import datediff, current_date

df.withColumn(
    "age",
    (datediff(current_date(), col("date_of_birth")) / 365).cast("int")
)


# Q34: Handle multiple delimiters in string split
"""
Answer:
"""
from pyspark.sql.functions import regexp_replace, split

# Split by comma OR semicolon OR pipe
df.withColumn(
    "cleaned",
    regexp_replace(col("text"), "[,;|]", ",")
).withColumn(
    "split_values",
    split(col("cleaned"), ",")
)


# Q35: Case-insensitive string matching
"""
Answer:
"""
from pyspark.sql.functions import lower

df.filter(lower(col("name")).contains("john"))

# OR using regexp
from pyspark.sql.functions import regexp_extract

df.filter(col("name").rlike("(?i)john"))  # (?i) for case-insensitive


# ==============================================================================
# HARD LEVEL (Questions 36-50)
# ==============================================================================

# Q36: Find consecutive dates
"""
Answer: Find employees who worked on consecutive days
"""
from pyspark.sql.functions import datediff, lead, lag

window_spec = Window.partitionBy("emp_id").orderBy("work_date")

df.withColumn("next_date", lead("work_date").over(window_spec)) \
  .withColumn("days_diff", datediff(col("next_date"), col("work_date"))) \
  .filter(col("days_diff") == 1)


# Q37: Implement complex business logic with multiple when conditions
"""
Answer: Calculate bonus based on multiple criteria
"""
from pyspark.sql.functions import when

df.withColumn(
    "bonus",
    when((col("department") == "Sales") & (col("performance") == "Excellent"), col("salary") * 0.2)
    .when((col("department") == "Sales") & (col("performance") == "Good"), col("salary") * 0.15)
    .when((col("department") == "Engineering") & (col("years_experience") > 5), col("salary") * 0.18)
    .when((col("department") == "Engineering"), col("salary") * 0.12)
    .otherwise(col("salary") * 0.10)
)


# Q38: Find employees who haven't made any sales (anti join pattern)
"""
Answer:
"""
# All employees who don't have any record in sales table
employees.join(
    sales,
    employees.emp_id == sales.emp_id,
    "left_anti"
).select("emp_id", "name")


# Q39: Calculate percentile ranks
"""
Answer:
"""
from pyspark.sql.functions import percent_rank

window_spec = Window.partitionBy("department").orderBy("salary")

df.withColumn("percentile_rank", percent_rank().over(window_spec))


# Q40: Implement ntile for quartiles/deciles
"""
Answer:
"""
from pyspark.sql.functions import ntile

window_spec = Window.orderBy("salary")

# Divide into 4 quartiles
df.withColumn("quartile", ntile(4).over(window_spec))

# Divide into 10 deciles
df.withColumn("decile", ntile(10).over(window_spec))


# Q41: Calculate year-over-year growth
"""
Answer:
"""
window_spec = Window.partitionBy("product_id").orderBy("year")

df.withColumn("prev_year_sales", lag("sales", 1).over(window_spec)) \
  .withColumn(
      "yoy_growth",
      ((col("sales") - col("prev_year_sales")) / col("prev_year_sales") * 100)
  )


# Q42: Find top N records per group
"""
Answer: Top 3 salaries per department
"""
window_spec = Window.partitionBy("department").orderBy(col("salary").desc())

df.withColumn("rank", row_number().over(window_spec)) \
  .filter(col("rank") <= 3)


# Q43: Implement complex join with multiple conditions
"""
Answer:
"""
df1.join(
    df2,
    (df1.emp_id == df2.manager_id) &
    (df1.department == df2.department) &
    (df1.hire_date < df2.hire_date),
    "inner"
)


# Q44: Calculate rolling/sliding window aggregations
"""
Answer: 7-day rolling average
"""
# Using rangeBetween for date-based windows
from pyspark.sql.functions import unix_timestamp

window_spec = Window.partitionBy("product_id") \
                    .orderBy(unix_timestamp("date").cast("long")) \
                    .rangeBetween(-6*86400, 0)  # 6 days before to current (86400 sec = 1 day)

df.withColumn("rolling_7day_avg", avg("sales").over(window_spec))


# Q45: Handle hierarchical data (manager-employee relationship)
"""
Answer: Find all subordinates of a manager (recursive)
"""
# This requires iterative joins in PySpark (no native recursion)
def get_all_subordinates(df, manager_id, level=0):
    subordinates = df.filter(col("manager_id") == manager_id)
    
    if subordinates.count() == 0:
        return df.filter(lit(False))  # Empty DataFrame
    
    subordinates = subordinates.withColumn("level", lit(level))
    
    # Get subordinates of subordinates
    for row in subordinates.select("emp_id").collect():
        next_level = get_all_subordinates(df, row.emp_id, level + 1)
        subordinates = subordinates.union(next_level)
    
    return subordinates


# Q46: Implement window frame specifications
"""
Answer: Different frame specifications
"""
# ROWS BETWEEN
window_rows = Window.orderBy("date") \
                    .rowsBetween(-2, 2)  # 2 rows before to 2 rows after

# RANGE BETWEEN
window_range = Window.orderBy("value") \
                     .rangeBetween(-100, 100)  # Values within ±100

# UNBOUNDED
window_unbounded = Window.orderBy("date") \
                         .rowsBetween(Window.unboundedPreceding, Window.currentRow)


# Q47: Complex string operations with regex
"""
Answer: Extract domain from email
"""
from pyspark.sql.functions import regexp_extract

df.withColumn(
    "domain",
    regexp_extract(col("email"), "@(.+)", 1)
)

# Extract phone number pattern
df.withColumn(
    "phone",
    regexp_extract(col("text"), r"\d{3}-\d{3}-\d{4}", 0)
)


# Q48: Handle slowly changing dimensions (SCD Type 2)
"""
Answer: Track historical changes
"""
from pyspark.sql.functions import current_date

# New records
new_df = ...

# Existing records
existing_df = ...

# Find changed records
changed = new_df.join(
    existing_df,
    (new_df.emp_id == existing_df.emp_id) &
    ((new_df.salary != existing_df.salary) | (new_df.department != existing_df.department))
)

# Mark old records as expired
expired = changed.select(existing_df["*"]) \
                 .withColumn("end_date", current_date()) \
                 .withColumn("is_current", lit(False))

# Mark new records as current
current = changed.select(new_df["*"]) \
                 .withColumn("start_date", current_date()) \
                 .withColumn("end_date", lit(None)) \
                 .withColumn("is_current", lit(True))


# Q49: Optimize join performance
"""
Answer: Broadcast join for small tables
"""
from pyspark.sql.functions import broadcast

# Regular join (shuffle both sides)
df_large.join(df_small, "key")

# Broadcast join (broadcast small table to all executors)
df_large.join(broadcast(df_small), "key")

# Repartition before join on join key
df1_repartitioned = df1.repartition("join_key")
df2_repartitioned = df2.repartition("join_key")
result = df1_repartitioned.join(df2_repartitioned, "join_key")


# Q50: Handle skewed data in joins
"""
Answer: Salting technique for skew
"""
from pyspark.sql.functions import rand, concat

# Add random salt to skewed key
salt_factor = 10

df_large_salted = df_large.withColumn(
    "salted_key",
    concat(col("key"), lit("_"), (rand() * salt_factor).cast("int"))
)

# Replicate small table with all salt values
df_small_exploded = df_small.withColumn(
    "salt",
    explode(array([lit(i) for i in range(salt_factor)]))
).withColumn(
    "salted_key",
    concat(col("key"), lit("_"), col("salt"))
)

# Join on salted key
result = df_large_salted.join(df_small_exploded, "salted_key")


print("="*80)
print("Interview preparation complete!")
print("Practice these questions with real data for best results")
print("="*80)
