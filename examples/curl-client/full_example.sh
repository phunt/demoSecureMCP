#!/bin/bash

# full_example.sh - Complete end-to-end example of MCP server interaction
# This script demonstrates the full OAuth flow and tool usage

set -euo pipefail

# Source common library
source "$(dirname "$0")/common.sh"

# Initialize client
init_client

# Banner
clear
print_banner "demoSecureMCP - Full Example Demo"

print_info "This demo will show the complete OAuth 2.0 flow and tool usage"
print_info "Make sure Docker containers are running: docker-compose up -d"
echo

# Check prerequisites
print_section "Checking Prerequisites"

# Check if scripts exist
if [ ! -f "${CLIENT_DIR}/get_token.sh" ] || [ ! -f "${CLIENT_DIR}/call_tool.sh" ]; then
    die "Required scripts not found. Please run from the examples/curl-client directory"
fi

# Check service availability
print_step 1 "Checking service availability"

# Check Keycloak
if check_service_availability "Keycloak" "${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token" "405"; then
    print_success "Keycloak is ready"
else
    die "Keycloak is not available. Please ensure Docker services are running."
fi

# Check MCP Server
if check_service_availability "MCP Server" "${MCP_SERVER_URL}/health" "200"; then
    print_success "MCP Server is ready"
else
    die "MCP Server is not available. Please ensure Docker services are running."
fi

# OAuth Discovery
print_section "OAuth Discovery"

print_step 2 "Fetching OAuth metadata"

METADATA=$(curl -sk "${MCP_SERVER_URL}/.well-known/oauth-protected-resource" | jq '.')
if [ -n "$METADATA" ]; then
    print_success "OAuth metadata retrieved"
    print_info "Issuer: $(echo "$METADATA" | jq -r '.issuer')"
    print_info "Resource: $(echo "$METADATA" | jq -r '.resource')"
    SCOPES=$(echo "$METADATA" | jq -r '.scopes_supported[]?' 2>/dev/null | tr '\n' ' ')
    [ -n "$SCOPES" ] && print_info "Supported scopes: $SCOPES"
else
    print_warning "Could not fetch OAuth metadata"
fi

# Token Acquisition
print_section "Token Acquisition"

print_step 3 "Obtaining access token from Keycloak"

# Set credentials explicitly
export CLIENT_SECRET="mcp-server-secret-change-in-production"

# Get token and save to temp file
TOKEN_OUTPUT=$(SAVE_TOKEN=true TOKEN_FILE="${TOKEN_FILE}" "${CLIENT_DIR}/get_token.sh" 2>&1)
TOKEN_EXIT=$?

if [ $TOKEN_EXIT -eq 0 ]; then
    print_success "Access token obtained!"
    
    # Extract token from file
    if [ -f "$TOKEN_FILE" ]; then
        ACCESS_TOKEN=$(cat "$TOKEN_FILE")
        export ACCESS_TOKEN
        
        # Parse token info
        PAYLOAD=$(parse_jwt_payload "$ACCESS_TOKEN")
        if [ -n "$PAYLOAD" ]; then
            print_info "Token expires at: $(echo "$PAYLOAD" | jq -r '.exp' | xargs -I {} date -r {} 2>/dev/null || echo "Unknown")"
        fi
    fi
else
    print_error "Failed to obtain token"
    echo "$TOKEN_OUTPUT" | grep -E "(ERROR|error)" | head -5
    exit 1
fi

# Tool Demonstration
print_section "Tool Demonstration"

# Echo Tool
print_step 4 "Testing Echo Tool"
print_info "Sending: 'Hello from the secure MCP client!'"

RESPONSE=$("${CLIENT_DIR}/call_tool.sh" -k echo "Hello from the secure MCP client!" 2>&1)
if echo "$RESPONSE" | jq -e '.result' >/dev/null 2>&1; then
    ECHO_RESULT=$(echo "$RESPONSE" | jq -r '.result')
    print_success "Echo response: $ECHO_RESULT"
else
    print_error "Echo tool failed"
    echo "$RESPONSE" | head -5
fi

# Timestamp Tool
print_step 5 "Testing Timestamp Tool"

RESPONSE=$("${CLIENT_DIR}/call_tool.sh" -k timestamp 2>&1)
if echo "$RESPONSE" | jq -e '.result.timestamp' >/dev/null 2>&1; then
    TIMESTAMP=$(echo "$RESPONSE" | jq -r '.result.timestamp')
    TIMEZONE=$(echo "$RESPONSE" | jq -r '.result.timezone // "Unknown"')
    print_success "Server time: $TIMESTAMP ($TIMEZONE)"
else
    print_error "Timestamp tool failed"
    echo "$RESPONSE" | head -5
fi

# Calculate Tool
print_step 6 "Testing Calculate Tool"
print_info "Calculating: 10 + 20 + 30"

RESPONSE=$("${CLIENT_DIR}/call_tool.sh" -k calculate add 10 20 30 2>&1)
if echo "$RESPONSE" | jq -e '.result' >/dev/null 2>&1; then
    RESULT=$(echo "$RESPONSE" | jq -r '.result')
    print_success "Calculation result: $RESULT"
else
    print_error "Calculate tool failed"
    echo "$RESPONSE" | head -5
fi

# Tool Discovery
print_step 7 "Discovering Available Tools"

RESPONSE=$("${CLIENT_DIR}/call_tool.sh" -k discover 2>&1)
if echo "$RESPONSE" | jq -e '.tools' >/dev/null 2>&1; then
    TOOL_COUNT=$(echo "$RESPONSE" | jq '.tools | length')
    print_success "Found $TOOL_COUNT available tools"
    echo "$RESPONSE" | jq -r '.tools[] | "  - \(.name): \(.description)"' 2>/dev/null
else
    print_error "Tool discovery failed"
fi

# Error Handling Demo
print_section "Error Handling"

print_step 8 "Testing error scenarios"

# Invalid token
print_info "Testing with invalid token..."
RESPONSE=$(ACCESS_TOKEN="invalid.token.here" "${CLIENT_DIR}/call_tool.sh" -k echo "test" 2>&1 || true)
if echo "$RESPONSE" | grep -qi "error\|failed\|invalid"; then
    print_success "Invalid token correctly rejected"
else
    print_warning "Unexpected response to invalid token"
fi

# No token
print_info "Testing without token..."
RESPONSE=$( (unset ACCESS_TOKEN; rm -f "$TOKEN_FILE"; "${CLIENT_DIR}/call_tool.sh" -k echo "test" 2>&1) || true)
if echo "$RESPONSE" | grep -qi "no access token"; then
    print_success "Missing token correctly handled"
else
    print_warning "Unexpected response to missing token"
fi

# Summary
print_section "Demo Complete!"

print_success "Successfully demonstrated:"
echo "  ✓ OAuth 2.0 client credentials flow"
echo "  ✓ JWT token acquisition from Keycloak"
echo "  ✓ Authenticated API calls to MCP server"
echo "  ✓ All three demo tools (echo, timestamp, calculate)"
echo "  ✓ Tool discovery endpoint"
echo "  ✓ Error handling for authentication failures"
echo

print_info "Next steps:"
echo "  - Review the scripts to understand the implementation"
echo "  - Modify CLIENT_SECRET in production deployments"
echo "  - Implement proper token refresh logic for long-running clients"
echo "  - Add additional error handling as needed"
echo

print_info "For more information, see the README.md file"

# Cleanup
rm -f "$TOKEN_FILE" 