from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.models.oauth_account import GOOGLE_PROVIDER, OAuthAccount
from app.repositories.oauth_account import OAuthAccountRepository
from app.repositories.user import UserRepository
from app.services.google_oauth_service import GOOGLE_AUTHORIZATION_URL, GOOGLE_TOKEN_URL, GOOGLE_USERINFO_URL
from tests.conftest import make_settings
from tests.factories import create_user

OAUTH_FAILED_LOCATION = "http://testserver/login?error=oauth_failed"
SUCCESS_LOCATION = "http://testserver/auth/callback"


async def start_google_login(client: httpx.AsyncClient) -> str:
    response = await client.get("/api/auth/google/start")
    assert response.status_code == 302
    return parse_qs(urlparse(response.headers["location"]).query)["state"][0]


def mock_google(
    google_api: respx.MockRouter,
    *,
    account_id: str = "google-sub-1",
    email: str = "ann@example.com",
    email_verified: bool = True,
    full_name: str = "Ann Google",
) -> respx.Route:
    token_route = google_api.post(GOOGLE_TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "google-access-token",
                "expires_in": 3599,
                "token_type": "Bearer",
                "scope": "openid email profile",
                "id_token": "not-used",
            },
        )
    )
    google_api.get(GOOGLE_USERINFO_URL).mock(
        return_value=httpx.Response(
            200, json={"sub": account_id, "email": email, "email_verified": email_verified, "name": full_name}
        )
    )
    return token_route


async def call_back(client: httpx.AsyncClient, **params: str) -> httpx.Response:
    return await client.get("/api/auth/google/callback", params=params)


async def test_google_disabled_returns_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/auth/google/start")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "google_login_disabled"


class TestGoogleLogin:
    @pytest.fixture
    def settings(self) -> Settings:
        return make_settings(GOOGLE_CLIENT_ID="google-client-id", GOOGLE_CLIENT_SECRET="google-client-secret")

    async def test_start_redirects_to_google_with_state_cookie(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/auth/google/start")

        assert response.status_code == 302
        location = urlparse(response.headers["location"])
        assert f"{location.scheme}://{location.netloc}{location.path}" == GOOGLE_AUTHORIZATION_URL
        query = parse_qs(location.query)
        assert query["client_id"] == ["google-client-id"]
        assert query["redirect_uri"] == ["http://testserver/api/auth/google/callback"]
        assert query["response_type"] == ["code"]
        assert query["scope"] == ["openid email profile"]
        assert query["state"][0]
        state_cookie = response.headers["set-cookie"]
        assert "google_oauth_state=" in state_cookie
        assert "Path=/api/auth/google" in state_cookie
        assert "HttpOnly" in state_cookie

    async def test_callback_creates_verified_user(self, client: httpx.AsyncClient, db_session: AsyncSession) -> None:
        state = await start_google_login(client)
        with respx.mock(assert_all_called=True) as google_api:
            token_route = mock_google(google_api, email="New.User@Gmail.com")
            response = await call_back(client, code="auth-code", state=state)

        assert response.status_code == 302
        assert response.headers["location"] == SUCCESS_LOCATION
        assert any(header.startswith("refresh_token=") for header in response.headers.get_list("set-cookie"))
        token_form = parse_qs(token_route.calls.last.request.content.decode())
        assert token_form["code"] == ["auth-code"]
        assert token_form["grant_type"] == ["authorization_code"]
        assert token_form["redirect_uri"] == ["http://testserver/api/auth/google/callback"]

        user = await UserRepository(db_session).get_by_email("new.user@gmail.com")
        assert user is not None
        assert user.is_email_verified is True
        assert user.password_hash is None
        assert user.full_name == "Ann Google"
        assert await OAuthAccountRepository(db_session).get_by_provider_account(GOOGLE_PROVIDER, "google-sub-1")

        refresh_response = await client.post("/api/auth/refresh")
        assert refresh_response.status_code == 200
        assert refresh_response.json()["user"]["google_linked"] is True
        assert refresh_response.json()["user"]["has_password"] is False

    async def test_callback_links_existing_user_by_verified_email(
        self, client: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        existing = await create_user(db_session, email="ann@example.com", is_email_verified=False)
        state = await start_google_login(client)
        with respx.mock(assert_all_called=True) as google_api:
            mock_google(google_api, email="Ann@Example.com")
            response = await call_back(client, code="auth-code", state=state)

        assert response.headers["location"] == SUCCESS_LOCATION
        linked = await OAuthAccountRepository(db_session).get_by_provider_account(GOOGLE_PROVIDER, "google-sub-1")
        assert linked is not None
        assert linked.user_id == existing.id
        assert existing.is_email_verified is True

    async def test_linking_unproven_account_drops_password_and_sessions(
        self, client: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        squatter_session = await client.post(
            "/api/auth/register", json={"email": "victim@example.com", "password": "squatter-pass1"}
        )
        assert squatter_session.status_code == 201
        squatter_refresh_cookie = client.cookies.get("refresh_token")
        client.cookies.clear()

        state = await start_google_login(client)
        with respx.mock(assert_all_called=True) as google_api:
            mock_google(google_api, email="victim@example.com")
            response = await call_back(client, code="auth-code", state=state)
        assert response.headers["location"] == SUCCESS_LOCATION

        user = await UserRepository(db_session).get_by_email("victim@example.com")
        assert user is not None
        await db_session.refresh(user)
        assert user.password_hash is None
        squatter_login = await client.post(
            "/api/auth/login", json={"email": "victim@example.com", "password": "squatter-pass1"}
        )
        assert squatter_login.status_code == 401
        client.cookies.clear()
        client.cookies.set("refresh_token", squatter_refresh_cookie or "", path="/api/auth")
        assert (await client.post("/api/auth/refresh")).status_code == 401

    async def test_linking_keeps_password_when_email_was_verified(
        self, client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
    ) -> None:
        settings.REQUIRE_EMAIL_VERIFICATION = True
        existing = await create_user(db_session, email="ann@example.com", is_email_verified=True)
        password_hash = existing.password_hash
        state = await start_google_login(client)
        with respx.mock(assert_all_called=True) as google_api:
            mock_google(google_api, email="ann@example.com")
            await call_back(client, code="auth-code", state=state)

        await db_session.refresh(existing)
        assert existing.password_hash == password_hash

    async def test_existing_link_wins_over_email(self, client: httpx.AsyncClient, db_session: AsyncSession) -> None:
        user = await create_user(db_session, email="ann@example.com")
        await OAuthAccountRepository(db_session).add(
            OAuthAccount(user_id=user.id, provider=GOOGLE_PROVIDER, provider_account_id="google-sub-1")
        )
        state = await start_google_login(client)
        with respx.mock(assert_all_called=True) as google_api:
            mock_google(google_api, email="changed@example.com")
            response = await call_back(client, code="auth-code", state=state)

        assert response.headers["location"] == SUCCESS_LOCATION
        assert await UserRepository(db_session).get_by_email("changed@example.com") is None
        assert user.last_login_at is not None

    async def test_unverified_google_email_is_rejected(
        self, client: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        state = await start_google_login(client)
        with respx.mock(assert_all_called=True) as google_api:
            mock_google(google_api, email="unverified@example.com", email_verified=False)
            response = await call_back(client, code="auth-code", state=state)

        assert response.headers["location"] == OAUTH_FAILED_LOCATION
        assert await UserRepository(db_session).get_by_email("unverified@example.com") is None

    async def test_state_mismatch_is_rejected(self, client: httpx.AsyncClient) -> None:
        await start_google_login(client)
        with respx.mock(assert_all_mocked=True):
            response = await call_back(client, code="auth-code", state="forged-state")
        assert response.headers["location"] == OAUTH_FAILED_LOCATION

    async def test_missing_state_cookie_is_rejected(self, client: httpx.AsyncClient) -> None:
        state = await start_google_login(client)
        client.cookies.clear()
        with respx.mock(assert_all_mocked=True):
            response = await call_back(client, code="auth-code", state=state)
        assert response.headers["location"] == OAUTH_FAILED_LOCATION

    async def test_token_exchange_failure(self, client: httpx.AsyncClient) -> None:
        state = await start_google_login(client)
        with respx.mock(assert_all_called=False) as google_api:
            google_api.post(GOOGLE_TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": "invalid_grant"}))
            response = await call_back(client, code="bad-code", state=state)
        assert response.headers["location"] == OAUTH_FAILED_LOCATION

    async def test_google_error_parameter(self, client: httpx.AsyncClient) -> None:
        state = await start_google_login(client)
        with respx.mock(assert_all_mocked=True):
            response = await call_back(client, error="access_denied", state=state)
        assert response.headers["location"] == OAUTH_FAILED_LOCATION

    async def test_blocked_user_is_redirected_with_user_blocked(
        self, client: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        await create_user(db_session, email="ann@example.com", is_blocked=True)
        state = await start_google_login(client)
        with respx.mock(assert_all_called=True) as google_api:
            mock_google(google_api, email="ann@example.com")
            response = await call_back(client, code="auth-code", state=state)
        assert response.headers["location"] == "http://testserver/login?error=user_blocked"
