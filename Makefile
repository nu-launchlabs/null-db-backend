.PHONY: help run migrate makemigrations test lint format shell superuser db-up db-down fresh

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ──────────────────────────────────────────────
# Development
# ──────────────────────────────────────────────
run: ## Start Django dev server
	python manage.py runserver

migrate: ## Run database migrations
	python manage.py migrate

makemigrations: ## Create new migrations
	python manage.py makemigrations

shell: ## Open Django shell (IPython)
	python manage.py shell

superuser: ## Create superuser
	python manage.py createsuperuser

# ──────────────────────────────────────────────
# Docker
# ──────────────────────────────────────────────
db-up: ## Start PostgreSQL container
	docker compose up db -d

db-down: ## Stop PostgreSQL container
	docker compose down

up: ## Start all containers
	docker compose up -d

down: ## Stop all containers
	docker compose down

logs: ## Tail backend logs
	docker compose logs -f backend

# ──────────────────────────────────────────────
# Testing & Quality
# ──────────────────────────────────────────────
test: ## Run all tests
	pytest -v

test-cov: ## Run tests with coverage
	pytest --cov=apps --cov-report=term-missing -v

lint: ## Run linter (ruff)
	ruff check .

format: ## Format code (black + ruff fix)
	black .
	ruff check --fix .

# ──────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────
fresh: ## Reset DB and re-migrate (DEV ONLY)
	python manage.py flush --no-input
	python manage.py migrate
	@echo "Database reset complete."

check: ## Run Django system checks
	python manage.py check

collectstatic: ## Collect static files
	python manage.py collectstatic --no-input