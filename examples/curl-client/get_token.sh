#!/bin/bash

# get_token.sh - Obtain an access token from Keycloak using client credentials flow
# This script demonstrates how to authenticate with the MCP server's Keycloak instance

set -euo pipefail

# Default values (can be overridden by environment variables)
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
KEYCLOAK_REALM="${KEYCLOAK_REALM:-mcp-realm}"
CLIENT_ID="${CLIENT_ID:-mcp-server}"
CLIENT_SECRET="${CLIENT_SECRET:-mcp-server-secret-change-in-production}"
TOKEN_ENDPOINT="${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if required tools are installed
if ! command -v curl &> /dev/null; then
    print_error "curl is not installed. Please install curl to continue."
    exit 1
fi

if ! command -v jq &> /dev/null; then
    print_error "jq is not installed. Please install jq to continue."
    exit 1
fi

# Display configuration
print_info "Keycloak Configuration:"
print_info "  URL: ${KEYCLOAK_URL}"
print_info "  Realm: ${KEYCLOAK_REALM}"
print_info "  Client ID: ${CLIENT_ID}"
print_info "  Token Endpoint: ${TOKEN_ENDPOINT}"
echo

# Check if Keycloak is reachable
print_info "Checking Keycloak availability..."
if curl -s -o /dev/null -w "%{http_code}" "${TOKEN_ENDPOINT}" | grep -q "405"; then
    print_info "Keycloak is available!"
else
    print_error "Keycloak is not reachable at ${KEYCLOAK_URL}"
    print_info "Make sure the Docker containers are running: docker-compose up -d"
    exit 1
fi
echo

# Request access token
print_info "Requesting access token..."
RESPONSE=$(curl -s -X POST "${TOKEN_ENDPOINT}" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials" \
    -d "client_id=${CLIENT_ID}" \
    -d "client_secret=${CLIENT_SECRET}" \
    -d "scope=mcp:read mcp:write mcp:infer" \
    2>&1)

# Check if the request was successful
if ! echo "${RESPONSE}" | jq -e '.access_token' > /dev/null 2>&1; then
    print_error "Failed to obtain access token"
    print_error "Response: ${RESPONSE}"
    
    # Try to parse error details
    if echo "${RESPONSE}" | jq -e '.error' > /dev/null 2>&1; then
        ERROR=$(echo "${RESPONSE}" | jq -r '.error')
        ERROR_DESC=$(echo "${RESPONSE}" | jq -r '.error_description // "No description available"')
        print_error "OAuth Error: ${ERROR}"
        print_error "Description: ${ERROR_DESC}"
    fi
    
    exit 1
fi

# Extract token information
ACCESS_TOKEN=$(echo "${RESPONSE}" | jq -r '.access_token')
TOKEN_TYPE=$(echo "${RESPONSE}" | jq -r '.token_type')
EXPIRES_IN=$(echo "${RESPONSE}" | jq -r '.expires_in')
SCOPE=$(echo "${RESPONSE}" | jq -r '.scope // "Not specified"')

# Decode and display token information (without exposing the full token)
print_info "Token obtained successfully!"
print_info "  Type: ${TOKEN_TYPE}"
print_info "  Expires in: ${EXPIRES_IN} seconds"
print_info "  Scopes: ${SCOPE}"

# Decode JWT payload for additional info (base64 decode the middle part)
if command -v base64 &> /dev/null; then
    # Extract payload (second part of JWT)
    PAYLOAD=$(echo "${ACCESS_TOKEN}" | cut -d'.' -f2)
    
    # Add padding if needed for base64 decode
    case ${#PAYLOAD} in
        *4) ;;
        *3) PAYLOAD="${PAYLOAD}=" ;;
        *2) PAYLOAD="${PAYLOAD}==" ;;
        *1) PAYLOAD="${PAYLOAD}===" ;;
    esac
    
    # Decode and parse
    DECODED=$(echo "${PAYLOAD}" | base64 -d 2>/dev/null | jq -r '.' 2>/dev/null || echo "{}")
    
    if [ "${DECODED}" != "{}" ]; then
        print_info "Token details:"
        print_info "  Subject: $(echo "${DECODED}" | jq -r '.sub // "N/A"')"
        print_info "  Issuer: $(echo "${DECODED}" | jq -r '.iss // "N/A"')"
        print_info "  Client ID: $(echo "${DECODED}" | jq -r '.azp // .aud // "N/A"')"
        
        # Calculate expiration time
        EXP=$(echo "${DECODED}" | jq -r '.exp // 0')
        if [ "${EXP}" -ne 0 ]; then
            CURRENT_TIME=$(date +%s)
            REMAINING=$((EXP - CURRENT_TIME))
            print_info "  Valid for: ${REMAINING} seconds"
        fi
    fi
fi

echo
print_info "Access token saved to environment variable: ACCESS_TOKEN"
print_info "You can use it in other scripts by sourcing this output:"
print_info "  export ACCESS_TOKEN=\"${ACCESS_TOKEN}\""
echo

# Optionally save to file for other scripts to use
if [ "${SAVE_TOKEN:-false}" == "true" ]; then
    TOKEN_FILE="${TOKEN_FILE:-/tmp/mcp_access_token}"
    echo "${ACCESS_TOKEN}" > "${TOKEN_FILE}"
    chmod 600 "${TOKEN_FILE}"
    print_info "Token saved to: ${TOKEN_FILE}"
fi

# Export for use in same shell session
export ACCESS_TOKEN="${ACCESS_TOKEN}"
export TOKEN_TYPE="${TOKEN_TYPE}"

# Return success
exit 0 