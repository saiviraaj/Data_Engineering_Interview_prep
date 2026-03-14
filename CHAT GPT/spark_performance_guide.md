# Spark Performance and Internals Guide

## Spark Execution Model

Spark builds a DAG of transformations which are divided into stages
separated by shuffles.

Execution flow:

Driver → DAG Scheduler → Task Scheduler → Executors

------------------------------------------------------------------------

## Key Performance Techniques

### Partitioning

Correct partitioning improves parallelism.

Example

``` python
df.repartition(200)
```

### Broadcast Join

``` python
from pyspark.sql.functions import broadcast

df.join(broadcast(dim_table),"id")
```

Use when one table \< 10MB.

------------------------------------------------------------------------

## Adaptive Query Execution

Spark dynamically optimizes queries at runtime.

Benefits

-   skew handling
-   better join strategy
-   dynamic partition pruning

------------------------------------------------------------------------

## Spark Memory Model

Memory split between:

-   execution memory
-   storage memory

Tune with

    spark.executor.memory
    spark.memory.fraction
