# Keycloak Configuration

This directory contains the Keycloak configuration for the secure MCP server.

## Files

- `realm-export.json` - The original Keycloak realm configuration with static client registration
- `realm-export-dcr.json` - The Keycloak realm configuration with Dynamic Client Registration (DCR) support

## Dynamic Client Registration (DCR)

The MCP server now supports Dynamic Client Registration as per RFC 7591. This allows the server to register itself dynamically with Keycloak instead of using static client credentials.

### Benefits of DCR

1. **No hardcoded credentials** - Client credentials are generated dynamically
2. **Automatic registration** - The MCP server registers itself on startup
3. **Better security** - Each instance can have its own client registration
4. **Easier deployment** - No need to pre-configure clients in Keycloak

### How to Enable DCR

1. Use the DCR-enabled realm configuration:
   ```bash
   # Update docker-compose.yml to use realm-export-dcr.json
   ```

2. Set up DCR using the provided script:
   ```bash
   ./scripts/setup_dcr.sh
   ```
   
   This script will:
   - Connect to Keycloak admin API
   - Create an initial access token
   - Update your .env file with DCR settings

3. Restart the MCP server:
   ```bash
   docker-compose restart mcp-server
   ```

### Manual DCR Setup

If you prefer to set up DCR manually:

1. Get an initial access token from Keycloak admin console
2. Add these to your .env file:
   ```env
   USE_DCR=true
   DCR_INITIAL_ACCESS_TOKEN=your-token-here
   ```
3. Remove any static client credentials from .env

### DCR Configuration

The DCR client registration includes:
- Client name: "MCP Server (secure-mcp-server)"
- Grant types: client_credentials
- Authentication method: client_secret_basic
- Automatic persistence of registration

The registration is saved to `.dcr_client.json` (git-ignored) and reused on subsequent startups.

## Static Client Configuration (Legacy)

The original `realm-export.json` includes a pre-configured client:

- **Client ID**: `mcp-server`
- **Client Secret**: `mcp-server-secret-change-in-production`
- **Access Type**: Confidential
- **Service Accounts**: Enabled
- **Direct Access Grants**: Enabled

To use static registration:
1. Use the original realm-export.json
2. Set USE_DCR=false in your .env
3. Provide KEYCLOAK_CLIENT_ID and KEYCLOAK_CLIENT_SECRET

## Client Scopes

Both configurations include these OAuth scopes:

- `mcp:read` - Read access to MCP resources
- `mcp:write` - Write access to MCP resources  
- `mcp:infer` - Inference access to MCP resources

## Users

A test user is pre-configured for development:

- **Username**: `test`
- **Password**: `test123`
- **Email**: `test@example.com`

## Security Considerations

1. **Change default passwords** - Update admin and test user passwords
2. **Use proper certificates** - Configure SSL/TLS for production
3. **Limit access** - Restrict Keycloak admin access
4. **Regular updates** - Keep Keycloak updated
5. **Initial access tokens** - These expire after 1 hour by default

## Import/Export

To export the current realm configuration:

```bash
docker exec -it mcp-keycloak \
  /opt/keycloak/bin/kc.sh export \
  --file /tmp/realm-export.json \
  --realm mcp-realm

docker cp mcp-keycloak:/tmp/realm-export.json ./keycloak/
```

To import a realm configuration, place the JSON file in this directory and restart Keycloak.

## Troubleshooting

### DCR Issues

1. **Initial access token expired**
   - Run `./scripts/setup_dcr.sh` again to get a new token

2. **Registration fails**
   - Check Keycloak logs: `docker-compose logs keycloak`
   - Verify DCR is enabled in the realm settings
   - Check client registration policies

3. **Client already registered**
   - Delete `.dcr_client.json` to force re-registration
   - Or use the existing registration

### General Issues

1. **Keycloak won't start**
   - Check if port 8080 is already in use
   - Verify PostgreSQL is running
   - Check Docker logs: `docker-compose logs keycloak`

2. **Can't access Keycloak admin console**
   - Default URL: http://localhost:8080
   - Default admin credentials: admin/admin_password
   - Check if Keycloak is healthy: `docker-compose ps`

3. **Realm not imported**
   - Ensure the realm JSON file is properly mounted
   - Check Keycloak logs for import errors
   - Manually import via admin console if needed 