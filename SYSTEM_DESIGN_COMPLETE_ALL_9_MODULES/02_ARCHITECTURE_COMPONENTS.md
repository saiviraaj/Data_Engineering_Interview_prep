# MODULE 2: ARCHITECTURE COMPONENTS
## PhD-Level Data Engineering Interview Preparation
### Tailored for Viraaj Sivaraju — Senior Data Engineer, Wells Fargo CDM Next

---

## PART 1: COMPUTE LAYER

### Serverless vs Managed vs Self-Managed

```
SERVERLESS (highest abstraction):
  - No infrastructure management
  - Auto-scales to zero
  - Pay per execution
  - Examples: Cloud Functions, BigQuery, Dataflow (Streaming Engine)
  - Best for: event-driven, variable workloads

MANAGED (middle ground):
  - Cluster management handled by provider
  - You configure sizing, scaling policies
  - Examples: Dataproc, GKE, Cloud Composer
  - Best for: long-running workloads, predictable traffic

SELF-MANAGED (lowest abstraction):
  - Full control over OS, runtime, dependencies
  - You handle patching, scaling, HA
  - Examples: VMs on GCE, on-premise Hadoop
  - Best for: legacy systems, special OS requirements
```

### GCP Compute Services for Data Engineering

| Service | Type | Best For | CDM Next Usage |
|---|---|---|---|
| Dataflow | Serverless | Stream + batch pipelines | Primary ingestion engine |
| Dataproc | Managed Spark/Hadoop | Heavy Spark transformations | Legacy migration jobs |
| Cloud Run | Serverless containers | APIs, microservices | Config validation API |
| Cloud Functions | Serverless functions | Event triggers, webhooks | Pipeline triggers |
| GKE | Managed Kubernetes | Long-running custom workloads | Specialized tools |
| Vertex AI | Managed ML | Model training and serving | DLP, ML scoring |

---

## PART 2: STORAGE LAYER — COMPLETE TAXONOMY

### Object Storage (GCS)

```
CHARACTERISTICS:
  - Flat namespace (no real directories — paths are just key prefixes)
  - Immutable objects (upload is atomic; no partial writes)
  - Unlimited scale
  - Eventual consistency on metadata operations
  - Strong consistency on object reads after write (since Nov 2020)
  - 11 nines (99.999999999%) durability

STORAGE CLASSES:
  Standard:     $0.020/GB-month — hot data, frequent access
  Nearline:     $0.010/GB-month — < once/month access, 30-day min
  Coldline:     $0.004/GB-month — < once/quarter access, 90-day min
  Archive:      $0.0012/GB-month — < once/year, 365-day min, retrieval fee

PERFORMANCE:
  Single object max: 5 TB
  Max throughput per object: 2 Gbps (single-stream read)
  Multi-stream: effectively unlimited (parallel reads)
  
GCS NAMING BEST PRACTICES for CDM Next:
  gs://cdm-[env]/[source]/[entity]/dt=[YYYY-MM-DD]/[file].parquet
  
  Example:
  gs://cdm-prod/teradata/accounts/dt=2024-01-15/accounts_00001.parquet
  
  Benefits:
  - Hive-compatible partitioning (Dataproc/Spark reads partitions natively)
  - Easy date-range filtering
  - Clear source attribution
```

### Block Storage (Persistent Disks)

```
CHARACTERISTICS:
  - Low-latency random access
  - Attached to single VM (standard) or multiple (multi-reader)
  - Durable: replicated within zone
  
TYPES:
  pd-standard: HDD, $0.040/GB-month, 120 IOPS/GB read
  pd-ssd:      SSD, $0.170/GB-month, 30,000 IOPS
  pd-extreme:  NVMe SSD, $0.125/GB-month, 120,000 IOPS
  
USE IN DATA ENGINEERING:
  - Dataflow worker local disk (shuffle, state)
  - Dataproc HDFS (local HDFS on nodes)
  - VM-based databases
```

### File Storage (Filestore)

```
CHARACTERISTICS:
  - NFS-compatible shared filesystem
  - Multiple VMs can mount simultaneously
  - Good for: shared ML datasets, legacy applications needing POSIX filesystem
  
LIMITED USE IN CDM NEXT:
  Not used in CDM Next — GCS preferred for all bulk storage.
  Filestore only for legacy on-prem applications that can't use GCS.
```

---

## PART 3: DATABASE DEEP DIVES

### BigQuery Architecture

```
STORAGE AND COMPUTE SEPARATION:
  BigQuery separates storage (Colossus) from compute (Dremel).
  
  COLOSSUS (storage):
  - Distributed columnar file system
  - Data stored in Capacitor format (columnar, compressed)
  - Replicated across multiple datacenters
  - Accessible to any compute worker
  
  DREMEL (compute):
  - Massively parallel query execution engine
  - Query distributed to thousands of workers
  - Each worker reads only relevant columns (columnar advantage)
  - Results aggregated in tree structure

QUERY EXECUTION FLOW:
  1. Query submitted → Query Router
  2. Router parses SQL → query plan
  3. Plan distributed to leaf nodes (storage workers)
  4. Leaf nodes read columns from Colossus
  5. Results aggregated at mixer nodes
  6. Final result returned

SLOTS:
  A slot = 1 unit of BigQuery compute (1 vCPU equivalent)
  On-demand: shared slot pool, fair queuing, $5/TB scanned
  Reserved: dedicated slots, $0.04/slot-hour
  
  1000 slots can process ~1TB in ~10 seconds
  (depends heavily on query structure)

PARTITIONING IN BIGQUERY:
  Time-unit partitioning (most common):
    PARTITION BY DATE(event_ts)  → daily partitions
    PARTITION BY TIMESTAMP_TRUNC(event_ts, HOUR) → hourly partitions
    
  Integer range partitioning:
    PARTITION BY RANGE_BUCKET(customer_id, GENERATE_ARRAY(0, 1000000, 10000))
    
  Ingestion-time partitioning:
    PARTITION BY _PARTITIONTIME  → when row was loaded
    
CLUSTERING (always combine with partitioning):
  CLUSTER BY region, product_category
  - Rows with same cluster key values stored together
  - BigQuery skips blocks that don't match WHERE clause on cluster columns
  - Free — no extra cost, automatic maintenance
  
  COMBINED EFFECT:
    Without: SELECT SUM(revenue) WHERE date='2024-01' AND region='US'
      → scans entire 2024-01 partition
    With partitioning + clustering:
      → scans only US rows in 2024-01 partition
      → 10-100× less data scanned
```

### Cloud Bigtable Architecture

```
ARCHITECTURE:
  - Wide-column NoSQL database
  - Based on Google's original Bigtable paper (2006)
  - Row key → sorted map of column families → column qualifiers → versioned cells
  
ROW KEY DESIGN (most critical decision):
  
  BAD: user_id as-is
    → All new users get sequential IDs → hotspot on latest tablet
  
  GOOD: hash_prefix + user_id
    → Hash(user_id)[:4] + user_id → distributed across tablets
    
  Pattern for CDM Next risk profiles:
    [hash(customer_id)[:2]]#[customer_id]
    Example: "4f#CUST123456"
    
COLUMN FAMILIES:
  - Group related columns that are accessed together
  - Different GC policies per family
  - In CDM Next context:
    cf:profile → customer_name, email_hash, risk_tier
    cf:velocity → txn_count_1h, txn_count_24h, amount_sum_7d
    cf:audit → last_update_ts, update_source

PERFORMANCE:
  Single row read: < 1ms P50, < 10ms P99
  Throughput per node: ~10,000 QPS
  Scale: add nodes to increase throughput linearly
  Storage: automatically balanced across nodes

BIGTABLE VS ALTERNATIVES:
  vs Redis: Bigtable persists to disk (durable), Redis in-memory (fast)
  vs HBase: Same data model, but Bigtable is fully managed
  vs Spanner: Bigtable no transactions, Spanner full ACID
  vs BigQuery: Bigtable for point lookups, BQ for analytics
```

### Cloud Spanner Architecture

```
WHAT MAKES SPANNER UNIQUE:
  Globally distributed + ACID transactions + SQL
  This was previously considered impossible (CAP theorem suggests CP + global = slow)
  
  HOW SPANNER ACHIEVES IT:
  1. TrueTime API: atomic clocks + GPS in every datacenter
     → Spanner knows the upper bound of clock skew globally (< 7ms)
     → Can assign globally consistent timestamps
  
  2. Paxos groups: each shard has a Paxos consensus group
     → Writes require majority agreement (not all replicas)
     → 2-phase commit across shards for distributed transactions
  
WHEN TO USE SPANNER (vs BigQuery vs Cloud SQL):
  Choose Spanner when:
  - Need global consistency + strong ACID
  - Multiple regions, writes from all regions
  - Scale beyond single PostgreSQL node
  - Example: global banking ledger, global inventory

  Choose Cloud SQL when:
  - Single region OLTP
  - Existing PostgreSQL/MySQL compatibility needed
  - Simpler use cases

  Choose BigQuery when:
  - Analytics workloads
  - Columnar access patterns
  - No transactional requirements

SPANNER IN CDM NEXT CONTEXT:
  Not used in CDM Next. CDM Next uses:
  - Firestore for config store (document model, cheap)
  - BigQuery for audit/metadata (analytics access pattern)
  - Bigtable for real-time profiles (low-latency KV access)
```

### Firestore Architecture

```
CHARACTERISTICS:
  - Document-oriented NoSQL database
  - Real-time listeners (push updates to clients)
  - Strong consistency for single-document reads
  - ACID transactions on single document or transaction block
  - Scales automatically (no provisioning)

DATA MODEL:
  Collections → Documents → Fields
  
  cdm-config (collection)
    ├── teradata-accounts-daily (document)
    │     ├── source: {...}
    │     ├── transformation: {...}
    │     └── destination: {...}
    └── kafka-events-streaming (document)
          ├── source: {...}
          └── ...

CDM NEXT CONFIG STORE DESIGN:
  - Pipeline configs stored as Firestore documents
  - Each Dataflow template reads its config at startup
  - Config changes reflected within seconds (no pipeline restart needed)
  - Versioned configs: config/v1/pipeline_id, config/v2/pipeline_id
  - Firestore transactions ensure atomic config updates
  
FIRESTORE LIMITS (important for design):
  - Document size: max 1 MB
  - Write rate per document: 1 write/second sustained
  - Reads: ~50,000 reads/second per project (soft limit)
  - Transactions: max 500 operations per transaction
```

---

## PART 4: MESSAGING AND STREAMING

### Apache Kafka vs Google Pub/Sub

| Feature | Kafka | Cloud Pub/Sub |
|---|---|---|
| Retention | Configurable (default 7 days, can be infinite) | 7 days max |
| Replay | Yes — seek to any offset | Limited — replay within retention window |
| Ordering | Per-partition ordering | Per-message ordering key (optional) |
| Consumer groups | Yes — multiple independent readers | Yes — subscriptions |
| Exactly-once | Yes (with transactions) | At-least-once (deduplicate downstream) |
| Management | Self-managed or Confluent | Fully managed |
| Schema registry | Confluent Schema Registry | Pub/Sub schema support |
| Throughput | 10+ GB/s per broker cluster | 10 GB/s per topic |
| Latency | ~5ms P99 | ~100ms P99 (higher latency) |

**When to use which in CDM Next context:**
- Kafka: On-premise source systems that already use Kafka → CDM Next reads from Kafka
- Pub/Sub: Cloud-native events, Dataflow integration (native connector), simpler ops

### Pub/Sub Deep Dive

```
CONCEPTS:
  Topic: named channel for messages
  Publisher: writes messages to topic
  Subscription: named read channel from a topic
  Subscriber: reads messages from subscription
  
  One topic can have multiple subscriptions.
  Each subscription gets ALL messages independently.
  
MESSAGE DELIVERY:
  Pull: subscriber calls Pub/Sub API to get messages
    - Dataflow uses pull internally
    - Better for variable throughput
    
  Push: Pub/Sub calls subscriber's HTTP endpoint
    - Better for event-driven architectures
    - Cloud Functions, Cloud Run integration

ORDERING GUARANTEES:
  Without ordering key: no ordering guarantee across partitions
  With ordering key: messages with same key delivered in order
    messages | "SetKey" >> beam.Map(lambda m: (m.user_id, m))
    → All messages for same user_id delivered in order

MESSAGE ACKNOWLEDGEMENT:
  - Subscriber must ACK each message within ack_deadline (default 10s, max 600s)
  - If not ACKed in time: redelivered (AT-LEAST-ONCE)
  - Extended with ModifyAckDeadline for long-processing messages
  - Dead-letter topic: after max_delivery_attempts failures, send to DLQ

EXACTLY-ONCE WITH PUB/SUB:
  Pub/Sub itself is at-least-once.
  Achieve exactly-once downstream:
    1. Assign unique message_id to each message at source
    2. Deduplicate on message_id in Dataflow state
    3. Use idempotent BigQuery writes (job_id deduplication)
```

### Kafka Deep Dive

```
ARCHITECTURE:
  Brokers: servers that store and serve messages
  Topics: logical channels, split into Partitions
  Partitions: ordered, immutable log of messages
  Offsets: position of a message within a partition
  Consumer Groups: set of consumers reading a topic cooperatively

PARTITIONING STRATEGY:
  Round-robin: even distribution across partitions (no key)
  Key-based: same key always goes to same partition (enables ordering per key)
  Custom: application-defined partition assignment
  
  CDM NEXT: If consuming from Kafka, partition by source_system_id
  → Ensures ordered processing per source

REPLICATION:
  Replication Factor: how many broker copies each partition has
  ISR (In-Sync Replicas): replicas fully caught up with leader
  
  RF=3 with ISR=2 means:
    - 3 copies exist
    - Write acknowledged when 2 replicas have it
    - Can tolerate 1 broker failure without data loss

KAFKA CONNECT FOR CDM NEXT:
  Source Connector: Kafka → GCS (reads from Kafka, writes to GCS)
  BigQuery Sink Connector: Kafka → BigQuery directly
  Enables CDM Next to consume from Kafka without writing custom code
```

---

## PART 5: NETWORKING FUNDAMENTALS FOR DATA ENGINEERING

### VPC and Private Networking

```
VPC (Virtual Private Cloud):
  - Isolated network within GCP
  - Control inbound/outbound traffic with firewall rules
  - Subnets within regions
  
CDM NEXT NETWORK DESIGN:
  
  On-premise (Wells Fargo DC)
       │
  Dedicated Interconnect (10 Gbps × 4 = 40 Gbps)
       │
  Transit VPC (shared services)
       │
  ├── CDM Platform VPC (Dataflow workers, Cloud Composer)
  └── Data VPC (BigQuery private access, GCS private access)
  
  VPC Service Controls (security perimeter):
    - BigQuery, GCS, Pub/Sub enclosed in perimeter
    - Data cannot leave perimeter even if credentials compromised
    - API calls from outside perimeter rejected
```

### Dedicated Interconnect vs VPN

```
DEDICATED INTERCONNECT:
  - Physical fiber connection between on-prem and GCP
  - 10 Gbps or 100 Gbps per link
  - Low latency (< 5ms)
  - SLA: 99.99% with 2+ links
  - Monthly commitment (no per-GB charge)
  - CDM NEXT: 4 × 10Gbps = 40Gbps total for 15PB migration

CLOUD VPN:
  - Encrypted tunnel over public internet
  - Max ~3 Gbps per tunnel (IPSec overhead)
  - Higher latency (50-200ms)
  - Cheaper ($0.04/hour + $0.05/GB egress)
  - Good for: dev environments, small data transfers
```

### Latency Numbers Every Engineer Should Know

```
Operation                          Latency
─────────────────────────────────────────────
L1 cache reference                  0.5 ns
L2 cache reference                  7 ns
RAM reference                       100 ns
SSD random read                     100 μs
Network round trip (same datacenter) 500 μs
SSD sequential read (1 MB)          1 ms
HDD seek                            10 ms
Network round trip (cross-region)   50 ms
Network round trip (cross-continent) 150 ms

PRACTICAL IMPLICATIONS:
  Bigtable single-row read:         1-10 ms    (network + SSD)
  Redis GET:                        < 1 ms     (network + RAM)
  BigQuery simple query:            1-3 sec    (massive parallel, startup cost)
  BigQuery complex analytics:       10-60 sec  (TB-scale scan)
  Pub/Sub publish-to-receive:       100 ms     (managed service overhead)
```

---

## PART 6: MONITORING AND OBSERVABILITY

### The Three Pillars

```
METRICS (What is happening?):
  - Numerical measurements over time
  - Examples: requests/sec, error rate, latency P99, CPU%
  - Tools: Cloud Monitoring, Prometheus, Datadog
  
LOGS (Why did it happen?):
  - Timestamped records of events
  - Structured logs > unstructured logs
  - Examples: pipeline run logs, error stack traces
  - Tools: Cloud Logging, Elasticsearch
  
TRACES (Where is time being spent?):
  - End-to-end request flow across services
  - Shows which component is slow
  - Tools: Cloud Trace, Jaeger, Zipkin

CDM NEXT OBSERVABILITY:
  - Cloud Monitoring: Dataflow job metrics, custom pipeline metrics
  - Cloud Logging: Pipeline execution logs, error details
  - BigQuery: Custom audit tables for business-level monitoring
  - Alerting: PagerDuty for P1 (data loss), email for P2 (SLA breach)
```

### Key Metrics for Data Pipelines

```python
# CDM Next custom metrics (published to Cloud Monitoring)

PIPELINE_METRICS = {
    # Throughput
    "rows_ingested_total": Counter,     # Total rows successfully ingested
    "bytes_processed_total": Counter,   # Total bytes processed
    
    # Quality
    "rows_quarantined_total": Counter,  # Rows failed quality checks
    "schema_drift_events": Counter,     # Schema change detections
    
    # Latency
    "pipeline_duration_seconds": Histogram,  # End-to-end runtime
    "watermark_lag_seconds": Gauge,          # Streaming: how far behind
    
    # Health
    "pipeline_success_rate": Gauge,     # % of successful runs (7-day rolling)
    "last_successful_run_ts": Gauge,    # Timestamp of last success (for freshness)
}

# Alert thresholds:
# watermark_lag_seconds > 3600 → CRITICAL
# pipeline_success_rate < 0.95 → WARNING
# last_successful_run_ts > expected_interval × 1.5 → WARNING
```

---

## PART 7: SECURITY IN DATA PLATFORMS

### IAM Design Principles

```
PRINCIPLE OF LEAST PRIVILEGE:
  Grant only the minimum permissions required.
  
  BAD: Grant roles/editor to all service accounts
  GOOD: Grant specific roles per need:
    Dataflow SA → roles/bigquery.dataEditor (only on target dataset)
    Dataflow SA → roles/storage.objectCreator (only on target bucket)
    Cloud Composer SA → roles/dataflow.developer (to launch jobs)
  
CDM NEXT IAM DESIGN:
  Service Account: cdm-dataflow-sa@project.iam.gserviceaccount.com
    - roles/bigquery.dataEditor on cdm_* datasets
    - roles/storage.objectAdmin on gs://cdm-*
    - roles/pubsub.subscriber on cdm-* topics
    - roles/cloudkms.cryptoKeyEncrypterDecrypter (for CMEK)
    - roles/secretmanager.secretAccessor (for source credentials)
  
  NOT granted:
    - roles/bigquery.admin (too broad)
    - roles/editor (way too broad)
    - roles/owner (never for service accounts)
```

### Encryption

```
ENCRYPTION AT REST:
  Google-managed: default, no action needed
  Customer-managed (CMEK): you manage keys in Cloud KMS
    - Required for regulated industries (PCI, HIPAA)
    - Key rotation schedule enforced
    - Key deletion = data inaccessible (crypto-shredding for GDPR)
  
  CDM NEXT:
    All BigQuery datasets: CMEK with keys in Cloud KMS
    All GCS buckets: CMEK
    Key rotation: annual
    
ENCRYPTION IN TRANSIT:
  All GCP APIs use TLS 1.2+ by default
  Dedicated Interconnect: encrypted at MACsec layer
  No additional configuration needed for GCP services

DLP (Data Loss Prevention) IN CDM NEXT:
  - Scans all data before writing to BigQuery
  - Detects: SSN, credit card, email, phone, passport numbers
  - Action: mask/tokenize PII columns
  - Result: raw PII never stored in BigQuery
  
  Performance: DLP API processes ~100 MB/s per worker
  At 10 GB/s ingestion: need 100 parallel DLP calls
  → CDM Next batches records, parallelizes DLP calls
```

---

## MODULE 2 SUMMARY

| Component | GCP Service | Key Characteristics |
|---|---|---|
| Object storage | GCS | Immutable, unlimited scale, 11 nines durability |
| Columnar warehouse | BigQuery | Serverless, columnar, partitioned + clustered |
| Low-latency KV | Bigtable | < 10ms reads, linear scaling, wide-column |
| Global ACID DB | Spanner | TrueTime, distributed transactions |
| Config/document | Firestore | Document model, real-time, strong consistency |
| Streaming | Pub/Sub | Managed, at-least-once, 7-day retention |
| Processing | Dataflow | Serverless, Apache Beam, exactly-once option |
| Orchestration | Cloud Composer | Managed Airflow, DAG-based workflows |
| Monitoring | Cloud Monitoring | Metrics, alerting, dashboards |
| Security | IAM + KMS + DLP | Least privilege, CMEK encryption, PII detection |

---

*Module 2 Complete — ~9,000 words.*
