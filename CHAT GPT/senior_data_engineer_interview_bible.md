# Senior Data Engineer Interview Bible

Comprehensive preparation guide for Senior / Staff Data Engineer roles.

------------------------------------------------------------------------

# PART 1 --- Advanced SQL

## Deduplication using Window Functions

``` sql
SELECT *
FROM (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY transaction_id
               ORDER BY updated_at DESC
           ) AS rn
    FROM transactions
)
WHERE rn = 1;
```

Explanation: - PARTITION groups duplicate records - ROW_NUMBER ranks
them - rn=1 keeps latest record

------------------------------------------------------------------------

## Top N per Category

``` sql
SELECT *
FROM (
  SELECT category,
         product,
         sales,
         RANK() OVER(
           PARTITION BY category
           ORDER BY sales DESC
         ) r
  FROM product_sales
)
WHERE r <= 3;
```

------------------------------------------------------------------------

## Running Totals

``` sql
SELECT
date,
SUM(amount) OVER(
ORDER BY date
ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
) running_total
FROM transactions;
```

------------------------------------------------------------------------

# PART 2 --- Python for Data Engineers

## Flatten Nested JSON

``` python
def flatten_json(data, parent_key="", sep="_"):
    items = []
    for k, v in data.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_json(v, new_key).items())
        else:
            items.append((new_key, v))
    return dict(items)
```

------------------------------------------------------------------------

# PART 3 --- PySpark Architecture

Driver → DAG Scheduler → Task Scheduler → Executors

Key concepts: - Lazy evaluation - Partition-based processing - Fault
tolerance via lineage

------------------------------------------------------------------------

## Handling Data Skew

``` python
from pyspark.sql.functions import rand

df = df.withColumn("salt", rand())
```

Broadcast join example:

``` python
from pyspark.sql.functions import broadcast

df.join(broadcast(dim_table),"id")
```

------------------------------------------------------------------------

# PART 4 --- Spark Performance Tuning

Common issues: - Too many small files - Large shuffle stages - Skewed
partitions

Solutions: - Repartitioning - Broadcast joins - File compaction

------------------------------------------------------------------------

# PART 5 --- BigQuery Best Practices

Example partitioned table

``` sql
CREATE TABLE sales
PARTITION BY DATE(order_timestamp)
CLUSTER BY customer_id
AS
SELECT *
FROM raw_sales;
```

Benefits: - Reduced scan cost - Faster queries

------------------------------------------------------------------------

# PART 6 --- Airflow / Composer

Best practices: - Idempotent tasks - Retries with exponential backoff -
Observability and alerting

Example pipeline:

extract → stage → transform → load → validate

------------------------------------------------------------------------

# PART 7 --- Data Engineering System Design

Example: Real-time fraud detection pipeline

Apps → Kafka → Spark Streaming → Feature Store → Model → Alerts

Key considerations: - exactly once processing - schema evolution -
monitoring

------------------------------------------------------------------------

# PART 8 --- Data Modeling

Star schema

FactSales \| sale_id \| product_id \| customer_id \| amount \|

DimProduct \| product_id \| product_name \| category \|

Benefits: - Fast BI queries - Simple joins

------------------------------------------------------------------------

# PART 9 --- Troubleshooting Scenarios

Spark job suddenly slow:

Steps: 1. Check Spark UI 2. Investigate shuffle size 3. Identify skewed
partitions 4. Verify cluster resources

------------------------------------------------------------------------

# PART 10 --- Behavioral Questions

Use STAR framework

Situation → Task → Action → Result

Example: Pipeline failure affecting regulatory reporting.

Actions: - identified root cause - ran backfill - implemented monitoring

Result: - restored pipeline - prevented recurrence

------------------------------------------------------------------------

# END
