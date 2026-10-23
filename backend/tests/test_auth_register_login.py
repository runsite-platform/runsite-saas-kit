import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from tests.auth_helpers import login_user, register_user
from tests.conftest import make_settings
from tests.factories import create_user
from tests.fakes import InMemoryEmailSender


async def test_register_returns_tokens_and_sets_cookie(client: httpx.AsyncClient) -> None:
    response = await register_user(client, email="Ann@Example.COM", full_name="  Ann  ")
    body = response.json()

    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "ann@example.com"
    assert body["user"]["full_name"] == "Ann"
    assert body["user"]["is_email_verified"] is True
    assert body["user"]["has_password"] is True
    assert body["user"]["google_linked"] is False
    assert body["user"]["platform_role"] == "user"

    cookie_header = response.headers["set-cookie"]
    assert "refresh_token=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "Path=/api/auth" in cookie_header
    assert "samesite=lax" in cookie_header.lower()


async def test_register_without_verification_sends_no_email(
    client: httpx.AsyncClient, email_outbox: InMemoryEmailSender
) -> None:
    await register_user(client)
    assert email_outbox.sent == []


async def test_register_duplicate_email_is_rejected(client: httpx.AsyncClient) -> None:
    await register_user(client, email="ann@example.com")
    response = await client.post(
        "/api/auth/register", json={"email": "ANN@example.com", "password": "password123", "full_name": "Ann"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


async def test_register_short_password_is_rejected(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/auth/register", json={"email": "ann@example.com", "password": "short"})
    assert response.status_code == 422


async def test_login_success_updates_last_login(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="bob@example.com")
    assert user.last_login_at is None

    response = await login_user(client, email="BOB@example.com")

    assert response.status_code == 200
    assert response.json()["user"]["id"] == str(user.id)
    assert "refresh_token=" in response.headers["set-cookie"]
    assert user.last_login_at is not None


@pytest.mark.parametrize(
    ("email", "password"),
    [("bob@example.com", "wrong-password"), ("nobody@example.com", "password123")],
    ids=["wrong-password", "unknown-email"],
)
async def test_login_invalid_credentials(
    client: httpx.AsyncClient, db_session: AsyncSession, email: str, password: str
) -> None:
    await create_user(db_session, email="bob@example.com")
    response = await login_user(client, email=email, password=password)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_login_oauth_only_user_has_no_password(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    await create_user(db_session, email="google@example.com", password=None)
    response = await login_user(client, email="google@example.com", password="password123")
    assert response.status_code == 401


async def test_login_blocked_user(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    await create_user(db_session, email="blocked@example.com", is_blocked=True)
    response = await login_user(client, email="blocked@example.com")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "user_blocked"


class TestSuperadminPromotion:
    @pytest.fixture
    def settings(self) -> Settings:
        return make_settings(SUPERADMIN_EMAIL="Boss@Example.com")

    async def test_matching_email_becomes_superadmin(self, client: httpx.AsyncClient) -> None:
        response = await register_user(client, email="boss@example.com")
        assert response.json()["user"]["platform_role"] == "superadmin"

    async def test_other_email_stays_user(self, client: httpx.AsyncClient) -> None:
        response = await register_user(client, email="worker@example.com")
        assert response.json()["user"]["platform_role"] == "user"
