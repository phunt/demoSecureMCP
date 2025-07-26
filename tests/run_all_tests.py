#!/usr/bin/env python3
"""
Comprehensive Test Runner for MCP Server

This script runs all test suites and provides a detailed report.
"""

import os
import sys
import subprocess
import time
from datetime import datetime
from typing import List, Tuple, Dict

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

def run_test_suite(test_file: str) -> Tuple[bool, float, str]:
    """Run a single test suite and return results"""
    start_time = time.time()
    
    try:
        # Run the test script
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        duration = time.time() - start_time
        
        # Check if tests passed
        success = result.returncode == 0
        
        # Combine stdout and stderr for output
        output = result.stdout
        if result.stderr:
            output += "\n\nSTDERR:\n" + result.stderr
        
        return success, duration, output
        
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return False, duration, "Test suite timed out after 5 minutes"
    except Exception as e:
        duration = time.time() - start_time
        return False, duration, f"Error running test suite: {str(e)}"

def extract_test_summary(output: str) -> Dict[str, int]:
    """Extract test counts from output"""
    summary = {"total": 0, "passed": 0, "failed": 0}
    
    # Look for summary line like "Total: X/Y tests passed"
    for line in output.split("\n"):
        if "Total:" in line and "tests passed" in line:
            # Extract numbers
            parts = line.split("Total:")[1].split("tests passed")[0].strip()
            if "/" in parts:
                passed, total = parts.split("/")
                try:
                    summary["passed"] = int(passed)
                    summary["total"] = int(total)
                    summary["failed"] = summary["total"] - summary["passed"]
                except ValueError:
                    pass
            break
    
    return summary

def main():
    """Run all test suites"""
    print_colored("\n╔══════════════════════════════════════════════════════════════════════════════╗", Colors.CYAN, bold=True)
    print_colored("║                        MCP Server Comprehensive Test Suite                       ║", Colors.CYAN, bold=True)
    print_colored("╚══════════════════════════════════════════════════════════════════════════════╝", Colors.CYAN, bold=True)
    
    print_colored(f"\nTest run started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.BLUE)
    
    # Define test suites
    test_suites = [
        {
            "name": "OAuth 2.0 Client Credentials Flow",
            "file": "tests/test_client_credentials.py",
            "description": "Tests OAuth token acquisition and basic authentication"
        },
        {
            "name": "JWT Token Validation",
            "file": "tests/test_token_validation.py",
            "description": "Tests various token validation scenarios and security"
        },
        {
            "name": "MCP Tools Integration",
            "file": "tests/test_mcp_tools_integration.py",
            "description": "Tests the demo MCP tools functionality"
        }
    ]
    
    # Check if Docker services are running
    print_colored("\nChecking Docker services...", Colors.BLUE)
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
        sys.exit(1)
    else:
        print_colored("✓ All required services are running", Colors.GREEN)
    
    # Run each test suite
    results = []
    total_tests = 0
    total_passed = 0
    total_time = 0
    
    for suite in test_suites:
        print_separator()
        print_colored(f"\nRunning: {suite['name']}", Colors.BLUE, bold=True)
        print_colored(f"Description: {suite['description']}", Colors.CYAN)
        print_colored(f"File: {suite['file']}", Colors.CYAN)
        print()
        
        success, duration, output = run_test_suite(suite['file'])
        total_time += duration
        
        # Extract test counts
        summary = extract_test_summary(output)
        total_tests += summary["total"]
        total_passed += summary["passed"]
        
        # Store results
        results.append({
            "name": suite["name"],
            "success": success,
            "duration": duration,
            "summary": summary,
            "output": output
        })
        
        # Print suite result
        if success:
            print_colored(f"\n✓ {suite['name']} PASSED", Colors.GREEN, bold=True)
        else:
            print_colored(f"\n✗ {suite['name']} FAILED", Colors.RED, bold=True)
        
        print_colored(f"Duration: {duration:.2f}s", Colors.BLUE)
        if summary["total"] > 0:
            print_colored(f"Tests: {summary['passed']}/{summary['total']} passed", Colors.BLUE)
        
        # Show last few lines of output for failed tests
        if not success and output:
            print_colored("\nLast output:", Colors.YELLOW)
            last_lines = output.strip().split("\n")[-10:]
            for line in last_lines:
                print(f"  {line}")
    
    # Print final summary
    print_separator()
    print_colored("\n📊 FINAL TEST SUMMARY", Colors.CYAN, bold=True)
    print_separator()
    
    # Overall statistics
    all_passed = all(r["success"] for r in results)
    
    print_colored(f"\nTotal Test Suites: {len(test_suites)}", Colors.BLUE)
    print_colored(f"Passed Suites: {sum(1 for r in results if r['success'])}", Colors.GREEN)
    print_colored(f"Failed Suites: {sum(1 for r in results if not r['success'])}", Colors.RED)
    
    if total_tests > 0:
        print_colored(f"\nTotal Tests: {total_tests}", Colors.BLUE)
        print_colored(f"Passed Tests: {total_passed}", Colors.GREEN)
        print_colored(f"Failed Tests: {total_tests - total_passed}", Colors.RED)
        print_colored(f"Success Rate: {(total_passed/total_tests)*100:.1f}%", Colors.BLUE)
    
    print_colored(f"\nTotal Duration: {total_time:.2f} seconds", Colors.BLUE)
    print_colored(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.BLUE)
    
    # Detailed results table
    print_colored("\n📋 Detailed Results:", Colors.CYAN, bold=True)
    print_colored("-" * 80, Colors.CYAN)
    print_colored(f"{'Test Suite':<40} {'Status':<10} {'Tests':<15} {'Duration':<10}", Colors.BLUE, bold=True)
    print_colored("-" * 80, Colors.CYAN)
    
    for result in results:
        status = "PASSED" if result["success"] else "FAILED"
        status_color = Colors.GREEN if result["success"] else Colors.RED
        
        tests_str = f"{result['summary']['passed']}/{result['summary']['total']}" if result['summary']['total'] > 0 else "N/A"
        
        print(f"{result['name']:<40} ", end="")
        print_colored(f"{status:<10}", status_color, bold=True)
        print(f" {tests_str:<15} {result['duration']:.2f}s")
    
    print_colored("-" * 80, Colors.CYAN)
    
    # Save detailed output to file
    report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, "w") as f:
        f.write("MCP Server Test Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        for i, result in enumerate(results):
            f.write(f"\nTest Suite {i+1}: {result['name']}\n")
            f.write("=" * 80 + "\n")
            f.write(f"Status: {'PASSED' if result['success'] else 'FAILED'}\n")
            f.write(f"Duration: {result['duration']:.2f}s\n")
            f.write(f"Tests: {result['summary']['passed']}/{result['summary']['total']}\n")
            f.write("\nOutput:\n")
            f.write("-" * 80 + "\n")
            f.write(result['output'])
            f.write("\n\n")
    
    print_colored(f"\n📄 Detailed report saved to: {report_file}", Colors.BLUE)
    
    # Final status
    print_separator()
    if all_passed:
        print_colored("\n✅ ALL TESTS PASSED! 🎉", Colors.GREEN, bold=True)
        return_code = 0
    else:
        print_colored("\n❌ SOME TESTS FAILED", Colors.RED, bold=True)
        print_colored("\nFailed suites:", Colors.RED)
        for result in results:
            if not result["success"]:
                print_colored(f"  - {result['name']}", Colors.RED)
        return_code = 1
    
    print()
    sys.exit(return_code)

if __name__ == "__main__":
    main() 