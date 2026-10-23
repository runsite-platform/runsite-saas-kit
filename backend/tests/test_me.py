import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.models.enums import PlatformRole
from app.utils.security import verify_password
from tests.auth_helpers import login_user
from tests.factories import auth_headers, create_user


async def test_me_requires_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


async def test_me_rejects_garbage_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/me", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401


async def test_me_returns_user_and_empty_organizations(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session, email="ann@example.com", full_name="Ann")
    response = await client.get("/api/me", headers=await auth_headers(user, settings=settings))

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["id"] == str(user.id)
    assert body["user"]["email"] == "ann@example.com"
    assert body["user"]["full_name"] == "Ann"
    assert body["user"]["avatar_url"] is None
    assert body["organizations"] == []
    assert body["impersonated_by"] is None


async def test_me_reports_impersonator(client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings) -> None:
    admin = await create_user(db_session, platform_role=PlatformRole.SUPERADMIN)
    user = await create_user(db_session)
    headers = await auth_headers(user, settings=settings, impersonated_by=admin.id)
    response = await client.get("/api/me", headers=headers)
    assert response.json()["impersonated_by"] == str(admin.id)


async def test_me_blocked_user(client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings) -> None:
    user = await create_user(db_session, is_blocked=True)
    response = await client.get("/api/me", headers=await auth_headers(user, settings=settings))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "user_blocked"


async def test_update_full_name(client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings) -> None:
    user = await create_user(db_session)
    response = await client.patch(
        "/api/me", json={"full_name": "  Renamed  "}, headers=await auth_headers(user, settings=settings)
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Renamed"
    assert user.full_name == "Renamed"


async def test_update_full_name_rejects_empty(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session)
    response = await client.patch(
        "/api/me", json={"full_name": ""}, headers=await auth_headers(user, settings=settings)
    )
    assert response.status_code == 422


async def test_change_password(client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings) -> None:
    user = await create_user(db_session, email="ann@example.com", password="password123")
    response = await client.post(
        "/api/me/password",
        json={"current_password": "password123", "new_password": "newpassword1"},
        headers=await auth_headers(user, settings=settings),
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert (await login_user(client, email="ann@example.com", password="newpassword1")).status_code == 200


async def test_change_password_with_wrong_current(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session, password="password123")
    response = await client.post(
        "/api/me/password",
        json={"current_password": "not-my-password", "new_password": "newpassword1"},
        headers=await auth_headers(user, settings=settings),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_change_password_requires_current_when_user_has_one(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session, password="password123")
    response = await client.post(
        "/api/me/password", json={"new_password": "newpassword1"}, headers=await auth_headers(user, settings=settings)
    )
    assert response.status_code == 400


async def test_oauth_only_user_sets_password(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session, password=None)
    headers = await auth_headers(user, settings=settings)
    response = await client.post("/api/me/password", json={"new_password": "newpassword1"}, headers=headers)
    assert response.status_code == 200
    assert verify_password("newpassword1", user.password_hash or "")
    me_response = await client.get("/api/me", headers=headers)
    assert me_response.json()["user"]["has_password"] is True
