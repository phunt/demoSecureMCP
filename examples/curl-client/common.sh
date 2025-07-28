#!/bin/bash

# common.sh - Common functions and environment setup for MCP API examples
# This file provides shared functionality for the curl client examples

# Enable strict error handling
set -euo pipefail

# ==========================================================================
# Environment Setup - Using External URLs (client always runs from host)
# ==========================================================================

# Default environment variables - clients always use external URLs
set_default_env() {
    local var_name=$1
    local default_value=$2
    if [ -z "${!var_name:-}" ]; then
        export "${var_name}=${default_value}"
    fi
}

# Set defaults for external access
set_default_env "MCP_SERVER_URL" "${EXTERNAL_BASE_URL:-https://localhost}"
set_default_env "KEYCLOAK_URL" "${EXTERNAL_KEYCLOAK_URL:-http://localhost:8080}"
set_default_env "KEYCLOAK_REALM" "mcp-realm"
set_default_env "CLIENT_ID" "mcp-server"
set_default_env "CLIENT_SECRET" "mcp-server-secret-change-in-production"

# Allow insecure connections for development (self-signed certificates)
set_default_env "CURL_INSECURE" "true"

# ==========================================================================
# Color Output Functions
# ==========================================================================

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# Print functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_debug() {
    if [ "${DEBUG:-false}" = "true" ]; then
        echo -e "${CYAN}[DEBUG]${NC} $1" >&2
    fi
}

# ==========================================================================
# Utility Functions
# ==========================================================================

# Check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Die with error message
die() {
    print_error "$1"
    exit "${2:-1}"
}

# Validate required commands
check_requirements() {
    local missing_commands=()
    
    for cmd in curl jq; do
        if ! command_exists "$cmd"; then
            missing_commands+=("$cmd")
        fi
    done
    
    if [ ${#missing_commands[@]} -gt 0 ]; then
        die "Missing required commands: ${missing_commands[*]}"
    fi
}

# ==========================================================================
# Authentication Functions
# ==========================================================================

# Get access token using client credentials flow
get_access_token() {
    local token_endpoint="${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token"
    local curl_opts=()
    
    if [ "${CURL_INSECURE}" = "true" ]; then
        curl_opts+=(-k)
    fi
    
    print_debug "Token endpoint: $token_endpoint"
    print_debug "Client ID: $CLIENT_ID"
    
    local response
    response=$(curl -s "${curl_opts[@]}" -X POST "$token_endpoint" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "grant_type=client_credentials" \
        -d "client_id=$CLIENT_ID" \
        -d "client_secret=$CLIENT_SECRET" \
        -d "scope=mcp:read mcp:write")
    
    local access_token
    access_token=$(echo "$response" | jq -r '.access_token // empty')
    
    if [ -z "$access_token" ]; then
        print_error "Failed to get access token"
        print_debug "Response: $response"
        return 1
    fi
    
    echo "$access_token"
}

# ==========================================================================
# API Call Functions
# ==========================================================================

# Make an authenticated API call
call_api() {
    local method=$1
    local endpoint=$2
    local data=${3:-}
    local token=${4:-$(get_access_token)}
    
    local url="${MCP_SERVER_URL}${endpoint}"
    local curl_opts=(-s -X "$method" -H "Authorization: Bearer $token")
    
    if [ "${CURL_INSECURE}" = "true" ]; then
        curl_opts+=(-k)
    fi
    
    if [ -n "$data" ]; then
        curl_opts+=(-H "Content-Type: application/json" -d "$data")
    fi
    
    print_debug "API Call: $method $url"
    
    local response
    local http_code
    
    # Make the request and capture both response and status code
    response=$(curl "${curl_opts[@]}" -w "\n%{http_code}" "$url")
    http_code=$(echo "$response" | tail -n1)
    response=$(echo "$response" | head -n-1)
    
    print_debug "HTTP Code: $http_code"
    print_debug "Response: $response"
    
    # Check for success (2xx status codes)
    if [[ "$http_code" =~ ^2[0-9][0-9]$ ]]; then
        echo "$response"
        return 0
    else
        print_error "API call failed with status: $http_code"
        print_error "Response: $response"
        return 1
    fi
}

# ==========================================================================
# Service Health Checks
# ==========================================================================

# Check if a service is available
check_service_availability() {
    local service_name=$1
    local url=$2
    local expected_status=${3:-200}
    
    local curl_opts=(-s -o /dev/null -w "%{http_code}")
    
    if [ "${CURL_INSECURE}" = "true" ]; then
        curl_opts+=(-k)
    fi
    
    local status
    status=$(curl "${curl_opts[@]}" "$url" 2>/dev/null || echo "000")
    
    if [ "$status" = "$expected_status" ] || [ "$status" = "200" ]; then
        print_success "$service_name is available"
        return 0
    else
        print_error "$service_name is not available (status: $status)"
        return 1
    fi
}

# ==========================================================================
# Validation Functions
# ==========================================================================

# Validate environment setup
validate_environment() {
    local valid=true
    
    # Check required environment variables
    for var in MCP_SERVER_URL KEYCLOAK_URL KEYCLOAK_REALM CLIENT_ID CLIENT_SECRET; do
        if [ -z "${!var:-}" ]; then
            print_error "Required environment variable $var is not set"
            valid=false
        fi
    done
    
    # Validate URLs
    for url_var in MCP_SERVER_URL KEYCLOAK_URL; do
        if ! is_valid_url "${!url_var}"; then
            print_error "Invalid URL in $url_var: ${!url_var}"
            valid=false
        fi
    done
    
    if [ "$valid" = "false" ]; then
        die "Environment validation failed"
    fi
}

# Check if a URL is valid
is_valid_url() {
    local url=$1
    [[ "$url" =~ ^https?:// ]]
}

# ==========================================================================
# Run checks on script load
# ==========================================================================

# Check requirements when sourced
check_requirements 