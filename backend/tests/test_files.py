import logging
import re
from uuid import UUID

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.models.enums import OrgRole
from app.models.organization import Organization
from app.models.stored_file import StoredFile
from app.services import file_service
from app.services.billing.plans import PLANS, Limits, Plan
from app.services.plan_limits import BYTES_PER_MEGABYTE
from tests.factories import add_member, auth_headers, create_organization, create_stored_file, create_user
from tests.fakes import InMemoryObjectStorage


async def upload(
    client: AsyncClient,
    organization: Organization,
    headers: dict[str, str],
    *,
    name: str = "notes.txt",
    data: bytes = b"hello",
    content_type: str = "text/plain",
) -> Response:
    return await client.post(
        f"/api/orgs/{organization.id}/files", files={"file": (name, data, content_type)}, headers=headers
    )


async def test_upload_list_and_download(
    client: AsyncClient, db_session: AsyncSession, settings: Settings, object_storage: InMemoryObjectStorage
) -> None:
    owner = await create_user(db_session, email="files-owner@example.com")
    organization = await create_organization(db_session, owner=owner)
    headers = await auth_headers(owner, settings=settings)

    upload_response = await upload(client, organization, headers, name="../My Notes.txt")

    assert upload_response.status_code == 201
    body = upload_response.json()
    assert body["name"] == "My Notes.txt"
    assert body["size_bytes"] == 5
    assert body["content_type"] == "text/plain"
    assert body["uploaded_by_id"] == str(owner.id)
    stored_file = await db_session.get(StoredFile, UUID(body["id"]))
    assert stored_file is not None
    assert re.fullmatch(rf"orgs/{organization.id}/files/[0-9a-f-]{{36}}-My_Notes\.txt", stored_file.storage_key)
    assert object_storage.objects[stored_file.storage_key] == b"hello"
    assert object_storage.content_types[stored_file.storage_key] == "text/plain"

    list_response = await client.get(f"/api/orgs/{organization.id}/files", headers=headers)
    assert [item["id"] for item in list_response.json()["items"]] == [body["id"]]

    download_response = await client.get(f"/api/orgs/{organization.id}/files/{body['id']}/download", headers=headers)
    assert download_response.status_code == 200
    assert download_response.json() == {"url": f"https://storage.test/{stored_file.storage_key}"}
    assert object_storage.download_names[stored_file.storage_key] == "My Notes.txt"


async def test_member_deletes_own_file_but_not_others(
    client: AsyncClient, db_session: AsyncSession, settings: Settings, object_storage: InMemoryObjectStorage
) -> None:
    owner = await create_user(db_session, email="files-roles-owner@example.com")
    organization = await create_organization(db_session, owner=owner)
    member = await create_user(db_session, email="files-roles-member@example.com")
    await add_member(db_session, organization=organization, user=member)
    owner_file = await create_stored_file(db_session, organization=organization, uploaded_by=owner)
    member_headers = await auth_headers(member, settings=settings)
    own_upload = await upload(client, organization, member_headers)
    own_file_id = own_upload.json()["id"]
    own_storage_key = (await db_session.get(StoredFile, UUID(own_file_id))).storage_key

    forbidden = await client.delete(f"/api/orgs/{organization.id}/files/{owner_file.id}", headers=member_headers)
    allowed = await client.delete(f"/api/orgs/{organization.id}/files/{own_file_id}", headers=member_headers)

    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "forbidden"
    assert allowed.status_code == 204
    assert object_storage.deleted == [own_storage_key]
    assert await db_session.get(StoredFile, owner_file.id) is not None


@pytest.mark.parametrize("role", [OrgRole.ADMIN, OrgRole.OWNER])
async def test_admin_and_owner_delete_any_file(
    client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    object_storage: InMemoryObjectStorage,
    role: OrgRole,
) -> None:
    owner = await create_user(db_session, email=f"files-any-owner-{role}@example.com")
    organization = await create_organization(db_session, owner=owner)
    member = await create_user(db_session, email=f"files-any-member-{role}@example.com")
    await add_member(db_session, organization=organization, user=member)
    member_file = await create_stored_file(db_session, organization=organization, uploaded_by=member)
    actor = owner
    if role == OrgRole.ADMIN:
        actor = await create_user(db_session, email="files-any-admin@example.com")
        await add_member(db_session, organization=organization, user=actor, role=OrgRole.ADMIN)

    response = await client.delete(
        f"/api/orgs/{organization.id}/files/{member_file.id}", headers=await auth_headers(actor, settings=settings)
    )

    assert response.status_code == 204
    assert object_storage.deleted == [member_file.storage_key]


async def test_delete_without_delete_permission_removes_record_and_keeps_object(
    client: AsyncClient, db_session: AsyncSession, settings: Settings, object_storage: InMemoryObjectStorage
) -> None:
    object_storage.can_delete = False
    owner = await create_user(db_session, email="files-nodelete@example.com")
    organization = await create_organization(db_session, owner=owner)
    headers = await auth_headers(owner, settings=settings)
    file_id = (await upload(client, organization, headers)).json()["id"]

    response = await client.delete(f"/api/orgs/{organization.id}/files/{file_id}", headers=headers)

    assert response.status_code == 204
    assert await db_session.get(StoredFile, UUID(file_id)) is None
    assert len(object_storage.objects) == 1


async def test_delete_survives_storage_errors_after_record_is_gone(
    client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    object_storage: InMemoryObjectStorage,
    caplog: pytest.LogCaptureFixture,
) -> None:
    owner = await create_user(db_session, email="files-outage@example.com")
    organization = await create_organization(db_session, owner=owner)
    headers = await auth_headers(owner, settings=settings)
    file_id = (await upload(client, organization, headers)).json()["id"]
    object_storage.fail_deletes = True

    with caplog.at_level(logging.WARNING):
        response = await client.delete(f"/api/orgs/{organization.id}/files/{file_id}", headers=headers)

    assert response.status_code == 204
    assert await db_session.get(StoredFile, UUID(file_id)) is None
    assert len(object_storage.objects) == 1
    assert "was left in the bucket" in caplog.text


async def test_other_organization_files_are_hidden(
    client: AsyncClient, db_session: AsyncSession, settings: Settings, object_storage: InMemoryObjectStorage
) -> None:
    owner_a = await create_user(db_session, email="files-iso-a@example.com")
    organization_a = await create_organization(db_session, owner=owner_a, name="A")
    file_a = await create_stored_file(db_session, organization=organization_a, uploaded_by=owner_a)
    owner_b = await create_user(db_session, email="files-iso-b@example.com")
    organization_b = await create_organization(db_session, owner=owner_b, name="B")
    headers_b = await auth_headers(owner_b, settings=settings)

    responses = [
        await client.get(f"/api/orgs/{organization_a.id}/files", headers=headers_b),
        await upload(client, organization_a, headers_b),
        await client.get(f"/api/orgs/{organization_a.id}/files/{file_a.id}/download", headers=headers_b),
        await client.get(f"/api/orgs/{organization_b.id}/files/{file_a.id}/download", headers=headers_b),
        await client.delete(f"/api/orgs/{organization_b.id}/files/{file_a.id}", headers=headers_b),
    ]

    assert [response.status_code for response in responses] == [404] * 5
    assert object_storage.objects == {}
    assert object_storage.deleted == []


async def test_upload_when_storage_disabled(client: AsyncClient, db_session: AsyncSession, settings: Settings) -> None:
    owner = await create_user(db_session, email="files-disabled@example.com")
    organization = await create_organization(db_session, owner=owner)

    response = await upload(client, organization, await auth_headers(owner, settings=settings))

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "storage_disabled"


async def test_upload_too_large(
    client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    object_storage: InMemoryObjectStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(file_service, "MAX_FILE_BYTES", 1024)
    owner = await create_user(db_session, email="files-large@example.com")
    organization = await create_organization(db_session, owner=owner)
    headers = await auth_headers(owner, settings=settings)

    too_large = await upload(client, organization, headers, data=b"x" * 1025)
    at_limit = await upload(client, organization, headers, data=b"x" * 1024)

    assert too_large.status_code == 413
    assert too_large.json()["error"]["code"] == "file_too_large"
    assert at_limit.status_code == 201
    assert len(object_storage.objects) == 1


async def test_upload_over_storage_limit(
    client: AsyncClient, db_session: AsyncSession, settings: Settings, object_storage: InMemoryObjectStorage
) -> None:
    owner = await create_user(db_session, email="files-quota@example.com")
    organization = await create_organization(db_session, owner=owner)
    await create_stored_file(
        db_session, organization=organization, uploaded_by=owner, size_bytes=100 * BYTES_PER_MEGABYTE - 4
    )
    headers = await auth_headers(owner, settings=settings)

    over_limit = await upload(client, organization, headers, data=b"hello")
    within_limit = await upload(client, organization, headers, data=b"abcd")

    assert over_limit.status_code == 402
    assert over_limit.json()["error"]["details"] == {"limit": "storage_mb", "plan_id": "free"}
    assert within_limit.status_code == 201
    assert len(object_storage.objects) == 1


async def test_upload_requires_file_uploads_feature(
    client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    object_storage: InMemoryObjectStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        PLANS,
        "no_files",
        Plan(
            id="no_files",
            name="No files",
            price_monthly_cents=0,
            price_yearly_cents=0,
            trial_days=0,
            limits=Limits(members=3, projects=3, storage_mb=100),
            features=frozenset(),
        ),
    )
    owner = await create_user(db_session, email="files-gated@example.com")
    organization = await create_organization(db_session, owner=owner, plan_id="no_files")

    response = await upload(client, organization, await auth_headers(owner, settings=settings))

    assert response.status_code == 402
    error = response.json()["error"]
    assert error["code"] == "plan_upgrade_required"
    assert error["details"]["feature"] == "file_uploads"
    assert object_storage.objects == {}
