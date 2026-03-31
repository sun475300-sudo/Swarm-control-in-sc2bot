# Phase 566: Terraform Advanced
# SC2 Bot 프로덕션 인프라를 HCL로 정의 — IaC 완전 자동화

# ─────────────────────────────────────────────
# Variables
# ─────────────────────────────────────────────

variable "project_name" {
  description = "프로젝트 이름"
  type        = string
  default     = "sc2-zerg-bot"
}

variable "environment" {
  description = "배포 환경"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "environment must be dev, staging, or production"
  }
}

variable "region" {
  description = "클라우드 리전"
  type        = string
  default     = "ap-northeast-2"
}

variable "bot_version" {
  description = "봇 버전"
  type        = string
  default     = "565.0"
}

variable "gpu_enabled" {
  description = "GPU 인스턴스 활성화 (PPO 학습용)"
  type        = bool
  default     = false
}

variable "min_replicas" {
  description = "최소 레플리카 수"
  type        = number
  default     = 2
}

variable "max_replicas" {
  description = "최대 레플리카 수"
  type        = number
  default     = 10
}

variable "tags" {
  description = "공통 태그"
  type        = map(string)
  default = {
    Project     = "sc2-zerg-bot"
    ManagedBy   = "terraform"
    Environment = "production"
  }
}

# ─────────────────────────────────────────────
# Locals — 파생 값 계산
# ─────────────────────────────────────────────

locals {
  name_prefix   = "${var.project_name}-${var.environment}"
  instance_type = var.gpu_enabled ? "g4dn.xlarge" : "t3.medium"

  common_labels = merge(var.tags, {
    Version = var.bot_version
    Region  = var.region
  })

  # SC2 봇 전용 포트
  ports = {
    bot_api   = 8080
    dashboard = 3000
    metrics   = 9090
    grpc      = 50051
    triton    = 8001
  }

  # 환경별 설정
  env_config = {
    dev = {
      instance_count = 1
      db_size        = "db.t3.micro"
      cache_size     = "cache.t3.micro"
      enable_waf     = false
    }
    staging = {
      instance_count = 2
      db_size        = "db.t3.small"
      cache_size     = "cache.t3.small"
      enable_waf     = true
    }
    production = {
      instance_count = 3
      db_size        = "db.r6g.large"
      cache_size     = "cache.r6g.large"
      enable_waf     = true
    }
  }

  current_env = local.env_config[var.environment]
}

# ─────────────────────────────────────────────
# VPC — 네트워크 인프라
# ─────────────────────────────────────────────

resource "aws_vpc" "bot_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.common_labels, {
    Name = "${local.name_prefix}-vpc"
  })
}

resource "aws_subnet" "public" {
  count             = 3
  vpc_id            = aws_vpc.bot_vpc.id
  cidr_block        = "10.0.${count.index}.0/24"
  availability_zone = "${var.region}${["a", "b", "c"][count.index]}"

  map_public_ip_on_launch = true

  tags = merge(local.common_labels, {
    Name = "${local.name_prefix}-public-${count.index}"
    Type = "public"
  })
}

resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.bot_vpc.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = "${var.region}${["a", "b", "c"][count.index]}"

  tags = merge(local.common_labels, {
    Name = "${local.name_prefix}-private-${count.index}"
    Type = "private"
  })
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.bot_vpc.id
  tags   = merge(local.common_labels, { Name = "${local.name_prefix}-igw" })
}

# ─────────────────────────────────────────────
# Security Groups
# ─────────────────────────────────────────────

resource "aws_security_group" "bot_sg" {
  name_prefix = "${local.name_prefix}-bot-"
  vpc_id      = aws_vpc.bot_vpc.id

  # Bot API
  ingress {
    from_port   = local.ports.bot_api
    to_port     = local.ports.bot_api
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Bot API"
  }

  # Dashboard
  ingress {
    from_port   = local.ports.dashboard
    to_port     = local.ports.dashboard
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Dashboard"
  }

  # Metrics (internal only)
  ingress {
    from_port   = local.ports.metrics
    to_port     = local.ports.metrics
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.bot_vpc.cidr_block]
    description = "Prometheus metrics"
  }

  # gRPC (internal only)
  ingress {
    from_port   = local.ports.grpc
    to_port     = local.ports.grpc
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.bot_vpc.cidr_block]
    description = "gRPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound"
  }

  tags = merge(local.common_labels, { Name = "${local.name_prefix}-bot-sg" })

  lifecycle {
    create_before_destroy = true
  }
}

# ─────────────────────────────────────────────
# EKS Cluster — Kubernetes
# ─────────────────────────────────────────────

resource "aws_eks_cluster" "bot_cluster" {
  name     = "${local.name_prefix}-eks"
  role_arn = aws_iam_role.eks_role.arn

  vpc_config {
    subnet_ids              = aws_subnet.private[*].id
    endpoint_private_access = true
    endpoint_public_access  = var.environment != "production"
    security_group_ids      = [aws_security_group.bot_sg.id]
  }

  tags = local.common_labels
}

resource "aws_eks_node_group" "bot_nodes" {
  cluster_name    = aws_eks_cluster.bot_cluster.name
  node_group_name = "${local.name_prefix}-nodes"
  node_role_arn   = aws_iam_role.node_role.arn
  subnet_ids      = aws_subnet.private[*].id
  instance_types  = [local.instance_type]

  scaling_config {
    desired_size = local.current_env.instance_count
    min_size     = var.min_replicas
    max_size     = var.max_replicas
  }

  tags = local.common_labels
}

# GPU Node Group (PPO 학습 전용)
resource "aws_eks_node_group" "gpu_nodes" {
  count           = var.gpu_enabled ? 1 : 0
  cluster_name    = aws_eks_cluster.bot_cluster.name
  node_group_name = "${local.name_prefix}-gpu"
  node_role_arn   = aws_iam_role.node_role.arn
  subnet_ids      = aws_subnet.private[*].id
  instance_types  = ["g4dn.xlarge"]

  scaling_config {
    desired_size = 1
    min_size     = 0
    max_size     = 4
  }

  labels = {
    "nvidia.com/gpu" = "true"
    workload         = "training"
  }

  taint {
    key    = "nvidia.com/gpu"
    value  = "true"
    effect = "NO_SCHEDULE"
  }

  tags = merge(local.common_labels, { Purpose = "PPO-Training" })
}

# ─────────────────────────────────────────────
# IAM Roles
# ─────────────────────────────────────────────

resource "aws_iam_role" "eks_role" {
  name = "${local.name_prefix}-eks-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
    }]
  })
  tags = local.common_labels
}

resource "aws_iam_role" "node_role" {
  name = "${local.name_prefix}-node-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
  tags = local.common_labels
}

resource "aws_iam_role_policy_attachment" "eks_policy" {
  role       = aws_iam_role.eks_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_iam_role_policy_attachment" "node_policy" {
  for_each = toset([
    "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
  ])
  role       = aws_iam_role.node_role.name
  policy_arn = each.value
}

# ─────────────────────────────────────────────
# RDS — 전투 통계 DB
# ─────────────────────────────────────────────

resource "aws_db_instance" "bot_db" {
  identifier     = "${local.name_prefix}-db"
  engine         = "postgres"
  engine_version = "16.1"
  instance_class = local.current_env.db_size

  allocated_storage     = 50
  max_allocated_storage = 200
  storage_encrypted     = true

  db_name  = "sc2bot"
  username = "sc2admin"
  password = var.environment == "dev" ? "dev-password" : null

  multi_az               = var.environment == "production"
  backup_retention_period = var.environment == "production" ? 30 : 7
  deletion_protection     = var.environment == "production"

  vpc_security_group_ids = [aws_security_group.bot_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.bot_db_subnet.name

  tags = merge(local.common_labels, { Service = "battle-stats" })
}

resource "aws_db_subnet_group" "bot_db_subnet" {
  name       = "${local.name_prefix}-db-subnet"
  subnet_ids = aws_subnet.private[*].id
  tags       = local.common_labels
}

# ─────────────────────────────────────────────
# ElastiCache — Redis 세션/캐시
# ─────────────────────────────────────────────

resource "aws_elasticache_cluster" "bot_cache" {
  cluster_id      = "${local.name_prefix}-cache"
  engine          = "redis"
  node_type       = local.current_env.cache_size
  num_cache_nodes = 1
  port            = 6379

  subnet_group_name  = aws_elasticache_subnet_group.bot_cache_subnet.name
  security_group_ids = [aws_security_group.bot_sg.id]

  tags = merge(local.common_labels, { Service = "game-state-cache" })
}

resource "aws_elasticache_subnet_group" "bot_cache_subnet" {
  name       = "${local.name_prefix}-cache-subnet"
  subnet_ids = aws_subnet.private[*].id
}

# ─────────────────────────────────────────────
# S3 — 모델 저장소 + 리플레이
# ─────────────────────────────────────────────

resource "aws_s3_bucket" "models" {
  bucket = "${local.name_prefix}-models-${var.region}"
  tags   = merge(local.common_labels, { Service = "model-storage" })
}

resource "aws_s3_bucket_versioning" "models_versioning" {
  bucket = aws_s3_bucket.models.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket" "replays" {
  bucket = "${local.name_prefix}-replays-${var.region}"
  tags   = merge(local.common_labels, { Service = "replay-archive" })
}

resource "aws_s3_bucket_lifecycle_configuration" "replays_lifecycle" {
  bucket = aws_s3_bucket.replays.id
  rule {
    id     = "archive-old-replays"
    status = "Enabled"
    transition {
      days          = 30
      storage_class = "GLACIER"
    }
    expiration { days = 365 }
  }
}

# ─────────────────────────────────────────────
# ECR — Docker Registry
# ─────────────────────────────────────────────

resource "aws_ecr_repository" "bot_image" {
  name                 = var.project_name
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
  tags = local.common_labels
}

# ─────────────────────────────────────────────
# Outputs
# ─────────────────────────────────────────────

output "vpc_id" {
  value       = aws_vpc.bot_vpc.id
  description = "VPC ID"
}

output "eks_cluster_name" {
  value       = aws_eks_cluster.bot_cluster.name
  description = "EKS 클러스터 이름"
}

output "eks_endpoint" {
  value       = aws_eks_cluster.bot_cluster.endpoint
  description = "EKS API endpoint"
  sensitive   = true
}

output "db_endpoint" {
  value       = aws_db_instance.bot_db.endpoint
  description = "RDS 엔드포인트"
  sensitive   = true
}

output "model_bucket" {
  value       = aws_s3_bucket.models.bucket
  description = "모델 저장 S3 버킷"
}

output "ecr_url" {
  value       = aws_ecr_repository.bot_image.repository_url
  description = "ECR 레포지토리 URL"
}

output "summary" {
  value = {
    environment    = var.environment
    region         = var.region
    instance_type  = local.instance_type
    gpu_enabled    = var.gpu_enabled
    node_count     = local.current_env.instance_count
    ports          = local.ports
  }
  description = "인프라 요약"
}
