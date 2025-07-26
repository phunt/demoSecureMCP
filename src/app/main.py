"""
Secure MCP Server
A production-ready MCP server with OAuth 2.1/PKCE compliance using Keycloak
"""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.config.settings import settings
from src.config.validation import validate_and_print
from src.app.auth.jwt_validator import jwt_validator
from src.app.auth.dependencies import (
    get_current_user,
    TokenPayload,
    RequireMcpRead,
    RequireMcpWrite,
    RequireMcpInfer
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    print("Starting up...")
    
    # Validate configuration
    validate_and_print()
    
    # Initialize JWT validator
    await jwt_validator.initialize()
    
    yield
    
    # Shutdown
    print("Shutting down...")
    await jwt_validator.close()


# Create FastAPI app
app = FastAPI(
    title="Secure MCP Server",
    description="A Model Context Protocol server with OAuth 2.1 authentication",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {"message": "Secure MCP Server", "status": "operational"}


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for Docker/Kubernetes"""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "mcp-server",
            "version": settings.app_version
        },
        status_code=200
    )


@app.get("/.well-known/oauth-protected-resource", tags=["Metadata"])
async def get_protected_resource_metadata():
    """
    OAuth 2.0 Protected Resource Metadata endpoint (RFC 9728)
    
    Provides metadata about this protected resource to help clients
    understand how to authenticate and authorize requests.
    
    This endpoint is publicly accessible (no authentication required).
    """
    metadata = {
        "issuer": str(settings.oauth_issuer),
        "resource": settings.mcp_resource_identifier,
        "token_introspection_endpoint": str(settings.oauth_token_introspection_endpoint) if settings.oauth_token_introspection_endpoint else None,
        "token_types_supported": ["Bearer"],
        "scopes_supported": settings.mcp_supported_scopes,
        "bearer_methods_supported": ["header"],
        "resource_documentation": "https://github.com/phunt/demoSecureMCP",
        "resource_signing_alg_values_supported": settings.jwt_algorithms,
    }
    
    # Remove None values for cleaner response
    metadata = {k: v for k, v in metadata.items() if v is not None}
    
    return JSONResponse(
        content=metadata,
        media_type="application/json",
        headers={
            "Cache-Control": "public, max-age=3600"  # Cache for 1 hour
        }
    )


# Protected endpoints for testing
@app.get("/api/v1/me", tags=["Auth"])
async def get_current_user_info(
    current_user: Annotated[TokenPayload, Depends(get_current_user)]
):
    """Get current user information from JWT token"""
    return {
        "sub": current_user.sub,
        "username": current_user.preferred_username,
        "email": current_user.email,
        "email_verified": current_user.email_verified,
        "scopes": jwt_validator.extract_scopes(current_user)
    }


@app.get("/api/v1/protected/read", tags=["Protected"])
async def protected_read(
    current_user: Annotated[TokenPayload, RequireMcpRead]
):
    """Protected endpoint requiring mcp:read scope"""
    return {
        "message": "You have read access",
        "user": current_user.preferred_username,
        "scope": "mcp:read"
    }


@app.get("/api/v1/protected/write", tags=["Protected"])
async def protected_write(
    current_user: Annotated[TokenPayload, RequireMcpWrite]
):
    """Protected endpoint requiring mcp:write scope"""
    return {
        "message": "You have write access",
        "user": current_user.preferred_username,
        "scope": "mcp:write"
    }


@app.get("/api/v1/protected/infer", tags=["Protected"])
async def protected_infer(
    current_user: Annotated[TokenPayload, RequireMcpInfer]
):
    """Protected endpoint requiring mcp:infer scope"""
    return {
        "message": "You have inference access",
        "user": current_user.preferred_username,
        "scope": "mcp:infer"
    }


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "src.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 