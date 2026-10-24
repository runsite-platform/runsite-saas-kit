# Agent instructions

Rules for AI coding agents (Claude Code, Cursor, Codex and others) working in this repository. The README is the
full reference; this file is the short version an agent needs before changing code.

## Commands

| Command | What it does |
|---|---|
| `make run` | Creates `.env` from `.env.example` if missing, starts PostgreSQL, MinIO and Mailpit, runs migrations, starts the backend (port 8000) and the frontend (http://localhost:5173). |
| `make test` | Backend (pytest) and frontend (Vitest) tests, memory-capped and time-limited. |
| `make check` | Lint, frontend type check and all tests. Run it before you say a task is done. |
| `make test-backend`, `make test-frontend` | One side only. |
| `make makemigration name="add invoices"` | Autogenerates an Alembic revision. Review the file before `make migrate`. |
| `make lint` | ruff check, ruff format check, ESLint. Fix formatting with `cd backend && uv run ruff format .`. |

Run a single backend test with `cd backend && uv run pytest tests/test_projects.py -k isolation`. Backend tests need
the database from `make db-up` (`saaskit_test`); every test rolls back.

## Architecture

Backend request flow, one file per layer:

```
Route          backend/app/routers/routes/<feature>.py
Dependencies   backend/app/utils/dependencies.py   (CurrentUser, CurrentMembership, require_org_role, require_feature)
Service        backend/app/services/<feature>_service.py
Repository     backend/app/repositories/<feature>_repository.py
Model          backend/app/models/<feature>.py
```

- Routes stay thin: take dependencies, call one service method, return a schema from `backend/app/schemas/`.
- Business rules, plan limits and the single `commit()` per write live in the service.
- Repositories only query. Every organization-scoped query takes `organization_id` first and filters by it.
- Raise `BusinessError`, `not_found()` or `forbidden()` from `backend/app/utils/exceptions.py`; never return error
  dicts or raise bare `HTTPException`.
- Organization routes live under `/orgs/{org_id}/...` and use `CurrentMembership`, which also proves the user
  belongs to that organization.

Frontend mirrors the backend: `src/types/api.ts` (response types, snake_case) → `src/services/<feature>Service.ts`
(functions over `fetchApi`) → `src/pages/` and `src/components/<feature>/`. UI primitives come from
`src/components/ui/` (shadcn/ui).

## Adding a module

Copy the `projects` module layer by layer. The README section "Add your own module" lists every file to touch:
model, model registry, migration, repository, schemas, service, routes, router registry, tests, API types, service
client, page, i18n namespace, route and menu entry.

## Rules

- Never query organization data without an `organization_id` filter. Copy the isolation and role tests from
  `backend/tests/test_projects.py` for every new module.
- Plan limits and paid features are defined only in `backend/app/services/billing/plans.py` and checked in
  `backend/app/services/plan_limits.py` or with `require_feature(...)`.
- Configuration comes only from environment variables in `backend/app/config/settings.py`. A new setting must be
  added to `.env.example` and the README configuration table; `backend/tests/test_project_docs.py` fails otherwise.
- Every UI string goes into `frontend/src/i18n/locales/en/`; `translationKeys.test.ts` fails on a missing key.
- Emails are templates in `backend/app/emails/templates/`, sent through `EmailQueue`. Notifications go through
  `backend/app/services/notification_service.py` and `notification_policy.py`.
- Schema changes always come with an Alembic migration; never edit a migration that is already in `main`.
- In tests use the factories in `backend/tests/factories.py` and the fakes in `backend/tests/fakes.py`; never call
  real email, storage or billing APIs.
- Python: type hints everywhere, ruff with line length 120. TypeScript: strict, no `any`.
- Do not commit `.env` or secrets.

## Deploying

The kit deploys on [Runsite](https://runsite.app) from the template linked in the README. The Runsite MCP server
(https://runsite.app/tools/mcp) gives an agent access to builds, logs and environment variables of the deployed app.
