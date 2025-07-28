"""
Pytest configuration for MCP Server tests
"""

import os
import pytest
from pathlib import Path


def pytest_configure():
    """Configure pytest before running tests"""
    # Set test environment variables before importing settings
    os.environ["TESTING"] = "true"
    os.environ["CONTAINER_ENV"] = "false"
    os.environ["DEBUG"] = "true"
    
    # Fix OAuth configuration for local testing
    os.environ["OAUTH_ISSUER"] = "http://localhost:8080/realms/mcp-realm"
    
    print("Test configuration loaded")


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Automatically set up test environment for each test"""
    # This fixture runs before each test
    # Store original env vars to restore later
    original_vars = {}
    test_vars = {
        "OAUTH_ISSUER": "http://localhost:8080/realms/mcp-realm",
        "CONTAINER_ENV": "false",
        "DEBUG": "true",
        "TESTING": "true"
    }
    
    for key, value in test_vars.items():
        original_vars[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original values
    for key, original_value in original_vars.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def oauth_audience():
    """Get the OAuth audience that matches the client ID"""
    # Read the DCR client file to get the client ID
    dcr_client_file = Path(__file__).parent.parent / ".dcr_client.json"
    if dcr_client_file.exists():
        import json
        with open(dcr_client_file) as f:
            dcr_data = json.load(f)
            client_id = dcr_data.get("client_id")
            if client_id:
                # Set the OAuth audience to match the client ID
                os.environ["OAUTH_AUDIENCE"] = client_id
                return client_id
    
    # Fallback to default
    default_audience = "mcp-server"
    os.environ["OAUTH_AUDIENCE"] = default_audience
    return default_audience 