# Terraform Advanced Guide: Modules, Patterns & Production

## Table of Contents
1. [Modules in Depth](#modules)
2. [Advanced Patterns](#patterns)
3. [Real-World Use Cases](#usecases)
4. [CI/CD Integration](#cicd)
5. [Multi-Cloud](#multicloud)
6. [Troubleshooting](#troubleshooting)
7. [Interview Scenarios](#scenarios)

---

## Modules in Depth

### What is a Module?

A **module** is a reusable container for multiple resources. It's like a function in programming.

```
Without modules (Bad):
├─ main.tf (500 lines - hard to maintain)

With modules (Good):
├─ modules/
│  ├─ vpc/       (VPC, subnets, routes)
│  ├─ security/  (Security groups)
│  ├─ compute/   (EC2, ASG)
│  └─ database/  (RDS, backups)
└─ main.tf (50 lines - orchestrates modules)
```

### Creating a Module

```hcl
# modules/vpc/variables.tf
variable "cidr_block" {
  type        = string
  description = "VPC CIDR block"
  default     = "10.0.0.0/16"
}

variable "enable_dns" {
  type        = bool
  description = "Enable DNS"
  default     = true
}

variable "tags" {
  type = map(string)
  default = {}
}

# modules/vpc/main.tf
resource "aws_vpc" "main" {
  cidr_block           = var.cidr_block
  enable_dns_hostnames = var.enable_dns

  tags = merge(var.tags, { Name = "vpc" })
}

resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.cidr_block, 2, 0)
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = merge(var.tags, { Name = "public-subnet" })
}

# modules/vpc/outputs.tf
output "vpc_id" {
  value = aws_vpc.main.id
}

output "subnet_id" {
  value = aws_subnet.public.id
}

# modules/vpc/data.tf
data "aws_availability_zones" "available" {
  state = "available"
}
```

### Using Modules

```hcl
# main.tf (root module)
module "vpc" {
  source = "./modules/vpc"
  
  cidr_block = "10.0.0.0/16"
  enable_dns = true
  tags = {
    Environment = "production"
    Team        = "DataEngineering"
  }
}

module "security_group" {
  source = "./modules/security"
  
  vpc_id = module.vpc.vpc_id
  app_port = 8080
}

module "compute" {
  source = "./modules/compute"
  
  subnet_id           = module.vpc.subnet_id
  security_group_id   = module.security_group.id
  instance_count      = 3
  instance_type       = "t3.medium"
}
```

### Module Locals & Meta-arguments

```hcl
# modules/vpc/main.tf
locals {
  # Compute derived values
  public_subnet_cidr = cidrsubnet(var.cidr_block, 2, 0)
  private_subnet_cidr = cidrsubnet(var.cidr_block, 2, 1)
  
  # Common tags
  common_tags = {
    Module      = "vpc"
    Environment = var.environment
    CreatedAt   = timestamp()
  }
}

# Meta-arguments (apply to all resources in module)
terraform {
  # Require minimum version
  required_version = ">= 1.0"
}

# Prevent accidental deletion
lifecycle {
  prevent_destroy = true
}

# Count: Create multiple instances
resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.cidr_block, 2, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]
}

# For-each: Better for scaling
variable "subnets" {
  type = map(string)
  default = {
    public1  = "10.0.1.0/24"
    public2  = "10.0.2.0/24"
    private1 = "10.0.11.0/24"
  }
}

resource "aws_subnet" "example" {
  for_each          = var.subnets
  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value
  availability_zone = data.aws_availability_zones.available.names[0]
}
```

---

## Advanced Patterns

### Pattern 1: Workspace-Based Deployments

```hcl
# main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "my-terraform-state"
    key    = "terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.region
}

# Variables based on workspace
variable "instance_types" {
  type = map(string)
  default = {
    dev     = "t2.micro"
    staging = "t3.small"
    prod    = "t3.large"
  }
}

variable "instance_counts" {
  type = map(number)
  default = {
    dev     = 1
    staging = 2
    prod    = 5
  }
}

locals {
  workspace = terraform.workspace
  instance_type = var.instance_types[local.workspace]
  instance_count = var.instance_counts[local.workspace]
}

resource "aws_instance" "app" {
  count         = local.instance_count
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = local.instance_type
  
  tags = {
    Environment = local.workspace
    Name        = "${local.workspace}-app-${count.index + 1}"
  }
}

# Usage:
# terraform workspace new dev
# terraform workspace new staging
# terraform workspace new prod
# 
# terraform workspace select prod
# terraform apply
```

### Pattern 2: Data-Driven Configuration

```hcl
# environment.tfvars (config file)
environment = "production"
region      = "us-east-1"

instances = {
  web1 = {
    instance_type = "t3.medium"
    az           = "us-east-1a"
    cpu_limit    = "70"
  }
  web2 = {
    instance_type = "t3.medium"
    az           = "us-east-1b"
    cpu_limit    = "70"
  }
  api1 = {
    instance_type = "t3.large"
    az           = "us-east-1a"
    cpu_limit    = "80"
  }
}

# main.tf
variable "instances" {
  type = map(object({
    instance_type = string
    az           = string
    cpu_limit    = string
  }))
}

resource "aws_instance" "app" {
  for_each          = var.instances
  ami               = "ami-0c55b159cbfafe1f0"
  instance_type     = each.value.instance_type
  availability_zone = each.value.az
  
  monitoring = true
  
  tags = {
    Name     = each.key
    CpuLimit = each.value.cpu_limit
  }
}

# Auto-scaling based on config
resource "aws_autoscaling_group" "app" {
  name            = "app-asg"
  desired_capacity = length(var.instances)
  min_size        = length(var.instances)
  max_size        = length(var.instances) * 2
}
```

### Pattern 3: Dynamic Blocks

```hcl
# Create security group with rules from list
variable "security_rules" {
  type = list(object({
    from_port = number
    to_port   = number
    protocol  = string
    cidr      = string
  }))
  default = [
    {
      from_port = 80
      to_port   = 80
      protocol  = "tcp"
      cidr      = "0.0.0.0/0"
    },
    {
      from_port = 443
      to_port   = 443
      protocol  = "tcp"
      cidr      = "0.0.0.0/0"
    }
  ]
}

resource "aws_security_group" "web" {
  name = "web-sg"
  
  dynamic "ingress" {
    for_each = var.security_rules
    content {
      from_port   = ingress.value.from_port
      to_port     = ingress.value.to_port
      protocol    = ingress.value.protocol
      cidr_blocks = [ingress.value.cidr]
    }
  }
  
  dynamic "egress" {
    for_each = var.security_rules
    content {
      from_port   = egress.value.from_port
      to_port     = egress.value.to_port
      protocol    = egress.value.protocol
      cidr_blocks = [egress.value.cidr]
    }
  }
}
```

### Pattern 4: Conditional Logic

```hcl
variable "enable_rds" {
  type    = bool
  default = false
}

variable "enable_autoscaling" {
  type    = bool
  default = true
}

variable "environment" {
  type    = string
  default = "dev"
}

# Create RDS only if enabled
resource "aws_db_instance" "main" {
  count             = var.enable_rds ? 1 : 0
  allocated_storage = 20
  engine            = "postgres"
  # ... other config
}

# Create ASG only if enabled
resource "aws_autoscaling_group" "app" {
  count           = var.enable_autoscaling ? 1 : 0
  desired_capacity = var.environment == "prod" ? 3 : 1
  # ... other config
}

# Reference optional resource
output "rds_endpoint" {
  value       = var.enable_rds ? aws_db_instance.main[0].endpoint : "N/A"
  description = "RDS endpoint if enabled"
}
```

---

## Real-World Use Cases

### Use Case 1: Multi-Tier Application Architecture

```hcl
# Directory structure
infrastructure/
├─ modules/
│  ├─ networking/
│  ├─ security/
│  ├─ compute/
│  └─ database/
├─ environments/
│  ├─ dev/
│  ├─ staging/
│  └─ prod/
└─ global/
   └─ iam.tf

# environments/prod/main.tf
module "networking" {
  source = "../../modules/networking"
  
  cidr_block = "10.0.0.0/16"
  region     = "us-east-1"
  environment = "prod"
}

module "security" {
  source = "../../modules/security"
  
  vpc_id      = module.networking.vpc_id
  environment = "prod"
}

module "compute" {
  source = "../../modules/compute"
  
  vpc_id              = module.networking.vpc_id
  subnet_id           = module.networking.public_subnet_id
  security_group_id   = module.security.web_sg_id
  instance_count      = 5
  instance_type       = "t3.large"
  environment         = "prod"
}

module "database" {
  source = "../../modules/database"
  
  vpc_id              = module.networking.vpc_id
  private_subnet_ids  = module.networking.private_subnet_ids
  db_name             = "appdb"
  db_engine           = "postgres"
  backup_retention    = 30
  environment         = "prod"
}

output "app_load_balancer_dns" {
  value = module.compute.load_balancer_dns
}

output "database_endpoint" {
  value     = module.database.endpoint
  sensitive = true
}
```

### Use Case 2: Data Pipeline Infrastructure (CDM Next style)

```hcl
# modules/data_pipeline/main.tf
variable "project_id" {
  type = string
}

variable "dataset_name" {
  type = string
}

variable "pipeline_config" {
  type = object({
    composer_machine_type = string
    dataflow_workers      = number
    enable_dlp           = bool
    enable_encryption    = bool
  })
}

# Create GCS buckets
resource "google_storage_bucket" "quarantine" {
  project  = var.project_id
  name     = "${var.project_id}-quarantine"
  location = "US"
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 90  # Auto-delete after 90 days
    }
  }
}

resource "google_storage_bucket" "application" {
  project  = var.project_id
  name     = "${var.project_id}-app"
  location = "US"
}

# Create BigQuery datasets
resource "google_bigquery_dataset" "quarantine" {
  project    = var.project_id
  dataset_id = "${var.dataset_name}_quarantine"
  
  access {
    role          = "OWNER"
    user_by_email = google_service_account.terraform.email
  }
}

resource "google_bigquery_dataset" "application" {
  project    = var.project_id
  dataset_id = "${var.dataset_name}_application"
  
  access {
    role          = "EDITOR"
    user_by_email = google_service_account.app.email
  }
}

# Create Cloud Composer (Airflow)
resource "google_composer_environment" "data_pipeline" {
  name   = "cdm-next-composer"
  region = "us-central1"
  
  config {
    node_count = var.pipeline_config.composer_machine_type == "large" ? 3 : 1
    
    node_config {
      machine_type = var.pipeline_config.composer_machine_type
    }
    
    software_config {
      image_version = "composer-2-airflow-2"
      python_version = "3"
    }
  }
}

# Create Dataflow template
resource "google_dataflow_job" "etl" {
  name              = "cdm-next-etl"
  template_gcs_path = "gs://dataflow-templates/latest/templates/Kafka_to_BigQuery"
  temp_gcs_location = google_storage_bucket.quarantine.url
  
  parameters = {
    inputTopic = google_pubsub_topic.data_events.id
    outputTable = "${var.project_id}:${google_bigquery_dataset.quarantine.dataset_id}.raw_events"
  }
}

# Enable DLP if configured
resource "google_data_loss_prevention_deidentify_template" "pii_detection" {
  count        = var.pipeline_config.enable_dlp ? 1 : 0
  parent       = "projects/${var.project_id}"
  display_name = "cdm-dlp-template"
  
  deidentify_config {
    info_type_transformations {
      transformations {
        info_types {
          name = "EMAIL_ADDRESS"
        }
        primitive_transformation {
          redact_config {}
        }
      }
    }
  }
}

# Outputs
output "quarantine_bucket" {
  value = google_storage_bucket.quarantine.name
}

output "app_bucket" {
  value = google_storage_bucket.application.name
}

output "composer_environment" {
  value = google_composer_environment.data_pipeline.name
}

output "quarantine_dataset" {
  value = google_bigquery_dataset.quarantine.dataset_id
}

output "application_dataset" {
  value = google_bigquery_dataset.application.dataset_id
}
```

---

## CI/CD Integration

### GitHub Actions + Terraform

```yaml
# .github/workflows/terraform.yml
name: Terraform

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  AWS_REGION: us-east-1
  TERRAFORM_VERSION: 1.5.0

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: ${{ env.TERRAFORM_VERSION }}
      
      - name: Terraform Format
        run: terraform fmt -check -recursive
      
      - name: Terraform Init
        run: terraform init -backend=false
      
      - name: Terraform Validate
        run: terraform validate

  plan:
    runs-on: ubuntu-latest
    needs: validate
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v3
      
      - uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: ${{ env.TERRAFORM_VERSION }}
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Terraform Init
        run: terraform init
      
      - name: Terraform Plan
        run: terraform plan -out=tfplan
      
      - name: Upload Plan
        uses: actions/upload-artifact@v3
        with:
          name: tfplan
          path: tfplan
      
      - name: Comment PR
        uses: terraform-linters/tflint-load-config-action@v3
        with:
          format: github-comment

  apply:
    runs-on: ubuntu-latest
    needs: validate
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    steps:
      - uses: actions/checkout@v3
      
      - uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: ${{ env.TERRAFORM_VERSION }}
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Terraform Init
        run: terraform init
      
      - name: Terraform Apply
        run: terraform apply -auto-approve
```

### GitLab CI + Terraform

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - plan
  - apply

variables:
  TERRAFORM_VERSION: 1.5.0
  TF_ROOT: ${CI_PROJECT_DIR}

.terraform_base:
  image: hashicorp/terraform:${TERRAFORM_VERSION}
  before_script:
    - cd ${TF_ROOT}

validate:
  extends: .terraform_base
  stage: validate
  script:
    - terraform fmt -check -recursive
    - terraform init -backend=false
    - terraform validate

plan:
  extends: .terraform_base
  stage: plan
  script:
    - terraform init
    - terraform plan -out=tfplan
  artifacts:
    paths:
      - ${TF_ROOT}/tfplan
    expire_in: 7 days
  only:
    - merge_requests

apply:
  extends: .terraform_base
  stage: apply
  script:
    - terraform init
    - terraform apply -input=false tfplan
  when: manual
  only:
    - main
```

---

## Multi-Cloud

### AWS + GCP Example

```hcl
# Configure both providers
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

# AWS resources
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.medium"
  
  tags = {
    Name = "web-server"
  }
}

# GCP resources
resource "google_compute_instance" "app" {
  name         = "app-server"
  machine_type = "e2-medium"
  zone         = "us-central1-a"
  
  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }
}

# Cross-cloud: AWS -> GCP communication
resource "aws_security_group_rule" "allow_gcp" {
  type              = "ingress"
  from_port         = 8080
  to_port           = 8080
  protocol          = "tcp"
  cidr_blocks       = [var.gcp_app_ip]  # GCP app's IP
  security_group_id = aws_security_group.web.id
}
```

---

## Troubleshooting

### Common Issues & Solutions

```
Issue 1: "Error: Error acquiring the state lock"

Cause: Someone else is running terraform apply
Solution: Wait for them to finish, or:
$ terraform force-unlock LOCK_ID

Issue 2: "Error: resource already exists in state"

Cause: Resource created outside Terraform (manual creation)
Solution:
$ terraform import aws_instance.web i-0c5b159cbfafe1f0
# Now Terraform manages it

Issue 3: "Error: resource doesn't exist"

Cause: Someone deleted resource manually
Solution:
$ terraform refresh
# Update state to match actual infrastructure

Issue 4: "Plan shows changes but code unchanged"

Cause: Drift (manual changes in console)
Solution:
$ terraform apply -refresh-only
# Update state without changing resources

Issue 5: "Cannot destroy - resource in use"

Cause: Dependency blocks destruction
Solution:
# Option 1: Remove dependency manually
# Option 2: Use depends_on to override
# Option 3: terraform destroy -target=resource_name
```

### Debugging Commands

```bash
# Enable debug logging
$ TF_LOG=DEBUG terraform apply

# Show variables being used
$ terraform console
> var.instance_type
"t3.medium"

# Inspect resource details
$ terraform state show aws_instance.web

# Compare state with actual
$ terraform refresh

# Get graph of dependencies
$ terraform graph | dot -Tpng > graph.png

# Show which workspace you're in
$ terraform workspace show

# List all resources
$ terraform state list

# Validate JSON outputs
$ terraform output -json | jq
```

---

## Interview Scenarios

### Scenario 1: Production Deployment

**Question:** "Walk through how you would deploy a production infrastructure using Terraform."

**Answer:**
1. **Code & Version Control**
   - Write .tf files in Git repository
   - Create main, dev, staging, prod branches
   - Use pull requests for code review

2. **State Management**
   - Remote backend (S3 with encryption)
   - State locking (DynamoDB)
   - Separate state per environment

3. **Environments**
   - Separate directories: environments/dev, environments/prod
   - Different tfvars files per environment
   - Different AWS accounts for isolation

4. **CI/CD Pipeline**
   - PR: terraform plan (shows changes)
   - Merge to main: Auto-deploy via GitHub Actions
   - Manual approval for prod changes

5. **Deployment Flow**
   ```
   $ git pull
   $ terraform init
   $ terraform plan -var-file="prod/terraform.tfvars"
   # Review plan carefully
   $ terraform apply -var-file="prod/terraform.tfvars"
   $ terraform output
   # Verify deployment
   ```

---

### Scenario 2: Scaling Application

**Question:** "Your application is growing. How would you use Terraform to scale?"

**Answer:**

**Current state:**
```hcl
resource "aws_instance" "app" {
  count         = 1
  instance_type = "t2.micro"
}
```

**To scale:**
```hcl
variable "desired_capacity" {
  type    = number
  default = 5
}

resource "aws_autoscaling_group" "app" {
  min_size            = var.desired_capacity
  max_size            = var.desired_capacity * 2
  desired_capacity    = var.desired_capacity
  availability_zones  = var.availability_zones
  
  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }
}

# Scale up:
terraform apply -var="desired_capacity=10"

# Scale down:
terraform apply -var="desired_capacity=3"
```

---

### Scenario 3: Disaster Recovery

**Question:** "Your AWS region fails. How do you recover using Terraform?"

**Answer:**

**Before disaster:** Replicate infrastructure to another region
```hcl
locals {
  primary_region = "us-east-1"
  dr_region      = "us-west-2"
}

# Primary infrastructure
resource "aws_instance" "primary" {
  provider      = aws.primary
  instance_type = "t3.medium"
}

# DR infrastructure (identical)
resource "aws_instance" "dr" {
  provider      = aws.dr
  instance_type = "t3.medium"
}
```

**After disaster:** Failover to DR region
```bash
# Update DNS to point to DR region
$ terraform apply -target=aws_route53_record.failover

# If primary is completely gone:
# 1. Copy state from backup
# 2. Promote DR to primary
# 3. Rebuild primary in new AZ
```

---

### Scenario 4: State File Corruption

**Question:** "Your state file got corrupted. How do you recover?"

**Answer:**

1. **Stop all operations** - No terraform apply
2. **Check backups** - S3 versioning, terraform.tfstate.backup
3. **Recover from backup**
   ```bash
   $ aws s3api get-object \
     --bucket my-terraform-state \
     --key terraform.tfstate \
     --version-id VERSION_ID \
     terraform.tfstate
   ```
4. **Refresh state**
   ```bash
   $ terraform refresh
   ```
5. **Verify** - Check resources exist in AWS
6. **Test plan** - Make sure terraform plan is clean

**Prevention:**
- Enable S3 versioning
- Enable MFA delete protection
- Regular backups to different bucket
- Monitor state file size changes

---

This comprehensive guide covers production-ready Terraform patterns and real-world scenarios you'll encounter in interviews.
