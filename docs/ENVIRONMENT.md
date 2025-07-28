# Environment Variables Documentation

This document provides comprehensive information about all environment variables used by demoSecureMCP, with a focus on the clear separation between internal (container) and external (host) URL contexts.

## Overview

The demoSecureMCP uses a context-aware URL management system that automatically selects the appropriate URLs based on whether the application is running inside a Docker container or on the host system. This eliminates common configuration errors related to hostname management.

## Configuration Files

- **Development**: `.env` or `.env.local` (local development without Docker)
- **Docker Development**: Environment variables in `docker-compose.yml`
- **Production**: `.env.prod` or environment variables/secrets
- **Template**: `docs/ENV_TEMPLATE.md` (comprehensive template with all variables)

## URL Configuration Strategy

### Three URL Categories

1. **EXTERNAL_\* URLs**: Accessible from outside Docker (host machine, browsers, external clients)
2. **INTERNAL_\* URLs**: For container-to-container communication within Docker network
3. **PUBLIC_\* URLs**: Production URLs for end-user access

### Automatic Context Detection

The application automatically detects its running context and selects appropriate URLs:

```python
# In container context:
keycloak_url = INTERNAL_KEYCLOAK_URL  # http://keycloak:8080

# In host context:
keycloak_url = EXTERNAL_KEYCLOAK_URL  # http://localhost:8080

# In production (when PUBLIC_* URLs are set):
keycloak_url = PUBLIC_AUTH_URL  # https://auth.example.com
```

## Environment Variables

### Application Settings

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `APP_NAME` | string | `demoSecureMCP` | No | Application name for logging and identification |
| `APP_VERSION` | string | `0.1.0` | No | Application version |
| `DEBUG` | boolean | `false` | No | Enable debug mode (set to `false` in production) |
| `LOG_LEVEL` | string | `INFO` | No | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FORMAT` | string | `json` | No | Log format: `json` or `text` |

### Server Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `HOST` | string | `0.0.0.0` | No | Server bind address |
| `PORT` | integer | `8000` | No | Server port |
| `WORKERS` | integer | `1` | No | Number of worker processes (production only) |

### URL Configuration - Context-Aware

#### External URLs (Host Access)

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `EXTERNAL_BASE_URL` | URL | `https://localhost` | No | External API access via Nginx |
| `EXTERNAL_KEYCLOAK_URL` | URL | `http://localhost:8080` | No | External Keycloak access |

#### Internal URLs (Container Communication)

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `INTERNAL_MCP_URL` | URL | `http://mcp-server:8000` | No | Internal MCP server URL |
| `INTERNAL_KEYCLOAK_URL` | URL | `http://keycloak:8080` | No | Internal Keycloak URL |
| `INTERNAL_REDIS_URL` | URL | `redis://redis:6379/0` | No | Internal Redis URL |

#### Public URLs (Production)

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `PUBLIC_BASE_URL` | URL | - | No | Public API URL for production |
| `PUBLIC_AUTH_URL` | URL | - | No | Public auth URL for production |

### Context Detection

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `CONTAINER_ENV` | boolean | Auto-detected | No | Explicitly mark as container environment |

The application automatically detects container context by checking:
1. Presence of `/.dockerenv` file
2. `CONTAINER_ENV` environment variable
3. Docker/Kubernetes markers in `/proc/1/cgroup`

### Keycloak Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
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

**Critical Note**: `OAUTH_ISSUER` must match what's in the JWT tokens. This is typically the external URL that clients see, even when running in containers.

### MCP Server Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `MCP_RESOURCE_IDENTIFIER` | string | - | **Yes** | Unique identifier for this MCP resource |
| `MCP_SUPPORTED_SCOPES` | string | `mcp:read,mcp:write,mcp:infer` | No | Comma-separated list of supported scopes |

### Redis Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `REDIS_TTL` | integer | `3600` | No | Cache TTL in seconds |

Note: Redis URL is automatically selected based on context (internal vs external).

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

## Environment-Specific Examples

### Local Development (No Docker)

```bash
# Minimal configuration for local development
APP_NAME=demoSecureMCP
DEBUG=true
LOG_LEVEL=DEBUG

# External URLs (default context for local dev)
EXTERNAL_KEYCLOAK_URL=http://localhost:8080
EXTERNAL_BASE_URL=https://localhost

# OAuth configuration
OAUTH_ISSUER=http://localhost:8080/realms/mcp-realm
OAUTH_AUDIENCE=mcp-server

# MCP configuration
MCP_RESOURCE_IDENTIFIER=https://mcp-server.example.com

# Security (relaxed for development)
REQUIRE_HTTPS=false
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Docker Development

When running in Docker, the application automatically uses internal URLs:

```bash
# Docker automatically sets CONTAINER_ENV=true
# The application will use:
# - INTERNAL_KEYCLOAK_URL for Keycloak communication
# - INTERNAL_REDIS_URL for Redis
# - But OAUTH_ISSUER remains external for token validation

OAUTH_ISSUER=http://localhost:8080/realms/mcp-realm  # Must match tokens
```

### Production

```bash
# Production configuration
APP_NAME=demoSecureMCP
APP_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=INFO
WORKERS=4

# External URLs (for reference)
EXTERNAL_BASE_URL=https://api.yourcompany.com
EXTERNAL_KEYCLOAK_URL=https://auth.yourcompany.com

# Public URLs (for production access)
PUBLIC_BASE_URL=https://api.yourcompany.com
PUBLIC_AUTH_URL=https://auth.yourcompany.com

# OAuth configuration (production issuer)
OAUTH_ISSUER=https://auth.yourcompany.com/realms/production
OAUTH_AUDIENCE=mcp-server

# Security (strict for production)
REQUIRE_HTTPS=true
CORS_ORIGINS=https://app.yourcompany.com,https://admin.yourcompany.com
```

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
3. Detect running context (container vs host)
4. Warn about development settings in production
5. Verify security settings

Run validation manually:

```bash
python -c "from src.config.validation import validate_and_print; validate_and_print()"
```

## Migration from Old Structure

If migrating from the old environment structure:

1. Replace single `KEYCLOAK_URL` with:
   - `EXTERNAL_KEYCLOAK_URL` for host access
   - `INTERNAL_KEYCLOAK_URL` for container access

2. Remove explicit `REDIS_URL` - it's now auto-selected based on context

3. Ensure `OAUTH_ISSUER` is set correctly (must match JWT tokens)

4. Add `PUBLIC_*` URLs for production deployments

## Troubleshooting

### Common Issues

1. **"Invalid token issuer" errors**
   - Ensure `OAUTH_ISSUER` matches exactly what's in your JWT tokens
   - This is often the external URL even in container contexts

2. **"Connection refused" in containers**
   - Check that internal URLs use container service names (e.g., `keycloak` not `localhost`)
   - Verify services are on the same Docker network

3. **"Cannot connect to Redis"**
   - In containers: Should use `redis://redis:6379/0`
   - On host: Should use `redis://localhost:6379/0`
   - Check context detection is working correctly

4. **Wrong URLs in production**
   - Set `PUBLIC_*` URLs for production domains
   - Ensure `DEBUG=false` to trigger production URL selection 