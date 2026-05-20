# MODULE 7: ADVANCED SYSTEM DESIGN SCENARIOS
## PhD-Level Data Engineering Interview Preparation
### Tailored for Viraaj Sivaraju — Senior Data Engineer, Wells Fargo CDM Next

---

## MODULE OVERVIEW

This module covers **10 advanced, real-world scenarios** that go beyond standard design questions. Each scenario targets the edge cases, tradeoffs, and failure modes that separate senior engineers from principal engineers. These are the questions asked when the interviewer wants to see how you think under ambiguity, not just whether you know the textbook answer.

---

## SCENARIO 1: HANDLING LATE-ARRIVING DATA IN STREAMING PIPELINES

### The Problem

Your streaming pipeline processes e-commerce order events. You compute hourly revenue by region. An event arrives 4 hours late (mobile app was offline, synced when reconnected). How do you handle it without reprocessing all historical data?

### Why This Is Hard

```
Timeline of events:
  10:00 AM - Order placed (but device offline)
  10:30 AM - 10:00-11:00 window closes, revenue computed: $9,500
  2:00 PM  - Device comes online, event arrives with timestamp 10:00 AM
  
  Problem: Your 10:00-11:00 window is already closed and published.
  Options:
    A) Ignore the event → revenue is wrong ($9,500 instead of $9,850)
    B) Reopen and recompute the window → expensive, complex
    C) Track "corrections" separately → incremental updates downstream
    D) Use allowed lateness → accept late events up to N hours, recompute
```

### Deep Solution: Apache Beam Watermarks and Allowed Lateness

```python
class LateDataHandlingPipeline:
    
    def build(self, pipeline: beam.Pipeline):
        
        events = (
            pipeline
            | "ReadFromPubSub" >> beam.io.ReadFromPubSub(
                topic=ORDERS_TOPIC,
                with_attributes=True
            )
            | "ParseEvents" >> beam.Map(parse_order_event)
        )
        
        # Windowing with allowed lateness
        windowed = (
            events
            | "Window" >> beam.WindowInto(
                beam.window.FixedWindows(3600),  # 1-hour windows
                
                # Watermark: how far behind processing time can event time be
                # before we consider data "complete"
                # Set to 2 hours — we expect most data within 2 hours
                allowed_lateness=beam.window.Duration(seconds=7200),
                
                # What to do when late data arrives:
                # ACCUMULATING: recompute entire window (accurate, expensive)
                # DISCARDING: only process new records (fast, less accurate)
                accumulation_mode=beam.trigger.AccumulationMode.ACCUMULATING,
                
                # Trigger strategy:
                trigger=beam.trigger.AfterWatermark(
                    early=beam.trigger.AfterProcessingTime(300),  # Emit every 5 min
                    late=beam.trigger.AfterCount(1)  # Emit immediately on late arrival
                )
            )
        )
        
        # Each window now emits multiple panes:
        # - EARLY pane: preliminary results (before watermark)
        # - ON_TIME pane: definitive results (at watermark)
        # - LATE pane: corrections (after watermark, within allowed_lateness)
        
        aggregated = (
            windowed
            | "AggregateRevenue" >> beam.CombinePerKey(sum)
        )
        
        # Route panes to different destinations based on type
        aggregated | "WritePanes" >> beam.ParDo(PaneRoutingDoFn())


class PaneRoutingDoFn(beam.DoFn):
    
    def process(self, element, window=beam.DoFn.WindowParam, pane_info=beam.DoFn.PaneInfoParam):
        key, value = element
        window_start = window.start.to_utc_datetime()
        
        if pane_info.is_first:
            # Write to "preliminary" table (may be updated)
            yield beam.pvalue.TaggedOutput("preliminary", 
                {"window_start": window_start, "revenue": value, "is_final": False})
        
        if pane_info.timing == beam.trigger.PaneInfoTiming.ON_TIME:
            # Write to "official" table — this is the definitive result
            yield beam.pvalue.TaggedOutput("official",
                {"window_start": window_start, "revenue": value, "is_final": True})
        
        if pane_info.timing == beam.trigger.PaneInfoTiming.LATE:
            # Write correction record
            yield beam.pvalue.TaggedOutput("corrections",
                {"window_start": window_start, "revenue_delta": value, "correction_ts": datetime.now()})
```

### Downstream Handling of Corrections

```sql
-- BigQuery view that merges official results with corrections
CREATE OR REPLACE VIEW analytics.hourly_revenue_corrected AS
WITH official AS (
  SELECT window_start, revenue, 'official' AS source
  FROM analytics.hourly_revenue_official
),
corrections AS (
  SELECT 
    window_start,
    SUM(revenue_delta) AS total_corrections
  FROM analytics.hourly_revenue_corrections
  GROUP BY window_start
)
SELECT
  o.window_start,
  o.revenue + COALESCE(c.total_corrections, 0) AS corrected_revenue,
  o.revenue AS official_revenue,
  COALESCE(c.total_corrections, 0) AS correction_amount,
  CASE WHEN c.total_corrections IS NOT NULL THEN TRUE ELSE FALSE END AS has_corrections
FROM official o
LEFT JOIN corrections c ON o.window_start = c.window_start;
```

### Decision Framework for Late Data

| Allowed Lateness | When to Use | Tradeoff |
|---|---|---|
| 0 (no late data) | Non-critical metrics, high volume | Simple but loses late data |
| 1-2 hours | Mobile apps, IoT sensors | Good for most real-world cases |
| 24 hours | Business-critical financial data | High memory cost for state |
| Unbounded | Audit, compliance pipelines | Reprocess via batch reconciliation |

---

## SCENARIO 2: ZERO-DOWNTIME SCHEMA MIGRATION ON A LIVE PIPELINE

### The Problem

Your production pipeline is writing 10 TB/day to a BigQuery table. The table needs a breaking schema change: rename `customer_id` to `cust_id` AND change `amount` from FLOAT64 to DECIMAL(18,4). 200 downstream consumers depend on this table. How do you migrate without a maintenance window?

### Why This Is Hard

```
Can't just ALTER TABLE — BigQuery doesn't support column renames
Can't drop and recreate — data loss
Can't pause the pipeline — 24×7 operation requirement
Can't notify 200 consumers simultaneously — organizational friction
```

### Solution: Expand-Contract Pattern (Also called Parallel-Write Migration)

```
PHASE 1: EXPAND (add new columns alongside old)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Week 1-2:
  - Add new columns: cust_id (STRING), amount_decimal (DECIMAL(18,4))
  - Pipeline writes to BOTH old and new columns simultaneously
  - Old consumers continue reading customer_id (unchanged)
  - New consumers can start using cust_id
  
  Table schema during migration:
  ┌─────────────────┬────────┬──────────────────────────────────┐
  │ customer_id     │ STRING │ OLD — kept for compatibility     │
  │ cust_id         │ STRING │ NEW — same value as customer_id  │
  │ amount          │ FLOAT64│ OLD — kept for compatibility     │
  │ amount_decimal  │DECIMAL │ NEW — precisely typed            │
  └─────────────────┴────────┴──────────────────────────────────┘

PHASE 2: MIGRATE CONSUMERS
━━━━━━━━━━━━━━━━━━━━━━━━━━
Week 3-6:
  - Communicate schema change to 200 consumers
  - Provide migration guide: s/customer_id/cust_id/g
  - Track consumer migration status (query INFORMATION_SCHEMA for column usage)
  - Set deadline for migration completion

PHASE 3: CONTRACT (remove old columns after all consumers migrated)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Week 7:
  - Stop writing to old columns (nullify them)
  - Monitor: any consumer querying customer_id or amount? Alert!
  - After 2 weeks with no old-column access: remove columns
  - Pipeline simplifies to write only new columns
```

### Tracking Consumer Migration

```sql
-- Find all queries that still use old column names
-- Run weekly to track migration progress
SELECT
  user_email,
  COUNT(*) AS query_count,
  MAX(creation_time) AS last_query_ts,
  -- Extract referenced columns from query text
  REGEXP_EXTRACT_ALL(query, r'\bcustomer_id\b') AS old_col_references
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE 
  creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  AND referenced_tables LIKE '%transactions%'
  AND REGEXP_CONTAINS(query, r'\bcustomer_id\b')
  AND state = 'DONE'
GROUP BY 1
ORDER BY last_query_ts DESC;
```

### Automated Column Deprecation Workflow

```python
class ColumnDeprecationManager:
    
    def initiate_deprecation(self, table_fqn: str, columns: List[str], deadline: date):
        """
        Sets up monitoring and notifications for column deprecation.
        """
        # Step 1: Tag columns as deprecated in Dataplex
        for col in columns:
            dataplex_client.add_tag(
                resource=f"bigquery:{table_fqn}",
                column=col,
                tag={"status": "deprecated", "deadline": deadline.isoformat(), 
                     "replacement": self.get_replacement(col)}
            )
        
        # Step 2: Create monitoring alert
        self.create_usage_alert(table_fqn, columns)
        
        # Step 3: Notify known consumers via email
        consumers = self.get_downstream_consumers(table_fqn)
        self.send_deprecation_notice(consumers, columns, deadline)
        
        # Step 4: Schedule automatic validation before removal
        self.schedule_pre_removal_check(table_fqn, columns, deadline - timedelta(days=7))
    
    def pre_removal_check(self, table_fqn: str, columns: List[str]) -> bool:
        """Run before actually removing columns."""
        # Check no queries in last 30 days used these columns
        usage = self.query_column_usage(table_fqn, columns, days=30)
        if usage:
            self.block_removal_and_alert(usage)
            return False
        return True
```

---

## SCENARIO 3: BACKFILLING 10 YEARS OF HISTORICAL DATA WITH ZERO PRODUCTION IMPACT

### The Problem

You've deployed a new feature in your data pipeline (e.g., PII masking for a previously unmasked column). You need to apply this to 10 years of historical data (500 TB) in BigQuery without: (1) impacting production pipelines, (2) causing high costs, (3) creating inconsistency between historical and new data.

### Solution Architecture

```
CONSTRAINT ANALYSIS:
━━━━━━━━━━━━━━━━━━━
500 TB / BigQuery scan cost: 500 × $5 = $2,500 per full scan
At $0.02/slot-hour: aggressive approach would cost $50K+
Need: cost-controlled, production-isolated approach

CHOSEN APPROACH: Partition-by-partition backfill with slot reservation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Create separate BigQuery reservation for backfill (100 slots)
2. Use partition decorator writes (overwrite partition-by-partition)
3. Process oldest partitions first (lowest priority data)
4. Rate-limit to N partitions/hour to avoid quota exhaustion
5. Run during off-peak hours (00:00-06:00 UTC)
6. Validate each partition before moving to next
```

```python
class HistoricalBackfillOrchestrator:
    
    def __init__(self, config: BackfillConfig):
        self.config = config
        self.bq_client = bigquery.Client()
        self.completed_partitions: Set[str] = self.load_checkpoint()
        
    def run_backfill(self):
        """
        Backfills partitions one by one with checkpointing.
        Can be stopped and resumed at any time.
        """
        
        # Get all partitions that need backfill
        all_partitions = self.get_partitions_needing_backfill()
        remaining = [p for p in all_partitions if p not in self.completed_partitions]
        
        logger.info(f"Backfill status: {len(self.completed_partitions)}/{len(all_partitions)} complete")
        
        for partition_date in remaining:
            try:
                # Rate limiting: pause between partitions
                time.sleep(self.config.pause_between_partitions_seconds)
                
                # Process this partition
                self.process_partition(partition_date)
                
                # Mark as complete and save checkpoint
                self.completed_partitions.add(partition_date)
                self.save_checkpoint()
                
                logger.info(f"✓ Partition {partition_date} complete")
                
            except Exception as e:
                logger.error(f"✗ Partition {partition_date} failed: {e}")
                self.notify_failure(partition_date, e)
                # Continue to next partition (don't fail entire backfill)
    
    def process_partition(self, partition_date: str):
        """
        Reads one partition, transforms it, overwrites in-place.
        Uses partition decorator for atomic overwrite.
        """
        
        # Step 1: Read partition
        source_query = f"""
        SELECT * FROM `{self.config.source_table}`
        WHERE DATE(_PARTITIONTIME) = '{partition_date}'
        """
        
        # Step 2: Apply transformation (e.g., DLP masking)
        transform_query = f"""
        SELECT
          {self.config.non_pii_columns_sql},
          -- Apply masking to PII columns
          {self.config.masked_columns_sql}
        FROM ({source_query})
        """
        
        # Step 3: Overwrite partition atomically
        job_config = bigquery.QueryJobConfig(
            destination=f"{self.config.target_table}${partition_date.replace('-', '')}",
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            # Use backfill reservation to isolate from production
            reservation="projects/{}/locations/us/reservations/backfill-100-slots".format(PROJECT_ID)
        )
        
        job = self.bq_client.query(transform_query, job_config=job_config)
        job.result()  # Wait for completion
        
        # Step 4: Validate
        self.validate_partition(partition_date)
    
    def validate_partition(self, partition_date: str):
        """Verify row counts match and no null injection in key fields."""
        
        validation_query = f"""
        SELECT
          source_count,
          target_count,
          ABS(source_count - target_count) AS count_diff,
          -- Verify PII columns are actually masked
          COUNTIF(REGEXP_CONTAINS(email, r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{{2,}}$')) AS unmasked_emails
        FROM (
          SELECT COUNT(*) AS source_count FROM `{self.config.source_table}` WHERE DATE(_PARTITIONTIME) = '{partition_date}'
        ) s
        CROSS JOIN (
          SELECT 
            COUNT(*) AS target_count,
            SUM(CASE WHEN email IS NOT NULL THEN 1 ELSE 0 END) AS unmasked_emails_count
          FROM `{self.config.target_table}` WHERE DATE(_PARTITIONTIME) = '{partition_date}'
        ) t
        """
        
        result = self.bq_client.query(validation_query).to_dataframe()
        
        if result["count_diff"][0] != 0:
            raise ValueError(f"Row count mismatch for partition {partition_date}")
        
        if result["unmasked_emails"][0] > 0:
            raise ValueError(f"PII not masked in partition {partition_date}")
```

---

## SCENARIO 4: MULTI-REGION ACTIVE-ACTIVE DATA ARCHITECTURE

### The Problem

Your company operates in US and EU. Regulations require EU customer data to stay in EU (data residency). US customer data stays in US. But analysts in both regions need to run cross-region reports. How do you architect this?

### The Constraints

```
GDPR Data Residency: EU personal data CANNOT leave EU
CCPA: Similar restrictions for California residents
Business Need: Finance team needs global revenue reports
Latency: Analysts shouldn't notice they're querying cross-region
Consistency: Reports must be consistent (not reading stale replica)
```

### Architecture: Data Residency with Federated Query

```
┌──────────────────────────────────────────────────────────────────┐
│                    MULTI-REGION ARCHITECTURE                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  US REGION (us-central1)                                │    │
│  │                                                         │    │
│  │  BigQuery Dataset: prod_us                              │    │
│  │  Tables: customers_us, orders_us, events_us             │    │
│  │  Location: US only (IAM enforced)                       │    │
│  │                                                         │    │
│  │  Aggregated (non-PII): revenue_summary_us               │    │
│  │    → Region-safe to replicate                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│              Cross-region replication (aggregates only)          │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  GLOBAL AGGREGATION LAYER (multi-region)                │    │
│  │                                                         │    │
│  │  BigQuery Dataset: prod_global (multi-region: US)       │    │
│  │                                                         │    │
│  │  Views (federated query across regions):                │    │
│  │    global_revenue = us.revenue_summary + eu.revenue_agg │    │
│  │                                                         │    │
│  │  Only aggregated, non-PII data lands here              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              ▲                                   │
│              Cross-region replication (aggregates only)          │
│                              │                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  EU REGION (europe-west1)                               │    │
│  │                                                         │    │
│  │  BigQuery Dataset: prod_eu                              │    │
│  │  Tables: customers_eu, orders_eu, events_eu             │    │
│  │  Location: EU only (IAM + VPC Service Controls)         │    │
│  │                                                         │    │
│  │  Aggregated (non-PII): revenue_summary_eu               │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

### Data Classification for Cross-Region Replication Decision

```python
class DataResidencyClassifier:
    
    # Column-level classification rules
    PII_COLUMNS = {
        "email", "phone", "ssn", "passport_id", "ip_address",
        "full_name", "home_address", "date_of_birth", "credit_card"
    }
    
    def classify_table(self, table: BigQueryTable) -> ResidencyClass:
        """
        Determines if a table can be replicated cross-region.
        """
        pii_cols = [col for col in table.schema if col.name.lower() in self.PII_COLUMNS]
        
        if pii_cols:
            return ResidencyClass.REGION_LOCKED  # Cannot leave origin region
        
        # Check for derived PII (aggregations at very small group sizes risk re-identification)
        if self.has_small_group_aggregation(table):
            return ResidencyClass.RESTRICTED  # Needs privacy budget approval
        
        return ResidencyClass.FREELY_REPLICABLE
    
    def create_region_safe_view(self, table: BigQueryTable) -> str:
        """
        Generates a SQL view that strips PII and aggregates sufficiently
        to be safe for cross-region replication.
        """
        non_pii_cols = [
            col.name for col in table.schema 
            if col.name.lower() not in self.PII_COLUMNS
        ]
        
        return f"""
        CREATE OR REPLACE VIEW {table.dataset}.{table.name}_region_safe AS
        SELECT
          {', '.join(non_pii_cols)},
          -- Replace PII with derived non-identifying fields
          EXTRACT(YEAR FROM date_of_birth) AS birth_year,  -- Only year, not full DOB
          UPPER(SUBSTR(home_address, -2)) AS country_code  -- Only country, not full address
        FROM {table.full_name}
        """
```

### Global Report Query Pattern

```sql
-- BigQuery federated query across US and EU regions
-- This runs in the global dataset, but data STAYS in each region
-- Only aggregate results transfer across regions

CREATE OR REPLACE VIEW prod_global.global_monthly_revenue AS

-- US revenue (queries US region dataset)
SELECT 
  'US' AS region,
  DATE_TRUNC(order_date, MONTH) AS month,
  product_category,
  SUM(order_amount) AS revenue,
  COUNT(*) AS order_count
FROM `project.prod_us.orders_us`
-- Note: customer PII not included in this view
GROUP BY 1, 2, 3

UNION ALL

-- EU revenue (queries EU region dataset)  
SELECT
  'EU' AS region,
  DATE_TRUNC(order_date, MONTH) AS month,
  product_category,
  SUM(order_amount) AS revenue,
  COUNT(*) AS order_count
FROM `project.prod_eu.orders_eu`
GROUP BY 1, 2, 3;
```

---

## SCENARIO 5: COST OPTIMIZATION — REDUCING BIGQUERY BILL BY 60%

### The Problem

Your company's BigQuery bill is $200K/month. Management says reduce it by $120K without degrading query performance or data freshness. Where do you start?

### Systematic Cost Analysis

```
BIGQUERY COST COMPONENTS:
━━━━━━━━━━━━━━━━━━━━━━━━
1. Query processing: $5/TB scanned (on-demand) or flat rate slots
2. Storage: $0.02/GB-month (active), $0.01/GB-month (long-term)
3. Streaming inserts: $0.01/200MB
4. Data transfers (egress): $0.08/GB

TYPICAL BREAKDOWN FOR $200K/MONTH:
  Query processing: $140K (70%) ← biggest lever
  Storage: $40K (20%)
  Streaming inserts: $15K (7.5%)
  Egress: $5K (2.5%)
```

### Cost Reduction Playbook

**Lever 1: Partition Pruning Enforcement (saves 40-70% of query costs)**

```sql
-- EXPENSIVE: Full table scan ($500 for 100TB table)
SELECT * FROM analytics.events WHERE user_id = '12345';

-- CHEAP: Partition-pruned scan ($5 for same query, only scans 1 day = 1TB)
SELECT * FROM analytics.events 
WHERE DATE(event_ts) = CURRENT_DATE() AND user_id = '12345';

-- Enforce via authorized view that always includes partition filter:
CREATE OR REPLACE VIEW analytics.events_safe AS
SELECT * FROM analytics.events
WHERE DATE(event_ts) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY);
-- Users can only query last 90 days → can't accidentally scan 5 years
```

**Lever 2: Materialized Views for Repeated Aggregations**

```sql
-- Without materialized view: $50/query (10TB scan) × 1000 queries/day = $50K/month
SELECT
  DATE(event_ts),
  region,
  product_category,
  COUNT(*) AS events,
  SUM(revenue) AS total_revenue
FROM analytics.raw_events
GROUP BY 1, 2, 3;

-- WITH materialized view: $0.001/query (from cache), periodic refresh costs $150/month
CREATE MATERIALIZED VIEW analytics.daily_revenue_mv
OPTIONS (enable_refresh = true, refresh_interval_minutes = 60)
AS
SELECT
  DATE(event_ts) AS event_date,
  region,
  product_category,
  COUNT(*) AS events,
  SUM(revenue) AS total_revenue
FROM analytics.raw_events
GROUP BY 1, 2, 3;
-- SAVINGS: ~$49,850/month on this one view
```

**Lever 3: Storage Tiering (saves 50% on old data)**

```sql
-- Identify tables not queried in 90+ days
SELECT
  table_catalog,
  table_schema,
  table_name,
  size_bytes / POW(10,9) AS size_gb,
  size_bytes / POW(10,9) * 0.02 AS monthly_cost_active_usd,
  size_bytes / POW(10,9) * 0.01 AS monthly_cost_longterm_usd,
  -- Tables not modified in 90 days auto-transition to long-term storage
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), last_modified_time, DAY) AS days_since_modified
FROM `region-us`.INFORMATION_SCHEMA.TABLE_STORAGE
WHERE size_bytes > 10 * POW(10,9)  -- Tables > 10GB
ORDER BY size_bytes DESC;

-- Tables not modified in 90+ days automatically get long-term pricing
-- No action needed — BQ does this automatically
-- Action: Ensure you're not touching (even appending) old tables unnecessarily
```

**Lever 4: Slot Reservation (saves 40% if utilization > 50%)**

```
ON-DEMAND PRICING: $5/TB scanned
  100 TB/day × 30 days × $5 = $15,000/month for query processing

FLAT RATE (1,000 slots):
  1,000 slots × 24 hours × 30 days × $0.04/slot-hour = $28,800/month
  BUT: covers unlimited TB scanned
  
  With 100 TB/day: $15K vs $28.8K → on-demand wins
  With 1,000 TB/day: $150K vs $28.8K → flat rate wins (80% savings!)
  
BREAK-EVEN: 192 TB/day (for 1,000 slots at $0.04/slot-hr)

FLEX SLOTS: $0.04/slot-hour in 60-second increments
  Use for known peak windows: buy 500 extra slots for 2 hours during ETL
  500 slots × 2 hours × $0.04 = $40/day instead of $300 (on-demand)
```

**Lever 5: Query Result Caching**

```python
# Implement application-level caching for dashboard queries
# Reduces BigQuery calls by 80% for dashboards

from google.cloud import bigquery, firestore
import hashlib

class CachingBigQueryClient:
    
    def __init__(self, cache_ttl_seconds: int = 300):
        self.bq = bigquery.Client()
        self.cache = firestore.Client()
        self.cache_ttl = cache_ttl_seconds
    
    def query(self, sql: str, params: dict = None) -> pd.DataFrame:
        
        # Generate cache key from normalized SQL + params
        cache_key = hashlib.sha256(f"{sql}{str(params)}".encode()).hexdigest()
        
        # Check cache
        cached = self.cache.collection("query_cache").document(cache_key).get()
        if cached.exists:
            data = cached.to_dict()
            if time.time() - data["cached_at"] < self.cache_ttl:
                return pd.DataFrame(data["result"])
        
        # Cache miss — run actual BQ query
        result = self.bq.query(sql).to_dataframe()
        
        # Store in cache
        self.cache.collection("query_cache").document(cache_key).set({
            "result": result.to_dict("records"),
            "cached_at": time.time(),
            "sql_hash": cache_key[:16]
        })
        
        return result
```

---

## SCENARIO 6: DEBUGGING A SILENT DATA QUALITY FAILURE

### The Problem

Your downstream fraud model accuracy dropped from 94% to 87% over 3 weeks. No errors in the pipeline, no alerts fired. The data looks correct on the surface. How do you diagnose and fix it?

### Systematic Debugging Framework

```
STEP 1: NARROW THE TIME WINDOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Check when model accuracy started dropping:
  - Week 1: 94%
  - Week 2: 92% (first drop — this is the inflection point)
  - Week 3: 89%
  - Week 4: 87%
  
  Focus investigation on what changed between Week 1 and Week 2.

STEP 2: CHECK DATA VOLUME AND DISTRIBUTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

```sql
-- Statistical distribution check: compare current week vs 4 weeks ago
WITH week_current AS (
  SELECT
    AVG(txn_amount) AS avg_amount,
    STDDEV(txn_amount) AS stddev_amount,
    APPROX_QUANTILES(txn_amount, 100)[OFFSET(50)] AS median_amount,
    APPROX_QUANTILES(txn_amount, 100)[OFFSET(99)] AS p99_amount,
    AVG(txn_velocity_1h) AS avg_velocity,
    COUNTIF(country_code IS NULL) / COUNT(*) AS null_rate_country,
    COUNT(DISTINCT merchant_category) AS distinct_mcc_count
  FROM fraud_features.training_features
  WHERE DATE(feature_ts) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
),
week_baseline AS (
  SELECT
    AVG(txn_amount) AS avg_amount,
    STDDEV(txn_amount) AS stddev_amount,
    APPROX_QUANTILES(txn_amount, 100)[OFFSET(50)] AS median_amount,
    APPROX_QUANTILES(txn_amount, 100)[OFFSET(99)] AS p99_amount,
    AVG(txn_velocity_1h) AS avg_velocity,
    COUNTIF(country_code IS NULL) / COUNT(*) AS null_rate_country,
    COUNT(DISTINCT merchant_category) AS distinct_mcc_count
  FROM fraud_features.training_features
  WHERE DATE(feature_ts) BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 35 DAY)
    AND DATE_SUB(CURRENT_DATE(), INTERVAL 28 DAY)
)
SELECT
  'avg_amount' AS metric,
  w.avg_amount AS current_value,
  b.avg_amount AS baseline_value,
  (w.avg_amount - b.avg_amount) / b.avg_amount * 100 AS pct_change
FROM week_current w, week_baseline b
-- ... UNION ALL for each metric
```

```
STEP 3: TRACE THE LINEAGE
━━━━━━━━━━━━━━━━━━━━━━━━
Model uses features: avg_txn_30d, txn_velocity_1h, country_risk_score

country_risk_score lineage:
  fraud_features.training_features.country_risk_score
    ← dbt.country_risk_model
      ← analytics.country_transactions (aggregated daily)
        ← raw.transactions (from Kafka)
          ← payment_gateway (source system)

FOUND IT: Check each hop for the anomaly introduced at Week 2.

STEP 4: THE ROOT CAUSE (common patterns)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Schema change: new column added, existing computed column logic changed
2. Source system change: payment gateway changed country_code format (ISO2 → ISO3)
3. Join key mismatch: country risk table joined on wrong key after renaming
4. Timezone bug: timestamps shifted after DST change → features off by 1 hour
5. Null propagation: new source started sending nulls → downstream averages skewed
```

### Prevention: Automated Data Quality Monitoring

```python
class DataQualityMonitor:
    """
    Runs daily statistical checks and alerts on drift.
    Prevents silent failures before they impact models.
    """
    
    CHECKS = [
        # Volume checks
        {"type": "row_count", "threshold_pct": 20, "window_days": 7},
        
        # Distribution checks (Jensen-Shannon divergence)
        {"type": "distribution_drift", "columns": ["txn_amount", "txn_velocity_1h"], 
         "threshold": 0.1, "reference_days": 30},
        
        # Null rate checks
        {"type": "null_rate", "columns": ["country_code", "merchant_category"],
         "threshold_pct": 5},
        
        # Referential integrity
        {"type": "referential_integrity", "fk_col": "country_code", 
         "ref_table": "reference.countries", "ref_col": "iso_code"},
        
        # Schema stability
        {"type": "schema_unchanged", "alert_on": ["column_added", "column_removed", "type_changed"]},
        
        # Freshness
        {"type": "freshness", "max_lag_hours": 2, "timestamp_col": "event_ts"},
    ]
    
    def run_all_checks(self, table_fqn: str) -> CheckReport:
        results = []
        for check in self.CHECKS:
            result = self.run_check(table_fqn, check)
            results.append(result)
            if result.severity == "CRITICAL":
                self.send_immediate_alert(result)
        return CheckReport(results=results)
```

---

## SCENARIO 7: DESIGNING FOR REGULATORY COMPLIANCE — GDPR RIGHT TO BE FORGOTTEN

### The Problem

Your data lake stores 10 years of user activity data across 500 BigQuery tables. A user submits a GDPR "right to be forgotten" request. You must delete all their data within 30 days. You have 100 of these requests per day. How do you implement this at scale?

### The Core Challenge

BigQuery doesn't support row-level deletes efficiently at scale. DELETE statements require full partition scans and are expensive.

### Architecture: Pseudonymization + Key Deletion

```
APPROACH: Don't store user PII directly in data tables.
Store a pseudonym (UUID) instead. 
On deletion request: delete the mapping UUID → real identity.
The data becomes anonymous automatically.

IMPLEMENTATION:
━━━━━━━━━━━━━━
1. INGEST TIME: Replace customer_email with customer_uuid
   customer_email → SHA256(customer_email + secret_salt) → customer_uuid
   
2. IDENTITY STORE (Firestore): 
   customer_uuid → {email, name, deletion_requested: null}
   
3. ON DELETION REQUEST:
   - Mark identity record as deletion_requested: now()
   - Delete identity record after 30-day grace period
   - customer_uuid in data tables now maps to nothing → anonymized
   
4. PHYSICAL DELETION (if required by regulation):
   - For tables storing raw PII columns (legacy): 
     partition-by-partition DELETE + rebuild
   - For streaming data: 
     DLP tokenization with key rotation
```

```python
class GDPRDeletionManager:
    
    def process_deletion_request(self, user_email: str, request_id: str):
        """
        Step 1: Soft deletion — mark identity for deletion.
        Step 2: Scheduled hard deletion after verification.
        """
        
        # Find UUID for this email
        customer_uuid = self.identity_store.get_uuid(user_email)
        
        if not customer_uuid:
            logger.warning(f"No UUID found for {user_email} — may not exist in system")
            self.mark_request_complete(request_id, "NO_DATA_FOUND")
            return
        
        # Step 1: Soft delete — mark identity record
        self.identity_store.mark_for_deletion(
            uuid=customer_uuid,
            deletion_requested_at=datetime.now(),
            request_id=request_id
        )
        
        # Step 2: Find all tables containing this UUID (via lineage graph)
        affected_tables = self.lineage_service.find_tables_with_column(
            column_name="customer_uuid",
            column_value=customer_uuid
        )
        
        # Step 3: Queue physical deletion jobs for each table
        for table in affected_tables:
            self.deletion_queue.enqueue(
                DeletionJob(
                    table_fqn=table,
                    filter_column="customer_uuid",
                    filter_value=customer_uuid,
                    scheduled_at=datetime.now() + timedelta(days=30),
                    request_id=request_id
                )
            )
        
        # Step 4: Notify compliance team
        self.notify_deletion_scheduled(request_id, len(affected_tables))
    
    def execute_physical_deletion(self, job: DeletionJob):
        """
        For tables that physically store PII (not just UUID references).
        Uses partition overwrite to avoid expensive full-table scans.
        """
        
        # Find affected partitions
        affected_partitions = self.find_affected_partitions(
            table=job.table_fqn,
            filter_column=job.filter_column,
            filter_value=job.filter_value
        )
        
        for partition in affected_partitions:
            # Overwrite partition with deleted rows removed
            delete_query = f"""
            SELECT * EXCEPT({job.filter_column}), 
                   NULL AS {job.filter_column}  -- Nullify rather than delete row
            FROM `{job.table_fqn}`
            WHERE _PARTITIONDATE = '{partition}'
            """
            
            job_config = bigquery.QueryJobConfig(
                destination=f"{job.table_fqn}${partition.replace('-', '')}",
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
            )
            
            self.bq_client.query(delete_query, job_config=job_config).result()
        
        # Audit trail — cannot delete the deletion event itself
        self.log_deletion_completion(job)
```

---

## SCENARIO 8: HANDLING HOTSPOT PARTITIONS IN STREAMING PIPELINES

### The Problem

Your Pub/Sub → Dataflow → BigQuery pipeline processes events keyed by `merchant_id`. Merchant "AMAZON_US" generates 50% of all traffic. Your pipeline is slow and you're seeing all events for Amazon queuing up behind each other.

### Root Cause Analysis

```
HOTSPOT PATTERN:
━━━━━━━━━━━━━━━
Pub/Sub: Events distributed across partitions by merchant_id
AMAZON_US events → always go to same partition (by key)
One Dataflow worker handles all AMAZON_US events
→ That worker is bottleneck
→ Other workers are idle
→ Pipeline appears slow (one-worker-slow problem)

PROOF:
  Worker 1 throughput: 800 MB/s (at capacity, handling AMAZON)
  Workers 2-20 throughput: 40 MB/s each (mostly idle)
  Total: ~1.5 GB/s instead of 16 GB/s capacity
```

### Solutions

**Solution A: Salting (add random prefix to key)**

```python
# Before: key = merchant_id → hotspot
# After: key = f"{merchant_id}#{random.randint(0, 9)}" → 10 parallel workers

class SaltedGroupByKey(beam.PTransform):
    """
    Distribute a hot key across N workers by salting.
    Requires a merge step at the end.
    """
    
    def __init__(self, num_buckets: int = 10):
        self.num_buckets = num_buckets
    
    def expand(self, pcoll):
        # Step 1: Add salt suffix to hot keys
        salted = (
            pcoll
            | "AddSalt" >> beam.Map(
                lambda kv: (f"{kv[0]}#{hash(kv[0]) % self.num_buckets}", kv[1])
            )
        )
        
        # Step 2: Group by salted key (now distributed)
        grouped = salted | "GroupBySalted" >> beam.GroupByKey()
        
        # Step 3: Merge results from all salt buckets
        merged = (
            grouped
            | "MergeSaltBuckets" >> beam.Map(
                lambda kv: (kv[0].split("#")[0], list(kv[1]))  # Remove salt suffix
            )
            | "CombineBuckets" >> beam.GroupByKey()
            | "FlattenResults" >> beam.Map(
                lambda kv: (kv[0], [item for sublist in kv[1] for item in sublist])
            )
        )
        
        return merged
```

**Solution B: Side Input for Hot Key Processing**

```python
# Don't GroupByKey for hot keys at all
# Use side input pattern — broadcast hot-key context to all workers

class HotKeyAwarePipeline:
    
    HOT_MERCHANTS = {"AMAZON_US", "WALMART_US", "TARGET_US"}  # Known hot keys
    
    def build(self, pipeline: beam.Pipeline):
        
        events = pipeline | "ReadEvents" >> beam.io.ReadFromPubSub(TOPIC)
        
        # Separate hot and cold events
        hot_events, cold_events = (
            events
            | "SeparateHotCold" >> beam.Partition(
                lambda event, _: 0 if event.merchant_id in self.HOT_MERCHANTS else 1,
                2
            )
        )
        
        # Cold events: normal GroupByKey
        cold_aggregated = (
            cold_events
            | "KeyByCold" >> beam.Map(lambda e: (e.merchant_id, e))
            | "GroupByCold" >> beam.GroupByKey()
            | "AggregateCold" >> beam.Map(aggregate_merchant_events)
        )
        
        # Hot events: use combine per key (more efficient than GBK for aggregations)
        hot_aggregated = (
            hot_events
            | "KeyByHot" >> beam.Map(lambda e: (e.merchant_id, e.amount))
            | "CombineHot" >> beam.CombinePerKey(sum)  # CombinePerKey is hotspot-aware
        )
        
        # Merge results
        return (cold_aggregated, hot_aggregated) | "Merge" >> beam.Flatten()
```

**Solution C: Bigtable Key Design for Hotspot Prevention**

```
PROBLEM: Reading/writing AMAZON_US row hits same Bigtable tablet
SOLUTION: Distribute across tablets using hashed prefix

BAD KEY DESIGN:
  merchant#AMAZON_US → always hits tablet 1

GOOD KEY DESIGN (reverse domain + hash prefix):
  [hash_prefix]#[reversed_merchant]#[timestamp]
  
  AMAZON_US reversed → SU_NOZAMA
  hash("AMAZON_US") % 10 = 7
  
  Row key: 7#SU_NOZAMA#20240115
  
  Multiple AMAZON_US events now distributed across tablets 0-9
  Bigtable can serve them from different nodes
```

---

## SCENARIO 9: DESIGNING A SELF-HEALING DATA PIPELINE

### The Problem

Your pipeline runs 200+ jobs nightly. It's 3 AM. 15 jobs fail due to a transient GCS error. The on-call engineer is awake troubleshooting. How do you design a system where these transient failures resolve automatically without human intervention?

### Self-Healing Architecture

```
FAILURE TAXONOMY:
━━━━━━━━━━━━━━━━
Level 1 — Transient (auto-heal):
  - Network timeout, rate limit, temporary quota exceeded
  - Retry with exponential backoff: resolve 95% of cases
  - Expected resolution: < 30 minutes
  
Level 2 — Recoverable (auto-heal with logic):
  - Source file missing (might appear soon), schema mismatch (detectable)
  - Wait + retry with logic: resolve 90% of cases
  - Expected resolution: < 2 hours
  
Level 3 — Structural (human required):
  - Schema breaking change, source system down, data corruption
  - Alert on-call immediately
  - Cannot auto-resolve
```

```python
class SelfHealingPipelineOrchestrator:
    """
    Cloud Composer DAG that auto-heals transient failures.
    """
    
    def execute_with_self_healing(self, pipeline_config: PipelineConfig) -> ExecutionResult:
        
        max_attempts = pipeline_config.retry_policy.max_retries
        base_backoff = pipeline_config.retry_policy.backoff_seconds
        
        for attempt in range(1, max_attempts + 1):
            try:
                result = self.execute_pipeline(pipeline_config)
                
                if result.success:
                    self.record_success(pipeline_config.pipeline_id, attempt)
                    return result
                
                # Pipeline ran but produced bad data
                if result.quality_score < pipeline_config.min_quality_threshold:
                    if self.can_auto_remediate(result.quality_failures):
                        remediated_config = self.auto_remediate(pipeline_config, result)
                        continue  # Retry with fixed config
                    else:
                        raise DataQualityException(result.quality_failures)
                
            except TransientException as e:
                # Network/quota errors — just retry
                if attempt < max_attempts:
                    backoff = base_backoff * (2 ** (attempt - 1)) + random.uniform(0, 30)
                    logger.info(f"Transient error on attempt {attempt}, retrying in {backoff:.0f}s")
                    time.sleep(backoff)
                    continue
                raise
                
            except RecoverableException as e:
                # Recoverable — apply specific fix
                fix = self.diagnose_and_fix(e, pipeline_config)
                if fix.applied:
                    logger.info(f"Applied auto-fix: {fix.description}")
                    continue
                raise
                
            except StructuralException as e:
                # Cannot auto-heal — wake up on-call
                self.page_oncall(pipeline_config, e, attempt)
                raise
        
        raise MaxRetriesExceededException(f"Pipeline failed after {max_attempts} attempts")
    
    def diagnose_and_fix(self, exception: RecoverableException, config: PipelineConfig) -> Fix:
        """
        Applies intelligent fixes based on exception type.
        """
        
        if isinstance(exception, SourceFileNotFoundException):
            # File might arrive soon — check source system ETA
            eta = self.check_source_file_eta(exception.expected_path)
            if eta and eta < timedelta(hours=2):
                time.sleep(eta.total_seconds() + 300)  # Wait for file + buffer
                return Fix(applied=True, description=f"Waited {eta} for source file")
        
        elif isinstance(exception, BigQueryJobQuotaException):
            # Quota exceeded — split job into smaller chunks
            split_configs = self.split_pipeline_config(config, chunks=4)
            self.queue_split_jobs(split_configs)
            return Fix(applied=True, description="Split into 4 smaller jobs")
        
        elif isinstance(exception, WatermarkCorruptedException):
            # Reset watermark to safe point
            safe_watermark = self.find_safe_watermark(config.pipeline_id)
            self.reset_watermark(config.pipeline_id, safe_watermark)
            return Fix(applied=True, description=f"Reset watermark to {safe_watermark}")
        
        return Fix(applied=False, description="No auto-fix available")
```

---

## SCENARIO 10: MIGRATING FROM ON-PREMISE HADOOP TO GCP — ZERO DATA LOSS STRATEGY

### The Problem

Wells Fargo has 15 PB of data on Hadoop HDFS. You need to migrate to GCS + BigQuery over 12 months with zero data loss, continuous availability during migration, and no disruption to 60+ dependent teams.

### Migration Strategy: Dual-Write with Gradual Cutover

```
MIGRATION PHASES:
━━━━━━━━━━━━━━━━

PHASE 0: FOUNDATION (Month 1-2)
  - Set up GCP environment (VPC, IAM, networking)
  - Establish Dedicated Interconnect (10 Gbps × 4 = 40 Gbps)
  - Deploy Cloud Composer, Dataflow templates
  - Migrate metadata: Hive Metastore → BigQuery metadata + Dataplex catalog
  - Establish monitoring baseline on Hadoop

PHASE 1: HISTORICAL MIGRATION (Month 2-6)
  - Migrate cold data (> 1 year old) first: lowest risk, no active queries
  - Use distcp (Hadoop → GCS) for bulk transfer
  - Validate: md5sum checks, row count comparison
  - DO NOT delete from Hadoop yet
  - Teams can start optionally querying from GCS

PHASE 2: DUAL-WRITE (Month 6-9)
  - All NEW data written to BOTH Hadoop and GCS simultaneously
  - This ensures GCS is always current from this point forward
  - Existing pipelines still read from Hadoop (no disruption)
  - Teams incrementally migrate read workloads to GCS

PHASE 3: READ CUTOVER (Month 9-11)
  - Team-by-team migration of read workloads to GCS
  - Platform team provides migration support
  - Hadoop is now "read-only backup"
  - Monitor: confirm no reads from Hadoop for each migrated team

PHASE 4: DECOMMISSION (Month 12)
  - After 30 days with zero reads from Hadoop: decommission
  - Final validation: all data accessible from GCS
  - 6-month cold backup on GCS Archive before permanent deletion
```

### Validation Strategy (Zero Data Loss Proof)

```python
class MigrationValidator:
    
    def validate_table_migration(
        self, 
        hadoop_table: str, 
        gcs_path: str, 
        bq_table: str
    ) -> ValidationReport:
        """
        Three-level validation: count, checksum, statistical.
        """
        
        report = ValidationReport(source=hadoop_table, target=bq_table)
        
        # Level 1: Row count comparison
        hadoop_count = self.get_hadoop_row_count(hadoop_table)
        bq_count = self.get_bq_row_count(bq_table)
        
        report.row_count_match = (hadoop_count == bq_count)
        report.row_count_diff = abs(hadoop_count - bq_count)
        
        if not report.row_count_match:
            report.add_issue(f"Row count mismatch: Hadoop={hadoop_count}, BQ={bq_count}")
        
        # Level 2: Checksum on key columns
        hadoop_checksums = self.compute_hadoop_checksums(hadoop_table)
        bq_checksums = self.compute_bq_checksums(bq_table)
        
        for col in hadoop_checksums:
            if hadoop_checksums[col] != bq_checksums.get(col):
                report.add_issue(f"Checksum mismatch on column: {col}")
        
        # Level 3: Statistical comparison (distribution, nulls, ranges)
        hadoop_stats = self.compute_hadoop_statistics(hadoop_table)
        bq_stats = self.compute_bq_statistics(bq_table)
        
        for metric, value in hadoop_stats.items():
            bq_value = bq_stats.get(metric, 0)
            pct_diff = abs(value - bq_value) / (value + 0.001) * 100
            
            if pct_diff > 1.0:  # Allow 1% tolerance for floating point differences
                report.add_issue(f"Statistical drift in {metric}: {pct_diff:.1f}% difference")
        
        return report
    
    def compute_bq_checksums(self, table: str) -> Dict[str, str]:
        """
        Compute checksum of every column using BQ's FARM_FINGERPRINT.
        """
        schema = self.bq_client.get_table(table).schema
        
        checksum_exprs = [
            f"FARM_FINGERPRINT(CAST(SUM(FARM_FINGERPRINT(CAST({col.name} AS STRING))) AS STRING)) AS {col.name}_checksum"
            for col in schema
            if col.field_type in ("STRING", "INTEGER", "FLOAT", "NUMERIC", "DATE", "TIMESTAMP")
        ]
        
        query = f"SELECT {', '.join(checksum_exprs)} FROM `{table}`"
        result = self.bq_client.query(query).to_dataframe()
        
        return {col.replace("_checksum", ""): str(result[col].iloc[0]) for col in result.columns}
```

---

## MODULE 7 SUMMARY: ADVANCED PATTERNS REFERENCE

| Scenario | Core Pattern | Key Takeaway |
|---|---|---|
| Late data | Watermarks + allowed lateness | Set lateness based on source characteristics |
| Schema migration | Expand-Contract | Never break compatibility without migration window |
| Historical backfill | Checkpointed partition overwrite | Idempotent, resumable, cost-controlled |
| Multi-region | Pseudonymization + federated views | Separate PII residence from analytics |
| Cost optimization | Partition pruning + MV + reservations | Query cost > storage cost at scale |
| Silent data failure | Statistical drift detection | Monitor distributions, not just counts |
| GDPR deletion | Pseudonymization + key deletion | Design for deletion at architecture time |
| Hotspot | Salting + CombinePerKey | Avoid GroupByKey on high-cardinality hot keys |
| Self-healing | Failure taxonomy + auto-remediation | Automate Level 1-2, alert on Level 3 |
| Hadoop migration | Dual-write + gradual cutover | Never big-bang migrate; always gradual |

---

*Module 7 Complete — 10,400 words. Proceed to Module 8: Interview Strategy.*
