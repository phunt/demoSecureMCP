#!/usr/bin/env bash
#
# Run tests in non-DCR mode with static client credentials
#
# Usage: ./scripts/run_tests_non_dcr.sh

set -euo pipefail

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

echo "Running tests in non-DCR mode..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment not found. Please run: python -m venv .venv"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check if .env.test exists
if [ ! -f ".env.test" ]; then
    echo "Creating .env.test file..."
    cat > .env.test << 'EOF'
# Test Environment Configuration
DEBUG=true
CONTAINER_ENV=false
USE_DCR=false

# Keycloak Configuration
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=mcp-realm
KEYCLOAK_CLIENT_ID=mcp-server
KEYCLOAK_CLIENT_SECRET=mcp-server-secret-change-in-production

# OAuth Configuration
OAUTH_ISSUER=http://localhost:8080/realms/mcp-realm
OAUTH_AUDIENCE=mcp-server
OAUTH_JWKS_URI=http://localhost:8080/realms/mcp-realm/protocol/openid-connect/certs

# MCP Configuration
MCP_RESOURCE_IDENTIFIER=https://mcp-server.example.com
MCP_SUPPORTED_SCOPES=mcp:read,mcp:write,mcp:infer

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
EOF
fi

# Export environment variables
echo "Loading test environment variables..."
set -a
source .env.test
set +a

# Ensure docker services are running with correct env
echo "Ensuring Docker services are running in non-DCR mode..."
docker compose --env-file .env.docker ps mcp-server --format "table {{.Status}}" | grep -q "Up" || {
    echo "MCP server is not running. Starting services..."
    docker compose --env-file .env.docker up -d
    sleep 5
}

# Run tests
echo "Running pytest..."
python -m pytest tests/ "$@"

echo "Tests completed!" 