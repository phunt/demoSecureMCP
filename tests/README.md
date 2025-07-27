# Testing Strategy

This directory contains the comprehensive test suite for the demoSecureMCP, ensuring reliability, security, and correctness of all components.

## Test Structure

```
tests/
├── __init__.py
├── run_all_tests.py              # Main test runner
├── test_client_credentials.py    # OAuth flow tests
├── test_token_validation.py      # JWT validation tests
├── test_mcp_tools_integration.py # Tool functionality tests
└── test_*.py                     # Additional test modules
```

## Test Categories

### 1. **Authentication Tests** (`test_client_credentials.py`)

Tests the complete OAuth 2.0 client credentials flow:

- **Token Acquisition**
  - Valid client credentials → access token
  - Invalid credentials → 401 error
  - Missing credentials → 400 error
  
- **Token Usage**
  - Valid token → successful API access
  - Expired token → 401 error
  - Invalid token → 401 error

- **Scope Enforcement**
  - Correct scope → access granted
  - Missing scope → 403 forbidden
  - Invalid scope → token request fails

### 2. **Token Validation Tests** (`test_token_validation.py`)

Comprehensive JWT validation scenarios:

- **Valid Tokens**
  - Properly signed tokens
  - All required claims present
  - Within validity period

- **Invalid Tokens**
  - Expired tokens
  - Future-dated tokens (nbf)
  - Invalid signatures
  - Wrong issuer/audience
  - Missing required claims

- **Edge Cases**
  - Malformed tokens
  - Empty tokens
  - Very long tokens
  - Special characters

- **Token Placement**
  - Authorization header variations
  - Case sensitivity
  - Missing bearer prefix

### 3. **MCP Tools Integration Tests** (`test_mcp_tools_integration.py`)

End-to-end testing of MCP tools:

- **Tool Discovery**
  - List all available tools
  - Check scope-based availability
  - Verify tool metadata

- **Tool Execution**
  - Echo tool functionality
  - Timestamp tool with formats
  - Calculator operations

- **Error Handling**
  - Invalid parameters → 422
  - Missing parameters → 422
  - Division by zero → 400
  - Unauthorized access → 403

## Running Tests

### Run All Tests

```bash
# From project root
python tests/run_all_tests.py

# Output includes:
# - Pre-flight checks
# - Individual test results
# - Summary statistics
# - Test report generation
```

### Run Specific Test Suite

```bash
# OAuth flow tests
python tests/test_client_credentials.py

# JWT validation tests
python tests/test_token_validation.py

# MCP tools tests
python tests/test_mcp_tools_integration.py
```

### Docker-based Testing

```bash
# Ensure services are running
./scripts/docker_manage.sh start

# Run tests against Docker services
python tests/run_all_tests.py
```

## Test Configuration

Tests use environment variables from `.env`:

```bash
# Test configuration
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_CLIENT_ID=mcp-server
KEYCLOAK_CLIENT_SECRET=your-secret-here
API_BASE_URL=https://localhost
```

## Writing New Tests

### Test Template

```python
#!/usr/bin/env python3
"""Test module description"""

import os
import sys
import asyncio
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.test_helpers import (
    TestConfig,
    get_test_token,
    create_test_client,
    wait_for_service
)

class TestNewFeature:
    """Test cases for new feature"""
    
    def __init__(self):
        self.config = TestConfig()
        self.results = []
    
    async def test_feature_success(self):
        """Test successful feature usage"""
        try:
            # Arrange
            token = await get_test_token(scope="mcp:read")
            client = create_test_client()
            
            # Act
            response = await client.post(
                "/api/v1/feature",
                headers={"Authorization": f"Bearer {token}"},
                json={"param": "value"}
            )
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            
            return True, "Feature works correctly"
            
        except Exception as e:
            return False, f"Feature test failed: {str(e)}"
    
    async def run_all_tests(self):
        """Run all test cases"""
        print("\n🧪 Testing New Feature")
        print("=" * 50)
        
        # Wait for services
        await wait_for_service(self.config.keycloak_url, "Keycloak")
        await wait_for_service(self.config.api_base_url, "API")
        
        # Run tests
        tests = [
            ("Success Case", self.test_feature_success),
            # Add more test methods
        ]
        
        for name, test_func in tests:
            success, message = await test_func()
            self.results.append((name, success, message))
            print(f"{'✓' if success else '✗'} {name}: {message}")
        
        return self.results

if __name__ == "__main__":
    tester = TestNewFeature()
    asyncio.run(tester.run_all_tests())
```

### Test Helpers (`test_helpers.py`)

Common utilities for tests:

```python
class TestConfig:
    """Test configuration from environment"""
    keycloak_url: str
    client_id: str
    client_secret: str
    api_base_url: str

async def get_test_token(scope: str = "mcp:read") -> str:
    """Get access token for testing"""
    # Request token from Keycloak
    # Return access_token string

async def wait_for_service(url: str, name: str, timeout: int = 30):
    """Wait for service to be healthy"""
    # Poll service health endpoint
    # Raise TimeoutError if not ready

def create_test_client() -> httpx.AsyncClient:
    """Create configured HTTP client"""
    # Return client with SSL verification disabled for tests
```

## Test Best Practices

### 1. **Test Isolation**
- Each test should be independent
- Clean up created resources
- Don't rely on test execution order

### 2. **Clear Assertions**
```python
# Good
assert response.status_code == 200, f"Expected 200, got {response.status_code}"

# Better
assert response.status_code == 200, (
    f"Token validation should succeed for valid token. "
    f"Response: {response.text}"
)
```

### 3. **Error Context**
```python
try:
    result = await some_operation()
except Exception as e:
    # Include context in error
    return False, f"Operation failed at step X: {str(e)}"
```

### 4. **Async Testing**
- Use `asyncio` for async operations
- Properly await all async calls
- Handle connection cleanup

### 5. **Security Testing**
- Test both positive and negative cases
- Verify error messages don't leak info
- Check all authorization paths

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Run Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start services
        run: docker compose up -d
        
      - name: Wait for services
        run: |
          timeout 60 bash -c 'until curl -f http://localhost:8080/health; do sleep 2; done'
          
      - name: Run tests
        run: python tests/run_all_tests.py
        
      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test_report_*.txt
```

### GitLab CI Example

```yaml
test:
  stage: test
  services:
    - docker:dind
  script:
    - docker compose up -d
    - sleep 30  # Wait for services
    - python tests/run_all_tests.py
  artifacts:
    reports:
      junit: test-results.xml
```

## Performance Testing

### Load Testing with Locust

```python
# tests/load_test.py
from locust import HttpUser, task, between

class MCPUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Get auth token
        self.token = self.get_token()
    
    @task(3)
    def use_echo_tool(self):
        self.client.post(
            "/api/v1/tools/echo",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"message": "Load test"}
        )
    
    @task(1)
    def list_tools(self):
        self.client.get(
            "/api/v1/tools",
            headers={"Authorization": f"Bearer {self.token}"}
        )
```

Run: `locust -f tests/load_test.py --host=https://localhost`

## Security Testing

### OWASP ZAP Integration

```bash
# Run security scan
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://localhost \
  -c zap-rules.conf
```

### Manual Security Tests

1. **Authentication Bypass**
   - Try accessing protected endpoints without token
   - Use expired/invalid tokens
   - Attempt token manipulation

2. **Authorization Tests**
   - Access resources with insufficient scopes
   - Try privilege escalation
   - Test boundary conditions

3. **Input Validation**
   - SQL injection attempts
   - XSS payloads
   - Buffer overflow tests

## Test Reports

The test runner generates detailed reports:

```
test_report_20240120_103045.txt
├── Environment Info
├── Service Health Checks
├── Test Results by Suite
├── Failed Test Details
├── Performance Metrics
└── Summary Statistics
```

## Debugging Failed Tests

### 1. **Check Service Logs**
```bash
./scripts/docker_manage.sh logs mcp-server
./scripts/docker_manage.sh logs keycloak
```

### 2. **Verify Configuration**
```bash
# Check environment variables
cat .env.docker

# Verify Keycloak realm
curl http://localhost:8080/realms/mcp-realm
```

### 3. **Interactive Debugging**
```python
# Add breakpoints
import pdb; pdb.set_trace()

# Or use VS Code debugger with launch.json
```

### 4. **Isolated Test Run**
```python
# Run single test method
python -c "
from tests.test_mcp_tools_integration import TestMCPToolsIntegration
import asyncio
t = TestMCPToolsIntegration()
asyncio.run(t.test_echo_tool())
"
```

## Future Enhancements

1. **Test Coverage**
   - Add code coverage reporting
   - Set minimum coverage thresholds
   - Generate coverage badges

2. **Contract Testing**
   - OpenAPI schema validation
   - Response format verification
   - Backwards compatibility checks

3. **Chaos Testing**
   - Service failure simulation
   - Network latency injection
   - Resource exhaustion tests

4. **Visual Testing**
   - API documentation screenshots
   - Admin UI testing (if applicable)
   - Response rendering validation 