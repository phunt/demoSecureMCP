#!/bin/bash

# get_token.sh - Obtain an access token from Keycloak using OAuth 2.0 client credentials flow

set -euo pipefail

# Source common library
source "$(dirname "$0")/common.sh"

# Initialize client
init_client

# Configuration
TOKEN_ENDPOINT="${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token"
SAVE_TOKEN="${SAVE_TOKEN:-false}"

# Show configuration
print_debug "Configuration:"
print_debug "  Keycloak URL: ${KEYCLOAK_URL}"
print_debug "  Realm: ${KEYCLOAK_REALM}"
print_debug "  Client ID: ${CLIENT_ID}"
print_debug "  Token Endpoint: ${TOKEN_ENDPOINT}"

# Check if Keycloak is available
if ! check_service_availability "Keycloak" "${TOKEN_ENDPOINT}" "405"; then
    print_error "Keycloak is not reachable at ${KEYCLOAK_URL}"
    print_info "Make sure Keycloak is running: docker-compose up -d keycloak"
    exit 1
fi

# Request token
print_debug "Requesting access token..."
RESPONSE=$(curl -s -k -X POST "${TOKEN_ENDPOINT}" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials" \
    -d "client_id=${CLIENT_ID}" \
    -d "client_secret=${CLIENT_SECRET}" \
    -d "scope=mcp:read mcp:write mcp:infer")

# Check if request was successful
if [ -z "$RESPONSE" ]; then
    print_error "Empty response from Keycloak"
    exit 1
fi

# Parse response
ACCESS_TOKEN=$(echo "$RESPONSE" | jq -r '.access_token // empty' 2>/dev/null)
ERROR=$(echo "$RESPONSE" | jq -r '.error // empty' 2>/dev/null)
ERROR_DESC=$(echo "$RESPONSE" | jq -r '.error_description // empty' 2>/dev/null)

# Handle errors
if [ -n "$ERROR" ]; then
    print_error "OAuth error: $ERROR"
    [ -n "$ERROR_DESC" ] && print_error "Description: $ERROR_DESC"
    exit 1
fi

if [ -z "$ACCESS_TOKEN" ]; then
    print_error "Failed to obtain access token"
    print_debug "Response: $RESPONSE"
    exit 1
fi

# Validate token format
if ! validate_jwt_format "$ACCESS_TOKEN"; then
    print_error "Invalid JWT token format received"
    exit 1
fi

# Parse token details
TOKEN_TYPE=$(echo "$RESPONSE" | jq -r '.token_type // "Bearer"')
EXPIRES_IN=$(echo "$RESPONSE" | jq -r '.expires_in // 0')
SCOPE=$(echo "$RESPONSE" | jq -r '.scope // "N/A"')

# Decode token payload for display
PAYLOAD=$(parse_jwt_payload "$ACCESS_TOKEN")
if [ -n "$PAYLOAD" ]; then
    ISSUER=$(echo "$PAYLOAD" | jq -r '.iss // "N/A"' 2>/dev/null)
    CLIENT=$(echo "$PAYLOAD" | jq -r '.azp // .client_id // "N/A"' 2>/dev/null)
    EXP_TIME=$(echo "$PAYLOAD" | jq -r '.exp // 0' 2>/dev/null)
    
    if [ "$EXP_TIME" -gt 0 ] 2>/dev/null; then
        EXP_DATE=$(date -r "$EXP_TIME" 2>/dev/null || date -d "@$EXP_TIME" 2>/dev/null || echo "N/A")
    else
        EXP_DATE="N/A"
    fi
else
    ISSUER="N/A"
    CLIENT="N/A"
    EXP_DATE="N/A"
fi

# Display token information
print_success "Access token obtained successfully!"
echo
echo "Token Details:"
echo "  Type: ${TOKEN_TYPE}"
echo "  Expires in: ${EXPIRES_IN} seconds"
echo "  Scope: ${SCOPE}"
echo "  Issuer: ${ISSUER}"
echo "  Client: ${CLIENT}"
echo "  Expires at: ${EXP_DATE}"
echo

# Save token if requested
if [ "$SAVE_TOKEN" = "true" ]; then
    echo -n "$ACCESS_TOKEN" > "$TOKEN_FILE"
    chmod 600 "$TOKEN_FILE"
    print_info "Token saved to: $TOKEN_FILE"
    echo
fi

# Display token for manual use
echo "Access Token:"
echo "$ACCESS_TOKEN"
echo
print_info "Use this token in the Authorization header:"
print_info "  Authorization: Bearer <token>"

# Export for use in same shell session
export ACCESS_TOKEN 