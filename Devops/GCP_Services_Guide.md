# GCP Services for Data Engineers

## Cloud Storage (GCS)

### Storage Classes
```
STANDARD: $0.02/GB/month - Hot data, frequent access
NEARLINE: $0.01/GB/month - Accessed <1/month
COLDLINE: $0.004/GB/month - Accessed <1/quarter
ARCHIVE: $0.0016/GB/month - Backup/compliance

Strategy: Use lifecycle policies to auto-transition
Day 0-30: STANDARD
Day 30-90: NEARLINE
Day 90-365: COLDLINE
Day >365: ARCHIVE
```

### Upload/Download
```python
from google.cloud import storage

client = storage.Client()
bucket = client.get_bucket("my-bucket")

# Upload
blob = bucket.blob("raw/users.csv")
blob.upload_from_filename("local_users.csv")

# Download
blob = bucket.blob("processed/results.csv")
blob.download_to_filename("local_results.csv")

# Batch upload
import os
for filename in os.listdir("local_data/"):
    blob = bucket.blob(f"raw/{filename}")
    blob.upload_from_filename(f"local_data/{filename}")
```

### Load to BigQuery
```python
from google.cloud import bigquery

client = bigquery.Client()

job_config = bigquery.LoadJobConfig(
    source_format=bigquery.SourceFormat.CSV,
    skip_leading_rows=1,
    autodetect=True,
)

load_job = client.load_table_from_uri(
    "gs://my-bucket/raw/users.csv",
    "project.dataset.users",
    job_config=job_config,
)
load_job.result()
```

## Dataflow (Apache Beam)

### Key Concepts
```
PCollection: Distributed data collection
PTransform: Operation on PCollection
Pipeline: DAG of transforms
```

### Batch Pipeline Example
```python
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions

class FilterEvents(beam.DoFn):
    def process(self, element):
        if element['amount'] > 100:
            yield element

options = PipelineOptions([
    '--runner=DataflowRunner',
    '--project=my-project',
])

with beam.Pipeline(options=options) as p:
    (p
     | 'ReadGCS' >> beam.io.ReadFromText('gs://bucket/input/*.json')
     | 'Parse' >> beam.Map(lambda x: json.loads(x))
     | 'Filter' >> beam.ParDo(FilterEvents())
     | 'WriteBQ' >> beam.io.WriteToBigQuery('project:dataset.events')
    )
```

### Streaming Pipeline
```python
from apache_beam.transforms.window import FixedWindows

with beam.Pipeline(options=options) as p:
    (p
     | 'ReadPubSub' >> beam.io.gcp.pubsub.ReadFromPubSub(topic='events')
     | 'Window' >> beam.WindowInto(FixedWindows(30))  # 30 sec
     | 'WriteBQ' >> beam.io.WriteToBigQuery('project:dataset.events')
    )
```

## Dataproc (Spark/Hadoop)

### Create Cluster
```python
from google.cloud import dataproc_v1

def create_cluster(project_id, region, cluster_name):
    client = dataproc_v1.ClusterControllerClient(
        client_options={"api_endpoint": f"{region}-dataproc.googleapis.com:443"}
    )
    
    cluster_config = dataproc_v1.types.ClusterConfig(
        master_config={
            "num_instances": 1,
            "machine_type_uri": "n2-standard-4",
        },
        worker_config={
            "num_instances": 2,
            "machine_type_uri": "n2-standard-4",
        },
        lifecycle_config={
            "idle_delete_ttl": {"seconds": 3600}  # Auto-delete after 1h
        },
    )
    
    operation = client.create_cluster(
        request={
            "project_id": project_id,
            "region": region,
            "cluster": dataproc_v1.types.Cluster(
                project_id=project_id,
                cluster_name=cluster_name,
                config=cluster_config,
            ),
        }
    )
    result = operation.result()
    print(f"Created cluster: {result.cluster_name}")
```

### Spark Job Example
```python
# submit_job.py
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("ETL_Job").getOrCreate()

# Read from BigQuery
df = spark.read.format("bigquery").option("table", "project.dataset.events").load()

# Transform
result = df.filter(df.amount > 100).groupBy("user_id").agg({"amount": "sum"})

# Write to BigQuery
result.write.format("bigquery").mode("overwrite").option("table", "project.dataset.aggregated").save()
```

## Cloud Composer (Airflow)

### Basic DAG
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'data_engineering',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 1, 1),
}

dag = DAG(
    'daily_pipeline',
    default_args=default_args,
    schedule_interval='0 2 * * *',  # 2 AM daily
    catchup=False,
)

def extract_data():
    print("Extracting data...")

def load_data():
    print("Loading data...")

t1 = PythonOperator(task_id='extract', python_callable=extract_data, dag=dag)
t2 = PythonOperator(task_id='load', python_callable=load_data, dag=dag)

t1 >> t2  # Define dependency
```

### XCom Communication
```python
def push_task(**context):
    context['task_instance'].xcom_push(key='my_key', value={'data': 'value'})

def pull_task(**context):
    data = context['task_instance'].xcom_pull(task_ids='push_task', key='my_key')
    print(f"Received: {data}")
```

## Cloud Pub/Sub

### Publish
```python
from google.cloud import pubsub_v1
import json

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path("my-project", "events")

event = {'event_id': 1, 'type': 'purchase', 'amount': 99.99}
message_bytes = json.dumps(event).encode('utf-8')

future = publisher.publish(topic_path, message_bytes)
message_id = future.result()
print(f"Published message: {message_id}")
```

### Subscribe
```python
from google.cloud import pubsub_v1
import json

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path("my-project", "events-sub")

def callback(message):
    event = json.loads(message.data.decode('utf-8'))
    print(f"Received: {event}")
    message.ack()

future = subscriber.subscribe(subscription_path, callback=callback)
future.result(timeout=3600)
```

## Cloud Functions

```python
# main.py - triggered by Pub/Sub
import functions_framework
from google.cloud import bigquery
import json

@functions_framework.cloud_event
def process_event(cloud_event):
    import base64
    
    client = bigquery.Client()
    message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
    event = json.loads(message)
    
    errors = client.insert_rows_json('project.dataset.events', [event])
    
    if not errors:
        return 'Success', 200
    else:
        raise Exception(f"Errors: {errors}")

# Deploy:
# gcloud functions deploy process_event --runtime python310 --trigger-topic events
```

## Datastream (CDC)

```python
from google.cloud import datastream_v1

def create_stream(project_id, location, stream_id):
    client = datastream_v1.DatastreamClient()
    
    source = datastream_v1.types.MysqlSourceConfig(
        hostname="source-mysql.example.com",
        port=3306,
        username="replication_user",
        password="password",
        database="source_db",
    )
    
    destination = datastream_v1.types.BigQueryDestinationConfig(
        dataset_prefix="replicated_",
    )
    
    stream = datastream_v1.types.Stream(
        display_name="MySQL to BQ",
        source_config=source,
        destination_config=destination,
    )
    
    operation = client.create_stream(
        request={
            "parent": f"projects/{project_id}/locations/{location}",
            "stream_id": stream_id,
            "stream": stream,
        }
    )
    result = operation.result()
    print(f"Created: {result.name}")
```

## Cost Optimization Strategies

### GCS
- Use lifecycle policies for auto-transition
- Archive data after 1 year (save 87%)
- Delete temporary files automatically

### Dataflow
- Batch is cheaper than streaming
- Use autoscaling
- Use preemptible VMs (70% cheaper)

### Dataproc
- Auto-scale clusters based on load
- Delete cluster immediately after job
- Use preemptible workers

### BigQuery
- Partition heavy tables
- Cluster on filtered columns
- Use materialized views
- Set table expiration

### Overall Pipeline Cost
```
Example 100K events/sec pipeline:
Pub/Sub: $500/month
Dataflow: $2000/month
BigQuery: $300/month
Total: ~$2800/month

vs Dataproc equivalent:
Dataproc: $5000/month (less efficient for streaming)
```

## Security Best Practices

```python
# Use Secret Manager (not env vars or hardcoding)
from google.cloud import secretmanager

def access_secret(project_id, secret_id):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Use Service Accounts (not user credentials)
# Grant least privilege (minimal IAM roles)
# Enable Cloud Audit Logs for compliance
# Use VPC-SC for network isolation
```

