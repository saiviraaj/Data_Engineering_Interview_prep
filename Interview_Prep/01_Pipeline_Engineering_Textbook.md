# Data Pipeline Engineering & ETL/ELT — Complete Textbook
### Building Reliable, Scalable, Production-Grade Data Pipelines

---

## CHAPTER 1: PIPELINE FUNDAMENTALS

### 1.1 What Is a Data Pipeline?

A data pipeline is a series of automated processes that move and transform data from source systems to target systems. Every pipeline has four concerns:

```
INGESTION   Extract data from source systems (DB, API, files, streams)
PROCESSING  Transform: clean, validate, enrich, aggregate
LOADING     Write to target: data warehouse, data lake, API
ORCHESTRATION Coordinate steps, handle dependencies, retry failures
```

### 1.2 ETL vs ELT

```
ETL (Extract, Transform, Load) — Traditional
  Extract from source → Transform outside (Spark, Python) → Load to warehouse
  When to use: source data needs heavy Python logic; PII must be masked
  before entering warehouse; compute cost inside warehouse is high.

ELT (Extract, Load, Transform) — Modern Cloud
  Extract from source → Load raw to warehouse → Transform inside (SQL)
  When to use: BigQuery/Snowflake has sufficient compute; analysts
  need access to raw data; iterative transformation logic in SQL.
  CDM Next approach: ELT via GCS → BigQuery load → SQL transforms.

ELTT (Extract, Light Transform, Load, Transform)
  Light transforms outside (type coercion, PII masking) before loading.
  Full business logic transforms inside warehouse.
  Best of both worlds — practical choice for regulated environments.
```

### 1.3 Batch vs Streaming

```
BATCH
  Bounded dataset. Process at scheduled intervals (hourly, daily).
  Latency: minutes to hours. Simpler to build and test.
  Use for: nightly data warehouse loads, monthly reports, ML training.

MICRO-BATCH
  Small batches on short schedule (every 30–60 seconds).
  Latency: seconds to minutes. Simpler than true streaming.
  Spark Structured Streaming default mode.

STREAMING
  Unbounded. Process each event as it arrives.
  Latency: milliseconds to seconds. Complex windowing and state management.
  Use for: fraud detection, operational alerts, live dashboards.
```

---

## CHAPTER 2: APACHE AIRFLOW / CLOUD COMPOSER

### 2.1 Core Concepts

```
DAG (Directed Acyclic Graph)
  A collection of tasks with dependencies.
  Acyclic = no circular dependencies.
  Defined in Python; stored in GCS for Cloud Composer.

TASK
  A single unit of work within a DAG.
  Implemented as an Operator.

OPERATOR
  Template for a task type.
  BashOperator: run shell command
  PythonOperator: call Python function
  BigQueryInsertJobOperator: run BQ query
  GCSToBigQueryOperator: load GCS file to BQ
  DataflowCreatePythonJobOperator: launch Dataflow job

SENSOR
  Operator that waits for a condition.
  GCSObjectExistenceSensor: wait for file to appear in GCS
  BigQueryTablePartitionExistenceSensor: wait for partition to land

XCOM
  Cross-communication between tasks.
  Task A pushes a value; Task B pulls it.
  Use for small data (row counts, file paths). Not for large datasets.

POOL
  Controls concurrency — limits simultaneous task executions.
  Use to prevent overwhelming external systems.
  Example: teradata_pool with 5 slots limits 5 concurrent TD queries.

VARIABLE
  Airflow-managed key-value store for config.
  Access: Variable.get('project_id')

CONNECTION
  Stored credentials for external systems.
  Never hardcode credentials; use Airflow connections or Secret Manager.
```

### 2.2 DAG Authoring Best Practices

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.providers.google.cloud.sensors.gcs import GCSObjectExistenceSensor
from airflow.utils.dates import days_ago
from datetime import timedelta

# Always define default_args
default_args = {
    'owner': 'cdm-platform',
    'depends_on_past': False,
    'email': ['cdm-alerts@company.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=15),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(hours=1),
    'execution_timeout': timedelta(hours=4),
}

with DAG(
    dag_id='finance_customer_migration',
    default_args=default_args,
    description='Daily incremental migration of customer_master from Teradata',
    schedule_interval='0 2 * * *',   # 2 AM daily
    start_date=days_ago(1),
    catchup=False,                    # Don't backfill historical missed runs
    max_active_runs=1,                # Prevent concurrent runs
    tags=['finance', 'migration', 'daily'],
    params={'batch_size': 10000, 'tolerance_pct': 0.01}
) as dag:

    # Task 1: Check source availability
    check_source = PythonOperator(
        task_id='check_source_availability',
        python_callable=check_teradata_connection,
        op_kwargs={'schema': 'FINANCE_DB', 'table': 'CUSTOMER_MASTER'}
    )

    # Task 2: Extract to GCS
    extract = PythonOperator(
        task_id='extract_to_gcs',
        python_callable=extract_incremental,
        op_kwargs={
            'source_table': 'FINANCE_DB.CUSTOMER_MASTER',
            'watermark_col': 'UPDATED_DATE',
            'gcs_bucket': 'wf-cdm-staging',
            'output_path': 'finance/customer_master/{{ ds }}/'
        }
    )

    # Task 3: Wait for file to land
    wait_for_file = GCSObjectExistenceSensor(
        task_id='wait_for_gcs_file',
        bucket='wf-cdm-staging',
        object='finance/customer_master/{{ ds }}/part-00000.parquet',
        timeout=3600,
        poke_interval=60
    )

    # Task 4: Run DLP scan
    dlp_scan = PythonOperator(
        task_id='scan_for_pii',
        python_callable=run_dlp_scan,
        op_kwargs={'gcs_path': 'gs://wf-cdm-staging/finance/customer_master/{{ ds }}/'}
    )

    # Task 5: Validate schema
    validate_schema = PythonOperator(
        task_id='validate_schema',
        python_callable=validate_source_schema,
        op_kwargs={'table': 'FINANCE_DB.CUSTOMER_MASTER'}
    )

    # Task 6: Load to BigQuery staging
    load_to_staging = BigQueryInsertJobOperator(
        task_id='load_to_bq_staging',
        configuration={
            'load': {
                'sourceUris': ['gs://wf-cdm-staging/finance/customer_master/{{ ds }}/*.parquet'],
                'destinationTable': {
                    'projectId': 'wf-cdm-prod',
                    'datasetId': 'finance_staging',
                    'tableId': 'customer_master_{{ ds_nodash }}'
                },
                'sourceFormat': 'PARQUET',
                'writeDisposition': 'WRITE_TRUNCATE',
                'createDisposition': 'CREATE_IF_NEEDED'
            }
        }
    )

    # Task 7: Validate row counts
    validate_counts = PythonOperator(
        task_id='validate_row_counts',
        python_callable=validate_row_count_reconciliation,
        op_kwargs={
            'source_table': 'FINANCE_DB.CUSTOMER_MASTER',
            'target_table': 'wf-cdm-prod.finance_staging.customer_master_{{ ds_nodash }}',
            'tolerance_pct': '{{ params.tolerance_pct }}'
        }
    )

    # Task 8: Merge to production
    merge_to_prod = BigQueryInsertJobOperator(
        task_id='merge_to_production',
        configuration={
            'query': {
                'query': """
                    MERGE INTO `wf-cdm-prod.finance_prod.customer_master` T
                    USING `wf-cdm-prod.finance_staging.customer_master_{{ ds_nodash }}` S
                    ON T.customer_id = S.customer_id
                    WHEN MATCHED THEN UPDATE SET
                        T.name = S.name, T.tier = S.tier,
                        T.updated_at = S.updated_at
                    WHEN NOT MATCHED THEN INSERT ROW
                """,
                'useLegacySql': False
            }
        }
    )

    # Task 9: Write audit record
    write_audit = PythonOperator(
        task_id='write_audit_record',
        python_callable=write_pipeline_audit,
        trigger_rule='all_done'  # run even if upstream fails — always write audit
    )

    # Define dependencies
    check_source >> extract >> wait_for_file >> [dlp_scan, validate_schema]
    [dlp_scan, validate_schema] >> load_to_staging >> validate_counts >> merge_to_prod >> write_audit
```

### 2.3 Dynamic DAG Generation

CDM Next's key pattern: generate DAGs from config, not code.

```python
import yaml
import os
from airflow import DAG

CONFIG_BUCKET = 'wf-cdm-configs'
CONFIG_PREFIX = 'pipeline-configs/'

def create_dag_from_config(config: dict) -> DAG:
    """Generate a fully configured migration DAG from a YAML config."""
    dag_id = f"migrate_{config['source']['table'].lower()}"

    with DAG(
        dag_id=dag_id,
        schedule_interval=config['schedule']['cron'],
        default_args={**BASE_DEFAULT_ARGS,
                      'retries': config['schedule']['retry_count']},
        catchup=False,
        max_active_runs=1,
        tags=[config['source']['type'], 'auto-generated']
    ) as dag:
        # Build tasks dynamically based on config
        tasks = build_migration_tasks(config)
        # Wire dependencies
        wire_task_dependencies(tasks, config)

    return dag


# Load all configs from GCS and generate DAGs
# Airflow picks up any DAG object in the globals() dict
for config_file in list_gcs_configs(CONFIG_BUCKET, CONFIG_PREFIX):
    config = load_yaml_from_gcs(CONFIG_BUCKET, config_file)
    dag_obj = create_dag_from_config(config)
    globals()[dag_obj.dag_id] = dag_obj  # register with Airflow
```

### 2.4 Airflow Operational Patterns

```python
# BRANCHING: conditional task execution
from airflow.operators.python import BranchPythonOperator

def choose_load_strategy(**context):
    """Choose full or incremental load based on last successful run."""
    last_run = get_last_successful_run(context['dag_id'])
    if last_run is None:
        return 'full_load_task'
    return 'incremental_load_task'

branch = BranchPythonOperator(
    task_id='choose_strategy',
    python_callable=choose_load_strategy
)

# TRIGGER RULES: control when a task runs
from airflow.utils.trigger_rule import TriggerRule

cleanup = PythonOperator(
    task_id='cleanup',
    python_callable=cleanup_staging,
    trigger_rule=TriggerRule.ALL_DONE  # run even if upstream failed
)

audit = PythonOperator(
    task_id='write_audit',
    trigger_rule=TriggerRule.ONE_FAILED  # only run if something failed
)

# XCOMS: pass data between tasks
def extract_and_push(**context):
    row_count = do_extraction()
    context['ti'].xcom_push(key='row_count', value=row_count)

def validate_and_pull(**context):
    row_count = context['ti'].xcom_pull(task_ids='extract', key='row_count')
    assert row_count > 0, "Empty extract"

# TASK GROUPS: organise related tasks
from airflow.utils.task_group import TaskGroup

with TaskGroup('validation', tooltip='Data quality checks') as validation_group:
    check_nulls = PythonOperator(task_id='check_nulls', ...)
    check_counts = PythonOperator(task_id='check_counts', ...)
    check_schema = PythonOperator(task_id='check_schema', ...)
    [check_nulls, check_counts, check_schema]
```

---

## CHAPTER 3: CHANGE DATA CAPTURE (CDC)

### 3.1 CDC Fundamentals

CDC captures every row-level change (INSERT, UPDATE, DELETE) from a database transaction log, rather than polling the table.

```
Traditional polling (watermark-based):
  SELECT * FROM table WHERE updated_at > last_run_time
  Problems: misses deletes; source must have reliable updated_at;
  heavy load on source system; not real-time

CDC from transaction log:
  Read INSERT/UPDATE/DELETE events from DB redo log as they happen
  Captures deletes; near real-time; minimal source load
  Requires DB-level access (redo log, WAL, binlog)
```

### 3.2 Datastream — GCP CDC Service

Datastream reads transaction logs from Oracle, MySQL, PostgreSQL, SQL Server and delivers change events to BigQuery, GCS, or Pub/Sub.

```python
from google.cloud import datastream_v1

def create_datastream_pipeline(
    project_id: str,
    oracle_connection: dict,
    bigquery_dataset: str
) -> None:
    client = datastream_v1.DatastreamClient()

    # Source: Oracle database
    source_config = datastream_v1.SourceConfig(
        oracle_source_config=datastream_v1.OracleSourceConfig(
            include_objects=datastream_v1.OracleRdbms(
                oracle_schemas=[
                    datastream_v1.OracleSchema(
                        schema_name="FINANCE_DB",
                        oracle_tables=[
                            datastream_v1.OracleTable(table_name="CUSTOMER_MASTER"),
                            datastream_v1.OracleTable(table_name="ORDERS")
                        ]
                    )
                ]
            )
        ),
        source_connection_profile=f"projects/{project_id}/locations/us/connectionProfiles/oracle-prod"
    )

    # Destination: BigQuery
    dest_config = datastream_v1.DestinationConfig(
        bigquery_destination_config=datastream_v1.BigQueryDestinationConfig(
            single_target_dataset=datastream_v1.BigQueryDestinationConfig.SingleTargetDataset(
                dataset_id=bigquery_dataset
            ),
            data_freshness={"seconds": 60}  # target 60s latency
        ),
        destination_connection_profile=f"projects/{project_id}/locations/us/connectionProfiles/bigquery"
    )

    stream = datastream_v1.Stream(
        display_name="Oracle Finance CDC",
        source_config=source_config,
        destination_config=dest_config,
        backfill_all=datastream_v1.Stream.BackfillAllStrategy()
    )

    client.create_stream(
        parent=f"projects/{project_id}/locations/us",
        stream_id="oracle-finance-cdc",
        stream=stream
    )
```

### 3.3 CDC Event Processing Pattern

```python
# CDC events arrive as JSON with metadata
# {
#   "_metadata": {
#     "operation": "INSERT" | "UPDATE" | "DELETE",
#     "source_timestamp": "2024-01-15T14:23:01Z",
#     "table": "CUSTOMER_MASTER"
#   },
#   "customer_id": "C001",
#   "name": "John Smith",
#   ...
# }

def process_cdc_event(event: dict, target_table: str) -> None:
    """Route CDC event to appropriate handler."""
    operation = event.get("_metadata", {}).get("operation")
    data = {k: v for k, v in event.items() if not k.startswith("_")}

    if operation == "INSERT":
        insert_to_bigquery(data, target_table)
    elif operation == "UPDATE":
        merge_to_bigquery(data, target_table, key_column="customer_id")
    elif operation == "DELETE":
        # Soft delete — never physically delete in data warehouse
        soft_delete_in_bigquery(data["customer_id"], target_table)
    else:
        logger.warning(f"Unknown CDC operation: {operation}")
        route_to_dlq(event)

def soft_delete_in_bigquery(key_value: str, table: str) -> None:
    """Mark record as deleted without removing it."""
    client = bigquery.Client()
    client.query(f"""
        UPDATE `{table}`
        SET is_deleted = TRUE, deleted_at = CURRENT_TIMESTAMP()
        WHERE customer_id = '{key_value}' AND is_deleted = FALSE
    """).result()
```

---

## CHAPTER 4: PIPELINE RELIABILITY PATTERNS

### 4.1 Idempotency

An idempotent pipeline produces the same result whether run once or ten times.

```python
# BAD: append-only → running twice creates duplicates
def load_to_bq_bad(data: list, table: str) -> None:
    errors = bq_client.insert_rows_json(table, data)

# GOOD: partition overwrite → re-running replaces, not duplicates
def load_to_bq_idempotent(data: list, table: str, partition_date: str) -> None:
    partition_table = f"{table}${partition_date.replace('-', '')}"
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",  # overwrite this partition
        create_disposition="CREATE_IF_NEEDED"
    )
    job = bq_client.load_table_from_json(data, partition_table, job_config=job_config)
    job.result()

# GOOD: MERGE → upserts on primary key
def upsert_to_bq(data: list, table: str, key_col: str) -> None:
    # Write to temp table first
    temp_table = f"{table}_temp_{uuid.uuid4().hex[:8]}"
    load_to_temp(data, temp_table)
    # MERGE temp into target
    bq_client.query(f"""
        MERGE `{table}` T
        USING `{temp_table}` S ON T.{key_col} = S.{key_col}
        WHEN MATCHED THEN UPDATE SET {build_update_set(data)}
        WHEN NOT MATCHED THEN INSERT ROW
    """).result()
    # Cleanup temp
    bq_client.delete_table(temp_table)
```

### 4.2 Checkpointing and Watermarks

```python
class WatermarkManager:
    """Track pipeline progress — resume from last successful position."""

    def __init__(self, pipeline_name: str, bq_client: bigquery.Client):
        self.pipeline_name = pipeline_name
        self.bq_client = bq_client
        self._table = "governance.pipeline_watermarks"

    def get_last_watermark(self) -> Optional[datetime]:
        """Get the last successfully processed watermark."""
        result = self.bq_client.query(f"""
            SELECT watermark_value
            FROM `{self._table}`
            WHERE pipeline_name = '{self.pipeline_name}'
              AND status = 'SUCCESS'
            ORDER BY recorded_at DESC
            LIMIT 1
        """).result()

        rows = list(result)
        if not rows:
            return None  # First run — full load
        return rows[0]["watermark_value"]

    def set_watermark(self, value: datetime, status: str = "SUCCESS") -> None:
        """Record current watermark after successful processing."""
        self.bq_client.query(f"""
            INSERT INTO `{self._table}`
            (pipeline_name, watermark_value, status, recorded_at)
            VALUES ('{self.pipeline_name}', '{value.isoformat()}',
                    '{status}', CURRENT_TIMESTAMP())
        """).result()

# Usage
wm = WatermarkManager("finance_customer_migration", bq_client)
last_run = wm.get_last_watermark()

if last_run is None:
    # Full load
    query = "SELECT * FROM CUSTOMER_MASTER"
else:
    # Incremental
    query = f"SELECT * FROM CUSTOMER_MASTER WHERE UPDATED_DATE > '{last_run}'"

rows_loaded = extract_and_load(query)
wm.set_watermark(datetime.utcnow())
```

### 4.3 Dead Letter Queue Pattern

```python
from google.cloud import pubsub_v1

def process_with_dlq(
    messages: list,
    process_fn: callable,
    dlq_topic: str
) -> dict:
    """Process messages, routing failures to a dead letter queue."""
    publisher = pubsub_v1.PublisherClient()
    results = {"success": 0, "failed": 0}

    for msg in messages:
        try:
            process_fn(msg)
            results["success"] += 1

        except ValidationError as e:
            # Data issue — route to DLQ with error context
            dlq_payload = {
                "original_message": msg,
                "error_type": "VALIDATION_ERROR",
                "error_detail": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "pipeline": "finance_migration"
            }
            publisher.publish(
                dlq_topic,
                json.dumps(dlq_payload).encode()
            )
            results["failed"] += 1

        except TransientError as e:
            # Retry-able — re-queue with backoff metadata
            retry_payload = {**msg, "_retry_count": msg.get("_retry_count", 0) + 1}
            if retry_payload["_retry_count"] <= 3:
                re_queue(retry_payload)
            else:
                route_to_dlq(dlq_payload, "MAX_RETRIES_EXCEEDED")
            results["failed"] += 1

    return results
```

### 4.4 Circuit Breaker Pattern

```python
class CircuitBreaker:
    """Prevent cascade failures when downstream systems are unhealthy."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.timeout = timeout  # seconds before attempting reset
        self._failures = 0
        self._last_failure_time = None
        self._state = "CLOSED"  # CLOSED=normal, OPEN=failing, HALF_OPEN=testing

    def call(self, fn, *args, **kwargs):
        if self._state == "OPEN":
            if time.time() - self._last_failure_time > self.timeout:
                self._state = "HALF_OPEN"
            else:
                raise CircuitOpenError("Circuit is OPEN — downstream system unhealthy")

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self._failures = 0
        self._state = "CLOSED"

    def _on_failure(self):
        self._failures += 1
        self._last_failure_time = time.time()
        if self._failures >= self.failure_threshold:
            self._state = "OPEN"
            logger.error(f"Circuit OPENED after {self._failures} failures")
```

---

## CHAPTER 5: DATA INGESTION PATTERNS

### 5.1 File-Based Ingestion (GCS)

```python
def ingest_file_to_bigquery(
    gcs_uri: str,
    target_table: str,
    schema: list,
    source_format: str = "PARQUET"
) -> bigquery.LoadJob:
    """Load a file from GCS to BigQuery with validation."""
    client = bigquery.Client()

    job_config = bigquery.LoadJobConfig(
        source_format=getattr(bigquery.SourceFormat, source_format),
        schema=schema or None,        # None = autodetect
        autodetect=(schema is None),
        write_disposition="WRITE_APPEND",
        create_disposition="CREATE_IF_NEEDED",
        ignore_unknown_values=False,  # fail on unexpected columns
        max_bad_records=0,            # zero tolerance for bad records
    )

    job = client.load_table_from_uri(gcs_uri, target_table, job_config=job_config)
    job.result()  # wait for completion

    table = client.get_table(target_table)
    logger.info(f"Loaded {table.num_rows} rows to {target_table}")
    return job
```

### 5.2 API Ingestion Pattern

```python
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
def fetch_api_page(url: str, params: dict, headers: dict) -> dict:
    """Fetch a single page from an API with retry."""
    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()

def ingest_paginated_api(
    base_url: str,
    params: dict,
    headers: dict,
    page_size: int = 1000
) -> Generator[list, None, None]:
    """Paginate through an API, yielding batches of records."""
    page = 1
    while True:
        data = fetch_api_page(
            base_url,
            {**params, 'page': page, 'page_size': page_size},
            headers
        )
        records = data.get('results', [])
        if not records:
            break
        yield records
        if not data.get('next'):  # no next page
            break
        page += 1
```

### 5.3 Database Ingestion with Batching

```python
def extract_in_batches(
    connection,
    query: str,
    batch_size: int = 10_000
) -> Generator[list, None, None]:
    """Extract data in batches to control memory usage."""
    cursor = connection.cursor()
    cursor.execute(query)

    while True:
        batch = cursor.fetchmany(batch_size)
        if not batch:
            break
        cols = [d[0].lower() for d in cursor.description]
        yield [dict(zip(cols, row)) for row in batch]

    cursor.close()


def incremental_extract(
    connection,
    table: str,
    watermark_col: str,
    last_watermark: Optional[datetime],
    batch_size: int = 10_000
) -> Generator[list, None, None]:
    """Extract only changed rows since last run."""
    if last_watermark:
        query = f"""
            SELECT * FROM {table}
            WHERE {watermark_col} > :watermark
            ORDER BY {watermark_col}
        """
        cursor = connection.cursor()
        cursor.execute(query, watermark=last_watermark)
    else:
        # First run: full extract
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {table} ORDER BY {watermark_col}")

    while True:
        batch = cursor.fetchmany(batch_size)
        if not batch:
            break
        cols = [d[0].lower() for d in cursor.description]
        yield [dict(zip(cols, row)) for row in batch]
```

---

## CHAPTER 6: PIPELINE TESTING

### 6.1 Test Pyramid for Data Pipelines

```
                     /\
                    /  \
                   / E2E \      ← Fewest, most expensive, test full pipeline
                  /--------\
                 / INTEGRATION \  ← Test component interactions (BQ+GCS+Airflow)
                /--------------\
               /   UNIT TESTS   \  ← Most, cheapest, test individual functions
              /------------------\
```

### 6.2 Unit Testing Pipeline Code

```python
import pytest
from unittest.mock import MagicMock, patch
from datetime import date

class TestIncrementalExtract:

    def test_builds_full_query_on_first_run(self):
        conn = MagicMock()
        conn.cursor().fetchmany.return_value = []
        list(incremental_extract(conn, "ORDERS", "UPDATED_DATE", None))
        # Verify cursor was called without watermark filter
        call_args = conn.cursor().execute.call_args[0][0]
        assert "WHERE" not in call_args

    def test_builds_incremental_query_on_subsequent_run(self):
        conn = MagicMock()
        conn.cursor().fetchmany.return_value = []
        last_run = date(2024, 1, 14)
        list(incremental_extract(conn, "ORDERS", "UPDATED_DATE", last_run))
        call_args = conn.cursor().execute.call_args[0][0]
        assert "WHERE" in call_args
        assert "UPDATED_DATE" in call_args

    @pytest.mark.parametrize("batch_data,expected_batches", [
        ([row1, row2, row3], 1),  # 3 rows, batch_size=10 → 1 batch
        ([row1]*25, 3),           # 25 rows, batch_size=10 → 3 batches
    ])
    def test_batches_correctly(self, batch_data, expected_batches):
        conn = MagicMock()
        batch_size = 10
        # Simulate cursor.fetchmany returning batch_size rows then []
        side_effects = [batch_data[i:i+batch_size]
                       for i in range(0, len(batch_data), batch_size)] + [[]]
        conn.cursor().fetchmany.side_effect = side_effects
        batches = list(incremental_extract(conn, "T", "dt", None, batch_size))
        assert len(batches) == expected_batches
```

### 6.3 Airflow DAG Testing

```python
from airflow.models import DagBag

def test_dag_loads_without_errors():
    """Verify all DAGs parse without syntax errors."""
    dagbag = DagBag(dag_folder='dags/', include_examples=False)
    assert dagbag.import_errors == {}, \
        f"DAG import errors: {dagbag.import_errors}"

def test_dag_has_correct_schedule():
    dagbag = DagBag(dag_folder='dags/')
    dag = dagbag.get_dag('finance_customer_migration')
    assert dag is not None
    assert dag.schedule_interval == '0 2 * * *'
    assert dag.max_active_runs == 1
    assert dag.catchup == False

def test_dag_task_dependencies():
    dagbag = DagBag(dag_folder='dags/')
    dag = dagbag.get_dag('finance_customer_migration')
    tasks = {t.task_id: t for t in dag.tasks}

    # Verify merge happens after validation
    assert 'validate_row_counts' in [
        t.task_id for t in tasks['merge_to_production'].upstream_list
    ]
    # Verify audit always runs (all_done trigger rule)
    assert tasks['write_audit'].trigger_rule == 'all_done'
```

---

*End of Data Pipeline Engineering & ETL/ELT Textbook*
