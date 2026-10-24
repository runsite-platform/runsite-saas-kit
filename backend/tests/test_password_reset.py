from datetime import timedelta

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import AuthTokenKind
from app.repositories.auth_token import AuthTokenRepository
from app.repositories.user import UserRepository
from app.utils.security import hash_token, utc_now
from tests.auth_helpers import extract_token, login_user, refresh_with_token, register_user
from tests.factories import create_user
from tests.fakes import InMemoryEmailSender


async def request_reset(client: httpx.AsyncClient, email: str) -> httpx.Response:
    return await client.post("/api/auth/forgot-password", json={"email": email})


async def test_forgot_password_for_unknown_email_is_ok_and_silent(
    client: httpx.AsyncClient, email_outbox: InMemoryEmailSender
) -> None:
    response = await request_reset(client, "nobody@example.com")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert email_outbox.sent == []


async def test_forgot_password_for_blocked_user_sends_nothing(
    client: httpx.AsyncClient, db_session: AsyncSession, email_outbox: InMemoryEmailSender
) -> None:
    await create_user(db_session, email="blocked@example.com", is_blocked=True)
    response = await request_reset(client, "blocked@example.com")
    assert response.status_code == 200
    assert email_outbox.sent == []


async def test_reset_password_flow(client: httpx.AsyncClient, email_outbox: InMemoryEmailSender) -> None:
    old_refresh_token = (await register_user(client, password="password123")).cookies["refresh_token"]
    await request_reset(client, "ANN@example.com")
    [message] = email_outbox.sent
    assert message.to == "ann@example.com"
    assert "http://testserver/reset-password?token=" in message.text
    token = extract_token(message)

    response = await client.post("/api/auth/reset-password", json={"token": token, "password": "brand-new-pass"})
    assert response.status_code == 200

    assert (await refresh_with_token(client, old_refresh_token)).status_code == 401
    client.cookies.clear()
    assert (await login_user(client, password="password123")).status_code == 401
    assert (await login_user(client, password="brand-new-pass")).status_code == 200

    reuse_response = await client.post("/api/auth/reset-password", json={"token": token, "password": "another-pass"})
    assert reuse_response.status_code == 400
    assert reuse_response.json()["error"]["code"] == "invalid_token"


async def test_expired_reset_token(
    client: httpx.AsyncClient, db_session: AsyncSession, email_outbox: InMemoryEmailSender
) -> None:
    await create_user(db_session, email="ann@example.com")
    await request_reset(client, "ann@example.com")
    token = extract_token(email_outbox.sent[0])
    stored = await AuthTokenRepository(db_session).get_by_hash(hash_token(token), AuthTokenKind.PASSWORD_RESET)
    assert stored is not None
    stored.expires_at = utc_now() - timedelta(seconds=1)
    await db_session.flush()

    response = await client.post("/api/auth/reset-password", json={"token": token, "password": "brand-new-pass"})
    assert response.status_code == 400


async def test_oauth_only_user_can_set_password_through_reset(
    client: httpx.AsyncClient, db_session: AsyncSession, email_outbox: InMemoryEmailSender
) -> None:
    await create_user(db_session, email="google@example.com", password=None, is_email_verified=False)
    await request_reset(client, "google@example.com")
    token = extract_token(email_outbox.sent[0])

    response = await client.post("/api/auth/reset-password", json={"token": token, "password": "brand-new-pass"})
    assert response.status_code == 200

    user = await UserRepository(db_session).get_by_email("google@example.com")
    assert user is not None
    assert user.password_hash is not None
    assert user.is_email_verified is True


async def test_reset_password_rejects_short_password(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/auth/reset-password", json={"token": "anything", "password": "short"})
    assert response.status_code == 422
