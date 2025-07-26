"""FastAPI authentication dependencies"""

from typing import List, Optional, Annotated

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt.exceptions import InvalidTokenError

from src.app.auth.jwt_validator import jwt_validator, TokenPayload
from src.core.logging import security_logger


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
    token: Annotated[str, Depends(get_token)],
    request: Request
) -> TokenPayload:
    """
    Get current authenticated user from JWT token
    
    Args:
        token: JWT token from Authorization header
        request: FastAPI request object
        
    Returns:
        TokenPayload: Validated token payload with user info
        
    Raises:
        HTTPException: 401 if token is invalid
    """
    client_ip = getattr(request.state, "client_ip", None)
    
    try:
        payload = await jwt_validator.validate_token(token)
        
        # Store user info in request state
        request.state.user_id = payload.sub
        request.state.user_scopes = jwt_validator.extract_scopes(payload)
        
        # Log successful authentication
        security_logger.log_authentication_attempt(
            success=True,
            user_id=payload.sub,
            client_ip=client_ip,
            extra={"preferred_username": payload.preferred_username}
        )
        
        return payload
    except InvalidTokenError as e:
        security_logger.log_authentication_attempt(
            success=False,
            client_ip=client_ip,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        security_logger.log_authentication_attempt(
            success=False,
            client_ip=client_ip,
            error=f"Unexpected error: {str(e)}"
        )
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
        current_user: Annotated[TokenPayload, Depends(get_current_user)],
        request: Request
    ) -> TokenPayload:
        has_scope = jwt_validator.has_scope(current_user, scope)
        client_ip = getattr(request.state, "client_ip", None)
        
        # Log authorization decision
        security_logger.log_authorization_decision(
            user_id=current_user.sub,
            resource=request.url.path,
            action=request.method,
            allowed=has_scope,
            required_scope=scope,
            user_scopes=jwt_validator.extract_scopes(current_user),
            client_ip=client_ip
        )
        
        if not has_scope:
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
        current_user: Annotated[TokenPayload, Depends(get_current_user)],
        request: Request
    ) -> TokenPayload:
        has_scope = jwt_validator.has_any_scope(current_user, scopes)
        client_ip = getattr(request.state, "client_ip", None)
        
        # Log authorization decision
        security_logger.log_authorization_decision(
            user_id=current_user.sub,
            resource=request.url.path,
            action=request.method,
            allowed=has_scope,
            required_scope=f"any of: {', '.join(scopes)}",
            user_scopes=jwt_validator.extract_scopes(current_user),
            client_ip=client_ip
        )
        
        if not has_scope:
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
        current_user: Annotated[TokenPayload, Depends(get_current_user)],
        request: Request
    ) -> TokenPayload:
        has_scope = jwt_validator.has_all_scopes(current_user, scopes)
        client_ip = getattr(request.state, "client_ip", None)
        
        # Log authorization decision
        security_logger.log_authorization_decision(
            user_id=current_user.sub,
            resource=request.url.path,
            action=request.method,
            allowed=has_scope,
            required_scope=f"all of: {', '.join(scopes)}",
            user_scopes=jwt_validator.extract_scopes(current_user),
            client_ip=client_ip
        )
        
        if not has_scope:
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