# Hostname Management Refactor Guide

## Overview

This document outlines the refactoring of hostname management in demoSecureMCP to clearly separate internal (container) and external (host) URL contexts, reducing configuration errors and simplifying deployment.

## Problem Statement

The current hostname management is complex and error-prone due to:

1. **Mixed Contexts**: Same variables used for both internal and external access
2. **OAuth Issuer Confusion**: JWT issuer must match client expectations but differs between contexts
3. **Multiple Environment Files**: Unclear distinction between .env, .env.docker, etc.
4. **DCR Complexity**: Token generation requires container-internal URLs but tests run from host

## Solution Design

### 1. Clear URL Categorization

We introduce three URL categories with explicit prefixes:

- **EXTERNAL_**: URLs accessible from the host machine (localhost)
- **INTERNAL_**: URLs for container-to-container communication  
- **PUBLIC_**: Production URLs for end-user access

### 2. New Environment Variable Structure

```bash
# ============================================================================
# URL CONFIGURATION - CRITICAL SECTION
# ============================================================================
# External URLs (from host machine perspective)
EXTERNAL_BASE_URL=https://localhost  # Nginx proxy (HTTPS)
EXTERNAL_KEYCLOAK_URL=http://localhost:8080  # Direct Keycloak access
EXTERNAL_KEYCLOAK_REALM_URL=http://localhost:8080/realms/mcp-realm

# Internal URLs (from container perspective)
INTERNAL_MCP_URL=http://mcp-server:8000
INTERNAL_KEYCLOAK_URL=http://keycloak:8080
INTERNAL_KEYCLOAK_REALM_URL=http://keycloak:8080/realms/mcp-realm
INTERNAL_REDIS_URL=redis://redis:6379/0

# Public URLs (for production)
PUBLIC_BASE_URL=https://api.example.com
PUBLIC_AUTH_URL=https://auth.example.com
```

### 3. Context-Aware Configuration

The application automatically selects appropriate URLs based on runtime context:

```python
class Settings(BaseSettings):
    # URL Configuration with clear separation
    external_base_url: HttpUrl
    external_keycloak_url: HttpUrl
    internal_keycloak_url: HttpUrl
    internal_redis_url: str
    
    @property
    def keycloak_url(self) -> str:
        """Returns appropriate Keycloak URL based on context"""
        if self.is_container_context():
            return str(self.internal_keycloak_url)
        return str(self.external_keycloak_url)
    
    def is_container_context(self) -> bool:
        """Detect if running inside Docker container"""
        return os.path.exists('/.dockerenv') or os.environ.get('CONTAINER_ENV') == 'true'
```

### 4. Simplified Environment Files

Instead of ambiguous files, we use clear naming:

- `.env.template` - Complete template with all options
- `.env.local` - Local development without Docker
- `.env.docker` - Docker development
- `.env.prod` - Production deployment

### 5. OAuth Issuer Handling

The OAuth issuer is explicitly configured separately from service URLs:

```bash
# The issuer must match what's in JWT tokens
# For local dev: external URL since tokens are obtained from host
OAUTH_ISSUER=${EXTERNAL_KEYCLOAK_REALM_URL}

# For production: public URL
# OAUTH_ISSUER=${PUBLIC_AUTH_URL}/realms/mcp-realm
```

## Implementation Steps

### Step 1: Update Settings Model

```python
# src/config/settings.py
class Settings(BaseSettings):
    """Application settings with clear URL separation"""
    
    # External URLs (host access)
    external_base_url: HttpUrl = Field(..., description="External base URL")
    external_keycloak_url: HttpUrl = Field(..., description="External Keycloak URL")
    
    # Internal URLs (container access)  
    internal_mcp_url: HttpUrl = Field(..., description="Internal MCP server URL")
    internal_keycloak_url: HttpUrl = Field(..., description="Internal Keycloak URL")
    internal_redis_url: str = Field(..., description="Internal Redis URL")
    
    # Public URLs (production)
    public_base_url: Optional[HttpUrl] = Field(None, description="Public API URL")
    public_auth_url: Optional[HttpUrl] = Field(None, description="Public auth URL")
    
    # OAuth configuration (explicit issuer)
    oauth_issuer: HttpUrl = Field(..., description="OAuth issuer URL")
    
    # Context detection
    container_env: bool = Field(default=False, description="Running in container")
    
    @model_validator(mode='after')
    def detect_container_context(self) -> 'Settings':
        """Auto-detect container context"""
        self.container_env = (
            os.path.exists('/.dockerenv') or 
            os.environ.get('CONTAINER_ENV', '').lower() == 'true'
        )
        return self
    
    # Computed properties for context-aware URLs
    @property
    def keycloak_url(self) -> str:
        """Returns appropriate Keycloak URL based on context"""
        if self.container_env:
            return str(self.internal_keycloak_url)
        return str(self.external_keycloak_url)
    
    @property
    def redis_url(self) -> str:
        """Returns appropriate Redis URL based on context"""
        if self.container_env:
            return self.internal_redis_url
        # For local dev without Docker
        return "redis://localhost:6379/0"
```

### Step 2: Update Docker Compose

```yaml
# docker-compose.yml
services:
  mcp-server:
    environment:
      # Explicitly mark as container context
      - CONTAINER_ENV=true
      # Internal URLs for container use
      - INTERNAL_KEYCLOAK_URL=http://keycloak:8080
      - INTERNAL_REDIS_URL=redis://redis:6379/0
      # External URLs for reference
      - EXTERNAL_KEYCLOAK_URL=http://localhost:8080
      # OAuth issuer remains external for token validation
      - OAUTH_ISSUER=${OAUTH_ISSUER:-http://localhost:8080/realms/mcp-realm}
```

### Step 3: Update Scripts

Scripts should use environment variables that match their execution context:

```bash
# scripts/common_lib.sh
# Determine execution context
if [[ -f /.dockerenv ]] || [[ "${CONTAINER_ENV}" == "true" ]]; then
    export KEYCLOAK_URL="${INTERNAL_KEYCLOAK_URL}"
    export REDIS_URL="${INTERNAL_REDIS_URL}"
else
    export KEYCLOAK_URL="${EXTERNAL_KEYCLOAK_URL}"
    export REDIS_URL="redis://localhost:6379/0"
fi
```

### Step 4: Update Client Examples

```bash
# examples/curl-client/common.sh
# Clients always use external URLs
set_default_env "MCP_SERVER_URL" "${EXTERNAL_BASE_URL:-https://localhost}"
set_default_env "KEYCLOAK_URL" "${EXTERNAL_KEYCLOAK_URL:-http://localhost:8080}"
```

## Benefits

1. **Clear Context Separation**: No ambiguity about which URL to use where
2. **Reduced Errors**: Explicit naming prevents using wrong URLs
3. **Easier Debugging**: Clear which context each component operates in
4. **Simplified Configuration**: One template with clear sections
5. **Better Documentation**: Self-documenting variable names

## Migration Guide

1. Create new environment files from template
2. Update docker-compose.yml with new variables
3. Update application code to use new settings
4. Update scripts to be context-aware
5. Test in both local and Docker contexts
6. Remove old environment files

## Testing Strategy

1. **Local Development**: Run without Docker, verify external URLs work
2. **Docker Development**: Run with Docker, verify internal URLs used
3. **Cross-Context**: Test scripts from host accessing Docker services
4. **Production Simulation**: Test with public URLs configured 