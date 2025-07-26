# MCP Server Curl Client

A shell-based client implementation for the Secure MCP Server using only `curl` commands. This demonstrates OAuth 2.0 client credentials flow and secure API interaction without any programming language dependencies.

## Overview

This client provides a complete example of:
- OAuth 2.0 authentication with Keycloak
- JWT token acquisition and management
- Authenticated API calls to MCP tools
- Error handling and troubleshooting
- Production-ready shell scripting patterns

## Prerequisites

### Required Tools

- `curl` - HTTP client for API requests
- `jq` - JSON parsing and manipulation
- `bash` - Shell interpreter (version 4.0+)

Install on macOS:
```bash
brew install curl jq
```

Install on Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install curl jq
```

### Docker Services

The MCP server and Keycloak must be running:
```bash
cd ../..  # Navigate to project root
docker-compose up -d
```

## Quick Start

### 1. Basic Usage

```bash
# Get an access token
./get_token.sh

# Call a tool with the token
export ACCESS_TOKEN="<token-from-above>"
./call_tool.sh echo "Hello, secure world!"

# Or use the full example
./full_example.sh
```

### 2. Using Token Files

```bash
# Save token to file
SAVE_TOKEN=true ./get_token.sh

# Use token from file
./call_tool.sh -f /tmp/mcp_access_token timestamp
```

## Scripts

### get_token.sh

Obtains an access token from Keycloak using the OAuth 2.0 client credentials flow.

**Usage:**
```bash
./get_token.sh
```

**Environment Variables:**
- `KEYCLOAK_URL` - Keycloak server URL (default: `http://localhost:8080`)
- `KEYCLOAK_REALM` - Realm name (default: `mcp-realm`)
- `CLIENT_ID` - OAuth client ID (default: `mcp-server`)
- `CLIENT_SECRET` - OAuth client secret (default: `your-secret-here`)
- `SAVE_TOKEN` - Save token to file if `true` (default: `false`)
- `TOKEN_FILE` - File path for saved token (default: `/tmp/mcp_access_token`)

**Example with custom settings:**
```bash
KEYCLOAK_URL=https://auth.example.com \
CLIENT_SECRET=production-secret \
SAVE_TOKEN=true \
./get_token.sh
```

### call_tool.sh

Calls MCP server tools with proper authentication.

**Usage:**
```bash
./call_tool.sh [OPTIONS] TOOL [ARGS...]
```

**Tools:**
- `echo TEXT` - Echo the provided text (requires `mcp:read` scope)
- `timestamp` - Get current timestamp (requires `mcp:read` scope)
- `calculate OPERATION NUM1 [NUM2...]` - Calculate using mathematical operations (requires `mcp:write` scope)
  - Operations: add, subtract, multiply, divide, power, sqrt, factorial
  - Examples: `calculate add 10 20`, `calculate sqrt 16`
- `discover` - List available tools (requires authentication)

**Options:**
- `-h, --help` - Show help message
- `-t, --token TOKEN` - Use specified access token
- `-f, --token-file FILE` - Read token from file
- `-u, --url URL` - MCP server URL (default: `https://localhost`)
- `-k, --insecure` - Allow insecure SSL connections
- `-v, --verbose` - Show verbose output including headers

**Examples:**
```bash
# Echo with token from environment
./call_tool.sh -t "$ACCESS_TOKEN" echo "Hello!"

# Timestamp with token from file
./call_tool.sh -f /tmp/mcp_access_token timestamp

# Calculate with custom server URL
./call_tool.sh -u https://mcp.example.com calculate multiply 10 5

# Discover tools with verbose output
./call_tool.sh -v discover
```

### full_example.sh

Demonstrates the complete OAuth flow and all tool usage.

**Usage:**
```bash
./full_example.sh
```

This script:
1. Checks service availability
2. Fetches OAuth metadata
3. Obtains access token
4. Tests security (unauthorized access)
5. Discovers available tools
6. Demonstrates each tool
7. Shows error handling

### test.sh

Comprehensive test suite for the client implementation.

**Usage:**
```bash
./test.sh
```

Tests include:
- Prerequisites verification
- Service health checks
- OAuth discovery
- Token acquisition
- Tool invocations
- Error handling
- Command-line arguments
- Environment variables

## Configuration

### Default Endpoints

- Keycloak: `http://localhost:8080`
- MCP Server: `https://localhost`
- Token Endpoint: `http://localhost:8080/realms/mcp-realm/protocol/openid-connect/token`

### Client Credentials

Default credentials (change in production!):
- Client ID: `mcp-server`
- Client Secret: `your-secret-here`

Update in Keycloak admin console: http://localhost:8080

### SSL/TLS

The nginx proxy uses self-signed certificates by default. Use `-k` flag with `call_tool.sh` to allow insecure connections in development.

For production:
1. Use proper certificates
2. Remove `-k` flag from scripts
3. Ensure certificate validation

## Token Management

### Token Lifetime

- Access tokens expire in 300 seconds (5 minutes)
- Plan for token refresh in long-running operations

### Token Storage

Options for managing tokens:
1. Environment variable: `export ACCESS_TOKEN="..."`
2. File storage: `SAVE_TOKEN=true ./get_token.sh`
3. Pass directly: `./call_tool.sh -t "..." echo "test"`

### Security Best Practices

- Never commit tokens to version control
- Use secure file permissions: `chmod 600 /tmp/token_file`
- Rotate client secrets regularly
- Use proper certificates in production

## Troubleshooting

### Common Issues

#### "Keycloak is not reachable"
```bash
# Check if containers are running
docker-compose ps

# Start services if needed
docker-compose up -d

# Check Keycloak logs
docker-compose logs keycloak
```

#### "Token signature verification failed"
- Token may be expired (check with `jwt.io`)
- Wrong client secret
- Keycloak realm misconfiguration

#### "Invalid audience"
- Token not intended for MCP server
- Check `OAUTH_AUDIENCE` in server config
- Verify client configuration in Keycloak

#### "Insufficient permissions (403)"
- Token lacks required scope
- Check client scope mappings in Keycloak
- Verify tool scope requirements

### Debug Mode

Enable verbose output for debugging:
```bash
# Verbose token acquisition
set -x
./get_token.sh

# Verbose API calls
./call_tool.sh -v echo "debug test"
```

### Network Issues

For Docker networking issues:
```bash
# Test from inside container
docker exec -it mcp-server curl http://keycloak:8080/health/ready

# Check network configuration
docker network ls
docker network inspect mcp-network
```

## OAuth Error Scenarios

### Invalid Client Credentials
```json
{
  "error": "invalid_client",
  "error_description": "Invalid client credentials"
}
```
**Fix:** Update `CLIENT_SECRET` environment variable

### Invalid Scope
```json
{
  "error": "invalid_scope",
  "error_description": "Invalid scopes: unknown-scope"
}
```
**Fix:** Use valid scopes: `mcp:read`, `mcp:write`, `mcp:infer`

### Expired Token
```json
{
  "detail": "Token is expired",
  "status_code": 401
}
```
**Fix:** Obtain new token with `./get_token.sh`

## Integration Examples

### Continuous Integration

```yaml
# .github/workflows/test.yml
- name: Test MCP Client
  run: |
    cd examples/curl-client
    ./test.sh
```

### Cron Job

```bash
# Refresh token and call tool every hour
0 * * * * cd /path/to/client && SAVE_TOKEN=true ./get_token.sh && ./call_tool.sh -f /tmp/mcp_access_token timestamp >> /var/log/mcp.log
```

### Shell Function

Add to `~/.bashrc`:
```bash
mcp_tool() {
    local tool=$1
    shift
    local token_file="/tmp/mcp_token_$$"
    
    # Get fresh token
    SAVE_TOKEN=true TOKEN_FILE="$token_file" \
        /path/to/get_token.sh > /dev/null 2>&1
    
    # Call tool
    /path/to/call_tool.sh -k -f "$token_file" "$tool" "$@"
    
    # Cleanup
    rm -f "$token_file"
}

# Usage
mcp_tool echo "Hello from function"
mcp_tool calculate "100 / 4"
```

## Advanced Usage

### Custom Headers

```bash
# Add custom headers with curl
curl -k -X POST https://localhost/api/v1/tools/echo \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: $(uuidgen)" \
  -d '{"text": "Custom request"}'
```

### Parallel Requests

```bash
# Run multiple tools in parallel
export ACCESS_TOKEN=$(SAVE_TOKEN=false ./get_token.sh | grep -A1 "export ACCESS_TOKEN" | tail -1 | cut -d'"' -f2)

./call_tool.sh echo "Request 1" &
./call_tool.sh timestamp &
./call_tool.sh calculate "2 + 2" &
wait
```

### Response Processing

```bash
# Extract specific fields with jq
TIMESTAMP=$(./call_tool.sh -f /tmp/mcp_access_token timestamp | grep -A10 RESPONSE | jq -r '.timestamp')
echo "Server time: $TIMESTAMP"
```

## Contributing

When adding new tools to the MCP server:

1. Update `call_tool.sh` with new tool command
2. Add tool to help text
3. Include in `test.sh` test suite
4. Document required scopes
5. Add examples to this README

## Security Considerations

This client is designed for demonstration and testing. For production use:

1. **Secrets Management**
   - Use secure vaults (HashiCorp Vault, AWS Secrets Manager)
   - Never hardcode credentials
   - Rotate secrets regularly

2. **Network Security**
   - Use proper TLS certificates
   - Implement network segmentation
   - Use VPN/private networks

3. **Token Security**
   - Minimize token lifetime
   - Implement token refresh
   - Secure token storage

4. **Audit Logging**
   - Log all authentication attempts
   - Monitor for suspicious activity
   - Implement alerting

## License

This example client is part of the Secure MCP Server project. See the main project LICENSE file for details. 