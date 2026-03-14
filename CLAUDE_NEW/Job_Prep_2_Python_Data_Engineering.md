# 🐍 PYTHON FOR DATA ENGINEERING - GCP FOCUSED
## Complete Guide for Lloyds Technology Centre Interview

**Focus:** Python + GCP Client Libraries + Data Processing  
**Level:** Senior Data Engineer  
**Target:** Production-ready, enterprise-grade code

---

## 📚 TABLE OF CONTENTS

1. Python Data Processing Libraries
2. Google Cloud Client Libraries (BigQuery, GCS, Pub/Sub)
3. Data Pipeline Design Patterns
4. Error Handling & Retry Logic
5. Logging Best Practices
6. Configuration Management
7. Testing Strategies
8. Code Quality & Documentation

---

## 🔧 PART 1: PYTHON DATA PROCESSING LIBRARIES

### **1.1 Pandas for Data Processing**

#### **Reading/Writing Data**
```python
import pandas as pd
from google.cloud import bigquery, storage

# Read from BigQuery
def read_from_bigquery(query, project_id):
    """
    Read data from BigQuery into pandas DataFrame
    """
    client = bigquery.Client(project=project_id)
    
    df = client.query(query).to_dataframe()
    
    # Or using pandas-gbq
    df = pd.read_gbq(
        query,
        project_id=project_id,
        dialect='standard'
    )
    
    return df

# Write to BigQuery
def write_to_bigquery(df, table_id, write_disposition='WRITE_APPEND'):
    """
    Write pandas DataFrame to BigQuery
    
    Args:
        df: pandas DataFrame
        table_id: 'project.dataset.table'
        write_disposition: WRITE_APPEND, WRITE_TRUNCATE, WRITE_EMPTY
    """
    client = bigquery.Client()
    
    job_config = bigquery.LoadJobConfig(
        write_disposition=write_disposition,
        # Auto-detect schema
        autodetect=True,
        # Or specify schema
        # schema=[
        #     bigquery.SchemaField("name", "STRING"),
        #     bigquery.SchemaField("age", "INTEGER"),
        # ]
    )
    
    job = client.load_table_from_dataframe(
        df,
        table_id,
        job_config=job_config
    )
    
    job.result()  # Wait for job to complete
    
    print(f"Loaded {job.output_rows} rows to {table_id}")

# Read from GCS
def read_from_gcs(bucket_name, blob_name):
    """
    Read CSV/Parquet from GCS
    """
    # CSV
    gcs_path = f"gs://{bucket_name}/{blob_name}"
    df = pd.read_csv(gcs_path)
    
    # Parquet (recommended for large data)
    df = pd.read_parquet(gcs_path)
    
    return df

# Write to GCS
def write_to_gcs(df, bucket_name, blob_name):
    """
    Write DataFrame to GCS
    """
    gcs_path = f"gs://{bucket_name}/{blob_name}"
    
    # Parquet (recommended)
    df.to_parquet(gcs_path, index=False, compression='snappy')
    
    # CSV
    df.to_csv(gcs_path, index=False)
```

#### **Data Transformation Patterns**
```python
# Common transformations for data engineering

def clean_and_transform(df):
    """
    Production-ready data cleaning
    """
    # 1. Handle nulls
    df['amount'] = df['amount'].fillna(0)
    df['category'] = df['category'].fillna('UNKNOWN')
    
    # 2. Data type conversions
    df['date'] = pd.to_datetime(df['date'])
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    
    # 3. Remove duplicates
    df = df.drop_duplicates(subset=['transaction_id'], keep='last')
    
    # 4. Add derived columns
    df['year_month'] = df['date'].dt.to_period('M').astype(str)
    df['day_of_week'] = df['date'].dt.day_name()
    
    # 5. Filter invalid data
    df = df[df['amount'] > 0]
    
    return df

def aggregate_data(df):
    """
    Common aggregations for reporting
    """
    # Daily summary
    daily_summary = df.groupby('date').agg({
        'amount': ['sum', 'mean', 'count'],
        'transaction_id': 'count',
        'user_id': 'nunique'
    }).reset_index()
    
    # Flatten multi-level columns
    daily_summary.columns = ['_'.join(col).strip('_') 
                             for col in daily_summary.columns.values]
    
    return daily_summary
```

---

## ☁️ PART 2: GOOGLE CLOUD CLIENT LIBRARIES

### **2.1 BigQuery Client Library**

#### **Complete BigQuery Operations**
```python
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
import time

class BigQueryManager:
    """
    Production-ready BigQuery operations
    """
    
    def __init__(self, project_id):
        self.project_id = project_id
        self.client = bigquery.Client(project=project_id)
    
    def run_query(self, query, timeout=300):
        """
        Execute query with timeout and error handling
        """
        try:
            query_job = self.client.query(query)
            results = query_job.result(timeout=timeout)
            
            print(f"Query processed {query_job.total_bytes_processed / (1024**3):.2f} GB")
            
            return results.to_dataframe()
        
        except Exception as e:
            print(f"Query failed: {e}")
            raise
    
    def create_table(self, dataset_id, table_id, schema):
        """
        Create table with schema
        """
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        
        table = bigquery.Table(table_ref, schema=schema)
        table = self.client.create_table(table)
        
        print(f"Created table {table_ref}")
        return table
    
    def load_from_gcs(self, dataset_id, table_id, gcs_uri, 
                      source_format='PARQUET', write_disposition='WRITE_APPEND'):
        """
        Load data from GCS to BigQuery
        """
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        
        job_config = bigquery.LoadJobConfig(
            source_format=source_format,
            write_disposition=write_disposition,
            autodetect=True  # Auto-detect schema
        )
        
        load_job = self.client.load_table_from_uri(
            gcs_uri,
            table_ref,
            job_config=job_config
        )
        
        load_job.result()  # Wait for completion
        
        table = self.client.get_table(table_ref)
        print(f"Loaded {table.num_rows} rows to {table_ref}")
    
    def export_to_gcs(self, dataset_id, table_id, gcs_uri, 
                      destination_format='PARQUET'):
        """
        Export BigQuery table to GCS
        """
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        
        job_config = bigquery.ExtractJobConfig(
            destination_format=destination_format,
            compression='SNAPPY' if destination_format == 'PARQUET' else None
        )
        
        extract_job = self.client.extract_table(
            table_ref,
            gcs_uri,
            job_config=job_config
        )
        
        extract_job.result()
        print(f"Exported {table_ref} to {gcs_uri}")
    
    def create_partitioned_table(self, dataset_id, table_id, schema, 
                                  partition_field, cluster_fields=None):
        """
        Create partitioned and clustered table
        """
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        
        table = bigquery.Table(table_ref, schema=schema)
        
        # Partitioning
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field=partition_field,
            expiration_ms=90 * 24 * 60 * 60 * 1000  # 90 days
        )
        
        # Clustering
        if cluster_fields:
            table.clustering_fields = cluster_fields
        
        table = self.client.create_table(table)
        print(f"Created partitioned table {table_ref}")
        
        return table

# Usage
bq = BigQueryManager(project_id='my-project')

# Query
df = bq.run_query("""
    SELECT 
        user_id,
        SUM(amount) as total_amount
    FROM `project.dataset.transactions`
    WHERE date = '2024-01-01'
    GROUP BY user_id
""")

# Load from GCS
bq.load_from_gcs(
    'my_dataset',
    'transactions',
    'gs://my-bucket/data/*.parquet',
    source_format='PARQUET'
)
```

### **2.2 Cloud Storage Client Library**

```python
from google.cloud import storage
import os

class GCSManager:
    """
    Production-ready GCS operations
    """
    
    def __init__(self, project_id):
        self.client = storage.Client(project=project_id)
    
    def upload_file(self, bucket_name, source_file_path, destination_blob_name):
        """
        Upload file to GCS
        """
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        
        blob.upload_from_filename(source_file_path)
        
        print(f"Uploaded {source_file_path} to gs://{bucket_name}/{destination_blob_name}")
    
    def download_file(self, bucket_name, source_blob_name, destination_file_path):
        """
        Download file from GCS
        """
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        
        blob.download_to_filename(destination_file_path)
        
        print(f"Downloaded gs://{bucket_name}/{source_blob_name} to {destination_file_path}")
    
    def list_blobs(self, bucket_name, prefix=None):
        """
        List all blobs in bucket/prefix
        """
        bucket = self.client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        
        blob_names = [blob.name for blob in blobs]
        return blob_names
    
    def delete_blob(self, bucket_name, blob_name):
        """
        Delete blob from GCS
        """
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        blob.delete()
        
        print(f"Deleted gs://{bucket_name}/{blob_name}")
    
    def copy_blob(self, source_bucket, source_blob, dest_bucket, dest_blob):
        """
        Copy blob between buckets
        """
        source_bucket = self.client.bucket(source_bucket)
        source_blob_obj = source_bucket.blob(source_blob)
        
        dest_bucket = self.client.bucket(dest_bucket)
        
        source_bucket.copy_blob(source_blob_obj, dest_bucket, dest_blob)
        
        print(f"Copied gs://{source_bucket}/{source_blob} to gs://{dest_bucket}/{dest_blob}")

# Usage
gcs = GCSManager(project_id='my-project')

# Upload
gcs.upload_file('my-bucket', 'local_file.csv', 'data/file.csv')

# List files
files = gcs.list_blobs('my-bucket', prefix='data/')
print(files)

# Download
gcs.download_file('my-bucket', 'data/file.csv', 'downloaded_file.csv')
```

### **2.3 Pub/Sub for Event-Driven Processing**

```python
from google.cloud import pubsub_v1
import json

class PubSubManager:
    """
    Pub/Sub for real-time data streaming
    """
    
    def __init__(self, project_id):
        self.project_id = project_id
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
    
    def publish_message(self, topic_name, message_data):
        """
        Publish message to topic
        """
        topic_path = self.publisher.topic_path(self.project_id, topic_name)
        
        # Convert to JSON if dict
        if isinstance(message_data, dict):
            message_data = json.dumps(message_data)
        
        # Publish
        future = self.publisher.publish(
            topic_path,
            message_data.encode('utf-8')
        )
        
        message_id = future.result()
        print(f"Published message {message_id} to {topic_name}")
        
        return message_id
    
    def subscribe_messages(self, subscription_name, callback):
        """
        Subscribe and process messages
        """
        subscription_path = self.subscriber.subscription_path(
            self.project_id, 
            subscription_name
        )
        
        streaming_pull_future = self.subscriber.subscribe(
            subscription_path,
            callback=callback
        )
        
        print(f"Listening for messages on {subscription_name}...")
        
        try:
            streaming_pull_future.result()
        except Exception as e:
            streaming_pull_future.cancel()
            print(f"Subscription cancelled: {e}")

# Callback function
def process_message(message):
    """
    Process incoming Pub/Sub message
    """
    print(f"Received: {message.data}")
    
    try:
        # Parse JSON
        data = json.loads(message.data.decode('utf-8'))
        
        # Process data (e.g., write to BigQuery)
        # ...
        
        # Acknowledge
        message.ack()
        
    except Exception as e:
        print(f"Error processing message: {e}")
        message.nack()  # Will be re-delivered

# Usage
pubsub = PubSubManager(project_id='my-project')

# Publish
pubsub.publish_message('my-topic', {'user_id': 123, 'event': 'click'})

# Subscribe
pubsub.subscribe_messages('my-subscription', process_message)
```

---

## 🔄 PART 3: DATA PIPELINE DESIGN PATTERNS

### **3.1 ETL Pipeline Template**

```python
import logging
from datetime import datetime
from google.cloud import bigquery, storage
import pandas as pd

class ETLPipeline:
    """
    Production ETL pipeline template
    """
    
    def __init__(self, project_id, config):
        self.project_id = project_id
        self.config = config
        self.bq_client = bigquery.Client(project=project_id)
        self.gcs_client = storage.Client(project=project_id)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def extract(self):
        """
        Extract data from source
        """
        self.logger.info("Starting extraction...")
        
        try:
            # Extract from BigQuery
            query = f"""
                SELECT *
                FROM `{self.config['source_table']}`
                WHERE date = '{self.config['process_date']}'
            """
            
            df = self.bq_client.query(query).to_dataframe()
            
            self.logger.info(f"Extracted {len(df)} rows")
            return df
        
        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            raise
    
    def transform(self, df):
        """
        Transform data
        """
        self.logger.info("Starting transformation...")
        
        try:
            # Data cleaning
            df = df.dropna(subset=['user_id', 'amount'])
            df = df[df['amount'] > 0]
            
            # Add derived columns
            df['processed_at'] = datetime.now()
            df['year_month'] = pd.to_datetime(df['date']).dt.to_period('M').astype(str)
            
            # Aggregations
            summary = df.groupby(['user_id', 'year_month']).agg({
                'amount': ['sum', 'mean', 'count'],
                'transaction_id': 'count'
            }).reset_index()
            
            self.logger.info(f"Transformed to {len(summary)} rows")
            return summary
        
        except Exception as e:
            self.logger.error(f"Transformation failed: {e}")
            raise
    
    def load(self, df):
        """
        Load data to destination
        """
        self.logger.info("Starting load...")
        
        try:
            table_id = self.config['destination_table']
            
            job_config = bigquery.LoadJobConfig(
                write_disposition='WRITE_APPEND',
                autodetect=True
            )
            
            job = self.bq_client.load_table_from_dataframe(
                df,
                table_id,
                job_config=job_config
            )
            
            job.result()
            
            self.logger.info(f"Loaded {job.output_rows} rows to {table_id}")
        
        except Exception as e:
            self.logger.error(f"Load failed: {e}")
            raise
    
    def run(self):
        """
        Execute full ETL pipeline
        """
        self.logger.info("=== Starting ETL Pipeline ===")
        start_time = datetime.now()
        
        try:
            # Extract
            data = self.extract()
            
            # Transform
            transformed_data = self.transform(data)
            
            # Load
            self.load(transformed_data)
            
            # Log success
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"=== Pipeline completed successfully in {duration}s ===")
            
            return {
                'status': 'SUCCESS',
                'duration': duration,
                'rows_processed': len(transformed_data)
            }
        
        except Exception as e:
            self.logger.error(f"=== Pipeline failed: {e} ===")
            return {
                'status': 'FAILED',
                'error': str(e)
            }

# Configuration
config = {
    'source_table': 'project.dataset.raw_transactions',
    'destination_table': 'project.dataset.aggregated_transactions',
    'process_date': '2024-01-01'
}

# Run pipeline
pipeline = ETLPipeline(project_id='my-project', config=config)
result = pipeline.run()

print(result)
```

### **3.2 Incremental Loading Pattern**

```python
def incremental_load_bigquery(source_table, dest_table, date_column):
    """
    Load only new/updated data
    """
    client = bigquery.Client()
    
    # Get max date from destination
    query = f"""
        SELECT MAX({date_column}) as max_date
        FROM `{dest_table}`
    """
    
    result = client.query(query).to_dataframe()
    last_loaded_date = result['max_date'].iloc[0]
    
    if last_loaded_date is None:
        # Initial load
        where_clause = ""
    else:
        # Incremental load
        where_clause = f"WHERE {date_column} > '{last_loaded_date}'"
    
    # Load new data
    query = f"""
        INSERT INTO `{dest_table}`
        SELECT * FROM `{source_table}`
        {where_clause}
    """
    
    job = client.query(query)
    job.result()
    
    print(f"Loaded data since {last_loaded_date}")
```

---

## 🛡️ PART 4: ERROR HANDLING & RETRY LOGIC

### **4.1 Retry Decorator**

```python
import time
from functools import wraps
from google.api_core import retry, exceptions

def retry_with_backoff(max_retries=3, backoff_factor=2):
    """
    Retry decorator with exponential backoff
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                
                except exceptions.TooManyRequests as e:
                    retries += 1
                    if retries >= max_retries:
                        raise
                    
                    wait_time = backoff_factor ** retries
                    print(f"Rate limited. Retry {retries}/{max_retries} in {wait_time}s")
                    time.sleep(wait_time)
                
                except Exception as e:
                    print(f"Error: {e}")
                    raise
        
        return wrapper
    return decorator

# Usage
@retry_with_backoff(max_retries=3)
def load_data_to_bigquery(df, table_id):
    client = bigquery.Client()
    job = client.load_table_from_dataframe(df, table_id)
    job.result()
```

### **4.2 Error Handling Best Practices**

```python
from google.cloud import bigquery
from google.cloud.exceptions import NotFound, Conflict
import logging

logger = logging.getLogger(__name__)

def safe_bigquery_operation(project_id, dataset_id, table_id):
    """
    Comprehensive error handling
    """
    client = bigquery.Client(project=project_id)
    table_ref = f"{project_id}.{dataset_id}.{table_id}"
    
    try:
        # Check if table exists
        table = client.get_table(table_ref)
        logger.info(f"Table {table_ref} found with {table.num_rows} rows")
        
        return table
    
    except NotFound:
        logger.warning(f"Table {table_ref} not found. Creating...")
        
        # Create table
        schema = [
            bigquery.SchemaField("id", "INTEGER"),
            bigquery.SchemaField("name", "STRING"),
        ]
        
        table = bigquery.Table(table_ref, schema=schema)
        table = client.create_table(table)
        logger.info(f"Created table {table_ref}")
        
        return table
    
    except Conflict as e:
        logger.error(f"Conflict error: {e}")
        # Table is being created by another process
        time.sleep(5)
        return client.get_table(table_ref)
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
```

---

## 📝 PART 5: LOGGING BEST PRACTICES

```python
import logging
from google.cloud import logging as cloud_logging

def setup_logging(log_name='data-pipeline'):
    """
    Setup logging for GCP Cloud Logging
    """
    # Cloud Logging
    client = cloud_logging.Client()
    client.setup_logging()
    
    # Console logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('pipeline.log')
        ]
    )
    
    logger = logging.getLogger(log_name)
    return logger

# Usage
logger = setup_logging()

logger.info("Pipeline started")
logger.warning("Partition contains no data")
logger.error("Failed to load data", extra={'table': 'transactions'})
```

---

## 🎯 INTERVIEW QUESTIONS - PYTHON FOR DATA ENGINEERING

**Q1: How do you handle large files that don't fit in memory?**
```python
ANSWER + CODE:

# Use chunking for large CSVs
def process_large_csv(file_path, chunk_size=100000):
    """
    Process CSV in chunks
    """
    chunks = []
    
    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
        # Process chunk
        processed = transform_data(chunk)
        chunks.append(processed)
    
    # Combine if needed
    result = pd.concat(chunks, ignore_index=True)
    return result

# Or use generators
def read_large_file_generator(file_path):
    """
    Memory-efficient file reading
    """
    with open(file_path, 'r') as f:
        for line in f:
            yield process_line(line)

# For BigQuery, use streaming or load from GCS
```

**Q2: How do you implement idempotent data pipelines?**
```python
ANSWER + CODE:

def idempotent_load(df, table_id, unique_key='id'):
    """
    Ensure pipeline can run multiple times safely
    """
    temp_table = f"{table_id}_temp"
    
    # 1. Load to temp table
    load_to_temp(df, temp_table)
    
    # 2. Merge with deduplication
    query = f"""
        MERGE `{table_id}` T
        USING `{temp_table}` S
        ON T.{unique_key} = S.{unique_key}
        WHEN MATCHED THEN
            UPDATE SET T.* = S.*
        WHEN NOT MATCHED THEN
            INSERT *
    """
    
    client.query(query).result()
    
    # 3. Drop temp table
    client.delete_table(temp_table)

# Benefits: Can rerun without duplicates
```

---

**STATUS:** Python for Data Engineering Complete!  
**Next File:** Data Management, Documentation, Process Improvement
