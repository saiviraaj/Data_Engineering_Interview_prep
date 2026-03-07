# Scalable Architecture & System Design — Exhaustive Interview Q&A
### Tailored for Senior Data Engineer with CDM Next / GCP Background

---

## SECTION 1: ARCHITECTURAL PATTERNS

**Q1. Compare Lambda and Kappa architectures. Which would you use and when?**

Lambda architecture uses two parallel paths: a batch layer that processes the full historical dataset with high accuracy but high latency, and a speed layer that processes only the most recent data in real-time but with potentially lower accuracy. A serving layer merges both views to answer queries.

Kappa simplifies this by using only a streaming pipeline for both real-time and historical processing. Historical reprocessing is done by replaying events from Kafka or Pub/Sub with updated code.

My decision framework: if you genuinely need both exactly-correct historical results and real-time data simultaneously, and the processing logic can reasonably be duplicated, Lambda is appropriate. If your use case is stream-first and historical reprocessing is rare and the logic is manageable as a stream, Kappa is simpler and more maintainable. The industry trend is toward Kappa because maintaining two codebases for the same logic doubles operational burden. In CDM Next, we effectively used a Kappa-like approach: our batch migrations used the same transformation logic as the streaming Kafka pipeline — one framework, two intake points.

---

**Q2. What is the Medallion architecture and how did you implement it in CDM Next?**

Medallion architecture organises data into quality tiers — Bronze (raw), Silver (cleaned), Gold (curated). Each layer has a specific purpose and quality contract.

Bronze holds an exact, immutable copy of source data — no transformations. This is critical because if a transformation bug is discovered months later, you can reprocess from Bronze without going back to the source system. In CDM Next, Bronze was data as extracted from Teradata/Oracle/Hive, landed as Parquet files in GCS, partitioned by source system and extraction date.

Silver is cleaned and standardised: nulls handled, types corrected, PII masked by Cloud DLP, deduplication applied. In CDM Next, this was our BigQuery staging dataset — join-ready but without business logic.

Gold is the business layer: dimensional model applied, aggregations computed, optimised for query performance with partitioning and clustering. This was what the 60+ application teams actually consumed. They got consistent, governed data without needing to understand source system complexity.

The key value: each layer's quality contract is explicit. Issues in Gold trace cleanly to Silver or Bronze — you always know which layer introduced a problem.

---

**Q3. What is the difference between batch, micro-batch, and streaming processing? When is each appropriate?**

**Batch:** Process a large, bounded dataset all at once. Typical cadence: daily, hourly. Latency from event to result: minutes to hours. Efficient for large volumes, simple to reason about. Use when: SLA allows data to be hours old, data arrives in bulk, historical reprocessing is common.

**Micro-batch:** Process small batches on a short, fixed schedule (every 30 seconds, every 1 minute). Spark Structured Streaming default. Latency: seconds to minutes. Trade-off: looks like streaming to end users but simpler to implement than true streaming. Use when: low latency desired but true event-by-event processing isn't needed.

**Streaming:** Process each event as it arrives. Latency: milliseconds to seconds. Handles windowing, late data, stateful operations. Most complex to implement and operate. Use when: real-time fraud detection, live dashboards, operational alerting where seconds matter.

In CDM Next: batch was right for most migrations (run nightly, replace partition). We used streaming for Kafka sources where the application team needed near-real-time data availability.

---

**Q4. Explain Change Data Capture (CDC) and when you would use it.**

CDC captures every row-level change (INSERT, UPDATE, DELETE) from a database's transaction log, rather than querying the table directly. Instead of asking "give me all rows where updated_at > yesterday," CDC says "here is every change that happened, in order."

Benefits: much lower source system load (reads the log, not the table), near-real-time latency (seconds vs hours), captures deletes (which watermark-based incremental loading misses), provides a complete audit trail.

On GCP, Datastream is the managed CDC service — it reads Oracle redo logs, MySQL/PostgreSQL WAL, and delivers changes as a stream to BigQuery or GCS.

I would use CDC when: (1) the source system is a regulated financial database where every change must be captured for audit; (2) the source table has no reliable updated_at column (can't do watermark-based incremental); (3) latency requirements are minutes rather than hours; (4) the source database can't handle full-table extract load.

In CDM Next, we used CDC via Datastream for Oracle sources where auditors required complete change history, not just the current state.

---

**Q5. What are the tradeoffs between ELT and ETL?**

ETL (Extract, Transform, Load): transform data before loading into the warehouse. Traditional approach — required because old warehouses had limited compute; you couldn't afford to transform inside them.

ELT (Extract, Load, Transform): load raw data first, then transform inside the warehouse using SQL. Modern cloud warehouses (BigQuery, Snowflake) have near-infinite compute — transforming inside BigQuery using SQL is often faster and cheaper than running an external Spark job.

ELT advantages: raw data preserved (Bronze layer), transformation logic in SQL (accessible to more people), no separate transformation infrastructure, warehouse optimiser can optimise across the full pipeline.

ETL advantages: compute happens outside the warehouse (saves warehouse costs for cheap filtering), can use Python logic that's difficult in SQL, better for PII — data can be masked before it ever touches the warehouse.

In CDM Next: we used ELT for most pipelines — land in GCS (Bronze), load to BigQuery staging, transform via SQL inside BigQuery. We used ETL only for PII handling — Cloud DLP masking happened before data entered any BigQuery dataset.

---

## SECTION 2: GCP ARCHITECTURE

**Q6. How would you design a data platform for a new business unit on GCP from scratch?**

I'd follow the architecture we built in CDM Next, adapted for a greenfield build:

**Ingestion layer:** Cloud Composer orchestrates batch ingestion DAGs. Datastream for CDC sources. Pub/Sub + Dataflow for streaming sources.

**Storage:** Three-tier Medallion in GCS (Bronze) and BigQuery (Silver/Gold). BigQuery tables partitioned by date, clustered by most common filter columns.

**Processing:** BigQuery SQL for most transforms (ELT pattern). Dataproc for complex PySpark transformations or ML feature engineering.

**Security:** Separate GCP projects for dev/staging/prod. IAM with least privilege — analysts get Data Viewer, not Editor. VPC Service Controls for data perimeter. Secret Manager for all credentials. Cloud DLP for PII detection and masking. Column-level security tags on sensitive fields.

**Governance:** Dataplex for unified catalog across datasets. Lineage tracking in a custom audit table. Schema registry in BigQuery. Data quality checks as part of every pipeline.

**Observability:** Pipeline audit table written by every job. Cloud Monitoring dashboards. Alerting on failures, freshness, and anomalies. Costs tracked per team via labels.

I'd start with one pilot use case, get the patterns right, then templatise for other teams — exactly the CDM Next approach.

---

**Q7. When would you choose Bigtable over BigQuery?**

Bigtable is a wide-column NoSQL database designed for high-throughput, low-latency key-based access. BigQuery is a columnar analytical database designed for complex SQL queries over large datasets.

Choose Bigtable when: (1) latency requirement is milliseconds — Bigtable serves row reads in < 10ms, BigQuery takes 0.5–3 seconds just to start; (2) write throughput is very high — millions of writes per second (IoT telemetry, financial tick data, application event logs); (3) access pattern is key-based — you know the row key and need that specific row; (4) data is time-series — Bigtable's wide-column model is perfect for metrics over time.

Choose BigQuery when: (1) you need SQL analytics and aggregations; (2) ad-hoc queries with arbitrary filter combinations; (3) data needs to be joined with other datasets; (4) analysts need to query it directly.

In CDM Next's real-time fraud detection component: Bigtable stored the enrichment data (customer profiles, account history) that the fraud scoring pipeline looked up at < 10ms latency per transaction. BigQuery stored the full transaction history for the analytics team to query. Two different tools, two different access patterns.

---

**Q8. How do you design for exactly-once processing in a streaming pipeline?**

Exactly-once means each event is processed and has its effect precisely once — not zero times (data loss), not two or more times (duplicates). It requires guarantees at two levels: message delivery and state updates.

**At the messaging layer:** Pub/Sub provides at-least-once delivery — messages may be delivered multiple times. To achieve exactly-once, the consumer must be idempotent.

**At the processing layer:** Dataflow (Apache Beam) provides exactly-once semantics through: (1) checkpointing — state is periodically persisted; on failure, replay resumes from the last checkpoint, not from the beginning; (2) idempotent writes — output is written with a deduplication key; the sink (BigQuery, Bigtable) rejects duplicate writes with the same key.

**At the sink layer:** BigQuery's streaming insert deduplication uses `insertId` — within a best-effort window, BQ deduplicates rows with the same insertId. For stronger guarantees, use batch loads with partition overwrite — writing to a partition is atomic and idempotent.

In CDM Next's Kafka streaming pipeline: we wrote to BigQuery using the batch load approach within micro-windows — accumulate 60 seconds of messages, write as a batch load to a partition, use the batch ID as the idempotency key. Replaying a failed window overwrites the same partition, not appends.

---

**Q9. Describe the Pub/Sub fan-out pattern and when you'd use it.**

Fan-out means one Pub/Sub topic has multiple subscriptions, and each subscription receives every message independently. This allows the same data to feed multiple downstream systems simultaneously, each processing it differently.

Example: a `transactions` topic fans out to:
- Subscription 1 → Dataflow fraud scoring pipeline
- Subscription 2 → Dataflow BigQuery load pipeline  
- Subscription 3 → Dataflow real-time aggregation pipeline
- Subscription 4 → Cloud Functions for operational alerts

Each subscriber processes at its own pace, with its own retry logic and backpressure. The topic acts as a buffer.

Use fan-out when: the same raw event stream needs to feed multiple systems (analytics + fraud + operations + archival), you want to decouple producers from consumers, you want to add a new consumer without touching the producer. The key benefit is operational independence — if the fraud pipeline is down, the BQ load pipeline is unaffected.

---

## SECTION 3: MIGRATION DESIGN

**Q10. How would you design a migration from Teradata to BigQuery for a 10TB table with 5 years of history?**

This is a specific scenario from CDM Next — I'd follow our proven approach:

**Step 1 — Assessment:** Profile the table: row count, schema, data types, partition strategy in TD, query patterns, downstream consumers, SLA.

**Step 2 — Schema translation:** Map TD types to BQ types. Key gotchas: DECIMAL(18,4) → NUMERIC for financial data (not FLOAT64 — precision matters in banking). PERIOD(DATE) → split into start_date and end_date columns. MULTISET → requires explicit deduplication in BigQuery.

**Step 3 — Phased historical migration:** Migrate year by year to manageable batch sizes. Each year: extract from TD → land as Parquet in GCS → load to BQ staging → validate → promote to prod. Use partition overwrite for idempotency. Compress data in transit.

**Step 4 — Delta sync:** Once historical is loaded, switch to incremental mode using the watermark column. Run daily, syncing only changed rows.

**Step 5 — Parallel validation (2 weeks):** Run the same set of business queries against both TD and BQ. Compare results. Engage the application team to sign off on data correctness.

**Step 6 — Cutover:** Update application connection string to point to BigQuery. Keep TD in read-only for 30 days as rollback option. Monitor BQ query performance for the first week.

**Step 7 — Decommission:** Remove TD table after sign-off.

Total elapsed time for a 10TB table at CDM Next: typically 2–4 weeks including validation and stakeholder sign-off.

---

**Q11. How do you handle a migration where the source system cannot be taken offline?**

You never take the source offline in CDM Next — these are production banking systems. The approach:

**Parallel run strategy:** Migrate historical data while the source keeps running. Use a watermark (updated_at or a CDC stream) to capture ongoing changes. The target BigQuery table catches up to the source through incremental loads.

**Convergence check:** The target is "caught up" when the lag between source changes and target ingestion is within the SLA window (e.g., < 1 hour). At this point you're ready to cut over applications.

**Zero-downtime cutover:** Switch applications from source to target one at a time. Start with read-only consumers (reports, dashboards) — lower risk. Last to switch: write-path consumers. If any issue: switch back immediately.

**Rollback safety net:** Keep source table in read-only mode for 30 days after cutover. If a bug is found, applications can be pointed back to source while BigQuery is corrected.

The confidence comes from running both systems in parallel long enough that you trust the target completely before any consumer is switched.

---

**Q12. How do you validate data after a migration?**

Validation is multi-layered in CDM Next — we never considered a migration "done" without passing all validation gates:

**Level 1 — Row count reconciliation:** Total rows in source vs target must match within tolerance (0.01% allowed for known data type conversion edge cases). This runs automatically as a DAG task.

**Level 2 — Financial checksums:** SUM of all numeric columns must match exactly after rounding to the precision of the BigQuery type. For financial tables: `SUM(CAST(amount AS BIGNUMERIC))` must be equal. Any discrepancy fails the migration.

**Level 3 — Statistical profiling:** Compare MIN, MAX, AVG, STDDEV, null rate for all numeric columns between source and target. Anomalies flag potential type conversion issues.

**Level 4 — Business query comparison:** Run the 10 most common business queries against both TD and BigQuery. Compare result sets. This is run by or with the application team — they're the true owners of what "correct" means.

**Level 5 — Sample comparison:** Pull a random 0.01% sample and compare row-by-row. Catches edge cases that aggregate checks miss.

All validation results are written to the CDM Next audit table. A migration advances to production only when all validation gates are GREEN.

---

## SECTION 4: SCALABILITY AND COST

**Q13. How do you design a BigQuery table for a 1 billion row/day financial transactions workload?**

```sql
CREATE TABLE transactions (
    transaction_id   STRING    NOT NULL,
    account_id       STRING    NOT NULL,
    transaction_date DATE      NOT NULL,   -- partition column
    transaction_ts   TIMESTAMP,
    transaction_type STRING,               -- DEBIT | CREDIT | TRANSFER
    amount           NUMERIC,              -- NOT FLOAT64 — financial precision
    currency         STRING,
    status           STRING,
    counterparty_id  STRING
)
PARTITION BY transaction_date
CLUSTER BY account_id, transaction_type
OPTIONS (
    partition_expiration_days = 2555,       -- 7-year regulatory retention
    require_partition_filter  = TRUE        -- force all queries to filter by date
);
```

Key decisions:
- **NUMERIC not FLOAT64:** Financial amounts require exact decimal precision. FLOAT64 has rounding errors.
- **Partition by date:** Most queries filter by date range. 1B rows/day × 365 days = 365B rows. Without partitioning, every query scans all of it.
- **Cluster by account_id, transaction_type:** Most queries filter on one or both. Reduces bytes scanned within a partition by 30–50%.
- **require_partition_filter = TRUE:** At 1B rows/day, an accidental full scan costs hundreds of dollars per query. This option hard-blocks unfiltered queries.
- **7-year retention:** Regulatory requirement for financial transaction records in most jurisdictions.

---

**Q14. Your BigQuery bill jumped 300% this month. How do you investigate and fix it?**

Systematic investigation:

**Step 1 — Identify what changed:**
```sql
-- Find most expensive queries this month vs last month
SELECT user_email, SUM(total_bytes_processed) / POW(1024,4) AS tb_scanned
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE DATE(creation_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY user_email ORDER BY tb_scanned DESC;
```

**Step 2 — Find queries without partition pruning:**
```sql
SELECT query, total_bytes_processed / POW(1024,3) AS gb
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE DATE(creation_time) >= CURRENT_DATE()
  AND total_bytes_processed > 10 * POW(1024,3)  -- > 10 GB
ORDER BY total_bytes_processed DESC;
```

**Step 3 — Check for SELECT * or missing filters:** Review the top 20 most expensive queries for missing partition filters, SELECT *, or accidental cross joins.

**Step 4 — Identify new consumers:** New dashboard tools, new pipelines, new team onboarded?

**Fix approaches:**
- Add `require_partition_filter` to large tables
- Replace `SELECT *` with specific columns
- Add partition filters to queries missing them
- Create materialised views for repeated expensive queries
- Set per-user or per-project custom quotas
- Implement query review process for new queries above a cost threshold

---

**Q15. How would you handle backfilling 3 years of historical data when a pipeline had a bug for 3 months?**

This is a real scenario — CDM Next had this happen. The approach:

**Step 1 — Define the blast radius:** Which partitions are affected? Which downstream tables depend on this data?

**Step 2 — Fix and test the bug:** The fix must be validated on a sample of the affected data before running at scale.

**Step 3 — Design the backfill job:**
- Identify the affected date range (e.g., 2023-10-01 to 2023-12-31)
- Process partitions in reverse chronological order (most recent first — provides fastest business value)
- Use partition overwrite — rewrite each date's partition with corrected data
- Idempotent by design: running twice produces the same result

**Step 4 — Run safely:**
- Use a separate slot reservation to avoid impacting live pipelines
- Process in batches of 30 days at a time — easier to monitor and resume
- Write corrected data to a staging dataset first, validate, then overwrite production

**Step 5 — Notify stakeholders:**
- Alert downstream teams that data is being corrected
- Provide before/after comparison for key metrics
- Update audit table with backfill metadata

**Step 6 — Prevent recurrence:**
- Add regression test that would have caught the bug
- Improve monitoring to detect this class of data quality issue proactively

---

## SECTION 5: OBSERVABILITY AND RELIABILITY

**Q16. How do you monitor a data pipeline end-to-end?**

Monitoring a pipeline requires multiple perspectives:

**Infrastructure monitoring (Cloud Monitoring):**
- Composer DAG success/failure rates
- Dataflow job throughput and latency
- BigQuery slot utilisation
- GCS storage growth rate

**Data monitoring (pipeline audit table):**
- Every pipeline run writes a record: start, end, rows extracted, rows loaded, rows rejected, status, error
- Query this table to: identify failing pipelines, track data volume trends, calculate SLA compliance, alert on anomalies

**Data quality monitoring:**
- Row count comparison source vs target
- Null rate monitoring — alert if null rate > threshold for key columns
- Statistical drift detection — compare daily averages to 30-day baseline
- Freshness monitoring — alert if table not updated within SLA window

**Business-level monitoring:**
- Downstream teams can see their data freshness on a self-service dashboard
- Revenue reconciliation: BigQuery totals match source system totals daily

In CDM Next, we built a single observability dashboard per application team showing: last successful run time, rows loaded today, any validation failures, and a green/yellow/red health status. Teams could self-diagnose without filing tickets with the platform team.

---

**Q17. How do you design an alerting system that avoids alert fatigue?**

Alert fatigue happens when too many alerts fire, operators start ignoring them, and real incidents get missed. The solution is tiered alerting with clear severity definitions.

Three tiers that worked in CDM Next:

**Tier 1 — Immediate, page on-call:** Reserved for: production pipeline failed after all retries exhausted; data freshness breach (critical table not updated in > 26 hours); row count anomaly > 20% from baseline; security/compliance violation. These are true incidents requiring immediate human action.

**Tier 2 — Business hours notification:** Pipeline slower than 2x normal duration; slot utilisation warning; schema drift detected; non-critical pipeline failure (retries still in progress). These need attention but can wait for business hours.

**Tier 3 — Daily digest:** Cost trends; storage growth; summary of all pipeline outcomes. Informational — no action needed unless trends continue.

Key principles: (1) every alert must have a runbook — what do you do when it fires? Alerts without actions are noise; (2) review alert thresholds quarterly — a threshold calibrated in January may be wrong in July as data volumes grow; (3) measure alert quality — if an alert fires and the answer is "nothing wrong, threshold too sensitive," fix the threshold; (4) suppress during known maintenance windows.

---

*End of Scalable Architecture & System Design Q&A*
