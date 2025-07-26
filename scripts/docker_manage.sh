#!/bin/bash

# Docker Compose Management Script for MCP Server
# Usage: ./scripts/docker_manage.sh [command]

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common library
source "${SCRIPT_DIR}/common_lib.sh"

# Project name
PROJECT_NAME="demoSecureMCP"

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
    print_info "Waiting for services to be healthy..."
    
    local max_wait=120
    local elapsed=0
    
    while [ $elapsed -lt $max_wait ]; do
        # Check if all services are healthy
        local unhealthy=$(docker compose ps --format json | jq -r 'select(.Health != "healthy" and .Health != "" and .Health != null) | .Service' | wc -l | xargs)
        
        if [ "$unhealthy" -eq "0" ]; then
            print_success "All services are healthy!"
            return 0
        fi
        
        printf "."
        sleep 2
        elapsed=$((elapsed + 2))
    done
    
    echo
    print_warning "Some services may not be healthy yet. Showing current status:"
    docker compose ps
    return 1
}

# Function to show health status
show_health_status() {
    print_info "Health check status:"
    echo
    
    # Get all services
    local services=$(docker compose ps --format json | jq -r '.Service' | sort)
    
    for service in $services; do
        local health=$(docker compose ps --format json | jq -r --arg svc "$service" 'select(.Service == $svc) | .Health' | head -n1)
        
        if [ -z "$health" ]; then
            health="not found"
        fi
        
        case "$health" in
            "healthy")
                echo -e "${GREEN}✓${NC} ${service}: ${GREEN}${health}${NC}"
                ;;
            "starting")
                echo -e "${YELLOW}⟳${NC} ${service}: ${YELLOW}${health}${NC}"
                ;;
            "unhealthy"|"not found")
                echo -e "${RED}✗${NC} ${service}: ${RED}${health}${NC}"
                ;;
            *)
                echo -e "${BLUE}-${NC} ${service}: ${BLUE}no health check${NC}"
                ;;
        esac
    done
}

# Check requirements
check_required_tools docker

# Main script logic
case "$1" in
    start)
        print_color $BLUE "Starting all services..."
        
        # Check if .env.docker exists
        if [ ! -f .env.docker ]; then
            print_warning ".env.docker not found. Creating from .env..."
            if [ -f scripts/create_docker_env.sh ]; then
                ./scripts/create_docker_env.sh
            else
                cp .env .env.docker
                print_warning "Using .env as .env.docker - may need adjustment for Docker networking"
            fi
        fi
        
        docker compose up -d
        wait_for_healthy
        
        print_success "\nServices started successfully!"
        print_color $BLUE "\nAccess points:"
        echo "  - MCP API: https://localhost/ (via Nginx)"
        echo "  - Keycloak: http://localhost:8080/"
        echo "  - Health check: https://localhost/health"
        echo "  - OpenAPI docs: https://localhost/docs"
        ;;
        
    stop)
        print_color $BLUE "Stopping all services..."
        docker compose stop
        print_success "Services stopped"
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
        print_success "Build complete"
        ;;
        
    clean)
        print_warning "This will stop and remove all containers, networks, and volumes!"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_color $BLUE "Cleaning up..."
            docker compose down -v --remove-orphans
            docker compose rm -f
            print_success "Cleanup complete"
        else
            print_info "Cleanup cancelled"
        fi
        ;;
        
    reset)
        print_warning "This will DESTROY all data including databases!"
        read -p "Are you absolutely sure? (type 'yes' to confirm) " -r
        if [ "$REPLY" = "yes" ]; then
            print_color $RED "Resetting everything..."
            docker compose down -v --remove-orphans --rmi all
            rm -f .env.docker
            print_success "Reset complete. Run './scripts/docker_manage.sh start' to begin fresh."
        else
            print_info "Reset cancelled"
        fi
        ;;
        
    ps)
        docker compose ps
        ;;
        
    health)
        show_health_status
        ;;
        
    shell)
        if [ -z "$2" ]; then
            print_error "Please specify a service name"
            echo "Available services: postgres, keycloak, redis, mcp-server, nginx"
            exit 1
        fi
        
        print_info "Opening shell in $2 container..."
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
        if [ -n "$1" ]; then
            print_error "Unknown command: $1"
        fi
        show_usage
        exit 1
        ;;
esac 