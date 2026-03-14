# Lloyds Technology Centre Hyderabad -- Senior Data Engineer Interview Guide

## SQL Questions (Detailed)

### 1. Find duplicate records in a table

**Question:** Write a SQL query to find duplicate rows based on a
column.

**Answer:** Duplicates occur when the same value appears more than once.

``` sql
SELECT column_name, COUNT(*)
FROM table_name
GROUP BY column_name
HAVING COUNT(*) > 1;
```

**Explanation:** - `GROUP BY` groups identical values - `COUNT(*)`
counts occurrences - `HAVING` filters aggregated results

**Follow-up:** remove duplicates

``` sql
DELETE FROM table_name
WHERE id NOT IN (
    SELECT MIN(id)
    FROM table_name
    GROUP BY column_name
);
```

------------------------------------------------------------------------

### 2. Second highest salary

``` sql
SELECT MAX(salary)
FROM employees
WHERE salary < (SELECT MAX(salary) FROM employees);
```

**Explanation** 1. Inner query finds highest salary 2. Outer query finds
highest below that value

**Alternative using window function**

``` sql
SELECT salary
FROM (
  SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) r
  FROM employees
) t
WHERE r = 2;
```

------------------------------------------------------------------------

### 3. Difference between ROW_NUMBER, RANK, DENSE_RANK

  Function     Behavior
  ------------ -----------------------------
  ROW_NUMBER   unique sequence
  RANK         duplicates allowed, gaps
  DENSE_RANK   duplicates allowed, no gaps

Example

``` sql
SELECT name, salary,
ROW_NUMBER() OVER(ORDER BY salary DESC),
RANK() OVER(ORDER BY salary DESC),
DENSE_RANK() OVER(ORDER BY salary DESC)
FROM employees;
```

------------------------------------------------------------------------

### 4. Query Optimization

**Techniques** - Indexing - Partitioning - Predicate pushdown - Column
pruning - Avoid SELECT \* - Reduce joins

**Example optimization**

Bad

``` sql
SELECT *
FROM orders o
JOIN customers c ON o.customer_id=c.id
```

Better

``` sql
SELECT o.order_id, c.customer_name
FROM orders o
JOIN customers c ON o.customer_id=c.id
WHERE o.order_date >= '2024-01-01'
```

------------------------------------------------------------------------

## Python Questions

### Reverse a string

``` python
def reverse_string(s):
    return s[::-1]
```

### Find duplicates in list

``` python
from collections import Counter

nums=[1,2,2,3,4,4,5]

duplicates=[num for num,count in Counter(nums).items() if count>1]
print(duplicates)
```

### Merge two sorted lists

``` python
def merge_sorted(a,b):
    result=[]
    i=j=0
    
    while i<len(a) and j<len(b):
        if a[i]<b[j]:
            result.append(a[i])
            i+=1
        else:
            result.append(b[j])
            j+=1
            
    result.extend(a[i:])
    result.extend(b[j:])
    
    return result
```

------------------------------------------------------------------------

## Spark Questions

### Spark Architecture

Spark consists of:

-   Driver program
-   Cluster manager
-   Executors
-   Tasks

Execution Flow

1.  User writes Spark job
2.  Driver builds DAG
3.  Tasks distributed to executors
4.  Executors process partitions

------------------------------------------------------------------------

### Lazy Evaluation

Spark transformations are not executed immediately.

Example:

``` python
df.filter("age>30").select("name")
```

Execution happens only when:

    df.count()
    df.show()
    df.write

------------------------------------------------------------------------

### Handling Data Skew

Techniques:

1.  Key salting
2.  Broadcast joins
3.  Skew join hints
4.  Repartitioning

Example:

``` python
df = df.withColumn("salt", rand())
```

------------------------------------------------------------------------

## Data Engineering Concepts

### ETL vs ELT

  ETL                      ELT
  ------------------------ -------------------------
  Transform before load    Transform after load
  traditional warehouses   modern cloud warehouses

Example

ETL → Informatica

ELT → Snowflake / BigQuery

------------------------------------------------------------------------

### CDC (Change Data Capture)

CDC tracks incremental changes.

Methods:

1.  Timestamp column
2.  Database logs
3.  Debezium/Kafka

Example

    SELECT *
    FROM orders
    WHERE last_updated > last_run_time

------------------------------------------------------------------------

## System Design

### Design real-time pipeline

Architecture

    Source → Kafka → Spark Streaming → Data Lake → Warehouse → BI

Key considerations:

-   fault tolerance
-   exactly once processing
-   schema evolution
-   monitoring

------------------------------------------------------------------------
