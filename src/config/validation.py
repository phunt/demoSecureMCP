"""Configuration validation module

Validates settings on startup and provides helpful warnings for common issues.
"""

from typing import Dict, Any, List
from urllib.parse import urlparse

from src.config.settings import get_settings


def validate_settings() -> Dict[str, Any]:
    """
    Validate configuration settings and return validation results
    
    Returns:
        Dict containing validation status, errors, warnings, and info
    """
    settings = get_settings()
    
    errors: List[str] = []
    warnings: List[str] = []
    info: List[str] = []
    
    # Required fields validation (done by Pydantic automatically)
    info.append("✓ All required fields are set")
    
    # URL validations
    required_urls = [
        ('external_keycloak_url', 'External Keycloak URL'),
        ('internal_keycloak_url', 'Internal Keycloak URL'),
        ('oauth_issuer', 'OAuth Issuer'),
        ('mcp_resource_identifier', 'MCP Resource Identifier'),
    ]
    
    for field_name, display_name in required_urls:
        try:
            value = getattr(settings, field_name, None)
            if value:
                parsed = urlparse(str(value))
                if not parsed.scheme:
                    errors.append(f"{display_name} missing scheme (http/https)")
                elif not parsed.netloc:
                    errors.append(f"{display_name} missing host")
                else:
                    info.append(f"✓ {display_name}: {value}")
        except Exception as e:
            errors.append(f"Invalid {display_name}: {e}")
    
    # DCR validation
    if settings.use_dcr:
        info.append("✓ Dynamic Client Registration enabled")
        if not settings.dcr_initial_access_token:
            warnings.append("DCR enabled but no initial access token provided")
    else:
        info.append("✓ Using static client credentials")
        if not settings.keycloak_client_id or not settings.keycloak_client_secret:
            errors.append("Static credentials required when DCR is disabled")
    
    # OAuth audience validation
    if not settings.oauth_audience:
        errors.append("OAuth audience is required")
    else:
        info.append(f"✓ OAuth audience: {settings.oauth_audience}")
    
    # Redis validation
    try:
        if not settings.redis_url:
            warnings.append("No Redis URL configured - JWKS caching disabled")
        else:
            info.append(f"✓ Redis URL: {settings.redis_url}")
    except Exception as e:
        warnings.append(f"Redis configuration issue: {e}")
    
    # Security warnings for production
    if not settings.debug:
        # Production mode checks
        if not settings.require_https:
            warnings.append("HTTPS not required in production mode")
            
        if settings.log_format != "json":
            warnings.append("JSON logging recommended for production")
            
        if settings.workers < 2:
            warnings.append("Consider increasing workers for production")
            
        # Check for development URLs in production
        dev_patterns = ['localhost', '127.0.0.1', 'http://']
        for pattern in dev_patterns:
            if hasattr(settings, 'keycloak_url') and pattern in str(settings.keycloak_url):
                warnings.append(f"Development URL pattern '{pattern}' found in Keycloak URL")
            if pattern in str(settings.oauth_issuer):
                warnings.append(f"Development URL pattern '{pattern}' found in OAuth issuer")
    
    # Container context detection
    if settings.container_env:
        info.append("✓ Running in container context")
        info.append(f"  Using internal Keycloak URL: {settings.keycloak_url}")
        info.append(f"  Using internal Redis URL: {settings.redis_url}")
    else:
        info.append("✓ Running in host context")
        info.append(f"  Using external Keycloak URL: {settings.keycloak_url}")
        
        # Check Redis URL for localhost in non-container context
        if "redis://" in settings.redis_url and "localhost" not in settings.redis_url and not settings.debug:
            warnings.append("Using non-localhost Redis URL outside container")
    
    # CORS configuration
    if not settings.cors_origins:
        warnings.append("No CORS origins configured")
    else:
        info.append(f"✓ CORS origins: {', '.join(settings.cors_origins)}")
        
    # Scope configuration
    if not settings.mcp_supported_scopes:
        warnings.append("No MCP scopes configured")
    else:
        info.append(f"✓ Supported scopes: {', '.join(settings.mcp_supported_scopes)}")
        
    # JWT algorithm validation
    if not settings.jwt_algorithms:
        errors.append("No JWT algorithms configured")
    elif 'none' in [alg.lower() for alg in settings.jwt_algorithms]:
        errors.append("'none' algorithm is not allowed for security reasons")
    else:
        info.append(f"✓ JWT algorithms: {', '.join(settings.jwt_algorithms)}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "summary": {
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "debug": settings.debug,
            "container_env": settings.container_env,
            "workers": settings.workers,
            "log_level": settings.log_level,
            "log_format": settings.log_format,
            "use_dcr": settings.use_dcr
        }
    }


def validate_and_print():
    """Validate settings and print results to console"""
    results = validate_settings()
    
    print("\n" + "="*60)
    print("Configuration Validation Results")
    print("="*60)
    
    # Print summary
    print("\nSummary:")
    for key, value in results["summary"].items():
        print(f"  {key}: {value}")
    
    # Print info
    if results["info"]:
        print("\nConfiguration Info:")
        for msg in results["info"]:
            print(f"  {msg}")
    
    # Print warnings
    if results["warnings"]:
        print("\n⚠️  Warnings:")
        for warning in results["warnings"]:
            print(f"  - {warning}")
    
    # Print errors
    if results["errors"]:
        print("\n❌ Errors:")
        for error in results["errors"]:
            print(f"  - {error}")
        print("\nConfiguration validation failed!")
    else:
        print("\n✅ Configuration validation passed!")
    
    print("="*60 + "\n")
    
    # Exit if errors
    if not results["valid"]:
        import sys
        sys.exit(1) 