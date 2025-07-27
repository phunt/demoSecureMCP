"""Application configuration using Pydantic Settings"""

from typing import List, Optional, Any, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl, field_validator, model_validator


class Settings(BaseSettings):
    """Application settings with validation"""
    
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
    
    # Keycloak Configuration
    keycloak_url: HttpUrl = Field(..., description="Keycloak base URL")
    keycloak_realm: str = Field(default="mcp-realm", description="Keycloak realm")
    keycloak_client_id: Optional[str] = Field(None, description="Keycloak client ID (for static registration)")
    keycloak_client_secret: Optional[str] = Field(None, description="Keycloak client secret (for static registration)")
    
    # Dynamic Client Registration
    use_dcr: bool = Field(default=False, description="Use Dynamic Client Registration")
    dcr_initial_access_token: Optional[str] = Field(None, description="Initial access token for DCR")
    
    # OAuth Configuration
    oauth_issuer: HttpUrl = Field(..., description="OAuth issuer URL")
    oauth_audience: str = Field(..., description="OAuth audience")
    oauth_jwks_uri: HttpUrl = Field(..., description="JWKS URI")
    oauth_token_introspection_endpoint: Optional[HttpUrl] = Field(None, description="Token introspection endpoint")
    
    # MCP Server Configuration
    mcp_resource_identifier: str = Field(..., description="MCP resource identifier")
    mcp_supported_scopes: Union[List[str], str] = Field(
        default="mcp:read,mcp:write,mcp:infer",
        description="Supported OAuth scopes"
    )
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    redis_ttl: int = Field(default=3600, description="Redis cache TTL in seconds")
    
    # Security Settings
    cors_origins: Union[List[str], str] = Field(
        default="http://localhost:3000,http://localhost:3001",
        description="Allowed CORS origins"
    )
    require_https: bool = Field(default=True, description="Require HTTPS")
    hsts_max_age: int = Field(default=31536000, description="HSTS max age in seconds")
    
    # JWT Validation Settings
    jwt_algorithms: Union[List[str], str] = Field(
        default="RS256,RS384,RS512",
        description="Allowed JWT algorithms"
    )
    jwt_leeway: int = Field(default=10, description="JWT time validation leeway in seconds")
    
    # Logging Configuration
    log_format: str = Field(default="json", description="Log format (json or text)")
    log_file_path: Optional[str] = Field(None, description="Log file path")
    
    @field_validator('mcp_supported_scopes', 'cors_origins', 'jwt_algorithms', mode='before')
    @classmethod
    def parse_comma_separated_list(cls, v: Union[List[str], str]) -> List[str]:
        """Parse comma-separated strings into lists"""
        if isinstance(v, str):
            return [s.strip() for s in v.split(',') if s.strip()]
        return v
    
    @model_validator(mode='after')
    def validate_client_config(self) -> 'Settings':
        """Validate client configuration - either DCR or static credentials required"""
        if not self.use_dcr:
            if not self.keycloak_client_id:
                raise ValueError("keycloak_client_id is required when not using DCR")
        return self
    
    @property
    def openid_config_url(self) -> str:
        """Get OpenID configuration URL"""
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}/.well-known/openid-configuration"


# Create settings instance
settings = Settings() 