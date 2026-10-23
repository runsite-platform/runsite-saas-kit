from datetime import timedelta

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AuthTokenKind
from app.repositories.auth_token import AuthTokenRepository
from app.repositories.user import UserRepository
from app.utils.security import hash_token, utc_now
from tests.auth_helpers import login_user, refresh_with_token, register_user


async def test_refresh_rotates_token(client: httpx.AsyncClient) -> None:
    register_response = await register_user(client)
    first_token = register_response.cookies["refresh_token"]

    response = await refresh_with_token(client, first_token)

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "ann@example.com"
    second_token = response.cookies["refresh_token"]
    assert second_token != first_token


async def test_reused_refresh_token_revokes_whole_family(client: httpx.AsyncClient) -> None:
    first_token = (await register_user(client)).cookies["refresh_token"]
    second_token = (await refresh_with_token(client, first_token)).cookies["refresh_token"]

    reuse_response = await refresh_with_token(client, first_token)
    assert reuse_response.status_code == 401
    assert reuse_response.json()["error"]["code"] == "not_authenticated"

    after_reuse_response = await refresh_with_token(client, second_token)
    assert after_reuse_response.status_code == 401


async def test_reuse_leaves_other_sessions_alive(client: httpx.AsyncClient) -> None:
    first_session_token = (await register_user(client)).cookies["refresh_token"]
    client.cookies.clear()
    second_session_token = (await login_user(client)).cookies["refresh_token"]

    await refresh_with_token(client, first_session_token)
    assert (await refresh_with_token(client, first_session_token)).status_code == 401

    assert (await refresh_with_token(client, second_session_token)).status_code == 200


async def test_refresh_without_cookie(client: httpx.AsyncClient) -> None:
    client.cookies.clear()
    response = await client.post("/api/auth/refresh")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


async def test_refresh_with_unknown_token(client: httpx.AsyncClient) -> None:
    response = await refresh_with_token(client, "unknown-token")
    assert response.status_code == 401


async def test_expired_refresh_token(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    refresh_token = (await register_user(client)).cookies["refresh_token"]
    stored = await AuthTokenRepository(db_session).get_by_hash(hash_token(refresh_token), AuthTokenKind.REFRESH)
    assert stored is not None
    stored.expires_at = utc_now() - timedelta(seconds=1)
    await db_session.flush()

    response = await refresh_with_token(client, refresh_token)
    assert response.status_code == 401


async def test_refresh_for_blocked_user(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    refresh_token = (await register_user(client)).cookies["refresh_token"]
    user = await UserRepository(db_session).get_by_email("ann@example.com")
    assert user is not None
    user.is_blocked = True
    await db_session.flush()

    response = await refresh_with_token(client, refresh_token)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "user_blocked"


async def test_logout_revokes_refresh_token_and_clears_cookie(client: httpx.AsyncClient) -> None:
    refresh_token = (await register_user(client)).cookies["refresh_token"]

    response = await client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert (await refresh_with_token(client, refresh_token)).status_code == 401


async def test_logout_without_cookie_is_ok(client: httpx.AsyncClient) -> None:
    client.cookies.clear()
    response = await client.post("/api/auth/logout")
    assert response.status_code == 200
