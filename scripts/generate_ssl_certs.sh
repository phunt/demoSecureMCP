#!/bin/bash

# Script to generate self-signed SSL certificates for development

SSL_DIR="nginx/ssl"
DAYS=365
COUNTRY="US"
STATE="California"
LOCALITY="San Francisco"
ORGANIZATION="MCP Development"
ORGANIZATIONAL_UNIT="IT"
COMMON_NAME="localhost"

echo "Generating self-signed SSL certificates for development..."

# Create SSL directory if it doesn't exist
mkdir -p "$SSL_DIR"

# Generate private key
openssl genrsa -out "$SSL_DIR/key.pem" 2048

# Generate certificate signing request
openssl req -new -key "$SSL_DIR/key.pem" -out "$SSL_DIR/csr.pem" \
    -subj "/C=$COUNTRY/ST=$STATE/L=$LOCALITY/O=$ORGANIZATION/OU=$ORGANIZATIONAL_UNIT/CN=$COMMON_NAME"

# Generate self-signed certificate
openssl x509 -req -days $DAYS -in "$SSL_DIR/csr.pem" -signkey "$SSL_DIR/key.pem" -out "$SSL_DIR/cert.pem"

# Create a certificate with Subject Alternative Names for better compatibility
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
openssl req -x509 -nodes -days $DAYS -newkey rsa:2048 \
    -keyout "$SSL_DIR/key.pem" \
    -out "$SSL_DIR/cert.pem" \
    -config "$SSL_DIR/openssl.cnf" \
    -extensions v3_req

# Clean up
rm -f "$SSL_DIR/csr.pem"

# Set appropriate permissions
chmod 600 "$SSL_DIR/key.pem"
chmod 644 "$SSL_DIR/cert.pem"

echo "✅ SSL certificates generated successfully!"
echo "   - Certificate: $SSL_DIR/cert.pem"
echo "   - Private Key: $SSL_DIR/key.pem"
echo ""
echo "⚠️  These are self-signed certificates for development only!"
echo "   Browsers will show a security warning. Add an exception to proceed." 