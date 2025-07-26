# Secure MCP Server TODO List

## Overview
Build a production-ready Python/FastAPI MCP server with OAuth 2.1/PKCE compliance, leveraging Keycloak for authentication and Docker for deployment.

## Task List

### 1. Project Setup
- **Status:** ✅ Completed
- **Description:** Initialize project structure with Python/FastAPI/FastMCP, Docker, and docker-compose
- **Actions:**
  - Create project directory structure
  - Initialize .venv and install base dependencies: `fastapi`, `fastmcp`, `uvicorn[standard]`, `gunicorn`
  - Create `.gitignore` with Python/Docker patterns
  - Set up `requirements.txt` and `requirements-dev.txt`

### 2. Keycloak Setup
- **Status:** ✅ Completed
- **Description:** Set up Keycloak container in docker-compose with realm and client configuration
- **Actions:**
  - Add Keycloak service to docker-compose.yml
  - Configure realm (e.g., "mcp-realm")
  - Create client configurations for MCP server
  - Enable PKCE for public clients
  - Configure client scopes: `mcp:read`, `mcp:write`, `mcp:infer`

### 3. JWT Validation Implementation
- **Status:** ✅ Completed
- **Description:** Implement JWT validation middleware with PyJWT and JWKS fetching from Keycloak
- **Dependencies:** `PyJWT`, `cryptography`, `httpx` (for async HTTP calls)
- **Actions:**
  - ✅ Fetch Keycloak's OpenID discovery document
  - ✅ Implement JWKS caching with TTL (using Redis)
  - ✅ Create JWT validation function with signature, issuer, audience, and expiry checks
  - ✅ Extract and validate scopes/roles from token
  - ✅ Handle Keycloak's use of 'azp' claim for client credentials flow
  - ✅ Implement FastAPI dependencies for token validation
  - ✅ Add scope-based authorization decorators

### 4. Protected Resource Metadata Endpoint
- **Status:** ✅ Completed
- **Description:** Create /.well-known/oauth-protected-resource endpoint (RFC 9728 compliance)
- **Actions:**
  - ✅ Implement GET endpoint returning OAuth 2.0 Protected Resource Metadata
  - ✅ Include issuer, resource identifier, token types, and supported scopes
  - ✅ Make endpoint publicly accessible (no auth required)
  - ✅ Add cache headers for client optimization
  - ✅ Include optional fields like token introspection endpoint and resource documentation

### 5. FastAPI Security Dependencies
- **Status:** ✅ Completed
- **Description:** Implement FastAPI dependencies for token validation and scope-based authorization
- **Actions:**
  - ✅ Create `get_current_user` dependency using JWT validation
  - ✅ Implement scope-checking decorators/dependencies
  - ✅ Add proper error handling (401/403 responses)  
  - ✅ Create user context extraction from validated tokens

### 6. Docker Configuration
- **Status:** ✅ Completed
- **Description:** Create production-ready Dockerfile with multi-stage build and security best practices
- **Actions:**
  - ✅ Multi-stage build: build stage with full Python, runtime with slim image
  - ✅ Run as non-root user
  - ✅ Copy only necessary files
  - ✅ Set up health check endpoint
  - ✅ Create production Dockerfile with Gunicorn
  - ✅ Configure Docker Compose integration
  - ✅ Handle Docker networking for service communication

### 7. Nginx Reverse Proxy
- **Status:** ✅ Completed
- **Description:** Configure Nginx reverse proxy with SSL/TLS termination in docker-compose
- **Actions:**
  - ✅ Add Nginx service to docker-compose
  - ✅ Configure SSL with Let's Encrypt or self-signed certs for dev
  - ✅ Set up HTTPS redirect and HSTS headers
  - ✅ Configure proxy pass to FastAPI service
  - ✅ Add security headers (X-Frame-Options, CSP, etc.)
  - ✅ Configure WebSocket support
  - ✅ Set up caching for .well-known endpoints

### 8. Environment Configuration
- **Status:** ✅ Completed
- **Description:** Set up secure configuration management with environment variables and .env files
- **Dependencies:** `python-dotenv`, `pydantic[dotenv]`
- **Actions:**
  - ✅ Create `.env.example` with all required variables
  - ✅ Implement Pydantic settings class
  - ✅ Configure Docker secrets for production
  - ✅ Add environment validation on startup
  - ✅ Create comprehensive documentation

### 9. Logging Setup
- **Status:** ✅ Completed
- **Description:** Configure structured logging with python-json-logger for security events
- **Dependencies:** `python-json-logger`
- **Actions:**
  - ✅ Set up JSON structured logging
  - ✅ Log authentication events, authorization decisions
  - ✅ Configure log levels per environment
  - ✅ Add correlation IDs for request tracking
  - ✅ Add request/response logging middleware
  - ✅ Include security context in logs

### 10. Demo MCP Tool
- **Status:** ⏳ Pending
- **Description:** Implement a simple MCP tool (e.g., echo or timestamp) to demonstrate secure access
- **Actions:**
  - Create `/tools/echo` endpoint requiring `mcp:read` scope
  - Implement request/response according to MCP protocol
  - Add OpenAPI documentation
  - Include in tool discovery endpoint

### 11. Docker Compose Configuration
- **Status:** ⏳ Pending
- **Description:** Finalize docker-compose.yml with all services
- **Services:**
  - MCP FastAPI server
  - Keycloak (auth server)
  - PostgreSQL (for Keycloak)
  - Nginx (reverse proxy)
  - Redis (for JWKS caching)
- **Actions:**
  - Define service dependencies
  - Configure networks and volumes
  - Set up health checks
  - Add restart policies

### 12. Testing & Verification
- **Status:** ⏳ Pending
- **Description:** Create test scripts to verify OAuth flow, token validation, and tool access
- **Actions:**
  - Create client credentials flow test
  - Test token validation with valid/invalid tokens
  - Verify scope enforcement
  - Create integration test for the demo tool
  - Document testing procedures

## Key Security Requirements Checklist

- [ ] OAuth 2.1 compliant token validation
- [ ] PKCE support (via Keycloak client config)
- [ ] RFC 9728 Protected Resource Metadata endpoint
- [ ] HTTPS/TLS enforcement
- [ ] Proper error handling without information leakage
- [ ] Structured security event logging
- [ ] No hardcoded secrets
- [ ] Container security best practices
- [ ] JWKS caching and rotation support

## Implementation References

- **OAuth 2.1:** [draft-ietf-oauth-v2-1-05](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-05)
- **PKCE:** [RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)
- **Protected Resource Metadata:** [RFC 9728](https://datatracker.ietf.org/doc/html/rfc9728)
- **JWT:** [RFC 7519](https://datatracker.ietf.org/doc/html/rfc7519)
- **JWKS:** [RFC 7517](https://datatracker.ietf.org/doc/html/rfc7517)

## Success Criteria

1. MCP server validates JWT tokens from Keycloak
2. Protected Resource Metadata endpoint is accessible
3. Demo tool requires valid token with appropriate scope
4. All services run via `docker-compose up`
5. HTTPS is enforced with proper certificates
6. Logs capture security events in structured format
7. No secrets in code or Docker images 