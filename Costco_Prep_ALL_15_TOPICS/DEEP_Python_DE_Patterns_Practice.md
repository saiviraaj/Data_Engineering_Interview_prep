# Python Data Engineering Patterns — Practice & Prep
## Round 2 Preparation — Costco Sr. Data Engineer

---

## CHALLENGE 3 (YOUR ROUND-1 QUESTION): The Small Files Problem

```
Scenario: 500 small CSV files in a folder.
Task:
  1. Read all CSVs from a directory
  2. Add source_file_name column
  3. Filter rows where email is null
  4. Write to one Parquet file
```

### The Naive (Wrong) Approach First — Explain WHY it's slow

```python
# SLOW: reads files one by one, pd.concat inside loop = O(n²) memory copies
import pandas as pd
import os

dfs = []
for file in os.listdir("/data/csv_files"):
    df = pd.read_csv(f"/data/csv_files/{file}")
    dfs.append(df)

result = pd.concat(dfs)  # PROBLEM: each concat copies all prior data
# With 500 files × 10MB each = 5GB total
# concat copies: 10MB, 20MB, 30MB... = O(n²) total copies = 1.25 TB of copy operations
```

### The Correct Production Solution

```python
import pandas as pd
import os
import glob
from pathlib import Path

def merge_csv_files_to_parquet(
    input_dir: str,
    output_path: str,
    email_column: str = "email"
) -> dict:
    """
    Read 500+ small CSV files → filter nulls → write single Parquet.
    
    Key techniques:
    1. glob for file discovery (cleaner than os.listdir)
    2. Build list of DataFrames, concat ONCE (not inside loop)
    3. source_file_name added per-file before concat
    4. Filter nulls BEFORE concat (process less data)
    5. Write as Parquet (10x smaller than CSV, columnar for fast analytics)
    """
    
    # Step 1: Discover all CSV files
    csv_files = glob.glob(os.path.join(input_dir, "*.csv"))
    
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {input_dir}")
    
    print(f"Found {len(csv_files)} CSV files")
    
    # Step 2: Read each file, add source column, filter nulls
    # Build list first — concat ONCE at the end (critical for performance)
    dfs = []
    
    for file_path in csv_files:
        try:
            df = pd.read_csv(file_path, low_memory=False)
            
            # Add source file name (just filename, not full path)
            df["source_file_name"] = Path(file_path).name
            
            # Filter out rows where email is null (BEFORE concat = less data)
            if email_column in df.columns:
                df = df[df[email_column].notna()]
                # .notna() is equivalent to ~df[email_column].isna()
                # Also handles empty strings if needed:
                # df = df[df[email_column].notna() & (df[email_column].str.strip() != "")]
            
            dfs.append(df)
            
        except Exception as e:
            print(f"WARNING: Failed to read {file_path}: {e}")
            continue  # skip bad files, don't fail entire job
    
    if not dfs:
        raise ValueError("No valid data found after processing all files")
    
    # Step 3: Combine all DataFrames into one (single concat = O(n) not O(n²))
    combined = pd.concat(dfs, ignore_index=True)
    
    print(f"Combined shape: {combined.shape}")
    print(f"Rows after null email filter: {len(combined)}")
    
    # Step 4: Write as Parquet
    # snappy compression: good balance of speed and compression ratio
    combined.to_parquet(
        output_path,
        engine="pyarrow",         # pyarrow is faster than fastparquet
        compression="snappy",     # snappy: fast compress/decompress
        index=False               # don't write pandas index as a column
    )
    
    file_size_mb = os.path.getsize(output_path) / 1_000_000
    print(f"Written: {output_path} ({file_size_mb:.1f} MB)")
    
    return {
        "files_processed": len(dfs),
        "total_rows": len(combined),
        "output_path": output_path,
        "output_size_mb": file_size_mb
    }

# Usage
result = merge_csv_files_to_parquet(
    input_dir="/data/csv_files",
    output_path="/data/output/merged_clicks.parquet"
)
```

### BONUS: Memory-Efficient Version for Very Large Files (PyArrow)

```python
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.csv as pac
from pathlib import Path
import glob

def merge_csv_large_scale(input_dir: str, output_path: str):
    """
    For 500 files × 100MB each (50GB total) — pandas would OOM.
    Use PyArrow directly: reads in chunks, writes incrementally.
    Never loads all data into memory at once.
    """
    csv_files = glob.glob(f"{input_dir}/*.csv")
    
    writer = None  # ParquetWriter — write incrementally
    schema = None
    
    for file_path in csv_files:
        # Read CSV as Arrow Table (no pandas involved)
        table = pac.read_csv(file_path)
        
        # Add source_file_name column
        source_col = pa.array(
            [Path(file_path).name] * len(table),
            type=pa.string()
        )
        table = table.append_column("source_file_name", source_col)
        
        # Filter null emails (Arrow native filter — no pandas needed)
        if "email" in table.schema.names:
            email_col = table.column("email")
            mask = email_col.is_valid()  # True where NOT null
            table = table.filter(mask)
        
        # Initialize writer with schema from first file
        if writer is None:
            schema = table.schema
            writer = pq.ParquetWriter(output_path, schema, compression="snappy")
        
        # Write this file's data immediately (never accumulates in RAM)
        writer.write_table(table)
    
    if writer:
        writer.close()
    
    print(f"Done. Output: {output_path}")
```

### Why Parquet Over CSV — Be Ready to Explain This

```
CSV:
  • Row-oriented: reading one column requires reading every row fully
  • No compression by default
  • No schema: every read requires type inference
  • Size: 100MB CSV → typically 8-20MB as Parquet

Parquet:
  • Columnar: reading 3 columns out of 30 reads 10% of the data
  • Compressed per column (snappy, gzip, zstd)
  • Schema stored in file footer: types known, no inference needed
  • Supports predicate pushdown: "rows where date='2024-01-15'" can skip other rows
  • Split into row groups: parallel processing in Spark/BigQuery
  
Query: SELECT campaign_id, SUM(cost_usd) FROM clicks WHERE date='2024-01-15'
  CSV (100GB): reads entire 100GB, filter after loading
  Parquet (8GB compressed): reads 2 column groups + skips non-matching row groups
                             → maybe reads 500MB total
  
  16x smaller storage + 200x less data read for typical analytical query
```

---

## SECTION 2: PYTHON PATTERNS YOU MUST KNOW

### Pattern 1: Generator for Memory-Efficient File Processing

```python
from pathlib import Path
import pandas as pd
import glob

def read_csvs_lazily(directory: str, pattern: str = "*.csv"):
    """
    Generator: yields one DataFrame at a time.
    Memory usage = max(largest single file) rather than sum(all files).
    Use when: 500 files × 100MB each = can't load all into RAM.
    """
    for file_path in Path(directory).glob(pattern):
        try:
            df = pd.read_csv(file_path)
            df["source_file_name"] = file_path.name
            yield df
        except Exception as e:
            print(f"Skipping {file_path.name}: {e}")

# Usage with generator — processes one file at a time
# count rows matching condition without loading all files
total_valid = sum(
    len(df[df["email"].notna()])
    for df in read_csvs_lazily("/data/files")
)
print(f"Total valid rows: {total_valid}")
```

### Pattern 2: Retry Decorator for Unreliable APIs

```python
import time
import functools
import logging

def retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,)):
    """
    Decorator: retry a function on failure with exponential backoff.
    
    max_attempts: total tries (including first attempt)
    delay: initial wait in seconds
    backoff: multiply delay by this after each failure
    exceptions: only retry these exception types
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logging.warning(
                            f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logging.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
            raise last_exception
        return wrapper
    return decorator

# Usage
@retry(max_attempts=5, delay=2.0, backoff=2.0, exceptions=(ConnectionError, TimeoutError))
def fetch_campaign_data(campaign_id: str, date: str) -> dict:
    """Fetch from Google Ads API — might fail transiently."""
    response = google_ads_client.get_metrics(campaign_id, date)
    return response.to_dict()

# Will try: immediately, after 2s, after 4s, after 8s, after 16s
# Then raises the last exception if all 5 attempts fail
```

### Pattern 3: Config-Driven Pipeline (What Interviewers Love)

```python
from dataclasses import dataclass, field
from typing import List, Optional
import yaml

@dataclass
class QualityCheck:
    column: str
    rule: str           # "not_null", "unique", "positive", "range"
    severity: str = "ERROR"   # "ERROR" fails pipeline, "WARNING" logs only
    min_value: Optional[float] = None
    max_value: Optional[float] = None

@dataclass
class PipelineConfig:
    name: str
    source_path: str
    output_path: str
    partition_column: str
    email_column: str = "email"
    quality_checks: List[QualityCheck] = field(default_factory=list)
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> "PipelineConfig":
        with open(yaml_path) as f:
            raw = yaml.safe_load(f)
        
        checks = [
            QualityCheck(**c)
            for c in raw.pop("quality_checks", [])
        ]
        return cls(**raw, quality_checks=checks)
    
    def validate(self):
        assert self.name, "Pipeline name required"
        assert self.source_path.startswith(("gs://", "s3://", "/")), \
            f"Invalid source_path: {self.source_path}"

# YAML config file:
# name: ad_clicks_daily
# source_path: /data/csv_files
# output_path: /data/output/merged.parquet
# partition_column: click_date
# quality_checks:
#   - column: click_id
#     rule: not_null
#     severity: ERROR
#   - column: cost_usd
#     rule: positive

def run_quality_checks(df: pd.DataFrame, checks: List[QualityCheck]) -> bool:
    all_passed = True
    
    for check in checks:
        if check.column not in df.columns:
            print(f"WARNING: Column {check.column} not found — skipping check")
            continue
        
        if check.rule == "not_null":
            failures = df[check.column].isna().sum()
        elif check.rule == "unique":
            failures = len(df) - df[check.column].nunique()
        elif check.rule == "positive":
            failures = (df[check.column] <= 0).sum()
        elif check.rule == "range":
            failures = ((df[check.column] < check.min_value) |
                       (df[check.column] > check.max_value)).sum()
        else:
            failures = 0
        
        pct = failures / len(df) * 100
        status = "✅ PASS" if failures == 0 else f"❌ FAIL"
        print(f"{status} | {check.rule}({check.column}) | {failures} failures ({pct:.2f}%)")
        
        if failures > 0 and check.severity == "ERROR":
            all_passed = False
    
    return all_passed
```

### Pattern 4: Context Manager for Safe Resource Handling

```python
from contextlib import contextmanager
from google.cloud import bigquery
import tempfile
import os

@contextmanager
def temp_gcs_stage(bucket: str, prefix: str):
    """
    Context manager: creates a temporary GCS path, cleans up on exit.
    Use for: staging files before final write.
    """
    from google.cloud import storage
    
    gcs_client = storage.Client()
    stage_path = f"gs://{bucket}/{prefix}/stage_{int(time.time())}/"
    staged_blobs = []
    
    try:
        yield stage_path, staged_blobs  # caller gets stage path + blob list
    finally:
        # Always clean up, even on failure
        for blob_name in staged_blobs:
            try:
                bucket_obj = gcs_client.bucket(bucket)
                bucket_obj.blob(blob_name).delete()
                print(f"Cleaned up: {blob_name}")
            except Exception as e:
                print(f"Warning: could not clean up {blob_name}: {e}")

# Usage
with temp_gcs_stage("my-bucket", "etl-temp") as (stage_path, blobs):
    # Write intermediate files to stage
    blobs.append("etl-temp/data_001.parquet")
    write_to_gcs(df, f"{stage_path}data_001.parquet")
    
    # Do transformation
    final_df = transform(df)
    
    # Write final output
    final_df.to_parquet("gs://my-bucket/output/final.parquet")
# Cleanup happens automatically (stage files deleted)
```

---

## SECTION 3: DATA QUALITY PATTERNS

### Writing a Complete DQ Validator

```python
from dataclasses import dataclass
from typing import Callable, List
import pandas as pd
import numpy as np

@dataclass
class DQResult:
    check_name: str
    column: str
    rule: str
    passed: bool
    failure_count: int
    total_count: int
    failure_pct: float
    sample_failures: List

def validate_dataframe(df: pd.DataFrame) -> List[DQResult]:
    """
    Run comprehensive DQ checks on a DataFrame.
    Returns list of results — caller decides what to do with failures.
    """
    results = []
    n = len(df)
    
    def add_result(name, col, rule, failures_mask):
        fail_count = failures_mask.sum()
        sample = df[failures_mask].head(3).to_dict("records") if fail_count > 0 else []
        results.append(DQResult(
            check_name=name,
            column=col,
            rule=rule,
            passed=(fail_count == 0),
            failure_count=int(fail_count),
            total_count=n,
            failure_pct=round(fail_count / n * 100, 4),
            sample_failures=sample
        ))
    
    # 1. Not null checks
    for col in ["click_id", "campaign_id", "clicked_at"]:
        if col in df.columns:
            add_result(f"not_null_{col}", col, "not_null", df[col].isna())
    
    # 2. Uniqueness check
    if "click_id" in df.columns:
        dupes = df.duplicated(subset=["click_id"], keep=False)
        add_result("unique_click_id", "click_id", "unique", dupes)
    
    # 3. Range checks
    if "cost_usd" in df.columns:
        add_result("cost_non_negative", "cost_usd", "non_negative",
                   df["cost_usd"] < 0)
        add_result("cost_reasonable", "cost_usd", "max_1000",
                   df["cost_usd"] > 1000)
    
    # 4. Referential integrity
    if "device_type" in df.columns:
        valid_devices = {"mobile", "desktop", "tablet", "unknown"}
        add_result("valid_device_type", "device_type", "accepted_values",
                   ~df["device_type"].isin(valid_devices))
    
    # 5. Anomaly detection (Z-score)
    if "cost_usd" in df.columns:
        mean = df["cost_usd"].mean()
        std  = df["cost_usd"].std()
        if std > 0:
            z_scores = np.abs((df["cost_usd"] - mean) / std)
            add_result("cost_no_outliers", "cost_usd", "z_score_3",
                       z_scores > 3)
    
    # Print summary
    for r in results:
        status = "✅" if r.passed else "❌"
        print(f"{status} {r.check_name}: {r.failure_count}/{r.total_count} failures")
    
    return results

# Run it
df = pd.read_parquet("/data/output/merged.parquet")
dq_results = validate_dataframe(df)

errors = [r for r in dq_results if not r.passed]
if errors:
    raise ValueError(f"DQ failed: {len(errors)} checks failed")
```

---

## SECTION 4: PYTHON INTERVIEW QUESTIONS

### Q1: "What's wrong with this code and how do you fix it?"

```python
# PROBLEM CODE given in interview:
import pandas as pd
import os

result = pd.DataFrame()
for file in os.listdir("/data"):
    df = pd.read_csv(f"/data/{file}")
    result = pd.concat([result, df])   # BUG: concat inside loop

result.to_csv("/output/merged.csv")
```

**Your answer**: *"There are four issues. First and most critical: `pd.concat` inside a loop is O(n²) in memory — each concat copies all prior data, so processing 500 files copies: 1 file, then 2 files, then 3 files... summing to 500×501/2 = 125,250 file-copies worth of data. The fix is to append to a list inside the loop and call concat exactly once at the end.*

*Second: the output is CSV — if this is for analytics, Parquet is 10x smaller and far faster to query later.*

*Third: no error handling — one bad file kills the entire job. Should wrap in try/except and skip malformed files.*

*Fourth: no source_file_name tracking — you lose the ability to trace which file a row came from."*

```python
# FIXED VERSION:
import pandas as pd
import os
from pathlib import Path

dfs = []
for file_path in Path("/data").glob("*.csv"):
    try:
        df = pd.read_csv(file_path)
        df["source_file_name"] = file_path.name
        dfs.append(df)
    except Exception as e:
        print(f"Skipping {file_path.name}: {e}")

if dfs:
    combined = pd.concat(dfs, ignore_index=True)
    combined.to_parquet("/output/merged.parquet", index=False)
```

---

### Q2: "Write a function to implement a simple checkpointing system for a pipeline"

```python
import json
import os
from datetime import datetime
from pathlib import Path

class PipelineCheckpoint:
    """
    Saves pipeline state to disk so it can resume from where it left off
    after a failure — instead of reprocessing from the beginning.
    
    Use case: processing 500 files, fails at file 350.
    Without checkpoint: restart from file 1.
    With checkpoint: restart from file 351.
    """
    
    def __init__(self, checkpoint_file: str):
        self.checkpoint_file = Path(checkpoint_file)
        self._state = self._load()
    
    def _load(self) -> dict:
        """Load existing checkpoint or start fresh."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file) as f:
                state = json.load(f)
                print(f"Resuming from checkpoint: {state}")
                return state
        return {}
    
    def save(self, key: str, value) -> None:
        """Save a checkpoint value."""
        self._state[key] = value
        self._state["last_updated"] = datetime.utcnow().isoformat()
        
        # Write atomically: write to temp, then rename
        # Prevents corruption if process dies during write
        tmp_path = self.checkpoint_file.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            json.dump(self._state, f, indent=2)
        os.replace(tmp_path, self.checkpoint_file)  # atomic rename
    
    def get(self, key: str, default=None):
        return self._state.get(key, default)
    
    def clear(self) -> None:
        """Remove checkpoint (call after successful completion)."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
        self._state = {}
        print("Checkpoint cleared")

# Usage in pipeline
def process_files_with_checkpoint(input_dir: str, output_path: str):
    checkpoint = PipelineCheckpoint("/tmp/pipeline_checkpoint.json")
    
    all_files = sorted(Path(input_dir).glob("*.csv"))
    last_processed = checkpoint.get("last_processed_file")
    
    # Find where to resume
    if last_processed:
        processed_files = set(checkpoint.get("processed_files", []))
        files_to_process = [f for f in all_files if f.name not in processed_files]
        print(f"Resuming: {len(files_to_process)} files remaining")
    else:
        files_to_process = all_files
    
    dfs = []
    processed = checkpoint.get("processed_files", [])
    
    for file_path in files_to_process:
        try:
            df = pd.read_csv(file_path)
            df["source_file_name"] = file_path.name
            dfs.append(df)
            processed.append(file_path.name)
            
            # Save checkpoint every 50 files
            if len(processed) % 50 == 0:
                checkpoint.save("processed_files", processed)
                checkpoint.save("last_processed_file", file_path.name)
                print(f"Checkpoint saved at {len(processed)} files")
        
        except Exception as e:
            print(f"Error on {file_path.name}: {e}")
    
    if dfs:
        combined = pd.concat(dfs, ignore_index=True)
        combined.to_parquet(output_path, index=False)
        checkpoint.clear()  # success: remove checkpoint
        print(f"Done. {len(dfs)} files processed.")
```

---

## QUICK REFERENCE: PYTHON DE INTERVIEW PATTERNS

```python
# FILE PROCESSING
glob.glob("/dir/*.csv")                     # find all CSV files
Path(file_path).name                        # just filename from full path
dfs.append(df); combined = pd.concat(dfs)  # build list, concat ONCE (not in loop)
df.to_parquet(path, compression="snappy")   # write Parquet

# NULL HANDLING
df[col].isna()          # True where null
df[col].notna()         # True where NOT null
df.fillna({"col": 0})   # fill with default values
df.dropna(subset=["email"])  # drop rows where email is null

# TYPE CASTING
df[col].astype("int64")
pd.to_datetime(df[col], errors="coerce")  # coerce: bad dates → NaT (not exception)

# PERFORMANCE
df.dtypes               # check types (object columns use most memory)
df.memory_usage(deep=True)  # see actual memory per column
pd.read_csv(path, dtype={"id": "int32"})  # specify dtypes to save memory
pd.read_csv(path, usecols=["id","email"])  # only read needed columns

# DEDUP
df.drop_duplicates(subset=["click_id"])           # arbitrary: keep first
df.sort_values("loaded_at").drop_duplicates(      # keep most recent
    subset=["click_id"], keep="last")

# DECORATORS
@retry(max_attempts=3)    # retry on failure
@functools.lru_cache(256) # cache function results

# CONTEXT MANAGERS
with open(path) as f:     # auto-close file
with tempfile.NamedTemporaryFile() as tmp:  # auto-delete temp file
```
