"""Middleware for request tracking and logging"""

import time
import uuid
import logging
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.logging import get_logger


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation IDs to requests for tracking"""
    
    CORRELATION_ID_HEADER = "X-Correlation-ID"
    REQUEST_ID_HEADER = "X-Request-ID"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add correlation ID to request and response"""
        
        # Get or generate correlation ID
        correlation_id = request.headers.get(self.CORRELATION_ID_HEADER)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Store in request state for access in handlers
        request.state.correlation_id = correlation_id
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add IDs to response headers
        response.headers[self.CORRELATION_ID_HEADER] = correlation_id
        response.headers[self.REQUEST_ID_HEADER] = request_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = get_logger("mcp_server.access")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details"""
        
        # Start timing
        start_time = time.time()
        
        # Get request details
        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""
        
        # Get correlation ID
        correlation_id = getattr(request.state, "correlation_id", None)
        request_id = getattr(request.state, "request_id", None)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Log request
        extra = {
            "correlation_id": correlation_id,
            "request_id": request_id,
            "method": method,
            "path": path,
            "query": query,
            "client_ip": client_ip,
            "user_agent": request.headers.get("user-agent"),
        }
        self.logger.info(f"Request started: {method} {path}", extra=extra)
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log response
            extra.update({
                "status_code": status_code,
                "duration_ms": duration_ms,
            })
            self.logger.info(
                f"Request completed: {method} {path} -> {status_code}",
                extra=extra
            )
            
            # Add timing header
            response.headers["X-Response-Time"] = f"{duration_ms}ms"
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log error
            extra.update({
                "duration_ms": duration_ms,
                "error": str(e),
                "error_type": type(e).__name__,
            })
            self.logger.error(
                f"Request failed: {method} {path} -> {type(e).__name__}",
                extra=extra,
                exc_info=True
            )
            raise
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Get client IP address from request"""
        # Check X-Forwarded-For header (for proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        if request.client:
            return request.client.host
        
        return None


class SecurityContextMiddleware(BaseHTTPMiddleware):
    """Middleware to add security context to requests"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security context to request state"""
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        request.state.client_ip = client_ip
        
        # Initialize user context
        request.state.user_id = None
        request.state.user_scopes = []
        
        # Process request
        response = await call_next(request)
        
        return response
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Get client IP address from request"""
        # Check X-Forwarded-For header (for proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        if request.client:
            return request.client.host
        
        return None 