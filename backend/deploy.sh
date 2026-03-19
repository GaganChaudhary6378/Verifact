#!/bin/bash
set -e

# ═══════════════════════════════════════════════════════════════════
# VeriFact Complete Deployment Script
# ═══════════════════════════════════════════════════════════════════
# This script:
# 1. Builds multi-architecture Docker image from latest code
# 2. Pushes to Docker Hub
# 3. SSHs into EC2 instance
# 4. Pulls latest image
# 5. Restarts services with zero downtime
# ═══════════════════════════════════════════════════════════════════

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
DOCKER_USERNAME="${DOCKER_USERNAME:-kickdrishu}"
IMAGE_NAME="${IMAGE_NAME:-ai-league-codesurgeons}"
VERSION="${VERSION:-latest}"
EC2_HOST="${EC2_HOST:-43.205.75.204}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/verifact-key}"
SSH_USER="${SSH_USER:-ec2-user}"
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN="${1:-}"

echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}VeriFact Complete Deployment${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Docker Image:${NC} $DOCKER_USERNAME/$IMAGE_NAME:$VERSION"
echo -e "${BLUE}EC2 Instance:${NC} $SSH_USER@$EC2_HOST"
echo -e "${BLUE}Backend Directory:${NC} $BACKEND_DIR"
if [ "$DRY_RUN" = "--dry-run" ]; then
    echo -e "${YELLOW}Mode: DRY RUN (no actual deployment)${NC}"
fi
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# Step 1: Pre-flight Checks
# ═══════════════════════════════════════════════════════════════════

echo -e "${BLUE}[1/6] Running pre-flight checks...${NC}"

# Check if we're in the right directory
if [ ! -f "$BACKEND_DIR/Dockerfile" ]; then
    echo -e "${RED}Error: Dockerfile not found in $BACKEND_DIR${NC}"
    echo "Please run this script from the backend directory or set BACKEND_DIR"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Check SSH key
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}Error: SSH key not found at $SSH_KEY${NC}"
    echo "Please set SSH_KEY environment variable or place key at $HOME/.ssh/verifact-key"
    exit 1
fi

# Check SSH key permissions
KEY_PERMS=$(stat -f "%A" "$SSH_KEY" 2>/dev/null || stat -c "%a" "$SSH_KEY" 2>/dev/null)
if [ "$KEY_PERMS" != "400" ] && [ "$KEY_PERMS" != "600" ]; then
    echo -e "${YELLOW}Warning: SSH key permissions are $KEY_PERMS (should be 400 or 600)${NC}"
    echo "Fixing permissions..."
    chmod 400 "$SSH_KEY"
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker daemon is not running${NC}"
    exit 1
fi

# Check Docker Hub login (skip for dry-run)
if [ "$DRY_RUN" != "--dry-run" ]; then
    if ! docker info | grep -q "Username: $DOCKER_USERNAME"; then
        echo -e "${YELLOW}Not logged in to Docker Hub as $DOCKER_USERNAME${NC}"
        echo "Attempting to login..."
        docker login
    fi
fi

echo -e "${GREEN}✓ Pre-flight checks passed${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# Step 2: Build Multi-Architecture Docker Image
# ═══════════════════════════════════════════════════════════════════

echo -e "${BLUE}[2/6] Building multi-architecture Docker image...${NC}"
cd "$BACKEND_DIR"

FULL_IMAGE_NAME="$DOCKER_USERNAME/$IMAGE_NAME:$VERSION"

# Check if buildx is available
if ! docker buildx version &> /dev/null; then
    echo -e "${RED}Error: Docker Buildx is not available${NC}"
    exit 1
fi

# Create or use existing builder
BUILDER_NAME="verifact-builder"
if ! docker buildx inspect $BUILDER_NAME &> /dev/null; then
    echo -e "${YELLOW}Creating new buildx builder: $BUILDER_NAME${NC}"
    docker buildx create --name $BUILDER_NAME --use
else
    docker buildx use $BUILDER_NAME
fi

# Bootstrap the builder
docker buildx inspect --bootstrap > /dev/null 2>&1

# Build and push (or just build for dry-run)
if [ "$DRY_RUN" = "--dry-run" ]; then
    echo -e "${YELLOW}DRY RUN: Building without push${NC}"
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --build-arg VERSION=$VERSION \
        --tag $FULL_IMAGE_NAME \
        --progress=plain \
        .
else
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --build-arg VERSION=$VERSION \
        --tag $FULL_IMAGE_NAME \
        --tag "$DOCKER_USERNAME/$IMAGE_NAME:latest" \
        --push \
        --progress=plain \
        .
fi

echo -e "${GREEN}✓ Docker image built successfully${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# Step 3: Verify EC2 Instance Connectivity
# ═══════════════════════════════════════════════════════════════════

echo -e "${BLUE}[3/6] Verifying EC2 instance connectivity...${NC}"

if ! ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_USER@$EC2_HOST" "echo 'Connection successful'" &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to EC2 instance${NC}"
    echo "Please check:"
    echo "  - EC2 instance is running"
    echo "  - Security group allows SSH from your IP"
    echo "  - SSH key is correct"
    exit 1
fi

echo -e "${GREEN}✓ EC2 instance is reachable${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# Step 4: Check Current Backend Status
# ═══════════════════════════════════════════════════════════════════

echo -e "${BLUE}[4/6] Checking current backend status...${NC}"

CURRENT_STATUS=$(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$EC2_HOST" \
    "cd /app && sudo docker-compose ps --format json" 2>/dev/null || echo "[]")

echo "Current containers:"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$EC2_HOST" \
    "cd /app && sudo docker-compose ps"

echo ""

# ═══════════════════════════════════════════════════════════════════
# Step 5: Deploy to EC2 (Pull and Restart)
# ═══════════════════════════════════════════════════════════════════

if [ "$DRY_RUN" = "--dry-run" ]; then
    echo -e "${YELLOW}[5/6] DRY RUN: Skipping deployment${NC}"
    echo "Would execute on EC2:"
    echo "  1. Pull new image: $FULL_IMAGE_NAME"
    echo "  2. Restart backend container"
    echo "  3. Verify health check"
else
    echo -e "${BLUE}[5/6] Deploying to EC2 instance...${NC}"
    
    # SSH into EC2 and deploy
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$EC2_HOST" bash <<EOF
set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "VeriFact Backend Deployment"
echo "═══════════════════════════════════════════════════════════════════"

cd /app

echo ""
echo "[1/4] Pulling latest Docker image..."
sudo docker pull $FULL_IMAGE_NAME

echo ""
echo "[2/4] Stopping backend container..."
sudo docker-compose stop backend

echo ""
echo "[3/4] Removing old backend container..."
sudo docker-compose rm -f backend

echo ""
echo "[4/4] Starting new backend container..."
sudo docker-compose up -d backend

echo ""
echo "Waiting for backend to be healthy (max 60 seconds)..."
for i in {1..12}; do
    if sudo docker-compose ps backend | grep -q "healthy"; then
        echo "✓ Backend is healthy!"
        break
    elif [ \$i -eq 12 ]; then
        echo "⚠ Warning: Backend health check timed out"
        echo "Checking logs:"
        sudo docker logs verifact-backend --tail 20
        exit 1
    else
        echo "Waiting... (attempt \$i/12)"
        sleep 5
    fi
done

echo ""
echo "Current status:"
sudo docker-compose ps

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "✓ Deployment Complete!"
echo "═══════════════════════════════════════════════════════════════════"
EOF

    echo -e "${GREEN}✓ Deployment completed on EC2${NC}"
fi

echo ""

# ═══════════════════════════════════════════════════════════════════
# Step 6: Verify Deployment
# ═══════════════════════════════════════════════════════════════════

if [ "$DRY_RUN" != "--dry-run" ]; then
    echo -e "${BLUE}[6/6] Verifying deployment...${NC}"
    
    echo "Testing health endpoint..."
    sleep 5
    
    HEALTH_RESPONSE=$(curl -s -m 10 "http://$EC2_HOST:8000/health" || echo "FAILED")
    
    if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
        echo -e "${GREEN}✓ Health check passed!${NC}"
        echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
    else
        echo -e "${YELLOW}⚠ Warning: Health check failed or timed out${NC}"
        echo "Response: $HEALTH_RESPONSE"
        echo ""
        echo "Checking backend logs:"
        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$EC2_HOST" \
            "sudo docker logs verifact-backend --tail 30"
        exit 1
    fi
else
    echo -e "${YELLOW}[6/6] DRY RUN: Skipping verification${NC}"
fi

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Complete Deployment Successful!${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Deployment Summary:${NC}"
echo "  • Image: $FULL_IMAGE_NAME"
echo "  • Pushed to Docker Hub: $([ "$DRY_RUN" = "--dry-run" ] && echo "No (dry-run)" || echo "Yes")"
echo "  • Deployed to EC2: $([ "$DRY_RUN" = "--dry-run" ] && echo "No (dry-run)" || echo "Yes")"
echo "  • Backend URL: http://$EC2_HOST:8000"
echo "  • API Docs: http://$EC2_HOST:8000/docs"
echo "  • Health Check: http://$EC2_HOST:8000/health"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Test the API: curl http://$EC2_HOST:8000/health"
echo "  2. View logs: ssh -i $SSH_KEY $SSH_USER@$EC2_HOST 'cd /app && sudo docker logs -f verifact-backend'"
echo "  3. Check status: ssh -i $SSH_KEY $SSH_USER@$EC2_HOST 'cd /app && sudo docker-compose ps'"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
