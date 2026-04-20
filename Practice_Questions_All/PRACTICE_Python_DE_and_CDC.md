# Python Data Engineering Patterns & CDC Implementation
## Costco Sr. Data Engineer Interview Prep

---

## PART 1: DATA ENGINEERING PYTHON PATTERNS

---

### DE1. Config-driven pipeline framework

```python
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    pipeline_name: str
    execution_date: str
    rows_read: int = 0
    rows_written: int = 0
    rows_failed: int = 0
    status: str = "SUCCESS"
    errors: List[str] = field(default_factory=list)


class Extractor(ABC):
    @abstractmethod
    def extract(self, config: dict, execution_date: str) -> Any:
        pass


class GCSExtractor(Extractor):
    def extract(self, config: dict, execution_date: str) -> Any:
        from google.cloud import storage
        import pandas as pd

        bucket_name = config["bucket"]
        path = config["path_pattern"].format(date=execution_date)

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=path))

        dfs = []
        for blob in blobs:
            content = blob.download_as_bytes()
            dfs.append(pd.read_parquet(content))

        return pd.concat(dfs) if dfs else pd.DataFrame()


class BigQueryExtractor(Extractor):
    def extract(self, config: dict, execution_date: str) -> Any:
        from google.cloud import bigquery
        import pandas as pd

        client = bigquery.Client()
        query = config["query"].format(date=execution_date)
        return client.query(query).to_dataframe()


class Transformer(ABC):
    @abstractmethod
    def transform(self, data: Any, config: dict) -> Any:
        pass


class RenameTransformer(Transformer):
    def transform(self, data: Any, config: dict) -> Any:
        return data.rename(columns=config["mappings"])


class ComputeColumnTransformer(Transformer):
    def transform(self, data: Any, config: dict) -> Any:
        for col_name, expr in config["columns"].items():
            data[col_name] = data.eval(expr)
        return data


class MaskPIITransformer(Transformer):
    def transform(self, data: Any, config: dict) -> Any:
        import hashlib
        for col in config["columns"]:
            if col in data.columns:
                data[col] = data[col].apply(
                    lambda x: hashlib.sha256(str(x).encode()).hexdigest()[:16]
                    if x is not None else None
                )
        return data


class Loader(ABC):
    @abstractmethod
    def load(self, data: Any, config: dict, execution_date: str) -> int:
        pass


class BigQueryLoader(Loader):
    def load(self, data: Any, config: dict, execution_date: str) -> int:
        from google.cloud import bigquery

        client = bigquery.Client()
        table_id = config["table"]

        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
            if config.get("mode") == "overwrite"
            else bigquery.WriteDisposition.WRITE_APPEND,
            time_partitioning=bigquery.TimePartitioning(
                field=config.get("partition_by")
            ) if config.get("partition_by") else None
        )

        job = client.load_table_from_dataframe(data, table_id, job_config=job_config)
        job.result()
        return len(data)


class DataPipeline:
    """
    Config-driven pipeline: YAML config → extract → transform → load.
    """

    EXTRACTORS  = {"gcs": GCSExtractor, "bigquery": BigQueryExtractor}
    TRANSFORMERS = {
        "rename": RenameTransformer,
        "compute": ComputeColumnTransformer,
        "mask_pii": MaskPIITransformer
    }
    LOADERS = {"bigquery": BigQueryLoader}

    def __init__(self, config: dict):
        self.config = config
        self.name = config["name"]

    def run(self, execution_date: str) -> PipelineResult:
        result = PipelineResult(
            pipeline_name=self.name,
            execution_date=execution_date
        )

        try:
            # 1. Extract
            extractor_type = self.config["source"]["type"]
            extractor = self.EXTRACTORS[extractor_type]()
            data = extractor.extract(self.config["source"], execution_date)
            result.rows_read = len(data)
            logger.info(f"[{self.name}] Extracted {result.rows_read} rows")

            # 2. Transform (chain of transformers)
            for transform_config in self.config.get("transformations", []):
                t_type = transform_config["type"]
                transformer = self.TRANSFORMERS[t_type]()
                data = transformer.transform(data, transform_config)
            logger.info(f"[{self.name}] Transformation complete")

            # 3. Load
            loader_type = self.config["destination"]["type"]
            loader = self.LOADERS[loader_type]()
            result.rows_written = loader.load(
                data, self.config["destination"], execution_date
            )
            logger.info(f"[{self.name}] Loaded {result.rows_written} rows")

        except Exception as e:
            result.status = "FAILED"
            result.errors.append(str(e))
            logger.error(f"[{self.name}] Pipeline failed: {e}")
            raise

        return result


# Example config and usage:
config = {
    "name": "ad_clicks_daily",
    "source": {
        "type": "gcs",
        "bucket": "costco-raw-data",
        "path_pattern": "google_ads/clicks/{date}/"
    },
    "transformations": [
        {"type": "rename", "mappings": {"gclid": "click_id", "costMicros": "cost_micros"}},
        {"type": "compute", "columns": {"cost_usd": "cost_micros / 1000000.0"}},
        {"type": "mask_pii", "columns": ["user_ip", "user_agent"]}
    ],
    "destination": {
        "type": "bigquery",
        "table": "costco-project.staging.ad_clicks",
        "partition_by": "click_date",
        "mode": "overwrite"
    }
}

# pipeline = DataPipeline(config)
# result = pipeline.run("2024-01-15")
# print(f"Status: {result.status}, Rows: {result.rows_written}")
```

---

### DE2. API ingestion with pagination, rate limiting, and error handling

```python
import requests
import time
import logging
from typing import Iterator, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    base_url: str
    api_key: str
    calls_per_minute: int = 100
    timeout_seconds: int = 30
    max_retries: int = 3
    page_size: int = 1000


class GoogleAdsAPIClient:
    """
    Production-grade API client with:
    - Pagination
    - Rate limiting
    - Retry with exponential backoff
    - Structured error handling
    """

    def __init__(self, config: APIConfig):
        self.config = config
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        })
        self._call_timestamps = []

    def _rate_limit(self):
        """Enforce rate limit: calls_per_minute."""
        now = time.time()
        window_start = now - 60.0

        # Remove timestamps older than 1 minute
        self._call_timestamps = [
            t for t in self._call_timestamps if t > window_start
        ]

        if len(self._call_timestamps) >= self.config.calls_per_minute:
            # Wait until oldest call is more than 1 minute ago
            wait_time = 60.0 - (now - self._call_timestamps[0])
            if wait_time > 0:
                logger.debug(f"Rate limit: sleeping {wait_time:.2f}s")
                time.sleep(wait_time)

        self._call_timestamps.append(time.time())

    def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> requests.Response:
        """Make HTTP request with exponential backoff retry."""
        url = f"{self.config.base_url}/{endpoint}"
        last_error = None

        for attempt in range(1, self.config.max_retries + 1):
            try:
                self._rate_limit()
                response = self._session.request(
                    method, url,
                    timeout=self.config.timeout_seconds,
                    **kwargs
                )

                if response.status_code == 429:  # Too Many Requests
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited. Waiting {retry_after}s")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response

            except requests.exceptions.Timeout as e:
                last_error = e
                delay = 2 ** (attempt - 1)
                logger.warning(f"Attempt {attempt}/{self.config.max_retries} timed out. Retry in {delay}s")
                time.sleep(delay)

            except requests.exceptions.RequestException as e:
                if 400 <= getattr(e.response, 'status_code', 0) < 500:
                    raise  # Don't retry client errors (4xx)
                last_error = e
                delay = 2 ** (attempt - 1)
                logger.warning(f"Attempt {attempt}: {e}. Retry in {delay}s")
                time.sleep(delay)

        raise last_error or RuntimeError("Max retries exceeded")

    def get_campaign_performance(
        self,
        account_id: str,
        start_date: str,
        end_date: str
    ) -> Iterator[dict]:
        """
        Paginated fetch of campaign performance data.
        Yields one record at a time (memory efficient).
        """
        page_token = None
        total_fetched = 0

        while True:
            params = {
                "account_id": account_id,
                "start_date": start_date,
                "end_date": end_date,
                "page_size": self.config.page_size
            }
            if page_token:
                params["page_token"] = page_token

            response = self._request_with_retry("GET", "campaign_performance", params=params)
            data = response.json()

            for record in data.get("results", []):
                yield record
                total_fetched += 1

            page_token = data.get("next_page_token")
            if not page_token:
                break   # No more pages

            logger.debug(f"Fetched {total_fetched} records so far, loading next page...")

        logger.info(f"Total records fetched: {total_fetched}")


def ingest_google_ads_to_gcs(
    account_id: str,
    execution_date: str,
    gcs_bucket: str,
    api_config: APIConfig
):
    """
    Full ingestion: Google Ads API → GCS (JSONL format).
    Idempotent: overwrites the GCS file for the same date.
    """
    from google.cloud import storage
    import json

    client = GoogleAdsAPIClient(api_config)
    storage_client = storage.Client()

    # Fetch all records
    records = []
    try:
        for record in client.get_campaign_performance(
            account_id=account_id,
            start_date=execution_date,
            end_date=execution_date
        ):
            record["_extracted_at"] = datetime.utcnow().isoformat()
            record["_execution_date"] = execution_date
            records.append(record)

    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        raise

    # Write to GCS (overwrite = idempotent)
    blob_path = f"google_ads/campaign_performance/{execution_date}/data.jsonl"
    bucket = storage_client.bucket(gcs_bucket)
    blob = bucket.blob(blob_path)
    blob.upload_from_string(
        "\n".join(json.dumps(r) for r in records),
        content_type="application/x-ndjson"
    )

    logger.info(f"Wrote {len(records)} records to gs://{gcs_bucket}/{blob_path}")
    return len(records)
```

---

## PART 2: CDC IMPLEMENTATION IN PYTHON

---

### CDC1. Timestamp-based CDC — polling approach

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class CDCState:
    """Persistent state for CDC pipeline."""
    source_table: str
    last_processed_at: datetime
    last_processed_id: Optional[int] = None
    rows_processed: int = 0
    last_run_status: str = "SUCCESS"


class StateStore:
    """Stores CDC state in BigQuery for durability."""

    def __init__(self, bq_client, state_table: str):
        self.bq = bq_client
        self.state_table = state_table

    def load(self, source_table: str) -> Optional[CDCState]:
        rows = list(self.bq.query(f"""
            SELECT last_processed_at, last_processed_id, rows_processed
            FROM `{self.state_table}`
            WHERE source_table = '{source_table}'
              AND last_run_status = 'SUCCESS'
            ORDER BY last_processed_at DESC
            LIMIT 1
        """).result())

        if not rows:
            return None

        row = rows[0]
        return CDCState(
            source_table=source_table,
            last_processed_at=row.last_processed_at,
            last_processed_id=row.last_processed_id,
            rows_processed=row.rows_processed
        )

    def save(self, state: CDCState) -> None:
        self.bq.query(f"""
            INSERT INTO `{self.state_table}`
            VALUES (
                '{state.source_table}',
                TIMESTAMP('{state.last_processed_at.isoformat()}'),
                {state.last_processed_id or 'NULL'},
                {state.rows_processed},
                '{state.last_run_status}',
                CURRENT_TIMESTAMP()
            )
        """).result()


class TimestampCDCPipeline:
    """
    Timestamp-based CDC pipeline.
    Polls source DB for rows where updated_at > last_run.
    Applies changes to BigQuery via MERGE.

    Limitations:
    - Cannot detect hard deletes
    - Requires reliable updated_at column on source table
    - May miss rows if updated_at is not indexed (slow for large tables)
    """

    def __init__(
        self,
        source_conn,        # psycopg2 connection or similar
        bq_client,
        source_table: str,
        target_table: str,
        state_store: StateStore,
        primary_key: str,
        timestamp_col: str = "updated_at",
        batch_size: int = 10_000
    ):
        self.conn = source_conn
        self.bq = bq_client
        self.source_table = source_table
        self.target_table = target_table
        self.state_store = state_store
        self.pk = primary_key
        self.ts_col = timestamp_col
        self.batch_size = batch_size

    def extract_changes(
        self,
        since: datetime,
        offset: int = 0
    ) -> List[Dict]:
        """Extract rows modified since last run."""
        cursor = self.conn.cursor()
        cursor.execute(f"""
            SELECT *
            FROM {self.source_table}
            WHERE {self.ts_col} > %s
            ORDER BY {self.ts_col} ASC, {self.pk} ASC
            LIMIT %s OFFSET %s
        """, (since, self.batch_size, offset))

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def apply_to_bigquery(self, changes: List[Dict]) -> int:
        """
        Apply changes to BigQuery using MERGE (idempotent UPSERT).
        """
        if not changes:
            return 0

        # Load changes to temp table
        temp_table = f"{self.target_table}_tmp_{int(datetime.utcnow().timestamp())}"
        self.bq.load_table_from_json(changes, temp_table).result()

        # MERGE into target
        pk = self.pk
        update_cols = [c for c in changes[0].keys() if c != pk]
        update_set = ", ".join([f"target.{c} = source.{c}" for c in update_cols])
        insert_cols = ", ".join(changes[0].keys())
        insert_vals = ", ".join([f"source.{c}" for c in changes[0].keys()])

        merge_sql = f"""
        MERGE INTO `{self.target_table}` AS target
        USING `{temp_table}` AS source
        ON target.{pk} = source.{pk}
        WHEN MATCHED THEN UPDATE SET
            {update_set},
            target._cdc_updated_at = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN INSERT ({insert_cols})
        VALUES ({insert_vals})
        """

        self.bq.query(merge_sql).result()

        # Cleanup
        self.bq.delete_table(temp_table)
        return len(changes)

    def run(self) -> Dict:
        """
        Full CDC run:
        1. Load last state
        2. Extract changes in batches
        3. Apply to BigQuery
        4. Save new state
        """
        run_start = datetime.utcnow()
        total_applied = 0

        # Load state (or use default for first run)
        state = self.state_store.load(self.source_table)
        since = state.last_processed_at if state else datetime(2020, 1, 1)
        logger.info(f"[{self.source_table}] Processing changes since {since}")

        # Extract and apply in batches
        offset = 0
        last_ts = since
        last_id = None

        while True:
            changes = self.extract_changes(since=since, offset=offset)

            if not changes:
                break

            applied = self.apply_to_bigquery(changes)
            total_applied += applied

            # Update watermarks
            last_ts = max(r[self.ts_col] for r in changes)
            last_id = max(r[self.pk] for r in changes)

            logger.info(f"Batch {offset//self.batch_size + 1}: applied {applied} changes")

            if len(changes) < self.batch_size:
                break   # Last batch (partial)
            offset += self.batch_size

        # Save new state
        new_state = CDCState(
            source_table=self.source_table,
            last_processed_at=last_ts if last_ts != since else run_start,
            last_processed_id=last_id,
            rows_processed=total_applied,
            last_run_status="SUCCESS"
        )
        self.state_store.save(new_state)

        result = {
            "source_table": self.source_table,
            "changes_applied": total_applied,
            "run_duration_seconds": (datetime.utcnow() - run_start).total_seconds(),
            "status": "SUCCESS"
        }
        logger.info(f"CDC run complete: {result}")
        return result


---

### CDC2. Log-based CDC — Debezium event processor

```python
import json
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class OperationType(Enum):
    CREATE  = "c"   # INSERT
    UPDATE  = "u"   # UPDATE
    DELETE  = "d"   # DELETE
    READ    = "r"   # snapshot read


@dataclass
class CDCEvent:
    """Parsed Debezium CDC event."""
    op: OperationType
    table: str
    database: str
    before: Optional[Dict]  # state before change (for UPDATE, DELETE)
    after: Optional[Dict]   # state after change (for CREATE, UPDATE)
    source_ts_ms: int
    log_position: int       # for idempotency

    @property
    def primary_key(self) -> Optional[Any]:
        """Extract primary key from after or before state."""
        record = self.after or self.before
        return record.get("id") if record else None


def parse_debezium_event(raw_message: bytes) -> CDCEvent:
    """
    Parse a Debezium CDC message from Kafka/Pub/Sub.

    Debezium format:
    {
      "payload": {
        "op": "u",
        "before": {"id": 1, "budget": 500},
        "after":  {"id": 1, "budget": 750},
        "source": {"db": "campaigns", "table": "campaigns",
                   "ts_ms": 1705363200000, "pos": 12345}
      }
    }
    """
    data = json.loads(raw_message.decode("utf-8"))
    payload = data["payload"]
    source = payload["source"]

    return CDCEvent(
        op=OperationType(payload["op"]),
        table=source["table"],
        database=source["db"],
        before=payload.get("before"),
        after=payload.get("after"),
        source_ts_ms=source["ts_ms"],
        log_position=source.get("pos", 0)
    )


class SCD2Processor:
    """
    Applies log-based CDC events to implement SCD Type 2.
    For UPDATE events: close old record, insert new version.
    For DELETE events: mark as soft-deleted.
    For CREATE events: insert new record.
    """

    def __init__(self, bq_client, target_table: str):
        self.bq = bq_client
        self.table = target_table
        self._processed_positions = set()  # for idempotency

    def process(self, event: CDCEvent) -> str:
        """
        Process a CDC event. Returns action taken.
        Idempotent: same log_position processed twice = no-op.
        """
        # Idempotency check
        if event.log_position in self._processed_positions:
            return "DUPLICATE_SKIPPED"
        self._processed_positions.add(event.log_position)

        if event.op == OperationType.CREATE or event.op == OperationType.READ:
            return self._handle_insert(event)
        elif event.op == OperationType.UPDATE:
            return self._handle_update(event)
        elif event.op == OperationType.DELETE:
            return self._handle_delete(event)

    def _handle_insert(self, event: CDCEvent) -> str:
        """Insert new dimension record."""
        record = event.after
        self.bq.query(f"""
            INSERT INTO `{self.table}`
            SELECT
                GENERATE_UUID()                                 AS surrogate_key,
                '{record['id']}'                               AS natural_key,
                TO_JSON_STRING({json.dumps(record)})            AS attributes_json,
                TIMESTAMP_MILLIS({event.source_ts_ms})          AS valid_from,
                NULL                                            AS valid_to,
                TRUE                                            AS is_current,
                FALSE                                           AS is_deleted,
                CURRENT_TIMESTAMP()                             AS dbt_updated_at
        """).result()
        return "INSERTED"

    def _handle_update(self, event: CDCEvent) -> str:
        """
        SCD2 update:
        1. Close the current record (set valid_to, is_current=FALSE)
        2. Insert new version
        """
        natural_key = event.after['id']
        change_ts = f"TIMESTAMP_MILLIS({event.source_ts_ms})"

        # Two operations in one SQL block
        self.bq.query(f"""
            BEGIN TRANSACTION;

            -- Step 1: Close old record
            UPDATE `{self.table}`
            SET
                valid_to    = {change_ts},
                is_current  = FALSE
            WHERE natural_key = '{natural_key}'
              AND is_current = TRUE;

            -- Step 2: Insert new version
            INSERT INTO `{self.table}` (surrogate_key, natural_key, attributes_json,
                                        valid_from, valid_to, is_current, is_deleted, dbt_updated_at)
            VALUES (
                GENERATE_UUID(),
                '{natural_key}',
                '{json.dumps(event.after)}',
                {change_ts},
                NULL,
                TRUE,
                FALSE,
                CURRENT_TIMESTAMP()
            );

            COMMIT TRANSACTION;
        """).result()
        return "SCD2_UPDATED"

    def _handle_delete(self, event: CDCEvent) -> str:
        """Soft delete: mark record as deleted."""
        natural_key = event.before['id']
        self.bq.query(f"""
            UPDATE `{self.table}`
            SET
                is_deleted  = TRUE,
                is_current  = FALSE,
                valid_to    = TIMESTAMP_MILLIS({event.source_ts_ms})
            WHERE natural_key = '{natural_key}'
              AND is_current = TRUE
        """).result()
        return "SOFT_DELETED"


class CDCPipelineWithDeadLetter:
    """
    Complete CDC pipeline with:
    - Debezium event parsing
    - SCD2 processing
    - Dead letter queue for failed messages
    - Metrics tracking
    """

    def __init__(self, bq_client, target_table: str, dlq_table: str):
        self.processor = SCD2Processor(bq_client, target_table)
        self.bq = bq_client
        self.dlq_table = dlq_table
        self.metrics = {
            "inserted": 0,
            "updated": 0,
            "deleted": 0,
            "skipped": 0,
            "failed": 0
        }

    def process_batch(self, messages: list) -> dict:
        """Process a batch of CDC messages."""
        for raw_message in messages:
            try:
                event = parse_debezium_event(raw_message)
                action = self.processor.process(event)

                if action == "INSERTED":      self.metrics["inserted"] += 1
                elif action == "SCD2_UPDATED": self.metrics["updated"] += 1
                elif action == "SOFT_DELETED": self.metrics["deleted"] += 1
                elif "SKIPPED" in action:     self.metrics["skipped"] += 1

            except json.JSONDecodeError as e:
                self._send_to_dlq(raw_message, f"JSON parse error: {e}")
                self.metrics["failed"] += 1

            except Exception as e:
                self._send_to_dlq(raw_message, f"Processing error: {e}")
                self.metrics["failed"] += 1
                logger.error(f"Failed to process CDC event: {e}")

        return self.metrics

    def _send_to_dlq(self, raw_message: bytes, error: str):
        """Route failed messages to dead letter queue."""
        self.bq.load_table_from_json([{
            "raw_message": raw_message.decode("utf-8", errors="replace"),
            "error_message": error,
            "failed_at": datetime.utcnow().isoformat()
        }], self.dlq_table).result()
        logger.warning(f"Sent to DLQ: {error[:100]}")
```

---

### CDC3. Full Debezium → BigQuery streaming pipeline

```python
from google.cloud import pubsub_v1, bigquery
import json
import threading
from datetime import datetime
from collections import deque
import time


class DebeziumBigQuerySink:
    """
    Consumes Debezium CDC events from Pub/Sub,
    buffers them, and batch-writes to BigQuery.

    Design decisions:
    - Buffer up to N events or T seconds before flushing (whichever first)
    - MERGE on primary key → idempotent
    - Dead letter for malformed messages
    - Thread-safe buffer with lock
    """

    def __init__(
        self,
        project_id: str,
        subscription_id: str,
        target_table: str,
        buffer_size: int = 1000,
        flush_interval_seconds: int = 30
    ):
        self.subscriber = pubsub_v1.SubscriberClient()
        self.subscription = f"projects/{project_id}/subscriptions/{subscription_id}"
        self.bq = bigquery.Client(project=project_id)
        self.target_table = target_table
        self.buffer: deque = deque()
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval_seconds
        self._lock = threading.Lock()
        self._last_flush = time.time()
        self._metrics = {"received": 0, "written": 0, "errors": 0}

    def _parse_message(self, message) -> dict:
        """Parse Pub/Sub message to normalized record."""
        payload = json.loads(message.data.decode("utf-8"))
        op = payload["payload"]["op"]
        after = payload["payload"].get("after", {})
        before = payload["payload"].get("before", {})
        record = after if op != "d" else before

        return {
            **record,
            "_op":          op,
            "_source_ts":   payload["payload"]["source"]["ts_ms"],
            "_log_pos":     payload["payload"]["source"].get("pos", 0),
            "_processed_at": datetime.utcnow().isoformat()
        }

    def _flush_buffer(self):
        """Write buffered records to BigQuery via MERGE."""
        with self._lock:
            if not self.buffer:
                return

            batch = list(self.buffer)
            self.buffer.clear()

        if not batch:
            return

        # Load to temp table
        temp_table = f"{self.target_table}_tmp_{int(time.time())}"
        try:
            job = self.bq.load_table_from_json(batch, temp_table)
            job.result()

            # MERGE: dedup by primary key within batch, keep latest
            pk_col = "id"  # adjust to your table's PK
            self.bq.query(f"""
                MERGE INTO `{self.target_table}` AS target
                USING (
                    SELECT * EXCEPT (rn)
                    FROM (
                        SELECT *,
                            ROW_NUMBER() OVER (
                                PARTITION BY {pk_col}
                                ORDER BY _log_pos DESC
                            ) AS rn
                        FROM `{temp_table}`
                    )
                    WHERE rn = 1 AND _op != 'd'
                ) AS source
                ON target.{pk_col} = source.{pk_col}
                WHEN MATCHED THEN UPDATE SET
                    target.updated_at = source.updated_at,
                    target._log_pos   = source._log_pos
                WHEN NOT MATCHED THEN
                    INSERT ROW
            """).result()

            self._metrics["written"] += len(batch)
            logger.info(f"Flushed {len(batch)} records to BigQuery")

        except Exception as e:
            logger.error(f"Flush failed: {e}")
            self._metrics["errors"] += len(batch)
        finally:
            self.bq.delete_table(temp_table, not_found_ok=True)

        self._last_flush = time.time()

    def callback(self, message):
        """Called for each Pub/Sub message."""
        try:
            record = self._parse_message(message)
            with self._lock:
                self.buffer.append(record)
            self._metrics["received"] += 1
            message.ack()

            # Flush if buffer is full or flush interval exceeded
            if (len(self.buffer) >= self.buffer_size or
                    time.time() - self._last_flush > self.flush_interval):
                threading.Thread(target=self._flush_buffer).start()

        except Exception as e:
            logger.error(f"Message processing failed: {e}")
            message.nack()  # redelivery

    def run(self):
        """Start streaming pull from Pub/Sub."""
        flow_control = pubsub_v1.types.FlowControl(
            max_messages=self.buffer_size * 2
        )
        future = self.subscriber.subscribe(
            self.subscription,
            callback=self.callback,
            flow_control=flow_control
        )

        logger.info(f"Listening on {self.subscription}...")
        try:
            future.result()
        except KeyboardInterrupt:
            future.cancel()
            self._flush_buffer()   # final flush on shutdown
            logger.info(f"Final metrics: {self._metrics}")
```

---

### CDC4. Reconciliation — validate CDC completeness

```python
def reconcile_cdc_pipeline(
    source_conn,
    bq_client,
    source_table: str,
    target_table: str,
    check_date: str,
    pk_column: str = "id"
) -> dict:
    """
    Validate that CDC pipeline hasn't missed any changes.
    Compares source record counts to target record counts.

    Returns a reconciliation report.
    """

    # Step 1: Count in source
    cursor = source_conn.cursor()
    cursor.execute(f"""
        SELECT
            COUNT(*)                    AS total_rows,
            COUNT(DISTINCT {pk_column}) AS unique_keys,
            MAX(updated_at)             AS latest_update
        FROM {source_table}
        WHERE DATE(updated_at) = %s
    """, (check_date,))
    source_stats = dict(zip(
        ["total_rows", "unique_keys", "latest_update"],
        cursor.fetchone()
    ))

    # Step 2: Count in target
    bq_stats = list(bq_client.query(f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT {pk_column}) AS unique_keys,
            MAX(_processed_at) AS latest_processed
        FROM `{target_table}`
        WHERE DATE(_processed_at) = '{check_date}'
    """).result())[0]

    # Step 3: Find missing keys
    cursor.execute(f"""
        SELECT {pk_column}
        FROM {source_table}
        WHERE DATE(updated_at) = %s
    """, (check_date,))
    source_keys = {row[0] for row in cursor.fetchall()}

    target_keys_result = bq_client.query(f"""
        SELECT DISTINCT {pk_column}
        FROM `{target_table}`
        WHERE DATE(_processed_at) = '{check_date}'
    """).result()
    target_keys = {row[pk_column] for row in target_keys_result}

    missing_in_target = source_keys - target_keys
    extra_in_target = target_keys - source_keys

    # Step 4: Build report
    source_count = source_stats["total_rows"]
    target_count = bq_stats.total_rows
    discrepancy_pct = abs(source_count - target_count) / max(source_count, 1) * 100

    report = {
        "check_date": check_date,
        "source_table": source_table,
        "target_table": target_table,
        "source_row_count": source_count,
        "target_row_count": target_count,
        "discrepancy_rows": source_count - target_count,
        "discrepancy_pct": round(discrepancy_pct, 4),
        "missing_keys_sample": list(missing_in_target)[:10],
        "extra_keys_count": len(extra_in_target),
        "status": "PASS" if discrepancy_pct < 0.01 else "FAIL",
        "recommendation": None
    }

    if report["status"] == "FAIL":
        if len(missing_in_target) > 0:
            report["recommendation"] = (
                f"CDC missed {len(missing_in_target)} keys. "
                f"Re-run pipeline with full-refresh for {check_date}."
            )
        else:
            report["recommendation"] = (
                "Count discrepancy but no missing keys — likely duplicate records. "
                "Check for duplicate inserts in the CDC pipeline."
            )

    return report
```

---

## QUICK REFERENCE: Python DE Patterns

```python
# Generator pipeline (memory efficient)
pipeline = transform(parse(read_file(path)))
for item in pipeline: process(item)

# Context manager
@contextmanager
def managed_resource():
    resource = acquire()
    try: yield resource
    finally: release(resource)

# Retry decorator
@retry(max_attempts=3, base_delay=2.0, exceptions=(ConnectionError,))
def api_call(): ...

# Config dataclass
@dataclass
class Config:
    name: str
    batch_size: int = 1000
    @classmethod
    def from_dict(cls, d): return cls(**d)

# Strategy pattern for pluggable connectors
CONNECTORS = {"gcs": GCSConnector, "bq": BQConnector}
connector = CONNECTORS[config["type"]]()

# Thread-safe buffer
import threading
buffer = []
lock = threading.Lock()
with lock: buffer.append(item)

# Exponential backoff
delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
time.sleep(delay + random.uniform(0, delay * 0.1))  # + jitter

# CDC idempotency
processed = set()
def process(event):
    if event.log_pos in processed: return "skip"
    processed.add(event.log_pos)
    apply(event)
```
