"""
Secure MCP Server
A production-ready MCP server with OAuth 2.1/PKCE compliance using Keycloak
"""

from contextlib import asynccontextmanager
from typing import Annotated, Dict, Any, List

from fastapi import FastAPI, Depends, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.config.settings import settings
from src.config.validation import validate_and_print
from src.core.logging import configure_logging
from src.core.middleware import (
    CorrelationIDMiddleware,
    LoggingMiddleware,
    SecurityContextMiddleware
)
from src.app.auth.jwt_validator import jwt_validator
from src.app.auth.dependencies import (
    get_current_user,
    TokenPayload,
    RequireMcpRead,
    RequireMcpWrite,
    RequireMcpInfer
)
from src.app.auth.dcr_client import DCRClient
from src.app.tools.echo import echo_tool, EchoRequest
from src.app.tools.timestamp import timestamp_tool, TimestampRequest
from src.app.tools.calculator import calculator_tool, CalculatorRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    print("Starting up...")
    
    # Configure logging
    configure_logging()
    
    # Validate configuration
    validate_and_print()
    
    # Handle Dynamic Client Registration if enabled
    if settings.use_dcr:
        print("Using Dynamic Client Registration...")
        if settings.dcr_initial_access_token:
            print(f"DCR token found (length: {len(settings.dcr_initial_access_token)})")
            print(f"DCR token repr last 5 chars: {repr(settings.dcr_initial_access_token[-5:])}")
        else:
            print("WARNING: No DCR initial access token found!")
        
        dcr_client = DCRClient(settings)
        
        try:
            # Register or load existing registration
            registered_client = await dcr_client.get_or_register_client(
                initial_access_token=settings.dcr_initial_access_token
            )
            
            # Update settings with DCR credentials
            settings.keycloak_client_id = registered_client.client_id
            settings.keycloak_client_secret = registered_client.client_secret
            
            print(f"DCR successful - Client ID: {registered_client.client_id}")
            
        except Exception as e:
            print(f"DCR failed: {e}")
            raise
    
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

# Add custom middleware (order matters - reverse order of execution)
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityContextMiddleware) 
app.add_middleware(CorrelationIDMiddleware)


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


# MCP Tool endpoints
@app.get("/api/v1/tools", tags=["MCP Tools"])
async def list_tools(
    current_user: Annotated[TokenPayload, Depends(get_current_user)]
):
    """List available MCP tools and their requirements"""
    user_scopes = jwt_validator.extract_scopes(current_user)
    
    tools = [
        {
            "name": "echo",
            "description": "Echo messages with optional transformations",
            "endpoint": "/api/v1/tools/echo",
            "required_scope": "mcp:read",
            "available": "mcp:read" in user_scopes,
            "parameters": {
                "message": "string (required)",
                "uppercase": "boolean (optional, default: false)",
                "timestamp": "boolean (optional, default: false)"
            }
        },
        {
            "name": "get_timestamp",
            "description": "Get current timestamp with formatting options",
            "endpoint": "/api/v1/tools/timestamp",
            "required_scope": "mcp:read",
            "available": "mcp:read" in user_scopes,
            "parameters": {
                "format": "string (optional, strftime format)",
                "timezone": "string (optional, timezone name)",
                "include_epoch": "boolean (optional, default: false)"
            }
        },
        {
            "name": "calculate",
            "description": "Perform mathematical calculations",
            "endpoint": "/api/v1/tools/calculate",
            "required_scope": "mcp:write",
            "available": "mcp:write" in user_scopes,
            "parameters": {
                "operation": "string (required: add|subtract|multiply|divide|power|sqrt|factorial)",
                "operands": "array of numbers (required)",
                "precision": "integer (optional, decimal places)"
            }
        }
    ]
    
    return {
        "tools": tools,
        "user_scopes": user_scopes,
        "total": len(tools),
        "available": len([t for t in tools if t["available"]])
    }


@app.post("/api/v1/tools/echo", tags=["MCP Tools"])
async def echo_endpoint(
    request: EchoRequest,
    current_user: Annotated[TokenPayload, RequireMcpRead],
    req: Request
):
    """
    Echo tool - returns your message with optional transformations.
    
    Requires mcp:read scope.
    """
    # Create a mock context for the tool
    class MockContext:
        async def info(self, msg: str): pass
        async def debug(self, msg: str): pass
        async def warning(self, msg: str): pass
        async def error(self, msg: str): pass
    
    ctx = MockContext()
    
    try:
        response = await echo_tool(request, ctx)
        return {"result": response.model_dump()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}"
        )


@app.post("/api/v1/tools/timestamp", tags=["MCP Tools"])
async def timestamp_endpoint(
    request: TimestampRequest,
    current_user: Annotated[TokenPayload, RequireMcpRead],
    req: Request
):
    """
    Timestamp tool - get current timestamp with various formatting options.
    
    Requires mcp:read scope.
    """
    # Create a mock context for the tool
    class MockContext:
        async def info(self, msg: str): pass
        async def debug(self, msg: str): pass
        async def warning(self, msg: str): pass
        async def error(self, msg: str): pass
    
    ctx = MockContext()
    
    try:
        response = await timestamp_tool(request, ctx)
        return {"result": response.model_dump()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}"
        )


@app.post("/api/v1/tools/calculate", tags=["MCP Tools"])
async def calculate_endpoint(
    request: CalculatorRequest,
    current_user: Annotated[TokenPayload, RequireMcpWrite],
    req: Request
):
    """
    Calculator tool - perform mathematical calculations.
    
    Requires mcp:write scope.
    
    Supported operations:
    - add: Addition of 2 or more numbers
    - subtract: Subtraction (left to right)
    - multiply: Multiplication of 2 or more numbers
    - divide: Division (left to right)
    - power: Exponentiation (base^exponent)
    - sqrt: Square root (single operand)
    - factorial: Factorial (single operand)
    """
    # Create a mock context for the tool
    class MockContext:
        async def info(self, msg: str): pass
        async def debug(self, msg: str): pass
        async def warning(self, msg: str): pass
        async def error(self, msg: str): pass
    
    ctx = MockContext()
    
    try:
        response = await calculator_tool(request, ctx)
        return {"result": response.model_dump()}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}"
        )


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "src.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 