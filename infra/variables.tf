variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "ssh_key_name" {
  description = "Name of the SSH key pair to use for EC2 instance"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH into the instance (restrict to your IP for security)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "team_name" {
  description = "Team name for resource tagging"
  type        = string
  default     = "codesurgeons"
}

variable "purpose" {
  description = "Purpose/project name for resource tagging"
  type        = string
  default     = "AI-League"
}

variable "project_name" {
  description = "Project name used in resource naming (lowercase, no spaces)"
  type        = string
  default     = "verifact"
}

variable "docker_image" {
  description = "Docker image to deploy (format: username/image:tag)"
  type        = string
}

# API Keys
variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key"
  type        = string
  sensitive   = true
}

variable "exa_api_key" {
  description = "Exa API key for web search"
  type        = string
  sensitive   = true
  default     = ""
}

variable "brave_search_api_key" {
  description = "Brave Search API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "news_api_key" {
  description = "News API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "cohere_api_key" {
  description = "Cohere API key for reranking"
  type        = string
  sensitive   = true
  default     = ""
}

variable "redis_password" {
  description = "Redis password (change for production)"
  type        = string
  sensitive   = true
  default     = "verifact_redis_pass"
}

variable "primary_llm" {
  description = "Primary LLM model"
  type        = string
  default     = "gpt-4o-mini"
}

variable "fallback_llm" {
  description = "Fallback LLM model"
  type        = string
  default     = "claude-3-5-sonnet-20241022"
}
