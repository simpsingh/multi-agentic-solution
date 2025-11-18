# =============================================================================
# Multi-Agentic Solution - Makefile
# =============================================================================

.PHONY: help install clean start stop restart logs health

# Default target
help:
	@echo "Multi-Agentic Solution - Available Commands"
	@echo "============================================"
	@echo "make install          - Install dependencies with UV"
	@echo "make start            - Start all Docker services"
	@echo "make stop             - Stop all Docker services"
	@echo "make restart          - Restart all Docker services"
	@echo "make logs             - Show Docker logs (follow mode)"
	@echo "make logs-service S=<name> - Show logs for specific service"
	@echo "make clean            - Stop services and remove volumes"
	@echo ""
	@echo "make health           - Check health of all services"
	@echo "make init-db          - Initialize database with init-db.sql"
	@echo "make shell-postgres   - Open PostgreSQL shell"
	@echo ""
	@echo "make run-fastapi      - Run FastAPI locally"
	@echo "make run-gradio       - Run Gradio UI locally"
	@echo ""
	@echo "make notebook         - Start Jupyter Notebook"
	@echo "make lab              - Start Jupyter Lab"
	@echo ""
	@echo "make test             - Run all tests"
	@echo "make test-coverage    - Run tests with coverage report"
	@echo "make lint             - Run code linting"
	@echo "make format           - Format code with black"

# =============================================================================
# Installation & Setup
# =============================================================================

install:
	uv sync

# =============================================================================
# Docker Operations
# =============================================================================

start:
	docker compose up -d
	@echo "Services starting... Wait a moment then run 'make health'"

stop:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

logs-service:
	docker compose logs -f $(S)

clean:
	docker compose down -v
	@echo "Volumes removed. Run 'make start' to recreate."

# =============================================================================
# Database Operations
# =============================================================================

init-db:
	docker compose exec postgres psql -U postgres -d agentic_db -f /init-db.sql

shell-postgres:
	docker compose exec postgres psql -U postgres -d agentic_db

# =============================================================================
# Health Checks
# =============================================================================

health:
	@echo "Checking service health..."
	@echo "FastAPI:"
	@curl -s http://localhost:8000/api/v1/health || echo "  ❌ FastAPI not responding"
	@echo "\nAirflow:"
	@curl -s http://localhost:8080/health || echo "  ❌ Airflow not responding"
	@echo "\nGradio:"
	@curl -s http://localhost:7860 || echo "  ❌ Gradio not responding"
	@echo "\nPostgreSQL:"
	@docker compose exec -T postgres pg_isready -U postgres || echo "  ❌ PostgreSQL not responding"
	@echo "\nRedis:"
	@docker compose exec -T redis redis-cli ping || echo "  ❌ Redis not responding"
	@echo "\nOpenSearch:"
	@curl -s http://localhost:9200/_cluster/health || echo "  ❌ OpenSearch not responding"

# =============================================================================
# Local Development
# =============================================================================

run-fastapi:
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

run-gradio:
	uv run python ui/app.py

notebook:
	uv run jupyter notebook

lab:
	uv run jupyter lab

# =============================================================================
# Testing & Quality
# =============================================================================

test:
	uv run pytest

test-coverage:
	uv run pytest --cov=src --cov-report=html --cov-report=term-missing

test-watch:
	uv run pytest-watch

lint:
	uv run ruff check src tests
	uv run mypy src

format:
	uv run black src tests ui airflow/dags
	uv run ruff check --fix src tests

# =============================================================================
# Database Migrations
# =============================================================================

migrate-create:
	uv run alembic revision --autogenerate -m "$(M)"

migrate-up:
	uv run alembic upgrade head

migrate-down:
	uv run alembic downgrade -1

migrate-history:
	uv run alembic history

# =============================================================================
# Airflow Operations
# =============================================================================

airflow-shell:
	docker compose exec airflow /bin/bash

airflow-trigger-dag:
	docker compose exec airflow airflow dags trigger $(DAG)

# =============================================================================
# OpenSearch Operations
# =============================================================================

opensearch-indices:
	curl -X GET "http://localhost:9200/_cat/indices?v"

opensearch-create-index:
	@echo "Creating OpenSearch indices..."
	@echo "TODO: Implement index creation scripts"

# =============================================================================
# Docker Build
# =============================================================================

build:
	docker compose build

build-nocache:
	docker compose build --no-cache

# =============================================================================
# Cleanup
# =============================================================================

clean-all: clean
	rm -rf .venv __pycache__ .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
