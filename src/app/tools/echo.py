"""Echo tool for MCP server

A simple tool that echoes back messages with optional transformations.
"""

from fastmcp import Context
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class EchoRequest(BaseModel):
    """Request model for echo tool"""
    message: str
    uppercase: bool = False
    timestamp: bool = False


class EchoResponse(BaseModel):
    """Response model for echo tool"""
    echo: str
    timestamp: Optional[str] = None
    length: int


async def echo_tool(request: EchoRequest, ctx: Optional[Context] = None) -> EchoResponse:
    """
    Echo the provided message with optional transformations.
    
    This is a simple demonstration tool that shows how MCP tools
    can process input and return structured responses. Requires
    mcp:read scope for access.
    
    Args:
        request: EchoRequest containing message and options
        ctx: FastMCP context (optional)
        
    Returns:
        EchoResponse with processed message
    """
    # Log the request
    logger.info(f"Echo tool called with message: {request.message[:50]}...")
    
    # Process the message
    message = request.message
    if request.uppercase:
        message = message.upper()
    
    # Create response
    response = EchoResponse(
        echo=message,
        length=len(request.message)
    )
    
    # Add timestamp if requested
    if request.timestamp:
        response.timestamp = datetime.utcnow().isoformat()
    
    # Log context info if available
    if ctx:
        logger.debug(f"Context info: {ctx}")
    
    logger.info("Echo tool completed successfully")
    return response 