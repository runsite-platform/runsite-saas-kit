import logging

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.models.enums import OrgRole
from app.services.media_service import MAX_IMAGE_BYTES
from tests.factories import add_member, auth_headers, create_organization, create_user
from tests.fakes import InMemoryObjectStorage

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32


async def test_upload_and_remove_avatar(
    client: AsyncClient, db_session: AsyncSession, settings: Settings, object_storage: InMemoryObjectStorage
) -> None:
    user = await create_user(db_session, email="avatar@example.com")
    headers = await auth_headers(user, settings=settings)
    avatar_key = f"users/{user.id}/avatar"

    upload_response = await client.put(
        "/api/me/avatar", files={"file": ("me.png", PNG_BYTES, "image/png")}, headers=headers
    )

    assert upload_response.status_code == 200
    assert upload_response.json() == {"avatar_url": f"https://storage.test/{avatar_key}"}
    assert object_storage.objects[avatar_key] == PNG_BYTES
    assert object_storage.content_types[avatar_key] == "image/png"
    assert user.avatar_key == avatar_key

    remove_response = await client.delete("/api/me/avatar", headers=headers)

    assert remove_response.status_code == 204
    assert user.avatar_key is None
    assert object_storage.deleted == [avatar_key]


async def test_remove_avatar_survives_storage_errors(
    client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    object_storage: InMemoryObjectStorage,
    caplog: pytest.LogCaptureFixture,
) -> None:
    user = await create_user(db_session, email="avatar-outage@example.com")
    headers = await auth_headers(user, settings=settings)
    await client.put("/api/me/avatar", files={"file": ("me.png", PNG_BYTES, "image/png")}, headers=headers)
    object_storage.fail_deletes = True

    with caplog.at_level(logging.WARNING):
        response = await client.delete("/api/me/avatar", headers=headers)

    assert response.status_code == 204
    assert user.avatar_key is None
    assert "was left in the bucket" in caplog.text


async def test_avatar_rejects_unsupported_type(
    client: AsyncClient, db_session: AsyncSession, settings: Settings, object_storage: InMemoryObjectStorage
) -> None:
    user = await create_user(db_session, email="avatar-type@example.com")

    response = await client.put(
        "/api/me/avatar",
        files={"file": ("me.svg", b"<svg/>", "image/svg+xml")},
        headers=await auth_headers(user, settings=settings),
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_file_type"
    assert object_storage.objects == {}


async def test_avatar_rejects_more_than_two_megabytes(
    client: AsyncClient, db_session: AsyncSession, settings: Settings, object_storage: InMemoryObjectStorage
) -> None:
    user = await create_user(db_session, email="avatar-size@example.com")

    response = await client.put(
        "/api/me/avatar",
        files={"file": ("me.jpg", b"0" * (MAX_IMAGE_BYTES + 1), "image/jpeg")},
        headers=await auth_headers(user, settings=settings),
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"
    assert object_storage.objects == {}


async def test_avatar_when_storage_disabled(client: AsyncClient, db_session: AsyncSession, settings: Settings) -> None:
    user = await create_user(db_session, email="avatar-disabled@example.com")

    response = await client.put(
        "/api/me/avatar",
        files={"file": ("me.png", PNG_BYTES, "image/png")},
        headers=await auth_headers(user, settings=settings),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "storage_disabled"


async def test_admin_uploads_and_removes_logo(
    client: AsyncClient, db_session: AsyncSession, settings: Settings, object_storage: InMemoryObjectStorage
) -> None:
    owner = await create_user(db_session, email="logo-owner@example.com")
    organization = await create_organization(db_session, owner=owner)
    admin = await create_user(db_session, email="logo-admin@example.com")
    await add_member(db_session, organization=organization, user=admin, role=OrgRole.ADMIN)
    headers = await auth_headers(admin, settings=settings)
    logo_key = f"orgs/{organization.id}/logo"

    upload_response = await client.put(
        f"/api/orgs/{organization.id}/logo", files={"file": ("logo.webp", PNG_BYTES, "image/webp")}, headers=headers
    )

    assert upload_response.status_code == 200
    assert upload_response.json() == {"logo_url": f"https://storage.test/{logo_key}"}
    assert organization.logo_key == logo_key

    remove_response = await client.delete(f"/api/orgs/{organization.id}/logo", headers=headers)

    assert remove_response.status_code == 204
    assert organization.logo_key is None
    assert object_storage.deleted == [logo_key]


async def test_member_cannot_change_logo(
    client: AsyncClient, db_session: AsyncSession, settings: Settings, object_storage: InMemoryObjectStorage
) -> None:
    owner = await create_user(db_session, email="logo-member-owner@example.com")
    organization = await create_organization(db_session, owner=owner)
    member = await create_user(db_session, email="logo-member@example.com")
    await add_member(db_session, organization=organization, user=member)
    headers = await auth_headers(member, settings=settings)

    upload_response = await client.put(
        f"/api/orgs/{organization.id}/logo", files={"file": ("logo.png", PNG_BYTES, "image/png")}, headers=headers
    )
    remove_response = await client.delete(f"/api/orgs/{organization.id}/logo", headers=headers)

    assert upload_response.status_code == 403
    assert remove_response.status_code == 403
    assert object_storage.objects == {}


async def test_logo_of_other_organization_is_hidden(
    client: AsyncClient, db_session: AsyncSession, settings: Settings, object_storage: InMemoryObjectStorage
) -> None:
    owner = await create_user(db_session, email="logo-iso-a@example.com")
    organization = await create_organization(db_session, owner=owner)
    outsider = await create_user(db_session, email="logo-iso-b@example.com")

    response = await client.put(
        f"/api/orgs/{organization.id}/logo",
        files={"file": ("logo.png", PNG_BYTES, "image/png")},
        headers=await auth_headers(outsider, settings=settings),
    )

    assert response.status_code == 404
