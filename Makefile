-include .env

POSTGRES_PORT ?= 5432
BACKEND_PORT ?= 8000
MAILPIT_UI_PORT ?= 8025
export TEST_DATABASE_URL ?= postgresql+asyncpg://saaskit:saaskit@localhost:$(POSTGRES_PORT)/saaskit_test

# Tests run memory-capped and time-limited where the tools exist (systemd on Linux, coreutils timeout).
MEMORY_CAP := $(shell command -v systemd-run >/dev/null 2>&1 && systemd-run --user --scope --quiet true >/dev/null 2>&1 \
	&& echo "systemd-run --user --scope --quiet -p MemoryMax=6G -p MemorySwapMax=0") \
	$(shell command -v timeout >/dev/null 2>&1 && echo "timeout 600")
IMAGE_NAME ?= runsite-saas-kit

.PHONY: run test check typecheck install dev-backend dev-frontend db-up db-down migrate makemigration test-backend test-frontend lint lint-backend lint-frontend build docker-build git-hooks secrets-scan

run: .env db-up migrate
	@test -d frontend/node_modules || $(MAKE) --no-print-directory install
	@echo "App: http://localhost:5173  API: http://localhost:$(BACKEND_PORT)  Mailpit: http://localhost:$(MAILPIT_UI_PORT)  (Ctrl+C stops both)"
	@trap 'kill 0' INT TERM; \
	$(MAKE) --no-print-directory dev-backend & \
	$(MAKE) --no-print-directory dev-frontend & \
	wait

.env:
	cp .env.example .env

test: test-backend test-frontend

check: lint typecheck test

install:
	cd backend && uv sync
	cd frontend && npm ci

dev-backend:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

dev-frontend:
	cd frontend && VITE_API_PROXY_TARGET=http://localhost:$(BACKEND_PORT) npm run dev

db-up:
	docker compose up -d --wait postgres minio
	docker compose up -d minio-setup mailpit

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

typecheck:
	cd frontend && npm run typecheck

build:
	cd frontend && npm run build

docker-build:
	docker build -t $(IMAGE_NAME) .

git-hooks:
	pre-commit install --hook-type pre-commit --hook-type pre-push

secrets-scan:
	gitleaks dir . --no-banner --redact
