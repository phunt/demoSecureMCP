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
