import uuid
from datetime import timedelta

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.models.enums import OrgRole
from app.models.invitation import Invitation
from app.models.membership import Membership
from tests.factories import add_member, auth_headers, create_invitation, create_organization, create_user


async def membership_role(session: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
    return await session.scalar(
        select(Membership.role).where(Membership.organization_id == organization_id, Membership.user_id == user_id)
    )


async def test_preview_is_public_and_describes_invitation(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    owner = await create_user(db_session, full_name="Olivia Owner")
    organization = await create_organization(db_session, owner=owner, name="Rocket Labs")
    _invitation, token = await create_invitation(
        db_session, organization=organization, invited_by=owner, email="guest@example.com", role=OrgRole.ADMIN
    )

    response = await client.get(f"/api/invitations/{token}")

    assert response.status_code == 200
    assert response.json() == {
        "organization_name": "Rocket Labs",
        "inviter_name": "Olivia Owner",
        "email": "guest@example.com",
        "role": "admin",
        "expired": False,
    }


async def test_preview_marks_expired_invitation(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    _invitation, token = await create_invitation(
        db_session, organization=organization, invited_by=owner, expires_in=timedelta(days=-1)
    )

    response = await client.get(f"/api/invitations/{token}")

    assert response.status_code == 200
    assert response.json()["expired"] is True


async def test_preview_of_unknown_or_used_token_returns_400(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    _invitation, used_token = await create_invitation(
        db_session, organization=organization, invited_by=owner, accepted=True
    )

    for token in ("unknown-token", used_token):
        response = await client.get(f"/api/invitations/{token}")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_token"


async def test_accept_creates_membership_and_marks_invitation(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    guest = await create_user(db_session, email="guest@example.com")
    organization = await create_organization(db_session, owner=owner, name="Rocket Labs")
    invitation, token = await create_invitation(
        db_session, organization=organization, invited_by=owner, email="guest@example.com", role=OrgRole.ADMIN
    )

    headers = await auth_headers(guest, settings=settings)
    response = await client.post(f"/api/invitations/{token}/accept", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(organization.id)
    assert body["slug"] == organization.slug
    assert body["role"] == "admin"
    assert await membership_role(db_session, organization.id, guest.id) == OrgRole.ADMIN
    accepted_at = await db_session.scalar(select(Invitation.accepted_at).where(Invitation.id == invitation.id))
    assert accepted_at is not None


async def test_accepting_twice_returns_400(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    guest = await create_user(db_session, email="guest@example.com")
    organization = await create_organization(db_session, owner=owner)
    _invitation, token = await create_invitation(
        db_session, organization=organization, invited_by=owner, email="guest@example.com"
    )
    headers = await auth_headers(guest, settings=settings)

    first_response = await client.post(f"/api/invitations/{token}/accept", headers=headers)
    second_response = await client.post(f"/api/invitations/{token}/accept", headers=headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 400
    assert second_response.json()["error"]["code"] == "invalid_token"


async def test_accept_with_other_email_returns_403(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    intruder = await create_user(db_session, email="intruder@example.com")
    organization = await create_organization(db_session, owner=owner)
    _invitation, token = await create_invitation(
        db_session, organization=organization, invited_by=owner, email="guest@example.com"
    )

    headers = await auth_headers(intruder, settings=settings)
    response = await client.post(f"/api/invitations/{token}/accept", headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "invitation_email_mismatch"
    assert await membership_role(db_session, organization.id, intruder.id) is None


async def test_accept_expired_invitation_returns_400(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    guest = await create_user(db_session, email="guest@example.com")
    organization = await create_organization(db_session, owner=owner)
    _invitation, token = await create_invitation(
        db_session,
        organization=organization,
        invited_by=owner,
        email="guest@example.com",
        expires_in=timedelta(days=-1),
    )

    headers = await auth_headers(guest, settings=settings)
    response = await client.post(f"/api/invitations/{token}/accept", headers=headers)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_token"
    assert await membership_role(db_session, organization.id, guest.id) is None


async def test_accept_requires_login(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    _invitation, token = await create_invitation(db_session, organization=organization, invited_by=owner)

    response = await client.post(f"/api/invitations/{token}/accept")

    assert response.status_code == 401


async def test_accept_when_already_member_keeps_single_membership(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    guest = await create_user(db_session, email="guest@example.com")
    organization = await create_organization(db_session, owner=owner)
    await add_member(db_session, organization=organization, user=guest, role=OrgRole.ADMIN)
    _invitation, token = await create_invitation(
        db_session, organization=organization, invited_by=owner, email="guest@example.com", role=OrgRole.MEMBER
    )

    headers = await auth_headers(guest, settings=settings)
    response = await client.post(f"/api/invitations/{token}/accept", headers=headers)

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    membership_count = await db_session.scalar(
        select(func.count())
        .select_from(Membership)
        .where(Membership.organization_id == organization.id, Membership.user_id == guest.id)
    )
    assert membership_count == 1
