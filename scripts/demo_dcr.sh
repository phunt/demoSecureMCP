#!/usr/bin/env bash
#
# demo_dcr.sh - Demonstrate Dynamic Client Registration
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
KEYCLOAK_REALM="${KEYCLOAK_REALM:-mcp-realm}"

echo -e "${BLUE}Dynamic Client Registration Demo${NC}"
echo "================================="
echo

# Step 1: Check if services are running
echo -e "${YELLOW}Step 1: Checking services...${NC}"
if ! curl -s "${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/.well-known/openid-configuration" > /dev/null 2>&1; then
    echo -e "${RED}Error: Keycloak is not accessible at ${KEYCLOAK_URL}${NC}"
    echo "Please run: docker-compose up -d"
    exit 1
fi
echo -e "${GREEN}✓ Keycloak is running${NC}"

# Step 2: Get OAuth metadata
echo -e "\n${YELLOW}Step 2: Discovering OAuth endpoints...${NC}"
METADATA=$(curl -s "${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/.well-known/openid-configuration")
REGISTRATION_ENDPOINT=$(echo "$METADATA" | jq -r '.registration_endpoint // empty')

if [[ -z "$REGISTRATION_ENDPOINT" ]]; then
    echo -e "${RED}Error: No registration endpoint found${NC}"
    echo "DCR may not be enabled in this realm"
    exit 1
fi

echo -e "${GREEN}✓ Registration endpoint: ${REGISTRATION_ENDPOINT}${NC}"

# Step 3: Register a client
echo -e "\n${YELLOW}Step 3: Registering a new client...${NC}"

CLIENT_METADATA='{
  "client_name": "Demo MCP Client",
  "grant_types": ["client_credentials"],
  "response_types": ["none"],
  "token_endpoint_auth_method": "client_secret_basic",
  "scope": "openid profile email",
  "contacts": ["demo@example.com"]
}'

echo "Client metadata:"
echo "$CLIENT_METADATA" | jq .

# Note: In production, you would use an initial access token
echo -e "\n${YELLOW}Attempting registration...${NC}"
RESPONSE=$(curl -s -X POST \
    "${REGISTRATION_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "$CLIENT_METADATA" 2>&1 || true)

if echo "$RESPONSE" | jq -e '.client_id' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Client registered successfully!${NC}"
    
    CLIENT_ID=$(echo "$RESPONSE" | jq -r '.client_id')
    CLIENT_SECRET=$(echo "$RESPONSE" | jq -r '.client_secret // empty')
    
    echo
    echo "Registration details:"
    echo "  Client ID: $CLIENT_ID"
    echo "  Client Secret: ${CLIENT_SECRET:-<not provided>}"
    
    # Step 4: Test the client
    if [[ -n "$CLIENT_SECRET" ]]; then
        echo -e "\n${YELLOW}Step 4: Testing client credentials...${NC}"
        
        TOKEN_RESPONSE=$(curl -s -X POST \
            "${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -d "grant_type=client_credentials" \
            -d "client_id=${CLIENT_ID}" \
            -d "client_secret=${CLIENT_SECRET}" \
            -d "scope=openid")
        
        if echo "$TOKEN_RESPONSE" | jq -e '.access_token' > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Successfully obtained access token!${NC}"
            
            ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')
            echo
            echo "Token details:"
            echo "$ACCESS_TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | jq . || echo "  (Unable to decode)"
        else
            echo -e "${RED}Failed to get token${NC}"
            echo "$TOKEN_RESPONSE" | jq .
        fi
    fi
else
    echo -e "${RED}Registration failed${NC}"
    echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"
    echo
    echo "Note: This realm may require an initial access token for DCR."
    echo "Run ./scripts/setup_dcr.sh to configure DCR properly."
fi

echo -e "\n${BLUE}Demo complete!${NC}" 