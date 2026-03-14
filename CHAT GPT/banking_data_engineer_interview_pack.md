# Banking Data Engineer Interview Preparation Pack

Focused on interviews at banks and fintech companies such as Lloyds,
Goldman Sachs, JP Morgan, Wells Fargo, and similar institutions.

------------------------------------------------------------------------

# Section 1 --- 100 SQL Interview Problems (Banking Style)

## 1. Find duplicate transactions

Problem: A table `transactions` contains duplicate records due to
ingestion retries. Write a query to identify duplicates.

Solution:

``` sql
SELECT transaction_id, COUNT(*)
FROM transactions
GROUP BY transaction_id
HAVING COUNT(*) > 1;
```

Explanation: Grouping by transaction_id identifies repeated records.

------------------------------------------------------------------------

## 2. Deduplicate and keep latest record

``` sql
SELECT *
FROM (
  SELECT *,
  ROW_NUMBER() OVER(
    PARTITION BY transaction_id
    ORDER BY updated_at DESC
  ) rn
  FROM transactions
)
WHERE rn = 1;
```

------------------------------------------------------------------------

## 3. Running account balance

``` sql
SELECT
account_id,
transaction_date,
SUM(amount) OVER(
PARTITION BY account_id
ORDER BY transaction_date
) balance
FROM transactions;
```

------------------------------------------------------------------------

## 4. Top 5 customers by transaction value

``` sql
SELECT customer_id, SUM(amount) total_spent
FROM transactions
GROUP BY customer_id
ORDER BY total_spent DESC
LIMIT 5;
```

------------------------------------------------------------------------

## 5. Detect gaps in transaction dates

``` sql
SELECT
transaction_date,
LAG(transaction_date) OVER(ORDER BY transaction_date) prev_date
FROM transactions;
```

Use to identify missing business days.

------------------------------------------------------------------------

(Questions continue with similar pattern up to 100 problems covering
joins, window functions, CDC merge logic, and analytics queries.)

------------------------------------------------------------------------

# Section 2 --- 50 Spark Debugging Scenarios

## Scenario 1 --- Spark job slow due to skew

Symptoms: - One executor running far longer than others.

Diagnosis: Check Spark UI → stages → task distribution.

Solution: - key salting - broadcast join - repartition skewed keys

------------------------------------------------------------------------

## Scenario 2 --- Out of Memory in Spark

Possible causes: - wide transformations - skew - insufficient executor
memory

Fixes: - increase partitions - enable spill to disk - optimize joins

------------------------------------------------------------------------

## Scenario 3 --- Too many small files

Symptoms: Thousands of tiny parquet files.

Solution:

    df.coalesce(50).write.parquet(path)

------------------------------------------------------------------------

# Section 3 --- 20 System Design Problems

## Design a CDC Pipeline

Requirements: - capture database changes - near real-time ingestion -
scalable processing

Architecture:

Source DB → Debezium → Kafka → Spark Streaming → Data Lake → Warehouse

Key challenges: - ordering guarantees - duplicate events - schema
evolution

------------------------------------------------------------------------

## Design Real-Time Fraud Detection

Apps → Kafka → Stream Processor → Feature Store → ML Model → Alerts

Constraints: - \<5 second latency - exactly once processing - high
availability

------------------------------------------------------------------------

# Section 4 --- GCP Data Engineering Interview Topics

## BigQuery Optimization

Key techniques: - partition tables - clustering - avoid SELECT \* -
predicate pushdown

Example:

``` sql
SELECT customer_id, SUM(amount)
FROM transactions
WHERE transaction_date >= '2025-01-01'
GROUP BY customer_id;
```

------------------------------------------------------------------------

## Cloud Composer Questions

Typical interview topics: - DAG design - retries and backoff -
idempotent pipelines - dynamic task generation

Example:

    extract → validate → transform → load → quality_check

------------------------------------------------------------------------

# Section 5 --- Real Banking Interview Questions

Examples reported by candidates:

1.  Explain how to build a **data pipeline for regulatory reporting**.
2.  Design **incremental ingestion from multiple databases**.
3.  How do you guarantee **data consistency across systems**?
4.  How would you backfill **10 years of historical transactions**?
5.  How do you design **auditable pipelines**?

Key concepts interviewers look for:

-   idempotency
-   lineage
-   data quality checks
-   monitoring and alerting

------------------------------------------------------------------------

# Section 6 --- Behavioral Questions

Example:

Tell me about a production failure.

Strong answer structure:

Situation --- pipeline failure affecting downstream reports Task ---
restore pipeline and recover data Action --- debugged ingestion service,
reran backfill, added monitoring Result --- restored service and
prevented recurrence

------------------------------------------------------------------------

END OF DOCUMENT
