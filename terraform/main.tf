# OrthoFlow AI — Terraform AWS Infrastructure
# This is the migration target. Local dev uses Docker Compose.
# Apply when ready to move to cloud.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state — uncomment when ready
  # backend "s3" {
  #   bucket = "orthoflow-terraform-state"
  #   key    = "prod/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  default = "us-east-1"
}

variable "environment" {
  default = "prod"
}

variable "project" {
  default = "orthoflow"
}

# ── VPC ───────────────────────────────────────────────────────────────────────
module "vpc" {
  source = "./modules/vpc"
  # Defined when ready
}

# ── RDS (PostgreSQL) ──────────────────────────────────────────────────────────
# module "rds" {
#   source          = "./modules/rds"
#   vpc_id          = module.vpc.vpc_id
#   subnet_ids      = module.vpc.private_subnet_ids
#   instance_class  = "db.t3.medium"
#   db_name         = "orthoflow"
#   engine_version  = "16.3"
# }

# ── S3 (Invoice Storage) ─────────────────────────────────────────────────────
# module "s3" {
#   source      = "./modules/s3"
#   bucket_name = "orthoflow-invoices-${var.environment}"
#   # HIPAA: encryption at rest, versioning, access logging
# }

# ── ECS Fargate (Backend + Worker) ────────────────────────────────────────────
# module "ecs" {
#   source          = "./modules/ecs"
#   vpc_id          = module.vpc.vpc_id
#   subnet_ids      = module.vpc.private_subnet_ids
#   backend_image   = "ghcr.io/melanin-tech/orthoflow-ai/backend:latest"
#   worker_image    = "ghcr.io/melanin-tech/orthoflow-ai/backend:latest"
#   worker_command  = ["python", "-m", "app.workers.main"]
# }

# ── Bedrock (LLM) ────────────────────────────────────────────────────────────
# No infra needed — Bedrock is serverless. Just IAM policy:
# resource "aws_iam_policy" "bedrock_access" {
#   name = "orthoflow-bedrock-access"
#   policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [{
#       Effect   = "Allow"
#       Action   = ["bedrock:InvokeModel"]
#       Resource = "arn:aws:bedrock:us-east-1::foundation-model/anthropic.*"
#     }]
#   })
# }

# ── SES (Email Ingestion) ────────────────────────────────────────────────────
# resource "aws_ses_receipt_rule_set" "orthoflow" {
#   rule_set_name = "orthoflow-inbound"
# }
