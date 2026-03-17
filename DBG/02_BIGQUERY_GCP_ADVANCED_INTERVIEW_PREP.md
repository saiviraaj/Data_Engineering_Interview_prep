# BigQuery & GCP Advanced Interview Preparation
## Deutsche Börse Group - Principal Data Engineer

**Author**: Prepared for Principal Data Engineer Interview  
**Experience Level**: 10+ years GCP/BigQuery expertise  
**Focus**: Production-scale warehouse design, cost optimization, and financial data patterns

---

## Table of Contents

1. [BigQuery Architecture & Fundamentals](#bigquery-architecture--fundamentals)
2. [Query Optimization & Cost Control](#query-optimization--cost-control)
3. [Partitioning & Clustering Strategy](#partitioning--clustering-strategy)
4. [Advanced SQL Patterns](#advanced-sql-patterns)
5. [Real-Time Data Ingestion](#real-time-data-ingestion)
6. [Security & Governance](#security--governance)
7. [GCP Ecosystem Integration](#gcp-ecosystem-integration)
8. [Production Patterns](#production-patterns)

---

## BigQuery Architecture & Fundamentals

### Q1: BigQuery Architecture - Dremel, Colossus, Jupiter

**Question**: Explain BigQuery's three-layer architecture and how it enables sub-second queries on petabyte-scale data.

**Answer**:

**Three-Layer Architecture**:

**1. Dremel (Query Engine)**:
- Massively parallel query processing engine
- Breaks queries into stages
- Uses tree-like architecture for data aggregation
- Fast aggregation across millions of machines

```
┌─────────────────────────────────────────┐
│      Dremel Query Engine                │
│  (Processes billions of rows in seconds)│
└─────────────────────────────────────────┘
         ↓         ↓         ↓
    Mixer Nodes (aggregate partial results)
    /    |    \
  Leaf Leaf Leaf  (scan columns in parallel)
```

**Key feature**: Columnar storage + tree aggregation = fast queries

**2. Colossus (Storage Layer)**:
- Google's distributed file system
- Stores data in columnar format (not row-based)
- Replicates across data centers for fault tolerance
- Compression: 10x-20x reduction

```
Data Layout in Colossus:
Tables stored by column:
- column_user_id (billions of values compressed)
- column_amount (billions of values compressed)
- column_date (billions of values compressed)

Only scan needed columns! Not entire rows.
Example: SELECT user_id, amount FROM sales
- Reads 2 columns (user_id, amount) 
- Ignores 50 other columns
```

**3. Jupiter (Network)**:
- Google's internal high-speed network
- Petabit-scale bisection bandwidth
- No bottlenecks between servers
- Enables fast inter-machine communication

```
Enables:
- 1TB scan → 5 seconds (200GB/second throughput per query)
- Parallel shuffle of 100GB across 1000 machines
```

**Why This Architecture Matters**:

```python
# Traditional Data Warehouse (row-based):
# User_ID | Amount | Date   | Product | ... (50 more columns)
# 1       | 100    | 1/1/24 | ABC     |
# 2       | 200    | 1/1/24 | XYZ     |
# SELECT user_id, amount FROM sales WHERE date = 1/1/24
# - Reads all 50+ columns (expensive)
# - Then filters (wasteful)

# BigQuery (column-based):
# user_id: [1, 2, 3, ...]
# amount: [100, 200, 300, ...]
# date: [1/1, 1/1, 1/1, ...]
# SELECT user_id, amount FROM sales WHERE date = 1/1/24
# - Reads only 2 columns + date filter
# - 98% less data scanned!
```

**Real Performance Impact**:

```sql
-- Traditional warehouse: 2 minutes
SELECT user_id, SUM(amount) 
FROM sales 
WHERE date = CURRENT_DATE()
GROUP BY user_id;

-- BigQuery: 1-2 seconds (same query)
-- Why: 
-- 1. Only read date & user_id & amount columns (not other 50)
-- 2. Columnar compression reduces IO 10x
-- 3. Dremel parallelizes across 10,000+ machines
-- 4. Jupiter network doesn't bottleneck
```

**Serverless Nature**:
- No clusters to manage
- Automatic scaling (1 to 100,000 workers)
- Pay per query (not per hour)
- No warm-up time

---

### Q2: BigQuery as Serverless - Implications for Architects

**Question**: Explain BigQuery's serverless model and how it changes data warehouse design vs. traditional Hadoop/Spark clusters.

**Answer**:

**Serverless vs. Managed Cluster**:

| Aspect | BigQuery (Serverless) | Spark Cluster (Traditional) |
|--------|-------|---------|
| **Setup** | Instant, no infra | Weeks to months |
| **Scaling** | Automatic, per-query | Manual, cluster-wide |
| **Cost** | Per-byte-scanned | Per-hour (reserved) |
| **Failure** | Auto-retry, transparent | Manual recovery |
| **Performance** | Predictable | Depends on cluster health |

**Design Implications**:

**1. No Cluster Tuning Needed**:
```sql
-- Spark: Spent 2 weeks tuning executor memory, partitions
-- BigQuery: Write query, runs optimally
SELECT COUNT(*) FROM billion_row_table;
-- Takes same time regardless of query complexity
```

**2. Cost Structure Differs**:
```python
# Spark (hourly pricing):
# Cluster: 10 executors × 4GB × $0.3/hour = $1.20/hour
# Running 8 hours/day = $9.60/day = $300/month
# Even if idle

# BigQuery (per-byte scanned):
# Query scans 100GB @ $6.25/TB = $0.625
# Run 100 queries/day = $62.50/day = ~$2000/month
# But WITH slot reservations: $2000/month flat for unlimited queries

# Implication: Design for query efficiency, not cluster size
```

**3. Slot Reservations - New Concept**:
```python
# On-demand (default):
# Pay $6.25 per TB scanned
# Unlimited concurrent queries (queued if busy)

# Slot-based (reserved):
# Buy "slots" = concurrent compute units
# 100 slots = $2000/month
# Scan unlimited data, all goes to reserved slots
# Cost-effective for >4-5 PB scanned/month
```

**4. Design for Scan Efficiency**:
```sql
-- BAD: Full scan every time
SELECT * FROM events;  -- Scans all 10 billion rows

-- GOOD: Filter first
SELECT * FROM events WHERE date = CURRENT_DATE();  -- Scans ~100M rows

-- BETTER: Use partitioning
-- Partition by date, only read needed date
SELECT * FROM events WHERE date = CURRENT_DATE();  -- Scans 1 partition
```

**5. No Pre-Aggregation Needed** (Unlike Spark):
```sql
-- Spark: Aggregate before storing to reduce size
-- Then query aggregate table

-- BigQuery: Store raw data, query raw data
-- Fast queries on raw data mean no need for aggregates
-- Simpler data model!

SELECT 
    date,
    account_id,
    SUM(amount) as total
FROM trades_raw  -- 100 billion rows, stored raw
WHERE date = CURRENT_DATE()
GROUP BY date, account_id;
-- Still sub-second, costs same as pre-aggregated version
```

**6. Materialized Views - Not Always Needed**:
```sql
-- Spark design: Heavy use of materialized views
-- pre-aggregate, store, query aggregate

-- BigQuery design: Query raw data directly
-- Faster than querying aggregate if Dremel can parallelize

-- Use materialized views only for:
-- - Complex transformations needed by many queries
-- - Real-time dashboards where freshness < 1 second
-- - Cross-organization reporting
```

**Architectural Decision Tree**:

```
Need fast analytics?
├─ Yes, data < 100GB
│  └─ Use BigQuery directly (simple, fast)
├─ Yes, data < 1TB
│  └─ Use BigQuery with partitioning (still simple)
├─ Yes, data < 10TB
│  └─ Use BigQuery with partitioning + clustering
├─ Yes, data > 10TB
│  └─ Use BigQuery with slots (reserve compute)
│
Need real-time streaming?
├─ Yes, latency < 1 second
│  └─ Use BigQuery Streaming Insert + Pub/Sub
├─ Yes, latency 1-5 seconds
│  └─ Use Cloud Dataflow (Beam) + BigQuery
│
Need complex ML?
├─ Yes, batch
│  └─ Use BigQuery ML or Vertex AI
├─ Yes, real-time
│  └─ Use Vertex AI Prediction
```

---

## Query Optimization & Cost Control

### Q3: Query Optimization - Reducing Data Scanned

**Question**: A query scans 500GB and costs $3. Rewrite to scan < 50GB without changing results.

**Original Query**:
```sql
SELECT 
    trader_id,
    SUM(notional_value) as total_notional,
    COUNT(*) as trade_count
FROM trades
WHERE trader_id IN (
    SELECT trader_id 
    FROM traders 
    WHERE department = 'EQUITY_DESK'
)
GROUP BY trader_id;
```

**Analysis**:
```
Current execution:
1. Scan entire trades table (500GB) → all trades
2. For each row, check if trader_id in subquery
3. Subquery scans entire traders table
4. Inefficient!
```

**Optimized Query #1: Join Instead of IN**:

```sql
SELECT 
    t.trader_id,
    SUM(tr.notional_value) as total_notional,
    COUNT(*) as trade_count
FROM trades tr
INNER JOIN (
    SELECT DISTINCT trader_id 
    FROM traders 
    WHERE department = 'EQUITY_DESK'
) t USING (trader_id)
GROUP BY t.trader_id;

-- Better: Reduces to ~10GB (only EQUITY_DESK trades)
-- Cost: $0.06
```

**Optimized Query #2: Pre-Filter First**:

```sql
-- If trades table is partitioned by trader_id or date:
WITH active_traders AS (
    SELECT trader_id 
    FROM traders 
    WHERE department = 'EQUITY_DESK'
)
SELECT 
    tr.trader_id,
    SUM(tr.notional_value) as total_notional,
    COUNT(*) as trade_count
FROM trades tr
WHERE tr.trader_id IN (SELECT trader_id FROM active_traders)
  AND tr.trade_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY tr.trader_id;

-- Cost: ~$0.02 (filters to recent data + specific traders)
```

**Optimized Query #3: Add Partitioning/Clustering**:

```sql
-- If trades table is:
-- PARTITIONED BY trade_date
-- CLUSTERED BY trader_id

SELECT 
    tr.trader_id,
    SUM(tr.notional_value) as total_notional,
    COUNT(*) as trade_count
FROM `project.dataset.trades`  -- Partitioned by date, clustered by trader
WHERE trade_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND trader_id IN (
    SELECT trader_id 
    FROM traders 
    WHERE department = 'EQUITY_DESK'
  )
GROUP BY tr.trader_id;

-- Cost: ~$0.01 (30 days data + clustering prunes blocks)
```

**Key Optimization Techniques**:

**1. Predicate Pushdown**:
```sql
-- SLOW: Reads entire table, filters later
SELECT * FROM trades WHERE amount > 1000;

-- FAST: Pushes filter to storage layer
-- Parquet/BigQuery columnar format filters at read time
SELECT * FROM trades WHERE amount > 1000;
-- Same SQL, but BQ recognizes column filter and applies at scan
```

**2. Column Selection (Not SELECT *)**:
```sql
-- SLOW: 500GB (all columns)
SELECT * FROM trades;

-- FAST: 50GB (2 columns)
SELECT trader_id, amount FROM trades;

-- BigQuery charges per byte SCANNED, not returned
-- So selecting fewer columns = lower cost
```

**3. Partition Pruning**:
```sql
-- SLOW: 500GB (scans all 5 years of data)
SELECT * FROM trades;

-- FAST: 20GB (scans 1 month)
SELECT * FROM trades WHERE trade_date >= '2024-01-01';

-- IF trades is partitioned by date, this prunes 98% of data
```

**4. Clustering for Fine-Grained Filtering**:
```sql
-- SLOW: Scans entire partition
SELECT * FROM trades 
WHERE trade_date = '2024-01-15'  -- 10GB partition
  AND trader_id = 'T123';         -- Scans entire partition to find T123

-- FAST: Clustering prunes blocks
-- IF trades is clustered by trader_id:
SELECT * FROM trades 
WHERE trade_date = '2024-01-15'
  AND trader_id = 'T123';
-- Only reads blocks containing trader T123 (~100MB, not 10GB)
```

**5. Approximate Aggregations**:
```sql
-- Exact count: 10GB scanned
SELECT COUNT(DISTINCT trader_id) FROM trades WHERE trade_date >= '2024-01-01';

-- Approximate count: 10GB scanned, but faster aggregation
SELECT APPROX_COUNT_DISTINCT(trader_id) FROM trades WHERE trade_date >= '2024-01-01';
-- Within 1% of true value, but queries faster
```

**Cost Optimization Pattern**:

```python
# Before optimization
# Query cost: $5.00 (scans 800GB)
# Runs 100 times/day = $500/day

# After optimization
# Query cost: $0.05 (scans 8GB) → 100x reduction
# Runs 100 times/day = $5/day

# Annual savings: $180,000 for single query!
```

---

### Q4: Slots vs On-Demand Pricing - Decision Matrix

**Question**: When would you recommend slot reservations vs on-demand pricing for Deutsche Börse's data pipeline?

**Answer**:

**Pricing Models**:

```
On-Demand:
- $6.25 per TB scanned
- No commitment
- Unlimited concurrency (queued if peak)

Slot Reservation:
- 100 slots = $2000/month
- Commit monthly or annual
- 1 slot = ability to scan 100GB in parallel
```

**Cost Comparison**:

```
PB/Month Scanned | On-Demand Cost | Slot Cost | Better Option
0.1              | $625           | $2000     | On-Demand
0.5              | $3125          | $2000     | Slots
1.0              | $6250          | $2000     | Slots
2.0              | $12500         | $2000     | Slots
5.0              | $31250         | $2000     | Slots
```

**Rule of Thumb**:
- If monthly scan > 320 GB → Slots become cheaper
- Typically slots break even at 300-400 GB/month

**For Deutsche Börse (Financial Institution)**:

```
Estimated data volume:
- Market data: 50GB/day
- Trade execution: 20GB/day  
- Risk analytics: 30GB/day
- Historical archives: 10GB/day
- Total: ~110GB/day × 30 = 3300GB/month

On-demand cost: 3300 × $6.25 / 1024 = $20,166/month
Slot cost: $2000/month (100 slots)

Recommendation: SLOTS (10x cheaper!)
```

**Slot Reservation Decisions**:

**100 slots (Standard)**:
```
Capability: 100 × 100GB = 10TB parallel scan
Cost: $2000/month
Best for: Moderate query load, average 3-5 concurrent queries
```

**500 slots (Enterprise)**:
```
Capability: 500 × 100GB = 50TB parallel scan
Cost: $10,000/month
Best for: High concurrency, 20+ concurrent queries, financial trading
```

**Multi-region consideration**:
```sql
-- London office: 500 slots in europe-west2
-- Frankfurt office: 500 slots in europe-west1
-- Total: 1000 slots, $20,000/month
-- Regional affinity ensures low latency
```

**Recommendation Framework for Deutsche Börse**:

```
Business Need: Real-time market data analytics
Data Volume: 3-5 PB/month
Concurrency: 50+ simultaneous queries during trading hours
Latency SLA: < 5 seconds

Recommendation:
├─ Slot reservation: 500 slots ($10,000/month)
├─ Multi-region: Europe-west2 (London) + europe-west1 (Frankfurt)
├─ Cost savings: 80% vs on-demand
├─ Predictable costs: $120,000/year
└─ Capacity: Handles 2x growth without additional cost
```

---

## Partitioning & Clustering Strategy

### Q5: Design Partitioning and Clustering for Market Data

**Question**: Design partitioning and clustering strategy for 10TB trade execution table accessed by: (a) date, (b) trader_id, (c) symbol. What's optimal?

**Answer**:

**Access Patterns**:

```
1. Daily reporting: SELECT * WHERE date = '2024-01-15'
   - 30GB of trades per day
   - Runs at 9:00 AM

2. Trader P&L: SELECT * WHERE trader_id = 'T123'
   - 100GB across entire history
   - Runs throughout day

3. Symbol analysis: SELECT * WHERE symbol = 'EURUSD'
   - 80GB across entire history
   - Runs throughout day
```

**Strategy**:

**Primary Partition: date**
```
Why: 
- Most selective (filters 99% of data daily)
- Enables time-window queries
- 10TB / 365 days = 30GB per partition
- Within optimal partition size (< 100GB)

CREATE TABLE trades
PARTITION BY date
AS SELECT * FROM raw_trades;
```

**Secondary Cluster: (trader_id, symbol)**
```
Why:
- Two most frequent filters after date
- Column order matters!
- First column trader_id: Most queries filter by trader
- Second column symbol: Refines within trader

CREATE TABLE trades
PARTITION BY date
CLUSTER BY trader_id, symbol
AS SELECT * FROM raw_trades;
```

**Query Performance**:

```sql
-- Query 1: Daily report (uses partition)
SELECT SUM(amount) FROM trades 
WHERE date = '2024-01-15'
GROUP BY trader_id;
-- Scans: 1 partition (30GB) ✓ Fast

-- Query 2: Trader P&L (uses partition + clustering)
SELECT * FROM trades 
WHERE trader_id = 'T123'
  AND date >= '2023-06-01'
GROUP BY symbol;
-- Scans: 7 months of daily partitions, 
--        but clustering limits to T123 blocks
-- Scans: ~5GB instead of 210GB ✓ 42x faster!

-- Query 3: Symbol analysis (uses partition + clustering)
SELECT * FROM trades 
WHERE symbol = 'EURUSD'
  AND date >= '2023-06-01';
-- Scans: With clustering by symbol, scans ~10GB
--        instead of 210GB ✓ 21x faster!
```

**Cost Impact**:

```
Without clustering:
- Query 2: 210GB × $6.25/TB = $1.31
- Query 3: 210GB × $6.25/TB = $1.31
- 100 similar queries/day = $262/day

With clustering:
- Query 2: 5GB × $6.25/TB = $0.03
- Query 3: 10GB × $6.25/TB = $0.06
- 100 similar queries/day = $9/day

Monthly savings: ($262 - $9) × 30 = $7,590
Annual savings: $91,000!
```

**Alternative: Hash Partition (Not Recommended)**:

```sql
-- Hash partition by trader_id
PARTITION BY FARM_FINGERPRINT(trader_id)

-- Problem: Loses date-based pruning
-- Every query must scan all 10TB
-- Can't take advantage of time-series nature of trades
```

**Best Practice for Financial Data**:

```sql
CREATE OR REPLACE TABLE trades
PARTITION BY DATE(trade_timestamp)
CLUSTER BY trader_id, symbol, counterparty
AS SELECT 
    * except(trade_timestamp),
    CAST(trade_timestamp AS DATE) as trade_date,
    trade_timestamp
FROM raw_trades;

-- Explanation:
-- - Partition by date: Most selective, supports time-window queries
-- - Cluster by trader_id: Primary filtering dimension
-- - Cluster by symbol: Secondary filtering dimension  
-- - Cluster by counterparty: Tertiary filtering dimension
```

**Monitoring Clustering Effectiveness**:

```sql
-- Check how much clustering helps
-- Scan same date-partition query with/without column filters

-- With clustering:
SELECT SUM(amount) FROM trades 
WHERE DATE(trade_timestamp) = '2024-01-15'
  AND trader_id = 'T123';
-- Scans: 500MB

-- Without clustering (just partition):
SELECT SUM(amount) FROM trades 
WHERE DATE(trade_timestamp) = '2024-01-15';
-- Scans: 30GB

-- Clustering benefit: 60x reduction
```

---

## Advanced SQL Patterns

### Q6: Window Functions in BigQuery - Financial Use Cases

**Question**: Calculate: (1) Rolling 30-day average price, (2) Rank traders by profitability, (3) Detect trend changes.

**Answer**:

```sql
-- Sample data
CREATE TEMP TABLE trades AS
SELECT
    CAST('2024-01-' || CAST(DAY AS STRING) AS DATE) as trade_date,
    'TRADER_' || MOD(CAST(RAND() * 100 AS INT64), 10) as trader_id,
    'AAPL' as symbol,
    100 + CAST(RAND() * 10 AS NUMERIC) as price,
    1000 as quantity,
    (100 + CAST(RAND() * 10 AS NUMERIC)) * 1000 as notional
FROM UNNEST(GENERATE_ARRAY(1, 30)) as DAY;

-- 1. Rolling 30-day average price
WITH rolling_avg AS (
    SELECT
        trade_date,
        trader_id,
        symbol,
        price,
        AVG(price) OVER (
            PARTITION BY symbol
            ORDER BY trade_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) as price_30day_avg,
        -- Compare to current price
        price - AVG(price) OVER (
            PARTITION BY symbol
            ORDER BY trade_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) as deviation_from_avg
    FROM trades
)
SELECT * FROM rolling_avg WHERE trade_date = CURRENT_DATE();

-- 2. Rank traders by profitability (with ties)
WITH trader_profits AS (
    SELECT
        trader_id,
        SUM(notional) as total_notional,
        COUNT(*) as trade_count,
        AVG(price) as avg_price
    FROM trades
    WHERE trade_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY trader_id
)
SELECT
    trader_id,
    total_notional,
    ROW_NUMBER() OVER (ORDER BY total_notional DESC) as rank_strict,  -- 1,2,3,4
    RANK() OVER (ORDER BY total_notional DESC) as rank_with_ties,    -- 1,2,2,4
    DENSE_RANK() OVER (ORDER BY total_notional DESC) as rank_dense,  -- 1,2,2,3
    PERCENT_RANK() OVER (ORDER BY total_notional DESC) as percentile,
    NTILE(4) OVER (ORDER BY total_notional DESC) as quartile
FROM trader_profits
ORDER BY rank_strict;

-- 3. Detect trend changes (price crossing moving average)
WITH moving_avg AS (
    SELECT
        trade_date,
        trader_id,
        symbol,
        price,
        AVG(price) OVER (
            PARTITION BY trader_id, symbol
            ORDER BY trade_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) as ma_7day,
        LAG(price) OVER (
            PARTITION BY trader_id, symbol
            ORDER BY trade_date
        ) as prev_price,
        LAG(AVG(price) OVER (
            PARTITION BY trader_id, symbol
            ORDER BY trade_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        )) OVER (
            PARTITION BY trader_id, symbol
            ORDER BY trade_date
        ) as prev_ma
    FROM trades
)
SELECT
    trade_date,
    trader_id,
    symbol,
    price,
    ma_7day,
    CASE
        WHEN prev_price < prev_ma AND price > ma_7day THEN 'GOLDEN_CROSS'
        WHEN prev_price > prev_ma AND price < ma_7day THEN 'DEATH_CROSS'
        ELSE 'NO_CHANGE'
    END as trend_signal
FROM moving_avg
WHERE trend_signal != 'NO_CHANGE';

-- 4. Detect anomalies (price deviation > 2 std devs)
WITH price_stats AS (
    SELECT
        symbol,
        AVG(price) as mean_price,
        STDDEV(price) as stddev_price
    FROM trades
    WHERE trade_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY symbol
)
SELECT
    t.trade_date,
    t.trader_id,
    t.symbol,
    t.price,
    ps.mean_price,
    ps.stddev_price,
    ABS((t.price - ps.mean_price) / ps.stddev_price) as z_score,
    CASE
        WHEN ABS((t.price - ps.mean_price) / ps.stddev_price) > 2 THEN 'ANOMALY'
        ELSE 'NORMAL'
    END as classification
FROM trades t
JOIN price_stats ps USING (symbol)
WHERE CAST((t.price - ps.mean_price) / ps.stddev_price AS FLOAT64) > 2;

-- 5. Session-based analysis (grouping consecutive days with activity)
WITH trader_sessions AS (
    SELECT
        trader_id,
        trade_date,
        COUNT(*) OVER (
            PARTITION BY trader_id
            ORDER BY trade_date
            -- This creates "gaps" when no trading
        ) as session_id,
        ROW_NUMBER() OVER (
            PARTITION BY trader_id
            ORDER BY trade_date
        ) as row_num,
        DATE_DIFF(
            trade_date,
            DATE_SUB(trade_date, INTERVAL 1 DAY),
            DAY
        ) as gap_from_previous
    FROM (
        SELECT DISTINCT trader_id, trade_date
        FROM trades
    )
)
SELECT
    trader_id,
    MIN(trade_date) as session_start,
    MAX(trade_date) as session_end,
    DATE_DIFF(MAX(trade_date), MIN(trade_date), DAY) as session_duration_days,
    COUNT(*) as trading_days_in_session
FROM trader_sessions
GROUP BY trader_id, session_id
HAVING COUNT(*) >= 5  -- Only sessions with 5+ trading days
ORDER BY session_start DESC;
```

**Key Window Function Concepts**:

```sql
-- Frame specifications:
ROWS BETWEEN 29 PRECEDING AND CURRENT ROW  -- Last 30 rows
RANGE BETWEEN INTERVAL 29 DAY PRECEDING AND CURRENT ROW  -- Last 30 days

-- Different from PARTITION BY:
PARTITION BY symbol  -- Separate calculations per symbol
ORDER BY trade_date  -- Order within partition
ROWS BETWEEN ...     -- Define window frame

-- Ranking functions:
ROW_NUMBER()   -- 1,2,3,4,5 (unique)
RANK()         -- 1,2,2,4,5 (with ties)
DENSE_RANK()   -- 1,2,2,3,4 (no gaps)

-- Offset functions:
LAG(column, 1) -- Previous value
LEAD(column, 1) -- Next value
FIRST_VALUE() -- First in window
LAST_VALUE() -- Last in window
```

---

## Real-Time Data Ingestion

### Q7: Streaming Data into BigQuery - Kafka to BQ Pipeline

**Question**: Design a real-time pipeline: Kafka (market ticks) → BigQuery (with exactly-once semantics and late data handling).

**Answer**:

**Architecture**:

```
Kafka (market ticks)
    ↓
Cloud Pub/Sub (fan-out)
    ↓
Cloud Dataflow (Apache Beam)
    ├─ Parse JSON
    ├─ Validate schema
    ├─ Handle duplicates (exactly-once)
    ├─ Buffer (micro-batching)
    ↓
BigQuery (streaming inserts)
    ├─ Partition by date
    ├─ Cluster by symbol
    ├─ Real-time table
    └─ Update materialized views
```

**Implementation**:

```python
# Using Apache Beam (Dataflow)

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.io.gcp.bigquery import WriteToBigQuery
from apache_beam.transforms import window
import json
from datetime import datetime

# 1. Parse Kafka message
class ParseKafkaMessage(beam.DoFn):
    def process(self, element):
        try:
            # Kafka message format
            message = json.loads(element)
            
            # Validate required fields
            required = ['timestamp', 'symbol', 'bid_price', 'ask_price']
            if not all(f in message for f in required):
                raise ValueError(f"Missing required field in {message}")
            
            # Normalize timestamp
            ts = datetime.fromisoformat(message['timestamp'])
            message['timestamp'] = ts.isoformat()
            message['ingest_time'] = datetime.utcnow().isoformat()
            
            yield message
        except json.JSONDecodeError as e:
            # Log malformed messages
            yield pvalue.TaggedOutput('invalid_messages', {
                'raw_message': element,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })

# 2. Deduplication (exactly-once semantics)
class Deduplicator(beam.DoFn):
    def __init__(self):
        self.seen_ids = {}
    
    def process(self, element):
        # Use message hash as ID
        msg_id = f"{element['timestamp']}_{element['symbol']}_{element['bid_price']}"
        
        if msg_id not in self.seen_ids:
            self.seen_ids[msg_id] = True
            yield element
        # else: Skip duplicate (exactly-once)

# 3. Validate data
class ValidateData(beam.DoFn):
    def process(self, element):
        try:
            # Validate business logic
            if element['bid_price'] < 0 or element['ask_price'] < 0:
                raise ValueError("Negative prices")
            if element['bid_price'] > element['ask_price']:
                raise ValueError("Bid > ask")
            if element['bid_size'] <= 0:
                raise ValueError("Invalid size")
            
            yield element
        except ValueError as e:
            yield pvalue.TaggedOutput('invalid_data', {
                'record': element,
                'error': str(e)
            })

# 4. Main pipeline
def run(argv=None):
    options = PipelineOptions(
        project='my-gcp-project',
        runner='DataflowRunner',
        region='europe-west1',
        temp_location='gs://my-bucket/temp',
        num_workers=10,
        machine_type='n1-standard-4'
    )
    
    with beam.Pipeline(options=options) as p:
        # Read from Pub/Sub (fan-out from Kafka)
        raw_messages = (
            p 
            | 'Read' >> beam.io.ReadFromPubSub(topic='projects/my-project/topics/market-ticks')
            | 'Decode' >> beam.Map(lambda x: x.decode('utf-8'))
        )
        
        # Parse and validate
        parsed = (
            raw_messages
            | 'Parse' >> beam.ParDo(ParseKafkaMessage()).with_outputs(
                'main', 'invalid_messages'
            )
        )
        
        # Deduplication
        deduplicated = (
            parsed['main']
            | 'Deduplicate' >> beam.ParDo(Deduplicator())
        )
        
        # Data validation
        validated = (
            deduplicated
            | 'Validate' >> beam.ParDo(ValidateData()).with_outputs(
                'main', 'invalid_data'
            )
        )
        
        # Windowing (for aggregation if needed)
        windowed = (
            validated['main']
            | 'Window' >> beam.WindowInto(window.FixedWindows(60))  # 1-minute windows
        )
        
        # Write to BigQuery
        table_schema = {
            'fields': [
                {'name': 'timestamp', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
                {'name': 'symbol', 'type': 'STRING', 'mode': 'REQUIRED'},
                {'name': 'bid_price', 'type': 'FLOAT64', 'mode': 'REQUIRED'},
                {'name': 'ask_price', 'type': 'FLOAT64', 'mode': 'REQUIRED'},
                {'name': 'bid_size', 'type': 'INT64', 'mode': 'REQUIRED'},
                {'name': 'ask_size', 'type': 'INT64', 'mode': 'REQUIRED'},
                {'name': 'ingest_time', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
            ]
        }
        
        _ = (
            windowed
            | 'WriteToBQ' >> WriteToBigQuery(
                table='my-dataset.market_ticks',
                schema=table_schema,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                method='STREAMING_INSERTS'  # Real-time
            )
        )
        
        # Log invalid data
        _ = (
            validated['invalid_data']
            | 'WriteInvalidToBQ' >> WriteToBigQuery(
                table='my-dataset.market_ticks_invalid',
                schema={'fields': [
                    {'name': 'record', 'type': 'JSON', 'mode': 'REQUIRED'},
                    {'name': 'error', 'type': 'STRING', 'mode': 'REQUIRED'},
                    {'name': 'timestamp', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
                ]},
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND
            )
        )

if __name__ == '__main__':
    run()
```

**BigQuery Table Configuration**:

```sql
CREATE TABLE dataset.market_ticks
PARTITION BY DATE(timestamp)
CLUSTER BY symbol
AS
SELECT
    CAST(NULL AS TIMESTAMP) as timestamp,
    CAST(NULL AS STRING) as symbol,
    CAST(NULL AS FLOAT64) as bid_price,
    CAST(NULL AS FLOAT64) as ask_price,
    CAST(NULL AS INT64) as bid_size,
    CAST(NULL AS INT64) as ask_size,
    CAST(NULL AS TIMESTAMP) as ingest_time
WHERE FALSE;

-- Materialized view for 1-minute OHLC
CREATE MATERIALIZED VIEW dataset.market_ticks_ohlc_1min AS
SELECT
    TIMESTAMP_TRUNC(timestamp, MINUTE) as minute,
    symbol,
    FIRST_VALUE(bid_price) OVER (PARTITION BY symbol, TIMESTAMP_TRUNC(timestamp, MINUTE) ORDER BY timestamp) as open_bid,
    MAX(ask_price) OVER (PARTITION BY symbol, TIMESTAMP_TRUNC(timestamp, MINUTE)) as high_ask,
    MIN(bid_price) OVER (PARTITION BY symbol, TIMESTAMP_TRUNC(timestamp, MINUTE)) as low_bid,
    LAST_VALUE(ask_price) OVER (PARTITION BY symbol, TIMESTAMP_TRUNC(timestamp, MINUTE) ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as close_ask,
    SUM(bid_size) OVER (PARTITION BY symbol, TIMESTAMP_TRUNC(timestamp, MINUTE)) as total_bid_size,
    SUM(ask_size) OVER (PARTITION BY symbol, TIMESTAMP_TRUNC(timestamp, MINUTE)) as total_ask_size,
    COUNT(*) as tick_count
FROM dataset.market_ticks
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR);

-- Refresh every minute
CALL BQ.REFRESH_MATERIALIZED_VIEW('dataset.market_ticks_ohlc_1min');
```

**Monitoring and SLAs**:

```sql
-- Monitor ingestion lag
SELECT
    symbol,
    MAX(timestamp) as latest_tick,
    CURRENT_TIMESTAMP() as current_time,
    TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(timestamp), SECOND) as lag_seconds
FROM dataset.market_ticks
GROUP BY symbol
HAVING lag_seconds > 60  -- Alert if > 1 minute lag;

-- Monitor error rates
SELECT
    TIMESTAMP_TRUNC(timestamp, MINUTE) as minute,
    COUNT(*) as invalid_records,
    ROUND(COUNT(*) / (SELECT COUNT(*) FROM dataset.market_ticks WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 MINUTE)) * 100, 2) as error_percentage
FROM dataset.market_ticks_invalid
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 MINUTE)
GROUP BY minute
HAVING error_percentage > 0.1;  -- Alert if error rate > 0.1%
```

---

## Security & Governance

### Q8: Row-Level and Column-Level Security in BigQuery

**Question**: Implement security so traders only see their own trades, and junior analysts can't see trader PnL details.

**Answer**:

**Strategy 1: Column-Level Security with Policy Tags**:

```sql
-- Step 1: Create policy tag taxonomy
CREATE OR REPLACE TAXONOMY `gcp-project.location.financial_data` 
    DISPLAY_NAME = "Financial Data"
    DESCRIPTION = "Tags for financial data classification";

CREATE OR REPLACE POLICY_TAG `gcp-project.location.financial_data.trader_pnl`
    DISPLAY_NAME = "Trader PnL"
    DESCRIPTION = "Sensitive trader profit/loss data";

CREATE OR REPLACE POLICY_TAG `gcp-project.location.financial_data.confidential_pricing`
    DISPLAY_NAME = "Confidential Pricing"
    DESCRIPTION = "Non-public pricing information";

-- Step 2: Apply tags to columns
ALTER TABLE dataset.trades
ALTER COLUMN pnl
SET OPTIONS (
    description = "Profit and Loss (Sensitive)",
    data_classification = "gcp-project.location.financial_data.trader_pnl"
);

ALTER TABLE dataset.trades
ALTER COLUMN trader_cost_basis
SET OPTIONS (
    data_classification = "gcp-project.location.financial_data.confidential_pricing"
);

-- Step 3: Create data mask for sensitive columns
-- For analysts, show NULL; for traders/managers, show actual value
CREATE OR REPLACE FUNCTION dataset.mask_trader_pnl(
    pnl FLOAT64,
    role STRING
) RETURNS FLOAT64
LANGUAGE SQL
OPTIONS (
    description = "Masks PnL based on user role"
) AS (
    CASE
        WHEN role IN ('TRADER', 'MANAGER', 'ADMIN') THEN pnl
        ELSE NULL  -- Analysts see NULL
    END
);

-- Step 4: Create authorized view with masking
CREATE OR REPLACE VIEW dataset.trades_analyst_view AS
SELECT
    trade_id,
    trader_id,
    symbol,
    amount,
    execution_price,
    dataset.mask_trader_pnl(pnl, SESSION_USER_ATTRIBUTE('role')) as pnl,
    trade_timestamp
FROM dataset.trades;

-- Step 5: Grant access
GRANT `roles/bigquery.dataEditor` ON VIEW dataset.trades_analyst_view 
TO group-analysts@deutscheboerse.com;

-- Restrict direct table access
DENY `roles/bigquery.dataViewer` ON TABLE dataset.trades 
TO group-analysts@deutscheboerse.com;
```

**Strategy 2: Row-Level Security (VPC-SC / Fine-grained)**:

```sql
-- For traders to see only their trades:

-- Option A: Authorized View
CREATE OR REPLACE VIEW dataset.trades_user_view AS
SELECT
    trade_id,
    trader_id,
    symbol,
    amount,
    execution_price,
    pnl,
    trade_timestamp
FROM dataset.trades
WHERE trader_id = SESSION_USER();  -- Filters to logged-in user
-- Note: Requires user format 'trader_email@domain.com' in trader_id column

-- Usage:
GRANT `roles/bigquery.dataViewer` ON VIEW dataset.trades_user_view 
TO serviceAccount-traders@deutscheboerse.com;

-- DENY direct table access
DENY `roles/bigquery.dataViewer` ON TABLE dataset.trades 
TO serviceAccount-traders@deutscheboerse.com;

-- Option B: Dynamic filtering with USER() function
SELECT
    *
FROM dataset.trades
WHERE
    -- Traders see only their trades
    trader_email = LOWER(REGEXP_EXTRACT(SESSION_USER(), r'^([^@]+@[^@]+)$'))
    -- Managers see all trades in their region
    OR SESSION_USER() IN (
        SELECT manager_email FROM dataset.managers 
        WHERE region = (
            SELECT region FROM dataset.traders WHERE trader_email = LOWER(REGEXP_EXTRACT(SESSION_USER(), r'^([^@]+@[^@]+)$'))
        )
    )
    -- Admins see everything (no filter)
    OR 'admin' IN UNNEST(SESSION_USER_ATTRIBUTES('role'));
```

**Strategy 3: Encryption and Access Control**:

```sql
-- Step 1: CMEK (Customer-Managed Encryption Key)
-- Use Google Cloud KMS for key management

-- Step 2: Dataset-level access control
GRANT `roles/bigquery.dataEditor` ON DATASET dataset 
TO user-trader@deutscheboerse.com
WITH CONDITION: dateTime.now('Europe/London') < dateTime('2025-01-01T00:00:00Z')
-- Temporary access, expires end of year

-- Step 3: Project-level IAM
# Restrict BigQuery API access to specific VPC only
resource "google_compute_security_policy" "bq_policy" {
  name = "bigquery-access-policy"
  
  rule {
    action = "deny(403)"
    match {
      # Deny access from non-VPC sources
      origin_region_code = ".*"  # Allow from VPC only
    }
    description = "BigQuery access from VPC only"
  }
}
```

**Monitoring Access**:

```sql
-- Check who accessed what
SELECT
    timestamp,
    user_email,
    action,
    job_id,
    referenced_fields,
    error_result
FROM `region-eu.INFORMATION_SCHEMA.JOBS_BY_PROJECT` jobs
CROSS JOIN UNNEST(referenced_tables) as tables
WHERE DATE(timestamp) = CURRENT_DATE()
  AND tables.project_id = 'my-project'
  AND tables.dataset_id = 'dataset'
  AND tables.table_id = 'trades'
GROUP BY user_email, action
HAVING COUNT(*) > 100;  -- Alert on unusual access patterns

-- Detect unauthorized access attempts
SELECT
    user_email,
    COUNT(*) as failed_queries,
    ARRAY_AGG(DISTINCT error_result.reason LIMIT 5) as errors
FROM `region-eu.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE DATE(timestamp) = CURRENT_DATE()
  AND error_result IS NOT NULL
GROUP BY user_email
HAVING failed_queries > 10;
```

---

## GCP Ecosystem Integration

### Q9: Complete Data Pipeline - Kafka → Dataflow → BigQuery → Looker

**Question**: Design end-to-end financial analytics pipeline integrating multiple GCP services.

**Architecture**:

```
Exchange APIs → Kafka (Cloud Pub/Sub) → Cloud Dataflow → BigQuery
                                                            ↓
                                                      Analytics Engine
                                                            ↓
                                                    Looker (BI)
                                                            ↓
                                    Traders/Managers (Real-time Dashboard)
```

**Component Details**:

**1. Data Ingestion (Cloud Pub/Sub)**:
```python
# Simulate market ticks from multiple exchanges
import random
from google.cloud import pubsub_v1
import json
from datetime import datetime

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path('my-project', 'market-ticks')

symbols = ['EURUSD', 'GBPUSD', 'AAPL', 'MSFT']
while True:
    for symbol in symbols:
        message = {
            'timestamp': datetime.utcnow().isoformat(),
            'symbol': symbol,
            'bid_price': 100 + random.uniform(-5, 5),
            'ask_price': 100 + random.uniform(-5, 5),
            'bid_size': random.randint(1000, 10000),
            'ask_size': random.randint(1000, 10000),
            'exchange': random.choice(['EUREX', 'LSEG', 'NASDAQ'])
        }
        
        publisher.publish(
            topic_path,
            json.dumps(message).encode('utf-8')
        )
```

**2. Stream Processing (Cloud Dataflow)**:
```python
# (See Q7 for full Dataflow implementation)
# Key additions:
# - Aggregation: 1-minute OHLC
# - Enrichment: Join with master data (symbols, exchanges)
# - Deduplication: Exactly-once semantics
```

**3. Warehouse (BigQuery)**:
```sql
-- Real-time market data table
CREATE TABLE dataset.market_ticks_realtime
PARTITION BY DATE(timestamp)
CLUSTER BY symbol, exchange
OPTIONS (
    partition_expiration_ms=7776000000,  -- 90 days retention
    description="Real-time market ticks from exchanges"
);

-- Aggregated OHLC view (1-minute windows)
CREATE MATERIALIZED VIEW dataset.ohlc_1min_realtime
PARTITION BY DATE(minute)
CLUSTER BY symbol
AS
SELECT
    TIMESTAMP_TRUNC(timestamp, MINUTE) as minute,
    symbol,
    exchange,
    FIRST_VALUE(bid_price) OVER w as open_bid,
    MAX(ask_price) OVER w as high,
    MIN(bid_price) OVER w as low,
    LAST_VALUE(ask_price) OVER w as close_ask,
    SUM(bid_size) OVER w as total_volume,
    COUNT(*) as tick_count
FROM dataset.market_ticks_realtime
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
WINDOW w AS (
    PARTITION BY symbol, exchange, TIMESTAMP_TRUNC(timestamp, MINUTE)
    ORDER BY timestamp
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
);

-- Historical analytics table (nightly aggregations)
CREATE TABLE dataset.daily_market_stats
PARTITION BY DATE(trading_date)
CLUSTER BY symbol
AS
SELECT
    trading_date,
    symbol,
    exchange,
    FIRST_VALUE(open_bid) OVER (PARTITION BY symbol ORDER BY minute) as daily_open,
    MAX(high) OVER (PARTITION BY symbol) as daily_high,
    MIN(low) OVER (PARTITION BY symbol) as daily_low,
    LAST_VALUE(close_ask) OVER (PARTITION BY symbol ORDER BY minute ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as daily_close,
    SUM(total_volume) OVER (PARTITION BY symbol) as daily_volume,
    AVG(close_ask - open_bid) OVER (PARTITION BY symbol) as avg_spread
FROM dataset.ohlc_1min_realtime;
```

**4. BI/Analytics (Looker)**:
```sql
-- Looker explores
view: market_ticks_realtime {
    sql_table_name: dataset.market_ticks_realtime ;;
    
    dimension: symbol {
        type: string
        primary_key: yes
        sql: ${TABLE}.symbol ;;
    }
    
    dimension: bid_price {
        type: number
        sql: ${TABLE}.bid_price ;;
    }
    
    measure: count {
        type: count
    }
    
    measure: avg_bid {
        type: average
        sql: ${TABLE}.bid_price ;;
    }
}

-- Dashboard: Real-time market monitor
dashboard: market_monitor {
    title: "Live Market Data"
    
    element: current_spreads {
        type: table
        query: latest_spreads
        
        Listen to refresh trigger every 30 seconds
    }
    
    element: volume_by_symbol {
        type: bar
        query: volume_last_hour
    }
    
    element: price_trends {
        type: line
        query: price_trend_30min
    }
}
```

**5. Scheduling & Orchestration (Cloud Composer - Airflow)**:
```python
from airflow import DAG
from airflow.operators.bigquery_operator import BigQueryCheckOperator
from airflow.providers.google.cloud.transfers.bigquery_to_bigquery import BigQueryToBigQueryOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'data-engineering',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 1, 1),
}

dag = DAG(
    'market_data_pipeline',
    default_args=default_args,
    schedule_interval='0 */1 * * *',  # Hourly
    catchup=False
)

# Quality check on streaming data
check_data_freshness = BigQueryCheckOperator(
    task_id='check_data_freshness',
    sql='''
    SELECT COUNT(*) 
    FROM `project.dataset.market_ticks_realtime`
    WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE)
    ''',
    use_legacy_sql=False,
    location='EU',
    dag=dag
)

# Aggregate to daily statistics
aggregate_daily = BigQueryToBigQueryOperator(
    task_id='aggregate_daily',
    source_project_dataset_table='project.dataset.ohlc_1min_realtime',
    destination_project_dataset_table='project.dataset.daily_market_stats',
    write_disposition='WRITE_APPEND',
    create_disposition='CREATE_IF_NEEDED',
    dag=dag
)

# Data quality checks
quality_checks = BigQueryCheckOperator(
    task_id='quality_checks',
    sql='''
    SELECT 1 WHERE NOT EXISTS (
        SELECT 1 FROM `project.dataset.daily_market_stats`
        WHERE trading_date = CURRENT_DATE()
        HAVING COUNT(*) = 0
    )
    ''',
    dag=dag
)

check_data_freshness >> aggregate_daily >> quality_checks
```

---

## Production Patterns

### Q10: Cost Optimization Framework for Financial Data Warehouse

**Question**: Your BigQuery costs tripled overnight. Diagnose and fix.

**Answer**:

**Investigation Steps**:

```sql
-- Step 1: Which tables consumed the most?
SELECT
    table_schema,
    table_name,
    ROUND(size_bytes / POW(10,9), 2) as size_gb,
    ROUND(size_bytes / POW(10,12), 4) as size_tb
FROM `project.dataset.__TABLES__`
ORDER BY size_bytes DESC
LIMIT 10;

-- Step 2: Which queries consumed the most?
SELECT
    user_email,
    SUM(total_bytes_processed) / POW(10,12) as tb_scanned,
    COUNT(*) as query_count,
    AVG(total_bytes_processed / POW(10,9)) as avg_gb_per_query
FROM `region-eu.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE DATE(creation_time) = DATE(CURRENT_TIMESTAMP() - 1)
GROUP BY user_email
ORDER BY tb_scanned DESC;

-- Step 3: Which specific queries are expensive?
SELECT
    user_email,
    statement_type,
    total_bytes_processed / POW(10,9) as gb_scanned,
    query[OFFSET(0)] as first_statement,
    creation_time
FROM `region-eu.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE DATE(creation_time) = DATE(CURRENT_TIMESTAMP() - 1)
ORDER BY total_bytes_processed DESC
LIMIT 20;
```

**Common Root Causes**:

**Root Cause 1: SELECT * Without Filtering**:
```sql
-- EXPENSIVE: Scans entire 500GB table
SELECT * FROM trades;

-- FIX: Select needed columns only
SELECT trade_id, trader_id, amount FROM trades;
-- Reduces scan from 500GB to 50GB (90% cost reduction)
```

**Root Cause 2: No Partitioning/Clustering**:
```sql
-- EXPENSIVE: Every query scans full table
SELECT * FROM trades WHERE trader_id = 'T123';  -- Scans 500GB

-- FIX: Add clustering
ALTER TABLE trades CLUSTER BY trader_id;
-- Same query now scans 5GB (100x cost reduction!)
```

**Root Cause 3: Inefficient Joins**:
```sql
-- EXPENSIVE: Cross join creates explosion
SELECT * FROM trades t, orders o;  -- Could be 500GB × 100GB = huge

-- FIX: Use appropriate joins
SELECT * FROM trades t INNER JOIN orders o ON t.order_id = o.id;
```

**Root Cause 4: Runaway Scheduled Queries**:
```python
# Check if scheduled queries are running unusually often
from google.cloud import bigquery

client = bigquery.Client(project='my-project')

# List all scheduled queries
scheduled_queries = client.list_jobs(job_type='SCHEDULED_QUERY')

for job in scheduled_queries:
    if 'SELECT *' in job.query:  # Red flag!
        print(f"Alert: {job.friendly_name} uses SELECT *")
```

**Root Cause 5: Unpartitioned Table Scans**:
```sql
-- Check unpartitioned tables (often the culprit)
SELECT
    table_schema,
    table_name,
    ROUND(size_bytes / POW(10,9), 2) as size_gb,
    CASE
        WHEN partition_field IS NOT NULL THEN 'Partitioned'
        ELSE 'NOT PARTITIONED - FIX THIS'
    END as partitioning_status
FROM `project.dataset.__TABLES__`
WHERE size_bytes > 10 * POW(10,9)  -- > 10GB
ORDER BY size_bytes DESC;

-- Fix: Repartition
CREATE TABLE trades_partitioned
PARTITION BY DATE(trade_date)
CLUSTER BY trader_id
AS SELECT * FROM trades;
```

**Cost Optimization Checklist**:

```python
# 1. Monthly cost tracking
monthly_cost = total_bytes_scanned * 6.25 / POW(10,12)
print(f"Monthly cost: ${monthly_cost:.2f}")

# 2. If cost > $10,000/month → Consider slots
# Break-even: 1,600,000 GB = 1.6 PB
if total_bytes_scanned / POW(10,9) > 1600000:
    print("RECOMMEND: Purchase 100-500 slots")

# 3. Implement cost governance
spark.conf.set("spark.sql.shuffle.partitions", "200")
spark.conf.set("spark.sql.adaptive.enabled", "true")

# 4. Monitor and alert
bigquery_cost_per_user = analyze_costs_by_user()
if any(cost > threshold for cost in bigquery_cost_per_user.values()):
    alert_team("High BigQuery costs detected")
```

**For Deutsche Börse - Recommended Cost Management**:

```sql
-- Layer 1: Query templates (enforce best practices)
CREATE PROCEDURE dataset.get_trader_daily_pnl(
    trader_id_input STRING,
    date_input DATE
)
BEGIN
    -- Force partitioning + clustering + column selection
    SELECT
        trader_id,
        SUM(pnl) as daily_pnl,
        SUM(amount) as notional,
        COUNT(*) as trade_count
    FROM dataset.trades
    WHERE trader_id = trader_id_input
      AND DATE(trade_timestamp) = date_input
    GROUP BY trader_id;
END;

-- Layer 2: Cost alerts
SELECT
    user_email,
    SUM(total_bytes_processed) / POW(10,12) * 6.25 as daily_cost,
    IF(SUM(total_bytes_processed) / POW(10,12) * 6.25 > 100,
       'ALERT: High cost user',
       'Normal') as status
FROM `region-eu.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE DATE(creation_time) = CURRENT_DATE()
GROUP BY user_email
HAVING daily_cost > 10;

-- Layer 3: Automatic optimization suggestions
SELECT
    table_schema,
    table_name,
    size_bytes / POW(10,12) as size_tb,
    CASE
        WHEN size_bytes > 100 * POW(10,9) AND partition_field IS NULL THEN 'URGENT: Add partitioning'
        WHEN size_bytes > 10 * POW(10,9) AND clustering_ordinal_position IS NULL THEN 'RECOMMEND: Add clustering'
        ELSE 'OK'
    END as recommendation
FROM `project.dataset.__TABLES__`
ORDER BY size_bytes DESC;
```

---

## Summary - Key Takeaways for Deutsche Börse Interview

**Must Know**:
1. ✅ Dremel + Colossus + Jupiter architecture
2. ✅ Partitioning vs Clustering (when to use each)
3. ✅ Query optimization (predicate pushdown, column selection)
4. ✅ Cost modeling (on-demand vs slots)
5. ✅ Real-time streaming (Dataflow + Pub/Sub)
6. ✅ Security (policy tags, row/column level)
7. ✅ Window functions for financial analysis
8. ✅ Ecosystem integration (Looker, Composer, Dataflow)

**Advanced Topics**:
- Materialized views for real-time dashboards
- Multi-region high-availability design
- ML integration (BigQuery ML, Vertex AI)
- Cost governance and monitoring

**For Principal Level**:
- Architecture thinking (end-to-end)
- Trade-off awareness (cost vs. latency vs. complexity)
- Production insights (failures, debugging, monitoring)
- Mentorship and knowledge sharing

---

**You've got this!** BigQuery is a powerful tool for financial data analytics. Focus on understanding the three-layer architecture and cost optimization, as these are the key differentiators at principal level.
