# Keycloak Configuration

This directory contains the Keycloak realm configuration for the secure MCP server.

## Quick Start

```bash
# Start Keycloak and dependencies
docker compose up -d postgres keycloak redis

# Wait for Keycloak to be ready (check logs)
docker compose logs -f keycloak

# Test the configuration
python scripts/test_keycloak.py
```

## Access Keycloak Admin Console

- URL: http://localhost:8080
- Username: `admin`
- Password: `admin_password`

## Configured Realm: mcp-realm

### Clients

1. **mcp-server** (Confidential Client)
   - Client ID: `mcp-server`
   - Client Secret: `mcp-server-secret-change-in-production`
   - Used by: The MCP server itself for service-to-service auth
   - Scopes: `mcp:read`, `mcp:write`, `mcp:infer`

2. **mcp-client** (Public Client)
   - Client ID: `mcp-client`
   - PKCE: Required (S256)
   - Used by: Frontend applications accessing the MCP server
   - Redirect URIs: `http://localhost:3000/*`, `http://localhost:3001/*`

### Test Users

1. **Demo User**
   - Username: `demo`
   - Password: `demo123`
   - Email: `demo@example.com`

2. **Admin User**
   - Username: `mcpadmin`
   - Password: `admin123`
   - Email: `admin@example.com`

### Client Scopes

- `mcp:read` - Read access to MCP resources
- `mcp:write` - Write access to MCP resources
- `mcp:infer` - Inference access to MCP resources

## Important Endpoints

- OpenID Configuration: `http://localhost:8080/realms/mcp-realm/.well-known/openid-configuration`
- JWKS URI: `http://localhost:8080/realms/mcp-realm/protocol/openid-connect/certs`
- Token Endpoint: `http://localhost:8080/realms/mcp-realm/protocol/openid-connect/token`
- Token Introspection: `http://localhost:8080/realms/mcp-realm/protocol/openid-connect/token/introspect`

## Security Notes

⚠️ **For Production:**
- Change all default passwords
- Use proper SSL/TLS certificates
- Update client secrets
- Configure proper CORS origins
- Enable additional security features in Keycloak
- Use external database for Keycloak data 