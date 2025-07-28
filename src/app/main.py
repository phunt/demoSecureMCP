"""FastAPI application for secure MCP server

This module implements the main FastAPI application with OAuth 2.0 protection,
MCP tool endpoints, and proper security configuration.
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config.settings import get_settings
from src.config.validation import validate_and_print
from src.core.logging import configure_logging
from src.core.middleware import (
    CorrelationIDMiddleware,
    LoggingMiddleware,
    SecurityContextMiddleware,
)
from src.app.auth.jwt_validator import jwt_validator
from src.app.auth.dependencies import (
    get_current_user,
    RequireMcpRead,
    RequireMcpWrite,
    RequireMcpInfer,
    TokenPayload
)

# Import MCP tools
from src.app.tools.echo import echo_tool, EchoRequest
from src.app.tools.timestamp import timestamp_tool, TimestampRequest
from src.app.tools.calculator import calculator_tool, CalculatorRequest

# Import DCR client
from src.app.auth.dcr_client import DCRClient

# Configure logging first
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Get settings
    settings = get_settings()
    
    # Validate configuration
    validate_and_print()
    
    # Initialize JWT validator
    await jwt_validator.initialize()
    logger.info("JWT validator initialized")
    
    # Initialize DCR client if enabled
    if settings.use_dcr:
        dcr_client = DCRClient(settings)
        
        # Get initial access token and register client
        initial_token = settings.dcr_initial_access_token
        if initial_token:
            try:
                registered_client = await dcr_client.get_or_register_client(initial_token)
                logger.info(f"Got client via DCR: {registered_client.client_id}")
                # Update settings with registered client credentials
                settings.keycloak_client_id = registered_client.client_id
                settings.keycloak_client_secret = registered_client.client_secret
                # Store client credentials for later use
                app.state.dcr_client_id = registered_client.client_id
                app.state.dcr_client_secret = registered_client.client_secret
            except Exception as e:
                logger.error(f"Failed to register client via DCR: {e}")
                raise
    
    yield
    
    # Cleanup
    await jwt_validator.close()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Secure MCP Server",
    description="Model Context Protocol server with OAuth 2.0 security",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Get settings for middleware configuration
settings = get_settings()

# Add middleware
app.add_middleware(SecurityContextMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Public Endpoints
# ============================================================================

@app.get("/", tags=["Public"])
async def root():
    """Root endpoint - returns service information"""
    return {
        "service": "Secure MCP Server",
        "version": "0.1.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "oauth_metadata": "/.well-known/oauth-protected-resource"
    }


@app.get("/health", tags=["Public"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/.well-known/oauth-protected-resource", tags=["Public"])
async def get_protected_resource_metadata():
    """
    OAuth 2.0 Protected Resource Metadata (RFC 9728)
    
    This endpoint provides metadata about the OAuth protection of this resource server.
    """
    settings = get_settings()
    
    metadata = {
        "issuer": str(settings.oauth_issuer),
        "resource": settings.mcp_resource_identifier,
        "token_introspection_endpoint": settings.oauth_token_introspection_endpoint,
        "token_types_supported": ["Bearer"],
        "scopes_supported": settings.mcp_supported_scopes,
        "bearer_methods_supported": ["header"],
        "resource_documentation": "https://github.com/yourusername/demoSecureMCP",
        "resource_signing_alg_values_supported": settings.jwt_algorithms,
    }
    
    return JSONResponse(
        content=metadata,
        media_type="application/json",
        headers={
            "Cache-Control": "public, max-age=3600",
        }
    )


# ============================================================================
# Protected Endpoints
# ============================================================================

@app.get("/api/v1/user", tags=["Protected"])
async def get_user_info(current_user: TokenPayload = Depends(get_current_user)):
    """
    Get current user information
    
    Returns the authenticated user's token payload information.
    """
    return {
        "sub": current_user.sub,
        "preferred_username": current_user.preferred_username,
        "email": current_user.email,
        "email_verified": current_user.email_verified,
        "client_id": current_user.client_id,
        "scopes": jwt_validator.extract_scopes(current_user),
    }


@app.get("/api/v1/dcr-info", tags=["Testing"], include_in_schema=settings.debug)
async def get_dcr_info():
    """
    Get DCR client information (debug only)
    
    Returns the dynamically registered client ID for testing purposes.
    Only available when DEBUG=true and USE_DCR=true.
    """
    if not settings.debug:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found"
        )
    
    if not settings.use_dcr:
        return {"dcr_enabled": False}
    
    # For testing only - include the actual credentials being used
    client_id = getattr(app.state, "dcr_client_id", None) or settings.keycloak_client_id
    client_secret = getattr(app.state, "dcr_client_secret", None) or settings.keycloak_client_secret
    
    return {
        "dcr_enabled": True,
        "client_id": client_id,
        "client_secret": client_secret,  # Only in debug mode!
        "has_secret": bool(client_secret),
        "using_dynamic": bool(getattr(app.state, "dcr_client_id", None))
    }


# ============================================================================
# MCP Tool Endpoints
# ============================================================================

# Tool discovery endpoint
@app.get("/api/v1/tools", tags=["MCP Tools"])
async def list_tools(current_user: TokenPayload = Depends(get_current_user)):
    """
    List available MCP tools
    
    Returns a list of available tools with their required scopes.
    """
    return {
        "tools": [
            {
                "name": "echo",
                "description": "Echo back a message",
                "endpoint": "/api/v1/tools/echo",
                "required_scope": "mcp:read",
                "method": "POST"
            },
            {
                "name": "timestamp", 
                "description": "Get current timestamp with optional timezone",
                "endpoint": "/api/v1/tools/timestamp",
                "required_scope": "mcp:read",
                "method": "POST"
            },
            {
                "name": "calculator",
                "description": "Perform basic arithmetic calculations",
                "endpoint": "/api/v1/tools/calculator",
                "required_scope": "mcp:write",
                "method": "POST"
            }
        ]
    }


# Echo Tool
@app.post("/api/v1/tools/echo", tags=["MCP Tools"])
async def echo_endpoint(
    request: EchoRequest,
    current_user: TokenPayload = Depends(RequireMcpRead)
) -> Dict[str, Any]:
    """
    Echo tool - requires mcp:read scope
    
    Returns the provided message with metadata.
    """
    # Call the tool without context since it's optional
    result = await echo_tool(request)
    return {
        "tool": "echo",
        "result": result,
        "user": current_user.preferred_username or current_user.sub,
        "client": current_user.client_id
    }

# Timestamp Tool  
@app.post("/api/v1/tools/timestamp", tags=["MCP Tools"])
async def timestamp_endpoint(
    request: TimestampRequest,
    current_user: TokenPayload = Depends(RequireMcpRead)
) -> Dict[str, Any]:
    """
    Timestamp tool - requires mcp:read scope
    
    Returns current timestamp with optional timezone conversion.
    """
    # Call the tool without context since it's optional
    result = await timestamp_tool(request)
    return {
        "tool": "timestamp",
        "result": result,
        "user": current_user.preferred_username or current_user.sub,
        "client": current_user.client_id
    }


# Calculator Tool
@app.post("/api/v1/tools/calculator", tags=["MCP Tools"])
async def calculate_endpoint(
    request: CalculatorRequest,
    current_user: TokenPayload = Depends(RequireMcpWrite)
) -> Dict[str, Any]:
    """
    Calculator tool - requires mcp:write scope
    
    Performs arithmetic calculations.
    """
    # Call the tool without context since it's optional
    result = await calculator_tool(request)
    return {
        "tool": "calculator", 
        "result": result,
        "user": current_user.preferred_username or current_user.sub,
        "client": current_user.client_id
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected errors"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    ) 