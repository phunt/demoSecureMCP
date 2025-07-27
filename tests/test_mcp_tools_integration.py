#!/usr/bin/env python3
"""
Integration Tests for MCP Tools

This script tests the MCP demo tools:
1. Echo tool - requires mcp:read
2. Timestamp tool - requires mcp:read  
3. Calculator tool - requires mcp:write
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Optional
import httpx

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import Settings

# Test configuration
class TestConfig:
    def __init__(self):
        self.settings = Settings()
        self.base_url = "https://localhost"
        self.keycloak_url = self.settings.keycloak_url
        self.realm = self.settings.keycloak_realm
        self.client_id = self.settings.keycloak_client_id
        self.client_secret = self.settings.keycloak_client_secret
        self.token_endpoint = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"
        self.verify_ssl = False

config = TestConfig()

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

def get_token(scope: str) -> Optional[str]:
    """Get an access token with specific scope"""
    data = {
        "grant_type": "client_credentials",
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "scope": scope
    }
    
    try:
        with httpx.Client(verify=config.verify_ssl) as client:
            response = client.post(config.token_endpoint, data=data)
        
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            print_test(f"Failed to get token: {response.status_code}", "FAIL")
            return None
    except Exception as e:
        print_test(f"Error getting token: {str(e)}", "FAIL")
        return None

def test_tool_discovery():
    """Test the tool discovery endpoint"""
    print_test("\n=== Testing Tool Discovery ===")
    
    # Test without auth
    print_test("Testing without authentication")
    try:
        with httpx.Client(verify=config.verify_ssl) as client:
            response = client.get(f"{config.base_url}/api/v1/tools")
        
        if response.status_code in [401, 403]:
            print_test("Correctly requires authentication", "PASS")
        else:
            print_test(f"Unexpected status without auth: {response.status_code}", "FAIL")
            return False
    except Exception as e:
        print_test(f"Error: {str(e)}", "FAIL")
        return False
    
    # Test with auth
    token = get_token("mcp:read mcp:write")
    if not token:
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print_test("\nTesting with authentication")
    try:
        with httpx.Client(verify=config.verify_ssl) as client:
            response = client.get(f"{config.base_url}/api/v1/tools", headers=headers)
        
        if response.status_code == 200:
            tools = response.json()
            print_test("Tool discovery successful", "PASS")
            
            # Verify expected tools
            expected_tools = ["echo", "get_timestamp", "calculate"]
            found_tools = [tool["name"] for tool in tools.get("tools", [])]
            
            for tool in expected_tools:
                if tool in found_tools:
                    print_test(f"Found tool: {tool}", "PASS")
                else:
                    print_test(f"Missing tool: {tool}", "FAIL")
                    return False
            
            # Display tool details
            for tool in tools.get("tools", []):
                print_test(f"\nTool: {tool['name']}")
                print_test(f"  Endpoint: {tool['endpoint']}")
                print_test(f"  Requires: {tool['required_scope']}")
                print_test(f"  Available: {tool.get('available', 'N/A')}")
            
            return True
        else:
            print_test(f"Tool discovery failed: {response.status_code}", "FAIL")
            return False
    except Exception as e:
        print_test(f"Error: {str(e)}", "FAIL")
        return False

def test_echo_tool():
    """Test the echo tool"""
    print_test("\n=== Testing Echo Tool ===")
    
    # Get token with read scope
    token = get_token("mcp:read")
    if not token:
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    test_cases = [
        {
            "message": "Hello, MCP!",
            "uppercase": True,
            "timestamp": True
        },
        {
            "message": "Test message 123",
            "uppercase": False,
            "timestamp": False
        },
        {
            "message": "Unicode test: 你好世界 🌍",
            "uppercase": True,
            "timestamp": False
        }
    ]
    
    all_passed = True
    for i, test_data in enumerate(test_cases):
        print_test(f"\nTest case {i + 1}: {test_data['message']}")
        
        try:
            with httpx.Client(verify=config.verify_ssl) as client:
                response = client.post(
                    f"{config.base_url}/api/v1/tools/echo",
                    headers=headers,
                    json=test_data
                )
            
            if response.status_code == 200:
                response_data = response.json()
                result = response_data.get('result', {})
                print_test("Request successful", "PASS")
                print_test(f"Original: {result.get('original')}")
                print_test(f"Processed: {result.get('echo')}")
                print_test(f"Timestamp: {result.get('timestamp')}")
                
                # Verify processing
                expected = test_data["message"]
                if test_data.get("uppercase"):
                    expected = expected.upper()
                
                if result.get("echo") == expected:
                    print_test("Processing verified", "PASS")
                else:
                    print_test(f"Processing mismatch: expected '{expected}'", "FAIL")
                    all_passed = False
                
                # Verify timestamp if requested
                if test_data.get("timestamp") and not result.get("timestamp"):
                    print_test("Timestamp missing", "FAIL")
                    all_passed = False
            else:
                print_test(f"Request failed: {response.status_code}", "FAIL")
                print_test(f"Response: {response.text}", "FAIL")
                all_passed = False
        except Exception as e:
            print_test(f"Error: {str(e)}", "FAIL")
            all_passed = False
    
    # Test with wrong scope
    print_test("\nTesting with write-only token (should fail)")
    write_token = get_token("mcp:write")
    if write_token:
        headers["Authorization"] = f"Bearer {write_token}"
        try:
            with httpx.Client(verify=config.verify_ssl) as client:
                response = client.post(
                    f"{config.base_url}/api/v1/tools/echo",
                    headers=headers,
                    json={"message": "test"}
                )
            
            if response.status_code == 403:
                print_test("Correctly rejected write-only token", "PASS")
            else:
                print_test(f"Unexpected status: {response.status_code}", "FAIL")
                all_passed = False
        except Exception as e:
            print_test(f"Error: {str(e)}", "FAIL")
            all_passed = False
    
    return all_passed

def test_timestamp_tool():
    """Test the timestamp tool"""
    print_test("\n=== Testing Timestamp Tool ===")
    
    # Get token with read scope
    token = get_token("mcp:read")
    if not token:
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    test_cases = [
        {
            "format": "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO-like format
            "timezone": "UTC",
            "include_epoch": True
        },
        {
            "format": "%Y-%m-%d %H:%M:%S %Z",  # Human readable format
            "timezone": "America/New_York",
            "include_epoch": False
        },
        {
            # No format for unix timestamp test - will use default
            "include_epoch": True
        }
    ]
    
    all_passed = True
    for i, test_data in enumerate(test_cases):
        print_test(f"\nTest case {i + 1}: format={test_data.get('format', 'iso')}")
        
        try:
            with httpx.Client(verify=config.verify_ssl) as client:
                response = client.post(
                    f"{config.base_url}/api/v1/tools/timestamp",
                    headers=headers,
                    json=test_data
                )
            
            if response.status_code == 200:
                response_data = response.json()
                result = response_data.get('result', {})
                print_test("Request successful", "PASS")
                print_test(f"Timestamp: {result.get('timestamp')}")
                print_test(f"Format: {result.get('format')}")
                if result.get("timezone"):
                    print_test(f"Timezone: {result.get('timezone')}")
                if result.get("epoch"):
                    print_test(f"Epoch: {result.get('epoch')}")
                if result.get("relative"):
                    print_test(f"Relative: {result.get('relative')}")
                
                # Verify timestamp format
                timestamp = result.get("timestamp")
                if timestamp:
                    # All timestamps should be strings
                    if isinstance(timestamp, str) and len(timestamp) > 0:
                        print_test("Timestamp format verified", "PASS")
                    else:
                        print_test("Invalid timestamp format", "FAIL")
                        all_passed = False
                else:
                    print_test("Missing timestamp in response", "FAIL")
                    all_passed = False
            else:
                print_test(f"Request failed: {response.status_code}", "FAIL")
                all_passed = False
        except Exception as e:
            print_test(f"Error: {str(e)}", "FAIL")
            all_passed = False
    
    return all_passed

def test_calculator_tool():
    """Test the calculator tool"""
    print_test("\n=== Testing Calculator Tool ===")
    
    # Get token with write scope
    token = get_token("mcp:write")
    if not token:
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    test_cases = [
        {
            "operation": "add",
            "operands": [10, 20, 30],
            "expected": 60
        },
        {
            "operation": "multiply",
            "operands": [5, 4, 2],
            "expected": 40
        },
        {
            "operation": "divide",
            "operands": [100, 4],
            "expected": 25
        },
        {
            "operation": "power",
            "operands": [2, 8],
            "expected": 256
        },
        {
            "operation": "sqrt",
            "operands": [144],
            "expected": 12
        },
        {
            "operation": "factorial",
            "operands": [5],
            "expected": 120
        },
        {
            "operation": "divide",
            "operands": [10, 0],
            "expected_error": True
        }
    ]
    
    all_passed = True
    for i, test_data in enumerate(test_cases):
        print_test(f"\nTest case {i + 1}: {test_data['operation']} {test_data['operands']}")
        
        try:
            with httpx.Client(verify=config.verify_ssl) as client:
                response = client.post(
                    f"{config.base_url}/api/v1/tools/calculate",
                    headers=headers,
                    json={
                        "operation": test_data["operation"],
                        "operands": test_data["operands"]
                    }
                )
            
            if test_data.get("expected_error"):
                if response.status_code == 400:
                    print_test("Correctly handled error case", "PASS")
                else:
                    print_test(f"Expected error but got: {response.status_code}", "FAIL")
                    all_passed = False
            elif response.status_code == 200:
                response_data = response.json()
                result = response_data.get('result', {})
                print_test("Request successful", "PASS")
                print_test(f"Result: {result}")
                print_test(f"Operation: {result.get('operation')}")
                print_test(f"Operands: {result.get('operands')}")
                
                # Verify result
                if abs(result.get("result", 0) - test_data["expected"]) < 0.0001:
                    print_test("Calculation verified", "PASS")
                else:
                    print_test(f"Calculation mismatch: expected {test_data['expected']}", "FAIL")
                    all_passed = False
            else:
                print_test(f"Request failed: {response.status_code}", "FAIL")
                print_test(f"Response: {response.text}", "FAIL")
                all_passed = False
        except Exception as e:
            print_test(f"Error: {str(e)}", "FAIL")
            all_passed = False
    
    # Test with wrong scope
    print_test("\nTesting with read-only token (should fail)")
    read_token = get_token("mcp:read")
    if read_token:
        headers["Authorization"] = f"Bearer {read_token}"
        try:
            with httpx.Client(verify=config.verify_ssl) as client:
                response = client.post(
                    f"{config.base_url}/api/v1/tools/calculate",
                    headers=headers,
                    json={"operation": "add", "operands": [1, 2]}
                )
            
            if response.status_code == 403:
                print_test("Correctly rejected read-only token", "PASS")
            else:
                print_test(f"Unexpected status: {response.status_code}", "FAIL")
                all_passed = False
        except Exception as e:
            print_test(f"Error: {str(e)}", "FAIL")
            all_passed = False
    
    return all_passed

def test_error_handling():
    """Test error handling for tools"""
    print_test("\n=== Testing Error Handling ===")
    
    token = get_token("mcp:read mcp:write")
    if not token:
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    error_cases = [
        {
            "tool": "echo",
            "data": {},  # Missing required field
            "description": "Missing required field"
        },
        {
            "tool": "echo",
            "data": {"message": 123},  # Wrong type (number instead of string)
            "description": "Wrong message type"
        },
        {
            "tool": "calculate",
            "data": {"operation": "invalid", "operands": [1, 2]},
            "description": "Invalid operation"
        },
        {
            "tool": "calculate",
            "data": {"operation": "add", "operands": []},  # Empty operands
            "description": "Empty operands"
        },
        {
            "tool": "timestamp",
            "data": {"format": 123},  # Wrong type - should be string
            "description": "Wrong format type"
        }
    ]
    
    all_passed = True
    for case in error_cases:
        print_test(f"\nTesting: {case['description']}")
        
        try:
            with httpx.Client(verify=config.verify_ssl) as client:
                response = client.post(
                    f"{config.base_url}/api/v1/tools/{case['tool']}",
                    headers=headers,
                    json=case['data']
                )
            
            if response.status_code in [400, 422]:
                print_test(f"Correctly returned error status {response.status_code}", "PASS")
                if response.headers.get("content-type", "").startswith("application/json"):
                    error_detail = response.json()
                    print_test(f"Error detail: {error_detail.get('detail', 'No detail')}")
            else:
                print_test(f"Expected error but got: {response.status_code}", "FAIL")
                all_passed = False
        except Exception as e:
            print_test(f"Error: {str(e)}", "FAIL")
            all_passed = False
    
    return all_passed

def run_all_tests():
    """Run all MCP tool integration tests"""
    print_test("=== MCP Tools Integration Test Suite ===\n", "INFO")
    
    results = []
    
    # Test 1: Tool discovery
    results.append(("Tool Discovery", test_tool_discovery()))
    
    # Test 2: Echo tool
    results.append(("Echo Tool", test_echo_tool()))
    
    # Test 3: Timestamp tool
    results.append(("Timestamp Tool", test_timestamp_tool()))
    
    # Test 4: Calculator tool
    results.append(("Calculator Tool", test_calculator_tool()))
    
    # Test 5: Error handling
    results.append(("Error Handling", test_error_handling()))
    
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