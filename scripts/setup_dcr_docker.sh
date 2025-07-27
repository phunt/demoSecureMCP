#!/bin/sh
#
# setup_dcr_docker.sh - Set up DCR for Docker environments
# This script should be run from inside a Docker container to ensure
# the initial access token is generated with the correct issuer URL
#

set -eu

# Configuration for Docker environment
KEYCLOAK_URL="http://keycloak:8080"
KEYCLOAK_REALM="mcp-realm"
KEYCLOAK_ADMIN="admin"
KEYCLOAK_ADMIN_PASSWORD="admin_password"

echo "[INFO] Setting up DCR for Docker environment"
echo "[INFO] Using Keycloak URL: $KEYCLOAK_URL"

# Get admin token
echo "[INFO] Getting admin token..."
ADMIN_TOKEN=$(curl -s -X POST \
    "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=${KEYCLOAK_ADMIN}" \
    -d "password=${KEYCLOAK_ADMIN_PASSWORD}" \
    -d "grant_type=password" \
    -d "client_id=admin-cli" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ADMIN_TOKEN" ]; then
    echo "[ERROR] Failed to get admin token"
    exit 1
fi

echo "[SUCCESS] Admin token obtained"

# Create initial access token
echo "[INFO] Creating initial access token..."
INITIAL_TOKEN_RESPONSE=$(curl -s -X POST \
    "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/clients-initial-access" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
        "count": 1,
        "expiration": 3600
    }')

INITIAL_TOKEN=$(echo "$INITIAL_TOKEN_RESPONSE" | grep -o '"token":"[^"]*' | cut -d'"' -f4)

if [ -z "$INITIAL_TOKEN" ]; then
    echo "[ERROR] Failed to create initial access token"
    echo "Response: $INITIAL_TOKEN_RESPONSE"
    exit 1
fi

echo "[SUCCESS] Initial access token created"
echo
echo "DCR_INITIAL_ACCESS_TOKEN=$INITIAL_TOKEN"
echo
echo "This token was generated with issuer URL: $KEYCLOAK_URL"
echo "Use this token in your .env.docker file" 