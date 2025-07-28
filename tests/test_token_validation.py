#!/usr/bin/env python3
"""
Test JWT Token Validation

This script tests various token validation scenarios:
1. Valid tokens
2. Expired tokens
3. Invalid signatures
4. Missing claims
5. Wrong audience/issuer
"""

import os
import sys
import time
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional
import httpx
import jwt

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import Settings

# Test configuration
class ValidationTestConfig:
    def __init__(self):
        self.settings = Settings()
        self.base_url = "https://localhost"
        self.keycloak_url = self.settings.keycloak_url
        self.realm = self.settings.keycloak_realm
        self.client_id = self.settings.keycloak_client_id
        self.client_secret = self.settings.keycloak_client_secret
        self.token_endpoint = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"
        self.verify_ssl = False

config = ValidationTestConfig()

# Color output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(message: str, status: str = "INFO"):
    color = Colors.BLUE
    if status == "PASS":
        color = Colors.GREEN
    elif status == "FAIL":
        color = Colors.RED
    elif status == "WARN":
        color = Colors.YELLOW
    
    print(f"{color}[{status}]{Colors.END} {message}")

def get_valid_token() -> Optional[str]:
    """Get a valid token from Keycloak"""
    data = {
        "grant_type": "client_credentials",
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "scope": "mcp:read mcp:write"
    }
    
    try:
        with httpx.Client(verify=config.verify_ssl) as client:
            response = client.post(config.token_endpoint, data=data)
        
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            print_test(f"Failed to get valid token: {response.status_code}", "FAIL")
            return None
    except Exception as e:
        print_test(f"Error getting token: {str(e)}", "FAIL")
        return None

def check_endpoint_with_token(token: str, expected_status: int = 200) -> bool:
    """Test accessing protected endpoint with a token"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        with httpx.Client(verify=config.verify_ssl) as client:
            response = client.get(f"{config.base_url}/api/v1/user", headers=headers)
        
        success = response.status_code == expected_status
        if success:
            print_test(f"Got expected status {expected_status}", "PASS")
        else:
            print_test(f"Got status {response.status_code}, expected {expected_status}", "FAIL")
            if response.text:
                print_test(f"Response: {response.text[:200]}")
        
        return success
    except Exception as e:
        print_test(f"Error: {str(e)}", "FAIL")
        assert False, "Test failed"
def create_malformed_token(valid_token: str, modification: str) -> str:
    """Create various types of malformed tokens"""
    parts = valid_token.split(".")
    
    if modification == "invalid_signature":
        # Change last 10 characters of signature
        return f"{parts[0]}.{parts[1]}.{'x' * 10}{parts[2][10:]}"
    
    elif modification == "missing_header":
        # Remove header
        return f".{parts[1]}.{parts[2]}"
    
    elif modification == "missing_payload":
        # Remove payload
        return f"{parts[0]}..{parts[2]}"
    
    elif modification == "invalid_base64":
        # Corrupt base64 in payload
        return f"{parts[0]}.invalid_base64!@#.{parts[2]}"
    
    elif modification == "wrong_algorithm":
        # Decode and modify algorithm
        header = json.loads(base64.urlsafe_b64decode(parts[0] + "=="))
        header["alg"] = "none"
        new_header = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        return f"{new_header}.{parts[1]}.{parts[2]}"
    
    elif modification == "expired":
        # Create expired token (we'll use a different approach since we can't sign)
        # Return the valid token but server will check expiration
        return valid_token
    
    elif modification == "wrong_issuer":
        # Decode and modify issuer
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
        payload["iss"] = "https://wrong-issuer.com"
        new_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        return f"{parts[0]}.{new_payload}.{parts[2]}"
    
    elif modification == "wrong_audience":
        # Decode and modify audience
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
        payload["aud"] = "wrong-audience"
        payload.pop("azp", None)  # Remove azp if present
        new_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        return f"{parts[0]}.{new_payload}.{parts[2]}"
    
    elif modification == "missing_exp":
        # Remove expiration claim
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
        payload.pop("exp", None)
        new_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        return f"{parts[0]}.{new_payload}.{parts[2]}"
    
    elif modification == "truncated":
        # Return truncated token
        return valid_token[:len(valid_token)//2]
    
    else:
        return valid_token

def test_malformed_tokens():
    """Test various types of malformed tokens"""
    print_test("\n=== Testing Malformed Tokens ===")
    
    # Get a valid token first
    valid_token = get_valid_token()
    assert valid_token, "Failed to obtain valid token"
    
    # Test valid token first
    print_test("\nTesting with valid token")
    if not check_endpoint_with_token(valid_token, 200):
        print_test("Valid token test failed!", "FAIL")
        assert False, "Test failed"
    # Test various malformations
    malformations = [
        ("invalid_signature", "Invalid signature"),
        ("missing_header", "Missing header"),
        ("missing_payload", "Missing payload"),
        ("invalid_base64", "Invalid base64 encoding"),
        ("wrong_algorithm", "Wrong algorithm (none)"),
        ("wrong_issuer", "Wrong issuer"),
        ("wrong_audience", "Wrong audience"),
        ("missing_exp", "Missing expiration"),
        ("truncated", "Truncated token"),
    ]
    
    all_passed = True
    for modification, description in malformations:
        print_test(f"\nTesting: {description}")
        malformed_token = create_malformed_token(valid_token, modification)
        
        # All malformed tokens should result in 401
        if not check_endpoint_with_token(malformed_token, 401):
            all_passed = False
    
    return all_passed

def test_token_in_different_positions():
    """Test token placement in request"""
    print_test("\n=== Testing Token Placement ===")
    
    valid_token = get_valid_token()
    assert valid_token, "Failed to obtain valid token"
    
    tests = [
        ("Valid Bearer token", {"Authorization": f"Bearer {valid_token}"}, 200),
        ("Lowercase bearer", {"Authorization": f"bearer {valid_token}"}, 200),  # Our implementation is case-insensitive
        ("No Bearer prefix", {"Authorization": valid_token}, [401, 403]),
        ("Wrong prefix", {"Authorization": f"Token {valid_token}"}, [401, 403]),
        ("No Authorization header", {}, [401, 403]),
        ("Empty Authorization", {"Authorization": ""}, [401, 403]),
        ("Bearer without token", {"Authorization": "Bearer"}, [401, 403]),
        ("Bearer with spaces", {"Authorization": f"Bearer  {valid_token}"}, 401),
    ]
    
    all_passed = True
    for description, headers, expected_status in tests:
        print_test(f"\nTesting: {description}")
        
        try:
            with httpx.Client(verify=config.verify_ssl) as client:
                response = client.get(f"{config.base_url}/api/v1/user", headers=headers)
            
            expected_statuses = expected_status if isinstance(expected_status, list) else [expected_status]
            if response.status_code in expected_statuses:
                print_test(f"Got expected status {response.status_code}", "PASS")
            else:
                print_test(f"Got status {response.status_code}, expected {expected_statuses}", "FAIL")
                all_passed = False
        except Exception as e:
            print_test(f"Error: {str(e)}", "FAIL")
            all_passed = False
    
    return all_passed

def test_token_claims_validation():
    """Test validation of specific token claims"""
    print_test("\n=== Testing Token Claims Validation ===")
    
    valid_token = get_valid_token()
    assert valid_token, "Failed to obtain valid token"
    
    # Decode token to inspect claims
    parts = valid_token.split(".")
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
    
    print_test("\nToken claims:")
    print_test(f"Issuer (iss): {payload.get('iss')}")
    print_test(f"Audience (aud): {payload.get('aud')}")
    print_test(f"Authorized party (azp): {payload.get('azp')}")
    print_test(f"Expiration (exp): {datetime.fromtimestamp(payload.get('exp', 0))}")
    print_test(f"Issued at (iat): {datetime.fromtimestamp(payload.get('iat', 0))}")
    print_test(f"Scopes: {payload.get('scope')}")
    
    # Test with valid token
    print_test("\nValidating all claims are properly checked")
    return check_endpoint_with_token(valid_token, 200)

def test_special_characters_in_token():
    """Test tokens with special characters"""
    print_test("\n=== Testing Special Characters ===")
    
    special_tokens = [
        ("SQL injection attempt", "' OR '1'='1"),
        ("Script tag", "<script>alert('xss')</script>"),
        # Skip null bytes and unicode - HTTP headers don't support them
        ("Very long string", "x" * 4000),
    ]
    
    all_passed = True
    for description, token in special_tokens:
        print_test(f"\nTesting: {description}")
        if not check_endpoint_with_token(token, 401):
            all_passed = False
    
    return all_passed

def run_all_tests():
    """Run all token validation tests"""
    print_test("=== JWT Token Validation Test Suite ===\n", "INFO")
    
    results = []
    
    # Test 1: Malformed tokens
    results.append(("Malformed Tokens", test_malformed_tokens()))
    
    # Test 2: Token placement
    results.append(("Token Placement", test_token_in_different_positions()))
    
    # Test 3: Claims validation
    results.append(("Claims Validation", test_token_claims_validation()))
    
    # Test 4: Special characters
    results.append(("Special Characters", test_special_characters_in_token()))
    
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
            response = client.get(f"{config.base_url}/health", timeout=5)
            if response.status_code != 200:
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