# DevOps & Infrastructure: Complete Guide for Data Engineers

## Table of Contents
1. [Docker](#docker)
2. [Kubernetes](#kubernetes)
3. [Terraform](#terraform)
4. [GitHub Actions](#github-actions)
5. [Jenkins](#jenkins)
6. [Integration Examples](#integration-examples)
7. [Interview Preparation](#interview-preparation)

---

# Docker

## What is Docker?

Docker is a containerization platform that packages your application with all its dependencies (code, runtime, libraries, config files) into a standardized unit called a **container**. This ensures your application runs the same way everywhere - your laptop, server, cloud, etc.

### Why Docker?

**Problem it solves:**
```
Developer: "It works on my machine!"
DevOps: "But it doesn't work on production..."

Solution: Docker ensures same environment everywhere
```

### Key Concepts

#### **Images vs Containers**

```
Docker Image: Like a blueprint or template
- Contains: Application code + dependencies + configuration
- Immutable (read-only)
- Stored as layers
- Example: ubuntu:20.04 + Python 3.9 + Pandas library

Docker Container: Running instance of an image
- Like a running process
- Mutable (can be changed)
- Each container is isolated
- Example: Running Python script in container
```

#### **Docker Architecture**

```
┌─────────────────────────────────────┐
│      Docker Desktop (Mac/Windows)    │
│  or Docker Engine (Linux)            │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┐
       │                │
   Docker CLI      Docker Daemon
   (docker         (runs containers)
    command)
       │                │
       └───────┬────────┘
               │
       ┌───────┴──────────────┐
       │                      │
   Docker Registry       Local Storage
   (Docker Hub)          (Images, Volumes)
   (Public images)
```

---

## Docker Installation & Setup

### Install Docker

**Mac & Windows:**
1. Download Docker Desktop from https://www.docker.com/products/docker-desktop
2. Install and run
3. Verify: `docker --version`

**Linux (Ubuntu):**
```bash
sudo apt-get update
sudo apt-get install docker.io
sudo usermod -aG docker $USER  # Run docker without sudo
docker --version
```

### First Docker Command

```bash
# Download and run a simple container
docker run -it ubuntu:20.04

# What happens:
# 1. Docker checks if ubuntu:20.04 image exists locally
# 2. If not, downloads from Docker Hub
# 3. Creates a container from the image
# 4. Starts the container
# 5. Gives you a shell (-it = interactive terminal)
```

---

## Creating Your Own Docker Image

### Dockerfile Basics

A **Dockerfile** is a text file with instructions to build an image.

#### **Example 1: Simple Python Application**

```dockerfile
# Start from base image
FROM python:3.9-slim

# Set working directory in container
WORKDIR /app

# Copy files from your machine to container
COPY requirements.txt .
COPY app.py .

# Install dependencies
RUN pip install -r requirements.txt

# Expose port (documentation)
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run when container starts
CMD ["python", "app.py"]
```

#### **Example 2: Data Engineering Pipeline**

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Copy source code
COPY . .

# Install system dependencies (for databases, etc.)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    google-cloud-bigquery==3.11.0 \
    google-cloud-storage==2.10.0 \
    pandas==1.5.3 \
    apache-beam==2.47.0

# Copy entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Set environment
ENV PROJECT_ID=my-gcp-project
ENV PYTHONUNBUFFERED=1

# Run the pipeline
CMD ["python", "pipeline.py"]
```

### Building & Running Docker Images

```bash
# Build image (creates new image)
docker build -t my-pipeline:1.0 .
# -t = tag (name:version)
# . = look for Dockerfile in current directory

# List images
docker images

# Run container from image
docker run -d \
  --name my-pipeline-container \
  -e PROJECT_ID=my-project \
  -e DATASET=my_dataset \
  -v /home/data:/app/data \
  my-pipeline:1.0

# Flags:
# -d = detached (background)
# --name = container name
# -e = environment variable
# -v = volume mount (share files)

# Check running containers
docker ps

# View logs
docker logs my-pipeline-container

# Stop container
docker stop my-pipeline-container

# Remove container
docker rm my-pipeline-container

# Remove image
docker rmi my-pipeline:1.0
```

---

## Docker Best Practices

### 1. Use .dockerignore

Just like .gitignore, exclude unnecessary files:

```
.git
.gitignore
__pycache__
*.pyc
.pytest_cache
.venv
README.md
.DS_Store
```

### 2. Multi-Stage Builds (Reduce Image Size)

```dockerfile
# Stage 1: Build
FROM python:3.9 as builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime (smaller)
FROM python:3.9-slim

WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder /root/.local /root/.local
COPY app.py .

ENV PATH=/root/.local/bin:$PATH
CMD ["python", "app.py"]

# Result: Final image is much smaller!
# Builder stage discarded after Stage 2 starts
```

### 3. Layer Caching

```dockerfile
# BAD: Changes invalidate entire cache
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y curl git
COPY . /app
WORKDIR /app

# GOOD: Dependencies installed first (less frequent changes)
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y curl git  # Cached, reused
WORKDIR /app
COPY requirements.txt .  # Changes less often
RUN pip install -r requirements.txt
COPY . /app  # Your code changes frequently
```

### 4. Running as Non-Root User

```dockerfile
# Security: Don't run as root
FROM python:3.9-slim

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

# Switch to non-root user
USER appuser

CMD ["python", "app.py"]
```

---

## Docker Compose (Multiple Containers)

Docker Compose runs multiple containers that work together.

### Example: Data Pipeline with PostgreSQL

```yaml
# docker-compose.yml
version: '3.8'

services:
  # PostgreSQL database
  postgres:
    image: postgres:13
    container_name: pipeline-db
    environment:
      POSTGRES_USER: pipeline_user
      POSTGRES_PASSWORD: secure_password
      POSTGRES_DB: pipeline_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - pipeline_network

  # Data pipeline application
  pipeline:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: data-pipeline
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql://pipeline_user:secure_password@postgres:5432/pipeline_db
      GCP_PROJECT: my-project
      PYTHONUNBUFFERED: 1
    volumes:
      - ./data:/app/data
    networks:
      - pipeline_network

  # Redis cache
  redis:
    image: redis:7-alpine
    container_name: pipeline-cache
    ports:
      - "6379:6379"
    networks:
      - pipeline_network

volumes:
  postgres_data:

networks:
  pipeline_network:
    driver: bridge
```

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View running services
docker-compose ps

# View logs
docker-compose logs pipeline

# Follow logs in real-time
docker-compose logs -f pipeline

# Execute command in container
docker-compose exec pipeline python manage.py migrate

# Stop all services
docker-compose down

# Remove volumes (cleanup data)
docker-compose down -v
```

---

## Docker for Data Engineering

### Pushing to Docker Hub

```bash
# Login to Docker Hub
docker login

# Tag image with your username
docker tag my-pipeline:1.0 username/my-pipeline:1.0

# Push to Docker Hub
docker push username/my-pipeline:1.0

# Pull from Docker Hub
docker pull username/my-pipeline:1.0
```

### Example: Dataflow Pipeline in Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install beam and GCP libraries
RUN pip install --no-cache-dir \
    apache-beam[gcp]==2.47.0 \
    google-cloud-storage==2.10.0 \
    google-cloud-bigquery==3.11.0

# Copy pipeline code
COPY dataflow_pipeline.py .
COPY requirements.txt .

RUN pip install -r requirements.txt

# Run beam pipeline
CMD ["python", "-m", "apache_beam.examples.wordcount", \
     "--input", "gs://bucket/input/*.txt", \
     "--output", "gs://bucket/output/results", \
     "--runner", "DataflowRunner", \
     "--project", "my-project"]
```

---

# Kubernetes

## What is Kubernetes?

Kubernetes (K8s) is an **orchestration platform** that:
- Runs and manages Docker containers at scale
- Automatically deploys containers
- Scales them up/down based on demand
- Handles failures (restart dead containers)
- Manages networking between containers
- Handles storage

### Why Kubernetes?

**Problem it solves:**

```
Without K8s:
- 1 container on 1 server: Manual management OK
- 100 containers on 10 servers: Nightmare!
  * Which container on which server?
  * What if a server dies?
  * How to scale up when traffic increases?
  * How to do rolling updates without downtime?

With K8s:
- Automatic deployment
- Automatic scaling
- Automatic failure recovery
- Rolling updates (zero downtime)
- Load balancing
```

---

## Kubernetes Architecture

### Core Components

```
┌────────────────────────────────────────────────┐
│         Kubernetes Cluster                      │
│                                                 │
│  ┌─────────────────────────────────────┐       │
│  │   Control Plane (Master)            │       │
│  │                                     │       │
│  │  • API Server (control center)      │       │
│  │  • Scheduler (assigns pods)         │       │
│  │  • Controller Manager (runs logic)  │       │
│  │  • etcd (database)                  │       │
│  └─────────────────────────────────────┘       │
│                                                 │
│  ┌──────────┬──────────┬──────────────┐        │
│  │ Worker 1 │ Worker 2 │ Worker 3     │        │
│  │          │          │              │        │
│  │ ┌──────┐ │ ┌──────┐ │ ┌──────┐    │        │
│  │ │ Pod  │ │ │ Pod  │ │ │ Pod  │    │        │
│  │ │(Cont)│ │ │(Cont)│ │ │(Cont)│    │        │
│  │ └──────┘ │ └──────┘ │ └──────┘    │        │
│  │          │          │              │        │
│  └──────────┴──────────┴──────────────┘        │
│                                                 │
└────────────────────────────────────────────────┘
```

### Key Concepts

#### **1. Pod (Smallest deployable unit)**

A Pod is a wrapper around one or more containers (usually just one).

```yaml
# Simple pod definition
apiVersion: v1
kind: Pod
metadata:
  name: my-pipeline-pod
spec:
  containers:
  - name: pipeline
    image: username/my-pipeline:1.0
    resources:
      requests:
        memory: "128Mi"
        cpu: "100m"
      limits:
        memory: "256Mi"
        cpu: "500m"
    env:
    - name: PROJECT_ID
      value: "my-project"
```

#### **2. Deployment (Manage Pods)**

A Deployment ensures a specified number of pods are running.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-pipeline
spec:
  replicas: 3  # Run 3 copies of the pod
  selector:
    matchLabels:
      app: data-pipeline
  template:
    metadata:
      labels:
        app: data-pipeline
    spec:
      containers:
      - name: pipeline
        image: username/my-pipeline:1.0
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

#### **3. Service (Network Access)**

A Service exposes pods to the network.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: pipeline-service
spec:
  selector:
    app: data-pipeline
  type: LoadBalancer  # External IP access
  ports:
  - port: 80          # External port
    targetPort: 8080  # Pod port
```

#### **4. ConfigMap & Secrets**

ConfigMaps store configuration, Secrets store sensitive data.

```yaml
# ConfigMap (non-sensitive)
apiVersion: v1
kind: ConfigMap
metadata:
  name: pipeline-config
data:
  LOG_LEVEL: "INFO"
  BATCH_SIZE: "1000"

---

# Secret (sensitive, encoded)
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  username: cGlwZWxpbmVfdXNlcg==  # base64 encoded
  password: c2VjdXJlX3Bhc3N3b3Jk
```

---

## Setting Up Kubernetes

### Option 1: Local Kubernetes (Development)

```bash
# Install Docker Desktop or Minikube
# Docker Desktop: Enable Kubernetes in settings
# Minikube: brew install minikube && minikube start

# Verify kubectl installed
kubectl version --client

# Check cluster
kubectl cluster-info

# Get nodes
kubectl get nodes
```

### Option 2: Google Kubernetes Engine (GKE)

```bash
# Create GKE cluster
gcloud container clusters create my-cluster \
  --num-nodes=3 \
  --machine-type=n1-standard-2 \
  --zone=us-central1-a

# Get credentials
gcloud container clusters get-credentials my-cluster --zone=us-central1-a

# Verify
kubectl get nodes
```

---

## Kubernetes Commands

### Deployment Management

```bash
# Apply configuration file
kubectl apply -f deployment.yaml

# Check deployment status
kubectl get deployments

# Check pods
kubectl get pods

# Detailed pod info
kubectl describe pod my-pipeline-pod-xyz

# Scale deployment
kubectl scale deployment data-pipeline --replicas=5

# Update image
kubectl set image deployment/data-pipeline \
  pipeline=username/my-pipeline:2.0 --record

# Rollback to previous version
kubectl rollout undo deployment/data-pipeline

# View rollout history
kubectl rollout history deployment/data-pipeline

# Watch pod status
kubectl get pods -w
```

### Viewing Logs

```bash
# View pod logs
kubectl logs my-pipeline-pod-xyz

# Follow logs
kubectl logs -f my-pipeline-pod-xyz

# View logs from multiple pods
kubectl logs -f -l app=data-pipeline

# View logs of previous container (if crashed)
kubectl logs my-pipeline-pod-xyz --previous
```

### Debugging

```bash
# Execute command in pod
kubectl exec -it my-pipeline-pod-xyz -- /bin/bash

# Port forward (access pod locally)
kubectl port-forward my-pipeline-pod-xyz 8080:8080

# Get detailed info
kubectl describe pod my-pipeline-pod-xyz

# Check events
kubectl get events

# Check resource usage
kubectl top pods
```

### Cleanup

```bash
# Delete pod
kubectl delete pod my-pipeline-pod-xyz

# Delete deployment
kubectl delete deployment data-pipeline

# Delete all resources
kubectl delete -f deployment.yaml

# Delete namespace (and all resources in it)
kubectl delete namespace my-namespace
```

---

## Kubernetes for Data Pipelines

### Example: BigQuery Data Pipeline

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-pipeline
spec:
  schedule: "0 2 * * *"  # Run at 2 AM daily
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: pipeline
            image: username/data-pipeline:1.0
            env:
            - name: PROJECT_ID
              value: "my-gcp-project"
            - name: DATASET
              value: "analytics"
            resources:
              requests:
                memory: "2Gi"
                cpu: "2"
              limits:
                memory: "4Gi"
                cpu: "4"
            volumeMounts:
            - name: config
              mountPath: /etc/config
          volumes:
          - name: config
            configMap:
              name: pipeline-config
          restartPolicy: OnFailure
```

---

# Terraform

## What is Terraform?

Terraform is an **Infrastructure as Code (IaC)** tool that lets you define cloud resources in code instead of using web UI.

### Why Terraform?

**Traditional way:**
```
Click through AWS/GCP console:
1. Create VPC
2. Create subnet
3. Create security group
4. Create instance
5. Configure load balancer
6. ... 50 more clicks

Problems:
- Manual, error-prone
- Hard to reproduce
- Hard to modify
- Hard to version control
- Hard to automate
```

**Terraform way:**
```hcl
# main.tf
resource "google_compute_instance" "web" {
  name         = "web-server"
  machine_type = "n1-standard-1"
  zone         = "us-central1-a"
  
  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }
}

# Then just run: terraform apply
# Done!
```

---

## Terraform Basics

### Core Concepts

#### **1. Configuration Files (.tf)**

```hcl
# main.tf

# Configure the Google Cloud provider
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = "my-gcp-project"
  region  = "us-central1"
}

# Define a resource
resource "google_cloud_storage_bucket" "data_bucket" {
  name          = "my-data-bucket-unique-name"
  location      = "US"
  force_destroy = true

  uniform_bucket_level_access = true
}

# Define another resource
resource "google_bigquery_dataset" "analytics" {
  dataset_id = "analytics_dataset"
  location   = "US"

  access {
    role          = "OWNER"
    user_by_email = "user@company.com"
  }
}

# Output values
output "bucket_name" {
  value = google_cloud_storage_bucket.data_bucket.name
}
```

#### **2. Variables & Reusability**

```hcl
# variables.tf

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "my-project"
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "replica_count" {
  description = "Number of replicas"
  type        = number
  default     = 3
}

# Use variables
resource "google_compute_instance" "app" {
  name    = "${var.environment}-app-server"
  zone    = "${var.region}-a"
  
  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }
}
```

#### **3. Outputs**

```hcl
# outputs.tf

output "database_ip" {
  description = "IP address of database"
  value       = google_sql_database_instance.db.private_ip_address
  sensitive   = false
}

output "bucket_url" {
  description = "URL of storage bucket"
  value       = "gs://${google_cloud_storage_bucket.data.name}"
}

output "gke_cluster_name" {
  value = google_container_cluster.primary.name
}
```

#### **4. State File**

Terraform maintains a **state file** (terraform.tfstate) that tracks resources.

```
terraform.tfstate (local)
├─ Resource IDs
├─ Resource properties
├─ Dependencies
└─ Metadata

Better practice: Store in remote backend (GCS, S3, Terraform Cloud)
```

---

## Terraform Workflow

### Step 1: Initialize

```bash
# Initialize Terraform in a directory
terraform init

# Downloads providers (Google Cloud plugin, AWS plugin, etc.)
# Creates .terraform directory
# Creates terraform.lock.hcl (lock file for versions)
```

### Step 2: Plan

```bash
# See what changes will be made
terraform plan

# Output shows:
# + add
# - delete
# ~ modify

# Save plan to file for review
terraform plan -out=tfplan
```

### Step 3: Apply

```bash
# Apply the changes
terraform apply

# For production: Use saved plan
terraform apply tfplan

# Asks for confirmation before applying
# Creates resources in cloud
# Updates terraform.tfstate
```

### Step 4: Destroy

```bash
# Delete all resources
terraform destroy

# Destroy specific resource
terraform destroy -target=google_compute_instance.app
```

---

## Terraform Best Practices

### 1. Project Structure

```
terraform/
├── main.tf           # Main resources
├── variables.tf      # Input variables
├── outputs.tf        # Output values
├── backend.tf        # Remote state config
├── providers.tf      # Provider config
├── terraform.tfvars  # Variable values (don't commit!)
├── .gitignore        # Ignore sensitive files
│   ├── *.tfvars
│   ├── .terraform/
│   ├── .terraform.lock.hcl
│   └── terraform.tfstate*
│
└── modules/
    ├── bigquery/
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    └── gke/
        ├── main.tf
        ├── variables.tf
        └── outputs.tf
```

### 2. Modules (Reusable Blocks)

```hcl
# modules/bigquery/main.tf
variable "dataset_id" {
  type = string
}

variable "location" {
  type    = string
  default = "US"
}

resource "google_bigquery_dataset" "dataset" {
  dataset_id = var.dataset_id
  location   = var.location
}

output "dataset_id" {
  value = google_bigquery_dataset.dataset.dataset_id
}

# ============================================

# main.tf (use the module)
module "analytics_dataset" {
  source = "./modules/bigquery"
  
  dataset_id = "analytics"
  location   = "US"
}

module "events_dataset" {
  source = "./modules/bigquery"
  
  dataset_id = "events"
  location   = "US"
}
```

### 3. Remote State Storage

```hcl
# backend.tf
terraform {
  backend "gcs" {
    bucket = "my-terraform-state-bucket"
    prefix = "prod"
  }
}

# Advantages:
# - Team collaboration
# - Prevents conflicts
# - Secure (encrypted)
# - Versioned (track changes)
```

### 4. Multiple Environments

```
terraform/
├── environments/
│   ├── dev/
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   ├── staging/
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   └── prod/
│       ├── terraform.tfvars
│       └── backend.tf
└── modules/
    └── ... shared modules
```

```bash
# Deploy to dev
terraform -chdir=environments/dev init
terraform -chdir=environments/dev apply -var-file=terraform.tfvars

# Deploy to prod
terraform -chdir=environments/prod init
terraform -chdir=environments/prod apply -var-file=terraform.tfvars
```

### 5. Sensitive Data

```hcl
# DON'T do this:
variable "db_password" {
  type    = string
  default = "password123"  # EXPOSED!
}

# DO this instead:
variable "db_password" {
  type      = string
  sensitive = true  # Hides from output
}

# terraform.tfvars (add to .gitignore)
db_password = "secure-password-from-secret-manager"

# Or use secret manager
data "google_secret_manager_secret_version" "db_password" {
  secret  = "db-password"
  version = "latest"
}
```

---

## Complete Example: Data Engineering Infrastructure

```hcl
# main.tf

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
  
  backend "gcs" {
    bucket = "my-terraform-state"
    prefix = "data-platform"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# GCS Bucket for data lake
resource "google_cloud_storage_bucket" "data_lake" {
  name          = "${var.project_id}-data-lake"
  location      = "US"
  force_destroy = true

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age = 30
    }
  }
}

# BigQuery Dataset
resource "google_bigquery_dataset" "analytics" {
  dataset_id = "analytics"
  location   = "US"

  access {
    role          = "OWNER"
    user_by_email = var.owner_email
  }
}

# BigQuery Table
resource "google_bigquery_table" "events" {
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  table_id   = "events"

  schema = jsonencode([
    {
      name = "event_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "event_type"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "event_timestamp"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    },
    {
      name = "user_id"
      type = "STRING"
      mode = "NULLABLE"
    }
  ])

  time_partitioning {
    type = "DAY"
    field = "event_timestamp"
  }

  clustering = ["user_id", "event_type"]
}

# GKE Cluster
resource "google_container_cluster" "primary" {
  name     = "${var.environment}-cluster"
  location = var.region
  
  initial_node_count = var.node_count

  node_config {
    machine_type = "n2-standard-4"
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }

  deletion_protection = var.environment == "prod"
}

# Cloud Composer (Airflow)
resource "google_composer_environment" "data_pipeline" {
  name    = "${var.environment}-composer"
  region  = var.region
  
  config {
    node_count = 3
    
    node_config {
      machine_type = "n1-standard-4"
    }

    env_variables = {
      PROJECT_ID = var.project_id
      DATASET    = google_bigquery_dataset.analytics.dataset_id
    }
  }
}

# variables.tf
variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Must be dev, staging, or prod."
  }
}

variable "node_count" {
  type    = number
  default = 3
}

variable "owner_email" {
  type = string
}

# outputs.tf
output "data_lake_bucket" {
  value = google_cloud_storage_bucket.data_lake.name
}

output "bigquery_dataset" {
  value = google_bigquery_dataset.analytics.dataset_id
}

output "gke_cluster_name" {
  value = google_container_cluster.primary.name
}

output "composer_environment" {
  value = google_composer_environment.data_pipeline.name
}
```

---

# GitHub Actions

## What is GitHub Actions?

GitHub Actions is a **CI/CD (Continuous Integration/Continuous Deployment)** platform built into GitHub that automatically runs code when events happen (push, pull request, schedule, etc.).

### Why GitHub Actions?

**Before:**
```
Manually running tests, deploying code
1. Write code
2. Push to GitHub
3. Manually run tests locally
4. If good, manually deploy to production
5. Hope nothing breaks!

Problems:
- Error-prone
- Takes time
- Inconsistent
- No audit trail
```

**With GitHub Actions:**
```
Automated workflow
1. Write code
2. Push to GitHub
3. Automatically runs tests
4. Automatically builds Docker image
5. Automatically deploys to production
6. Notifies on failure

Benefits:
- Fast feedback
- Consistent
- No manual errors
- Full audit trail
```

---

## GitHub Actions Concepts

### 1. Workflows

A workflow is a YAML file that defines what to do.

```yaml
# .github/workflows/test.yml
name: Test & Deploy

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest
    
    - name: Run tests
      run: pytest tests/
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### 2. Events (What Triggers Workflows)

```yaml
on:
  push:                    # On push to any branch
    branches: [main]       # Only main branch
    paths:
      - 'src/**'           # Only when src/ changes
      - 'requirements.txt'
  
  pull_request:            # On pull request
    types: [opened, synchronize, reopened]
  
  schedule:                # On schedule (cron)
    - cron: '0 2 * * *'   # Daily at 2 AM UTC
  
  workflow_dispatch:       # Manual trigger from GitHub UI
  
  release:                 # On release
    types: [published]
```

### 3. Jobs & Steps

```yaml
jobs:
  test:                    # Job 1: Test
    runs-on: ubuntu-latest # Which OS to run on
    steps:                 # Sequential steps
    - name: Checkout
      uses: actions/checkout@v3
    
    - name: Run tests
      run: pytest tests/
  
  deploy:                  # Job 2: Deploy
    needs: test            # Only run if test succeeds
    runs-on: ubuntu-latest
    steps:
    - name: Deploy
      run: |
        echo "Deploying..."
        # Deployment commands
```

### 4. Secrets (Sensitive Data)

```yaml
# In workflow file
steps:
- name: Deploy to GCP
  env:
    GCP_PROJECT: ${{ secrets.GCP_PROJECT }}
    GCP_KEY: ${{ secrets.GCP_KEY }}
  run: |
    gcloud auth activate-service-account --key-file=$GCP_KEY
    gcloud config set project $GCP_PROJECT
```

Store secrets in GitHub:
1. Go to repo settings
2. Secrets and variables → Actions
3. Add new secret (e.g., GCP_KEY, DATABASE_PASSWORD)

---

## Complete GitHub Actions Example for Data Pipeline

```yaml
# .github/workflows/data-pipeline.yml

name: Data Pipeline CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/data-pipeline

jobs:
  # Job 1: Test
  test:
    name: Test
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
        cache: 'pip'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run unit tests
      run: pytest tests/ --cov=pipeline --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml
    
    - name: Run linting
      run: |
        pip install flake8
        flake8 pipeline/ --count --select=E9,F63,F7,F82 --show-source --statistics
  
  # Job 2: Build Docker image
  build:
    name: Build Docker Image
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=semver,pattern={{version}}
          type=sha
    
    - name: Build and push
      uses: docker/build-push-action@v4
      with:
        context: .
        push: ${{ github.event_name != 'pull_request' }}
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
  
  # Job 3: Deploy to GKE (only on main branch)
  deploy:
    name: Deploy to GKE
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up Cloud SDK
      uses: google-github-actions/setup-gcloud@v1
      with:
        service_account_key: ${{ secrets.GCP_SERVICE_ACCOUNT_KEY }}
        project_id: ${{ secrets.GCP_PROJECT_ID }}
    
    - name: Configure kubectl
      run: |
        gcloud container clusters get-credentials production-cluster \
          --zone us-central1-a \
          --project ${{ secrets.GCP_PROJECT_ID }}
    
    - name: Deploy to GKE
      run: |
        kubectl set image deployment/data-pipeline \
          data-pipeline=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
          --record
        kubectl rollout status deployment/data-pipeline
    
    - name: Notify Slack on success
      if: success()
      uses: slackapi/slack-github-action@v1.24.0
      with:
        webhook-url: ${{ secrets.SLACK_WEBHOOK }}
        payload: |
          {
            "text": "✅ Data Pipeline deployed successfully!"
          }
    
    - name: Notify Slack on failure
      if: failure()
      uses: slackapi/slack-github-action@v1.24.0
      with:
        webhook-url: ${{ secrets.SLACK_WEBHOOK }}
        payload: |
          {
            "text": "❌ Data Pipeline deployment failed!"
          }
```

### Running This Workflow

```bash
# When you push to main:
1. Tests run automatically
2. If tests pass, Docker image is built
3. If on main branch, deployment runs
4. Slack notification sent

# In GitHub Actions UI:
- See real-time logs
- Download artifacts
- Retry failed jobs
- Cancel running jobs
```

---

# Jenkins

## What is Jenkins?

Jenkins is an **open-source automation server** that runs jobs (scripts) on triggers.

### Jenkins vs GitHub Actions

| Feature | Jenkins | GitHub Actions |
|---------|---------|----------------|
| Where it runs | Your server | GitHub's servers |
| Setup | Self-hosted (complex) | Built-in GitHub |
| Cost | Free but infrastructure | Free (with limits) |
| Plugins | Massive ecosystem | Growing |
| Best for | On-premise | Cloud-native |

---

## Jenkins Basics

### Installation

```bash
# Mac
brew install jenkins-lts

# Linux
wget -q -O - https://pkg.jenkins.io/debian-stable/jenkins.io.key | sudo apt-key add -
sudo sh -c 'echo deb https://pkg.jenkins.io/debian-stable binary/ > /etc/apt/sources.list.d/jenkins.list'
sudo apt-get update && sudo apt-get install jenkins

# Start Jenkins
sudo systemctl start jenkins

# Access at http://localhost:8080
```

### Jenkins Web UI

```
1. Go to http://localhost:8080
2. Unlock Jenkins (get password from /var/lib/jenkins/secrets/initialAdminPassword)
3. Install plugins
4. Create admin user
5. Create your first job
```

---

## Jenkins Job Configuration

### Job Type 1: Freestyle Job (Simple)

```
New Item → Freestyle job → Configure

Build Triggers:
  ☑ GitHub hook trigger for GITScm polling
  ☑ Poll SCM: H H * * * (daily)

Source Code Management:
  Git: https://github.com/username/repo.git
  Credentials: (set up GitHub credentials)
  Branch: */main

Build Steps:
  Execute shell:
    #!/bin/bash
    set -e  # Exit on error
    
    # Install dependencies
    pip install -r requirements.txt
    
    # Run tests
    pytest tests/
    
    # Build Docker image
    docker build -t my-pipeline:latest .
    
    # Push to registry
    docker push my-pipeline:latest

Post-build Actions:
  E-mail Notification:
    Recipients: team@company.com
    Send email for: Every unstable build, Failed build
```

### Job Type 2: Pipeline Job (Advanced)

```groovy
// Jenkinsfile (stored in repo)

pipeline {
    agent any
    
    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 1, unit: 'HOURS')
    }
    
    parameters {
        string(name: 'ENVIRONMENT', defaultValue: 'dev', description: 'Deployment environment')
        booleanParam(name: 'DEPLOY', defaultValue: false, description: 'Deploy to production?')
    }
    
    environment {
        REGISTRY = 'docker.io'
        IMAGE_NAME = 'my-pipeline'
        GCP_PROJECT = credentials('gcp-project-id')
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Test') {
            steps {
                script {
                    sh '''
                        pip install -r requirements.txt
                        pytest tests/ --junitxml=results.xml
                    '''
                }
            }
            post {
                always {
                    junit 'results.xml'
                }
            }
        }
        
        stage('Build') {
            steps {
                script {
                    sh '''
                        docker build -t ${REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER} .
                        docker tag ${REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER} ${REGISTRY}/${IMAGE_NAME}:latest
                    '''
                }
            }
        }
        
        stage('Push') {
            when {
                branch 'main'
            }
            steps {
                script {
                    withCredentials([usernamePassword(credentialsId: 'docker-credentials', 
                                    usernameVariable: 'DOCKER_USER', 
                                    passwordVariable: 'DOCKER_PASS')]) {
                        sh '''
                            echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin
                            docker push ${REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER}
                            docker push ${REGISTRY}/${IMAGE_NAME}:latest
                        '''
                    }
                }
            }
        }
        
        stage('Deploy') {
            when {
                allOf {
                    branch 'main'
                    expression { params.DEPLOY == true }
                }
            }
            steps {
                script {
                    withCredentials([file(credentialsId: 'gcp-key', variable: 'GCP_KEY_FILE')]) {
                        sh '''
                            gcloud auth activate-service-account --key-file=$GCP_KEY_FILE
                            gcloud config set project ${GCP_PROJECT}
                            
                            kubectl set image deployment/data-pipeline \
                                data-pipeline=${REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER} \
                                --record
                            
                            kubectl rollout status deployment/data-pipeline
                        '''
                    }
                }
            }
        }
    }
    
    post {
        always {
            // Cleanup
            cleanWs()
        }
        success {
            // Notify on success
            emailext(
                subject: "Jenkins Build ${BUILD_NUMBER}: SUCCESS",
                body: "Build ${BUILD_NUMBER} succeeded!",
                to: 'team@company.com'
            )
        }
        failure {
            // Notify on failure
            emailext(
                subject: "Jenkins Build ${BUILD_NUMBER}: FAILED",
                body: "Build ${BUILD_NUMBER} failed! Check logs at ${BUILD_URL}",
                to: 'team@company.com'
            )
        }
    }
}
```

### Running Jenkins Pipeline

```bash
# In your GitHub repo, create Jenkinsfile at root
# In Jenkins, create "Pipeline" job
# Point it to your GitHub repo
# Specify path to Jenkinsfile

# Now Jenkins automatically runs Jenkinsfile on every commit!
```

---

# Integration Examples

## Example 1: Complete Data Pipeline Flow

```
┌─────────────┐
│ Code pushed │
└──────┬──────┘
       │
       ├──→ GitHub Actions
       │    - Runs tests
       │    - Builds Docker image
       │    - Pushes to registry
       │
       ├──→ Terraform
       │    - Updates infrastructure
       │    - Creates BigQuery tables
       │    - Manages GKE cluster
       │
       └──→ Kubernetes
            - Deploys new container
            - Scales if needed
            - Updates service
            - Monitors health
```

### Workflow File

```yaml
# .github/workflows/deploy.yml

name: Deploy Data Pipeline

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pytest tests/
  
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: docker/build-push-action@v4
        with:
          push: true
          tags: gcr.io/${{ secrets.GCP_PROJECT }}/data-pipeline:${{ github.sha }}
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy with Terraform
        run: |
          terraform init
          terraform plan
          terraform apply -auto-approve
        env:
          GOOGLE_CREDENTIALS: ${{ secrets.GCP_KEY }}
      
      - name: Deploy to Kubernetes
        run: |
          gcloud auth activate-service-account --key-file=$GCP_KEY
          gcloud container clusters get-credentials prod-cluster
          
          kubectl set image deployment/data-pipeline \
            pipeline=gcr.io/${{ secrets.GCP_PROJECT }}/data-pipeline:${{ github.sha }}
        env:
          GCP_KEY: ${{ secrets.GCP_KEY }}
```

---

## Example 2: Jenkins + Kubernetes

```groovy
// Jenkinsfile for deploying to Kubernetes

pipeline {
    agent any
    
    environment {
        DOCKER_REGISTRY = 'gcr.io'
        GCP_PROJECT = 'my-gcp-project'
        IMAGE_NAME = "${DOCKER_REGISTRY}/${GCP_PROJECT}/data-pipeline"
    }
    
    stages {
        stage('Build Docker Image') {
            steps {
                script {
                    sh 'docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} .'
                }
            }
        }
        
        stage('Push to Registry') {
            steps {
                script {
                    sh '''
                        docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_NAME}:latest
                        gcloud auth configure-docker
                        docker push ${IMAGE_NAME}:${BUILD_NUMBER}
                        docker push ${IMAGE_NAME}:latest
                    '''
                }
            }
        }
        
        stage('Update Kubernetes') {
            steps {
                script {
                    sh '''
                        gcloud container clusters get-credentials prod-cluster --zone us-central1-a
                        
                        # Update deployment with new image
                        kubectl set image deployment/data-pipeline \
                            data-pipeline=${IMAGE_NAME}:${BUILD_NUMBER} \
                            --record
                        
                        # Wait for rollout
                        kubectl rollout status deployment/data-pipeline
                    '''
                }
            }
        }
    }
}
```

---

# Interview Preparation

## Key Concepts to Know

### Docker
```
☐ What is a container vs image
☐ How Dockerfile works
☐ Docker commands (build, run, push, pull)
☐ Docker Compose for multi-container
☐ Best practices (layer caching, small images)
```

### Kubernetes
```
☐ Pod, Deployment, Service concepts
☐ kubectl commands
☐ ConfigMap vs Secret
☐ Rolling updates
☐ Resource requests/limits
```

### Terraform
```
☐ Infrastructure as Code concept
☐ Configuration files (.tf)
☐ Variables, outputs, modules
☐ State file (local vs remote)
☐ Plan vs Apply workflow
```

### GitHub Actions
```
☐ Workflows, jobs, steps
☐ Triggers (push, pull_request, schedule)
☐ Secrets for sensitive data
☐ Matrix builds (test on multiple versions)
☐ Artifacts and caching
```

### Jenkins
```
☐ Freestyle vs Pipeline jobs
☐ Jenkinsfile in repo
☐ Credentials management
☐ Build triggers
☐ Post-build actions
```

---

## Interview Questions & Answers

**Q: Explain Docker vs Kubernetes**
```
A: Docker is containerization (package app with dependencies)
   Kubernetes is orchestration (manage many containers at scale)
   
   Docker: "Build once, run anywhere"
   Kubernetes: "Run many containers reliably"
```

**Q: When would you use Terraform?**
```
A: When you have infrastructure to manage:
   - Multiple environments (dev, staging, prod)
   - Need to version control infrastructure
   - Want to automate setup
   - Team collaboration on infrastructure
```

**Q: GitHub Actions vs Jenkins?**
```
A: GitHub Actions:
   - Best for cloud-native teams
   - Less setup (built into GitHub)
   - Good for small-medium scale
   
   Jenkins:
   - Best for on-premise
   - More flexibility
   - Larger plugin ecosystem
   - More setup required
```

**Q: Describe a deployment pipeline**
```
A: 
1. Developer pushes code
2. CI/CD (GitHub Actions/Jenkins) runs:
   - Tests
   - Builds Docker image
   - Pushes to registry
3. Terraform updates infrastructure if needed
4. Kubernetes deploys new container
5. Health checks verify deployment
6. Notify team of success/failure
```

---

## Hands-On Practice

### Practice 1: Docker

```bash
# Create simple Python app
# Write Dockerfile
# Build image: docker build -t my-app:1.0 .
# Run: docker run my-app:1.0
# Push to Docker Hub
```

### Practice 2: Kubernetes

```bash
# Create local k8s cluster (Minikube or Docker Desktop)
# Write deployment.yaml
# Deploy: kubectl apply -f deployment.yaml
# Check: kubectl get pods
# Scale: kubectl scale deployment --replicas=3
```

### Practice 3: Terraform

```bash
# Create simple GCP resources
# Write main.tf, variables.tf, outputs.tf
# terraform init
# terraform plan
# terraform apply
# terraform destroy
```

### Practice 4: GitHub Actions

```bash
# Create .github/workflows/test.yml
# Push to GitHub
# Watch it run automatically
# Modify and iterate
```

### Practice 5: Jenkins

```bash
# Install Jenkins locally
# Create Jenkinsfile
# Create pipeline job pointing to repo
# Trigger build and watch logs
```

