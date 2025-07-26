#!/bin/bash

# Script to set up Docker secrets for production deployment

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common library
source "${SCRIPT_DIR}/common_lib.sh"

# Configuration
SECRETS_DIR="secrets"

# Check for required tools
check_required_tools openssl base64

print_banner "Docker Secrets Setup"

print_info "This script will generate secure secrets for production deployment"
print_warning "Run this only in a secure environment!"
echo

# Create secrets directory
mkdir -p "$SECRETS_DIR"

# Function to generate a secure random secret
generate_secret() {
    openssl rand -hex 32
}

# Function to generate and save a secret
create_secret() {
    local name=$1
    local value=$2
    local file="$SECRETS_DIR/$name"
    
    if [ -f "$file" ]; then
        print_warning "Secret $name already exists. Skipping..."
        return
    fi
    
    echo -n "$value" > "$file"
    chmod 600 "$file"
    print_success "Created secret: $name"
}

# Generate secrets
print_section "Generating Secrets"

print_step 1 "Generating JWT secret key..."
create_secret "jwt_secret_key" "$(generate_secret)"

print_step 2 "Generating database passwords..."
create_secret "postgres_password" "$(generate_secret)"
create_secret "keycloak_db_password" "$(generate_secret)"

print_step 3 "Generating Keycloak admin password..."
create_secret "keycloak_admin_password" "$(generate_secret)"

print_step 4 "Generating MCP client secret..."
create_secret "mcp_client_secret" "$(generate_secret)"

print_step 5 "Generating Redis password..."
create_secret "redis_password" "$(generate_secret)"

# Create Docker Compose override for production
print_section "Creating Production Configuration"

cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  postgres:
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    secrets:
      - postgres_password

  keycloak:
    environment:
      KC_DB_PASSWORD_FILE: /run/secrets/keycloak_db_password
      KEYCLOAK_ADMIN_PASSWORD_FILE: /run/secrets/keycloak_admin_password
    secrets:
      - keycloak_db_password
      - keycloak_admin_password

  redis:
    command: redis-server --requirepass-file /run/secrets/redis_password
    secrets:
      - redis_password

  mcp-server:
    environment:
      JWT_SECRET_KEY_FILE: /run/secrets/jwt_secret_key
      REDIS_PASSWORD_FILE: /run/secrets/redis_password
    secrets:
      - jwt_secret_key
      - redis_password

secrets:
  postgres_password:
    file: ./secrets/postgres_password
  keycloak_db_password:
    file: ./secrets/keycloak_db_password
  keycloak_admin_password:
    file: ./secrets/keycloak_admin_password
  jwt_secret_key:
    file: ./secrets/jwt_secret_key
  redis_password:
    file: ./secrets/redis_password
  mcp_client_secret:
    file: ./secrets/mcp_client_secret
EOF

print_success "Created docker-compose.prod.yml"

# Show summary
print_section "Summary"

print_info "Secrets have been generated in: $SECRETS_DIR/"
print_info "Production config created: docker-compose.prod.yml"
echo
print_warning "IMPORTANT: These secrets are for production use!"
print_warning "1. Store them securely (e.g., in a password manager)"
print_warning "2. Never commit them to version control"
print_warning "3. Set appropriate file permissions (already done)"
print_warning "4. Consider using a proper secret management system"
echo
print_info "To use in production:"
print_info "  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d" 