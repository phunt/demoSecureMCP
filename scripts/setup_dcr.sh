#!/usr/bin/env bash
#
# setup_dcr.sh - Set up Dynamic Client Registration for MCP Server
#

set -euo pipefail

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common_lib.sh"

# Configuration
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
KEYCLOAK_REALM="${KEYCLOAK_REALM:-mcp-realm}"
KEYCLOAK_ADMIN="${KEYCLOAK_ADMIN:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin_password}"

# For Docker environments, the issuer URL might be different
# This is the URL that the MCP server will use to connect to Keycloak
KEYCLOAK_ISSUER_URL="${KEYCLOAK_ISSUER_URL:-$KEYCLOAK_URL}"

# Script options
AUTO_UPDATE=true
ENV_FILE=".env.docker"
SHOW_HELP=false

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Set up Dynamic Client Registration for MCP Server by creating an initial access token
in Keycloak and optionally updating the environment file.

OPTIONS:
    -a, --no-auto-update    Disable automatically updating the environment file without prompting
    -e, --env-file FILE     Specify the environment file to update (default: .env.docker)
    -h, --help              Show this help message
    
EXAMPLES:
    $0                      # Interactive mode (prompts for confirmation)
    $0 --no-auto-update     # Disable utomatically updating .env.docker
    $0 -a -e .env.custom    # Automatically update .env.custom
    
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--no-auto-update)
            AUTO_UPDATE=false
            shift
            ;;
        -e|--env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Function to get admin token
get_admin_token() {
    print_info "Getting Keycloak admin token..." >&2
    
    local response=$(curl -s -X POST \
        "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=${KEYCLOAK_ADMIN}" \
        -d "password=${KEYCLOAK_ADMIN_PASSWORD}" \
        -d "grant_type=password" \
        -d "client_id=admin-cli")
    
    local token=$(echo "$response" | jq -r '.access_token // empty')
    
    if [[ -z "$token" ]]; then
        print_error "Failed to get admin token" >&2
        echo "$response" >&2
        return 1
    fi
    
    echo "$token"
}

# Function to create initial access token
create_initial_access_token() {
    local admin_token=$1
    
    print_info "Creating initial access token..." >&2
    
    local response=$(curl -s -X POST \
        "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/clients-initial-access" \
        -H "Authorization: Bearer ${admin_token}" \
        -H "Content-Type: application/json" \
        -d '{
            "count": 10,
            "expiration": 3600
        }')
    
    local token=$(echo "$response" | jq -r '.token // empty')
    
    if [[ -z "$token" ]]; then
        print_error "Failed to create initial access token" >&2
        echo "$response" >&2
        return 1
    fi
    
    echo "$token"
}

# Function to update environment file
update_env_file() {
    local token=$1
    
    print_info "Updating environment file: $ENV_FILE"
    
    # Check if file exists
    if [[ ! -f "$ENV_FILE" ]]; then
        print_error "Environment file not found: $ENV_FILE"
        return 1
    fi
    
    # Update or add DCR settings
    if grep -q "^USE_DCR=" "$ENV_FILE"; then
        sed -i.bak "s/^USE_DCR=.*/USE_DCR=true/" "$ENV_FILE"
    else
        echo "USE_DCR=true" >> "$ENV_FILE"
    fi
    
    if grep -q "^DCR_INITIAL_ACCESS_TOKEN=" "$ENV_FILE"; then
        sed -i.bak "s/^DCR_INITIAL_ACCESS_TOKEN=.*/DCR_INITIAL_ACCESS_TOKEN=${token}/" "$ENV_FILE"
    else
        printf "DCR_INITIAL_ACCESS_TOKEN=%s\n" "${token}" >> "$ENV_FILE"
    fi
    
    # Remove client ID and secret if present
    sed -i.bak '/^KEYCLOAK_CLIENT_ID=/d' "$ENV_FILE"
    sed -i.bak '/^KEYCLOAK_CLIENT_SECRET=/d' "$ENV_FILE"
    
    # Clean up backup files
    rm -f "${ENV_FILE}.bak"
    
    print_success "Environment file updated successfully"
}

# Main function
main() {
    print_info "Setting up Dynamic Client Registration"
    
    # Check if Keycloak is running
    if ! curl -s "${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/.well-known/openid-configuration" > /dev/null 2>&1; then
        print_error "Keycloak is not accessible at ${KEYCLOAK_URL}"
        print_info "Make sure Keycloak is running: docker-compose up -d keycloak"
        exit 1
    fi
    
    # Get admin token
    local admin_token=$(get_admin_token)
    if [[ -z "$admin_token" ]]; then
        exit 1
    fi
    
    # Create initial access token
    local initial_token=$(create_initial_access_token "$admin_token")
    if [[ -z "$initial_token" ]]; then
        exit 1
    fi
    
    print_success "Initial access token created successfully"
    echo
    print_info "Initial Access Token (valid for 1 hour):"
    echo "$initial_token"
    echo
    
    # Ask to update environment file
    if [[ "$AUTO_UPDATE" == "false" ]]; then
        read -p "Update $ENV_FILE with DCR settings? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            update_env_file "$initial_token"
            
            echo
            print_info "Next steps:"
            echo "1. Restart the MCP server: docker-compose restart mcp-server"
            echo "2. The server will automatically register itself using DCR"
            echo "3. Check logs: docker-compose logs mcp-server"
        else
            echo
            print_info "To manually configure DCR, add these to your .env file:"
            echo "USE_DCR=true"
            echo "DCR_INITIAL_ACCESS_TOKEN=${initial_token}"
        fi
    else
        # Auto-update mode
        update_env_file "$initial_token"
        
        echo
        print_info "Environment file updated automatically."
        echo "Next steps:"
        echo "1. Restart the MCP server: docker-compose restart mcp-server"
        echo "2. The server will automatically register itself using DCR"
        echo "3. Check logs: docker-compose logs mcp-server"
    fi
}

# Run main function
main "$@" 