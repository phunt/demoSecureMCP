#!/bin/bash

# common.sh - Common functions for curl client scripts
# Source this file in client scripts: source "$(dirname "$0")/common.sh"

# Get the directory of this script
CLIENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source main common library
source "${CLIENT_DIR}/../../scripts/common_lib.sh"

# Client-specific configuration defaults
set_default_env "MCP_SERVER_URL" "https://localhost"
set_default_env "KEYCLOAK_URL" "http://localhost:8080"
set_default_env "KEYCLOAK_REALM" "mcp-realm"
set_default_env "CLIENT_ID" "mcp-server"
set_default_env "CLIENT_SECRET" "mcp-server-secret-change-in-production"
set_default_env "TOKEN_FILE" "/tmp/mcp_access_token"

# Client-specific functions

# Check if access token is available
check_access_token() {
    local token="${ACCESS_TOKEN:-}"
    local token_file="${1:-$TOKEN_FILE}"
    
    # Try environment variable first
    if [ -n "$token" ]; then
        echo "$token"
        return 0
    fi
    
    # Try token file
    if [ -f "$token_file" ] && [ -r "$token_file" ]; then
        token=$(cat "$token_file")
        if [ -n "$token" ]; then
            echo "$token"
            return 0
        fi
    fi
    
    return 1
}

# Validate JWT token format
validate_jwt_format() {
    local token=$1
    
    # JWT should have three parts separated by dots
    local parts=$(echo "$token" | tr '.' '\n' | wc -l)
    if [ "$parts" -ne 3 ]; then
        return 1
    fi
    
    # Each part should be base64url encoded
    if ! echo "$token" | grep -E '^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$' > /dev/null; then
        return 1
    fi
    
    return 0
}

# Parse JWT payload (base64url decode)
parse_jwt_payload() {
    local token=$1
    local payload=$(echo "$token" | cut -d. -f2)
    
    # Add padding if needed
    local len=$((${#payload} % 4))
    if [ $len -eq 2 ]; then
        payload="${payload}=="
    elif [ $len -eq 3 ]; then
        payload="${payload}="
    fi
    
    # Decode (handle both Linux and macOS base64)
    if command_exists base64; then
        echo "$payload" | base64 -d 2>/dev/null || echo "$payload" | base64 -D 2>/dev/null
    fi
}

# Check if token is expired
is_token_expired() {
    local token=$1
    
    if ! validate_jwt_format "$token"; then
        return 0  # Invalid token is considered expired
    fi
    
    local payload=$(parse_jwt_payload "$token")
    if [ -z "$payload" ]; then
        return 0  # Can't parse, consider expired
    fi
    
    local exp=$(echo "$payload" | jq -r '.exp' 2>/dev/null)
    if [ -z "$exp" ] || [ "$exp" = "null" ]; then
        return 0  # No expiry, consider expired
    fi
    
    local now=$(date +%s)
    if [ "$now" -ge "$exp" ]; then
        return 0  # Token is expired
    fi
    
    return 1  # Token is valid
}

# Make authenticated request
make_authenticated_request() {
    local method=$1
    local url=$2
    local data=$3
    local token=$4
    
    local curl_opts=(-s -k -H "Authorization: Bearer ${token}" -H "Content-Type: application/json")
    
    case "$method" in
        GET)
            curl "${curl_opts[@]}" -X GET "$url"
            ;;
        POST)
            if [ -n "$data" ]; then
                curl "${curl_opts[@]}" -X POST -d "$data" "$url"
            else
                curl "${curl_opts[@]}" -X POST "$url"
            fi
            ;;
        *)
            print_error "Unsupported HTTP method: $method"
            return 1
            ;;
    esac
}

# Check service availability
check_service_availability() {
    local service_name=$1
    local url=$2
    local expected_status=${3:-200}
    
    print_debug "Checking $service_name availability at $url"
    
    local status=$(curl -s -k -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    
    if [ "$status" = "$expected_status" ]; then
        print_debug "$service_name is available (status: $status)"
        return 0
    else
        print_debug "$service_name returned status: $status (expected: $expected_status)"
        return 1
    fi
}

# Wait for Keycloak to be ready
wait_for_keycloak() {
    local max_wait=${1:-30}
    local token_endpoint="${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token"
    
    print_info "Waiting for Keycloak to be ready..."
    
    if retry_with_backoff 5 2 "check_service_availability 'Keycloak' '$token_endpoint' '405'"; then
        print_success "Keycloak is ready!"
        return 0
    else
        print_error "Keycloak is not available after ${max_wait} seconds"
        return 1
    fi
}

# Common initialization
init_client() {
    # Check for required tools
    check_required_tools curl jq base64
    
    # Validate URLs
    if ! is_valid_url "$MCP_SERVER_URL"; then
        die "Invalid MCP_SERVER_URL: $MCP_SERVER_URL"
    fi
    
    if ! is_valid_url "$KEYCLOAK_URL"; then
        die "Invalid KEYCLOAK_URL: $KEYCLOAK_URL"
    fi
}

# Export client-specific functions
export -f check_access_token validate_jwt_format parse_jwt_payload
export -f is_token_expired make_authenticated_request
export -f check_service_availability wait_for_keycloak init_client 