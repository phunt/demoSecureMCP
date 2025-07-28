"""Application configuration using Pydantic Settings"""

import os
from typing import List, Optional, Any, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl, field_validator, model_validator


class Settings(BaseSettings):
    """Application settings with clear URL separation"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application Settings
    app_name: str = Field(default="demoSecureMCP", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of workers")
    
    # ============================================================================
    # URL Configuration with Clear Context Separation
    # ============================================================================
    
    # External URLs (accessed from host machine)
    external_base_url: HttpUrl = Field(
        default="https://localhost",
        description="External base URL for accessing the API from host"
    )
    external_keycloak_url: HttpUrl = Field(
        default="http://localhost:8080",
        description="External Keycloak URL for host access"
    )
    
    # Internal URLs (container-to-container communication)
    internal_mcp_url: HttpUrl = Field(
        default="http://mcp-server:8000",
        description="Internal MCP server URL within Docker network"
    )
    internal_keycloak_url: HttpUrl = Field(
        default="http://keycloak:8080",
        description="Internal Keycloak URL within Docker network"
    )
    internal_redis_url: str = Field(
        default="redis://redis:6379/0",
        description="Internal Redis URL within Docker network"
    )
    
    # Public URLs (production endpoints)
    public_base_url: Optional[HttpUrl] = Field(
        default=None,
        description="Public API URL for production"
    )
    public_auth_url: Optional[HttpUrl] = Field(
        default=None,
        description="Public auth URL for production"
    )
    
    # Context Detection
    container_env: bool = Field(
        default=False,
        description="Whether running inside a Docker container"
    )
    
    # ============================================================================
    # Keycloak Configuration
    # ============================================================================
    keycloak_realm: str = Field(default="mcp-realm", description="Keycloak realm")
    keycloak_client_id: Optional[str] = Field(None, description="Keycloak client ID (for static registration)")
    keycloak_client_secret: Optional[str] = Field(None, description="Keycloak client secret (for static registration)")
    
    # Dynamic Client Registration
    use_dcr: bool = Field(default=False, description="Use Dynamic Client Registration")
    dcr_initial_access_token: Optional[str] = Field(None, description="Initial access token for DCR")
    
    # ============================================================================
    # OAuth Configuration (Explicit)
    # ============================================================================
    oauth_issuer: HttpUrl = Field(..., description="OAuth issuer URL (must match JWT tokens)")
    oauth_audience: str = Field(..., description="OAuth audience")
    
    # Computed OAuth URLs
    @property
    def oauth_jwks_uri(self) -> str:
        """JWKS URI - uses internal URL when in container for fetching"""
        # When in container, use internal URL for fetching JWKS
        if self.container_env:
            base_url = f"{self.internal_keycloak_url}/realms/{self.keycloak_realm}"
            return f"{base_url}/protocol/openid-connect/certs"
        # Otherwise use the issuer URL
        base_url = str(self.oauth_issuer).rstrip('/')
        return f"{base_url}/protocol/openid-connect/certs"
    
    @property
    def oauth_token_introspection_endpoint(self) -> str:
        """Token introspection endpoint - uses internal URL when in container"""
        # When in container, use internal URL for introspection
        if self.container_env:
            base_url = f"{self.internal_keycloak_url}/realms/{self.keycloak_realm}"
            return f"{base_url}/protocol/openid-connect/token/introspect"
        # Otherwise use the issuer URL
        base_url = str(self.oauth_issuer).rstrip('/')
        return f"{base_url}/protocol/openid-connect/token/introspect"
    
    # ============================================================================
    # MCP Server Configuration
    # ============================================================================
    mcp_resource_identifier: str = Field(..., description="MCP resource identifier")
    # Accept both string and list to handle different sources
    mcp_supported_scopes: Union[str, List[str]] = Field(
        default="mcp:read,mcp:write,mcp:infer",
        description="Supported OAuth scopes"
    )
    
    # ============================================================================
    # Context-Aware Properties
    # ============================================================================
    
    @property
    def keycloak_url(self) -> str:
        """Returns appropriate Keycloak URL based on context"""
        if self.container_env:
            return str(self.internal_keycloak_url)
        # Check if we should use public URL in production
        if not self.debug and self.public_auth_url:
            return str(self.public_auth_url)
        return str(self.external_keycloak_url)
    
    @property
    def redis_url(self) -> str:
        """Returns appropriate Redis URL based on context"""
        if self.container_env:
            return self.internal_redis_url
        # For local development without Docker
        return "redis://localhost:6379/0"
    
    @property
    def base_url(self) -> str:
        """Returns appropriate base URL based on context"""
        if not self.debug and self.public_base_url:
            return str(self.public_base_url)
        return str(self.external_base_url)
    
    # ============================================================================
    # Other Configuration
    # ============================================================================
    redis_ttl: int = Field(default=3600, description="Redis cache TTL in seconds")
    
    # Security Settings
    cors_origins: Union[str, List[str]] = Field(
        default="http://localhost:3000,http://localhost:3001",
        description="Allowed CORS origins"
    )
    require_https: bool = Field(default=True, description="Require HTTPS")
    hsts_max_age: int = Field(default=31536000, description="HSTS max age in seconds")
    
    # JWT Settings
    jwt_algorithms: Union[str, List[str]] = Field(
        default="RS256,RS384,RS512",
        description="Allowed JWT algorithms"
    )
    jwt_leeway: int = Field(default=10, description="JWT time validation leeway in seconds")
    
    # Logging
    log_format: str = Field(default="json", description="Log format (json or text)")
    log_file_path: Optional[str] = Field(None, description="Log file path")
    
    # ============================================================================
    # Validators
    # ============================================================================
    
    @field_validator("cors_origins", mode="after")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from comma-separated string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @field_validator("mcp_supported_scopes", mode="after")
    @classmethod
    def parse_scopes(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse scopes from comma-separated string or list"""
        if isinstance(v, str):
            return [scope.strip() for scope in v.split(",") if scope.strip()]
        return v
    
    @field_validator("jwt_algorithms", mode="after")
    @classmethod
    def parse_algorithms(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse algorithms from comma-separated string or list"""
        if isinstance(v, str):
            return [algo.strip() for algo in v.split(",") if algo.strip()]
        return v
    
    @model_validator(mode='after')
    def detect_container_context(self) -> 'Settings':
        """Auto-detect if running in a container"""
        self.container_env = (
            os.path.exists('/.dockerenv') or 
            os.environ.get('CONTAINER_ENV', '').lower() == 'true' or
            os.environ.get('DOCKER_CONTAINER', '').lower() == 'true'
        )
        return self
    
    @model_validator(mode='after')
    def validate_oauth_config(self) -> 'Settings':
        """Validate OAuth configuration"""
        # In production, issuer should use HTTPS
        if not self.debug and str(self.oauth_issuer).startswith("http://"):
            import warnings
            warnings.warn("OAuth issuer should use HTTPS in production")
        return self
    
    @model_validator(mode='after')
    def validate_dcr_config(self) -> 'Settings':
        """Validate DCR configuration"""
        if self.use_dcr:
            if not self.dcr_initial_access_token:
                raise ValueError("DCR_INITIAL_ACCESS_TOKEN required when USE_DCR=true")
        else:
            if not self.keycloak_client_id or not self.keycloak_client_secret:
                raise ValueError("KEYCLOAK_CLIENT_ID and KEYCLOAK_CLIENT_SECRET required when USE_DCR=false")
        return self
    
    @model_validator(mode='after')
    def normalize_list_fields(self) -> 'Settings':
        """Ensure list fields are actually lists after validation"""
        # These fields need to be lists for the rest of the application
        if isinstance(self.cors_origins, str):
            self.cors_origins = self.parse_cors_origins(self.cors_origins)
        if isinstance(self.mcp_supported_scopes, str):
            self.mcp_supported_scopes = self.parse_scopes(self.mcp_supported_scopes)
        if isinstance(self.jwt_algorithms, str):
            self.jwt_algorithms = self.parse_algorithms(self.jwt_algorithms)
        return self
    
    # ============================================================================
    # Computed Properties for Backward Compatibility
    # ============================================================================
    
    @property
    def openid_configuration_url(self) -> str:
        """OpenID Connect discovery URL - uses internal URL when in container"""
        if self.container_env:
            return f"{self.internal_keycloak_url}/realms/{self.keycloak_realm}/.well-known/openid-configuration"
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}/.well-known/openid-configuration"
    
    @property
    def token_endpoint(self) -> str:
        """Token endpoint URL"""
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}/protocol/openid-connect/token"
    
    @property
    def dcr_endpoint(self) -> str:
        """Dynamic client registration endpoint"""
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}/clients-registrations/openid-connect"
    
    def __repr__(self) -> str:
        """String representation hiding sensitive values"""
        return (
            f"<Settings "
            f"app_name={self.app_name} "
            f"debug={self.debug} "
            f"container_env={self.container_env} "
            f"keycloak_url={self.keycloak_url}>"
        )


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings 