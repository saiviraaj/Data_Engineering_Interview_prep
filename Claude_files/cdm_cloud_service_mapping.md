# CDM vNext: Multi-Cloud Service Mapping

## Complete Service Equivalence Table

| **Component/Function** | **GCP (Your Experience)** | **AWS Equivalent** | **Databricks Equivalent** | **Key Terminology** |
|------------------------|---------------------------|-------------------|---------------------------|---------------------|
| **Storage Layer** | | | | |
| Object Storage | Google Cloud Storage (GCS) | Amazon S3 | Databricks File System (DBFS) / S3 | Data Lake, Object Store, Blob Storage |
| Data Warehouse | BigQuery | Amazon Redshift / Athena | Databricks SQL / Delta Lake | Cloud Data Warehouse, Serverless Analytics |
| | | | | |
| **Data Security & Governance** | | | | |
| Data Scanning/DLP | BigQuery DLP | Amazon Macie / AWS Glue DataBrew | Unity Catalog Data Classification | PII Detection, Sensitive Data Discovery |
| Metadata Management | Dataplex / Data Catalog | AWS Glue Data Catalog / Lake Formation | Unity Catalog | Data Discovery, Metadata Store |
| Schema Management | Aspect Types (Dataplex) | AWS Glue Schema Registry / Custom Tags | Unity Catalog Tags / Table Properties | Schema Evolution, Metadata Templates |
| Encryption at Rest | Cloud KMS | AWS KMS | Customer-managed keys in KMS | Envelope Encryption, CMEK |
| Encryption in Transit | TLS/SSL (Cloud Load Balancing) | TLS/SSL (ELB/ALB) | TLS/SSL (Databricks Runtime) | End-to-end Encryption |
| Secrets Management | Secret Manager | AWS Secrets Manager / Parameter Store | Databricks Secrets / AWS Secrets Manager | Credential Vault, Secret Rotation |
| Access Control | IAM (Service Accounts, Roles) | IAM (Roles, Policies) | Unity Catalog RBAC / IAM | RBAC, ABAC, Fine-grained Access Control |
| Data Masking | DLP Transformation | AWS Glue / Lambda | Delta Sharing with Dynamic Views | Column-level Security, Row-level Security |
| | | | | |
| **Orchestration & Workflow** | | | | |
| Workflow Orchestration | Cloud Composer (Airflow) | Amazon MWAA (Managed Airflow) / Step Functions | Databricks Workflows / Jobs | DAG Orchestration, Job Scheduling |
| CI/CD Pipeline | Harness | Harness / AWS CodePipeline / Jenkins | Databricks Repos + CI/CD tools | Infrastructure as Code, GitOps |
| Infrastructure as Code | Terraform | Terraform / CloudFormation | Terraform / Databricks Terraform Provider | IaC, Configuration Management |
| | | | | |
| **Data Processing** | | | | |
| Batch Processing | Dataproc (Spark) | Amazon EMR / AWS Glue | Databricks Clusters (Apache Spark) | Distributed Processing, ETL/ELT |
| Serverless Compute | Cloud Run Functions | AWS Lambda | Databricks Jobs (Serverless) | Function-as-a-Service, Event-driven |
| Stream Processing | Dataflow (Apache Beam) | Amazon Kinesis / AWS Glue Streaming | Databricks Structured Streaming | Real-time Processing, Micro-batching |
| Message Queue | Pub/Sub | Amazon SNS/SQS / Kinesis | Delta Live Tables (DLT) / External Queue | Event Bus, Message Broker |
| | | | | |
| **Data Transfer** | | | | |
| Bulk Transfer | Storage Transfer Service (STS) | AWS DataSync / S3 Transfer Acceleration | Databricks AutoLoader / COPY INTO | High-throughput Transfer, Incremental Load |
| Database Migration | Database Migration Service | AWS DMS (Database Migration Service) | Partner Connect / JDBC | CDC, Full/Incremental Load |
| Streaming Ingestion | Pub/Sub + Dataflow | Kinesis Data Streams + Firehose | Delta Live Tables / Structured Streaming | Real-time Ingestion, Event Streaming |
| API Ingestion | Cloud Functions + Pub/Sub | API Gateway + Lambda + EventBridge | Databricks Jobs + REST API | API-driven Ingestion |
| | | | | |
| **Monitoring & Observability** | | | | |
| Logging | Cloud Logging | CloudWatch Logs | Databricks System Tables / CloudWatch | Centralized Logging, Log Analytics |
| Monitoring | Cloud Monitoring | CloudWatch Metrics / X-Ray | Databricks System Tables / Ganglia | Metrics, APM, Distributed Tracing |
| Alerting | Cloud Monitoring Alerts | CloudWatch Alarms / SNS | Databricks Alerts / CloudWatch | Threshold-based Alerts, Notifications |
| Log Analysis | Log Analytics / BigQuery | CloudWatch Insights / Athena | Databricks SQL / System Tables | Query-based Analysis |
| Incident Management | Integration with ServiceNow | Integration with PagerDuty / ServiceNow | Integration with PagerDuty | Auto-incident Creation, ITSM |
| | | | | |
| **Data Quality & Validation** | | | | |
| Data Quality Framework | Custom Spark/BQ validation | AWS Glue DataBrew / Deequ | Delta Live Tables Expectations / Great Expectations | Data Profiling, Rule-based Validation |
| Data Lineage | Dataplex Lineage | AWS Glue Lineage / OpenLineage | Unity Catalog Lineage | End-to-end Traceability |
| | | | | |
| **Network & Connectivity** | | | | |
| Private Networking | VPC / Private Service Connect | VPC / PrivateLink | VPC Peering / PrivateLink | Secure Connectivity, Network Isolation |
| Hybrid Connectivity | Cloud Interconnect | AWS Direct Connect | AWS Direct Connect / VPN | On-prem to Cloud Bridge |

---

## Architecture Pattern Translation

### **Quarantine → Delivery Pattern**

#### **GCP Implementation (Your Current)**
```
On-Prem Sources → GCS (Quarantine) → DLP Scan → Encryption → 
→ GCS/BQ (Delivery/Application) → App Teams
```

#### **AWS Equivalent**
```
On-Prem Sources → S3 (Landing/Quarantine Bucket) → Macie Scan / Glue Job → 
→ KMS Encryption → S3 (Curated/Application Bucket) / Redshift → App Teams
```

**AWS Services Flow:**
1. **Ingestion**: AWS DMS, Kinesis, S3 Transfer
2. **Quarantine Zone**: S3 bucket with restricted access
3. **Scanning**: Amazon Macie (PII detection), AWS Glue DataBrew
4. **Processing**: AWS Glue ETL Jobs, EMR (Spark)
5. **Encryption**: AWS KMS with envelope encryption
6. **Delivery**: S3 (curated zone) or Redshift Spectrum
7. **Orchestration**: MWAA (Airflow) or Step Functions
8. **Governance**: Lake Formation, Glue Data Catalog

#### **Databricks Equivalent**
```
On-Prem Sources → Bronze Layer (Raw) → Unity Catalog Scan → 
→ Silver Layer (Validated/Encrypted) → Gold Layer (Application) → App Teams
```

**Databricks Services Flow:**
1. **Ingestion**: AutoLoader, COPY INTO, Delta Live Tables
2. **Bronze Layer**: Raw data landing (Delta Lake format)
3. **Scanning**: Unity Catalog data classification, custom Spark jobs
4. **Processing**: Databricks Jobs, Delta Live Tables
5. **Encryption**: Unity Catalog encryption, AWS KMS integration
6. **Silver Layer**: Validated, deduplicated data
7. **Gold Layer**: Business-ready aggregated data
8. **Orchestration**: Databricks Workflows
9. **Governance**: Unity Catalog (RBAC, lineage, auditing)

---

## Key Interview-Ready Explanations

### **Project Summary (AWS Version)**

*"I architected a cloud-native data migration framework on AWS that enables secure, governed data movement from on-premises to cloud. The framework implements a two-tier architecture with a quarantine zone (S3 landing buckets) and application zone (S3 curated buckets/Redshift).

Data flows through Amazon Macie for sensitive data scanning, detecting PII and restricted content based on custom classification templates. Suspicious Activity Report (SAR) data is isolated and encrypted using AWS KMS with policy-driven encryption. The framework is orchestrated through Amazon MWAA (Managed Airflow), processing 15+ PB of enterprise data with automated validation, retry logic, and comprehensive CloudWatch monitoring.

I implemented Lake Formation for fine-grained access control, Glue Data Catalog for metadata management, and integrated with Step Functions for complex workflow orchestration. The platform reduced data center exit timeline by 40% while maintaining SOC2 and regulatory compliance."*

### **Project Summary (Databricks Version)**

*"I designed a medallion architecture-based data migration platform on Databricks that supports secure data movement from legacy systems to cloud. The framework implements Bronze-Silver-Gold layers with Unity Catalog as the governance backbone.

Data ingestion uses AutoLoader for scalable file processing and Delta Live Tables for streaming pipelines. Unity Catalog handles data classification, detecting sensitive data through custom tags and applying column-level encryption for SAR (Suspicious Activity Report) data. Delta Lake provides ACID transactions and time travel capabilities for data validation and rollback.

The platform leverages Databricks Workflows for orchestration, processing 15+ PB with automated quality checks using Delta Live Tables Expectations. I implemented row-level and column-level security through Unity Catalog, centralized lineage tracking, and integrated with external monitoring tools. The framework supports both batch and streaming patterns with exactly-once processing guarantees."*

---

## Architecture Diagrams (Conceptual)

### **AWS Two-Tier Architecture**
```
┌─────────────────────────────────────────────────────────────┐
│                    QUARANTINE ZONE (Account A)               │
├─────────────────────────────────────────────────────────────┤
│  Data Sources → S3 Landing Bucket                            │
│      ↓                                                       │
│  Macie Scan (PII/Restricted/SAR Detection)                   │
│      ↓                                                       │
│  Glue ETL Job (Validation + Classification)                  │
│      ↓                                                       │
│  KMS Encryption (Policy-based for SAR)                       │
│      ↓                                                       │
│  Decision Logic:                                             │
│    • Restricted → Alert + Purge                              │
│    • SAR → Encrypt + Tag + Route to Isolated Bucket          │
│    • Clean → Route to Curated Zone                           │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              APPLICATION ZONE (Account B)                    │
├─────────────────────────────────────────────────────────────┤
│  S3 Curated Bucket / Redshift                                │
│      ↓                                                       │
│  Lake Formation (Fine-grained Access Control)                │
│      ↓                                                       │
│  App Teams Consumption (Athena, EMR, Redshift)               │
└─────────────────────────────────────────────────────────────┘

Orchestration: MWAA (Airflow DAGs)
Monitoring: CloudWatch + EventBridge + SNS
Governance: Glue Data Catalog + Lake Formation
```

### **Databricks Medallion Architecture**
```
┌─────────────────────────────────────────────────────────────┐
│                      BRONZE LAYER (Raw)                      │
├─────────────────────────────────────────────────────────────┤
│  AutoLoader → Delta Lake Tables                              │
│    • Schema Evolution Enabled                                │
│    • Checkpoint for Exactly-once Processing                  │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              SILVER LAYER (Validated/Classified)             │
├─────────────────────────────────────────────────────────────┤
│  Delta Live Tables Pipeline:                                 │
│    • Unity Catalog Data Classification                       │
│    • DLT Expectations (Data Quality Rules)                   │
│    • SAR Detection via Custom Spark UDFs                     │
│    • Column Masking for SAR columns                          │
│    • Separate SAR tables with encryption                     │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   GOLD LAYER (Application)                   │
├─────────────────────────────────────────────────────────────┤
│  Business-ready aggregated tables                            │
│    • Unity Catalog RBAC enforcement                          │
│    • Dynamic row/column filtering                            │
│    • App team consumption via Databricks SQL                 │
└─────────────────────────────────────────────────────────────┘

Orchestration: Databricks Workflows
Monitoring: System Tables + Databricks SQL Alerts
Governance: Unity Catalog (Tags, Lineage, Access Control)
```

---

## Interview Keywords & Phrases by Topic

### **Data Migration & Ingestion**
- **Batch Ingestion**: "Full and incremental loads", "Partition-based extraction", "Change Data Capture (CDC)"
- **Streaming Ingestion**: "Event-driven pipelines", "Micro-batching", "Exactly-once semantics"
- **Hybrid Patterns**: "Landing zone pattern", "Medallion architecture", "Multi-hop architecture"

### **Security & Governance**
- **Encryption**: "Envelope encryption with KMS", "Customer-managed encryption keys (CMEK)", "Encryption at rest and in transit"
- **Access Control**: "Role-based access control (RBAC)", "Attribute-based access control (ABAC)", "Fine-grained permissions"
- **Compliance**: "Data residency requirements", "Audit trails", "Immutable logging", "SOC2 compliance"
- **Data Classification**: "Sensitive data discovery", "PII detection", "Policy-driven masking", "Tag-based governance"

### **Data Quality & Validation**
- "Schema validation and evolution"
- "Data profiling and anomaly detection"
- "Reconciliation frameworks"
- "Idempotent pipelines"
- "Data quality dimensions: completeness, accuracy, consistency, timeliness"

### **Performance Optimization**
- "Partitioning strategies (time-based, hash-based)"
- "Predicate pushdown optimization"
- "Columnar storage formats (Parquet, ORC, Delta)"
- "Z-ordering and clustering"
- "Adaptive query execution"
- "Broadcast joins vs shuffle joins"
- "Caching and materialized views"

### **Orchestration & Workflow**
- "DAG-based orchestration"
- "Retry logic with exponential backoff"
- "Circuit breaker patterns"
- "Dynamic task generation"
- "SLA-driven scheduling"
- "Dependency management across pipelines"

### **Architecture Patterns**
- "Two-tier architecture (quarantine + application zones)"
- "Medallion architecture (Bronze-Silver-Gold)"
- "Lambda architecture (batch + streaming)"
- "Kappa architecture (streaming-first)"
- "Event-driven architecture"
- "Microservices-based data platform"

### **Monitoring & Observability**
- "End-to-end pipeline observability"
- "Data lineage tracking"
- "Distributed tracing"
- "Alert fatigue reduction"
- "SLI/SLO-based monitoring"
- "Automated incident management"

---

## Common Interview Questions & Your Responses

### Q1: "How would you implement this on AWS instead of GCP?"

**Response Template:**
*"The core architecture pattern remains the same—a two-tier security model with quarantine and application zones. In AWS, I would leverage S3 buckets for the landing zone with lifecycle policies for automated data retention. Amazon Macie would replace BigQuery DLP for sensitive data scanning, with custom classification jobs detecting PII, restricted data, and SAR content.

For orchestration, I'd use Amazon MWAA (Managed Airflow) to maintain the same DAG-based workflow logic we built in Cloud Composer. AWS Glue would handle ETL transformations with PySpark, and Lake Formation would provide fine-grained access control similar to Dataplex. The encryption layer would use AWS KMS with policy-driven key management, and CloudWatch would centralize logging with automated SNS alerts for incidents.

The key advantage in AWS is the tight integration between services like Glue Data Catalog, Lake Formation, and Athena for serverless querying, which reduces operational overhead compared to managing separate compute clusters."*

### Q2: "Why Databricks instead of just Spark on EMR or Dataproc?"

**Response Template:**
*"Databricks provides three key advantages over self-managed Spark: First, Unity Catalog offers enterprise-grade governance with centralized metadata, RBAC, data lineage, and automated classification—eliminating the need to build custom frameworks.

Second, Delta Lake brings ACID transactions, time travel, and schema evolution natively, which is critical for data validation and rollback capabilities in our migration workflows. Third, Delta Live Tables simplifies streaming pipeline development with declarative syntax and built-in data quality expectations, reducing development time by 50%.

From an operational standpoint, Databricks Workflows provides integrated orchestration without managing a separate Airflow cluster, and autoscaling clusters with spot instance optimization significantly reduce compute costs. For our SAR data use case, Unity Catalog's dynamic views enable row-level and column-level security without duplicating data, which was a major challenge with traditional Spark deployments."*

### Q3: "How do you ensure exactly-once processing in your pipelines?"

**Response Template:**
*"We implement exactly-once semantics through multiple mechanisms. For batch processing, we use idempotent operations with unique business keys and upsert logic (MERGE statements) to ensure records are not duplicated even on retries. Every ingestion job writes checkpoint markers to track processed offsets.

In streaming scenarios with Pub/Sub (or Kinesis in AWS), we leverage consumer group offsets and transaction markers. With Databricks, Delta Lake's ACID transactions guarantee atomic commits—either the entire micro-batch succeeds or none of it is committed.

We also maintain an audit table that tracks job execution metadata including source-to-target record counts, checksums, and processing timestamps. Before delivering data to the application zone, we run automated reconciliation checks comparing source and target counts with configurable tolerance thresholds. Any discrepancy triggers an alert and halts downstream processing."*

---

## Technical Deep-Dive Scenarios

### **Scenario 1: SAR Data Handling Across Platforms**

#### GCP (Your Implementation)
- DLP identifies SAR columns via custom templates
- Dataplex policy tags mark SAR columns
- Cloud KMS encrypts SAR columns
- Separate BQ dataset for SAR data
- IAM restricts access to authorized users

#### AWS Equivalent
```python
# Pseudo-implementation
1. Macie custom data identifier detects SAR patterns
2. Glue crawler discovers schema, tags SAR columns
3. Glue ETL job reads tags, applies KMS encryption
4. Writes to separate S3 prefix or Redshift schema
5. Lake Formation column-level permissions restrict access
```

#### Databricks Equivalent
```python
# Pseudo-implementation using Delta Lake
1. Unity Catalog classification identifies SAR columns
2. Tag-based rules trigger masking functions
3. Delta Lake MERGE with encryption UDFs
4. Separate Delta table with encrypted SAR columns
5. Unity Catalog grants restrict to authorized groups
6. Dynamic views apply real-time masking for queries
```

### **Scenario 2: Performance Tuning Example**

**Interview Question**: *"You mentioned 60% performance improvement. Walk me through one optimization."*

**Response**:
*"One major optimization was in our Teradata-to-BigQuery migration pipeline. Initially, we were processing 500GB tables in 4 hours with full table scans.

I analyzed the query patterns and found that 80% of queries filtered on date ranges. I implemented the following:

1. **Partitioning Strategy**: Converted to date-partitioned tables in BigQuery (or Redshift with sort keys / Delta Lake with partition columns)
2. **Predicate Pushdown**: Modified the extraction query to leverage source system indexes
3. **Parallel Processing**: Split extraction into concurrent workers using Airflow dynamic task mapping (or MWAA / Databricks Jobs)
4. **Columnar Compression**: Switched from CSV to Parquet format, reducing I/O by 70%
5. **Caching Layer**: Implemented a temporary staging table for frequently accessed lookups

Result: Processing time dropped from 4 hours to 90 minutes—a 62.5% improvement. We also reduced BigQuery slot consumption by 40% through better query planning, which translated to cost savings of $15K per month for that single pipeline."*

---

## Platform-Specific "Gotchas" to Mention

### **AWS-Specific**
- "S3 eventual consistency considerations (now strongly consistent, but important for legacy knowledge)"
- "Glue job capacity units (DPU) vs. EMR instance types—cost optimization trade-offs"
- "Lake Formation permissions can conflict with S3 bucket policies—need clear IAM strategy"
- "Redshift distribution keys and sort keys critical for join performance"

### **Databricks-Specific**
- "Cluster sizing: compute-optimized vs. memory-optimized for Spark workloads"
- "Delta Lake OPTIMIZE and VACUUM operations essential for read performance"
- "Unity Catalog requires careful namespace planning—can't easily restructure later"
- "Databricks Runtime versions—Delta Lake features vary significantly across versions"

---

## Recommended Certifications (If Asked)

While you have GCP and AWS ML certifications, for senior roles interviewing with AWS/Databricks:

**AWS Path:**
- AWS Certified Solutions Architect – Professional (aligns with your architecture experience)
- AWS Certified Data Analytics – Specialty (directly relevant)

**Databricks Path:**
- Databricks Certified Data Engineer Professional (highly valued)
- Databricks Lakehouse Fundamentals (good foundational credential)

*Note: You can mention you're actively pursuing these based on job requirements.*

---

## Final Strategic Advice

1. **Lead with Architecture, Not Tools**: Focus on *why* you made design decisions, not just *what* tools you used
2. **Use Cloud-Agnostic Terminology First**: Say "object storage" before saying "S3" or "GCS"—shows transferable thinking
3. **Quantify Impact**: Always tie technical work to business outcomes (15+ PB migrated, 60% performance improvement, 40% incident reduction)
4. **Show Adaptability**: Mention you've researched the company's stack and highlight how your GCP experience translates

**Example Opening Statement**:
*"While my recent experience is in GCP, data engineering principles are cloud-agnostic. The quarantine-to-delivery pattern I built is fundamentally about secure data movement with governance—whether that's S3 + Macie + Lake Formation in AWS, or Bronze-Silver-Gold with Unity Catalog in Databricks. The Airflow DAGs I developed would run identically on MWAA or integrate seamlessly with Databricks Workflows. What matters is understanding distributed systems, data security, and building resilient pipelines—and I'm excited to apply that expertise to [Company's] AWS/Databricks environment."*
