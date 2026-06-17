#!/bin/bash
# =============================================================================
# 一键部署/检查脚本 — 活动内容生产工作流
# 设计文档 v3.2，第十章
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "============================================"
echo "  活动内容生产工作流 — 部署检查"
echo "============================================"
echo ""

# --- 检查前置条件 ---
echo -e "${YELLOW}[1/6]${NC} Checking prerequisites..."

if ! command -v docker &>/dev/null; then
    echo -e "${RED}✗ Docker not installed${NC}"
    echo "  Install: https://docs.docker.com/engine/install/"
    exit 1
fi
echo -e "${GREEN}✓${NC} Docker: $(docker --version)"

if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null; then
    echo -e "${RED}✗ Docker Compose not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Docker Compose available"

# --- 检查 .env ---
echo ""
echo -e "${YELLOW}[2/6]${NC} Checking environment configuration..."

if [ ! -f "$DEPLOY_DIR/.env" ]; then
    echo -e "${RED}✗ .env file not found${NC}"
    echo "  Copy .env.example to .env and fill in the required values:"
    echo "  cp $DEPLOY_DIR/.env.example $DEPLOY_DIR/.env"
    exit 1
fi
echo -e "${GREEN}✓${NC} .env exists"

# Source .env and check critical variables
source "$DEPLOY_DIR/.env"

MISSING_VARS=()
for var in N8N_HOST N8N_ENCRYPTION_KEY FEISHU_APP_ID FEISHU_APP_SECRET GAODING_API_KEY TONGYI_WANXIANG_API_KEY INTERNAL_WEBHOOK_TOKEN; do
    if [ -z "${!var:-}" ] || [ "${!var}" == "changeme" ] || [[ "${!var}" == *"your-"* ]] || [[ "${!var}" == *"<"*">"* ]]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠ The following variables need to be configured in .env:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
else
    echo -e "${GREEN}✓${NC} All critical environment variables configured"
fi

# --- 检查 TLS 证书 ---
echo ""
echo -e "${YELLOW}[3/6]${NC} Checking TLS certificates..."

CERT_DIR="$DEPLOY_DIR/certs"
if [ ! -d "$CERT_DIR" ] || [ ! -f "$CERT_DIR/fullchain.pem" ] || [ ! -f "$CERT_DIR/privkey.pem" ]; then
    echo -e "${YELLOW}⚠ TLS certificates not found in $CERT_DIR${NC}"
    echo "  You need valid TLS certificates for the webhook to work."
    echo "  Generate with Let's Encrypt or place your certificates in:"
    echo "    $CERT_DIR/fullchain.pem"
    echo "    $CERT_DIR/privkey.pem"
else
    echo -e "${GREEN}✓${NC} TLS certificates found"
fi

# --- 检查 Nginx 配置 ---
echo ""
echo -e "${YELLOW}[4/6]${NC} Checking Nginx configuration..."

if grep -q '${N8N_HOST}' "$DEPLOY_DIR/nginx.conf"; then
    echo -e "${YELLOW}⚠ nginx.conf contains placeholder \${N8N_HOST}${NC}"
    echo "  Replace \${N8N_HOST} in nginx.conf with your actual domain: $N8N_HOST"
else
    echo -e "${GREEN}✓${NC} Nginx configuration ready"
fi

# --- 检查品牌配置 ---
echo ""
echo -e "${YELLOW}[5/6]${NC} Checking brand configuration..."

BRAND_CONFIG="../config/brand_config.json"
if grep -q '待填入' "$BRAND_CONFIG" 2>/dev/null; then
    echo -e "${YELLOW}⚠ brand_config.json contains placeholder template IDs${NC}"
    echo "  Update gaoding_templates with actual template IDs from Gaoding platform."
else
    echo -e "${GREEN}✓${NC} Brand configuration ready"
fi

# --- 启动服务 ---
echo ""
echo -e "${YELLOW}[6/6]${NC} Starting services..."

read -p "Start Docker Compose services now? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd "$DEPLOY_DIR"
    docker compose up -d
    echo ""
    echo -e "${GREEN}✓${NC} Services started!"
    echo ""
    echo "Next steps:"
    echo "  1. Verify webhook: curl https://$N8N_HOST/webhook/test"
    echo "  2. Login n8n: https://$N8N_HOST/ (internal network only)"
    echo "  3. Import workflows from workflows/ directory"
    echo "  4. Configure n8n credentials"
    echo "  5. Test with a sample record in Feishu"
else
    echo ""
    echo "Run 'docker compose up -d' when ready."
fi

echo ""
echo "============================================"
echo "  Check complete"
echo "============================================"
