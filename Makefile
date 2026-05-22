# EdTech RAG Platform — Developer Tasks
#
# `make setup` is the one-shot install for a fresh clone.
# Other targets manage running services and routine workflows.

SHELL := /bin/bash
PYTHON ?= python3
VENV := .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python

.PHONY: help setup install-backend install-frontend install-mcp env up down logs migrate revision \
        backend-run worker-run mcp-run frontend-run test clean

help:
	@echo "EdTech RAG — common tasks"
	@echo
	@echo "  make setup          Install all dependencies + create .env from example"
	@echo "  make up             Start full stack via docker compose (requires Docker)"
	@echo "  make down           Stop and remove the docker compose stack"
	@echo "  make logs           Tail docker compose logs"
	@echo "  make migrate        Apply Alembic migrations against running Postgres"
	@echo
	@echo "  make backend-run    Run FastAPI locally (without Docker, against local DB)"
	@echo "  make worker-run     Run Celery worker locally"
	@echo "  make mcp-run        Run MCP server locally"
	@echo "  make frontend-run   Run Vite dev server locally"
	@echo
	@echo "  make clean          Remove .venv, node_modules, __pycache__"

# ── One-shot setup ──────────────────────────────────────────────────────────
setup: env $(VENV) install-backend install-frontend
	@echo
	@echo "✓ Setup complete."
	@echo "  Next: edit .env with your API keys, then run 'make up'"

$(VENV):
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip

install-backend: $(VENV)
	$(PIP) install -r backend/requirements.txt

install-mcp: $(VENV)
	$(PIP) install -r mcp_server/requirements.txt

install-frontend:
	cd frontend && npm install

env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ Created .env from .env.example — edit it with real API keys."; \
	else \
		echo "✓ .env already exists, leaving alone."; \
	fi

# ── Docker stack ────────────────────────────────────────────────────────────
up:
	docker compose up -d
	@echo "✓ Stack starting. Frontend: http://localhost:3000  API: http://localhost:8000/docs"

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose exec backend alembic upgrade head

revision:
	@read -p "Migration message: " msg; \
	docker compose exec backend alembic revision --autogenerate -m "$$msg"

# ── Local dev (no Docker) ───────────────────────────────────────────────────
backend-run:
	cd backend && DATABASE_URL="$${DATABASE_URL:-postgresql+psycopg2://edtech:edtech_dev@localhost:5432/edtech}" \
		../$(VENV)/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000

worker-run:
	cd backend && DATABASE_URL="$${DATABASE_URL:-postgresql+psycopg2://edtech:edtech_dev@localhost:5432/edtech}" \
		../$(VENV)/bin/celery -A core.celery_app worker -B --loglevel=info --concurrency=4

mcp-run:
	cd mcp_server && ../$(VENV)/bin/python server.py

frontend-run:
	cd frontend && npm run dev

# ── Maintenance ─────────────────────────────────────────────────────────────
clean:
	rm -rf $(VENV) frontend/node_modules frontend/dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	@echo "✓ Cleaned."
