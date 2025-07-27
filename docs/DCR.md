# Dynamic Client Registration (DCR) Implementation

This document describes the Dynamic Client Registration (DCR) implementation in the Secure MCP Server.

## Overview

Dynamic Client Registration (DCR) allows OAuth clients to register themselves dynamically with an authorization server, as specified in [RFC 7591](https://datatracker.ietf.org/doc/html/rfc7591). This eliminates the need for static client credentials and improves security.

## Architecture

```
┌─────────────────┐     1. Get metadata      ┌──────────────┐
│                 │ ────────────────────────> │              │
│   MCP Server    │                           │   Keycloak   │
│                 │ <──────────────────────── │              │
│                 │     2. Registration       │              │
│                 │ ────────────────────────> │              │
│                 │                           │              │
│                 │ <──────────────────────── │              │
└─────────────────┘  3. Client credentials    └──────────────┘
        │
        │ 4. Save registration
        v
┌─────────────────┐
│ .dcr_client.json│
└─────────────────┘
```

## Components

### 1. DCR Client Module (`src/app/auth/dcr_client.py`)

The core DCR implementation providing:

- **Discovery**: Automatic discovery of registration endpoint from OAuth metadata
- **Registration**: Client registration with customizable metadata
- **Persistence**: Save/load registration for reuse across restarts
- **Management**: Update and delete client registrations

Key classes:
- `ClientMetadata`: OAuth 2.0 client metadata model
- `RegisteredClient`: Response from successful registration
- `DCRClient`: Main DCR client implementation

### 2. Configuration Updates

#### Settings (`src/config/settings.py`)

New configuration options:
- `use_dcr`: Boolean to enable/disable DCR
- `dcr_initial_access_token`: Optional initial access token
- `keycloak_client_id`: Now optional (required only for static registration)
- `keycloak_client_secret`: Now optional

#### Validation

Model validator ensures either DCR is enabled OR static credentials are provided.

### 3. Startup Integration (`src/app/main.py`)

The application lifecycle now includes DCR:

```python
if settings.use_dcr:
    dcr_client = DCRClient(settings)
    registered_client = await dcr_client.get_or_register_client()
    settings.keycloak_client_id = registered_client.client_id
    settings.keycloak_client_secret = registered_client.client_secret
```

## Configuration

### Option 1: Using the Setup Script

```bash
./scripts/setup_dcr.sh
```

This script:
1. Connects to Keycloak admin API
2. Creates an initial access token
3. Updates your .env file with DCR settings
4. Provides instructions for next steps

### Option 2: Manual Configuration

1. **Enable DCR in Keycloak**
   - Ensure client registration is allowed in realm settings
   - Configure client registration policies as needed

2. **Get Initial Access Token**
   - Via Keycloak Admin Console:
     - Navigate to Realm Settings → Client Registration → Initial Access Token
     - Create new token with desired count and expiration
   
   - Via Admin API:
     ```bash
     curl -X POST http://localhost:8080/admin/realms/mcp-realm/clients-initial-access \
       -H "Authorization: Bearer ${ADMIN_TOKEN}" \
       -H "Content-Type: application/json" \
       -d '{"count": 10, "expiration": 3600}'
     ```

3. **Configure Environment**
   ```env
   USE_DCR=true
   DCR_INITIAL_ACCESS_TOKEN=your-token-here
   # Remove or comment out static credentials
   # KEYCLOAK_CLIENT_ID=...
   # KEYCLOAK_CLIENT_SECRET=...
   ```

4. **Start the Server**
   ```bash
   docker-compose up -d mcp-server
   ```

## Security Considerations

### Initial Access Tokens

- **Limited lifetime**: Default 1 hour expiration
- **Limited use count**: Can be restricted to single use
- **Secure storage**: Never commit tokens to version control
- **Rotation**: Generate new tokens as needed

### Client Registration

- **Unique per instance**: Each server instance gets its own client
- **Secure persistence**: Registration saved with 0600 permissions
- **No hardcoded secrets**: Credentials generated dynamically

### Registration Policies

Keycloak allows configuring policies to control:
- Allowed grant types
- Required client scopes
- Protocol mappers
- Maximum number of clients

## Operational Aspects

### Registration Persistence

The DCR client saves registration to `.dcr_client.json`:
```json
{
  "client_id": "generated-client-id",
  "client_secret": "generated-secret",
  "registration_access_token": "...",
  "registration_client_uri": "...",
  "registered_at": "hostname"
}
```

This file is:
- Git-ignored for security
- Reused on server restarts
- Protected with restrictive permissions

### Monitoring

Log messages indicate DCR status:
- "Discovered DCR endpoint: ..."
- "Successfully registered client: ..."
- "Loaded registration for client: ..."
- "Failed to register client: ..."

### Troubleshooting

#### Registration Fails

1. **Check initial access token**
   ```bash
   echo $DCR_INITIAL_ACCESS_TOKEN
   ```

2. **Verify Keycloak policies**
   - Check realm settings for client registration
   - Review registration policies

3. **Check logs**
   ```bash
   docker-compose logs mcp-server | grep -i dcr
   ```

#### Client Already Exists

If you see "Client already exists" errors:
1. Delete `.dcr_client.json`
2. Restart the server
3. Or use the existing registration

#### Token Expired

Initial access tokens expire. Generate a new one:
```bash
./scripts/setup_dcr.sh
```

## Migration Guide

### From Static to DCR

1. **Backup existing configuration**
   ```bash
   cp .env .env.backup
   ```

2. **Enable DCR**
   ```bash
   ./scripts/setup_dcr.sh
   ```

3. **Restart services**
   ```bash
   docker-compose restart mcp-server
   ```

4. **Verify operation**
   ```bash
   docker-compose logs mcp-server
   curl -k https://localhost/health
   ```

### From DCR to Static

1. **Note current client credentials**
   ```bash
   cat .dcr_client.json | jq '.client_id, .client_secret'
   ```

2. **Update environment**
   ```env
   USE_DCR=false
   KEYCLOAK_CLIENT_ID=your-client-id
   KEYCLOAK_CLIENT_SECRET=your-client-secret
   ```

3. **Remove DCR configuration**
   ```bash
   rm .dcr_client.json
   ```

## Testing DCR

### Demo Script

Test DCR functionality:
```bash
./scripts/demo_dcr.sh
```

This demonstrates:
- OAuth metadata discovery
- Client registration attempt
- Token acquisition with registered client

### Integration Tests

The test suite supports both DCR and static modes:
```bash
# With DCR
USE_DCR=true python tests/run_all_tests.py

# With static credentials
USE_DCR=false python tests/run_all_tests.py
```

## Best Practices

1. **Use DCR in production** - Eliminates hardcoded credentials
2. **Secure initial tokens** - Treat as sensitive credentials
3. **Monitor registrations** - Track client creation/updates
4. **Regular rotation** - Periodically refresh registrations
5. **Backup registrations** - Keep secure copies of `.dcr_client.json`

## References

- [RFC 7591: OAuth 2.0 Dynamic Client Registration Protocol](https://datatracker.ietf.org/doc/html/rfc7591)
- [RFC 7592: OAuth 2.0 Dynamic Client Registration Management Protocol](https://datatracker.ietf.org/doc/html/rfc7592)
- [Keycloak Client Registration](https://www.keycloak.org/docs/latest/securing_apps/#_client_registration)
- [OAuth 2.0 Security Best Current Practice](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics) 