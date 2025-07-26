"""Timestamp MCP tool for demonstrating secure access"""

from datetime import datetime, timezone
from typing import Optional, Literal
from zoneinfo import ZoneInfo

from fastmcp import Context
from pydantic import BaseModel, Field

from src.core.logging import get_logger


logger = get_logger(__name__)


class TimestampRequest(BaseModel):
    """Request model for timestamp tool"""
    format: Optional[str] = Field(
        None,
        description="Custom strftime format string (e.g., '%Y-%m-%d %H:%M:%S')"
    )
    timezone: Optional[str] = Field(
        None,
        description="Timezone name (e.g., 'America/New_York', 'Europe/London')"
    )
    include_epoch: bool = Field(
        False,
        description="Include Unix epoch timestamp"
    )
    relative: Optional[Literal["seconds_ago", "minutes_ago", "hours_ago", "days_ago"]] = Field(
        None,
        description="Include relative time calculation"
    )


class TimestampResponse(BaseModel):
    """Response model for timestamp tool"""
    timestamp: str = Field(..., description="Formatted timestamp")
    iso8601: str = Field(..., description="ISO 8601 formatted timestamp")
    timezone: str = Field(..., description="Timezone used")
    epoch: Optional[int] = Field(None, description="Unix epoch timestamp")
    relative: Optional[str] = Field(None, description="Relative time description")


async def timestamp_tool(request: TimestampRequest, ctx: Context) -> TimestampResponse:
    """
    Get current timestamp with various formatting options.
    
    This tool provides flexible timestamp generation with timezone
    support and multiple output formats. Requires mcp:read scope.
    
    Args:
        request: Timestamp request with formatting options
        ctx: FastMCP context for logging and progress
        
    Returns:
        TimestampResponse with formatted timestamps
    """
    await ctx.info("Generating timestamp")
    
    # Determine timezone
    tz = timezone.utc
    timezone_name = "UTC"
    
    if request.timezone:
        try:
            tz = ZoneInfo(request.timezone)
            timezone_name = request.timezone
            await ctx.debug(f"Using timezone: {timezone_name}")
        except Exception as e:
            await ctx.warning(f"Invalid timezone '{request.timezone}', using UTC: {e}")
    
    # Get current time
    now = datetime.now(tz)
    
    # Format timestamp
    if request.format:
        try:
            formatted = now.strftime(request.format)
            await ctx.debug(f"Applied custom format: {request.format}")
        except Exception as e:
            await ctx.warning(f"Invalid format string, using default: {e}")
            formatted = now.strftime("%Y-%m-%d %H:%M:%S %Z")
    else:
        formatted = now.strftime("%Y-%m-%d %H:%M:%S %Z")
    
    # Build response
    response = TimestampResponse(
        timestamp=formatted,
        iso8601=now.isoformat(),
        timezone=timezone_name
    )
    
    # Add epoch if requested
    if request.include_epoch:
        response.epoch = int(now.timestamp())
        await ctx.debug("Added epoch timestamp")
    
    # Add relative time if requested
    if request.relative:
        utc_now = datetime.now(timezone.utc)
        delta = utc_now - now.astimezone(timezone.utc)
        
        if request.relative == "seconds_ago":
            relative_value = int(delta.total_seconds())
            response.relative = f"{relative_value} seconds ago"
        elif request.relative == "minutes_ago":
            relative_value = int(delta.total_seconds() / 60)
            response.relative = f"{relative_value} minutes ago"
        elif request.relative == "hours_ago":
            relative_value = int(delta.total_seconds() / 3600)
            response.relative = f"{relative_value} hours ago"
        elif request.relative == "days_ago":
            relative_value = int(delta.days)
            response.relative = f"{relative_value} days ago"
    
    await ctx.info("Timestamp generated successfully")
    return response 