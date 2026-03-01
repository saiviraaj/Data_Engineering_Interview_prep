# 7-DAY INTENSIVE PREPARATION PLAN
# LLOYDS TECHNOLOGY CENTRE - DATA ENGINEER ROLE
# YOUR PATH TO SUCCESS

"""
MISSION: Transform you from good to EXCEPTIONAL in 7 days
TARGET: Ace Lloyds Technology Centre Data Engineer Interview
APPROACH: Focused, practical, interview-oriented preparation
"""

## OVERVIEW

You have **7 DAYS** to prepare. This is intensive but absolutely achievable.
Your profile is STRONG (10 YOE, GCP, Banking), so we're polishing existing skills
and filling specific gaps.

**Success Probability**: Starting at 60% → Target 90% by Day 7

---

# DAY-BY-DAY BREAKDOWN

## 📅 DAY 1 (Today) - FOUNDATION & ASSESSMENT
**Goal**: Understand gaps, set baseline, quick wins
**Time**: 6-8 hours

### Morning (3 hours): PySpark Fundamentals Revival
**WHY**: Your weak area from Round 1

✅ **Tasks**:
1. Review `/home/claude/pyspark_masterclass.py` - Sections 1-5
2. Run ALL basic transformation examples
3. Practice these 10 must-know patterns:
   - select(), filter(), withColumn()
   - groupBy() + agg()
   - join() - all types
   - Window functions (row_number, rank, dense_rank)
   - lag(), lead()
   - Cumulative sum
   - Pivot
   - Explode
   - String functions
   - Date functions

**Practice Questions** (Do 5):
- Find 2nd highest salary by department
- Running total by employee
- Employees above department average
- Remove duplicates keeping latest
- Calculate YoY growth

### Afternoon (3 hours): GCP BigQuery Deep Dive
**WHY**: This is your STRENGTH - show mastery

✅ **Study Topics**:
1. **Architecture**:
   - Dremel (query engine)
   - Colossus (storage)
   - Jupiter (network)
   - Borg (orchestration)

2. **Partitioning & Clustering** (CRITICAL):
   ```sql
   -- Partitioning
   CREATE TABLE dataset.table
   PARTITION BY DATE(timestamp_column)
   CLUSTER BY user_id, category
   
   -- Benefits: Reduces cost + improves performance
   -- Interview Q: "How would you optimize a 10TB table?"
   Answer: "Partition by date, cluster by frequently filtered columns"
   ```

3. **Cost Optimization**:
   - Use partitions/clusters
   - SELECT specific columns (not SELECT *)
   - Materialize views for repeated queries
   - Use query caching
   - Approx aggregation functions (APPROX_COUNT_DISTINCT)

4. **Key Functions**:
   - ARRAY_AGG(), STRUCT()
   - LAG(), LEAD() (window functions)
   - WITH clauses (CTEs)
   - UNNEST() for arrays

**Practice Questions** (Do 3):
Q1: "How do you migrate 10TB Oracle table to BigQuery?"
Answer:
1. Export to GCS as Parquet/Avro (compressed, columnar)
2. Use bq load with schema auto-detect
3. Partition by date column
4. Cluster by frequently queried columns
5. Validate row counts, sample data checks

Q2: "BigQuery query costs $500/day. How to optimize?"
Answer:
1. Audit queries - find expensive ones
2. Add partitioning/clustering
3. Use materialized views
4. Limit SELECT * queries
5. Set query cost limits
6. Use BI Engine for dashboard queries

Q3: "Explain partitioning vs clustering"
Answer:
- **Partitioning**: Physical data division (by date/time/integer)
  - Prunes partitions at query time
  - Reduces data scanned → lower cost
  
- **Clustering**: Data organization within partitions
  - Orders data by columns
  - Improves query performance
  - Free (no storage overhead)

### Evening (2 hours): Apache Airflow Essentials
**WHY**: Lloyds uses Cloud Composer (managed Airflow)

✅ **Core Concepts**:

1. **DAG (Directed Acyclic Graph)**:
   ```python
   from airflow import DAG
   from airflow.operators.python import PythonOperator
   from datetime import datetime, timedelta
   
   default_args = {
       'owner': 'viraaj',
       'depends_on_past': False,
       'start_date': datetime(2025, 1, 1),
       'retries': 3,
       'retry_delay': timedelta(minutes=5)
   }
   
   dag = DAG(
       'data_pipeline',
       default_args=default_args,
       schedule_interval='@daily',
       catchup=False
   )
   ```

2. **Task Dependencies**:
   ```python
   task1 >> task2 >> [task3, task4] >> task5
   # task3 and task4 run in parallel after task2
   ```

3. **Operators** (Know these):
   - PythonOperator
   - BashOperator  
   - BigQueryOperator
   - GCSToGCSOperator
   - BranchPythonOperator

4. **XComs** (Cross-communication):
   ```python
   # Task 1 - push data
   def extract_data(**context):
       data = fetch_from_api()
       context['task_instance'].xcom_push(key='api_data', value=data)
   
   # Task 2 - pull data
   def process_data(**context):
       data = context['task_instance'].xcom_pull(
           task_ids='extract_task', 
           key='api_data'
       )
   ```

**Practice Questions**:
Q: "How would you handle DAG failure?"
A: Set retries, use on_failure_callback, email alerts, monitoring

Q: "How to pass data between tasks?"
A: XComs for small data (<48KB), GCS for large data

Q: "DAG not running on schedule?"
A: Check start_date, schedule_interval, catchup=False, scheduler status

**End of Day 1**:
✅ Completed PySpark basics
✅ Understood BigQuery deeply
✅ Airflow fundamentals clear
✅ Ran code examples
✅ Practiced 8+ interview questions

---

## 📅 DAY 2 - ADVANCED TRANSFORMATIONS & SQL MASTERY
**Goal**: Master window functions, complex SQL, scenario-based questions
**Time**: 8 hours

### Morning (4 hours): Window Functions Intensive

**WHY THIS MATTERS**: 60% of data engineer interviews test window functions

✅ **Practice Patterns**:

1. **ROW_NUMBER() - Find Nth record per group**:
   ```python
   from pyspark.sql.window import Window
   from pyspark.sql.functions import row_number
   
   # Find 2nd highest salary per department
   window = Window.partitionBy("department").orderBy(col("salary").desc())
   
   df.withColumn("rank", row_number().over(window)) \
     .filter(col("rank") == 2)
   ```

2. **LAG/LEAD - Time series analysis**:
   ```python
   # Calculate month-over-month growth
   window = Window.partitionBy("product").orderBy("month")
   
   df.withColumn("prev_sales", lag("sales", 1).over(window)) \
     .withColumn("mom_growth", 
       (col("sales") - col("prev_sales")) / col("prev_sales") * 100)
   ```

3. **Cumulative SUM - Running totals**:
   ```python
   window = Window.partitionBy("customer") \
                  .orderBy("order_date") \
                  .rowsBetween(Window.unboundedPreceding, Window.currentRow)
   
   df.withColumn("running_total", sum("amount").over(window))
   ```

4. **NTILE - Quartiles/Percentiles**:
   ```python
   window = Window.orderBy("salary")
   df.withColumn("salary_quartile", ntile(4).over(window))
   ```

**Practice Problems** (MUST DO - 10 questions):

1. Find employees earning more than department average
2. Calculate 7-day moving average of sales
3. Find gaps in transaction sequence
4. First and last order per customer
5. Rank products by revenue per category (dense_rank)
6. Calculate percentage of total by group
7. Find consecutive login days
8. Compare current vs previous month sales (lag)
9. Top 3 products per store per month
10. Median salary by department (percentile_approx)

### Afternoon (4 hours): Complex SQL Scenarios

✅ **BigQuery SQL Patterns**:

1. **WITH Clauses (CTEs)**:
   ```sql
   WITH monthly_sales AS (
     SELECT 
       DATE_TRUNC(order_date, MONTH) as month,
       SUM(amount) as total_sales
     FROM orders
     GROUP BY month
   ),
   sales_growth AS (
     SELECT 
       month,
       total_sales,
       LAG(total_sales) OVER (ORDER BY month) as prev_month_sales,
       (total_sales - LAG(total_sales) OVER (ORDER BY month)) 
         / LAG(total_sales) OVER (ORDER BY month) * 100 as growth_pct
     FROM monthly_sales
   )
   SELECT * FROM sales_growth WHERE growth_pct > 10
   ```

2. **Array/Struct Operations**:
   ```sql
   -- ARRAY_AGG
   SELECT 
     department,
     ARRAY_AGG(employee_name) as employees
   FROM employees
   GROUP BY department
   
   -- UNNEST
   SELECT user_id, skill
   FROM users,
   UNNEST(skills_array) as skill
   ```

3. **Window Frames**:
   ```sql
   -- Sliding 3-month window
   SELECT 
     month,
     sales,
     AVG(sales) OVER (
       ORDER BY month 
       ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
     ) as moving_avg_3m
   FROM monthly_sales
   ```

**SQL Interview Questions** (Practice 8):

1. Find customers who made purchases in all 12 months
2. Self-join to find employee-manager hierarchy
3. Calculate customer lifetime value
4. Find duplicate email addresses
5. Products never purchased
6. Running balance for each account
7. Sessions with gaps > 30 minutes
8. Customers with decreasing purchase frequency

**End of Day 2**:
✅ Window functions mastered
✅ Complex SQL scenarios solved
✅ 18+ practice problems completed
✅ Confidence level: +20%

---

## 📅 DAY 3 - GCP SERVICES DEEP DIVE
**Goal**: Become expert in GCP data services
**Time**: 8 hours

### Morning (4 hours): Cloud Composer (Managed Airflow)

✅ **Key Topics**:

1. **Architecture**:
   - Runs on Google Kubernetes Engine (GKE)
   - Integrated with Cloud Logging/Monitoring
   - Managed infrastructure

2. **Common Operators**:
   ```python
   # BigQuery Operator
   from airflow.providers.google.cloud.operators.bigquery import \
       BigQueryInsertJobOperator
   
   bq_task = BigQueryInsertJobOperator(
       task_id='run_query',
       configuration={
           "query": {
               "query": "SELECT * FROM dataset.table",
               "useLegacySql": False
           }
       }
   )
   
   # GCS Operator
   from airflow.providers.google.cloud.operators.gcs import \
       GCSToGCSOperator
   
   copy_task = GCSToGCSOperator(
       task_id='copy_files',
       source_bucket='source-bucket',
       source_object='data/*.csv',
       destination_bucket='dest-bucket'
   )
   ```

3. **Best Practices**:
   - Use Variables for configuration
   - Secrets in Secret Manager
   - Idempotent tasks
   - Set SLAs
   - Enable email alerts

**Practice**:
- Design DAG for: Extract from API → Load to GCS → Transform in BigQuery → Send email
- Handle failures and retries
- Implement data quality checks

### Afternoon (4 hours): Other GCP Services

✅ **Dataflow (Apache Beam)**:
```python
import apache_beam as beam

# Batch pipeline
with beam.Pipeline() as pipeline:
    (pipeline
     | 'Read' >> beam.io.ReadFromText('gs://bucket/input.csv')
     | 'Parse' >> beam.Map(lambda x: x.split(','))
     | 'Filter' >> beam.Filter(lambda x: int(x[2]) > 1000)
     | 'Write' >> beam.io.WriteToText('gs://bucket/output'))

# Streaming from Pub/Sub
(pipeline
 | 'Read from Pub/Sub' >> beam.io.ReadFromPubSub(topic='projects/my-project/topics/my-topic')
 | 'Process' >> beam.Map(process_message)
 | 'Write to BigQuery' >> beam.io.WriteToBigQuery(table_spec))
```

✅ **Cloud Storage**:
- Storage classes: Standard, Nearline, Coldline, Archive
- Lifecycle policies
- Versioning
- Signed URLs

✅ **Pub/Sub** (Messaging):
- Publisher/Subscriber model
- Topics and subscriptions
- Message ordering
- Dead letter topics

✅ **Dataproc** (Managed Spark/Hadoop):
- Ephemeral clusters
- Autoscaling
- Job submission
- Integration with GCS

**Interview Scenarios**:

Q1: "Real-time fraud detection pipeline?"
A: Pub/Sub (ingest) → Dataflow (process) → BigQuery (store) → Data Studio (visualize)

Q2: "Batch ETL for 100GB daily data?"
A: Cloud Scheduler → Cloud Composer → Dataflow/Dataproc → BigQuery

Q3: "When to use Dataflow vs Dataproc?"
A: 
- Dataflow: Streaming, serverless, auto-scaling, Java/Python
- Dataproc: Existing Spark/Hadoop code, custom libraries, ephemeral clusters

**End of Day 3**:
✅ Cloud Composer mastery
✅ GCP services architecture clear
✅ Scenario-based solutions practiced
✅ Can design end-to-end pipelines

---

## 📅 DAY 4 - BANKING DOMAIN & SYSTEM DESIGN
**Goal**: Gain banking domain knowledge, design thinking
**Time**: 8 hours

### Morning (4 hours): Banking Domain Crash Course

✅ **Core Banking Concepts**:

1. **Customer Channels**:
   - **Branch Banking**: Physical locations
   - **Digital Banking**: Web portals
   - **Mobile Banking**: iOS/Android apps
   - **ATM Network**: Cash withdrawal/deposit
   - **Call Center**: Phone support
   
2. **Key Banking Functions**:
   - **Deposits**: Savings, Current, Fixed Deposits
   - **Lending**: Personal loans, Mortgages, Credit cards
   - **Payments**: Transfers, Bill payments, SWIFT
   - **Wealth Management**: Investments, Mutual funds
   - **Risk Management**: Credit risk, Fraud detection

3. **Digital Banking Terms** (Know these):
   - **KYC**: Know Your Customer (identity verification)
   - **AML**: Anti-Money Laundering
   - **PSD2**: Payment Services Directive (EU regulation)
   - **Open Banking**: API-based account access
   - **SWIFT**: International payments network
   - **ACH**: Automated Clearing House (US payments)
   - **SEPA**: Single Euro Payments Area
   - **FCA**: Financial Conduct Authority (UK regulator)

4. **Customer Journey** (Lloyds focus):
   - Account opening (digital onboarding)
   - Daily transactions (mobile app)
   - Loan application (digital forms)
   - Investment decisions (robo-advisory)
   - Customer support (chatbots + human)

5. **Data in Banking**:
   - **Transactional Data**: Payments, transfers
   - **Customer Data**: Demographics, preferences
   - **Product Data**: Accounts, loans, cards
   - **Risk Data**: Credit scores, fraud scores
   - **Behavioral Data**: App usage, click streams

**Lloyds-Specific**:
- 27 million customers
- Focus: Digital transformation
- AI initiatives: Athena (GenAI)
- "Help Britain Prosper" mission
- Predominantly UK retail banking

**Interview Talking Points**:
"At Wells Fargo, I built data pipelines supporting **retail banking operations** including customer transaction processing, fraud detection data, and regulatory reporting. I understand the criticality of **data accuracy, security, and compliance** in banking. At Lloyds, I'm excited to contribute to your **digital transformation** journey, particularly in building cloud-native data platforms that enable **real-time analytics** for better customer experiences."

### Afternoon (4 hours): System Design Practice

✅ **Pattern**: Interviewer asks "Design a system for..."

**Framework to Answer**:
1. **Clarify Requirements** (5 min)
   - Functional requirements
   - Non-functional (scale, latency, availability)
   - Constraints

2. **High-Level Design** (10 min)
   - Components
   - Data flow
   - Technology choices

3. **Deep Dive** (10 min)
   - Database schema
   - APIs
   - Error handling
   - Monitoring

4. **Trade-offs** (5 min)
   - Why these choices?
   - Alternatives considered

**Practice Design Questions** (Do 3):

**Q1: Design a real-time fraud detection system**

Answer:
```
Requirements:
- Detect fraudulent transactions in <100ms
- Process 10,000 transactions/sec
- Low false positives

Architecture:
1. Data Ingestion:
   - Pub/Sub topic for transaction events
   - Schema: {transaction_id, user_id, amount, merchant, timestamp, location}

2. Processing:
   - Dataflow (streaming)
   - Rules engine: Check amount, frequency, location anomalies
   - ML model (deployed on Vertex AI): Score 0-1 fraud probability

3. Storage:
   - BigTable: Real-time user profile (last 10 transactions)
   - BigQuery: Historical fraud data for model training

4. Alerting:
   - If score > 0.8: Block transaction + alert
   - If 0.5-0.8: Send OTP for verification

5. Monitoring:
   - Cloud Monitoring: Latency, throughput
   - False positive rate tracking

Trade-offs:
- BigTable (low latency) vs BigQuery (analytical)
- Real-time blocking vs post-transaction review
```

**Q2: Design ETL for migrating 10TB Oracle database to BigQuery**

Answer:
```
Requirements:
- Minimal downtime
- Data validation
- Incremental updates

Architecture:
1. Initial Load:
   - Export Oracle tables to Parquet (compressed, columnar)
   - Upload to GCS (multi-part upload for large files)
   - bq load into partitioned BigQuery tables
   - Validation: Row counts, checksums, sample queries

2. Incremental Updates (CDC):
   - Oracle GoldenGate / Debezium (change data capture)
   - Stream to Pub/Sub
   - Dataflow processes and merges to BigQuery
   - Use MERGE statement for upserts

3. Data Transformation:
   - Spark on Dataproc for complex transformations
   - dbt for SQL-based transformations in BigQuery

4. Orchestration:
   - Cloud Composer DAG:
     - Check Oracle source
     - Extract → GCS
     - Load → BigQuery
     - Validate
     - Send success/failure notification

5. Monitoring:
   - Data quality checks (null rates, value distributions)
   - Latency tracking (extract to load time)
   - Error alerting
```

**Q3: Design customer 360 view data warehouse**

Answer:
```
Requirements:
- Unified customer view across products
- Support for dashboards and ML
- PII security

Architecture:
1. Source Systems:
   - Core banking (accounts, transactions)
   - CRM (customer interactions)
   - Mobile app (usage data)
   - Marketing (campaigns)

2. Data Lake (GCS):
   - Raw zone: Original data
   - Cleaned zone: Validated, deduplicated
   - Curated zone: Business-ready datasets

3. Data Warehouse (BigQuery):
   - Dimensional Model:
     - Fact_Transactions
     - Dim_Customer (SCD Type 2 for history)
     - Dim_Product
     - Dim_Date
   - Partitioned by date, clustered by customer_id

4. Security:
   - Column-level encryption (PII)
   - Row-level security (RLS)
   - Data masking for non-prod environments
   - Audit logging (Cloud Audit Logs)

5. Consumption:
   - BI tools: Looker, Data Studio
   - ML: Vertex AI for churn prediction, next-best-offer

6. Data Governance:
   - Dataplex: Metadata management, data lineage
   - DLP API: PII detection and redaction
```

**End of Day 4**:
✅ Banking domain fundamentals learned
✅ Can speak intelligently about digital banking
✅ System design framework practiced
✅ 3 complete design solutions prepared

---

## 📅 DAY 5 - PERFORMANCE TUNING & PRODUCTION ISSUES
**Goal**: Show senior-level expertise in optimization
**Time**: 8 hours

### Morning (4 hours): PySpark Performance Optimization

✅ **Critical Concepts**:

1. **Partitioning**:
   ```python
   # Bad: Default partitions (200)
   df.groupBy("category").count()
   
   # Good: Right-sized partitions
   df.repartition(10, "category") \
     .groupBy("category") \
     .count()
   
   # When to use:
   # - repartition(): Increases/decreases, full shuffle
   # - coalesce(): Decreases only, minimal shuffle
   ```

2. **Caching**:
   ```python
   # Cache when DF used multiple times
   df_cached = df.filter(col("amount") > 1000).cache()
   
   df_cached.groupBy("category").count()  # Triggers cache
   df_cached.groupBy("user").sum("amount")  # Uses cache
   
   # Unpersist when done
   df_cached.unpersist()
   ```

3. **Broadcast Joins**:
   ```python
   from pyspark.sql.functions import broadcast
   
   # Small dimension table (<10MB)
   large_df.join(
       broadcast(small_df),
       "product_id"
   )
   ```

4. **Avoiding Shuffles**:
   ```python
   # Bad: Multiple groupBy operations
   df.groupBy("A").count() \
     .groupBy("B").sum("count")
   
   # Good: Single aggregation
   df.groupBy("A", "B").count()
   ```

5. **Predicate Pushdown**:
   ```python
   # Filter early
   df = spark.read.parquet("gs://bucket/data") \
            .filter(col("date") >= "2025-01-01")  # Before other ops
   ```

**Interview Questions**:

Q: "Spark job takes 4 hours. How to optimize?"
A:
1. Check **data skew**: Use `df.groupBy("key").count()` to find skewed keys
2. **Repartition** on skewed column: `df.repartition(100, "key")`
3. **Broadcast** small tables
4. **Cache** reused DataFrames
5. Use **columnar formats**: Parquet instead of CSV
6. **Filter early** to reduce data volume
7. Increase **executor memory** if OOM errors
8. Check for **wide transformations** (reduce shuffles)

Q: "Data skew in join causing stragglers?"
A:
```python
# Salting technique
from pyspark.sql.functions import rand, concat

# Add random salt to skewed key
large_df_salted = large_df.withColumn(
    "salted_key",
    concat(col("key"), lit("_"), (rand() * 10).cast("int"))
)

# Explode small table with all salt values
small_df_exploded = small_df.withColumn(
    "salt",
    explode(array([lit(i) for i in range(10)]))
).withColumn(
    "salted_key",
    concat(col("key"), lit("_"), col("salt"))
)

# Join on salted key
result = large_df_salted.join(small_df_exploded, "salted_key")
```

### Afternoon (4 hours): BigQuery Performance Tuning

✅ **Optimization Techniques**:

1. **Query Optimization**:
   ```sql
   -- Bad: SELECT *
   SELECT * FROM large_table WHERE date > '2025-01-01'
   
   -- Good: Select only needed columns
   SELECT user_id, amount, date 
   FROM large_table 
   WHERE date > '2025-01-01'
   
   -- Cost: 10TB scanned → 100GB scanned (100x reduction!)
   ```

2. **Partitioning Strategies**:
   ```sql
   -- Time-based partitioning (most common)
   CREATE TABLE dataset.transactions
   PARTITION BY DATE(timestamp)
   CLUSTER BY user_id, category
   AS SELECT * FROM source
   
   -- Integer range partitioning
   CREATE TABLE dataset.users
   PARTITION BY RANGE_BUCKET(user_id, GENERATE_ARRAY(0, 1000000, 10000))
   ```

3. **Materialized Views**:
   ```sql
   CREATE MATERIALIZED VIEW dataset.daily_sales AS
   SELECT 
     DATE(order_date) as date,
     product_id,
     SUM(amount) as total_sales
   FROM orders
   GROUP BY date, product_id
   
   -- Queries on this view use precomputed results
   -- Auto-refresh when base table changes
   ```

4. **Approximate Functions** (cost savings):
   ```sql
   -- Bad: Exact count (scans all data)
   SELECT COUNT(DISTINCT user_id) FROM large_table
   
   -- Good: Approximate (faster, cheaper)
   SELECT APPROX_COUNT_DISTINCT(user_id) FROM large_table
   ```

5. **BI Engine** (for dashboards):
   - In-memory analysis engine
   - Sub-second query response
   - Reserved capacity (1-100GB)

**Production Troubleshooting**:

Q: "Pipeline failing intermittently?"
A:
1. Check **Cloud Logging**: Look for error patterns
2. **Data quality**: Null values, schema changes
3. **Resource limits**: Quotas, concurrent queries
4. **Dependencies**: Upstream data delays
5. Implement **retries** with exponential backoff
6. Add **monitoring alerts**: Stackdriver metrics

Q: "BigQuery costs spiking?"
A:
1. **Audit**: Run query cost analysis
2. Find **expensive queries**: Check INFORMATION_SCHEMA.JOBS
3. Implement **cost controls**:
   ```sql
   -- Set max bytes billed
   SELECT * FROM large_table
   -- Options: max_bytes_billed = 10737418240 (10GB)
   ```
4. Use **slots** for predictable pricing
5. Educate team on **best practices**

**End of Day 5**:
✅ Performance tuning expert
✅ Can diagnose and solve production issues
✅ Cost optimization strategies ready
✅ Senior engineer level knowledge

---

## 📅 DAY 6 - BEHAVIORAL PREP & MOCK INTERVIEW
**Goal**: Perfect your interview presence and storytelling
**Time**: 8 hours

### Morning (3 hours): STAR Method Stories

✅ **Framework**: Situation, Task, Action, Result

**Prepare 6 Stories** (from your resume):

**Story 1: CDM Next - Large Scale Migration**
- **Situation**: Wells Fargo needed to migrate 15+ PB data from on-prem to GCP
- **Task**: Design and build cloud-native migration framework
- **Action**: 
  - Architected configuration-driven ELT pipelines
  - Built Airflow DAGs for orchestration
  - Implemented data quality checks and monitoring
  - Optimized Spark jobs for performance
- **Result**:
  - Migrated 15+ PB successfully
  - Adopted by 60+ teams
  - Reduced migration time by 60%
  - Accelerated data center exit

**Story 2: Performance Optimization**
- **Situation**: Teradata-to-BigQuery pipeline taking 8 hours
- **Task**: Reduce processing time to meet SLA
- **Action**:
  - Profiled job to identify bottlenecks
  - Implemented partitioning by date
  - Added clustering on frequently queried columns
  - Used broadcast joins for dimension tables
  - Optimized Spark configurations
- **Result**:
  - Reduced time from 8 hours to 3 hours (62% improvement)
  - Saved $10K/month in compute costs
  - Met SLA requirements

**Story 3: Handling Production Incident**
- **Situation**: Critical pipeline failing at 3 AM, affecting morning reports
- **Task**: Diagnose and fix urgently
- **Action**:
  - Checked Cloud Logging for error patterns
  - Found schema mismatch in source data
  - Implemented schema validation check
  - Added alerting for similar issues
  - Created runbook for on-call team
- **Result**:
  - Restored pipeline in 45 minutes
  - Prevented future occurrences
  - Improved monitoring coverage

**Story 4: Team Collaboration**
- **Situation**: Cross-functional project with 5 teams, different priorities
- **Task**: Align teams and deliver unified solution
- **Action**:
  - Organized weekly sync meetings
  - Created shared documentation
  - Defined clear interfaces and SLAs
  - Mediated priority conflicts
- **Result**:
  - Delivered on time
  - All teams satisfied
  - Became template for future projects

**Story 5: Learning New Technology**
- **Situation**: GCP was new tech stack at Wells Fargo
- **Task**: Become expert and train team
- **Action**:
  - Got GCP Professional Data Engineer certification
  - Built POCs for key services
  - Created internal training materials
  - Mentored 10+ engineers
- **Result**:
  - Team productive within 2 months
  - Successful production deployments
  - Became go-to GCP expert

**Story 6: Innovation/Initiative**
- **Situation**: Manual data quality checks time-consuming
- **Task**: Automate and improve coverage
- **Action**:
  - Built reusable data quality framework
  - Integrated with CI/CD pipeline
  - Created quality dashboards
- **Result**:
  - Reduced QA time by 80%
  - Caught issues earlier
  - Adopted across organization

### Afternoon (3 hours): Common Behavioral Questions

✅ **Practice Answers**:

**Q: Why Lloyds Technology Centre?**
A: "I'm excited about Lloyds for three reasons:
1. **Digital transformation scale**: 27 million customers, £4B investment - working on UK's largest digital bank transformation is a once-in-career opportunity
2. **Technical alignment**: Your GCP + Airflow + BigQuery stack matches my production expertise perfectly. I can contribute from day one.
3. **Mission**: 'Help Britain Prosper' resonates with me. Banking tech that improves millions of lives is meaningful work.
Additionally, Hyderabad center is new with growth potential, and I'm impressed by the leadership team's credentials."

**Q: Why leaving Wells Fargo?**
A: "Wells Fargo has been excellent for growth. I've built enterprise-scale platforms and learned immensely. However, Lloyds offers:
- Opportunity to be part of something new (Hyderabad center just opened)
- Work with cutting-edge AI/ML initiatives like Athena
- More direct impact in a growing team vs large established one
- UK market exposure and different regulatory environment
I'm not running from Wells Fargo, I'm running toward Lloyds."

**Q: Biggest technical challenge?**
A: [Use Story 2 - Performance Optimization]

**Q: Conflict with teammate?**
A: "We had a disagreement on architecture approach:
- **Situation**: Colleague wanted to use Dataproc, I advocated for Dataflow
- **Task**: Choose right tool without damaging relationship
- **Action**: 
  - Organized technical discussion with both approaches
  - Built small POCs for both
  - Evaluated on criteria: cost, complexity, maintenance
  - Let data decide
- **Result**: Dataflow won on merits, colleague agreed. We implemented together and became stronger collaborators."

**Q: Handling tight deadline?**
A: [Use Story 3 - Production Incident]

**Q: Mentoring junior engineers?**
A: [Use Story 5 - Training team on GCP]

**Q: Dealing with ambiguous requirements?**
A: "On CDM Next project, requirements were initially vague:
- **Action**: Asked clarifying questions, created prototypes, iterative feedback
- **Result**: Converted ambiguity to clear requirements through collaboration"

**Q: Your weakness?**
A: "I sometimes get too focused on technical perfection and can over-engineer solutions. I've learned to balance by:
- Setting timebox for design phase
- Getting early feedback on MVP
- Remembering 'done is better than perfect'
Recent example: Instead of building complex framework, shipped simpler solution that met 80% of needs, then iterated."

**Q: Where do you see yourself in 5 years?**
A: "Leading data engineering initiatives at Lloyds:
- Year 1-2: Master your tech stack, deliver high-impact projects
- Year 3-4: Technical lead role, mentoring team, driving architecture decisions
- Year 5: Principal Engineer / Architect, shaping org-wide data strategy
I want deep technical expertise + people leadership."

### Evening (2 hours): Questions for Interviewer

✅ **Prepare 10 Intelligent Questions**:

**Technical**:
1. "What's the biggest technical challenge your data team faces currently?"
2. "How is data governance implemented across multiple countries?"
3. "What's your ML/AI strategy? I saw Athena mentioned - how is GenAI being used?"
4. "What does the data platform roadmap look like for next 12 months?"

**Team/Culture**:
5. "How does Hyderabad center collaborate with UK teams? Time zones?"
6. "What does success look like for this role in first 6 months?"
7. "How is knowledge shared between teams? Documentation practices?"
8. "What's the team's approach to learning and experimentation?"

**Growth**:
9. "What learning and certification opportunities are available?"
10. "How do engineers progress from mid to senior to lead?"

**End of Day 6**:
✅ 6 STAR stories prepared
✅ All behavioral questions answered
✅ Questions for interviewer ready
✅ Confident interview presence

---

## 📅 DAY 7 - FINAL POLISH & MOCK INTERVIEWS
**Goal**: Peak performance readiness
**Time**: 8 hours

### Morning (2 hours): Quick Review

✅ **Rapid Fire Revision**:
- Review PySpark cheat sheet (30 min)
- BigQuery key concepts (30 min)
- Airflow DAG structure (20 min)
- Banking domain terms (20 min)
- System design patterns (20 min)

### Mid-Morning (3 hours): MOCK INTERVIEW #1 (Technical)

[We'll do this together when you're ready]

**Round 1: PySpark/SQL (45 min)**
- Live coding questions
- Window functions
- Optimization scenarios

**Round 2: GCP/Airflow (45 min)**
- Architecture questions
- DAG design
- Troubleshooting

**Round 3: System Design (45 min)**
- Design fraud detection system
- Trade-offs discussion

**Feedback & Improvement (45 min)**

### Afternoon (3 hours): MOCK INTERVIEW #2 (Full Loop)

[We'll simulate complete interview]

**Technical + Behavioral + Questions**
- Resume deep-dive
- Project discussions
- STAR stories
- Your questions for interviewer

**Final Feedback & Polish**

**End of Day 7**:
✅ Two full mock interviews completed
✅ Gaps identified and fixed
✅ Ready for real interview
✅ Confidence: 90%+

---

# INTERVIEW DAY CHECKLIST

## Day Before:
- [ ] Review STAR stories once more
- [ ] Practice 5 PySpark questions
- [ ] Review GCP architecture diagrams
- [ ] Get good sleep (7-8 hours)
- [ ] Prepare questions for interviewer

## Interview Day Morning:
- [ ] Light breakfast
- [ ] 15-min meditation/deep breathing
- [ ] Review quick notes (not deep study)
- [ ] Test video/audio setup
- [ ] Dress professionally (even for remote)
- [ ] Keep water nearby

## During Interview:
- [ ] Smile and maintain eye contact
- [ ] Think before speaking (pause is OK)
- [ ] Use examples from YOUR experience
- [ ] Ask clarifying questions
- [ ] Show enthusiasm for role
- [ ] Take notes during discussion

## After Interview:
- [ ] Send thank-you email within 24 hours
- [ ] Note questions you struggled with
- [ ] Prepare for potential next rounds

---

# EMERGENCY INTERVIEW SCENARIOS

## "I don't know the answer"
**Good Response**: "I haven't worked directly with that technology, but based on my experience with [similar tech], I would approach it like this... Could you tell me more about your specific use case?"

## Blank Mind Moment
**Strategy**: "That's an interesting question. Let me think through this systematically..." [Buy 10 seconds, organize thoughts]

## Technical Question Too Hard
**Response**: "I'm not sure about the complete solution, but here's how I'd start... [give partial answer]. In a real scenario, I'd [research/consult docs/ask team]."

---

# SUCCESS MANTRAS

1. **You're qualified**: 10 YOE, GCP expert, Banking domain - you DESERVE this role
2. **They need you**: Lloyds is hiring aggressively, not looking for perfect
3. **Be authentic**: Don't pretend to know what you don't
4. **Show learning**: "I'm excited to learn X" is positive
5. **Confidence ≠ Arrogance**: Be humble but own your achievements
6. **Energy matters**: Enthusiasm > perfect answers

---

# YOUR COMPETITIVE ADVANTAGES

1. ✅ **10 years experience** > their typical requirement
2. ✅ **Production GCP** (rare in market)
3. ✅ **Airflow expertise** (their tech stack)
4. ✅ **Banking domain** (Wells Fargo BFSI)
5. ✅ **Large-scale migration** (15+ PB impressive)
6. ✅ **Location** (Hyderabad, no relocation needed)

---

# FINAL WORDS

You have everything needed to succeed. The next 7 days will transform you from good to exceptional.

**Believe in yourself. Work hard. Stay focused.**

**See you in Lloyds Technology Centre!** 🚀

---

# DAILY PROGRESS TRACKER

Mark completion:

**DAY 1**: [ ] PySpark [ ] BigQuery [ ] Airflow Basics
**DAY 2**: [ ] Window Functions [ ] Complex SQL [ ] 18 Problems
**DAY 3**: [ ] Cloud Composer [ ] GCP Services [ ] Design Patterns
**DAY 4**: [ ] Banking Domain [ ] System Design [ ] 3 Solutions
**DAY 5**: [ ] Performance Tuning [ ] Troubleshooting [ ] Optimization
**DAY 6**: [ ] STAR Stories [ ] Behavioral Prep [ ] Questions Ready
**DAY 7**: [ ] Mock Interview 1 [ ] Mock Interview 2 [ ] Final Polish

---

GOOD LUCK! YOU'VE GOT THIS! 💪
