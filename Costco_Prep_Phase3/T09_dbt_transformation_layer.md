# Topic 9: DBT & Transformation Layer
## Costco Sr. Data Engineer — Exhaustive Interview Textbook

---

## Table of Contents
1. [L1: Core Concepts — DBT Basics](#l1-core-concepts)
2. [L2: Deep Technical Understanding](#l2-deep-technical-understanding)
3. [L3: Real-World Scenarios — Costco/MarTech Style](#l3-real-world-scenarios)
4. [L4: Hands-On Models & Code](#l4-hands-on-models--code)
5. [L5: Edge Cases & Pitfalls](#l5-edge-cases--pitfalls)
6. [L6: Interview Questions — Easy to Very Hard](#l6-interview-questions)

---

## L1: Core Concepts

### 1.1 What is DBT and Why It Exists

DBT (Data Build Tool) is a transformation framework that lets data engineers write modular SQL SELECT statements and handles the rest: dependency management, testing, documentation, and lineage.

**The core philosophy**: You write only the transformation logic as a SELECT statement. DBT wraps it in the appropriate `CREATE TABLE AS` or `CREATE VIEW AS` based on your configuration. You never write DDL.

**What DBT solves**:

| Problem Before DBT | How DBT Solves It |
|--------------------|-------------------|
| No dependency management — manually track what runs before what | `ref()` creates a DAG automatically |
| No testing — data quality is an afterthought | Built-in testing framework |
| No documentation — tribal knowledge | YAML-based docs with `dbt docs generate` |
| No version control integration | Plain .sql/.yml files → git |
| No lineage — can't trace raw data to dashboard | DAG shows full data lineage |
| Hardcoded schemas — breaks between dev/prod | `ref()` and `source()` resolve names at runtime |

**DBT's position in the stack**:
```
Sources (BigQuery raw tables, GCS files)
    ↓
DBT (Transform: SELECT-based SQL models)
    ↓
Marts (BigQuery tables ready for BI)
    ↓
Looker / Tableau / Business Users
```

---

### 1.2 The Four Materializations

| Materialization | What DBT Creates | Run Behavior | Best For |
|----------------|-----------------|--------------|----------|
| `view` | SQL view | Query time — no data stored | Staging models, lightweight logic |
| `table` | Physical table | Full rebuild every run | Small-medium marts |
| `incremental` | Physical table | Processes only new/changed rows | Large event tables |
| `ephemeral` | CTE (inlined) | Never persisted; inlined into consumer | Reusable logic, no standalone value |

---

### 1.3 The ref() and source() Functions

**`ref('model_name')`**: References another DBT model. Does two things:
1. Resolves the fully qualified name at runtime (handles dev/prod schema differences)
2. Creates a DAG dependency — DBT knows model B must run after model A

**`source('source_name', 'table_name')`**: References a raw table that DBT doesn't manage. Creates a node in the DAG so lineage starts from the source.

```sql
-- WRONG: hardcoded — breaks in CI, breaks in other environments
SELECT * FROM `costco-prod.raw.google_ads_clicks`

-- CORRECT: ref() and source()
SELECT * FROM {{ source('google_ads', 'raw_clicks') }}   -- for raw tables
SELECT * FROM {{ ref('stg_ad_clicks') }}                  -- for other models
```

---

## L2: Deep Technical Understanding

### 2.1 DBT Project Structure — Production Grade

```
dbt_project/
├── dbt_project.yml              # Master config: name, profiles, model configs
├── profiles.yml                 # Connection config (usually ~/.dbt/profiles.yml)
├── packages.yml                 # External packages
│
├── models/
│   ├── staging/                 # 1:1 with sources. Clean, rename, cast. NO business logic.
│   │   ├── _sources.yml         # source() definitions
│   │   ├── _stg_google_ads.yml  # model docs + tests
│   │   ├── stg_google_ads__clicks.sql
│   │   └── stg_google_ads__campaigns.sql
│   ├── intermediate/            # Business logic: joins, sessionization, attribution
│   │   ├── int_attributed_conversions.sql
│   │   └── int_member_ad_sessions.sql
│   └── marts/
│       ├── marketing/
│       │   ├── _schema.yml
│       │   ├── mart_campaign_performance.sql
│       │   └── mart_roas_by_channel.sql
│       └── member/
│           └── mart_member_ltv.sql
│
├── snapshots/                   # SCD Type 2
│   └── scd_campaigns.sql
│
├── seeds/                       # Static CSV lookup tables
│   └── channel_mapping.csv
│
├── tests/                       # Singular (custom) tests
│   └── assert_roas_non_negative.sql
│
├── macros/                      # Reusable Jinja macros
│   ├── generate_schema_name.sql # Override dev/prod schema naming
│   └── safe_divide.sql
│
└── target/                      # Auto-generated: compiled SQL + artifacts
    ├── compiled/                # Jinja-resolved SQL
    └── manifest.json            # Full DAG + metadata (critical for CI/CD)
```

**dbt_project.yml** — master configuration:

```yaml
name: 'costco_martech'
version: '1.0.0'
profile: 'costco_martech'

model-paths: ["models"]
test-paths: ["tests"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]
seed-paths: ["seeds"]

models:
  costco_martech:
    staging:
      +materialized: view           # all staging = views
      +schema: staging
      +tags: ['staging']
    intermediate:
      +materialized: ephemeral      # never persisted
      +tags: ['intermediate']
    marts:
      +materialized: table          # marts = physical tables
      +schema: marts
      +tags: ['marts']
      marketing:
        +tags: ['marketing', 'daily']
        +post-hook: "GRANT SELECT ON {{ this }} TO ROLE `analyst@costco.com`"
```

---

### 2.2 Models — Staging → Intermediate → Mart

**Staging layer rules**:
- ONLY: rename columns, cast types, basic cleaning (TRIM, LOWER, null handling)
- NEVER: join to other tables, apply business logic, aggregate
- Mirrors source: one staging model per source table

```sql
-- models/staging/stg_google_ads__clicks.sql
-- GOOD staging model:

WITH source AS (
    SELECT * FROM {{ source('google_ads', 'raw_clicks') }}
),

renamed AS (
    SELECT
        click_id,
        campaign_id,
        ad_group_id,
        user_id,
        -- Type casts
        CAST(clicked_at AS TIMESTAMP)       AS clicked_at,
        DATE(clicked_at)                    AS click_date,
        -- Unit conversion
        COALESCE(cost_micros, 0) / 1e6      AS cost_usd,
        -- Standardize string values
        LOWER(TRIM(device_type))            AS device_type,
        LOWER(TRIM(match_type))             AS match_type,
        -- Audit
        _loaded_at
    FROM source
    WHERE click_id IS NOT NULL   -- basic filter only
),

deduplicated AS (
    SELECT *
    FROM (
        SELECT *,
               ROW_NUMBER() OVER (
                   PARTITION BY click_id ORDER BY _loaded_at DESC
               ) AS rn
        FROM renamed
    )
    WHERE rn = 1
)

SELECT * EXCEPT (rn) FROM deduplicated
```

**Intermediate layer**: Pure business logic. Never queried directly by BI.

```sql
-- models/intermediate/int_attributed_conversions.sql

WITH clicks AS (
    SELECT * FROM {{ ref('stg_google_ads__clicks') }}
),

conversions AS (
    SELECT * FROM {{ ref('stg_conversions') }}
),

-- Last-touch attribution with 30-day lookback
attributed AS (
    SELECT
        c.conversion_id,
        c.user_id,
        c.converted_at,
        c.conversion_value_usd,
        cl.click_id         AS attributed_click_id,
        cl.campaign_id,
        cl.clicked_at,
        TIMESTAMP_DIFF(c.converted_at, cl.clicked_at, HOUR) AS hours_to_convert,
        ROW_NUMBER() OVER (
            PARTITION BY c.conversion_id
            ORDER BY cl.clicked_at DESC   -- last click
        ) AS touch_rank
    FROM conversions c
    INNER JOIN clicks cl
        ON c.user_id = cl.user_id
        AND cl.clicked_at < c.converted_at
        AND cl.clicked_at >= TIMESTAMP_SUB(c.converted_at, INTERVAL 30 DAY)
)

SELECT * EXCEPT (touch_rank) FROM attributed WHERE touch_rank = 1
```

**Mart layer**: Analytics-ready, aggregated, fully documented.

```sql
-- models/marts/marketing/mart_campaign_performance.sql

{{
    config(
        materialized='table',
        partition_by={'field': 'report_date', 'data_type': 'date'},
        cluster_by=['campaign_id', 'channel'],
        labels={'team': 'marketing', 'refresh': 'daily'}
    )
}}

WITH clicks AS (SELECT * FROM {{ ref('stg_google_ads__clicks') }}),
conversions AS (SELECT * FROM {{ ref('int_attributed_conversions') }}),
campaigns AS (SELECT * FROM {{ ref('stg_google_ads__campaigns') }}),

daily_clicks AS (
    SELECT
        click_date              AS report_date,
        campaign_id,
        COUNT(*)                AS clicks,
        SUM(cost_usd)           AS spend_usd,
        COUNT(DISTINCT user_id) AS unique_users
    FROM clicks
    GROUP BY 1, 2
),

daily_conv AS (
    SELECT
        DATE(converted_at)          AS report_date,
        campaign_id,
        COUNT(*)                    AS conversions,
        SUM(conversion_value_usd)   AS revenue_usd
    FROM conversions
    GROUP BY 1, 2
)

SELECT
    dc.report_date,
    dc.campaign_id,
    c.campaign_name,
    c.channel,
    c.campaign_type,
    dc.clicks,
    dc.spend_usd,
    dc.unique_users,
    COALESCE(dv.conversions, 0)                                 AS conversions,
    COALESCE(dv.revenue_usd, 0)                                 AS revenue_usd,
    SAFE_DIVIDE(COALESCE(dv.revenue_usd, 0), dc.spend_usd)      AS roas,
    SAFE_DIVIDE(dc.clicks, dc.unique_users)                     AS click_density,
    SAFE_DIVIDE(COALESCE(dv.conversions, 0), dc.clicks)         AS cvr,
    SAFE_DIVIDE(dc.spend_usd, dc.clicks)                        AS cpc_usd,
    CURRENT_TIMESTAMP()                                         AS dbt_updated_at
FROM daily_clicks dc
LEFT JOIN daily_conv dv  USING (report_date, campaign_id)
LEFT JOIN campaigns c    USING (campaign_id)
```

---

### 2.3 Incremental Models — Deep Dive

```sql
-- Full incremental model template for BigQuery

{{
    config(
        materialized='incremental',

        -- Strategy choice:
        -- 'append': just insert new rows (fastest, no dedup)
        -- 'merge': UPSERT on unique_key (handles updates)
        -- 'insert_overwrite': replace partitions (best for BigQuery date-partitioned)
        -- 'delete+insert': delete matching rows, then insert
        incremental_strategy='insert_overwrite',

        -- For insert_overwrite: partition config required
        partition_by={
            'field': 'click_date',
            'data_type': 'date',
            'granularity': 'day'
        },

        cluster_by=['campaign_id'],

        -- What to do when source schema changes
        on_schema_change='append_new_columns',

        -- For merge strategy: the unique key
        -- unique_key='click_id',
    )
}}

WITH source AS (
    SELECT
        click_id,
        campaign_id,
        DATE(clicked_at)        AS click_date,
        clicked_at,
        cost_usd
    FROM {{ source('google_ads', 'raw_clicks') }}

    -- THE CRITICAL PART: only process new rows during incremental runs
    {% if is_incremental() %}
    -- Lookback 3 days for late data (not exact watermark — safer)
    WHERE DATE(clicked_at) >= (
        SELECT DATE_SUB(MAX(click_date), INTERVAL 3 DAY)
        FROM {{ this }}
    )
    {% endif %}
)

SELECT * FROM source
WHERE click_id IS NOT NULL
```

**The `is_incremental()` lifecycle**:
```
First run ever:
  is_incremental() = FALSE → builds full table from scratch

Normal run (table exists):
  is_incremental() = TRUE → only processes new data

dbt run --full-refresh:
  is_incremental() = FALSE → rebuilds full table from scratch
  Use when: bug fix needed, schema change, backfill required
```

**Strategy comparison on BigQuery**:

| Strategy | How DBT Compiles It | When to Use |
|----------|---------------------|-------------|
| `append` | `INSERT INTO target SELECT ... FROM source WHERE new` | Immutable events, strict append-only |
| `merge` | `MERGE INTO target USING source ON unique_key` | Rows can update (cost adjustments, corrections) |
| `insert_overwrite` | Deletes + replaces partitions affected by new data | Date-partitioned event tables (most common on BQ) |
| `delete+insert` | `DELETE FROM target WHERE pk IN (...); INSERT ...` | Alternative to merge; simpler |

---

### 2.4 Jinja Templating — Complete Reference

```sql
-- ============================================================
-- VARIABLES
-- ============================================================
-- Access project variables defined in dbt_project.yml or passed at runtime
{{ var('start_date', '2024-01-01') }}          -- with default
{{ var('attribution_window_days') }}            -- required variable

-- Runtime: dbt run --vars '{"start_date": "2024-06-01"}'

-- ============================================================
-- CONDITIONALS
-- ============================================================
{% if target.name == 'prod' %}
    -- Production: full data
    WHERE 1=1
{% elif target.name == 'dev' %}
    -- Development: limit to last 30 days to save cost
    WHERE click_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
{% else %}
    -- CI: last 7 days
    WHERE click_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
{% endif %}

-- ============================================================
-- LOOPS
-- ============================================================
{% set channels = ['google', 'meta', 'tiktok', 'email'] %}

SELECT
    report_date,
    {% for channel in channels %}
    SUM(CASE WHEN channel = '{{ channel }}' THEN spend_usd END) AS {{ channel }}_spend
    {% if not loop.last %},{% endif %}
    {% endfor %}
FROM mart_campaign_performance
GROUP BY report_date

-- ============================================================
-- SET VARIABLES IN JINJA
-- ============================================================
{% set lookback_days = var('lookback_days', 3) %}
{% set cutoff_date = "DATE_SUB(CURRENT_DATE(), INTERVAL " ~ lookback_days ~ " DAY)" %}

WHERE click_date >= {{ cutoff_date }}

-- ============================================================
-- MACROS (reusable functions)
-- ============================================================
-- Define in macros/ directory:
{% macro safe_divide(numerator, denominator) %}
    SAFE_DIVIDE({{ numerator }}, {{ denominator }})
{% endmacro %}

{% macro attribution_window_filter(ts_col) %}
    {{ ts_col }} >= TIMESTAMP_SUB(
        CURRENT_TIMESTAMP(),
        INTERVAL {{ var('attribution_window_days', 30) }} DAY
    )
{% endmacro %}

-- Use in models:
SELECT {{ safe_divide('revenue_usd', 'spend_usd') }} AS roas
FROM mart_campaign_performance
WHERE {{ attribution_window_filter('clicked_at') }}
```

---

### 2.5 Testing Framework — Complete

```yaml
# models/staging/_stg_google_ads.yml

version: 2

models:
  - name: stg_google_ads__clicks
    description: "Cleaned ad click events from Google Ads"

    # Model-level tests (entire table)
    tests:
      - dbt_utils.expression_is_true:
          expression: "cost_usd >= 0"
          config:
            severity: error

    columns:
      - name: click_id
        description: "Unique click identifier from Google Ads"
        tests:
          - unique:
              config:
                severity: error
          - not_null:
              config:
                severity: error

      - name: campaign_id
        tests:
          - not_null
          - relationships:          # FK check
              to: ref('stg_google_ads__campaigns')
              field: campaign_id
              config:
                severity: warn      # soft fail — alerts but doesn't break pipeline

      - name: device_type
        tests:
          - accepted_values:
              values: ['mobile', 'desktop', 'tablet', 'unknown']

      - name: cost_usd
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: "cost_usd >= 0"
```

**Singular (custom) test**:
```sql
-- tests/assert_roas_non_negative.sql
-- Test FAILS if any rows are returned

SELECT
    report_date,
    campaign_id,
    revenue_usd,
    spend_usd
FROM {{ ref('mart_campaign_performance') }}
WHERE spend_usd > 0
  AND revenue_usd < 0   -- negative revenue shouldn't exist
```

**Custom generic test (reusable)**:
```sql
-- tests/generic/assert_column_between.sql
{% test assert_column_between(model, column_name, min_value, max_value) %}

SELECT {{ column_name }}
FROM {{ model }}
WHERE {{ column_name }} < {{ min_value }}
   OR {{ column_name }} > {{ max_value }}

{% endtest %}

-- Use in YAML:
# - name: ctr
#   tests:
#     - assert_column_between:
#         min_value: 0
#         max_value: 1
```

---

### 2.6 DAG and Lineage

```
source:google_ads.raw_clicks ─────────────────────────┐
source:google_ads.raw_campaigns ──┐                    │
                                   ↓                    ↓
                          stg_google_ads__campaigns  stg_google_ads__clicks
                                   │                    │
                                   └──────┬─────────────┘
                                          ↓
                               int_attributed_conversions ← stg_conversions
                                          │
                               mart_campaign_performance
                                          │
                               mart_roas_by_channel
```

**Graph operators for dbt run/test**:
```bash
# Run specific model
dbt run --select mart_campaign_performance

# Run model + all its upstream dependencies
dbt run --select +mart_campaign_performance

# Run model + all downstream dependents
dbt run --select mart_campaign_performance+

# Run both directions
dbt run --select +mart_campaign_performance+

# Tag-based selection
dbt run --select tag:daily

# State-based (CI/CD slim CI)
dbt run --select state:modified+  # only changed models + downstream
```

---

### 2.7 Snapshots — SCD Type 2 with DBT

```sql
-- snapshots/scd_campaigns.sql

{% snapshot scd_campaigns %}

{{
    config(
        target_schema='snapshots',
        unique_key='campaign_id',
        strategy='timestamp',       -- uses updated_at column to detect changes
        updated_at='updated_at',
        invalidate_hard_deletes=True
    )
}}

SELECT
    campaign_id,
    campaign_name,
    daily_budget_usd,
    bidding_strategy,
    status,
    updated_at
FROM {{ source('google_ads', 'raw_campaigns') }}

{% endsnapshot %}
```

DBT adds four metadata columns:
| Column | Description |
|--------|-------------|
| `dbt_scd_id` | Hash identifying this version |
| `dbt_updated_at` | When DBT processed this |
| `dbt_valid_from` | When this version became active |
| `dbt_valid_to` | When superseded (NULL = current) |

```sql
-- Querying snapshots: point-in-time join
SELECT
    p.report_date,
    p.campaign_id,
    p.spend_usd,
    s.daily_budget_usd    -- budget active on that date
FROM mart_campaign_performance p
JOIN {{ ref('scd_campaigns') }} s
    ON p.campaign_id = s.campaign_id
    AND p.report_date >= DATE(s.dbt_valid_from)
    AND p.report_date < DATE(COALESCE(s.dbt_valid_to, '9999-12-31'))
```

---

## L3: Real-World Scenarios — Costco/MarTech Style

### 3.1 Scenario: DBT Transformation Layer for MarTech

**Complete model dependency map**:

```
SOURCES
├── google_ads: raw_clicks, raw_campaigns, raw_ad_groups
├── meta_ads: raw_insights, raw_campaigns
└── costco_members: raw_profiles, raw_transactions

STAGING (1:1 with sources, views)
├── stg_google_ads__clicks
├── stg_google_ads__campaigns
├── stg_meta_ads__insights
├── stg_meta_ads__campaigns
├── stg_members__profiles
└── stg_members__transactions

INTERMEDIATE (business logic, ephemeral)
├── int_unified_ad_events      ← union Google + Meta
├── int_attributed_conversions ← last-touch attribution
└── int_member_ltv_segments    ← RFM scoring

MARTS (tables, partitioned/clustered)
├── marketing/
│   ├── mart_campaign_performance   (daily, by campaign)
│   ├── mart_channel_performance    (daily, by channel)
│   └── mart_attribution_report     (conversion attribution)
└── member/
    ├── mart_member_acquisition     (member acquisition channel)
    └── mart_member_ltv             (LTV segments)

SNAPSHOTS
└── scd_campaigns (budget/status history)

SEEDS
└── channel_mapping.csv (channel → category lookup)
```

---

### 3.2 Scenario: CI/CD with DBT Slim CI

```yaml
# .github/workflows/dbt-ci.yml

name: DBT CI
on:
  pull_request:
    branches: [main]

jobs:
  dbt-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install DBT
        run: pip install dbt-bigquery==1.7.0

      - name: Auth GCP
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: DBT deps
        run: dbt deps

      - name: Download prod manifest
        run: gsutil cp gs://costco-artifacts/prod/manifest.json ./artifacts/

      - name: Slim CI run
        run: |
          dbt build \
            --target ci \
            --select state:modified+ \
            --state ./artifacts/ \
            --vars '{"execution_date": "2024-01-15"}'
        # Only runs: changed models + downstream + their tests
        # Result: fast CI (minutes not hours), low cost (changed only)
```

---

## L4: Hands-On Models & Code

### 4.1 Write a Production DBT Model from Requirements

**Requirement**: Build a model showing daily ROAS per campaign, with 7-day rolling average and anomaly flag.

```sql
-- models/marts/marketing/mart_campaign_roas_trend.sql

{{
    config(
        materialized='table',
        partition_by={'field': 'report_date', 'data_type': 'date'},
        cluster_by=['campaign_id']
    )
}}

WITH daily AS (
    SELECT
        report_date,
        campaign_id,
        campaign_name,
        channel,
        spend_usd,
        revenue_usd,
        SAFE_DIVIDE(revenue_usd, spend_usd)     AS roas
    FROM {{ ref('mart_campaign_performance') }}
    WHERE spend_usd > 0
),

with_rolling AS (
    SELECT
        *,
        -- 7-day rolling average (prior 7 days, not including today)
        AVG(roas) OVER (
            PARTITION BY campaign_id
            ORDER BY report_date
            ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
        ) AS roas_7d_avg,

        -- Standard deviation for anomaly bounds
        STDDEV(roas) OVER (
            PARTITION BY campaign_id
            ORDER BY report_date
            ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
        ) AS roas_7d_stddev
    FROM daily
)

SELECT
    report_date,
    campaign_id,
    campaign_name,
    channel,
    spend_usd,
    revenue_usd,
    roas,
    roas_7d_avg,
    roas_7d_stddev,

    -- Anomaly: current ROAS > 2 std devs from rolling mean
    CASE
        WHEN roas_7d_avg IS NULL THEN 'insufficient_data'
        WHEN roas < roas_7d_avg - 2 * COALESCE(roas_7d_stddev, 0) THEN 'low_anomaly'
        WHEN roas > roas_7d_avg + 2 * COALESCE(roas_7d_stddev, 0) THEN 'high_anomaly'
        ELSE 'normal'
    END AS roas_status,

    CURRENT_TIMESTAMP() AS dbt_updated_at
FROM with_rolling
```

---

## L5: Edge Cases & Pitfalls

### 5.1 Incremental Model Watermark Bug

```sql
-- DANGEROUS: exact watermark without lookback
{% if is_incremental() %}
WHERE clicked_at > (SELECT MAX(clicked_at) FROM {{ this }})
{% endif %}

-- Problem 1: If pipeline fails halfway through, MAX(clicked_at) is set to
-- a partially-complete high-water mark. Next run misses rows between
-- the real max of the incomplete run and the new data.

-- Problem 2: Late-arriving data (mobile events that arrive 6h later)
-- is permanently missed — MAX(clicked_at) already advanced past them.

-- SAFE: lookback window
{% if is_incremental() %}
WHERE clicked_at >= (
    SELECT TIMESTAMP_SUB(MAX(clicked_at), INTERVAL 3 DAY)
    FROM {{ this }}
)
{% endif %}
-- Reprocesses last 3 days every run → catches late data + retries
-- Combined with insert_overwrite: idempotent (partitions replaced, not appended)
```

### 5.2 Ephemeral Model Performance Trap

```sql
-- BAD: ephemeral model referenced 5 times = inlined 5 times
-- Each downstream model gets a full copy of the ephemeral SQL embedded

-- int_large_complex_logic.sql (ephemeral):
-- This query joins 4 tables and processes 1B rows

-- mart_a.sql: {{ ref('int_large_complex_logic') }}  ← full 1B row query inlined
-- mart_b.sql: {{ ref('int_large_complex_logic') }}  ← full 1B row query inlined
-- mart_c.sql: {{ ref('int_large_complex_logic') }}  ← full 1B row query inlined
-- mart_d.sql: {{ ref('int_large_complex_logic') }}  ← full 1B row query inlined
-- mart_e.sql: {{ ref('int_large_complex_logic') }}  ← full 1B row query inlined
-- Result: 5 × 1B row scan = 5TB scanned (5x the cost!)

-- FIX: change to table materialization
{{ config(materialized='table') }}
-- Now int_large_complex_logic is computed ONCE, then 5 marts read from the table
```

### 5.3 generate_schema_name Override Not Set

```python
# By default, DBT concatenates target.schema + custom schema:
# dev target schema: dbt_viraaj
# model config: +schema: staging
# resulting dataset: dbt_viraaj_staging  ← correct for dev

# BUT in production without override:
# prod target schema: dbt_prod
# resulting dataset: dbt_prod_staging  ← wrong! Should just be 'staging'

# FIX: override generate_schema_name macro
# macros/generate_schema_name.sql:
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- elif target.name == 'prod' -%}
        {{ custom_schema_name | trim }}      -- prod: use custom schema directly
    {%- else -%}
        {{ default_schema }}_{{ custom_schema_name | trim }}  -- dev: prefix with personal schema
    {%- endif -%}
{%- endmacro %}
```

### 5.4 `dbt build` vs `dbt run` — Don't Confuse Them

```bash
# dbt run: ONLY runs models (no tests, no seeds, no snapshots)
dbt run --select mart_campaign_performance

# dbt test: ONLY runs tests
dbt test --select mart_campaign_performance

# dbt build: runs models + tests + seeds + snapshots IN DEPENDENCY ORDER
# (tests run immediately after their model, before downstream models)
dbt build --select +mart_campaign_performance

# Why dbt build is better in production:
# If mart_campaign_performance fails a test, its downstream models DON'T run
# With dbt run + dbt test sequentially: downstream models run on bad data,
# then tests fail — too late, already polluted marts
```

---

## L6: Interview Questions — Easy to Very Hard

### EASY

**Q1: What is DBT and why is it used?**

**Answer**: DBT (Data Build Tool) is a transformation framework for data warehouses. You write SQL SELECT statements, and DBT wraps them in the appropriate DDL (CREATE TABLE AS, CREATE VIEW AS), manages dependencies, runs tests, and generates documentation. It brings software engineering best practices — version control, testing, modularity, documentation, CI/CD — to SQL-based data transformations. It enables the ELT pattern: data is loaded raw into the warehouse first, then DBT transforms it inside the warehouse using the warehouse's own compute.

---

**Q2: What is the difference between ref() and source() in DBT?**

**Answer**: `ref('model_name')` references another DBT model — a SQL file you've written in your project. It creates a dependency edge in the DAG and resolves the fully-qualified table name at runtime (handling dev vs prod schema differences automatically).

`source('source_name', 'table_name')` references a raw table in the warehouse that DBT does not own — tables loaded by Fivetran, Airbyte, or your custom ingestion pipelines. Sources are declared in YAML with optional freshness checks. They also appear in the DAG lineage, so you can trace data all the way from the raw source table to the final mart.

Never hardcode database/schema names in DBT models — always use ref() and source() so the same code works in dev, CI, and production.

---

### MEDIUM

**Q3: Walk me through the four DBT materializations and when you'd use each.**

**Answer**:

**View**: DBT creates a SQL view. No data stored — the query executes at runtime when queried. Use for staging models where you want the freshest data, the transformation is lightweight, and the model isn't queried heavily by BI tools.

**Table**: DBT drops and recreates the physical table every run. Use for mart models that are queried frequently by BI tools and need fast query performance. Avoid for tables that are too large for a full rebuild every day.

**Incremental**: DBT processes only new or changed rows and merges them into the existing table. Essential for large event tables (hundreds of millions to billions of rows) where a full rebuild is impractical. Requires careful thought about the incremental filter and strategy (insert_overwrite for BigQuery partitioned tables, merge for mutable records).

**Ephemeral**: Not materialized at all — inlined as a CTE in downstream models. Use for reusable logic (e.g., "clean device type") that's referenced by one or two downstream models and has no standalone value. Avoid when the same ephemeral is referenced many times (logic gets duplicated, executed multiple times).

---

**Q4: What is slim CI in DBT and how does it work?**

**Answer**: Slim CI is a technique that runs only the models changed in a pull request plus their downstream dependents, rather than the entire project. This keeps CI fast (minutes not hours) and cheap.

It works by comparing the current compiled SQL against the production manifest.json (generated during every prod run and stored in GCS). DBT compares node hashes — if a model's compiled SQL changed, it's `state:modified`. The `+` operator adds all downstream dependents.

```bash
dbt build --select state:modified+ --state ./artifacts/prod/
```

For a project with 200 models, a PR changing one staging model might only trigger 3-5 downstream models to run in CI instead of all 200. This is 40-100x faster and 40-100x cheaper.

---

### HARD

**Q5: Your incremental model that's been running for 6 months suddenly has 3x more rows than expected after a run. What happened and how do you fix it?**

**What they're testing**: Incremental model debugging, understanding of materialization behavior.

**Answer**:

**Most likely root cause**: The incremental filter broke down — the model ran as a full refresh without `is_incremental()` being TRUE, appending 6 months of data on top of the existing 6 months.

**Investigation**:
```bash
# Check DBT run logs — was --full-refresh passed?
# Check: did someone run dbt run --full-refresh manually?

# Check if model ran in full-refresh mode:
# In BigQuery: check INFORMATION_SCHEMA.JOBS for the time of the incident
SELECT job_id, statement_type, start_time, total_bytes_processed
FROM `region-us`.INFORMATION_SCHEMA.JOBS
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
  AND statement_type = 'SCRIPT'
ORDER BY start_time DESC;
```

**Check 1**: Did `on_schema_change='fail'` trigger a full rebuild? If a column was added to the source, DBT may have rebuilt the entire model.

**Check 2**: Was `is_incremental()` returning FALSE due to an environment issue?

**Fix**:
```sql
-- Step 1: Deduplicate the current table
CREATE OR REPLACE TABLE `staging.stg_ad_clicks_fixed` AS
SELECT * EXCEPT (rn) FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY click_id ORDER BY _loaded_at DESC) AS rn
    FROM `staging.stg_ad_clicks`
) WHERE rn = 1;

-- Step 2: Replace original with fixed version
CREATE OR REPLACE TABLE `staging.stg_ad_clicks` AS
SELECT * FROM `staging.stg_ad_clicks_fixed`;
```

**Prevention**:
1. Add uniqueness test: `- unique` on click_id — would have caught this immediately
2. Add row count monitoring: alert if row count increases >50% vs prior day
3. Add guard in incremental model: if `is_incremental()` is unexpectedly FALSE in prod, alert (use a post-hook to record materialization type)

---

### VERY HARD

**Q6: Design a complete DBT project for Costco MarTech that: handles multi-source data (Google + Meta + TikTok), implements multi-touch attribution, tracks SCD2 for campaign dimensions, has CI/CD with slim CI, and costs < $500/month in BigQuery compute. Walk through every architectural decision.**

**What they're testing**: End-to-end DBT project design, cost awareness, production maturity.

**Answer**:

**Project structure decision**: Use a single DBT project (not multi-project mesh) since the team is unified and the data is all in one BigQuery project. Use the `generate_schema_name` macro to ensure dev schemas are prefixed and prod schemas are clean.

**Staging layer design**:
- One staging model per source table per platform
- All staging models: `materialized='view'` — no storage cost, always fresh
- Standardize column names: ALL sources produce `campaign_id`, `cost_usd`, `clicked_at` — no platform-specific naming in staging

**Intermediate layer decision**:
- `int_unified_ad_events`: UNION ALL of Google + Meta + TikTok staging models (after standardization)
- `materialized='ephemeral'` — only used by attribution model (single consumer)
- `int_attributed_conversions`: multi-touch attribution logic
- `materialized='table'` — referenced by 3+ mart models (NOT ephemeral to avoid inlining 3× a large join)

**Mart layer**:
- All marts: `materialized='incremental'`, `incremental_strategy='insert_overwrite'`
- Partition by report_date, cluster by campaign_id
- `on_schema_change='append_new_columns'`

**SCD2 via snapshots**:
```sql
{% snapshot scd_campaigns %}
{{ config(strategy='timestamp', updated_at='updated_at', ...) }}
SELECT campaign_id, campaign_name, daily_budget_usd, status, updated_at
FROM {{ source('google_ads', 'raw_campaigns') }}
{% endsnapshot %}
```

**CI/CD design**:
- GitHub Actions: on PR, run `dbt build --select state:modified+ --state prod_artifacts/`
- On merge to main: run `dbt build --target prod` (full run, but incremental models only process new data)
- Store manifest.json in GCS after each prod run

**Cost calculation**:
- Staging views: $0 (no data stored, no queries until downstream runs)
- Intermediate tables: one build per day, ~50GB processed → $0.30/day
- Mart incremental builds: process 3 days × ~5GB = 15GB/day → $0.09/day
- Total transformation cost: ~$12/month
- Storage: staging=view (free), intermediate=table (~10GB=$0.20/month), marts=incremental (~100GB=$2/month)
- Total: ~$15/month for transformation + storage
- BI queries: if marts are queried via BI Engine: additional ~$100/month
- Well under $500/month

**Key cost levers**:
1. Staging as views (zero storage cost)
2. Incremental strategy (only process new data, not full rebuilds)
3. Ephemeral for single-consumer intermediates (no redundant storage)
4. Slim CI (test only changed models → 90% CI cost reduction)

---

## Summary: DBT & Transformation Layer — Senior Mastery Checklist

| Skill | What Senior Looks Like |
|-------|------------------------|
| Project structure | Staging/intermediate/mart layers with clear responsibilities |
| Materializations | Picks the right one; explains trade-offs; avoids ephemeral fan-out |
| Incremental models | Uses lookback windows not exact watermarks; picks right strategy for BQ |
| Jinja | Writes macros, uses conditionals for dev/prod, variables for config |
| Testing | Generic + singular + custom; severity levels; model + column tests |
| Snapshots | Implements SCD2 with DBT snapshot; queries with point-in-time joins |
| CI/CD | Slim CI with state:modified+; manifest.json storage/retrieval |
| generate_schema_name | Override to prevent dev/prod schema naming issues |
| Cost awareness | Staging as views; incremental to minimize BQ compute |
| Debugging | Diagnoses incremental watermark bugs, ephemeral performance traps |
