# Python for Data Engineering — Exhaustive Interview Q&A
### Tailored for Senior Data Engineer with CDM Next / GCP Background

---

## SECTION 1: PYTHON FUNDAMENTALS

**Q1. What is the difference between a list, tuple, and set? When would you use each in a data pipeline?**

Lists are ordered, mutable sequences — ideal for collecting pipeline results, maintaining column lists, or accumulating batches during processing. Tuples are ordered but immutable — I use them for fixed configuration values (like connection parameters), database rows returned from cursors, or function returns where I want to guarantee immutability. Sets are unordered collections of unique values — extremely useful in pipeline validation: comparing `expected_columns - actual_columns` to detect schema drift instantly. In CDM Next, I used sets to compare source and target table schemas before every migration run.

---

**Q2. Explain generators and why they matter for data engineering.**

A generator is a function that uses `yield` instead of `return`, producing values lazily one at a time rather than building the entire result in memory. This is fundamental for data engineering because we routinely process datasets that exceed available RAM. Instead of loading a 50GB file into a list, a generator yields one batch at a time — memory usage stays constant regardless of file size. In CDM Next, all our extractors were generator-based: we'd yield batches of 10,000 rows from Teradata, process each batch, load to BigQuery, then move to the next — never holding more than one batch in memory. This allowed us to migrate tables with billions of rows on standard compute.

---

**Q3. What are list comprehensions and when should you avoid them?**

List comprehensions are concise, Pythonic ways to create lists, running faster than equivalent for-loops due to bytecode optimisation. I use them for data transformations: normalising column names, type mapping, batch filtering. However, avoid them when: (1) the expression is complex and readability suffers; (2) the result list is huge and only iterated once — use a generator expression instead (`sum(x for x in data)`); (3) multiple nested operations are needed — a named function is cleaner and testable.

---

**Q4. Explain Python's GIL and its impact on data engineering workloads.**

The GIL prevents multiple Python threads from executing Python bytecode simultaneously. For CPU-bound tasks (data transformation), threading provides no parallelism — you need `multiprocessing`. However, for I/O-bound tasks (network calls, database queries, file reads), threads work well because the GIL is released during I/O waits. In data pipelines, most parallelism is I/O-bound: concurrent BigQuery queries, parallel GCS reads, simultaneous API calls — `ThreadPoolExecutor` is appropriate for these. For CPU-intensive transformation at scale, we offload to Spark rather than fighting the GIL.

---

**Q5. What are decorators? Give a practical data engineering example.**

A decorator wraps a function to add behaviour without modifying the original — a clean way to handle cross-cutting concerns. In CDM Next, I built a `@retry_with_backoff` decorator that automatically retried any decorated function on transient errors (API rate limits, network timeouts) with exponential backoff and jitter. Applied once to all external API call functions — retry logic stayed in one place, not duplicated across every function. Same pattern for `@log_execution_time`, `@validate_output`, and `@require_config`.

---

**Q6. Explain *args and **kwargs.**

`*args` captures any number of positional arguments as a tuple; `**kwargs` captures keyword arguments as a dictionary. In data engineering, `**kwargs` is particularly useful for passing configuration options through abstraction layers without changing function signatures. A `load_to_bigquery(**options)` function can forward options like `write_disposition`, `schema`, and `partition_field` to the underlying client — you can add new options without updating signatures everywhere they're called. Also essential in decorators for transparently wrapping any function: `def wrapper(*args, **kwargs): return func(*args, **kwargs)`.

---

## SECTION 2: OOP AND DESIGN PATTERNS

**Q7. Why do you use abstract base classes in pipeline design?**

Abstract base classes enforce a contract across different implementations. In CDM Next, we needed extractors for Teradata, Oracle, Hadoop/Hive, Kafka, and file-based sources. By defining `BaseExtractor` with abstract methods `connect()`, `extract()`, and `get_row_count()`, we guaranteed every extractor implementation provided these methods — missing one caused an error at instantiation, not at runtime during count validation. This also enabled the Factory Pattern: pipeline orchestration code works against the `BaseExtractor` interface without knowing which concrete extractor is used. Adding a new source type meant writing one new class — zero changes to pipeline logic.

---

**Q8. Explain the Factory Pattern and how you've used it.**

The Factory Pattern separates object creation from object use — a factory decides which concrete class to instantiate based on configuration. In CDM Next, `ExtractorFactory.create(config)` looked up the registered extractor class for `config.source_type` and returned the appropriate instance. The pipeline code never had `if source == "teradata": ... elif source == "oracle": ...` — it just called the factory and worked with the returned extractor. This was critical because CDM Next was configuration-driven: application teams submitted YAML configs specifying their source system, and the framework handled 5+ source types without hardcoded conditionals.

---

**Q9. What is a context manager and why is it important in data pipelines?**

A context manager (used with `with`) guarantees setup and teardown runs regardless of exceptions — essential for resource management. I implement `__enter__` and `__exit__` on all extractors: `__enter__` establishes the database connection, `__exit__` closes it. If a batch fails halfway through, the connection always closes cleanly — no leaked connections. Beyond connections, I use context managers for: audit logging (log start in enter, log completion/failure in exit), temporary GCS file management, and BigQuery job wrappers.

---

**Q10. What is the difference between shallow copy and deep copy? When does it matter in pipelines?**

A shallow copy creates a new object but copies references to nested objects — modifying a nested dict in the copy modifies the original. A deep copy creates fully independent copies of all nested objects. This matters when transforming batches: `transformed = batch` is assignment (same object); `transformed = batch.copy()` is shallow (dict references shared). The safe pattern is creating new dictionaries during transformation rather than mutating: `[{**row, "new_key": transform(row)} for row in batch]` — each row is a new dict, originals are untouched.

---

## SECTION 3: ETL PATTERNS

**Q11. How do you design a Python ETL pipeline for resilience?**

Resilience comes from multiple layers: (1) **Batch processing with checkpointing** — track completed batches, resume from failure rather than restart; (2) **Retry logic with backoff** on all external calls; (3) **Partial failure tolerance** — one bad record doesn't fail the batch; route to dead letter queue, continue; (4) **Idempotency** — running twice produces the same result; use partition overwrite or MERGE/upsert; (5) **Audit logging** — persist run state (start, end, rows, errors) to BigQuery; (6) **Circuit breakers** — stop processing if error rate exceeds threshold. CDM Next implemented all six layers, which is why 60+ application teams could rely on it for petabyte-scale migration with minimal manual intervention.

---

**Q12. How do you handle schema evolution in Python ETL pipelines?**

Schema evolution is one of the trickiest pipeline challenges. My approach: (1) **Schema detection at extraction** — compare source schema against expected target schema before every run; fail fast on breaking changes; (2) **Non-breaking changes handled automatically** — new nullable columns are added to target with NULLs; (3) **Breaking changes require approval** — column renames, type changes, removals trigger alerts and pause the pipeline; (4) **Schema versioning** — store schema snapshots in BigQuery, detect drift by comparison; (5) **Explicit schema management** — use `autodetect=False` in BigQuery loads and manage schema changes via the BigQuery API. In CDM Next, a schema registry table tracked the expected schema per source table, and every run validated against it.

---

**Q13. How do you make a Python data pipeline idempotent?**

Idempotency means re-running produces the same result, not duplicates. Best approaches: (1) **Partition overwrite** — write to a specific date partition with `WRITE_TRUNCATE` on that partition; re-running overwrites rather than appends; cleanest for batch pipelines; (2) **MERGE/UPSERT** — BigQuery MERGE inserts new records and updates existing ones based on primary key; (3) **Run ID deduplication** — check if run_id exists in audit table before processing; skip if already completed; (4) **Deduplication after load** — allow duplicates on load, deduplicate using `ROW_NUMBER()`. The partition overwrite pattern is what we used in CDM Next for all daily batch loads.

---

**Q14. How do you handle NULL values in Python data pipelines?**

Nulls need handling at every stage: (1) **At extraction** — check nulls in primary keys and required fields; fail early with clear errors; (2) **At transformation** — use `row.get("column", default)` for safe access; use `or` for fallback: `value = raw_value or "UNKNOWN"`; (3) **At validation** — monitor null rates per column; alert if rate exceeds threshold (> 5% in a previously non-null column signals a source issue); (4) **At load** — understand target NULL semantics; in BigQuery, NULL in arithmetic returns NULL, not error; (5) **Type coercion** — treat `None`, `0`, and `""` as semantically distinct; don't coalesce carelessly.

---

## SECTION 4: PYSPARK

**Q15. Explain the difference between transformations and actions in Spark.**

Transformations are lazy — they define what to do but don't execute: `filter()`, `select()`, `join()` build a logical plan. Actions trigger execution: `count()`, `collect()`, `show()`, `write.save()`. Laziness enables Spark's Catalyst optimiser to look at the entire chain and pick the best physical plan — reordering filters, choosing join strategies, pruning data. The implication: chain transformations, then call one action. Calling `df.count()` after each transformation to log progress triggers a full job each time — extremely expensive. Log once at the end, or use `df.sample(0.001).count()` for estimates.

---

**Q16. When would you use repartition vs coalesce?**

`repartition(n)` does a full shuffle — data moves across the network to create n evenly distributed partitions. Use when increasing partition count, fixing skew, or partitioning by a specific column for join performance. `coalesce(n)` reduces partitions without a full shuffle — combines local partitions only. Use when reducing partition count before writing to avoid creating too many small output files. In CDM Next: repartition by primary key before large joins (ensures co-location), then coalesce before writing to GCS to control output file count and avoid the "small files problem."

---

**Q17. How do you handle data skew in Spark?**

Data skew means some partitions have vastly more data — one executor does 80% of the work, causing slowdowns or OOM. Three solutions: (1) **Broadcast join** — if the smaller join table is < 200MB, broadcast it to all executors; eliminates shuffle entirely; (2) **AQE (Spark 3+)** — `spark.sql.adaptive.skewJoin.enabled=true` automatically splits skewed partitions at runtime; (3) **Salting** — add a random integer suffix (0–9) to the skewed key; explode the dimension table with each suffix; join on salted key; distributes one large key across 10 partitions. We used salting in CDM Next for Teradata tables where a few customer IDs had hundreds of millions of transactions.

---

**Q18. When should you use a Pandas UDF instead of a regular UDF?**

Regular PySpark UDFs operate row-by-row: Spark serialises each row to Python, calls the function, deserialises — enormous overhead at millions of rows. Pandas UDFs (vectorised UDFs) operate on entire columns as Pandas Series using Apache Arrow for zero-copy serialisation, achieving 10–100x better performance. Use Pandas UDFs when you need custom Python logic that native Spark SQL functions can't express. But always prefer native functions (`F.when`, `F.regexp_extract`, `F.date_format`) — they compile to JVM code and are fastest. UDFs only when native SQL genuinely can't express the logic.

---

**Q19. Explain Spark's execution model: jobs, stages, and tasks.**

When an action triggers, Spark creates a job. The job is divided into stages at shuffle boundaries — whenever data must move between executors (joins, groupBy, repartition), a new stage begins. Each stage is divided into tasks — one task per partition. Tasks are the unit of parallelism: each runs on one executor core, processing one partition. Understanding this helps diagnose issues: too few tasks = low parallelism (add partitions); uneven task durations = data skew; too many stages = too many shuffles (reorder operations or cache intermediates).

---

**Q20. What is the difference between persist() and cache() in Spark?**

`cache()` is shorthand for `persist(StorageLevel.MEMORY_AND_DISK)` — stores in memory, spills to disk if needed. `persist()` gives explicit control: `MEMORY_ONLY` (fastest, risks OOM), `DISK_ONLY` (slowest, reliable), `MEMORY_AND_DISK_SER` (serialised, saves memory), `OFF_HEAP`. Use caching only when a DataFrame is used in multiple actions in the same job — otherwise wastes memory. Always call `unpersist()` when done. In CDM Next, I cached validated DataFrames used for both BigQuery loading and validation report generation — without caching, Spark would recompute the entire validation chain twice.

---

## SECTION 5: TESTING

**Q21. How do you test a data pipeline effectively?**

Testing data pipelines requires layers: (1) **Unit tests** — test individual transformation functions with small hand-crafted data; mock all external dependencies; run in milliseconds; (2) **Integration tests** — test end-to-end flow against real infrastructure with representative data samples; (3) **Data quality tests** — validate output properties: row counts, null rates, value distributions, referential integrity; (4) **Regression tests** — maintain a golden dataset with known inputs and expected outputs; run on every code change. In CDM Next, every pipeline ran a post-load validation comparing source and target row counts, alerting on any difference above 0.01%.

---

**Q22. How do you mock external dependencies in pipeline tests?**

Use `unittest.mock.patch` to replace external dependencies with controlled mocks. Key patterns: (1) `@patch("my_module.bigquery.Client")` replaces the BQ client with MagicMock; set `mock.insert_rows_json.return_value = []` for success; `[{"errors": [...]}]` for failure; (2) Similarly mock `storage.Client` for GCS; (3) Use `responses` library to mock HTTP endpoints without network calls; (4) Use pytest's `tmp_path` fixture for temporary files. Core principle: unit tests must never make real network calls — must be deterministic, fast (< 1s per test), and runnable without GCP credentials.

---

## SECTION 6: PYTHON AT SCALE

**Q23. How do you process a 100GB CSV file in Python without running out of memory?**

Three approaches: (1) **Chunked Pandas** — `pd.read_csv("file.csv", chunksize=100_000)` reads 100K rows at a time; process each chunk and aggregate or write output; good for single-machine, files up to a few hundred GB; (2) **Generator streaming** — open file as text stream, yield one line at a time, parse and process; minimal memory footprint; (3) **Spark on Dataproc** — for truly large files or when parallelism matters, `spark.read.csv(path)` distributes across the cluster; each executor handles one partition. In CDM Next, generator-based extraction meant the pipeline never held more than one batch in memory regardless of source table size.

---

**Q24. What Python libraries are essential for a GCP data engineer?**

GCP clients: `google-cloud-bigquery`, `google-cloud-storage`, `google-cloud-secret-manager`, `google-cloud-pubsub`, `google-cloud-logging`. Data processing: `pandas`, `pyspark`, `pyarrow` (columnar I/O, Arrow bridge), `sqlalchemy` (database abstraction for legacy sources). Airflow: `apache-airflow`, `apache-airflow-providers-google`. Utilities: `pydantic` (validation, settings), `tenacity` (retry logic), `pytest` (testing), `python-dotenv` (local env vars). For GenAI: `langchain-google-vertexai`, `vertexai` SDK.

---

**Q25. How would you optimise a slow Python ETL script?**

Profile first — never optimise blind. Use `cProfile` to find the actual bottleneck. Common findings: (1) **Python loop over rows** — vectorise with Pandas or Spark; `apply()` is always slower than `str.method()` or numpy ops; (2) **Sequential API calls** — parallelise with `ThreadPoolExecutor` for I/O-bound work; (3) **Loading all data into memory** — switch to chunked/streaming reads; (4) **Repeated computation** — cache with `@functools.lru_cache` or persist to GCS/BQ; (5) **Python UDFs in Spark** — replace with native Spark SQL or Pandas UDFs; (6) **Too many small files** — coalesce Spark output to fewer, larger partitions before writing.

---

*End of Python for Data Engineering Q&A*
