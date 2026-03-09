# Data Governance, Quality & Observability — Exhaustive Interview Q&A

---

**Q1. What are the dimensions of data quality and how do you measure each?**

There are seven dimensions I work with: Completeness (null rates per column), Accuracy (reconciliation against source of truth), Consistency (cross-system comparison — BigQuery totals match Teradata), Timeliness (hours since last update vs SLA), Uniqueness (duplicate rate on primary keys), Validity (value range, format, allowed-value checks), and Referential Integrity (orphaned foreign key counts). Each has a SQL metric and an alert threshold. In CDM Next, every migration pipeline emitted scores for all seven dimensions into a quality metrics table, so teams had a self-service quality dashboard per table.

---

**Q2. How did you handle PII in CDM Next?**

PII protection was layered across the pipeline. At extraction, we ran Cloud DLP against sample data from every source table to automatically identify sensitive columns — SSNs, account numbers, dates of birth. Those columns were tagged in the schema registry. During transformation, DLP masking was applied before data landed in BigQuery: SSNs tokenised, card numbers masked, names pseudonymised for non-production environments. At rest, column-level security tags in BigQuery meant analysts couldn't see raw PII values without explicit IAM grants. Row-level security isolated team data so Finance couldn't see Risk data even if they shared a table. Audit logs captured every data access event. The net result: raw PII never existed in BigQuery in plaintext in any environment.

---

**Q3. What is column-level security in BigQuery and how does it work?**

Column-level security in BigQuery is implemented via policy tags managed in Dataplex's Policy Tag Manager. You create a taxonomy of sensitive categories (PII > Name, PII > SSN, Financial > AccountNo), then tag specific columns with those policy tags via the BigQuery metadata API. Once tagged, only principals granted the `Fine-Grained Reader` IAM binding on that specific policy tag can see the column values. Anyone else — even with BigQuery Data Viewer on the table — sees NULL for that column in their query results. The key benefit: same table, same query, different results based on the requester's IAM permissions. You don't need separate tables for different access levels.

---

**Q4. How do you detect and respond to data quality anomalies automatically?**

Detection runs at three levels. First, row-count monitoring: after every pipeline run, compare today's row count to a 7-day rolling average. A ratio below 0.5 or above 2.0 triggers a VOLUME_DROP or VOLUME_SPIKE alert. Second, statistical drift: compare today's mean and standard deviation for key numeric columns to the 30-day baseline. A z-score above 3 signals a potential data issue. Third, SQL-based quality checks run as Airflow tasks after each load: null rate checks, duplicate checks, referential integrity checks. Each check writes a PASS/FAIL result to the quality metrics table. If any critical check fails, the Airflow task fails, which blocks downstream DAG tasks from running — the pipeline self-quarantines until the issue is resolved.

---

**Q5. What is a data contract and why are they important?**

A data contract is a formal agreement between a data producer and its consumers, specifying the schema, quality guarantees, freshness SLAs, and notification procedures for breaking changes. It's the data equivalent of an API contract. Without contracts, schema changes in a source table silently break downstream dashboards and ML models — the producer doesn't know who depends on them, and consumers don't know changes are coming. With contracts: producers commit to 14 days' notice for breaking changes, consumers can register as dependents, and the CI/CD pipeline validates that any proposed schema change doesn't violate existing contracts before deployment. In CDM Next, data contracts were the formal handshake between the platform team and the 60+ application teams consuming migrated data.

---

**Q6. Explain data lineage and how you implemented it in CDM Next.**

Data lineage tracks where data came from, how it was transformed, and where it flows to — the complete provenance of every record. In CDM Next, we implemented two layers: automatic and custom. For automatic lineage, Dataplex captures lineage for all BigQuery SQL jobs and Dataflow pipelines without any instrumentation — you get a visual lineage graph for every BigQuery table. For custom lineage, every CDM Next pipeline wrote a record to `governance.pipeline_lineage` at completion: source system, source table, target table, transformation description, columns mapped, run metadata. This custom table enabled two critical use cases: forward impact analysis (if we change column X in source, which 15 downstream tables are affected?) and backward traceability (this risk metric in a report traces back through 4 tables to the Oracle core banking system). Regulators frequently asked for the latter.

---

**Q7. How do you ensure data quality in a streaming pipeline vs a batch pipeline?**

Batch pipelines: validate after the batch is complete. Run all quality checks as a blocking Airflow task before promoting data from staging to production. Rollback is straightforward — if quality fails, don't overwrite the production partition.

Streaming pipelines: quality is more complex because you can't wait for a batch to complete. Three approaches: (1) Row-level validation at ingest — validate each event as it arrives in Dataflow; route invalid events to a dead letter topic for analysis rather than dropping them; (2) Micro-window aggregation checks — after each 5-minute window lands in BigQuery, run lightweight quality assertions (null rate, count anomaly); trigger alerts but don't halt the stream; (3) Late-arriving reconciliation — at end-of-day, compare streaming table row counts to the source system's daily total; alert if discrepancy exceeds threshold. The key difference: streaming pipelines can't easily roll back, so the response is detect-and-alert rather than detect-and-fail.

---

**Q8. How do you implement data governance for a multi-tenant platform with 60+ teams?**

The hub-and-spoke model: a central platform team owns the governance infrastructure, but day-to-day governance is delegated to data owners in each business unit.

Infrastructure (hub): VPC Service Controls perimeter around all data services; Cloud DLP scanning on all ingestion pipelines; Dataplex catalog for unified discovery; centralised audit logging to a shared BigQuery dataset; schema registry.

Business unit isolation (spokes): each team gets a dedicated BigQuery dataset; IAM is set at dataset level — only the team's service accounts and user groups have access; row-level security if teams share tables; column-level security tags on sensitive fields regardless of which team's dataset.

Governance delegation: each dataset has a designated data owner who approves access requests; changes to IAM policies go through a pull request in the governance repo, reviewed by the data owner; the platform team reviews and approves structural changes (new datasets, VPC SC policy changes).

Self-service with guardrails: teams can query their own data freely; they can't modify IAM on other teams' datasets; they can't bypass DLP masking; they can request cross-team access through a formal process that creates an authorised view.

---

**Q9. What is VPC Service Controls and when did you use it in CDM Next?**

VPC Service Controls (VPC SC) creates a logical security perimeter around GCP API services. Even if an attacker obtains valid GCP credentials, they cannot exfiltrate data outside the perimeter because API calls from outside allowed IP ranges are blocked. Inside the perimeter: BigQuery, GCS, Dataflow, Composer, Secret Manager, Cloud DLP. Outside the perimeter (blocked): any request from a non-corporate IP, any attempt to copy data to an external project.

In CDM Next, VPC SC was mandatory because we handled regulated financial data. Scenarios it protected against: a developer's laptop compromised → attacker can't query BigQuery from an unknown IP; accidental public bucket creation → GCS still blocks external access even if bucket ACL is misconfigured; a rogue pipeline trying to copy data to a personal project → cross-project data movement blocked by perimeter.

The challenge we solved: source systems (Teradata, Oracle) were on-premises. We connected them via Cloud Interconnect (private dedicated connection, not public internet) so data moved directly into the VPC SC perimeter without ever traversing the public internet.

---

**Q10. What is the difference between data masking and data tokenisation?**

Both protect sensitive values, but with different reversibility properties. Masking replaces a value with a fixed representation: credit card 4111-1111-1111-1111 becomes ****-****-****-1111. It's irreversible — you can never recover the original from the masked value. Masking is appropriate when downstream consumers genuinely don't need the full value (analysts seeing masked card numbers for UI display).

Tokenisation replaces a value with a random token: customer_id C001 → TOKEN_7f3a9b2c. A secure vault maps token → original value. It's reversible — authorised systems can retrieve the original by presenting the token to the vault. Tokenisation is appropriate when referential integrity must be preserved (join tables on customer_id across systems) while still protecting the actual identifier. In CDM Next, we tokenised customer identifiers using Cloud KMS-backed tokenisation — downstream analytical queries could join on the token, but the real customer_id was never exposed in BigQuery.

---

**Q11. How do you handle the GDPR right to erasure in a data warehouse?**

Right to erasure ("right to be forgotten") is challenging in data warehouses because they're append-only and history-preserving by design. The standard approach for BigQuery:

Step 1: Never store real customer identifiers — tokenise at ingestion (customer_id → token in vault).

Step 2: When erasure is requested, delete the token-to-original mapping from the vault. All records containing that token are now effectively anonymised — no one can reverse-map the token to the individual.

Step 3: If required to fully purge the data (not just anonymise): use BigQuery's DML DELETE statement to remove rows with the specific token, then the Time Travel window (7 days) expires and the data is permanently gone. Use table snapshots for anything requiring longer rollback before deleting.

Step 4: Document the erasure in an audit trail: timestamp, token identifier, which tables were affected.

The key architectural requirement: you must have tokenised at ingestion. If raw PII is stored in BigQuery, erasure requires finding and deleting it from every partition of every table it appears in — extremely expensive and error-prone.

---

*End of Data Governance, Quality & Observability Q&A*
