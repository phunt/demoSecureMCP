# Testing Documentation

This document describes the testing procedures and test suites for the demoSecureMCP.

## Overview

The MCP Server includes comprehensive test suites that verify:
- OAuth 2.0 authentication flows
- JWT token validation
- Scope-based authorization
- MCP tool functionality
- Error handling and security

## Test Suites

### 1. Client Credentials Flow Tests
**File**: `tests/test_client_credentials.py`

Tests the OAuth 2.0 client credentials flow:
- Token acquisition from Keycloak
- Protected endpoint access
- Scope enforcement
- Token expiration handling
- Metadata endpoint availability

**Key test scenarios**:
- Valid token acquisition
- Access without authentication
- Scope-based authorization
- Token refresh/expiration
- Public endpoint access

### 2. JWT Token Validation Tests
**File**: `tests/test_token_validation.py`

Tests various JWT validation scenarios:
- Valid token acceptance
- Malformed token rejection
- Invalid signature detection
- Missing/wrong claims handling
- Token placement validation

**Security tests**:
- Invalid signatures
- Wrong issuer/audience
- Expired tokens
- Malformed tokens
- SQL injection/XSS attempts

### 3. MCP Tools Integration Tests
**File**: `tests/test_mcp_tools_integration.py`

Tests the demo MCP tools:
- Echo tool (mcp:read scope)
- Timestamp tool (mcp:read scope)
- Calculator tool (mcp:write scope)
- Tool discovery endpoint
- Error handling

**Test coverage**:
- Correct functionality
- Scope enforcement
- Input validation
- Error responses
- Edge cases

### 4. Curl Client Test Suite
**File**: `examples/curl-client/test.sh`

Tests the curl-based MCP client implementation:
- OAuth token acquisition via shell scripts
- Authenticated API calls using curl
- Error handling in shell scripts
- Environment variable configuration
- All demo tools via command line

**Test coverage**:
- Service availability checks
- Token format validation
- Tool invocation with authentication
- Invalid token/credential handling
- Command-line argument parsing
- Full end-to-end workflow

**Running the curl client tests**:
```bash
cd examples/curl-client
./test.sh
```

## Running Tests

### Prerequisites

1. **Start Docker services**:
   ```bash
   ./scripts/docker_manage.sh start
   ```

2. **Verify services are healthy**:
   ```bash
   ./scripts/docker_manage.sh health
   ```

### Running Individual Test Suites

Run a specific test suite:

```bash
# Client credentials flow
python tests/test_client_credentials.py

# Token validation
python tests/test_token_validation.py

# MCP tools integration
python tests/test_mcp_tools_integration.py
```

### Running All Tests

Use the comprehensive test runner:

```bash
# Run all test suites
python tests/run_all_tests.py

# Make script executable and run
chmod +x tests/run_all_tests.py
./tests/run_all_tests.py
```

The test runner provides:
- Colored output for easy reading
- Progress tracking
- Detailed summaries
- Test report file generation
- Docker service verification

### Test Output

Each test suite provides:
- ✅ **PASS** - Test succeeded
- ❌ **FAIL** - Test failed
- ⚠️  **WARN** - Warning or note
- 🔵 **INFO** - Information

Example output:
```
[INFO] === OAuth 2.0 Client Credentials Flow Test Suite ===

[INFO] === Testing Token Acquisition ===
[PASS] Token obtained successfully (expires in 300 seconds)
[INFO] Token scopes: mcp:read mcp:write mcp:infer
[INFO] Token audience: mcp-server

[INFO] === Test Summary ===
[PASS] Token Acquisition: PASS
[PASS] Protected Endpoints: PASS
[PASS] Scope Requirements: PASS

[PASS] Total: 6/6 tests passed
```

## Test Configuration

Tests use settings from `.env` file:

```bash
# Keycloak settings
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=mcp-realm
KEYCLOAK_CLIENT_ID=mcp-server
KEYCLOAK_CLIENT_SECRET=your-secret

# OAuth settings
OAUTH_ISSUER=http://localhost:8080/realms/mcp-realm
OAUTH_AUDIENCE=mcp-server
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Start services
      run: docker compose up -d
    
    - name: Wait for services
      run: ./scripts/docker_manage.sh health
    
    - name: Run tests
      run: python tests/run_all_tests.py
    
    - name: Upload test report
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: test-report
        path: test_report_*.txt
```

## Manual Testing

### Using the Curl Client

The project includes a comprehensive curl-based client for manual testing:

```bash
cd examples/curl-client

# Full demonstration
./full_example.sh

# Individual operations
./get_token.sh                     # Get OAuth token
./call_tool.sh echo "Test"         # Call echo tool
./call_tool.sh timestamp           # Get timestamp
./call_tool.sh calculate "5 * 10"  # Calculate expression
./call_tool.sh discover            # List available tools
```

See [examples/curl-client/README.md](../examples/curl-client/README.md) for detailed usage.

### 1. Token Acquisition

Get a token manually:

```bash
curl -X POST http://localhost:8080/realms/mcp-realm/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=mcp-server" \
  -d "client_secret=your-secret" \
  -d "scope=mcp:read mcp:write"
```

### 2. Test Protected Endpoint

Use the token:

```bash
TOKEN="eyJhbGc..."  # Token from above

curl https://localhost/api/v1/me \
  -H "Authorization: Bearer $TOKEN" \
  --insecure  # For self-signed certs
```

### 3. Test MCP Tools

Echo tool:
```bash
curl -X POST https://localhost/api/v1/tools/echo \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, MCP!", "uppercase": true}' \
  --insecure
```

Calculator tool:
```bash
curl -X POST https://localhost/api/v1/tools/calculate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"operation": "add", "operands": [10, 20, 30]}' \
  --insecure
```

## Debugging Failed Tests

### 1. Check Service Logs

```bash
# View all logs
./scripts/docker_manage.sh logs

# View specific service
./scripts/docker_manage.sh logs mcp-server
./scripts/docker_manage.sh logs keycloak
```

### 2. Verify Token Contents

Decode a JWT token to inspect claims:

```bash
# Split token by '.' and decode middle part
echo "YOUR_TOKEN" | cut -d. -f2 | base64 -d | jq
```

### 3. Check Network Connectivity

```bash
# Test from inside container
docker compose exec mcp-server curl http://keycloak:8080/health
```

### 4. Verify Keycloak Configuration

Access Keycloak admin console:
1. Navigate to http://localhost:8080
2. Login with admin/admin_password
3. Check realm and client settings

## Adding New Tests

### Test Structure

```python
#!/usr/bin/env python3
"""Test description"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import Settings

def test_feature():
    """Test specific feature"""
    # Arrange
    config = Settings()
    
    # Act
    result = perform_action()
    
    # Assert
    assert result == expected_value
    
    return True  # or False

def run_all_tests():
    """Run all tests in this suite"""
    results = []
    
    results.append(("Feature Test", test_feature()))
    
    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"Total: {passed}/{total} tests passed")
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
```

### Best Practices

1. **Isolation**: Each test should be independent
2. **Clarity**: Use descriptive test names
3. **Coverage**: Test both success and failure cases
4. **Security**: Include security-focused tests
5. **Performance**: Set reasonable timeouts

## Performance Testing

For load testing, use tools like:

```bash
# Using Apache Bench
ab -n 1000 -c 10 -H "Authorization: Bearer $TOKEN" https://localhost/api/v1/me

# Using hey
hey -n 1000 -c 10 -H "Authorization: Bearer $TOKEN" https://localhost/api/v1/me

# Using locust
locust -f tests/load_test.py --host=https://localhost
```

## Security Testing

Additional security testing:

1. **OWASP ZAP**: Automated security scanning
2. **Burp Suite**: Manual security testing
3. **SQLMap**: SQL injection testing
4. **JWT_Tool**: JWT security testing

## Test Maintenance

1. **Update tests** when adding new features
2. **Review test coverage** regularly
3. **Monitor test execution time**
4. **Keep tests simple and focused**
5. **Document complex test scenarios** 