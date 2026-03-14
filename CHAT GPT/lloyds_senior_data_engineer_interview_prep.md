# Lloyds Technology Centre Hyderabad --- Senior Data Engineer Interview Prep

## 1. SQL Questions

### Q1. Find duplicate records in a table

``` sql
SELECT column_name, COUNT(*)
FROM table_name
GROUP BY column_name
HAVING COUNT(*) > 1;
```

### Q2. Find the second highest salary

``` sql
SELECT MAX(salary)
FROM employees
WHERE salary < (SELECT MAX(salary) FROM employees);
```

### Q3. Difference between ROW_NUMBER, RANK, DENSE_RANK

-   ROW_NUMBER: assigns unique sequential numbers
-   RANK: duplicates create gaps
-   DENSE_RANK: duplicates allowed but no gaps

### Q4. Difference between WHERE and HAVING

-   WHERE filters rows before aggregation
-   HAVING filters groups after aggregation

### Q5. Generate date range

``` sql
SELECT date
FROM UNNEST(GENERATE_DATE_ARRAY('2024-01-01','2024-12-31',INTERVAL 1 DAY)) AS date;
```

### Q6. Optimize a slow query

-   Add indexes
-   Use partitioning
-   Reduce scans
-   Avoid SELECT \*
-   Use query plan analysis

------------------------------------------------------------------------

## 2. Python Questions

### Q1. Reverse a string

``` python
s = "hello"
print(s[::-1])
```

### Q2. Find duplicates in list

``` python
nums=[1,2,3,1,4,2]
dups=set([x for x in nums if nums.count(x)>1])
print(dups)
```

    ### Q3. Flatten nested JSON

    ``` python
    import json
    def flatten(d,parent_key='',sep='_'):
        items=[]
        for k,v in d.items():
            new_key=parent_key+sep+k if parent_key else k
            if isinstance(v,dict):
                items.extend(flatten(v,new_key,sep=sep).items())
            else:
                items.append((new_key,v))
        return dict(items)
```

### Q4. Merge two sorted lists

``` python
a=[1,3,5]
b=[2,4,6]
print(sorted(a+b))
```

### Q5. Generators vs Iterators

-   Iterator: object implementing `__iter__` and `__next__`
-   Generator: function using `yield` to produce sequence lazily

------------------------------------------------------------------------

## 3. Spark / Big Data Questions

### Q1. Difference between RDD, DataFrame, Dataset

-   RDD: low-level distributed objects
-   DataFrame: structured data with catalyst optimization
-   Dataset: type-safe (mainly Scala/Java)

### Q2. What is lazy evaluation

Spark builds DAG but executes only on action.

### Q3. Difference between repartition and coalesce

-   repartition: full shuffle
-   coalesce: reduce partitions without shuffle

### Q4. Handling data skew

-   salting keys
-   broadcast joins
-   skew hints

### Q5. Spark performance tuning

-   partition tuning
-   caching
-   predicate pushdown
-   column pruning

------------------------------------------------------------------------

## 4. Data Engineering Concepts

### Q1. ETL vs ELT

-   ETL: transform before loading
-   ELT: load first then transform

### Q2. CDC

Change Data Capture tracks incremental changes using logs or timestamps.

### Q3. Data lake vs warehouse

  Feature   Data Lake        Warehouse
  --------- ---------------- -----------------
  Data      raw              structured
  Storage   cheap            expensive
  Schema    schema-on-read   schema-on-write

### Q4. Ensuring data quality

-   validation rules
-   schema checks
-   anomaly detection

------------------------------------------------------------------------

## 5. System Design Questions

### Q1. Design a real-time data pipeline

Components: - Kafka ingestion - Spark streaming - Storage (S3 /
BigQuery) - BI layer

### Q2. Handle billions of events

-   partition data
-   distributed processing
-   batch + streaming architecture

### Q3. Handling late arriving data

-   watermarking
-   reprocessing windows

------------------------------------------------------------------------

## 6. Behavioral Questions

### Q1. Tell me about yourself

Focus on: - data engineering experience - scale handled - architecture
built

### Q2. Difficult production issue

Explain using STAR format: Situation → Task → Action → Result

### Q3. Why Lloyds?

-   financial data scale
-   modern data platforms
-   engineering culture

------------------------------------------------------------------------

# Additional Preparation Sets

## 30 Common SQL Interview Questions

1.  Find duplicates
2.  Second highest salary
3.  Top N per group
4.  Running total
5.  Window functions
6.  Recursive queries
7.  Pivot tables
8.  JSON extraction
9.  Date calculations
10. Rank within partition
11. Gap detection
12. Sessionization
13. Query optimization
14. Index types
15. Partitioning strategies
16. Data deduplication
17. Self joins
18. Anti joins
19. Merge statements
20. SCD type 2
21. CDC merge logic
22. Generate series
23. Aggregation strategies
24. Distinct vs group by
25. Materialized views
26. Query plans
27. Join order optimization
28. Temporary tables
29. CTE vs subquery
30. Window frame definitions

------------------------------------------------------------------------

## 25 Spark Interview Questions

1.  Spark architecture
2.  DAG execution
3.  Catalyst optimizer
4.  Tungsten engine
5.  Broadcast joins
6.  Shuffle operations
7.  Partition strategies
8.  Data skew solutions
9.  Spark memory model
10. Lazy evaluation
11. Checkpointing
12. Caching vs persistence
13. Structured streaming
14. Watermarking
15. Exactly once processing
16. Fault tolerance
17. Serialization
18. Parquet optimizations
19. Delta Lake basics
20. Spark SQL vs Hive
21. Adaptive query execution
22. Dynamic partition pruning
23. Column pruning
24. Predicate pushdown
25. Spark UI debugging

------------------------------------------------------------------------

## Mock Lloyds Interview

### Round 1

-   SQL joins
-   Python coding
-   Spark fundamentals

### Round 2

-   System design
-   Data pipeline architecture

### Round 3

-   Behavioral
