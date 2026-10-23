import logging

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from tests.factories import auth_headers, create_organization, create_user
from tests.fakes import InMemoryObjectStorage

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32


async def test_deleting_organization_deletes_files_and_logo(
    client: AsyncClient, db_session: AsyncSession, settings: Settings, object_storage: InMemoryObjectStorage
) -> None:
    owner = await create_user(db_session, email="org-objects@example.com")
    organization = await create_organization(db_session, owner=owner)
    headers = await auth_headers(owner, settings=settings)
    await client.post(
        f"/api/orgs/{organization.id}/files", files={"file": ("a.txt", b"hello", "text/plain")}, headers=headers
    )
    await client.put(
        f"/api/orgs/{organization.id}/logo", files={"file": ("logo.png", PNG_BYTES, "image/png")}, headers=headers
    )
    stored_keys = set(object_storage.objects)
    assert len(stored_keys) == 2

    response = await client.delete(f"/api/orgs/{organization.id}", headers=headers)

    assert response.is_success
    assert set(object_storage.deleted) == stored_keys
    assert object_storage.objects == {}


async def test_deleting_organization_without_delete_key_keeps_objects_and_warns(
    client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    object_storage: InMemoryObjectStorage,
    caplog: pytest.LogCaptureFixture,
) -> None:
    owner = await create_user(db_session, email="org-objects-nodelete@example.com")
    organization = await create_organization(db_session, owner=owner)
    headers = await auth_headers(owner, settings=settings)
    await client.post(
        f"/api/orgs/{organization.id}/files", files={"file": ("a.txt", b"hello", "text/plain")}, headers=headers
    )
    object_storage.can_delete = False

    with caplog.at_level(logging.WARNING):
        response = await client.delete(f"/api/orgs/{organization.id}", headers=headers)

    assert response.is_success
    assert len(object_storage.objects) == 1
    assert "left in the bucket" in caplog.text


async def test_deleting_organization_survives_storage_errors(
    client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    object_storage: InMemoryObjectStorage,
    caplog: pytest.LogCaptureFixture,
) -> None:
    owner = await create_user(db_session, email="org-objects-outage@example.com")
    organization = await create_organization(db_session, owner=owner)
    headers = await auth_headers(owner, settings=settings)
    await client.post(
        f"/api/orgs/{organization.id}/files", files={"file": ("a.txt", b"hello", "text/plain")}, headers=headers
    )
    object_storage.fail_deletes = True

    with caplog.at_level(logging.WARNING):
        response = await client.delete(f"/api/orgs/{organization.id}", headers=headers)
    detail_response = await client.get(f"/api/orgs/{organization.id}", headers=headers)

    assert response.status_code == 204
    assert detail_response.status_code == 404
    assert len(object_storage.objects) == 1
    assert "left in the bucket" in caplog.text
