#!/bin/bash
set -e

# ═══════════════════════════════════════════════════════════════════
# VeriFact Backend - EC2 User Data Bootstrap Script
# ═══════════════════════════════════════════════════════════════════
# This script runs on first boot to:
# 1. Install Docker and Docker Compose
# 2. Set up the application directory
# 3. Create docker-compose.yml and .env files
# 4. Pull and start the Docker containers
# ═══════════════════════════════════════════════════════════════════

# Log everything to a file for debugging
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "=========================================="
echo "VeriFact Backend Setup - $(date)"
echo "=========================================="

# Update system packages
echo "[1/9] Updating system packages..."
yum update -y

# Install Docker
echo "[2/9] Installing Docker..."
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
echo "[3/9] Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Verify installations
docker --version
docker-compose --version

# Create application directory
echo "[4/9] Creating application directory..."
mkdir -p /app
cd /app

# Fetch secrets from SSM Parameter Store
echo "[5/9] Fetching configuration from SSM Parameter Store..."
AWS_REGION="${aws_region}"
ENVIRONMENT="${environment}"
PROJECT_NAME="${project_name}"
SSM_PATH="/$PROJECT_NAME/$ENVIRONMENT"

# Function to get SSM parameter
get_ssm_param() {
    aws ssm get-parameter --name "$1" --with-decryption --region "$AWS_REGION" --query 'Parameter.Value' --output text 2>/dev/null || echo ""
}

# Fetch all parameters
OPENAI_API_KEY=$(get_ssm_param "$SSM_PATH/openai_api_key")
ANTHROPIC_API_KEY=$(get_ssm_param "$SSM_PATH/anthropic_api_key")
EXA_API_KEY=$(get_ssm_param "$SSM_PATH/exa_api_key")
BRAVE_SEARCH_API_KEY=$(get_ssm_param "$SSM_PATH/brave_search_api_key")
NEWS_API_KEY=$(get_ssm_param "$SSM_PATH/news_api_key")
COHERE_API_KEY=$(get_ssm_param "$SSM_PATH/cohere_api_key")
REDIS_PASSWORD=$(get_ssm_param "$SSM_PATH/redis_password")
DOCKER_IMAGE=$(get_ssm_param "$SSM_PATH/docker_image")
PRIMARY_LLM=$(get_ssm_param "$SSM_PATH/primary_llm")
FALLBACK_LLM=$(get_ssm_param "$SSM_PATH/fallback_llm")

# Create .env file with fetched values
echo "[6/9] Creating .env file..."
cat > /app/.env <<EOF
# LLM Providers
OPENAI_API_KEY=$OPENAI_API_KEY
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY

# Web Search & News APIs
EXA_API_KEY=$EXA_API_KEY
BRAVE_SEARCH_API_KEY=$BRAVE_SEARCH_API_KEY
NEWS_API_KEY=$NEWS_API_KEY

# Reranking
COHERE_API_KEY=$COHERE_API_KEY

# Redis Configuration
REDIS_HOST=redis-stack
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=$REDIS_PASSWORD

# LLM Configuration
PRIMARY_LLM=$PRIMARY_LLM
FALLBACK_LLM=$FALLBACK_LLM
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096

# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false
LOG_LEVEL=INFO

# CORS
ALLOWED_ORIGINS=http://localhost:3000,chrome-extension://*
EOF

# Create docker-compose.yml for production
echo "[7/9] Creating docker-compose.yml..."
cat > /app/docker-compose.yml <<'COMPOSE_EOF'
services:
  # Redis Stack - Vector DB, Cache, and JSON storage
  redis-stack:
    image: redis/redis-stack-server:latest
    container_name: verifact-redis-stack
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    environment:
      - REDIS_ARGS=--requirepass $$REDIS_PASSWORD
    healthcheck:
      test: ["CMD", "redis-cli", "--pass", "$$REDIS_PASSWORD", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - verifact-network
    restart: unless-stopped

  # VeriFact Backend API
  backend:
    image: $$DOCKER_IMAGE
    container_name: verifact-backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      redis-stack:
        condition: service_healthy
    networks:
      - verifact-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  redis-data:
    driver: local

networks:
  verifact-network:
    driver: bridge
COMPOSE_EOF

# Pull Docker images
echo "[8/9] Pulling Docker images..."
docker-compose pull

# Start services
echo "[9/9] Starting services..."
docker-compose up -d

# Configure automatic restart on reboot
echo "[10/10] Configuring auto-restart on reboot..."
cat > /etc/systemd/system/verifact.service <<'SERVICE_EOF'
[Unit]
Description=VeriFact Backend
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/app
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
SERVICE_EOF

systemctl daemon-reload
systemctl enable verifact.service

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 30

# Check service status
echo "=========================================="
echo "Service Status:"
echo "=========================================="
docker-compose ps

echo "=========================================="
echo "Setup Complete! - $(date)"
echo "=========================================="
echo "Backend API: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000"
echo "API Docs: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000/docs"
echo "=========================================="
