#!/bin/bash

# docker_manage.sh - Docker services management script
# Usage: ./scripts/docker_manage.sh [command] [options]

set -euo pipefail

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common_lib.sh"
source "${SCRIPT_DIR}/context_aware_urls.sh"

# Get project root
PROJECT_ROOT=$(get_project_root)
cd "${PROJECT_ROOT}"

# Script configuration
COMPOSE_FILE="docker-compose.yml"
SERVICES=("postgres" "keycloak" "redis" "mcp-server" "nginx")

# Help text
show_help() {
    cat << EOF
Docker Services Management Script

Usage: ${0##*/} COMMAND [OPTIONS]

Commands:
    start       Start all services
    stop        Stop all services  
    restart     Restart all services
    down        Stop and remove all containers
    status      Show service status
    logs        Show service logs
    clean       Clean up volumes and images
    dev         Development mode (with logs)
    prod        Production mode (with docker-compose.prod.yml)
    build       Build/rebuild services
    health      Check service health
    shell       Enter a service container
    
Options:
    -h, --help  Show this help message
    -f          Follow logs (with 'logs' command)
    -v          Verbose output
    
Examples:
    ${0##*/} start              # Start all services
    ${0##*/} logs -f            # Follow all logs
    ${0##*/} logs mcp-server -f # Follow specific service logs
    ${0##*/} shell mcp-server   # Enter MCP server container
    ${0##*/} clean              # Clean everything

EOF
}

# Check if Docker is running
check_docker() {
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
}

# Wait for services to be healthy
wait_for_healthy() {
    print_info "Waiting for services to be healthy..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        local all_healthy=true
        
        for service in "${SERVICES[@]}"; do
            if ! docker compose ps --format json | jq -r ".[] | select(.Service == \"$service\") | .Health" | grep -q "healthy\|running"; then
                all_healthy=false
                break
            fi
        done
        
        if [ "$all_healthy" = true ]; then
            print_success "All services are healthy!"
            return 0
        fi
        
        printf "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "Services did not become healthy in time"
    docker compose ps
    return 1
}

# Main command processing
main() {
    check_docker
    
    case "${1:-}" in
    start)
        print_color $BLUE "Starting all services..."
        
        # Load environment if .env file exists
        if [ -f .env ]; then
            print_info "Loading environment from .env file..."
            set -a
            source .env
            set +a
        fi
        
        docker compose up -d
        wait_for_healthy
        
        print_success "\nServices started successfully!"
        print_color $BLUE "\nAccess points:"
        echo "  - MCP API: https://localhost/ (via Nginx)"
        echo "  - Keycloak: http://localhost:8080/"
        echo "  - Health check: https://localhost/health"
        echo "  - OpenAPI docs: https://localhost/docs"
        
        # Show context information
        print_context_info
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
        print_success "Services restarted"
        ;;
        
    down)
        print_color $BLUE "Stopping and removing containers..."
        docker compose down
        print_success "Containers removed"
        ;;
        
    status)
        print_color $BLUE "Service Status:"
        docker compose ps
        ;;
        
    logs)
        shift
        if [[ "${1:-}" == "-f" ]] || [[ "${2:-}" == "-f" ]]; then
            docker compose logs -f ${1:-} | grep -v "^$"
        else
            docker compose logs ${1:-} | tail -100
        fi
        ;;
        
    clean)
        print_warning "This will remove all containers, volumes, and images!"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Cleaning up..."
            docker compose down -v --remove-orphans
            docker image prune -af --filter "label=com.docker.compose.project=${PWD##*/}"
            print_success "Cleanup complete"
        fi
        ;;
        
    dev)
        print_color $BLUE "Starting in development mode..."
        
        # Load environment if .env file exists
        if [ -f .env ]; then
            set -a
            source .env
            set +a
        fi
        
        docker compose up
        ;;
        
    prod)
        print_color $BLUE "Starting in production mode..."
        
        # Check for production environment file
        if [ -f .env.prod ]; then
            print_info "Loading production environment..."
            set -a
            source .env.prod
            set +a
        fi
        
        docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
        wait_for_healthy
        print_success "Production services started"
        ;;
        
    build)
        print_color $BLUE "Building services..."
        docker compose build ${2:-}
        print_success "Build complete"
        ;;
        
    health)
        print_color $BLUE "Health Check Results:"
        for service in "${SERVICES[@]}"; do
            echo -n "  $service: "
            health=$(docker compose ps --format json | jq -r ".[] | select(.Service == \"$service\") | .Health")
            case "$health" in
                "healthy") print_color $GREEN "HEALTHY" ;;
                "running") print_color $YELLOW "RUNNING (no health check)" ;;
                *) print_color $RED "UNHEALTHY" ;;
            esac
        done
        ;;
        
    shell)
        service="${2:-mcp-server}"
        print_info "Entering $service container..."
        docker compose exec $service /bin/sh
        ;;
        
    -h|--help|help)
        show_help
        ;;
        
    *)
        print_error "Unknown command: ${1:-}"
        show_help
        exit 1
        ;;
    esac
}

# Run main function
main "$@" 