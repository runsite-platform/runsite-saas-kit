from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from tests.factories import auth_headers, create_organization, create_user
from tests.fakes import InMemoryObjectStorage


async def test_me_returns_presigned_avatar_and_logo_urls(
    client: AsyncClient, db_session: AsyncSession, settings: Settings, object_storage: InMemoryObjectStorage
) -> None:
    user = await create_user(db_session, email="urls@example.com")
    organization = await create_organization(db_session, owner=user)
    user.avatar_key = f"users/{user.id}/avatar"
    organization.logo_key = f"orgs/{organization.id}/logo"
    await db_session.flush()
    headers = await auth_headers(user, settings=settings)

    me_response = await client.get("/api/me", headers=headers)
    patch_response = await client.patch("/api/me", json={"full_name": "Renamed"}, headers=headers)

    assert me_response.status_code == 200
    body = me_response.json()
    assert body["user"]["avatar_url"] == f"https://storage.test/users/{user.id}/avatar"
    summary = next(item for item in body["organizations"] if item["id"] == str(organization.id))
    assert summary["logo_url"] == f"https://storage.test/orgs/{organization.id}/logo"
    patched_user = patch_response.json()
    patched_user = patched_user.get("user", patched_user)
    assert patched_user["avatar_url"] == f"https://storage.test/users/{user.id}/avatar"


async def test_urls_are_null_without_storage(client: AsyncClient, db_session: AsyncSession, settings: Settings) -> None:
    user = await create_user(db_session, email="urls-disabled@example.com")
    organization = await create_organization(db_session, owner=user)
    user.avatar_key = f"users/{user.id}/avatar"
    organization.logo_key = f"orgs/{organization.id}/logo"
    await db_session.flush()

    response = await client.get("/api/me", headers=await auth_headers(user, settings=settings))

    body = response.json()
    assert body["user"]["avatar_url"] is None
    assert all(item["logo_url"] is None for item in body["organizations"])
