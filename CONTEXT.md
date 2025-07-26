Okay, here's the comprehensive To-Do list for your Python/FastAPI MCP server, complete with relevant links to RFCs, specifications, and recommended tools.

---

### Python/FastAPI MCP Server Production To-Do List (with Keycloak)

This list focuses on the responsibilities of the MCP server author building on a REST interface.

---

### I. Core Authorization & Token Validation (OAuth 2.1 & PKCE)

Your REST interface already uses token-based auth, but you need to ensure it's fully compliant with OAuth 2.1 as enforced by Keycloak.

1.  **Integrate JWT Validation:**
    *   **Action:** Implement robust JWT validation for incoming requests.
    *   **Recommended Library:** `PyJWT` with `cryptography`.
        *   Install: `pip install PyJWT cryptography`
        *   **References:**
            *   [PyJWT Documentation](https://pyjwt.readthedocs.io/en/stable/)
            *   [Cryptography Library Documentation](https://cryptography.io/en/latest/)
    *   **Details:**
        *   **FastAPI Integration:** Create a [FastAPI dependency](https://fastapi.tiangolo.com/tutorial/dependencies/) (e.g., using `Depends`) or a [middleware](https://fastapi.tiangolo.com/tutorial/middleware/) that intercepts the `Authorization: Bearer` token.
        *   **Keycloak Metadata Discovery:** At application startup, fetch Keycloak's OpenID Connect discovery document (usually `https://{keycloak_url}/realms/{realm_name}/.well-known/openid-configuration`). Parse this JSON to extract the `jwks_uri`.
            *   **References:**
                *   [OpenID Connect Discovery 1.0 - .well-known URI](https://openid.net/specs/openid-connect-discovery-1_0.html#ProviderConfiguration)
                *   [Keycloak OpenID Connect Discovery](https://www.keycloak.org/docs/latest/securing_apps/#_oidc_discovery_endpoint)
        *   **JWKS Fetching & Caching:** Dynamically fetch the JWKS from the discovered `jwks_uri`. Implement caching for this JWKS (e.g., in-memory dictionary with a TTL of a few hours) to reduce network requests, ensuring periodic refresh for key rotation.
            *   **References:**
                *   [RFC 7517: JSON Web Key (JWK)](https://datatracker.ietf.org/doc/html/rfc7517) (Specifies JWKS structure)
        *   **JWT Validation Steps (with `PyJWT`):**
            *   Verify the JWT signature using the public key from the JWKS (matched by `kid` in the token header).
                *   **References:**
                    *   [RFC 7519: JSON Web Token (JWT)](https://datatracker.ietf.org/doc/html/rfc7519) (Core JWT spec)
                    *   [RFC 7515: JSON Web Signature (JWS)](https://datatracker.ietf.org/doc/html/rfc7515) (JWT signature spec)
            *   Validate the `iss` (issuer) claim against your Keycloak realm's URL.
            *   Validate the `aud` (audience) claim to ensure it includes your MCP server's identifier. **This is crucial.**
            *   Validate `exp` (expiration) and `nbf` (not before, if present) claims.
            *   Validate `alg` (algorithm) to ensure it's on an allowed list (e.g., `RS256`, `ES256`), preventing "alg=none" attacks.
            *   Extract `scope` or role claims (e.g., `realm_access.roles` or `resource_access.<your-client-id>.roles` from Keycloak if using roles in tokens) from the decoded token's payload.
                *   **References:**
                    *   [OAuth 2.0 Scopes (RFC 6749, Section 3.3)](https://datatracker.ietf.org/doc/html/rfc6749#section-3.3)
                    *   [Keycloak JWT Access Token Structure](https://www.keycloak.org/docs/latest/securing_apps/#_access_token)
        *   **Authorization Logic:** Based on the extracted scopes/roles, implement authorization rules within your FastAPI path operations (e.g., using custom decorators or dependencies to check for required scopes for each endpoint).
    *   **Rationale:** Secures your API by verifying that incoming tokens are legitimate, un-tampered, intended for your service, and carry sufficient permissions. Directly supports [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-05) requirements.

2.  **Ensure PKCE Compliance is Handled by Keycloak Client Setup:**
    *   **Action:** No implementation needed on your MCP server directly. Your MCP server validates the token (which PKCE helps protect *during issuance*).
    *   **Details:** Verify with whoever manages the MCP *client* applications that they are configured in Keycloak (e.g., as public clients) and implement [PKCE (Proof Key for Code Exchange)](https://datatracker.ietf.org/doc/html/rfc7636) when acquiring tokens from Keycloak. This protects the authorization code itself during the OAuth flow.
    *   **Rationale:** Keycloak (as the AS) mandates PKCE for public clients in OAuth 2.1; your MCP server only needs to validate the resulting token, not worry about the PKCE exchange itself.

### II. Dynamic Client Registration (RFC 7591)

1.  **Acknowledge Keycloak's Role:**
    *   **Action:** No implementation needed on your MCP server.
    *   **Recommended Tool:** Keycloak (as the Authorization Server).
    *   **Details:** Keycloak (as the Authorization Server) provides the necessary [OAuth 2.0 Dynamic Client Registration Protocol (RFC 7591)](https://datatracker.ietf.org/doc/html/rfc7591) endpoint. Confirm with the Keycloak administrator that this feature is enabled and appropriately secured if MCP clients will be using it for self-registration.
    *   **Rationale:** Your MCP server is a protected resource, not an Authorization Server handling client registration.

### III. Protected Resource Metadata (RFC 9728)

This is a **MANDATORY** implementation for your MCP server.

1.  **Implement `/.well-known/oauth-protected-resource` Endpoint:**
    *   **Action:** Create a **publicly accessible** FastAPI GET endpoint that provides your MCP server's OAuth 2.0 Protected Resource Metadata.
    *   **Recommended Tool:** FastAPI itself.
    *   **Details:**
        *   **Endpoint:** `@app.get("/.well-known/oauth-protected-resource", response_class=JSONResponse)`
        *   **Content:** Return a JSON document conforming to [OAuth 2.0 Protected Resource Metadata (RFC 9728)](https://datatracker.ietf.org/doc/html/rfc9728). Key fields include:
            *   `"issuer"`: Your Keycloak realm's full issuer URL.
            *   `"resource"`: A unique identifier for your MCP server/API (e.g., `https://api.mcp.example.com` or `urn:mcp:api`).
            *   `"token_types_supported"`: `["Bearer"]`.
            *   `"scopes_supported"` (highly recommended): An array of strings listing all scopes your MCP server recognizes and enforces (e.g., `["mcp:read", "mcp:write", "mcp:infer"]`).
            *   `"token_introspection_endpoint"` (recommended): The URL to Keycloak's [token introspection endpoint (RFC 7662)](https://datatracker.ietf.org/doc/html/rfc7662).
        *   **FastAPI Example Sketch:**
            ```python
            from fastapi import FastAPI
            from fastapi.responses import JSONResponse

            app = FastAPI()

            @app.get("/.well-known/oauth-protected-resource", tags=["Metadata"])
            async def get_protected_resource_metadata():
                metadata = {
                    "issuer": "YOUR_KEYCLOAK_ISSUER_URL", # e.g., "https://auth.example.com/realms/mcp"
                    "resource": "YOUR_MCP_SERVER_RESOURCE_IDENTIFIER", # e.g., "https://api.mcp.example.com" or "urn:mcp:resource"
                    "token_introspection_endpoint": "YOUR_KEYCLOAK_INTROSPECTION_URL",
                    "token_types_supported": ["Bearer"],
                    "scopes_supported": ["mcp:read_data", "mcp:write_data", "profile", "email"]
                }
                return JSONResponse(content=metadata, media_type="application/json")
            ```
    *   **Rationale:** This is a **MANDATORY** requirement for MCP servers, allowing MCP clients to automatically discover how to authorize requests to your server.

### IV. Authorization Server Metadata (RFC 8414)

1.  **Consume Keycloak's Discovery Endpoint:**
    *   **Action:** No implementation for *providing* this metadata on your MCP server.
    *   **Recommended Tool:** Keycloak (as the Authorization Server).
    *   **Details:** Your token validation setup (from I.1) will automatically consume Keycloak's [OAuth 2.0 Authorization Server Metadata (RFC 8414)](https://datatracker.ietf.org/doc/html/rfc8414) compliant discovery endpoint (`/.well-known/openid-configuration`). This is where your MCP server will automatically find the `jwks_uri` for token validation.
    *   **Rationale:** Keycloak handles providing this metadata; your MCP server (as a client of Keycloak in this context) consumes it.

### V. General Production & Security Best Practices (Python/FastAPI Specific)

1.  **Enforce HTTPS/TLS:**
    *   **Action:** Deploy your FastAPI application behind a reverse proxy or cloud load balancer that handles SSL/TLS termination.
    *   **Recommended Tool:** `Nginx` (for on-prem/VMs) or your cloud provider's Load Balancer (e.g., AWS ALB, GCP Load Balancer).
        *   **References:**
            *   [Nginx Official Site](https://www.nginx.com/)
            *   [Let's Encrypt](https://letsencrypt.org/) (for free TLS certificates)
            *   [MDN Web Docs on HTTPS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security) (for HSTS headers)
    *   **Details:** Configure redirects for HTTP to HTTPS, and ensure valid, renewed certificates are in place. Implement Strict-Transport-Security (HSTS) headers.
    *   **Rationale:** Protects all data in transit, including sensitive tokens.

2.  **Robust Error Handling:**
    *   **Action:** Use FastAPI's built-in exception handling to return clear, non-verbose errors for authentication/authorization failures.
    *   **Recommended Tool:** FastAPI's `HTTPException`.
    *   **Details:** Return `HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")` for general token issues and `HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")` for authorization failures (e.g., wrong scope). Avoid stack traces or internal details in production error responses.
        *   **References:**
            *   [FastAPI Error Handling](https://fastapi.tiangolo.com/tutorial/handling-errors/)
            *   [HTTP Status Codes (MDN)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
    *   **Rationale:** Good API design and prevents information leakage.

3.  **Comprehensive Logging & Monitoring:**
    *   **Action:** Configure Python's standard logging to capture authentication and authorization events, errors, and access patterns.
    *   **Recommended Tool:** Python's built-in `logging` module.
    *   **Details:** Set up structured logging (e.g., using `python-json-logger` if sending to ELK/Splunk). Log user IDs, client IDs, requested scopes, and policy decisions. Ensure logs are rotated and securely stored.
        *   **References:**
            *   [Python Logging Howto](https://docs.python.org/3/howto/logging.html)
            *   [python-json-logger](https://github.com/madzak/python-json-logger)
            *   [OpenTelemetry for Python](https://opentelemetry.io/docs/instrumentation/python/) (for advanced observability/tracing)
    *   **Rationale:** Facilitates debugging, auditing, security monitoring, and incident response.

4.  **Secure Configuration Management:**
    *   **Action:** Do not hardcode secrets (Keycloak URLs, realm names, API keys).
    *   **Recommended Tools:**
        *   **Development:** `python-dotenv` for loading environment variables from a `.env` file.
        *   **Production:** Cloud-native secrets managers (e.g., AWS Secrets Manager, GCP Secret Manager, Azure Key Vault) or HashiCorp Vault.
        *   **References:**
            *   [python-dotenv](https://pypi.org/project/python-dotenv/)
            *   [Pydantic Settings Management](https://pydantic-docs.helpmanual.io/usage/settings/)
            *   [HashiCorp Vault](https://www.vaultproject.io/)
    *   **Details:** Access configurations via environment variables (`os.getenv()`) or a dedicated configuration library (e.g., Pydantic settings).
    *   **Rationale:** Prevents credential exposure in source control or deployments.

5.  **Performance & Scalability Deployment:**
    *   **Action:** Deploy your FastAPI application using a production-ready ASGI server.
    *   **Recommended Tool:** `Uvicorn` (typically run as a worker under `Gunicorn` for process management).
        *   Install: `pip install "uvicorn[standard]" gunicorn`
        *   **References:**
            *   [Uvicorn Documentation](https://www.uvicorn.org/)
            *   [Gunicorn Documentation](https://gunicorn.org/)
            *   [Deploying FastAPI (Official Guide)](https://fastapi.tiangolo.com/deployment/)
    *   **Details:** Configure `Gunicorn` to run multiple `Uvicorn` workers based on your server's CPU cores. Perform load testing to ensure your token validation and API endpoints scale as expected.
    *   **Rationale:** Ensures your MCP server remains performant and reliable under varying loads.

6.  **Containerization Best Practices:**
    *   **Action:** If deploying with Docker/Kubernetes, create a minimal Docker image and apply security best practices.
    *   **Recommended Tools:** `Docker`, `Kubernetes`.
    *   **Details:** Use a multi-stage build (e.g., build in a larger Python image, run in `python:3.x-slim-buster`). Use a non-root user inside the container. Define resource limits and requests, and implement readiness/liveness probes in your Kubernetes deployment.
        *   **References:**
            *   [Docker Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
            *   [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/workloads/pods/pod-topology-spread-constraints/#topology-spread-constraints-for-pods)
            *   [Official Python Docker Images](https://hub.docker.com/_/python)
    *   **Rationale:** Improves security and operational stability in containerized environments.

---
