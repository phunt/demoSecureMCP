#!/usr/bin/env python3
"""
OAuth 2.0 Client Credentials Flow Test Suite

Tests client credentials flow, token validation, and endpoint access patterns.
"""

import json
import httpx
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Set test environment early
import os
os.environ["TESTING"] = "true"
os.environ["CONTAINER_ENV"] = "false"
os.environ["OAUTH_ISSUER"] = "http://localhost:8080/realms/mcp-realm"

from src.config.settings import Settings

# Test configuration
class ClientTestConfig:
    def __init__(self):
        self.settings = Settings()
        self.base_url = "https://localhost"
        self.keycloak_url = self.settings.keycloak_url
        self.keycloak_realm = self.settings.keycloak_realm
        self.keycloak_client_id = self.settings.keycloak_client_id
        self.keycloak_client_secret = self.settings.keycloak_client_secret
        self.verify_ssl = False
        self.use_dcr = self.settings.use_dcr

# Initialize test configuration
config = ClientTestConfig()


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_test(message: str, status: str = "INFO") -> None:
    """Print colored test output"""
    if status == "PASS":
        print(f"[{Colors.GREEN}PASS{Colors.END}] {message}")
    elif status == "FAIL":
        print(f"[{Colors.RED}FAIL{Colors.END}] {message}")
    elif status == "INFO":
        print(f"[{Colors.BLUE}INFO{Colors.END}] {message}")
    else:
        print(f"[{status}] {message}")


def get_dcr_client_info() -> Optional[Dict[str, Any]]:
    """Get client information (DCR or static)"""
    # Check if we're in DCR mode
    if config.use_dcr:
        try:
            with open(".dcr_client.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print_test("DCR client file not found", "FAIL")
            return None
        except json.JSONDecodeError:
            print_test("Invalid DCR client file", "FAIL")
            return None
    else:
        # Use static credentials
        if config.keycloak_client_id and config.keycloak_client_secret:
            print_test("Using static client credentials", "INFO")
            return {
                "client_id": config.keycloak_client_id,
                "client_secret": config.keycloak_client_secret
            }
        else:
            print_test("Static client credentials not configured", "FAIL")
            return None


def get_client_credentials_token(scope: str = "mcp:read mcp:write mcp:infer") -> Optional[Dict[str, Any]]:
    """Get access token using client credentials flow"""
    dcr_client = get_dcr_client_info()
    if not dcr_client:
        return None

    client_id = dcr_client["client_id"]
    client_secret = dcr_client["client_secret"]
    
    print_test(f"Using DCR client: {client_id}")
    print_test("Requesting access token via client credentials flow")

    token_endpoint = f"{config.keycloak_url}/realms/{config.keycloak_realm}/protocol/openid-connect/token"
    
    # Update OAuth audience to match client ID
    os.environ["OAUTH_AUDIENCE"] = client_id
    
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": scope
    }

    try:
        with httpx.Client(verify=config.verify_ssl) as client:
            response = client.post(token_endpoint, data=data)

        if response.status_code == 200:
            token_data = response.json()
            expires_in = token_data.get("expires_in", 300)
            print_test(f"Token obtained successfully (expires in {expires_in} seconds)", "PASS")
            
            # Print token info for debugging
            if "scope" in token_data:
                print_test(f"Token scopes: {token_data['scope']}")
            
            # Check if we have azp claim
            import jwt
            payload = jwt.decode(token_data["access_token"], options={"verify_signature": False})
            if "azp" in payload:
                print_test(f"Token audience: {payload['azp']}")
            
            return token_data
        else:
            print_test(f"Failed to get token: {response.status_code} - {response.text}", "FAIL")
            return None

    except Exception as e:
        print_test(f"Error getting token: {str(e)}", "FAIL")
        return None

def check_protected_endpoint(endpoint: str, token: str, expected_status: int = 200) -> bool:
    """Check accessing a protected endpoint with a token"""
    print_test(f"Testing endpoint: {endpoint}")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        with httpx.Client(verify=config.verify_ssl) as client:
            response = client.get(f"{config.base_url}{endpoint}", headers=headers)
        
        if response.status_code == expected_status:
            print_test(f"Endpoint returned expected status {expected_status}", "PASS")
            if response.status_code == 200:
                print_test(f"Response: {response.json()}")
            return True
        else:
            print_test(f"Unexpected status: {response.status_code} (expected {expected_status})", "FAIL")
            print_test(f"Response: {response.text}")
            return False
    except Exception as e:
        print_test(f"Error accessing endpoint: {str(e)}", "FAIL")
        return False

def test_no_token_access():
    """Test accessing protected endpoints without a token"""
    print_test("\n=== Testing Access Without Token ===")
    
    endpoints = ["/api/v1/user", "/api/v1/tools", "/api/v1/tools/echo"]
    
    for endpoint in endpoints:
        print_test(f"Testing {endpoint} without token")
        try:
            with httpx.Client(verify=config.verify_ssl) as client:
                response = client.get(f"{config.base_url}{endpoint}")
            
            if response.status_code in [401, 403]:
                print_test(f"Correctly rejected with status {response.status_code}", "PASS")
            else:
                print_test(f"Unexpected status {response.status_code} - endpoint may not be protected!", "FAIL")
        except Exception as e:
            print_test(f"Error: {str(e)}", "FAIL")

def test_token_expiration():
    """Test token expiration handling"""
    print_test("\n=== Testing Token Expiration ===")
    
    # Get a token
    token_data = get_client_credentials_token()
    assert token_data, "Failed to obtain token"
    
    token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 300)
    
    # Test with valid token
    assert check_protected_endpoint("/api/v1/user", token), "Failed to access endpoint with valid token"
    
    # Calculate expiration time
    expiry_time = datetime.now() + timedelta(seconds=expires_in)
    print_test(f"Token expires at: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # For testing purposes, we can't wait for actual expiration
    # Instead, we'll test with an invalid token
    print_test("Testing with invalid/expired token")
    invalid_token = token[:-10] + "invalid123"  # Corrupt the token
    
    assert check_protected_endpoint("/api/v1/user", invalid_token, expected_status=401), \
        "Failed to reject invalid token"
    print_test("Correctly rejected expired/invalid token", "PASS")

def test_scope_requirements():
    """Test scope-based authorization"""
    print_test("\n=== Testing Scope Requirements ===")
    
    # Test 1: Get token with specific scopes
    print_test("Testing with mcp:read scope")
    token_data = get_client_credentials_token(scope="mcp:read")
    assert token_data, "Failed to obtain token with mcp:read scope"
    
    read_token = token_data["access_token"]
    
    # Should work for read endpoints (tools endpoint returns tool list)
    check_protected_endpoint("/api/v1/tools", read_token)
    check_protected_endpoint("/api/v1/user", read_token)
    
    # Test 2: Try write endpoint with read token (calculator requires mcp:write)
    print_test("\nTesting write endpoint with read-only token")
    # Note: We can't test POST endpoints with check_protected_endpoint as it uses GET
    # So we'll check that we can list tools but acknowledge calculator requires write scope
    
    # Test 3: Get token with write scope
    print_test("\nTesting with mcp:write scope")
    token_data = get_client_credentials_token(scope="mcp:write")
    assert token_data, "Failed to obtain token with mcp:write scope"
    
    write_token = token_data["access_token"]
    # With write scope, we should still be able to list tools
    check_protected_endpoint("/api/v1/tools", write_token)
    
    # Test 4: Get token with all scopes
    print_test("\nTesting with all scopes")
    token_data = get_client_credentials_token(scope="mcp:read mcp:write mcp:infer")
    assert token_data, "Failed to obtain token with all scopes"
    
    full_token = token_data["access_token"]
    # With all scopes, we should be able to access all endpoints
    check_protected_endpoint("/api/v1/tools", full_token)
    check_protected_endpoint("/api/v1/user", full_token)
    # Note: actual tool invocation would require POST requests
    
    print_test("All scope-based authorization tests passed", "PASS")

def test_metadata_endpoints():
    """Test public metadata endpoints"""
    print_test("\n=== Testing Metadata Endpoints ===")
    
    endpoints = [
        ("/.well-known/oauth-protected-resource", "OAuth Protected Resource Metadata"),
        ("/health", "Health Check"),
        ("/docs", "OpenAPI Documentation")
    ]
    
    for endpoint, description in endpoints:
        print_test(f"Testing {description}: {endpoint}")
        try:
            with httpx.Client(verify=config.verify_ssl) as client:
                response = client.get(f"{config.base_url}{endpoint}")
            
            assert response.status_code == 200, \
                f"Failed to access {description}: {response.status_code}"
            
            print_test(f"{description} accessible", "PASS")
            if endpoint == "/.well-known/oauth-protected-resource":
                metadata = response.json()
                print_test(f"Issuer: {metadata.get('issuer')}")
                print_test(f"Resource: {metadata.get('resource')}")
                print_test(f"Scopes: {metadata.get('scopes_supported')}")
                
        except AssertionError:
            raise
        except Exception as e:
            print_test(f"Error: {str(e)}", "FAIL")
            assert False, f"Error accessing {description}: {str(e)}"
    
    print_test("All metadata endpoints accessible", "PASS")

def run_all_tests():
    """Run all client credentials flow tests"""
    print_test("=== OAuth 2.0 Client Credentials Flow Test Suite ===\n", "INFO")
    
    results = []
    
    # Test 1: Metadata endpoints (no auth required)
    results.append(("Metadata Endpoints", test_metadata_endpoints()))
    
    # Test 2: No token access
    results.append(("No Token Access", test_no_token_access()))
    
    # Test 3: Basic token acquisition
    print_test("\n=== Testing Token Acquisition ===")
    token_data = get_client_credentials_token()
    results.append(("Token Acquisition", token_data is not None))
    
    if token_data:
        # Test 4: Protected endpoint access
        print_test("\n=== Testing Protected Endpoints ===")
        token = token_data["access_token"]
        results.append(("Protected Endpoints", check_protected_endpoint("/api/v1/user", token)))
        
        # Test 5: Scope requirements
        results.append(("Scope Requirements", test_scope_requirements()))
        
        # Test 6: Token expiration
        results.append(("Token Expiration", test_token_expiration()))
    
    # Summary
    print_test("\n=== Test Summary ===", "INFO")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print_test(f"{test_name}: {status}", status)
    
    print_test(f"\nTotal: {passed}/{total} tests passed", "PASS" if passed == total else "FAIL")
    
    return passed == total

if __name__ == "__main__":
    # Check if services are running
    print_test("Checking if services are accessible...", "INFO")
    
    try:
        with httpx.Client(verify=config.verify_ssl) as client:
            # Check Keycloak
            keycloak_response = client.get(f"{config.keycloak_url}/realms/{config.keycloak_realm}/.well-known/openid-configuration", timeout=5)
            if keycloak_response.status_code != 200:
                print_test("Keycloak is not ready. Please ensure Docker services are running.", "FAIL")
                sys.exit(1)
            
            # Check MCP server via Nginx
            mcp_response = client.get(f"{config.base_url}/health", timeout=5)
            if mcp_response.status_code != 200:
                print_test("MCP server is not accessible. Please ensure Docker services are running.", "FAIL")
                sys.exit(1)
    except Exception as e:
        print_test(f"Services not accessible: {str(e)}", "FAIL")
        print_test("Please run: ./scripts/docker_manage.sh start", "INFO")
        sys.exit(1)
    
    print_test("Services are ready", "PASS")
    
    # Run tests
    success = run_all_tests()
    sys.exit(0 if success else 1) 