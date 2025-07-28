.PHONY: help test test-setup test-clean test-reports install-dev lint format type-check

# Default target
help:
	@echo "Available targets:"
	@echo "  test           - Run all tests with comprehensive reporting"
	@echo "  test-setup     - Set up test environment and directories"
	@echo "  test-clean     - Clean test results and cache files"
	@echo "  test-reports   - Open test reports in browser"
	@echo "  install-dev    - Install development dependencies"
	@echo "  lint           - Run code linting"
	@echo "  format         - Format code"
	@echo "  type-check     - Run type checking"

# Test targets
test: test-setup
	@echo "Running comprehensive test suite..."
	source .venv/bin/activate && python tests/run_all_tests.py

test-setup:
	@echo "Setting up test environment..."
	./scripts/setup_test_environment.sh

test-clean:
	@echo "Cleaning test results..."
	rm -rf test-results/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete

test-reports:
	@echo "Opening test reports..."
	@if [ -f "test-results/report.html" ]; then \
		echo "Opening HTML test report..."; \
		open test-results/report.html 2>/dev/null || xdg-open test-results/report.html 2>/dev/null || echo "Please open test-results/report.html manually"; \
	fi
	@if [ -f "test-results/coverage-html/index.html" ]; then \
		echo "Opening coverage report..."; \
		open test-results/coverage-html/index.html 2>/dev/null || xdg-open test-results/coverage-html/index.html 2>/dev/null || echo "Please open test-results/coverage-html/index.html manually"; \
	fi

# Development targets
install-dev:
	@echo "Installing development dependencies..."
	source .venv/bin/activate && pip install -r requirements-dev.txt

lint:
	@echo "Running linting..."
	source .venv/bin/activate && ruff check src/ tests/
	source .venv/bin/activate && bandit -r src/

format:
	@echo "Formatting code..."
	source .venv/bin/activate && black src/ tests/
	source .venv/bin/activate && ruff check --fix src/ tests/

type-check:
	@echo "Running type checking..."
	source .venv/bin/activate && mypy src/

# Quick test with pytest directly
pytest:
	@echo "Running pytest directly..."
	./scripts/setup_test_environment.sh
	source .venv/bin/activate && pytest --verbose --color=yes tests/ 