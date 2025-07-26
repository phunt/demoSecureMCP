#!/bin/bash

# common_lib.sh - Common functions and variables for all shell scripts
# Source this file in other scripts: source "$(dirname "$0")/../scripts/common_lib.sh"

# Color codes for output
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export CYAN='\033[0;36m'
export MAGENTA='\033[0;35m'
export NC='\033[0m' # No Color

# Common error handling
# Don't set these here - let the calling script decide
# set -euo pipefail

# Get the absolute path of the script directory
get_script_dir() {
    echo "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
}

# Print functions with consistent formatting
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_debug() {
    if [ "${DEBUG:-false}" = "true" ]; then
        echo -e "${CYAN}[DEBUG]${NC} $1" >&2
    fi
}

print_section() {
    echo
    echo -e "${CYAN}==== $1 ====${NC}"
    echo
}

print_step() {
    echo -e "${YELLOW}[STEP $1]${NC} $2"
}

print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check for required tools and exit if any are missing
check_required_tools() {
    local tools=("$@")
    local missing_tools=()
    
    for tool in "${tools[@]}"; do
        if ! command_exists "${tool}"; then
            missing_tools+=("${tool}")
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_info "Please install the missing tools and try again."
        exit 1
    fi
}

# Validate environment variable is set and not empty
require_env_var() {
    local var_name=$1
    local var_value="${!var_name:-}"
    
    if [ -z "${var_value}" ]; then
        print_error "Required environment variable ${var_name} is not set"
        exit 1
    fi
}

# Set default value for environment variable if not set
set_default_env() {
    local var_name=$1
    local default_value=$2
    
    if [ -z "${!var_name:-}" ]; then
        export "${var_name}=${default_value}"
    fi
}

# Exit with error message
die() {
    print_error "$1"
    exit "${2:-1}"
}

# Show a spinner while a command runs in the background
show_spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    
    while [ "$(ps a | awk '{print $1}' | grep ${pid})" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

# Retry a command with exponential backoff
retry_with_backoff() {
    local max_attempts="${1}"
    local delay="${2}"
    local command="${3}"
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if eval "${command}"; then
            return 0
        fi
        
        if [ $attempt -lt $max_attempts ]; then
            print_warning "Command failed, attempt ${attempt}/${max_attempts}. Retrying in ${delay}s..."
            sleep "${delay}"
            delay=$((delay * 2))
        fi
        
        attempt=$((attempt + 1))
    done
    
    return 1
}

# Check if running in CI environment
is_ci() {
    [ "${CI:-false}" = "true" ] || [ "${CONTINUOUS_INTEGRATION:-false}" = "true" ] || [ -n "${GITHUB_ACTIONS:-}" ]
}

# Get project root directory (looks for docker-compose.yml)
get_project_root() {
    local current_dir="$(pwd)"
    
    while [ "${current_dir}" != "/" ]; do
        if [ -f "${current_dir}/docker-compose.yml" ]; then
            echo "${current_dir}"
            return 0
        fi
        current_dir="$(dirname "${current_dir}")"
    done
    
    print_error "Could not find project root (no docker-compose.yml found)"
    return 1
}

# Common banner for scripts
print_banner() {
    local title="${1:-MCP Server}"
    echo -e "${BLUE}"
    cat << 'EOF'
  __  __  ____ ____    ____                           
 |  \/  |/ ___|  _ \  / ___|  ___ _ ____   _____ _ __ 
 | |\/| | |   | |_) | \___ \ / _ \ '__\ \ / / _ \ '__|
 | |  | | |___|  __/   ___) |  __/ |   \ V /  __/ |   
 |_|  |_|\____|_|     |____/ \___|_|    \_/ \___|_|   
                                                      
EOF
    echo -e "                ${title}${NC}"
    echo
}

# Validate URL format
is_valid_url() {
    local url=$1
    local url_regex='^https?://[-A-Za-z0-9\+&@#/%?=~_|!:,.;]*[-A-Za-z0-9\+&@#/%=~_|]$'
    
    if [[ $url =~ $url_regex ]]; then
        return 0
    else
        return 1
    fi
}

# Check if a port is open
is_port_open() {
    local host=$1
    local port=$2
    local timeout=${3:-5}
    
    if command_exists nc; then
        nc -z -w "${timeout}" "${host}" "${port}" &> /dev/null
    elif command_exists timeout; then
        timeout "${timeout}" bash -c "echo >/dev/tcp/${host}/${port}" &> /dev/null
    else
        # Fallback to basic bash tcp check
        (echo >/dev/tcp/"${host}"/"${port}") &> /dev/null
    fi
}

# Wait for a service to be available
wait_for_service() {
    local name=$1
    local host=$2
    local port=$3
    local max_wait=${4:-60}
    local elapsed=0
    
    print_info "Waiting for ${name} to be available at ${host}:${port}..."
    
    while ! is_port_open "${host}" "${port}" 1; do
        if [ $elapsed -ge $max_wait ]; then
            print_error "${name} did not become available within ${max_wait} seconds"
            return 1
        fi
        
        printf "."
        sleep 1
        elapsed=$((elapsed + 1))
    done
    
    echo
    print_success "${name} is available!"
    return 0
}

# Export functions so they're available in subshells
export -f print_info print_error print_warning print_success print_debug
export -f command_exists die is_ci get_project_root 