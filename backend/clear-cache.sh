#!/bin/bash
set -e

# ═══════════════════════════════════════════════════════════════════
# Redis Cache Clear Script
# ═══════════════════════════════════════════════════════════════════
# Clears old cached claims to allow fresh verifications with new format
# ═══════════════════════════════════════════════════════════════════

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
EC2_HOST="${EC2_HOST:-43.205.75.204}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/verifact-key}"
SSH_USER="${SSH_USER:-ec2-user}"
REDIS_PASSWORD="${REDIS_PASSWORD:-verifact_redis_pass_CHANGE_ME}"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}VeriFact Redis Cache Clear${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

# Verify SSH connectivity
if ! ssh -i "$SSH_KEY" -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$SSH_USER@$EC2_HOST" "echo 'Connected'" &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to EC2 instance${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Connected to EC2 instance${NC}"
echo ""

# Clear cache
echo -e "${YELLOW}Clearing cached claims from Redis...${NC}"
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$EC2_HOST" bash <<EOF
set -e

echo "Connecting to Redis..."
CACHE_KEYS=\$(sudo docker exec verifact-redis-stack redis-cli --pass "$REDIS_PASSWORD" --scan --pattern "claim_*" | wc -l)

if [ "\$CACHE_KEYS" -eq 0 ]; then
    echo -e "No cached claims found."
    exit 0
fi

echo "Found \$CACHE_KEYS cached claim(s)"
echo ""
echo "Deleting cached claims..."

# Delete all claim_* keys
sudo docker exec verifact-redis-stack redis-cli --pass "$REDIS_PASSWORD" --scan --pattern "claim_*" | \
    xargs -I {} sudo docker exec verifact-redis-stack redis-cli --pass "$REDIS_PASSWORD" DEL {}

echo ""
echo -e "✓ Cache cleared successfully!"
echo ""

# Verify cache is empty
REMAINING=\$(sudo docker exec verifact-redis-stack redis-cli --pass "$REDIS_PASSWORD" --scan --pattern "claim_*" | wc -l)
echo "Remaining cached claims: \$REMAINING"
EOF

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Cache Clear Complete${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. New verifications will create cache entries with full data"
echo "  2. Test by verifying the same claim twice"
echo "  3. Second verification (cache hit) should show all details"
echo ""
