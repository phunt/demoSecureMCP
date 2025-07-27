# Switching Between DCR and Non-DCR Modes

This document explains the key considerations when switching between Dynamic Client Registration (DCR) and static client credentials in Docker environments.

## Key Findings

### 1. Container Environment Variables

**Critical Issue**: Docker containers preserve environment variables from creation time.

- ❌ `docker compose restart` does NOT pick up new environment variables
- ✅ `docker compose down` + `docker compose up` DOES pick up new environment variables

```bash
# Wrong way - container keeps old environment
sed -i '' 's/USE_DCR=false/USE_DCR=true/' .env.docker
docker compose restart mcp-server  # Still uses old values!

# Correct way - container gets new environment
sed -i '' 's/USE_DCR=false/USE_DCR=true/' .env.docker
docker compose down mcp-server
docker compose up -d mcp-server  # Now uses new values
```

### 2. Issuer URL Mismatch

**Critical Issue**: JWT tokens are validated against their issuer claim.

| Context | Issuer URL | Used By |
|---------|------------|---------|
| Host machine | `http://localhost:8080` | Tests, setup scripts |
| Docker network | `http://keycloak:8080` | MCP server container |

This creates a fundamental conflict:
- Tests run from host need tokens issued by `localhost:8080`
- MCP server in container needs tokens issued by `keycloak:8080`

### 3. Configuration Requirements

#### For Non-DCR Mode (Static Credentials)
```env
USE_DCR=false
OAUTH_ISSUER=http://localhost:8080/realms/mcp-realm  # For tests
KEYCLOAK_CLIENT_ID=mcp-server
KEYCLOAK_CLIENT_SECRET=mcp-server-secret-change-in-production
```

#### For DCR Mode
```env
USE_DCR=true
OAUTH_ISSUER=http://keycloak:8080/realms/mcp-realm  # For container
DCR_INITIAL_ACCESS_TOKEN=<token-generated-inside-container>
# Client ID/secret not needed - will be generated
```

### 4. Switching Process

#### From DCR to Non-DCR:
```bash
# 1. Update configuration
perl -i -pe 's/USE_DCR=true/USE_DCR=false/' .env.docker
perl -i -pe 's|OAUTH_ISSUER=http://keycloak:8080|OAUTH_ISSUER=http://localhost:8080|' .env.docker

# 2. Ensure static credentials are present
grep -E "KEYCLOAK_CLIENT_ID|KEYCLOAK_CLIENT_SECRET" .env.docker || {
  echo "KEYCLOAK_CLIENT_ID=mcp-server" >> .env.docker
  echo "KEYCLOAK_CLIENT_SECRET=mcp-server-secret-change-in-production" >> .env.docker
}

# 3. Recreate container
docker compose down mcp-server && docker compose up -d mcp-server
```

#### From Non-DCR to DCR:
```bash
# 1. Generate DCR token from INSIDE container
docker compose exec -T mcp-server sh < scripts/setup_dcr_docker.sh > dcr_token.txt

# 2. Update configuration  
perl -i -pe 's/USE_DCR=false/USE_DCR=true/' .env.docker
perl -i -pe 's|OAUTH_ISSUER=http://localhost:8080|OAUTH_ISSUER=http://keycloak:8080|' .env.docker

# 3. Update DCR token (from dcr_token.txt)
# ... update DCR_INITIAL_ACCESS_TOKEN in .env.docker ...

# 4. Recreate container
docker compose down mcp-server && docker compose up -d mcp-server
```

## Testing Considerations

### Running Tests Against Different Modes

1. **Static Credentials Mode**: Tests can run directly as the issuer matches
2. **DCR Mode**: Tests will fail due to issuer mismatch

### Solutions for Testing with DCR:

1. **Use Static Credentials for Testing**
   - Keep tests simple by using static credentials
   - Switch to DCR only for production deployments

2. **Create Test-Specific DCR Registration**
   - Generate DCR tokens with `localhost:8080` issuer for tests
   - Requires modifying test setup to handle DCR

3. **Run Tests Inside Container**
   - Execute tests from within Docker network
   - Ensures consistent issuer URLs

## Recommendations

1. **Development**: Use static credentials for easier testing
2. **Production**: Use DCR for better security
3. **CI/CD**: Create separate configurations for test vs deployment
4. **Documentation**: Always specify which mode is active and why

## Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "Failed decode token" | Token issuer mismatch | Regenerate token with correct issuer |
| Container keeps restarting | Environment not updated | Use `down`/`up` not `restart` |
| "Invalid token issuer" | Wrong OAUTH_ISSUER | Match issuer to execution context |
| Tests fail with DCR | Issuer mismatch | Use static credentials for tests |

## Summary

The key challenge in switching between DCR and non-DCR modes is managing the different perspectives of "localhost" vs "keycloak" between the host system and Docker containers. This fundamental networking difference affects token validation and requires careful configuration management.

Best practice: Use static credentials for development/testing and DCR for production deployments. 