# Cloud Data Platform — GCP Deep Dive — Exhaustive Interview Q&A

---

**Q1. How does BigQuery store data and why does this matter for query performance?**

BigQuery stores data in Capacitor — a proprietary columnar format on top of GCP's Colossus distributed file system. Columnar storage means each column is stored separately, physically co-located on disk. A query that reads 5 columns from a 200-column table only touches 2.5% of the physical storage — the other 197 columns are never read.

This has two major performance implications. First, `SELECT *` is expensive in BigQuery: it reads every column. In a data platform serving 60+ teams, I always enforced column selection in production queries via code review and query analysis. Second, different columns have very different compression ratios — integers compress far better than strings, and columns with low cardinality (like `status` with values ACTIVE/INACTIVE) compress extremely well. BigQuery applies per-column compression automatically.

The query engine (Dremel) also distributes execution across thousands of workers simultaneously — there's no single machine bottleneck. A query over a 10 TB table and a query over a 100 TB table don't differ as much in wall clock time as you'd expect from a traditional database, because each adds more parallel workers. Understanding this helps set accurate performance expectations with stakeholders.

---

**Q2. Explain BigQuery partitioning and clustering. When does each help?**

Partitioning divides a table into separate physical segments, usually by date. BigQuery reads only the partitions that match the query's filter. The benefit: a 100 TB table partitioned by day — a query with `WHERE order_date = '2024-01-15'` reads only that day's data, perhaps 274 GB. Without partitioning: 100 TB scanned, 365x more expensive. Partitioning is the highest-impact optimisation in BigQuery.

Clustering sorts the data within each partition by specified column values and records the byte range for each column value block. A query filtering on a clustered column can skip blocks that don't contain matching values. The benefit is 30–50% reduction in bytes scanned within a partition, but it works on top of partitioning, not instead of it.

When to use each: partitioning — almost always, for any table over 1 GB with a natural date column and date-based query patterns. Clustering — for the columns most frequently used in WHERE clauses and JOIN conditions beyond the partition column. In CDM Next, every production table was partitioned by date and clustered by the most common business filter columns (account_id, transaction_type, region).

The practical rule: if a query uses `WHERE date = X`, partitioning saves you; if it uses `WHERE date = X AND account_id = Y`, both partitioning and clustering save you.

---

**Q3. How does the Airflow `execution_date` work and why does it matter?**

The `execution_date` in Airflow is the start of the scheduling interval the DAG run represents — not the actual time the run executes. For a DAG with `schedule_interval='0 2 * * *'` (runs at 2 AM), the run that actually starts at 2024-01-16 02:00 UTC has `execution_date = 2024-01-15`. The execution_date represents the day the data covers, not the day the job ran.

This matters enormously for data processing. When you write a BigQuery query inside an Airflow task and use `{{ ds }}` (the execution_date formatted as YYYY-MM-DD), you correctly process yesterday's data. If you use `CURRENT_DATE()` or `datetime.now()` instead, your query always processes today's data regardless of execution_date — making backfills impossible.

Correct pattern: `WHERE order_date = '{{ ds }}'` — this processes the correct date both in normal runs and in backfills. Wrong pattern: `WHERE order_date = CURRENT_DATE() - 1` — this always processes yesterday from now, not from the execution_date.

In CDM Next, we had a CI check that scanned DAG files for `CURRENT_DATE`, `datetime.now()`, and `date.today()` calls inside operator SQL — any use failed the PR unless explicitly justified in a comment. This prevented a whole class of backfill bugs.

---

**Q4. When would you choose Dataflow over Dataproc for a data pipeline?**

Both process data at scale, but they have different strengths.

Choose Dataflow when: the workload is streaming or requires streaming + batch in one framework. Dataflow (Apache Beam) handles both with the same code. It provides exactly-once processing semantics, windowing, watermarks, and late data handling that Dataproc/Spark doesn't match. Dataflow is also fully managed — no cluster provisioning, auto-scaling, and pay-per-processing-second. For a new pipeline with no existing Spark code, Dataflow is usually the right choice on GCP.

Choose Dataproc when: you have existing PySpark or Hadoop code to migrate — Dataproc runs it without rewriting. The CDM Next migration from Hadoop used Dataproc Serverless: we took existing Hive/Spark jobs, pointed them at GCS instead of HDFS, and ran them on Dataproc with minimal changes. Dataproc also supports Delta Lake and Apache Iceberg natively, which Dataflow doesn't. For ML feature engineering where the data science team writes PySpark and needs GPU nodes, Dataproc is the better fit.

In CDM Next: Dataflow for new streaming pipelines (Kafka → BigQuery real-time); Dataproc Serverless for migrating existing Hadoop batch workloads.

---

**Q5. Explain BigQuery slot reservations and when you would use them.**

Slots are units of BigQuery compute. On-demand pricing gives you access to slots as needed but with no guarantees — during peak usage, your queries may queue. You're billed per TB scanned.

Slot reservations let you commit to a fixed number of slots, billed per slot-hour (much cheaper than on-demand at high volumes). Your committed slots are always available, with no queuing. You can create multiple reservations, assign BigQuery projects or folders to each, and set priorities between them.

In CDM Next we had three reservations: a `migration-prod` pool of 500 slots for production migration jobs (high priority, always available), a `migration-dev` pool of 100 flex slots for development workloads (lower priority, preemptible), and we left ad-hoc analyst queries on on-demand so they didn't consume committed slots.

The decision to commit to slots: if your BigQuery spend on on-demand is predictable and consistently above ~$X/month, slots are cheaper. For CDM Next with 15+ PB of data being migrated on a schedule, our daily query volumes were very predictable — commitments saved approximately 40% compared to on-demand pricing.

---

**Q6. How does Cloud Composer differ between version 1 and version 2, and which would you use?**

Composer 1 ran on a GKE Standard cluster that you managed to some degree — you chose node counts, machine types, and managed upgrades. It used CeleryExecutor with a fixed worker pool.

Composer 2 runs on GKE Autopilot — Google manages all node infrastructure. It uses KubernetesExecutor by default: each task runs in its own isolated pod, which starts fresh and terminates on completion. This eliminates noisy-neighbour problems (one task consuming all memory doesn't affect others). Composer 2 also supports Airflow 2.x features: multiple schedulers for HA, task groups, dynamic task mapping.

I would use Composer 2 exclusively for new deployments. The per-task isolation model makes resource management predictable. The HA scheduler (two scheduler replicas by default) means a scheduler crash doesn't halt all running DAGs. For CDM Next's production workload — 60+ teams, hundreds of daily DAG runs — Composer 2's reliability and isolation were critical.

---

**Q7. How do you trigger a Dataflow job from Cloud Composer and monitor it?**

```python
# Option 1: DataflowTemplatedJobStartOperator (Flex Templates)
from airflow.providers.google.cloud.operators.dataflow import DataflowTemplatedJobStartOperator

run_pipeline = DataflowTemplatedJobStartOperator(
    task_id='run_dataflow_migration',
    template='gs://wf-cdm-templates/migration-template',
    parameters={'source': 'CUSTOMER_MASTER', 'date': '{{ ds }}'},
    environment={'maxWorkers': 20},
    wait_until_finished=True  # block until job completes (or fails)
)
```

With `wait_until_finished=True`, Airflow polls the Dataflow job status and fails the task if the Dataflow job fails — the failure propagates correctly through the DAG.

Monitoring: Dataflow jobs appear in the GCP Console under Dataflow → Jobs. Logs are in Cloud Logging (filter by Dataflow job ID). Metrics — bytes processed, elements processed, system lag for streaming — appear in Cloud Monitoring. In CDM Next, we wrote Dataflow job completion events to the pipeline_audit table (via a callback Cloud Function triggered by Dataflow job completion PubSub notifications), giving us a single view of all pipeline activity regardless of whether they ran on Composer, Dataflow, or Dataproc.

---

**Q8. What is Datastream and how does it differ from a scheduled batch extract?**

Datastream is GCP's managed Change Data Capture service. It reads the transaction log of a source database (Oracle redo logs, MySQL/PostgreSQL WAL, SQL Server change tracking) and delivers a continuous stream of INSERT, UPDATE, and DELETE events to BigQuery, GCS, or Pub/Sub.

The fundamental difference from scheduled batch extract: a batch extract takes a snapshot — "give me all rows where updated_at > yesterday." It misses deletes (deleted rows don't appear in the table), requires a reliable updated_at column (not all tables have one), runs on a schedule (latency is at least one batch cycle), and puts periodic load on the source database.

Datastream captures every change as it happens: latency under one minute, captures deletes as explicit DELETE events, requires no updated_at column (it reads the log), and puts minimal load on the source (log reads don't impact query performance).

When I used Datastream in CDM Next: Oracle financial tables where regulators required a complete audit trail of every balance change, not just current state. A batch extract would give current balances; Datastream gave every change with timestamps — exactly what a Basel III BCBS 239 audit requires.

---

**Q9. How do you handle a BigQuery load job failure in the middle of a batch?**

BigQuery load jobs are atomic: a load job either fully succeeds or fully fails. There's no partial commit — if a job fails midway, no rows are written. This is actually the correct behaviour for idempotency.

The recovery strategy depends on write disposition. With `WRITE_TRUNCATE` (partition overwrite): simply retry the load job. It will overwrite the partition, producing the same result as the original. Safe to retry unlimited times. With `WRITE_APPEND`: retrying could duplicate data. Never use WRITE_APPEND for load jobs — always use WRITE_TRUNCATE to a partition or a staging table followed by MERGE.

In Airflow: the Dataflow/BigQuery operators have built-in retry logic. For load jobs specifically, I set `retries=3` with `retry_delay=timedelta(minutes=5)`. The retry is safe because we use partition overwrite. The Airflow task writes the actual completion status (SUCCESS/FAILED) to the audit table on every attempt, so I can see whether the first attempt failed and the retry succeeded.

---

**Q10. Explain the difference between Cloud Functions and Cloud Run. When would you use each for a data pipeline?**

Cloud Functions: event-driven, single-purpose functions. Triggered by events: GCS file arrival, Pub/Sub message, HTTP request, Cloud Scheduler. Maximum execution time: 9 minutes (1st gen) or 60 minutes (2nd gen). Scales to zero, billed per invocation. No containers to build — you deploy Python/Node/Java code directly.

Cloud Run: containerised services. Can be triggered by HTTP, Pub/Sub, or run on a schedule. No execution time limit. Full container control (dependencies, system libraries). Scales to zero, billed per request-second.

For data pipelines: Cloud Functions for lightweight, event-driven triggers — trigger a Composer DAG when a file lands in GCS, send a Slack notification on pipeline failure, run a quick data quality check after a load. I used Cloud Functions in CDM Next as the "glue" between GCS events and Airflow: a file arrives → Cloud Function triggers the right DAG via the Airflow REST API → Airflow orchestrates the full pipeline.

Cloud Run for heavier, longer-running tasks: a custom Oracle CDC consumer that runs continuously (not event-driven), a data validation service with complex dependencies, or a migration job that takes 30 minutes (beyond Functions timeout). Cloud Run also allows you to use custom system libraries (Oracle client libraries) that aren't available in the Functions environment.

---

**Q11. How do you use BigQuery's Time Travel feature and what are its limits?**

Time Travel allows you to query data as it existed at any point within the last 7 days.

```sql
-- Query as of a specific time
SELECT * FROM dataset.orders
FOR SYSTEM_TIME AS OF '2024-01-15 14:00:00 UTC';

-- Query as of N hours ago
SELECT * FROM dataset.orders
FOR SYSTEM_TIME AS OF TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 6 HOUR);

-- Restore accidentally deleted data
CREATE OR REPLACE TABLE dataset.orders AS
SELECT * FROM dataset.orders
FOR SYSTEM_TIME AS OF '2024-01-14 23:59:59 UTC';
```

Practical uses in CDM Next: recovering from accidental table truncation (happened once when a backfill DAG was pointed at prod instead of staging — Time Travel restored the table in under 10 minutes); comparing today's data to yesterday's for anomaly investigation; creating point-in-time snapshots for regulatory purposes.

Limits: 7 days maximum. After 7 days, the historical data is garbage collected. For longer-term recovery capability, use Table Snapshots — they're cheap (differential storage, you only pay for changed blocks), can be taken at specific times, and persist until you delete them. In CDM Next, we took weekly Table Snapshots of all production dimension tables and retained them for 90 days.

---

*End of GCP Deep Dive Q&A*
