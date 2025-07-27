"""MCP Server implementation with demo tools"""

import logging
from typing import Dict, Any

from fastmcp import FastMCP, Context
from fastapi import Request

from src.app.tools.echo import echo_tool, EchoRequest
from src.app.tools.timestamp import timestamp_tool, TimestampRequest
from src.app.tools.calculator import calculator_tool, CalculatorRequest
from src.core.logging import get_logger, security_logger


logger = get_logger(__name__)


# Create FastMCP server instance
mcp = FastMCP(
    "demoSecureMCP",
    description="A secure MCP server with OAuth 2.1 authentication and demo tools"
)


def create_secure_context(request: Request) -> Dict[str, Any]:
    """Create context with security information from the request"""
    return {
        "user_id": getattr(request.state, "user_id", None),
        "user_scopes": getattr(request.state, "user_scopes", []),
        "client_ip": getattr(request.state, "client_ip", None),
        "correlation_id": getattr(request.state, "correlation_id", None),
        "request_id": getattr(request.state, "request_id", None),
    }


# Register the echo tool (requires mcp:read)
@mcp.tool
async def echo(
    message: str,
    uppercase: bool = False,
    timestamp: bool = False,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Echo the provided message with optional transformations.
    
    This is a simple demonstration tool that shows how MCP tools
    can process input and return structured responses. Requires
    mcp:read scope for access.
    
    Args:
        message: Message to echo back
        uppercase: Convert message to uppercase
        timestamp: Include timestamp in response
        ctx: FastMCP context
        
    Returns:
        Dict with echo response
    """
    request = EchoRequest(
        message=message,
        uppercase=uppercase,
        timestamp=timestamp
    )
    
    response = await echo_tool(request, ctx)
    
    # Log tool usage
    if ctx:
        security_info = ctx.get("security", {})
        security_logger.log_authorization_decision(
            user_id=security_info.get("user_id", "unknown"),
            resource="/tools/echo",
            action="execute",
            allowed=True,
            required_scope="mcp:read",
            user_scopes=security_info.get("user_scopes", []),
            client_ip=security_info.get("client_ip"),
            extra={"tool": "echo", "message_length": len(message)}
        )
    
    return response.model_dump()


# Register the timestamp tool (requires mcp:read)
@mcp.tool
async def get_timestamp(
    format: str = None,
    timezone: str = None,
    include_epoch: bool = False,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Get current timestamp with various formatting options.
    
    This tool provides flexible timestamp generation with timezone
    support and multiple output formats. Requires mcp:read scope.
    
    Args:
        format: Custom strftime format string (e.g., '%Y-%m-%d %H:%M:%S')
        timezone: Timezone name (e.g., 'America/New_York', 'Europe/London')
        include_epoch: Include Unix epoch timestamp
        ctx: FastMCP context
        
    Returns:
        Dict with timestamp information
    """
    request = TimestampRequest(
        format=format,
        timezone=timezone,
        include_epoch=include_epoch
    )
    
    response = await timestamp_tool(request, ctx)
    
    # Log tool usage
    if ctx:
        security_info = ctx.get("security", {})
        security_logger.log_authorization_decision(
            user_id=security_info.get("user_id", "unknown"),
            resource="/tools/get_timestamp",
            action="execute",
            allowed=True,
            required_scope="mcp:read",
            user_scopes=security_info.get("user_scopes", []),
            client_ip=security_info.get("client_ip"),
            extra={"tool": "get_timestamp", "timezone": timezone}
        )
    
    return response.model_dump()


# Register the calculator tool (requires mcp:write)
@mcp.tool
async def calculate(
    operation: str,
    operands: list,
    precision: int = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Perform mathematical calculations with various operations.
    
    This tool demonstrates operations that modify state (requiring write scope).
    Supports basic arithmetic, power operations, square root, and factorial.
    Requires mcp:write scope for access.
    
    Args:
        operation: One of: add, subtract, multiply, divide, power, sqrt, factorial
        operands: Numbers to operate on (most operations require 2, sqrt/factorial require 1)
        precision: Decimal precision for the result
        ctx: FastMCP context
        
    Returns:
        Dict with calculation result
    """
    request = CalculatorRequest(
        operation=operation,
        operands=operands,
        precision=precision
    )
    
    response = await calculator_tool(request, ctx)
    
    # Log tool usage
    if ctx:
        security_info = ctx.get("security", {})
        security_logger.log_authorization_decision(
            user_id=security_info.get("user_id", "unknown"),
            resource="/tools/calculate",
            action="execute",
            allowed=True,
            required_scope="mcp:write",
            user_scopes=security_info.get("user_scopes", []),
            client_ip=security_info.get("client_ip"),
            extra={"tool": "calculate", "operation": operation}
        )
    
    return response.model_dump()


# Add a resource for server information
@mcp.resource("mcp://server/info")
async def get_server_info(ctx: Context = None) -> str:
    """
    Get information about the MCP server.
    
    Returns server metadata including version, available tools,
    and security configuration.
    """
    info = {
        "name": "demoSecureMCP",
        "version": "0.1.0",
        "description": "A secure MCP server with OAuth 2.1 authentication",
        "tools": [
            {
                "name": "echo",
                "description": "Echo messages with transformations",
                "required_scope": "mcp:read"
            },
            {
                "name": "get_timestamp", 
                "description": "Get current timestamp with formatting",
                "required_scope": "mcp:read"
            },
            {
                "name": "calculate",
                "description": "Perform mathematical calculations",
                "required_scope": "mcp:write"
            }
        ],
        "authentication": {
            "type": "OAuth 2.1",
            "issuer": "Keycloak",
            "scopes": ["mcp:read", "mcp:write", "mcp:infer"]
        }
    }
    
    if ctx:
        await ctx.info("Server information retrieved")
    
    return str(info)


# Add a prompt for interactive tool usage
@mcp.prompt
async def tool_usage_guide(tool_name: str = None) -> str:
    """
    Get an interactive guide for using MCP tools.
    
    Provides examples and best practices for tool usage.
    """
    if tool_name == "echo":
        return """
        Echo Tool Usage Guide
        ====================
        
        The echo tool returns your message with optional transformations.
        
        Examples:
        - Simple echo: echo("Hello, World!")
        - Uppercase: echo("hello", uppercase=True)
        - With timestamp: echo("Event occurred", timestamp=True)
        
        Required scope: mcp:read
        """
    elif tool_name == "get_timestamp":
        return """
        Timestamp Tool Usage Guide
        ==========================
        
        The timestamp tool provides current time in various formats.
        
        Examples:
        - Current time: get_timestamp()
        - Custom format: get_timestamp(format="%Y-%m-%d")
        - With timezone: get_timestamp(timezone="America/New_York")
        - Unix epoch: get_timestamp(include_epoch=True)
        
        Required scope: mcp:read
        """
    elif tool_name == "calculate":
        return """
        Calculator Tool Usage Guide
        ===========================
        
        The calculator performs mathematical operations.
        
        Examples:
        - Addition: calculate("add", [5, 3])
        - Division with precision: calculate("divide", [10, 3], precision=2)
        - Square root: calculate("sqrt", [16])
        - Factorial: calculate("factorial", [5])
        
        Required scope: mcp:write
        """
    else:
        return """
        MCP Tools Overview
        ==================
        
        Available tools:
        1. echo - Echo messages with transformations (mcp:read)
        2. get_timestamp - Get formatted timestamps (mcp:read)
        3. calculate - Perform calculations (mcp:write)
        
        Use tool_usage_guide(tool_name) for specific examples.
        """ 