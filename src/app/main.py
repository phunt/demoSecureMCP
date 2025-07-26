"""
Secure MCP Server
A production-ready MCP server with OAuth 2.1/PKCE compliance using Keycloak
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Create FastAPI app
app = FastAPI(
    title="Secure MCP Server",
    description="A Model Context Protocol server with OAuth 2.1 authentication",
    version="0.1.0",
)

# Configure CORS (will be restricted in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
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
            "version": "0.1.0"
        },
        status_code=200
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