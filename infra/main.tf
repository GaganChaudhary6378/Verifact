terraform {
  required_version = ">= 1.0"
  
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

# Data source to get the latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Common tags for all resources
locals {
  common_tags = {
    Environment = var.environment
    Team        = var.team_name
    Purpose     = var.purpose
    ManagedBy   = "Terraform"
  }
}

# KMS Key for EBS encryption
resource "aws_kms_key" "ebs" {
  description             = "KMS key for ${var.project_name} EBS volume encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-ebs-key"
  })
}

resource "aws_kms_alias" "ebs" {
  name          = "alias/${var.project_name}-ebs-${var.environment}"
  target_key_id = aws_kms_key.ebs.key_id
}

# IAM Role for EC2 to access SSM Parameter Store
resource "aws_iam_role" "ec2_ssm_role" {
  name = "${var.project_name}-ec2-ssm-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy for reading SSM parameters
resource "aws_iam_role_policy" "ec2_ssm_policy" {
  name = "${var.project_name}-ec2-ssm-policy"
  role = aws_iam_role.ec2_ssm_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/${var.project_name}/${var.environment}/*"
      }
    ]
  })
}

# Instance profile for EC2
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-ec2-profile-${var.environment}"
  role = aws_iam_role.ec2_ssm_role.name

  tags = local.common_tags
}

# SSM Parameters for sensitive data
resource "aws_ssm_parameter" "openai_api_key" {
  name  = "/${var.project_name}/${var.environment}/openai_api_key"
  type  = "SecureString"
  value = var.openai_api_key

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-openai-key"
  })
}

resource "aws_ssm_parameter" "anthropic_api_key" {
  name  = "/${var.project_name}/${var.environment}/anthropic_api_key"
  type  = "SecureString"
  value = var.anthropic_api_key

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-anthropic-key"
  })
}

resource "aws_ssm_parameter" "exa_api_key" {
  name  = "/${var.project_name}/${var.environment}/exa_api_key"
  type  = "SecureString"
  value = var.exa_api_key

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-exa-key"
  })
}

resource "aws_ssm_parameter" "brave_search_api_key" {
  name  = "/${var.project_name}/${var.environment}/brave_search_api_key"
  type  = "SecureString"
  value = var.brave_search_api_key

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-brave-key"
  })
}

resource "aws_ssm_parameter" "news_api_key" {
  name  = "/${var.project_name}/${var.environment}/news_api_key"
  type  = "SecureString"
  value = var.news_api_key

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-news-key"
  })
}

resource "aws_ssm_parameter" "cohere_api_key" {
  name  = "/${var.project_name}/${var.environment}/cohere_api_key"
  type  = "SecureString"
  value = var.cohere_api_key

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-cohere-key"
  })
}

resource "aws_ssm_parameter" "redis_password" {
  name  = "/${var.project_name}/${var.environment}/redis_password"
  type  = "SecureString"
  value = var.redis_password

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-redis-password"
  })
}

resource "aws_ssm_parameter" "docker_image" {
  name  = "/${var.project_name}/${var.environment}/docker_image"
  type  = "String"
  value = var.docker_image

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-docker-image"
  })
}

resource "aws_ssm_parameter" "primary_llm" {
  name  = "/${var.project_name}/${var.environment}/primary_llm"
  type  = "String"
  value = var.primary_llm

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-primary-llm"
  })
}

resource "aws_ssm_parameter" "fallback_llm" {
  name  = "/${var.project_name}/${var.environment}/fallback_llm"
  type  = "String"
  value = var.fallback_llm

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-fallback-llm"
  })
}

# Security Group for EC2 instance
resource "aws_security_group" "verifact_sg" {
  name        = "${var.project_name}-backend-sg-${var.environment}"
  description = "Security group for VeriFact backend EC2 instance"

  # SSH access
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  # Backend API access
  ingress {
    description = "Backend API"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound traffic (for pulling Docker images, API calls, etc.)
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-backend-sg"
  })
}

# EC2 Instance
resource "aws_instance" "verifact_backend" {
  ami           = data.aws_ami.amazon_linux_2023.id
  instance_type = var.instance_type
  key_name      = var.ssh_key_name

  vpc_security_group_ids = [aws_security_group.verifact_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
    encrypted   = true
    kms_key_id  = aws_kms_key.ebs.arn
    tags = merge(local.common_tags, {
      Name = "${var.project_name}-backend-root"
    })
  }

  user_data = templatefile("${path.module}/user-data.sh", {
    aws_region   = var.aws_region
    environment  = var.environment
    project_name = var.project_name
  })

  tags = merge(local.common_tags, {
    Name        = "${var.project_name}-backend-${var.environment}"
    Application = "VeriFact"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Elastic IP for stable public IP
resource "aws_eip" "verifact_eip" {
  instance = aws_instance.verifact_backend.id
  domain   = "vpc"

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-backend-eip"
  })
}
