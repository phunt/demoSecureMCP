# Core Utilities & Middleware

This directory contains cross-cutting concerns and shared utilities used throughout the demoSecureMCP application.

## Structure

```
core/
├── __init__.py
├── logging.py      # Structured logging configuration
└── middleware.py   # FastAPI middleware components
```

## Logging Module (`logging.py`)

Provides structured JSON logging with security event tracking.

### Features

1. **Structured JSON Logs**
   ```json
   {
     "timestamp": "2024-01-20T10:30:45.123Z",
     "level": "INFO",
     "logger": "src.app.auth.dependencies",
     "message": "Token validation successful",
     "correlation_id": "abc123",
     "user_id": "user_456",
     "client_ip": "192.168.1.100",
     "event_type": "auth_success"
   }
   ```

2. **Security Event Logger**
   ```python
   security_logger = SecurityEventLogger()
   
   # Log authentication attempt
   security_logger.log_auth_attempt(
       success=True,
       user_id="user123",
       client_ip="192.168.1.1",
       reason="Valid JWT token"
   )
   
   # Log authorization decision
   security_logger.log_authorization(
       user_id="user123",
       resource="/api/v1/tools/calculate",
       action="execute",
       allowed=True,
       required_scope="mcp:write",
       user_scopes=["mcp:read", "mcp:write"]
   )
   ```

3. **Configuration**
   - Log level from environment (`LOG_LEVEL`)
   - JSON or text format (`LOG_FORMAT`)
   - Optional file output (`LOG_FILE_PATH`)
   - Sensitive data filtering

### Usage

```python
from src.core.logging import get_logger, security_logger

# Get module logger
logger = get_logger(__name__)

# Standard logging
logger.info("Processing request", request_id=req_id)
logger.error("Failed to connect", error=str(e), retry_count=3)

# Security events
security_logger.log_token_validation(
    success=False,
    reason="Token expired",
    token_id=jti,
    client_ip=client_ip
)
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for unusual conditions
- **ERROR**: Error conditions that need attention
- **CRITICAL**: Critical failures requiring immediate action

## Middleware Module (`middleware.py`)

FastAPI middleware for request tracking and security context.

### 1. **Correlation ID Middleware**

Ensures every request has a unique correlation ID for tracking across services.

```python
class CorrelationIDMiddleware:
    """Add correlation ID to all requests"""
    
    # Checks for existing ID in headers:
    # - X-Correlation-ID
    # - X-Request-ID
    # - X-Trace-ID
    
    # Generates UUID if not present
    # Adds to request.state and response headers
```

**Benefits:**
- Track requests across microservices
- Correlate logs for debugging
- Support distributed tracing

### 2. **Security Context Middleware**

Extracts and stores security-relevant information in request state.

```python
class SecurityContextMiddleware:
    """Extract security context from authenticated requests"""
    
    # Sets request.state attributes:
    # - client_ip: Real client IP (handles proxies)
    # - user_agent: Client user agent
    # - user_id: From JWT if authenticated
    # - user_scopes: User's OAuth scopes
```

**Features:**
- Handles X-Forwarded-For headers
- Extracts from multiple proxy layers
- Makes context available to all handlers

### 3. **Logging Middleware**

Comprehensive request/response logging with performance metrics.

```python
class LoggingMiddleware:
    """Log all HTTP requests and responses"""
    
    # Logs include:
    # - Method, path, status code
    # - Request/response size
    # - Processing duration
    # - User context if authenticated
    # - Correlation ID
```

**Log Example:**
```json
{
  "event": "http_request",
  "method": "POST",
  "path": "/api/v1/tools/echo",
  "status_code": 200,
  "duration_ms": 45.2,
  "request_size": 128,
  "response_size": 256,
  "user_id": "user123",
  "correlation_id": "abc-def-ghi"
}
```

### 4. **Error Handling Middleware** (Future)

Potential middleware for consistent error responses:

```python
class ErrorHandlingMiddleware:
    """Consistent error response formatting"""
    
    # Features:
    # - Catch unhandled exceptions
    # - Format errors consistently
    # - Log stack traces (dev only)
    # - Hide sensitive information
```

## Middleware Stack Order

The order of middleware is important:

```python
# In main.py
app.add_middleware(CorrelationIDMiddleware)      # First: Add correlation ID
app.add_middleware(SecurityContextMiddleware)    # Second: Extract context
app.add_middleware(LoggingMiddleware)           # Third: Log with context
app.add_middleware(CORSMiddleware, ...)         # Fourth: CORS handling
```

## Security Considerations

### 1. **Data Sanitization**
- Remove sensitive data from logs
- Mask tokens and passwords
- Redact PII when configured

### 2. **Performance Impact**
- Minimal overhead design
- Async logging handlers
- Efficient JSON serialization

### 3. **Privacy Compliance**
- Configurable PII handling
- Log retention policies
- Right to erasure support

## Adding New Middleware

### Template

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class CustomMiddleware(BaseHTTPMiddleware):
    """Description of what this middleware does"""
    
    def __init__(self, app, setting1: str = "default"):
        super().__init__(app)
        self.setting1 = setting1
    
    async def dispatch(self, request: Request, call_next):
        # Pre-processing
        request.state.custom_value = "something"
        
        # Call the next middleware/handler
        response = await call_next(request)
        
        # Post-processing
        response.headers["X-Custom-Header"] = "value"
        
        return response
```

### Best Practices

1. **Keep it lightweight** - Middleware runs on every request
2. **Handle exceptions** - Don't let middleware break requests
3. **Use request.state** - For passing data to handlers
4. **Log sparingly** - Avoid verbose logging in middleware
5. **Test thoroughly** - Middleware affects all endpoints

## Utilities (Future)

Potential additions to core:

### 1. **Cache Utils**
```python
# src/core/cache.py
class CacheManager:
    """Manage Redis caching with TTL"""
    async def get(key: str) -> Optional[Any]
    async def set(key: str, value: Any, ttl: int)
    async def invalidate(pattern: str)
```

### 2. **Rate Limiting**
```python
# src/core/ratelimit.py
class RateLimiter:
    """Token bucket rate limiting"""
    async def check_rate_limit(user_id: str, endpoint: str) -> bool
```

### 3. **Metrics Collection**
```python
# src/core/metrics.py
class MetricsCollector:
    """Prometheus/StatsD metrics"""
    def increment(metric: str, tags: dict)
    def histogram(metric: str, value: float, tags: dict)
```

### 4. **Validation Helpers**
```python
# src/core/validators.py
def validate_uuid(value: str) -> UUID
def validate_email(email: str) -> str
def sanitize_user_input(text: str) -> str
```

## Testing

Core utilities should be thoroughly tested:

```python
# tests/test_core/test_logging.py
def test_security_logger():
    with capture_logs() as logs:
        security_logger.log_auth_attempt(
            success=True,
            user_id="test123"
        )
    
    assert logs[0]["event_type"] == "auth_attempt"
    assert logs[0]["success"] is True

# tests/test_core/test_middleware.py
async def test_correlation_id_middleware():
    request = create_test_request()
    middleware = CorrelationIDMiddleware(app)
    
    response = await middleware.dispatch(request, call_next)
    
    assert "X-Correlation-ID" in response.headers
    assert request.state.correlation_id is not None
```

## Performance Monitoring

Monitor core components:

1. **Logging Performance**
   - Log write latency
   - Queue sizes
   - Drop rates

2. **Middleware Timing**
   - Processing duration
   - Memory usage
   - Request throughput

3. **Cache Hit Rates**
   - JWKS cache hits/misses
   - Response cache effectiveness

## Configuration

Core utilities are configured via environment:

```bash
# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE_PATH=/var/log/mcp/app.log

# Middleware
ENABLE_REQUEST_LOGGING=true
CORRELATION_ID_HEADER=X-Correlation-ID
MAX_REQUEST_SIZE=10485760  # 10MB

# Performance
MIDDLEWARE_TIMEOUT=30
LOG_BUFFER_SIZE=1000
```

## Future Enhancements

1. **Distributed Tracing**
   - OpenTelemetry integration
   - Jaeger/Zipkin support

2. **Advanced Security**
   - Request signing
   - Replay attack prevention
   - Anomaly detection

3. **Performance Optimization**
   - Request/response compression
   - Connection pooling
   - Async optimizations 