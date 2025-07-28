# Environment Configuration Templates

This document provides templates for environment configuration with the new hostname management structure.

## .env.example Template

```bash
# ============================================================================
# demoSecureMCP Environment Configuration Example
# ============================================================================
# This example shows all available configuration options with clear separation
# between internal (container) and external (host) URLs.
#
# Copy this file to:
#   - .env.local    (for local development without Docker)
#   - .env.docker   (for Docker development)
#   - .env.prod     (for production deployment)
# ============================================================================

# ============================================================================
# APPLICATION SETTINGS
# ============================================================================
APP_NAME=demoSecureMCP
APP_VERSION=0.1.0
DEBUG=true  # Set to false in production
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json  # json or text

# ============================================================================
# SERVER CONFIGURATION
# ============================================================================
HOST=0.0.0.0
PORT=8000
WORKERS=1  # Increase for production (e.g., 4)

# ============================================================================
# URL CONFIGURATION - CRITICAL SECTION
# ============================================================================
# This section defines URLs from different access contexts:
# - EXTERNAL_*: URLs accessible from outside Docker (host machine, browsers, external clients)
# - INTERNAL_*: URLs for container-to-container communication within Docker network
# - PUBLIC_*:   URLs that will be exposed to end users (production URLs)

# --- External URLs (from host machine perspective) ---
# These are used by scripts, tests, and clients running on the host
EXTERNAL_BASE_URL=https://localhost  # Nginx proxy (HTTPS)
EXTERNAL_KEYCLOAK_URL=http://localhost:8080  # Direct Keycloak access

# --- Internal URLs (from container perspective) ---
# These are used by services communicating within the Docker network
INTERNAL_MCP_URL=http://mcp-server:8000
INTERNAL_KEYCLOAK_URL=http://keycloak:8080
INTERNAL_REDIS_URL=redis://redis:6379/0

# --- Public URLs (for production) ---
# These replace localhost with actual domain names in production
PUBLIC_BASE_URL=https://api.example.com  # Your API domain
PUBLIC_AUTH_URL=https://auth.example.com  # Your auth domain

# ============================================================================
# KEYCLOAK CONFIGURATION
# ============================================================================
KEYCLOAK_REALM=mcp-realm

# For static client registration (USE_DCR=false)
KEYCLOAK_CLIENT_ID=mcp-server
KEYCLOAK_CLIENT_SECRET=mcp-server-secret-change-in-production  # Change in production!

# For dynamic client registration (USE_DCR=true)
USE_DCR=false
DCR_INITIAL_ACCESS_TOKEN=  # Set when using DCR

# ============================================================================
# OAUTH/JWT CONFIGURATION
# ============================================================================
# CRITICAL: The issuer URL must match what's in the JWT tokens!
# - For local development: Use EXTERNAL_KEYCLOAK_URL/realms/{realm}
# - For production: Use PUBLIC_AUTH_URL/realms/{realm}
OAUTH_ISSUER=http://localhost:8080/realms/mcp-realm  # Must match token issuer
OAUTH_AUDIENCE=mcp-server
JWT_ALGORITHMS=RS256,RS384,RS512
JWT_LEEWAY=10  # seconds

# ============================================================================
# MCP SERVER CONFIGURATION
# ============================================================================
# Resource identifier should be a stable, public URL or URN
MCP_RESOURCE_IDENTIFIER=https://mcp-server.example.com
MCP_SUPPORTED_SCOPES=mcp:read,mcp:write,mcp:infer

# ============================================================================
# REDIS CONFIGURATION
# ============================================================================
# Note: The application will automatically select the appropriate Redis URL
# based on container context detection
REDIS_TTL=3600  # Cache TTL in seconds

# ============================================================================
# SECURITY SETTINGS
# ============================================================================
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
REQUIRE_HTTPS=true  # Set to false for local development
HSTS_MAX_AGE=31536000  # 1 year in seconds

# ============================================================================
# ENVIRONMENT-SPECIFIC CONFIGURATION NOTES
# ============================================================================
# For .env.local (no Docker):
#   - No changes needed, uses external URLs by default
#   - Set REQUIRE_HTTPS=false for local development
#
# For .env.docker (Docker development):
#   - Set CONTAINER_ENV=true (or let auto-detection work)
#   - The app will automatically use internal URLs
#
# For .env.prod (production):
#   - Set DEBUG=false
#   - Set WORKERS=4 (or appropriate for your server)
#   - Update all localhost URLs to production domains
#   - Set OAUTH_ISSUER to match your production auth server
#   - Update CORS_ORIGINS to your production frontend URLs
#   - Ensure all secrets are strong and unique
```

## .env.docker Template

```bash
# Docker-specific environment configuration
# Inherits from .env.example and overrides as needed

# Mark as container environment (optional - auto-detected)
CONTAINER_ENV=true

# OAuth issuer must match what external clients expect
# Even in Docker, tokens are validated against this issuer
OAUTH_ISSUER=http://localhost:8080/realms/mcp-realm

# All other URLs are automatically selected based on container context
```

## .env.prod Template

```bash
# Production environment configuration

# Application settings
APP_NAME=demoSecureMCP
APP_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

# Server configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4

# External URLs (not used in production containers)
EXTERNAL_BASE_URL=https://api.yourcompany.com
EXTERNAL_KEYCLOAK_URL=https://auth.yourcompany.com

# Internal URLs (used by containers)
INTERNAL_MCP_URL=http://mcp-server:8000
INTERNAL_KEYCLOAK_URL=http://keycloak:8080
INTERNAL_REDIS_URL=redis://redis:6379/0

# Public URLs (for external access)
PUBLIC_BASE_URL=https://api.yourcompany.com
PUBLIC_AUTH_URL=https://auth.yourcompany.com

# Keycloak configuration
KEYCLOAK_REALM=production-realm
KEYCLOAK_CLIENT_ID=mcp-server
KEYCLOAK_CLIENT_SECRET=${KEYCLOAK_CLIENT_SECRET}  # From secrets management

# OAuth configuration
OAUTH_ISSUER=https://auth.yourcompany.com/realms/production-realm
OAUTH_AUDIENCE=mcp-server
JWT_ALGORITHMS=RS256
JWT_LEEWAY=5

# MCP configuration
MCP_RESOURCE_IDENTIFIER=https://api.yourcompany.com
MCP_SUPPORTED_SCOPES=mcp:read,mcp:write,mcp:infer

# Redis configuration
REDIS_TTL=7200

# Security settings
CORS_ORIGINS=https://app.yourcompany.com,https://admin.yourcompany.com
REQUIRE_HTTPS=true
HSTS_MAX_AGE=63072000  # 2 years
```

## Key Differences Between Environments

### Local Development (.env.local)
- Uses external URLs (localhost)
- REQUIRE_HTTPS=false
- DEBUG=true
- Single worker

### Docker Development (.env.docker)
- Container context auto-detected
- Uses internal URLs automatically
- OAuth issuer remains external for token validation
- DEBUG=true for development

### Production (.env.prod)
- All URLs use production domains
- HTTPS required
- Multiple workers
- Strict security settings
- Secrets from external management

## Migration from Old Structure

To migrate from the old environment structure:

1. **Identify current URLs**:
   - KEYCLOAK_URL → Split into EXTERNAL_KEYCLOAK_URL and INTERNAL_KEYCLOAK_URL
   - REDIS_URL → Becomes INTERNAL_REDIS_URL (auto-selected based on context)

2. **Update OAuth issuer**:
   - Ensure OAUTH_ISSUER matches what's in your JWT tokens
   - This is critical for token validation

3. **Add new URL variables**:
   - Add EXTERNAL_* URLs for host access
   - Add INTERNAL_* URLs for container communication
   - Add PUBLIC_* URLs for production

4. **Test in both contexts**:
   - Run locally without Docker
   - Run with Docker Compose
   - Verify correct URLs are used in each context 