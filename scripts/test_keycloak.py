#!/usr/bin/env python3
"""Test script to verify Keycloak configuration"""

import requests
import json
import sys

KEYCLOAK_URL = "http://localhost:8080"
REALM = "mcp-realm"

def test_openid_configuration():
    """Test that the OpenID configuration endpoint is accessible"""
    print("1. Testing OpenID Configuration endpoint...")
    url = f"{KEYCLOAK_URL}/realms/{REALM}/.well-known/openid-configuration"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        config = response.json()
        print(f"   ✅ OpenID Configuration accessible")
        print(f"   - Issuer: {config['issuer']}")
        print(f"   - JWKS URI: {config['jwks_uri']}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_client_credentials():
    """Test client credentials flow for the MCP server"""
    print("\n2. Testing Client Credentials flow...")
    url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
    
    data = {
        'grant_type': 'client_credentials',
        'client_id': 'mcp-server',
        'client_secret': 'mcp-server-secret-change-in-production',
        'scope': 'mcp:read mcp:write'
    }
    
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        token_data = response.json()
        print(f"   ✅ Client credentials token obtained")
        print(f"   - Access Token: {token_data['access_token'][:50]}...")
        print(f"   - Token Type: {token_data['token_type']}")
        print(f"   - Expires In: {token_data['expires_in']} seconds")
        
        # Decode token to check scopes
        import base64
        token_parts = token_data['access_token'].split('.')
        payload = json.loads(base64.urlsafe_b64decode(token_parts[1] + '=' * (4 - len(token_parts[1]) % 4)))
        print(f"   - Scopes in token: {payload.get('scope', 'No scopes found')}")
        
        return token_data['access_token']
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return None

def test_password_grant():
    """Test password grant flow for demo user"""
    print("\n3. Testing Password Grant flow (demo user)...")
    url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
    
    data = {
        'grant_type': 'password',
        'client_id': 'mcp-server',
        'client_secret': 'mcp-server-secret-change-in-production',
        'username': 'demo',
        'password': 'demo123',
        'scope': 'openid profile email mcp:read'
    }
    
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        token_data = response.json()
        print(f"   ✅ Password grant token obtained")
        print(f"   - Access Token: {token_data['access_token'][:50]}...")
        print(f"   - Refresh Token: {token_data.get('refresh_token', 'N/A')[:50]}...")
        
        # Decode token to check user info
        import base64
        token_parts = token_data['access_token'].split('.')
        payload = json.loads(base64.urlsafe_b64decode(token_parts[1] + '=' * (4 - len(token_parts[1]) % 4)))
        print(f"   - Username: {payload.get('preferred_username', 'N/A')}")
        print(f"   - Email: {payload.get('email', 'N/A')}")
        print(f"   - Scopes: {payload.get('scope', 'No scopes found')}")
        
        return token_data['access_token']
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return None

def test_jwks():
    """Test that JWKS endpoint is accessible"""
    print("\n4. Testing JWKS endpoint...")
    url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/certs"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        jwks = response.json()
        print(f"   ✅ JWKS accessible")
        print(f"   - Number of keys: {len(jwks.get('keys', []))}")
        for i, key in enumerate(jwks.get('keys', [])):
            print(f"   - Key {i+1}: {key.get('alg')} (kid: {key.get('kid')[:10]}...)")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_token_introspection(token):
    """Test token introspection endpoint"""
    print("\n5. Testing Token Introspection...")
    url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token/introspect"
    
    data = {
        'token': token,
        'client_id': 'mcp-server',
        'client_secret': 'mcp-server-secret-change-in-production'
    }
    
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        introspection = response.json()
        print(f"   ✅ Token introspection successful")
        print(f"   - Active: {introspection.get('active')}")
        print(f"   - Username: {introspection.get('username', 'N/A')}")
        print(f"   - Client ID: {introspection.get('client_id')}")
        print(f"   - Scopes: {introspection.get('scope', 'N/A')}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def main():
    print("=" * 60)
    print("Keycloak Configuration Test")
    print("=" * 60)
    
    # Test OpenID configuration
    if not test_openid_configuration():
        print("\n❌ OpenID configuration test failed. Is Keycloak running?")
        sys.exit(1)
    
    # Test client credentials
    client_token = test_client_credentials()
    
    # Test password grant
    user_token = test_password_grant()
    
    # Test JWKS
    test_jwks()
    
    # Test token introspection
    if user_token:
        test_token_introspection(user_token)
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    main() 