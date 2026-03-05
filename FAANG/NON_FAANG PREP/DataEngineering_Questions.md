# Data Engineering Interview Questions

Complete data pipeline and architecture questions.

---

## NonFAANG Level (1-20)

### Q1: Design ETL Pipeline

Ingest data from multiple sources, transform, load to warehouse.

```python
# Source ingestion
def ingest_data(source_type, config):
    if source_type == 'api':
        return fetch_from_api(config['url'])
    elif source_type == 'database':
        return query_database(config['connection'])
    elif source_type == 's3':
        return read_from_s3(config['bucket'], config['key'])

# Transformation
def transform(raw_data):
    # Validate schema
    validate_schema(raw_data)
    
    # Clean
    cleaned = raw_data.drop_duplicates()
    cleaned = cleaned.dropna(subset=['id'])
    
    # Normalize
    cleaned['amount'] = cleaned['amount'].astype('float')
    cleaned['date'] = pd.to_datetime(cleaned['date'])
    
    return cleaned

# Load
def load_to_warehouse(data, target):
    if target == 'bigquery':
        data.to_gbq(table_id='dataset.table', if_exists='append')
    elif target == 'redshift':
        copy_to_redshift(data)
```

### Q2: Slowly Changing Dimensions (SCD)

Track changes in dimension tables over time.

```python
# SCD Type 1: Overwrite
def scd_type1(new_data, existing_data):
    # Simply update records
    existing_data.update(new_data)

# SCD Type 2: Keep history
def scd_type2(new_data, existing_data):
    # Mark old record as expired
    existing_data.loc[existing_data['id'].isin(new_data['id']), 'is_current'] = False
    existing_data.loc[existing_data['id'].isin(new_data['id']), 'end_date'] = today()
    
    # Add new record as current
    new_data['is_current'] = True
    new_data['start_date'] = today()
    new_data['end_date'] = NULL
    
    return pd.concat([existing_data, new_data])

# SCD Type 3: Keep limited history
def scd_type3(new_data, existing_data):
    # Keep previous value
    existing_data['previous_value'] = existing_data['current_value']
    existing_data['current_value'] = new_data['value']
```

### Q3: Data Quality Checks

```python
class DataQualityValidator:
    def validate(self, df):
        issues = []
        
        # Null check
        null_check = df.isnull().sum()
        if null_check.any():
            issues.append(f"Null values: {null_check}")
        
        # Duplicate check
        duplicates = df.duplicated(subset=['id']).sum()
        if duplicates > 0:
            issues.append(f"Duplicates: {duplicates}")
        
        # Range check
        if (df['amount'] < 0).any():
            issues.append("Negative amounts found")
        
        # Schema check
        expected_types = {'id': 'int', 'amount': 'float', 'date': 'datetime'}
        for col, dtype in expected_types.items():
            if str(df[col].dtype) != dtype:
                issues.append(f"Type mismatch: {col}")
        
        return issues if issues else "All checks passed"
```

### Q4: Incremental Load Pattern

```python
def incremental_load(source, warehouse):
    # Get last sync time
    last_sync = warehouse.query("SELECT MAX(sync_time) FROM tracking")
    
    # Load only new/changed data
    new_data = source.query(f"SELECT * WHERE updated_at > {last_sync}")
    
    # Identify changes
    new_ids = set(new_data['id'])
    existing_ids = set(warehouse.query("SELECT id FROM target")['id'])
    
    # New records
    new_records = new_data[new_data['id'].isin(new_ids - existing_ids)]
    warehouse.insert(new_records)
    
    # Updated records
    updated_records = new_data[new_data['id'].isin(new_ids & existing_ids)]
    warehouse.update(updated_records)
```

### Q5: Schema Evolution

```python
def evolve_schema(old_schema, new_schema):
    # Identify changes
    old_columns = set(old_schema.keys())
    new_columns = set(new_schema.keys())
    
    # Added columns
    added = new_columns - old_columns
    for col in added:
        df[col] = None  # Default value
    
    # Removed columns
    removed = old_columns - new_columns
    df = df.drop(removed, axis=1)
    
    # Type changes
    for col in new_columns & old_columns:
        if old_schema[col] != new_schema[col]:
            df[col] = df[col].astype(new_schema[col])
    
    return df
```

### Q6-20: Additional Topics
**6. Fact and Dimension Tables**
**7. Data Lineage Tracking**
**8. Disaster Recovery and Backups**
**9. Schema Validation**
**10. Deduplication Logic**
**11. Data Partitioning Strategies**
**12. Handling Late Arriving Data**
**13. Data Retention Policies**
**14. CDC (Change Data Capture)**
**15. Data Masking for PII**
**16. Cost Optimization**
**17. Monitoring Data Pipelines**
**18. Testing Data Pipelines**
**19. Documentation Requirements**
**20. Compliance (GDPR, HIPAA)**

---

## FAANG Level (21-40)

### Q21: Large Scale Data Migration

```python
class DataMigration:
    def migrate(self, source_db, target_db, table_name):
        # Phase 1: Full copy
        df = source_db.read_table(table_name)
        target_db.write_table(table_name, df)
        
        # Phase 2: Validate
        source_count = source_db.count(table_name)
        target_count = target_db.count(table_name)
        assert source_count == target_count
        
        # Phase 3: Incremental sync
        while True:
            new_data = source_db.query(f"""
                SELECT * FROM {table_name}
                WHERE updated_at > {last_sync_time}
            """)
            
            if new_data.empty:
                break
            
            target_db.upsert(table_name, new_data, 'id')
            last_sync_time = new_data['updated_at'].max()
            
            # Small batch delay
            time.sleep(1)
        
        # Phase 4: Cutover
        redirect_traffic_to_target()
```

### Q22: Real-time vs Batch Trade-offs

```
Batch Processing:
+ Simple, proven
+ Better for bulk operations
+ Cost-effective
- Latency (hours/days)

Real-time Streaming:
+ Low latency (seconds)
+ Immediate insights
- Complex infrastructure
- Higher cost
- State management

Hybrid (Lambda Architecture):
+ Best of both
- Complexity
- Dual maintenance
```

### Q23: Data Mesh Architecture

```
Instead of centralized DW:
- Each team owns their data as a product
- Teams expose APIs for data
- Central metadata registry
- Decentralized governance

Example:
Team A (Payments) → Payments Data Product (API)
Team B (Users) → User Data Product (API)
Team C (Analytics) → Consumes both via APIs
```

### Q24-40: Advanced Topics
**24. Disaster Recovery RTO/RPO**
**25. Data Governance at Scale**
**26. Delta Lake / Iceberg Features**
**27. Stream Processing Patterns**
**28. Data Quality SLOs**
**29. Cost Attribution**
**30. Multi-region Replication**

---

