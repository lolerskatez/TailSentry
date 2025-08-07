# TailSentry Development and Deployment Automation

.PHONY: help install dev test lint format clean build docker run-dev run-prod stop logs backup restore health

# Default target
help: ## Show this help message
	@echo "TailSentry - Makefile Commands"
	@echo "================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation and Setup
install: ## Install dependencies and setup environment
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	@echo "✅ Dependencies installed"

install-dev: ## Install development dependencies
	./venv/bin/pip install -r requirements-dev.txt
	@echo "✅ Development dependencies installed"

setup: ## First-time setup with environment configuration
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "🔧 .env file created from template"; \
		echo "⚠️  Please edit .env with your configuration"; \
	fi
	@mkdir -p logs data
	@echo "✅ Project setup complete"

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
