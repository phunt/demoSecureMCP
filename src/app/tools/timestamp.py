"""Timestamp tool for MCP server

Provides current timestamp with various formatting options.
"""

from typing import Optional
from fastmcp import Context
from pydantic import BaseModel
from datetime import datetime
from zoneinfo import ZoneInfo


class TimestampRequest(BaseModel):
    """Request model for timestamp tool"""
    format: Optional[str] = None
    timezone: Optional[str] = None
    include_epoch: bool = False


class TimestampResponse(BaseModel):
    """Response model for timestamp tool"""
    timestamp: str
    epoch: Optional[float] = None
    timezone: str
    format_used: str


async def timestamp_tool(request: TimestampRequest, ctx: Optional[Context] = None) -> TimestampResponse:
    """
    Get current timestamp with various formatting options.
    
    Args:
        request: TimestampRequest with formatting options
        ctx: FastMCP context (optional)
        
    Returns:
        TimestampResponse with formatted timestamp
    """
    # Get current time
    tz = ZoneInfo(request.timezone) if request.timezone else None
    now = datetime.now(tz)
    
    # Determine format
    format_str = request.format or "%Y-%m-%d %H:%M:%S %Z"
    
    # Create response
    response = TimestampResponse(
        timestamp=now.strftime(format_str),
        timezone=str(now.tzinfo) if now.tzinfo else "UTC",
        format_used=format_str
    )
    
    # Add epoch if requested
    if request.include_epoch:
        response.epoch = now.timestamp()
    
    return response 