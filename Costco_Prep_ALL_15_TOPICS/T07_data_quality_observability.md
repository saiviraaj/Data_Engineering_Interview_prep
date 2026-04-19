# Topic 7: Data Quality, Validation & Observability
## Costco Sr. Data Engineer — Exhaustive Interview Textbook

---

## Table of Contents
1. [L1: Core Concepts — Data Quality Dimensions](#l1-core-concepts)
2. [L2: Deep Technical Understanding](#l2-deep-technical-understanding)
3. [L3: Real-World Scenarios — Costco/MarTech Style](#l3-real-world-scenarios)
4. [L4: Hands-On Code & Design](#l4-hands-on-code--design)
5. [L5: Edge Cases & Pitfalls](#l5-edge-cases--pitfalls)
6. [L6: Interview Questions — Easy to Very Hard](#l6-interview-questions)

---

## L1: Core Concepts

### 1.1 The Six Dimensions of Data Quality

Data quality is not a single metric — it's a multi-dimensional assessment. Understanding these dimensions is fundamental to senior-level DQ discussions.

| Dimension | Definition | Example Failure | Detection Method |
|-----------|------------|-----------------|-----------------|
| **Completeness** | Required data is present, not null | click_id is NULL for 5% of rows | NOT NULL checks, null rate monitoring |
| **Uniqueness** | No unexpected duplicates | Same click_id appears 3 times | COUNT vs COUNT(DISTINCT), duplicate checks |
| **Validity** | Values conform to format/range rules | cost_usd = -50 (negative cost) | Range checks, regex validation, enum checks |
| **Consistency** | Values consistent across related tables/fields | clicks.campaign_id not in campaigns table | Referential integrity checks |
| **Timeliness** | Data arrives and is processed on time | Yesterday's events not loaded by 8 AM | Freshness monitoring, SLA checks |
| **Accuracy** | Data matches real-world truth | Revenue = $100K in BQ, $110K in source system | Reconciliation against source, checksums |

### 1.2 Where Data Quality Breaks Down — The Pipeline Layers

```
Source Systems     → Ingestion      → Staging       → Transform     → Mart
─────────────       ──────────       ────────         ──────────      ────
• Schema drift     • Late data      • Null inflation • Logic bugs    • Wrong aggregation
• Type changes     • Duplicates     • Encoding bugs  • Join fan-out  • Missing rows
• Upstream bugs    • Partial loads  • Truncation     • Dedup errors  • Stale dimensions
```

**Senior insight**: Most data quality issues originate upstream (source systems, ingestion), but are discovered downstream (BI dashboards, analyst complaints). The earlier you catch a quality issue, the cheaper it is to fix.

---

### 1.3 Data Observability — The Four Pillars

Data observability is the ability to understand the health of your data pipelines from the inside:

1. **Freshness**: Is data up to date? How old is the newest record?
2. **Volume**: Is the expected amount of data present? Is it abnormally high or low?
3. **Schema**: Has the structure changed unexpectedly?
4. **Distribution**: Are value distributions within expected bounds? (No sudden spike in NULL rates, no new unexpected values)

---

## L2: Deep Technical Understanding

### 2.1 Validation Framework Design

A robust validation framework has three layers:

**Layer 1: Schema validation** (structure)
- Column names and types match expected schema
- Required columns are present
- No unexpected new columns (schema drift detection)

**Layer 2: Constraint validation** (rules on values)
- NOT NULL on required columns
- Uniqueness on primary keys
- Range checks (cost > 0, rate between 0 and 1)
- Referential integrity (FK exists in dimension table)
- Enum validation (status in allowed values)

**Layer 3: Statistical validation** (distribution)
- Row count within expected bounds (vs prior period or baseline)
- NULL rate within expected bounds
- Value distribution hasn't shifted significantly
- Key metrics (ROAS, CTR) within expected ranges

---

### 2.2 Implementing Validation in SQL and Python

#### 2.2.1 SQL-Based Validation Checks

```sql
-- ============================================================
-- COMPLETENESS: null rate per critical column
-- ============================================================
SELECT
    'click_id'      AS column_name,
    COUNTIF(click_id IS NULL) AS null_count,
    COUNT(*) AS total_rows,
    ROUND(100.0 * COUNTIF(click_id IS NULL) / COUNT(*), 4) AS null_pct,
    CASE WHEN COUNTIF(click_id IS NULL) > 0 THEN 'FAIL' ELSE 'PASS' END AS status
FROM `staging.ad_clicks`
WHERE click_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)

UNION ALL

SELECT
    'campaign_id',
    COUNTIF(campaign_id IS NULL),
    COUNT(*),
    ROUND(100.0 * COUNTIF(campaign_id IS NULL) / COUNT(*), 4),
    CASE WHEN 100.0 * COUNTIF(campaign_id IS NULL) / COUNT(*) > 1.0 THEN 'FAIL' ELSE 'PASS' END
FROM `staging.ad_clicks`
WHERE click_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY);

-- ============================================================
-- UNIQUENESS: duplicate detection
-- ============================================================
WITH duplicates AS (
    SELECT
        click_id,
        COUNT(*) AS cnt
    FROM `staging.ad_clicks`
    WHERE click_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    GROUP BY click_id
    HAVING COUNT(*) > 1
)
SELECT
    'click_id_uniqueness'               AS check_name,
    COUNT(*) AS duplicate_key_count,
    SUM(cnt - 1) AS extra_rows,
    CASE WHEN COUNT(*) > 0 THEN 'FAIL' ELSE 'PASS' END AS status
FROM duplicates;

-- ============================================================
-- VALIDITY: value range checks
-- ============================================================
SELECT
    COUNT(*) AS total_rows,
    COUNTIF(cost_usd < 0) AS negative_cost_rows,
    COUNTIF(cost_usd > 10000) AS suspicious_high_cost_rows,
    COUNTIF(ctr < 0 OR ctr > 1) AS invalid_ctr_rows,
    COUNTIF(device_type NOT IN ('mobile','desktop','tablet','unknown')) AS invalid_device_rows,
    CASE
        WHEN COUNTIF(cost_usd < 0) > 0 THEN 'FAIL: negative cost'
        WHEN COUNTIF(ctr < 0 OR ctr > 1) > 0 THEN 'FAIL: invalid CTR'
        ELSE 'PASS'
    END AS status
FROM `staging.ad_events`
WHERE report_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY);

-- ============================================================
-- CONSISTENCY: referential integrity
-- ============================================================
SELECT
    'campaign_id_referential_integrity' AS check_name,
    COUNT(*) AS orphan_click_count,
    CASE WHEN COUNT(*) > 0 THEN 'FAIL' ELSE 'PASS' END AS status
FROM `staging.ad_clicks` c
LEFT JOIN `staging.campaigns` camp USING (campaign_id)
WHERE camp.campaign_id IS NULL
  AND c.click_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY);

-- ============================================================
-- TIMELINESS: freshness check
-- ============================================================
SELECT
    MAX(click_date)                         AS latest_data_date,
    DATE_DIFF(CURRENT_DATE(), MAX(click_date), DAY) AS days_behind,
    CASE
        WHEN DATE_DIFF(CURRENT_DATE(), MAX(click_date), DAY) > 1 THEN 'FAIL'
        ELSE 'PASS'
    END AS status
FROM `staging.ad_clicks`;

-- ============================================================
-- VOLUME: row count anomaly detection
-- ============================================================
WITH daily_counts AS (
    SELECT
        click_date,
        COUNT(*) AS row_count
    FROM `staging.ad_clicks`
    WHERE click_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY click_date
),

stats AS (
    SELECT
        AVG(row_count)      AS mean_count,
        STDDEV(row_count)   AS stddev_count
    FROM daily_counts
    WHERE click_date < DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)  -- exclude today
)

SELECT
    d.click_date,
    d.row_count,
    s.mean_count,
    s.stddev_count,
    (d.row_count - s.mean_count) / s.stddev_count AS z_score,
    CASE
        WHEN ABS((d.row_count - s.mean_count) / s.stddev_count) > 3 THEN 'ANOMALY'
        ELSE 'NORMAL'
    END AS status
FROM daily_counts d
CROSS JOIN stats s
WHERE d.click_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY);
```

---

#### 2.2.2 Python-Based Validation Framework

```python
from dataclasses import dataclass, field
from typing import Callable, Any
from enum import Enum
import logging
from google.cloud import bigquery

logger = logging.getLogger(__name__)

class Severity(Enum):
    ERROR = "ERROR"     # pipeline should stop
    WARNING = "WARNING" # alert but continue
    INFO = "INFO"       # log only

@dataclass
class ValidationRule:
    name: str
    description: str
    severity: Severity
    check_fn: Callable[[Any], bool]
    threshold: float = 0.0   # tolerance threshold

@dataclass
class ValidationResult:
    rule_name: str
    passed: bool
    severity: Severity
    actual_value: Any
    threshold: float
    message: str

class DataQualityValidator:
    """
    Modular validation framework.
    Runs a suite of rules and produces a structured report.
    """
    
    def __init__(self, bq_client: bigquery.Client, table: str, execution_date: str):
        self.bq = bq_client
        self.table = table
        self.execution_date = execution_date
        self.results: list[ValidationResult] = []
    
    def run_sql_check(self, sql: str) -> list[dict]:
        return [dict(row) for row in self.bq.query(sql).result()]
    
    def check_not_null(
        self, column: str, max_null_pct: float = 0.0, severity: Severity = Severity.ERROR
    ) -> ValidationResult:
        sql = f"""
            SELECT
                ROUND(100.0 * COUNTIF({column} IS NULL) / COUNT(*), 4) AS null_pct
            FROM `{self.table}`
            WHERE DATE(event_date) = '{self.execution_date}'
        """
        result = self.run_sql_check(sql)[0]
        null_pct = result['null_pct']
        passed = null_pct <= max_null_pct
        
        return ValidationResult(
            rule_name=f"not_null_{column}",
            passed=passed,
            severity=severity,
            actual_value=null_pct,
            threshold=max_null_pct,
            message=f"{column} null rate: {null_pct:.2f}% (threshold: {max_null_pct}%)"
        )
    
    def check_uniqueness(
        self, columns: list, severity: Severity = Severity.ERROR
    ) -> ValidationResult:
        col_str = ', '.join(columns)
        sql = f"""
            SELECT COUNT(*) AS duplicate_count
            FROM (
                SELECT {col_str}, COUNT(*) AS cnt
                FROM `{self.table}`
                WHERE DATE(event_date) = '{self.execution_date}'
                GROUP BY {col_str}
                HAVING cnt > 1
            )
        """
        result = self.run_sql_check(sql)[0]
        dup_count = result['duplicate_count']
        
        return ValidationResult(
            rule_name=f"unique_{'+'.join(columns)}",
            passed=dup_count == 0,
            severity=severity,
            actual_value=dup_count,
            threshold=0,
            message=f"Duplicate ({col_str}) count: {dup_count}"
        )
    
    def check_row_count_vs_baseline(
        self,
        lookback_days: int = 7,
        min_z_score: float = -3.0,
        max_z_score: float = 3.0,
        severity: Severity = Severity.WARNING
    ) -> ValidationResult:
        sql = f"""
            WITH daily_counts AS (
                SELECT DATE(event_date) AS dt, COUNT(*) AS cnt
                FROM `{self.table}`
                WHERE DATE(event_date) >= DATE_SUB('{self.execution_date}', INTERVAL {lookback_days + 1} DAY)
                GROUP BY 1
            ),
            baseline AS (
                SELECT AVG(cnt) AS mean, STDDEV(cnt) AS std
                FROM daily_counts
                WHERE dt < '{self.execution_date}'
            ),
            today AS (
                SELECT cnt FROM daily_counts WHERE dt = '{self.execution_date}'
            )
            SELECT
                today.cnt AS today_count,
                baseline.mean,
                baseline.std,
                SAFE_DIVIDE(today.cnt - baseline.mean, baseline.std) AS z_score
            FROM today CROSS JOIN baseline
        """
        rows = self.run_sql_check(sql)
        if not rows:
            return ValidationResult(
                rule_name="row_count_baseline",
                passed=False,
                severity=severity,
                actual_value=0,
                threshold=0,
                message=f"No data found for {self.execution_date}"
            )
        
        row = rows[0]
        z = row['z_score'] or 0
        passed = min_z_score <= z <= max_z_score
        
        return ValidationResult(
            rule_name="row_count_baseline",
            passed=passed,
            severity=severity,
            actual_value=row['today_count'],
            threshold=0,
            message=f"Row count {row['today_count']} (mean={row['mean']:.0f}, z={z:.2f})"
        )
    
    def run_all(self, rules: list[dict]) -> list[ValidationResult]:
        """Run all validation rules and return results."""
        results = []
        
        for rule in rules:
            method = getattr(self, rule['check'])
            result = method(**rule.get('params', {}))
            results.append(result)
            
            # Log and potentially halt on ERROR
            if not result.passed:
                log_fn = logger.error if result.severity == Severity.ERROR else logger.warning
                log_fn(f"[{result.severity.value}] {result.rule_name}: {result.message}")
        
        return results
    
    def assert_no_errors(self, results: list[ValidationResult]):
        """Raise exception if any ERROR-severity check failed."""
        errors = [r for r in results if not r.passed and r.severity == Severity.ERROR]
        if errors:
            error_msgs = '\n'.join(f"  - {e.rule_name}: {e.message}" for e in errors)
            raise DataQualityError(
                f"Data quality check FAILED for {self.table} on {self.execution_date}:\n{error_msgs}"
            )

class DataQualityError(Exception):
    pass

# Usage in Airflow task
def run_dq_checks(execution_date: str):
    bq = bigquery.Client()
    validator = DataQualityValidator(bq, "project.staging.ad_clicks", execution_date)
    
    rules = [
        {'check': 'check_not_null', 'params': {'column': 'click_id', 'max_null_pct': 0.0}},
        {'check': 'check_not_null', 'params': {'column': 'campaign_id', 'max_null_pct': 0.5}},
        {'check': 'check_uniqueness', 'params': {'columns': ['click_id']}},
        {'check': 'check_row_count_vs_baseline', 'params': {'lookback_days': 7}},
    ]
    
    results = validator.run_all(rules)
    validator.assert_no_errors(results)
    
    # Write results to monitoring table
    bq.load_table_from_json(
        [r.__dict__ for r in results],
        "project.monitoring.dq_results"
    )
    
    return results
```

---

### 2.3 DBT Tests as Data Quality

```yaml
# models/staging/_stg_ad_clicks.yml
version: 2

models:
  - name: stg_ad_clicks
    description: "Cleaned ad click events"
    tests:
      # Model-level tests
      - dbt_utils.expression_is_true:
          expression: "cost_usd >= 0"
      - dbt_utils.expression_is_true:
          expression: "ctr between 0 and 1 or ctr is null"
    
    columns:
      - name: click_id
        tests:
          - unique:
              severity: error      # HARD FAIL
          - not_null:
              severity: error
      
      - name: campaign_id
        tests:
          - not_null:
              severity: error
          - relationships:         # referential integrity
              to: ref('stg_campaigns')
              field: campaign_id
              severity: warn       # SOFT FAIL — alert but don't block
      
      - name: device_type
        tests:
          - accepted_values:
              values: ['mobile', 'desktop', 'tablet', 'unknown']
              severity: warn
      
      - name: cost_usd
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: "cost_usd >= 0"

# Custom singular test for business logic
# tests/assert_roas_not_infinite.sql
SELECT campaign_id, report_date, spend_usd, revenue_usd
FROM {{ ref('mart_campaign_performance') }}
WHERE spend_usd = 0 AND revenue_usd > 0  -- infinite ROAS: data issue
-- Returns rows = test FAILS
```

---

### 2.4 Reconciliation — The Gold Standard

```sql
-- Source-to-Target reconciliation
-- Compare counts and sums between source system and BigQuery

WITH source_stats AS (
    -- Run this on the source database (PostgreSQL/MySQL)
    -- Stored as a reference snapshot
    SELECT
        '2024-01-15'        AS report_date,
        987654              AS row_count,
        1234567.89          AS total_spend_usd,
        9876543.21          AS total_revenue_usd
    -- In production: this would be populated by the ingestion job
    -- which records source stats before loading
),

target_stats AS (
    SELECT
        click_date          AS report_date,
        COUNT(*)            AS row_count,
        SUM(cost_usd)       AS total_spend_usd,
        SUM(revenue_usd)    AS total_revenue_usd
    FROM `marts.ad_clicks`
    WHERE click_date = '2024-01-15'
    GROUP BY 1
)

SELECT
    s.report_date,
    s.row_count AS source_rows,
    t.row_count AS target_rows,
    s.row_count - t.row_count AS row_diff,
    ROUND(100.0 * ABS(s.row_count - t.row_count) / s.row_count, 4) AS row_pct_diff,

    ROUND(s.total_spend_usd, 2) AS source_spend,
    ROUND(t.total_spend_usd, 2) AS target_spend,
    ROUND(ABS(s.total_spend_usd - t.total_spend_usd), 2) AS spend_diff,

    CASE
        WHEN ABS(s.row_count - t.row_count) / s.row_count > 0.001 THEN 'ROW COUNT MISMATCH'
        WHEN ABS(s.total_spend_usd - t.total_spend_usd) / s.total_spend_usd > 0.001 THEN 'SPEND MISMATCH'
        ELSE 'PASS'
    END AS reconciliation_status

FROM source_stats s
JOIN target_stats t USING (report_date);
```

---

### 2.5 Monitoring & Alerting Architecture

```
Data Pipeline → Validation Checks → Results Table → Monitoring DAG
                                                          │
                                                    ┌─────┴─────┐
                                                    │           │
                                              ERROR → PagerDuty  WARNING → Slack
                                              (pipeline halts)   (alert, continue)
```

```python
# Monitoring DAG: runs after every pipeline DAG
# Checks recent DQ results and sends alerts

def check_dq_results_and_alert(execution_date: str):
    from google.cloud import bigquery
    
    bq = bigquery.Client()
    
    # Get failures from last run
    failures = list(bq.query(f"""
        SELECT
            table_name,
            rule_name,
            severity,
            message,
            actual_value
        FROM `monitoring.dq_results`
        WHERE execution_date = '{execution_date}'
          AND passed = FALSE
        ORDER BY severity DESC
    """).result())
    
    if not failures:
        return  # all good
    
    errors   = [f for f in failures if f.severity == 'ERROR']
    warnings = [f for f in failures if f.severity == 'WARNING']
    
    # Error → PagerDuty (immediate wake-up call)
    if errors:
        pagerduty_alert(
            title=f"Data Quality ERROR on {execution_date}",
            body=format_failures(errors),
            severity='critical'
        )
        raise DataQualityError(f"{len(errors)} ERROR-severity DQ checks failed")
    
    # Warning → Slack
    if warnings:
        slack_alert(
            channel='#data-quality-alerts',
            message=f"⚠️ {len(warnings)} DQ warnings on {execution_date}",
            details=format_failures(warnings)
        )
```

---

### 2.6 Root Cause Analysis — Debugging Bad Data

```
Step 1: WHEN did it break?
  → Check DQ monitoring history: when did this check start failing?
  → git blame / deployment history: what changed around that time?

Step 2: WHERE is it broken?
  → Which layer introduced the issue?
  → Check raw data first: is it in the source or introduced by pipeline?

Step 3: WHAT is the pattern?
  → Is it all rows or specific subset?
  → Is it specific campaigns, dates, channels?
  → Is it consistent or intermittent?

Step 4: WHY did it happen?
  → Schema change upstream?
  → Logic bug in transformation?
  → New data pattern not handled?

Step 5: FIX and PREVENT
  → Hotfix current data
  → Add DQ check to catch it earlier in future
  → Add regression test
```

```sql
-- Root cause investigation: finding WHERE bad data enters pipeline

-- Step 1: Is it in raw data?
SELECT COUNT(*), COUNTIF(cost_usd < 0)
FROM `raw.google_ads_clicks`
WHERE click_date = '2024-01-15';
-- If negative cost here → source system issue

-- Step 2: Is it introduced during staging?
SELECT COUNT(*), COUNTIF(cost_usd < 0)
FROM `staging.ad_clicks`
WHERE click_date = '2024-01-15';
-- If OK in raw but bad in staging → transformation bug

-- Step 3: Narrow to specific transformation
-- Check the compiled SQL for the staging model
-- Look for: CAST that could flip sign, division that could go negative, CASE logic error

-- Step 4: Check by data segment
SELECT
    DATE(clicked_at)        AS date,
    device_type,
    channel,
    COUNTIF(cost_usd < 0)   AS negative_count,
    COUNT(*)                AS total
FROM `raw.google_ads_clicks`
WHERE click_date BETWEEN '2024-01-10' AND '2024-01-15'
GROUP BY 1, 2, 3
HAVING negative_count > 0
ORDER BY negative_count DESC;
-- Narrows to: mobile + google_display starting 2024-01-13
-- → Correlates with platform update on that date
```

---

## L3: Real-World Scenarios

### 3.1 Scenario: Building a Data Quality System for Costco MarTech

**Requirement**: Automated DQ checks across all 20 mart tables, with SLA alerting, daily report, and historical tracking.

```python
# Complete DQ framework structure

QUALITY_RULES = {
    'mart_campaign_performance': [
        # Completeness
        {'check': 'not_null', 'column': 'campaign_id', 'severity': 'ERROR'},
        {'check': 'not_null', 'column': 'report_date', 'severity': 'ERROR'},
        {'check': 'not_null', 'column': 'spend_usd', 'severity': 'ERROR'},
        
        # Uniqueness
        {'check': 'unique', 'columns': ['report_date', 'campaign_id'], 'severity': 'ERROR'},
        
        # Validity
        {'check': 'range', 'column': 'roas', 'min': 0, 'max': 100, 'severity': 'WARNING'},
        {'check': 'range', 'column': 'ctr_pct', 'min': 0, 'max': 100, 'severity': 'WARNING'},
        {'check': 'range', 'column': 'spend_usd', 'min': 0, 'severity': 'ERROR'},
        
        # Timeliness
        {'check': 'freshness', 'max_hours_behind': 26, 'severity': 'ERROR'},
        
        # Volume
        {'check': 'row_count_anomaly', 'z_score_threshold': 3.0, 'severity': 'WARNING'},
        
        # Business logic
        {'check': 'custom_sql',
         'sql': "SELECT COUNT(*) FROM {table} WHERE revenue_usd > 0 AND spend_usd = 0",
         'expected_count': 0,
         'severity': 'WARNING',
         'message': 'Revenue with zero spend (infinite ROAS)'},
    ]
}
```

---

### 3.2 Scenario: Investigating a ROAS Discrepancy

**Business report**: "Looker shows ROAS = 3.2 for Campaign C001 last week, but our Google Ads dashboard shows ROAS = 4.1. Which is correct?"

```sql
-- Step 1: Verify attribution model
-- BigQuery mart uses last-touch attribution (30-day window)
-- Google Ads uses direct click attribution (no cross-device)
-- These should differ — document and explain

-- Step 2: Check time zone alignment
SELECT
    campaign_id,
    SUM(spend_usd)      AS bq_spend_pst,
    SUM(revenue_usd)    AS bq_revenue_pst,
    SUM(revenue_usd) / SUM(spend_usd) AS bq_roas
FROM mart_campaign_performance
WHERE report_date BETWEEN '2024-01-08' AND '2024-01-14'  -- PST week
  AND campaign_id = 'C001'
GROUP BY 1;

-- Google Ads might use UTC (different day boundaries)

-- Step 3: Check for conversion window differences
-- Google Ads default: 30-day click conversion window
-- Your pipeline: 30-day window? 7-day? 

-- Step 4: Document the discrepancy source and provide both numbers
-- "BQ ROAS = 3.2 (last-touch, PST, 30-day window)"
-- "Google Ads ROAS = 4.1 (direct, UTC, includes view-through)"
```

---

## L4: Hands-On Code & Design

### 4.1 Complete DQ Pipeline in Airflow

```python
# Full Airflow DAG for data quality monitoring

with DAG('data_quality_monitoring', schedule='0 8 * * *', ...) as dag:

    # Run after main pipeline DAG
    wait_for_pipeline = ExternalTaskSensor(
        task_id='wait_for_martech_pipeline',
        external_dag_id='martech_daily_pipeline',
        external_task_id='dbt_test_marts',
        timeout=7200
    )

    run_dq_checks = PythonOperator(
        task_id='run_dq_checks',
        python_callable=run_all_dq_checks,
        op_kwargs={'execution_date': '{{ ds }}'}
    )

    reconcile_source = PythonOperator(
        task_id='source_target_reconciliation',
        python_callable=reconcile_all_tables,
        op_kwargs={'execution_date': '{{ ds }}'}
    )

    alert_on_failures = PythonOperator(
        task_id='alert_on_failures',
        python_callable=send_dq_report,
        op_kwargs={'execution_date': '{{ ds }}'}
    )

    wait_for_pipeline >> run_dq_checks >> reconcile_source >> alert_on_failures
```

---

## L5: Edge Cases & Pitfalls

### 5.1 False Positives — Over-Alerting Kills Observability

```python
# Problem: too-strict thresholds → alerts fire daily → team ignores them
# Real alerts get missed among the noise ("alert fatigue")

# BAD: absolute threshold that fires on normal variation
if row_count < 1000000:  # fires whenever there's a weekend dip
    alert()

# GOOD: statistical threshold relative to recent baseline
# Use z-score: alert only if count deviates > 3 standard deviations from 7-day mean
z_score = (today_count - mean_7d) / stddev_7d
if abs(z_score) > 3.0:
    alert()

# ALSO GOOD: separate weekday/weekend baselines
if is_weekend(execution_date):
    baseline = weekend_mean
else:
    baseline = weekday_mean

# BETTER: use relative comparison vs same day last week
pct_change = (today - last_week_same_day) / last_week_same_day
if abs(pct_change) > 0.20:  # >20% change vs same day last week
    alert()
```

### 5.2 Validation That Runs Too Slowly

```sql
-- BAD: running null check on 10B rows every hour
SELECT COUNTIF(click_id IS NULL) FROM raw.ad_clicks;
-- Full table scan: expensive, slow

-- GOOD: run on today's partition only
SELECT COUNTIF(click_id IS NULL)
FROM raw.ad_clicks
WHERE click_date = CURRENT_DATE();
-- 1000x cheaper

-- ALSO GOOD: use TABLESAMPLE for large-scale approximate checks
SELECT COUNTIF(click_id IS NULL) / COUNT(*) AS null_pct
FROM raw.ad_clicks TABLESAMPLE SYSTEM (1 PERCENT);
-- Only scans 1% of data, fast approximation
```

### 5.3 Silently Passing Tests That Shouldn't

```sql
-- DANGEROUS: referential integrity test that passes due to NULL behavior
-- clicks.campaign_id should always exist in campaigns table

-- WRONG TEST (passes even with bad data):
SELECT COUNT(*)
FROM staging.ad_clicks c
LEFT JOIN staging.campaigns camp USING (campaign_id)
WHERE camp.campaign_id IS NULL;
-- If all click.campaign_id values are NULL → LEFT JOIN produces NULLs everywhere
-- But the test passes because the join "matches" on NULL = NULL behavior... wait, no
-- Actually NULL != NULL in SQL, so all NULL campaign_ids join to nothing
-- Result: every click with NULL campaign_id appears as orphan
-- BUT: if you only check WHERE camp.campaign_id IS NULL, you capture both
--   1. Clicks with valid campaign_id not in campaigns → real integrity issue
--   2. Clicks with NULL campaign_id → separate null issue

-- CORRECT: separate the two issues
-- Issue 1: non-null campaign_id not in campaigns (referential integrity failure)
SELECT COUNT(*)
FROM staging.ad_clicks c
LEFT JOIN staging.campaigns camp USING (campaign_id)
WHERE c.campaign_id IS NOT NULL    -- exclude nulls from this check
  AND camp.campaign_id IS NULL;    -- not found in campaigns

-- Issue 2: null campaign_id (completeness failure)
SELECT COUNTIF(campaign_id IS NULL) FROM staging.ad_clicks;
```

---

## L6: Interview Questions — Easy to Very Hard

### EASY

**Q1: What are the dimensions of data quality? Give an example of each.**

**Answer**: Data quality has six dimensions:

**Completeness**: Required data is present. Example: 5% of click events have NULL click_id — incomplete.

**Uniqueness**: No unexpected duplicates. Example: the same transaction appears twice in the payments table — a duplicate record.

**Validity**: Values conform to expected format/range. Example: a CTR value of 1.5 (150%) is invalid since CTR must be between 0 and 1.

**Consistency**: Values are consistent across related data. Example: a click references campaign_id='C999' but campaign C999 doesn't exist in the campaigns table — referential integrity violation.

**Timeliness**: Data is available when needed. Example: the 8 AM daily report uses data that's 3 days old because the ingestion pipeline failed.

**Accuracy**: Data matches the real-world source of truth. Example: BigQuery shows $1M revenue for campaign C001, but the finance system shows $1.1M — 10% discrepancy.

---

### MEDIUM

**Q2: How do you detect that a data pipeline produced incorrect results without having access to the source system?**

**Answer**: Without source access, use internal consistency checks:

1. **Row count anomalies**: Compare today's count to a 7-day rolling baseline. Alert if count deviates more than 2-3 standard deviations. Sudden drops (50% fewer rows) indicate data loss; sudden spikes indicate duplicates.

2. **Key metric trends**: Monitor ROAS, CTR, and conversion rates over time. A 40% ROAS drop from prior day is likely a data issue, not a real business change. Use z-score anomaly detection.

3. **Cross-table consistency**: Total spend in `mart_campaign_performance` should equal total spend in `mart_channel_performance` when aggregated. If they differ → one has a bug.

4. **Intra-table validity**: `clicks ≤ impressions` always (you can't have more clicks than impressions). If violated → data pipeline error.

5. **Historical stability**: Metric values for closed historical periods should not change. If March 2024 revenue changes in July's run → incremental logic bug causing reprocessing of historical partitions.

---

**Q3: Walk me through how you'd investigate a stakeholder complaint: "The revenue number in my Looker dashboard for last week changed overnight."**

**Answer**:

**Step 1: Confirm the change**
Query the mart table directly for last week's revenue before and after the suspected change time. Use BigQuery's `INFORMATION_SCHEMA.TABLE_SNAPSHOTS` or time-travel queries:
```sql
-- BigQuery time travel: query table as it was 24 hours ago
SELECT SUM(revenue_usd) FROM `mart.campaign_performance`
FOR SYSTEM_TIME AS OF TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
WHERE report_date BETWEEN '2024-01-08' AND '2024-01-14';
```

**Step 2: Identify which layer changed**
- Did the mart table change? (DBT run re-ran the mart model for historical dates)
- Did the staging table change? (incremental model picked up new late-arriving data)
- Did the source data change? (upstream correction applied to historical records)

**Step 3: Check pipeline run logs**
- Was there a `--full-refresh` DBT run?
- Was there a backfill triggered by someone?
- Was the lookback window wider than expected?

**Step 4: Root cause**
Most common cause: incremental model with `WHERE event_date > MAX(event_date) - 3 DAYS` — reprocesses 3 days every run, and if there was late-arriving data, historical partitions got updated.

**Step 5: Communicate**
"The change is expected — late-arriving ad click data for last Monday arrived on Wednesday and was incorporated in Tuesday night's pipeline run. The updated number is more accurate than the original." OR "There was a bug — a full-refresh was accidentally run. I've corrected the data and added a guard to prevent this."

---

### HARD

**Q4: Design a data observability system for a 50-table BigQuery data warehouse that monitors freshness, volume, schema, and distribution automatically — without writing a custom check for each table.**

**What they're testing**: Scalable system design, metadata-driven validation.

**Answer**:

**Architecture**:

```
Metadata-driven config
    ↓
Universal validation engine
    ↓
BigQuery INFORMATION_SCHEMA (for schema monitoring)
BigQuery audit logs (for freshness)
Computed statistics table (for volume/distribution)
    ↓
Results table → Alerting → Dashboard
```

**1. Schema monitoring (automatic, no per-table config)**:
```python
def detect_schema_changes():
    """
    Compare today's column set vs yesterday's for every table.
    Uses INFORMATION_SCHEMA — no custom config needed.
    """
    sql = """
    WITH today AS (
        SELECT table_name, column_name, data_type
        FROM `project.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_schema = 'marts'
    ),
    yesterday AS (
        SELECT table_name, column_name, data_type
        FROM `project.INFORMATION_SCHEMA.COLUMNS`
        FOR SYSTEM_TIME AS OF TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
        WHERE table_schema = 'marts'
    )
    SELECT 'NEW_COLUMN' AS change_type, t.table_name, t.column_name, t.data_type
    FROM today t
    LEFT JOIN yesterday y USING (table_name, column_name)
    WHERE y.column_name IS NULL
    
    UNION ALL
    
    SELECT 'DROPPED_COLUMN', y.table_name, y.column_name, y.data_type
    FROM yesterday y
    LEFT JOIN today t USING (table_name, column_name)
    WHERE t.column_name IS NULL
    
    UNION ALL
    
    SELECT 'TYPE_CHANGED', t.table_name, t.column_name, 
           CONCAT(y.data_type, ' -> ', t.data_type)
    FROM today t
    JOIN yesterday y USING (table_name, column_name)
    WHERE t.data_type != y.data_type
    """
    # Run daily → automatically catches all 50 tables
```

**2. Volume and freshness (one query covers all tables)**:
```python
def collect_table_statistics():
    """
    For each table: row count, max partition date, null rates for key columns.
    Stored daily for trend analysis.
    """
    # Use BigQuery __TABLES__ system view for metadata
    sql = """
    SELECT
        table_id,
        row_count,
        last_modified_time / 1000 AS last_modified_ts,
        TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), TIMESTAMP_MILLIS(last_modified_time), HOUR) AS hours_since_modified
    FROM `project.marts.__TABLES__`
    """
    # Freshness alert: if hours_since_modified > table's SLA threshold
```

**3. Distribution monitoring (per column, sampled)**:
```sql
-- Run on each table daily, store results
-- Alert when null_rate increases by >5% vs 7-day average
SELECT
    CURRENT_DATE() AS check_date,
    'mart_campaign_performance' AS table_name,
    'roas' AS column_name,
    AVG(roas) AS mean,
    STDDEV(roas) AS stddev,
    COUNTIF(roas IS NULL) / COUNT(*) AS null_rate,
    MIN(roas) AS min_val,
    MAX(roas) AS max_val,
    APPROX_QUANTILES(roas, 100)[OFFSET(50)] AS median
FROM mart_campaign_performance
WHERE report_date = CURRENT_DATE() - 1;
```

**4. Comparison against historical baseline**:
- Compare today's statistics to 7-day rolling mean
- Alert if null_rate increases by >5% absolute
- Alert if row count z-score > 3 or < -3
- Alert if mean of key metrics shifts by >2 standard deviations

This system covers all 50 tables automatically. New tables added to the warehouse are automatically included in schema monitoring (INFORMATION_SCHEMA query covers all). Per-table thresholds stored in a config table.

---

### VERY HARD

**Q5: Your data quality team reports that 0.1% of campaign revenue records are duplicated in BigQuery. This has been happening for 3 months undetected. The business wants to know: what was the actual revenue for the last 90 days, and how do you prevent this in future?**

**What they're testing**: Investigation, remediation, and prevention of long-running data quality issues.

**Answer**:

**Phase 1: Quantify the impact**

```sql
-- Find ALL duplicates across 90 days
WITH ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY conversion_id      -- business key
               ORDER BY _loaded_at DESC        -- keep most recent load
           ) AS rn,
           COUNT(*) OVER (PARTITION BY conversion_id) AS dup_count
    FROM `marts.conversions`
    WHERE conversion_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
),

duplicates AS (
    SELECT * FROM ranked WHERE dup_count > 1
),

-- Compute over-counted revenue
overcount AS (
    SELECT
        DATE_TRUNC(conversion_date, MONTH) AS month,
        SUM(CASE WHEN rn = 1 THEN revenue_usd ELSE 0 END) AS correct_revenue,
        SUM(revenue_usd) AS reported_revenue,
        SUM(revenue_usd) - SUM(CASE WHEN rn = 1 THEN revenue_usd ELSE 0 END) AS overcounted_revenue
    FROM ranked
    GROUP BY 1
)

SELECT * FROM overcount ORDER BY month;
-- Shows: we over-reported revenue by X% each month
```

**Phase 2: Correct the historical data**

```sql
-- Fix: replace the duplicated table with deduplicated version
CREATE OR REPLACE TABLE `marts.conversions_corrected` AS
SELECT * EXCEPT (rn)
FROM (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY conversion_id
               ORDER BY _loaded_at DESC
           ) AS rn
    FROM `marts.conversions`
)
WHERE rn = 1;

-- Verify counts match expectation
SELECT
    COUNT(*) AS before_dedup,
    (SELECT COUNT(DISTINCT conversion_id) FROM marts.conversions) AS distinct_conversions
FROM marts.conversions;
-- If different → confirms duplicate issue
```

**Phase 3: Notify stakeholders**
"We've identified that conversion records were being duplicated due to a retry mechanism in our ingestion pipeline loading the same records multiple times. Revenue was overcounted by approximately X% per month. The corrected figures are attached. We've fixed the pipeline and added uniqueness monitoring."

**Phase 4: Root cause and prevention**

Root cause investigation:
- Check ingestion code: was there an `append` strategy without deduplication?
- Check Pub/Sub: were messages being redelivered without deduplication?
- Check Airflow retries: did task retries re-run the load without truncating first?

Prevention:
1. Add `unique(conversion_id)` DBT test — would have caught this on day 1
2. Change ingestion from WRITE_APPEND to MERGE on conversion_id
3. Add row count monitoring that compares `COUNT(*)` vs `COUNT(DISTINCT conversion_id)` — if they diverge by >0.01%, alert
4. Add reconciliation against source system monthly

---

## Summary: Data Quality — Senior Mastery Checklist

| Skill | What Senior Looks Like |
|-------|------------------------|
| DQ dimensions | Can define all 6; uses them to structure any DQ discussion |
| Validation framework | Modular, severity-based, stores results for trending |
| DBT tests | Uses generic + singular + custom tests; knows severity config |
| Anomaly detection | Z-score based volume monitoring; separate weekday/weekend baselines |
| Reconciliation | Source-to-target count and sum comparison |
| Root cause analysis | Systematic: when/where/what/why/fix framework |
| Observability | Freshness, volume, schema, distribution — automated for all tables |
| False positives | Uses statistical thresholds, not absolute; prevents alert fatigue |
| Historical correction | Time travel queries; dedup strategies; stakeholder communication |
| Prevention mindset | Every pipeline adds DQ checks; quality is built in, not bolted on |
