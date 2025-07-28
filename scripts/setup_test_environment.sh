#!/bin/bash
set -e

echo "Setting up test environment..."

# Create test-results directory if it doesn't exist
mkdir -p test-results

# Create subdirectories for organized outputs
mkdir -p test-results/coverage-html
mkdir -p test-results/logs

# Set permissions
chmod 755 test-results
chmod 755 test-results/coverage-html
chmod 755 test-results/logs

echo "Test environment setup complete!"
echo "Test reports will be generated in: test-results/"
echo "  - JUnit XML: test-results/junit.xml"
echo "  - HTML Report: test-results/report.html"
echo "  - Coverage HTML: test-results/coverage-html/index.html"
echo "  - Coverage XML: test-results/coverage.xml" 