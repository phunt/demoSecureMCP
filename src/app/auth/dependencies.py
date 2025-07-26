"""FastAPI authentication dependencies"""

from typing import List, Optional, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt.exceptions import InvalidTokenError

from src.app.auth.jwt_validator import jwt_validator, TokenPayload


# Security scheme for OpenAPI documentation
security_scheme = HTTPBearer(
    scheme_name="OAuth2",
    description="Bearer token using JWT from Keycloak",
    bearerFormat="JWT",
    auto_error=True
)


async def get_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)]
) -> str:
    """Extract token from Authorization header"""
    return credentials.credentials


async def get_current_user(
    token: Annotated[str, Depends(get_token)]
) -> TokenPayload:
    """
    Get current authenticated user from JWT token
    
    Args:
        token: JWT token from Authorization header
        
    Returns:
        TokenPayload: Validated token payload with user info
        
    Raises:
        HTTPException: 401 if token is invalid
    """
    try:
        payload = await jwt_validator.validate_token(token)
        return payload
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_scope(scope: str):
    """
    Create a dependency that requires a specific scope
    
    Args:
        scope: Required scope
        
    Returns:
        Dependency function that validates the scope
    """
    async def scope_checker(
        current_user: Annotated[TokenPayload, Depends(get_current_user)]
    ) -> TokenPayload:
        if not jwt_validator.has_scope(current_user, scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scope: {scope}"
            )
        return current_user
    
    return scope_checker


def require_any_scope(scopes: List[str]):
    """
    Create a dependency that requires any of the specified scopes
    
    Args:
        scopes: List of allowed scopes
        
    Returns:
        Dependency function that validates the scopes
    """
    async def scope_checker(
        current_user: Annotated[TokenPayload, Depends(get_current_user)]
    ) -> TokenPayload:
        if not jwt_validator.has_any_scope(current_user, scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of: {', '.join(scopes)}"
            )
        return current_user
    
    return scope_checker


def require_all_scopes(scopes: List[str]):
    """
    Create a dependency that requires all specified scopes
    
    Args:
        scopes: List of required scopes
        
    Returns:
        Dependency function that validates the scopes
    """
    async def scope_checker(
        current_user: Annotated[TokenPayload, Depends(get_current_user)]
    ) -> TokenPayload:
        if not jwt_validator.has_all_scopes(current_user, scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required all: {', '.join(scopes)}"
            )
        return current_user
    
    return scope_checker


# Pre-defined scope dependencies for MCP operations
RequireMcpRead = Depends(require_scope("mcp:read"))
RequireMcpWrite = Depends(require_scope("mcp:write"))
RequireMcpInfer = Depends(require_scope("mcp:infer"))
RequireMcpAny = Depends(require_any_scope(["mcp:read", "mcp:write", "mcp:infer"])) 