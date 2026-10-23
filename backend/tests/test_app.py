import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def test_openapi_is_served_under_api_prefix(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Acme"


async def test_db_session_reaches_test_database(db_session: AsyncSession) -> None:
    database_name = await db_session.scalar(text("SELECT current_database()"))
    assert database_name == "saaskit_test"
