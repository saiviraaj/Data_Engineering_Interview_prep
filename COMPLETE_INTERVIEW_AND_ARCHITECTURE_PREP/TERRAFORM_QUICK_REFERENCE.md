# Terraform Quick Reference & Commands Cheatsheet

## Essential Commands

```bash
# Initialize project (download providers, setup backend)
terraform init

# Validate syntax
terraform validate

# Format code
terraform fmt -recursive

# Plan changes (dry run - ALWAYS do this first!)
terraform plan
terraform plan -out=tfplan              # Save plan to file
terraform plan -target=aws_instance.web # Plan specific resource
terraform plan -var="key=value"         # Override variable

# Apply changes (actually deploy)
terraform apply
terraform apply tfplan                  # Apply saved plan
terraform apply -auto-approve          # Skip confirmation (use in CI/CD)
terraform apply -target=aws_instance.web # Apply specific resource

# Destroy (delete infrastructure)
terraform destroy
terraform destroy -target=aws_instance.web

# State management
terraform state list                    # List resources
terraform state show aws_instance.web  # Show resource details
terraform state mv old_name new_name   # Rename resource
terraform state rm aws_instance.web    # Remove from state (don't delete)
terraform state pull > backup.json     # Backup state
terraform state push backup.json       # Restore state

# Refresh state (update to match actual infrastructure)
terraform refresh
terraform apply -refresh-only          # Refresh without changes

# Import existing resource
terraform import aws_instance.web i-0c5b159cbfafe1f0

# Output values
terraform output                        # Show all outputs
terraform output instance_id            # Show specific output
terraform output -json                  # JSON format

# Workspaces
terraform workspace list                # List workspaces
terraform workspace new dev             # Create workspace
terraform workspace select prod         # Switch workspace
terraform workspace show                # Current workspace

# Debugging
terraform console                       # Interactive console
terraform graph                         # Show dependency graph
TF_LOG=DEBUG terraform apply           # Debug logging
```

## Variable Types & Syntax

```hcl
# String
variable "app_name" {
  type    = string
  default = "myapp"
}

# Number
variable "port" {
  type    = number
  default = 8080
}

# Boolean
variable "enable_https" {
  type    = bool
  default = true
}

# List
variable "zones" {
  type    = list(string)
  default = ["us-east-1a", "us-east-1b"]
}

# Map
variable "tags" {
  type    = map(string)
  default = {
    Environment = "prod"
    Team        = "DataEng"
  }
}

# Set (unique list)
variable "allowed_ips" {
  type    = set(string)
  default = ["10.0.0.0/8", "10.0.0.1/32"]
}

# Object (complex structure)
variable "database" {
  type = object({
    engine   = string
    version  = string
    storage  = number
  })
  default = {
    engine   = "postgres"
    version  = "14"
    storage  = 100
  }
}
```

## Resources Quick Lookup

```hcl
# AWS EC2
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"
}

# AWS VPC
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

# AWS Subnet
resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"
}

# AWS Security Group
resource "aws_security_group" "web" {
  vpc_id = aws_vpc.main.id
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# AWS S3 Bucket
resource "aws_s3_bucket" "data" {
  bucket = "my-data-bucket"
}

# AWS RDS Database
resource "aws_db_instance" "postgres" {
  identifier        = "mydb"
  engine            = "postgres"
  engine_version    = "14.1"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  username          = "admin"
  password          = var.db_password
}

# AWS Lambda Function
resource "aws_lambda_function" "processor" {
  filename      = "lambda.zip"
  function_name = "my-function"
  role          = aws_iam_role.lambda.arn
  handler       = "index.handler"
  runtime       = "python3.11"
}

# GCP Compute Instance
resource "google_compute_instance" "vm" {
  name         = "my-vm"
  machine_type = "e2-medium"
  zone         = "us-central1-a"
}

# GCP Cloud SQL Database
resource "google_sql_database_instance" "postgres" {
  name             = "my-postgres"
  database_version = "POSTGRES_14"
  
  settings {
    tier = "db-f1-micro"
  }
}

# GCP BigQuery Dataset
resource "google_bigquery_dataset" "dataset" {
  dataset_id = "my_dataset"
  location   = "US"
}

# Azure Virtual Machine
resource "azurerm_virtual_machine" "vm" {
  name                  = "my-vm"
  location              = "eastus"
  resource_group_name   = azurerm_resource_group.rg.name
  vm_size               = "Standard_B1s"
}
```

## Expressions & Functions Cheatsheet

```hcl
# String interpolation
name = "${var.environment}-server-${count.index}"

# Ternary (if/else)
instance_type = var.environment == "prod" ? "t3.large" : "t2.micro"

# Count (create multiple)
count = var.create_instances ? 3 : 0

# For-each (loop over map)
for_each = var.availability_zones
availability_zone = each.value

# Length function
instance_count = length(var.zones)

# List functions
subnets = slice(var.all_subnets, 0, 2)
combined = concat(var.list_a, var.list_b)

# String functions
lower_name = lower(var.app_name)
trimmed = trim(var.text, " ")

# Conditional functions
zone = var.multi_az ? var.zones[0] : var.zones[0]

# Merge (combine maps)
all_tags = merge(var.default_tags, var.custom_tags)

# Try-catch
value = try(var.optional_var, "default")

# Conditional expression
description = var.enable_monitoring ? "Monitoring enabled" : "Monitoring disabled"
```

## File Structure Best Practice

```
project/
├── main.tf              # Primary resources
├── variables.tf         # Input variables
├── outputs.tf           # Output values
├── terraform.tfvars    # Variable values (gitignored if secrets)
├── versions.tf         # Provider versions
├── locals.tf           # Local values
│
├── modules/
│  ├── networking/
│  │  ├── main.tf
│  │  ├── variables.tf
│  │  └── outputs.tf
│  ├── compute/
│  │  ├── main.tf
│  │  ├── variables.tf
│  │  └── outputs.tf
│  └── database/
│     ├── main.tf
│     ├── variables.tf
│     └── outputs.tf
│
├── environments/
│  ├── dev/
│  │  ├── main.tf
│  │  └── terraform.tfvars
│  ├── staging/
│  │  ├── main.tf
│  │  └── terraform.tfvars
│  └── prod/
│     ├── main.tf
│     └── terraform.tfvars
│
├── .gitignore
├── .terraform.lock.tcl (version lock - COMMIT THIS)
└── README.md
```

## .gitignore for Terraform

```
# Local .terraform directories
**/.terraform/*

# .tfstate files
*.tfstate
*.tfstate.*
*.backup

# Crash log files
crash.log
crash.*.log

# Exclude all .tfvars files (may contain sensitive data)
*.tfvars
*.tfvars.json

# Ignore override files
override.tf
override.tf.json
*_override.tf
*_override.tf.json

# Ignore CLI configuration files
.terraformrc
terraform.rc

# Ignore plan files
*.tfplan

# IDE
.idea/
*.swp
*.swo
*~
.vscode/
```

## Backend Configuration Examples

```hcl
# S3 Backend (AWS)
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

# GCS Backend (Google Cloud)
terraform {
  backend "gcs" {
    bucket = "my-terraform-state"
    prefix = "prod"
  }
}

# Azure Backend
terraform {
  backend "azurerm" {
    resource_group_name  = "tfstate"
    storage_account_name = "tfstate"
    container_name       = "tfstate"
    key                  = "prod.terraform.tfstate"
  }
}

# Terraform Cloud Backend
terraform {
  cloud {
    organization = "my-org"
    
    workspaces {
      name = "my-workspace"
    }
  }
}

# Local Backend (dev only)
terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}
```

## Common Patterns

```hcl
# Create multiple resources with count
resource "aws_instance" "servers" {
  count         = var.server_count
  instance_type = "t2.micro"
  
  tags = {
    Name = "server-${count.index + 1}"
  }
}

# Create multiple resources with for_each
resource "aws_instance" "servers" {
  for_each      = var.server_config
  instance_type = each.value.type
  
  tags = {
    Name = each.key
  }
}

# Reference resources
instance_id = aws_instance.servers[0].id              # count
instance_id = aws_instance.servers["web1"].id        # for_each

# Conditional resource creation
resource "aws_instance" "optional" {
  count = var.create_instance ? 1 : 0
}

# Reference optional resource
instance = var.create_instance ? aws_instance.optional[0].id : ""

# Use output from module
resource "aws_instance" "app" {
  subnet_id = module.networking.subnet_id
}

# Dynamic blocks
resource "aws_security_group" "web" {
  dynamic "ingress" {
    for_each = var.ingress_rules
    content {
      from_port = ingress.value.from_port
      to_port   = ingress.value.to_port
    }
  }
}
```

## Troubleshooting Quick Tips

```bash
# Check what will be destroyed
terraform plan -destroy

# See if there's drift
terraform refresh
terraform plan

# Debug a specific resource
terraform state show aws_instance.web

# See all resources
terraform state list

# Force unlock (if stuck)
terraform force-unlock LOCK_ID

# See debug logs
TF_LOG=DEBUG terraform plan

# Validate JSON output
terraform output -json | jq

# Check syntax errors
terraform validate

# Format issues
terraform fmt -check

# Find unused variables
terraform console
# Then manually check if variables are used

# Check what workspace you're in
terraform workspace show

# List all workspaces
terraform workspace list
```

## Interview Q&A Cheat Sheet

| Question | Key Points |
|----------|-----------|
| "What is Terraform?" | IaC tool, declarative, multi-cloud, version control, plan before apply |
| "Explain state file" | JSON file tracking resources, enables drift detection, must be secured |
| "plan vs apply" | plan = dry run (no changes), apply = actual deployment |
| "Modules use case" | Reusability, organization, team collaboration |
| "State backend" | Remote storage (S3), encryption, locking, backup |
| "How to scale?" | Variables, count/for_each, autoscaling groups |
| "Environment separation" | Workspaces or directories + tfvars |
| "Secrets management" | Variables (gitignored), environment vars, secrets manager |
| "CI/CD integration" | terraform plan in PR, terraform apply in main |
| "Disaster recovery" | Remote state backup, replicated infrastructure |

---

**Remember:** Always run `terraform plan` before `terraform apply`!
