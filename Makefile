-include .env

POSTGRES_PORT ?= 5432
BACKEND_PORT ?= 8000
export TEST_DATABASE_URL ?= postgresql+asyncpg://saaskit:saaskit@localhost:$(POSTGRES_PORT)/saaskit_test

MEMORY_CAP := systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0 timeout 600
IMAGE_NAME ?= runsite-saas-kit

.PHONY: install dev-backend dev-frontend db-up db-down migrate makemigration test-backend test-frontend lint lint-backend lint-frontend build docker-build git-hooks secrets-scan

install:
	cd backend && uv sync
	cd frontend && npm ci

dev-backend:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

dev-frontend:
	cd frontend && VITE_API_PROXY_TARGET=http://localhost:$(BACKEND_PORT) npm run dev

db-up:
	docker compose up -d

db-down:
	docker compose down

migrate:
	cd backend && uv run alembic upgrade head

makemigration:
	@test -n "$(name)" || (echo 'Usage: make makemigration name="add users"' && exit 1)
	cd backend && uv run alembic revision --autogenerate -m "$(name)"

test-backend:
	cd backend && $(MEMORY_CAP) uv run pytest -v

test-frontend:
	cd frontend && $(MEMORY_CAP) npx vitest run

lint: lint-backend lint-frontend

lint-backend:
	cd backend && uv run ruff check . && uv run ruff format --check .

lint-frontend:
	cd frontend && npm run lint

build:
	cd frontend && npm run build

docker-build:
	docker build -t $(IMAGE_NAME) .

git-hooks:
	pre-commit install --hook-type pre-commit --hook-type pre-push

secrets-scan:
	gitleaks dir . --no-banner --redact
