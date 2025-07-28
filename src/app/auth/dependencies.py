"""Authentication dependencies for FastAPI endpoints

Provides dependency injection functions for token validation and authorization.
"""

from typing import Optional, List, Callable
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.app.auth.jwt_validator import jwt_validator, TokenPayload
from src.core.logging import get_logger, security_logger

logger = get_logger(__name__)

# Security scheme for OpenAPI documentation
security = HTTPBearer(
    scheme_name="Bearer",
    description="OAuth 2.0 Bearer Token",
    bearerFormat="JWT",
    auto_error=True
)


async def get_token_from_header(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract and validate bearer token from Authorization header
    
    Args:
        credentials: HTTP authorization credentials from header
        
    Returns:
        str: The bearer token
        
    Raises:
        HTTPException: If token is missing or malformed
    """
    if not credentials:
        logger.warning("Missing authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if credentials.scheme.lower() != "bearer":
        logger.warning(f"Invalid authorization scheme: {credentials.scheme}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return credentials.credentials


async def get_current_user(
    token: str = Depends(get_token_from_header)
) -> TokenPayload:
    """
    Validate JWT token and return the current user's token payload
    
    Args:
        token: JWT bearer token from Authorization header
        
    Returns:
        TokenPayload: Validated token payload with user information
        
    Raises:
        HTTPException: If token validation fails
    """
    try:
        # Validate token and get payload
        payload = await jwt_validator.validate_token(token)
        
        # Log successful authentication
        security_logger.log_auth_attempt(
            success=True,
            user_id=payload.sub,
            client_id=payload.client_id
        )
        
        return payload
        
    except HTTPException:
        # Re-raise FastAPI exceptions
        raise
    except Exception as e:
        # Log failed authentication
        security_logger.log_auth_attempt(
            success=False,
            reason=str(e)
        )
        
        logger.error(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )


def require_scope(scope: str) -> Callable:
    """
    Create a dependency that requires a specific OAuth scope
    
    Args:
        scope: The required OAuth scope
        
    Returns:
        Callable: A FastAPI dependency function
    """
    async def scope_checker(
        current_user: TokenPayload = Depends(get_current_user)
    ) -> TokenPayload:
        """Check if the current user has the required scope"""
        scopes = jwt_validator.extract_scopes(current_user)
        
        has_scope = scope in scopes
        
        # Log authorization check
        security_logger.log_authorization_check(
            resource="API",
            action=scope,
            granted=has_scope,
            user_id=current_user.sub,
            required_scope=scope
        )
        
        if not has_scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {scope}"
            )
        return current_user
    
    return scope_checker


def require_any_scope(scopes: List[str]) -> Callable:
    """
    Create a dependency that requires any of the specified OAuth scopes
    
    Args:
        scopes: List of OAuth scopes (user needs at least one)
        
    Returns:
        Callable: A FastAPI dependency function
    """
    async def scope_checker(
        current_user: TokenPayload = Depends(get_current_user)
    ) -> TokenPayload:
        """Check if the current user has any of the required scopes"""
        user_scopes = jwt_validator.extract_scopes(current_user)
        
        has_scope = any(scope in user_scopes for scope in scopes)
        
        # Log authorization check
        security_logger.log_authorization_check(
            resource="API",
            action=f"any of: {', '.join(scopes)}",
            granted=has_scope,
            user_id=current_user.sub,
            required_scope=f"any of: {', '.join(scopes)}"
        )
        
        if not has_scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required any of: {', '.join(scopes)}"
            )
        return current_user
    
    return scope_checker


def require_all_scopes(scopes: List[str]) -> Callable:
    """
    Create a dependency that requires all of the specified OAuth scopes
    
    Args:
        scopes: List of OAuth scopes (user needs all of them)
        
    Returns:
        Callable: A FastAPI dependency function
    """
    async def scope_checker(
        current_user: TokenPayload = Depends(get_current_user)
    ) -> TokenPayload:
        """Check if the current user has all required scopes"""
        user_scopes = jwt_validator.extract_scopes(current_user)
        
        has_scope = all(scope in user_scopes for scope in scopes)
        
        # Log authorization check
        security_logger.log_authorization_check(
            resource="API",
            action=f"all of: {', '.join(scopes)}",
            granted=has_scope,
            user_id=current_user.sub,
            required_scope=f"all of: {', '.join(scopes)}"
        )
        
        if not has_scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required all: {', '.join(scopes)}"
            )
        return current_user
    
    return scope_checker


# Pre-defined scope dependencies for MCP operations
RequireMcpRead = require_scope("mcp:read")
RequireMcpWrite = require_scope("mcp:write")
RequireMcpInfer = require_scope("mcp:infer")
RequireMcpAny = require_any_scope(["mcp:read", "mcp:write", "mcp:infer"]) 