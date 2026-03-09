# Cloud Data Platform — GCP Deep Dive — Complete Textbook
### BigQuery, Composer, Dataflow, Dataproc, Pub/Sub, and the Full GCP Data Stack

---

## CHAPTER 1: BIGQUERY ARCHITECTURE

### 1.1 How BigQuery Works Internally

BigQuery is a serverless, columnar, distributed analytical database. Understanding its internals helps you write faster, cheaper queries.

```
STORAGE LAYER (Colossus — GCP distributed file system)
  Data stored in Capacitor format (proprietary columnar format)
  Columns stored separately → reading 3 columns from 100-column table
  reads only 3% of data physically
  Data automatically compressed per column type
  Data replicated across multiple datacenters automatically

QUERY ENGINE (Dremel)
  Massively parallel query execution
  A query is decomposed into a tree of tasks
  Thousands of workers execute simultaneously
  No single machine bottleneck — scales with data size

SHUFFLE SERVICE
  Moves data between Dremel workers during joins and aggregations
  Proprietary high-speed network layer
  Explains why BigQuery joins are fast: shuffle is optimised

SLOT
  A unit of BigQuery compute (CPU + memory + I/O)
  Queries consume slots; more complex queries need more slots
  On-demand: auto-allocated based on query demand
  Reserved: committed slots in your reservation
```

### 1.2 Partitioning

Partitioning divides a table into segments so queries can skip irrelevant segments.

```sql
-- DATE/TIMESTAMP partitioning (most common)
CREATE TABLE orders (
    order_id    STRING,
    order_date  DATE,
    amount      NUMERIC
)
PARTITION BY order_date;

-- Queries with WHERE order_date = '2024-01-15' only scan that day's partition
-- Without partitioning: scan entire table

-- INGESTION TIME partitioning (use when no date column exists)
CREATE TABLE events (
    event_id  STRING,
    payload   JSON
)
PARTITION BY _PARTITIONDATE;
-- Partitioned by the date the row was inserted

-- INTEGER RANGE partitioning
CREATE TABLE customer_segments (
    customer_id   INT64,
    segment_score INT64
)
PARTITION BY RANGE_BUCKET(segment_score, GENERATE_ARRAY(0, 100, 10));
-- Partitions: 0-10, 10-20, ..., 90-100

-- Partition expiration: auto-delete old partitions
CREATE TABLE orders (...)
PARTITION BY order_date
OPTIONS (partition_expiration_days = 2555);  -- 7 years

-- require_partition_filter: block unfiltered queries on large tables
CREATE TABLE large_events (...)
PARTITION BY event_date
OPTIONS (require_partition_filter = TRUE);
-- SELECT * FROM large_events → ERROR (must provide date filter)
```

### 1.3 Clustering

Clustering sorts data within each partition by specified column(s). BigQuery skips blocks that don't match the filter.

```sql
-- Create a clustered + partitioned table
CREATE TABLE transactions (
    transaction_id  STRING,
    transaction_date DATE,
    account_id      STRING,
    transaction_type STRING,
    amount          NUMERIC
)
PARTITION BY transaction_date
CLUSTER BY account_id, transaction_type;

-- This query benefits from BOTH partition pruning AND clustering:
SELECT SUM(amount)
FROM transactions
WHERE transaction_date = '2024-01-15'   -- partition pruning
  AND account_id = 'ACC001234'           -- clustering benefit
  AND transaction_type = 'DEBIT';        -- clustering benefit

-- Cluster column order matters:
-- account_id, transaction_type → queries filtering on account_id benefit
-- queries filtering on transaction_type alone don't benefit as much
-- Put your most selective filter column first
```

### 1.4 Query Optimisation

```sql
-- BAD: full table scan (no partition filter)
SELECT * FROM transactions WHERE account_id = 'ACC001';

-- GOOD: partition filter + column selection
SELECT transaction_id, amount, transaction_type
FROM transactions
WHERE transaction_date BETWEEN '2024-01-01' AND '2024-01-31'
  AND account_id = 'ACC001';

-- BAD: SELECT * in a 200-column table reads all columns
SELECT * FROM wide_table;

-- GOOD: only read needed columns (columnar storage = massive savings)
SELECT col1, col2, col3 FROM wide_table;

-- BAD: calling a function on a partition column kills pruning
SELECT * FROM transactions
WHERE DATE(transaction_ts) = '2024-01-15';  -- function on column = no pruning

-- GOOD: direct comparison on partition column
SELECT * FROM transactions
WHERE transaction_ts >= '2024-01-15 00:00:00'
  AND transaction_ts <  '2024-01-16 00:00:00';

-- Use APPROX functions for exploration (100x faster, < 1% error)
SELECT APPROX_COUNT_DISTINCT(account_id) FROM transactions;  -- fast
SELECT COUNT(DISTINCT account_id)         FROM transactions;  -- slow (exact)

-- Use INFORMATION_SCHEMA to understand query costs before running
SELECT total_bytes_processed / POW(1024,4) AS tb_estimated
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE job_id = '<your_job_id>';
```

### 1.5 Materialised Views

```sql
-- Precompute expensive aggregations
CREATE MATERIALISED VIEW daily_account_summary AS
SELECT
    transaction_date,
    account_id,
    transaction_type,
    COUNT(*)          AS transaction_count,
    SUM(amount)       AS total_amount,
    AVG(amount)       AS avg_amount
FROM transactions
GROUP BY 1, 2, 3;

-- BigQuery automatically refreshes the MV when base table is updated
-- Queries that match the MV pattern are automatically served from MV
-- No code change needed in queries — BigQuery rewrites transparently

-- Check MV staleness
SELECT last_refresh_time, refresh_watermark
FROM `region-us`.INFORMATION_SCHEMA.MATERIALIZED_VIEWS
WHERE table_name = 'daily_account_summary';
```

### 1.6 BigQuery SQL: Advanced Features

```sql
-- STRUCT: row-like nested record
SELECT
    customer_id,
    address.city,           -- dot notation to access struct field
    address.postal_code
FROM customers;

-- ARRAY: repeated values
SELECT
    order_id,
    item.product_id,
    item.quantity
FROM orders, UNNEST(order_items) AS item;  -- flatten array

-- GENERATE_ARRAY: create numeric sequences
SELECT date
FROM UNNEST(GENERATE_DATE_ARRAY('2024-01-01', '2024-12-31', INTERVAL 1 DAY)) AS date;

-- QUALIFY: filter window function results (BigQuery-specific)
SELECT customer_id, order_id, amount
FROM orders
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY amount DESC) = 1;
-- Returns only the highest-value order per customer

-- JSON functions
SELECT
    JSON_VALUE(payload, '$.event_type') AS event_type,
    JSON_VALUE(payload, '$.user_id')    AS user_id,
    CAST(JSON_VALUE(payload, '$.amount') AS NUMERIC) AS amount
FROM raw_events;

-- MERGE: upsert pattern
MERGE `project.dataset.target` T
USING `project.dataset.staging` S ON T.id = S.id
WHEN MATCHED AND S.updated_at > T.updated_at
    THEN UPDATE SET T.name = S.name, T.updated_at = S.updated_at
WHEN NOT MATCHED
    THEN INSERT (id, name, updated_at) VALUES (S.id, S.name, S.updated_at)
WHEN NOT MATCHED BY SOURCE AND T.updated_at < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
    THEN DELETE;   -- delete old records not in source

-- BigQuery scripting: variables and control flow
DECLARE batch_start DATE DEFAULT '2024-01-01';
DECLARE batch_end DATE;

SET batch_end = DATE_ADD(batch_start, INTERVAL 30 DAY);

IF EXISTS (
    SELECT 1 FROM `dataset.table` WHERE partition_date = batch_start LIMIT 1
) THEN
    SELECT 'Already processed';
ELSE
    -- Run the load
    INSERT INTO `dataset.table`
    SELECT * FROM `dataset.source` WHERE date = batch_start;
END IF;
```

---

## CHAPTER 2: CLOUD COMPOSER / AIRFLOW — DEEP DIVE

### 2.1 Composer Architecture

```
Cloud Composer 2 (GKE Autopilot based):
  Scheduler (x2 for HA)  → reads DAGs, triggers task instances
  Web Server             → Airflow UI
  Workers (auto-scaled)  → execute task instances
  Database (Cloud SQL)   → stores DAG runs, task states, XComs
  DAG Storage (GCS)      → DAG Python files, plugins, data
  Redis                  → task queue (CeleryExecutor)
```

### 2.2 GCP Operators Reference

```python
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryInsertJobOperator,      # run BQ query or load job
    BigQueryCreateEmptyTableOperator,
    BigQueryDeleteTableOperator,
    BigQueryCheckOperator,          # assert query returns True
    BigQueryValueCheckOperator,     # assert query returns specific value
)
from airflow.providers.google.cloud.operators.dataflow import (
    DataflowCreatePythonJobOperator,
    DataflowTemplatedJobStartOperator,
)
from airflow.providers.google.cloud.operators.gcs import (
    GCSDeleteObjectsOperator,
    GCSListObjectsOperator,
)
from airflow.providers.google.cloud.operators.dataproc import (
    DataprocCreateClusterOperator,
    DataprocSubmitJobOperator,
    DataprocDeleteClusterOperator,
)
from airflow.providers.google.cloud.sensors.bigquery import (
    BigQueryTablePartitionExistenceSensor,
)
from airflow.providers.google.cloud.sensors.gcs import (
    GCSObjectExistenceSensor,
    GCSObjectsWithPrefixExistenceSensor,
)

# Example: BigQueryCheckOperator for data quality gate
quality_gate = BigQueryCheckOperator(
    task_id='validate_no_nulls',
    sql="""
        SELECT COUNTIF(customer_id IS NULL) = 0
        FROM `project.dataset.orders`
        WHERE order_date = '{{ ds }}'
    """,
    use_legacy_sql=False
)

# Example: BigQueryValueCheckOperator for exact value check
count_check = BigQueryValueCheckOperator(
    task_id='check_row_count',
    sql="SELECT COUNT(*) FROM `project.dataset.orders` WHERE order_date = '{{ ds }}'",
    pass_value=1_000_000,
    tolerance=0.01,  # 1% tolerance
    use_legacy_sql=False
)
```

### 2.3 Templating and Macros

```python
# Jinja2 templating in Airflow operators
# {{ ds }}          execution_date as YYYY-MM-DD (e.g., 2024-01-15)
# {{ ds_nodash }}   execution_date without dashes (e.g., 20240115)
# {{ ts }}          execution_date as ISO timestamp
# {{ prev_ds }}     previous execution date
# {{ next_ds }}     next execution date
# {{ dag.dag_id }}  current DAG ID
# {{ run_id }}      unique run identifier
# {{ params.key }}  value from DAG params

# Use {{ ds }} for date-partitioned queries
BigQueryInsertJobOperator(
    task_id='load_partition',
    configuration={
        'query': {
            'query': """
                SELECT * FROM source_table
                WHERE extract_date = '{{ ds }}'
            """,
            'destinationTable': {
                'tableId': 'target_table${{ ds_nodash }}'  # write to specific partition
            },
            'writeDisposition': 'WRITE_TRUNCATE'
        }
    }
)

# Custom macros
def get_last_day_of_month(ds: str) -> str:
    from datetime import datetime
    import calendar
    dt = datetime.strptime(ds, '%Y-%m-%d')
    last_day = calendar.monthrange(dt.year, dt.month)[1]
    return f"{dt.year}-{dt.month:02d}-{last_day:02d}"

with DAG(..., user_defined_macros={'last_day_of_month': get_last_day_of_month}):
    task = BigQueryInsertJobOperator(
        sql="SELECT * FROM t WHERE date = '{{ last_day_of_month(ds) }}'"
    )
```

---

## CHAPTER 3: DATAFLOW (APACHE BEAM)

### 3.1 Beam Programming Model

```python
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, GoogleCloudOptions

# Configure for Dataflow
options = PipelineOptions()
gcp_options = options.view_as(GoogleCloudOptions)
gcp_options.project = 'wf-cdm-prod'
gcp_options.region = 'us-central1'
gcp_options.temp_location = 'gs://wf-cdm-temp/beam-temp'
gcp_options.staging_location = 'gs://wf-cdm-temp/beam-staging'
options.view_as(beam.options.pipeline_options.WorkerOptions).max_num_workers = 50
options.view_as(beam.options.pipeline_options.StandardOptions).runner = 'DataflowRunner'

# Core transforms
with beam.Pipeline(options=options) as p:
    # Read → Map → Filter → GroupBy → Write
    result = (
        p
        | 'Read CSV from GCS' >> beam.io.ReadFromText('gs://bucket/data/*.csv',
                                                        skip_header_lines=1)
        | 'Parse'             >> beam.Map(parse_csv_row)
        | 'Filter Valid'      >> beam.Filter(lambda r: r['amount'] > 0)
        | 'Add Key'           >> beam.Map(lambda r: (r['account_id'], r))
        | 'Group by Account'  >> beam.GroupByKey()
        | 'Aggregate'         >> beam.Map(aggregate_account)
        | 'Write to BQ'       >> beam.io.WriteToBigQuery(
            'project:dataset.account_summary',
            schema=BQ_SCHEMA,
            write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
            create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED
        )
    )
```

### 3.2 Dataflow Templates

Flex Templates package a Dataflow pipeline as a Docker container. Launch without Python environment setup.

```python
# Build a Flex Template
# 1. Write pipeline with ValueProvider for runtime parameters
class MigrationOptions(PipelineOptions):
    @classmethod
    def _add_argparse_args(cls, parser):
        parser.add_value_provider_argument('--source_table', type=str)
        parser.add_value_provider_argument('--partition_date', type=str)
        parser.add_value_provider_argument('--target_dataset', type=str)

# 2. Build Docker image, push to Artifact Registry
# 3. Create template spec file in GCS
# 4. Launch via Airflow or API

from airflow.providers.google.cloud.operators.dataflow import DataflowTemplatedJobStartOperator

run_dataflow = DataflowTemplatedJobStartOperator(
    task_id='run_migration_dataflow',
    template='gs://wf-cdm-templates/migration-flex-template',
    parameters={
        'source_table': 'FINANCE_DB.CUSTOMER_MASTER',
        'partition_date': '{{ ds }}',
        'target_dataset': 'finance_prod'
    },
    environment={
        'maxWorkers': 20,
        'machineType': 'n1-standard-4',
        'serviceAccountEmail': 'cdm-pipeline-sa@project.iam.gserviceaccount.com'
    }
)
```

---

## CHAPTER 4: DATAPROC (SPARK ON GCP)

### 4.1 Dataproc Cluster Types

```
STANDARD CLUSTER
  Long-lived cluster. Provision once, submit jobs repeatedly.
  Cost: pay per node per hour even when idle.
  Use for: iterative development, many small jobs per day.

EPHEMERAL CLUSTER
  Create cluster → submit job → delete cluster when done.
  Cost: pay only for job duration.
  Use for: scheduled batch jobs, production workloads.

DATAPROC SERVERLESS
  No cluster provisioning at all.
  Submit a PySpark job, GCP handles workers, auto-scales, tears down.
  Slower startup (~2 min) but zero cluster management.
  Use for: infrequent jobs where startup latency is acceptable.
```

### 4.2 PySpark Job on Dataproc

```python
# pyspark_etl_job.py
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DecimalType
import sys

def main(project_id: str, partition_date: str, bq_dataset: str):
    spark = SparkSession.builder \
        .appName(f"finance_migration_{partition_date}") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()

    # Read Parquet from GCS
    df = spark.read.parquet(
        f"gs://wf-cdm-staging/finance/customer_master/{partition_date}/"
    )

    # Transform
    df_clean = (
        df
        .filter(F.col("customer_id").isNotNull())
        .filter(F.col("amount") > 0)
        .withColumn("amount_usd", F.col("amount").cast(DecimalType(18, 4)))
        .withColumn("load_date", F.lit(partition_date))
        .dropDuplicates(["customer_id"])
    )

    # Handle skew: salt for skewed joins
    df_skew = df_clean.withColumn("salt", (F.rand() * 10).cast("int"))
    dim_broadcast = spark.table(f"{bq_dataset}.dim_customer")
    # Use broadcast for small dims
    df_enriched = df_skew.join(F.broadcast(dim_broadcast), "customer_id")

    # Write to BigQuery
    df_enriched.write \
        .format("bigquery") \
        .option("table", f"{project_id}:{bq_dataset}.customer_master") \
        .option("partitionField", "load_date") \
        .option("partitionType", "DAY") \
        .option("writeMethod", "indirect") \
        .mode("overwrite") \
        .save()

    spark.stop()

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
```

```python
# Submit to Dataproc from Airflow
from airflow.providers.google.cloud.operators.dataproc import (
    DataprocCreateClusterOperator,
    DataprocSubmitJobOperator,
    DataprocDeleteClusterOperator
)

create_cluster = DataprocCreateClusterOperator(
    task_id='create_cluster',
    project_id='wf-cdm-prod',
    region='us-central1',
    cluster_name='cdm-spark-{{ ds_nodash }}',
    cluster_config={
        'master_config': {'num_instances': 1, 'machine_type_uri': 'n1-standard-8'},
        'worker_config': {'num_instances': 10, 'machine_type_uri': 'n1-standard-8'},
        'secondary_worker_config': {'num_instances': 20}  # preemptible workers (cheaper)
    }
)

submit_job = DataprocSubmitJobOperator(
    task_id='run_pyspark_job',
    job={
        'reference': {'project_id': 'wf-cdm-prod'},
        'placement': {'cluster_name': 'cdm-spark-{{ ds_nodash }}'},
        'pyspark_job': {
            'main_python_file_uri': 'gs://wf-cdm-code/pyspark_etl_job.py',
            'args': ['wf-cdm-prod', '{{ ds }}', 'finance_prod'],
            'jar_file_uris': ['gs://spark-lib/bigquery/spark-bigquery-latest_2.12.jar']
        }
    }
)

delete_cluster = DataprocDeleteClusterOperator(
    task_id='delete_cluster',
    project_id='wf-cdm-prod',
    region='us-central1',
    cluster_name='cdm-spark-{{ ds_nodash }}',
    trigger_rule='all_done'  # delete even if job failed
)

create_cluster >> submit_job >> delete_cluster
```

---

## CHAPTER 5: GCS, PUB/SUB, AND CLOUD FUNCTIONS

### 5.1 GCS Best Practices

```python
from google.cloud import storage

def upload_to_gcs(local_path: str, bucket: str, blob_name: str) -> str:
    client = storage.Client()
    bucket_obj = client.bucket(bucket)
    blob = bucket_obj.blob(blob_name)
    blob.upload_from_filename(local_path, content_type='application/octet-stream')
    return f"gs://{bucket}/{blob_name}"

def list_gcs_objects(bucket: str, prefix: str) -> list:
    client = storage.Client()
    blobs = client.list_blobs(bucket, prefix=prefix)
    return [f"gs://{bucket}/{b.name}" for b in blobs]

# Naming convention for CDM Next GCS paths:
# gs://wf-cdm-staging/{domain}/{table}/{partition_date}/part-{sequence}.parquet
# Example: gs://wf-cdm-staging/finance/customer_master/2024-01-15/part-00000.parquet

# Lifecycle rules (set via Terraform or gsutil):
# Standard → Nearline after 30 days (staging data)
# Standard → Archive after 365 days (raw Bronze data)
# Delete after 7 days (temp/work files)
```

### 5.2 Cloud Functions for Event-Driven Pipelines

```python
# main.py — Cloud Function triggered by GCS file arrival
import json
import functions_framework
from google.cloud import storage, bigquery

@functions_framework.cloud_event
def trigger_pipeline_on_file_arrival(cloud_event):
    """Trigger a BigQuery load when a file lands in GCS."""
    data = cloud_event.data
    bucket = data["bucket"]
    name = data["name"]

    # Only trigger for specific file patterns
    if not name.startswith("finance/") or not name.endswith(".parquet"):
        return

    # Extract partition date from path
    # finance/customer_master/2024-01-15/part-00000.parquet
    parts = name.split("/")
    if len(parts) < 3:
        return
    domain = parts[0]
    table_name = parts[1]
    partition_date = parts[2]

    # Load to BigQuery
    bq = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition="WRITE_APPEND"
    )
    uri = f"gs://{bucket}/{name}"
    table_ref = f"wf-cdm-prod.{domain}_staging.{table_name}${partition_date.replace('-', '')}"

    job = bq.load_table_from_uri(uri, table_ref, job_config=job_config)
    job.result()

    print(json.dumps({
        "status": "success",
        "file": uri,
        "target": table_ref,
        "rows_loaded": bq.get_table(table_ref.split("$")[0]).num_rows
    }))
```

---

## CHAPTER 6: CLOUD DLP, IAM, AND SECRET MANAGER

### 6.1 Cloud DLP Integration Pattern

```python
from google.cloud import dlp_v2

def inspect_and_mask_dataframe(
    df: pd.DataFrame,
    project_id: str,
    pii_columns: list
) -> pd.DataFrame:
    """Mask PII columns in a Pandas DataFrame using Cloud DLP."""
    client = dlp_v2.DlpServiceClient()

    info_types = [
        {"name": "US_SOCIAL_SECURITY_NUMBER"},
        {"name": "CREDIT_CARD_NUMBER"},
        {"name": "EMAIL_ADDRESS"},
        {"name": "FINANCIAL_ACCOUNT_NUMBER"},
    ]

    deidentify_config = {
        "info_type_transformations": {
            "transformations": [{
                "primitive_transformation": {
                    "character_mask_config": {
                        "masking_character": "X",
                        "number_to_mask": 0,  # mask all except last 4
                        "reverse_order": True,
                        "characters_to_ignore": [{"common_characters_to_ignore": "PUNCTUATION"}]
                    }
                }
            }]
        }
    }

    for col in pii_columns:
        if col not in df.columns:
            continue
        # Process in batches (DLP has item size limits)
        masked_values = []
        for val in df[col].fillna(""):
            if val:
                response = client.deidentify_content(
                    request={
                        "parent": f"projects/{project_id}",
                        "deidentify_config": deidentify_config,
                        "inspect_config": {"info_types": info_types},
                        "item": {"value": str(val)}
                    }
                )
                masked_values.append(response.item.value)
            else:
                masked_values.append(None)
        df[col] = masked_values

    return df
```

### 6.2 IAM Best Practices Code

```python
from google.cloud import bigquery
from google.iam.v1 import iam_policy_pb2

def grant_bq_dataset_access(
    project_id: str,
    dataset_id: str,
    member: str,
    role: str = "roles/bigquery.dataViewer"
) -> None:
    """Grant IAM access to a BigQuery dataset with audit logging."""
    client = bigquery.Client(project=project_id)
    dataset = client.get_dataset(f"{project_id}.{dataset_id}")

    access_entries = list(dataset.access_entries)
    access_entries.append(
        bigquery.AccessEntry(role=role, entity_type="iamMember", entity_id=member)
    )
    dataset.access_entries = access_entries
    client.update_dataset(dataset, ["access_entries"])

    print(f"Granted {role} to {member} on {project_id}.{dataset_id}")
    # This access grant is captured in Cloud Audit Logs (ADMIN_ACTIVITY)
```

---

## CHAPTER 7: DATAPLEX AND DATA CATALOG

### 7.1 Dataplex Data Quality Rules

```python
# Define DQ rules declaratively
from google.cloud import dataplex_v1

def create_dq_scan(project: str, location: str, dataset: str, table: str) -> None:
    client = dataplex_v1.DataScanServiceClient()

    datascan = dataplex_v1.DataScan(
        display_name=f"DQ Scan: {table}",
        data=dataplex_v1.DataSource(
            resource=f"//bigquery.googleapis.com/projects/{project}/datasets/{dataset}/tables/{table}"
        ),
        data_quality_spec=dataplex_v1.DataQualitySpec(
            rules=[
                # Not null check
                dataplex_v1.DataQualityRule(
                    column="customer_id",
                    non_null_expectation=dataplex_v1.DataQualityRule.NonNullExpectation(),
                    dimension="COMPLETENESS",
                    threshold=1.0  # 100% must be non-null
                ),
                # Row count check
                dataplex_v1.DataQualityRule(
                    table_condition_expectation=dataplex_v1.DataQualityRule.TableConditionExpectation(
                        sql_expression="COUNT(*) > 100000"
                    ),
                    dimension="COMPLETENESS"
                ),
                # Value range
                dataplex_v1.DataQualityRule(
                    column="amount",
                    range_expectation=dataplex_v1.DataQualityRule.RangeExpectation(
                        min_value="0",
                        max_value="10000000"
                    ),
                    dimension="VALIDITY",
                    threshold=0.999
                )
            ]
        ),
        execution_spec=dataplex_v1.DataScan.ExecutionSpec(
            trigger=dataplex_v1.Trigger(
                schedule=dataplex_v1.Trigger.Schedule(cron="0 6 * * *")
            )
        )
    )

    client.create_data_scan(
        parent=f"projects/{project}/locations/{location}",
        data_scan=datascan,
        data_scan_id=f"dq-{table.lower()}"
    )
```

---

## CHAPTER 8: CLOUD MONITORING AND LOGGING

### 8.1 Custom Metrics

```python
from google.cloud import monitoring_v3
import time

def write_custom_metric(
    project_id: str,
    metric_name: str,
    value: float,
    labels: dict
) -> None:
    """Write a custom metric to Cloud Monitoring."""
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project_id}"

    series = monitoring_v3.TimeSeries()
    series.metric.type = f"custom.googleapis.com/cdm/{metric_name}"
    for k, v in labels.items():
        series.metric.labels[k] = str(v)

    series.resource.type = "global"

    point = monitoring_v3.Point()
    point.value.double_value = value
    now = time.time()
    point.interval.end_time.seconds = int(now)
    point.interval.end_time.nanos = int((now - int(now)) * 10**9)
    series.points = [point]

    client.create_time_series(
        request={"name": project_name, "time_series": [series]}
    )

# Usage: emit pipeline metrics
write_custom_metric(
    project_id="wf-cdm-prod",
    metric_name="rows_loaded",
    value=1_234_567,
    labels={"pipeline": "finance_customer_migration", "environment": "prod"}
)
write_custom_metric(
    project_id="wf-cdm-prod",
    metric_name="validation_pass_rate",
    value=0.9998,
    labels={"pipeline": "finance_customer_migration"}
)
```

### 8.2 Log-Based Metrics

```python
# Create log-based metric via Python (or Terraform)
from google.cloud import logging_v2

def create_pipeline_failure_metric(project_id: str) -> None:
    """Create a log-based metric to count pipeline failures."""
    client = logging_v2.MetricsServiceV2Client()

    metric = logging_v2.LogMetric(
        name="cdm_pipeline_failures",
        description="Count of CDM pipeline failures",
        filter='resource.type="global" jsonPayload.severity="ERROR" '
               'jsonPayload.pipeline=~".*migration.*"',
        metric_descriptor={
            "metric_kind": "DELTA",
            "value_type": "INT64",
            "labels": [
                {"key": "pipeline", "value_type": "STRING"},
                {"key": "error_type", "value_type": "STRING"}
            ]
        },
        label_extractors={
            "pipeline":    "EXTRACT(jsonPayload.pipeline)",
            "error_type":  "EXTRACT(jsonPayload.error_type)"
        }
    )

    client.create_log_metric(
        parent=f"projects/{project_id}",
        metric=metric
    )
```

---

*End of GCP Deep Dive Textbook*
