#!/usr/bin/env python3
"""Test script to verify JWT validation functionality"""

import requests
import json
import sys
import time

KEYCLOAK_URL = "http://localhost:8080"
MCP_SERVER_URL = "http://localhost:8000"
REALM = "mcp-realm"


def get_client_token(scopes="mcp:read mcp:write"):
    """Get token using client credentials flow"""
    print(f"Getting token with scopes: {scopes}")
    url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
    
    data = {
        'grant_type': 'client_credentials',
        'client_id': 'mcp-server',
        'client_secret': 'mcp-server-secret-change-in-production',
        'scope': scopes
    }
    
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        token_data = response.json()
        print("✅ Token obtained successfully")
        return token_data['access_token']
    except Exception as e:
        print(f"❌ Failed to get token: {e}")
        return None


def test_health_endpoint():
    """Test unprotected health endpoint"""
    print("\n1. Testing Health Endpoint (No Auth Required)...")
    
    try:
        response = requests.get(f"{MCP_SERVER_URL}/health")
        response.raise_for_status()
        print(f"   ✅ Health check passed: {response.json()}")
        return True
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False


def test_protected_endpoint_no_auth():
    """Test protected endpoint without auth"""
    print("\n2. Testing Protected Endpoint Without Auth...")
    
    try:
        response = requests.get(f"{MCP_SERVER_URL}/api/v1/me")
        if response.status_code == 403:
            print(f"   ✅ Correctly rejected (403): {response.json()}")
            return True
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
        return False


def test_current_user_endpoint(token):
    """Test current user endpoint with valid token"""
    print("\n3. Testing Current User Endpoint...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{MCP_SERVER_URL}/api/v1/me", headers=headers)
        response.raise_for_status()
        user_info = response.json()
        print(f"   ✅ User info retrieved:")
        print(f"      - Subject: {user_info.get('sub')}")
        print(f"      - Username: {user_info.get('username')}")
        print(f"      - Scopes: {user_info.get('scopes')}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        if hasattr(e, 'response'):
            print(f"      Response: {e.response.text}")
        return False


def test_scope_protected_endpoints(token):
    """Test endpoints with different scope requirements"""
    print("\n4. Testing Scope-Protected Endpoints...")
    
    headers = {"Authorization": f"Bearer {token}"}
    endpoints = [
        ("/api/v1/protected/read", "mcp:read"),
        ("/api/v1/protected/write", "mcp:write"),
        ("/api/v1/protected/infer", "mcp:infer")
    ]
    
    all_passed = True
    for endpoint, scope in endpoints:
        try:
            response = requests.get(f"{MCP_SERVER_URL}{endpoint}", headers=headers)
            if response.status_code == 200:
                print(f"   ✅ {scope} access granted: {response.json()['message']}")
            elif response.status_code == 403:
                print(f"   ⚠️  {scope} access denied (missing scope)")
                all_passed = False
            else:
                print(f"   ❌ Unexpected response for {scope}: {response.status_code}")
                all_passed = False
        except Exception as e:
            print(f"   ❌ Failed to test {scope}: {e}")
            all_passed = False
    
    return all_passed


def test_expired_token():
    """Test with an expired token"""
    print("\n5. Testing Expired Token Handling...")
    
    # Use a pre-generated expired token (you'd need to generate this)
    expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjE1MTYyMzkwMjJ9.4Adcj3UFYzPUVaVF43FmMab6RlaQD8A9V8wFzzht-KQ"
    
    headers = {"Authorization": f"Bearer {expired_token}"}
    
    try:
        response = requests.get(f"{MCP_SERVER_URL}/api/v1/me", headers=headers)
        if response.status_code == 401:
            print(f"   ✅ Correctly rejected expired token: {response.json()}")
            return True
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
        return False


def test_different_scope_combinations():
    """Test with different scope combinations"""
    print("\n6. Testing Different Scope Combinations...")
    
    # Test with only read scope
    print("\n   Testing with only 'mcp:read' scope:")
    token = get_client_token("mcp:read")
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Should succeed
        response = requests.get(f"{MCP_SERVER_URL}/api/v1/protected/read", headers=headers)
        if response.status_code == 200:
            print("      ✅ Read access granted")
        else:
            print("      ❌ Read access denied")
        
        # Should fail
        response = requests.get(f"{MCP_SERVER_URL}/api/v1/protected/write", headers=headers)
        if response.status_code == 403:
            print("      ✅ Write access correctly denied")
        else:
            print("      ❌ Write access should have been denied")


def main():
    print("=" * 60)
    print("JWT Validation Test Suite")
    print("=" * 60)
    
    # Wait a moment for server to be ready
    print("\nWaiting for server to be ready...")
    time.sleep(2)
    
    # Run tests
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Health check
    total_tests += 1
    if test_health_endpoint():
        tests_passed += 1
    
    # Test 2: No auth
    total_tests += 1
    if test_protected_endpoint_no_auth():
        tests_passed += 1
    
    # Get token for authenticated tests
    token = get_client_token("mcp:read mcp:write")
    if not token:
        print("\n❌ Cannot continue without valid token")
        sys.exit(1)
    
    # Test 3: Current user
    total_tests += 1
    if test_current_user_endpoint(token):
        tests_passed += 1
    
    # Test 4: Scope protection
    total_tests += 1
    if test_scope_protected_endpoints(token):
        tests_passed += 1
    
    # Test 5: Expired token
    total_tests += 1
    if test_expired_token():
        tests_passed += 1
    
    # Test 6: Different scopes
    test_different_scope_combinations()
    
    print("\n" + "=" * 60)
    print(f"Test Results: {tests_passed}/{total_tests} passed")
    print("=" * 60)


if __name__ == "__main__":
    main() 