# Data Pipeline Engineering & ETL/ELT — Exhaustive Interview Q&A

---

**Q1. Walk me through how you would design a production-grade data pipeline from scratch.**

I follow a consistent five-layer design whenever I build a pipeline from scratch.

First, I clarify requirements: What is the source system type (database, API, file, stream)? What is the expected data volume and change frequency? What is the latency SLA — does the business need this data in 30 minutes or 24 hours? Who consumes it and in what form? Are there regulatory constraints?

Second, I design the ingestion approach: batch extraction for databases using a watermark column, CDC via Datastream if the source is Oracle/PostgreSQL and we need real-time or audit-complete history, file ingestion for flat files landed in GCS.

Third, I design the staging layer: raw data always lands in GCS first as Parquet — immutable, partitioned by extraction date. This is the Bronze layer. Never write directly to the production BigQuery table from a pipeline.

Fourth, I define the validation gates: row count reconciliation against source, schema validation, PII detection via Cloud DLP, null rate and range checks. Any validation failure stops the pipeline and routes to a dead letter or quarantine path.

Fifth, the load pattern: partition overwrite for daily batch loads (idempotent), MERGE for dimension tables with upsert semantics. All orchestrated by Cloud Composer with retries, SLA monitoring, and an audit record written on every run regardless of outcome.

This is the exact pattern CDM Next used for 60+ application teams across 15+ PB.

---

**Q2. What is idempotency and why is it critical in data pipelines?**

An idempotent pipeline produces the same result whether it runs once or ten times. It is critical because pipelines fail — network issues, upstream delays, transient errors — and when they're retried, you must not end up with duplicate data.

The non-idempotent antipattern is appending rows on every run. If a pipeline loads today's orders and is retried after a partial failure, you get two copies of today's orders. At scale this breaks every downstream report.

The idempotent approach in BigQuery: use partition overwrite. Write today's data to a staging table with `WRITE_TRUNCATE`, then overwrite the production partition. Re-running replaces, never appends. For dimension tables with MERGE, an upsert on primary key is inherently idempotent: inserting an existing row updates it, not duplicates it.

In CDM Next every pipeline was partition-overwrite by default. The idempotency property meant backfills were trivially safe: you could re-run any date's partition and it would produce the correct, deduplicated result.

---

**Q3. How do you implement incremental loading and what are the risks?**

Incremental loading means processing only rows that changed since the last run, tracked via a watermark — typically the `MAX(updated_at)` from the last successful run.

Implementation: persist the last watermark in a `pipeline_watermarks` table in BigQuery. On the next run, query the source for `WHERE updated_at > last_watermark`. After successful load, update the watermark to the current run's `MAX(updated_at)`.

Risks and mitigations: First, if the source table has no reliable `updated_at` column, incremental loading doesn't work — you need CDC or full reload. Second, late-arriving data: records updated after your extraction window but before your watermark move to the next cycle; this is acceptable for most use cases but not for financial reconciliation. Third, watermark drift: if a source has clock skew across nodes, some records may be missed; add a small overlap buffer (re-process the last 2 hours of the previous run's window). Fourth, the first run must be a full load — handle this branch explicitly. In CDM Next we always had a `last_watermark IS NULL` path that triggered a full historical extraction.

---

**Q4. Explain the ETL vs ELT decision and when you'd choose each.**

ETL: extract from source, transform using external compute (Spark, Python, Dataflow), then load the transformed data into the warehouse. The transformation happens outside the target system.

ELT: extract, load raw data into the warehouse, then transform using the warehouse's own compute (SQL in BigQuery). The warehouse does the heavy lifting.

ELT is the dominant pattern for modern cloud warehouses because BigQuery has effectively unlimited compute available via slots. Running a SQL transform inside BigQuery is faster and cheaper than spinning up a Dataproc cluster to do the same thing. ELT also preserves raw data — analysts can see what arrived from the source, which builds trust.

When I'd still choose ETL: PII masking must happen before data enters BigQuery, so Cloud DLP masking runs as part of the extraction step — that is ETL. Complex Python logic that cannot be expressed in SQL (advanced ML feature engineering, text processing, calling external APIs) — Dataflow or Dataproc. When the source data is so voluminous and so dirty that filtering it before loading is significantly cheaper.

In CDM Next we used what I'd call ELTT: Extract, Light Transform (type coercion + PII masking), Load to staging, Transform in BigQuery SQL. The best of both.

---

**Q5. How do you design a pipeline that can handle schema changes from the source?**

Schema changes are inevitable — source teams add columns, rename fields, change types. A resilient pipeline must handle them without breaking.

Strategy: maintain a schema registry table that stores the expected schema for each source. Before extraction, compare the actual source schema against the registry. Classify the change:

Non-breaking changes (safe to auto-handle): new nullable column added → add column to BigQuery target automatically, populate with NULL for historical records. Column dropped from source → keep column in BigQuery, populate with NULL going forward.

Breaking changes (require intervention): column renamed (data loss risk — is it a rename or a new column plus drop?); type changed in an incompatible way (STRING → DATE); primary key column dropped. These fail the pipeline and trigger an alert. The source team and data owner must coordinate a fix.

In CDM Next we had a `schema_drift_detector` task that ran before every extraction. Non-breaking drifts were auto-resolved with a BigQuery `ALTER TABLE ADD COLUMN`. Breaking drifts sent a Slack alert to the owning team with the before/after diff and blocked the pipeline until a human reviewed it.

---

**Q6. How does Airflow's scheduler work and what is the `execution_date`?**

Airflow uses a concept of `execution_date` which can be confusing: it is not the date the DAG ran, but the start of the scheduling interval it represents. For a DAG with `schedule_interval='0 2 * * *'` (runs at 2 AM), the run at 2024-01-16 02:00 has `execution_date = 2024-01-15` — the day it covers, not the day it ran.

This matters for data processing: when your task needs to process yesterday's data, use `{{ ds }}` (the execution_date as a string) not `CURRENT_DATE()`. Using `CURRENT_DATE()` inside a DAG makes it impossible to backfill correctly — a backfill of Jan 1 through Jan 10 would always process today's data, not historical.

The scheduler evaluates DAGs based on `start_date` and `schedule_interval`. With `catchup=True`, it will create backfill runs for all missed intervals since `start_date`. I always set `catchup=False` in CDM Next and trigger backfills explicitly when needed — automated catchup on a data migration platform could flood the Teradata extract layer.

---

**Q7. What is the dead letter queue pattern and how did you use it?**

A dead letter queue (DLQ) is a secondary queue or table where messages/records that fail processing are routed instead of being dropped or causing the pipeline to halt.

The pattern: for each record, attempt processing. If it fails with a non-retryable error (validation failure, schema mismatch, unparseable data), write the record plus error metadata (error type, message, timestamp, pipeline name, retry count) to the DLQ — a Pub/Sub topic or a BigQuery quarantine table. Continue processing the rest of the batch without halting.

Benefits: no data loss; failed records are available for analysis and manual reprocessing; the main pipeline continues operating; you can alert on DLQ growth without triggering a full pipeline failure.

In CDM Next we had a `cdm_quarantine` BigQuery table. Every pipeline routed invalid records there. A daily report showed quarantine counts per pipeline — a spike indicated a source-system data quality issue upstream. Operations team could inspect quarantined records, fix the root cause, and reprocess from the quarantine table with a single Airflow backfill.

---

**Q8. How do you implement a backfill strategy when a pipeline had a bug for 2 months?**

When a production bug corrupts or loses data for a historical window, backfilling must be surgical and safe.

Step 1 — Fix and validate the bug. Run the corrected pipeline against a sample of the affected date range in a staging environment. Verify the output is correct before touching production.

Step 2 — Define the blast radius. Which exact date partitions are affected? Which downstream tables depend on this table? Notify owners of all downstream tables that a backfill is running.

Step 3 — Design for idempotency. Because we use partition overwrite, re-running any day's pipeline replaces that day's partition atomically. The backfill is risk-free in terms of duplication.

Step 4 — Execute in batches. Don't backfill 60 days in one Airflow run. Process 7 days at a time, validate each week before continuing. Process most recent dates first — provides business value fastest.

Step 5 — Separate slot reservation. Run the backfill using a dedicated BigQuery slot reservation so it doesn't impact live production pipelines.

Step 6 — Close the loop. Write a post-mortem: what caused the bug, what monitoring should have caught it, what regression test now covers it.

In CDM Next we backfilled a 3-month Teradata migration gap caused by a watermark logic bug. The process took 4 days of careful, monitored execution. No production queries were impacted because we used a separate slot reservation.

---

**Q9. How do you test a data pipeline?**

Three levels of testing, run in CI/CD before any deployment.

Unit tests test individual functions in isolation. The extract function is tested with a mock database connection — verify it builds the correct SQL for first-run vs incremental. The transform function is tested with known input data — verify the output matches expectations. The validation function is tested with edge cases — zero rows, all-null column, type mismatch.

Integration tests test component interactions with real (or near-real) infrastructure. Use BigQuery sandbox datasets. Verify that a GCS → BigQuery load job actually creates the correct schema. Verify that a MERGE statement handles upsert correctly with a 10-row test dataset.

DAG tests verify Airflow DAG structure without executing tasks. `DagBag` import checks catch syntax errors. Dependency chain tests verify that merge runs after validation. Trigger rule tests verify that audit runs on all_done even when upstream fails.

End-to-end tests run the full pipeline against a small representative dataset in a dev environment. Expensive to run but verify the complete flow works.

In CDM Next, unit and DAG tests ran on every PR in 2 minutes. Integration tests ran nightly. E2E tests ran weekly.

---

**Q10. Explain Cloud Composer vs self-managed Airflow. What are the operational differences?**

Self-managed Airflow: you provision and manage the scheduler, workers, webserver, and metadata database (typically PostgreSQL) yourself on GKE or VMs. Full control but full operational burden: upgrades, HA configuration, scaling worker pools, backup of the metadata database.

Cloud Composer (managed Airflow): Google manages the infrastructure. You provide DAGs (in GCS), plugins, Python packages. Composer handles scheduler HA, worker scaling, upgrades, and the metadata database.

Key Composer advantages: HA scheduler is built-in (multiple scheduler replicas — Airflow 2 feature). Native GCP integration — BigQuery, Dataflow, GCS operators use GCP credentials automatically. Automatic integration with Cloud Logging and Cloud Monitoring. VPC-native deployment stays inside the security perimeter.

Key Composer considerations: higher cost than self-managed (you pay for the managed infrastructure). Composer environment startup takes 15–30 minutes to provision. Package installation requires rebuilding the environment (slower iteration loop). Version upgrades are done by Google on a schedule.

In CDM Next we used Composer 2 with autopilot workers. For a platform serving 60+ teams with strict reliability requirements, the reduced operational overhead was worth the cost premium. The platform team couldn't afford to be oncall for Airflow infrastructure issues on top of pipeline issues.

---

*End of Data Pipeline Engineering & ETL/ELT Q&A*
