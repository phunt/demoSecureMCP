# Environment Variables Documentation

This document provides comprehensive information about all environment variables used by the Secure MCP Server.

## Configuration Files

- **Development**: `.env`
- **Docker Development**: `.env.docker`
- **Production**: Use environment variables or Docker secrets
- **Example**: `.env.example` (template with all variables)

## Environment Variables

### Application Settings

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `APP_NAME` | string | `secure-mcp-server` | No | Application name for logging and identification |
| `APP_VERSION` | string | `0.1.0` | No | Application version |
| `DEBUG` | boolean | `false` | No | Enable debug mode (set to `false` in production) |
| `LOG_LEVEL` | string | `INFO` | No | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

### Server Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `HOST` | string | `0.0.0.0` | No | Server bind address |
| `PORT` | integer | `8000` | No | Server port |
| `WORKERS` | integer | `1` | No | Number of worker processes (production only) |

### Keycloak Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `KEYCLOAK_URL` | URL | - | **Yes** | Keycloak base URL |
| `KEYCLOAK_REALM` | string | `mcp-realm` | No | Keycloak realm name |
| `KEYCLOAK_CLIENT_ID` | string | - | Conditional | Client ID (required if DCR is disabled) |
| `KEYCLOAK_CLIENT_SECRET` | string | - | Conditional | Client secret (required if DCR is disabled) |

### Dynamic Client Registration (DCR)

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `USE_DCR` | boolean | `false` | No | Enable Dynamic Client Registration |
| `DCR_INITIAL_ACCESS_TOKEN` | string | - | Conditional | Initial access token (required if DCR is enabled) |

**Note**: Either enable DCR (`USE_DCR=true` with `DCR_INITIAL_ACCESS_TOKEN`) OR provide static credentials (`KEYCLOAK_CLIENT_ID` and `KEYCLOAK_CLIENT_SECRET`).

### OAuth Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `OAUTH_ISSUER` | URL | - | **Yes** | OAuth issuer URL (must match token issuer) |
| `OAUTH_AUDIENCE` | string | - | **Yes** | Expected audience in JWT tokens |
| `OAUTH_JWKS_URI` | URL | - | **Yes** | JWKS endpoint for public key retrieval |
| `OAUTH_TOKEN_INTROSPECTION_ENDPOINT` | URL | - | No | Token introspection endpoint |

### MCP Server Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `MCP_RESOURCE_IDENTIFIER` | string | - | **Yes** | Unique identifier for this MCP resource |
| `MCP_SUPPORTED_SCOPES` | string | `mcp:read,mcp:write,mcp:infer` | No | Comma-separated list of supported scopes |

### Redis Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `REDIS_URL` | URL | `redis://localhost:6379/0` | No | Redis connection URL |
| `REDIS_TTL` | integer | `3600` | No | Cache TTL in seconds |

### Security Settings

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `CORS_ORIGINS` | string | `http://localhost:3000,http://localhost:3001` | No | Comma-separated allowed CORS origins |
| `REQUIRE_HTTPS` | boolean | `true` | No | Require HTTPS in production |
| `HSTS_MAX_AGE` | integer | `31536000` | No | HSTS header max-age in seconds |

### JWT Validation Settings

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `JWT_ALGORITHMS` | string | `RS256,RS384,RS512` | No | Comma-separated allowed JWT algorithms |
| `JWT_LEEWAY` | integer | `10` | No | Time validation leeway in seconds |

### Logging Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `LOG_FORMAT` | string | `json` | No | Log format: `json` or `text` |
| `LOG_FILE_PATH` | string | - | No | Log file path (empty = stdout only) |

## Environment-Specific Configurations

### Local Development

```bash
# Minimal configuration for local development
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_CLIENT_ID=mcp-server
OAUTH_ISSUER=http://localhost:8080/realms/mcp-realm
OAUTH_AUDIENCE=mcp-server
OAUTH_JWKS_URI=http://localhost:8080/realms/mcp-realm/protocol/openid-connect/certs
MCP_RESOURCE_IDENTIFIER=https://mcp-server.example.com
DEBUG=true
```

### Docker Development

When running in Docker, use internal service names:

```bash
# Docker networking requires internal URLs
KEYCLOAK_URL=http://keycloak:8080
REDIS_URL=redis://redis:6379/0
# But OAuth issuer must match external URL in tokens
OAUTH_ISSUER=http://localhost:8080/realms/mcp-realm
```

### Production

For production deployment:

1. Set `DEBUG=false`
2. Use HTTPS URLs everywhere
3. Set appropriate `WORKERS` count
4. Use strong secrets
5. Consider using Docker secrets or cloud secret managers

## Docker Secrets

For production deployments using Docker Swarm or Kubernetes, use secrets instead of environment variables for sensitive data:

```yaml
secrets:
  - keycloak_client_secret
  - postgres_password
  - keycloak_admin_password
  - redis_password
```

## Validation

The application validates configuration on startup and will:

1. Check all required variables are set
2. Validate URL formats
3. Warn about development settings in production
4. Verify security settings

Run validation manually:

```bash
python -c "from src.config.validation import validate_and_print; validate_and_print()"
```

## Best Practices

1. **Never commit secrets**: Use `.env` files locally, secrets in production
2. **Use strong passwords**: Generate with `openssl rand -base64 32`
3. **Environment-specific files**: Use `.env.example` as template, create `.env` for local dev
4. **Validate before deployment**: Check configuration validity
5. **Rotate secrets regularly**: Update passwords and keys periodically
6. **Use HTTPS in production**: All URLs should use HTTPS
7. **Minimize logging**: Set appropriate log levels for production 