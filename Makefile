# TailSentry Cross-Platform Development and Deployment

# Detect OS for cross-platform compatibility
UNAME_S := $(shell uname -s 2>/dev/null || echo Windows)
ifeq ($(UNAME_S),Windows)
    DETECTED_OS := Windows
    PYTHON := python
    VENV_ACTIVATE := venv\Scripts\activate
    VENV_PYTHON := venv\Scripts\python
    PIP := venv\Scripts\pip
    SHELL_EXT := .ps1
    EXEC_PREFIX := powershell -ExecutionPolicy Bypass -File
else ifeq ($(UNAME_S),Linux)
    DETECTED_OS := Linux
    PYTHON := python3
    VENV_ACTIVATE := venv/bin/activate
    VENV_PYTHON := venv/bin/python
    PIP := venv/bin/pip
    SHELL_EXT := .sh
    EXEC_PREFIX := ./
else ifeq ($(UNAME_S),Darwin)
    DETECTED_OS := macOS
    PYTHON := python3
    VENV_ACTIVATE := venv/bin/activate
    VENV_PYTHON := venv/bin/python
    PIP := venv/bin/pip
    SHELL_EXT := .sh
    EXEC_PREFIX := ./
endif

.PHONY: help install dev test lint format clean build docker run-dev run-prod stop logs backup restore health security

# Default target
help: ## Show this help message for $(DETECTED_OS)
	@echo "TailSentry Cross-Platform Makefile ($(DETECTED_OS))"
	@echo "================================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation and Setup
install: ## Install dependencies and setup environment
	$(PYTHON) -m venv venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "✅ Dependencies installed on $(DETECTED_OS)"

install-dev: ## Install development dependencies
	$(PIP) install -r requirements-dev.txt
	@echo "✅ Development dependencies installed"

setup: ## First-time cross-platform setup
	@echo "🔧 Setting up TailSentry on $(DETECTED_OS)..."
ifeq ($(DETECTED_OS),Windows)
	@if not exist .env copy .env.example .env
	@if not exist logs mkdir logs
	@if not exist data mkdir data
else
	@if [ ! -f .env ]; then cp .env.example .env; echo "🔧 .env file created from template"; fi
	@mkdir -p logs data
endif
	@echo "✅ Project setup complete for $(DETECTED_OS)"

# Security (Cross-Platform)
security: ## Run security hardening and checks
	@echo "🔒 Running security hardening for $(DETECTED_OS)..."
ifeq ($(DETECTED_OS),Windows)
	$(EXEC_PREFIX) security_hardening$(SHELL_EXT)
	$(EXEC_PREFIX) scripts\dependency_security_check$(SHELL_EXT)
else
	chmod +x security_hardening$(SHELL_EXT)
	$(EXEC_PREFIX)security_hardening$(SHELL_EXT)
	chmod +x scripts/dependency_security_check$(SHELL_EXT)
	$(EXEC_PREFIX)scripts/dependency_security_check$(SHELL_EXT)
endif

update-packages: ## Update packages and security patches
	@echo "📦 Updating packages for $(DETECTED_OS)..."
ifeq ($(DETECTED_OS),Windows)
	$(EXEC_PREFIX) scripts\update_packages$(SHELL_EXT)
else
	chmod +x scripts/update_packages$(SHELL_EXT)
	$(EXEC_PREFIX)scripts/update_packages$(SHELL_EXT)
endif

# Development
dev: ## Run development server with auto-reload
	./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080 --reload --log-level debug

run-dev: dev ## Alias for dev

# Testing
test: ## Run all tests
	./venv/bin/python -m pytest tests.py -v

test-coverage: ## Run tests with coverage report
	./venv/bin/python -m pytest tests.py --cov=. --cov-report=html --cov-report=term

test-security: ## Run security scans
	./venv/bin/bandit -r . -x venv/,tests.py
	./venv/bin/safety check

# Code Quality
lint: ## Run linting
	./venv/bin/flake8 --max-line-length=100 --exclude=venv/ .
	./venv/bin/mypy --ignore-missing-imports .

format: ## Format code
	./venv/bin/black --line-length=100 .
	./venv/bin/isort .

check: lint test ## Run all checks (lint + test)

# Docker
docker-build: ## Build Docker image
	docker build -t tailsentry:latest .

docker-run: ## Run with Docker Compose
	docker-compose up -d

docker-logs: ## View Docker logs
	docker-compose logs -f tailsentry

docker-stop: ## Stop Docker containers
	docker-compose down

# Production
deploy: ## Deploy to production (requires systemd)
	sudo cp tailsentry.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable tailsentry.service
	sudo systemctl restart tailsentry.service
	@echo "✅ Deployed to systemd"

prod-status: ## Check production service status
	sudo systemctl status tailsentry.service

prod-logs: ## View production logs
	sudo journalctl -u tailsentry.service -f

prod-restart: ## Restart production service
	sudo systemctl restart tailsentry.service

# Maintenance
backup: ## Create backup of configuration and data
	@mkdir -p backups
	@tar -czf backups/tailsentry-backup-$$(date +%Y%m%d_%H%M%S).tar.gz \
		.env data/ logs/ --exclude=logs/*.log
	@echo "✅ Backup created in backups/"

clean: ## Clean temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache/ htmlcov/ .coverage

health: ## Check application health
	@curl -f http://localhost:8080/health || echo "❌ Application not responding"

# Database/Config management
hash-password: ## Generate password hash for .env
	@read -p "Enter password: " -s password; \
	echo; \
	./venv/bin/python -c "import bcrypt; print('ADMIN_PASSWORD_HASH=' + bcrypt.hashpw('$$password'.encode(), bcrypt.gensalt()).decode())"

generate-secret: ## Generate session secret for .env
	@./venv/bin/python -c "import secrets; print('SESSION_SECRET=' + secrets.token_hex(32))"

# Update
update: ## Update application from git
	git pull
	./venv/bin/pip install -r requirements.txt --upgrade
	sudo systemctl restart tailsentry.service || echo "Manual restart required"
	@echo "✅ Update complete"
