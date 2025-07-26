#!/bin/bash

# test.sh - Test suite for the curl-based MCP client
# This script verifies that all client functionality works correctly

# Source common library
source "$(dirname "$0")/common.sh"

# Override error handling for tests
set +e

# Test configuration
TEST_TOKEN_FILE="/tmp/mcp_test_token"
TEST_ACCESS_TOKEN=""  # Initialize to empty

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test functions
print_test() {
    echo -e "${CYAN}[TEST]${NC} $1"
    ((TESTS_RUN++))
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

# Cleanup function
cleanup() {
    rm -f "${TEST_TOKEN_FILE}" /tmp/mcp_access_token
}
trap cleanup EXIT

# Banner
print_banner "Curl Client Test Suite"

# Prerequisites check
print_section "Prerequisites Check"

print_test "Checking for required scripts"
if [ -f "${CLIENT_DIR}/get_token.sh" ] && [ -f "${CLIENT_DIR}/call_tool.sh" ]; then
    print_pass "All required scripts found"
else
    print_fail "Missing required scripts"
    exit 1
fi

print_test "Checking for required tools"
if command_exists curl && command_exists jq && command_exists base64; then
    print_pass "All required tools installed"
else
    print_fail "Missing required tools"
    exit 1
fi

# Service Availability
print_section "Service Availability"

print_test "Keycloak availability"
TOKEN_ENDPOINT="${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token"
if check_service_availability "Keycloak" "$TOKEN_ENDPOINT" "405"; then
    print_pass "Keycloak is available"
else
    print_fail "Keycloak is not available"
fi

print_test "MCP Server availability"
if check_service_availability "MCP Server" "${MCP_SERVER_URL}/health" "200"; then
    print_pass "MCP Server is available"
else
    print_fail "MCP Server is not available"
fi

# OAuth Discovery
print_section "OAuth Discovery"

print_test "OAuth metadata endpoint"
METADATA_URL="${MCP_SERVER_URL}/.well-known/oauth-protected-resource"
METADATA=$(curl -sk "$METADATA_URL" 2>/dev/null)
if echo "$METADATA" | jq -e '.issuer' >/dev/null 2>&1; then
    print_pass "OAuth metadata accessible"
else
    print_fail "Cannot access OAuth metadata"
fi

# Token Acquisition
print_section "Token Acquisition"

print_test "Get access token"
OUTPUT=$(SAVE_TOKEN=true TOKEN_FILE="${TEST_TOKEN_FILE}" "${CLIENT_DIR}/get_token.sh" 2>&1)
if [ $? -eq 0 ] && [ -f "${TEST_TOKEN_FILE}" ]; then
    print_pass "Token acquired successfully"
    TEST_ACCESS_TOKEN=$(cat "${TEST_TOKEN_FILE}")
else
    print_fail "Failed to acquire token"
    echo "$OUTPUT" | head -5
fi

print_test "Token format validation"
if [ -n "${TEST_ACCESS_TOKEN}" ] && validate_jwt_format "${TEST_ACCESS_TOKEN}"; then
    print_pass "Token has valid JWT format"
else
    print_fail "Invalid token format"
fi

# Tool Invocation
print_section "Tool Invocation"

if [ -n "${TEST_ACCESS_TOKEN}" ]; then
    print_test "Echo tool"
    RESPONSE=$(ACCESS_TOKEN="${TEST_ACCESS_TOKEN}" "${CLIENT_DIR}/call_tool.sh" -k echo "Test message" 2>&1)
    if echo "$RESPONSE" | jq -e '.result' >/dev/null 2>&1; then
        print_pass "Echo tool works"
    else
        print_fail "Echo tool failed"
    fi

    print_test "Timestamp tool"
    RESPONSE=$(ACCESS_TOKEN="${TEST_ACCESS_TOKEN}" "${CLIENT_DIR}/call_tool.sh" -k timestamp 2>&1)
    if echo "$RESPONSE" | jq -e '.result.timestamp' >/dev/null 2>&1; then
        print_pass "Timestamp tool works"
    else
        print_fail "Timestamp tool failed"
    fi

    print_test "Calculate tool"
    RESPONSE=$(ACCESS_TOKEN="${TEST_ACCESS_TOKEN}" "${CLIENT_DIR}/call_tool.sh" -k calculate add 2 2 2>&1)
    if echo "$RESPONSE" | jq -e '.result' >/dev/null 2>&1; then
        RESULT=$(echo "$RESPONSE" | jq -r '.result.result')
        if [ "$RESULT" = "4" ] || [ "$RESULT" = "4.0" ]; then
            print_pass "Calculate tool works correctly"
        else
            print_fail "Calculate tool gave wrong result: $RESULT"
        fi
    else
        print_fail "Calculate tool failed"
    fi
else
    print_warning "Skipping tool tests - no token available"
fi

# Error Handling
print_section "Error Handling"

print_test "Call without token"
OUTPUT=$( (unset ACCESS_TOKEN; rm -f /tmp/mcp_access_token "${TEST_TOKEN_FILE}"; "${CLIENT_DIR}/call_tool.sh" echo test) 2>&1)
if echo "$OUTPUT" | grep -q "No access token found"; then
    print_pass "Correctly handles missing token"
else
    print_fail "Accepted request without token"
fi

print_test "Invalid tool name"
if [ -n "${TEST_ACCESS_TOKEN}" ]; then
    OUTPUT=$(ACCESS_TOKEN="${TEST_ACCESS_TOKEN}" "${CLIENT_DIR}/call_tool.sh" -k invalid_tool 2>&1)
    if echo "$OUTPUT" | grep -qi "unknown tool"; then
        print_pass "Correctly rejects invalid tool"
    else
        print_fail "Did not reject invalid tool"
    fi
else
    print_warning "Skipping - no token"
fi

# Command Line Arguments
print_section "Command Line Arguments"

print_test "Help option for call_tool.sh"
if "${CLIENT_DIR}/call_tool.sh" -h 2>&1 | grep -q "Usage:"; then
    print_pass "Help option works"
else
    print_fail "Help option failed"
fi

print_test "Token file option"
if [ -f "${TEST_TOKEN_FILE}" ] && [ -n "${TEST_ACCESS_TOKEN}" ]; then
    OUTPUT=$("${CLIENT_DIR}/call_tool.sh" -f "${TEST_TOKEN_FILE}" -k echo "file test" 2>&1)
    if echo "$OUTPUT" | jq -e '.result' >/dev/null 2>&1; then
        print_pass "Token file option works"
    else
        print_fail "Token file option failed"
    fi
else
    print_warning "Skipping - no test token file"
fi

# Environment Variables
print_section "Environment Variables"

print_test "Custom MCP server URL"
OUTPUT=$(MCP_SERVER_URL="http://custom:443" "${CLIENT_DIR}/call_tool.sh" -h 2>&1)
if echo "$OUTPUT" | grep -q "http://custom:443"; then
    print_pass "Custom server URL respected"
else
    print_fail "Custom server URL not used"
fi

print_test "Custom Keycloak URL"
OUTPUT=$(KEYCLOAK_URL="http://custom:8080" "${CLIENT_DIR}/get_token.sh" 2>&1 || true)
if echo "$OUTPUT" | head -10 | grep -q "http://custom:8080"; then
    print_pass "Custom Keycloak URL respected"
else
    print_fail "Custom Keycloak URL not used"
fi

# Full Example Script
print_section "Full Example Script"

print_test "Full example script exists"
if [ -f "${CLIENT_DIR}/full_example.sh" ]; then
    print_pass "Full example script found"
else
    print_fail "Full example script not found"
fi

# Summary
print_section "Test Summary"

echo "Tests run: ${TESTS_RUN}"
echo "Tests passed: ${TESTS_PASSED}"
echo "Tests failed: ${TESTS_FAILED}"

if [ ${TESTS_FAILED} -eq 0 ]; then
    print_success "All tests passed!"
    exit 0
else
    print_error "Some tests failed"
    exit 1
fi 