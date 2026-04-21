# Apache Iceberg — Complete Textbook: From Zero to Expert
## Data Engineering Interview Preparation — Exhaustive Reference

---

## Table of Contents

1. [What is Apache Iceberg and Why It Was Created](#1-what-is-apache-iceberg-and-why-it-was-created)
2. [The Problem with Data Lakes Before Iceberg](#2-the-problem-with-data-lakes-before-iceberg)
3. [Iceberg Architecture — Tables, Metadata, Files](#3-iceberg-architecture--tables-metadata-files)
4. [Iceberg Catalog — The Registration Layer](#4-iceberg-catalog--the-registration-layer)
5. [Snapshot-Based Design — How Changes Work](#5-snapshot-based-design--how-changes-work)
6. [Schema Evolution — Changing Schemas Safely](#6-schema-evolution--changing-schemas-safely)
7. [Partition Evolution — Changing Partitioning Without Rewrites](#7-partition-evolution--changing-partitioning-without-rewrites)
8. [ACID Transactions on the Data Lake](#8-acid-transactions-on-the-data-lake)
9. [Time Travel and Rollback](#9-time-travel-and-rollback)
10. [Row-Level Operations — Deletes, Updates, Merges](#10-row-level-operations--deletes-updates-merges)
11. [Maintenance Operations — Compaction, Expiration](#11-maintenance-operations--compaction-expiration)
12. [Iceberg with Different Query Engines](#12-iceberg-with-different-query-engines)
13. [Iceberg in GCP — BigLake and BigQuery Integration](#13-iceberg-in-gcp--biglake-and-bigquery-integration)
14. [Iceberg vs Delta Lake vs Hudi — Table Format Comparison](#14-iceberg-vs-delta-lake-vs-hudi--table-format-comparison)
15. [Real-World Patterns and Use Cases](#15-real-world-patterns-and-use-cases)
16. [Interview Questions — Easy to Very Hard](#16-interview-questions--easy-to-very-hard)

---

## 1. What is Apache Iceberg and Why It Was Created

### 1.1 The Simple Definition

Apache Iceberg is an **open table format** for huge analytic datasets. It is NOT a storage system — it doesn't store your actual data files. Instead, it defines how to organize, track, and manage a collection of data files (Parquet, ORC, Avro) to give them database-like capabilities.

Think of it this way:

```
WITHOUT ICEBERG:
  You have a folder of Parquet files in S3:
  s3://my-bucket/events/year=2024/month=01/day=15/
    file_001.parquet
    file_002.parquet
    file_003.parquet
  
  This is just a collection of files.
  • No transaction guarantees
  • No way to do UPDATE or DELETE on individual rows
  • No schema history
  • Changing the partitioning requires rewriting all files
  • Multiple writers can corrupt data (race conditions)

WITH ICEBERG:
  Same Parquet files, PLUS a metadata layer that tracks:
  • Exactly which files belong to "this version" of the table
  • The schema of the table (and all past schemas)
  • The partition structure (and all past structures)
  • Statistics about each file (for query optimization)
  • Full history of every change (snapshots)
  
  Now these files behave like a database table:
  • ACID transactions (safe concurrent writes)
  • UPDATE and DELETE on specific rows
  • Schema evolution without rewriting data
  • Partition evolution without rewriting data
  • Time Travel to any past snapshot
  • Complete audit trail
```

### 1.2 Who Created Iceberg and Why

Apache Iceberg was created by **Netflix** engineers (Ryan Blue, Daniel Carl, others) starting around 2017, open-sourced in 2018, and graduated to a top-level Apache project in 2020.

Netflix's specific problems that motivated Iceberg:

**Problem 1: Hive tables on S3 at petabyte scale were broken**

Netflix had petabyte-scale Hive tables with billions of files. Operations like `ALTER TABLE ... ADD PARTITION` required updating a centralized Hive Metastore — a single MySQL database that became a severe bottleneck. Listing all files in a table could take hours.

**Problem 2: Concurrent writers caused data corruption**

Multiple Spark jobs writing to the same Hive table simultaneously could corrupt data. There was no mechanism to ensure atomic writes.

**Problem 3: Schema changes required full table rewrites**

Changing a column type, adding a column, or renaming a column in Hive often meant rewriting the entire dataset — impractical at petabyte scale.

**Problem 4: Partition changes required full rewrites**

Changing from daily to hourly partitioning in Hive meant rewriting all historical data with the new directory structure.

Iceberg solved ALL of these problems with a carefully designed metadata architecture.

---

### 1.3 Iceberg vs Parquet: A Common Confusion

**Parquet is a file format.** It defines how data is encoded and compressed within a single file. It's columnar, efficient, and widely supported.

**Iceberg is a table format.** It sits ABOVE Parquet and manages a collection of Parquet (or ORC or Avro) files as a coherent table with transactions, schema, partitioning, and history.

```
ANALOGY:
  Parquet = a chapter of a book (contains actual content, well-organized)
  Iceberg = the library catalog system (tracks all the chapters,
            their order, their history, which chapters are current
            vs archived, how to find specific information)

  The library catalog doesn't replace the chapters — it makes them
  manageable and queryable as a coherent whole.
```

---

## 2. The Problem with Data Lakes Before Iceberg

### 2.1 The Traditional Hive Table Problem

Before Iceberg, the dominant approach for large-scale data lakes was **Hive tables** — directories of Parquet/ORC files organized with Hive's partition naming convention.

```
Traditional Hive Table on S3:

s3://my-bucket/events/
├── year=2024/
│   ├── month=01/
│   │   ├── day=01/
│   │   │   ├── part-00000.parquet
│   │   │   └── part-00001.parquet
│   │   ├── day=02/
│   │   │   └── part-00000.parquet
│   │   └── ...
│   └── month=02/
│       └── ...
└── year=2023/
    └── ...

Hive Metastore (MySQL database):
  Stores: table name, partition names, S3 locations, schema

Problems with this approach:
```

**Problem 1: Partition listing is catastrophically slow at scale**

```
Hive: "What files belong to this table?"
  → Query Hive Metastore for all partitions
  → If table has 10,000 partitions: 10,000 database rows to fetch
  → If table has 1,000,000 partitions (Netflix scale): fails or takes hours
  → S3 LIST operations are slow: listing 1M files = minutes

Iceberg: "What files belong to this table?"
  → Read one metadata file (pointer chain)
  → From that, read manifest list (one file, lists all manifests)
  → From manifests, get exact file locations
  → Total: 3-5 file reads regardless of table size
  → Milliseconds even for tables with 100 million files
```

**Problem 2: No atomicity — concurrent writes cause corruption**

```
SCENARIO: Two Spark jobs write to the same Hive table simultaneously

Job A: Writes 10 new Parquet files for January data
Job B: Writes 8 new Parquet files for January data (at the same time)

Job A finishes → updates Hive Metastore partition
Job B finishes → overwrites that partition with its version

RESULT: Data from Job A is lost!
Or worse: the table points to a mix of files from both jobs → corrupted data

Iceberg uses optimistic concurrency control to prevent this:
  • Each writer computes a new snapshot based on current state
  • Writer atomically commits the snapshot IF the table hasn't changed
  • If another writer committed first: retry or fail with conflict error
  • It is IMPOSSIBLE for two writers to corrupt each other's data
```

**Problem 3: Schema changes require full rewrites**

```
Hive: Add a column to a 10TB table
  → No safe in-place schema update exists
  → Must either:
    a) Rewrite all 10TB of data with the new schema → days of compute
    b) Add the column and deal with NULL/missing values in old files → messy
    c) Use schema-on-read and hope your readers handle it → fragile

Iceberg: Add a column to a 10TB table
  → Update one metadata file (add column to the schema version)
  → Takes milliseconds
  → Old Parquet files don't change — readers see NULL for the new column in old data
  → New Parquet files include the new column
  → All readers see a consistent schema regardless of which files they read
```

**Problem 4: No update or delete on individual rows**

```
Hive: "Delete user U12345's data (GDPR right to erasure)"
  → Hive doesn't support row-level deletes
  → Must read entire partition, filter out the row, rewrite entire partition
  → For a 1TB partition: read 1TB, write 1TB = 2TB of I/O just to delete one row

Iceberg: "Delete user U12345's data"
  → Write a small "delete file" that records "row with user_id=U12345 is deleted"
  → Original data files are untouched (no rewrite)
  → Query engines merge delete files with data files at read time
  → Later: background compaction merges and removes the deleted rows physically
```

---

## 3. Iceberg Architecture — Tables, Metadata, Files

### 3.1 The Four-Layer Architecture

Iceberg organizes a table into four distinct layers. Understanding these layers is the foundation of all Iceberg knowledge.

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  LAYER 1: CATALOG                                                   │
│  ─────────────────                                                  │
│  "Where does this table's metadata live?"                           │
│                                                                      │
│  catalog.my_database.my_table → s3://bucket/table/metadata/         │
│                                   v3.metadata.json  (current)       │
│                                                                      │
│  The catalog maps table names → metadata file locations             │
│  Examples: Hive Metastore, AWS Glue, Nessie, REST Catalog           │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  LAYER 2: METADATA FILES                                            │
│  ───────────────────────                                            │
│  "What is the current state of this table?"                         │
│                                                                      │
│  v3.metadata.json:                                                  │
│  {                                                                  │
│    "format-version": 2,                                             │
│    "current-snapshot-id": 9999,                                     │
│    "schemas": [{id:0, cols:[...]}, {id:1, cols:[...]}],             │
│    "current-schema-id": 1,                                          │
│    "partition-specs": [{...}, {...}],                               │
│    "sort-orders": [...],                                            │
│    "snapshots": [                                                   │
│      {snapshot-id: 9998, manifest-list: "snap-9998.avro"},         │
│      {snapshot-id: 9999, manifest-list: "snap-9999.avro"}          │
│    ]                                                                │
│  }                                                                  │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  LAYER 3: MANIFEST FILES (the index)                                │
│  ──────────────────────────────────                                 │
│  "Exactly which data files belong to this snapshot?"                │
│                                                                      │
│  snap-9999-manifest-list.avro (the "manifest list"):                │
│  → Points to: manifest-A.avro (contains 500 data file entries)      │
│  → Points to: manifest-B.avro (contains 300 data file entries)      │
│  → Points to: manifest-C.avro (contains 200 data file entries)      │
│                                                                      │
│  manifest-A.avro (one manifest):                                    │
│  For each data file it tracks:                                      │
│  • File path (s3://bucket/table/data/part-0001.parquet)             │
│  • File format (PARQUET)                                            │
│  • Partition data (click_date='2024-01-15')                         │
│  • Row count                                                        │
│  • File size                                                        │
│  • Column-level statistics: lower_bound, upper_bound, null_count    │
│  • Status: ADDED or DELETED or EXISTING                             │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  LAYER 4: DATA FILES                                                │
│  ──────────────────                                                 │
│  The actual Parquet/ORC/Avro files in S3/GCS/HDFS                  │
│                                                                      │
│  s3://bucket/table/data/                                            │
│  ├── 00000-0-abc123.parquet  (2M rows, Jan 15 data)                 │
│  ├── 00001-0-def456.parquet  (1.8M rows, Jan 15 data)              │
│  ├── 00000-1-ghi789.parquet  (2.1M rows, Jan 16 data)              │
│  └── ...                                                            │
│                                                                      │
│  DELETE FILES (for row-level deletes without rewriting):            │
│  ├── eq-delete-00001.avro  (equality deletes: WHERE user_id='X')   │
│  └── pos-delete-00001.avro (positional deletes: row N in file F)    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Walking Through the Architecture

Let's trace exactly what happens when you read `SELECT * FROM events WHERE click_date = '2024-01-15'`:

```
STEP 1: Catalog lookup
  Engine asks catalog: "Where is the metadata for table 'events'?"
  Catalog returns: "s3://bucket/events/metadata/v5.metadata.json"

STEP 2: Read metadata file
  Engine reads v5.metadata.json
  Finds: current-snapshot-id = 8712
  Finds: snapshot 8712's manifest list is at "snap-8712.avro"

STEP 3: Read manifest list
  Engine reads snap-8712.avro
  Finds: this snapshot has 3 manifest files
    manifest-001.avro (partition range: click_date 2024-01-01 to 2024-01-15)
    manifest-002.avro (partition range: click_date 2024-01-16 to 2024-01-31)
    manifest-003.avro (partition range: click_date 2024-02-01 to 2024-02-28)
  
  PARTITION PRUNING: We want click_date = '2024-01-15'
  manifest-002 range starts at Jan 16 → SKIP
  manifest-003 range starts at Feb 1  → SKIP
  Only read manifest-001 → 66% of manifests pruned already!

STEP 4: Read manifest-001
  Engine reads manifest-001.avro
  Contains entries for ~500 data files
  Each entry has: lower_bound and upper_bound for click_date column
  
  FILE PRUNING:
  Files where lower_bound > '2024-01-15': SKIP
  Files where upper_bound < '2024-01-15': SKIP
  Files that overlap with '2024-01-15': READ
  
  Say 490 of 500 files are pruned → read only 10 files!

STEP 5: Read data files + apply delete files
  Engine reads the 10 relevant Parquet files
  Also checks: are there any delete files for these data files?
  If yes: merge deletes at read time (positions or equality matching)
  
  Returns only rows where click_date = '2024-01-15'

Total metadata reads: 4 (catalog + metadata file + manifest list + one manifest)
Total data files read: 10 out of potentially millions
This is what makes Iceberg fast at scale.
```

### 3.3 Manifest Files in Detail — The Power of Column Statistics

Each entry in a manifest file contains rich statistics about the data file it represents:

```
Manifest entry for file "part-00042.parquet":

{
  "status": "ADDED",
  "snapshot_id": 8712,
  "data_file": {
    "content": "DATA",
    "file_path": "s3://bucket/events/data/part-00042.parquet",
    "file_format": "PARQUET",
    "partition": {"click_date": "2024-01-15"},
    "record_count": 2_150_000,
    "file_size_in_bytes": 245_678_901,
    "column_sizes": {
      "click_id": 120_MB,
      "cost_usd": 18_MB,
      ...
    },
    "value_counts": {
      "click_id": 2_150_000,
      "cost_usd": 2_148_000   // 2,000 nulls
    },
    "null_value_counts": {
      "cost_usd": 2000
    },
    "lower_bounds": {
      "click_id": "C_000001",
      "click_date": "2024-01-15",
      "cost_usd": 0.01
    },
    "upper_bounds": {
      "click_id": "C_999999",
      "click_date": "2024-01-15",
      "cost_usd": 487.50
    }
  }
}
```

**Why column statistics matter for query planning**:

```
Query: WHERE cost_usd > 500
  
  For file part-00042.parquet:
    upper_bound for cost_usd = 487.50
    487.50 < 500 → NO row in this file can satisfy cost_usd > 500
    → SKIP this file entirely (data pruning, no I/O needed)
  
  For file part-00987.parquet:
    upper_bound for cost_usd = 2500.00
    lower_bound for cost_usd = 450.00
    Could contain rows where cost_usd > 500 → must READ
  
  This is "file-level pruning" based on manifest statistics.
  Works for any column, not just partition columns — huge advantage over Hive.
```

---

## 4. Iceberg Catalog — The Registration Layer

### 4.1 What is a Catalog?

The catalog is the entry point for Iceberg tables. It serves one primary purpose: mapping a table name (like `my_db.my_table`) to the current metadata file location on storage.

Without a catalog, you'd have to know the exact path of the metadata file — tables would have no names, no namespace, no discoverability.

```
CATALOG RESPONSIBILITIES:

1. NAME RESOLUTION: "events" → s3://bucket/events/metadata/v5.metadata.json
2. ATOMIC COMMITS: When a new snapshot is created, atomically update 
                   the catalog's pointer from v4 to v5
3. NAMESPACE MANAGEMENT: databases, schemas, catalogs hierarchy
4. LOCKING: prevent concurrent writers from committing conflicting snapshots

"Atomic commit" is the KEY property:
  Without atomic updates, two writers updating the same table
  could each read "current metadata = v4", write their changes,
  and both try to commit "new current metadata = v5"
  → one writer's changes are silently lost
  
  With atomic compare-and-swap in the catalog:
  Writer A: "set current to v5-A if current is still v4" → SUCCESS
  Writer B: "set current to v5-B if current is still v4" → FAILS (it's now v5-A)
  Writer B: retries with conflict resolution
  → No data loss, both changes preserved eventually
```

### 4.2 Catalog Implementations

There are multiple catalog implementations, each with different trade-offs:

**Hive Metastore**

```
HIVE METASTORE CATALOG:

  ┌────────────────────────────────────────┐
  │         MySQL / PostgreSQL             │
  │  Table: iceberg_tables                 │
  │  id | db    | table  | metadata_loc    │
  │  1  | mydb  | events | s3://...v5.json │
  └────────────────────────────────────────┘

  Pros:
  + Already deployed in most enterprises
  + Works with existing Spark/Hive infrastructure
  + Widely supported by all query engines

  Cons:
  - Single point of failure (MySQL outage = no table access)
  - Limited scalability for 10,000+ tables
  - No built-in multi-version history of catalog state
  - Lock contention with many concurrent writers

  Usage: Most common in legacy environments
```

**AWS Glue Catalog**

```
AWS GLUE CATALOG:

  Managed by AWS — no database to run yourself
  
  Stores: table name → metadata file location (just like Hive Metastore)
  Works with: Spark, Athena, Flink, Trino
  
  Pros:
  + Fully managed, highly available
  + Native integration with Athena, S3, EMR
  + No operational overhead
  
  Cons:
  - AWS-only (vendor lock-in)
  - Limited ACID guarantees for concurrent writers
  - Rate limits can be an issue at high scale

  Usage: Standard choice for AWS-based data lakes
```

**Project Nessie**

```
PROJECT NESSIE CATALOG:

  Open-source, Git-like catalog for data lakes
  
  Key feature: BRANCHING AND MERGING (like Git, but for data tables)
  
  ┌──────────────────────────────────────────────────┐
  │  main branch      → Production tables            │
  │       │                                          │
  │  dev  branch      → Dev environment tables       │
  │  (from main at   → Can write freely, test changes│
  │   a point)       → Merge to main when ready     │
  └──────────────────────────────────────────────────┘
  
  Pros:
  + Experiment without affecting production
  + Tag specific states (like release tags in Git)
  + Full history of all table changes
  + Multi-engine support
  
  Cons:
  - Requires running the Nessie server
  - Less battle-tested at very large scale than Hive/Glue

  Usage: Modern data platforms, data mesh architectures
  Nessie is built into Dremio (commercial offering)
```

**REST Catalog**

```
REST CATALOG (Iceberg spec v1 and newer):

  A standard HTTP API specification for Iceberg catalogs.
  Any HTTP service that implements the spec can be an Iceberg catalog.
  
  Examples:
  - Tabular (Snowflake's Iceberg catalog product)
  - Polaris (open-source implementation from Snowflake/Apple)
  - Dremio Arctic
  
  Pros:
  + Standard interface (not tied to any specific implementation)
  + Can add auth, governance, metrics at the API layer
  + Language and platform agnostic
  + Increasingly the "default" catalog choice for new systems

  Usage: Increasingly preferred for new greenfield deployments
```

---

## 5. Snapshot-Based Design — How Changes Work

### 5.1 What is a Snapshot?

Every time you change an Iceberg table — whether you INSERT new rows, DELETE rows, UPDATE rows, or do a bulk COPY — Iceberg creates a new **snapshot**. A snapshot is an immutable, complete view of the table at a specific point in time.

```
SNAPSHOT TIMELINE:

  Snapshot 1001 (created 09:00):
    "The table as it was at 9 AM"
    Points to: manifest files for the original 100 data files
  
  INSERT 5M rows (09:30) →
  
  Snapshot 1002 (created 09:30):
    "The table as it was at 9:30 AM"
    Points to: 
      • manifest for the SAME 100 original data files (unchanged)
      • manifest for 3 NEW data files (the inserted rows)
    Total: 103 data files

  DELETE WHERE date < '2023-01-01' (10:00) →
  
  Snapshot 1003 (created 10:00):
    "The table as it was at 10 AM"
    Points to:
      • manifest for 80 of the original 100 files (20 are old, now deleted)
      • manifest for 3 NEW files
      • delete file recording which rows to exclude from the 80 files
    
  Table name in catalog → points to snapshot 1003 (current)
  Old snapshots 1001 and 1002 still exist until explicitly expired
```

### 5.2 Copy-On-Write vs Merge-On-Read

This is one of the most important concepts in Iceberg — and a very common interview question. Iceberg supports two modes for handling row-level changes:

**Copy-On-Write (COW)**

```
COPY-ON-WRITE (COW) — THE REWRITE APPROACH:

When you DELETE or UPDATE rows in Copy-On-Write mode:
  1. Read the affected data files completely
  2. Apply the change (filter out deleted rows, apply updates)
  3. Write entirely new data files with the changes applied
  4. The new snapshot points to the new files instead of the old ones

EXAMPLE: DELETE 1,000 rows from a 1GB Parquet file

  Before: snapshot → [file_A.parquet: 1,000,000 rows, 1GB]
  
  Operation: DELETE 1,000 rows where user_id = 'GDPR_REQUEST_42'
  
  After (COW): 
  Read 1GB → filter out 1,000 rows → Write 0.999GB new file
  Snapshot → [file_A_new.parquet: 999,000 rows, ~0.999GB]
  
  Old file_A.parquet still exists (for Time Travel) but is no longer in the current snapshot.

WRITE characteristics:
  ✗ Expensive: Must rewrite entire affected files (lots of I/O)
  ✗ Slow for small changes in large files
  
READ characteristics:
  ✓ Fast: No merge step needed — files are "clean" (no pending deletes)
  ✓ Simple: Query engines just read the Parquet files
  
GOOD FOR:
  • Batch ETL workloads (bulk inserts, large updates)
  • Workloads where reads >> writes in frequency
  • GDPR bulk deletion jobs (run once, fast reads forever)
```

**Merge-On-Read (MOR)**

```
MERGE-ON-READ (MOR) — THE LAZY APPROACH:

When you DELETE or UPDATE rows in Merge-On-Read mode:
  1. Don't touch the original data files
  2. Write a small "delete file" recording which rows are deleted
  3. The new snapshot references both the original data file AND the delete file

EXAMPLE: DELETE 1,000 rows from a 1GB Parquet file

  Before: snapshot → [file_A.parquet: 1,000,000 rows, 1GB]
  
  Operation: DELETE 1,000 rows where user_id = 'GDPR_REQUEST_42'
  
  After (MOR):
  Write tiny delete file: {equality_deletes: [{user_id: 'GDPR_REQUEST_42'}]}
  
  Snapshot → {
    data_files: [file_A.parquet: 1,000,000 rows, 1GB],
    delete_files: [eq_delete_001.avro: 1,000 delete records]
  }
  
  file_A.parquet is NOT rewritten.

WRITE characteristics:
  ✓ Very fast: Just write a tiny delete file (kilobytes)
  ✓ Low I/O for small changes in large files
  
READ characteristics:
  ✗ Slower: Must merge data file with delete file at read time
  ✗ Many accumulated delete files = significant read overhead
  ✗ Delete files accumulate over time (need periodic compaction)
  
GOOD FOR:
  • Streaming inserts with frequent small updates
  • Near-real-time ingestion where write latency matters
  • Use cases where reads can tolerate some overhead
  
COMPACTION CLOSES THE GAP:
  Periodic background job reads data files + delete files,
  produces new "clean" data files with deletes applied,
  then deletes the old delete files.
  After compaction: reads are as fast as COW.
```

**Visual comparison**:

```
OPERATION: UPDATE 100 rows in a table with 1 million rows across 5 files

                COW                              MOR
                ───                              ───
WRITE:          Read all affected files          Write tiny delete file
                Rewrite with updates applied     Write new file with updated rows
                Time: minutes (large I/O)        Time: seconds (tiny write)

READ:           Read clean files                 Read data files PLUS
(before compact) No overhead                     merge with delete files
                Fast                             Slower (merge overhead)

READ:           Same as before                   Same as COW
(after compact) Fast                             Fast (after compaction)

STORAGE:        Old files kept for TT            Both old data + delete files
                New files for current data       kept until compaction + expiry
```

---

## 6. Schema Evolution — Changing Schemas Safely

### 6.1 The Problem Schema Evolution Solves

In a traditional data lake, if you add a column to your Parquet files, you have a mess:
- Old files don't have the column
- New files do have the column
- Query engines don't know how to reconcile them safely
- You might need to rewrite all old files

Iceberg solves this cleanly and permanently.

### 6.2 How Iceberg Schema Evolution Works

Iceberg tracks schemas by **schema ID**, not by column position. Every column has a unique field ID that never changes, even if the column is renamed, moved, or the schema is otherwise restructured.

```
ICEBERG SCHEMA TRACKING:

Schema v1 (initial):
  {
    "schema-id": 0,
    "fields": [
      {"id": 1, "name": "click_id",    "type": "string",  "required": true},
      {"id": 2, "name": "campaign_id", "type": "string",  "required": true},
      {"id": 3, "name": "cost_usd",    "type": "double",  "required": false},
      {"id": 4, "name": "clicked_at",  "type": "timestamptz"}
    ]
  }

Schema v2 (after ADD COLUMN device_type):
  {
    "schema-id": 1,
    "fields": [
      {"id": 1, "name": "click_id",    "type": "string"},  ← same ID
      {"id": 2, "name": "campaign_id", "type": "string"},  ← same ID
      {"id": 3, "name": "cost_usd",    "type": "double"},  ← same ID
      {"id": 4, "name": "clicked_at",  "type": "timestamptz"},  ← same ID
      {"id": 5, "name": "device_type", "type": "string"}   ← NEW, ID=5
    ]
  }

Schema v3 (after RENAME cost_usd → cost):
  {
    "schema-id": 2,
    "fields": [
      {"id": 1, "name": "click_id"},
      {"id": 2, "name": "campaign_id"},
      {"id": 3, "name": "cost"},        ← renamed, but ID=3 UNCHANGED
      {"id": 4, "name": "clicked_at"},
      {"id": 5, "name": "device_type"}
    ]
  }

KEY INSIGHT:
  The field with ID=3 was originally "cost_usd", now renamed to "cost".
  Old Parquet files store this column as field ID 3 (not by name).
  When you read old files with schema v3, the engine maps:
    "field ID 3 in the Parquet file" → "cost" (the current name)
  
  This works correctly because Parquet stores column data by field ID internally.
  The rename doesn't require rewriting any data files!
```

### 6.3 Supported Schema Evolution Operations

```
SAFE OPERATIONS (no rewriting required):

1. ADD COLUMN
   ────────────
   New column added to schema with a new unique field ID.
   Old files: return NULL for this column (or the column's default value).
   New files: contain the actual values.
   
   Example:
   ALTER TABLE events ADD COLUMN device_category STRING;
   
   Cost: update one metadata file. Zero data file reads or writes.

2. DROP COLUMN
   ─────────────
   Column marked as deleted in the schema (field hidden from readers).
   Data in old files is NOT physically deleted — it's just ignored at read time.
   Physical removal happens during compaction.
   
   Example:
   ALTER TABLE events DROP COLUMN legacy_field;
   
   Cost: update one metadata file. Zero data file reads or writes.

3. RENAME COLUMN
   ───────────────
   Column's name changes in the schema, but field ID stays the same.
   Old and new files both use the same field ID.
   Readers use the current schema to map field IDs to column names.
   
   Example:
   ALTER TABLE events RENAME COLUMN cost_usd TO cost;

4. WIDEN TYPE (numeric upcasting)
   ──────────────────────────────
   int → long, float → double, decimal(10,2) → decimal(12,2)
   Safe because old values still fit in the wider type.
   
   Example:
   ALTER TABLE events ALTER COLUMN impressions TYPE BIGINT;

5. REORDER COLUMNS
   ─────────────────
   Change the display order of columns.
   No physical reordering of data (Parquet uses field IDs, not positions).
   
   Example:
   ALTER TABLE events ALTER COLUMN device_type FIRST;

UNSAFE OPERATIONS (would require full rewrite — Iceberg prevents them):
  • Narrowing a type: BIGINT → INT (values could overflow)
  • Changing type completely: STRING → INT
  • Making a nullable column non-nullable (old NULL values would be invalid)
```

---

## 7. Partition Evolution — Changing Partitioning Without Rewrites

### 7.1 The Partition Evolution Problem

This is where Iceberg truly shines — and where Hive completely fails.

**The scenario**: You start with daily partitioning. Your table grows, and you decide hourly partitioning would give better query performance. In Hive, you'd need to rewrite every historical file into a new directory structure. For a 5TB table, that's days of work.

In Iceberg, partition evolution is **instant and backward-compatible**.

### 7.2 How Iceberg Handles Partition Specs

Iceberg separates "how data is partitioned" from "what data exists." The partition specification (partition spec) is versioned separately from the data. New data is written with the NEW partition spec; old data retains the OLD partition spec. Both coexist in the same table.

```
PARTITION EVOLUTION EXAMPLE:

Phase 1: Daily partitioning (Jan 2023 - Dec 2023)
─────────────────────────────────────────────────
Partition spec ID 0: IDENTITY(date_col)
  → Creates partitions: date=2023-01-01, date=2023-01-02, etc.
  
  Files:
  s3://bucket/events/date=2023-01-01/part-001.parquet (1GB)
  s3://bucket/events/date=2023-01-02/part-001.parquet (1GB)
  ... (365 files total)

Phase 2: Change to hourly partitioning (Jan 2024 onward)
──────────────────────────────────────────────────────────
ALTER TABLE events ADD PARTITION FIELD hours(event_timestamp);
-- (this adds hourly transform to the partition spec)

New partition spec ID 1: hours(event_timestamp)
  → Creates partitions like: event_timestamp_hour=2024-01-01-00,
                               event_timestamp_hour=2024-01-01-01, etc.
  
  New files:
  s3://bucket/events/event_timestamp_hour=2024-01-01-00/part-001.parquet
  s3://bucket/events/event_timestamp_hour=2024-01-01-01/part-001.parquet
  ...

The table now contains BOTH partitioning schemes simultaneously:
  Old data: daily partitioned (spec 0) — never touched
  New data: hourly partitioned (spec 1) — written going forward
  
  The manifest files record WHICH partition spec each data file uses.
  Query engines understand both specs and can query the whole table
  seamlessly — you don't need to know about the transition.

Query: SELECT * FROM events WHERE DATE(event_timestamp) = '2024-01-15'
  For old data: uses daily partitioning → reads date=2024-01-15 partition
  For new data: uses hourly partitioning → reads all 24 hourly partitions
  Returns unified result with no gaps or duplicates.
```

### 7.3 Partition Transform Functions

Iceberg supports rich partition transforms — you don't have to partition by the raw column value:

```
PARTITION TRANSFORM FUNCTIONS:

identity(column)        → Use column value directly as partition value
                          Example: IDENTITY(country) → partition=US, partition=IN

year(ts_column)         → Extract year from timestamp
                          Example: click_date=2024-01-15 → partition year=2024

month(ts_column)        → Extract year-month
                          Example: click_date=2024-01-15 → partition month=2024-01

day(ts_column)          → Extract date
                          Example: click_date=2024-01-15 → partition day=2024-01-15

hour(ts_column)         → Extract year-month-day-hour
                          Example: clicked_at=2024-01-15 14:23 → hour=2024-01-15-14

bucket(N, column)       → Hash the column value into N buckets
                          Example: bucket(16, user_id) → buckets 0-15
                          USEFUL FOR: high-cardinality columns (user_id, order_id)
                          Without bucketing: identity(user_id) = millions of tiny partitions

truncate(W, column)     → Truncate string/int to width W
                          Example: truncate(3, category) → "ELE" for "ELECTRONICS"
                          Useful for prefix-based partitioning

WHY TRANSFORMS MATTER:

  BAD: IDENTITY partition on user_id
    → 50 million users → 50 million partitions
    → Catastrophic for partition listing and metadata management
    → Thousands of tiny files per "partition"
  
  GOOD: bucket(256, user_id)  
    → 256 partitions regardless of user count
    → Even distribution
    → Fast: queries for a specific user → check only 1/256 of data
    → Manageable: 256 partitions total
```

---

## 8. ACID Transactions on the Data Lake

### 8.1 What ACID Means for a Data Lake

ACID (Atomicity, Consistency, Isolation, Durability) are properties that traditional relational databases guarantee. Before table formats like Iceberg, data lakes had NONE of these. Iceberg brings full ACID semantics to object storage.

**Atomicity** — "All or nothing"

```
ATOMICITY WITH ICEBERG:

Without atomicity (Hive):
  Job writes 10 new files to S3 over 30 minutes
  Network failure at the 25-minute mark
  → 7 files exist in S3, 3 were not written
  → Hive Metastore says the partition exists
  → Queries return PARTIAL DATA — no way to know it's incomplete
  → YOU HAVE NO IDEA THIS HAPPENED

With atomicity (Iceberg):
  Job writes 10 new files to S3 staging location
  Job then atomically commits the new snapshot (metadata update = 1 operation)
  Network failure at 25 minutes:
  → Files written so far are in staging, not in the current snapshot
  → Metadata was never updated
  → Current snapshot still points to old complete state
  → Queries return CORRECT OLD DATA — no partial state visible
  → The partial files are orphans, cleaned up by maintenance jobs
```

**Isolation** — "Concurrent readers and writers don't interfere"

```
ISOLATION WITH ICEBERG:

Scenario: Analytics query runs for 2 minutes; ETL job loads new data at minute 1

Without isolation (Hive):
  Analytics query starts: reads files A, B, C
  ETL job adds files D, E and removes file A
  Analytics query continues: file A is gone! 
  → FileNotFoundException or silently missing data
  → Queries see inconsistent intermediate state

With isolation (Iceberg):
  Analytics query starts at snapshot 100
  → All reads for this query use snapshot 100's file list
  ETL job creates snapshot 101 (adds D, E, marks A as deleted)
  Analytics query continues reading from snapshot 100
  → File A still exists in storage (needed for snapshot 100)
  → Query completes successfully with consistent snapshot 100 view
  → ETL job's changes are invisible to the running query
  
  After the analytics query completes:
  New queries use snapshot 101 and DON'T see file A
```

**Optimistic Concurrency Control**

```
HOW ICEBERG HANDLES CONCURRENT WRITERS:

Both Writer A and Writer B want to update the table simultaneously.

Step 1: Both read current metadata → both see snapshot 100

Step 2: Both compute their changes independently:
  Writer A: "I'll add 3 files and call it snapshot 101-A"
  Writer B: "I'll add 5 files and call it snapshot 101-B"

Step 3: Both try to commit to the catalog:
  Writer A: "Set current snapshot to 101-A if current is still 100"
  → CATALOG: Current is 100 → SUCCESS
  Current metadata is now: snapshot 101-A

  Writer B: "Set current snapshot to 101-B if current is still 100"
  → CATALOG: Current is 101-A, not 100 → CONFLICT!
  
Step 4: Conflict resolution:
  Writer B re-reads current state (now 101-A)
  Checks: do my changes conflict with 101-A's changes?
    If NO conflict (different rows/files): retry commit with 101-A as base → creates 102-B
    If CONFLICT: fail with error (user must retry the operation)
  
NET RESULT: Serializability — it's as if the writes happened one at a time.
            No data loss, no corruption.
```

---

## 9. Time Travel and Rollback

### 9.1 Querying Historical Snapshots

Every snapshot has a unique snapshot ID and a timestamp. You can read any historical snapshot.

```python
# Spark: read an Iceberg table at a specific snapshot
df = spark.read \
    .option("snapshot-id", 8712) \
    .format("iceberg") \
    .load("s3://bucket/events")

# Or at a specific timestamp
df = spark.read \
    .option("as-of-timestamp", 1705276800000)  # Unix timestamp in ms
    .format("iceberg") \
    .load("s3://bucket/events")

# SQL with Spark
spark.sql("""
    SELECT * FROM catalog.db.events 
    TIMESTAMP AS OF '2024-01-14 09:00:00'
""")

spark.sql("""
    SELECT * FROM catalog.db.events 
    VERSION AS OF 8712
""")

# Trino / Athena syntax
SELECT * FROM events FOR SYSTEM_TIME AS OF TIMESTAMP '2024-01-14 09:00:00'
SELECT * FROM events FOR SYSTEM_VERSION AS OF 8712
```

### 9.2 Rollback — Undoing Changes

```python
from pyiceberg.catalog import load_catalog

catalog = load_catalog("glue", **conf)
table = catalog.load_table("my_db.events")

# Rollback to a specific snapshot
table.manage_snapshots().rollback_to_snapshot(snapshot_id=8710).commit()
# Now the current snapshot is 8710, as if 8711 and 8712 never happened
# Snapshots 8711 and 8712 still exist in history (not deleted)

# Rollback to a timestamp
table.manage_snapshots().rollback_to_timestamp(1705190400000).commit()
```

```sql
-- SQL approach (Spark):
CALL system.rollback_to_snapshot('catalog.db.events', 8710);
CALL system.rollback_to_timestamp('catalog.db.events', '2024-01-14T00:00:00.000+00:00');
```

### 9.3 Incremental Reads — What Changed Between Snapshots

This is extremely useful for CDC-style pipelines:

```python
# Read only rows that were ADDED between two snapshots
df_new_rows = spark.read \
    .format("iceberg") \
    .option("start-snapshot-id", 8710) \
    .option("end-snapshot-id", 8712) \
    .load("catalog.db.events")

# Only includes rows that are in snapshot 8712 but not in 8710
# Perfect for: "what new data arrived since last run?"
```

---

## 10. Row-Level Operations — Deletes, Updates, Merges

### 10.1 Equality Deletes vs Positional Deletes

Iceberg Merge-On-Read mode uses two types of delete files:

**Equality Delete Files**: Record that "delete all rows where column X = value Y"

```
Equality delete file content (Avro format):
{
  "equality_ids": [1],  // field ID 1 = user_id
  "deletes": [
    {"user_id": "GDPR_USER_12345"},
    {"user_id": "GDPR_USER_67890"}
  ]
}

When reading data files, engine applies:
  → Filter out any row where user_id is in the equality delete set
  → Works across ALL data files in the table (global delete)
  
Use case: GDPR erasure, deleting rows matching a business condition
```

**Positional Delete Files**: Record that "delete the row at position N in file F"

```
Positional delete file content (Parquet format):
{
  "file_path": "s3://bucket/data/part-00042.parquet",
  "pos": 12345
},
{
  "file_path": "s3://bucket/data/part-00042.parquet",
  "pos": 12346
}

When reading data files, engine applies:
  → For part-00042.parquet: skip rows at positions 12345 and 12346
  → Scoped to specific data files (faster than equality deletes)
  
Use case: SQL UPDATE (old version recorded as delete, new version inserted)
```

### 10.2 MERGE INTO — The Upsert Pattern

MERGE (also called UPSERT) is the most important DML operation for data engineering. It inserts new rows and updates existing ones atomically:

```sql
-- MERGE in Iceberg (using Spark SQL or Trino)

MERGE INTO catalog.db.dim_campaigns AS target
USING (
    SELECT
        campaign_id,
        campaign_name,
        daily_budget_usd,
        status,
        CURRENT_TIMESTAMP() AS updated_at
    FROM staging.incoming_campaigns
) AS source
ON target.campaign_id = source.campaign_id

WHEN MATCHED AND source.status = 'deleted'
    THEN DELETE

WHEN MATCHED AND (
    target.campaign_name != source.campaign_name OR
    target.daily_budget_usd != source.daily_budget_usd
) THEN UPDATE SET
    target.campaign_name = source.campaign_name,
    target.daily_budget_usd = source.daily_budget_usd,
    target.updated_at = source.updated_at

WHEN NOT MATCHED
    THEN INSERT (campaign_id, campaign_name, daily_budget_usd, status, updated_at)
    VALUES (source.campaign_id, source.campaign_name, source.daily_budget_usd,
            source.status, source.updated_at);
```

---

## 11. Maintenance Operations — Compaction, Expiration

### 11.1 Why Maintenance is Critical

Iceberg's MOR mode accumulates delete files and small data files over time. Without maintenance, query performance degrades:

```
PERFORMANCE DEGRADATION WITHOUT MAINTENANCE:

Day 1:  10 data files, 0 delete files  → fast reads
Day 10: 10 data files, 50 delete files → readers merge 5 delete files per data file
Day 30: 10 data files, 200 delete files → readers merge 20 delete files per data file
                                         → reads 10x slower

Also: Streaming ingestion creates many small files:
Day 1:  1 file per 5-minute micro-batch = 288 small files
Week 1: 288 × 7 = 2,016 small files for one week's data
Month 1: 8,640 small files → massive overhead for file listing
         → each file requires a separate S3 API call to read
```

### 11.2 Compaction (Rewrite Data Files)

Compaction merges small files into larger files and physically applies pending deletes:

```python
from pyiceberg.expressions import AlwaysTrue

# Compact all files in the table
table.rewrite_data_files(AlwaysTrue())

# Compact with configuration
table.rewrite_data_files(
    strategy="binpack",      # bin-packing algorithm
    options={
        "target-file-size-bytes": 134217728,  # 128MB target file size
        "min-file-size-bytes":    33554432,   # files below 32MB are candidates
        "max-file-size-bytes":    536870912,  # files above 512MB are candidates
    }
)

# SQL equivalent (Spark):
CALL system.rewrite_data_files(
    table => 'catalog.db.events',
    strategy => 'binpack',
    options => map(
        'target-file-size-bytes', '134217728',
        'rewrite-all', 'false'       -- only rewrite files that need it
    )
);
```

### 11.3 Snapshot Expiration

Old snapshots accumulate over time. Expiring them frees up storage by allowing the deletion of orphaned data files:

```python
# Expire snapshots older than 7 days
table.expire_snapshots() \
     .expire_older_than(datetime.now() - timedelta(days=7)) \
     .retain_last(5) \   # always keep at least 5 snapshots
     .commit()

# SQL equivalent:
CALL system.expire_snapshots(
    table => 'catalog.db.events',
    older_than => TIMESTAMP '2024-01-08 00:00:00',
    retain_last => 5
);
```

### 11.4 Removing Orphan Files

Sometimes files exist in storage that aren't referenced by any snapshot (e.g., from a failed write or from bugs). Orphan file removal cleans these up:

```python
table.remove_orphan_files() \
     .older_than(datetime.now() - timedelta(days=3)) \
     .execute()

# SQL:
CALL system.remove_orphan_files(
    table => 'catalog.db.events',
    older_than => TIMESTAMP '2024-01-12 00:00:00'
);
```

### 11.5 Recommended Maintenance Schedule

```
PRODUCTION MAINTENANCE SCHEDULE:

Hourly (for streaming tables):
  → Compact small files generated by streaming writes
  → CALL rewrite_data_files with min-file-size-bytes = 32MB
  → Goal: merge many 5-50MB files into 128-256MB files

Daily (all tables):
  → Expire snapshots older than 7 days (adjust for your Time Travel needs)
  → Remove orphan files older than 3 days
  → Rewrite manifests if heavily fragmented

Weekly (large tables):
  → Full compaction: rewrite ALL files to optimal sizes with deletes applied
  → Especially important for tables with heavy DML (many deletes/updates)
  → CALL rewrite_data_files with rewrite-all=true
```

---

## 12. Iceberg with Different Query Engines

### 12.1 The Multi-Engine Advantage

One of Iceberg's biggest selling points is **engine independence**. The same table can be read and written by different compute engines without any conversion or copying:

```
SINGLE ICEBERG TABLE (in S3):
          │
          ├──► Apache Spark (batch ETL, large transformations)
          ├──► Trino/Presto (fast interactive SQL queries)
          ├──► Apache Flink (real-time streaming)
          ├──► AWS Athena (serverless SQL on S3)
          ├──► BigQuery (via BigLake external tables)
          ├──► Snowflake (Iceberg tables feature)
          ├──► DuckDB (local analytics)
          └──► Dremio, Starburst, etc.

The table format is the CONTRACT between all these engines.
Each engine reads the same metadata, understands the same file format,
and writes following the same specification.

You can write with Spark in the morning and query with Trino in the afternoon.
No conversion. No copying. No sync needed.
```

### 12.2 Iceberg with Apache Spark

```python
# Configure Spark to use Iceberg with AWS Glue catalog
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("Iceberg Demo") \
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .config("spark.sql.catalog.glue_catalog", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.glue_catalog.warehouse", "s3://my-bucket/warehouse/") \
    .config("spark.sql.catalog.glue_catalog.catalog-impl", "org.apache.iceberg.aws.glue.GlueCatalog") \
    .config("spark.sql.catalog.glue_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
    .getOrCreate()

# Create an Iceberg table
spark.sql("""
    CREATE TABLE glue_catalog.my_db.ad_clicks (
        click_id        STRING,
        campaign_id     STRING,
        user_id         STRING,
        clicked_at      TIMESTAMP,
        cost_usd        DOUBLE,
        click_date      DATE
    )
    USING iceberg
    PARTITIONED BY (day(clicked_at))
    LOCATION 's3://my-bucket/warehouse/my_db/ad_clicks'
    TBLPROPERTIES (
        'write.format.default'              = 'parquet',
        'write.parquet.compression-codec'   = 'zstd',
        'write.target-file-size-bytes'      = '134217728',
        'write.delete.mode'                 = 'merge-on-read',
        'read.split.target-size'            = '134217728',
        'history.expire.max-snapshot-age-ms'= '604800000'  -- 7 days
    )
""")

# Insert data
spark.sql("""
    INSERT INTO glue_catalog.my_db.ad_clicks
    SELECT
        click_id,
        campaign_id,
        user_id,
        clicked_at,
        cost_micros / 1000000.0 AS cost_usd,
        CAST(clicked_at AS DATE) AS click_date
    FROM glue_catalog.raw.google_ads_clicks
    WHERE CAST(clicked_at AS DATE) = '2024-01-15'
""")

# Merge (upsert) — common pattern for CDC
spark.sql("""
    MERGE INTO glue_catalog.my_db.ad_clicks AS target
    USING staging_updates AS source
    ON target.click_id = source.click_id
    WHEN MATCHED THEN UPDATE SET target.cost_usd = source.cost_usd
    WHEN NOT MATCHED THEN INSERT *
""")

# Check table history
spark.sql("SELECT * FROM glue_catalog.my_db.ad_clicks.history").show()

# Check table snapshots
spark.sql("SELECT * FROM glue_catalog.my_db.ad_clicks.snapshots").show()

# Check files in current snapshot
spark.sql("SELECT * FROM glue_catalog.my_db.ad_clicks.files").show()
```

### 12.3 PyIceberg — Python-Native Access

```python
from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.types import NestedField, StringType, DoubleType, TimestampType
from pyiceberg.partitioning import PartitionSpec, PartitionField
from pyiceberg.transforms import DayTransform
from pyiceberg.expressions import GreaterThanOrEqual, LessThan, And

# Load catalog
catalog = load_catalog(
    "glue",
    **{
        "type": "glue",
        "s3.region": "us-east-1",
    }
)

# Load table
table = catalog.load_table("my_db.ad_clicks")

# Scan with filters (predicate pushdown)
df = table.scan(
    row_filter=And(
        GreaterThanOrEqual("click_date", "2024-01-15"),
        LessThan("click_date", "2024-01-16")
    ),
    selected_fields=("click_id", "campaign_id", "cost_usd"),  # column projection
    limit=1000
).to_arrow()  # returns PyArrow Table

import pandas as pd
pandas_df = df.to_pandas()

# Using scan with PyArrow filtering
batches = table.scan(
    row_filter=GreaterThanOrEqual("cost_usd", 100.0)
).to_arrow_batch_reader()  # memory-efficient batch reading

for batch in batches:
    process_batch(batch)

# Table metadata inspection
print(f"Current snapshot: {table.current_snapshot()}")
print(f"Schema: {table.schema()}")
print(f"Partition spec: {table.spec()}")
print(f"Properties: {table.properties}")

# List snapshots
for snapshot in table.metadata.snapshots:
    print(f"Snapshot {snapshot.snapshot_id}: {snapshot.timestamp_ms}")
```

---

## 13. Iceberg in GCP — BigLake and BigQuery Integration

### 13.1 BigLake — Google's Managed Iceberg Tables

Google Cloud's **BigLake** allows you to manage Iceberg tables stored in GCS and query them directly from BigQuery. This is a key integration for GCP-based data platforms.

```
BIGLAKE ARCHITECTURE:

GCS (Google Cloud Storage)
├── s3://costco-lake/events/metadata/    (Iceberg metadata files)
├── s3://costco-lake/events/data/        (Parquet data files)
└── ...

BigLake Metastore (optional managed catalog)
  OR
Google Cloud Storage (direct file-based catalog)

BigQuery
  └── External connection to GCS
  └── CREATE EXTERNAL TABLE pointing to Iceberg metadata
  └── Query with BigQuery SQL!

Other engines:
  ├── Spark on Dataproc
  ├── Apache Flink on Dataproc
  └── Trino/Presto
  All can read the same GCS Iceberg files
```

```sql
-- Create BigQuery Iceberg external table
CREATE EXTERNAL TABLE `project.dataset.ad_clicks`
WITH CONNECTION `us.my-gcs-connection`
OPTIONS (
    format = 'ICEBERG',
    uris = ['gs://costco-lake/events/metadata/']
);

-- Query it like any BigQuery table
SELECT
    campaign_id,
    COUNT(*) AS clicks,
    SUM(cost_usd) AS total_spend
FROM `project.dataset.ad_clicks`
WHERE click_date BETWEEN '2024-01-01' AND '2024-01-31'
GROUP BY campaign_id
ORDER BY total_spend DESC;

-- The query benefits from Iceberg metadata:
-- Partition pruning: only reads Jan data
-- Column statistics: can skip files that can't satisfy filters
-- Results are exactly as if the data were in a native BigQuery table
```

### 13.2 The BigLake + Iceberg Pattern for GCP Data Lakes

```
RECOMMENDED GCP DATA LAKE ARCHITECTURE WITH ICEBERG:

Raw Layer (GCS):
  gs://costco-raw/
  ├── google_ads/    (JSON, CSV from API ingestion)
  ├── member_events/ (Parquet from streaming)
  └── transactions/  (CDC from CloudSQL/Spanner via Datastream)
  
  Format: Raw files, NO Iceberg (just files, not tables)

Staging/Processed Layer (GCS + Iceberg):
  gs://costco-processed/
  ├── ad_clicks/           (Iceberg table, Parquet files)
  ├── member_profiles/     (Iceberg table, Parquet files)
  └── transactions/        (Iceberg table, Parquet files)
  
  Format: Iceberg tables managed via BigLake
  Written by: Spark on Dataproc (batch) + Flink on Dataproc (streaming)
  Queried by: BigQuery (SQL analytics)

Mart Layer (BigQuery native):
  BigQuery datasets: marts.campaign_performance, marts.member_ltv
  
  These are native BigQuery tables (not Iceberg).
  Populated by: DBT running SQL CTAS/INSERT from processed Iceberg tables.
  Queried by: Looker, Tableau, analysts.

Why Iceberg for the middle layer (not BigQuery native)?
  1. Engine flexibility: Spark can write, BigQuery can query — same data
  2. Schema evolution: add columns to Iceberg without data migration
  3. Partition evolution: change partitioning from daily to hourly as data grows
  4. Time Travel: 30-day history without paying BigQuery storage rates for old data
  5. Cost: GCS storage is cheaper than BigQuery storage for raw/staging data
```

---

## 14. Iceberg vs Delta Lake vs Hudi — Table Format Comparison

### 14.1 The Open Table Format Landscape

Three major open table formats compete in the modern data lake ecosystem:

```
ORIGIN AND BACKING:
  Apache Iceberg  ← Netflix, open Apache project, widely adopted
  Delta Lake      ← Databricks, open-source, strong Spark/Databricks integration
  Apache Hudi     ← Uber, open Apache project, streaming-focused
```

### 14.2 Feature-by-Feature Comparison

```
FEATURE                 ICEBERG         DELTA LAKE       HUDI
──────────────────────────────────────────────────────────────────

Metadata layer         Multi-level      Single delta     Multi-level
                       (manifest list   log (_delta_log  (commit log
                       → manifests      directory)        directory)
                       → data files)

Engine support         Spark, Trino,    Spark (best),    Spark (best),
                       Flink, Hive,     some Hive/       some Trino/
                       Athena, BigQuery, Trino support    Presto support
                       Snowflake        (improving)      (improving)

Multi-engine writes    ✓ Any engine     ✗ Databricks     Limited
                       can write        preferred

Schema evolution       ✓ Excellent      ✓ Good           ✓ Good
                       (field IDs,      (column rename    
                       all safe ops)    more limited)

Partition evolution    ✓ No rewrites    ✗ Requires       ✗ Limited
                       needed           rewrite

Time travel            ✓ Snapshot-      ✓ Delta log      ✓ Timeline-
                       based, very      allows queries   based
                       flexible         at version/time

ACID transactions      ✓ Optimistic     ✓ Optimistic     ✓ OCC for
                       concurrency      concurrency       upserts

Row-level deletes      ✓ MOR or COW     ✓ MOR or COW     ✓ MOR
                       (configurable)   (configurable)    (built for this)

Streaming ingest       ✓ Via Flink or   ✓ Via Spark      ✓ Native (built
                       micro-batch      Streaming         for streaming)
                       Spark            

Upsert performance     Good             Good             Excellent
                       (COW or MOR)     (COW or MOR)     (index-based
                                                          optimizations)

Query optimization     ✓ Rich metadata  ✓ Stats          ✓ Stats
(file pruning)         (min/max,        (but less        available
                       null counts)     granular)

Compaction             Manual or        Auto (OPTIMIZE)  Auto or manual
                       automated        in Databricks    (cleaner)

Catalog flexibility    ✓ Many catalogs  ✗ Databricks     Limited
                       (Hive, Glue,     Unity Catalog
                       Nessie, REST)    preferred

Cloud neutrality       ✓ True multi-    Limited (best    ✓ Reasonably
                       cloud            on Databricks    cloud-neutral
                                        → Azure, AWS)

Industry adoption      Netflix, Apple,  Primarily        Uber, streaming-
                       AWS (default),   Databricks       heavy use cases
                       GCP (BigLake)    customers

GCP integration        ✓ BigLake,       Limited          Limited
                       BigQuery native
```

### 14.3 When to Choose Each

```
CHOOSE ICEBERG WHEN:
  ✓ You need true multi-engine writes (Spark + Trino + Flink + BigQuery)
  ✓ Partition evolution matters (changing from daily to hourly)
  ✓ You're on GCP (BigLake native integration)
  ✓ You're on AWS using Glue, Athena, or EMR (all support Iceberg well)
  ✓ You want catalog flexibility (not locked into one vendor)
  ✓ You're building a vendor-neutral architecture
  ✓ Long-term open standard commitment is important

CHOOSE DELTA LAKE WHEN:
  ✓ You're heavily invested in Databricks
  ✓ Most of your workload is Spark on Databricks
  ✓ Databricks Auto Optimize/Auto Compaction simplifies operations
  ✓ The Databricks ecosystem (MLflow, Unity Catalog) is your platform
  ✓ Azure is your primary cloud (Databricks is Azure-native)

CHOOSE HUDI WHEN:
  ✓ You have very high-velocity streaming writes with frequent upserts
  ✓ Your primary write pattern is streaming → you need optimized index
  ✓ You're doing CDC pipelines with millions of updates/second
  ✓ Kafka → Data Lake real-time pipelines are your core use case
  ✓ Low-latency near-real-time query latency is critical
```

---

## 15. Real-World Patterns and Use Cases

### 15.1 Pattern 1: CDC Pipeline with Iceberg MOR

```
USE CASE: Replicate a transactional MySQL database to a data lake
          with near-real-time latency and full history preservation

ARCHITECTURE:
  MySQL (source) 
    → Debezium (reads MySQL binlog)
      → Kafka topic (raw CDC events)
        → Flink job (processes CDC events)
          → Iceberg table in S3 (MOR mode)
            → Queried by Trino/BigQuery

FLINK JOB LOGIC:
  For each CDC event from Kafka:
    - INSERT event: append row to Iceberg table
    - UPDATE event: write equality delete for old key + append new row
    - DELETE event: write equality delete for the key
  
  Iceberg MOR mode makes this very fast:
    No data files are rewritten
    Delete files are small and written quickly
    Reads merge deletes at query time

COMPACTION SCHEDULE:
  Hourly: compact small files from streaming writes
  Daily: rewrite all MOR files to clean COW state (faster reads)
  Weekly: expire old snapshots, remove orphans
```

### 15.2 Pattern 2: GDPR Data Deletion at Scale

```
USE CASE: Process 10,000 GDPR deletion requests per day
          against a 50TB event table

CHALLENGE:
  50TB table, 100 billion rows, partitioned by date
  Each deletion request: "delete all rows where user_id = X"
  10,000 requests × average 500 rows each = 5 million rows to delete per day
  5M out of 100B = 0.005% of data
  
  Rewriting entire files for 0.005% of rows = 50TB of I/O per day → unacceptable!

ICEBERG SOLUTION:
  Use MOR (Merge-On-Read) delete files:
  
  Step 1: Collect deletion requests into batches (hourly)
  Step 2: Write ONE equality delete file per batch:
    {"equality_ids": [user_id_field_id],
     "deletes": [{"user_id": "U1"}, {"user_id": "U2"}, ...(5000 users)...]}
  
  Cost: Write a few KB delete file (not 50TB!)
  Query behavior: reads merge delete file → deleted rows invisible
  Compliance: row is "logically deleted" immediately ← satisfies GDPR
  
  Step 3: Weekly physical deletion (compaction)
    Run REWRITE DATA FILES with delete files applied
    Produces new clean files with deleted rows actually removed
    Cost: Only need to rewrite files that actually contain deleted user_ids
          (use partition pruning + statistics to minimize I/O)

OUTCOME:
  Near-instant logical deletion (seconds per batch)
  Physical deletion within 7 days (per GDPR requirement)
  50TB table: deletion backlog processed without massive I/O overhead
```

### 15.3 Pattern 3: The Lakehouse Architecture

```
LAKEHOUSE = Data Lake storage + Data Warehouse query performance
             = Iceberg (or Delta) tables in object storage + SQL query engine

TRADITIONAL DATA WAREHOUSE:
  Data Lake (S3) → ETL → Data Warehouse (Snowflake/BigQuery)
  Problems:
  • Double storage cost (pay for S3 AND DWH)
  • ETL lag (data warehouse is hours behind)
  • Schema lock-in (DWH schema must be defined upfront)
  • Data movement = complexity + cost

LAKEHOUSE (Iceberg-based):
  Data Lake (S3 with Iceberg tables) ← Compute Layer (Spark/Trino/BigQuery)
  
  No separate DWH!
  • Store data once in S3 (cheap)
  • Query with SQL (fast, Trino/BigQuery/Spark)
  • ACID transactions via Iceberg
  • Schema evolution via Iceberg
  • Time Travel via Iceberg
  
  Same S3 data:
  ← Batch ETL (Spark)
  ← Real-time ingest (Flink)
  ← SQL analytics (Trino, BigQuery)
  ← ML training (Spark ML, PyTorch)
  ← BI dashboards (Looker → Trino → Iceberg)

Best of both worlds:
  Lake = cheap storage, flexibility, all data types
  House = SQL, ACID, schema, performance
```

---

## 16. Interview Questions — Easy to Very Hard

### EASY

**Q1: What is Apache Iceberg and why was it created?**

**Answer**: Apache Iceberg is an open table format for large-scale analytical datasets. It's not a storage system — it's a metadata layer that sits on top of Parquet/ORC files in object storage (S3/GCS) and gives them database-like capabilities. It was created by Netflix engineers around 2017 to solve problems they encountered with Hive tables at petabyte scale: partition listing was catastrophically slow with millions of partitions, concurrent writers could corrupt data, schema changes required full rewrites, and there was no way to do row-level deletes without rewriting entire files. Iceberg solves all of these with a carefully designed multi-level metadata architecture and snapshot-based versioning.

---

**Q2: What are the layers of Iceberg's architecture?**

**Answer**: Iceberg has four layers. First, the catalog maps table names to metadata file locations — examples include Hive Metastore, AWS Glue, and REST Catalog. Second, metadata files (JSON) contain the table schema, partition specification, and references to all snapshots. Third, manifest files (Avro) serve as the index — each manifest contains entries for many data files, and each entry includes rich statistics (row count, min/max values per column, null counts) that enable file-level pruning. Fourth, the actual data files are Parquet/ORC files in object storage containing the rows.

This hierarchy means reading a table requires only: one catalog lookup, one metadata file read, a few manifest reads, and then reading only the relevant data files. Query engines never need to list all files in a directory — they walk the metadata tree.

---

### MEDIUM

**Q3: Explain Copy-On-Write vs Merge-On-Read in Iceberg. When would you use each?**

**Answer**: These are two strategies for how Iceberg handles row-level changes like DELETE and UPDATE.

**Copy-On-Write (COW)**: When you delete or update rows, Iceberg reads the affected data files, applies the change, and writes entirely new data files. The new snapshot points to the new files. Reads are always against clean files with no merge step. Writes are expensive (must rewrite entire affected files) but reads are fast.

**Merge-On-Read (MOR)**: When you delete or update, Iceberg writes a small delete file that records which rows are removed, without touching the original data files. Writes are very fast (just a tiny delete file), but reads must merge the data files with the delete files at query time, which adds overhead. Over time, accumulated delete files significantly slow down reads until compaction is run.

Use COW for: batch ETL pipelines where writes happen infrequently (daily), read-heavy workloads, and GDPR deletion jobs where you want clean files afterward.

Use MOR for: streaming or near-real-time ingestion where write latency matters, CDC pipelines with frequent small updates, and workloads where you can schedule regular compaction to restore read performance.

---

**Q4: A Hive table with 500 million partitions is taking 2 hours to list all files. You want to migrate to Iceberg. How does Iceberg solve this problem?**

**Answer**: Hive's file listing problem occurs because listing partitions requires either querying the Hive Metastore (potentially 500 million database rows) or doing S3 LIST operations over directories (extremely slow at that scale — millions of API calls).

Iceberg completely avoids file listing. Instead of storing "which partitions exist" in a central database, Iceberg uses a chain of metadata files: the catalog points to one metadata file, the metadata file points to the current snapshot's manifest list (one file), and the manifest list points to manifest files (each covering many data files). Reading a table requires only: 1 catalog lookup + 1 metadata file read + 1 manifest list read + reading a few relevant manifests.

The total is 3-5 file reads regardless of whether the table has 100 files or 100 billion files. The migration would involve: creating a new Iceberg table with the same schema, bulk loading the existing data (Spark's `CTAS ... USING iceberg`), and pointing the catalog to the new table. After migration, partition listing operations that took 2 hours would take under 1 second.

---

### HARD

**Q5: Explain how Iceberg implements ACID transactions on S3. S3 doesn't have native locking — how does Iceberg prevent two writers from corrupting the same table?**

**Answer**: S3 doesn't have file locking or transactions, but Iceberg achieves ACID guarantees through a combination of immutable files and optimistic concurrency control (OCC) at the catalog layer.

The key insight is that Iceberg never modifies existing files. All changes (new data files, delete files, updated metadata) are written as NEW files with new names. The existing files are untouched. This means writes to S3 can never corrupt existing data — the only thing that makes a change "live" is updating the catalog pointer.

The catalog update is the critical atomic operation. When a writer wants to commit a new snapshot (say, snapshot 102 based on snapshot 101), it asks the catalog: "atomically set current snapshot to 102 IF the current snapshot is still 101." If another writer already committed snapshot 102, this operation fails (the current snapshot is no longer 101). The catalog implementations achieve this atomicity differently: Hive Metastore uses database transactions, AWS Glue uses conditional updates, and REST Catalog uses HTTP conditional requests.

The failing writer then re-reads the current state (102 from the competing writer), checks whether its changes conflict, and retries if they don't. This gives serializable isolation: the final result is as if the writes happened one at a time, even if they were attempted concurrently. No data is lost and no corruption occurs.

---

### VERY HARD

**Q6: You have a 50TB event table partitioned by date. Due to business requirements changing, you need to: (1) change the partitioning from daily to hourly for new data, (2) add a new column to capture device category, (3) implement GDPR deletion for 5,000 users per day, all without taking the table offline. Walk through exactly how you would do each with Iceberg and why it's possible without Hive.**

**Answer**:

**Part 1: Partition Evolution (daily → hourly for new data)**

With Iceberg, I add a new partition field without touching existing data:

```sql
ALTER TABLE events ADD PARTITION FIELD hours(event_timestamp);
```

This creates a new partition spec. Going forward, new data is written with hourly partitions (event_timestamp_hour=2024-01-15-00, etc.). All historical data remains with daily partitions — Iceberg tracks which partition spec applies to each file via the manifest entries. Queries seamlessly use both partition schemes: for historical data, daily pruning applies; for new data, hourly pruning applies. Zero data files are rewritten. Zero downtime.

In Hive, this would be impossible without rewriting all 50TB of historical data into the new hourly directory structure, taking days.

**Part 2: Schema Evolution (add device_category column)**

```sql
ALTER TABLE events ADD COLUMN device_category STRING;
```

Iceberg updates one metadata file — takes milliseconds. The new column gets a unique field ID (say, ID=7). Old Parquet files don't have field 7 — when you read them, Iceberg returns NULL for device_category. New files written after this change include field ID 7 with actual values. All readers see a consistent schema.

No files are rewritten. The table is available for reads and writes continuously throughout this operation.

**Part 3: GDPR Deletion (5,000 users/day)**

Using Merge-On-Read delete files for efficiency:

```python
# Run once per day: collect that day's deletion requests
users_to_delete = load_gdpr_requests_for_today()  # 5,000 user_ids

# Write ONE equality delete file (not 5,000 separate operations)
table.delete(
    In("user_id", users_to_delete)
)
```

This writes a single small equality delete file (a few KB containing 5,000 user_id values). No data files are read or written. The operation takes seconds, not hours. The deleted rows are immediately invisible to all queries (logical deletion satisfies GDPR's "without undue delay" requirement).

For physical deletion, run weekly compaction:

```python
CALL system.rewrite_data_files(
    table => 'catalog.db.events',
    strategy => 'binpack',
    where => 'click_date >= current_date - 365'  -- only compact recent data if needed
)
```

This physically removes the deleted rows from the Parquet files and deletes the equality delete files, completing the physical erasure within 7 days.

All three operations run concurrently without any table lock or downtime. Writers can continue inserting data while all three changes take effect. The snapshot-based design ensures readers always see a consistent state — they're either reading pre-change snapshot N or post-change snapshot N+1, never an intermediate broken state.

---

## Summary: Iceberg Expert Reference Card

```
WHAT IS IT:
  Open table format for large-scale analytics
  NOT a storage system — manages Parquet/ORC files in object storage
  Brings database capabilities (ACID, schema, partitioning, history) to data lakes

ARCHITECTURE (4 layers):
  Catalog: name → metadata file location (Glue, Hive Metastore, REST, Nessie)
  Metadata file: schema versions, partition specs, snapshot history
  Manifest files: index of data files with per-file statistics
  Data files: actual Parquet/ORC data in S3/GCS

KEY CONCEPTS:
  Snapshot: complete immutable view of table at a point in time
  COW: rewrite affected files on change (slow write, fast read)
  MOR: write delete files without touching data files (fast write, slower read)
  Compaction: merge small files + apply pending deletes → restores read performance

SCHEMA EVOLUTION:
  Add column: instant (new field ID, old files return NULL)
  Drop column: instant (hidden from readers, data still in files)
  Rename column: instant (field ID unchanged, name updated in schema)
  All changes use field IDs, not positions → safe and reversible

PARTITION EVOLUTION:
  Old data keeps old partition spec
  New data uses new partition spec
  Both coexist in same table — no rewrites needed!

ACID:
  Immutable files + optimistic concurrency control at catalog
  Snapshot isolation: running queries see consistent snapshot
  Never see partially-written data

TIME TRAVEL:
  Any snapshot is queryable by snapshot-id or timestamp
  Rollback: set current snapshot to any historical snapshot
  Incremental reads: what changed between snapshot A and B?

VS HIVE:
  File listing: Iceberg = 3-5 metadata reads; Hive = millions of S3 LIST ops
  Concurrent writes: Iceberg = OCC (safe); Hive = corruption possible
  Schema changes: Iceberg = instant; Hive = often full rewrite
  Partition changes: Iceberg = instant (evolution); Hive = full rewrite

VS DELTA / HUDI:
  Iceberg: best multi-engine support, best partition evolution, best GCP support
  Delta: best Databricks integration, simpler operations
  Hudi: best streaming upsert performance, built-in indexing

MAINTENANCE:
  Compaction: merge small files, apply MOR deletes physically
  Snapshot expiry: delete old snapshots to free storage
  Orphan removal: clean up unreferenced files
  Schedule: compact hourly (streaming), expire daily, deep compact weekly
```
