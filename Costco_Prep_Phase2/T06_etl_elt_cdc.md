# Topic 6: ETL / ELT / CDC Patterns
## Costco Sr. Data Engineer — Exhaustive Interview Textbook

---

## Table of Contents
1. [L1: Core Concepts — ETL vs ELT Basics](#l1-core-concepts)
2. [L2: Deep Technical Understanding](#l2-deep-technical-understanding)
3. [L3: Real-World Scenarios — Costco/MarTech Style](#l3-real-world-scenarios)
4. [L4: Hands-On Code & Design](#l4-hands-on-code--design)
5. [L5: Edge Cases & Pitfalls](#l5-edge-cases--pitfalls)
6. [L6: Interview Questions — Easy to Very Hard](#l6-interview-questions)

---

## L1: Core Concepts

### 1.1 ETL vs ELT — The Fundamental Architecture Difference

**ETL (Extract → Transform → Load)**:
```
Source DB → [Extract] → [Transform in-flight] → [Load to DWH]
           (pull data)   (Spark/Informatica)    (target schema)
```
- Transformation happens BEFORE loading into the warehouse
- Uses a separate compute layer (Spark, Informatica, custom code)
- Data arrives in the warehouse already clean and structured
- Traditional approach (Informatica, SSIS, DataStage era)

**ELT (Extract → Load → Transform)**:
```
Source DB → [Extract] → [Load raw to DWH] → [Transform inside DWH]
           (pull data)   (raw landing zone)  (SQL/DBT/Spark on DWH)
```
- Raw data lands in the warehouse first, THEN transformed using DWH compute
- The warehouse itself (BigQuery, Snowflake) does the heavy transformation
- Modern approach (enabled by cheap cloud DWH compute)

**Why ELT won in the cloud era**:

| Dimension | ETL | ELT |
|-----------|-----|-----|
| Raw data preserved | No (transformed before landing) | Yes (raw always available for reprocessing) |
| Debugging | Hard (data changed before you see it) | Easy (query raw data directly) |
| Compute cost | Separate compute needed | DWH handles both storage and compute |
| Flexibility | Schema must be defined upfront | Schema-on-read, evolve easily |
| Latency | Can be faster (skip DWH load) | Load first → latency before transform |
| Best for | Low-latency, pre-aggregated feeds | Analytics, BI, ML feature stores |

---

### 1.2 CDC — Change Data Capture Fundamentals

CDC captures the changes (inserts, updates, deletes) happening in a source operational database and propagates them to downstream systems in near-real-time or batch.

**Why CDC matters**:
- Full table extracts for a 100M-row operational table takes hours and hammers the source DB
- CDC extracts only the CHANGES (typically 0.1-1% of total data each run)
- Near-real-time sync (seconds to minutes vs hours for full extract)
- Captures DELETEs (full extract can't detect what was removed)

**Three main CDC approaches**:

| Method | How It Works | Pros | Cons |
|--------|-------------|------|------|
| **Log-based** | Read DB binary/write-ahead log | True real-time, captures DELETEs, zero source DB load | Complex setup, requires DB-level access |
| **Timestamp-based** | Poll for rows where `updated_at > last_run` | Simple, no special DB access | Misses DELETEs, requires reliable timestamp column |
| **Trigger-based** | DB triggers write changes to a shadow table | Captures DELETEs, reliable | High source DB overhead, triggers slow writes |

---

## L2: Deep Technical Understanding

### 2.1 Log-Based CDC — Internals

Every major relational database writes all changes to a transaction log before applying them:
- **PostgreSQL**: WAL (Write-Ahead Log)
- **MySQL**: Binary Log (binlog)
- **SQL Server**: Transaction Log
- **Oracle**: Redo Log

Log-based CDC reads this log, not the tables themselves → zero impact on source DB performance.

```
PostgreSQL WAL:
  LSN 00000001: BEGIN txn_42
  LSN 00000002: INSERT campaigns (id='C001', budget=500)
  LSN 00000003: UPDATE campaigns SET budget=750 WHERE id='C001'
  LSN 00000004: COMMIT txn_42

Debezium reads WAL → publishes to Kafka:
  Topic: mysql.costco.campaigns
  Message 1: {op: "c", after: {id: "C001", budget: 500}}
  Message 2: {op: "u", before: {id: "C001", budget: 500}, after: {id: "C001", budget: 750}}
```

**Debezium CDC Event Schema**:
```json
{
  "schema": {
    "type": "struct",
    "name": "campaigns.Envelope"
  },
  "payload": {
    "op": "u",
    "before": {
      "campaign_id": "C001",
      "daily_budget_usd": 500.0,
      "status": "active",
      "updated_at": 1705276800000
    },
    "after": {
      "campaign_id": "C001",
      "daily_budget_usd": 750.0,
      "status": "active",
      "updated_at": 1705363200000
    },
    "source": {
      "db": "costco_crm",
      "table": "campaigns",
      "ts_ms": 1705363200000,
      "pos": 12345678
    },
    "ts_ms": 1705363210000
  }
}
```

**op codes**:
- `c` = create (INSERT)
- `u` = update (UPDATE)
- `d` = delete (DELETE)
- `r` = read (initial snapshot)

---

### 2.2 Timestamp-Based CDC — Implementation

```python
import datetime
from google.cloud import bigquery, secretmanager
import psycopg2

class TimestampCDC:
    """
    Polls source Postgres DB for rows changed since last run.
    State: stored in BigQuery metadata table.
    """
    
    def __init__(self, source_table: str, bq_target: str, state_table: str):
        self.source_table = source_table
        self.bq_target = bq_target
        self.state_table = state_table
        self.bq = bigquery.Client()
    
    def get_last_run_timestamp(self) -> datetime.datetime:
        """Read last successful run timestamp from state table."""
        result = self.bq.query(f"""
            SELECT MAX(last_processed_at) AS ts
            FROM `{self.state_table}`
            WHERE source_table = '{self.source_table}'
              AND status = 'SUCCESS'
        """).result()
        
        row = list(result)[0]
        return row.ts or datetime.datetime(2020, 1, 1)  # default: very old date
    
    def extract_changed_rows(
        self,
        conn,
        since: datetime.datetime
    ) -> list:
        """Extract rows modified since last run."""
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT *
            FROM {self.source_table}
            WHERE updated_at > %s
            ORDER BY updated_at ASC
        """, (since,))
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    
    def apply_changes(self, changes: list, batch_time: datetime.datetime):
        """
        Apply changed rows to BigQuery using MERGE (upsert).
        Safe to re-run: MERGE is idempotent on primary key.
        """
        if not changes:
            return 0
        
        # Stage in a temp table
        temp_table = f"{self.bq_target}_tmp_{batch_time.strftime('%Y%m%d%H%M%S')}"
        job = self.bq.load_table_from_json(changes, temp_table)
        job.result()
        
        # MERGE into target
        merge_sql = f"""
        MERGE INTO `{self.bq_target}` AS target
        USING `{temp_table}` AS source
        ON target.campaign_id = source.campaign_id
        WHEN MATCHED THEN UPDATE SET
            target.daily_budget_usd = source.daily_budget_usd,
            target.status           = source.status,
            target.updated_at       = source.updated_at
        WHEN NOT MATCHED THEN INSERT (
            campaign_id, daily_budget_usd, status, updated_at
        ) VALUES (
            source.campaign_id, source.daily_budget_usd, source.status, source.updated_at
        )
        """
        self.bq.query(merge_sql).result()
        
        # Cleanup temp table
        self.bq.delete_table(temp_table)
        return len(changes)
    
    def run(self, conn):
        """Full CDC run: extract → apply → record state."""
        run_start = datetime.datetime.utcnow()
        last_run = self.get_last_run_timestamp()
        
        changes = self.extract_changed_rows(conn, since=last_run)
        rows_processed = self.apply_changes(changes, run_start)
        
        # Record success in state table
        self.bq.query(f"""
            INSERT INTO `{self.state_table}`
            VALUES (
                '{self.source_table}',
                '{run_start.isoformat()}',
                {rows_processed},
                'SUCCESS',
                CURRENT_TIMESTAMP()
            )
        """).result()
        
        return rows_processed
```

---

### 2.3 Incremental Processing — Design Patterns

#### 2.3.1 Append-Only Pattern (Immutable Events)

```python
# For event streams where records are NEVER updated after creation
# Examples: click events, impressions, purchase transactions

# Simple approach: track max ID or max timestamp
def incremental_append(spark, source, target, watermark_col='event_id'):
    # Get current max from target
    max_id = spark.read.parquet(target).agg({'event_id': 'max'}).collect()[0][0] or 0
    
    # Extract only new records
    new_data = spark.read.parquet(source).filter(F.col(watermark_col) > max_id)
    
    # Append (no dedup needed — IDs are strictly increasing)
    new_data.write.mode('append').parquet(target)
    
    return new_data.count()

# Risk: if source generates duplicate IDs (retry scenario)
# Mitigation: add dedup by event_id after append, or use MERGE instead
```

#### 2.3.2 Upsert Pattern (Mutable Records)

```python
# For dimension tables where records change (campaigns, products, users)
# Must handle: new records (insert) + changed records (update)

def incremental_upsert_bigquery(
    source_query: str,
    target_table: str,
    unique_key: str,
    update_columns: list
):
    """
    Idempotent upsert using BigQuery MERGE.
    """
    update_set = ',\n        '.join([
        f"target.{col} = source.{col}" for col in update_columns
    ])
    insert_cols = f"source.{unique_key}, " + ', '.join([f"source.{c}" for c in update_columns])
    insert_vals = f"source.{unique_key}, " + ', '.join([f"source.{c}" for c in update_columns])
    
    merge_sql = f"""
    MERGE INTO `{target_table}` AS target
    USING ({source_query}) AS source
    ON target.{unique_key} = source.{unique_key}
    WHEN MATCHED AND (
        {' OR '.join([f'target.{c} != source.{c}' for c in update_columns])}
    ) THEN UPDATE SET
        {update_set},
        target._updated_at = CURRENT_TIMESTAMP()
    WHEN NOT MATCHED THEN INSERT (
        {unique_key}, {', '.join(update_columns)}, _inserted_at
    ) VALUES (
        {insert_vals}, CURRENT_TIMESTAMP()
    )
    """
    
    from google.cloud import bigquery
    bigquery.Client().query(merge_sql).result()
```

#### 2.3.3 SCD Type 2 Pattern — DBT Snapshot Approach

```sql
-- Without DBT, implement SCD2 manually:

-- Step 1: Identify changed records
WITH current_state AS (
    SELECT * FROM dim_campaigns WHERE is_current = TRUE
),

incoming AS (
    SELECT * FROM staged_campaigns_today
),

changed AS (
    SELECT i.*
    FROM incoming i
    JOIN current_state c USING (campaign_id)
    WHERE i.daily_budget_usd != c.daily_budget_usd
       OR i.status != c.status
       OR i.bidding_strategy != c.bidding_strategy
),

new_records AS (
    SELECT i.*
    FROM incoming i
    LEFT JOIN current_state c USING (campaign_id)
    WHERE c.campaign_id IS NULL
)

-- Step 2: Close changed records
UPDATE dim_campaigns
SET valid_to = CURRENT_DATE() - 1,
    is_current = FALSE
WHERE campaign_id IN (SELECT campaign_id FROM changed)
  AND is_current = TRUE;

-- Step 3: Insert new versions + new records
INSERT INTO dim_campaigns
SELECT
    GENERATE_UUID()     AS surrogate_key,
    campaign_id,
    campaign_name,
    daily_budget_usd,
    status,
    bidding_strategy,
    CURRENT_DATE()      AS valid_from,
    NULL                AS valid_to,
    TRUE                AS is_current,
    CURRENT_TIMESTAMP() AS created_at
FROM (
    SELECT * FROM changed
    UNION ALL
    SELECT * FROM new_records
);
```

---

### 2.4 Merge Strategies — Full Comparison

#### Strategy 1: TRUNCATE + INSERT (Full Refresh)

```sql
-- Simplest, most reliable — complete replacement
TRUNCATE TABLE target_table;
INSERT INTO target_table SELECT * FROM source_query;

-- Pros: always correct, simple to reason about
-- Cons: expensive for large tables, brief unavailability during truncate
-- Use for: small dimension tables (< 10M rows), lookup tables, seeds
```

#### Strategy 2: INSERT OVERWRITE by Partition

```sql
-- BigQuery: overwrite specific date partition (idempotent)
INSERT INTO `mart.ad_clicks` PARTITION (click_date = '2024-01-15')
SELECT * FROM staged_clicks WHERE click_date = '2024-01-15';
-- Re-running: overwrites the same partition → same result

-- Pros: idempotent per partition, only touches affected data
-- Cons: partition column must exist, all records in partition must be reprocessed
-- Use for: time-series fact tables, event tables with date partitioning
```

#### Strategy 3: MERGE / UPSERT

```sql
-- Update existing + insert new, in one atomic operation
MERGE INTO target AS t
USING source AS s
ON t.pk = s.pk
WHEN MATCHED THEN UPDATE SET t.col1 = s.col1, t.updated_at = s.updated_at
WHEN NOT MATCHED THEN INSERT VALUES (s.pk, s.col1, s.updated_at)
WHEN NOT MATCHED BY SOURCE THEN DELETE;  -- optional: handle deletes

-- Pros: handles all three operations (insert/update/delete), atomic
-- Cons: slower than INSERT OVERWRITE for large tables (row-by-row comparison)
-- Use for: CDC-sourced tables, mutable dimension tables, slowly changing data
```

#### Strategy 4: DELETE + INSERT

```sql
-- Two-step: delete matching rows then insert all (alternative to MERGE)
-- Step 1: delete rows that will be replaced
DELETE FROM target WHERE pk IN (SELECT pk FROM source);

-- Step 2: insert all source rows
INSERT INTO target SELECT * FROM source;

-- Pros: simpler than MERGE in some databases, works everywhere
-- Cons: not atomic (window between delete and insert where rows are missing)
-- Use for: databases without MERGE support, small batches
```

---

### 2.5 DBT Incremental Models — The ELT Incremental Pattern

```sql
-- DBT makes incremental processing declarative

{{
    config(
        materialized='incremental',
        unique_key='click_id',
        incremental_strategy='merge',     -- or 'insert_overwrite', 'append'
        on_schema_change='append_new_columns',
        partition_by={'field': 'click_date', 'data_type': 'date'},
        cluster_by=['campaign_id']
    )
}}

WITH source AS (
    SELECT
        click_id,
        campaign_id,
        user_id,
        DATE(clicked_at)        AS click_date,
        clicked_at,
        cost_micros / 1e6       AS cost_usd
    FROM {{ source('google_ads', 'raw_clicks') }}

    -- THE KEY: only process new rows during incremental runs
    {% if is_incremental() %}
    WHERE clicked_at >= (
        SELECT TIMESTAMP_SUB(MAX(clicked_at), INTERVAL 3 DAY)
        FROM {{ this }}          -- {{ this }} = the existing target table
    )
    {% endif %}
)

SELECT * FROM source
WHERE click_id IS NOT NULL
```

**DBT incremental strategies on BigQuery**:

| Strategy | When to Use | How it Works |
|----------|-------------|-------------|
| `append` | Immutable events, guaranteed unique IDs | Just INSERTs new rows |
| `merge` | Mutable records, rows can change | MERGE on unique_key |
| `insert_overwrite` | Date-partitioned event tables | Replaces entire partitions |
| `delete+insert` | Alternative to merge | DELETE matching rows, then INSERT |

**The `is_incremental()` lifecycle**:
- First run ever → `is_incremental()` = False → builds from scratch
- Normal run (table exists) → `is_incremental()` = True → only processes new data
- `dbt run --full-refresh` → `is_incremental()` = False → rebuilds from scratch

---

## L3: Real-World Scenarios

### 3.1 Scenario: Building a CDC Pipeline for Costco Member Data

**Context**: Costco member profiles (loyalty tier, address, email) are in a PostgreSQL operational database. MarTech needs near-real-time member data in BigQuery for campaign targeting.

**Architecture**:
```
PostgreSQL (source)
  → Datastream (GCP's managed CDC service — reads WAL)
    → GCS bucket (raw CDC events as Avro files)
      → Dataflow job (parse CDC events, apply SCD2 logic)
        → BigQuery dim_members (SCD2 history table)
```

```python
# Using GCP Datastream for log-based CDC (no Debezium needed on GCP)
# Datastream configuration is done via Console/Terraform:

# terraform/datastream.tf
resource "google_datastream_stream" "members_cdc" {
  stream_id    = "costco-members-cdc"
  display_name = "Costco Members CDC"
  location     = "us-central1"
  
  source_config {
    postgresql_source_config {
      hostname = "costco-crm-db.internal"
      port     = 5432
      username = "datastream_user"
      password = var.db_password
      database = "costco_crm"
      
      include_objects {
        postgresql_schemas {
          schema = "public"
          postgresql_tables {
            table = "members"
            postgresql_columns {
              column = "member_id"
              primary_key = true
            }
          }
        }
      }
    }
  }
  
  destination_config {
    gcs_destination_config {
      path      = "gs://costco-cdc-staging/members/"
      file_rotation_mb  = 100
      file_rotation_interval = "60s"
      avro_file_format {}
    }
  }
}
```

```python
# Dataflow job: process CDC events → apply SCD2 to BigQuery
import apache_beam as beam

class ApplySCD2(beam.DoFn):
    def process(self, cdc_event):
        op = cdc_event['source']['op']  # c=create, u=update, d=delete
        
        if op in ('c', 'r'):  # insert or snapshot
            yield {'action': 'INSERT', 'data': cdc_event['after']}
        elif op == 'u':
            yield {'action': 'CLOSE_AND_INSERT', 
                   'old': cdc_event['before'],
                   'new': cdc_event['after']}
        elif op == 'd':
            yield {'action': 'SOFT_DELETE', 'data': cdc_event['before']}

# Processing logic:
# CLOSE_AND_INSERT → MERGE to close old record + insert new one
# This implements SCD2 without custom state management
```

---

### 3.2 Scenario: Migration Pipeline — CDM Next Style

**Context** (directly from your experience): Migrate 15PB of data across 60+ application teams from on-prem to GCP BigQuery.

**Strategy**:
```
Phase 1: Full historical load (one-time)
    Source → Dataproc Spark → GCS (raw) → BigQuery (partitioned)
    Run in parallel by application team
    Validate: row counts, checksums, sample data comparison

Phase 2: CDC / Delta loads (ongoing sync during cutover window)
    Source → Kafka (capture deltas) → Dataflow → BigQuery
    Catchup period: ensure delta from Phase 1 snapshot applied

Phase 3: Cutover
    Switch application reads to BigQuery
    Maintain source as fallback for N days
    Monitor: query response time, data accuracy

Phase 4: Decommission
    After validation period: shut down source system
```

```python
# Batch migration job: on-prem HDFS → BigQuery via GCS
def migrate_table(
    source_hdfs_path: str,
    gcs_staging: str,
    bq_target: str,
    partition_col: str,
    batch_date: str
):
    """Migrates one day's partition of one table."""
    spark = SparkSession.builder.appName(f"migrate_{bq_target}").getOrCreate()
    
    # Read from HDFS
    df = spark.read.parquet(f"{source_hdfs_path}/dt={batch_date}/")
    
    # Data quality check before writing
    source_count = df.count()
    assert source_count > 0, f"No data for {batch_date}"
    
    # Normalize schema for BigQuery compatibility
    df_clean = (df
        .withColumn("migration_date", F.lit(batch_date).cast("date"))
        .withColumn("migrated_at", F.current_timestamp())
        .dropDuplicates([partition_col])
    )
    
    # Write to GCS staging
    gcs_path = f"{gcs_staging}/{bq_target}/dt={batch_date}/"
    df_clean.write.mode("overwrite").parquet(gcs_path)
    
    # Load GCS → BigQuery
    from google.cloud import bigquery
    bq = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        time_partitioning=bigquery.TimePartitioning(field="migration_date")
    )
    load_job = bq.load_table_from_uri(
        f"{gcs_path}*.parquet",
        f"{bq_target}${batch_date.replace('-','')}",
        job_config=job_config
    )
    load_job.result()
    
    # Validate
    bq_count = list(bq.query(f"SELECT COUNT(*) FROM `{bq_target}` WHERE migration_date = '{batch_date}'").result())[0][0]
    
    if abs(source_count - bq_count) / source_count > 0.001:  # >0.1% mismatch
        raise ValueError(f"Count mismatch: source={source_count}, bq={bq_count}")
    
    return {"source": source_count, "target": bq_count}
```

---

## L4: Hands-On Code & Design

### 4.1 Full ELT Pipeline with DBT and BigQuery

```python
# Orchestration: Cloud Composer DAG for complete ELT pipeline

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator

with DAG('elt_ad_events', schedule='0 2 * * *', ...) as dag:

    # E: Extract (API → GCS)
    extract = BashOperator(
        task_id='extract_google_ads',
        bash_command='python /scripts/extract_google_ads.py --date {{ ds }}'
    )

    # L: Load raw (GCS → BigQuery raw dataset)
    load_raw = GCSToBigQueryOperator(
        task_id='load_raw_to_bq',
        bucket='costco-raw-data',
        source_objects=['google_ads/{{ ds }}/clicks_*.parquet'],
        destination_project_dataset_table='costco.raw.google_ads_clicks${{ ds_nodash }}',
        source_format='PARQUET',
        write_disposition='WRITE_TRUNCATE',  # overwrite partition = idempotent
        autodetect=True
    )

    # T: Transform (DBT)
    transform_staging = BashOperator(
        task_id='dbt_staging',
        bash_command='dbt run --select tag:staging --vars \'{"execution_date": "{{ ds }}"}\''
    )

    test_staging = BashOperator(
        task_id='dbt_test_staging',
        bash_command='dbt test --select tag:staging'
    )

    transform_marts = BashOperator(
        task_id='dbt_marts',
        bash_command='dbt run --select tag:daily'
    )

    test_marts = BashOperator(
        task_id='dbt_test_marts',
        bash_command='dbt test --select tag:daily'
    )

    extract >> load_raw >> transform_staging >> test_staging >> transform_marts >> test_marts
```

---

## L5: Edge Cases & Pitfalls

### 5.1 The Missing Delete Problem in Timestamp CDC

```python
# Problem: timestamp-based CDC cannot detect deletes
# A campaign is deleted in the source DB
# Source: campaign C001 no longer exists
# Your timestamp-based job: WHERE updated_at > last_run
# Result: deleted campaign still exists in BigQuery with stale data

# Solution 1: Soft deletes (source adds is_deleted=TRUE instead of hard delete)
# Your job picks up the change via updated_at

# Solution 2: Full snapshot comparison (periodic)
# Every Sunday: extract ALL source IDs, compare to BigQuery IDs
# IDs in BigQuery but not in source → mark as deleted
def find_deleted_records():
    source_ids = set(db.query("SELECT campaign_id FROM campaigns"))
    bq_ids = set(bq.query("SELECT campaign_id FROM dim_campaigns WHERE is_current=TRUE"))
    deleted = bq_ids - source_ids
    if deleted:
        bq.query(f"""
            UPDATE dim_campaigns
            SET is_deleted = TRUE, valid_to = CURRENT_DATE()
            WHERE campaign_id IN ({','.join([f"'{i}'" for i in deleted])})
        """).result()

# Solution 3: Use log-based CDC (Debezium/Datastream) — captures deletes natively
```

---

### 5.2 Duplicate Records from At-Least-Once CDC

```python
# Problem: CDC event delivered twice (Debezium retry, Kafka redelivery)
# Your pipeline processes the same UPDATE event twice
# Result: SCD2 creates two nearly-identical records with slightly different timestamps

# Solution: idempotency key on CDC events
# Debezium events have: source.pos (log position) + source.ts_ms
# Use these as a composite idempotency key

def is_already_processed(log_pos: int, ts_ms: int) -> bool:
    result = bq.query(f"""
        SELECT COUNT(*) AS cnt
        FROM `pipeline.processed_cdc_events`
        WHERE log_position = {log_pos} AND event_ts_ms = {ts_ms}
    """).result()
    return list(result)[0].cnt > 0

def process_cdc_event(event: dict):
    log_pos = event['source']['pos']
    ts_ms = event['source']['ts_ms']
    
    if is_already_processed(log_pos, ts_ms):
        logger.info(f"Duplicate event at pos={log_pos}, skipping")
        return
    
    apply_to_bigquery(event)
    record_processed(log_pos, ts_ms)
```

---

### 5.3 DBT Incremental Stale Data Bug

```sql
-- DANGEROUS incremental model: uses MAX(updated_at) as watermark
-- Problem: if a batch fails halfway, MAX(updated_at) = partially-processed high-water mark
-- Next run: starts from the wrong position, skips records that didn't complete

{{ config(materialized='incremental') }}

SELECT * FROM source
{% if is_incremental() %}
WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})  -- BUG if run fails
{% endif %}

-- SAFE: use a lookback window instead of exact watermark
{% if is_incremental() %}
WHERE updated_at >= TIMESTAMP_SUB(
    (SELECT MAX(updated_at) FROM {{ this }}),
    INTERVAL 3 DAY   -- process last 3 days every run (handles failures + late data)
)
{% endif %}
-- With INSERT OVERWRITE: safe because partition is replaced, not appended
```

---

### 5.4 Schema Evolution in ELT Pipelines

```python
# Problem: source adds a new column, your pipeline breaks

# Scenario 1: Pipeline reads CSV/JSON → schema validation fails
# Fix: use schema inference with backwards compatibility
df = spark.read \
    .option("mergeSchema", "true") \       # merge new columns
    .parquet("gs://bucket/source/")         # doesn't break on new columns

# Scenario 2: BigQuery table doesn't have the new column
# Fix: use 'on_schema_change' in DBT
{{ config(
    materialized='incremental',
    on_schema_change='append_new_columns'  # adds new cols to target, no error
) }}

# Scenario 3: Column type changed (e.g., INT → BIGINT)
# Requires: schema migration script
bq.query("""
    ALTER TABLE `project.dataset.table`
    ALTER COLUMN amount SET DATA TYPE FLOAT64
""").result()

# Best practice: always version your schemas
# Schema Registry (Confluent) for Kafka/Avro: enforces backwards compatibility
# BigQuery: use schema_update_options on load jobs
```

---

## L6: Interview Questions — Easy to Very Hard

### EASY

**Q1: What is the difference between ETL and ELT?**

**Answer**: ETL (Extract-Transform-Load) extracts data from source, transforms it outside the warehouse using a separate compute layer (Spark, Informatica), then loads the transformed data into the target. ELT (Extract-Load-Transform) extracts and loads raw data into the warehouse first, then uses the warehouse's own compute to transform it.

ELT has become dominant in cloud data engineering because: (1) cloud data warehouses (BigQuery, Snowflake) have massive compute capacity that can handle transformations efficiently; (2) raw data is preserved for debugging and reprocessing; (3) schema-on-read allows flexibility; (4) tools like DBT make the T step declarative and testable. ETL is still valid for: very low-latency streaming, pre-aggregated feeds, or when the warehouse can't handle complex transformations.

---

**Q2: What is CDC and why is it better than full table extracts?**

**Answer**: CDC (Change Data Capture) captures only the changes to a database — inserts, updates, deletes — rather than extracting the entire table each time. For a table with 100M rows where only 10,000 change each day, a full extract processes 100M rows while CDC processes only 10,000 — a 10,000x reduction in data volume. This means: faster pipeline runs, less load on the source database, near-real-time data availability, and the ability to capture deletes (which full extracts can't detect). Log-based CDC reads the database's write-ahead log and adds zero overhead to the source database.

---

### MEDIUM

**Q3: How does a MERGE statement work and when would you use it in a data pipeline?**

**Answer**: MERGE (also called UPSERT) combines INSERT and UPDATE in a single atomic statement. It compares a source dataset to a target table on a join key: if the key exists in both, it updates the target row; if it exists only in the source, it inserts a new row; optionally, if it exists only in the target (deleted from source), it deletes the target row.

Use MERGE in data pipelines when: your source data contains both new records and updates to existing records (e.g., campaign budgets change, member tier updates). It's the standard pattern for CDC-driven dimension tables and DBT incremental models with `incremental_strategy='merge'`. Avoid MERGE for very large tables in BigQuery — on tables of billions of rows, row-level MERGE is much slower than partition-level INSERT OVERWRITE. Choose INSERT OVERWRITE when data is date-partitioned and you're processing whole partitions.

---

**Q4: Your DBT incremental model has been running fine for 3 months. Today it produced 50% fewer rows than expected for yesterday. How do you diagnose it?**

**Answer**:

**Step 1: Check the incremental filter**
The most common cause: the watermark shifted incorrectly.
```sql
-- Check: what MAX(updated_at) does the target table show?
SELECT MAX(updated_at), MAX(click_date) FROM target_table
-- If this shows a wrong high-water mark, the filter excluded valid rows
```

**Step 2: Check source data**
Did the source actually deliver less data, or is it a pipeline issue?
```sql
SELECT COUNT(*) FROM raw_source
WHERE click_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
-- If count here is also low → source data issue (late arrival, upstream failure)
```

**Step 3: Check DBT run logs**
- Did the model run with `--full-refresh` accidentally?
- Was there a schema change that caused the incremental filter to be skipped?
- Did the model fall back to full refresh due to `on_schema_change='fail'`?

**Step 4: Check the is_incremental() filter logic**
If using `WHERE updated_at > MAX(updated_at)` instead of a lookback window, and a batch failed yesterday, today's run might start from a too-recent watermark.

**Fix**: Run `dbt run --select target_model --full-refresh` to rebuild from scratch if the watermark is wrong, then switch to lookback-window-based filtering to prevent recurrence.

---

### HARD

**Q5: Design a CDC pipeline that syncs changes from a PostgreSQL operational database to BigQuery with < 5 minute latency, handles all DML operations (insert/update/delete), and supports point-in-time recovery.**

**Answer**:

**Architecture**:

```
PostgreSQL (WAL enabled, replication slot) 
  → Debezium / GCP Datastream (reads WAL)
    → Pub/Sub topic: db.public.campaigns
      → Dataflow streaming job
        ├── → BigQuery: staging.cdc_campaigns (raw CDC events, append-only)
        └── → BigQuery: dim_campaigns (current state, MERGE applied)
```

**BigQuery design**:

1. **Raw CDC table** (audit/recovery):
```sql
CREATE TABLE staging.cdc_campaigns (
    event_id        STRING,
    op              STRING,         -- c/u/d/r
    before          JSON,
    after           JSON,
    source_ts_ms    INT64,
    processed_at    TIMESTAMP
)
PARTITION BY DATE(processed_at)
CLUSTER BY op;
-- Append-only: never modified, true audit trail
```

2. **Current state table** (queryable):
```sql
CREATE TABLE marts.dim_campaigns (
    campaign_id         STRING,
    campaign_name       STRING,
    daily_budget_usd    FLOAT64,
    status              STRING,
    valid_from          TIMESTAMP,
    valid_to            TIMESTAMP,      -- NULL = current
    is_current          BOOL,
    is_deleted          BOOL
)
PARTITION BY DATE(valid_from)
CLUSTER BY campaign_id;
```

**Point-in-time recovery**: Since all raw CDC events are preserved in `staging.cdc_campaigns`, you can reconstruct the state of any record at any point in time by replaying events in order.

```sql
-- What did campaign C001 look like at 2024-03-15 12:00:00?
WITH events_ordered AS (
    SELECT
        JSON_VALUE(after, '$.campaign_id') AS campaign_id,
        JSON_VALUE(after, '$.daily_budget_usd') AS budget,
        JSON_VALUE(after, '$.status') AS status,
        TIMESTAMP_MILLIS(source_ts_ms) AS event_ts,
        ROW_NUMBER() OVER (ORDER BY source_ts_ms DESC) AS rn
    FROM staging.cdc_campaigns
    WHERE JSON_VALUE(after, '$.campaign_id') = 'C001'
      AND op IN ('c', 'u')
      AND TIMESTAMP_MILLIS(source_ts_ms) <= '2024-03-15 12:00:00'
)
SELECT * FROM events_ordered WHERE rn = 1;
```

**Latency**: Datastream reads WAL continuously → Pub/Sub delivers in < 1s → Dataflow streaming processes in < 30s → BigQuery streaming insert available in < 5s. Total: well under 5 minutes, typically under 60 seconds.

---

### VERY HARD

**Q6: You're designing the incremental load strategy for a 50TB dimension table (product catalog) that receives 5M updates per day out of 500M total records. The current full-refresh approach takes 8 hours and is causing a daily 8-hour data gap. Design a solution that reduces latency to < 30 minutes with zero data loss.**

**What they're testing**: Deep understanding of CDC, incremental patterns, tradeoffs at scale.

**Answer**:

**Problem analysis**:
- 50TB table, full refresh = 8 hours → unacceptable
- 5M updates/day = 1% of 500M records
- Goal: < 30 min latency, zero data loss

**Step 1: Enable CDC on the source**

Set up Datastream to read the PostgreSQL WAL for the products table. This captures all 5M daily changes as a stream of events rather than requiring a full table scan.

**Step 2: Redesign the BigQuery table for incremental updates**

```sql
-- Partition by update_date (not product_id — too high cardinality)
-- Cluster by product_id for fast MERGE lookups
CREATE TABLE `marts.dim_products`
PARTITION BY DATE(last_updated_date)
CLUSTER BY product_id, category_id
OPTIONS (partition_expiration_days = NULL);  -- never expire
```

**Step 3: Micro-batch incremental updates every 5 minutes**

Instead of daily full refresh, apply CDC events every 5 minutes via MERGE:

```python
def apply_product_cdc_batch(events: list[dict]):
    """Process a micro-batch of CDC events — runs every 5 minutes."""
    
    # Load events to a temp table
    temp_table = f"staging.tmp_products_{int(time.time())}"
    bq.load_table_from_json(events, temp_table).result()
    
    # Classify: inserts, updates, deletes
    bq.query(f"""
    MERGE `marts.dim_products` AS target
    USING (
        SELECT 
            after.product_id,
            after.name,
            after.price,
            after.category_id,
            after.is_active,
            TIMESTAMP_MILLIS(source_ts_ms)  AS last_updated_ts,
            DATE(TIMESTAMP_MILLIS(source_ts_ms)) AS last_updated_date,
            op
        FROM `{temp_table}`
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY after.product_id 
            ORDER BY source_ts_ms DESC
        ) = 1   -- latest op per product in this micro-batch
    ) AS source
    ON target.product_id = source.product_id
    WHEN MATCHED AND source.op IN ('u', 'c') THEN UPDATE SET
        target.name = source.name,
        target.price = source.price,
        target.is_active = source.is_active,
        target.last_updated_ts = source.last_updated_ts,
        target.last_updated_date = source.last_updated_date
    WHEN NOT MATCHED AND source.op IN ('c', 'r') THEN INSERT (
        product_id, name, price, category_id, is_active, last_updated_ts, last_updated_date
    ) VALUES (
        source.product_id, source.name, source.price, source.category_id,
        source.is_active, source.last_updated_ts, source.last_updated_date
    )
    WHEN MATCHED AND source.op = 'd' THEN UPDATE SET
        target.is_active = FALSE,
        target.deleted_at = source.last_updated_ts
    """).result()
    
    bq.delete_table(temp_table)

# Orchestrate every 5 minutes via Cloud Scheduler → Cloud Function → this code
```

**Step 4: Initial load (one-time)**
For the first run: use Dataproc Spark to read the full 50TB table in parallel, write to BigQuery. Takes ~4 hours but is a one-time operation.

**Step 5: Validation**
```python
# Every hour: compare source record count to BigQuery record count
# Alert if drift > 0.01%
source_count = db.query("SELECT COUNT(*) FROM products WHERE is_active=TRUE").fetchone()[0]
bq_count = bq.query("SELECT COUNT(*) FROM dim_products WHERE is_active=TRUE").result()
drift = abs(source_count - bq_count) / source_count
if drift > 0.0001:
    alert(f"Product catalog drift: {drift:.4%}")
```

**Result**:
- Data latency: 5 minutes (micro-batch) vs 8 hours (full refresh)
- Data processed per run: 5M changes × ~500 bytes = 2.5GB vs 50TB
- Cost: ~95% reduction in compute
- Zero data loss: CDC preserves all events, idempotent MERGE handles retries

---

## Summary: ETL/ELT/CDC — Senior Mastery Checklist

| Skill | What Senior Looks Like |
|-------|------------------------|
| ETL vs ELT | Clear decision framework; knows when each is appropriate |
| Log-based CDC | Understands WAL, Debezium event schema, op codes |
| Timestamp CDC | Implements with state management; knows limitations (no deletes) |
| MERGE/UPSERT | Writes production-grade MERGE with conditional updates |
| SCD Type 2 | Can implement open/close pattern manually or via DBT snapshot |
| DBT incremental | Knows all strategies; uses lookback window not exact watermark |
| Schema evolution | Handles new columns, type changes without breaking pipelines |
| Idempotency | Every load pattern is safe to retry |
| Scale | Designs CDC for 50TB+ tables; understands micro-batch tradeoffs |
| Debugging | Can diagnose missing rows, duplicate records, stale data |
