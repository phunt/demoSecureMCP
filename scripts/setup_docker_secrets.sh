#!/bin/bash

# Script to set up Docker secrets for production deployment

SECRETS_DIR="./secrets"

echo "Setting up Docker secrets directory structure..."

# Create secrets directory
mkdir -p "$SECRETS_DIR"

# Create .gitignore for secrets directory
cat > "$SECRETS_DIR/.gitignore" << 'EOF'
# Ignore all files in this directory
*
# Except this .gitignore file
!.gitignore
!README.md
EOF

# Create README for secrets directory
cat > "$SECRETS_DIR/README.md" << 'EOF'
# Docker Secrets Directory

This directory contains secret files for production deployment.

## Required Secret Files

Create the following files with secure values:

1. **keycloak_client_secret.txt**
   - Contains the Keycloak client secret
   - Generate with: `openssl rand -hex 32`

2. **postgres_password.txt**
   - Contains the PostgreSQL password
   - Generate with: `openssl rand -base64 32`

3. **keycloak_admin_password.txt**
   - Contains the Keycloak admin password
   - Generate with: `openssl rand -base64 32`

4. **redis_password.txt**
   - Contains the Redis password
   - Generate with: `openssl rand -base64 32`

## Security Best Practices

1. **NEVER commit these files to version control**
2. Use strong, randomly generated passwords
3. Set appropriate file permissions (600)
4. Use a secure method to transfer secrets to production
5. Consider using a secrets management service in production

## Example Commands

```bash
# Generate secure passwords
openssl rand -hex 32 > keycloak_client_secret.txt
openssl rand -base64 32 > postgres_password.txt
openssl rand -base64 32 > keycloak_admin_password.txt
openssl rand -base64 32 > redis_password.txt

# Set proper permissions
chmod 600 *.txt
```

## Production Deployment

Use with Docker Compose:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```
EOF

# Generate example secrets for development (not for production use!)
if [ "$1" == "--dev" ]; then
    echo "Generating example secrets for development..."
    echo "dev-keycloak-client-secret" > "$SECRETS_DIR/keycloak_client_secret.txt"
    echo "dev-postgres-password" > "$SECRETS_DIR/postgres_password.txt"
    echo "dev-keycloak-admin-password" > "$SECRETS_DIR/keycloak_admin_password.txt"
    echo "dev-redis-password" > "$SECRETS_DIR/redis_password.txt"
    
    # Set proper permissions
    chmod 600 "$SECRETS_DIR"/*.txt
    
    echo "⚠️  Development secrets created. DO NOT use these in production!"
else
    echo ""
    echo "To generate example secrets for development, run:"
    echo "  $0 --dev"
    echo ""
    echo "For production, generate secure secrets with:"
    echo "  openssl rand -hex 32 > $SECRETS_DIR/keycloak_client_secret.txt"
    echo "  openssl rand -base64 32 > $SECRETS_DIR/postgres_password.txt"
    echo "  openssl rand -base64 32 > $SECRETS_DIR/keycloak_admin_password.txt"
    echo "  openssl rand -base64 32 > $SECRETS_DIR/redis_password.txt"
fi

echo ""
echo "✅ Docker secrets directory structure created at: $SECRETS_DIR"
echo "   See $SECRETS_DIR/README.md for instructions." 