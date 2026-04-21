# Snowflake — Complete Textbook: From Zero to Expert
## Data Engineering Interview Preparation — Exhaustive Reference

---

## Table of Contents

1. [What is Snowflake and Why It Exists](#1-what-is-snowflake-and-why-it-exists)
2. [Snowflake Architecture — The Three-Layer Model](#2-snowflake-architecture--the-three-layer-model)
3. [Storage Layer — How Snowflake Stores Data](#3-storage-layer--how-snowflake-stores-data)
4. [Compute Layer — Virtual Warehouses Deep Dive](#4-compute-layer--virtual-warehouses-deep-dive)
5. [Cloud Services Layer — The Brain](#5-cloud-services-layer--the-brain)
6. [Data Types, Tables, and Schemas](#6-data-types-tables-and-schemas)
7. [Loading Data into Snowflake](#7-loading-data-into-snowflake)
8. [Querying — SQL Dialect and Special Features](#8-querying--sql-dialect-and-special-features)
9. [Semi-Structured Data — Variant, JSON, Arrays](#9-semi-structured-data--variant-json-arrays)
10. [Performance Optimization — Clustering, Search Optimization](#10-performance-optimization--clustering-search-optimization)
11. [Time Travel and Fail-Safe](#11-time-travel-and-fail-safe)
12. [Cloning — Zero-Copy Clones](#12-cloning--zero-copy-clones)
13. [Streams and Tasks — CDC and Orchestration](#13-streams-and-tasks--cdc-and-orchestration)
14. [Data Sharing — Snowflake Marketplace](#14-data-sharing--snowflake-marketplace)
15. [Security — Roles, RBAC, Dynamic Data Masking](#15-security--roles-rbac-dynamic-data-masking)
16. [Cost Management and Optimization](#16-cost-management-and-optimization)
17. [Snowflake vs BigQuery — Deep Comparison](#17-snowflake-vs-bigquery--deep-comparison)
18. [Snowflake in Data Engineering Pipelines](#18-snowflake-in-data-engineering-pipelines)
19. [Interview Questions — Easy to Very Hard](#19-interview-questions--easy-to-very-hard)

---

## 1. What is Snowflake and Why It Exists

### 1.1 The Problem Before Snowflake

To understand Snowflake's value, you need to understand what the world looked like before it.

**The old world — on-premises data warehouses (Teradata, Oracle Exadata)**:

```
┌─────────────────────────────────────────┐
│         On-Premises Data Warehouse       │
│                                          │
│  Storage ←→ Compute  (tightly coupled)  │
│                                          │
│  • Fixed hardware capacity               │
│  • Scale = buy more servers              │
│  • Scaling takes months                  │
│  • Pay for capacity whether used or not  │
│  • Schema changes are painful            │
│  • Global teams can't access easily      │
└─────────────────────────────────────────┘
```

Problems with this model:
- **Capacity planning is a nightmare**: You buy hardware for peak load, but pay for it 24/7 even when 90% idle
- **Scaling takes months**: Need more capacity? Submit a procurement request, wait for hardware, rack it, configure it
- **Storage and compute are the same machine**: If you need more compute but not storage, you still buy both
- **No elasticity**: Can't handle sudden surges in query load without pre-provisioned headroom
- **Maintenance burden**: DBAs spend huge effort on patching, backup, tuning, hardware failures

**The early cloud era — "lift and shift" (EC2 + Redshift, 2012)**:

Amazon Redshift moved the DWH to the cloud, but the fundamental architecture remained: compute and storage are still on the same nodes. You provision a cluster, pay for it 24/7. Scaling requires adding nodes and redistributing data.

**Snowflake's insight (2012, launched 2014)**:

> *"What if storage and compute were completely separate, each scaling independently, and the database ran as a pure service with no infrastructure management by the user?"*

This was genuinely revolutionary at the time. Snowflake was designed from scratch for the cloud, not adapted from an on-premises system.

---

### 1.2 What Snowflake Is

Snowflake is a **cloud-native analytical data warehouse** delivered as a Software-as-a-Service (SaaS). Key properties:

**1. Multi-cloud**: Runs on AWS, Azure, and GCP. You choose your cloud provider and region when creating an account.

**2. SaaS model**: You never manage servers, patches, backups, or hardware. Snowflake handles all infrastructure. You only manage your data and queries.

**3. Separation of storage and compute**: Your data lives in cloud object storage (S3, Azure Blob, GCS). Your query engines (Virtual Warehouses) are separate compute clusters that read from storage. You can have many warehouses (dev, prod, analytics, ML) all reading the same data simultaneously.

**4. Per-second billing**: You only pay for the compute you actually use. A warehouse that runs for 10 minutes costs 1/6 of an hourly rate. Idle warehouses auto-suspend and stop costing money.

**5. Instantly elastic**: Scale a warehouse up (more powerful) or out (more parallel) in seconds, not months.

**6. SQL-native**: Query with standard ANSI SQL. No new language to learn.

---

### 1.3 Snowflake's Position in the Modern Data Stack

```
┌────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                             │
│  SaaS apps │ DBs │ Event streams │ Files │ APIs            │
└──────────────────────────┬─────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  ELT Tools  │
                    │  Fivetran   │
                    │  Airbyte    │
                    │  Kafka      │
                    └──────┬──────┘
                           │
            ┌──────────────▼───────────────┐
            │         SNOWFLAKE            │
            │                              │
            │  Raw → Staging → Marts       │
            │  (via DBT on top of SF)      │
            │                              │
            │  Storage: S3/Azure/GCS       │
            │  Compute: Virtual Warehouses │
            └──────────────┬───────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
       Tableau          Looker         Python/
       Power BI         Sigma          Notebook
       (BI Tools)    (Analytics)    (Data Science)
```

**Snowflake's key differentiators vs competitors**:

| Feature | Snowflake | BigQuery | Redshift |
|---------|-----------|----------|---------|
| **Infrastructure management** | Zero (full SaaS) | Zero (serverless) | Some (cluster sizing) |
| **Compute model** | Virtual Warehouses (you size) | Serverless (auto) | Clusters (you size) |
| **Multi-cloud** | AWS + Azure + GCP | GCP only | AWS only |
| **Concurrency** | Multi-cluster for high concurrency | Auto | Limited without additional nodes |
| **Semi-structured** | VARIANT type, Snowpark | JSON natively | Limited |
| **Data sharing** | Native, live, cross-account | BigQuery Analytics Hub | Manual exports |
| **Time Travel** | 1-90 days (standard/enterprise) | 7 days | None native |
| **Cloning** | Zero-copy instant | Not supported | Not supported |
| **Pricing** | Per-second compute + storage | Per TB scanned | Per node-hour |

---

## 2. Snowflake Architecture — The Three-Layer Model

### 2.1 The Big Picture

Snowflake's architecture has three distinct, independently scalable layers. Understanding this separation is the most important concept in Snowflake.

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                   CLOUD SERVICES LAYER                       ║
║                                                              ║
║    Authentication │ Access Control │ Query Optimizer         ║
║    Metadata       │ Infrastructure Manager │ Transactions    ║
║                                                              ║
║    (Always running, shared across all customers)             ║
║    (No charge for compute — included in overhead)            ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║               QUERY PROCESSING LAYER                         ║
║            (Virtual Warehouses / Compute)                    ║
║                                                              ║
║   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ║
║   │  Warehouse A │   │  Warehouse B │   │  Warehouse C │   ║
║   │   (X-Large)  │   │   (Small)    │   │   (Medium)   │   ║
║   │  Analytics   │   │  Dev/Test    │   │  Data Load   │   ║
║   └──────────────┘   └──────────────┘   └──────────────┘   ║
║                                                              ║
║    • Each warehouse = cluster of EC2/VM nodes               ║
║    • Warehouses share NO resources with each other          ║
║    • Billed per second when running                         ║
║    • Auto-suspend when idle                                 ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║                  DATABASE STORAGE LAYER                      ║
║                                                              ║
║         Columnar compressed files in S3 / Azure / GCS        ║
║                                                              ║
║    [Table A files] [Table B files] [Table C files]           ║
║    (Micro-partitions: 50-500MB compressed Parquet-like)      ║
║                                                              ║
║    • Persistent, independent of any warehouse               ║
║    • Priced at $23/TB/month (compressed)                    ║
║    • Managed by Snowflake — you never touch the files       ║
╚══════════════════════════════════════════════════════════════╝
```

### 2.2 Why Separation of Storage and Compute is Revolutionary

Think about what this means practically:

**Scenario 1: Multiple teams, same data**
```
Same underlying storage (your fact and dimension tables)
         │
         ├──► Analytics Warehouse (Large): dashboards, BI tools
         ├──► Data Engineering Warehouse (Small): DBT transformations
         ├──► Data Science Warehouse (X-Large): ML model training
         └──► Reporting Warehouse (X-Small): lightweight reports

All four warehouses read from the SAME data simultaneously.
No data copying. No contention for storage resources.
Each warehouse's compute is completely isolated from the others.
```

This means: the analytics team running slow dashboard queries cannot slow down the data engineering pipelines. They're on separate compute clusters.

**Scenario 2: Elastic scaling**
```
Monday morning dashboard rush:
  → Scale Analytics Warehouse from Medium to X-Large (30 seconds)
  → Scale back down at 10 AM when rush is over (saves $$$)

Month-end financial close (once a month):
  → Spin up a dedicated Finance Warehouse for 2 hours
  → Auto-suspend after use — pay for 2 hours only

Normal overnight:
  → All warehouses auto-suspended
  → Pay only for storage — pennies per hour
```

**Scenario 3: Zero data migration**

If you add a new team that needs access to existing data, you don't copy or move anything. Just create a new warehouse and grant them access. They read from the same storage.

---

### 2.3 How Data Flows Through the Architecture

When you run `SELECT * FROM ad_clicks WHERE click_date = '2024-01-15'`:

```
Step 1: Cloud Services Layer receives the query
   │
   ├── Authentication: Is this user authorized?
   ├── Parser: Is the SQL syntax valid?
   ├── Optimizer: What's the best execution plan?
   │   └── Which micro-partitions contain data for 2024-01-15?
   │       (metadata lookup — no data movement yet)
   └── Sends execution plan to your Virtual Warehouse

Step 2: Virtual Warehouse (your compute cluster) executes
   │
   ├── Worker nodes receive execution plan
   ├── Each node fetches ONLY the relevant micro-partitions from S3
   │   (Only partitions where click_date overlaps 2024-01-15)
   ├── Local caching: hot micro-partitions stay in SSD cache
   │   (avoids re-reading from S3 for repeated queries)
   ├── Nodes process in parallel
   └── Results assembled and returned

Step 3: Results returned to user
   Total time: 0.5 seconds for a billion-row table
   (because only 1/365 of data was read)
```

---

## 3. Storage Layer — How Snowflake Stores Data

### 3.1 Micro-Partitions — The Foundation of Snowflake Storage

Snowflake doesn't store data as one giant file per table. Instead, it divides every table into **micro-partitions**: small, contiguous units of storage, each containing 50-500MB of uncompressed data (typically 10-50MB when compressed).

```
Table: fact_ad_clicks (100 billion rows, 50TB raw)
                │
                ▼
┌─────────────────────────────────────────────────┐
│                 MICRO-PARTITIONS                 │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ MP_0001  │ │ MP_0002  │ │ MP_0003  │  ...    │
│  │ 100MB    │ │ 100MB    │ │ 100MB    │         │
│  │ rows     │ │ rows     │ │ rows     │         │
│  │ 1-50K    │ │ 50K-100K │ │ 100K-150K│         │
│  └──────────┘ └──────────┘ └──────────┘         │
│                                                  │
│  Each micro-partition contains:                  │
│  • A contiguous range of rows                    │
│  • Data stored COLUMNAR within the partition     │
│  • Columnar compression (per-column statistics)  │
│  • Min/max values for EVERY column               │
│  • Bloom filters for high-cardinality columns    │
└─────────────────────────────────────────────────┘
```

**What's stored in each micro-partition's metadata**:

```
MP_0001 metadata (stored in Cloud Services Layer):
├── Row count: 50,000
├── Size: 95MB compressed
├── Column statistics:
│   ├── click_date:    min='2024-01-01', max='2024-01-01'  ← all same day
│   ├── campaign_id:   min='C0001',      max='C9999'
│   ├── cost_usd:      min=0.01,         max=500.00
│   └── user_id:       distinct count = 48,230 (approx)
└── Storage location: s3://sf-bucket/table_id/mp_0001.parquet.zst
```

### 3.2 Partition Pruning — How Snowflake Eliminates Unnecessary Work

When you query `WHERE click_date = '2024-01-15'`, Snowflake consults the metadata for ALL micro-partitions:

```
Query: WHERE click_date = '2024-01-15'

Metadata scan (FREE — no warehouse needed):
  MP_0001: click_date min='2024-01-01', max='2024-01-01'  → SKIP (no overlap)
  MP_0002: click_date min='2024-01-02', max='2024-01-03'  → SKIP
  ...
  MP_0365: click_date min='2024-01-15', max='2024-01-15'  → READ ✓
  MP_0366: click_date min='2024-01-15', max='2024-01-16'  → READ ✓ (might overlap)
  MP_0367: click_date min='2024-01-16', max='2024-01-16'  → SKIP
  ...
  
Result: Read 2 micro-partitions out of 365
        → 0.5% of data scanned
        → 99.5% partition pruning efficiency
```

This is why **clustering** (keeping related rows in the same micro-partitions) is so important. If click_date values are randomly scattered across all micro-partitions, every query must read every partition.

### 3.3 Columnar Storage Within Micro-Partitions

Within each micro-partition, data is stored in columnar format — similar to Parquet:

```
Row-oriented (traditional):
┌──────────────────────────────────────────────────────────┐
│ click_id | campaign_id | user_id | cost_usd | click_date │
│ C_001    | camp_A      | U_1234  | 1.25     | 2024-01-15 │
│ C_002    | camp_B      | U_5678  | 2.50     | 2024-01-15 │
│ C_003    | camp_A      | U_9012  | 0.75     | 2024-01-15 │
└──────────────────────────────────────────────────────────┘
Reading cost_usd column = must read entire rows = inefficient

Column-oriented (Snowflake):
click_id:    [C_001, C_002, C_003, ...]     → read only for SELECT click_id
campaign_id: [camp_A, camp_B, camp_A, ...]  → read only when needed
user_id:     [U_1234, U_5678, U_9012, ...]  → read only when needed
cost_usd:    [1.25, 2.50, 0.75, ...]       → read for SUM(cost_usd)
click_date:  [2024-01-15, 2024-01-15, ...] → read for WHERE click_date=

SELECT SUM(cost_usd) FROM ad_clicks WHERE click_date = '2024-01-15'
→ Read ONLY: cost_usd column + click_date column
→ Ignore: click_id, campaign_id, user_id
→ 2 columns out of 5 = 60% less data read
```

**Compression benefits of columnar storage**:
- All values in `click_date` column for a given day's data are identical → run-length encoding → 100:1 compression
- `campaign_id` has limited cardinality → dictionary encoding → 10:1 compression
- `cost_usd` varies but can use delta encoding → 5:1 compression

Result: A 10TB raw table might occupy only 1-2TB in Snowflake.

---

### 3.4 The Metadata Store — Snowflake's Secret Weapon

Snowflake maintains a massive metadata store in the Cloud Services Layer. This metadata includes:

- Min/max values for every column in every micro-partition
- Row counts per micro-partition
- Null counts per column
- Distinct value counts (approximate)
- File sizes and locations
- Clustering information
- DML history (for Time Travel)

**Why this matters**: Most metadata operations (like checking which partitions to skip) don't require running a Virtual Warehouse. They execute in the Cloud Services Layer for free. This is why simple metadata queries in Snowflake are nearly instantaneous.

---

## 4. Compute Layer — Virtual Warehouses Deep Dive

### 4.1 What is a Virtual Warehouse?

A Virtual Warehouse (VW) is a named cluster of compute resources (EC2 instances on AWS, VMs on Azure/GCP) that executes SQL queries. It is:

- **Ephemeral**: Created in seconds, destroyed in seconds
- **Isolated**: Shares no resources with other warehouses
- **Elastic**: Can be scaled up or out on demand
- **Billed per second**: Costs money only when running (minimum 60 seconds)

Think of a Virtual Warehouse as a **rented supercomputer** that you summon on demand, use for exactly as long as you need, and then dismiss.

```
VIRTUAL WAREHOUSE ANATOMY

  ┌──────────────────────────────────────────────────────┐
  │  Virtual Warehouse: "ANALYTICS_WH" (Size: LARGE)     │
  │                                                       │
  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐│
  │  │   Node 1    │   │   Node 2    │   │   Node 3    ││
  │  │  (compute)  │   │  (compute)  │   │  (compute)  ││
  │  │             │   │             │   │             ││
  │  │ CPU: 4 cores│   │ CPU: 4 cores│   │ CPU: 4 cores││
  │  │ RAM: 16GB   │   │ RAM: 16GB   │   │ RAM: 16GB   ││
  │  │ SSD: 200GB  │   │ SSD: 200GB  │   │ SSD: 200GB  ││
  │  │ (local      │   │ (local      │   │ (local      ││
  │  │  disk cache)│   │  disk cache)│   │  disk cache)││
  │  └─────────────┘   └─────────────┘   └─────────────┘│
  │                                                       │
  │  All nodes connected via high-speed internal network  │
  │  All nodes read from same S3 storage                  │
  └──────────────────────────────────────────────────────┘
```

### 4.2 Warehouse Sizes

Snowflake uses T-shirt sizes. Each size doubles the compute and cost of the previous:

| Size | Nodes | Credits/Hour | Use Case |
|------|-------|-------------|----------|
| X-Small (XS) | 1 | 1 | Development, small queries |
| Small (S) | 2 | 2 | Light analytics, small tables |
| Medium (M) | 4 | 4 | Regular analytics, medium tables |
| Large (L) | 8 | 8 | Heavy analytics, large tables |
| X-Large (XL) | 16 | 16 | Complex queries, 100GB+ tables |
| 2X-Large (2XL) | 32 | 32 | Very heavy workloads |
| 3X-Large (3XL) | 64 | 64 | Massive data processing |
| 4X-Large (4XL) | 128 | 128 | Largest batch jobs |

**Credit pricing**: Typically $2-$4 per credit depending on your Snowflake edition and cloud region. An X-Large warehouse costs ~$3.20/hour (8 credits × $0.40 per credit on Standard edition, AWS us-east-1).

**The key insight about sizing**: A larger warehouse doesn't necessarily mean faster queries for all workloads. SQL queries that are inherently sequential (can't be parallelized) won't get faster by adding more nodes. More nodes help when: your query can be broken into independent parallel pieces (large scans, large joins, large aggregations). For simple point lookups, X-Small might be as fast as 4X-Large.

---

### 4.3 The Local Disk Cache — Critical for Performance

Each node in a Virtual Warehouse has local SSD storage used as a **result cache** and **disk cache**:

```
CACHING HIERARCHY (fastest to slowest):

1. Result Cache (Cloud Services Layer)
   ─────────────────────────────────────
   • Stores COMPLETE query results for 24 hours
   • If exact same query runs again: returns instantly
   • FREE — no warehouse needed
   • Invalidated when underlying data changes
   • Works across sessions (different users benefit)

2. Local Disk Cache (SSD on each warehouse node)
   ─────────────────────────────────────────────
   • Stores micro-partitions fetched from S3
   • Persists as long as warehouse stays running
   • Cleared when warehouse suspends/resizes
   • Makes repeated queries on same data 10-100x faster
   • Private to this warehouse

3. S3 / Azure / GCS Storage
   ───────────────────────────
   • Persistent source of truth
   • First access always reads from here
   • ~100-300ms per micro-partition access
   • Billed at ~$0.023/GB/month (S3 standard)
```

**Practical implication**: 

If your analytics team runs the same dashboards every morning, the first run of the day is slower (reading from S3, populating SSD cache). Subsequent queries in the same day are much faster (reading from SSD cache). This is why **never suspending the warehouse** is sometimes deliberately chosen for latency-sensitive production workloads, even though it costs more.

---

### 4.4 Multi-Cluster Warehouses — Handling Concurrency

A standard Virtual Warehouse processes queries sequentially from a queue — if 50 users submit queries simultaneously, they queue up.

For high-concurrency workloads, Snowflake offers **Multi-Cluster Warehouses**:

```
SINGLE-CLUSTER WAREHOUSE (default):

  User 1 query ─────────────────────────────► Executed
  User 2 query ─── waiting ────────────────► Executed (after user 1)
  User 3 query ─── waiting ─── waiting ───► Executed (after user 2)

  Problem: long queue times when many concurrent users

MULTI-CLUSTER WAREHOUSE (Enterprise feature):

  ┌─────────────────────────────────────────────┐
  │          MULTI-CLUSTER WAREHOUSE             │
  │          (max_clusters = 5)                  │
  │                                              │
  │  Cluster 1: User 1, 2, 3 queries            │
  │  Cluster 2: User 4, 5, 6 queries            │
  │  Cluster 3: User 7, 8, 9 queries (auto-spun │
  │              up when queue grows)            │
  │                                              │
  │  Clusters 4,5: Available but idle (cost-     │
  │                saving: scaled down when      │
  │                queue shrinks)                │
  └─────────────────────────────────────────────┘

  Auto-scale policy: add cluster when queue > N seconds
                     remove cluster when underutilized
```

**When to use multi-cluster**:
- BI tool with 100+ concurrent dashboard users
- End-of-quarter reporting rush
- Public-facing analytics product where query concurrency is unpredictable

---

### 4.5 Warehouse Auto-Suspend and Auto-Resume

```sql
-- Create warehouse with auto-suspend after 5 minutes of inactivity
CREATE WAREHOUSE analytics_wh
    WAREHOUSE_SIZE = 'LARGE'
    AUTO_SUSPEND = 300          -- seconds (300 = 5 minutes)
    AUTO_RESUME = TRUE          -- automatically resumes when query arrives
    INITIALLY_SUSPENDED = TRUE; -- start in suspended state

-- Manually suspend
ALTER WAREHOUSE analytics_wh SUSPEND;

-- Manually resume
ALTER WAREHOUSE analytics_wh RESUME;

-- Check warehouse status
SHOW WAREHOUSES LIKE 'analytics%';
```

**The AUTO_RESUME = TRUE behavior**:
When a query is submitted to a suspended warehouse, Snowflake automatically resumes it. The user experiences a ~10-30 second delay for the warehouse to provision. After that, queries run normally.

**Cost optimization pattern**:

```
Production analytics (accessed all day):
  AUTO_SUSPEND = 600    (10 minutes — saves money vs always-on)
  
ETL pipelines (scheduled, predictable):
  AUTO_SUSPEND = 60     (1 minute — pipeline finishes, warehouse shuts down fast)
  
Ad hoc data science:
  AUTO_SUSPEND = 300    (5 minutes — reasonable for exploration)
  
Monthly reports (run once, done):
  START_WAREHOUSE → RUN QUERY → SUSPEND_WAREHOUSE (immediate)
```

---

## 5. Cloud Services Layer — The Brain

### 5.1 What the Cloud Services Layer Does

The Cloud Services Layer is the intelligence of Snowflake. It's always running (Snowflake manages it — you can't touch it), shared across all customers (multi-tenanted but isolated), and handles everything that isn't actual query computation:

```
CLOUD SERVICES LAYER RESPONSIBILITIES:

1. AUTHENTICATION & SESSION MANAGEMENT
   ────────────────────────────────────
   • Validates user credentials
   • Manages SSO/MFA integration
   • Handles service account tokens (key-pair auth)
   • Creates and tracks sessions

2. ACCESS CONTROL
   ──────────────
   • Enforces RBAC (Role-Based Access Control)
   • Checks: does this user have SELECT on this table?
   • Applies row-level and column-level security policies
   • Dynamic Data Masking enforcement

3. QUERY COMPILATION & OPTIMIZATION
   ──────────────────────────────────
   • SQL parsing (checks syntax)
   • Query optimization (rewrites query for efficiency)
   • Execution plan generation
   • Decides which micro-partitions to read (partition pruning)
   • Generates parallelization plan for warehouse nodes

4. METADATA MANAGEMENT
   ─────────────────────
   • Stores all table, schema, database definitions
   • Stores micro-partition metadata (min/max/rowcount)
   • Manages Time Travel history
   • Tracks clones and sharing relationships

5. TRANSACTION MANAGEMENT
   ──────────────────────
   • ACID transaction support
   • Isolation levels
   • Lock management for concurrent DML

6. RESULT CACHE
   ────────────
   • Stores query results for 24 hours
   • Returns cached results for identical queries
   • No warehouse needed for cached results
```

### 5.2 The Query Optimizer

Snowflake uses a **cost-based query optimizer** similar to other major databases, but with cloud-native enhancements:

```
QUERY OPTIMIZATION PIPELINE:

  Raw SQL
    │
    ▼
  PARSING: Check syntax, resolve object names
    │
    ▼
  LOGICAL PLAN: Tree representation of the query
    │
    ▼
  OPTIMIZATION REWRITES:
  ├── Predicate pushdown (WHERE close to data source)
  ├── Join reordering (small tables before large tables)
  ├── Projection elimination (remove unused columns early)
  ├── Subquery flattening (convert subqueries to joins)
  └── Constant folding (compute constants at plan time)
    │
    ▼
  MICRO-PARTITION PRUNING:
  └── Consult metadata: which micro-partitions match WHERE clause?
      → Potentially eliminate 99% of data before any compute
    │
    ▼
  PHYSICAL PLAN: How to execute on warehouse nodes
  ├── Which operator for each step (hash join vs sort-merge)
  ├── How to distribute work across nodes
  └── Memory allocation per operator
    │
    ▼
  EXECUTION on Virtual Warehouse
```

**Key optimizer behaviors you should know**:

1. **Automatic statistics**: The optimizer uses micro-partition metadata (min/max, null counts, distinct counts) automatically — no `ANALYZE TABLE` required like in PostgreSQL.

2. **Adaptive optimization**: During execution, if actual row counts differ from estimates, the plan can be adjusted mid-execution.

3. **Join optimization**: Snowflake automatically decides between hash joins and merge joins based on data size. For joins where one side is very small, it may broadcast the small side to all nodes.

---

## 6. Data Types, Tables, and Schemas

### 6.1 Snowflake Objects Hierarchy

```
ACCOUNT
└── DATABASE (e.g., COSTCO_DW)
    ├── SCHEMA (e.g., RAW, STAGING, MARTS)
    │   ├── TABLE
    │   │   ├── Permanent Table (default)
    │   │   ├── Temporary Table (session-scoped)
    │   │   ├── Transient Table (no fail-safe)
    │   │   └── External Table (files in S3/Azure/GCS)
    │   ├── VIEW
    │   │   ├── Standard View
    │   │   └── Materialized View
    │   ├── STREAM (CDC tracking)
    │   ├── TASK (scheduled execution)
    │   ├── STAGE (data loading area)
    │   │   ├── Internal Stage
    │   │   └── External Stage (S3/Azure/GCS bucket)
    │   ├── FILE FORMAT
    │   ├── SEQUENCE
    │   └── FUNCTION / PROCEDURE
    └── INFORMATION_SCHEMA (virtual, always present)
```

### 6.2 Table Types — Critical Differences

```
TABLE TYPES COMPARISON:

                 Permanent    Transient    Temporary    External
                 ─────────    ─────────    ─────────    ────────
Time Travel      Up to 90d    0-1 day      0-1 day      None
Fail-Safe        7 days       None         None         None
Duration         Persistent   Persistent   Session only Read-only
Storage Billing  Full         Reduced      Reduced      Ext only
Use Case         Production   Staging      ETL work     Data lake

```

**Permanent Table**: Your main production tables. Full Time Travel (1-90 days). 7-day Fail-Safe after Time Travel expires. Highest storage cost because you pay for current data + historical versions + fail-safe.

**Transient Table**: Like permanent but no Fail-Safe. Use for staging tables, intermediate pipeline results that you can recreate if lost. Significantly cheaper because no fail-safe period.

**Temporary Table**: Exists only for the current session. Automatically dropped when session ends. Perfect for intermediate results within a pipeline run. No storage cost beyond session.

**External Table**: A "table" that points to files in your cloud storage (S3/Azure/GCS) but doesn't copy the data. Metadata about the files is stored in Snowflake. You can query external tables with SQL, but performance is lower than native tables.

```sql
-- Create a permanent table (default)
CREATE TABLE campaigns (
    campaign_id     VARCHAR(50)     NOT NULL,
    campaign_name   VARCHAR(200)    NOT NULL,
    channel         VARCHAR(50),
    daily_budget    NUMBER(12,2),
    created_at      TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP()
);

-- Create a transient table (cheaper staging table)
CREATE TRANSIENT TABLE stg_ad_clicks (
    click_id        VARCHAR(100),
    campaign_id     VARCHAR(50),
    user_id         VARCHAR(100),
    clicked_at      TIMESTAMP_NTZ,
    cost_usd        FLOAT
);

-- Create an external table pointing to S3
CREATE EXTERNAL TABLE ext_raw_clicks (
    click_id        VARCHAR AS (value:click_id::VARCHAR),
    campaign_id     VARCHAR AS (value:campaign_id::VARCHAR),
    clicked_at      TIMESTAMP AS (value:clicked_at::TIMESTAMP)
)
WITH LOCATION = @my_s3_stage/raw_clicks/
FILE_FORMAT = (TYPE = 'PARQUET');
```

### 6.3 Data Types You Must Know

```sql
-- NUMERIC TYPES
NUMBER(precision, scale)  -- Fixed-point: NUMBER(10,2) = up to 10 digits, 2 decimal
FLOAT / REAL / DOUBLE     -- Floating point (approximate)
INT / INTEGER / BIGINT    -- Integer (internally stored as NUMBER)

-- STRING TYPES
VARCHAR(n)                -- Variable length string, max n chars (max 16MB)
CHAR(n)                   -- Fixed length (Snowflake treats same as VARCHAR internally)
STRING                    -- Alias for VARCHAR (unlimited length)
TEXT                      -- Alias for VARCHAR (unlimited length)

-- DATE/TIME TYPES
DATE                      -- Date only: 2024-01-15
TIME                      -- Time only: 14:23:07.000
TIMESTAMP_NTZ             -- Timestamp, No TimeZone: 2024-01-15 14:23:07.000
TIMESTAMP_LTZ             -- Timestamp, Local TimeZone: stored as UTC, shown in session TZ
TIMESTAMP_TZ              -- Timestamp WITH timezone offset: 2024-01-15 14:23:07+05:30

-- SEMI-STRUCTURED TYPES (Snowflake's unique strength)
VARIANT                   -- Can hold ANY JSON, XML, array, or scalar value
OBJECT                    -- JSON object (key-value pairs)
ARRAY                     -- Ordered list of values

-- BOOLEAN
BOOLEAN                   -- TRUE / FALSE / NULL

-- BINARY
BINARY / VARBINARY        -- Raw bytes
```

**VARIANT is a crucial Snowflake differentiator** — covered extensively in Section 9.

---

### 6.4 Clustering Keys — Controlling Data Organization

By default, Snowflake loads data in the order it arrives. Over time, a table with millions of micro-partitions may have poor clustering — the same date's data scattered across thousands of partitions.

**Clustering Keys** tell Snowflake to organize micro-partitions by specific columns, so queries filtering on those columns skip the maximum number of partitions.

```sql
-- Define clustering key when creating table
CREATE TABLE fact_ad_clicks (
    click_id        VARCHAR,
    campaign_id     VARCHAR,
    click_date      DATE,
    cost_usd        FLOAT
)
CLUSTER BY (click_date, campaign_id);
-- Micro-partitions will be organized so same click_date+campaign_id rows
-- are stored close together → queries filtering on these are much faster

-- Add clustering to existing table
ALTER TABLE fact_ad_clicks CLUSTER BY (click_date);

-- Check clustering health
SELECT SYSTEM$CLUSTERING_INFORMATION('fact_ad_clicks', '(click_date)');
-- Returns: average_depth, average_overlaps, etc.
-- Good clustering: average_depth close to 1 (minimal overlap)
-- Poor clustering: average_depth >> 1 (many partitions overlap on cluster key values)

-- Automatic reclustering (Serverless feature)
ALTER TABLE fact_ad_clicks
SET ENABLE_AUTOMATIC_CLUSTERING = TRUE;
-- Snowflake automatically reclusters in background as data grows
-- Billed as Serverless compute (not Virtual Warehouse)
```

**When to use clustering keys**:

```
Use clustering when ALL of these are true:
1. Table is large (> 1 TB)
2. Queries FREQUENTLY filter on specific columns
3. Current partition pruning is poor (SYSTEM$CLUSTERING_INFORMATION shows high depth)

Don't cluster when:
- Table is small (pruning benefit is minimal)
- Query patterns are highly varied (no single dominant filter column)
- Data is already naturally ordered by the desired column (e.g., append-only time-series)
```

---

## 7. Loading Data into Snowflake

### 7.1 The COPY INTO Command — Bulk Loading

Snowflake's primary bulk loading mechanism is the `COPY INTO` command. It reads files from a **Stage** (a location in cloud storage) and loads them into a table.

**Stages** are named references to cloud storage locations:

```sql
-- ─────────────────────────────────────────────
-- STAGE TYPES
-- ─────────────────────────────────────────────

-- 1. Internal Named Stage (Snowflake-managed storage)
CREATE STAGE my_internal_stage
    FILE_FORMAT = (TYPE = 'CSV' SKIP_HEADER = 1);

-- Upload file to internal stage via SnowSQL CLI:
-- PUT file:///local/path/clicks.csv @my_internal_stage;

-- 2. External Stage (your own S3 bucket)
CREATE STAGE my_s3_stage
    URL = 's3://costco-data-bucket/raw/'
    CREDENTIALS = (AWS_KEY_ID='...' AWS_SECRET_KEY='...')
    FILE_FORMAT = (TYPE = 'PARQUET');

-- Better: use Storage Integration (avoids embedding credentials)
CREATE STORAGE INTEGRATION s3_integration
    TYPE = EXTERNAL_STAGE
    STORAGE_PROVIDER = 'S3'
    ENABLED = TRUE
    STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::123:role/snowflake-role'
    STORAGE_ALLOWED_LOCATIONS = ('s3://costco-data-bucket/');

CREATE STAGE my_s3_stage
    URL = 's3://costco-data-bucket/raw/'
    STORAGE_INTEGRATION = s3_integration
    FILE_FORMAT = (TYPE = 'PARQUET');

-- 3. External Stage (Azure Blob Storage)
CREATE STAGE my_azure_stage
    URL = 'azure://myaccount.blob.core.windows.net/mycontainer/raw/'
    CREDENTIALS = (AZURE_SAS_TOKEN='?...')
    FILE_FORMAT = (TYPE = 'JSON');
```

**COPY INTO — the actual load command**:

```sql
-- Basic CSV load
COPY INTO stg_ad_clicks
FROM @my_s3_stage/ad_clicks/
FILE_FORMAT = (
    TYPE = 'CSV'
    SKIP_HEADER = 1
    FIELD_DELIMITER = ','
    NULL_IF = ('NULL', 'null', '')
    EMPTY_FIELD_AS_NULL = TRUE
    DATE_FORMAT = 'YYYY-MM-DD'
    TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS'
)
PATTERN = '.*clicks_2024.*\\.csv'  -- only load files matching this pattern
ON_ERROR = 'SKIP_FILE'             -- skip files with errors (vs ABORT_STATEMENT)
PURGE = FALSE;                     -- don't delete source files after load

-- Load Parquet (best format for Snowflake)
COPY INTO fact_ad_clicks
FROM (
    SELECT
        $1:click_id::VARCHAR,
        $1:campaign_id::VARCHAR,
        $1:user_id::VARCHAR,
        $1:clicked_at::TIMESTAMP_NTZ,
        $1:cost_micros::NUMBER / 1000000.0
    FROM @my_s3_stage/parquet_clicks/
)
FILE_FORMAT = (TYPE = 'PARQUET')
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;

-- Load JSON (VARIANT column)
COPY INTO raw_events (event_id, raw_payload, loaded_at)
FROM (
    SELECT
        $1:event_id::VARCHAR,
        $1,                          -- entire JSON as VARIANT
        CURRENT_TIMESTAMP()
    FROM @my_s3_stage/events/
)
FILE_FORMAT = (TYPE = 'JSON');

-- Check load history
SELECT * FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
    TABLE_NAME => 'stg_ad_clicks',
    START_TIME => DATEADD('hour', -24, CURRENT_TIMESTAMP())
));
```

### 7.2 Loading Error Handling

```sql
-- COPY INTO ON_ERROR options:
ON_ERROR = 'CONTINUE'        -- Load good rows, skip bad rows, continue
ON_ERROR = 'SKIP_FILE'       -- Skip entire file if any error
ON_ERROR = 'SKIP_FILE_10'    -- Skip file if more than 10 errors
ON_ERROR = 'SKIP_FILE_1%'    -- Skip file if more than 1% of rows error
ON_ERROR = 'ABORT_STATEMENT' -- Stop entire COPY on first error (default for some)

-- After load: check what was rejected
SELECT * FROM TABLE(VALIDATE(stg_ad_clicks, JOB_ID => '_last'));
-- Returns rejected rows with error descriptions
```

### 7.3 Snowpipe — Continuous / Micro-Batch Loading

For near-real-time loading (as files arrive in S3), Snowflake offers **Snowpipe** — a serverless, event-driven loading service:

```
HOW SNOWPIPE WORKS:

1. New file lands in S3 bucket
        │
        ▼
2. S3 sends event notification to SQS queue (or Azure Event Grid)
        │
        ▼
3. Snowpipe receives SQS event
        │
        ▼
4. Snowpipe runs the COPY INTO command for the new file
        │
        ▼
5. Data available in Snowflake table (typically within 1-5 minutes)

Key properties:
• Serverless — no warehouse running costs (Snowflake manages compute)
• Billed per file loaded (compute cost per-file, very cheap)
• Best for: continuous micro-batch loading (1 file every few minutes)
• Not for: high-volume real-time streaming (use Kafka connector instead)
```

```sql
-- Create Snowpipe
CREATE PIPE ad_clicks_pipe
    AUTO_INGEST = TRUE  -- Uses SQS notifications from S3
AS
COPY INTO stg_ad_clicks
FROM @my_s3_stage/ad_clicks/
FILE_FORMAT = (TYPE = 'PARQUET');

-- Get the SQS ARN to configure on your S3 bucket
SHOW PIPES;
-- Column: notification_channel = arn:aws:sqs:...

-- Check pipe status
SELECT SYSTEM$PIPE_STATUS('ad_clicks_pipe');

-- Check ingestion history
SELECT * FROM TABLE(INFORMATION_SCHEMA.PIPE_USAGE_HISTORY(
    DATE_RANGE_START => DATEADD('day', -1, CURRENT_TIMESTAMP()),
    PIPE_NAME => 'ad_clicks_pipe'
));
```

---

## 8. Querying — SQL Dialect and Special Features

### 8.1 Standard SQL Features

Snowflake supports ANSI SQL with extensions. All standard SQL features work: SELECT/FROM/WHERE/GROUP BY/HAVING/ORDER BY, all JOIN types, subqueries, CTEs (WITH clauses), window functions, etc.

```sql
-- Standard SQL: all of this works exactly as expected
WITH daily_metrics AS (
    SELECT
        click_date,
        campaign_id,
        COUNT(*)                AS clicks,
        SUM(cost_usd)           AS spend,
        COUNT(DISTINCT user_id) AS unique_users
    FROM fact_ad_clicks
    WHERE click_date >= DATEADD('day', -30, CURRENT_DATE())
    GROUP BY 1, 2
),
with_roas AS (
    SELECT
        dm.*,
        COALESCE(cv.revenue, 0)         AS revenue,
        SAFE_DIVIDE(cv.revenue, dm.spend) AS roas,
        ROW_NUMBER() OVER (
            PARTITION BY click_date ORDER BY dm.spend DESC
        ) AS spend_rank
    FROM daily_metrics dm
    LEFT JOIN daily_conversions cv USING (click_date, campaign_id)
)
SELECT * FROM with_roas
WHERE spend_rank <= 10
ORDER BY click_date DESC, spend_rank;
```

### 8.2 Snowflake-Specific SQL Features

**QUALIFY clause** (very useful shorthand):

```sql
-- Without QUALIFY: requires subquery
SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY roas DESC) AS rn
    FROM campaign_daily
) WHERE rn = 1;

-- With QUALIFY: much cleaner
SELECT *
FROM campaign_daily
QUALIFY ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY roas DESC) = 1;
```

**SAMPLE** — statistical sampling:

```sql
-- Row sampling: each row has 0.1% probability of being included
SELECT * FROM fact_ad_clicks SAMPLE (0.1);

-- Block sampling: sample 10% of micro-partitions
SELECT * FROM fact_ad_clicks SAMPLE BLOCK (10);
-- Faster than row sampling for large tables (skips entire partitions)

-- Reproducible sampling (SEED makes it deterministic)
SELECT * FROM fact_ad_clicks SAMPLE (1) SEED (42);
```

**PIVOT and UNPIVOT**:

```sql
-- PIVOT: rows to columns
SELECT * FROM campaign_daily
PIVOT (SUM(spend_usd) FOR channel IN ('google_search', 'meta', 'tiktok'))
AS p (click_date, campaign_id, google_search_spend, meta_spend, tiktok_spend);

-- UNPIVOT: columns to rows
SELECT click_date, campaign_id, channel, spend_usd
FROM campaign_wide_table
UNPIVOT (spend_usd FOR channel IN (google_search_spend, meta_spend, tiktok_spend));
```

**GENERATOR** — generate rows programmatically:

```sql
-- Generate a date spine (sequence of dates)
SELECT
    DATEADD('day', SEQ4(), '2024-01-01')::DATE AS date_day
FROM TABLE(GENERATOR(ROWCOUNT => 366))  -- generates 366 rows
WHERE date_day <= '2024-12-31';
```

**Conditional expressions**:

```sql
-- IFF: Snowflake's shorthand for CASE WHEN condition THEN a ELSE b END
SELECT IFF(spend_usd > 1000, 'high', 'low') AS spend_tier FROM campaigns;

-- ZEROIFNULL: replace NULL with 0
SELECT ZEROIFNULL(revenue_usd) AS revenue FROM fact_ad_clicks;

-- NULLIFZERO: replace 0 with NULL (useful before division)
SELECT revenue_usd / NULLIFZERO(spend_usd) AS roas FROM fact_ad_clicks;

-- DECODE: like CASE with equality checks
SELECT DECODE(status, 'active', 'A', 'paused', 'P', 'deleted', 'D', 'U') AS status_code
FROM campaigns;
```

---

### 8.3 Time Functions

```sql
-- Current timestamps
CURRENT_TIMESTAMP()    -- TIMESTAMP_LTZ (with local timezone)
CURRENT_DATE()         -- DATE only
SYSDATE()              -- Same as CURRENT_TIMESTAMP()
GETDATE()              -- Same as CURRENT_TIMESTAMP()

-- Date arithmetic
DATEADD('day', -7, CURRENT_DATE())       -- 7 days ago
DATEADD('month', -1, CURRENT_DATE())     -- 1 month ago
DATEADD('year', 1, '2024-01-15')         -- next year

-- Date difference
DATEDIFF('day', '2024-01-01', '2024-01-15')    -- 14 days
DATEDIFF('hour', clicked_at, converted_at)      -- hours between events

-- Extract parts
EXTRACT(YEAR FROM clicked_at)
YEAR(clicked_at)        -- shorthand
MONTH(clicked_at)
DAY(clicked_at)
HOUR(clicked_at)
DAYOFWEEK(clicked_at)  -- 0=Sun, 1=Mon, ..., 6=Sat
DAYOFYEAR(clicked_at)

-- Truncation
DATE_TRUNC('month', clicked_at)   -- first of the month
DATE_TRUNC('week', clicked_at)    -- first day of the week
DATE_TRUNC('hour', clicked_at)    -- top of the hour

-- Format and parse
TO_DATE('2024-01-15', 'YYYY-MM-DD')
TO_TIMESTAMP('2024-01-15 14:23:07', 'YYYY-MM-DD HH24:MI:SS')
TO_CHAR(clicked_at, 'YYYY-MM-DD')   -- timestamp to string

-- Timezone handling
CONVERT_TIMEZONE('UTC', 'America/Los_Angeles', clicked_at)
AT TIME ZONE 'America/New_York'
```

---

## 9. Semi-Structured Data — Variant, JSON, Arrays

### 9.1 The VARIANT Type — Snowflake's Superpower

The VARIANT type can hold ANY value: JSON objects, arrays, scalars, NULL. It's stored in a columnar binary format that enables efficient querying without fully deserializing the data.

This is one of Snowflake's biggest advantages over traditional data warehouses — you can ingest raw JSON/event data immediately without defining a schema, and query it flexibly.

```
┌──────────────────────────────────────────────────────────────┐
│                    HOW VARIANT STORAGE WORKS                  │
│                                                              │
│  Input JSON:                                                 │
│  {                                                           │
│    "event": "click",                                         │
│    "campaign": {"id": "C001", "name": "Summer Sale"},        │
│    "user": {"id": "U123", "age": 28},                       │
│    "tags": ["mobile", "retargeting"],                        │
│    "cost_usd": 1.25                                          │
│  }                                                           │
│                                                              │
│  Stored internally as an efficient binary columnar format.   │
│  Snowflake auto-detects field types (strings, numbers,       │
│  arrays) and stores them efficiently.                        │
│                                                              │
│  Queried with colon (:) dot notation:                        │
│  payload:event           → "click"                           │
│  payload:campaign:id     → "C001"                            │
│  payload:user:age        → 28                                │
│  payload:tags[0]         → "mobile"                          │
│  payload:cost_usd        → 1.25                              │
└──────────────────────────────────────────────────────────────┘
```

```sql
-- Table with VARIANT column
CREATE TABLE raw_events (
    event_id    VARCHAR,
    payload     VARIANT,           -- raw JSON stored here
    loaded_at   TIMESTAMP_NTZ
);

-- Load JSON
INSERT INTO raw_events
SELECT
    value:event_id::VARCHAR,
    value,
    CURRENT_TIMESTAMP()
FROM @my_s3_stage/events/
(FILE_FORMAT => 'json_format');

-- Querying VARIANT data
SELECT
    payload:event::VARCHAR              AS event_type,
    payload:campaign:id::VARCHAR        AS campaign_id,
    payload:campaign:name::VARCHAR      AS campaign_name,
    payload:user:id::VARCHAR            AS user_id,
    payload:user:age::INTEGER           AS user_age,
    payload:cost_usd::FLOAT             AS cost_usd,
    payload:tags                        AS tags_array,       -- still VARIANT
    payload:tags[0]::VARCHAR            AS first_tag,        -- first array element
    ARRAY_SIZE(payload:tags)            AS tag_count
FROM raw_events
WHERE payload:event::VARCHAR = 'click';

-- The :: operator is TYPE CASTING:
-- payload:cost_usd         → VARIANT (still JSON-encoded float)
-- payload:cost_usd::FLOAT  → native Snowflake FLOAT
-- Without casting: comparisons and math don't work correctly

-- FLATTEN: explode arrays into rows
SELECT
    r.event_id,
    r.payload:user:id::VARCHAR      AS user_id,
    f.value::VARCHAR                AS tag
FROM raw_events r,
LATERAL FLATTEN(INPUT => r.payload:tags) f;
-- One row per (event_id, tag)
```

### 9.2 FLATTEN — Exploding Nested Arrays

`FLATTEN` is Snowflake's equivalent of Spark's `explode()`. It takes an array or object and returns one row per element:

```sql
-- FLATTEN a simple array
SELECT
    click_id,
    f.index     AS tag_position,
    f.value     AS tag_value
FROM events,
LATERAL FLATTEN(INPUT => payload:tags) f;

-- FLATTEN a nested object (key-value pairs)
SELECT
    campaign_id,
    f.key       AS attribute_name,
    f.value     AS attribute_value
FROM campaigns,
LATERAL FLATTEN(INPUT => attributes) f;

-- Important FLATTEN output columns:
-- SEQ:   position of the array within the source row
-- KEY:   key name (for objects), null for arrays
-- PATH:  full path of the flattened element
-- INDEX: 0-based position within the array
-- VALUE: the actual value (VARIANT)
-- THIS:  the input (the array/object being flattened)

-- Nested FLATTEN: flatten array of objects
SELECT
    event_id,
    f.value:sku::VARCHAR        AS sku,
    f.value:quantity::INTEGER   AS quantity,
    f.value:price::FLOAT        AS unit_price
FROM raw_orders,
LATERAL FLATTEN(INPUT => payload:items) f;
-- payload = {"items": [{"sku":"X1", "qty":2, "price":19.99}, ...]}
-- One row per item per order
```

### 9.3 PARSE_JSON and TO_JSON

```sql
-- Convert JSON string to VARIANT
SELECT PARSE_JSON('{"name": "Costco", "id": 1}') AS parsed;

-- Convert VARIANT back to JSON string
SELECT TO_JSON(payload) AS json_string FROM raw_events;

-- Build OBJECT from columns
SELECT OBJECT_CONSTRUCT(
    'campaign_id', campaign_id,
    'spend', spend_usd,
    'roas', revenue_usd / NULLIFZERO(spend_usd)
) AS metrics_json
FROM campaign_daily;

-- Build ARRAY from values
SELECT ARRAY_CONSTRUCT('mobile', 'retargeting', 'google') AS tags;

-- Array operations
SELECT
    ARRAY_CONTAINS('mobile'::VARIANT, tags) AS is_mobile,
    ARRAY_SIZE(tags)                         AS tag_count,
    ARRAY_APPEND(tags, 'new_tag'::VARIANT)  AS updated_tags
FROM events;
```

---

## 10. Performance Optimization — Clustering, Search Optimization

### 10.1 Understanding Query Performance Issues

Before optimizing, diagnose. Snowflake provides rich query profiling:

```sql
-- View query profile in Snowflake UI:
-- After running a query, go to Query History → click a query → View Profile
-- This shows a visual execution plan with:
-- • Time spent in each operator
-- • Bytes scanned vs bytes pruned (partition pruning efficiency)
-- • Spillage to disk (indicates memory pressure)
-- • Rows produced/consumed at each step
-- • Join types used

-- Programmatic query inspection
SELECT
    query_id,
    query_text,
    execution_time / 1000 AS execution_seconds,
    bytes_scanned / 1e9   AS gb_scanned,
    partitions_scanned,
    partitions_total,
    ROUND(100 * (1 - partitions_scanned / partitions_total), 2) AS pct_pruned,
    bytes_spilled_to_local_storage / 1e9 AS gb_spilled_local
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION())
WHERE start_time >= DATEADD('hour', -1, CURRENT_TIMESTAMP())
ORDER BY execution_time DESC;
```

### 10.2 Common Performance Problems and Solutions

**Problem 1: Poor partition pruning (high partitions_scanned / partitions_total)**

```
Symptom: partitions_scanned = 5000, partitions_total = 5000 (0% pruned)
Cause: No useful clustering; query filter doesn't match any min/max ranges
Fix: Add a CLUSTER BY on the frequently-filtered column

Example:
Before: SELECT * FROM fact_ad_clicks WHERE campaign_id = 'C001'
        → Scans ALL partitions because campaign_id values are mixed throughout

After adding CLUSTER BY (campaign_id):
        → Scans only partitions where min/max of campaign_id includes 'C001'
        → Might prune 95% of partitions
```

**Problem 2: Disk spill (bytes_spilled_to_local_storage > 0)**

```
Symptom: gb_spilled_local = 50 (50GB of data spilled to local SSD)
Cause: Operation (join, aggregation, sort) requires more memory than available
Fix options:
  1. Use larger warehouse size (more memory per node)
  2. Optimize query to reduce working set (filter earlier, select fewer columns)
  3. Break query into steps using temporary tables
  4. For very large joins: pre-aggregate before joining

Disk spill progression (bad to worse):
  No spill → spill to local SSD → spill to remote storage (S3)
  Remote spill is catastrophically slow — 100x worse than local spill
```

**Problem 3: Cartesian product / join explosion**

```sql
-- PROBLEM: missing join condition causes cross join
SELECT a.*, b.*
FROM campaigns a, conversions b  -- implicit cross join!
-- If campaigns has 1000 rows and conversions has 1M: 1 TRILLION rows

-- PROBLEM: non-unique join key causes fan-out
SELECT c.*, d.*
FROM ad_clicks c
JOIN dim_campaigns d ON c.campaign_id = d.campaign_id
-- If dim_campaigns has 5 rows per campaign_id (SCD2 history):
-- 1M clicks × 5 versions = 5M rows (5x explosion)
-- FIX: filter dim to current version: WHERE d.is_current = TRUE
```

### 10.3 Search Optimization Service

For high-cardinality lookup queries (finding specific rows by unique identifier), Snowflake's **Search Optimization Service** can dramatically improve performance:

```
SEARCH OPTIMIZATION SERVICE:

Problem it solves: "Find the 5 rows where user_id = 'U_12345'"
Normal behavior: scan all micro-partitions (user_id min/max ranges don't help much)
With search optimization: bloom filter index over all values → near-instant lookup

┌─────────────────────────────────────────────────────┐
│             SEARCH OPTIMIZATION INDEX                │
│                                                      │
│  Bloom filter per unique value per column:           │
│  user_id='U_12345' → in partitions [MP_0042, MP_2891]│
│                       NOT in other 99% of partitions │
│                                                      │
│  Cost: extra storage (typically 10-20% of table size)│
│  Benefit: point lookups go from seconds to ms        │
└─────────────────────────────────────────────────────┘
```

```sql
-- Enable search optimization on a table
ALTER TABLE fact_ad_clicks
ADD SEARCH OPTIMIZATION ON EQUALITY(user_id, click_id);

-- For multi-value equality (IN clause)
ALTER TABLE fact_ad_clicks
ADD SEARCH OPTIMIZATION ON EQUALITY(campaign_id)
                          ON SUBSTRING(campaign_name);   -- also supports LIKE

-- Check optimization status
SHOW SEARCH OPTIMIZATION;

-- Use case: customer support tool that looks up specific user's clicks
SELECT * FROM fact_ad_clicks WHERE user_id = 'U_12345_SPECIFIC_USER';
-- Without search optimization: scans all partitions → 30 seconds
-- With search optimization: reads 2 specific partitions → 0.1 seconds
```

---

## 11. Time Travel and Fail-Safe

### 11.1 Time Travel — Querying Historical Data

Time Travel is one of Snowflake's most powerful and unique features. It allows you to query data AS IT WAS at any point in the past (up to 90 days on Enterprise edition).

```
TIME TRAVEL CONCEPT:

Present:  [Row A: budget=1000] [Row B: budget=500] [Row C: budget=750]
   │
   │ 2 hours ago: UPDATE campaigns SET budget=1000 WHERE id='A'
   │              (budget was 750 before)
   │
   │ Yesterday: ACCIDENTALLY RAN: DELETE FROM campaigns WHERE id='B'
   │
   │
Time Travel allows you to:
1. Query the table as it was BEFORE the accidental delete
2. Restore the accidentally deleted/modified data
3. Audit: see what changed, when, and by whom
```

```sql
-- ─────────────────────────────────────────────────────
-- QUERYING HISTORICAL DATA
-- ─────────────────────────────────────────────────────

-- At a specific timestamp
SELECT * FROM campaigns
AT (TIMESTAMP => '2024-01-14 08:00:00'::TIMESTAMP_NTZ);

-- N seconds ago
SELECT * FROM campaigns
AT (OFFSET => -3600);  -- 1 hour ago

-- Before a specific statement (using Query ID)
-- First: find the query ID of the accidental DELETE
SELECT QUERY_ID, QUERY_TEXT, START_TIME
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY())
WHERE QUERY_TEXT ILIKE '%DELETE FROM campaigns%'
ORDER BY START_TIME DESC;

-- Then: see data as it was just before that query
SELECT * FROM campaigns
BEFORE (STATEMENT => '01aXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX');

-- ─────────────────────────────────────────────────────
-- RESTORING DATA (Undoing Accidental Changes)
-- ─────────────────────────────────────────────────────

-- Option 1: INSERT back the deleted rows
INSERT INTO campaigns
SELECT * FROM campaigns BEFORE (STATEMENT => 'query_id_of_the_delete');
-- This inserts back all rows that existed before the delete

-- Option 2: Recreate entire table from a past point (CLONE with Time Travel)
CREATE TABLE campaigns_restored
CLONE campaigns
AT (TIMESTAMP => '2024-01-14 07:59:00'::TIMESTAMP_NTZ);
-- Instantly creates a copy as it was before the accident

-- Option 3: Full table restore (UNDROP)
DROP TABLE campaigns;    -- simulate accidental drop
UNDROP TABLE campaigns;  -- restore it (works within Time Travel retention period)
```

### 11.2 Configuring Time Travel Retention

```sql
-- Set retention period at table level (0-90 days, depends on edition)
-- Standard edition: 0-1 day
-- Enterprise edition: 0-90 days

CREATE TABLE fact_ad_clicks (...)
DATA_RETENTION_TIME_IN_DAYS = 7;      -- 7 days of Time Travel

-- Change retention on existing table
ALTER TABLE fact_ad_clicks
SET DATA_RETENTION_TIME_IN_DAYS = 30;

-- Disable Time Travel (for transient tables or cost savings)
ALTER TABLE staging_temp
SET DATA_RETENTION_TIME_IN_DAYS = 0;

-- Schema/database level
ALTER DATABASE costco_dw
SET DATA_RETENTION_TIME_IN_DAYS = 14;

-- Cost implications:
-- Time Travel data is stored in addition to current data
-- A table with 100GB current data + 7-day retention:
-- If 5% of rows change daily → 35% extra storage = ~135GB total
-- Storage is priced at ~$23/TB/month
```

### 11.3 Fail-Safe — The Last Resort

After Time Travel retention expires, data enters **Fail-Safe** for 7 days (always 7 days, non-configurable, Enterprise and above). Fail-Safe is NOT accessible via SQL — only Snowflake support can recover data from Fail-Safe, and it's an emergency procedure.

```
DATA LIFECYCLE TIMELINE:

    Data written
         │
         ▼
    ACTIVE PERIOD (current data — always accessible)
         │
         ▼  ← Data is modified/deleted
    TIME TRAVEL PERIOD (configurable, up to 90 days)
         │  ← Query with AT/BEFORE syntax, UNDROP
         │  ← Full user control
         ▼  ← Time Travel period expires
    FAIL-SAFE PERIOD (fixed 7 days)
         │  ← No user access
         │  ← Snowflake support recovery only
         │  ← Emergency safety net
         ▼  ← Fail-Safe expires
    DATA PERMANENTLY DELETED

STORAGE BILLING:
    Active: billed at $23/TB/month
    Time Travel: billed at $23/TB/month (additional)
    Fail-Safe: billed at $23/TB/month (additional)
    
    A table with 1TB active data, 30-day retention, and 5% daily change:
    → ~1.5TB active + ~1.5TB time travel + ~0.35TB fail-safe = ~3.35TB billed
```

---

## 12. Cloning — Zero-Copy Clones

### 12.1 What is a Zero-Copy Clone?

Cloning creates an independent copy of a database, schema, or table that:
- Is **instantaneous** (no data is physically copied)
- **Costs nothing initially** (clone points to same micro-partitions as the original)
- Is **fully independent** (changes to clone don't affect original and vice versa)

This is possible because of **copy-on-write** semantics:

```
BEFORE CLONE:
  Original Table → [MP_001][MP_002][MP_003][MP_004][MP_005]
                    ↑       ↑       ↑       ↑       ↑
                    All micro-partitions in S3

AFTER CLONE (instant, no data copied):
  Original Table → [MP_001][MP_002][MP_003][MP_004][MP_005]
  Cloned Table  →  [MP_001][MP_002][MP_003][MP_004][MP_005]
  (both point to the SAME physical files — no duplication)

AFTER MODIFYING CLONED TABLE (copy-on-write):
  -- If you UPDATE rows in MP_003 of the clone:
  -- Snowflake creates NEW micro-partition MP_003_new with the changes
  -- Original MP_003 remains unchanged

  Original Table → [MP_001][MP_002][MP_003]    [MP_004][MP_005]
  Cloned Table  →  [MP_001][MP_002][MP_003_new][MP_004][MP_005]
  
  Only MP_003_new is additional storage cost.
```

### 12.2 Use Cases for Cloning

```sql
-- ─────────────────────────────────────────
-- USE CASE 1: Dev/Test Environment Setup
-- ─────────────────────────────────────────
-- Create a full copy of production for development
-- WITHOUT copying all the data

CREATE DATABASE dev_costco_dw
CLONE costco_dw;
-- Instant! Now dev team has their own isolated copy of production data.
-- They can run destructive tests, drop tables, modify schemas.
-- Production is completely unaffected.

-- ─────────────────────────────────────────
-- USE CASE 2: Before Risky Operations
-- ─────────────────────────────────────────
-- "Backup" before a dangerous migration

CREATE TABLE fact_ad_clicks_backup_20240115
CLONE fact_ad_clicks;

-- Run risky migration
ALTER TABLE fact_ad_clicks ADD COLUMN new_attribution_model VARCHAR;
UPDATE fact_ad_clicks SET new_attribution_model = compute_model(click_id);

-- If something goes wrong:
DROP TABLE fact_ad_clicks;
ALTER TABLE fact_ad_clicks_backup_20240115 RENAME TO fact_ad_clicks;

-- ─────────────────────────────────────────
-- USE CASE 3: CI/CD Pipeline Testing
-- ─────────────────────────────────────────
-- Create a temporary schema for each PR/build
CREATE SCHEMA pr_123_test
CLONE staging;

-- Run integration tests against this schema
-- Tests can safely modify/delete data
-- Drop when done

DROP SCHEMA pr_123_test;

-- ─────────────────────────────────────────
-- USE CASE 4: Clone with Time Travel
-- ─────────────────────────────────────────
-- Clone the table as it was before an accident

CREATE TABLE fact_ad_clicks_recovered
CLONE fact_ad_clicks
AT (TIMESTAMP => '2024-01-14 09:00:00'::TIMESTAMP_NTZ);
```

---

## 13. Streams and Tasks — CDC and Orchestration

### 13.1 Streams — Change Data Capture

A **Snowflake Stream** is an object that tracks DML changes (INSERT, UPDATE, DELETE) to a source table. It records what changed, making it easy to build incremental processing pipelines entirely within Snowflake.

```
HOW STREAMS WORK:

Source Table (fact_ad_clicks):
  Time 0: [Row A: cost=1.25] [Row B: cost=2.50] [Row C: cost=0.75]
                 │
    Stream created (offset = current)
                 │
  Time 1: INSERT [Row D: cost=3.00]
           UPDATE Row B: cost=2.75
                 │
  Time 2: Stream shows:
    ┌──────────────────────────────────────────────────────┐
    │  click_id │ cost_usd │ METADATA$ACTION │ METADATA$ISUPDATE│
    │  D        │ 3.00     │ INSERT          │ FALSE            │
    │  B        │ 2.75     │ INSERT          │ TRUE             │
    │  B        │ 2.50     │ DELETE          │ TRUE             │
    └──────────────────────────────────────────────────────┘
    
    Note: UPDATEs appear as a DELETE (old value) + INSERT (new value)
    
  Reading the stream advances the OFFSET — consumed changes are removed
  from the stream view (but underlying data is untouched)
```

```sql
-- ─────────────────────────────────────────
-- CREATING AND USING STREAMS
-- ─────────────────────────────────────────

-- Create a stream on a source table
CREATE STREAM ad_clicks_stream
ON TABLE fact_ad_clicks
APPEND_ONLY = FALSE;  -- captures INSERTs, UPDATEs, DELETEs
-- APPEND_ONLY = TRUE: captures only INSERTs (cheaper, faster for append-only tables)

-- Check if stream has data
SELECT SYSTEM$STREAM_HAS_DATA('ad_clicks_stream');  -- TRUE or FALSE

-- View stream contents (what changed since last consumed)
SELECT
    *,
    METADATA$ACTION,           -- 'INSERT' or 'DELETE'
    METADATA$ISUPDATE,         -- TRUE if this is part of an UPDATE operation
    METADATA$ROW_ID            -- unique identifier for tracking
FROM ad_clicks_stream;

-- Process the stream (consume changes into target table)
BEGIN TRANSACTION;

-- Merge stream changes into the analytics table
MERGE INTO analytics.ad_clicks_mart AS target
USING (
    -- Get the latest state of each changed row
    SELECT *,
           METADATA$ACTION,
           METADATA$ISUPDATE
    FROM ad_clicks_stream
) AS source
ON target.click_id = source.click_id
WHEN MATCHED AND source.METADATA$ACTION = 'DELETE' AND NOT source.METADATA$ISUPDATE
    THEN DELETE
WHEN MATCHED AND source.METADATA$ISUPDATE = TRUE AND source.METADATA$ACTION = 'INSERT'
    THEN UPDATE SET
        target.cost_usd = source.cost_usd,
        target.updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED AND source.METADATA$ACTION = 'INSERT'
    THEN INSERT (click_id, campaign_id, cost_usd, clicked_at, updated_at)
    VALUES (source.click_id, source.campaign_id, source.cost_usd,
            source.clicked_at, CURRENT_TIMESTAMP());

COMMIT;
-- After COMMIT: the stream offset advances (consumed changes are cleared)
```

### 13.2 Tasks — Scheduled SQL Execution

**Tasks** are Snowflake's built-in job scheduler. They execute SQL statements (including stored procedures) on a schedule or when triggered.

```sql
-- ─────────────────────────────────────────
-- CREATING TASKS
-- ─────────────────────────────────────────

-- Simple scheduled task (cron-based)
CREATE TASK refresh_campaign_mart
    WAREHOUSE = 'analytics_wh'       -- which warehouse to use for compute
    SCHEDULE = 'USING CRON 0 6 * * * UTC'  -- daily at 6 AM UTC
AS
CALL refresh_mart_stored_procedure();

-- OR: fixed interval
CREATE TASK refresh_staging
    WAREHOUSE = 'etl_wh'
    SCHEDULE = '60 MINUTE'           -- every 60 minutes
AS
INSERT INTO staging.ad_clicks
SELECT * FROM raw.ad_clicks_new;

-- Serverless task (Snowflake manages compute — no warehouse needed)
CREATE TASK refresh_mart_serverless
    USER_TASK_MANAGED_INITIAL_WAREHOUSE_SIZE = 'MEDIUM'  -- auto-managed
    SCHEDULE = 'USING CRON 0 */1 * * * UTC'   -- every hour
AS
MERGE INTO marts.campaign_performance ...;

-- ─────────────────────────────────────────
-- TASK DEPENDENCIES (Task DAGs)
-- ─────────────────────────────────────────

-- Root task: triggers the chain
CREATE TASK root_pipeline_task
    WAREHOUSE = 'etl_wh'
    SCHEDULE = 'USING CRON 0 6 * * * UTC'
AS
SELECT CURRENT_TIMESTAMP();  -- just a trigger, does nothing itself

-- Child task: runs after root completes
CREATE TASK load_staging_task
    WAREHOUSE = 'etl_wh'
    AFTER root_pipeline_task        -- depends on root_pipeline_task
AS
CALL load_staging();

CREATE TASK transform_marts_task
    WAREHOUSE = 'etl_wh'
    AFTER load_staging_task         -- depends on load_staging_task
AS
CALL transform_marts();

CREATE TASK send_alerts_task
    WAREHOUSE = 'etl_wh'
    AFTER transform_marts_task
AS
CALL send_completion_alerts();

-- Activate tasks (they start suspended by default)
ALTER TASK send_alerts_task RESUME;
ALTER TASK transform_marts_task RESUME;
ALTER TASK load_staging_task RESUME;
ALTER TASK root_pipeline_task RESUME;  -- resume root LAST

-- Monitor task runs
SELECT *
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
    SCHEDULED_TIME_RANGE_START => DATEADD('day', -1, CURRENT_TIMESTAMP())
))
ORDER BY SCHEDULED_TIME DESC;

-- ─────────────────────────────────────────
-- STREAM + TASK: Common Pattern
-- ─────────────────────────────────────────

-- Task that fires only when stream has new data
CREATE TASK process_stream_task
    WAREHOUSE = 'etl_wh'
    SCHEDULE = '5 MINUTE'           -- check every 5 minutes
    WHEN SYSTEM$STREAM_HAS_DATA('ad_clicks_stream')  -- only run if stream has data
AS
MERGE INTO analytics_mart USING ad_clicks_stream ...;
```

---

## 14. Data Sharing — Snowflake Marketplace

### 14.1 Snowflake Data Sharing — A Game-Changer

Snowflake's Data Sharing allows you to share **live data** with other Snowflake accounts — without copying the data, without moving files, and with instant revocation.

```
TRADITIONAL DATA SHARING (before Snowflake):

  Company A                          Company B
  ─────────                          ─────────
  Exports data to S3 file ─────────► Downloads from S3
  (daily batch, hours of work)       Loads into their DB
                                     Data is already stale
  Problems:
  • Latency (batch process)
  • Double storage (both pay)
  • Version mismatch
  • Security complexity

SNOWFLAKE DATA SHARING:

  Company A                          Company B
  ─────────                          ─────────
  Creates SHARE (metadata only)─────► Consumer queries via
  Points to existing tables           their own VW
  No data copy                       Reads same S3 files
                                     Always current
  Benefits:
  • Zero latency (live data)
  • Zero extra storage cost
  • Provider controls access
  • Instant revocation
  • Works across cloud regions (with replication)
```

```sql
-- ─────────────────────────────────────────
-- PROVIDER SIDE: Creating a Share
-- ─────────────────────────────────────────

-- Create a share object
CREATE SHARE campaign_performance_share
COMMENT = 'Daily campaign performance metrics for partners';

-- Add objects to the share
GRANT USAGE ON DATABASE costco_dw TO SHARE campaign_performance_share;
GRANT USAGE ON SCHEMA costco_dw.marts TO SHARE campaign_performance_share;
GRANT SELECT ON TABLE costco_dw.marts.mart_campaign_performance TO SHARE campaign_performance_share;

-- Share only specific columns (create a secure view to mask PII)
CREATE SECURE VIEW costco_dw.shared_views.partner_campaign_metrics AS
SELECT
    report_date,
    campaign_id,
    channel,
    impressions,
    clicks,
    spend_usd,
    roas
    -- Note: NO user_id, email, or member PII
FROM costco_dw.marts.mart_campaign_performance;

GRANT SELECT ON VIEW costco_dw.shared_views.partner_campaign_metrics TO SHARE campaign_performance_share;

-- Add the consumer account to the share
ALTER SHARE campaign_performance_share
ADD ACCOUNTS = 'partner_account.us-east-1.aws';  -- their Snowflake account identifier

-- ─────────────────────────────────────────
-- CONSUMER SIDE: Accessing a Share
-- ─────────────────────────────────────────

-- Create a database from the share
CREATE DATABASE costco_partner_data
FROM SHARE costco_account.campaign_performance_share;

-- Query shared data (using consumer's own warehouse)
SELECT * FROM costco_partner_data.shared_views.partner_campaign_metrics
WHERE report_date = CURRENT_DATE() - 1;
```

### 14.2 Snowflake Marketplace

Snowflake operates a **Data Marketplace** where companies publish datasets for purchase or free access. As a data engineer, you can enrich your internal data with:

- Weather data (correlate sales with weather patterns)
- Demographic data (enrich member profiles)
- Financial market data (correlate ad spend with stock prices)
- Geolocation data (postal code → demographics)

The key insight: you query this external data using Snowflake SQL, within your own environment, with no file downloads or ETL. It appears as a database you can join against your own tables.

---

## 15. Security — Roles, RBAC, Dynamic Data Masking

### 15.1 Role-Based Access Control (RBAC)

Snowflake uses a **role-based** access control model. Users don't get permissions directly — they're assigned roles, and roles have permissions.

```
SNOWFLAKE RBAC HIERARCHY:

  ACCOUNTADMIN ─── highest privilege, manage account, billing
       │
  SYSADMIN ──── create/manage databases, warehouses
       │
  SECURITYADMIN ── manage users and roles
       │
  USERADMIN ─── create/manage users
       │
  PUBLIC ──────── default role for all users (minimal permissions)
  
Additional roles YOU create:
  DATA_ENGINEER_ROLE ── read raw, write staging, manage pipelines
  ANALYST_ROLE ──────── read marts only
  BI_TOOL_ROLE ──────── read marts, cannot modify data
  ADMIN_ROLE ─────────── full access within databases they own
```

```sql
-- Create a role
CREATE ROLE data_engineer;
CREATE ROLE analyst;

-- Grant permissions to roles
GRANT USAGE ON DATABASE costco_dw TO ROLE data_engineer;
GRANT USAGE ON SCHEMA costco_dw.raw TO ROLE data_engineer;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA costco_dw.raw TO ROLE data_engineer;
GRANT USAGE ON WAREHOUSE etl_wh TO ROLE data_engineer;

GRANT USAGE ON DATABASE costco_dw TO ROLE analyst;
GRANT USAGE ON SCHEMA costco_dw.marts TO ROLE analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA costco_dw.marts TO ROLE analyst;
GRANT USAGE ON WAREHOUSE analytics_wh TO ROLE analyst;

-- Grant roles to users
GRANT ROLE data_engineer TO USER viraaj_sivaraju;
GRANT ROLE analyst TO USER john_analyst;

-- Role inheritance: create hierarchy
GRANT ROLE analyst TO ROLE data_engineer;
-- Now data_engineer inherits analyst privileges

-- Activate a role in session
USE ROLE data_engineer;

-- Future grants (automatically grant to new objects)
GRANT SELECT ON FUTURE TABLES IN SCHEMA costco_dw.marts TO ROLE analyst;
-- Any new table created in marts schema automatically grants SELECT to analyst
```

### 15.2 Dynamic Data Masking

Dynamic Data Masking applies masking policies to columns. The actual data in the column is unchanged, but certain roles see masked values.

```sql
-- Create a masking policy
CREATE MASKING POLICY email_mask AS
    (val VARCHAR) RETURNS VARCHAR ->
    CASE
        WHEN CURRENT_ROLE() IN ('ADMIN', 'DATA_ENGINEER') THEN val  -- see real value
        WHEN CURRENT_ROLE() = 'ANALYST' THEN CONCAT('***@', SPLIT_PART(val, '@', 2))  -- partial mask
        ELSE '***REDACTED***'                                                           -- full mask
    END;

-- Apply masking policy to a column
ALTER TABLE dim_members
MODIFY COLUMN email
SET MASKING POLICY email_mask;

-- Test: what analysts see
USE ROLE analyst;
SELECT email FROM dim_members LIMIT 3;
-- Result: ***@gmail.com, ***@yahoo.com, ***@hotmail.com (domain visible, local part masked)

-- Test: what engineers see
USE ROLE data_engineer;
SELECT email FROM dim_members LIMIT 3;
-- Result: john.doe@gmail.com, jane.smith@yahoo.com (full email visible)

-- Row Access Policies (Row-Level Security)
CREATE ROW ACCESS POLICY region_policy AS
    (region_col VARCHAR) RETURNS BOOLEAN ->
    CASE
        WHEN CURRENT_ROLE() = 'US_ANALYST' THEN region_col = 'US'
        WHEN CURRENT_ROLE() = 'EU_ANALYST' THEN region_col = 'EU'
        WHEN CURRENT_ROLE() IN ('ADMIN', 'DATA_ENGINEER') THEN TRUE  -- see all
        ELSE FALSE
    END;

ALTER TABLE dim_members
ADD ROW ACCESS POLICY region_policy ON (region);
-- US_ANALYST now sees only US rows — automatically, transparently
```

### 15.3 Network Policies and Private Connectivity

```sql
-- Restrict Snowflake access to specific IP ranges
CREATE NETWORK POLICY corporate_only
ALLOWED_IP_LIST = ('192.168.1.0/24', '10.0.0.0/8')
BLOCKED_IP_LIST = ();

-- Apply to specific user
ALTER USER viraaj_sivaraju
SET NETWORK_POLICY = corporate_only;

-- Apply account-wide
ALTER ACCOUNT SET NETWORK_POLICY = corporate_only;

-- Private Link: connect without going over public internet
-- AWS PrivateLink / Azure Private Link / GCP Private Service Connect
-- Traffic stays within cloud provider's network — never touches public internet
```

---

## 16. Cost Management and Optimization

### 16.1 Snowflake's Pricing Model

Snowflake charges for three things:

```
COMPUTE COSTS (Virtual Warehouses):
  • Billed per second while running
  • Minimum 60 seconds per query
  • Rates: ~$0.40/credit (Standard), ~$0.70/credit (Enterprise)
  • 1 credit = 1 hour of X-Small warehouse
  • Larger warehouses use more credits per hour

STORAGE COSTS:
  • $23/TB/month (on-demand) or $40/TB/month (on-demand, higher rates apply)
  • More precisely: billed per byte, per day
  • Includes: active data + Time Travel data + Fail-Safe data

CLOUD SERVICES COSTS:
  • Activities that use Cloud Services Layer
  • Generally free up to 10% of daily compute credits
  • Excess billed at ~$0.70/credit

DATA TRANSFER COSTS:
  • Transferring data OUT of Snowflake (egress) to different regions/clouds
  • Typically ~$0.08/GB
```

### 16.2 Cost Monitoring

```sql
-- Monitor credit usage by warehouse
SELECT
    warehouse_name,
    SUM(credits_used)           AS total_credits,
    SUM(credits_used) * 0.40    AS estimated_cost_usd,  -- adjust per your rate
    COUNT(DISTINCT DATE_TRUNC('day', start_time)) AS active_days,
    AVG(credits_used)           AS avg_daily_credits
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE start_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
GROUP BY warehouse_name
ORDER BY total_credits DESC;

-- Find expensive queries (top compute consumers)
SELECT
    query_id,
    LEFT(query_text, 100) AS query_preview,
    warehouse_name,
    execution_time / 1000 AS execution_seconds,
    bytes_scanned / 1e9   AS gb_scanned,
    credits_used_cloud_services
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE start_time >= DATEADD('day', -7, CURRENT_TIMESTAMP())
  AND execution_status = 'SUCCESS'
ORDER BY execution_time DESC
LIMIT 50;

-- Storage costs breakdown
SELECT
    TABLE_SCHEMA,
    TABLE_NAME,
    ACTIVE_BYTES / 1e9              AS active_gb,
    TIME_TRAVEL_BYTES / 1e9        AS time_travel_gb,
    FAILSAFE_BYTES / 1e9           AS failsafe_gb,
    (ACTIVE_BYTES + TIME_TRAVEL_BYTES + FAILSAFE_BYTES) / 1e9 AS total_gb
FROM SNOWFLAKE.ACCOUNT_USAGE.TABLE_STORAGE_METRICS
WHERE DELETED = FALSE
ORDER BY total_gb DESC
LIMIT 20;
```

### 16.3 Cost Optimization Strategies

**Strategy 1: Right-size warehouses**

```
The most common waste: oversized warehouses for workloads that don't need them.

Test: does my query get faster with a larger warehouse?
- Run the same query on X-Small, Small, Medium, Large
- If X-Small and Large take the same time: query is single-threaded → don't overpay
- If Large is 4x faster: query parallelizes well → size matters

Typical sweet spots:
  DBT transformations (parallelizable SQL): Medium or Large
  Dashboards (simple aggregations): Small or Medium
  ETL loading (COPY INTO): Medium (limited parallelism)
  Data science (complex analytics): X-Large or 2X-Large
  
Automatic warehouse scaling (via Snowflake Resource Monitor):
  Set credit limits per warehouse per day/week/month
  Get alerts before hitting limits
  Auto-suspend or terminate when limit reached
```

**Strategy 2: Maximize partition pruning**

```sql
-- Add clustering keys to frequently filtered columns
-- A well-clustered table can reduce scans by 90-99%
ALTER TABLE fact_ad_clicks CLUSTER BY (click_date, campaign_id);

-- Use date ranges instead of functions on date columns
-- BAD: prevents pruning
WHERE YEAR(click_date) = 2024

-- GOOD: enables pruning
WHERE click_date >= '2024-01-01' AND click_date < '2025-01-01'
```

**Strategy 3: Reduce Time Travel retention on staging tables**

```sql
-- Staging tables that can be recreated don't need long Time Travel
ALTER TABLE raw.staging_ad_clicks
SET DATA_RETENTION_TIME_IN_DAYS = 1;  -- not 7 or 90 days

-- Even better: use TRANSIENT tables (no Fail-Safe = no extra storage cost)
CREATE TRANSIENT TABLE raw.staging_ad_clicks (...);
```

**Strategy 4: Use result cache aggressively**

```
Result cache stores query results for 24 hours.
Identical query = zero compute cost (uses cached result).

Conditions for result cache hit:
1. Same query text (including whitespace and case)
2. Same user role
3. Underlying data hasn't changed
4. Query was run within last 24 hours

BI dashboard tip: 
  Looker/Tableau often re-run same queries for multiple users.
  Result cache means the 2nd-100th user pays nothing for compute.
  First user pays; everyone else is free.
```

---

## 17. Snowflake vs BigQuery — Deep Comparison

This is a question you WILL get asked. Know it cold.

### 17.1 Architecture Differences

```
BIGQUERY:
  • Truly serverless — you never choose compute size
  • Google manages all compute allocation automatically
  • You pay per TB scanned (on-demand) OR flat monthly slots (reservations)
  • Compute is invisible to the user
  • Best for: spiky, unpredictable workloads; you don't want to manage infrastructure

SNOWFLAKE:
  • You manage Virtual Warehouses (choose size, auto-suspend settings)
  • More control, more responsibility
  • You pay per second of warehouse usage
  • Best for: predictable workloads; you want control over compute; multi-cloud
```

### 17.2 Feature Comparison

| Feature | Snowflake | BigQuery | Advantage |
|---------|-----------|---------|-----------|
| **Compute model** | User-managed VWs | Fully serverless | BigQuery (simpler) |
| **Multi-cloud** | AWS + Azure + GCP | GCP only | Snowflake |
| **Semi-structured** | VARIANT type | JSON natively | Tie |
| **Time Travel** | Up to 90 days | 7 days | Snowflake |
| **Zero-copy clone** | Yes, instant | No | Snowflake |
| **Data sharing** | Native, live | Analytics Hub | Tie |
| **CDC (streams)** | Native streams + tasks | Not native (use Dataflow) | Snowflake |
| **Concurrency** | Multi-cluster VWs | Auto-managed | Tie |
| **Geospatial** | Limited | Native ST_ functions | BigQuery |
| **ML in SQL** | Snowpark ML | BigQuery ML | Tie |
| **Python/Java in DB** | Snowpark | Not native | Snowflake |
| **Cost for large scans** | Always pays (VW running) | Pays per TB scanned | Depends |
| **Cost for many small queries** | Efficient (small VW) | Efficient (per TB) | Depends |
| **GCP integration** | Via connectors | Native | BigQuery |
| **Maturity** | Very mature | Very mature | Tie |

### 17.3 When to Choose Each

```
CHOOSE SNOWFLAKE WHEN:
  ✓ Multi-cloud strategy (can't commit to one cloud provider)
  ✓ Heavy mixed workloads (ETL + Analytics + Data Science simultaneously)
  ✓ You need Time Travel > 7 days
  ✓ CDC and streaming pipelines entirely within the warehouse (Streams + Tasks)
  ✓ Zero-copy cloning is important (dev/test environments)
  ✓ Your team wants warehouse-level cost control and isolation
  ✓ You're already in a company using Snowflake ecosystem

CHOOSE BIGQUERY WHEN:
  ✓ Google Cloud is your primary/only cloud
  ✓ GCP-native stack (Dataflow, Cloud Composer, Looker, Vertex AI)
  ✓ Truly serverless — no infrastructure thinking at all
  ✓ Geospatial analytics (GEOGRAPHY type is exceptional)
  ✓ Large infrequent ad hoc queries (per-TB pricing is fair)
  ✓ Cost predictability via flat-rate slot reservations

REAL WORLD:
  Many large enterprises use BOTH:
  • One cloud team uses Snowflake on AWS
  • Another team uses BigQuery on GCP
  • Data is replicated between them for different use cases
```

---

## 18. Snowflake in Data Engineering Pipelines

### 18.1 DBT + Snowflake (The Dominant Pattern)

DBT is the most common transformation tool on top of Snowflake. The combination is sometimes called the "Modern Data Stack."

```sql
-- DBT profiles.yml for Snowflake
costco_martech:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: costco.us-east-1.aws       # your account identifier
      user: dbt_user
      private_key_path: /secrets/dbt_rsa_key.pem
      role: data_engineer
      database: costco_dw
      warehouse: dbt_wh                   # dedicated DBT warehouse
      schema: dbt_viraaj                  # personal dev schema
      threads: 8                          # parallel model execution
      client_session_keep_alive: false

    prod:
      type: snowflake
      account: costco.us-east-1.aws
      user: dbt_prod_sa
      private_key_path: /secrets/prod_rsa_key.pem
      role: data_engineer
      database: costco_dw
      warehouse: dbt_prod_wh
      schema: marts
      threads: 16
```

### 18.2 Snowflake + Fivetran Pattern

```
Source Systems (Salesforce, HubSpot, Google Ads, MySQL, Postgres)
    │
    ▼
Fivetran (managed ELT connectors)
    │  Handles: schema changes, incremental loads, retries, monitoring
    ▼
Snowflake Raw Schema
  (tables like: salesforce_contacts, google_ads_clicks, mysql_orders)
    │
    ▼
DBT on Snowflake (T in ELT)
  Staging → Intermediate → Marts
    │
    ▼
BI Tools (Tableau, Looker, Mode)
```

### 18.3 Snowflake + Kafka (Real-Time Ingestion)

```
For real-time event ingestion from Kafka topics into Snowflake:

Kafka Topic (ad_events) 
    │
    ▼
Kafka Connector for Snowflake
(Snowflake provides an official connector)
    │
    ▼
Snowflake Staging Table (raw_ad_events)
  - Data arrives in seconds to minutes (micro-batch)
  - Connector uses Snowpipe internally
    │
    ▼
Snowflake Stream (detects new rows)
    │
    ▼
Snowflake Task (runs every 5 minutes if stream has data)
    │
    ▼
MERGE into clean analytics table
```

---

## 19. Interview Questions — Easy to Very Hard

### EASY

**Q1: What makes Snowflake different from a traditional data warehouse?**

**Answer**: Three things. First, separation of storage and compute — your data lives in cloud object storage (S3/Azure/GCS) independently of the compute clusters (Virtual Warehouses) that query it. You can have multiple warehouses all reading the same data simultaneously. Second, it's fully managed SaaS — no infrastructure to manage, automatic patching, scaling, and backups. Third, pay-per-second elasticity — you only pay for compute while it's actually running, and you can scale from one node to 128 nodes in seconds.

---

**Q2: What is a Virtual Warehouse in Snowflake and how is it different from a traditional compute cluster?**

**Answer**: A Virtual Warehouse is a named cluster of compute resources (EC2 instances) in Snowflake that executes SQL queries. The key differences from traditional clusters: (1) It can be created in seconds and destroyed in seconds — it's ephemeral, not permanent infrastructure. (2) It auto-suspends when idle and auto-resumes when a query arrives — you pay nothing when it's not running. (3) Multiple warehouses can read the same data simultaneously without any conflict — they're fully isolated from each other. (4) You can instantly resize it (more powerful) or scale it out (multi-cluster for concurrency) without downtime.

---

### MEDIUM

**Q3: Explain Snowflake's Time Travel feature. What is it, how does it work, and when would you use it?**

**Answer**: Time Travel allows you to query data as it was at any point in the past — up to 1 day on Standard edition, up to 90 days on Enterprise. It works by preserving the micro-partition files that would normally be deleted after a DML operation. When you DELETE or UPDATE rows, Snowflake writes new micro-partitions but retains the old ones (marked as historical). The metadata system tracks which files belong to which point in time.

You use it with AT or BEFORE clauses: `SELECT * FROM table AT (TIMESTAMP => '2024-01-14 10:00:00')` or `SELECT * FROM table BEFORE (STATEMENT => 'query_id_of_the_delete')`.

Use cases: recovering from accidental deletes or updates, auditing data changes, comparing current data to historical snapshots, building slowly changing dimensions that track historical state.

After the Time Travel period expires, data enters Fail-Safe for 7 days — accessible only by Snowflake support for emergency recovery.

---

**Q4: What is a Snowflake Stream and how would you use it to build a CDC pipeline?**

**Answer**: A Stream is an object that tracks DML changes (INSERT, UPDATE, DELETE) to a source table. It works like an offset-based changelog: it records what changed since the last time the stream was consumed. Each row in a stream has metadata columns: METADATA$ACTION (INSERT or DELETE), METADATA$ISUPDATE (TRUE if part of an UPDATE), and METADATA$ROW_ID.

To build a CDC pipeline: create a stream on the source table with `CREATE STREAM my_stream ON TABLE source_table`. Then create a Task that runs on a schedule and fires only when the stream has data: `WHEN SYSTEM$STREAM_HAS_DATA('my_stream')`. The task runs a MERGE statement that processes the stream's changes into a target table — INSERT for new rows, UPDATE for changed rows, DELETE for removed rows.

Important: UPDATE operations appear in the stream as two rows — a DELETE row (old values) and an INSERT row (new values). The METADATA$ISUPDATE flag on both rows is TRUE, distinguishing them from actual INSERTs and DELETEs.

---

### HARD

**Q5: A query that runs against a 5TB table in Snowflake takes 10 minutes. The query scans 100% of all micro-partitions. Walk me through how you would diagnose and optimize it.**

**Answer**:

**Step 1: Diagnose via Query Profile**
In the Snowflake UI, open Query History → find the query → View Profile. Check:
- Partitions scanned vs partitions total: if 100% scanned, partition pruning is completely failing
- Bytes spilled to disk: indicates the warehouse is too small for this operation
- The operator with the most time: is it a full table scan? A large join? A sort?

**Step 2: Check clustering health**
```sql
SELECT SYSTEM$CLUSTERING_INFORMATION('my_big_table', '(my_filter_column)');
```
If `average_depth` is very high (>> 1), the table has poor clustering. The query's WHERE clause column values are spread across all micro-partitions with overlapping ranges, so no partitions can be skipped.

**Step 3: Fix clustering**
```sql
ALTER TABLE my_big_table CLUSTER BY (most_common_filter_column, second_most_common);
```
After clustering: re-run the query. Partitions scanned should drop dramatically.

**Step 4: Check the WHERE clause**
Is there a function on the filter column? `YEAR(click_date) = 2024` prevents pruning because Snowflake can't use min/max metadata to evaluate a function. Replace with `click_date >= '2024-01-01' AND click_date < '2025-01-01'`.

**Step 5: Check for disk spill**
If bytes_spilled > 0 and the query involves a large join or aggregation, the warehouse is too small for the working set. Scale up one size (e.g., Large → X-Large) and re-run.

**Step 6: Check query logic**
Is a DISTINCT or large join creating an unnecessarily large working set? Can pre-filtering before the join reduce data volume? Can a large aggregation be split into a two-step process (pre-aggregate by day, then by month) instead of aggregating billions of rows at once?

---

### VERY HARD

**Q6: Design a Snowflake-based data platform for a retail company with these requirements: 50 data sources, 200 concurrent BI users, sub-5-second dashboard query SLA, 30-day data retention for compliance, GDPR right-to-erasure capability, and $50K/month budget. Walk through every architectural decision.**

**Answer**:

**Layer 1: Ingestion**

50 sources divided into categories:
- SaaS tools (Salesforce, HubSpot, Google Ads, Meta Ads → Fivetran; pre-built connectors, handles schema changes automatically)
- Internal databases (MySQL, Postgres → Debezium CDC → Kafka → Kafka Connector for Snowflake; near-real-time with full change tracking)
- Files (S3 drops → Snowpipe for automated ingestion)
- APIs (custom Python pipelines writing to internal stages via COPY INTO)

Landing zone: a `RAW` database with one schema per source. All tables are TRANSIENT (no Fail-Safe, cheapest storage) since raw data can be re-ingested.

**Layer 2: Transformation (DBT)**

Three schema layers:
- STAGING: 1:1 with raw sources, clean/rename/cast only, TRANSIENT tables
- INTERMEDIATE: business logic, joins, attribution; TRANSIENT
- MARTS: final analytics-ready tables, PERMANENT, 30-day Time Travel for compliance

Virtual Warehouse for DBT: dedicated Medium warehouse (`DBT_WH`) with `AUTO_SUSPEND = 60` seconds — runs for the duration of the DBT job then suspends.

**Layer 3: Serving (200 Concurrent Users)**

200 concurrent users require a Multi-Cluster Warehouse. Configuration:
```sql
CREATE WAREHOUSE analytics_wh
    WAREHOUSE_SIZE = 'MEDIUM'
    MIN_CLUSTER_COUNT = 2     -- always 2 clusters running (handles baseline load)
    MAX_CLUSTER_COUNT = 8     -- auto-scale up to 8 clusters for peaks
    SCALING_POLICY = 'ECONOMY'  -- prefers fewer clusters (vs STANDARD which is faster)
    AUTO_SUSPEND = 300;
```

For sub-5-second dashboard SLA: pre-aggregated mart tables clustered by common filter columns (report_date, channel, campaign_id). Looker's PDT (Persistent Derived Tables) can pre-compute heavy aggregations. Snowflake's Result Cache handles repeated identical queries for zero cost.

**GDPR Right-to-Erasure**: 

Since raw data in Fivetran tables can be re-ingested, we pseudonymize at the staging layer — member PII (email, phone, name) is hashed using SHA256 before entering the mart layer. Only member_id (opaque) flows into marts. For erasure requests: delete from the dim_members table (one row), purge from raw layer. All mart data automatically becomes PII-free because it only contains the member_id hash.

For data that truly requires hard deletion: use Snowflake's `DELETE WHERE member_id = 'X'` across all relevant tables. Track erasure requests in a compliance log table.

**30-day Compliance Retention**:
```sql
ALTER TABLE marts.fact_transactions SET DATA_RETENTION_TIME_IN_DAYS = 30;
-- Allows querying "as of 30 days ago" for compliance audits
```

**Cost estimation ($50K/month budget)**:
- DBT warehouse (Medium, 2 hours/day): ~2 credits/day × 30 = 60 credits × $0.40 = $24/month
- Analytics warehouse (2×Medium baseline, bursts to 8): avg ~10 credits/day × 30 = 300 × $0.40 = $120/month
- Fivetran: ~$15,000/month (50 connectors × $300/month avg)
- Storage (500GB marts + 2TB raw + 30-day TT): ~$150/month
- Snowpipe/Serverless: ~$100/month
- **Total: ~$15,394/month** — well under $50K budget
- Remaining $34K can fund: Enterprise edition features (90-day TT, multi-cluster), support, additional sources

---

## Summary: Snowflake Expert Reference Card

```
ARCHITECTURE:
  3 Layers: Storage (S3/Azure/GCS) | Compute (VWs) | Cloud Services (brain)
  Key property: storage and compute are completely independent

STORAGE:
  Micro-partitions: 50-500MB, columnar, compressed
  Metadata: min/max per column per partition → partition pruning
  Clustering keys: organize partitions to maximize pruning

COMPUTE:
  Virtual Warehouses: XS to 4XL, billed per second
  Multi-cluster: handles concurrency, auto-scales
  Cache: result cache (24h, free) → local SSD (VW lifetime) → S3

TIME TRAVEL:
  Standard: 0-1 day | Enterprise: 0-90 days
  AT/BEFORE clause | UNDROP | Clone at past timestamp
  Fail-Safe: 7 days after TT (Snowflake support only)

CLONING:
  Zero-copy, instant | Copy-on-write | Use for dev/test/CI

CDC:
  Streams track DML changes | METADATA$ACTION, METADATA$ISUPDATE
  Tasks schedule processing | WHEN SYSTEM$STREAM_HAS_DATA()

SEMI-STRUCTURED:
  VARIANT type | colon notation (payload:field::TYPE)
  LATERAL FLATTEN to explode arrays/objects

SECURITY:
  RBAC: roles → permissions, users → roles
  Dynamic Data Masking: per-column, per-role masking policies
  Row Access Policies: row-level filtering by role

COST:
  Compute: per second | Storage: per TB/month
  Optimization: right-size VW, clustering keys, result cache, transient tables

VS BIGQUERY:
  SF wins: multi-cloud, 90d TT, cloning, CDC, warehouse control
  BQ wins: fully serverless, GCP native, per-TB pricing, geospatial
```
