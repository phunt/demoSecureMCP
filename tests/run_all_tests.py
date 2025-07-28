#!/usr/bin/env python3
"""
Comprehensive Test Runner for MCP Server

This script runs all test suites using pytest and provides a detailed report.
"""

import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Color output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_colored(message: str, color: str = Colors.END, bold: bool = False):
    """Print colored message"""
    if bold:
        print(f"{Colors.BOLD}{color}{message}{Colors.END}")
    else:
        print(f"{color}{message}{Colors.END}")

def print_separator():
    """Print a separator line"""
    print_colored("=" * 80, Colors.CYAN)

def setup_test_environment():
    """Set up the test environment"""
    print_colored("Setting up test environment...", Colors.BLUE)
    
    # Create test-results directory
    test_results_dir = Path("test-results")
    test_results_dir.mkdir(exist_ok=True)
    (test_results_dir / "coverage-html").mkdir(exist_ok=True)
    (test_results_dir / "logs").mkdir(exist_ok=True)
    
    print_colored("✓ Test results directory created", Colors.GREEN)

def check_docker_services():
    """Check if required Docker services are running"""
    print_colored("Checking Docker services...", Colors.BLUE)
    
    docker_check = subprocess.run(
        ["docker", "compose", "ps", "--services", "--filter", "status=running"],
        capture_output=True,
        text=True
    )
    
    running_services = docker_check.stdout.strip().split("\n") if docker_check.returncode == 0 else []
    required_services = ["keycloak", "mcp-server", "nginx", "redis", "postgres"]
    
    missing_services = [s for s in required_services if s not in running_services]
    if missing_services:
        print_colored(f"\n⚠️  Missing services: {', '.join(missing_services)}", Colors.RED)
        print_colored("Please run: ./scripts/docker_manage.sh start", Colors.YELLOW)
        return False
    else:
        print_colored("✓ All required services are running", Colors.GREEN)
        return True

def run_pytest():
    """Run pytest with configured options"""
    print_colored("Running pytest with comprehensive reporting...", Colors.BLUE)
    
    # Add current directory to Python path
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    
    # Run pytest
    cmd = [
        sys.executable, "-m", "pytest",
        "--verbose",
        "--tb=short", 
        "--color=yes",
        "--junitxml=test-results/junit.xml",
        "--html=test-results/report.html",
        "--self-contained-html",
        "--cov=src",
        "--cov-report=html:test-results/coverage-html",
        "--cov-report=xml:test-results/coverage.xml",
        "--cov-report=term-missing",
        "--cov-config=.coveragerc",
        "tests/"
    ]
    
    print_colored(f"Command: {' '.join(cmd)}", Colors.CYAN)
    print_separator()
    
    start_time = time.time()
    result = subprocess.run(cmd, env=env)
    duration = time.time() - start_time
    
    return result.returncode == 0, duration

def display_results(success: bool, duration: float):
    """Display test results and report locations"""
    print_separator()
    print_colored("\n📊 TEST RESULTS", Colors.CYAN, bold=True)
    print_separator()
    
    if success:
        print_colored("\n✅ ALL TESTS PASSED! 🎉", Colors.GREEN, bold=True)
    else:
        print_colored("\n❌ SOME TESTS FAILED", Colors.RED, bold=True)
    
    print_colored(f"\nTotal Duration: {duration:.2f} seconds", Colors.BLUE)
    print_colored(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.BLUE)
    
    # Display report locations
    print_colored("\n📄 Generated Reports:", Colors.CYAN, bold=True)
    reports = [
        ("JUnit XML Report", "test-results/junit.xml"),
        ("HTML Test Report", "test-results/report.html"),
        ("Coverage HTML Report", "test-results/coverage-html/index.html"),
        ("Coverage XML Report", "test-results/coverage.xml")
    ]
    
    for name, path in reports:
        if Path(path).exists():
            print_colored(f"  ✓ {name}: {path}", Colors.GREEN)
        else:
            print_colored(f"  ✗ {name}: {path} (not generated)", Colors.YELLOW)
    
    # Show how to view reports
    print_colored("\n🔍 View Reports:", Colors.BLUE, bold=True)
    print_colored("  HTML Test Report: open test-results/report.html", Colors.CYAN)
    print_colored("  Coverage Report: open test-results/coverage-html/index.html", Colors.CYAN)
    
    return 0 if success else 1

def main():
    """Run all test suites"""
    print_colored("\n╔══════════════════════════════════════════════════════════════════════════════╗", Colors.CYAN, bold=True)
    print_colored("║                        MCP Server Comprehensive Test Suite                       ║", Colors.CYAN, bold=True)
    print_colored("╚══════════════════════════════════════════════════════════════════════════════╝", Colors.CYAN, bold=True)
    
    print_colored(f"\nTest run started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.BLUE)
    
    # Setup test environment
    setup_test_environment()
    
    # Check Docker services
    if not check_docker_services():
        sys.exit(1)
    
    # Run tests
    print_separator()
    success, duration = run_pytest()
    
    # Display results
    return_code = display_results(success, duration)
    
    print()
    sys.exit(return_code)

if __name__ == "__main__":
    main() 