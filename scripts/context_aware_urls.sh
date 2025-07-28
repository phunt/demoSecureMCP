#!/bin/bash

# context_aware_urls.sh - Context-aware URL management
# This script provides functions to automatically select the correct URLs
# based on execution context (host vs container)

# Source common library
source "$(dirname "$0")/common_lib.sh"

# Detect if running inside a Docker container
is_container_context() {
    # Check multiple indicators
    if [ -f /.dockerenv ]; then
        return 0
    fi
    
    if [ "${CONTAINER_ENV:-false}" = "true" ]; then
        return 0
    fi
    
    # Check if we're in a container by looking at cgroup
    if [ -f /proc/1/cgroup ] && grep -q 'docker\|kubepods' /proc/1/cgroup 2>/dev/null; then
        return 0
    fi
    
    return 1
}

# Get the appropriate Keycloak URL based on context
get_keycloak_url() {
    if is_container_context; then
        echo "${INTERNAL_KEYCLOAK_URL:-http://keycloak:8080}"
    else
        echo "${EXTERNAL_KEYCLOAK_URL:-http://localhost:8080}"
    fi
}

# Get the appropriate MCP server URL based on context
get_mcp_url() {
    if is_container_context; then
        echo "${INTERNAL_MCP_URL:-http://mcp-server:8000}"
    else
        echo "${EXTERNAL_BASE_URL:-https://localhost}"
    fi
}

# Get the appropriate Redis URL based on context
get_redis_url() {
    if is_container_context; then
        echo "${INTERNAL_REDIS_URL:-redis://redis:6379/0}"
    else
        echo "redis://localhost:6379/0"
    fi
}

# Get the OAuth issuer URL (always uses external/public URL)
get_oauth_issuer() {
    # OAuth issuer must match what's in the JWT tokens
    # This is always the external URL that clients see
    echo "${OAUTH_ISSUER:-http://localhost:8080/realms/mcp-realm}"
}

# Get the appropriate base URL for the current context
get_base_url() {
    # In production, use public URL if available
    if [ -n "${PUBLIC_BASE_URL:-}" ] && [ "${DEBUG:-true}" = "false" ]; then
        echo "${PUBLIC_BASE_URL}"
    elif is_container_context; then
        echo "${INTERNAL_MCP_URL:-http://mcp-server:8000}"
    else
        echo "${EXTERNAL_BASE_URL:-https://localhost}"
    fi
}

# Print current context information
print_context_info() {
    print_section "Context Information"
    
    if is_container_context; then
        print_info "Running in CONTAINER context"
        print_info "Using internal service URLs for communication"
    else
        print_info "Running in HOST context"
        print_info "Using external URLs for communication"
    fi
    
    echo
    print_info "Resolved URLs:"
    print_info "  Keycloak URL: $(get_keycloak_url)"
    print_info "  MCP URL: $(get_mcp_url)"
    print_info "  Redis URL: $(get_redis_url)"
    print_info "  OAuth Issuer: $(get_oauth_issuer)"
    echo
}

# Set up environment variables based on context
setup_context_env() {
    export KEYCLOAK_URL=$(get_keycloak_url)
    export MCP_URL=$(get_mcp_url)
    export REDIS_URL=$(get_redis_url)
    export OAUTH_ISSUER=$(get_oauth_issuer)
    
    print_debug "Environment variables set based on context:"
    print_debug "  KEYCLOAK_URL=${KEYCLOAK_URL}"
    print_debug "  MCP_URL=${MCP_URL}"
    print_debug "  REDIS_URL=${REDIS_URL}"
    print_debug "  OAUTH_ISSUER=${OAUTH_ISSUER}"
}

# Wait for services based on context
wait_for_context_services() {
    local keycloak_host keycloak_port
    local mcp_host mcp_port
    
    # Parse URLs to get host and port
    if is_container_context; then
        keycloak_host="keycloak"
        keycloak_port="8080"
        mcp_host="mcp-server"
        mcp_port="8000"
    else
        keycloak_host="localhost"
        keycloak_port="8080"
        mcp_host="localhost"
        mcp_port="443"  # Through nginx
    fi
    
    # Wait for services
    wait_for_service "Keycloak" "${keycloak_host}" "${keycloak_port}" 120
    wait_for_service "MCP Server" "${mcp_host}" "${mcp_port}" 60
}

# Export functions
export -f is_container_context
export -f get_keycloak_url get_mcp_url get_redis_url get_oauth_issuer
export -f print_context_info setup_context_env wait_for_context_services 