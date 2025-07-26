#!/bin/bash

# call_tool.sh - Call MCP server tools with authentication

set -euo pipefail

# Source common library
source "$(dirname "$0")/common.sh"

# Initialize client
init_client

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] TOOL [ARGS...]"
    echo ""
    echo "Tools:"
    echo "  echo MESSAGE      - Echo a message back"
    echo "  timestamp         - Get current server timestamp"
    echo "  calculate OP ARGS - Perform calculation (add|subtract|multiply|divide)"
    echo "  discover          - Discover available tools"
    echo ""
    echo "Options:"
    echo "  -t TOKEN          - Use specific access token"
    echo "  -f FILE           - Read token from file (default: $TOKEN_FILE)"
    echo "  -k                - Skip SSL certificate verification"
    echo "  -v                - Verbose output"
    echo ""
    echo "Examples:"
    echo "  $0 echo 'Hello, World!'"
    echo "  $0 timestamp"
    echo "  $0 calculate add 10 20 30"
    echo "  $0 -v discover"
    echo ""
    echo "Environment Variables:"
    echo "  ACCESS_TOKEN      - OAuth access token"
    echo "  MCP_SERVER_URL    - MCP server URL (default: https://localhost, current: $MCP_SERVER_URL)"
}

# Parse command line options
VERBOSE=false
SKIP_SSL=""
USE_TOKEN=""
USE_TOKEN_FILE="$TOKEN_FILE"

while getopts "t:f:kvh" opt; do
    case $opt in
        t)
            USE_TOKEN="$OPTARG"
            ;;
        f)
            USE_TOKEN_FILE="$OPTARG"
            ;;
        k)
            SKIP_SSL="-k"
            ;;
        v)
            VERBOSE=true
            export DEBUG=true
            ;;
        h)
            show_usage
            exit 0
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
done

shift $((OPTIND-1))

# Check if tool was specified
if [ $# -eq 0 ]; then
    print_error "No tool specified"
    show_usage
    exit 1
fi

TOOL="$1"
shift

# Get access token
if [ -n "$USE_TOKEN" ]; then
    ACCESS_TOKEN="$USE_TOKEN"
else
    if ACCESS_TOKEN=$(check_access_token "$USE_TOKEN_FILE"); then
        : # Token found successfully
    else
        print_error "No access token found"
        print_info "Run: SAVE_TOKEN=true ./get_token.sh"
        exit 1
    fi
fi

# Validate token format
if ! validate_jwt_format "$ACCESS_TOKEN"; then
    print_error "Invalid JWT token format"
    exit 1
fi

# Check if token is expired
if is_token_expired "$ACCESS_TOKEN"; then
    print_warning "Token appears to be expired. You may need to get a new token."
fi

# Function to call a tool
call_tool() {
    local endpoint="$1"
    local method="$2"
    local data="$3"
    
    print_debug "Calling: $method $endpoint"
    [ -n "$data" ] && print_debug "Data: $data"
    
    local response=$(make_authenticated_request "$method" "$endpoint" "$data" "$ACCESS_TOKEN")
    local status=$?
    
    if [ $status -ne 0 ]; then
        print_error "Request failed"
        return 1
    fi
    
    # Check if response is JSON
    if echo "$response" | jq . >/dev/null 2>&1; then
        echo "$response" | jq .
    else
        echo "$response"
    fi
    
    return 0
}

# Execute tool based on selection
case "$TOOL" in
    echo)
        if [ $# -eq 0 ]; then
            print_error "Echo requires a message"
            exit 1
        fi
        
        MESSAGE="$*"
        DATA=$(jq -n --arg msg "$MESSAGE" '{"message": $msg}')
        call_tool "${MCP_SERVER_URL}/api/v1/tools/echo" "POST" "$DATA"
        ;;
        
    timestamp)
        call_tool "${MCP_SERVER_URL}/api/v1/tools/timestamp" "POST" "{}"
        ;;
        
    calculate)
        if [ $# -lt 2 ]; then
            print_error "Calculate requires operation and at least one operand"
            print_info "Usage: calculate OPERATION NUM1 [NUM2...]"
            print_info "Operations: add, subtract, multiply, divide"
            exit 1
        fi
        
        OPERATION="$1"
        shift
        
        # Validate operation
        case "$OPERATION" in
            add|subtract|multiply|divide)
                ;;
            *)
                print_error "Invalid operation: $OPERATION"
                print_info "Valid operations: add, subtract, multiply, divide"
                exit 1
                ;;
        esac
        
        # Build operands array
        OPERANDS=$(printf '%s\n' "$@" | jq -R . | jq -s .)
        DATA=$(jq -n --arg op "$OPERATION" --argjson operands "$OPERANDS" '{"operation": $op, "operands": $operands}')
        
        call_tool "${MCP_SERVER_URL}/api/v1/tools/calculate" "POST" "$DATA"
        ;;
        
    discover)
        call_tool "${MCP_SERVER_URL}/api/v1/tools" "GET" ""
        ;;
        
    *)
        print_error "Unknown tool: $TOOL"
        print_info "Available tools: echo, timestamp, calculate, discover"
        exit 1
        ;;
esac 