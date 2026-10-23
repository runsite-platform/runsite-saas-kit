from datetime import timedelta

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.models.enums import AuthTokenKind
from app.repositories.auth_token import AuthTokenRepository
from app.repositories.user import UserRepository
from app.utils.security import hash_token, utc_now
from tests.auth_helpers import extract_token, register_user
from tests.conftest import make_settings
from tests.factories import create_user
from tests.fakes import InMemoryEmailSender


async def test_resend_for_unknown_email_is_ok_and_silent(
    client: httpx.AsyncClient, email_outbox: InMemoryEmailSender
) -> None:
    response = await client.post("/api/auth/resend-verification", json={"email": "nobody@example.com"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert email_outbox.sent == []


async def test_resend_for_verified_user_sends_nothing(
    client: httpx.AsyncClient, db_session: AsyncSession, email_outbox: InMemoryEmailSender
) -> None:
    await create_user(db_session, email="ann@example.com", is_email_verified=True)
    response = await client.post("/api/auth/resend-verification", json={"email": "ann@example.com"})
    assert response.status_code == 200
    assert email_outbox.sent == []


async def test_invalid_verification_token(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/auth/verify-email", json={"token": "does-not-exist"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_token"


class TestVerificationRequired:
    @pytest.fixture
    def settings(self) -> Settings:
        return make_settings(REQUIRE_EMAIL_VERIFICATION=True)

    async def test_register_creates_unverified_user_and_sends_email(
        self, client: httpx.AsyncClient, email_outbox: InMemoryEmailSender
    ) -> None:
        response = await register_user(client, email="Ann@Example.com")

        assert response.json()["user"]["is_email_verified"] is False
        [message] = email_outbox.sent
        assert message.to == "ann@example.com"
        assert "http://testserver/verify-email?token=" in message.text

    async def test_verify_email_marks_user_verified_once(
        self, client: httpx.AsyncClient, db_session: AsyncSession, email_outbox: InMemoryEmailSender
    ) -> None:
        await register_user(client)
        token = extract_token(email_outbox.sent[0])

        response = await client.post("/api/auth/verify-email", json={"token": token})
        assert response.status_code == 200

        user = await UserRepository(db_session).get_by_email("ann@example.com")
        assert user is not None
        assert user.is_email_verified is True

        second_response = await client.post("/api/auth/verify-email", json={"token": token})
        assert second_response.status_code == 400

    async def test_expired_verification_token(
        self, client: httpx.AsyncClient, db_session: AsyncSession, email_outbox: InMemoryEmailSender
    ) -> None:
        await register_user(client)
        token = extract_token(email_outbox.sent[0])
        stored = await AuthTokenRepository(db_session).get_by_hash(hash_token(token), AuthTokenKind.EMAIL_VERIFY)
        assert stored is not None
        stored.expires_at = utc_now() - timedelta(seconds=1)
        await db_session.flush()

        response = await client.post("/api/auth/verify-email", json={"token": token})
        assert response.status_code == 400

    async def test_resend_sends_a_new_working_link(
        self, client: httpx.AsyncClient, email_outbox: InMemoryEmailSender
    ) -> None:
        await register_user(client)
        response = await client.post("/api/auth/resend-verification", json={"email": "ann@example.com"})

        assert response.status_code == 200
        assert len(email_outbox.sent) == 2
        new_token = extract_token(email_outbox.sent[1])
        verify_response = await client.post("/api/auth/verify-email", json={"token": new_token})
        assert verify_response.status_code == 200

    async def test_unverified_user_can_log_in(self, client: httpx.AsyncClient) -> None:
        await register_user(client)
        client.cookies.clear()
        response = await client.post("/api/auth/login", json={"email": "ann@example.com", "password": "password123"})
        assert response.status_code == 200
        assert response.json()["user"]["is_email_verified"] is False
