#!/bin/bash
set -e

# ═══════════════════════════════════════════════════════════════════
# Multi-Architecture Docker Build and Push Script
# ═══════════════════════════════════════════════════════════════════
# Builds Docker images for both AMD64 (EC2) and ARM64 (Apple Silicon)
# and pushes to Docker Hub
# ═══════════════════════════════════════════════════════════════════

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="${IMAGE_NAME:-verifact-backend}"
VERSION="${VERSION:-latest}"
DRY_RUN="${1:-}"

# Validate required environment variables
if [ -z "$DOCKER_USERNAME" ]; then
    echo -e "${RED}Error: DOCKER_USERNAME environment variable is not set${NC}"
    echo "Usage: export DOCKER_USERNAME=your-username && ./build-and-push.sh"
    exit 1
fi

FULL_IMAGE_NAME="$DOCKER_USERNAME/$IMAGE_NAME:$VERSION"

echo "═══════════════════════════════════════════════════════════════════"
echo "Multi-Architecture Docker Build"
echo "═══════════════════════════════════════════════════════════════════"
echo "Image: $FULL_IMAGE_NAME"
echo "Platforms: linux/amd64, linux/arm64"
echo "═══════════════════════════════════════════════════════════════════"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Check if user is logged in to Docker Hub
if [ "$DRY_RUN" != "--dry-run" ]; then
    if ! docker info | grep -q "Username: $DOCKER_USERNAME"; then
        echo -e "${YELLOW}Warning: Not logged in to Docker Hub as $DOCKER_USERNAME${NC}"
        echo "Attempting to login..."
        docker login
    fi
fi

# Check if buildx is available
if ! docker buildx version &> /dev/null; then
    echo -e "${RED}Error: Docker Buildx is not available${NC}"
    echo "Please update Docker to a version that supports Buildx"
    exit 1
fi

# Create or use existing builder
BUILDER_NAME="verifact-builder"
if ! docker buildx inspect $BUILDER_NAME &> /dev/null; then
    echo -e "${YELLOW}Creating new buildx builder: $BUILDER_NAME${NC}"
    docker buildx create --name $BUILDER_NAME --use
else
    echo -e "${GREEN}Using existing buildx builder: $BUILDER_NAME${NC}"
    docker buildx use $BUILDER_NAME
fi

# Bootstrap the builder
echo "Bootstrapping builder..."
docker buildx inspect --bootstrap

# Build and push (or just build for dry-run)
echo ""
echo "Building multi-architecture image..."
echo ""

if [ "$DRY_RUN" = "--dry-run" ]; then
    echo -e "${YELLOW}DRY RUN MODE - Image will NOT be pushed to Docker Hub${NC}"
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

# Success message
echo ""
echo "═══════════════════════════════════════════════════════════════════"
if [ "$DRY_RUN" = "--dry-run" ]; then
    echo -e "${GREEN}✓ Build completed successfully (dry-run)${NC}"
else
    echo -e "${GREEN}✓ Build and push completed successfully!${NC}"
    echo ""
    echo "Image pushed to Docker Hub:"
    echo "  - $FULL_IMAGE_NAME"
    echo "  - $DOCKER_USERNAME/$IMAGE_NAME:latest"
    echo ""
    echo "View on Docker Hub:"
    echo "  https://hub.docker.com/r/$DOCKER_USERNAME/$IMAGE_NAME"
fi
echo "═══════════════════════════════════════════════════════════════════"
