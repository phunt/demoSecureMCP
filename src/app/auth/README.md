# Authentication & Authorization

This directory contains the OAuth 2.1 compliant authentication and authorization implementation for the Secure MCP Server.

## Components

```
auth/
├── __init__.py
├── dependencies.py    # FastAPI dependencies for auth
└── jwt_validator.py   # JWT token validation logic
```

## JWT Token Validation (`jwt_validator.py`)

The `JWTValidator` class handles all JWT validation operations:

### Key Features

1. **JWKS Caching**
   - Fetches public keys from Keycloak's JWKS endpoint
   - Caches in Redis with configurable TTL
   - Automatic refresh on cache miss

2. **Token Validation Steps**
   ```python
   async def validate_token(token: str) -> TokenPayload:
       # 1. Decode without verification to check claims
       # 2. Handle azp claim (Keycloak client credentials)
       # 3. Fetch JWKS (from cache or Keycloak)
       # 4. Verify signature with public key
       # 5. Validate claims (iss, aud/azp, exp, nbf)
       # 6. Return TokenPayload
   ```

3. **Keycloak Compatibility**
   - Handles `azp` (authorized party) claim for client credentials
   - Supports both `aud` and `azp` claims
   - Configurable issuer validation

### Configuration

Environment variables:
- `OAUTH_ISSUER`: Expected token issuer
- `OAUTH_AUDIENCE`: Expected audience (client ID)
- `OAUTH_JWKS_URI`: JWKS endpoint URL
- `JWT_ALGORITHMS`: Allowed algorithms (default: RS256, RS384, RS512)
- `JWT_LEEWAY`: Time leeway for exp/nbf validation (seconds)

### Error Handling

Common validation errors:
- `Invalid token format`: Malformed JWT
- `Token signature verification failed`: Invalid signature
- `Token is expired`: Past expiration time
- `Token used before issued`: nbf claim violation
- `Invalid issuer`: Wrong token issuer
- `Invalid audience`: Wrong aud/azp claim

## Authentication Dependencies (`dependencies.py`)

FastAPI dependencies for protecting endpoints:

### 1. **Token Extraction**

```python
async def get_token(authorization: str = Header(...)) -> str:
    """Extract Bearer token from Authorization header"""
    # Validates format: "Bearer <token>"
    # Case-insensitive bearer check
    # Returns token string
```

### 2. **User Authentication**

```python
async def get_current_user(
    token: str = Depends(get_token),
    request: Request
) -> TokenPayload:
    """Validate token and return user info"""
    # Validates JWT token
    # Logs authentication attempt
    # Stores user context in request.state
    # Returns TokenPayload with user info
```

### 3. **Scope-Based Authorization**

Base class for scope checking:
```python
class RequireScope:
    def __init__(self, required_scope: str):
        self.required_scope = required_scope
    
    async def __call__(
        self,
        request: Request,
        payload: TokenPayload = Depends(get_current_user)
    ) -> TokenPayload:
        # Extract user scopes
        # Check if required scope present
        # Log authorization decision
        # Raise 403 if unauthorized
```

Pre-defined scope requirements:
- `RequireMcpRead = RequireScope("mcp:read")`
- `RequireMcpWrite = RequireScope("mcp:write")`
- `RequireMcpInfer = RequireScope("mcp:infer")`

### 4. **Advanced Authorization**

```python
class RequireAnyScope:
    """Require ANY of the specified scopes"""
    def __init__(self, scopes: List[str]):
        self.scopes = scopes

class RequireAllScopes:
    """Require ALL of the specified scopes"""
    def __init__(self, scopes: List[str]):
        self.scopes = scopes
```

## Security Context

The authentication system populates `request.state` with:

```python
request.state.user_id      # Subject from JWT (sub claim)
request.state.user_scopes  # List of user's scopes
request.state.client_ip    # Client IP address
```

This context is available throughout the request lifecycle for:
- Logging and auditing
- Business logic decisions
- Response customization

## Usage Examples

### Basic Protected Endpoint

```python
@app.get("/api/v1/user/profile")
async def get_profile(
    current_user: Annotated[TokenPayload, Depends(get_current_user)]
):
    return {
        "user_id": current_user.sub,
        "email": current_user.email
    }
```

### Endpoint Requiring Specific Scope

```python
@app.post("/api/v1/data/write")
async def write_data(
    data: DataModel,
    current_user: Annotated[TokenPayload, RequireMcpWrite]
):
    # User has mcp:write scope
    return {"status": "written"}
```

### Multiple Scope Options

```python
@app.get("/api/v1/data/read")
async def read_data(
    current_user: Annotated[
        TokenPayload, 
        RequireAnyScope(["mcp:read", "mcp:admin"])
    ]
):
    # User has either mcp:read OR mcp:admin
    return {"data": "..."}
```

### Accessing Security Context

```python
@app.get("/api/v1/audit/log")
async def audit_log(
    request: Request,
    current_user: Annotated[TokenPayload, Depends(get_current_user)]
):
    logger.info(
        "Audit log accessed",
        user_id=request.state.user_id,
        scopes=request.state.user_scopes,
        client_ip=request.state.client_ip
    )
    return {"entries": [...]}
```

## Security Best Practices

1. **Always validate tokens** - Never trust client-provided data
2. **Use specific scopes** - Principle of least privilege
3. **Log security events** - Authentication and authorization decisions
4. **Handle errors gracefully** - Don't leak implementation details
5. **Cache appropriately** - Balance security and performance

## Testing Authentication

### Unit Tests
```python
# Test JWT validation
async def test_valid_token():
    token = create_test_token(sub="user123", scope="mcp:read")
    payload = await jwt_validator.validate_token(token)
    assert payload.sub == "user123"

# Test scope checking
async def test_scope_requirement():
    dep = RequireMcpWrite()
    with pytest.raises(HTTPException) as exc:
        await dep(request, payload_without_write_scope)
    assert exc.value.status_code == 403
```

### Integration Tests
See `tests/test_client_credentials.py` for full OAuth flow testing.

## Troubleshooting

### Common Issues

1. **"Invalid token format"**
   - Check Authorization header format
   - Ensure "Bearer " prefix is present

2. **"Token signature verification failed"**
   - JWKS endpoint may be unreachable
   - Token may be from different issuer
   - Check Docker networking if in containers

3. **"Invalid audience"**
   - Token has wrong client ID
   - Check OAUTH_AUDIENCE setting
   - For Keycloak, may need to check azp claim

4. **"Token is expired"**
   - Token lifetime exceeded
   - Check Keycloak token settings
   - Request new token

## Future Enhancements

- Token introspection endpoint support
- Refresh token handling
- Dynamic scope registration
- Role-based access control (RBAC)
- Multi-tenant support 