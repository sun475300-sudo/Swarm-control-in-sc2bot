# OpenTofu IaC for SC2 Bot Infrastructure
# OpenTofu is the open-source fork of Terraform under the MPL-2.0 license.
# Usage: tofu init && tofu plan && tofu apply

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "opentofu/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "opentofu/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "opentofu/kubernetes"
      version = "~> 2.25"
    }
    random = {
      source  = "opentofu/random"
      version = "~> 3.6"
    }
  }

  backend "s3" {
    bucket         = "sc2bot-tofu-state"
    key            = "sc2bot/infra/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "sc2bot-tofu-locks"
  }
}

# ─── Variables ────────────────────────────────────────────────────────────────

variable "project_name" {
  type        = string
  default     = "sc2bot"
  description = "Base name for all SC2 bot resources"
}

variable "environment" {
  type        = string
  default     = "prod"
  description = "Deployment environment (dev, staging, prod)"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod"
  }
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "gcp_project" {
  type        = string
  description = "GCP project ID for multi-cloud resources"
}

variable "gcp_region" {
  type    = string
  default = "us-central1"
}

variable "eks_node_count" {
  type    = number
  default = 3
}

variable "eks_node_type" {
  type    = string
  default = "t3.xlarge"
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.medium"
}

variable "db_password" {
  type        = string
  sensitive   = true
  description = "Master password for the RDS replay database"
}

# ─── Locals ───────────────────────────────────────────────────────────────────

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "opentofu"
    Repository  = "github.com/sc2bot/zerg-ai"
  }

  vpc_cidr            = "10.0.0.0/16"
  private_subnets     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets      = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  availability_zones  = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
}

# ─── Provider Configuration ───────────────────────────────────────────────────

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = local.common_tags
  }
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

# ─── AWS EKS Cluster ──────────────────────────────────────────────────────────

resource "aws_iam_role" "eks_cluster_role" {
  name = "${local.name_prefix}-eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  role       = aws_iam_role.eks_cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_eks_cluster" "sc2bot" {
  name     = "${local.name_prefix}-eks"
  role_arn = aws_iam_role.eks_cluster_role.arn
  version  = "1.29"

  vpc_config {
    subnet_ids              = aws_subnet.private[*].id
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = ["0.0.0.0/0"]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  encryption_config {
    provider {
      key_arn = aws_kms_key.eks.arn
    }
    resources = ["secrets"]
  }

  depends_on = [aws_iam_role_policy_attachment.eks_cluster_policy]

  tags = local.common_tags
}

resource "aws_kms_key" "eks" {
  description             = "KMS key for EKS secrets encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  tags                    = local.common_tags
}

# Networking (simplified — use a module like terraform-aws-modules/vpc in production)
resource "aws_vpc" "sc2bot" {
  cidr_block           = local.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = merge(local.common_tags, { Name = "${local.name_prefix}-vpc" })
}

resource "aws_subnet" "private" {
  count             = length(local.private_subnets)
  vpc_id            = aws_vpc.sc2bot.id
  cidr_block        = local.private_subnets[count.index]
  availability_zone = local.availability_zones[count.index]
  tags              = merge(local.common_tags, { Name = "${local.name_prefix}-private-${count.index + 1}" })
}

resource "aws_subnet" "public" {
  count                   = length(local.public_subnets)
  vpc_id                  = aws_vpc.sc2bot.id
  cidr_block              = local.public_subnets[count.index]
  availability_zone       = local.availability_zones[count.index]
  map_public_ip_on_launch = true
  tags                    = merge(local.common_tags, { Name = "${local.name_prefix}-public-${count.index + 1}" })
}

# ─── GCP GKE Cluster ──────────────────────────────────────────────────────────

resource "google_container_cluster" "sc2bot" {
  name     = "${local.name_prefix}-gke"
  location = var.gcp_region
  project  = var.gcp_project

  remove_default_node_pool = true
  initial_node_count       = 1

  network    = google_compute_network.sc2bot.name
  subnetwork = google_compute_subnetwork.sc2bot.name

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  logging_service    = "logging.googleapis.com/kubernetes"
  monitoring_service = "monitoring.googleapis.com/kubernetes"
}

resource "google_compute_network" "sc2bot" {
  name                    = "${local.name_prefix}-vpc"
  project                 = var.gcp_project
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "sc2bot" {
  name          = "${local.name_prefix}-subnet"
  project       = var.gcp_project
  region        = var.gcp_region
  network       = google_compute_network.sc2bot.id
  ip_cidr_range = "10.1.0.0/16"

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.2.0.0/16"
  }
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.3.0.0/16"
  }
}

# ─── AWS RDS for Replay Database ──────────────────────────────────────────────

resource "aws_db_subnet_group" "sc2bot" {
  name       = "${local.name_prefix}-db-subnet"
  subnet_ids = aws_subnet.private[*].id
  tags       = local.common_tags
}

resource "aws_security_group" "rds" {
  name   = "${local.name_prefix}-rds-sg"
  vpc_id = aws_vpc.sc2bot.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [local.vpc_cidr]
    description = "PostgreSQL access from VPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_rds_instance" "sc2bot_replay_db" {
  identifier          = "${local.name_prefix}-replay-db"
  engine              = "postgres"
  engine_version      = "15.4"
  instance_class      = var.db_instance_class
  allocated_storage   = 100
  storage_type        = "gp3"
  storage_encrypted   = true
  db_name             = "sc2bot_replays"
  username            = "sc2bot_admin"
  password            = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.sc2bot.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  multi_az               = var.environment == "prod" ? true : false
  publicly_accessible    = false
  deletion_protection    = var.environment == "prod" ? true : false
  backup_retention_period = 7
  skip_final_snapshot    = var.environment != "prod"
  performance_insights_enabled = true

  tags = local.common_tags
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "eks_cluster_name" {
  description = "Name of the EKS cluster"
  value       = aws_eks_cluster.sc2bot.name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster API endpoint"
  value       = aws_eks_cluster.sc2bot.endpoint
  sensitive   = true
}

output "db_endpoint" {
  description = "RDS endpoint for replay database"
  value       = aws_rds_instance.sc2bot_replay_db.endpoint
  sensitive   = true
}

output "gke_cluster_name" {
  description = "Name of the GKE cluster"
  value       = google_container_cluster.sc2bot.name
}

output "vpc_id" {
  description = "AWS VPC ID"
  value       = aws_vpc.sc2bot.id
}
