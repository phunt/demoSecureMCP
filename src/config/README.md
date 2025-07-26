# Configuration Management

This directory contains the configuration system for the Secure MCP Server, providing centralized settings management with validation and type safety.

## Overview

The configuration system uses Pydantic Settings for:
- **Type Safety**: All settings are strongly typed
- **Validation**: Automatic validation of environment variables
- **Documentation**: Self-documenting configuration
- **Environment Support**: Easy switching between dev/staging/prod
- **Security**: No hardcoded secrets in code

## Components

### `settings.py`

Main settings class using Pydantic BaseSettings:

```python
class Settings(BaseSettings):
    """Application configuration settings"""
    
    # Application
    app_name: str = "secure-mcp-server"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Keycloak
    keycloak_url: str
    keycloak_realm: str = "mcp-realm"
    keycloak_client_id: str
    keycloak_client_secret: Optional[str] = None
    
    # OAuth
    oauth_issuer: str
    oauth_audience: str
    oauth_jwks_uri: str
    
    # MCP
    mcp_resource_identifier: str
    mcp_supported_scopes: List[str] = ["mcp:read", "mcp:write", "mcp:infer"]
```

### `validation.py`

Runtime validation of configuration:

```python
def validate_config(settings: Settings) -> ValidationResult:
    """Validate configuration at runtime"""
    
    # Check required fields
    # Validate URLs
    # Check production settings
    # Verify connectivity
    
    return ValidationResult(valid=True, warnings=[], errors=[])
```

## Environment Variables

### Loading Order

1. `.env` file (if exists)
2. `.env.{environment}` file
3. System environment variables
4. Docker secrets (if configured)

### Variable Types

Pydantic automatically converts environment variables:

```bash
# Boolean (case-insensitive)
DEBUG=true
DEBUG=True
DEBUG=1

# Lists (comma-separated)
MCP_SUPPORTED_SCOPES=mcp:read,mcp:write,mcp:infer
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Optional with defaults
LOG_LEVEL=INFO  # defaults to INFO if not set

# Required (no default)
KEYCLOAK_URL=http://localhost:8080  # must be set
```

## Usage in Application

### Accessing Settings

```python
from src.config import settings

# Use directly
print(f"App: {settings.app_name} v{settings.app_version}")

# Dependency injection
from fastapi import Depends

def get_settings() -> Settings:
    return settings

@app.get("/config")
async def get_config(settings: Settings = Depends(get_settings)):
    return {
        "app": settings.app_name,
        "debug": settings.debug
    }
```

### Validation on Startup

```python
from src.config.validation import validate_config

async def lifespan(app: FastAPI):
    # Validate configuration
    result = validate_config(settings)
    
    if not result.valid:
        for error in result.errors:
            logger.error(f"Config error: {error}")
        raise ValueError("Invalid configuration")
    
    for warning in result.warnings:
        logger.warning(f"Config warning: {warning}")
    
    yield
```

## Configuration Patterns

### 1. **Environment-Specific Settings**

```python
class Settings(BaseSettings):
    environment: str = "development"
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    # Use in validators
    @field_validator("debug")
    def validate_debug(cls, v, values):
        if values.get("environment") == "production" and v:
            raise ValueError("Debug must be False in production")
        return v
```

### 2. **Computed Properties**

```python
class Settings(BaseSettings):
    keycloak_url: str
    keycloak_realm: str
    
    @property
    def token_endpoint(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}/protocol/openid-connect/token"
    
    @property
    def jwks_uri(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"
```

### 3. **Secret Management**

```python
class Settings(BaseSettings):
    # From environment
    client_secret: Optional[str] = None
    
    # From file (Docker secrets)
    client_secret_file: Optional[str] = None
    
    @property
    def get_client_secret(self) -> str:
        if self.client_secret_file:
            with open(self.client_secret_file) as f:
                return f.read().strip()
        return self.client_secret or ""
```

### 4. **Custom Validators**

```python
from pydantic import field_validator, HttpUrl

class Settings(BaseSettings):
    keycloak_url: HttpUrl
    
    @field_validator("keycloak_url")
    def validate_keycloak_url(cls, v):
        if not str(v).startswith(("http://", "https://")):
            raise ValueError("Keycloak URL must start with http:// or https://")
        return v
    
    @field_validator("mcp_supported_scopes")
    def validate_scopes(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",")]
        return v
```

## Testing Configuration

### Unit Tests

```python
import pytest
from src.config import Settings

def test_settings_defaults():
    settings = Settings(
        keycloak_url="http://test",
        keycloak_client_id="test-client",
        oauth_issuer="http://test/realm",
        oauth_audience="test-client",
        oauth_jwks_uri="http://test/jwks",
        mcp_resource_identifier="test-resource"
    )
    
    assert settings.app_name == "secure-mcp-server"
    assert settings.debug is False
    assert settings.mcp_supported_scopes == ["mcp:read", "mcp:write", "mcp:infer"]

def test_settings_validation():
    with pytest.raises(ValueError):
        Settings(
            keycloak_url="invalid-url",  # Should fail URL validation
            # ... other required fields
        )
```

### Integration Tests

```python
async def test_config_validation():
    from src.config.validation import validate_config
    
    settings = Settings(_env_file=".env.test")
    result = validate_config(settings)
    
    assert result.valid
    assert len(result.warnings) == 0
    assert len(result.errors) == 0
```

## Best Practices

### 1. **No Hardcoded Secrets**
```python
# ❌ Bad
client_secret = "hardcoded-secret"

# ✅ Good
client_secret: str  # Required from environment
```

### 2. **Use Type Hints**
```python
# ❌ Bad
cors_origins = Field(...)

# ✅ Good
cors_origins: List[str] = Field(default_factory=list)
```

### 3. **Provide Defaults Where Sensible**
```python
# Optional with sensible default
log_level: str = "INFO"
redis_ttl: int = 3600  # 1 hour

# Required - no default
keycloak_url: str  # Must be explicitly set
```

### 4. **Validate Early**
```python
# Validate on application startup
async def startup():
    try:
        validate_config(settings)
    except ValidationError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
```

## Environment Files

### `.env.example`
Template for developers:
```bash
# Application
APP_NAME=secure-mcp-server
DEBUG=false
LOG_LEVEL=INFO

# Keycloak (REQUIRED)
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_CLIENT_ID=mcp-server
KEYCLOAK_CLIENT_SECRET=your-secret-here

# OAuth (REQUIRED)
OAUTH_ISSUER=http://localhost:8080/realms/mcp-realm
OAUTH_AUDIENCE=mcp-server
```

### `.env.development`
Development overrides:
```bash
DEBUG=true
LOG_LEVEL=DEBUG
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### `.env.production`
Production settings:
```bash
DEBUG=false
LOG_LEVEL=WARNING
REQUIRE_HTTPS=true
```

## Docker Integration

### Using ENV in Dockerfile
```dockerfile
# Set defaults that can be overridden
ENV APP_NAME=secure-mcp-server
ENV LOG_LEVEL=INFO

# Runtime overrides
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0"]
```

### Docker Compose
```yaml
services:
  mcp-server:
    env_file:
      - .env.docker
    environment:
      - KEYCLOAK_URL=http://keycloak:8080
      - REDIS_URL=redis://redis:6379/0
```

## Troubleshooting

### Common Issues

1. **Missing Required Variable**
   ```
   ValidationError: field required (type=value_error.missing)
   ```
   Solution: Check `.env` file or set environment variable

2. **Type Conversion Error**
   ```
   ValidationError: value is not a valid boolean
   ```
   Solution: Use true/false, not yes/no

3. **List Parsing Error**
   ```
   ValidationError: value is not a valid list
   ```
   Solution: Use comma-separated values

### Debug Configuration

```python
# Print all settings (masks secrets)
print(settings.model_dump())

# Check specific setting source
print(settings.__fields__["keycloak_url"].field_info)

# Validate without starting app
python -c "from src.config import settings; print(settings)"
```

## Future Enhancements

1. **Dynamic Reloading**
   - Watch for config changes
   - Reload without restart

2. **Configuration UI**
   - Admin interface for settings
   - Real-time validation

3. **Encrypted Secrets**
   - Support for encrypted values
   - Integration with KMS

4. **Feature Flags**
   - Toggle features dynamically
   - A/B testing support 