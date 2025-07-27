# Docker Compose Configuration

This document describes the Docker Compose setup for the Secure MCP Server project.

## Overview

The project uses Docker Compose to orchestrate multiple services:

- **MCP Server**: FastAPI application serving the MCP API
- **Keycloak**: Identity and Access Management for OAuth 2.1/OIDC
- **PostgreSQL**: Database backend for Keycloak
- **Redis**: Cache for JWKS and session data
- **Nginx**: Reverse proxy with SSL/TLS termination

## Quick Start

```bash
# Start all services
./scripts/docker_manage.sh start

# Check service health
./scripts/docker_manage.sh health

# View logs
./scripts/docker_manage.sh logs

# Stop all services
./scripts/docker_manage.sh stop
```

## Service Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│    Nginx    │────▶│  MCP Server │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                     │
                           │                     ▼
                           │              ┌─────────────┐
                           │              │    Redis    │
                           │              └─────────────┘
                           │                     │
                           ▼                     ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  Keycloak   │────▶│ PostgreSQL  │
                    └─────────────┘     └─────────────┘
```

## Services

### MCP Server

- **Container**: `mcp-server`
- **Image**: Built from `Dockerfile` (dev) or `Dockerfile.prod` (production)
- **Port**: 8000 (internal only, exposed via Nginx)
- **Health Check**: `GET /health`
- **Dependencies**: Keycloak (healthy), Redis (healthy)
- **Volumes**:
  - `./src:/app/src` - Source code (read-write in dev, read-only in prod)
  - `mcp_logs:/app/logs` - Application logs

### Keycloak

- **Container**: `mcp-keycloak`
- **Image**: `quay.io/keycloak/keycloak:26.0`
- **Port**: 8080
- **Health Check**: `GET /health/ready`
- **Dependencies**: PostgreSQL (healthy)
- **Volumes**:
  - `./keycloak/realm-export.json` - Realm configuration
  - `keycloak_data:/opt/keycloak/data` - Keycloak data

### PostgreSQL

- **Container**: `mcp-postgres`
- **Image**: `postgres:17-alpine`
- **Port**: 5432 (development only)
- **Health Check**: `pg_isready`
- **Volumes**:
  - `postgres_data:/var/lib/postgresql/data` - Database files

### Redis

- **Container**: `mcp-redis`
- **Image**: `redis:7.4-alpine`
- **Port**: 6379 (development only)
- **Health Check**: `redis-cli ping`
- **Configuration**: 256MB memory limit with LRU eviction
- **Volumes**:
  - `redis_data:/data` - Persistent data

### Nginx

- **Container**: `mcp-nginx`
- **Image**: `nginx:1.27-alpine`
- **Ports**: 80 (HTTP), 443 (HTTPS)
- **Health Check**: `GET /health`
- **Dependencies**: MCP Server (healthy)
- **Volumes**:
  - `./nginx/conf.d` - Nginx configuration
  - `./nginx/ssl` - SSL certificates
  - `nginx_logs:/var/log/nginx` - Access/error logs

## Network Configuration

All services communicate on a custom bridge network:

- **Network Name**: `mcp-network`
- **Subnet**: `172.20.0.0/16`
- **Bridge Name**: `mcp_bridge`

Services can reach each other using their container names as hostnames.

## Volume Management

| Volume | Purpose | Persistence |
|--------|---------|-------------|
| `postgres_data` | PostgreSQL database | Persistent |
| `redis_data` | Redis cache data | Persistent |
| `keycloak_data` | Keycloak configuration | Persistent |
| `nginx_logs` | Nginx access/error logs | Persistent |
| `mcp_logs` | Application logs | Persistent |

## Environment Variables

The following environment files are used:

- `.env` - Local development
- `.env.docker` - Docker Compose configuration
- `.env.example` - Template with all available variables

Key variables for Docker:

```env
# Keycloak connection (use container names)
KEYCLOAK_URL=http://keycloak:8080
OAUTH_ISSUER=http://keycloak:8080/realms/mcp-realm

# Redis connection
REDIS_URL=redis://redis:6379/0

# Dynamic Client Registration (optional)
USE_DCR=true
DCR_INITIAL_ACCESS_TOKEN=your-token-here

# OR static credentials (if DCR disabled)
# KEYCLOAK_CLIENT_ID=mcp-server
# KEYCLOAK_CLIENT_SECRET=your-secret
```

### Dynamic Client Registration in Docker

When using DCR in Docker environments:

1. **Generate tokens from inside container**:
   ```bash
   docker cp scripts/setup_dcr_docker.sh mcp-server:/tmp/
   docker compose exec mcp-server sh /tmp/setup_dcr_docker.sh
   ```
   This ensures the token has the correct issuer URL (`http://keycloak:8080`).

2. **Use the auto-update option**:
   ```bash
   ./scripts/setup_dcr.sh --auto-update
   ```
   This avoids interactive prompts that can hang in CI/CD pipelines.

3. **Token whitespace handling**: The DCR client automatically strips whitespace from tokens to handle Docker Compose environment variable behavior.

## Management Commands

The `scripts/docker_manage.sh` script provides convenient commands:

| Command | Description |
|---------|-------------|
| `start` | Start all services and wait for health |
| `stop` | Stop all services gracefully |
| `restart` | Restart all services |
| `status` | Show service status and health |
| `logs [service]` | View logs (all or specific service) |
| `build` | Build/rebuild all images |
| `clean` | Remove containers and images |
| `reset` | Remove everything including volumes |
| `ps` | List running containers |
| `health` | Check health status |
| `shell <service>` | Open shell in service |

## Health Checks

All services implement health checks:

- **Startup Period**: Time allowed for initial startup
- **Interval**: How often to check health
- **Timeout**: Maximum time for health check
- **Retries**: Failed checks before marking unhealthy

## Restart Policies

All services use `restart: unless-stopped`:
- Automatically restart on failure
- Do not restart if manually stopped
- Restart on Docker daemon restart

## Development Workflow

1. **Initial Setup**:
   ```bash
   # Generate SSL certificates
   ./scripts/generate_ssl_certs.sh
   
   # Start services
   ./scripts/docker_manage.sh start
   ```

2. **Development**:
   - Source code is mounted with hot-reload
   - All ports exposed for debugging
   - Debug logging enabled

3. **Testing**:
   ```bash
   # View logs
   ./scripts/docker_manage.sh logs mcp-server
   
   # Access shell
   ./scripts/docker_manage.sh shell mcp-server
   ```

## Production Deployment

1. **Prepare secrets**:
   ```bash
   ./scripts/setup_docker_secrets.sh
   ```

2. **Deploy with production config**:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

3. **Monitor**:
   ```bash
   docker compose logs -f
   ```

## Troubleshooting

### Services Not Starting

```bash
# Check status
./scripts/docker_manage.sh status

# View detailed logs
docker compose logs <service-name>
```

### Health Check Failures

```bash
# Check health status
./scripts/docker_manage.sh health

# Inspect container
docker inspect mcp-<service-name> | jq '.[0].State.Health'
```

### Network Issues

```bash
# Test internal connectivity
docker compose exec mcp-server ping keycloak
docker compose exec mcp-server curl http://keycloak:8080/health
```

### Clean Start

```bash
# Remove everything and start fresh
./scripts/docker_manage.sh reset
./scripts/docker_manage.sh start
```

## Security Considerations

1. **Development**:
   - Self-signed certificates for HTTPS
   - Ports exposed for debugging
   - Default passwords (change in production!)

2. **Production**:
   - Use Docker secrets for sensitive data
   - No ports exposed except Nginx 80/443
   - Enable firewall rules
   - Use proper SSL certificates
   - Change all default passwords

## Performance Tuning

1. **MCP Server**:
   - Adjust `WORKERS` based on CPU cores
   - Configure connection pools

2. **Redis**:
   - Tune `maxmemory` based on available RAM
   - Monitor eviction metrics

3. **PostgreSQL**:
   - Tune `shared_buffers` and `work_mem`
   - Regular vacuum and analyze

4. **Nginx**:
   - Enable caching for static assets
   - Configure rate limiting
   - Tune worker processes 