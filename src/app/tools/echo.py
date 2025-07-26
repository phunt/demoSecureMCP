"""Echo MCP tool for demonstrating secure access"""

from typing import Dict, Any, Optional
from datetime import datetime

from fastmcp import Context
from pydantic import BaseModel, Field

from src.core.logging import get_logger


logger = get_logger(__name__)


class EchoRequest(BaseModel):
    """Request model for echo tool"""
    message: str = Field(..., description="Message to echo back")
    uppercase: bool = Field(False, description="Convert message to uppercase")
    timestamp: bool = Field(False, description="Include timestamp in response")


class EchoResponse(BaseModel):
    """Response model for echo tool"""
    original: str = Field(..., description="Original message")
    echo: str = Field(..., description="Processed echo message")
    timestamp: Optional[str] = Field(None, description="Timestamp if requested")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


async def echo_tool(request: EchoRequest, ctx: Context) -> EchoResponse:
    """
    Echo the provided message with optional transformations.
    
    This is a simple demonstration tool that shows how MCP tools
    can process input and return structured responses. Requires
    mcp:read scope for access.
    
    Args:
        request: Echo request with message and options
        ctx: FastMCP context for logging and progress
        
    Returns:
        EchoResponse with processed message and metadata
    """
    await ctx.info(f"Processing echo request for message: '{request.message}'")
    
    # Process the message
    processed = request.message
    if request.uppercase:
        processed = processed.upper()
        await ctx.debug("Applied uppercase transformation")
    
    # Build response
    response = EchoResponse(
        original=request.message,
        echo=processed,
        metadata={
            "length": len(request.message),
            "words": len(request.message.split()),
            "uppercase_applied": request.uppercase
        }
    )
    
    # Add timestamp if requested
    if request.timestamp:
        response.timestamp = datetime.utcnow().isoformat()
        response.metadata["timestamp_added"] = True
        await ctx.debug("Added timestamp to response")
    
    await ctx.info("Echo request processed successfully")
    return response 