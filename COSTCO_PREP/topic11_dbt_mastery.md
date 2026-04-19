# Topic 11: DBT (Data Build Tool) — Full Mastery
## Costco Sr. Data Engineer Interview Preparation — Exhaustive Textbook

---

## Table of Contents

1. [What is DBT and Why It Exists](#1-what-is-dbt-and-why-it-exists)
2. [DBT Architecture and Core Concepts](#2-dbt-architecture-and-core-concepts)
3. [DBT Project Structure](#3-dbt-project-structure)
4. [Models — The Heart of DBT](#4-models--the-heart-of-dbt)
5. [Materializations](#5-materializations)
6. [Sources and Seeds](#6-sources-and-seeds)
7. [Tests — Data Quality Built-In](#7-tests--data-quality-built-in)
8. [Documentation](#8-documentation)
9. [Macros and Jinja Templating](#9-macros-and-jinja-templating)
10. [Packages](#10-packages)
11. [Snapshots — SCD Type 2 with DBT](#11-snapshots--scd-type-2-with-dbt)
12. [Hooks and Operations](#12-hooks-and-operations)
13. [Exposures and Metrics](#13-exposures-and-metrics)
14. [DBT on BigQuery — Deep Dive](#14-dbt-on-bigquery--deep-dive)
15. [Incremental Models — Full Deep Dive](#15-incremental-models--full-deep-dive)
16. [DAG, Lineage and the Manifest](#16-dag-lineage-and-the-manifest)
17. [Environments, Profiles and Targets](#17-environments-profiles-and-targets)
18. [DBT Cloud vs DBT Core](#18-dbt-cloud-vs-dbt-core)
19. [CI/CD with DBT](#19-cicd-with-dbt)
20. [DBT Best Practices and Anti-Patterns](#20-dbt-best-practices-and-anti-patterns)
21. [DBT for AdTech/MarTech Pipelines](#21-dbt-for-adtechmartech-pipelines)
22. [Performance Tuning DBT on BigQuery](#22-performance-tuning-dbt-on-bigquery)
23. [Advanced DBT Patterns](#23-advanced-dbt-patterns)
24. [Interview Questions and Model Answers](#24-interview-questions-and-model-answers)

---

## 1. What is DBT and Why It Exists

### 1.1 The Problem DBT Solves

Before DBT, data transformation in a warehouse was done through one of these approaches:
- **Stored procedures**: SQL bundled inside the database, hard to version, test, or deploy
- **ETL tools (Informatica, Talend)**: Expensive, proprietary, GUI-driven, fragile
- **Custom Python scripts**: No standardization, no lineage, no documentation
- **Ad-hoc SQL in Jupyter notebooks**: Not production-grade, no dependency management

All of these shared common problems:
1. No dependency management — you manually track what runs before what
2. No built-in testing — data quality was an afterthought
3. No documentation — tribal knowledge
4. No version control integration — changes were invisible
5. No lineage — you could not see how raw data becomes a dashboard metric

DBT solves all five problems simultaneously.

### 1.2 The DBT Philosophy

DBT's philosophy can be summarized in one sentence:

> **"Transform data using SELECT statements, and DBT handles everything else."**

You write only the transformation logic (as a SELECT query). DBT handles:
- Creating or replacing the target table/view
- Dependency resolution (what runs first)
- Running tests on outputs
- Generating documentation
- Tracking lineage

This is called the **ELT (Extract-Load-Transform)** pattern. Raw data is loaded into the warehouse first (by tools like Fivetran, Airbyte, or custom Dataflow pipelines), and DBT handles the T.

### 1.3 Where DBT Fits in the Modern Data Stack

```
Data Sources → [Extract + Load] → Raw Layer → [DBT Transforms] → Analytics Layer → BI Tools
               (Fivetran, Airbyte,  (BigQuery,  (models, tests,    (marts, metrics)  (Looker,
                custom Dataflow)     Snowflake)   documentation)                       Tableau)
```

At Costco/MarTech context:
```
Ad Platforms (Google Ads, Meta)
  → Dataflow/Pub/Sub pipelines
    → BigQuery raw tables (impressions, clicks, conversions)
      → DBT staging models (clean, rename, cast)
        → DBT intermediate models (sessionize, attribute, join)
          → DBT mart models (campaign_performance, roas_by_channel, member_ltv)
            → Looker/Tableau dashboards
```

### 1.4 DBT Core Competencies (What Interviewers Expect)

| Area | What They Test |
|------|---------------|
| Models | Writing clean SELECT-based models, ref(), source() |
| Materializations | Table vs View vs Incremental vs Ephemeral — when to use each |
| Tests | Generic tests, singular tests, custom tests |
| Incremental | Strategies: append, merge, insert_overwrite, delete+insert |
| Macros | Jinja2 templating, custom macros, dbt_utils |
| Snapshots | SCD Type 2 using DBT snapshots |
| Lineage | DAG, manifest.json, understanding upstream/downstream |
| BigQuery specifics | Partitioning, clustering via DBT configs |
| CI/CD | `dbt build --select state:modified+`, slim CI |
| Best practices | Naming conventions, layering, DRY with macros |

---

## 2. DBT Architecture and Core Concepts

### 2.1 DBT's Execution Model

DBT is a **CLI tool** that:
1. Reads your project (`.sql` files, `.yml` files)
2. Compiles Jinja templates into pure SQL
3. Sends SQL to the data warehouse (BigQuery, Snowflake, Redshift, etc.)
4. Returns results and logs

DBT does **not** move data. It only transforms data already in the warehouse.

```
Your DBT Project (SQL + YAML)
        ↓
   DBT Compiler (Jinja → SQL)
        ↓
  Compiled SQL Files (/target/compiled/)
        ↓
   Adapter (BigQuery Adapter, Snowflake Adapter)
        ↓
   Warehouse (BigQuery executes the SQL)
        ↓
   Tables / Views created in warehouse
```

### 2.2 The Compile Step

Every `.sql` file you write in DBT contains Jinja templating. Before executing, DBT compiles it:

Source model:
```sql
-- models/staging/stg_ad_clicks.sql
SELECT
    click_id,
    campaign_id,
    {{ dbt_utils.surrogate_key(['click_id', 'campaign_id']) }} AS click_surrogate_key,
    clicked_at
FROM {{ source('google_ads', 'raw_clicks') }}
WHERE clicked_at >= '{{ var("start_date") }}'
```

After compilation (stored in `/target/compiled/`):
```sql
SELECT
    click_id,
    campaign_id,
    TO_HEX(MD5(CAST(click_id AS STRING) || '|' || CAST(campaign_id AS STRING))) AS click_surrogate_key,
    clicked_at
FROM `my_project`.`raw`.`raw_clicks`
WHERE clicked_at >= '2024-01-01'
```

### 2.3 The Graph / DAG

DBT builds a **Directed Acyclic Graph (DAG)** from all `ref()` and `source()` calls.

```
source('google_ads','raw_clicks')    source('google_ads','raw_impressions')
            ↓                                       ↓
    stg_ad_clicks                         stg_ad_impressions
            ↓                                       ↓
    int_ad_events (joined)─────────────────────────┘
            ↓
    mart_campaign_performance
            ↓
    mart_roas_by_channel
```

DBT resolves this DAG and runs models in topological order. If `int_ad_events` depends on both staging models, DBT runs both staging models first before running the intermediate model.

### 2.4 ref() — The Most Important DBT Function

`ref()` is how you reference other models. It does two things:
1. Resolves the fully-qualified name at runtime (e.g., `project.dataset.table_name`)
2. Creates a DAG dependency — DBT knows model B must run after model A

```sql
-- Without ref() — WRONG, hardcoded, no lineage
SELECT * FROM my_project.staging.stg_ad_clicks

-- With ref() — CORRECT
SELECT * FROM {{ ref('stg_ad_clicks') }}
```

`ref()` also handles **cross-project references** in advanced setups:
```sql
{{ ref('project_name', 'model_name') }}
```

### 2.5 source() — Referencing Raw Data

`source()` references raw tables that DBT does not manage. It:
1. Resolves the fully-qualified name of the raw table
2. Allows you to define freshness checks
3. Creates a node in the DAG (so lineage starts from raw data)

```sql
-- In model SQL
SELECT * FROM {{ source('google_ads', 'raw_clicks') }}

-- Defined in schema.yml
sources:
  - name: google_ads
    database: costco-data-warehouse
    schema: raw_google_ads
    tables:
      - name: raw_clicks
        freshness:
          warn_after: {count: 12, period: hour}
          error_after: {count: 24, period: hour}
        loaded_at_field: _loaded_at
```

---

## 3. DBT Project Structure

### 3.1 Standard Directory Layout

```
dbt_project/
├── dbt_project.yml              # Project config — name, version, model configs
├── profiles.yml                 # Connection config — credentials, targets (usually ~/.dbt/)
├── packages.yml                 # External package dependencies
│
├── models/                      # All your SQL transformation files
│   ├── staging/                 # 1:1 with source tables, clean/rename/cast only
│   │   ├── _sources.yml         # source() definitions
│   │   ├── _stg_google_ads.yml  # model documentation + tests
│   │   ├── stg_ad_clicks.sql
│   │   ├── stg_ad_impressions.sql
│   │   └── stg_campaigns.sql
│   ├── intermediate/            # business logic, joins, sessionization
│   │   ├── int_ad_events.sql
│   │   ├── int_attributed_conversions.sql
│   │   └── int_member_sessions.sql
│   └── marts/                   # final analytics-ready tables
│       ├── marketing/
│       │   ├── _schema.yml
│       │   ├── mart_campaign_performance.sql
│       │   ├── mart_roas_by_channel.sql
│       │   └── mart_member_attribution.sql
│       └── finance/
│           └── mart_revenue_by_campaign.sql
│
├── snapshots/                   # SCD Type 2 snapshot definitions
│   └── scd_campaign_budget.sql
│
├── seeds/                       # Static CSV files loaded to warehouse
│   ├── channel_mapping.csv
│   └── campaign_type_lookup.csv
│
├── tests/                       # Singular (custom) tests
│   ├── assert_roas_positive.sql
│   └── assert_attribution_sums_to_one.sql
│
├── macros/                      # Reusable Jinja macros
│   ├── generate_schema_name.sql # Override DBT default schema naming
│   ├── deduplicate.sql
│   ├── get_date_spine.sql
│   └── ad_metrics.sql
│
├── analyses/                    # Ad-hoc SQL queries (compiled but not run)
│   └── campaign_exploration.sql
│
└── target/                      # Auto-generated compiled SQL + artifacts
    ├── compiled/
    ├── run/
    └── manifest.json            # Full DAG + metadata — critical for CI/CD
```

### 3.2 dbt_project.yml — Master Config

```yaml
# dbt_project.yml
name: 'costco_martech'
version: '1.0.0'
config-version: 2

# Target profile (in profiles.yml)
profile: 'costco_martech'

# File paths
model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

target-path: "target"
clean-targets: ["target", "dbt_packages"]

# Model-level configs by directory
models:
  costco_martech:
    staging:
      +materialized: view          # all staging models are views by default
      +schema: staging
      +tags: ['staging']
    intermediate:
      +materialized: ephemeral     # never persisted, just CTEs
      +tags: ['intermediate']
    marts:
      +materialized: table         # marts are physical tables
      +schema: marts
      +tags: ['marts']
      marketing:
        +tags: ['marketing']
        +post-hook: "GRANT SELECT ON {{ this }} TO ROLE analyst"

# Snapshot configs
snapshots:
  costco_martech:
    +target_schema: snapshots
    +strategy: timestamp

# Seed configs
seeds:
  costco_martech:
    +schema: seeds
    channel_mapping:
      +column_types:
        channel_id: integer
        channel_name: string
```

### 3.3 profiles.yml — Connection Credentials

Usually stored in `~/.dbt/profiles.yml` (NOT in the project repo for security):

```yaml
# ~/.dbt/profiles.yml
costco_martech:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: oauth                # or service-account
      project: costco-dev-project
      dataset: dbt_viraaj          # your personal dev schema
      threads: 4
      timeout_seconds: 300
      location: US
      priority: interactive
      retries: 1

    prod:
      type: bigquery
      method: service-account
      project: costco-prod-project
      dataset: dbt_prod
      keyfile: /secrets/bq-service-account.json
      threads: 8
      timeout_seconds: 600
      location: US
      priority: batch
      retries: 3

    ci:
      type: bigquery
      method: service-account
      project: costco-ci-project
      dataset: "dbt_ci_{{ env_var('PR_NUMBER') }}"  # dynamic schema per PR
      keyfile: "{{ env_var('GOOGLE_APPLICATION_CREDENTIALS') }}"
      threads: 4
      timeout_seconds: 300
      location: US
```

---

## 4. Models — The Heart of DBT

### 4.1 What is a Model?

A model is simply a `.sql` file containing a single SELECT statement. DBT wraps it in a `CREATE TABLE AS` or `CREATE VIEW AS` depending on the configured materialization.

```sql
-- models/staging/stg_ad_clicks.sql
-- This is the ENTIRE file. No CREATE, no INSERT, just SELECT.

SELECT
    click_id,
    impression_id,
    campaign_id,
    ad_group_id,
    keyword_id,
    user_id,
    CAST(clicked_at AS TIMESTAMP)    AS clicked_at,
    LOWER(device_type)               AS device_type,
    LOWER(match_type)                AS match_type,
    cost_micros / 1000000.0          AS cost_usd,
    _loaded_at
FROM {{ source('google_ads', 'raw_clicks') }}
WHERE click_id IS NOT NULL
```

### 4.2 Staging Models — Best Practices

Staging models are the first layer. Their only job:
1. **Rename** columns to a consistent convention
2. **Cast** data types correctly
3. **Basic cleaning** (LOWER, TRIM, null handling)
4. **No joins** (1:1 with source table)
5. **No business logic**

```sql
-- models/staging/stg_campaigns.sql

WITH source AS (
    SELECT * FROM {{ source('google_ads', 'raw_campaigns') }}
),

renamed AS (
    SELECT
        -- IDs
        campaign_id,
        customer_id                              AS advertiser_id,

        -- Strings — standardize casing
        LOWER(TRIM(campaign_name))               AS campaign_name,
        LOWER(campaign_status)                   AS campaign_status,
        LOWER(campaign_type)                     AS campaign_type,
        LOWER(bidding_strategy_type)             AS bidding_strategy_type,

        -- Financials — convert micros to dollars
        budget_amount_micros / 1000000.0         AS daily_budget_usd,
        target_cpa_micros / 1000000.0            AS target_cpa_usd,

        -- Dates — ensure proper types
        CAST(start_date AS DATE)                 AS campaign_start_date,
        CAST(end_date AS DATE)                   AS campaign_end_date,

        -- Audit fields
        CAST(created_at AS TIMESTAMP)            AS created_at,
        CAST(updated_at AS TIMESTAMP)            AS updated_at,
        _loaded_at

    FROM source
),

deduplicated AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY campaign_id
            ORDER BY updated_at DESC
        ) AS row_num
    FROM renamed
),

final AS (
    SELECT * EXCEPT (row_num)
    FROM deduplicated
    WHERE row_num = 1
)

SELECT * FROM final
```

### 4.3 Intermediate Models

Intermediate models contain the complex business logic: joins, sessionization, attribution, aggregation.

```sql
-- models/intermediate/int_attributed_conversions.sql
-- Attribution: assign conversion credit to ad clicks using last-touch model

WITH clicks AS (
    SELECT * FROM {{ ref('stg_ad_clicks') }}
),

conversions AS (
    SELECT * FROM {{ ref('stg_conversions') }}
),

-- Find the last click before each conversion within a 30-day window
attributed AS (
    SELECT
        c.conversion_id,
        c.user_id,
        c.converted_at,
        c.conversion_value_usd,
        c.conversion_type,

        -- Last-touch attribution
        cl.click_id                              AS attributed_click_id,
        cl.campaign_id                           AS attributed_campaign_id,
        cl.ad_group_id                           AS attributed_ad_group_id,
        cl.clicked_at                            AS attributed_click_at,

        TIMESTAMP_DIFF(c.converted_at, cl.clicked_at, HOUR) AS hours_to_convert,

        -- Rank to get the LAST click before conversion
        ROW_NUMBER() OVER (
            PARTITION BY c.conversion_id
            ORDER BY cl.clicked_at DESC
        ) AS touch_rank

    FROM conversions c
    INNER JOIN clicks cl
        ON c.user_id = cl.user_id
        AND cl.clicked_at < c.converted_at
        AND cl.clicked_at >= TIMESTAMP_SUB(c.converted_at, INTERVAL 30 DAY)
)

SELECT
    conversion_id,
    user_id,
    converted_at,
    conversion_value_usd,
    conversion_type,
    attributed_click_id,
    attributed_campaign_id,
    attributed_ad_group_id,
    attributed_click_at,
    hours_to_convert
FROM attributed
WHERE touch_rank = 1
```

### 4.4 Mart Models

Mart models are the final, analytics-ready, denormalized tables that BI tools and stakeholders consume.

```sql
-- models/marts/marketing/mart_campaign_performance.sql
-- Daily campaign performance summary with attribution metrics

WITH campaigns AS (
    SELECT * FROM {{ ref('stg_campaigns') }}
),

clicks AS (
    SELECT * FROM {{ ref('stg_ad_clicks') }}
),

impressions AS (
    SELECT * FROM {{ ref('stg_ad_impressions') }}
),

conversions AS (
    SELECT * FROM {{ ref('int_attributed_conversions') }}
),

daily_clicks AS (
    SELECT
        DATE(clicked_at)    AS report_date,
        campaign_id,
        COUNT(*)            AS clicks,
        SUM(cost_usd)       AS spend_usd
    FROM clicks
    GROUP BY 1, 2
),

daily_impressions AS (
    SELECT
        DATE(served_at)     AS report_date,
        campaign_id,
        COUNT(*)            AS impressions
    FROM impressions
    GROUP BY 1, 2
),

daily_conversions AS (
    SELECT
        DATE(converted_at)  AS report_date,
        attributed_campaign_id AS campaign_id,
        COUNT(*)            AS conversions,
        SUM(conversion_value_usd) AS revenue_usd
    FROM conversions
    GROUP BY 1, 2
),

joined AS (
    SELECT
        COALESCE(di.report_date, dc.report_date, dconv.report_date) AS report_date,
        COALESCE(di.campaign_id, dc.campaign_id, dconv.campaign_id) AS campaign_id,
        COALESCE(di.impressions, 0)             AS impressions,
        COALESCE(dc.clicks, 0)                  AS clicks,
        COALESCE(dc.spend_usd, 0)               AS spend_usd,
        COALESCE(dconv.conversions, 0)          AS conversions,
        COALESCE(dconv.revenue_usd, 0)          AS revenue_usd
    FROM daily_impressions di
    FULL OUTER JOIN daily_clicks dc
        ON di.report_date = dc.report_date
        AND di.campaign_id = dc.campaign_id
    FULL OUTER JOIN daily_conversions dconv
        ON COALESCE(di.report_date, dc.report_date) = dconv.report_date
        AND COALESCE(di.campaign_id, dc.campaign_id) = dconv.campaign_id
),

final AS (
    SELECT
        j.report_date,
        j.campaign_id,
        c.campaign_name,
        c.campaign_type,
        c.campaign_status,
        c.daily_budget_usd,

        -- Volume metrics
        j.impressions,
        j.clicks,
        j.conversions,

        -- Financial metrics
        j.spend_usd,
        j.revenue_usd,

        -- Calculated rates
        SAFE_DIVIDE(j.clicks, j.impressions)    AS ctr,
        SAFE_DIVIDE(j.spend_usd, j.clicks)      AS cpc_usd,
        SAFE_DIVIDE(j.spend_usd, j.impressions) * 1000 AS cpm_usd,
        SAFE_DIVIDE(j.conversions, j.clicks)    AS cvr,
        SAFE_DIVIDE(j.spend_usd, j.conversions) AS cpa_usd,
        SAFE_DIVIDE(j.revenue_usd, j.spend_usd) AS roas,

        -- Budget utilization
        SAFE_DIVIDE(j.spend_usd, c.daily_budget_usd) AS budget_utilization_rate,

        -- Load metadata
        CURRENT_TIMESTAMP() AS dbt_updated_at

    FROM joined j
    LEFT JOIN campaigns c USING (campaign_id)
)

SELECT * FROM final
```

### 4.5 The config() Block

You can override project-level configs at the model level using the `config()` macro:

```sql
-- Override materialization and add BigQuery-specific configs
{{
    config(
        materialized='incremental',
        unique_key='event_id',
        incremental_strategy='merge',
        partition_by={
            'field': 'event_date',
            'data_type': 'date',
            'granularity': 'day'
        },
        cluster_by=['campaign_id', 'ad_group_id'],
        on_schema_change='append_new_columns',
        tags=['daily', 'marketing'],
        labels={'team': 'martech', 'cost_center': 'marketing'}
    )
}}

SELECT
    event_id,
    DATE(event_at) AS event_date,
    ...
FROM {{ source('events', 'raw_events') }}
```

---

## 5. Materializations

Materialization is how DBT persists (or doesn't persist) the result of a model query.

### 5.1 The Four Materializations

| Materialization | What it Creates | When to Use |
|----------------|-----------------|-------------|
| `view` | SQL view | Staging models; when freshness matters more than performance |
| `table` | Physical table (full refresh every run) | Mart models with manageable data volume |
| `incremental` | Physical table (only processes new rows) | Large event tables; partitioned data |
| `ephemeral` | CTE (inlined into downstream models) | Intermediate logic with no standalone value |

### 5.2 View Materialization

```sql
-- DBT creates: CREATE OR REPLACE VIEW staging.stg_ad_clicks AS SELECT ...
-- Run time: instantaneous (no data is moved)
-- Query time: slow (executes the SELECT every time a BI tool queries it)

{{ config(materialized='view') }}

SELECT * FROM {{ source('google_ads', 'raw_clicks') }}
```

**When to use**: Staging models. The view always returns fresh data. Since staging models are lightweight (no joins, no aggregations), query-time overhead is acceptable.

**When NOT to use**: Models that are queried frequently by BI tools, models with expensive joins/aggregations, models over large datasets.

### 5.3 Table Materialization

```sql
-- DBT creates: CREATE OR REPLACE TABLE marts.mart_campaign_performance AS SELECT ...
-- Run time: full table scan every run
-- Query time: fast (data is pre-computed)

{{ config(materialized='table') }}

SELECT
    report_date,
    campaign_id,
    SUM(spend_usd) AS total_spend
FROM {{ ref('int_ad_events') }}
GROUP BY 1, 2
```

**When to use**: Mart models that aggregate data. BI tools need fast query performance, and the table is not so large that a full refresh is prohibitively expensive.

**When NOT to use**: Models over billions of rows where a full refresh takes hours.

### 5.4 Ephemeral Materialization

```sql
-- DBT does NOT create anything in the warehouse.
-- Instead, this model's SQL is inlined as a CTE in any downstream model that ref()s it.

{{ config(materialized='ephemeral') }}

SELECT
    user_id,
    clicked_at,
    campaign_id,
    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY clicked_at DESC) AS rn
FROM {{ ref('stg_ad_clicks') }}
```

If a mart model does `{{ ref('int_last_touch_click') }}`, DBT inlines the ephemeral model's SQL as a CTE:

```sql
-- Compiled output in downstream model:
WITH int_last_touch_click AS (
    SELECT
        user_id,
        clicked_at,
        campaign_id,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY clicked_at DESC) AS rn
    FROM `project`.`staging`.`stg_ad_clicks`
),

downstream_model AS (
    SELECT * FROM int_last_touch_click WHERE rn = 1
)

SELECT * FROM downstream_model
```

**When to use**: Pure logic helpers that are consumed by exactly one or two downstream models. No need to create a table/view for them.

**When NOT to use**: If the ephemeral model is referenced by many downstream models (the SQL gets duplicated in each compiled query). Use a table instead.

### 5.5 Incremental Materialization (Critical — Covered in Depth in Section 15)

```sql
{{ config(
    materialized='incremental',
    unique_key='click_id',
    incremental_strategy='merge'
) }}

SELECT
    click_id,
    campaign_id,
    clicked_at,
    cost_usd
FROM {{ source('google_ads', 'raw_clicks') }}

{% if is_incremental() %}
    -- Only process rows from the last 3 days (with overlap for late data)
    WHERE clicked_at >= (
        SELECT DATEADD(DAY, -3, MAX(clicked_at)) FROM {{ this }}
    )
{% endif %}
```

---

## 6. Sources and Seeds

### 6.1 Sources — Full Specification

Sources are raw tables that DBT does not own. You declare them in YAML files:

```yaml
# models/staging/_sources.yml
version: 2

sources:
  - name: google_ads                        # Logical source name
    description: "Raw Google Ads data loaded by Fivetran"
    database: costco-raw-data               # BigQuery project
    schema: google_ads_raw                  # BigQuery dataset
    loader: fivetran
    loaded_at_field: _fivetran_synced       # Used for freshness checks

    freshness:
      warn_after: {count: 6, period: hour}
      error_after: {count: 12, period: hour}

    tables:
      - name: campaign
        description: "Campaign-level configuration and settings"
        columns:
          - name: id
            description: "Unique campaign ID"
            tests:
              - unique
              - not_null
          - name: name
            tests:
              - not_null

      - name: click_view
        description: "Individual ad click events"
        freshness:                          # Override source-level freshness
          warn_after: {count: 1, period: hour}
          error_after: {count: 3, period: hour}
        columns:
          - name: gclid
            description: "Google Click ID — unique per click"
            tests:
              - unique
              - not_null

  - name: meta_ads
    description: "Raw Meta (Facebook/Instagram) Ads data"
    database: costco-raw-data
    schema: meta_ads_raw
    tables:
      - name: ad_insights
        description: "Daily ad performance snapshots from Meta API"
```

### 6.2 Source Freshness Checking

Run `dbt source freshness` to check if raw tables are being loaded on schedule:

```bash
# Check all sources
dbt source freshness

# Check specific source
dbt source freshness --select source:google_ads

# Output:
# Found 3 sources
# 
# 14:23:04  1 of 3 START freshness of google_ads.campaign ........................
# 14:23:05  1 of 3 WARN freshness of google_ads.campaign [WARN in 0.98s]
# 14:23:05  Last loaded at: 2024-01-15 08:00:00+00:00
# 14:23:05  Freshness check warning after: 6 hours
```

### 6.3 Seeds — Loading Static CSV Files

Seeds are CSV files that DBT loads into the warehouse as tables. Use for:
- Channel/platform lookup tables
- Country/region mappings
- Campaign type categories
- Attribution weight configurations

```bash
# File: seeds/channel_mapping.csv
channel_id,channel_name,channel_category,is_paid
1,google_search,search,true
2,google_display,display,true
3,meta_facebook,social,true
4,meta_instagram,social,true
5,organic_search,search,false
6,direct,direct,false
7,email,email,false
```

```yaml
# dbt_project.yml
seeds:
  costco_martech:
    +schema: reference_data
    +quote_columns: false
    channel_mapping:
      +column_types:
        channel_id: integer
        is_paid: boolean
```

```bash
# Run seeds
dbt seed

# Run specific seed
dbt seed --select channel_mapping
```

Reference a seed in a model:
```sql
SELECT
    e.*,
    cm.channel_name,
    cm.channel_category,
    cm.is_paid
FROM {{ ref('int_ad_events') }} e
LEFT JOIN {{ ref('channel_mapping') }} cm USING (channel_id)
```

---

## 7. Tests — Data Quality Built-In

DBT has a built-in testing framework. Tests are SQL queries that return rows when they fail (zero rows = test passes).

### 7.1 Generic Tests (Out of the Box)

DBT ships with four generic tests:

```yaml
# models/staging/_stg_google_ads.yml
version: 2

models:
  - name: stg_ad_clicks
    description: "Cleaned and standardized ad click events from Google Ads"
    columns:
      - name: click_id
        description: "Unique identifier for each click event"
        tests:
          - unique              # No duplicates
          - not_null            # No nulls

      - name: campaign_id
        tests:
          - not_null
          - relationships:     # Referential integrity check
              to: ref('stg_campaigns')
              field: campaign_id

      - name: device_type
        tests:
          - accepted_values:   # Enum validation
              values: ['desktop', 'mobile', 'tablet', 'unknown']

      - name: cost_usd
        tests:
          - not_null
```

### 7.2 Model-Level Generic Tests

Some tests apply to the model as a whole, not individual columns:

```yaml
models:
  - name: mart_campaign_performance
    tests:
      - unique:
          column_name: "concat(report_date, '-', campaign_id)"
      - dbt_utils.expression_is_true:
          expression: "roas >= 0"
      - dbt_utils.expression_is_true:
          expression: "ctr between 0 and 1"
```

### 7.3 Singular Tests (Custom SQL Tests)

For complex business logic that can't be expressed as a generic test, write a singular test — a SQL file in the `tests/` directory that should return zero rows:

```sql
-- tests/assert_attribution_sums_to_one.sql
-- Each conversion should have exactly one attributed click (last-touch)
-- Test FAILS if any conversion_id appears more than once

SELECT
    conversion_id,
    COUNT(*) AS attribution_count
FROM {{ ref('int_attributed_conversions') }}
GROUP BY conversion_id
HAVING COUNT(*) > 1
```

```sql
-- tests/assert_spend_not_negative.sql
-- Ad spend should never be negative

SELECT
    click_id,
    cost_usd
FROM {{ ref('stg_ad_clicks') }}
WHERE cost_usd < 0
```

```sql
-- tests/assert_roas_data_integrity.sql
-- If there are impressions for a campaign on a day, there should be spend data too
-- No phantom revenue (revenue with zero spend)

SELECT
    report_date,
    campaign_id,
    revenue_usd,
    spend_usd
FROM {{ ref('mart_campaign_performance') }}
WHERE revenue_usd > 0
  AND spend_usd = 0
```

### 7.4 Custom Generic Tests (Reusable)

Write a macro in `tests/generic/` to create a reusable generic test:

```sql
-- tests/generic/assert_column_is_between.sql

{% test assert_column_is_between(model, column_name, min_value, max_value) %}

SELECT {{ column_name }}
FROM {{ model }}
WHERE {{ column_name }} < {{ min_value }}
   OR {{ column_name }} > {{ max_value }}

{% endtest %}
```

Use it like any other generic test:
```yaml
columns:
  - name: ctr
    tests:
      - assert_column_is_between:
          min_value: 0
          max_value: 1
  - name: roas
    tests:
      - assert_column_is_between:
          min_value: 0
          max_value: 100
```

### 7.5 Test Severity and Configs

```yaml
columns:
  - name: click_id
    tests:
      - unique:
          severity: error    # Pipeline fails if test fails
      - not_null:
          severity: warn     # Only a warning, pipeline continues

  - name: cost_usd
    tests:
      - not_null:
          severity: error
          config:
            where: "clicked_at >= '2024-01-01'"   # Only test recent data
```

### 7.6 Running Tests

```bash
# Run all tests
dbt test

# Test specific model
dbt test --select stg_ad_clicks

# Test model + its upstream dependencies
dbt test --select +stg_ad_clicks

# Test only data tests (not schema tests)
dbt test --select test_type:singular

# Run tests after build
dbt build   # runs models + tests + seeds + snapshots in one command
```

---

## 8. Documentation

### 8.1 Column Descriptions in YAML

```yaml
# models/marts/marketing/_schema.yml
version: 2

models:
  - name: mart_campaign_performance
    description: >
      Daily aggregate of campaign performance metrics including spend, clicks,
      impressions, conversions, and derived KPIs (CTR, CPC, ROAS).
      Attribution uses last-touch model with 30-day lookback window.
      Refreshed daily at 6 AM UTC.

    columns:
      - name: report_date
        description: "UTC date for which metrics are aggregated"
      - name: campaign_id
        description: "Google Ads campaign identifier"
      - name: campaign_name
        description: "Human-readable campaign name from Google Ads"
      - name: roas
        description: >
          Return on Ad Spend = revenue_usd / spend_usd.
          NULL if spend is zero. Calculated using last-touch attribution.
      - name: ctr
        description: "Click-Through Rate = clicks / impressions. Range: 0 to 1"
```

### 8.2 Docs Blocks — Long Descriptions in Markdown

For long descriptions, use `docs` blocks:

```sql
-- models/marts/marketing/docs_blocks.md (markdown file in models/)

{% docs roas %}
## Return on Ad Spend (ROAS)

ROAS measures revenue generated per dollar of ad spend.

**Formula**: `revenue_usd / spend_usd`

**Interpretation**:
- ROAS of 3.0 means $3 revenue per $1 spent
- Target ROAS varies by campaign type:
  - Brand campaigns: >= 5.0
  - Prospecting campaigns: >= 2.0
  - Retargeting campaigns: >= 4.0

**Attribution**: Uses last-touch model with 30-day lookback window.

**Null handling**: Returns NULL when spend = 0 to avoid division by zero.
{% enddocs %}
```

Reference in YAML:
```yaml
- name: roas
  description: "{{ doc('roas') }}"
```

### 8.3 Generating and Serving Docs

```bash
# Generate documentation artifacts
dbt docs generate

# Serve documentation locally (opens browser)
dbt docs serve

# In CI/CD — generate and upload to GCS
dbt docs generate
gsutil -m cp -r target/. gs://costco-dbt-docs/latest/
```

---

## 9. Macros and Jinja Templating

### 9.1 Jinja Basics in DBT

DBT uses Jinja2 as its templating engine. Every `.sql` and `.yml` file can use Jinja.

```
{{ }}    — Expression: output a value
{% %}    — Statement: control flow (if, for, set)
{# #}    — Comment (not rendered in compiled SQL)
```

Built-in Jinja variables in DBT:
```sql
-- Access current target info
{{ target.name }}        -- 'dev', 'prod', 'ci'
{{ target.schema }}      -- 'dbt_viraaj', 'dbt_prod'
{{ target.project }}     -- 'costco-dev-project'
{{ target.type }}        -- 'bigquery'

-- Access DBT metadata
{{ this }}               -- Fully-qualified name of the current model
{{ this.identifier }}    -- Just the table name
{{ this.schema }}        -- Just the schema

-- Project variables (defined in dbt_project.yml)
{{ var('start_date') }}
{{ var('attribution_window_days', 30) }}  -- with default

-- Environment variables
{{ env_var('SECRET_API_KEY') }}
{{ env_var('OPTIONAL_VAR', 'default_value') }}
```

### 9.2 Conditional Logic with Jinja

```sql
-- Different logic per environment
SELECT
    click_id,
    campaign_id,
    {% if target.name == 'prod' %}
        cost_usd,          -- Full data in prod
    {% else %}
        0.0 AS cost_usd,   -- Masked in dev/ci to save money
    {% endif %}
    clicked_at
FROM {{ source('google_ads', 'raw_clicks') }}

{% if target.name != 'prod' %}
-- Limit to last 30 days in dev to control costs
WHERE clicked_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
{% endif %}
```

### 9.3 Writing Custom Macros

```sql
-- macros/ad_metrics.sql

-- Macro to calculate CTR safely
{% macro safe_ctr(clicks_col, impressions_col) %}
    SAFE_DIVIDE({{ clicks_col }}, {{ impressions_col }})
{% endmacro %}

-- Macro to calculate ROAS safely
{% macro safe_roas(revenue_col, spend_col) %}
    SAFE_DIVIDE({{ revenue_col }}, {{ spend_col }})
{% endmacro %}

-- Macro to standardize attribution window filter
{% macro attribution_window_filter(timestamp_col) %}
    {{ timestamp_col }} >= TIMESTAMP_SUB(
        CURRENT_TIMESTAMP(),
        INTERVAL {{ var('attribution_window_days', 30) }} DAY
    )
{% endmacro %}

-- Macro to generate a date spine
{% macro date_spine(start_date, end_date) %}
    SELECT
        date_day
    FROM UNNEST(
        GENERATE_DATE_ARRAY(
            DATE('{{ start_date }}'),
            DATE('{{ end_date }}'),
            INTERVAL 1 DAY
        )
    ) AS date_day
{% endmacro %}
```

Usage in models:
```sql
SELECT
    report_date,
    campaign_id,
    clicks,
    impressions,
    {{ safe_ctr('clicks', 'impressions') }} AS ctr,
    {{ safe_roas('revenue_usd', 'spend_usd') }} AS roas
FROM {{ ref('mart_campaign_performance') }}
WHERE {{ attribution_window_filter('report_date') }}
```

### 9.4 The generate_schema_name Macro — Critical for Multi-Env Setups

By default, DBT concatenates the target schema with the custom schema config:
- Target schema: `dbt_viraaj`
- Model config: `+schema: staging`
- Resulting dataset: `dbt_viraaj_staging` ← often not what you want in prod

Override with `generate_schema_name`:

```sql
-- macros/generate_schema_name.sql

{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- elif target.name == 'prod' -%}
        -- In prod: use the custom schema directly (no prefix)
        {{ custom_schema_name | trim }}
    {%- else -%}
        -- In dev/ci: prefix with personal schema
        {{ default_schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
```

Result:
| Environment | Model Config | Dataset Created |
|------------|-------------|-----------------|
| dev | `+schema: staging` | `dbt_viraaj_staging` |
| prod | `+schema: staging` | `staging` |
| ci | `+schema: marts` | `dbt_ci_123_marts` |

### 9.5 Looping in Macros

```sql
-- macros/union_relations.sql
-- Dynamically union multiple tables matching a pattern

{% macro union_ad_platforms(tables) %}
    {% for table in tables %}
        SELECT
            '{{ table.platform }}' AS platform,
            campaign_id,
            impressions,
            clicks,
            spend_usd,
            report_date
        FROM {{ source(table.source, table.table_name) }}
        {% if not loop.last %} UNION ALL {% endif %}
    {% endfor %}
{% endmacro %}
```

Usage:
```sql
{{ union_ad_platforms([
    {'platform': 'google', 'source': 'google_ads', 'table_name': 'campaign_stats'},
    {'platform': 'meta', 'source': 'meta_ads', 'table_name': 'ad_insights'},
    {'platform': 'tiktok', 'source': 'tiktok_ads', 'table_name': 'ad_report'}
]) }}
```

---

## 10. Packages

### 10.1 dbt Packages Overview

DBT packages are reusable collections of macros, models, and tests hosted on the DBT Package Hub (https://hub.getdbt.com).

```yaml
# packages.yml
packages:
  - package: dbt-labs/dbt_utils
    version: 1.1.1
  - package: dbt-labs/audit_helper
    version: 0.9.0
  - package: calogica/dbt_expectations
    version: 0.10.1
  - package: dbt-labs/codegen
    version: 0.12.1
```

```bash
dbt deps   # installs packages into dbt_packages/
```

### 10.2 dbt_utils — The Most Important Package

```sql
-- Surrogate key (MD5 hash of multiple columns)
{{ dbt_utils.surrogate_key(['user_id', 'session_id', 'event_at']) }}

-- Generate date spine
{{ dbt_utils.date_spine(
    datepart="day",
    start_date="cast('2024-01-01' as date)",
    end_date="current_date()"
) }}

-- Get column values (useful in macros)
{{ dbt_utils.get_column_values(ref('stg_channels'), 'channel_name') }}

-- Pivot (like SQL PIVOT)
{{ dbt_utils.pivot(
    column='channel_name',
    values=dbt_utils.get_column_values(ref('stg_channels'), 'channel_name'),
    agg='SUM',
    then_value='spend_usd'
) }}

-- Star (SELECT all except some columns)
{{ dbt_utils.star(from=ref('mart_campaign_performance'), except=['dbt_updated_at']) }}

-- Union all relations
{{ dbt_utils.union_relations(
    relations=[ref('events_2022'), ref('events_2023'), ref('events_2024')]
) }}
```

Generic tests from dbt_utils:
```yaml
- name: mart_campaign_performance
  tests:
    - dbt_utils.expression_is_true:
        expression: "roas >= 0 or roas is null"
    - dbt_utils.equal_rowcount:
        compare_model: ref('mart_campaign_performance_v2')
    - dbt_utils.not_empty_string:
        column_name: campaign_name
    - dbt_utils.at_least_one:
        column_name: spend_usd
```

### 10.3 dbt_expectations — Great Expectations for DBT

```yaml
columns:
  - name: ctr
    tests:
      - dbt_expectations.expect_column_values_to_be_between:
          min_value: 0
          max_value: 1
      - dbt_expectations.expect_column_values_to_not_be_null:
          mostly: 0.99   # Allow 1% nulls

  - name: campaign_id
    tests:
      - dbt_expectations.expect_column_values_to_match_regex:
          regex: "^[0-9]+$"  # campaign IDs are numeric strings

models:
  - name: mart_campaign_performance
    tests:
      - dbt_expectations.expect_table_row_count_to_be_between:
          min_value: 1000    # Should have at least 1000 rows
          max_value: 10000000
      - dbt_expectations.expect_column_pair_values_A_to_be_greater_than_B:
          column_A: revenue_usd
          column_B: spend_usd   # Revenue should exceed spend (ROAS > 1)
          or_equal: true
```

### 10.4 audit_helper — Comparing Model Versions

Useful when refactoring models:
```sql
-- Compare row counts between old and new model versions
{{ audit_helper.compare_relation_columns(
    a_relation=ref('mart_campaign_performance'),
    b_relation=ref('mart_campaign_performance_v2')
) }}

-- Compare actual data values
{{ audit_helper.compare_relations(
    a_relation=ref('mart_campaign_performance'),
    b_relation=ref('mart_campaign_performance_v2'),
    summarize=false
) }}
```

---

## 11. Snapshots — SCD Type 2 with DBT

### 11.1 What are Snapshots?

Snapshots implement **Slowly Changing Dimension Type 2 (SCD2)** — tracking historical changes to dimension records over time. When a campaign's budget changes, a snapshot preserves both the old and new records with valid timestamps.

Without snapshots, you'd only have the current state. With snapshots, you have a full history.

### 11.2 Snapshot Syntax and Strategies

**Strategy 1: Timestamp** — Uses an `updated_at` column to detect changes

```sql
-- snapshots/scd_campaigns.sql

{% snapshot scd_campaigns %}

{{
    config(
        target_schema='snapshots',
        unique_key='campaign_id',
        strategy='timestamp',
        updated_at='updated_at',
        invalidate_hard_deletes=True
    )
}}

SELECT
    campaign_id,
    campaign_name,
    campaign_status,
    daily_budget_usd,
    target_cpa_usd,
    bidding_strategy,
    updated_at
FROM {{ source('google_ads', 'raw_campaigns') }}

{% endsnapshot %}
```

**Strategy 2: Check** — Detects changes by comparing specific columns

```sql
{% snapshot scd_ad_group_targeting %}

{{
    config(
        target_schema='snapshots',
        unique_key='ad_group_id',
        strategy='check',
        check_cols=['target_cpa_usd', 'max_cpc_usd', 'targeting_keywords'],
        invalidate_hard_deletes=True
    )
}}

SELECT
    ad_group_id,
    campaign_id,
    ad_group_name,
    target_cpa_usd,
    max_cpc_usd,
    targeting_keywords
FROM {{ source('google_ads', 'raw_ad_groups') }}

{% endsnapshot %}
```

### 11.3 Snapshot Output Table Structure

DBT adds four metadata columns to the snapshot table:

| Column | Type | Description |
|--------|------|-------------|
| `dbt_scd_id` | STRING | Hash uniquely identifying this record version |
| `dbt_updated_at` | TIMESTAMP | When DBT last updated this record |
| `dbt_valid_from` | TIMESTAMP | When this version became active |
| `dbt_valid_to` | TIMESTAMP | When this version was superseded (NULL = current) |

Example output:

| campaign_id | daily_budget_usd | dbt_valid_from | dbt_valid_to |
|------------|-----------------|----------------|--------------|
| C001 | 500.00 | 2024-01-01 | 2024-03-15 |
| C001 | 750.00 | 2024-03-15 | 2024-05-01 |
| C001 | 1000.00 | 2024-05-01 | NULL |

### 11.4 Querying Snapshots

```sql
-- Get the campaign's budget on a specific date
SELECT
    campaign_id,
    daily_budget_usd
FROM {{ ref('scd_campaigns') }}
WHERE campaign_id = 'C001'
  AND '2024-04-01' BETWEEN DATE(dbt_valid_from) AND DATE(COALESCE(dbt_valid_to, '9999-12-31'))

-- Join snapshot to daily performance (point-in-time budget)
SELECT
    p.report_date,
    p.campaign_id,
    p.spend_usd,
    c.daily_budget_usd,
    p.spend_usd / c.daily_budget_usd AS budget_utilization
FROM {{ ref('mart_campaign_performance') }} p
LEFT JOIN {{ ref('scd_campaigns') }} c
    ON p.campaign_id = c.campaign_id
    AND p.report_date BETWEEN DATE(c.dbt_valid_from) AND DATE(COALESCE(c.dbt_valid_to, '9999-12-31'))
```

### 11.5 Running Snapshots

```bash
# Run all snapshots
dbt snapshot

# Run specific snapshot
dbt snapshot --select scd_campaigns

# Run snapshots + models together
dbt build --select snapshots.*+ mart_campaign_performance
```

---

## 12. Hooks and Operations

### 12.1 Hooks — Running SQL Before/After Models

Hooks execute SQL at specific points in the DBT lifecycle:

```yaml
# dbt_project.yml

models:
  costco_martech:
    marts:
      +pre-hook:
        - "{{ logging.log_model_start(this) }}"
      +post-hook:
        - "GRANT SELECT ON {{ this }} TO ROLE `analyst@costco.com`"
        - "{{ logging.log_model_end(this) }}"
```

Model-level hooks:
```sql
{{
    config(
        post_hook=[
            "GRANT SELECT ON {{ this }} TO ROLE analyst",
            "INSERT INTO {{ ref('dbt_audit_log') }} VALUES ('{{ this }}', CURRENT_TIMESTAMP())"
        ]
    )
}}

SELECT ...
```

Use cases for hooks:
- Granting permissions after table creation
- Logging pipeline execution metadata
- Creating clustering on BigQuery tables
- Calling stored procedures post-load
- Sending Slack notifications on completion

### 12.2 Operations — One-Off SQL Commands

Operations are macros you run outside the model execution cycle:

```sql
-- macros/operations.sql

{% macro vacuum_staging() %}
    -- BigQuery doesn't need VACUUM but in Snowflake/Redshift:
    {% for table in dbt_utils.get_tables_by_prefix(this.database, this.schema, 'stg_') %}
        VACUUM {{ table }};
    {% endfor %}
{% endmacro %}

{% macro grant_analyst_access() %}
    {% set schemas = ['staging', 'marts', 'snapshots'] %}
    {% for schema in schemas %}
        GRANT SELECT ON ALL TABLES IN SCHEMA {{ target.schema }}_{{ schema }}
        TO ROLE analyst;
    {% endfor %}
{% endmacro %}
```

```bash
# Run an operation
dbt run-operation grant_analyst_access
dbt run-operation vacuum_staging
```

---

## 13. Exposures and Metrics

### 13.1 Exposures — Documenting Downstream Consumers

Exposures declare what consumes your DBT models (Looker dashboards, Airflow pipelines, APIs):

```yaml
# models/marts/marketing/_exposures.yml
version: 2

exposures:
  - name: campaign_performance_dashboard
    label: "Campaign Performance Dashboard"
    type: dashboard
    maturity: high
    url: "https://looker.costco.com/dashboards/campaign-performance"
    description: >
      Daily campaign performance dashboard used by the Growth Marketing team.
      Shows ROAS, CTR, CPC, conversion rates by channel and campaign type.
    depends_on:
      - ref('mart_campaign_performance')
      - ref('mart_roas_by_channel')
    owner:
      name: "Viraaj Sivaraju"
      email: "viraaj.s@costco.com"

  - name: weekly_performance_report
    label: "Weekly Marketing Performance Email"
    type: ml                    # Could also be: dashboard, notebook, analysis, application
    maturity: medium
    description: >
      Automated weekly email sent to VP Marketing every Monday.
      Sourced from the mart layer.
    depends_on:
      - ref('mart_campaign_performance')
      - ref('mart_member_attribution')
    owner:
      name: "Growth Analytics Team"
      email: "growth-analytics@costco.com"
```

Exposures appear in the DBT docs lineage graph, showing the full flow from raw source → transformation → dashboard.

### 13.2 DBT Metrics (Semantic Layer)

DBT's semantic layer (MetricFlow) allows defining business metrics once, then querying them consistently:

```yaml
# models/marts/marketing/_metrics.yml
version: 2

metrics:
  - name: total_spend
    label: "Total Ad Spend"
    model: ref('mart_campaign_performance')
    description: "Total ad spend in USD across all campaigns"
    type: simple
    type_params:
      measure:
        name: spend_usd
        agg: sum

  - name: roas
    label: "Return on Ad Spend"
    model: ref('mart_campaign_performance')
    description: "Revenue generated per dollar of ad spend"
    type: ratio
    type_params:
      numerator:
        name: revenue_usd
        agg: sum
      denominator:
        name: spend_usd
        agg: sum

  - name: ctr
    label: "Click-Through Rate"
    model: ref('mart_campaign_performance')
    type: ratio
    type_params:
      numerator:
        name: clicks
        agg: sum
      denominator:
        name: impressions
        agg: sum
    dimensions:
      - name: campaign_type
      - name: report_date
```

Query metrics from the CLI:
```bash
dbt sl query --metrics roas --group-by campaign_type --where "report_date >= '2024-01-01'"
```

---

## 14. DBT on BigQuery — Deep Dive

### 14.1 BigQuery-Specific Configurations

```sql
{{
    config(
        materialized='table',
        
        -- Partitioning
        partition_by={
            'field': 'event_date',
            'data_type': 'date',
            'granularity': 'day'      -- day, month, year, hour
        },
        
        -- Clustering (up to 4 columns)
        cluster_by=['campaign_id', 'channel_id'],
        
        -- Require partition filter (prevents full table scans)
        require_partition_filter=True,
        
        -- Schema evolution: what to do when columns are added/removed
        on_schema_change='append_new_columns',  -- options: ignore, fail, sync_all_columns
        
        -- BigQuery labels (for cost attribution)
        labels={
            'team': 'martech',
            'cost_center': 'marketing',
            'env': target.name
        },
        
        -- KMS encryption key
        kms_key_name='projects/costco-project/locations/us/keyRings/ring/cryptoKeys/key',
        
        -- Table expiration (useful for temp/CI tables)
        expiration_timestamp='2025-01-01T00:00:00',
        
        -- Description
        description='Daily campaign performance metrics'
    )
}}
```

### 14.2 Incremental on BigQuery with Partitions

The combination of incremental models + BigQuery partitioning is the standard pattern for large event tables:

```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='insert_overwrite',   -- Most efficient for BigQuery
        partition_by={
            'field': 'event_date',
            'data_type': 'date',
            'granularity': 'day'
        },
        cluster_by=['campaign_id', 'user_id'],
        on_schema_change='append_new_columns'
    )
}}

SELECT
    event_id,
    user_id,
    session_id,
    campaign_id,
    event_type,
    DATE(event_at) AS event_date,
    event_at,
    revenue_usd,
    cost_usd
FROM {{ source('events', 'raw_ad_events') }}

{% if is_incremental() %}
-- Process partitions from the last 3 days (handles late data)
WHERE DATE(event_at) >= DATE_SUB(
    (SELECT MAX(event_date) FROM {{ this }}),
    INTERVAL 3 DAY
)
{% endif %}
```

With `insert_overwrite` strategy on a date-partitioned table, DBT:
1. Identifies which partitions will be affected by the new data
2. Deletes those entire partitions from the existing table
3. Inserts the new data

This is more efficient than MERGE because it avoids row-level comparison.

### 14.3 Copy Grants on BigQuery

When DBT recreates a table, BigQuery permissions are lost. Use `copy_grants` to preserve them:

```sql
{{ config(
    materialized='table',
    copy_grants=true    -- Copy IAM grants from previous table version
) }}
```

### 14.4 BigQuery Scripting and Stored Procedures via DBT

```sql
-- Use BigQuery scripting syntax via pre/post hooks
{{ config(
    post_hook="""
        CALL `costco-project.procedures.refresh_materialized_view`(
            '{{ this.schema }}',
            '{{ this.identifier }}'
        );
    """
) }}
```

### 14.5 Time-Partitioned vs Ingestion-Partitioned Tables

**Time-partitioned** (recommended): Use an explicit timestamp column:
```sql
{{ config(
    partition_by={
        'field': 'event_date',         -- Explicit column
        'data_type': 'date'
    }
) }}
```

**Ingestion-partitioned**: Partition by load time (`_PARTITIONTIME`):
```sql
{{ config(
    partition_by={
        'field': '_PARTITIONTIME',     -- Pseudo-column
        'data_type': 'timestamp'
    }
) }}
```

Use time-partitioned when possible — you can backfill specific partitions without re-processing everything.

---

## 15. Incremental Models — Full Deep Dive

### 15.1 Why Incremental Models?

Full table refreshes don't scale. For a table with 1 billion rows, recomputing every row every day is:
- Expensive (BigQuery charges by bytes scanned)
- Slow (may take hours)
- Fragile (if it fails mid-run, you have partial data)

Incremental models only process new or changed rows.

### 15.2 The Four Incremental Strategies

#### Strategy 1: `append` — Simplest, for insert-only workloads

```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='append'
    )
}}

SELECT
    event_id,
    user_id,
    event_at,
    event_type
FROM {{ source('events', 'raw_events') }}

{% if is_incremental() %}
-- Only append rows newer than the latest existing row
WHERE event_at > (SELECT MAX(event_at) FROM {{ this }})
{% endif %}
```

**Behavior**: Only inserts new rows. Never updates or deletes.

**Risk**: If the source retransmits data (late arriving events), you get duplicates.

**Use when**: Source data is immutable and append-only (e.g., click events with guaranteed-unique IDs from Pub/Sub).

#### Strategy 2: `merge` — Most flexible

```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key='click_id',                 -- The key for MERGE ON condition
        merge_update_columns=['cost_usd', 'updated_at']  -- Only update these columns
    )
}}

SELECT
    click_id,
    campaign_id,
    user_id,
    clicked_at,
    cost_usd,
    CURRENT_TIMESTAMP() AS updated_at
FROM {{ source('google_ads', 'raw_clicks') }}

{% if is_incremental() %}
WHERE clicked_at >= TIMESTAMP_SUB(
    (SELECT MAX(clicked_at) FROM {{ this }}),
    INTERVAL 3 DAY
)
{% endif %}
```

**Behavior**: Uses SQL MERGE (UPSERT). Rows matching `unique_key` are updated; new rows are inserted.

**Compiled SQL** (simplified):
```sql
MERGE INTO `project`.`dataset`.`stg_ad_clicks` AS DBT_INTERNAL_TARGET
USING (SELECT ...) AS DBT_INTERNAL_SOURCE
ON DBT_INTERNAL_TARGET.click_id = DBT_INTERNAL_SOURCE.click_id
WHEN MATCHED THEN
    UPDATE SET cost_usd = DBT_INTERNAL_SOURCE.cost_usd,
               updated_at = DBT_INTERNAL_SOURCE.updated_at
WHEN NOT MATCHED THEN
    INSERT (click_id, campaign_id, user_id, clicked_at, cost_usd, updated_at)
    VALUES (DBT_INTERNAL_SOURCE.click_id, ...)
```

**Use when**: Source data can update existing rows (e.g., cost adjustments after click validation).

#### Strategy 3: `insert_overwrite` — Best for BigQuery partitioned tables

```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='insert_overwrite',
        partition_by={
            'field': 'event_date',
            'data_type': 'date'
        }
    )
}}

SELECT
    event_id,
    DATE(event_at) AS event_date,
    campaign_id,
    event_at,
    cost_usd
FROM {{ source('events', 'raw_events') }}

{% if is_incremental() %}
-- Process last 3 days to handle late data
WHERE DATE(event_at) >= DATE_SUB(
    (SELECT MAX(event_date) FROM {{ this }}),
    INTERVAL 3 DAY
)
{% endif %}
```

**Behavior**: Deletes and replaces entire partitions. No row-level MERGE needed.

**Why it's efficient on BigQuery**: BigQuery's slot usage for partition replacement is much lower than row-level MERGE on large tables. Cost is based on data scanned by the SELECT, not by the INSERT.

**Use when**: Data is partitioned by date and late data affects whole date partitions (most common case in AdTech).

#### Strategy 4: `delete+insert` — Two-step approach

```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key='click_id'
    )
}}
```

**Behavior**: First deletes rows where `unique_key` matches, then inserts all rows from the new data batch.

**Use when**: MERGE is not supported or is too slow. Useful in Postgres/Redshift.

### 15.3 The `is_incremental()` Flag

`is_incremental()` returns `True` only when:
1. The target table already exists
2. The materialization is `incremental`
3. The `--full-refresh` flag was NOT passed

```sql
{% if is_incremental() %}
    -- Only when running incrementally (table exists)
    WHERE event_at > (SELECT MAX(event_at) FROM {{ this }})
{% endif %}
```

When you run `dbt run --full-refresh`, `is_incremental()` returns `False`, so the WHERE clause is skipped and the entire table is rebuilt from scratch.

### 15.4 Handling Late-Arriving Data

The most common mistake with incremental models: using `WHERE event_at > MAX(event_at)` without a lookback buffer.

Late data problem:
```
Day 1 (Jan 1): Events land → table shows MAX = Jan 1 23:59
Day 2 (Jan 2): Some Jan 1 events arrive late (network delay from ad network)
Day 2 run: WHERE event_at > Jan 1 23:59 → MISSES late Jan 1 events
```

Solution — use a lookback window:
```sql
{% if is_incremental() %}
WHERE event_at >= TIMESTAMP_SUB(
    (SELECT MAX(event_at) FROM {{ this }}),
    INTERVAL {{ var('incremental_lookback_days', 3) }} DAY   -- Look back 3 days
)
{% endif %}
```

For `insert_overwrite` on partitioned tables, the partition replacement handles this naturally — you overwrite entire date partitions, so late data is automatically included when you reprocess that partition.

### 15.5 The --full-refresh Flag

```bash
# Rebuild the entire table from scratch (ignore incremental filter)
dbt run --select mart_campaign_performance --full-refresh

# When to use full-refresh:
# 1. Schema changes (new columns added to source)
# 2. Bug fix that affects historical data
# 3. First run on a new environment
# 4. Backfilling historical data
```

### 15.6 Incremental Predicates (DBT 1.3+)

For complex incremental logic, use `incremental_predicates`:

```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key='event_id',
        incremental_predicates=[
            "DBT_INTERNAL_TARGET.event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)"
        ]
    )
}}
```

This adds a partition filter to the MERGE's ON clause, limiting the rows DBT needs to scan in the existing table. Critical for performance on very large tables.

---

## 16. DAG, Lineage and the Manifest

### 16.1 Understanding the DAG

The **DAG (Directed Acyclic Graph)** is DBT's dependency graph. Every `ref()` and `source()` creates an edge.

```
source:google_ads.raw_clicks ─────────────────────────────┐
source:google_ads.raw_impressions ────────────────────────┤
source:google_ads.raw_campaigns ──┐                       │
                                   ↓                       ↓
                            stg_campaigns           stg_ad_clicks
                            stg_ad_impressions ─────────────┘
                                   │                       │
                                   └──────────┬────────────┘
                                              ↓
                                    int_ad_events
                                    int_attributed_conversions ← stg_conversions
                                              │
                                              ↓
                                    mart_campaign_performance
                                    mart_roas_by_channel
```

### 16.2 Manifest.json — The Artifact That Powers CI/CD

After every `dbt compile` or `dbt run`, DBT writes `target/manifest.json`. This JSON file contains:
- Complete node definitions (models, tests, sources, seeds)
- Column-level metadata
- Model configs (materialization, schema, etc.)
- Full DAG (node dependencies)
- Compiled SQL for each node
- Execution results (timing, status)

The manifest is critical for **slim CI** (running only changed models). By comparing the current manifest against the production manifest, DBT can identify which models changed:

```bash
# In CI: run only models changed in this PR + their downstream dependents
dbt run --select state:modified+

# Requires: production manifest.json at --state path
dbt run --select state:modified+ --state gs://costco-dbt-artifacts/prod/
```

### 16.3 Selecting Models with Graph Operators

DBT's `--select` syntax has powerful graph traversal operators:

```bash
# Run a specific model
dbt run --select mart_campaign_performance

# Run model + all its upstream dependencies (+ means upstream)
dbt run --select +mart_campaign_performance

# Run model + all its downstream dependents (+ after means downstream)
dbt run --select mart_campaign_performance+

# Both upstream and downstream
dbt run --select +mart_campaign_performance+

# All models in a directory
dbt run --select models/marts/marketing/

# All models with a specific tag
dbt run --select tag:daily

# Models in a specific package
dbt run --select package:dbt_utils

# Exclude a model
dbt run --select +mart_campaign_performance --exclude mart_roas_by_channel

# State-based selection (CI/CD)
dbt run --select state:modified+          # Changed + downstream
dbt run --select state:new                # New models only
dbt test --select state:modified          # Test only changed models
```

---

## 17. Environments, Profiles and Targets

### 17.1 The Dev/CI/Prod Pattern

| Environment | Who Uses It | Purpose | Schema Pattern |
|------------|-------------|---------|----------------|
| `dev` | Individual developers | Local development, iteration | `dbt_viraaj_staging`, `dbt_viraaj_marts` |
| `ci` | Pull Request pipelines | Automated PR validation | `dbt_ci_pr123_staging` |
| `prod` | Production | Live analytics | `staging`, `marts` |

### 17.2 Using Variables for Environment-Specific Behavior

```yaml
# dbt_project.yml
vars:
  attribution_window_days: 30          # Default
  start_date: '2024-01-01'             # Default start date for dev
  enable_audit_logging: false          # Default off
```

Override at runtime:
```bash
# Dev: shorter lookback to reduce cost
dbt run --vars '{"start_date": "2024-12-01", "attribution_window_days": 7}'

# Prod: full history
dbt run --target prod
```

In models:
```sql
{% if var('enable_audit_logging', false) %}
    INSERT INTO {{ ref('dbt_audit_log') }} VALUES (...)
{% endif %}
```

### 17.3 Personal Dev Schemas

Each developer should have their own schema so they don't overwrite each other:

```yaml
# ~/.dbt/profiles.yml
costco_martech:
  outputs:
    dev:
      type: bigquery
      dataset: "dbt_{{ env_var('DBT_USER', 'unknown') }}"  # e.g., dbt_viraaj
```

```bash
export DBT_USER=viraaj
dbt run  # Creates tables in dbt_viraaj dataset
```

---

## 18. DBT Cloud vs DBT Core

### 18.1 DBT Core (Open Source)

- Free, open-source Python library
- Run via CLI: `dbt run`, `dbt test`, `dbt build`
- You manage infrastructure: orchestration, scheduling, CI/CD
- Typically integrated with Airflow, Prefect, or Cloud Composer

```python
# Trigger DBT from Airflow (Cloud Composer)
from airflow.operators.bash_operator import BashOperator

dbt_run = BashOperator(
    task_id='dbt_run',
    bash_command='dbt run --target prod --select tag:daily',
    env={
        'DBT_USER': 'airflow',
        'GOOGLE_APPLICATION_CREDENTIALS': '/secrets/bq-sa.json'
    }
)

dbt_test = BashOperator(
    task_id='dbt_test',
    bash_command='dbt test --target prod --select tag:daily',
)

dbt_run >> dbt_test
```

### 18.2 DBT Cloud (SaaS)

- Managed service by dbt Labs
- Web IDE, job scheduler, deployment environments built-in
- Slim CI integration with GitHub/GitLab
- Automated artifact storage (manifest.json per run)
- Team collaboration features

Key DBT Cloud features:
- **Jobs**: Scheduled or triggered runs (like Cloud Composer but simpler)
- **Environments**: Dev/Staging/Prod environment configs in the UI
- **CI/CD**: Auto-run on PRs with `state:modified+` selection
- **Exploratory IDE**: Write and test models in browser

### 18.3 DBT in Cloud Composer (Airflow)

For Costco's GCP-native stack, DBT Core + Cloud Composer is the likely setup:

```python
# dags/martech_dbt_pipeline.py

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryCheckOperator

default_args = {
    'owner': 'martech-de',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': True,
    'email': ['martech-alerts@costco.com']
}

with DAG(
    dag_id='martech_dbt_daily',
    schedule_interval='0 6 * * *',   # 6 AM UTC daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=['martech', 'dbt']
) as dag:

    # Check that raw data is fresh before running DBT
    check_raw_freshness = BashOperator(
        task_id='check_source_freshness',
        bash_command='cd /dbt && dbt source freshness --target prod',
    )

    # Run staging models
    run_staging = BashOperator(
        task_id='run_staging',
        bash_command='cd /dbt && dbt run --target prod --select tag:staging',
    )

    # Test staging
    test_staging = BashOperator(
        task_id='test_staging',
        bash_command='cd /dbt && dbt test --target prod --select tag:staging',
    )

    # Run intermediate + marts
    run_marts = BashOperator(
        task_id='run_marts',
        bash_command='cd /dbt && dbt run --target prod --select tag:daily',
    )

    # Test marts
    test_marts = BashOperator(
        task_id='test_marts',
        bash_command='cd /dbt && dbt test --target prod --select tag:daily',
    )

    check_raw_freshness >> run_staging >> test_staging >> run_marts >> test_marts
```

---

## 19. CI/CD with DBT

### 19.1 The CI/CD Workflow

```
Developer pushes branch
        ↓
GitHub PR created
        ↓
CI pipeline triggers
        ↓
1. dbt deps (install packages)
2. dbt source freshness --target ci
3. dbt build --select state:modified+ --target ci
   (runs models + tests only for changed models and downstream)
        ↓
All checks pass? → PR can be merged
        ↓
Merge to main
        ↓
CD pipeline triggers
        ↓
dbt build --target prod  (full production run)
        ↓
Store manifest.json as artifact for next CI run
```

### 19.2 GitHub Actions CI Setup

```yaml
# .github/workflows/dbt-ci.yml

name: DBT CI

on:
  pull_request:
    branches: [main]
    paths:
      - 'dbt/**'

jobs:
  dbt-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install DBT
        run: pip install dbt-bigquery==1.7.0

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Install DBT packages
        run: dbt deps
        working-directory: dbt/

      - name: Download production manifest
        run: |
          gsutil cp gs://costco-dbt-artifacts/prod/manifest.json ./prod_manifest/manifest.json

      - name: Run DBT CI (slim CI)
        run: |
          dbt build \
            --target ci \
            --select state:modified+ \
            --state ./prod_manifest/ \
            --vars '{"pr_number": "${{ github.event.pull_request.number }}"}'
        working-directory: dbt/
        env:
          DBT_PR_NUMBER: ${{ github.event.pull_request.number }}

      - name: Upload CI manifest
        if: always()
        run: |
          gsutil cp dbt/target/manifest.json \
            gs://costco-dbt-artifacts/ci/pr-${{ github.event.pull_request.number }}/manifest.json
```

### 19.3 Slim CI — The Key Concept

Running all 200 models in CI for every PR would:
- Cost too much (BigQuery charges per scan)
- Take too long (30+ minutes)

Slim CI solves this by only running models that changed in the PR + their downstream dependencies:

```bash
# Requires production manifest at --state path
dbt build --select state:modified+ --state ./artifacts/prod/

# state:modified = any model whose SQL or config changed in this PR
# +            = also run all downstream dependents
```

How it works:
1. Download `manifest.json` from last production run
2. DBT compares current compiled SQL against production manifest SQL
3. Nodes with different SQL or config are `state:modified`
4. The `+` operator adds all downstream dependents

---

## 20. DBT Best Practices and Anti-Patterns

### 20.1 Naming Conventions (Critical)

```
Staging models:  stg_<source>__<entity>       e.g., stg_google_ads__clicks
Intermediate:    int_<description>             e.g., int_attributed_conversions
Marts:           mart_<description>            e.g., mart_campaign_performance
Snapshots:       scd_<entity>                  e.g., scd_campaigns
Seeds:           <descriptive_name>            e.g., channel_mapping
```

Note the **double underscore** `__` separating source from entity in staging — this is the dbt convention and makes it clear which source system the data comes from.

### 20.2 The Staging/Intermediate/Mart Layer Pattern

**The Rule**: Each layer has a specific and limited responsibility.

| Layer | Job | What It Should Do | What It Should NOT Do |
|-------|-----|-------------------|-----------------------|
| Staging | Clean raw data | Rename, cast, deduplicate | Join, aggregate, business logic |
| Intermediate | Business logic | Joins, sessionization, attribution | BI-ready aggregations |
| Mart | Analytics-ready | Aggregations, calculated metrics | Complex row-level logic |

Violating this leads to:
- Tightly coupled models (change one thing, break ten)
- Models that are impossible to test independently
- Lineage that doesn't reflect real data flow

### 20.3 Anti-Pattern: Hardcoding Database/Schema Names

```sql
-- WRONG — environment-specific, breaks in dev and CI
SELECT * FROM `costco-prod-project.raw_google_ads.raw_clicks`

-- CORRECT — environment-aware
SELECT * FROM {{ source('google_ads', 'raw_clicks') }}
SELECT * FROM {{ ref('stg_ad_clicks') }}
```

### 20.4 Anti-Pattern: Business Logic in Staging

```sql
-- WRONG — staging model with business logic
SELECT
    click_id,
    campaign_id,
    cost_usd,
    -- Attribution logic in staging = wrong layer
    CASE WHEN clicked_at >= '2024-01-01' THEN cost_usd * 1.2 ELSE cost_usd END AS adjusted_cost
FROM {{ source('google_ads', 'raw_clicks') }}

-- CORRECT — staging just cleans, intermediate applies business logic
-- staging: just expose cost_usd as-is
-- intermediate: apply business adjustments
```

### 20.5 Anti-Pattern: Using `*` in Models

```sql
-- WRONG — schema changes in source break downstream
SELECT * FROM {{ ref('stg_ad_clicks') }}

-- CORRECT — explicit columns
SELECT
    click_id,
    campaign_id,
    clicked_at,
    cost_usd
FROM {{ ref('stg_ad_clicks') }}
```

Exception: In staging models, `SELECT *` from source is acceptable as staging is a thin clean layer and you want all columns available.

### 20.6 Anti-Pattern: Re-joining the Same Data Multiple Times

```sql
-- WRONG — joining campaigns 3 times in different mart models
-- mart_roas joins campaigns to get campaign_name
-- mart_budget_pacing joins campaigns to get daily_budget
-- mart_conversion_rate joins campaigns to get campaign_type

-- CORRECT — join campaigns once in intermediate, reuse everywhere
-- int_campaign_enriched: stg_campaigns + all enrichment logic
-- All marts join to int_campaign_enriched
```

### 20.7 Anti-Pattern: Not Testing

Every model should have at minimum:
- `not_null` on primary key
- `unique` on primary key
- `not_null` on critical foreign keys
- `accepted_values` on status/type enums

No tests = no trust in the data.

### 20.8 Best Practice: DRY with Macros

When the same logic appears in 3+ models, extract it to a macro:

```sql
-- BAD: same ROAS calculation in 5 models
SAFE_DIVIDE(revenue_usd, spend_usd) AS roas

-- GOOD: macro called in 5 models
{{ safe_roas('revenue_usd', 'spend_usd') }} AS roas
```

### 20.9 Best Practice: CTEs Over Subqueries

```sql
-- BAD — nested subqueries, hard to read and debug
SELECT *
FROM (
    SELECT click_id, SUM(cost) as total_cost
    FROM (SELECT * FROM raw_clicks WHERE status = 'valid') t1
    GROUP BY 1
) t2
WHERE total_cost > 100

-- GOOD — named CTEs, clear flow
WITH valid_clicks AS (
    SELECT * FROM {{ ref('stg_ad_clicks') }}
    WHERE status = 'valid'
),

click_costs AS (
    SELECT
        click_id,
        SUM(cost_usd) AS total_cost
    FROM valid_clicks
    GROUP BY 1
)

SELECT *
FROM click_costs
WHERE total_cost > 100
```

### 20.10 Best Practice: Document as You Build

Add `description` fields as you write models, not as a separate task later. When you add a column, add its description immediately in the YAML. Documentation debt accumulates fast.

---

## 21. DBT for AdTech/MarTech Pipelines

### 21.1 The Complete MarTech DBT Model Map

```
SOURCES (Raw Data)
├── google_ads: campaigns, ad_groups, keywords, clicks, impressions, conversions
├── meta_ads: campaigns, ad_sets, ads, insights (daily snapshots)
├── costco_members: member_profiles, transactions, loyalty_events
└── website: sessions, page_views, events (from GA4/BigQuery export)

STAGING (1:1 with sources)
├── stg_google_ads__campaigns
├── stg_google_ads__ad_clicks
├── stg_google_ads__impressions
├── stg_google_ads__conversions
├── stg_meta_ads__campaigns
├── stg_meta_ads__ad_insights
├── stg_members__profiles
├── stg_members__transactions
└── stg_website__sessions

INTERMEDIATE (Business Logic)
├── int_unified_ad_events           (union Google + Meta clicks)
├── int_attributed_conversions      (last/first/linear touch attribution)
├── int_member_ad_sessions          (join member profiles to ad clicks)
├── int_campaign_hierarchy          (campaign → ad_group → ad flattened)
└── int_member_ltv_segments         (RFM + LTV scoring)

MARTS (Analytics-Ready)
├── marketing/
│   ├── mart_campaign_performance   (daily by campaign: spend, ROAS, CTR)
│   ├── mart_channel_performance    (daily by channel: Google vs Meta vs organic)
│   ├── mart_attribution_report     (conversions with full attribution chain)
│   ├── mart_keyword_performance    (keyword-level for search campaigns)
│   └── mart_audience_performance   (performance by audience segment)
├── member/
│   ├── mart_member_acquisition     (which campaigns acquired which members)
│   ├── mart_member_ltv             (lifetime value by acquisition channel)
│   └── mart_cohort_retention       (member retention by acquisition cohort)
└── finance/
    └── mart_marketing_roi          (revenue attribution by campaign)

SNAPSHOTS
├── scd_campaigns                   (track budget/status changes over time)
├── scd_ad_group_targeting          (track targeting changes)
└── scd_member_segments             (track member segment evolution)
```

### 21.2 Building Multi-Touch Attribution in DBT

```sql
-- models/intermediate/int_attributed_conversions.sql
-- Linear attribution: split conversion credit equally across all touches

{{
    config(materialized='table')
}}

WITH conversions AS (
    SELECT * FROM {{ ref('stg_google_ads__conversions') }}
),

clicks AS (
    SELECT * FROM {{ ref('stg_google_ads__ad_clicks') }}
    WHERE clicked_at >= '{{ var("attribution_start_date", "2024-01-01") }}'
),

-- Find all touches for each conversion (within 30-day window)
all_touches AS (
    SELECT
        c.conversion_id,
        c.member_id,
        c.converted_at,
        c.conversion_value_usd,
        c.conversion_type,

        cl.click_id,
        cl.campaign_id,
        cl.ad_group_id,
        cl.channel_id,
        cl.clicked_at,

        TIMESTAMP_DIFF(c.converted_at, cl.clicked_at, HOUR) AS hours_before_conversion,

        -- Count total touches per conversion (for linear attribution)
        COUNT(*) OVER (PARTITION BY c.conversion_id) AS total_touches,

        -- Touch position (1 = first, total = last)
        ROW_NUMBER() OVER (
            PARTITION BY c.conversion_id
            ORDER BY cl.clicked_at ASC
        ) AS touch_position

    FROM conversions c
    INNER JOIN clicks cl
        ON c.member_id = cl.member_id
        AND cl.clicked_at BETWEEN
            TIMESTAMP_SUB(c.converted_at, INTERVAL {{ var('attribution_window_days', 30) }} DAY)
            AND c.converted_at
),

-- Compute attribution weights by model
attributed AS (
    SELECT
        *,

        -- Last-touch weight
        CASE
            WHEN touch_position = total_touches THEN 1.0
            ELSE 0.0
        END AS last_touch_weight,

        -- First-touch weight
        CASE
            WHEN touch_position = 1 THEN 1.0
            ELSE 0.0
        END AS first_touch_weight,

        -- Linear weight (equal credit to all touches)
        1.0 / total_touches AS linear_weight,

        -- Time-decay weight (more credit to recent touches)
        POW(0.5, (total_touches - touch_position) * 1.0)
            / SUM(POW(0.5, (total_touches - touch_position) * 1.0)) OVER (
                PARTITION BY conversion_id
              ) AS time_decay_weight

    FROM all_touches
)

SELECT
    conversion_id,
    member_id,
    converted_at,
    conversion_type,
    click_id,
    campaign_id,
    ad_group_id,
    channel_id,
    clicked_at,
    touch_position,
    total_touches,
    hours_before_conversion,

    -- Attribution credit by model
    ROUND(conversion_value_usd * last_touch_weight, 4)   AS last_touch_revenue,
    ROUND(conversion_value_usd * first_touch_weight, 4)  AS first_touch_revenue,
    ROUND(conversion_value_usd * linear_weight, 4)       AS linear_revenue,
    ROUND(conversion_value_usd * time_decay_weight, 4)   AS time_decay_revenue

FROM attributed
```

### 21.3 Member LTV Segmentation in DBT

```sql
-- models/intermediate/int_member_ltv_segments.sql

{{
    config(
        materialized='table',
        partition_by={'field': 'segment_date', 'data_type': 'date'},
        cluster_by=['member_segment', 'acquisition_channel']
    )
}}

WITH member_transactions AS (
    SELECT
        member_id,
        SUM(transaction_amount_usd)         AS total_spend_usd,
        COUNT(DISTINCT transaction_date)    AS active_days,
        COUNT(*)                            AS transaction_count,
        MIN(transaction_date)               AS first_transaction_date,
        MAX(transaction_date)               AS last_transaction_date,
        DATE_DIFF(CURRENT_DATE(), MAX(transaction_date), DAY) AS days_since_last_purchase
    FROM {{ ref('stg_members__transactions') }}
    WHERE transaction_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
    GROUP BY 1
),

rfm_scores AS (
    SELECT
        *,
        CURRENT_DATE() AS segment_date,

        -- Recency score (1-5, 5 = most recent)
        NTILE(5) OVER (ORDER BY days_since_last_purchase ASC) AS recency_score,

        -- Frequency score (1-5, 5 = most frequent)
        NTILE(5) OVER (ORDER BY transaction_count ASC) AS frequency_score,

        -- Monetary score (1-5, 5 = highest spend)
        NTILE(5) OVER (ORDER BY total_spend_usd ASC) AS monetary_score

    FROM member_transactions
),

segmented AS (
    SELECT
        *,
        (recency_score + frequency_score + monetary_score) AS rfm_total,

        -- Segment labels based on RFM
        CASE
            WHEN recency_score >= 4 AND frequency_score >= 4 AND monetary_score >= 4
                THEN 'champions'
            WHEN recency_score >= 3 AND frequency_score >= 3 AND monetary_score >= 3
                THEN 'loyal_customers'
            WHEN recency_score >= 4 AND frequency_score <= 2
                THEN 'new_customers'
            WHEN recency_score <= 2 AND frequency_score >= 3 AND monetary_score >= 3
                THEN 'at_risk'
            WHEN recency_score <= 2 AND frequency_score <= 2 AND monetary_score <= 2
                THEN 'lost_customers'
            ELSE 'potential_loyalists'
        END AS member_segment

    FROM rfm_scores
)

SELECT * FROM segmented
```

### 21.4 Cross-Channel Attribution Mart

```sql
-- models/marts/marketing/mart_attribution_report.sql

{{
    config(
        materialized='table',
        partition_by={'field': 'conversion_date', 'data_type': 'date'},
        cluster_by=['channel_id', 'conversion_type']
    )
}}

WITH attributed_conversions AS (
    SELECT * FROM {{ ref('int_attributed_conversions') }}
),

channels AS (
    SELECT * FROM {{ ref('channel_mapping') }}  -- seed
),

campaigns AS (
    SELECT * FROM {{ ref('stg_google_ads__campaigns') }}
),

members AS (
    SELECT * FROM {{ ref('stg_members__profiles') }}
),

-- Aggregate by channel and date for reporting
final AS (
    SELECT
        DATE(ac.converted_at)           AS conversion_date,
        ac.conversion_type,
        c.channel_name,
        c.channel_category,
        c.is_paid,

        -- Conversion counts
        COUNT(DISTINCT ac.conversion_id) AS conversions,
        COUNT(DISTINCT ac.member_id)     AS unique_converters,

        -- Attribution revenue by model
        SUM(ac.last_touch_revenue)       AS last_touch_revenue_usd,
        SUM(ac.first_touch_revenue)      AS first_touch_revenue_usd,
        SUM(ac.linear_revenue)           AS linear_revenue_usd,
        SUM(ac.time_decay_revenue)       AS time_decay_revenue_usd,

        -- Avg time to convert
        AVG(ac.hours_before_conversion)  AS avg_hours_to_convert,
        AVG(ac.total_touches)            AS avg_touches_per_conversion,

        -- Load metadata
        CURRENT_TIMESTAMP()              AS dbt_updated_at

    FROM attributed_conversions ac
    LEFT JOIN channels c USING (channel_id)
    GROUP BY 1, 2, 3, 4, 5
)

SELECT * FROM final
```

---

## 22. Performance Tuning DBT on BigQuery

### 22.1 Cost Control Strategies

**1. Limit Dev Queries with Conditional Filtering**
```sql
FROM {{ source('events', 'raw_events') }}

{% if target.name != 'prod' %}
-- Dev/CI: only last 30 days
WHERE DATE(event_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
{% endif %}
```

**2. Use Incremental Models for Large Tables**
Any table > 100M rows should be incremental, not a full table refresh.

**3. Project-Level Dev Limits**
```yaml
# dbt_project.yml
vars:
  dev_row_limit: 1000000   # 1M rows max in dev

models:
  costco_martech:
    +post-hook: >
      {% if target.name == 'dev' %}
        SELECT 'dev mode: row limit applied' as message
      {% endif %}
```

### 22.2 Query Performance Tuning

**Always partition mart models** — especially those queried by BI tools:
```sql
{{ config(
    materialized='table',
    partition_by={'field': 'report_date', 'data_type': 'date'},
    cluster_by=['campaign_id', 'channel_id']
) }}
```

BI tool query: `WHERE report_date = '2024-01-15'` → BigQuery reads only that partition.

**Use `require_partition_filter`** on very large tables to prevent accidental full scans:
```sql
{{ config(
    partition_by={'field': 'event_date', 'data_type': 'date'},
    require_partition_filter=True
) }}
```

**Thread Count Tuning**
```yaml
# profiles.yml
dev:
  threads: 4     # Run 4 models in parallel locally

prod:
  threads: 8     # Run 8 in parallel in prod (BigQuery handles concurrency well)
```

### 22.3 The `--defer` Flag (Critical for Cost Savings in Dev)

Instead of building all upstream models in dev (expensive), defer to production:

```bash
# Run only the model you're developing, but reference prod tables for upstream
dbt run \
  --select mart_campaign_performance \
  --defer \
  --state ./artifacts/prod/

# This runs:
# - mart_campaign_performance in your dev schema (dbt_viraaj)
# - All ref() calls resolve to PROD tables (not rebuilt in dev)
# Cost savings: 90%+ reduction in dev BigQuery costs
```

How it works: For every `ref()` that points to a model NOT in your dev schema, DBT substitutes the production version from the manifest.

### 22.4 Analyzing Slow Models

```bash
# Check model execution times
cat target/run_results.json | python3 -c "
import json, sys
results = json.load(sys.stdin)
nodes = sorted(results['results'], key=lambda x: x.get('execution_time', 0), reverse=True)
for n in nodes[:10]:
    print(f\"{n['execution_time']:.1f}s  {n['unique_id']}\")
"

# Output:
# 245.3s  model.costco_martech.mart_campaign_performance
# 180.1s  model.costco_martech.int_attributed_conversions
# 45.2s   model.costco_martech.stg_ad_clicks
```

Top optimization levers for slow models:
1. Add partitioning and clustering
2. Reduce the lookback window in incremental filter
3. Switch from `merge` to `insert_overwrite` on BigQuery
4. Use `incremental_predicates` to filter existing table rows during MERGE
5. Replace correlated subqueries with window functions

---

## 23. Advanced DBT Patterns

### 23.1 Dynamic Models with Jinja Loops

When you have many similar models (e.g., one per ad platform), use macros to generate them:

```sql
-- macros/generate_platform_staging.sql

{% macro generate_platform_staging(platform, source_name, table_name) %}

WITH source AS (
    SELECT * FROM {{ source(source_name, table_name) }}
),

standardized AS (
    SELECT
        '{{ platform }}'                    AS platform,
        campaign_id,
        ad_group_id,
        LOWER(campaign_name)                AS campaign_name,
        CAST(report_date AS DATE)           AS report_date,
        CAST(impressions AS INT64)          AS impressions,
        CAST(clicks AS INT64)               AS clicks,
        CAST(spend AS FLOAT64)              AS spend_usd,
        CAST(conversions AS INT64)          AS conversions,
        CAST(conversion_value AS FLOAT64)   AS conversion_value_usd
    FROM source
)

SELECT * FROM standardized

{% endmacro %}
```

```sql
-- models/staging/stg_google_ads__performance.sql
{{ generate_platform_staging('google', 'google_ads', 'campaign_performance') }}

-- models/staging/stg_meta_ads__performance.sql
{{ generate_platform_staging('meta', 'meta_ads', 'ad_insights') }}

-- models/staging/stg_tiktok_ads__performance.sql
{{ generate_platform_staging('tiktok', 'tiktok_ads', 'campaign_report') }}
```

### 23.2 The `run_query` Macro — Dynamic SQL

```sql
-- macros/get_active_campaigns.sql

{% macro get_active_campaigns() %}
    {% set query %}
        SELECT DISTINCT campaign_id
        FROM {{ ref('stg_campaigns') }}
        WHERE campaign_status = 'active'
    {% endset %}

    {% set results = run_query(query) %}

    {% if execute %}
        {% set campaign_ids = results.columns[0].values() %}
        {{ return(campaign_ids) }}
    {% else %}
        {{ return([]) }}
    {% endif %}
{% endmacro %}
```

```sql
-- Use in a model
SELECT *
FROM {{ ref('mart_campaign_performance') }}
WHERE campaign_id IN (
    {% for cid in get_active_campaigns() %}
        '{{ cid }}'{% if not loop.last %},{% endif %}
    {% endfor %}
)
```

### 23.3 Unit Testing DBT Models (dbt-unit-testing package)

```yaml
# tests/unit/test_mart_campaign_performance.yml

unit_tests:
  - name: test_roas_calculation
    model: mart_campaign_performance
    given:
      - input: ref('int_ad_events')
        rows:
          - {campaign_id: 'C001', report_date: '2024-01-01', spend_usd: 100.0, revenue_usd: 300.0}
          - {campaign_id: 'C001', report_date: '2024-01-01', spend_usd: 0.0, revenue_usd: 50.0}
    expect:
      rows:
        - {campaign_id: 'C001', report_date: '2024-01-01', roas: 3.0}
        - {campaign_id: 'C001', report_date: '2024-01-01', roas: null}  # spend = 0 → null ROAS
```

### 23.4 Multi-Project DBT (dbt Mesh)

For large organizations, DBT supports cross-project references:

```
Project A: raw_transforms (staging + intermediate)
  ↓ publishes select nodes as "public"

Project B: marketing_marts (marts that ref() Project A models)
  ↓
Project C: finance_marts (mart that ref() Project A + Project B)
```

```yaml
# dbt_project.yml in Project B
dependencies:
  - name: raw_transforms
    project: costco-raw-transforms  # Cross-project reference

# In a model in Project B
SELECT * FROM {{ ref('raw_transforms', 'int_attributed_conversions') }}
```

This pattern is called **dbt Mesh** — it enables:
- Team autonomy (each team owns their DBT project)
- Shared data contracts (published interfaces between projects)
- Independent CI/CD (projects deploy independently)

### 23.5 Column-Level Lineage

DBT 1.6+ supports column-level lineage tracking through the `persist_docs` config:

```yaml
# dbt_project.yml
models:
  +persist_docs:
    relation: true
    columns: true
```

This writes column descriptions to BigQuery table/view metadata, enabling tools to trace which columns in a mart came from which source columns.

---

## 24. Interview Questions and Model Answers

### 24.1 Conceptual Questions

**Q1: What is DBT and how does it fit in the modern data stack?**

DBT is a transformation framework that enables data engineers and analysts to write modular SELECT-based SQL transformations with built-in dependency management, testing, and documentation. It sits in the T of ELT — after data is loaded into the warehouse by tools like Fivetran or custom Dataflow pipelines, DBT handles all transformations within the warehouse. At Costco's MarTech stack, DBT would orchestrate the transformation of raw ad event data from Google Ads and Meta into analytics-ready campaign performance tables and member attribution models.

---

**Q2: What are the four materializations in DBT? When would you use each?**

**View**: Creates a SQL view. No data stored. Best for staging models where freshness is more important than query speed and the underlying queries are lightweight.

**Table**: Full table rebuild on every run. Best for mart models that are queried heavily by BI tools and where a full refresh is computationally feasible.

**Incremental**: Appends or merges only new/changed rows. Essential for large event tables (billions of rows) where a full refresh would be too expensive or time-consuming. At Costco, the ad click events table would be incremental.

**Ephemeral**: Not materialized in the warehouse. Inlined as a CTE in downstream models. Best for pure logic helpers referenced by only one or two models.

---

**Q3: How does DBT handle dependencies?**

Through the `ref()` function. When model B calls `{{ ref('model_a') }}`, DBT:
1. Resolves `model_a` to its fully-qualified name at runtime (handling dev/prod schema differences automatically)
2. Adds an edge in the DAG: B depends on A

DBT then uses topological sort to determine execution order. Models at the top of the DAG (sources, staging) run first; marts run last. DBT also parallelizes independent models using threads.

---

**Q4: What is the difference between `ref()` and `source()`?**

`ref()` references models that DBT manages (other `.sql` files in the project). It creates a DAG dependency and resolves the fully-qualified name dynamically.

`source()` references raw tables that DBT does not own — typically tables loaded by Fivetran, Airbyte, or custom pipelines. You declare sources in YAML with freshness checks. Sources also appear in the DAG lineage, so you can trace all the way from raw data to dashboard.

---

**Q5: Explain incremental model strategies on BigQuery.**

For BigQuery, the three relevant strategies are:

**`merge`**: Uses BigQuery's MERGE statement. For each row in the new batch, if a row with the same `unique_key` exists in the target table, it's updated; otherwise it's inserted. Best when rows can be modified (e.g., cost adjustments to clicks).

**`insert_overwrite`**: The most efficient for BigQuery partitioned tables. For the partitions covered by the new data batch, DBT deletes those entire partitions and replaces them. No row-level comparison needed. Best for event tables partitioned by date.

**`append`**: Simply inserts new rows without checking for duplicates. Only safe for immutable, deduplicated source data.

For a table like ad click events (500M+ rows/month, partitioned by click_date), I'd use `insert_overwrite` with a 3-day lookback to handle late-arriving events.

---

**Q6: How does slim CI work in DBT?**

Slim CI uses `state:modified+` selection with a reference to the production manifest:

```bash
dbt build --select state:modified+ --state ./artifacts/prod/
```

DBT compares the current compiled SQL of each model against what's in the production manifest. Models whose SQL or config differs are `state:modified`. The `+` includes all downstream dependents. This means a PR that only touches one staging model will only rebuild that staging model and its downstream intermediates and marts — not the entire project.

This drastically reduces CI cost and runtime. For a 200-model project, a change to one staging model might only trigger 5-10 models to run instead of all 200.

---

### 24.2 Hands-On / Coding Questions

**Q7: Write a DBT incremental model for ad click events on BigQuery.**

```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='insert_overwrite',
        partition_by={
            'field': 'click_date',
            'data_type': 'date',
            'granularity': 'day'
        },
        cluster_by=['campaign_id', 'channel_id'],
        on_schema_change='append_new_columns'
    )
}}

WITH source AS (
    SELECT
        click_id,
        campaign_id,
        ad_group_id,
        channel_id,
        member_id,
        DATE(clicked_at)                        AS click_date,
        clicked_at,
        cost_micros / 1000000.0                 AS cost_usd,
        device_type,
        match_type,
        _loaded_at
    FROM {{ source('google_ads', 'raw_clicks') }}

    {% if is_incremental() %}
    -- Process last 3 days to handle late-arriving data
    WHERE DATE(clicked_at) >= DATE_SUB(
        (SELECT MAX(click_date) FROM {{ this }}),
        INTERVAL 3 DAY
    )
    {% endif %}
)

SELECT * FROM source
WHERE click_id IS NOT NULL
```

---

**Q8: Write a DBT snapshot for tracking campaign budget changes.**

```sql
-- snapshots/scd_campaigns.sql

{% snapshot scd_campaigns %}

{{
    config(
        target_schema='snapshots',
        unique_key='campaign_id',
        strategy='timestamp',
        updated_at='updated_at',
        invalidate_hard_deletes=True
    )
}}

SELECT
    campaign_id,
    campaign_name,
    campaign_status,
    daily_budget_usd,
    target_cpa_usd,
    bidding_strategy,
    start_date,
    end_date,
    updated_at
FROM {{ source('google_ads', 'raw_campaigns') }}

{% endsnapshot %}
```

To query: "What was the budget for campaign C001 on March 15?"
```sql
SELECT daily_budget_usd
FROM {{ ref('scd_campaigns') }}
WHERE campaign_id = 'C001'
  AND DATE('2024-03-15') >= DATE(dbt_valid_from)
  AND DATE('2024-03-15') < DATE(COALESCE(dbt_valid_to, '9999-12-31'))
```

---

**Q9: How would you implement multi-touch attribution in DBT?**

I'd use three layers:

1. **Staging**: Clean click and conversion data individually
2. **Intermediate** (`int_attributed_conversions`): Join clicks to conversions using a time-window join (all clicks within 30 days before a conversion, for the same member). Calculate weight per attribution model (last-touch=1.0 for last click; linear=1/N for each touch; time-decay=exponential decay).
3. **Mart** (`mart_attribution_report`): Aggregate attributed revenue by campaign, channel, date.

The key SQL pattern is a self-joining conversion-to-click join with `ROW_NUMBER()` for last-touch, and `COUNT(*) OVER (PARTITION BY conversion_id)` for linear weight.

---

**Q10: A DBT model is running for 4 hours in production. How do you troubleshoot and fix it?**

**Step 1: Identify the slow model**
```bash
cat target/run_results.json | python -c "..."  # find which model is slowest
```

**Step 2: Check if it's a full refresh issue**
Is this model running as a full table rebuild when it should be incremental?

**Step 3: Check the compiled SQL**
```bash
cat target/compiled/.../slow_model.sql
```
Look for missing WHERE clauses, Cartesian joins, unoptimized subqueries.

**Step 4: Check BigQuery execution plan**
Run the compiled SQL in BigQuery Console. Look at the execution details:
- How many bytes were processed?
- Is there a full table scan on a large table?
- Is there a join that fans out (many-to-many)?

**Step 5: Common fixes**
- Add `WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)` to limit lookback
- Switch from `MERGE` to `insert_overwrite` if on BigQuery with partitioned tables
- Add partitioning/clustering configs to the model
- Replace correlated subqueries with window functions
- Use `incremental_predicates` to limit MERGE scan on existing table rows

---

**Q11: How do you handle schema changes in an incremental model?**

DBT's `on_schema_change` config controls behavior:

```sql
{{ config(
    materialized='incremental',
    on_schema_change='append_new_columns'   # Options below
) }}
```

| Option | Behavior |
|--------|----------|
| `ignore` (default) | Silently ignore new/removed columns |
| `fail` | Fail the run if schema changes detected |
| `append_new_columns` | Add new columns to existing table; ignore removed columns |
| `sync_all_columns` | Add new columns AND remove deleted columns (dangerous — data loss) |

Best practice for production: use `append_new_columns`. When a source adds a new column, DBT adds it to your table automatically. When a column is removed, existing data is preserved. If a major schema change requires rebuilding, run `dbt run --full-refresh`.

---

**Q12: You need to run DBT tests that check referential integrity across models. How?**

Use the `relationships` generic test:

```yaml
# In stg_ad_clicks.yml
columns:
  - name: campaign_id
    tests:
      - relationships:
          to: ref('stg_campaigns')
          field: campaign_id
```

This runs: `SELECT click_id FROM stg_ad_clicks WHERE campaign_id NOT IN (SELECT campaign_id FROM stg_campaigns)`

If any rows are returned, the test fails.

For performance on BigQuery, note that `relationships` tests can be expensive on large tables. You can add a filter:
```yaml
- relationships:
    to: ref('stg_campaigns')
    field: campaign_id
    config:
      where: "clicked_at >= '2024-01-01'"  # Only test recent data
```

---

**Q13: How do you organize a DBT project for a team of 10 data engineers?**

**Project structure by domain**:
```
models/
├── staging/        # Raw source cleaning — owned by ingestion team
├── intermediate/   # Domain logic — owned by domain teams
│   ├── marketing/
│   ├── member/
│   └── finance/
└── marts/          # Final tables — owned by analytics team
    ├── marketing/
    ├── member/
    └── finance/
```

**Key governance decisions**:
1. **Naming conventions**: Enforce `stg_<source>__<entity>` for staging, `int_` for intermediate, `mart_` for marts
2. **Schema isolation in dev**: Each engineer gets `dbt_<name>_staging`, `dbt_<name>_marts` via `generate_schema_name` override
3. **Required tests**: At minimum `unique` + `not_null` on primary keys for every model — enforced in CI
4. **Docs required**: `description` mandatory for all models and columns — enforced in CI via `dbt docs generate` + custom check
5. **Tags**: Every model tagged by team and refresh frequency (`tag:marketing`, `tag:daily`)
6. **CI/CD**: Slim CI on every PR (`state:modified+`) with auto-merge blocked if tests fail

---

**Q14: What is `dbt build` and how is it different from `dbt run`?**

`dbt run` only executes models (creates tables/views).

`dbt build` runs **all node types in DAG order**:
1. Seeds (load CSVs)
2. Snapshots
3. Models (run SQL)
4. Tests (validate output)

And it does this in dependency order — if `stg_ad_clicks` has tests, they run immediately after `stg_ad_clicks` is built, before `int_ad_events` (which depends on it) runs. This means a test failure in staging prevents downstream models from running — no point building marts on top of bad staging data.

```bash
dbt build                             # Build everything
dbt build --select tag:daily          # Build daily models + their tests
dbt build --select state:modified+    # Slim CI build
```

---

**Q15: How do you implement row-level security or data masking in DBT?**

DBT itself doesn't enforce row-level security — that's a warehouse concern. But you can implement masking at the model layer:

```sql
-- In dev: mask sensitive member data
SELECT
    member_id,
    {% if target.name == 'prod' %}
        email,
        phone_number,
    {% else %}
        -- Mask PII in dev/CI environments
        CONCAT(LEFT(email, 2), '***@***.com') AS email,
        CONCAT('***-***-', RIGHT(phone_number, 4)) AS phone_number,
    {% endif %}
    loyalty_tier,
    total_spend_usd
FROM {{ source('members', 'raw_profiles') }}
```

For production row-level security, configure BigQuery's row-level security policies or column-level security policies outside DBT, then document the policy in the exposure YAML.

---

*End of Topic 11: DBT Full Mastery*

---

## Summary: Key DBT Concepts for the Costco Interview

| Concept | One-Line Summary |
|---------|-----------------|
| `ref()` | References another DBT model; creates DAG dependency |
| `source()` | References raw table DBT doesn't manage; enables freshness checks |
| `is_incremental()` | True when running incrementally; used to filter only new rows |
| `insert_overwrite` | Best incremental strategy for BigQuery partitioned tables |
| `merge` | UPSERT-style incremental; use when rows can change |
| `snapshot` | SCD Type 2 history tracking for dimension tables |
| Slim CI | `state:modified+` — run only changed models + downstream in PRs |
| `--defer` | Use prod tables for upstream deps in dev; massive cost savings |
| `generate_schema_name` | Override to prevent schema name collision between dev and prod |
| `dbt build` | Run seeds + snapshots + models + tests in DAG order |
