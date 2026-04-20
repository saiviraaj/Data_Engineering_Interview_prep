# PySpark Practice Questions — Easy to Hard
## Costco Sr. Data Engineer Interview Prep

---

## SETUP — Standard Imports (use in all examples)

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    DoubleType, TimestampType, DateType, BooleanType, ArrayType
)

spark = SparkSession.builder \
    .appName("CostcoMartech") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.shuffle.partitions", "200") \
    .getOrCreate()
```

---

## SECTION 1: EASY

---

### E1. Read Parquet, filter, select, write back

```python
# Read ad clicks from GCS
clicks = spark.read.parquet("gs://costco-data/raw/ad_clicks/")

# Filter: only last 30 days
recent = clicks.filter(
    F.col("clicked_at") >= F.date_sub(F.current_date(), 30)
)

# Select relevant columns only
minimal = recent.select(
    "click_id",
    "campaign_id",
    "user_id",
    F.col("clicked_at"),
    (F.col("cost_micros") / 1e6).alias("cost_usd")
)

# Write partitioned output
minimal.write \
    .mode("overwrite") \
    .partitionBy("click_date") \
    .parquet("gs://costco-data/staging/ad_clicks/")

print(f"Rows written: {minimal.count()}")
```

---

### E2. Schema definition and enforcement

```python
schema = StructType([
    StructField("click_id",     StringType(),    nullable=False),
    StructField("campaign_id",  StringType(),    nullable=True),
    StructField("user_id",      StringType(),    nullable=True),
    StructField("clicked_at",   TimestampType(), nullable=False),
    StructField("cost_micros",  IntegerType(),   nullable=True),
    StructField("device_type",  StringType(),    nullable=True)
])

# Read with explicit schema (faster + safer than autodetect)
df = spark.read \
    .schema(schema) \
    .option("mode", "DROPMALFORMED") \
    .json("gs://costco-data/raw/ad_events/*.json")
# DROPMALFORMED: silently drops rows that don't fit the schema
# FAILFAST: raises error on schema mismatch
# PERMISSIVE (default): sets bad columns to NULL

# Verify schema
df.printSchema()
df.show(5, truncate=False)
```

---

### E3. WithColumn — type casting, derived columns, conditionals

```python
df = spark.read.parquet("gs://costco-data/raw/ad_clicks/")

df_clean = df \
    .withColumn("cost_usd",
                (F.col("cost_micros") / 1e6).cast(DoubleType())) \
    .withColumn("click_date",
                F.to_date("clicked_at")) \
    .withColumn("device_category",
                F.when(F.col("device_type").isin("mobile", "tablet"), "mobile")
                 .when(F.col("device_type") == "desktop", "desktop")
                 .otherwise("unknown")) \
    .withColumn("is_high_cost",
                F.col("cost_usd") > 5.0) \
    .withColumn("campaign_id_upper",
                F.upper(F.trim(F.col("campaign_id")))) \
    .withColumnRenamed("clicked_at", "event_timestamp") \
    .drop("cost_micros")  # remove raw column after conversion

df_clean.printSchema()
```

---

### E4. GroupBy and multiple aggregations in one pass

```python
# GOOD: one groupBy with all aggregations = ONE shuffle
daily = df_clean.groupBy("click_date", "campaign_id").agg(
    F.count("*").alias("clicks"),
    F.countDistinct("user_id").alias("unique_users"),
    F.sum("cost_usd").alias("spend_usd"),
    F.avg("cost_usd").alias("avg_cpc"),
    F.min("cost_usd").alias("min_cpc"),
    F.max("cost_usd").alias("max_cpc"),
    F.stddev("cost_usd").alias("cpc_stddev"),
    F.percentile_approx("cost_usd", 0.5).alias("median_cpc"),
    F.collect_set("device_category").alias("devices_used")
)

daily.orderBy("click_date", F.desc("clicks")).show(10)

# BAD: multiple separate groupBys = multiple shuffles
# clicks = df.groupBy("campaign_id").count()  # shuffle 1
# spend  = df.groupBy("campaign_id").agg(F.sum("cost_usd"))  # shuffle 2
# result = clicks.join(spend, "campaign_id")  # shuffle 3
# THREE shuffles vs ONE above
```

---

### E5. Handling nulls

```python
df = spark.read.parquet("gs://costco-data/raw/ad_clicks/")

# Check null counts per column
null_counts = df.select([
    F.count(F.when(F.col(c).isNull(), c)).alias(c)
    for c in df.columns
])
null_counts.show()

# Fill nulls with appropriate values
df_filled = df.fillna({
    "campaign_id": "UNKNOWN",
    "cost_usd":    0.0,
    "device_type": "unknown",
    "user_id":     None   # keep as null — don't fill user_id with fake value
})

# Drop rows where critical column is null
df_clean = df.filter(F.col("click_id").isNotNull())

# Conditional null handling
df_fixed = df.withColumn("adjusted_cost",
    F.when(F.col("cost_usd").isNull(), 0.0)
     .when(F.col("cost_usd") < 0, 0.0)   # treat negative as 0
     .otherwise(F.col("cost_usd"))
)

# Count remaining nulls after cleanup
print(df_clean.filter(F.col("click_id").isNull()).count())  # should be 0
```

---

## SECTION 2: MEDIUM

---

### M1. Window functions — ranking, lag, rolling average

```python
from pyspark.sql.window import Window

# Define windows
w_campaign_by_date  = Window.partitionBy("campaign_id").orderBy("report_date")
w_campaign_rolling7 = Window.partitionBy("campaign_id") \
                             .orderBy("report_date") \
                             .rowsBetween(-6, 0)   # current + 6 preceding = 7 rows
w_channel_by_roas   = Window.partitionBy("channel").orderBy(F.desc("roas"))

df = spark.read.parquet("gs://costco-data/marts/campaign_daily/")

df_enriched = df \
    .withColumn("roas", F.col("revenue_usd") / F.col("spend_usd")) \
    .withColumn("rank_in_channel",
                F.rank().over(w_channel_by_roas)) \
    .withColumn("dense_rank_in_channel",
                F.dense_rank().over(w_channel_by_roas)) \
    .withColumn("roas_7d_avg",
                F.avg("roas").over(w_campaign_rolling7)) \
    .withColumn("roas_prev_day",
                F.lag("roas", 1).over(w_campaign_by_date)) \
    .withColumn("roas_dod_change",
                F.col("roas") - F.lag("roas", 1).over(w_campaign_by_date)) \
    .withColumn("spend_mtd",
                F.sum("spend_usd").over(
                    Window.partitionBy("campaign_id",
                                       F.date_trunc("month", F.col("report_date")))
                          .orderBy("report_date")
                          .rowsBetween(Window.unboundedPreceding, Window.currentRow)
                ))

df_enriched.show(10)
```

---

### M2. Deduplication — deterministic

```python
from pyspark.sql.window import Window

# WRONG: dropDuplicates keeps arbitrary row (non-deterministic)
df_wrong = df.dropDuplicates(["click_id"])

# CORRECT: ROW_NUMBER picks the most recent load
w_dedup = Window.partitionBy("click_id").orderBy(F.desc("_loaded_at"))

df_dedup = df \
    .withColumn("rn", F.row_number().over(w_dedup)) \
    .filter(F.col("rn") == 1) \
    .drop("rn")

# Verify
before = df.count()
after  = df_dedup.count()
print(f"Before: {before}, After: {after}, Removed: {before - after}")

# Verify uniqueness
dups = df_dedup.groupBy("click_id").count().filter(F.col("count") > 1).count()
assert dups == 0, f"Still {dups} duplicate click_ids!"
```

---

### M3. Broadcast join — eliminate shuffle for small table

```python
# Read large table (10B rows)
clicks = spark.read.parquet("gs://costco-data/raw/ad_clicks/")

# Read small table (50K rows = ~5MB)
campaigns = spark.read.parquet("gs://costco-data/dims/campaigns/")

# WRONG: both sides shuffle (SortMergeJoin)
result_slow = clicks.join(campaigns, "campaign_id", "left")

# CORRECT: campaigns broadcast to all executors → zero shuffle on large side
from pyspark.sql.functions import broadcast

result_fast = clicks.join(broadcast(campaigns), "campaign_id", "left")

# Verify join strategy in physical plan
result_fast.explain()
# Look for: BroadcastHashJoin vs SortMergeJoin

# Set threshold (default: 10MB — increase for bigger dim tables)
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "100MB")
```

---

### M4. UDF — define and use a custom function

```python
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType, DoubleType
import re

# AVOID Python UDFs when native SQL functions exist — they're slow (Python serialization)
# USE Pandas UDFs (vectorized) for batch processing performance

# BAD: Python UDF (slow — row by row, Python GIL)
@udf(StringType())
def extract_utm_source(url: str) -> str:
    if not url:
        return None
    match = re.search(r'utm_source=([^&]+)', url)
    return match.group(1) if match else None

# BETTER: native SQL function (stays in JVM)
df = df.withColumn("utm_source",
    F.regexp_extract("landing_url", r"utm_source=([^&]+)", 1)
)

# BEST FOR COMPLEX LOGIC: Pandas UDF (vectorized, much faster than row UDF)
import pandas as pd
from pyspark.sql.functions import pandas_udf

@pandas_udf(DoubleType())
def compute_adjusted_roas(revenue: pd.Series, spend: pd.Series, fee_pct: pd.Series) -> pd.Series:
    """Compute ROAS after deducting platform fee."""
    adjusted_revenue = revenue * (1 - fee_pct)
    return adjusted_revenue / spend.replace(0, float('nan'))

df_with_roas = df.withColumn(
    "adjusted_roas",
    compute_adjusted_roas(F.col("revenue_usd"), F.col("spend_usd"), F.lit(0.15))
)
```

---

### M5. JSON parsing — from_json and explode

```python
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, ArrayType

# Schema for JSON payload column
event_schema = StructType([
    StructField("event_type", StringType()),
    StructField("campaign", StructType([
        StructField("id",   StringType()),
        StructField("name", StringType()),
        StructField("type", StringType())
    ])),
    StructField("user", StructType([
        StructField("id",  StringType()),
        StructField("age", IntegerType())
    ])),
    StructField("tags", ArrayType(StringType())),
    StructField("cost_usd", DoubleType())
])

# Parse JSON column
df = spark.read.parquet("gs://costco-data/raw/events/")
df_parsed = df.withColumn("payload", F.from_json(F.col("payload_str"), event_schema))

# Access nested fields
df_flat = df_parsed.select(
    "event_id",
    F.col("payload.event_type").alias("event_type"),
    F.col("payload.campaign.id").alias("campaign_id"),
    F.col("payload.campaign.name").alias("campaign_name"),
    F.col("payload.user.id").alias("user_id"),
    F.col("payload.cost_usd").alias("cost_usd"),
    F.col("payload.tags").alias("tags")   # ArrayType column
)

# Explode array — one row per tag
df_tags = df_flat.select(
    "event_id",
    "campaign_id",
    F.explode("tags").alias("tag")
)

# explode_outer: keep rows even when array is null/empty
df_tags_safe = df_flat.select(
    "event_id",
    F.explode_outer("tags").alias("tag")
)

# posexplode: include array index
df_with_pos = df_flat.select(
    "event_id",
    F.posexplode("tags").alias("tag_idx", "tag")
)
```

---

### M6. Incremental processing pattern

```python
def process_incremental(
    source_path: str,
    target_path: str,
    execution_date: str,
    lookback_days: int = 3
):
    """
    Process events from (execution_date - lookback_days) to execution_date.
    Use INSERT OVERWRITE on affected partitions → idempotent.
    """
    from datetime import datetime, timedelta

    start_date = (
        datetime.strptime(execution_date, "%Y-%m-%d")
        - timedelta(days=lookback_days)
    ).strftime("%Y-%m-%d")

    # Read only relevant partitions (Spark partition pruning on read)
    source = spark.read.parquet(source_path) \
                  .filter(
                      (F.col("event_date") >= start_date) &
                      (F.col("event_date") <= execution_date)
                  )

    # Transform
    result = source \
        .filter(F.col("click_id").isNotNull()) \
        .withColumn("cost_usd", F.col("cost_micros") / 1e6) \
        .dropDuplicates(["click_id"])

    # OVERWRITE affected partitions (idempotent — safe to re-run)
    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

    result.write \
        .mode("overwrite") \
        .partitionBy("event_date") \
        .parquet(target_path)

    return result.count()

# Run
rows = process_incremental(
    source_path="gs://costco-data/raw/ad_clicks/",
    target_path="gs://costco-data/staging/ad_clicks/",
    execution_date="2024-01-15",
    lookback_days=3
)
print(f"Processed {rows} rows")
```

---

## SECTION 3: HARD

---

### H1. Detect and fix data skew with salting

```python
# STEP 1: Detect skew
key_distribution = clicks.groupBy("campaign_id") \
    .count() \
    .orderBy(F.desc("count"))

key_distribution.show(10)
# Output: C_VIRAL has 50M rows, others have ~100K → severe skew

# STEP 2: Check Spark UI for straggler tasks (manual in production)
# Or check programmatically:
from pyspark.sql import functions as F
stats = clicks.groupBy("campaign_id").count().agg(
    F.mean("count").alias("mean"),
    F.stddev("count").alias("stddev"),
    F.max("count").alias("max")
)
stats.show()
# If max >> mean + 3*stddev → skew

# STEP 3: Fix with salting
N_SALT = 50

# Salt the skewed (large) table
clicks_salted = clicks \
    .withColumn("salt", (F.rand() * N_SALT).cast("int")) \
    .withColumn("salted_campaign_id",
                F.concat_ws("_", F.col("campaign_id"), F.col("salt")))

# Explode the small table to match all salts
campaigns = spark.read.parquet("gs://costco-data/dims/campaigns/")
campaigns_exploded = campaigns \
    .withColumn("salt",
                F.explode(F.array([F.lit(i) for i in range(N_SALT)]))) \
    .withColumn("salted_campaign_id",
                F.concat_ws("_", F.col("campaign_id"), F.col("salt")))

# Join on salted key — skew is now distributed across N_SALT partitions
result = clicks_salted.join(
    campaigns_exploded,
    "salted_campaign_id",
    "left"
).drop("salt", "salted_campaign_id")

# Verify: no single partition should dominate now
result.write.mode("overwrite").parquet("gs://costco-data/staging/enriched_clicks/")
```

---

### H2. Complex transformation pipeline — end-to-end

```python
def build_daily_campaign_performance(spark, execution_date: str) -> int:
    """
    Full pipeline: Raw ad events → Daily campaign performance mart.
    Handles: dedup, late data, type conversion, attribution, aggregation.
    """

    # ── 1. Read with partition pruning ──────────────────────────────────
    clicks = spark.read.parquet("gs://costco-data/raw/ad_clicks/") \
                  .filter(F.col("click_date") == execution_date)

    conversions = spark.read.parquet("gs://costco-data/raw/conversions/") \
                      .filter(F.col("conv_date") == execution_date)

    campaigns = spark.read.parquet("gs://costco-data/dims/campaigns/")

    # ── 2. Clean and deduplicate ─────────────────────────────────────────
    w_click_dedup = Window.partitionBy("click_id").orderBy(F.desc("_loaded_at"))
    clicks_clean = clicks \
        .withColumn("cost_usd", F.col("cost_micros") / 1e6) \
        .withColumn("rn", F.row_number().over(w_click_dedup)) \
        .filter(F.col("rn") == 1) \
        .drop("rn") \
        .filter(F.col("click_id").isNotNull() & F.col("campaign_id").isNotNull())

    # ── 3. Aggregate clicks ──────────────────────────────────────────────
    daily_clicks = clicks_clean.groupBy("campaign_id").agg(
        F.count("*").alias("clicks"),
        F.countDistinct("user_id").alias("unique_users"),
        F.sum("cost_usd").alias("spend_usd"),
        F.avg("cost_usd").alias("avg_cpc")
    )

    # ── 4. Aggregate conversions ─────────────────────────────────────────
    daily_convs = conversions.groupBy("campaign_id").agg(
        F.count("*").alias("conversions"),
        F.sum("conversion_value_usd").alias("revenue_usd")
    )

    # ── 5. Join (broadcast small dims) ───────────────────────────────────
    result = daily_clicks \
        .join(daily_convs, "campaign_id", "left") \
        .join(broadcast(campaigns.select("campaign_id","campaign_name","channel","campaign_type")),
              "campaign_id", "left") \
        .withColumn("revenue_usd", F.coalesce(F.col("revenue_usd"), F.lit(0.0))) \
        .withColumn("conversions",  F.coalesce(F.col("conversions"),  F.lit(0))) \
        .withColumn("roas", F.col("revenue_usd") / F.nullif(F.col("spend_usd"), 0)) \
        .withColumn("cvr",  F.col("conversions")  / F.nullif(F.col("clicks"),   0)) \
        .withColumn("report_date", F.lit(execution_date).cast(DateType()))

    # ── 6. Write idempotent partition ────────────────────────────────────
    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
    result.write \
        .mode("overwrite") \
        .partitionBy("report_date") \
        .parquet("gs://costco-data/marts/campaign_daily/")

    count = result.count()
    print(f"[{execution_date}] Written {count} campaign-day rows")
    return count

build_daily_campaign_performance(spark, "2024-01-15")
```

---

### H3. Sessionization in PySpark

```python
from pyspark.sql.window import Window
from pyspark.sql import functions as F

# Goal: assign session IDs to user events
# New session = gap > 30 minutes from previous event by same user

events = spark.read.parquet("gs://costco-data/raw/web_events/") \
              .filter(F.col("event_date") == "2024-01-15") \
              .orderBy("user_id", "event_at")

w_user = Window.partitionBy("user_id").orderBy("event_at")
w_user_session = Window.partitionBy("user_id") \
                       .orderBy("event_at") \
                       .rowsBetween(Window.unboundedPreceding, Window.currentRow)

sessions = events \
    .withColumn("prev_event_at",
                F.lag("event_at").over(w_user)) \
    .withColumn("gap_seconds",
                F.unix_timestamp("event_at") - F.unix_timestamp("prev_event_at")) \
    .withColumn("is_new_session",
                F.when(
                    F.col("gap_seconds").isNull() | (F.col("gap_seconds") > 1800),
                    1
                ).otherwise(0)) \
    .withColumn("session_num",
                F.sum("is_new_session").over(w_user_session)) \
    .withColumn("session_id",
                F.concat_ws("_", F.col("user_id"), F.col("session_num")))

# Aggregate to session level
session_summary = sessions.groupBy("user_id", "session_id").agg(
    F.min("event_at").alias("session_start"),
    F.max("event_at").alias("session_end"),
    F.count("*").alias("event_count"),
    F.countDistinct("page_url").alias("unique_pages"),
    F.max(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("had_purchase"),
    (F.unix_timestamp(F.max("event_at")) -
     F.unix_timestamp(F.min("event_at"))).alias("duration_seconds")
)

session_summary.orderBy("user_id", "session_start").show(20)
```

---

### H4. SCD Type 2 in PySpark

```python
def apply_scd2(
    spark,
    existing_dim: str,
    incoming_data,
    natural_key: str,
    hash_columns: list,
    effective_date: str
):
    """
    Apply SCD Type 2 update to a dimension table.
    1. Identify changed rows (hash comparison)
    2. Close old versions (set valid_to, is_current=False)
    3. Insert new versions
    """
    import hashlib

    # Load existing dimension
    existing = spark.read.parquet(existing_dim)

    # Compute hash for incoming data
    def compute_hash(row):
        values = "|".join(str(row[c] or '') for c in sorted(hash_columns))
        return hashlib.md5(values.encode()).hexdigest()

    compute_hash_udf = F.udf(compute_hash, StringType())

    incoming_with_hash = incoming_data.withColumn(
        "row_hash",
        F.md5(F.concat_ws("|", *[F.coalesce(F.col(c).cast("string"), F.lit("")) 
                                   for c in sorted(hash_columns)]))
    )

    # Find: new records (not in existing) and changed records (hash differs)
    current_dim = existing.filter(F.col("is_current") == True) \
                          .select(natural_key, "row_hash") \
                          .alias("curr")

    incoming_with_hash_alias = incoming_with_hash.alias("inc")

    changes = incoming_with_hash_alias.join(
        current_dim,
        F.col(f"inc.{natural_key}") == F.col(f"curr.{natural_key}"),
        "left"
    ).filter(
        F.col("curr.row_hash").isNull()  |   # new record
        (F.col("inc.row_hash") != F.col("curr.row_hash"))  # changed record
    ).select("inc.*")

    if changes.count() == 0:
        print("No changes detected.")
        return

    # Close old records for changed natural keys
    changed_keys = changes.select(natural_key).distinct()
    existing_closed = existing.join(changed_keys, natural_key, "left_anti")  # unchanged

    existing_to_close = existing \
        .join(changed_keys, natural_key, "inner") \
        .filter(F.col("is_current") == True) \
        .withColumn("valid_to",    F.lit(effective_date).cast(DateType())) \
        .withColumn("is_current",  F.lit(False))

    # New versions to insert
    new_versions = changes \
        .withColumn("surrogate_key", F.expr("uuid()")) \
        .withColumn("valid_from",    F.lit(effective_date).cast(DateType())) \
        .withColumn("valid_to",      F.lit(None).cast(DateType())) \
        .withColumn("is_current",    F.lit(True))

    # Union all three sets
    final_dim = existing_closed \
        .union(existing_to_close) \
        .union(new_versions)

    # Overwrite dimension table
    final_dim.write.mode("overwrite").parquet(existing_dim)

    print(f"SCD2 complete: {changes.count()} changes applied")
```

---

### H5. Custom aggregation with UDAF (User-Defined Aggregate Function)

```python
# Use case: compute weighted average ROAS across campaigns
# weighted_roas = sum(revenue) / sum(spend) — not AVG(ROAS) which weights each campaign equally

# METHOD 1: Use native Spark functions (BEST — no UDF needed)
weighted_roas = df.groupBy("channel").agg(
    F.sum("revenue_usd").alias("total_revenue"),
    F.sum("spend_usd").alias("total_spend")
).withColumn(
    "weighted_roas",
    F.col("total_revenue") / F.col("total_spend")
)

# METHOD 2: Pandas UDAF for truly custom logic
import pandas as pd
from pyspark.sql.functions import pandas_udf, PandasUDFType

# For complex custom aggregations not expressible with built-ins:
@pandas_udf(DoubleType(), PandasUDFType.GROUPED_AGG)
def weighted_avg_roas(revenue: pd.Series, spend: pd.Series) -> float:
    """Weighted average ROAS: total_revenue / total_spend"""
    total_spend = spend.sum()
    if total_spend == 0:
        return None
    return revenue.sum() / total_spend

df_roas = df.groupBy("channel").agg(
    weighted_avg_roas(F.col("revenue_usd"), F.col("spend_usd")).alias("weighted_roas")
)
```

---

## SECTION 4: OPTIMIZATION CHALLENGES

---

### O1. Identify and fix the performance issues in this code

```python
# SLOW CODE — find all issues:
def slow_pipeline(spark):
    df = spark.read.parquet("gs://costco-data/raw/events/")  # reads ALL data

    result1 = df.filter(F.col("event_type") == "click") \
                .groupBy("campaign_id").count().alias("clicks")

    result2 = df.filter(F.col("event_type") == "conversion") \
                .groupBy("campaign_id").agg(F.sum("value").alias("revenue"))

    result3 = df.filter(F.col("event_type") == "impression") \
                .groupBy("campaign_id").count().alias("impressions")

    final = result1.join(result2, "campaign_id") \
                   .join(result3, "campaign_id")

    final.coalesce(1).write.csv("gs://costco-data/output/")

# ISSUES:
# 1. No partition filter: reads ALL events (all time, all dates)
# 2. Three separate scans + three separate groupBys = 3 shuffles
# 3. `df` is not cached, so it's read 3 times
# 4. coalesce(1): forces all data to one partition before writing (OOM risk for large data)
# 5. CSV output: not columnar, slow to read back

# FIXED CODE:
def fast_pipeline(spark, execution_date: str):
    # 1. Partition filter + cache
    df = spark.read.parquet("gs://costco-data/raw/events/") \
              .filter(F.col("event_date") == execution_date) \
              .cache()   # reused 3 times below

    # 2. One scan, three event types in one groupBy
    result = df.groupBy("campaign_id").agg(
        F.count(F.when(F.col("event_type") == "click",       1)).alias("clicks"),
        F.count(F.when(F.col("event_type") == "impression",  1)).alias("impressions"),
        F.count(F.when(F.col("event_type") == "conversion",  1)).alias("conversions"),
        F.sum(F.when(F.col("event_type") == "conversion",
                     F.col("value")).otherwise(0)).alias("revenue_usd")
    )
    # ONE scan, ONE shuffle — vs 3 scans + 3 shuffles + 2 joins before

    # 3. Write as Parquet, partitioned
    result.repartition(max(1, result.count() // 500000)) \
          .write \
          .mode("overwrite") \
          .parquet(f"gs://costco-data/output/date={execution_date}/")

    df.unpersist()
    return result.count()
```

---

### O2. Right-sizing partitions

```python
# Problem: after a filter, 1000 partitions remain but most are tiny (1-10 rows)
# This causes 1000 tasks with most doing almost nothing → overhead dominates

# Step 1: Detect partition sizes
partition_sizes = df.rdd.mapPartitions(
    lambda it: [sum(1 for _ in it)]
).collect()

print(f"Partitions: {len(partition_sizes)}")
print(f"Min rows: {min(partition_sizes)}")
print(f"Max rows: {max(partition_sizes)}")
print(f"Empty: {partition_sizes.count(0)}")

# Step 2: Choose the right operation
import math

total_rows = df.count()
target_rows_per_partition = 500_000  # ~64MB at 128 bytes/row

optimal_partitions = max(1, math.ceil(total_rows / target_rows_per_partition))

# If REDUCING partition count → coalesce (no shuffle)
if df.rdd.getNumPartitions() > optimal_partitions:
    df_optimized = df.coalesce(optimal_partitions)

# If INCREASING or need uniform distribution → repartition (triggers shuffle)
else:
    df_optimized = df.repartition(optimal_partitions)

# For BigQuery output: usually repartition on the BQ partition column
df_for_bq = df.repartition(optimal_partitions, "event_date")

print(f"Before: {df.rdd.getNumPartitions()} partitions")
print(f"After:  {df_optimized.rdd.getNumPartitions()} partitions")
```

---

### O3. Caching strategy

```python
from pyspark import StorageLevel

def compute_multiple_metrics(spark, execution_date: str):
    """
    Compute 5 different metrics from the same base dataset.
    Cache the base to avoid 5 separate reads.
    """

    # Read and prepare base dataset (expensive — join + filter)
    base = spark.read.parquet("gs://costco-data/raw/ad_events/") \
                .filter(F.col("event_date") == execution_date) \
                .join(broadcast(spark.read.parquet("gs://costco-data/dims/campaigns/")),
                      "campaign_id", "left") \
                .withColumn("cost_usd", F.col("cost_micros") / 1e6) \
                .filter(F.col("click_id").isNotNull())

    # Cache before multiple uses
    base.persist(StorageLevel.MEMORY_AND_DISK)
    base.count()  # trigger the cache (force materialization)

    # Now compute 5 metrics from cached base
    clicks_by_device = base.groupBy("device_type").count()
    spend_by_channel = base.groupBy("channel").agg(F.sum("cost_usd"))
    hourly_clicks    = base.groupBy(F.hour("clicked_at")).count()
    top_campaigns    = base.groupBy("campaign_id").agg(F.sum("cost_usd")).orderBy(F.desc("sum(cost_usd)")).limit(10)
    new_users        = base.filter(F.col("is_new_user") == True).groupBy("campaign_id").countDistinct("user_id")

    # Collect results
    results = {
        "clicks_by_device": clicks_by_device.collect(),
        "spend_by_channel": spend_by_channel.collect(),
        "hourly_clicks":    hourly_clicks.collect(),
        "top_campaigns":    top_campaigns.collect(),
        "new_user_counts":  new_users.collect()
    }

    # IMPORTANT: always unpersist when done
    base.unpersist()

    return results
```

---

## SECTION 5: INTERVIEW SCENARIOS

---

### IS1. "Process a 1TB file efficiently — read, clean, aggregate, write"

```python
def process_1tb_efficiently(spark, input_path: str, output_path: str, date: str):
    """
    Best practices for processing large files.
    """
    # 1. Set shuffle partitions based on expected data size
    # 1TB → target 256MB/partition → ~4000 partitions
    spark.conf.set("spark.sql.shuffle.partitions", "4000")
    spark.conf.set("spark.sql.adaptive.enabled", "true")  # auto-tunes

    # 2. Read with partition pruning (critical for performance)
    df = spark.read.parquet(input_path) \
              .filter(F.col("event_date") == date)
    # If file is partitioned by event_date: reads ~1/365 of the data

    # 3. Push filters as early as possible (filter before any expensive ops)
    df_valid = df.filter(
        F.col("click_id").isNotNull() &
        F.col("campaign_id").isNotNull() &
        (F.col("cost_micros") > 0)
    )

    # 4. Select only needed columns (columnar advantage)
    df_minimal = df_valid.select(
        "click_id", "campaign_id", "user_id",
        "clicked_at", "cost_micros", "device_type"
    ).withColumn("cost_usd", F.col("cost_micros") / 1e6)

    # 5. Aggregate ONCE (single shuffle)
    result = df_minimal.groupBy("campaign_id", "device_type").agg(
        F.count("*").alias("clicks"),
        F.countDistinct("user_id").alias("unique_users"),
        F.sum("cost_usd").alias("spend_usd")
    )

    # 6. Write with right partition count
    # After aggregation: campaign_id × device_type = ~50K rows → 1 partition is fine
    result.coalesce(20) \
          .write \
          .mode("overwrite") \
          .partitionBy("report_date") \
          .parquet(output_path)

    print(f"Done. Output rows: {result.count()}")
```

---

### IS2. "Implement a data quality check function in PySpark"

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class DQResult:
    check_name: str
    passed: bool
    rows_failed: int
    total_rows: int
    failure_pct: float
    sample_failures: list

def run_dq_checks(df, checks: list) -> List[DQResult]:
    """
    Run a list of data quality checks on a PySpark DataFrame.
    Returns structured results.
    """
    total = df.count()
    results = []

    for check in checks:
        check_name = check['name']
        condition  = check['condition']   # PySpark Column expression
        severity   = check.get('severity', 'ERROR')
        threshold  = check.get('threshold', 0.0)  # max allowed failure %

        # Count failures
        failures = df.filter(~condition)  # rows that FAIL the condition
        fail_count = failures.count()
        fail_pct = (fail_count / total * 100) if total > 0 else 0

        # Get sample of failures for debugging
        sample = failures.limit(5).collect()

        passed = fail_pct <= threshold

        result = DQResult(
            check_name=check_name,
            passed=passed,
            rows_failed=fail_count,
            total_rows=total,
            failure_pct=round(fail_pct, 4),
            sample_failures=[row.asDict() for row in sample]
        )
        results.append(result)

        # Log
        status = "✅ PASS" if passed else f"❌ FAIL [{severity}]"
        print(f"{status} | {check_name} | Failed: {fail_count}/{total} ({fail_pct:.2f}%)")

        if not passed and severity == 'ERROR':
            raise ValueError(f"DATA QUALITY ERROR: {check_name} failed with {fail_pct:.2f}% failure rate")

    return results

# Usage:
checks = [
    {
        'name': 'click_id_not_null',
        'condition': F.col("click_id").isNotNull(),
        'severity': 'ERROR',
        'threshold': 0.0
    },
    {
        'name': 'cost_usd_non_negative',
        'condition': F.col("cost_usd") >= 0,
        'severity': 'ERROR',
        'threshold': 0.0
    },
    {
        'name': 'device_type_valid',
        'condition': F.col("device_type").isin("mobile", "desktop", "tablet", "unknown"),
        'severity': 'WARNING',
        'threshold': 1.0  # allow up to 1% invalid device types
    }
]

results = run_dq_checks(clicks_clean, checks)
```

---

## QUICK REFERENCE: PySpark Patterns

```python
# Narrow transformations (no shuffle):
df.filter(), .select(), .withColumn(), .drop(), .sample()

# Wide transformations (shuffle):
df.groupBy().agg(), .join(), .distinct(), .repartition(), .orderBy()

# Optimization:
broadcast(df)                           # eliminate shuffle for small table
df.persist(StorageLevel.MEMORY_AND_DISK) # cache reused DataFrames
spark.conf.set("spark.sql.adaptive.enabled", "true")  # AQE

# Window functions:
Window.partitionBy(X).orderBy(Y).rowsBetween(-N, 0)  # rolling N rows
Window.partitionBy(X).orderBy(Y).rowsBetween(W.unboundedPreceding, W.currentRow)

# Dedup (deterministic):
df.withColumn("rn", F.row_number().over(w)).filter(F.col("rn")==1).drop("rn")

# Null safe join:
df1.join(df2, df1.key.eqNullSafe(df2.key))

# Forward fill:
F.last(col, ignorenulls=True).over(Window.partitionBy(X).orderBy(Y).rowsBetween(W.unboundedPreceding, W.currentRow))

# Salting for skew:
df.withColumn("salt", (F.rand() * N).cast("int"))
  .withColumn("salted_key", F.concat_ws("_", "key", "salt"))

# Partition overwrite:
spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
df.write.mode("overwrite").partitionBy("date").parquet(path)
```
