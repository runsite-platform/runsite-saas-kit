import uuid

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.models.enums import OrgRole
from app.models.membership import Membership
from app.models.organization import Organization
from app.services.organization_service import OrganizationService
from app.utils.exceptions import BusinessError
from tests.factories import add_member, auth_headers, create_invitation, create_organization, create_user


async def count_organizations(session: AsyncSession, organization_id: uuid.UUID) -> int:
    return await session.scalar(
        select(func.count()).select_from(Organization).where(Organization.id == organization_id)
    )


async def roles_by_user(session: AsyncSession, organization_id: uuid.UUID) -> dict[uuid.UUID, str]:
    rows = await session.execute(
        select(Membership.user_id, Membership.role).where(Membership.organization_id == organization_id)
    )
    return {user_id: role for user_id, role in rows.all()}


async def test_owner_deletes_organization_with_members_and_invitations(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    await add_member(db_session, organization=organization, user=await create_user(db_session))
    await create_invitation(db_session, organization=organization, invited_by=owner, email="later@example.com")
    organization_id = organization.id

    response = await client.delete(f"/api/orgs/{organization_id}", headers=await auth_headers(owner, settings=settings))

    assert response.status_code == 204
    assert await count_organizations(db_session, organization_id) == 0
    assert await roles_by_user(db_session, organization_id) == {}
    follow_up = await client.get(f"/api/orgs/{organization_id}", headers=await auth_headers(owner, settings=settings))
    assert follow_up.status_code == 404


async def test_admin_cannot_delete_organization(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    admin = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    await add_member(db_session, organization=organization, user=admin, role=OrgRole.ADMIN)

    response = await client.delete(f"/api/orgs/{organization.id}", headers=await auth_headers(admin, settings=settings))

    assert response.status_code == 403
    assert await count_organizations(db_session, organization.id) == 1


async def test_delete_is_refused_when_subscription_hook_blocks(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def block_deletion(self: OrganizationService, organization: Organization) -> None:
        raise BusinessError("active_subscription", "Cancel the subscription first", status_code=409)

    monkeypatch.setattr(OrganizationService, "_ensure_no_blocking_subscription", block_deletion)
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)

    response = await client.delete(f"/api/orgs/{organization.id}", headers=await auth_headers(owner, settings=settings))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "active_subscription"
    assert await count_organizations(db_session, organization.id) == 1


async def test_delete_runs_object_cleanup_hook(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    cleaned_organization_ids: list[uuid.UUID] = []

    async def record_cleanup(self: OrganizationService, organization: Organization) -> None:
        cleaned_organization_ids.append(organization.id)

    monkeypatch.setattr(OrganizationService, "_delete_organization_objects", record_cleanup)
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)

    response = await client.delete(f"/api/orgs/{organization.id}", headers=await auth_headers(owner, settings=settings))

    assert response.status_code == 204
    assert cleaned_organization_ids == [organization.id]


async def test_owner_transfers_ownership_to_member(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    member = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    member_membership = await add_member(db_session, organization=organization, user=member)

    response = await client.post(
        f"/api/orgs/{organization.id}/transfer-ownership",
        json={"membership_id": str(member_membership.id)},
        headers=await auth_headers(owner, settings=settings),
    )

    assert response.status_code == 204
    assert await roles_by_user(db_session, organization.id) == {owner.id: OrgRole.ADMIN, member.id: OrgRole.OWNER}
    owner_id = await db_session.scalar(select(Organization.owner_id).where(Organization.id == organization.id))
    assert owner_id == member.id


async def test_after_transfer_only_new_owner_can_delete(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    member = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    member_membership = await add_member(db_session, organization=organization, user=member)
    await client.post(
        f"/api/orgs/{organization.id}/transfer-ownership",
        json={"membership_id": str(member_membership.id)},
        headers=await auth_headers(owner, settings=settings),
    )

    old_owner_headers = await auth_headers(owner, settings=settings)
    old_owner_response = await client.delete(f"/api/orgs/{organization.id}", headers=old_owner_headers)
    new_owner_headers = await auth_headers(member, settings=settings)
    new_owner_response = await client.delete(f"/api/orgs/{organization.id}", headers=new_owner_headers)

    assert old_owner_response.status_code == 403
    assert new_owner_response.status_code == 204


async def test_transfer_to_unknown_membership_returns_404(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)

    response = await client.post(
        f"/api/orgs/{organization.id}/transfer-ownership",
        json={"membership_id": str(uuid.uuid4())},
        headers=await auth_headers(owner, settings=settings),
    )

    assert response.status_code == 404


async def test_transfer_to_membership_of_another_organization_returns_404(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    other_organization = await create_organization(db_session, owner=await create_user(db_session))
    foreign_membership = await add_member(
        db_session, organization=other_organization, user=await create_user(db_session)
    )

    response = await client.post(
        f"/api/orgs/{organization.id}/transfer-ownership",
        json={"membership_id": str(foreign_membership.id)},
        headers=await auth_headers(owner, settings=settings),
    )

    assert response.status_code == 404
    assert await roles_by_user(db_session, organization.id) == {owner.id: OrgRole.OWNER}


async def test_admin_cannot_transfer_ownership(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    admin = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    admin_membership = await add_member(db_session, organization=organization, user=admin, role=OrgRole.ADMIN)

    response = await client.post(
        f"/api/orgs/{organization.id}/transfer-ownership",
        json={"membership_id": str(admin_membership.id)},
        headers=await auth_headers(admin, settings=settings),
    )

    assert response.status_code == 403


async def test_transfer_to_self_changes_nothing(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    owner_membership_id = await db_session.scalar(
        select(Membership.id).where(Membership.organization_id == organization.id, Membership.user_id == owner.id)
    )

    response = await client.post(
        f"/api/orgs/{organization.id}/transfer-ownership",
        json={"membership_id": str(owner_membership_id)},
        headers=await auth_headers(owner, settings=settings),
    )

    assert response.status_code == 204
    assert await roles_by_user(db_session, organization.id) == {owner.id: OrgRole.OWNER}
