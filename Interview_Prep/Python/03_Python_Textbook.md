# Python for Data Engineering — Complete Textbook
### Clean, Modular, Production-Grade Python for Senior Data Engineers

---

## CHAPTER 1: PYTHON FOUNDATIONS FOR DATA ENGINEERS

### 1.1 Python Data Types — What Matters in DE

```python
# Strings — immutable, common for file paths, SQL, configs
s = "SELECT * FROM orders"
s.upper(), s.lower(), s.strip(), s.replace("*", "customer_id")
f"SELECT {col} FROM {table} WHERE date = '{dt}'"  # f-strings — use these

# Lists — ordered, mutable, used for batches, rows, column lists
cols = ["customer_id", "amount", "date"]
cols.append("status")
cols.extend(["region", "channel"])

# Tuples — immutable, great for fixed configs, DB rows
config = ("us-central1", "my-project", "my-dataset")
region, project, dataset = config  # unpacking

# Dictionaries — key-value, used everywhere (schema defs, configs, JSON)
schema = {"customer_id": "STRING", "amount": "FLOAT64", "date": "DATE"}
schema.get("region", "STRING")  # safe get with default
for col, dtype in schema.items():
    print(f"{col}: {dtype}")

# Sets — unique values, great for deduplication checks
actual_cols = {"customer_id", "amount", "date", "extra_col"}
expected_cols = {"customer_id", "amount", "date"}
missing = expected_cols - actual_cols       # set difference
extra = actual_cols - expected_cols         # extra columns
common = actual_cols & expected_cols        # intersection
```

### 1.2 Comprehensions and Generators

```python
# List comprehension — Pythonic, faster than loops
cols = ["Customer_ID", "Order_Amount", "  Date  "]
clean_cols = [c.strip().lower().replace(" ", "_") for c in cols]
# ['customer_id', 'order_amount', 'date']

# Dict comprehension — schema transformation
bq_type_map = {"int": "INT64", "float": "FLOAT64", "str": "STRING"}
source_schema = {"id": "int", "amount": "float", "name": "str"}
bq_schema = {col: bq_type_map[dtype] for col, dtype in source_schema.items()}

# Generator expression — memory efficient for large data (lazy evaluation)
total = sum(row["amount"] for row in large_dataset if row["status"] == "completed")

# Generator function — yields one item at a time, essential for large datasets
def read_in_batches(data: list, batch_size: int):
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]

# Use it:
for batch in read_in_batches(million_rows, batch_size=1000):
    process_batch(batch)  # only 1000 rows in memory at a time
```

### 1.3 Functions — Clean, Type-Hinted, Documented

```python
from typing import Optional, List, Dict, Any, Generator
from datetime import date

def extract_table_rows(
    project_id: str,
    dataset: str,
    table: str,
    partition_date: Optional[date] = None,
    batch_size: int = 1000
) -> Generator[List[Dict[str, Any]], None, None]:
    """
    Extract rows from a BigQuery table in batches.
    
    Args:
        project_id: GCP project ID
        dataset: BigQuery dataset name
        table: Table name
        partition_date: Optional partition filter (DATE column)
        batch_size: Number of rows per yielded batch
    
    Yields:
        Batches of rows as list of dictionaries
    
    Raises:
        ValueError: If table name is empty
        google.cloud.exceptions.NotFound: If table does not exist
    """
    if not table:
        raise ValueError("Table name cannot be empty")
    # implementation ...
```

### 1.4 Error Handling

```python
from google.cloud import bigquery
from google.api_core.exceptions import NotFound, GoogleAPICallError
import logging

logger = logging.getLogger(__name__)

# Custom exception hierarchy — always build one for pipelines
class PipelineError(Exception):
    """Base exception for all pipeline errors."""
    pass

class ExtractionError(PipelineError):
    def __init__(self, source: str, reason: str):
        self.source = source
        self.reason = reason
        super().__init__(f"Extraction failed for {source}: {reason}")

class ValidationError(PipelineError):
    pass

class RateLimitError(PipelineError):
    pass


def safe_bq_query(client: bigquery.Client, sql: str) -> Optional[List[Dict]]:
    try:
        result = client.query(sql).result()
        return [dict(row) for row in result]

    except NotFound as e:
        logger.error(f"Table not found: {e}")
        raise  # re-raise — let caller decide

    except GoogleAPICallError as e:
        if e.code == 429:
            raise RateLimitError(f"BQ quota exceeded: {e}") from e
        raise

    except Exception as e:
        logger.exception(f"Unexpected error for query: {sql[:100]}")
        return None
```

---

## CHAPTER 2: OBJECT-ORIENTED PYTHON FOR DATA ENGINEERING

### 2.1 Dataclasses — For Config and DTOs

```python
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

@dataclass
class PipelineConfig:
    source_type: str           # 'teradata', 'oracle', 'hive', 'kafka'
    source_connection: str
    target_project: str
    target_dataset: str
    target_table: str
    batch_size: int = 10_000
    enable_validation: bool = True
    partition_column: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        valid_sources = {"teradata", "oracle", "hive", "kafka", "gcs"}
        if self.source_type not in valid_sources:
            raise ValueError(f"Invalid source_type: {self.source_type}")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")

    @property
    def target_table_ref(self) -> str:
        return f"{self.target_project}.{self.target_dataset}.{self.target_table}"
```

### 2.2 Abstract Base Classes — Extractor Interface

```python
from abc import ABC, abstractmethod

class BaseExtractor(ABC):
    """Defines the contract for all data source extractors."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def extract(self, query: str) -> Generator: ...

    @abstractmethod
    def get_row_count(self, table: str) -> int: ...

    def disconnect(self) -> None:
        self.logger.info(f"Disconnecting from {self.config.source_type}")

    # Context manager support — use with 'with' statement
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False  # never suppress exceptions


class TeradataExtractor(BaseExtractor):

    def connect(self) -> None:
        import teradatasql
        self._conn = teradatasql.connect(
            host=self.config.source_connection,
            user=self._get_secret("teradata-user"),
            password=self._get_secret("teradata-password")
        )

    def extract(self, query: str) -> Generator[List[dict], None, None]:
        cursor = self._conn.cursor()
        cursor.execute(query)
        while True:
            batch = cursor.fetchmany(self.config.batch_size)
            if not batch:
                break
            cols = [d[0] for d in cursor.description]
            yield [dict(zip(cols, row)) for row in batch]

    def get_row_count(self, table: str) -> int:
        cursor = self._conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        return cursor.fetchone()[0]

    def _get_secret(self, name: str) -> str:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        path = f"projects/{self.config.target_project}/secrets/{name}/versions/latest"
        return client.access_secret_version(name=path).payload.data.decode()

    def disconnect(self) -> None:
        if hasattr(self, "_conn"):
            self._conn.close()
        super().disconnect()
```

### 2.3 Factory Pattern — Config-Driven Extractor Creation

```python
class ExtractorFactory:
    _registry: Dict[str, type] = {}

    @classmethod
    def register(cls, source_type: str):
        def decorator(extractor_class: type):
            cls._registry[source_type] = extractor_class
            return extractor_class
        return decorator

    @classmethod
    def create(cls, config: PipelineConfig) -> BaseExtractor:
        extractor_class = cls._registry.get(config.source_type)
        if not extractor_class:
            raise ValueError(f"No extractor for: {config.source_type}")
        return extractor_class(config)


@ExtractorFactory.register("teradata")
class TeradataExtractor(BaseExtractor): ...

@ExtractorFactory.register("oracle")
class OracleExtractor(BaseExtractor): ...

# Usage — no if/else chains, fully config-driven (like CDM Next)
extractor = ExtractorFactory.create(config)
```

---

## CHAPTER 3: ETL/ELT PIPELINE PATTERNS

### 3.1 The Complete Pipeline

```python
class DataPipeline:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.bq = bigquery.Client(project=config.target_project)
        self.stats = {"extracted": 0, "loaded": 0, "errors": 0}

    def run(self) -> Dict[str, int]:
        extractor = ExtractorFactory.create(self.config)
        with extractor:
            for batch_num, batch in enumerate(extractor.extract(self._build_query())):
                transformed = self._transform(batch)
                if self.config.enable_validation:
                    self._validate(transformed, batch_num)
                self._load(transformed)
                self.stats["extracted"] += len(batch)
                self.stats["loaded"] += len(transformed)
        return self.stats

    def _transform(self, batch: List[Dict]) -> List[Dict]:
        result = []
        for row in batch:
            try:
                result.append({
                    **{k.lower(): v for k, v in row.items()},
                    "_ingestion_ts": datetime.utcnow().isoformat(),
                    "_source": self.config.source_type
                })
            except Exception as e:
                self.stats["errors"] += 1
                logger.warning(f"Transform failed: {e}")
        return result

    def _validate(self, batch: List[Dict], batch_num: int) -> None:
        if not batch:
            raise ValidationError(f"Empty batch at {batch_num}")
        required = {"customer_id", "amount"}
        missing = required - set(batch[0].keys())
        if missing:
            raise ValidationError(f"Missing columns: {missing}")
        nulls = sum(1 for r in batch if r.get("customer_id") is None)
        if nulls:
            raise ValidationError(f"{nulls} null primary keys in batch {batch_num}")

    def _load(self, batch: List[Dict]) -> None:
        errors = self.bq.insert_rows_json(self.config.target_table_ref, batch)
        if errors:
            raise ExtractionError(self.config.target_table, str(errors))

    def _build_query(self) -> str:
        q = f"SELECT * FROM {self.config.source_connection}"
        if self.config.partition_column:
            q += f" WHERE {self.config.partition_column} = CURRENT_DATE"
        return q
```

### 3.2 GCS Operations

```python
from google.cloud import storage
import json

def write_json_to_gcs(data: dict, bucket: str, path: str) -> None:
    client = storage.Client()
    blob = client.bucket(bucket).blob(path)
    blob.upload_from_string(
        json.dumps(data, default=str),  # default=str handles datetime, Decimal
        content_type="application/json"
    )

def stream_csv_from_gcs(bucket: str, path: str):
    """Stream large CSV without loading fully into memory."""
    import csv
    client = storage.Client()
    with client.bucket(bucket).blob(path).open("r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row

def get_partition_path(table: str, partition_date: date) -> str:
    return (f"data/{table}/year={partition_date.year}/"
            f"month={partition_date.month:02d}/"
            f"day={partition_date.day:02d}/data.parquet")
```

### 3.3 BigQuery Python Client

```python
from google.cloud import bigquery
from google.cloud.bigquery import LoadJobConfig

def run_query(client: bigquery.Client, sql: str) -> List[Dict]:
    return [dict(row) for row in client.query(sql).result()]

def load_df_to_bq(df, client: bigquery.Client, table_ref: str,
                  mode: str = "WRITE_APPEND") -> None:
    job = client.load_table_from_dataframe(
        df, table_ref,
        job_config=LoadJobConfig(
            write_disposition=mode,
            autodetect=True,
            create_disposition="CREATE_IF_NEEDED"
        )
    )
    job.result()
    if job.errors:
        raise Exception(f"BQ load errors: {job.errors}")

def dry_run(client: bigquery.Client, sql: str) -> Dict:
    job = client.query(sql, job_config=bigquery.QueryJobConfig(
        dry_run=True, use_query_cache=False
    ))
    gb = job.total_bytes_processed / (1024 ** 3)
    return {"gb": round(gb, 3), "cost_usd": round(gb * 6.25 / 1000, 6)}
```

---

## CHAPTER 4: PYSPARK FOR DATA ENGINEERING

### 4.1 SparkSession

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import *

spark = (
    SparkSession.builder
    .appName("cdm-migration")
    .config("spark.sql.adaptive.enabled", "true")
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
    .config("spark.sql.adaptive.skewJoin.enabled", "true")
    .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
    .getOrCreate()
)
```

### 4.2 DataFrame Operations

```python
# Reading
df = spark.read.parquet("gs://bucket/data/")
df = spark.read.format("bigquery").option("table", "proj.ds.tbl").load()

# Column ops
df = df.withColumn("amount_usd", F.col("amount") / 100)
df = df.withColumn("load_date", F.current_date())
df = df.withColumn("status_clean", F.trim(F.upper(F.col("status"))))
df = df.withColumn("category",
    F.when(F.col("amount") < 100, "LOW")
     .when(F.col("amount") < 1000, "MEDIUM")
     .otherwise("HIGH"))

# Null handling
df = df.fillna({"amount": 0.0, "status": "UNKNOWN"})
df = df.dropna(subset=["customer_id"])
df = df.withColumn("amount", F.coalesce(F.col("amount"), F.lit(0.0)))

# Aggregations
summary = df.groupBy("customer_id").agg(
    F.sum("amount").alias("total"),
    F.count("*").alias("cnt"),
    F.max("order_date").alias("last_date"),
    F.countDistinct("product_id").alias("products")
)

# Window functions
w = Window.partitionBy("customer_id").orderBy(F.col("order_date").desc())
df = df.withColumn("row_num", F.row_number().over(w))
df = df.withColumn("prev_amount", F.lag("amount", 1).over(w))
df = df.withColumn("running_total", F.sum("amount").over(
    w.rowsBetween(Window.unboundedPreceding, Window.currentRow)
))
# Latest record per customer
df_latest = df.filter(F.col("row_num") == 1)
```

### 4.3 Joins and Optimisation

```python
# Standard join
result = orders.join(customers, on="customer_id", how="inner")

# Broadcast join — for small tables (< 200MB) — eliminates shuffle
from pyspark.sql.functions import broadcast
result = large_fact.join(broadcast(small_dim), on="product_id")

# Anti-join — records in orders not in processed
new_only = orders.join(processed, on="order_id", how="left_anti")

# Semi-join — filter orders to only those with active customers
filtered = orders.join(active_customers, on="customer_id", how="left_semi")
```

### 4.4 UDFs

```python
from pyspark.sql.functions import udf, pandas_udf
import pandas as pd

# AVOID regular UDFs — row-by-row, Python overhead, not optimised
@udf(returnType=StringType())
def slow_udf(x): return x.upper()  # bad for production at scale

# PREFER native Spark SQL functions (compiled, JVM speed)
df = df.withColumn("upper", F.upper(F.col("name")))

# USE Pandas UDFs when native functions are insufficient (vectorised, uses Arrow)
@pandas_udf(DoubleType())
def normalise(series: pd.Series) -> pd.Series:
    return (series - series.mean()) / series.std()

df = df.withColumn("amount_norm", normalise(F.col("amount")))
```

### 4.5 Partitioning, Caching, Writing

```python
# Repartition (shuffle) vs Coalesce (no shuffle)
df = df.repartition(200, "customer_id")  # increase or change partition key
df = df.coalesce(10)                      # reduce partitions before write

# Cache — only when DataFrame is reused multiple times in same job
df_valid = df.filter(F.col("amount") > 0).cache()
train = df_valid.filter(F.col("year") < 2024)
test  = df_valid.filter(F.col("year") == 2024)
df_valid.unpersist()  # always release after use

# Writing
df.write.mode("overwrite").partitionBy("year", "month") \
  .option("compression", "snappy").parquet("gs://bucket/output/")

df.write.format("bigquery") \
  .option("table", "project.dataset.table") \
  .option("temporaryGcsBucket", "temp-bucket") \
  .mode("append").save()
```

### 4.6 Handling Data Skew

```python
# Problem: one key dominates → one executor does all the work

# Solution 1: Salting
SALT = 10
df = df.withColumn("salt", (F.rand() * SALT).cast("int"))
df = df.withColumn("key_salted", F.concat(F.col("customer_id"), F.lit("_"), F.col("salt")))

dim = dim.withColumn("salt", F.explode(F.array([F.lit(i) for i in range(SALT)])))
dim = dim.withColumn("key_salted", F.concat(F.col("customer_id"), F.lit("_"), F.col("salt")))
result = df.join(dim, on="key_salted").drop("salt", "key_salted")

# Solution 2: AQE (Spark 3+) — handles skew automatically
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")

# Solution 3: Broadcast join if dim fits in memory
result = fact.join(broadcast(dim), on="customer_id")
```

### 4.7 Structured Streaming

```python
schema = StructType([
    StructField("order_id", StringType()),
    StructField("customer_id", StringType()),
    StructField("amount", DoubleType()),
    StructField("event_time", TimestampType())
])

stream = (spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", "broker:9092")
    .option("subscribe", "orders")
    .load()
    .select(F.from_json(F.col("value").cast("string"), schema).alias("d"))
    .select("d.*"))

# Windowed aggregation with watermark for late data
agg = (stream
    .withWatermark("event_time", "10 minutes")
    .groupBy(F.window("event_time", "5 minutes"), "customer_id")
    .agg(F.sum("amount").alias("total"), F.count("*").alias("cnt")))

query = (agg.writeStream.outputMode("append")
    .format("bigquery")
    .option("table", "project.dataset.orders_agg")
    .option("temporaryGcsBucket", "temp-bucket")
    .option("checkpointLocation", "gs://bucket/checkpoints/orders")
    .trigger(processingTime="30 seconds")
    .start())

query.awaitTermination()
```

---

## CHAPTER 5: PANDAS

### 5.1 Core Operations

```python
import pandas as pd
import numpy as np

df = pd.read_csv("data.csv", dtype={"id": str}, parse_dates=["date"])
df = pd.read_parquet("data.parquet")

# Inspection
df.shape; df.dtypes; df.isnull().sum(); df.describe()

# Filtering
df_valid = df[(df["amount"] > 0) & (df["status"].isin(["ACTIVE", "PENDING"]))]

# Transformations
df["name_clean"] = df["name"].str.strip().str.lower().str.replace(r"\s+", "_", regex=True)
df["category"] = np.where(df["amount"] > 1000, "HIGH", "LOW")

# GroupBy
summary = df.groupby("customer_id").agg(
    total=("amount", "sum"),
    cnt=("order_id", "count"),
    last=("date", "max")
).reset_index()

# Window functions
df = df.sort_values("date")
df["rolling_7d"] = df.groupby("customer_id")["amount"] \
    .transform(lambda x: x.rolling(7, min_periods=1).mean())
df["cumsum"] = df.groupby("customer_id")["amount"].cumsum()
```

### 5.2 Memory Optimisation

```python
def optimise_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.select_dtypes("int64").columns:
        df[col] = pd.to_numeric(df[col], downcast="integer")
    for col in df.select_dtypes("float64").columns:
        df[col] = pd.to_numeric(df[col], downcast="float")
    for col in df.select_dtypes("object").columns:
        if df[col].nunique() / len(df) < 0.5:  # low cardinality
            df[col] = df[col].astype("category")
    return df

# Chunked reading for files too large for RAM
results = []
for chunk in pd.read_csv("huge.csv", chunksize=100_000):
    results.append(process_chunk(chunk))
df = pd.concat(results, ignore_index=True)
```

---

## CHAPTER 6: TESTING

### 6.1 pytest Unit Tests

```python
# tests/test_pipeline.py
import pytest
from unittest.mock import MagicMock, patch

class TestTransformations:

    @pytest.mark.parametrize("amount,expected", [
        (50, "LOW"), (500, "MEDIUM"), (5000, "HIGH"), (None, "UNKNOWN")
    ])
    def test_amount_category(self, amount, expected):
        assert categorise(amount) == expected

    def test_lowercase_keys(self):
        result = clean_record({"Customer_ID": "C1", "Amount": 100})
        assert "customer_id" in result
        assert "amount" in result

    def test_raises_on_null_pk(self):
        with pytest.raises(ValidationError, match="null customer_id"):
            validate_batch([{"customer_id": None, "amount": 10}], 0)


class TestBigQueryLoader:

    @patch("my_pipeline.loader.bigquery.Client")
    def test_calls_insert_rows(self, mock_bq_class):
        mock_client = MagicMock()
        mock_bq_class.return_value = mock_client
        mock_client.insert_rows_json.return_value = []

        loader = BigQueryLoader("test-project")
        loader.load([{"id": "1"}], "proj.ds.tbl")

        mock_client.insert_rows_json.assert_called_once()
```

### 6.2 PySpark Tests

```python
# conftest.py
import pytest
from pyspark.sql import SparkSession

@pytest.fixture(scope="session")
def spark():
    s = (SparkSession.builder.master("local[2]")
         .config("spark.sql.shuffle.partitions", "2")
         .getOrCreate())
    s.sparkContext.setLogLevel("ERROR")
    yield s
    s.stop()


def test_dedup(spark):
    data = [(1, "C1", 100), (1, "C1", 100), (2, "C2", 200)]
    df = spark.createDataFrame(data, ["id", "cid", "amt"])
    result = deduplicate(df, ["id"])
    assert result.count() == 2


def test_window_rank(spark):
    data = [("C1", 100, "2024-01-02"), ("C1", 200, "2024-01-01")]
    df = spark.createDataFrame(data, ["cid", "amt", "dt"])
    result = add_row_number(df, partition="cid", order="dt")
    latest = result.filter("row_num = 1").collect()[0]
    assert latest["amt"] == 100  # most recent = 2024-01-02
```

---

## CHAPTER 7: CONCURRENCY AND RETRY

### 7.1 Parallel Execution

```python
import concurrent.futures

def parallel_process(items, fn, max_workers=10, use_threads=True):
    """
    I/O-bound tasks (API calls, DB queries): use threads
    CPU-bound tasks (data transformation): use processes
    """
    Executor = (concurrent.futures.ThreadPoolExecutor if use_threads
                else concurrent.futures.ProcessPoolExecutor)
    results, errors = [], []

    with Executor(max_workers=max_workers) as ex:
        futures = {ex.submit(fn, item): item for item in items}
        for f in concurrent.futures.as_completed(futures):
            try:
                results.append(f.result(timeout=300))
            except Exception as e:
                errors.append({"item": futures[f], "error": str(e)})

    return results, errors

# Example: migrate 50 tables in parallel (5 at a time to avoid BQ quota)
results, errors = parallel_process(table_list, migrate_table, max_workers=5)
```

### 7.2 Retry with Exponential Backoff

```python
import functools, time, random
from google.api_core.exceptions import ServiceUnavailable, TooManyRequests

def retry(max_retries=3, base=2.0, exceptions=(Exception,)):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        raise
                    wait = base ** attempt + random.uniform(0, 0.5)
                    logger.warning(f"{fn.__name__} attempt {attempt+1} failed: {e}. Retrying in {wait:.1f}s")
                    time.sleep(wait)
        return wrapper
    return decorator

@retry(max_retries=3, exceptions=(ServiceUnavailable, TooManyRequests))
def call_vertex_ai(prompt: str) -> str:
    return model.generate_content(prompt).text
```

---

## CHAPTER 8: PRODUCTION BEST PRACTICES

### 8.1 Config from Environment

```python
import os
from dataclasses import dataclass

@dataclass
class AppConfig:
    project_id: str
    dataset: str
    environment: str
    batch_size: int

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            project_id=os.environ["GCP_PROJECT_ID"],
            dataset=os.environ["BQ_DATASET"],
            environment=os.environ.get("ENVIRONMENT", "dev"),
            batch_size=int(os.environ.get("BATCH_SIZE", "10000"))
        )

    @property
    def is_prod(self) -> bool:
        return self.environment == "production"
```

### 8.2 Structured Logging

```python
import logging, json, sys
from datetime import datetime

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "function": record.funcName,
            "line": record.lineno
        })

def setup_logging(level="INFO"):
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[h])
```

### 8.3 Production Code Checklist

```
✓ Type hints on all functions
✓ Docstrings on public functions/classes
✓ Custom exception hierarchy
✓ Retry logic on all external API calls
✓ JSON-structured logging (Cloud Logging compatible)
✓ Config from environment variables — no hardcoded values
✓ Unit tests with >80% coverage on business logic
✓ No secrets in code (Secret Manager)
✓ Input validation at entry points
✓ Context managers for resource management
✓ Generators for memory-efficient large data handling
✓ Graceful degradation — one bad record doesn't kill the batch
```

---

*End of Python for Data Engineering Textbook*
