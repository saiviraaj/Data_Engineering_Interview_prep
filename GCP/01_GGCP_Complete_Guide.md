# 🌐 Google Cloud Platform (GCP) — Complete Interview Bible
### Senior Data Engineer Edition

---

# TABLE OF CONTENTS

1. [GCP Fundamentals & Architecture](#1-gcp-fundamentals--architecture)
2. [BigQuery — Deep Dive](#2-bigquery--deep-dive)
3. [Cloud Storage (GCS)](#3-cloud-storage-gcs)
4. [Cloud Dataflow (Apache Beam)](#4-cloud-dataflow-apache-beam)
5. [Cloud Dataproc (Managed Spark/Hadoop)](#5-cloud-dataproc-managed-sparkhadoop)
6. [Cloud Composer / Apache Airflow](#6-cloud-composer--apache-airflow)
7. [Pub/Sub — Streaming Messaging](#7-pubsub--streaming-messaging)
8. [Cloud Functions & Cloud Run](#8-cloud-functions--cloud-run)
9. [Cloud DLP, IAM, Secret Manager](#9-cloud-dlp-iam-secret-manager)
10. [Cloud Logging & Monitoring](#10-cloud-logging--monitoring)
11. [Dataplex — Data Governance](#11-dataplex--data-governance)
12. [System Design Patterns on GCP](#12-system-design-patterns-on-gcp)
13. [Practice Interview Questions](#13-practice-interview-questions)
14. [Cheat Sheet](#14-cheat-sheet)

---

# 1. GCP Fundamentals & Architecture

## 1.1 Core Concepts

### Projects, Folders, Organizations
```
Organization (e.g., wells-fargo.com)
  └── Folders (e.g., Finance, Engineering)
       └── Projects (e.g., data-platform-prod)
            └── Resources (BigQuery, GCS, Dataflow...)
```

- **Project** = billing + IAM boundary. Every GCP resource lives in a project.
- **Folder** = logical grouping, inherits IAM policies.
- **Organization** = root node, linked to Google Workspace domain.

### Resource Hierarchy & IAM Inheritance
- Policies set at Organization level flow **down** to all children.
- More permissive policy at a lower level **wins** (policies are union'd, not overridden).
- Exception: `constraints/` (Organization Policies) — these can **deny** lower levels.

### Regions vs Zones
| Concept | Example | Notes |
|---|---|---|
| Multi-region | `US`, `EU`, `ASIA` | Highest availability, higher cost |
| Region | `us-central1` | ~10 zones in a region |
| Zone | `us-central1-a` | Single datacenter |

**For Data Engineers:** BigQuery is multi-regional. Dataflow, Dataproc are zonal/regional. GCS can be regional, dual-region, or multi-regional.

## 1.2 GCP Service Categories (Data Engineering View)

| Category | Services |
|---|---|
| **Ingestion** | Pub/Sub, Datastream, Transfer Service, Storage Transfer |
| **Processing** | Dataflow, Dataproc, BigQuery (BQML, SQL), Cloud Functions |
| **Orchestration** | Cloud Composer (Airflow), Cloud Scheduler, Workflows |
| **Storage** | GCS, BigQuery, Bigtable, Firestore, Cloud SQL, Spanner |
| **Governance** | Dataplex, Cloud DLP, Data Catalog |
| **Security** | IAM, Secret Manager, VPC Service Controls, CMEK |
| **Observability** | Cloud Logging, Cloud Monitoring, Cloud Trace |
| **DevOps** | Cloud Build, Artifact Registry, Cloud Deploy |

## 1.3 GCP Networking Basics for Data Engineers

### VPC (Virtual Private Cloud)
- All GCP compute runs inside a VPC.
- **Subnets** are regional (unlike AWS where they're zonal).
- **Private Google Access**: Allows VMs without external IPs to reach GCP APIs.
- Always enable Private Google Access for data engineering workloads — Dataflow workers, Dataproc clusters should NOT have public IPs.

### VPC Service Controls
- Creates a **security perimeter** around GCP services.
- Prevents data exfiltration even if IAM is misconfigured.
- Example: BigQuery dataset in perimeter cannot be accessed from outside the perimeter, even with valid credentials.

### Shared VPC
- One host project owns the VPC; service projects (like data pipelines) use it.
- Common in enterprises — your Dataflow jobs run in your project but use central network.

---

# 2. BigQuery — Deep Dive

## 2.1 What is BigQuery?

BigQuery is a **serverless, fully managed, petabyte-scale data warehouse** on GCP. It separates compute from storage, uses columnar storage (Capacitor format), and executes queries using Dremel (distributed query engine).

**Key differentiators:**
- No infrastructure to manage
- Pay-per-query OR flat-rate pricing
- Columnar + compressed storage (massive scan performance)
- Built-in ML (`BQML`), geospatial, BI Engine
- Federated queries (query GCS, Bigtable, Cloud SQL, Spanner without loading data)

## 2.2 BigQuery Architecture

```
User SQL Query
      ↓
  Dremel Engine (Query Coordination)
      ↓
  ┌─────────────────────────────────┐
  │  Leaf Nodes (Compute — Slots)   │
  │  - Read from Colossus (Storage) │
  │  - Each node scans column data  │
  └─────────────────────────────────┘
      ↓
  Results aggregated, returned
```

### Slots
- A **slot** = unit of BigQuery compute (CPU + RAM + network).
- On-demand: automatically allocates slots based on query size.
- Flat-rate: purchase reserved slots (100-slot increments).
- A single large query can use thousands of slots simultaneously.

### Storage: Capacitor Format
- Proprietary columnar format optimized for BigQuery.
- Data is automatically **sharded** across many storage nodes.
- **Automatic compression** per column based on data type.
- **Dremel** reads only the columns needed for a query.

## 2.3 BigQuery Storage Concepts

### Datasets
- Logical container for tables and views.
- Has a **location** (regional or multi-regional) — cannot be changed after creation.
- IAM can be applied at dataset level.

### Tables Types

| Type | Description | Use Case |
|---|---|---|
| **Native Table** | Data stored in Capacitor format in BigQuery | Primary table type |
| **External Table** | Data in GCS, Bigtable, etc. | Data lake queries, avoid loading |
| **Materialized View** | Pre-computed, auto-refreshed results | Repeated aggregations |
| **View** | Saved SQL query | Abstraction layer |
| **Wildcard Table** | `project.dataset.table_*` | Sharded tables by date |

### Partitioning
Partitioning = physically splitting a table into segments. **Hugely reduces cost and query time.**

```sql
-- Ingestion-time partitioned (automatic, uses _PARTITIONTIME)
CREATE TABLE dataset.events
PARTITION BY DATE(_PARTITIONTIME)
AS SELECT * FROM source;

-- Column-based partitioning (best practice)
CREATE TABLE dataset.sales
PARTITION BY DATE(sale_date)
OPTIONS(
  partition_expiration_days=365,
  require_partition_filter=TRUE  -- Forces all queries to specify partition
)
AS SELECT * FROM source;

-- Integer-range partitioning (for non-date columns)
CREATE TABLE dataset.customer_segments
PARTITION BY RANGE_BUCKET(customer_id, GENERATE_ARRAY(0, 1000000, 10000))
AS SELECT * FROM source;
```

**Interview Tip:** Always partition large tables. `require_partition_filter=TRUE` prevents full table scans — critical in enterprise settings to control costs.

### Clustering
Clustering = sorted order within each partition. **Further reduces data scanned.**

```sql
CREATE TABLE dataset.sales
PARTITION BY DATE(sale_date)
CLUSTER BY region, product_category, customer_id
AS SELECT * FROM source;
```

**Rules:**
- Up to 4 cluster columns (order matters — most selective first).
- Clustering is **automatic** — BQ maintains cluster order as data is inserted.
- Unlike partitioning, clustering doesn't create hard boundaries — BQ uses **block pruning**.

**Partitioning vs Clustering Decision:**
| Scenario | Choice |
|---|---|
| Filter on date/timestamp | Partition |
| Filter on high-cardinality string (region, category) | Cluster |
| Both date + string filters | Partition by date + Cluster by string |
| Very small tables (<1GB) | Neither (overhead not worth it) |

## 2.4 BigQuery SQL — Advanced Patterns

### Window Functions
```sql
-- Running total
SELECT
  sale_date,
  region,
  amount,
  SUM(amount) OVER (
    PARTITION BY region
    ORDER BY sale_date
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS running_total,

  -- Lag/Lead
  LAG(amount, 1) OVER (PARTITION BY region ORDER BY sale_date) AS prev_day_amount,

  -- Rank
  RANK() OVER (PARTITION BY region ORDER BY amount DESC) AS rank_in_region,
  DENSE_RANK() OVER (PARTITION BY region ORDER BY amount DESC) AS dense_rank,

  -- NTILE
  NTILE(4) OVER (ORDER BY amount) AS quartile

FROM sales;
```

### ARRAY and STRUCT (Nested/Repeated Fields)
BigQuery natively handles nested data — extremely efficient vs JOINs.

```sql
-- Creating nested data
SELECT
  customer_id,
  ARRAY_AGG(
    STRUCT(order_id, order_date, amount)
    ORDER BY order_date DESC
    LIMIT 10
  ) AS recent_orders
FROM orders
GROUP BY customer_id;

-- Querying nested data
SELECT
  customer_id,
  order.order_id,
  order.amount
FROM customers,
UNNEST(recent_orders) AS order  -- Flattens the array
WHERE order.amount > 1000;
```

### WITH ROLLUP / CUBE (Aggregation Extensions)
```sql
-- ROLLUP: hierarchical subtotals
SELECT
  region,
  country,
  city,
  SUM(sales) AS total_sales
FROM sales_data
GROUP BY ROLLUP(region, country, city);
-- Generates: (region, country, city), (region, country), (region), ()

-- CUBE: all combinations
GROUP BY CUBE(region, country, product_category);
```

### MERGE Statement (UPSERT)
```sql
MERGE dataset.target_table T
USING dataset.staging_table S
ON T.customer_id = S.customer_id

WHEN MATCHED AND S.action = 'DELETE' THEN
  DELETE

WHEN MATCHED THEN
  UPDATE SET
    T.name = S.name,
    T.email = S.email,
    T.updated_at = CURRENT_TIMESTAMP()

WHEN NOT MATCHED BY TARGET THEN
  INSERT (customer_id, name, email, created_at)
  VALUES (S.customer_id, S.name, S.email, CURRENT_TIMESTAMP())

WHEN NOT MATCHED BY SOURCE THEN
  UPDATE SET T.is_active = FALSE;
```

### INFORMATION_SCHEMA (Metadata Queries)
```sql
-- All tables in a dataset
SELECT * FROM dataset.INFORMATION_SCHEMA.TABLES;

-- Column details
SELECT * FROM dataset.INFORMATION_SCHEMA.COLUMNS
WHERE table_name = 'my_table';

-- Query history (cost analysis)
SELECT
  job_id,
  user_email,
  query,
  total_bytes_processed,
  total_bytes_billed,
  total_slot_ms,
  TIMESTAMP_DIFF(end_time, start_time, SECOND) AS duration_seconds,
  creation_time
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
ORDER BY total_bytes_processed DESC
LIMIT 50;
```

## 2.5 BigQuery Performance Optimization

### Query Anti-Patterns to Avoid
```sql
-- ❌ BAD: SELECT *
SELECT * FROM big_table WHERE date = '2024-01-01';

-- ✅ GOOD: Select only needed columns
SELECT customer_id, amount, status FROM big_table WHERE date = '2024-01-01';

-- ❌ BAD: Filtering on non-partitioned column
SELECT * FROM sales WHERE UPPER(region) = 'US';

-- ✅ GOOD: Avoid transforms on filter columns
SELECT * FROM sales WHERE region = 'US';

-- ❌ BAD: Self-join on large table
SELECT a.*, b.name FROM orders a JOIN orders b ON a.customer_id = b.customer_id;

-- ✅ GOOD: Use window functions or CTEs instead of self-joins
SELECT *, FIRST_VALUE(name) OVER (PARTITION BY customer_id) AS customer_name
FROM orders;
```

### Slot Utilization & Skew
- **Data skew** = one partition/key has disproportionately more data → one slot becomes bottleneck.
- Diagnose with: `EXPLAIN` or BigQuery Job information (shuffle size per stage).
- Fix with: salt keys, approximate aggregations, or pre-aggregating skewed keys.

```sql
-- Detecting skew: check row distribution
SELECT partition_id, row_count
FROM dataset.INFORMATION_SCHEMA.PARTITIONS
WHERE table_name = 'events'
ORDER BY row_count DESC;
```

### Materialized Views for Repeated Aggregations
```sql
CREATE MATERIALIZED VIEW dataset.daily_sales_mv
PARTITION BY sale_date
CLUSTER BY region
AS
SELECT
  DATE(sale_timestamp) AS sale_date,
  region,
  product_category,
  SUM(amount) AS total_amount,
  COUNT(*) AS transaction_count
FROM dataset.sales
GROUP BY 1, 2, 3;
-- BQ auto-refreshes this within 5 minutes of base table changes
-- Queries on base table automatically use the MV if query matches
```

## 2.6 BigQuery Data Ingestion Patterns

### Batch Loading
```python
from google.cloud import bigquery

client = bigquery.Client()

job_config = bigquery.LoadJobConfig(
    source_format=bigquery.SourceFormat.PARQUET,
    write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    schema_update_options=[
        bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION,
        bigquery.SchemaUpdateOption.ALLOW_FIELD_RELAXATION,
    ],
    time_partitioning=bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="event_date",
        expiration_ms=365 * 24 * 60 * 60 * 1000  # 1 year
    ),
    clustering_fields=["region", "event_type"],
    destination_table_description="Raw events from CDM pipeline"
)

load_job = client.load_table_from_uri(
    "gs://my-bucket/data/events/2024-01-01/*.parquet",
    "project.dataset.events",
    job_config=job_config
)
load_job.result()  # Wait for completion
print(f"Loaded {load_job.output_rows} rows")
```

### Streaming Inserts
```python
# Use for low-latency, real-time inserts
# Note: streaming buffer is NOT immediately queryable for free tier
# Best Practice: batch streaming inserts in groups of 500-1000 rows

rows_to_insert = [
    {"customer_id": 1, "event": "click", "timestamp": "2024-01-01T10:00:00"},
    {"customer_id": 2, "event": "purchase", "timestamp": "2024-01-01T10:00:01"},
]

errors = client.insert_rows_json(
    "project.dataset.events",
    rows_to_insert,
    row_ids=[f"row_{i}" for i in range(len(rows_to_insert))]  # Deduplication
)
if errors:
    raise Exception(f"Streaming insert errors: {errors}")
```

### BigQuery Storage Write API (Modern Approach)
```python
# Storage Write API — replaces streaming inserts
# Supports EXACTLY_ONCE semantics, transactions, schema updates

from google.cloud.bigquery_storage_v1 import BigQueryWriteClient, types

write_client = BigQueryWriteClient()
parent = write_client.table_path("project", "dataset", "table")

# COMMITTED mode (immediate visibility) or PENDING (batched commit)
write_stream = write_client.create_write_stream(
    parent=parent,
    write_stream=types.WriteStream(type_=types.WriteStream.Type.COMMITTED)
)
```

## 2.7 BigQuery Cost Management

| Strategy | Details |
|---|---|
| **Partition pruning** | Always filter on partition column |
| **Column selection** | Never `SELECT *` on wide tables |
| **Materialized Views** | Avoid re-computing same aggregations |
| **Flat-rate pricing** | >5TB/day queries → flat rate cheaper |
| **Table expiration** | Auto-delete staging/temp tables |
| **Authorized views** | Share aggregated data, not raw |
| **BI Engine** | Cache frequently accessed dashboards |
| **Cost labels** | Tag queries with team/project labels for chargeback |

```sql
-- Estimate query cost BEFORE running (dry run)
-- In Python:
job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
query_job = client.query("SELECT ...", job_config=job_config)
print(f"Estimated bytes: {query_job.total_bytes_processed}")
print(f"Estimated cost: ${query_job.total_bytes_processed / 1e12 * 5:.4f}")
```

## 2.8 BigQuery Security

### Row-Level Security
```sql
-- Create row access policy (CMEK-protected dataset)
CREATE ROW ACCESS POLICY americas_filter
ON dataset.sales_global
GRANT TO ("group:americas-team@company.com")
FILTER USING (region = 'Americas');

-- Users in americas-team only see Americas rows
-- No policy = no rows visible (default deny)
```

### Column-Level Security (Policy Tags)
```sql
-- Assign policy tag to sensitive columns
-- In schema, add policy_tags to columns:
ALTER TABLE dataset.customers
ALTER COLUMN ssn SET OPTIONS (
  policy_tags='projects/proj/locations/us/taxonomies/123/policyTags/456'
);
-- Users need Fine-Grained Reader role on the policy tag to see column
-- Others see NULL for that column
```

### Data Masking
```sql
-- Built-in masking rules available:
-- SHA256 hash, default masking (NULL/0/""), last 4 chars, etc.
-- Applied via Column-level security + masking rules in Data Catalog
```

---

# 3. Cloud Storage (GCS)

## 3.1 Overview

Google Cloud Storage is **object storage** — not a file system, not a database. Objects are immutable; you overwrite by creating a new version.

**Key concepts:**
- **Bucket**: namespace for objects (globally unique name)
- **Object**: file + metadata, max 5TB per object
- **Bucket-level vs Object-level IAM**: prefer uniform bucket-level access

## 3.2 Storage Classes

| Class | Use Case | Min Duration | Access Latency |
|---|---|---|---|
| **Standard** | Frequently accessed, hot data | None | Milliseconds |
| **Nearline** | ~Monthly access (backups) | 30 days | Milliseconds |
| **Coldline** | ~Quarterly access | 90 days | Milliseconds |
| **Archive** | Yearly access (compliance) | 365 days | Milliseconds |

**Note:** All classes have millisecond latency — difference is **storage cost vs retrieval cost**.

### Autoclass
```
Automatically transitions objects between storage classes based on access patterns.
No need to set lifecycle rules manually.
Objects start at Standard, move to Nearline → Coldline → Archive if not accessed.
```

## 3.3 Lifecycle Management

```json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 30, "matchesStorageClass": ["STANDARD"]}
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {"age": 90}
      },
      {
        "action": {"type": "Delete"},
        "condition": {"age": 365, "isLive": false}
      },
      {
        "action": {"type": "Delete"},
        "condition": {
          "numNewerVersions": 3,
          "matchesPrefix": ["temp/", "staging/"]
        }
      }
    ]
  }
}
```

## 3.4 GCS for Data Engineering

### Data Lake Organization (Best Practice)
```
gs://company-data-lake/
├── raw/                          # Landing zone (immutable)
│   ├── source=teradata/
│   │   ├── table=customers/
│   │   │   ├── year=2024/month=01/day=01/
│   │   │   │   └── customers_20240101.parquet
├── curated/                      # Cleaned, validated
│   ├── domain=finance/
│   │   ├── table=transactions/
│   │   │   ├── year=2024/month=01/
├── processed/                    # Aggregated, analytics-ready
├── temp/                         # Pipeline temp files (short lifecycle)
└── archive/                      # Historical, compressed
```

### Hive-Partitioned Paths
When using Dataflow or Dataproc to write data, use Hive-style partitioning so BigQuery external tables and tools like Spark can auto-discover partitions:
```
gs://bucket/table/year=2024/month=01/day=15/hour=10/data.parquet
```

### GCS + BigQuery Integration
```python
# External table pointing to GCS
# BigQuery reads directly from GCS (no data movement)
table = bigquery.Table("project.dataset.external_events")
external_config = bigquery.ExternalConfig("PARQUET")
external_config.source_uris = ["gs://my-bucket/raw/events/*.parquet"]
external_config.hive_partitioning_options = bigquery.HivePartitioningOptions(
    mode="AUTO",  # AUTO detects year=, month=, day= patterns
    source_uri_prefix="gs://my-bucket/raw/events/"
)
table.external_data_configuration = external_config
client.create_table(table)
```

## 3.5 GCS Performance & Best Practices

### Parallel Uploads (Composite Objects)
```python
from google.cloud.storage import Client, transfer_manager

storage_client = Client()
bucket = storage_client.bucket("my-bucket")

# Upload large file with parallel composite uploads
blob = bucket.blob("large-file.parquet")
blob.upload_from_filename(
    "local-large-file.parquet",
    num_retries=3
)

# For very large files, use transfer_manager
transfer_manager.upload_many_from_filenames(
    bucket,
    filenames=["file1.parquet", "file2.parquet"],
    max_workers=8,
    source_directory="/data/"
)
```

### Naming Best Practices
- **Avoid sequential prefixes** (`file_0001`, `file_0002`) — GCS shards by prefix, sequential names → hotspot.
- Use **random/hashed prefixes** or date-based prefixes for high-throughput writes.
- Good: `events/2024-01-15/abc123-events.parquet` (date + UUID)
- Bad: `events/000001.parquet`, `events/000002.parquet`

### Signed URLs (Temporary Access)
```python
from datetime import timedelta

blob = bucket.blob("sensitive-report.pdf")
url = blob.generate_signed_url(
    version="v4",
    expiration=timedelta(hours=1),
    method="GET"
)
# Share this URL — expires after 1 hour, no auth needed
```

## 3.6 GCS Security

### Uniform Bucket-Level Access
```
Always enable this. It disables ACLs and forces IAM-only access.
IAM policies are easier to audit than per-object ACLs.
```

### Customer-Managed Encryption Keys (CMEK)
```python
# Bucket encrypted with Cloud KMS key
bucket = storage_client.bucket("encrypted-bucket")
bucket.default_kms_key_name = "projects/my-proj/locations/us/keyRings/my-ring/cryptoKeys/my-key"
bucket.create()
# All objects written to this bucket are encrypted with your KMS key
# You control key rotation and revocation
```

### VPC Service Controls with GCS
- Lock down GCS to only be accessible from within your VPC perimeter.
- Prevents data exfiltration even if credentials are stolen.

---

# 4. Cloud Dataflow (Apache Beam)

## 4.1 What is Dataflow?

Cloud Dataflow is a **fully managed, serverless execution engine for Apache Beam pipelines**. It handles:
- Auto-scaling workers
- Work distribution and rebalancing
- Fault tolerance (automatic retry)
- Windowing, watermarks (for streaming)

**Apache Beam** is the programming model (SDK). **Dataflow** is the runner.

Other runners: Spark, Flink, Direct (local testing).

## 4.2 Core Apache Beam Concepts

### Pipeline, PCollection, PTransform
```python
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions

options = PipelineOptions([
    '--runner=DataflowRunner',
    '--project=my-project',
    '--region=us-central1',
    '--temp_location=gs://my-bucket/temp/',
    '--staging_location=gs://my-bucket/staging/',
    '--job_name=my-pipeline',
    '--max_num_workers=100',
    '--worker_machine_type=n1-standard-4',
])

with beam.Pipeline(options=options) as p:
    # PCollection = distributed, immutable collection of data
    lines = (
        p
        | 'ReadFromGCS' >> beam.io.ReadFromText('gs://bucket/input/*.csv')
        | 'ParseCSV' >> beam.Map(parse_csv_row)
        | 'FilterValid' >> beam.Filter(lambda row: row['amount'] > 0)
        | 'TransformData' >> beam.Map(transform_row)
        | 'WriteToBigQuery' >> beam.io.WriteToBigQuery(
            table='project:dataset.table',
            schema='customer_id:INTEGER,amount:FLOAT,event_date:DATE',
            write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
            create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED
        )
    )
```

### ParDo and DoFn (Core Processing)
```python
class EnrichCustomerFn(beam.DoFn):
    """DoFn for complex element-wise processing."""

    def setup(self):
        """Called once per worker. Initialize connections, load models."""
        self.db_client = DatabaseClient()  # One connection per worker
        self.enrichment_cache = {}

    def process(self, element, timestamp=beam.DoFn.TimestampParam):
        """
        Called once per element.
        Can yield 0, 1, or many output elements.
        """
        customer_id = element['customer_id']

        # Lookup enrichment data
        if customer_id not in self.enrichment_cache:
            self.enrichment_cache[customer_id] = self.db_client.lookup(customer_id)

        enriched = {**element, **self.enrichment_cache[customer_id]}
        yield enriched

    def teardown(self):
        """Cleanup per worker."""
        self.db_client.close()

# Usage
enriched = records | 'Enrich' >> beam.ParDo(EnrichCustomerFn())
```

### Side Inputs (Broadcasting Small Data)
```python
# Load reference data once (small dataset)
ref_data = (
    p
    | 'ReadRefData' >> beam.io.ReadFromText('gs://bucket/ref_data.json')
    | 'ParseRef' >> beam.Map(json.loads)
)

# Use as side input in another transform
def enrich_with_ref(element, ref_data_dict):
    key = element['product_id']
    ref = ref_data_dict.get(key, {})
    return {**element, 'product_name': ref.get('name')}

enriched = (
    transactions
    | 'EnrichProducts' >> beam.Map(
        enrich_with_ref,
        ref_data_dict=beam.pvalue.AsDict(ref_data)  # Broadcast as dict
    )
)
```

### Windowing (Streaming)
```python
# Tumbling window (fixed, non-overlapping)
windowed = (
    events
    | 'ApplyWindow' >> beam.WindowInto(
        beam.window.FixedWindows(60)  # 60-second windows
    )
    | 'AggregatePerWindow' >> beam.CombinePerKey(sum)
)

# Sliding window (overlapping)
beam.WindowInto(beam.window.SlidingWindows(size=60, period=30))  # 60s window, every 30s

# Session window (gap-based)
beam.WindowInto(beam.window.Sessions(gap_size=600))  # New window after 10min gap

# Global window (entire stream as one window)
beam.WindowInto(beam.window.GlobalWindows())
```

### Watermarks and Late Data
```python
# Watermark tells Dataflow "data up to time T has arrived"
# Late data = arrives after watermark has passed window end

windowed = (
    events
    | 'Timestamp' >> beam.Map(
        lambda x: beam.window.TimestampedValue(x, x['event_time'])
    )
    | 'Window' >> beam.WindowInto(
        beam.window.FixedWindows(60),
        trigger=beam.trigger.AfterWatermark(
            late=beam.trigger.AfterCount(1)  # Emit late data as it arrives
        ),
        allowed_lateness=beam.window.Duration(seconds=3600),  # Accept up to 1hr late
        accumulation_mode=beam.trigger.AccumulationMode.ACCUMULATING
    )
)
```

## 4.3 Dataflow Templates

### Flex Templates (Modern Approach)
```
Flex Templates package your pipeline as a Docker container.
Users pass runtime parameters without needing the source code.

Structure:
  my-pipeline/
  ├── Dockerfile
  ├── pipeline.py
  ├── metadata.json   ← parameter definitions
  └── requirements.txt

Build:
  gcloud dataflow flex-template build gs://bucket/templates/my-pipeline.json \
    --image-gcr-path gcr.io/project/my-pipeline:latest \
    --sdk-language PYTHON \
    --flex-template-base-image PYTHON3 \
    --py-path pipeline.py \
    --metadata-file metadata.json

Run:
  gcloud dataflow flex-template run my-job \
    --template-file-gcs-location gs://bucket/templates/my-pipeline.json \
    --region us-central1 \
    --parameters inputTable=project:dataset.source,outputTable=project:dataset.dest
```

## 4.4 Dataflow Use Cases & Patterns

| Pattern | Description | Example |
|---|---|---|
| **Batch ETL** | Read GCS/BQ → transform → write BQ | Daily data loads |
| **Streaming Ingestion** | Pub/Sub → transform → BigQuery | Real-time event processing |
| **Change Data Capture** | Datastream → Pub/Sub → Dataflow → BQ | DB replication |
| **Data Validation** | Read BQ → validate → write errors to BQ | Data quality checks |
| **Aggregation** | Stream → window → aggregate → BQ | Metrics computation |

## 4.5 Dataflow vs Dataproc — When to Use Which

| Criterion | Dataflow | Dataproc |
|---|---|---|
| **Programming model** | Apache Beam | Apache Spark / Hadoop |
| **Scaling** | Fully auto, serverless | Manual (autoscaling available) |
| **Streaming** | First-class | Spark Streaming (less mature) |
| **Existing Spark code** | Rewrite needed | Run as-is |
| **Startup time** | 3-5 min | 90s-3min |
| **Cost model** | Per vCPU-sec + data | Per cluster-hour |
| **SQL support** | Via Beam SQL | Spark SQL, Hive |
| **Maintenance** | Zero (fully managed) | Some (cluster configs) |

**Rule of thumb:** New pipelines → Dataflow. Migrating existing Spark/Hive → Dataproc.

---

# 5. Cloud Dataproc (Managed Spark/Hadoop)

## 5.1 What is Dataproc?

Dataproc is a **managed Apache Spark and Hadoop service**. It provisions clusters in 90 seconds, integrates natively with GCS/BigQuery, and supports spot/preemptible workers for cost reduction.

**Why Dataproc over self-managed Spark:**
- Cluster creation in 90 seconds
- Native GCS connector (treats GCS like HDFS)
- Pre-installed: Spark, Hadoop, Hive, Pig, Tez, Jupyter, Zeppelin
- Automatic cluster deletion after job completion (ephemeral clusters)

## 5.2 Cluster Architecture

```
Dataproc Cluster
├── Master Node(s)         ← YARN ResourceManager, HDFS NameNode
│   └── HA: 3 masters      ← For production
├── Primary Worker Nodes   ← YARN NodeManagers, HDFS DataNodes
└── Preemptible Workers    ← YARN only (no HDFS), can be reclaimed
    └── Use for: Stateless processing (GCS-backed pipelines)
```

### Ephemeral vs Persistent Clusters

**Ephemeral (recommended):**
```python
# Airflow operator to create cluster, run job, delete cluster
from airflow.providers.google.cloud.operators.dataproc import (
    DataprocCreateClusterOperator,
    DataprocSubmitJobOperator,
    DataprocDeleteClusterOperator
)

create_cluster = DataprocCreateClusterOperator(
    task_id="create_cluster",
    cluster_name="spark-etl-{{ ds_nodash }}",
    project_id="my-project",
    region="us-central1",
    cluster_config={
        "master_config": {
            "num_instances": 1,
            "machine_type_uri": "n1-standard-4",
            "disk_config": {"boot_disk_size_gb": 100}
        },
        "worker_config": {
            "num_instances": 4,
            "machine_type_uri": "n1-standard-8",
            "disk_config": {"boot_disk_size_gb": 200}
        },
        "secondary_worker_config": {
            "num_instances": 8,  # Preemptible workers
            "is_preemptible": True
        },
        "software_config": {
            "image_version": "2.1-debian11",
            "optional_components": ["JUPYTER", "ZEPPELIN"]
        },
        "gce_cluster_config": {
            "service_account": "dataproc-sa@project.iam.gserviceaccount.com",
            "service_account_scopes": ["https://www.googleapis.com/auth/cloud-platform"],
            "subnetwork_uri": "projects/host-proj/regions/us-central1/subnetworks/data-subnet",
            "internal_ip_only": True  # Security best practice
        }
    }
)
```

## 5.3 PySpark on Dataproc — Patterns

### Reading from GCS and Writing to BigQuery
```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import *

spark = SparkSession.builder \
    .appName("CustomerETL") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .getOrCreate()

# Read Parquet from GCS (gs:// treated like HDFS)
df = spark.read \
    .option("basePath", "gs://bucket/raw/events/") \
    .parquet("gs://bucket/raw/events/year=2024/month=01/")

# Schema enforcement
schema = StructType([
    StructField("customer_id", LongType(), nullable=False),
    StructField("event_type", StringType(), nullable=True),
    StructField("amount", DoubleType(), nullable=True),
    StructField("event_timestamp", TimestampType(), nullable=True),
])

# Transformations
transformed = df \
    .withColumn("event_date", F.to_date("event_timestamp")) \
    .withColumn("amount_usd", F.when(F.col("currency") == "EUR",
                                      F.col("amount") * 1.1)
                               .otherwise(F.col("amount"))) \
    .filter(F.col("amount") > 0) \
    .dropDuplicates(["customer_id", "event_timestamp"])

# Write to BigQuery
transformed.write \
    .format("bigquery") \
    .option("table", "project:dataset.events") \
    .option("temporaryGcsBucket", "my-temp-bucket") \
    .option("partitionField", "event_date") \
    .option("clusteredFields", "event_type,region") \
    .mode("append") \
    .save()
```

### Performance Tuning
```python
# Adaptive Query Execution (Spark 3.x)
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")

# Proper partitioning
df_repartitioned = df.repartition(200, "customer_id")  # By column (hash-based)
df_coalesced = df.coalesce(10)  # Reduce partitions without shuffle

# Broadcast join for small tables (<= 10MB)
from pyspark.sql.functions import broadcast
result = large_df.join(broadcast(small_df), "customer_id")

# Caching for multiple uses
df.cache()  # Or persist(StorageLevel.MEMORY_AND_DISK)
df.count()  # Trigger cache
# Use df for multiple downstream operations
df.unpersist()  # Free memory when done

# Checkpointing for long lineages
spark.sparkContext.setCheckpointDir("gs://bucket/checkpoints/")
df.checkpoint()
```

### Spark SQL with Hive Metastore
```python
# Dataproc includes Hive metastore
spark.sql("CREATE DATABASE IF NOT EXISTS analytics")
spark.sql("""
    CREATE TABLE IF NOT EXISTS analytics.customer_events (
        customer_id BIGINT,
        event_type STRING,
        amount DOUBLE,
        event_date DATE
    )
    USING PARQUET
    PARTITIONED BY (event_date)
    LOCATION 'gs://bucket/processed/customer_events/'
""")

spark.sql("MSCK REPAIR TABLE analytics.customer_events")  # Discover partitions
spark.sql("SELECT * FROM analytics.customer_events WHERE event_date = '2024-01-01'").show()
```

## 5.4 Dataproc Serverless

A newer option — submit Spark jobs **without managing clusters**:
```bash
gcloud dataflow batches submit spark \
  --project=my-project \
  --region=us-central1 \
  --jars=gs://bucket/jars/my-pipeline.jar \
  --class=com.company.SparkJob \
  -- arg1 arg2

# Or for PySpark:
gcloud dataproc batches submit pyspark \
  gs://bucket/scripts/my_job.py \
  --region=us-central1 \
  -- --input gs://bucket/input/ --output gs://bucket/output/
```

---

# 6. Cloud Composer / Apache Airflow

## 6.1 What is Cloud Composer?

Cloud Composer is a **managed Apache Airflow service**. It handles:
- Airflow infrastructure (web server, scheduler, workers, database)
- Auto-scaling workers
- GKE-based (Composer 2) or GKE Autopilot (Composer 3)
- Native GCP integrations

## 6.2 Core Airflow Concepts

### DAG Structure
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.providers.google.cloud.operators.dataproc import (
    DataprocCreateClusterOperator, DataprocSubmitJobOperator, DataprocDeleteClusterOperator
)
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta

# DAG-level defaults
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=30),
    'email_on_failure': True,
    'email': ['de-team@company.com'],
    'execution_timeout': timedelta(hours=6),
    'sla': timedelta(hours=8),  # Alert if not complete in 8 hours
}

with DAG(
    dag_id='cdm_teradata_to_bigquery',
    default_args=default_args,
    description='Daily Teradata to BigQuery migration',
    schedule_interval='0 2 * * *',  # 2 AM daily
    start_date=datetime(2024, 1, 1),
    catchup=False,      # IMPORTANT: Don't backfill on deploy
    max_active_runs=1,  # Prevent overlapping runs
    tags=['cdm', 'teradata', 'bigquery', 'batch'],
    doc_md="""
    ## CDM Teradata to BigQuery Pipeline
    Migrates daily data from Teradata source to BigQuery.
    SLA: 8 hours. Contact: de-team@company.com
    """
) as dag:
    pass
```

### Key Operators for Data Engineering
```python
# 1. BigQuery Operator
bq_transform = BigQueryInsertJobOperator(
    task_id='transform_data',
    configuration={
        "query": {
            "query": """
                INSERT INTO `project.dataset.target`
                SELECT * FROM `project.dataset.staging`
                WHERE DATE(created_at) = '{{ ds }}'
            """,
            "useLegacySql": False,
            "writeDisposition": "WRITE_APPEND",
            "destinationTable": {
                "projectId": "project",
                "datasetId": "dataset",
                "tableId": "target${{ ds_nodash }}"
            }
        }
    },
    location='US',
)

# 2. GCS to BigQuery
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator

load_to_bq = GCSToBigQueryOperator(
    task_id='load_gcs_to_bq',
    bucket='my-bucket',
    source_objects=['raw/events/{{ ds }}/*.parquet'],
    destination_project_dataset_table='project.dataset.events${{ ds_nodash }}',
    source_format='PARQUET',
    write_disposition='WRITE_TRUNCATE',
    autodetect=True,
    bigquery_conn_id='google_cloud_default',
)

# 3. Dataflow
from airflow.providers.google.cloud.operators.dataflow import DataflowCreatePythonJobOperator

run_dataflow = DataflowCreatePythonJobOperator(
    task_id='run_dataflow_pipeline',
    py_file='gs://bucket/pipelines/etl_pipeline.py',
    job_name='etl-{{ ds_nodash }}',
    options={
        'project': 'my-project',
        'region': 'us-central1',
        'temp_location': 'gs://bucket/temp/',
        'input': 'gs://bucket/raw/{{ ds }}/',
        'output': 'project:dataset.processed${{ ds_nodash }}',
    },
    dataflow_default_options={
        'project': 'my-project',
    }
)

# 4. Sensor (wait for upstream data)
from airflow.providers.google.cloud.sensors.gcs import GCSObjectExistenceSensor

wait_for_file = GCSObjectExistenceSensor(
    task_id='wait_for_source_file',
    bucket='source-bucket',
    object='raw/events/{{ ds }}/SUCCESS',  # Wait for _SUCCESS flag
    timeout=3600,  # Fail after 1 hour
    poke_interval=60,  # Check every 60 seconds
    mode='reschedule',  # Release worker slot while waiting (IMPORTANT)
)
```

### XCom — Passing Data Between Tasks
```python
def extract_row_count(**context):
    """Task that returns a value via XCom."""
    client = bigquery.Client()
    result = client.query("SELECT COUNT(*) as cnt FROM dataset.staging").result()
    row_count = next(result).cnt
    return row_count  # Automatically pushed to XCom

def validate_row_count(**context):
    """Task that reads value from XCom."""
    ti = context['task_instance']
    row_count = ti.xcom_pull(task_ids='extract_row_count')
    if row_count < 1000:
        raise ValueError(f"Too few rows: {row_count}. Expected at least 1000.")

extract_task = PythonOperator(task_id='extract_row_count', python_callable=extract_row_count)
validate_task = PythonOperator(task_id='validate_row_count', python_callable=validate_row_count)
extract_task >> validate_task
```

### Dynamic DAGs (Task Mapping)
```python
# Composer 2 / Airflow 2.3+ — dynamic task mapping
@dag(schedule_interval='@daily', start_date=datetime(2024, 1, 1))
def dynamic_migration_dag():

    @task
    def get_tables_to_migrate():
        return ['customers', 'orders', 'products', 'transactions']

    @task
    def migrate_table(table_name: str):
        # Migration logic per table
        print(f"Migrating {table_name}")

    tables = get_tables_to_migrate()
    migrate_table.expand(table_name=tables)  # Creates parallel tasks dynamically

dag = dynamic_migration_dag()
```

## 6.3 Airflow Best Practices (Production)

### Idempotency
```python
# Every task must be safe to re-run.
# Use WRITE_TRUNCATE or partition-level writes instead of WRITE_APPEND

# BAD: Running twice doubles data
INSERT INTO table SELECT * FROM staging WHERE date = '{{ ds }}'

# GOOD: Idempotent — same result if run 5 times
INSERT OVERWRITE TABLE dataset.events PARTITION (event_date='{{ ds }}')
SELECT * FROM staging WHERE event_date = '{{ ds }}'

# In BigQuery — write to specific partition
destination_table='project.dataset.events${{ ds_nodash }}'
write_disposition='WRITE_TRUNCATE'  # Truncates that partition only
```

### Avoiding Pitfalls
```python
# 1. Never do heavy computation in top-level DAG code
# BAD: This runs on scheduler every heartbeat
result = expensive_db_query()  # ← Top-level code in DAG file

# GOOD: Wrap in operators/tasks

# 2. Use KubernetesPodOperator for custom environments
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator

run_custom = KubernetesPodOperator(
    task_id='run_custom_transform',
    name='custom-transform',
    namespace='composer-user-workloads',
    image='gcr.io/project/my-image:latest',
    arguments=['--date', '{{ ds }}'],
    env_vars={'PROJECT': 'my-project'},
    resources={'request_memory': '2G', 'request_cpu': '1'},
    get_logs=True,
)

# 3. connection_id for external systems
from airflow.hooks.base import BaseHook
conn = BaseHook.get_connection('teradata_prod')
# Store credentials in Airflow Connections, not in DAG code
```

## 6.4 Composer 2 Architecture

```
Composer 2 Environment
├── GKE Autopilot Cluster
│   ├── Airflow Scheduler Pod (high-availability, 2 schedulers)
│   ├── Airflow Webserver Pod
│   ├── Airflow Worker Pods (auto-scaled 0-N)
│   └── Redis Pod (Celery message broker)
├── Cloud SQL (Airflow metadata DB — PostgreSQL)
├── Cloud Storage Bucket (DAGs, logs, plugins, data)
└── Secret Manager (connections, variables)
```

### Environment Variables & Connections
```python
# Access Secret Manager from Airflow (Composer 2 native support)
# Add to Airflow config:
# [secrets]
# backend = airflow.providers.google.cloud.secrets.secret_manager.CloudSecretManagerBackend
# backend_kwargs = {"project_id": "my-project", "connections_prefix": "airflow-connections", "variables_prefix": "airflow-variables"}

# Then in DAG:
from airflow.hooks.base import BaseHook
conn = BaseHook.get_connection('my-db-connection')  # Fetched from Secret Manager
```

---

# 7. Pub/Sub — Streaming Messaging

## 7.1 What is Pub/Sub?

Cloud Pub/Sub is a **fully managed, serverless messaging service** for asynchronous, event-driven architectures. It's Google's equivalent to Apache Kafka (managed) or AWS SNS/SQS.

**Core concepts:**
- **Topic**: Channel where messages are published
- **Subscription**: Named resource attached to topic; consumers pull/push from subscription
- **Publisher**: Writes messages to topic
- **Subscriber**: Reads messages from subscription
- **Message**: Data (payload ≤ 10MB) + attributes (key-value metadata)

## 7.2 Delivery Semantics

| Feature | Detail |
|---|---|
| **At-least-once delivery** | Default — messages may be delivered multiple times |
| **Exactly-once** | Available with exactly-once subscriptions (higher cost) |
| **Ordering** | Ordering key → messages with same key delivered in order |
| **Retention** | Up to 7 days (configurable) |
| **Acknowledgement** | Consumer acks each message; unacked messages re-delivered |

## 7.3 Pull vs Push Subscriptions

### Pull (consumer-initiated)
```python
from google.cloud import pubsub_v1
from concurrent.futures import TimeoutError

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path("my-project", "my-subscription")

def callback(message):
    """Process each message."""
    try:
        data = json.loads(message.data.decode('utf-8'))
        attributes = message.attributes  # e.g., {"source": "teradata", "table": "customers"}

        # Process message
        process_event(data)

        message.ack()  # Acknowledge success
    except Exception as e:
        print(f"Error processing message: {e}")
        message.nack()  # Nack = re-deliver this message

# Subscribe with concurrency control
flow_control = pubsub_v1.types.FlowControl(max_messages=100)
streaming_pull_future = subscriber.subscribe(
    subscription_path,
    callback=callback,
    flow_control=flow_control
)

with subscriber:
    try:
        streaming_pull_future.result(timeout=300)
    except TimeoutError:
        streaming_pull_future.cancel()
```

### Push (Pub/Sub-initiated, sends to endpoint)
```
Pub/Sub → HTTPS POST → Cloud Run / Cloud Functions / App Engine

Use when:
- Consumer is a Cloud Run service or Cloud Function
- Want serverless processing triggered by messages
- Don't want to manage a pull loop
```

## 7.4 Pub/Sub → Dataflow (Streaming Pipeline)
```python
# Classic pattern: Pub/Sub → Dataflow → BigQuery
with beam.Pipeline(options=streaming_options) as p:
    messages = (
        p
        | 'ReadFromPubSub' >> beam.io.ReadFromPubSub(
            subscription='projects/proj/subscriptions/events-sub',
            with_attributes=True  # Include message attributes
        )
        | 'ParseMessages' >> beam.Map(parse_pubsub_message)
        | 'ApplyTimestamps' >> beam.Map(
            lambda x: beam.window.TimestampedValue(x, x['event_time'])
        )
        | 'WindowInto' >> beam.WindowInto(
            beam.window.FixedWindows(60),  # 1-minute windows
            trigger=beam.trigger.AfterWatermark(
                late=beam.trigger.AfterCount(1)
            ),
            allowed_lateness=beam.window.Duration(seconds=300),
            accumulation_mode=beam.trigger.AccumulationMode.ACCUMULATING
        )
        | 'AggregateByKey' >> beam.CombinePerKey(sum)
        | 'FormatForBQ' >> beam.Map(format_for_bigquery)
        | 'WriteToBigQuery' >> beam.io.WriteToBigQuery(
            table='project:dataset.streaming_aggregates',
            write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
        )
    )
```

## 7.5 Dead Letter Queue (DLQ) Pattern
```python
# Messages that fail processing → Dead Letter Topic
# Configure in subscription:
# dead_letter_policy:
#   dead_letter_topic: projects/proj/topics/events-dlq
#   max_delivery_attempts: 5

# Monitor DLQ for failed messages
# Process DLQ separately (alert, manual review, retry logic)
```

## 7.6 Pub/Sub vs Kafka — Interview Comparison

| Feature | Pub/Sub | Kafka (self-managed or Confluent) |
|---|---|---|
| Management | Fully managed | Self-managed or Confluent |
| Scaling | Automatic | Manual partition scaling |
| Retention | Up to 7 days | Configurable, can be forever |
| Replay | Up to 7 days (seek) | Full replay from any point |
| Ordering | Per ordering-key | Per partition |
| Cost | Per message | Per cluster-hour + storage |
| Ecosystem | GCP-native | Broad (Kafka Connect, ksqlDB) |

---

# 8. Cloud Functions & Cloud Run

## 8.1 Cloud Functions

**Event-driven, serverless functions.** Best for simple, short-running tasks triggered by events.

### Triggers
| Trigger | Use Case |
|---|---|
| HTTP | REST API endpoint |
| Pub/Sub | React to Pub/Sub message |
| GCS | File uploaded/deleted |
| Firestore | Document changed |
| Cloud Scheduler | Cron job |

### Example: GCS Trigger → BigQuery Load
```python
# Triggered when file lands in GCS
# functions/main.py

import functions_framework
from google.cloud import bigquery, storage
import json

@functions_framework.cloud_event
def on_gcs_upload(cloud_event):
    """Triggered by GCS object finalization."""
    data = cloud_event.data
    bucket_name = data["bucket"]
    file_name = data["name"]

    # Only process Parquet files in raw/ prefix
    if not file_name.startswith("raw/") or not file_name.endswith(".parquet"):
        print(f"Skipping {file_name}")
        return

    # Load to BigQuery
    client = bigquery.Client()
    table_id = "project.dataset.raw_events"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        autodetect=True,
    )

    uri = f"gs://{bucket_name}/{file_name}"
    load_job = client.load_table_from_uri(uri, table_id, job_config=job_config)
    load_job.result()

    print(f"Loaded {file_name} to {table_id}: {load_job.output_rows} rows")
```

### Gen 2 Cloud Functions (Current)
- Built on Cloud Run internally
- Up to **60 minutes** timeout (vs 9 min for Gen 1)
- Can handle **concurrent requests** (not just 1-at-a-time)
- Better cold start performance

## 8.2 Cloud Run

**Containerized, serverless compute.** Best for:
- Long-running processes
- Custom runtime environments
- HTTP APIs
- Complex dependencies (libraries, system packages)

### Cloud Run for Data Engineering
```python
# app.py — FastAPI service deployed on Cloud Run
from fastapi import FastAPI, BackgroundTasks
from google.cloud import bigquery, pubsub_v1
import uvicorn

app = FastAPI()
bq_client = bigquery.Client()

@app.post("/ingest")
async def ingest_data(payload: dict, background_tasks: BackgroundTasks):
    """Accept data, validate, and queue for BigQuery insertion."""
    validated = validate_payload(payload)
    background_tasks.add_task(insert_to_bigquery, validated)
    return {"status": "accepted", "message_id": payload.get("id")}

def insert_to_bigquery(data: dict):
    errors = bq_client.insert_rows_json("project.dataset.events", [data])
    if errors:
        raise Exception(f"BQ insert failed: {errors}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
```

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

### Cloud Run vs Cloud Functions

| Aspect | Cloud Functions | Cloud Run |
|---|---|---|
| Container control | No | Full |
| Language | Supported runtimes | Any |
| Timeout | 60 min (Gen 2) | 60 min (up to 24h for jobs) |
| Cold start | Faster | Slightly slower |
| Concurrency | Per instance | Per container (up to 1000) |
| Use case | Simple event handlers | Complex apps, APIs |

---

# 9. Cloud DLP, IAM, Secret Manager

## 9.1 Identity and Access Management (IAM)

### IAM Hierarchy
```
Permission: can do one action (bigquery.tables.getData)
Role: collection of permissions
  ├── Primitive: Owner, Editor, Viewer (too broad, avoid)
  ├── Predefined: roles/bigquery.dataViewer, roles/dataflow.developer
  └── Custom: your own role with specific permissions

Binding: "who has what role on what resource"
Policy: collection of bindings on a resource
```

### Key Predefined Roles for Data Engineering
| Role | Purpose |
|---|---|
| `roles/bigquery.dataEditor` | Read/write BQ data |
| `roles/bigquery.jobUser` | Run BQ jobs (needed alongside dataEditor) |
| `roles/bigquery.admin` | Full BQ control |
| `roles/storage.objectViewer` | Read GCS objects |
| `roles/storage.objectCreator` | Create GCS objects |
| `roles/dataflow.developer` | Create/manage Dataflow jobs |
| `roles/dataproc.editor` | Manage Dataproc clusters |
| `roles/iam.serviceAccountTokenCreator` | Impersonate service accounts |

### Service Accounts (Data Engineering)
```python
# Best practice: one service account per pipeline/workload
# Principle of least privilege

# Dataflow pipeline SA: needs to read GCS + write BigQuery
# gcloud projects add-iam-policy-binding my-project \
#   --member="serviceAccount:dataflow-sa@project.iam.gserviceaccount.com" \
#   --role="roles/dataflow.worker"
# Also needs: storage.objectViewer on source bucket, bigquery.dataEditor on target dataset

# Using service account in code (Workload Identity preferred for GKE/Composer)
import google.auth
credentials, project = google.auth.default()  # Uses attached SA automatically
```

### Workload Identity (for GKE/Composer)
```
Instead of downloading SA key files:
1. Create a GCP SA: pipeline-sa@project.iam.gserviceaccount.com
2. Create a Kubernetes SA: pipeline-ksa in namespace airflow
3. Bind them:
   gcloud iam service-accounts add-iam-policy-binding pipeline-sa@project.iam.gserviceaccount.com \
     --role=roles/iam.workloadIdentityUser \
     --member="serviceAccount:project.svc.id.goog[airflow/pipeline-ksa]"
4. Annotate the Kubernetes SA:
   kubectl annotate serviceaccount pipeline-ksa \
     iam.gke.io/gcp-service-account=pipeline-sa@project.iam.gserviceaccount.com

Result: Pods using pipeline-ksa automatically authenticate as pipeline-sa
No key files needed. Much more secure.
```

## 9.2 Cloud DLP (Data Loss Prevention)

Cloud DLP **inspects and de-identifies sensitive data** (PII, PCI, PHI, credentials).

### Common Use Cases in Data Engineering
1. **Inspect** data before loading to BigQuery (find SSNs, credit cards, etc.)
2. **De-identify** (mask/tokenize) PII in pipelines
3. **Profile** BigQuery datasets for sensitive data discovery
4. **Re-identify** with proper authorization for analytics

### Key Transformation Types
| Transformation | Description | Example |
|---|---|---|
| **Redact** | Remove value | `555-12-3456` → `` |
| **Replace** | Static replacement | `555-12-3456` → `[REDACTED]` |
| **Crypto hash** | Deterministic hash | `john@test.com` → `abc123def` |
| **Bucketing** | Range → bucket | Age `34` → `30-40` |
| **Date shift** | Shift date randomly | `2024-01-15` → `2023-11-20` |
| **Character mask** | Partial masking | `555-12-3456` → `XXX-XX-3456` |
| **Format-preserving encryption** | Tokenize, keep format | `4111111111111111` → `9876543210987654` |

### DLP in a Pipeline
```python
from google.cloud import dlp_v2

def inspect_and_deidentify(text: str, project_id: str) -> str:
    dlp = dlp_v2.DlpServiceClient()

    # Info types to detect
    info_types = [
        {"name": "US_SOCIAL_SECURITY_NUMBER"},
        {"name": "CREDIT_CARD_NUMBER"},
        {"name": "EMAIL_ADDRESS"},
        {"name": "PHONE_NUMBER"},
    ]

    # De-identification config
    deidentify_config = {
        "info_type_transformations": {
            "transformations": [
                {
                    "info_types": [{"name": "EMAIL_ADDRESS"}],
                    "primitive_transformation": {
                        "crypto_deterministic_config": {
                            "crypto_key": {
                                "kms_wrapped": {
                                    "wrapped_key": b"...",
                                    "crypto_key_name": "projects/proj/locations/us/keyRings/kr/cryptoKeys/dlp-key"
                                }
                            }
                        }
                    }
                },
                {
                    "primitive_transformation": {
                        "replace_with_info_type_config": {}  # Replace with [EMAIL_ADDRESS] etc.
                    }
                }
            ]
        }
    }

    item = {"value": text}
    response = dlp.deidentify_content(
        request={
            "parent": f"projects/{project_id}/locations/global",
            "deidentify_config": deidentify_config,
            "inspect_config": {"info_types": info_types},
            "item": item,
        }
    )
    return response.item.value
```

## 9.3 Secret Manager

Stores API keys, passwords, certificates securely with versioning and audit logging.

```python
from google.cloud import secretmanager

def get_secret(project_id: str, secret_id: str, version: str = "latest") -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Usage in pipeline
db_password = get_secret("my-project", "teradata-prod-password")
connection_string = f"terajdbc://host:1025/db;user=svc_account;password={db_password}"
```

---

# 10. Cloud Logging & Monitoring

## 10.1 Cloud Logging

**Centralized log management.** All GCP services write logs here automatically.

### Log Types
| Type | Source |
|---|---|
| **Audit Logs** | WHO did WHAT — data access, admin activity |
| **Data Access Logs** | BQ queries, GCS reads (must enable) |
| **Platform Logs** | Dataflow job logs, Dataproc cluster logs |
| **User-written Logs** | Your application code |

### Writing Structured Logs from Python
```python
import google.cloud.logging
import logging

# Setup structured logging
client = google.cloud.logging.Client()
client.setup_logging()

logger = logging.getLogger(__name__)

# Structured log entry
logger.info("Pipeline step completed", extra={
    "json_fields": {
        "step": "validation",
        "table": "customers",
        "rows_processed": 1500000,
        "rows_rejected": 42,
        "execution_date": "2024-01-15",
        "pipeline_id": "cdm-teradata-bq-20240115"
    }
})
```

### Log-Based Metrics
```python
# Create metric from logs (e.g., count of pipeline failures)
# gcloud logging metrics create pipeline_errors \
#   --description="Count of pipeline failures" \
#   --log-filter='
#     resource.type="dataflow_step"
#     severity=ERROR
#     jsonPayload.pipeline_id=~"cdm-.*"
#   '
```

### Log Export (Log Sinks)
```
Route logs to:
- Cloud Storage (archival, compliance)
- BigQuery (analysis)
- Pub/Sub (real-time processing, alerting)

Example: All BigQuery data access logs → BQ audit dataset → query who accessed what
```

## 10.2 Cloud Monitoring

### Custom Metrics
```python
from google.cloud import monitoring_v3
import time

def write_pipeline_metric(project_id: str, rows_processed: int, pipeline_name: str):
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project_id}"

    series = monitoring_v3.TimeSeries()
    series.metric.type = "custom.googleapis.com/pipeline/rows_processed"
    series.metric.labels["pipeline_name"] = pipeline_name
    series.resource.type = "global"

    now = time.time()
    seconds = int(now)
    nanos = int((now - seconds) * 10 ** 9)

    interval = monitoring_v3.TimeInterval(
        {"end_time": {"seconds": seconds, "nanos": nanos}}
    )
    point = monitoring_v3.Point(
        {"interval": interval, "value": {"int64_value": rows_processed}}
    )
    series.points = [point]

    client.create_time_series(name=project_name, time_series=[series])
```

### Alerting Policies
```yaml
# Alert when Dataflow pipeline fails
displayName: "Dataflow Pipeline Failure Alert"
conditions:
  - displayName: "Pipeline Error Count"
    conditionThreshold:
      filter: |
        resource.type="dataflow_step"
        AND metric.type="dataflow.googleapis.com/job/failed_element_count"
      comparison: COMPARISON_GT
      thresholdValue: 0
      duration: 60s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_SUM
notificationChannels:
  - "projects/my-project/notificationChannels/pagerduty-channel"
  - "projects/my-project/notificationChannels/slack-channel"
```

### Dashboards for Data Pipelines
Key metrics to monitor:
- BigQuery: job duration, slot utilization, bytes processed, failed jobs
- Dataflow: throughput (elements/sec), lag, worker count, failed elements
- Dataproc: cluster utilization, job duration, YARN queue depth
- Composer: DAG run duration, task failure rate, slot pool usage

---

# 11. Dataplex — Data Governance

## 11.1 What is Dataplex?

Dataplex is GCP's **unified data governance platform**. It organizes data across GCS and BigQuery into a logical hierarchy and provides:
- Data discovery and cataloging
- Automated metadata management
- Data quality checks
- Data lineage
- Access control at scale

### Hierarchy
```
Lake (e.g., "enterprise-data-lake")
├── Zone (e.g., "raw-zone", "curated-zone", "analytics-zone")
│   ├── Asset (GCS bucket or BigQuery dataset)
│   │   └── Tables/Objects (auto-discovered)
```

## 11.2 Data Quality with Dataplex

```yaml
# Data quality spec (YAML-based)
rules:
  - column: customer_id
    rule_type: NOT_NULL
    dimension: COMPLETENESS

  - column: amount
    rule_type: RANGE
    range_expectation:
      min_value: 0
      max_value: 1000000
    dimension: VALIDITY

  - column: email
    rule_type: REGEX
    regex_expectation:
      regex: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    dimension: VALIDITY

  - rule_type: ROW_CONDITION
    row_condition_expectation:
      sql_expression: "amount > 0 OR status = 'REFUND'"
    dimension: CONSISTENCY

  - rule_type: TABLE_CONDITION
    table_condition_expectation:
      sql_expression: "COUNT(*) > 1000"
    dimension: COMPLETENESS
```

## 11.3 Data Catalog Integration

```python
from google.cloud import datacatalog_v1

catalog_client = datacatalog_v1.DataCatalogClient()

# Search for tables with sensitive data tags
results = catalog_client.search_catalog(
    request={
        "scope": {"include_project_ids": ["my-project"]},
        "query": "type=TABLE tag:pii_data.contains_pii=true"
    }
)

# Attach business metadata tag
tag = datacatalog_v1.Tag()
tag.template = "projects/my-project/locations/us-central1/tagTemplates/data_classification"
tag.fields["data_owner"] = datacatalog_v1.TagField(string_value="finance-team@company.com")
tag.fields["classification"] = datacatalog_v1.TagField(enum_value={"display_name": "CONFIDENTIAL"})
tag.fields["pii_flag"] = datacatalog_v1.TagField(bool_value=True)

catalog_client.create_tag(parent=entry.name, tag=tag)
```

---

# 12. System Design Patterns on GCP

## 12.1 Batch Data Pipeline (Lambda Architecture)

```
Architecture: CDM Next-style enterprise batch ingestion

┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Source Systems  │────▶│   Landing Zone   │────▶│  Staging Layer   │
│                  │     │                  │     │                  │
│  - Teradata      │     │  GCS Raw Bucket  │     │  BigQuery        │
│  - Oracle        │     │  (immutable)     │     │  _staging tables │
│  - Hive          │     │                  │     │                  │
└─────────────────┘     └──────────────────┘     └──────────────────┘
         │                        │                        │
         │              ┌─────────┘                        │
         │         Dataproc/Dataflow                        │
         │         (extract + validate)              DQ Checks
         │                                                  │
                                                  ┌─────────┘
                                            ┌─────▼──────────────┐
                                            │  Curated Layer      │
                                            │  BigQuery           │
                                            │  (partitioned,      │
                                            │   clustered,        │
                                            │   MERGE'd)          │
                                            └─────────────────────┘
                                                       │
                                            Cloud Composer orchestrates entire flow
                                            Cloud DLP scans for PII before loading
                                            Cloud Monitoring alerts on failures
```

### Design Decisions to Discuss in Interview:
1. **Why GCS as landing zone?** Decouples ingestion from processing. Source can push to GCS independently. GCS is cheap, durable, and scalable.
2. **Why partitioning in BQ?** Partition by date + cluster by key columns reduces scan cost by 90%+.
3. **Why MERGE not INSERT?** Idempotent — safe to re-run without duplicates.
4. **Why Cloud Composer for orchestration?** Complex dependencies, retries, SLA monitoring, observability.
5. **Why DLP before loading?** Prevent PII from entering analytics layer unmasked.

## 12.2 Real-Time Streaming Architecture

```
Real-Time Event Processing

┌──────────┐    ┌─────────┐    ┌──────────────┐    ┌──────────────┐
│  Kafka   │───▶│ Pub/Sub │───▶│  Dataflow    │───▶│  BigQuery    │
│  (on-   │    │ (bridge)│    │  (Beam)      │    │  (streaming  │
│   prem)  │    │         │    │  - parse     │    │   buffer)    │
└──────────┘    └─────────┘    │  - validate  │    └──────────────┘
                               │  - window    │           │
                               │  - aggregate │    ┌──────▼──────┐
                               └──────────────┘    │  BI/Looker  │
                                      │            └─────────────┘
                               ┌──────▼──────┐
                               │ Pub/Sub DLQ │
                               │ (failures)  │
                               └─────────────┘

Latency target: < 60 seconds end-to-end
Throughput: millions of events/second (Pub/Sub auto-scales)
```

## 12.3 Multi-Source Data Migration (40PB Scale)

```
Pattern: Configuration-driven migration (CDM Next style)

Config DB (BigQuery or GCS)
├── migration_config table
│   ├── source_type: "teradata"
│   ├── source_table: "EDW.CUSTOMER_DIM"
│   ├── target_dataset: "curated"
│   ├── target_table: "customers"
│   ├── extraction_query: "SELECT * FROM EDW.CUSTOMER_DIM WHERE ..."
│   ├── partition_column: "LOAD_DATE"
│   ├── validation_query: "SELECT COUNT(*) FROM ..."
│   └── dlp_enabled: true

Composer DAG reads config → generates tasks dynamically → executes migration
├── For each table in config:
│   ├── Extract from source (Dataproc/JDBC)
│   ├── Write to GCS (raw/)
│   ├── DLP scan (if enabled)
│   ├── Load to BQ staging
│   ├── Validate row counts + checksums
│   └── Promote to curated (MERGE)
└── Audit log every step to BQ audit table
```

## 12.4 Data Lakehouse Architecture

```
Modern Lakehouse on GCP

┌─────────────────────────────────────────────────────────────┐
│                    Dataplex Lake                             │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐   │
│  │ Raw Zone    │  │ Curated Zone│  │ Analytics Zone    │   │
│  │             │  │             │  │                   │   │
│  │ GCS Bucket  │  │ GCS + BQ   │  │ BigQuery          │   │
│  │ (Parquet,   │  │ External   │  │ (native tables,   │   │
│  │  Avro, CSV) │  │ tables     │  │  materialized     │   │
│  │             │  │             │  │  views, BI Engine)│   │
│  └─────────────┘  └─────────────┘  └───────────────────┘   │
│                                                             │
│  Data Catalog (metadata, lineage, tags)                     │
│  DLP (PII scanning, masking)                                │
│  IAM (column-level, row-level security)                     │
└─────────────────────────────────────────────────────────────┘
```

## 12.5 CI/CD for Data Pipelines

```
Source Code (GitHub)
       │
       ├── PR → GitHub Actions / Cloud Build
       │          ├── Unit tests (pytest)
       │          ├── BigQuery SQL validation (dry run)
       │          ├── DAG import check (airflow dags test)
       │          └── Docker build + push to Artifact Registry
       │
       ├── Merge to main → Deploy to Dev
       │          ├── Terraform apply (infrastructure)
       │          ├── Deploy DAGs to Composer (GCS sync)
       │          ├── Deploy Dataflow templates
       │          └── Integration tests
       │
       └── Tag → Deploy to Prod (with approval gate)
```

```yaml
# .github/workflows/deploy_pipeline.yaml
name: Deploy Data Pipeline
on:
  push:
    branches: [main]
    paths: ['pipelines/**', 'dags/**']

jobs:
  test-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v1
        with:
          workload_identity_provider: "projects/123/locations/global/workloadIdentityPools/github/providers/github"
          service_account: "cicd-sa@project.iam.gserviceaccount.com"

      - name: Run Unit Tests
        run: pytest tests/ -v --coverage

      - name: Validate BigQuery SQL
        run: |
          for sql_file in sql/*.sql; do
            bq query --dry_run --nouse_legacy_sql "$(cat $sql_file)"
          done

      - name: Validate DAGs
        run: |
          pip install apache-airflow
          python -c "
          from airflow.models import DagBag
          bag = DagBag(dag_folder='dags/', include_examples=False)
          assert len(bag.import_errors) == 0, f'DAG errors: {bag.import_errors}'
          "

      - name: Deploy DAGs to Composer
        run: |
          gsutil -m rsync -r dags/ gs://composer-bucket/dags/

      - name: Build and Push Dataflow Template
        run: |
          docker build -t gcr.io/project/pipeline:$GITHUB_SHA .
          docker push gcr.io/project/pipeline:$GITHUB_SHA
          gcloud dataflow flex-template build \
            gs://bucket/templates/pipeline-$GITHUB_SHA.json \
            --image gcr.io/project/pipeline:$GITHUB_SHA \
            --sdk-language PYTHON
```

---

# 13. Practice Interview Questions

## 13.1 BigQuery Questions

**Q: You have a 10TB table queried 100 times/day. What optimizations would you apply?**

Answer framework:
1. Partition by date column (reduces scan per query)
2. Cluster by frequently-filtered columns
3. Use `require_partition_filter=TRUE`
4. Create materialized views for common aggregations
5. Consider BI Engine for dashboard queries
6. Use flat-rate pricing if query volume is high

---

**Q: Explain the difference between partitioning and clustering. When would you use each?**

Answer: Partitioning physically separates data into segments (files/directories). BigQuery skips entire partitions if the filter doesn't match. Clustering sorts data within each partition by up to 4 columns. BQ uses block-level pruning to skip blocks that don't contain matching values. Use partitioning for date/timestamp filters, clustering for high-cardinality string filters. Often combine: partition by date, cluster by region/user_id.

---

**Q: How do you handle slowly changing dimensions (SCD) in BigQuery?**

```sql
-- SCD Type 2: Keep history with valid_from/valid_to
MERGE `project.dataset.dim_customer` AS target
USING `project.dataset.staging_customer` AS source
ON target.customer_id = source.customer_id
  AND target.is_current = TRUE

WHEN MATCHED AND (
  target.email != source.email OR
  target.address != source.address
) THEN
  -- Expire old record
  UPDATE SET
    is_current = FALSE,
    valid_to = CURRENT_DATE(),
    updated_at = CURRENT_TIMESTAMP()

WHEN NOT MATCHED BY TARGET THEN
  -- Insert new record
  INSERT (customer_id, email, address, is_current, valid_from, valid_to)
  VALUES (source.customer_id, source.email, source.address,
          TRUE, CURRENT_DATE(), DATE('9999-12-31'));

-- Then insert new "current" records for updated ones
INSERT INTO `project.dataset.dim_customer`
SELECT
  s.customer_id, s.email, s.address,
  TRUE as is_current,
  CURRENT_DATE() as valid_from,
  DATE('9999-12-31') as valid_to
FROM staging_customer s
JOIN dim_customer d ON s.customer_id = d.customer_id
WHERE d.is_current = FALSE
  AND d.valid_to = CURRENT_DATE();
```

---

**Q: How would you optimize a BigQuery job that's taking too long?**

1. Check INFORMATION_SCHEMA.JOBS — which stage is slow?
2. Look at slot utilization — is there contention?
3. Check for data skew — one partition much larger?
4. Review query plan (EXPLAIN) — is there a cross join or broadcast?
5. Check if partitions are being pruned (bytes scanned vs total)
6. Consider denormalization — fewer JOINs
7. Pre-aggregate with materialized views

---

## 13.2 Dataflow/Beam Questions

**Q: What's the difference between bounded and unbounded data in Apache Beam?**

Bounded = finite dataset (batch file, BQ table snapshot). Unbounded = infinite stream (Pub/Sub, Kafka). Beam handles both with the same programming model. For unbounded data, you apply windowing to create finite chunks for aggregation.

---

**Q: Explain watermarks and how late data is handled.**

Watermark = system's best estimate of event time progress. It says "I believe all events up to time T have arrived." When watermark passes end of a window, the window closes and results are emitted. Late data (arrives after watermark) can be handled by: (1) discarding, (2) updating with `allowed_lateness`, (3) accumulating vs discarding depending on `AccumulationMode`. In Dataflow, `allowed_lateness` tells the system how long to wait for late data before evicting window state.

---

## 13.3 Composer/Airflow Questions

**Q: How do you handle a pipeline where Task B must re-run if Task A fails?**

Using `depends_on_past=True` on Task B causes it to wait for previous run's Task B to succeed. For simpler cases, Airflow automatically handles this — if Task A fails, downstream tasks are skipped. Set appropriate `retries` and `retry_delay` on Task A.

---

**Q: What's the difference between `poke` and `reschedule` mode in sensors?**

`poke` mode: worker holds its slot while waiting — wastes resources for long waits.
`reschedule` mode: worker releases its slot, re-schedules check at next interval — much more efficient for long-running waits. Always use `reschedule` for sensors with >5 min expected wait time.

---

**Q: How do you ensure a DAG is idempotent?**

1. Use `WRITE_TRUNCATE` or partition-specific writes (not WRITE_APPEND)
2. Write to specific partition: `table${{ ds_nodash }}`
3. Use `MERGE` instead of `INSERT`
4. Delete-then-insert pattern for staging tables
5. Use idempotency keys in streaming inserts

---

## 13.4 Architecture/System Design Questions

**Q: Design a data pipeline to migrate 40PB from Teradata to BigQuery.**

Structure your answer:
1. **Assessment phase**: inventory tables, data volumes, dependencies
2. **Prioritization**: migrate in waves (small→large, less-critical→critical)
3. **Extraction**: Teradata JDBC via Dataproc clusters, parallel extraction by partition
4. **Landing**: GCS with Avro/Parquet format
5. **Validation**: row count + checksum at source vs GCS
6. **Loading**: GCS → BigQuery with partition alignment
7. **Post-load validation**: BQ row count vs source
8. **Cutover**: dual-write period → validation → switch consumers
9. **Orchestration**: Composer DAG per table/wave
10. **Monitoring**: Custom dashboard, alerting, audit logging

Key points: config-driven (not one-off), security (DLP, IAM), parallel execution, rollback strategy.

---

**Q: How would you design a real-time fraud detection system on GCP?**

```
Transaction → Pub/Sub → Dataflow (feature extraction + scoring) → Bigtable (low-latency store)
                                 ↓
                          ML model (Vertex AI endpoint)
                                 ↓
                          If fraud score > threshold → alert Pub/Sub topic → Cloud Functions → notify
                                 ↓
                          BigQuery (all transactions for batch ML training)
```

Key design considerations: latency (< 100ms decision needed), exactly-once semantics, feature store (Bigtable for current state), model serving (Vertex AI), feedback loop (labeled fraudulent transactions → retrain).

---

# 14. Cheat Sheet

## BigQuery
```
Partition types: TIMESTAMP/DATE, INTEGER RANGE, Ingestion-time
Cluster: up to 4 columns, after partition
Partition pruning: filter on partition column
Storage classes: Active (<90 days), Long-term (>90 days, 50% cheaper)
Max table size: unlimited
Max partition size: 1TB (can be exceeded with warnings)
Streaming buffer: ~1GB, visible in ~30min-1hr
Storage Write API: replaces streaming inserts, supports exactly-once
Slot: unit of compute. On-demand: auto. Flat-rate: reserved.
DML: INSERT, UPDATE, DELETE, MERGE (limited per day: 1000 DML jobs/table)
INFORMATION_SCHEMA.JOBS_BY_PROJECT → query history
```

## Cloud Storage
```
Storage classes: Standard > Nearline (30d) > Coldline (90d) > Archive (365d)
Max object size: 5TB
Naming: avoid sequential prefixes (hotspot risk)
Uniform bucket-level access: always enable
CMEK: encrypt with your own Cloud KMS key
gsutil -m: parallel operations
```

## Dataflow (Beam)
```
PCollection: distributed immutable dataset
PTransform: operation on PCollection
ParDo/DoFn: element-wise processing
Side input: broadcast small dataset
Window: Fixed, Sliding, Session, Global
Trigger: AfterWatermark, AfterCount, AfterProcessingTime
AccumulationMode: ACCUMULATING vs DISCARDING
Flex Template: containerized, parameterized
Runner: DataflowRunner (prod), DirectRunner (local test)
```

## Composer/Airflow
```
DAG: Directed Acyclic Graph of tasks
Executor: CeleryExecutor (Composer 2 = KubernetesExecutor)
XCom: pass small data between tasks (< few MB)
Sensor mode: reschedule > poke for long waits
Idempotent: WRITE_TRUNCATE, MERGE, partition-specific writes
depends_on_past: task waits for previous run's same task
catchup=False: don't backfill historical runs on deploy
max_active_runs=1: prevent overlapping
schedule: cron string or timedelta
Templating: {{ ds }}, {{ ds_nodash }}, {{ execution_date }}
```

## Pub/Sub
```
Topic → Subscription → Subscriber
Pull: consumer pulls (better control, exactly-once possible)
Push: Pub/Sub pushes to HTTPS endpoint
DLQ: dead_letter_topic after max_delivery_attempts
Ordering: use ordering_key for ordered delivery
Retention: up to 7 days (can seek back)
Message size: max 10MB
Throughput: virtually unlimited (auto-scales)
```

## IAM
```
Principle of least privilege: always
Service accounts: one per workload
Workload Identity: no key files for GKE/Composer
Key roles for DE:
  bigquery.dataEditor + bigquery.jobUser (for BQ access)
  storage.objectViewer / objectCreator
  dataflow.worker
  dataproc.worker
VPC Service Controls: security perimeter around services
```

## GCP Service Selection
```
Batch pipelines (new): Dataflow (Beam)
Batch pipelines (existing Spark): Dataproc
Streaming: Dataflow (Beam) + Pub/Sub
Orchestration: Cloud Composer (Airflow)
DW/Analytics: BigQuery
Object Storage: GCS
Event triggers: Cloud Functions (simple) / Cloud Run (complex)
Secrets: Secret Manager
PII protection: Cloud DLP
Governance: Dataplex + Data Catalog
Monitoring: Cloud Monitoring + Cloud Logging
CI/CD: Cloud Build + Artifact Registry + Cloud Deploy
IaC: Terraform
```
