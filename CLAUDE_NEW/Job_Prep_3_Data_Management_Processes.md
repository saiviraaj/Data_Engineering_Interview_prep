# 📊 DATA MANAGEMENT & PROCESS IMPROVEMENT
## Complete Guide for Lloyds Technology Centre Interview

**Focus:** Data Governance, Documentation, Project Management, Process Improvement  
**Level:** Senior Data Engineer with Process Ownership  
**Target:** Enterprise-grade best practices

---

## 📚 TABLE OF CONTENTS

1. Data Management Systems Overview
2. Data Governance & Quality
3. Metadata Management
4. Data Cataloging
5. Documentation Best Practices
6. Knowledge Management Systems
7. Project Management for Data Engineers
8. Process Improvement Methodologies
9. Collaboration & Communication

---

## 🗄️ PART 1: DATA MANAGEMENT SYSTEMS OVERVIEW

### **1.1 What is a Data Management System?**

**Definition:** Integrated systems and processes to acquire, validate, store, protect, and process data to ensure accessibility, reliability, and timeliness of data.

### **Key Components:**

```
┌─────────────────────────────────────────────────────┐
│          DATA MANAGEMENT ECOSYSTEM                   │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐      ┌──────────────────┐        │
│  │  DATA        │      │  DATA QUALITY    │        │
│  │  CATALOG     │◄────►│  MANAGEMENT      │        │
│  │              │      │                  │        │
│  │ - Inventory  │      │ - Validation     │        │
│  │ - Lineage    │      │ - Profiling      │        │
│  │ - Discovery  │      │ - Monitoring     │        │
│  └──────────────┘      └──────────────────┘        │
│         │                       │                   │
│         ▼                       ▼                   │
│  ┌──────────────┐      ┌──────────────────┐        │
│  │  METADATA    │      │  DATA            │        │
│  │  MANAGEMENT  │◄────►│  GOVERNANCE      │        │
│  │              │      │                  │        │
│  │ - Business   │      │ - Policies       │        │
│  │ - Technical  │      │ - Access Control │        │
│  │ - Operational│      │ - Compliance     │        │
│  └──────────────┘      └──────────────────┘        │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### **1.2 Your Experience at Wells Fargo CDM Next**

**What to Highlight:**
```
PROJECT: Cloud Data Movement (CDM Next) Platform
- Scope: Enterprise-scale data migration
- Sources: Teradata, Oracle, Hadoop, Kafka → BigQuery
- Scale: Serving 100+ application teams
- Role: Senior Data Engineer

KEY RESPONSIBILITIES:
1. Data Pipeline Development
   - Designed ETL/ELT pipelines
   - Implemented data quality checks
   - Optimized BigQuery performance

2. Data Management
   - Metadata tracking for source-to-target mapping
   - Data lineage documentation
   - Schema evolution management

3. Process Improvement
   - Standardized pipeline templates
   - Automated testing frameworks
   - Reduced deployment time by X%
```

---

## 🎯 PART 2: DATA GOVERNANCE & QUALITY

### **2.1 Data Governance Framework**

#### **Key Principles:**
1. **Data Quality:** Accurate, complete, consistent, timely
2. **Data Security:** Access control, encryption, audit
3. **Data Privacy:** PII protection, GDPR compliance
4. **Data Ownership:** Clear roles and responsibilities

#### **Implementing Data Governance in BigQuery**

```python
# Data Quality Checks
class DataQualityValidator:
    """
    Validate data quality before loading
    """
    
    def __init__(self, project_id):
        self.client = bigquery.Client(project=project_id)
        self.logger = logging.getLogger(__name__)
    
    def validate_completeness(self, table_id, required_columns):
        """
        Check for null values in required columns
        """
        checks = []
        
        for col in required_columns:
            query = f"""
                SELECT 
                    '{col}' as column_name,
                    COUNT(*) as total_rows,
                    COUNTIF({col} IS NULL) as null_count,
                    COUNTIF({col} IS NULL) * 100.0 / COUNT(*) as null_percentage
                FROM `{table_id}`
            """
            
            result = self.client.query(query).to_dataframe()
            checks.append(result)
        
        df = pd.concat(checks, ignore_index=True)
        
        # Flag issues
        issues = df[df['null_percentage'] > 0]
        
        if not issues.empty:
            self.logger.warning(f"Data quality issues found:\n{issues}")
            return False
        
        return True
    
    def validate_uniqueness(self, table_id, unique_columns):
        """
        Check for duplicate records
        """
        cols_str = ', '.join(unique_columns)
        
        query = f"""
            SELECT 
                {cols_str},
                COUNT(*) as duplicate_count
            FROM `{table_id}`
            GROUP BY {cols_str}
            HAVING COUNT(*) > 1
        """
        
        duplicates = self.client.query(query).to_dataframe()
        
        if not duplicates.empty:
            self.logger.error(f"Found {len(duplicates)} duplicate records")
            return False
        
        return True
    
    def validate_referential_integrity(self, fact_table, dim_table, key_column):
        """
        Check foreign key constraints
        """
        query = f"""
            SELECT COUNT(*) as orphan_count
            FROM `{fact_table}` f
            LEFT JOIN `{dim_table}` d ON f.{key_column} = d.{key_column}
            WHERE d.{key_column} IS NULL
        """
        
        result = self.client.query(query).to_dataframe()
        orphan_count = result['orphan_count'].iloc[0]
        
        if orphan_count > 0:
            self.logger.error(f"Found {orphan_count} orphan records")
            return False
        
        return True
    
    def validate_all(self, table_id, validation_rules):
        """
        Run all validation checks
        """
        results = {
            'table': table_id,
            'timestamp': datetime.now(),
            'checks': []
        }
        
        # Completeness
        if 'required_columns' in validation_rules:
            passed = self.validate_completeness(
                table_id, 
                validation_rules['required_columns']
            )
            results['checks'].append({
                'check': 'completeness',
                'passed': passed
            })
        
        # Uniqueness
        if 'unique_columns' in validation_rules:
            passed = self.validate_uniqueness(
                table_id,
                validation_rules['unique_columns']
            )
            results['checks'].append({
                'check': 'uniqueness',
                'passed': passed
            })
        
        # Overall status
        all_passed = all(c['passed'] for c in results['checks'])
        results['status'] = 'PASSED' if all_passed else 'FAILED'
        
        return results

# Usage
validator = DataQualityValidator(project_id='my-project')

validation_rules = {
    'required_columns': ['user_id', 'transaction_id', 'amount'],
    'unique_columns': ['transaction_id']
}

results = validator.validate_all(
    'project.dataset.transactions',
    validation_rules
)

print(results)
```

### **2.2 Data Quality Metrics**

```sql
-- Data Quality Dashboard Query
WITH quality_metrics AS (
    SELECT 
        -- Completeness
        COUNT(*) as total_records,
        COUNTIF(user_id IS NULL) as missing_user_id,
        COUNTIF(amount IS NULL) as missing_amount,
        
        -- Validity
        COUNTIF(amount < 0) as invalid_amount,
        COUNTIF(DATE(transaction_date) > CURRENT_DATE()) as future_dates,
        
        -- Accuracy
        COUNTIF(country NOT IN ('US', 'UK', 'CA', 'AU')) as invalid_country,
        
        -- Consistency
        COUNTIF(total_amount != price * quantity) as calculation_mismatch
    
    FROM `project.dataset.transactions`
    WHERE DATE(transaction_date) = CURRENT_DATE()
)
SELECT 
    total_records,
    
    -- Completeness %
    (total_records - missing_user_id) * 100.0 / total_records as user_id_completeness,
    (total_records - missing_amount) * 100.0 / total_records as amount_completeness,
    
    -- Validity %
    (total_records - invalid_amount) * 100.0 / total_records as amount_validity,
    (total_records - future_dates) * 100.0 / total_records as date_validity,
    
    -- Overall Quality Score
    ((total_records - missing_user_id - missing_amount - invalid_amount - future_dates - invalid_country - calculation_mismatch) * 100.0 / total_records) as overall_quality_score

FROM quality_metrics;
```

---

## 📋 PART 3: METADATA MANAGEMENT

### **3.1 Metadata Types**

**Business Metadata:**
- Business glossary terms
- Data ownership
- Business rules
- Semantic definitions

**Technical Metadata:**
- Schema definitions
- Data types
- Constraints
- Indexes/partitions

**Operational Metadata:**
- Data lineage
- Processing history
- Job execution logs
- Data quality metrics

### **3.2 Implementing Metadata Management**

```python
# Metadata Catalog System
class MetadataCatalog:
    """
    Centralized metadata management
    """
    
    def __init__(self, project_id, catalog_dataset):
        self.project_id = project_id
        self.catalog_dataset = catalog_dataset
        self.client = bigquery.Client(project=project_id)
        self.setup_catalog_tables()
    
    def setup_catalog_tables(self):
        """
        Create metadata tables if not exist
        """
        # Table metadata
        table_metadata_schema = [
            bigquery.SchemaField("table_id", "STRING"),
            bigquery.SchemaField("table_name", "STRING"),
            bigquery.SchemaField("description", "STRING"),
            bigquery.SchemaField("owner", "STRING"),
            bigquery.SchemaField("created_date", "TIMESTAMP"),
            bigquery.SchemaField("last_updated", "TIMESTAMP"),
            bigquery.SchemaField("row_count", "INTEGER"),
            bigquery.SchemaField("size_gb", "FLOAT"),
        ]
        
        # Column metadata
        column_metadata_schema = [
            bigquery.SchemaField("table_id", "STRING"),
            bigquery.SchemaField("column_name", "STRING"),
            bigquery.SchemaField("data_type", "STRING"),
            bigquery.SchemaField("description", "STRING"),
            bigquery.SchemaField("is_nullable", "BOOLEAN"),
            bigquery.SchemaField("is_partition_key", "BOOLEAN"),
            bigquery.SchemaField("is_cluster_key", "BOOLEAN"),
        ]
        
        # Create tables (if not exist)
        # ... implementation
    
    def register_table(self, table_ref, metadata):
        """
        Register table in metadata catalog
        """
        table = self.client.get_table(table_ref)
        
        # Extract metadata
        table_metadata = {
            'table_id': str(table.reference),
            'table_name': table.table_id,
            'description': metadata.get('description', ''),
            'owner': metadata.get('owner', ''),
            'created_date': table.created,
            'last_updated': table.modified,
            'row_count': table.num_rows,
            'size_gb': table.num_bytes / (1024**3)
        }
        
        # Insert to catalog
        catalog_table = f"{self.project_id}.{self.catalog_dataset}.table_metadata"
        
        df = pd.DataFrame([table_metadata])
        
        job = self.client.load_table_from_dataframe(
            df,
            catalog_table,
            job_config=bigquery.LoadJobConfig(
                write_disposition='WRITE_APPEND'
            )
        )
        
        job.result()
    
    def get_table_lineage(self, table_id):
        """
        Get data lineage for table
        """
        # Query INFORMATION_SCHEMA for dependencies
        query = f"""
            SELECT
                table_catalog,
                table_schema,
                table_name,
                column_name,
                referenced_table,
                referenced_column
            FROM `{self.project_id}.{self.catalog_dataset}.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`
            WHERE table_name = '{table_id}'
        """
        
        lineage = self.client.query(query).to_dataframe()
        return lineage
```

---

## 📚 PART 4: DOCUMENTATION BEST PRACTICES

### **4.1 Documentation Structure**

```markdown
# Project Documentation Template

## 1. PROJECT OVERVIEW
- **Name:** [Project Name]
- **Owner:** [Team/Person]
- **Status:** [Active/In Development/Deprecated]
- **Last Updated:** [Date]

## 2. PURPOSE
Clear description of what this project does and why it exists.

## 3. ARCHITECTURE
```
Source Systems → Ingestion → Processing → Storage → Consumption
```

## 4. DATA SOURCES
| Source | Type | Refresh Frequency | Owner |
|--------|------|-------------------|-------|
| Oracle DB | JDBC | Daily | DBA Team |
| Kafka | Stream | Real-time | Platform Team |

## 5. DATA TRANSFORMATIONS
### 5.1 Cleaning Rules
- Remove nulls from `user_id`
- Filter `amount > 0`
- Deduplicate by `transaction_id`

### 5.2 Business Logic
```sql
-- Calculate customer lifetime value
SUM(amount) OVER (PARTITION BY user_id) as ltv
```

## 6. DATA QUALITY CHECKS
- Completeness: No nulls in required fields
- Uniqueness: `transaction_id` must be unique
- Validity: `amount` must be positive

## 7. SCHEDULING
- **Frequency:** Daily at 02:00 UTC
- **Dependencies:** Upstream job X must complete
- **SLA:** Complete by 04:00 UTC

## 8. MONITORING & ALERTS
- Alert if row count < 1000
- Alert if job fails
- Alert if runtime > 2 hours

## 9. TROUBLESHOOTING
### Common Issues
**Issue:** Job timeout
**Cause:** Large partition scan
**Solution:** Add partition filter

## 10. RUNBOOK
### How to Rerun Failed Job
```bash
python pipeline.py --date 2024-01-01 --rerun
```

## 11. CHANGE LOG
| Date | Change | Author |
|------|--------|--------|
| 2024-01-15 | Added partitioning | John |
```

### **4.2 Code Documentation Standards**

```python
def process_transactions(
    df: pd.DataFrame,
    start_date: str,
    end_date: str,
    min_amount: float = 0.0
) -> pd.DataFrame:
    """
    Process transaction data with business rules.
    
    Args:
        df: DataFrame containing raw transactions
        start_date: Start date filter (format: YYYY-MM-DD)
        end_date: End date filter (format: YYYY-MM-DD)
        min_amount: Minimum transaction amount (default: 0.0)
    
    Returns:
        Processed DataFrame with following columns:
        - transaction_id: Unique transaction identifier
        - user_id: Customer identifier
        - amount: Transaction amount (filtered by min_amount)
        - transaction_date: Date of transaction
        - category: Derived transaction category
    
    Raises:
        ValueError: If date format is invalid
        TypeError: If df is not a pandas DataFrame
    
    Example:
        >>> df = pd.DataFrame({
        ...     'transaction_id': [1, 2],
        ...     'user_id': [100, 101],
        ...     'amount': [50.0, 25.0],
        ...     'transaction_date': ['2024-01-01', '2024-01-02']
        ... })
        >>> result = process_transactions(df, '2024-01-01', '2024-01-31')
        >>> len(result)
        2
    
    Note:
        - Filters out negative amounts
        - Deduplicates by transaction_id (keeps last)
        - Adds 'category' column based on amount ranges
    
    Business Rules:
        - amount < 100: 'low'
        - 100 <= amount < 1000: 'medium'
        - amount >= 1000: 'high'
    """
    # Validate inputs
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    
    # Date filtering
    df = df[
        (df['transaction_date'] >= start_date) &
        (df['transaction_date'] <= end_date)
    ]
    
    # Amount filtering
    df = df[df['amount'] >= min_amount]
    
    # Deduplication
    df = df.drop_duplicates(subset=['transaction_id'], keep='last')
    
    # Add category
    df['category'] = pd.cut(
        df['amount'],
        bins=[0, 100, 1000, float('inf')],
        labels=['low', 'medium', 'high']
    )
    
    return df
```

---

## 🔄 PART 5: PROCESS IMPROVEMENT METHODOLOGIES

### **5.1 Identifying Improvement Opportunities**

**Framework: PDCA (Plan-Do-Check-Act)**

```
1. PLAN
   ├─ Identify problem
   ├─ Analyze root cause
   ├─ Develop solution
   └─ Define metrics

2. DO
   ├─ Implement on small scale
   └─ Document changes

3. CHECK
   ├─ Measure results
   ├─ Compare to baseline
   └─ Gather feedback

4. ACT
   ├─ Standardize if successful
   └─ Iterate if not
```

### **5.2 Real Process Improvements for Data Pipelines**

#### **Example 1: Reduce Pipeline Runtime**

**Problem:** Daily ETL job taking 4 hours (exceeds SLA)

**Analysis:**
```sql
-- Query job history to find bottlenecks
SELECT
    job_id,
    query,
    total_slot_ms / 1000 as total_seconds,
    total_bytes_processed / POW(10, 9) as gb_processed,
    creation_time
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE DATE(creation_time) = CURRENT_DATE()
  AND user_email = 'pipeline@company.com'
ORDER BY total_slot_ms DESC
LIMIT 10;
```

**Root Cause:**
- Full table scan on large fact table
- No partitioning
- SELECT * instead of specific columns

**Solution:**
1. Add date partitioning
2. Use partition filter in queries
3. Select only needed columns
4. Implement incremental loading

**Implementation:**
```python
# BEFORE
query = "SELECT * FROM large_table"

# AFTER
query = """
    SELECT user_id, amount, date
    FROM large_table
    WHERE date = '2024-01-01'  -- Partition filter
"""
```

**Results:**
- Runtime: 4 hours → 30 minutes (87.5% reduction)
- Cost: $50 → $5 (90% reduction)
- SLA: Now met with buffer

**Standardization:**
- Created partition filter template
- Added to coding standards
- Shared with team

#### **Example 2: Automate Manual Data Quality Checks**

**Problem:** Manual data validation taking 2 hours/day

**Solution:**
```python
# Automated validation framework
class AutomatedQualityChecks:
    def __init__(self):
        self.checks = []
    
    def add_check(self, name, query, threshold):
        self.checks.append({
            'name': name,
            'query': query,
            'threshold': threshold
        })
    
    def run_all_checks(self):
        results = []
        
        for check in self.checks:
            result = self.run_check(check)
            results.append(result)
        
        # Send alert if any failed
        failed = [r for r in results if not r['passed']]
        if failed:
            self.send_alert(failed)
        
        return results

# Define checks
validator = AutomatedQualityChecks()

validator.add_check(
    'null_user_ids',
    "SELECT COUNT(*) FROM table WHERE user_id IS NULL",
    threshold=0
)

validator.add_check(
    'row_count',
    "SELECT COUNT(*) FROM table",
    threshold=1000  # Min expected rows
)

# Run automatically after each load
results = validator.run_all_checks()
```

**Results:**
- Manual effort: 2 hours → 0 minutes
- Detection time: Next day → Immediate
- Coverage: 5 checks → 20 checks

### **5.3 Continuous Improvement Tracking**

```markdown
# Improvement Log Template

## Improvement ID: IMP-2024-001
**Date:** 2024-01-15
**Category:** Performance Optimization
**Priority:** High

**Current State:**
- Pipeline runtime: 4 hours
- Cost: $50/day
- SLA breaches: 2-3/week

**Proposed State:**
- Pipeline runtime: <1 hour
- Cost: <$10/day
- SLA breaches: 0

**Implementation:**
- Week 1: Add partitioning
- Week 2: Optimize queries
- Week 3: Test and validate
- Week 4: Deploy to production

**Metrics:**
| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Runtime | 4h | 30m | -87.5% |
| Cost | $50 | $5 | -90% |
| SLA Met | 60% | 100% | +40% |

**Lessons Learned:**
- Always check query execution plan
- Partition large tables by date
- Test on subset first

**Replication:**
- Created template for team
- Added to onboarding docs
- Shared in tech talk
```

---

## 📊 PART 6: PROJECT MANAGEMENT FOR DATA ENGINEERS

### **6.1 Agile for Data Projects**

**Sprint Structure:**
```
2-Week Sprint:
├─ Sprint Planning (2 hours)
│  ├─ Review backlog
│  ├─ Estimate stories
│  └─ Commit to sprint goal
│
├─ Daily Standups (15 min)
│  ├─ What I did yesterday
│  ├─ What I'm doing today
│  └─ Any blockers
│
├─ Sprint Review (1 hour)
│  └─ Demo completed work
│
└─ Sprint Retrospective (1 hour)
   ├─ What went well
   ├─ What can improve
   └─ Action items
```

### **6.2 Data Engineering User Stories**

**Template:**
```
As a [role]
I want [feature]
So that [benefit]

Acceptance Criteria:
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

Technical Notes:
- Implementation details
- Dependencies
- Risks
```

**Examples:**
```
Story 1: Incremental Data Loading

As a Data Engineer
I want to implement incremental loading for transactions table
So that we reduce processing time and costs

Acceptance Criteria:
- [ ] Only new records since last run are processed
- [ ] Pipeline is idempotent (can rerun safely)
- [ ] Logging shows records processed count
- [ ] Unit tests cover edge cases

Technical Notes:
- Use _PARTITIONTIME for watermark
- Store last run timestamp in metadata table
- Handle late-arriving data (7-day lookback)

Estimation: 5 story points
Dependencies: Metadata table creation
```

---

## 🎯 INTERVIEW PREPARATION - SCENARIOS

### **Scenario 1: Data Quality Issue**

**Question:** "We're seeing data quality issues in production. How would you approach this?"

**STAR Answer:**

**Situation:**
At Wells Fargo CDM Next, we received alerts about inconsistent customer data in BigQuery after migration from Oracle.

**Task:**
Need to identify root cause, fix data, and prevent recurrence.

**Action:**
1. **Immediate Response**
   - Quarantined affected partition
   - Notified downstream teams
   - Rolled back to last known good state

2. **Root Cause Analysis**
   - Queried audit logs
   - Found data type mismatch in source-to-target mapping
   - NUMBER(10,2) → STRING → precision loss

3. **Long-term Fix**
   - Implemented automated schema validation
   - Added data quality checks pre-load
   - Created data reconciliation reports

4. **Prevention**
   - Updated migration playbook
   - Added to code review checklist
   - Shared learnings in team retrospective

**Result:**
- Zero data quality incidents in following 6 months
- Reduced data validation time by 75%
- Framework adopted by 3 other teams

### **Scenario 2: Process Improvement**

**Question:** "Tell me about a process you improved"

**STAR Answer:**

**Situation:**
Manual deployment process taking 2-3 hours, error-prone, no rollback capability.

**Task:**
Automate deployment to reduce time and errors.

**Action:**
1. **Current State Analysis**
   - Documented 23-step manual process
   - Identified 5 high-risk steps
   - Calculated time: 2.5 hours average

2. **Solution Design**
   - Created CI/CD pipeline in Cloud Build
   - Automated testing (unit + integration)
   - Implemented blue-green deployment

3. **Implementation**
   ```yaml
   # Cloud Build config
   steps:
   - name: 'gcr.io/cloud-builders/python'
     args: ['python', '-m', 'pytest']
   
   - name: 'gcr.io/cloud-builders/gcloud'
     args: ['dataproc', 'jobs', 'submit']
   ```

4. **Rollout**
   - Piloted with 1 pipeline
   - Gathered feedback
   - Scaled to all 15 pipelines

**Result:**
- Deployment time: 2.5h → 15min (94% reduction)
- Errors: 10% → 0.5%
- Team velocity: +30%
- Deployments/week: 3 → 15

---

## 📝 QUICK REFERENCE - INTERVIEW TALKING POINTS

**Data Management:**
- "Implemented metadata catalog tracking 500+ tables"
- "Automated data quality checks reducing manual effort by 80%"
- "Created data lineage documentation for compliance"

**Process Improvement:**
- "Reduced pipeline runtime from 4h to 30min through partitioning"
- "Automated deployments saving 10 hours/week"
- "Standardized data quality framework across team"

**Documentation:**
- "Maintained comprehensive runbooks for 15+ pipelines"
- "Created onboarding docs reducing ramp-up time by 50%"
- "Documented tribal knowledge in Confluence"

**Project Management:**
- "Led migration of 50+ tables in 3-month timeline"
- "Managed stakeholder expectations across 10+ teams"
- "Delivered 95% of sprint commitments"

---

**STATUS:** Complete Data Management & Process Improvement Guide!  
**Total Package:** 3 comprehensive guides ready for Lloyds interview!
