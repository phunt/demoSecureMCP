#!/bin/bash

# Script to generate self-signed SSL certificates for development

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common library
source "${SCRIPT_DIR}/common_lib.sh"

# Configuration
SSL_DIR="nginx/ssl"
DAYS=365
COUNTRY="US"
STATE="California"
LOCALITY="San Francisco"
ORGANIZATION="MCP Development"
ORGANIZATIONAL_UNIT="IT"
COMMON_NAME="localhost"

# Check for required tools
check_required_tools openssl

print_info "Generating self-signed SSL certificates for development..."

# Create SSL directory if it doesn't exist
mkdir -p "$SSL_DIR"

# Generate private key
print_step 1 "Generating private key..."
openssl genrsa -out "$SSL_DIR/key.pem" 2048 || die "Failed to generate private key"

# Generate certificate signing request
print_step 2 "Generating certificate signing request..."
openssl req -new -key "$SSL_DIR/key.pem" -out "$SSL_DIR/csr.pem" \
    -subj "/C=$COUNTRY/ST=$STATE/L=$LOCALITY/O=$ORGANIZATION/OU=$ORGANIZATIONAL_UNIT/CN=$COMMON_NAME" \
    || die "Failed to generate CSR"

# Create a certificate with Subject Alternative Names for better compatibility
print_step 3 "Creating OpenSSL configuration..."
cat > "$SSL_DIR/openssl.cnf" << EOF
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
C = $COUNTRY
ST = $STATE
L = $LOCALITY
O = $ORGANIZATION
OU = $ORGANIZATIONAL_UNIT
CN = $COMMON_NAME

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = mcp-server.local
DNS.3 = *.mcp-server.local
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

# Generate new certificate with SAN
print_step 4 "Generating self-signed certificate with Subject Alternative Names..."
openssl req -x509 -nodes -days $DAYS -newkey rsa:2048 \
    -keyout "$SSL_DIR/key.pem" \
    -out "$SSL_DIR/cert.pem" \
    -config "$SSL_DIR/openssl.cnf" \
    -extensions v3_req \
    || die "Failed to generate certificate"

# Clean up
rm -f "$SSL_DIR/csr.pem"

# Set appropriate permissions
chmod 600 "$SSL_DIR/key.pem" || die "Failed to set key permissions"
chmod 644 "$SSL_DIR/cert.pem" || die "Failed to set certificate permissions"

print_success "SSL certificates generated successfully!"
print_info "   Certificate: $SSL_DIR/cert.pem"
print_info "   Private Key: $SSL_DIR/key.pem"
echo
print_warning "These are self-signed certificates for development only!"
print_warning "Browsers will show a security warning. Add an exception to proceed." 