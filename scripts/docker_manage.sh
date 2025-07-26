#!/bin/bash

# Docker Compose Management Script for MCP Server
# Usage: ./scripts/docker_manage.sh [command]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project name
PROJECT_NAME="demoSecureMCP"

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if docker and docker compose are installed
check_requirements() {
    if ! command -v docker &> /dev/null; then
        print_color $RED "Error: Docker is not installed"
        exit 1
    fi
    
    if ! docker compose version &> /dev/null; then
        print_color $RED "Error: Docker Compose is not installed"
        exit 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start       - Start all services"
    echo "  stop        - Stop all services"
    echo "  restart     - Restart all services"
    echo "  status      - Show status of all services"
    echo "  logs        - Show logs (all services)"
    echo "  logs [svc]  - Show logs for specific service"
    echo "  build       - Build/rebuild all images"
    echo "  clean       - Stop and remove all containers, volumes, and images"
    echo "  reset       - Clean + remove all data (DESTRUCTIVE)"
    echo "  ps          - List running containers"
    echo "  health      - Check health status of all services"
    echo "  shell [svc] - Open shell in service container"
    echo ""
    echo "Services: postgres, keycloak, redis, mcp-server, nginx"
}

# Function to wait for services to be healthy
wait_for_healthy() {
    print_color $YELLOW "Waiting for services to be healthy..."
    
    local max_attempts=60
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        local all_healthy=true
        
        # Check each service health
        for service in postgres keycloak redis mcp-server nginx; do
            if docker compose ps --format json | jq -r ".[] | select(.Service==\"$service\") | .Health" | grep -q "healthy"; then
                echo -n "."
            else
                all_healthy=false
            fi
        done
        
        if [ "$all_healthy" = true ]; then
            print_color $GREEN "\nAll services are healthy!"
            return 0
        fi
        
        attempt=$((attempt + 1))
        sleep 2
    done
    
    print_color $RED "\nTimeout waiting for services to be healthy"
    docker compose ps
    return 1
}

# Main script logic
check_requirements

case "$1" in
    start)
        print_color $BLUE "Starting all services..."
        
        # Check if .env.docker exists
        if [ ! -f .env.docker ]; then
            print_color $YELLOW ".env.docker not found. Creating from .env..."
            if [ -f scripts/create_docker_env.sh ]; then
                ./scripts/create_docker_env.sh
            else
                cp .env .env.docker
                print_color $YELLOW "Warning: Using .env as .env.docker - may need adjustment for Docker networking"
            fi
        fi
        
        docker compose up -d
        wait_for_healthy
        
        print_color $GREEN "\nServices started successfully!"
        print_color $BLUE "\nAccess points:"
        echo "  - MCP API: https://localhost/ (via Nginx)"
        echo "  - Keycloak: http://localhost:8080/"
        echo "  - Health check: https://localhost/health"
        echo "  - OpenAPI docs: https://localhost/docs"
        ;;
        
    stop)
        print_color $BLUE "Stopping all services..."
        docker compose stop
        print_color $GREEN "Services stopped"
        ;;
        
    restart)
        print_color $BLUE "Restarting all services..."
        docker compose restart
        wait_for_healthy
        ;;
        
    status)
        print_color $BLUE "Service status:"
        docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Health}}\t{{.Ports}}"
        ;;
        
    logs)
        if [ -z "$2" ]; then
            docker compose logs -f --tail=100
        else
            docker compose logs -f --tail=100 "$2"
        fi
        ;;
        
    build)
        print_color $BLUE "Building all images..."
        docker compose build --no-cache
        print_color $GREEN "Build complete"
        ;;
        
    clean)
        print_color $YELLOW "This will stop and remove all containers and images. Continue? (y/N)"
        read -r response
        if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            docker compose down --rmi all
            print_color $GREEN "Clean complete"
        else
            print_color $BLUE "Cancelled"
        fi
        ;;
        
    reset)
        print_color $RED "WARNING: This will delete ALL data including databases! Continue? (y/N)"
        read -r response
        if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            docker compose down -v --rmi all
            rm -f .env.docker
            print_color $GREEN "Reset complete"
        else
            print_color $BLUE "Cancelled"
        fi
        ;;
        
    ps)
        docker compose ps
        ;;
        
    health)
        print_color $BLUE "Health check status:"
        echo ""
        
        # Check each service
        for service in postgres keycloak redis mcp-server nginx; do
            health=$(docker compose ps --format json | jq -r ".[] | select(.Service==\"$service\") | .Health" || echo "unknown")
            
            if [[ "$health" == "healthy" ]]; then
                print_color $GREEN "✓ $service: $health"
            elif [[ "$health" == "starting" ]]; then
                print_color $YELLOW "⟳ $service: $health"
            else
                print_color $RED "✗ $service: $health"
            fi
        done
        ;;
        
    shell)
        if [ -z "$2" ]; then
            print_color $RED "Error: Please specify a service name"
            echo "Available services: postgres, keycloak, redis, mcp-server, nginx"
            exit 1
        fi
        
        case "$2" in
            postgres)
                docker compose exec postgres psql -U keycloak
                ;;
            redis)
                docker compose exec redis redis-cli
                ;;
            *)
                docker compose exec "$2" /bin/sh
                ;;
        esac
        ;;
        
    *)
        show_usage
        exit 1
        ;;
esac 