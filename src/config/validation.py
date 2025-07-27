"""Environment validation module"""

import sys
from typing import List, Dict, Any
from urllib.parse import urlparse

from src.config.settings import settings


class ConfigValidationError(Exception):
    """Configuration validation error"""
    pass


def validate_url(url: str, name: str) -> None:
    """Validate URL format"""
    try:
        result = urlparse(str(url))
        if not all([result.scheme, result.netloc]):
            raise ConfigValidationError(f"{name} is not a valid URL: {url}")
    except Exception as e:
        raise ConfigValidationError(f"Invalid {name}: {e}")


def validate_settings() -> Dict[str, Any]:
    """
    Validate all settings at startup
    
    Returns:
        Dict with validation results and warnings
        
    Raises:
        ConfigValidationError: If critical validation fails
    """
    errors = []
    warnings = []
    info = []
    
    # Check required fields
    required_fields = [
        ('keycloak_url', 'Keycloak URL'),
        ('oauth_issuer', 'OAuth Issuer'),
        ('oauth_audience', 'OAuth Audience'),
        ('oauth_jwks_uri', 'JWKS URI'),
        ('mcp_resource_identifier', 'MCP Resource Identifier'),
    ]
    
    # Only require client_id if not using DCR
    if not settings.use_dcr:
        required_fields.append(('keycloak_client_id', 'Keycloak Client ID'))
    else:
        # When using DCR, check for initial access token
        if not settings.dcr_initial_access_token:
            errors.append("DCR Initial Access Token is required when USE_DCR is enabled")
    
    for field, name in required_fields:
        value = getattr(settings, field, None)
        if not value:
            errors.append(f"{name} is required but not set")
    
    # Validate URLs
    url_fields = [
        ('keycloak_url', 'Keycloak URL'),
        ('oauth_issuer', 'OAuth Issuer'),
        ('oauth_jwks_uri', 'JWKS URI'),
    ]
    
    for field, name in url_fields:
        value = getattr(settings, field, None)
        if value:
            try:
                validate_url(value, name)
            except ConfigValidationError as e:
                errors.append(str(e))
    
    # Check production settings
    if not settings.debug:
        # Production mode checks
        info.append("Running in PRODUCTION mode")
        
        if not settings.require_https:
            warnings.append("REQUIRE_HTTPS is disabled in production mode")
        
        if settings.log_format != "json":
            warnings.append("Consider using JSON log format in production")
        
        if settings.workers < 2:
            warnings.append("Consider increasing WORKERS for production (current: 1)")
        
        # Check for development URLs in production
        dev_patterns = ['localhost', '127.0.0.1', 'http://']
        for pattern in dev_patterns:
            if pattern in str(settings.keycloak_url):
                warnings.append(f"Development URL pattern '{pattern}' found in Keycloak URL")
            if pattern in str(settings.oauth_issuer):
                warnings.append(f"Development URL pattern '{pattern}' found in OAuth Issuer")
    else:
        # Development mode
        info.append("Running in DEVELOPMENT mode")
    
    # Check Redis connection
    if "localhost" in settings.redis_url and not settings.debug:
        warnings.append("Using localhost Redis URL in production")
    
    # Check CORS origins
    if not settings.cors_origins:
        warnings.append("No CORS origins configured")
    else:
        info.append(f"CORS origins: {', '.join(settings.cors_origins)}")
    
    # Check scopes
    if not settings.mcp_supported_scopes:
        errors.append("No MCP scopes configured")
    else:
        info.append(f"Supported scopes: {', '.join(settings.mcp_supported_scopes)}")
    
    # Check JWT algorithms
    if not settings.jwt_algorithms:
        errors.append("No JWT algorithms configured")
    elif 'none' in [alg.lower() for alg in settings.jwt_algorithms]:
        errors.append("Insecure 'none' algorithm in JWT_ALGORITHMS")
    
    # Raise exception if there are errors
    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ConfigValidationError(error_msg)
    
    return {
        "status": "valid",
        "warnings": warnings,
        "info": info,
        "environment": {
            "debug": settings.debug,
            "workers": settings.workers,
            "log_level": settings.log_level,
            "log_format": settings.log_format,
        }
    }


def print_validation_results(results: Dict[str, Any]) -> None:
    """Print validation results in a formatted way"""
    print("\n" + "=" * 60)
    print("Configuration Validation Results")
    print("=" * 60)
    
    # Print info
    if results["info"]:
        print("\n📋 Information:")
        for item in results["info"]:
            print(f"   ✓ {item}")
    
    # Print warnings
    if results["warnings"]:
        print("\n⚠️  Warnings:")
        for warning in results["warnings"]:
            print(f"   - {warning}")
    
    # Print environment summary
    env = results["environment"]
    print("\n🔧 Environment:")
    print(f"   - Mode: {'Development' if env['debug'] else 'Production'}")
    print(f"   - Workers: {env['workers']}")
    print(f"   - Log Level: {env['log_level']}")
    print(f"   - Log Format: {env['log_format']}")
    
    print("\n✅ Configuration is valid")
    print("=" * 60 + "\n")


def validate_and_print() -> None:
    """Validate settings and print results"""
    try:
        results = validate_settings()
        print_validation_results(results)
    except ConfigValidationError as e:
        print(f"\n❌ {e}", file=sys.stderr)
        sys.exit(1) 