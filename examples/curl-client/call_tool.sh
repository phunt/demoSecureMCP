#!/bin/bash

# call_tool.sh - Call MCP server tools with proper authentication
# This script demonstrates how to interact with the secure MCP server tools

set -euo pipefail

# Default values
MCP_SERVER_URL="${MCP_SERVER_URL:-https://localhost}"
ACCESS_TOKEN="${ACCESS_TOKEN:-}"
TOKEN_FILE="${TOKEN_FILE:-/tmp/mcp_access_token}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_response() {
    echo -e "${BLUE}[RESPONSE]${NC} $1"
}

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS] TOOL [ARGS...]

Call MCP server tools with authentication.

TOOLS:
  echo TEXT                 Echo the provided text (requires mcp:read)
  timestamp                 Get current timestamp (requires mcp:read)  
  calculate OPERATION NUM1 [NUM2...]
                          Calculate using operation: add, subtract, multiply, 
                          divide, power, sqrt, factorial (requires mcp:write)
                          Examples: 
                            calculate add 10 20 30
                            calculate multiply 5 4
                            calculate sqrt 16
  discover                 List available tools (requires authentication)

OPTIONS:
  -h, --help              Show this help message
  -t, --token TOKEN       Use specified access token
  -f, --token-file FILE   Read token from file (default: ${TOKEN_FILE})
  -u, --url URL          MCP server URL (default: ${MCP_SERVER_URL})
  -k, --insecure         Allow insecure SSL connections (for self-signed certs)
  -v, --verbose          Show verbose output including headers

EXAMPLES:
  # Echo tool
  $0 echo "Hello, MCP Server!"
  
  # Timestamp tool
  $0 timestamp
  
  # Calculate tool
  $0 calculate add 10 20 30
  $0 calculate multiply 5 4
  $0 calculate sqrt 16
  
  # With custom token
  $0 -t "your-jwt-token" echo "Authenticated message"
  
  # Using token from file
  SAVE_TOKEN=true ./get_token.sh
  $0 -f /tmp/mcp_access_token timestamp

EOF
}

# Parse command line arguments
VERBOSE=false
INSECURE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -t|--token)
            ACCESS_TOKEN="$2"
            shift 2
            ;;
        -f|--token-file)
            TOKEN_FILE="$2"
            shift 2
            ;;
        -u|--url)
            MCP_SERVER_URL="$2"
            shift 2
            ;;
        -k|--insecure)
            INSECURE="-k"
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            break
            ;;
    esac
done

# Check if tool is specified
if [ $# -eq 0 ]; then
    print_error "No tool specified"
    echo
    usage
    exit 1
fi

TOOL="$1"
shift

# Get access token if not provided
if [ -z "${ACCESS_TOKEN}" ]; then
    if [ -f "${TOKEN_FILE}" ]; then
        print_info "Reading token from ${TOKEN_FILE}"
        ACCESS_TOKEN=$(cat "${TOKEN_FILE}")
    else
        print_error "No access token provided. Please either:"
        print_error "  1. Set ACCESS_TOKEN environment variable"
        print_error "  2. Use -t option to provide token"
        print_error "  3. Run: SAVE_TOKEN=true ./get_token.sh"
        exit 1
    fi
fi

# Verify token format (basic check)
if ! echo "${ACCESS_TOKEN}" | grep -E -q "^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$"; then
    print_warning "Token doesn't appear to be a valid JWT format"
fi

# Common curl options
CURL_OPTS="-s ${INSECURE}"
if [ "${VERBOSE}" = true ]; then
    CURL_OPTS="${CURL_OPTS} -v"
fi

# Function to make authenticated request
make_request() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    
    if [ -n "${data}" ]; then
        curl ${CURL_OPTS} -X "${method}" \
            -H "Authorization: Bearer ${ACCESS_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "${data}" \
            "${MCP_SERVER_URL}${endpoint}"
    else
        curl ${CURL_OPTS} -X "${method}" \
            -H "Authorization: Bearer ${ACCESS_TOKEN}" \
            "${MCP_SERVER_URL}${endpoint}"
    fi
}

# Function to handle and display response
handle_response() {
    local response="$1"
    local tool="$2"
    
    # Check if response is valid JSON
    if echo "${response}" | jq . > /dev/null 2>&1; then
        # Check for error response
        if echo "${response}" | jq -e '.detail' > /dev/null 2>&1; then
            print_error "Server returned an error:"
            echo "${response}" | jq -r '.detail'
            
            # Check for specific auth errors
            local status_code=$(echo "${response}" | jq -r '.status_code // 0')
            case ${status_code} in
                401)
                    print_error "Authentication failed. Token may be expired or invalid."
                    print_info "Try getting a new token: ./get_token.sh"
                    ;;
                403)
                    print_error "Authorization failed. Token lacks required scope for this tool."
                    ;;
            esac
            return 1
        else
            # Success response
            print_info "Tool '${tool}' executed successfully!"
            print_response "$(echo "${response}" | jq .)"
            return 0
        fi
    else
        print_error "Invalid response from server:"
        echo "${response}"
        return 1
    fi
}

# Execute tool based on command
case "${TOOL}" in
    echo)
        if [ $# -eq 0 ]; then
            print_error "Echo tool requires text argument"
            exit 1
        fi
        TEXT="$*"
        print_info "Calling echo tool with text: ${TEXT}"
        
        RESPONSE=$(make_request "POST" "/api/v1/tools/echo" "{\"message\": \"${TEXT}\"}")
        handle_response "${RESPONSE}" "echo"
        ;;
        
    timestamp)
        print_info "Calling timestamp tool..."
        
        RESPONSE=$(make_request "POST" "/api/v1/tools/timestamp" "{}")
        handle_response "${RESPONSE}" "timestamp"
        ;;
        
    calculate)
        if [ $# -lt 2 ]; then
            print_error "Calculate tool requires operation and at least one operand"
            print_error "Usage: calculate OPERATION NUM1 [NUM2...]"
            print_error "Operations: add, subtract, multiply, divide, power, sqrt, factorial"
            exit 1
        fi
        OPERATION="$1"
        shift
        
        # Build operands array
        OPERANDS="["
        FIRST=true
        for NUM in "$@"; do
            if [ "$FIRST" = true ]; then
                OPERANDS="${OPERANDS}${NUM}"
                FIRST=false
            else
                OPERANDS="${OPERANDS},${NUM}"
            fi
        done
        OPERANDS="${OPERANDS}]"
        
        print_info "Calling calculate tool: ${OPERATION} with operands ${OPERANDS}"
        
        RESPONSE=$(make_request "POST" "/api/v1/tools/calculate" "{\"operation\": \"${OPERATION}\", \"operands\": ${OPERANDS}}")
        handle_response "${RESPONSE}" "calculate"
        ;;
        
    discover)
        print_info "Discovering available tools..."
        
        RESPONSE=$(make_request "GET" "/api/v1/tools" "")
        handle_response "${RESPONSE}" "discover"
        ;;
        
    *)
        print_error "Unknown tool: ${TOOL}"
        echo
        print_info "Available tools:"
        print_info "  echo       - Echo text (requires mcp:read)"
        print_info "  timestamp  - Get current time (requires mcp:read)"
        print_info "  calculate  - Calculate expression (requires mcp:write)"
        print_info "  discover   - List all available tools"
        exit 1
        ;;
esac 