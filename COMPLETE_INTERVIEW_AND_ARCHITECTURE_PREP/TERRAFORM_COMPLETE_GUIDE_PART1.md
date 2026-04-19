# Terraform Complete Guide: From Zero to Expert

## Table of Contents
1. [What is Terraform?](#what-is-terraform)
2. [Infrastructure as Code (IaC) Fundamentals](#iac-fundamentals)
3. [Terraform Core Concepts](#core-concepts)
4. [HCL Syntax & Configuration](#hcl-syntax)
5. [Terraform Workflow](#workflow)
6. [State Management](#state-management)
7. [Best Practices](#best-practices)
8. [Real-World Examples](#examples)
9. [Interview Questions](#interview-questions)

---

## What is Terraform?

### Definition
**Terraform** is an open-source Infrastructure as Code (IaC) tool created by HashiCorp that lets you define, preview, and deploy infrastructure using simple, human-readable configuration files.

### Key Characteristics
```
┌─────────────────────────────────────┐
│ TERRAFORM CHARACTERISTICS           │
├─────────────────────────────────────┤
│ • Declarative (not imperative)      │
│ • Multi-cloud (AWS, GCP, Azure)     │
│ • Version control friendly          │
│ • Repeatable & consistent           │
│ • Idempotent (safe to run multiple) │
│ • Open source                       │
│ • Large ecosystem (providers)       │
│ • Plan before apply (dry run)       │
└─────────────────────────────────────┘
```

### What is IaC?

**Infrastructure as Code** means:
- Define infrastructure in code files (not manual clicks)
- Version control infrastructure like application code
- Reproducible deployments
- Automated testing & deployment
- Faster changes

```
BEFORE IaC (Manual):
Step 1: Click AWS Console → EC2
Step 2: Create instance
Step 3: Configure security group
Step 4: Attach IAM role
Step 5: Document in spreadsheet
(Repeat steps 1-5 for each environment)

AFTER IaC (Terraform):
Step 1: Write main.tf
Step 2: terraform plan
Step 3: terraform apply
(Same code works for all environments)
```

### Traditional vs Terraform

| Aspect | Traditional | Terraform |
|--------|-----------|-----------|
| **How** | Manual AWS Console clicks | Code in HCL (.tf files) |
| **Repeatability** | Manual (error-prone) | Automatic & consistent |
| **Documentation** | Spreadsheets (outdated) | Code = documentation |
| **Disaster Recovery** | Rebuild from notes | Re-run terraform apply |
| **Version Control** | No | Yes (Git) |
| **Testing** | Manual | Automated |
| **Time to Deploy** | Hours | Minutes |

---

## IaC Fundamentals

### Why IaC Matters

```
Problem without IaC:
├─ Infrastructure changes are manual
├─ No version history
├─ Inconsistent across environments
├─ Hard to reproduce in new region
├─ Disaster recovery is nightmare
└─ Takes 2+ weeks to clone infrastructure

Solution with Terraform:
├─ Everything in code
├─ Full version history (Git)
├─ Identical across dev/staging/prod
├─ Clone infrastructure in 30 minutes
├─ Disaster recovery: terraform apply
└─ New environment = terraform apply
```

### Infrastructure Components (What Terraform Manages)

```
┌─────────────────────────────────────┐
│ COMPUTE                             │
├─────────────────────────────────────┤
│ • VMs (EC2, GCE, AzureVM)          │
│ • Auto-scaling groups               │
│ • Kubernetes clusters               │
│ • Lambda functions                  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ NETWORKING                          │
├─────────────────────────────────────┤
│ • VPCs / Networks                   │
│ • Subnets                           │
│ • Route tables                      │
│ • Security groups                   │
│ • Load balancers                    │
│ • VPN connections                   │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ STORAGE                             │
├─────────────────────────────────────┤
│ • S3 buckets                        │
│ • EBS volumes                       │
│ • Databases (RDS, Cloud SQL)        │
│ • File systems                      │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ SECURITY & ACCESS                   │
├─────────────────────────────────────┤
│ • IAM roles & policies              │
│ • SSL certificates                  │
│ • Secrets management                │
│ • Key pairs                         │
└─────────────────────────────────────┘

Terraform manages ALL of these via code!
```

---

## Core Concepts

### 1. Provider

**Provider** = Connection to a cloud platform

```hcl
# AWS Provider
provider "aws" {
  region = "us-east-1"
  
  default_tags {
    tags = {
      Environment = "production"
      ManagedBy   = "Terraform"
    }
  }
}

# Google Cloud Provider
provider "google" {
  project = "my-gcp-project"
  region  = "us-central1"
}

# Azure Provider
provider "azurerm" {
  features {}
  subscription_id = var.azure_subscription_id
}
```

### 2. Resource

**Resource** = Actual infrastructure you want to create

```hcl
# AWS EC2 Instance
resource "aws_instance" "web_server" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"
  
  tags = {
    Name = "MyWebServer"
  }
}

# GCP Compute Instance
resource "google_compute_instance" "app_server" {
  name         = "app-server"
  machine_type = "e2-medium"
  zone         = "us-central1-a"
  
  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }
}
```

### 3. Variables

**Variables** = Input values (like function parameters)

```hcl
# Define variable
variable "environment" {
  type        = string
  description = "Environment name"
  default     = "development"
}

variable "instance_count" {
  type        = number
  description = "Number of instances"
  validation {
    condition     = var.instance_count > 0
    error_message = "Instance count must be > 0"
  }
}

variable "tags" {
  type = map(string)
  default = {
    Project = "MyProject"
    Owner   = "DataTeam"
  }
}

# Use variable
resource "aws_instance" "example" {
  count         = var.instance_count
  instance_type = "t2.micro"
  tags          = var.tags
}
```

### 4. Outputs

**Outputs** = Values returned from infrastructure

```hcl
# Define output
output "instance_ip" {
  value       = aws_instance.web_server.public_ip
  description = "Public IP of web server"
}

output "database_endpoint" {
  value       = aws_db_instance.postgres.endpoint
  description = "Database connection string"
  sensitive   = true  # Hide from logs
}

# Access output
# After terraform apply:
# instance_ip = "203.0.113.42"
```

### 5. State File

**State** = Terraform's memory of what exists

```
terraform.tfstate (JSON file):
{
  "version": 4,
  "resources": [
    {
      "type": "aws_instance",
      "name": "web_server",
      "instances": [
        {
          "attributes": {
            "id": "i-0c5b159cbfafe1f0",
            "public_ip": "203.0.113.42",
            "tags": {"Name": "MyWebServer"}
          }
        }
      ]
    }
  ]
}

⚠️ CRITICAL: State file contains sensitive data!
├─ Never commit to Git
├─ Store in secure backend (S3, Terraform Cloud)
├─ Use encryption
└─ Restrict access
```

---

## HCL Syntax

### Basic Structure

```hcl
# ============================================
# TERRAFORM CONFIGURATION FILE (main.tf)
# ============================================

# 1. Terraform settings
terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# 2. Provider configuration
provider "aws" {
  region = "us-east-1"
}

# 3. Variables (inputs)
variable "instance_type" {
  type    = string
  default = "t2.micro"
}

# 4. Resources (infrastructure)
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = var.instance_type
}

# 5. Outputs (return values)
output "instance_id" {
  value = aws_instance.web.id
}
```

### Data Types

```hcl
# String
variable "environment" {
  type = string
  default = "production"
}

# Number
variable "instance_count" {
  type = number
  default = 1
}

# Boolean
variable "enable_monitoring" {
  type = bool
  default = true
}

# List
variable "availability_zones" {
  type = list(string)
  default = ["us-east-1a", "us-east-1b"]
}

# Map
variable "tags" {
  type = map(string)
  default = {
    Environment = "prod"
    Owner       = "DataTeam"
  }
}

# Object (complex type)
variable "database_config" {
  type = object({
    engine       = string
    version      = string
    instance_class = string
  })
  default = {
    engine         = "postgres"
    version        = "14.1"
    instance_class = "db.t3.micro"
  }
}
```

### Expressions & Functions

```hcl
# String interpolation
resource "aws_instance" "example" {
  tags = {
    Name = "${var.environment}-web-server"
  }
}

# Conditional
resource "aws_instance" "conditional" {
  count = var.enable_compute ? 1 : 0
  # Will create if enable_compute is true
}

# Loops
resource "aws_instance" "multiple" {
  count         = var.instance_count
  instance_type = "t2.micro"
  
  tags = {
    Name = "server-${count.index + 1}"
  }
}

# For-each (better than count)
resource "aws_instance" "by_zone" {
  for_each      = toset(var.availability_zones)
  instance_type = "t2.micro"
  availability_zone = each.value
  
  tags = {
    Zone = each.value
  }
}

# Built-in functions
locals {
  # String functions
  app_name = lower(var.app_name)
  
  # List functions
  zones = slice(var.all_zones, 0, 2)
  
  # Math functions
  count_rounded = ceil(var.desired_capacity / 2)
  
  # Conditional functions
  instance_type = var.environment == "prod" ? "t3.large" : "t2.micro"
}
```

---

## Terraform Workflow

### Step 1: Write Configuration

```hcl
# main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

variable "instance_type" {
  type    = string
  default = "t2.micro"
}

resource "aws_instance" "web_server" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = var.instance_type
  
  tags = {
    Name = "WebServer"
  }
}

output "instance_id" {
  value = aws_instance.web_server.id
}
```

### Step 2: Initialize Project

```bash
$ terraform init

Initializing the backend...
Downloading plugins from registry.terraform.io...
Terraform initialized successfully!

# Creates:
# .terraform/       (downloaded providers)
# .terraform.lock.tcl (version lock file)
```

### Step 3: Plan (Dry Run)

```bash
$ terraform plan

# Shows what will happen WITHOUT making changes

Plan: 1 to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + instance_id = (known after apply)

# Review changes carefully!
```

### Step 4: Apply (Deploy)

```bash
$ terraform apply

# Asks for confirmation before deploying
# Then creates real infrastructure

aws_instance.web_server: Creating...
aws_instance.web_server: Still creating... [10s elapsed]
aws_instance.web_server: Creation complete after 20s

Apply complete! Resources: 1 added, 0 changed, 0 destroyed.

Outputs:
instance_id = "i-0c5b159cbfafe1f0"
```

### Step 5: Verify & Manage

```bash
# Check current state
$ terraform state list
# aws_instance.web_server

# Get resource details
$ terraform state show aws_instance.web_server

# Verify with AWS CLI
$ aws ec2 describe-instances --instance-ids i-0c5b159cbfafe1f0
```

### Step 6: Destroy (Cleanup)

```bash
$ terraform destroy

# Shows what will be deleted
# Asks for confirmation

aws_instance.web_server: Destroying...
aws_instance.web_server: Destruction complete after 2s

Destroy complete!
```

### Complete Workflow Diagram

```
┌─────────────┐
│ Write .tf   │
│ files       │
└──────┬──────┘
       │
       ↓
┌─────────────────┐
│ terraform init  │ (Download providers)
└──────┬──────────┘
       │
       ↓
┌──────────────────┐
│ terraform plan   │ (Dry run - shows changes)
└──────┬───────────┘
       │
       ↓ (Review output!)
┌──────────────────┐
│ terraform apply  │ (Actually create resources)
└──────┬───────────┘
       │
       ↓
┌───────────────────┐
│ Resources created │
│ in AWS/GCP/etc    │
└──────┬────────────┘
       │
       ↓ (Later: to delete)
┌──────────────────┐
│ terraform destroy│ (Remove all resources)
└──────────────────┘
```

---

## State Management

### What is State?

```
State file = Terraform's database of what exists

Before: terraform apply
└─ State empty (no resources)

After: terraform apply
└─ State updated with:
   ├─ Resource IDs
   ├─ Current attributes
   ├─ Metadata
   └─ Sensitive values

Next: terraform apply
└─ Compares desired state (code) vs current state (state file)
   ├─ No changes? → Do nothing
   ├─ Changes? → Apply differences only
   └─ Deletions? → Destroy resources
```

### State File Structure

```json
{
  "version": 4,
  "terraform_version": "1.5.0",
  "serial": 3,
  "lineage": "abc-123",
  "outputs": {
    "instance_id": {
      "value": "i-0c5b159cbfafe1f0",
      "type": "string"
    }
  },
  "resources": [
    {
      "type": "aws_instance",
      "name": "web_server",
      "instances": [
        {
          "schema_version": 1,
          "attributes": {
            "id": "i-0c5b159cbfafe1f0",
            "ami": "ami-0c55b159cbfafe1f0",
            "instance_type": "t2.micro",
            "public_ip": "203.0.113.42",
            "private_ip": "10.0.1.25",
            "tags": {
              "Name": "WebServer"
            }
          }
        }
      ]
    }
  ]
}
```

### Remote State (Best Practice for Teams)

```hcl
# Store state in S3 (not local machine)
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"  # For locking
  }
}

Benefits:
├─ Shared across team
├─ Encrypted at rest
├─ Versioned (rollback possible)
├─ Locking (prevent concurrent changes)
└─ Backup & recovery
```

### Common State Issues

```hcl
# Issue 1: Changing resource names
# OLD: resource "aws_instance" "web"
# NEW: resource "aws_instance" "web_server"
# Result: Terraform thinks resource is deleted & recreated

# Solution: Use mv
# terraform state mv aws_instance.web aws_instance.web_server

# Issue 2: Drift (manual changes in console)
# Someone logs into AWS and changes security group manually

# Solution: Detect & fix drift
# terraform plan -refresh-only  (detects drift)
# terraform apply -refresh-only (updates state)

# Issue 3: Lost state file
# Solution: Recover from remote backend or Git history
```

---

## Best Practices

### 1. Directory Structure

```
my-infrastructure/
├─ main.tf              # Main resources
├─ variables.tf         # Input variables
├─ outputs.tf           # Output values
├─ terraform.tfvars     # Variable values
├─ backend.tf           # Backend config
├─ versions.tf          # Provider versions
│
├─ modules/             # Reusable code
│  ├─ vpc/
│  │  ├─ main.tf
│  │  ├─ variables.tf
│  │  └─ outputs.tf
│  ├─ security_group/
│  │  ├─ main.tf
│  │  ├─ variables.tf
│  │  └─ outputs.tf
│  └─ rds/
│
├─ environments/        # Different envs
│  ├─ dev/
│  │  ├─ terraform.tfvars
│  │  └─ main.tf
│  ├─ staging/
│  │  ├─ terraform.tfvars
│  │  └─ main.tf
│  └─ prod/
│     ├─ terraform.tfvars
│     └─ main.tf
│
├─ .gitignore          # Don't commit
│  ├─ *.tfstate
│  ├─ *.tfstate.backup
│  ├─ .terraform/
│  ├─ terraform.tfvars (if secrets)
│  └─ crash.log
│
└─ README.md           # Documentation
```

### 2. Modularization

```hcl
# BAD: Everything in one file
resource "aws_vpc" "main" {...}
resource "aws_subnet" "a" {...}
resource "aws_security_group" "web" {...}
resource "aws_instance" "web" {...}
resource "aws_rds_cluster" "db" {...}
# 500+ lines in one file (hard to maintain)

# GOOD: Organized in modules
# modules/vpc/main.tf
resource "aws_vpc" "main" {...}
resource "aws_subnet" "a" {...}

# modules/security_group/main.tf
resource "aws_security_group" "web" {...}

# modules/compute/main.tf
resource "aws_instance" "web" {...}

# modules/database/main.tf
resource "aws_rds_cluster" "db" {...}

# main.tf (orchestrates modules)
module "vpc" {
  source = "./modules/vpc"
  cidr_block = "10.0.0.0/16"
}

module "security" {
  source = "./modules/security_group"
  vpc_id = module.vpc.vpc_id
}
```

### 3. Variable Validation

```hcl
variable "instance_type" {
  type        = string
  description = "EC2 instance type"
  
  validation {
    condition     = contains(["t2.micro", "t2.small", "t2.medium"], var.instance_type)
    error_message = "Instance type must be t2.micro, t2.small, or t2.medium"
  }
}

variable "environment" {
  type        = string
  description = "Environment name"
  
  validation {
    condition     = can(regex("^(dev|staging|prod)$", var.environment))
    error_message = "Environment must be dev, staging, or prod"
  }
}

variable "instance_count" {
  type        = number
  description = "Number of instances"
  
  validation {
    condition     = var.instance_count > 0 && var.instance_count <= 100
    error_message = "Instance count must be between 1 and 100"
  }
}
```

### 4. Version Pinning

```hcl
# BAD: Any version (can break)
terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      # No version specified!
    }
  }
}

# GOOD: Explicit version
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.0.1"  # Exact version
    }
  }
}

# BETTER: Version range
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"  # 5.0.x (not 6.x)
    }
  }
}

# .terraform.lock.tcl
# Lock file ensures same version across team
```

### 5. Security Best Practices

```hcl
# DON'T: Hardcode secrets
resource "aws_db_instance" "db" {
  username = "admin"
  password = "MyPassword123"  # ❌ NEVER!
}

# DO: Use variables or secrets manager
variable "db_password" {
  type      = string
  sensitive = true  # Hide from logs
  # Get from: terraform.tfvars (gitignored)
  # Or: Environment variable
  # Or: AWS Secrets Manager
}

resource "aws_db_instance" "db" {
  username = var.db_admin_username
  password = var.db_password  # From secure source
}

# DO: Use outputs as sensitive
output "database_password" {
  value       = aws_db_instance.db.password
  sensitive   = true  # Won't print in output
  description = "Database password"
}

# DO: Encrypt state file
terraform {
  backend "s3" {
    encrypt = true  # Encrypt at rest
  }
}

# DO: Use IAM roles (not access keys)
provider "aws" {
  # No access_key/secret_key!
  # Uses IAM role instead (from EC2/ECS/Lambda context)
}
```

### 6. Testing & Validation

```bash
# Validate syntax
$ terraform validate
Success! The configuration is valid.

# Format check
$ terraform fmt -check
# Check if code is formatted correctly

# Plan to file
$ terraform plan -out=tfplan
# For review before apply

# Apply from file
$ terraform apply tfplan

# Target specific resource
$ terraform apply -target=aws_instance.web_server
# Only apply/destroy one resource

# Detailed output
$ terraform plan -json > plan.json
# Machine-readable output

# Dry run with variables
$ terraform plan \
  -var="environment=prod" \
  -var="instance_count=3"
```

---

## Real-World Examples

### Example 1: Simple Web Server

```hcl
# main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "instance_type" {
  type    = string
  default = "t2.micro"
}

variable "environment" {
  type    = string
  default = "dev"
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true

  tags = {
    Name = "${var.environment}-vpc"
  }
}

# Subnet
resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.aws_region}a"

  tags = {
    Name = "${var.environment}-subnet"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.environment}-igw"
  }
}

# Route Table
resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block      = "0.0.0.0/0"
    gateway_id      = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.environment}-rt"
  }
}

resource "aws_route_table_association" "main" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.main.id
}

# Security Group
resource "aws_security_group" "web" {
  vpc_id      = aws_vpc.main.id
  name        = "${var.environment}-web-sg"
  description = "Security group for web server"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["203.0.113.0/24"]  # Your IP
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-web-sg"
  }
}

# EC2 Instance
resource "aws_instance" "web" {
  ami                    = "ami-0c55b159cbfafe1f0"  # Ubuntu 22.04
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.web.id]
  
  associate_public_ip_address = true

  user_data = base64encode(<<-EOF
    #!/bin/bash
    apt-get update
    apt-get install -y nginx
    systemctl start nginx
  EOF
  )

  tags = {
    Name = "${var.environment}-web-server"
  }
}

# Outputs
output "instance_public_ip" {
  value       = aws_instance.web.public_ip
  description = "Public IP of web server"
}

output "instance_id" {
  value       = aws_instance.web.id
  description = "Instance ID"
}

output "vpc_id" {
  value       = aws_vpc.main.id
  description = "VPC ID"
}
```

---

## Interview Questions

### Q1: "What is Terraform and why use it?"

**Answer:**
Terraform is an Infrastructure as Code tool that lets you define cloud resources in HCL code instead of manual console clicks.

**Benefits:**
- Repeatable: Same code creates identical infrastructure
- Versionable: Track changes in Git
- Testable: Plan before apply
- Reproducible: Disaster recovery via terraform apply
- Multi-cloud: Works with AWS, GCP, Azure, etc.
- Idempotent: Safe to run multiple times

**Example:**
Without Terraform: Click 50 times in AWS console to create VPC, subnets, security groups, EC2, RDS
With Terraform: Write 100 lines of HCL code, run terraform apply

---

### Q2: "Explain Terraform state. Why is it important?"

**Answer:**
State is Terraform's memory of what infrastructure exists. It's a JSON file that maps your code to real resources.

**Example:**
```hcl
# Code
resource "aws_instance" "web" {
  instance_type = "t2.micro"
}

# State (after terraform apply)
{
  "aws_instance": {
    "web": {
      "id": "i-0c5b159cbfafe1f0"
    }
  }
}
```

**Why important:**
1. Tracks what's created (without it, Terraform can't know what to update/delete)
2. Performance (queries existing state, not AWS API each time)
3. Enables operations (terraform destroy reads state to know what to delete)

**Best practices:**
- Store in remote backend (S3, Terraform Cloud) not local
- Encrypt at rest
- Enable state locking
- Never commit to Git

---

### Q3: "What's the difference between terraform plan and terraform apply?"

**Answer:**

| Command | What it does | When to use |
|---------|---|---|
| **plan** | Shows what WILL happen (dry run) | Before every apply |
| **apply** | Actually creates/updates resources | After reviewing plan |

**Workflow:**
```
terraform plan  → Review output
                → Check for errors
                → Confirm changes needed
                → terraform apply
                → Actual changes happen
```

---

### Q4: "How do you manage different environments (dev/staging/prod)?"

**Answer:**

**Option 1: Separate tfvars files**
```hcl
# variables.tf (shared)
variable "instance_type" {
  type = string
}

# dev/terraform.tfvars
instance_type = "t2.micro"

# prod/terraform.tfvars
instance_type = "t3.large"

# Deploy
terraform apply -var-file="dev/terraform.tfvars"
terraform apply -var-file="prod/terraform.tfvars"
```

**Option 2: Separate directories**
```
environments/
├─ dev/
│  ├─ main.tf
│  └─ variables.tfvars
├─ staging/
│  ├─ main.tf
│  └─ variables.tfvars
└─ prod/
   ├─ main.tf
   └─ variables.tfvars
```

**Option 3: Modules + workspaces**
```
terraform workspace new dev
terraform workspace new prod

terraform workspace select dev
terraform apply

terraform workspace select prod
terraform apply
```

---

### Q5: "How do you handle sensitive data like passwords?"

**Answer:**

**NEVER hardcode:**
```hcl
# ❌ BAD
password = "MyPassword123"
```

**GOOD approaches:**

```hcl
# Method 1: Environment variables
variable "db_password" {
  type      = string
  sensitive = true
}

# Set: export TF_VAR_db_password="MyPassword123"

# Method 2: terraform.tfvars (gitignored)
# terraform.tfvars
db_password = "MyPassword123"

# Method 3: AWS Secrets Manager
data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = "prod/db-password"
}

resource "aws_db_instance" "main" {
  password = data.aws_secretsmanager_secret_version.db_password.secret_string
}

# Mark outputs as sensitive
output "db_password" {
  value     = aws_db_instance.main.password
  sensitive = true  # Won't print
}
```

---

### Q6: "What happens if someone manually changes infrastructure in the console?"

**Answer:**

This is called **drift**. Terraform won't know about it until you run plan.

**Example:**
```
# Code says: t2.micro
# AWS console: Someone changes to t3.large

terraform plan
# Will show: Instance type will change from t3.large to t2.micro

terraform apply
# Will REVERT the change back to t2.micro
```

**To detect & fix drift:**
```bash
terraform plan -refresh-only
# Shows what's drifted

terraform apply -refresh-only
# Updates state to match actual infrastructure
```

**Prevention:**
- Lock console access (IAM policy)
- Use automated deployments (CI/CD)
- Regular drift detection

---

This comprehensive guide covers everything from basics to advanced Terraform usage. For interview preparation, focus on understanding state management, the apply workflow, and best practices.
