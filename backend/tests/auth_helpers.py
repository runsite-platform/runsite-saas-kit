import re

import httpx

from app.services.email_service import EmailMessage

REFRESH_COOKIE_NAME = "refresh_token"


async def register_user(
    client: httpx.AsyncClient,
    *,
    email: str = "ann@example.com",
    password: str = "password123",
    full_name: str = "Ann Example",
) -> httpx.Response:
    response = await client.post(
        "/api/auth/register", json={"email": email, "password": password, "full_name": full_name}
    )
    assert response.status_code == 201, response.text
    return response


async def login_user(
    client: httpx.AsyncClient, *, email: str = "ann@example.com", password: str = "password123"
) -> httpx.Response:
    return await client.post("/api/auth/login", json={"email": email, "password": password})


async def refresh_with_token(client: httpx.AsyncClient, refresh_token: str) -> httpx.Response:
    client.cookies.clear()
    return await client.post("/api/auth/refresh", headers={"Cookie": f"{REFRESH_COOKIE_NAME}={refresh_token}"})


def extract_token(message: EmailMessage) -> str:
    match = re.search(r"token=([A-Za-z0-9_\-]+)", message.text)
    assert match is not None, message.text
    return match.group(1)
