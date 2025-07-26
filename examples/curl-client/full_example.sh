#!/bin/bash

# full_example.sh - Complete end-to-end example of MCP server interaction
# This script demonstrates the full OAuth flow and tool usage

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default values
MCP_SERVER_URL="${MCP_SERVER_URL:-https://localhost}"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_section() {
    echo
    echo -e "${CYAN}==== $1 ====${NC}"
    echo
}

print_step() {
    echo -e "${YELLOW}[STEP $1]${NC} $2"
}

# Banner
clear
echo -e "${BLUE}"
cat << 'EOF'
 __  __  ____ ____    ____                           
|  \/  |/ ___|  _ \  / ___|  ___ _ ____   _____ _ __ 
| |\/| | |   | |_) | \___ \ / _ \ '__\ \ / / _ \ '__|
| |  | | |___|  __/   ___) |  __/ |   \ V /  __/ |   
|_|  |_|\____|_|     |____/ \___|_|    \_/ \___|_|   
                                                      
        Secure MCP Server - Full Example Demo
EOF
echo -e "${NC}"

print_info "This demo will show the complete OAuth 2.0 flow and tool usage"
print_info "Make sure Docker containers are running: docker-compose up -d"
echo

# Check prerequisites
print_section "Checking Prerequisites"

# Check if scripts exist
if [ ! -f "${SCRIPT_DIR}/get_token.sh" ] || [ ! -f "${SCRIPT_DIR}/call_tool.sh" ]; then
    print_error "Required scripts not found. Please run from the examples/curl-client directory"
    exit 1
fi

# Check for required tools
for tool in curl jq; do
    if ! command -v ${tool} &> /dev/null; then
        print_error "${tool} is not installed. Please install it to continue."
        exit 1
    fi
done
print_info "All prerequisites met!"

# Step 1: Check services
print_section "Service Health Check"
print_step "1" "Checking Keycloak availability"

if curl -s -o /dev/null -w "%{http_code}" "${KEYCLOAK_URL}/realms/mcp-realm/protocol/openid-connect/token" | grep -q "405"; then
    print_info "Keycloak is running at ${KEYCLOAK_URL}"
else
    print_error "Keycloak is not available. Please start the services:"
    print_info "  cd ../.. && docker-compose up -d"
    exit 1
fi

print_step "2" "Checking MCP Server availability"
# Use -k for self-signed certificates
if curl -sk -o /dev/null -w "%{http_code}" "${MCP_SERVER_URL}/health" | grep -q "200"; then
    print_info "MCP Server is running at ${MCP_SERVER_URL}"
else
    print_error "MCP Server is not available. Please check the logs:"
    print_info "  docker-compose logs mcp-server"
    exit 1
fi

# Step 2: OAuth Discovery
print_section "OAuth 2.0 Discovery"
print_step "3" "Fetching Protected Resource Metadata"

METADATA=$(curl -sk "${MCP_SERVER_URL}/.well-known/oauth-protected-resource" 2>/dev/null)
if [ -n "${METADATA}" ]; then
    print_info "Protected Resource Metadata:"
    echo "${METADATA}" | jq . || echo "${METADATA}"
    
    # Extract information
    ISSUER=$(echo "${METADATA}" | jq -r '.issuer // "Not found"')
    RESOURCE=$(echo "${METADATA}" | jq -r '.resource // "Not found"')
    SCOPES=$(echo "${METADATA}" | jq -r '.scopes_supported[]? // empty' | tr '\n' ' ')
    
    print_info "  Issuer: ${ISSUER}"
    print_info "  Resource: ${RESOURCE}"
    print_info "  Supported Scopes: ${SCOPES}"
else
    print_warning "Could not fetch metadata, continuing anyway..."
fi

# Step 3: Get Access Token
print_section "OAuth 2.0 Authentication"
print_step "4" "Obtaining access token via client credentials flow"

# Run get_token.sh and capture output
export SAVE_TOKEN=true
export TOKEN_FILE="/tmp/mcp_demo_token"
export CLIENT_SECRET="mcp-server-secret-change-in-production"

print_info "Running: ./get_token.sh"
if "${SCRIPT_DIR}/get_token.sh"; then
    print_info "Token obtained successfully!"
    
    # Read the token
    if [ -f "${TOKEN_FILE}" ]; then
        ACCESS_TOKEN=$(cat "${TOKEN_FILE}")
        print_info "Token saved to: ${TOKEN_FILE}"
    else
        print_error "Token file not found"
        exit 1
    fi
else
    print_error "Failed to obtain access token"
    exit 1
fi

# Step 4: Test unauthorized access
print_section "Security Verification"
print_step "5" "Testing unauthorized access (should fail)"

print_info "Attempting to call API without token..."
UNAUTH_RESPONSE=$(curl -sk -X GET "${MCP_SERVER_URL}/api/v1/tools" 2>&1)
if echo "${UNAUTH_RESPONSE}" | grep -q "401\|Unauthorized\|credentials"; then
    print_info "✓ Correctly rejected unauthorized request"
else
    print_warning "Unexpected response to unauthorized request"
fi

# Step 5: Tool Discovery
print_section "Tool Discovery"
print_step "6" "Discovering available tools"

if "${SCRIPT_DIR}/call_tool.sh" -k -f "${TOKEN_FILE}" discover; then
    print_info "Tool discovery successful!"
else
    print_error "Tool discovery failed"
fi

# Step 6: Demo each tool
print_section "Tool Demonstrations"

# Echo tool
print_step "7" "Testing Echo Tool (requires mcp:read scope)"
echo
if "${SCRIPT_DIR}/call_tool.sh" -k -f "${TOKEN_FILE}" echo "Hello from the secure MCP server!"; then
    print_info "Echo tool test passed!"
else
    print_error "Echo tool test failed"
fi

sleep 1

# Timestamp tool
print_step "8" "Testing Timestamp Tool (requires mcp:read scope)"
echo
if "${SCRIPT_DIR}/call_tool.sh" -k -f "${TOKEN_FILE}" timestamp; then
    print_info "Timestamp tool test passed!"
else
    print_error "Timestamp tool test failed"
fi

sleep 1

# Calculate tool
print_step "9" "Testing Calculate Tool (requires mcp:write scope)"
echo
EXPRESSION="add 10 5 3"
print_info "Operation: ${EXPRESSION}"
if "${SCRIPT_DIR}/call_tool.sh" -k -f "${TOKEN_FILE}" calculate ${EXPRESSION}; then
    print_info "Calculate tool test passed!"
else
    print_error "Calculate tool test failed"
fi

# Step 7: Error handling demo
print_section "Error Handling Examples"

print_step "10" "Testing with invalid token"
echo
INVALID_TOKEN="invalid.jwt.token"
"${SCRIPT_DIR}/call_tool.sh" -k -t "${INVALID_TOKEN}" echo "This should fail" || true

print_step "11" "Testing with missing scope"
echo
print_info "If the token doesn't have mcp:write scope, calculate should fail:"
print_info "(This may pass if your token has all scopes)"
"${SCRIPT_DIR}/call_tool.sh" -k -f "${TOKEN_FILE}" calculate add 1 1 || true

# Summary
print_section "Demo Complete!"

cat << EOF
This demo showed:
✓ OAuth 2.0 client credentials flow with Keycloak
✓ JWT token validation
✓ Scope-based authorization
✓ All three MCP tools (echo, timestamp, calculate)
✓ Error handling for authentication/authorization

Next steps:
1. Examine the scripts to understand the implementation
2. Try modifying the client credentials in Keycloak
3. Create new tools with different scope requirements
4. Integrate this pattern into your own applications

For more information:
- README: ${SCRIPT_DIR}/README.md
- Main project: ${SCRIPT_DIR}/../..
EOF

# Cleanup
rm -f "${TOKEN_FILE}"

print_info "Thank you for trying the Secure MCP Server!"
exit 0 