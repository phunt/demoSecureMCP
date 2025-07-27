#!/bin/bash
# Script to check for DCR-registered clients in Keycloak

KEYCLOAK_URL="http://localhost:8080"
KEYCLOAK_REALM="mcp-realm"
ADMIN_USER="admin"
ADMIN_PASSWORD="admin_password"

echo "=== Checking for DCR-registered clients in Keycloak ==="
echo

# Get admin token
echo "1. Getting admin token..."
ADMIN_TOKEN=$(curl -s -X POST \
  "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${ADMIN_USER}" \
  -d "password=${ADMIN_PASSWORD}" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | jq -r '.access_token')

if [ "$ADMIN_TOKEN" == "null" ] || [ -z "$ADMIN_TOKEN" ]; then
    echo "Error: Failed to get admin token"
    exit 1
fi
echo "✓ Admin token obtained"

# List all clients
echo -e "\n2. Listing all clients in ${KEYCLOAK_REALM} realm:"
echo "----------------------------------------"
curl -s -X GET \
  "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/clients" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" | jq -r '.[] | "\(.clientId) - \(.name // "No name") - Created: \(.attributes.createdBy // "Static")"'

# Check for MCP server clients
echo -e "\n3. Checking MCP server client details:"
echo "----------------------------------------"

# Get the mcp-server client specifically
MCP_CLIENT=$(curl -s -X GET \
  "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/clients?clientId=mcp-server" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" | jq -r '.[0]')

if [ "$MCP_CLIENT" != "null" ] && [ -n "$MCP_CLIENT" ]; then
    CLIENT_ID=$(echo "$MCP_CLIENT" | jq -r '.id')
    
    # Get detailed client info
    CLIENT_DETAILS=$(curl -s -X GET \
      "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/clients/${CLIENT_ID}" \
      -H "Authorization: Bearer ${ADMIN_TOKEN}")
    
    echo "Static mcp-server client found:"
    echo "$CLIENT_DETAILS" | jq '{
        clientId: .clientId,
        name: .name,
        protocol: .protocol,
        publicClient: .publicClient,
        serviceAccountsEnabled: .serviceAccountsEnabled,
        attributes: .attributes
    }'
fi

# Check for dynamically registered clients
echo -e "\n4. Checking for dynamically registered clients:"
echo "----------------------------------------"

# DCR clients typically have:
# - Names starting with "MCP Server ("
# - Generated client IDs (not human-readable)
# - Registration access tokens

DCR_CLIENTS=$(curl -s -X GET \
  "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/clients" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" | jq -r '.[] | select(.name // "" | contains("MCP Server ("))')

if [ -n "$DCR_CLIENTS" ] && [ "$DCR_CLIENTS" != "" ]; then
    echo "Found DCR-registered clients:"
    echo "$DCR_CLIENTS" | jq '{clientId: .clientId, name: .name, registrationAccessToken: .registrationAccessToken}'
else
    echo "No DCR-registered clients found"
fi

# Check for local DCR registration
echo -e "\n5. Checking for local DCR registration file:"
echo "----------------------------------------"
if [ -f ".dcr_client.json" ]; then
    echo "✓ Found .dcr_client.json"
    cat .dcr_client.json | jq '{client_id: .client_id, client_name: .client_name, registered_at: .registered_at}'
else
    echo "✗ No .dcr_client.json file found"
fi

echo -e "\n=== Summary ==="
echo "To identify DCR clients vs static clients:"
echo "- Static clients: Have predefined client IDs (like 'mcp-server')"
echo "- DCR clients: Have generated UUIDs as client IDs and names like 'MCP Server (secure-mcp-server)'"
echo "- DCR clients may have registration access tokens"
echo "- Local .dcr_client.json file indicates the server has registered via DCR" 