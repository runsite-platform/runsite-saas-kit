import uuid
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.constants.enums import OrgRole
from app.models.invitation import Invitation
from app.utils.security import hash_token
from tests.factories import add_member, auth_headers, create_invitation, create_organization, create_user
from tests.fakes import InMemoryEmailSender


def invitations_url(organization_id: uuid.UUID, invitation_id: uuid.UUID | None = None) -> str:
    base_url = f"/api/orgs/{organization_id}/invitations"
    return base_url if invitation_id is None else f"{base_url}/{invitation_id}"


async def count_unaccepted(session: AsyncSession, organization_id: uuid.UUID, email: str) -> int:
    return await session.scalar(
        select(func.count())
        .select_from(Invitation)
        .where(
            Invitation.organization_id == organization_id,
            Invitation.email == email,
            Invitation.accepted_at.is_(None),
        )
    )


async def test_admin_creates_invitation_and_email_is_sent(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings, email_outbox: InMemoryEmailSender
) -> None:
    owner = await create_user(db_session)
    admin = await create_user(db_session, full_name="Adam Admin")
    organization = await create_organization(db_session, owner=owner, name="Rocket Labs")
    await add_member(db_session, organization=organization, user=admin, role=OrgRole.ADMIN)

    response = await client.post(
        invitations_url(organization.id),
        json={"email": "New.Person@Example.com", "role": "member"},
        headers=await auth_headers(admin, settings=settings),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["invitation"]["email"] == "new.person@example.com"
    assert body["invitation"]["role"] == "member"
    assert set(body["invitation"]) == {"id", "email", "role", "expires_at", "created_at"}
    invite_url = body["invite_url"]
    assert invite_url.startswith("http://testserver/invite/")
    token = invite_url.rsplit("/", 1)[1]

    stored_invitation = await db_session.scalar(
        select(Invitation).where(Invitation.id == uuid.UUID(body["invitation"]["id"]))
    )
    assert stored_invitation is not None
    assert stored_invitation.token_hash == hash_token(token)
    assert stored_invitation.invited_by_id == admin.id
    time_left = stored_invitation.expires_at - datetime.now(UTC)
    assert timedelta(days=6, hours=23) < time_left <= timedelta(days=7)

    assert len(email_outbox.sent) == 1
    assert email_outbox.sent[0].to == "new.person@example.com"
    assert invite_url in email_outbox.sent[0].text
    assert "Adam Admin" in email_outbox.sent[0].subject


async def test_inviting_existing_member_returns_409(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings, email_outbox: InMemoryEmailSender
) -> None:
    owner = await create_user(db_session)
    member = await create_user(db_session, email="already@example.com")
    organization = await create_organization(db_session, owner=owner)
    await add_member(db_session, organization=organization, user=member)

    response = await client.post(
        invitations_url(organization.id),
        json={"email": "Already@example.com", "role": "member"},
        headers=await auth_headers(owner, settings=settings),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "already_member"
    assert email_outbox.sent == []


async def test_reinviting_replaces_pending_invitation(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings, email_outbox: InMemoryEmailSender
) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    headers = await auth_headers(owner, settings=settings)

    first_response = await client.post(
        invitations_url(organization.id), json={"email": "twice@example.com", "role": "member"}, headers=headers
    )
    second_response = await client.post(
        invitations_url(organization.id), json={"email": "twice@example.com", "role": "admin"}, headers=headers
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert await count_unaccepted(db_session, organization.id, "twice@example.com") == 1
    first_token = first_response.json()["invite_url"].rsplit("/", 1)[1]
    preview_response = await client.get(f"/api/invitations/{first_token}")
    assert preview_response.status_code == 400
    assert preview_response.json()["error"]["code"] == "invalid_token"


async def test_member_limit_counts_pending_invitations(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings, email_outbox: InMemoryEmailSender
) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner, plan_id="free")
    await add_member(db_session, organization=organization, user=await create_user(db_session))
    await create_invitation(db_session, organization=organization, invited_by=owner, email="pending@example.com")

    response = await client.post(
        invitations_url(organization.id),
        json={"email": "fourth@example.com", "role": "member"},
        headers=await auth_headers(owner, settings=settings),
    )

    assert response.status_code == 402
    error = response.json()["error"]
    assert error["code"] == "plan_limit_reached"
    assert error["details"] == {"limit": "members", "plan_id": "free"}
    assert email_outbox.sent == []


async def test_expired_invitation_does_not_block_new_invite(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings, email_outbox: InMemoryEmailSender
) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner, plan_id="free")
    await add_member(db_session, organization=organization, user=await create_user(db_session))
    await create_invitation(
        db_session,
        organization=organization,
        invited_by=owner,
        email="stale@example.com",
        expires_in=timedelta(days=-1),
    )

    response = await client.post(
        invitations_url(organization.id),
        json={"email": "third@example.com", "role": "member"},
        headers=await auth_headers(owner, settings=settings),
    )

    assert response.status_code == 201


async def test_list_returns_only_pending_invitations(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner, plan_id="pro")
    pending, _token = await create_invitation(
        db_session, organization=organization, invited_by=owner, email="pending@example.com"
    )
    await create_invitation(
        db_session, organization=organization, invited_by=owner, email="old@example.com", expires_in=timedelta(days=-1)
    )
    await create_invitation(
        db_session, organization=organization, invited_by=owner, email="done@example.com", accepted=True
    )

    response = await client.get(invitations_url(organization.id), headers=await auth_headers(owner, settings=settings))

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(pending.id)]


async def test_revoke_invitation(client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    invitation, token = await create_invitation(
        db_session, organization=organization, invited_by=owner, email="bye@example.com"
    )

    response = await client.delete(
        invitations_url(organization.id, invitation.id), headers=await auth_headers(owner, settings=settings)
    )

    assert response.status_code == 204
    preview_response = await client.get(f"/api/invitations/{token}")
    assert preview_response.status_code == 400


async def test_revoke_unknown_invitation_returns_404(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)

    response = await client.delete(
        invitations_url(organization.id, uuid.uuid4()), headers=await auth_headers(owner, settings=settings)
    )

    assert response.status_code == 404


async def test_invalid_email_or_owner_role_returns_422(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    headers = await auth_headers(owner, settings=settings)

    invalid_email_response = await client.post(
        invitations_url(organization.id), json={"email": "not-an-email", "role": "member"}, headers=headers
    )
    owner_role_response = await client.post(
        invitations_url(organization.id), json={"email": "valid@example.com", "role": "owner"}, headers=headers
    )

    assert invalid_email_response.status_code == 422
    assert owner_role_response.status_code == 422
