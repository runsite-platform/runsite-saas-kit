from collections.abc import AsyncIterator

import httpx
from fastapi import FastAPI
from sqlalchemy.exc import OperationalError

from app.config.db import get_db_session


class UnreachableDatabaseSession:
    async def execute(self, statement: object) -> None:
        raise OperationalError("SELECT 1", {}, ConnectionRefusedError("connection refused"))


async def test_health_reports_ok_when_database_answers(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_reports_error_when_database_fails(app: FastAPI, client: httpx.AsyncClient) -> None:
    async def override_db_session() -> AsyncIterator[UnreachableDatabaseSession]:
        yield UnreachableDatabaseSession()

    app.dependency_overrides[get_db_session] = override_db_session
    response = await client.get("/api/health")
    assert response.status_code == 503
    assert response.json() == {"status": "error"}
