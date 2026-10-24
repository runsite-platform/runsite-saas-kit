#!/usr/bin/env bash
# Waits for Postgres, applies migrations and starts the API + SPA in one process.
set -euo pipefail

PORT="${PORT:-8080}"
UVICORN_WORKERS="${UVICORN_WORKERS:-1}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"
DB_WAIT_TIMEOUT="${DB_WAIT_TIMEOUT:-180}"
DB_WAIT_INTERVAL="${DB_WAIT_INTERVAL:-3}"
MIGRATION_ATTEMPTS="${MIGRATION_ATTEMPTS:-3}"

cd /app/backend

# On a fresh deploy the database service can still be booting. Connecting
# straight away would crash the container and put it into CrashLoopBackOff.
# Exit code 2 means the configuration itself is broken, so waiting is pointless.
probe_database() {
    python - <<'PY'
import asyncio
import sys

import asyncpg

from app.config.settings import SettingsError, get_settings

try:
    database_url = get_settings().DATABASE_URL
except SettingsError as error:
    print(f"FATAL: {error}", file=sys.stderr)
    sys.exit(2)


async def connect_once() -> None:
    plain_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(plain_url, timeout=5)
    await connection.close()


try:
    asyncio.run(connect_once())
except Exception as error:
    print(error, file=sys.stderr)
    sys.exit(1)
PY
}

wait_for_database() {
    local deadline=$((SECONDS + DB_WAIT_TIMEOUT))
    local attempt=0
    local probe_status

    while true; do
        attempt=$((attempt + 1))
        probe_status=0
        probe_database || probe_status=$?

        if (( probe_status == 0 )); then
            echo "==> Database is reachable (attempt ${attempt})"
            return 0
        fi
        if (( probe_status == 2 )); then
            return 1
        fi
        if (( SECONDS >= deadline )); then
            echo "FATAL: database unreachable after ${DB_WAIT_TIMEOUT}s" >&2
            return 1
        fi

        echo "==> Database not ready (attempt ${attempt}), retrying in ${DB_WAIT_INTERVAL}s"
        sleep "$DB_WAIT_INTERVAL"
    done
}

wait_for_database

if [[ "$RUN_MIGRATIONS" == "true" ]]; then
    echo "==> Applying database migrations"
    for attempt in $(seq 1 "$MIGRATION_ATTEMPTS"); do
        if alembic upgrade head; then
            break
        fi
        if (( attempt == MIGRATION_ATTEMPTS )); then
            echo "FATAL: migrations failed after ${MIGRATION_ATTEMPTS} attempts" >&2
            exit 1
        fi
        echo "==> Migration attempt ${attempt} failed, retrying in ${DB_WAIT_INTERVAL}s" >&2
        sleep "$DB_WAIT_INTERVAL"
    done
fi

echo "==> Starting the app on 0.0.0.0:${PORT}"
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers "$UVICORN_WORKERS" \
    --proxy-headers \
    --forwarded-allow-ips '*'
