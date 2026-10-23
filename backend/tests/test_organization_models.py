from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import OrgRole
from app.models.invitation import Invitation
from app.models.membership import Membership
from app.models.organization import Organization
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.organization_repository import OrganizationRepository
from tests.factories import add_member, create_invitation, create_organization, create_user


async def test_create_organization_factory_adds_owner_membership(db_session: AsyncSession) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner, name="Acme")

    assert organization.owner_id == owner.id
    assert organization.plan_id == "free"
    memberships = (
        (await db_session.execute(select(Membership).where(Membership.organization_id == organization.id)))
        .scalars()
        .all()
    )
    assert [(membership.user_id, membership.role) for membership in memberships] == [(owner.id, OrgRole.OWNER)]


async def test_membership_is_unique_per_user_and_organization(db_session: AsyncSession) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    with pytest.raises(IntegrityError):
        await add_member(db_session, organization=organization, user=owner, role=OrgRole.ADMIN)


async def test_organization_slug_is_unique(db_session: AsyncSession) -> None:
    owner = await create_user(db_session)
    await create_organization(db_session, owner=owner, slug="taken-slug")
    with pytest.raises(IntegrityError):
        await create_organization(db_session, owner=owner, slug="taken-slug")


async def test_deleting_organization_cascades_to_memberships_and_invitations(db_session: AsyncSession) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    await create_invitation(db_session, organization=organization, invited_by=owner, email="someone@example.com")
    organization_id = organization.id

    await db_session.delete(organization)
    await db_session.flush()

    membership_count = await db_session.scalar(
        select(func.count()).select_from(Membership).where(Membership.organization_id == organization_id)
    )
    invitation_count = await db_session.scalar(
        select(func.count()).select_from(Invitation).where(Invitation.organization_id == organization_id)
    )
    assert membership_count == 0
    assert invitation_count == 0
    assert await db_session.get(Organization, organization_id) is None


async def test_create_invitation_factory_returns_plain_token_and_stores_hash(db_session: AsyncSession) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    invitation, token = await create_invitation(
        db_session, organization=organization, invited_by=owner, email="Mixed@Example.com", expires_in=timedelta(days=1)
    )
    assert invitation.email == "mixed@example.com"
    assert invitation.token_hash != token
    assert len(invitation.token_hash) == 64
    assert invitation.accepted_at is None


async def test_list_for_user_returns_only_user_organizations_with_roles(db_session: AsyncSession) -> None:
    user = await create_user(db_session)
    stranger = await create_user(db_session)
    own_organization = await create_organization(db_session, owner=user, name="Alpha")
    joined_organization = await create_organization(db_session, owner=stranger, name="Beta")
    await add_member(db_session, organization=joined_organization, user=user, role=OrgRole.ADMIN)
    await create_organization(db_session, owner=stranger, name="Gamma")

    rows = await OrganizationRepository(db_session).list_for_user(user.id)

    roles_by_organization = {organization.id: role for organization, role in rows}
    assert roles_by_organization == {own_organization.id: OrgRole.OWNER, joined_organization.id: OrgRole.ADMIN}


async def test_slug_exists(db_session: AsyncSession) -> None:
    owner = await create_user(db_session)
    await create_organization(db_session, owner=owner, slug="existing")
    repository = OrganizationRepository(db_session)
    assert await repository.slug_exists("existing") is True
    assert await repository.slug_exists("missing") is False


async def test_get_for_user_loads_organization(db_session: AsyncSession) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner, name="Loaded")
    db_session.expunge_all()

    membership = await MembershipRepository(db_session).get_for_user(organization.id, owner.id)

    assert membership is not None
    assert membership.organization.name == "Loaded"


async def test_get_in_organization_ignores_other_organizations(db_session: AsyncSession) -> None:
    owner = await create_user(db_session)
    first_organization = await create_organization(db_session, owner=owner)
    second_organization = await create_organization(db_session, owner=owner)
    member = await create_user(db_session)
    membership = await add_member(db_session, organization=first_organization, user=member)
    repository = MembershipRepository(db_session)

    assert await repository.get_in_organization(first_organization.id, membership.id) is not None
    assert await repository.get_in_organization(second_organization.id, membership.id) is None


async def test_get_by_email_in_organization(db_session: AsyncSession) -> None:
    owner = await create_user(db_session, email="owner@example.com")
    organization = await create_organization(db_session, owner=owner)
    repository = MembershipRepository(db_session)
    assert await repository.get_by_email_in_organization(organization.id, "OWNER@example.com") is not None
    assert await repository.get_by_email_in_organization(organization.id, "nobody@example.com") is None


async def test_pending_invitations_exclude_expired_and_accepted(db_session: AsyncSession) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    pending, _token = await create_invitation(
        db_session, organization=organization, invited_by=owner, email="a@example.com"
    )
    await create_invitation(
        db_session, organization=organization, invited_by=owner, email="b@example.com", expires_in=timedelta(days=-1)
    )
    await create_invitation(
        db_session, organization=organization, invited_by=owner, email="c@example.com", accepted=True
    )
    repository = InvitationRepository(db_session)
    now = datetime.now(UTC)

    assert await repository.count_pending_for_organization(organization.id, now) == 1
    assert [invitation.id for invitation in await repository.list_pending_for_organization(organization.id, now)] == [
        pending.id
    ]


async def test_delete_unaccepted_for_email_keeps_accepted_rows(db_session: AsyncSession) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    await create_invitation(db_session, organization=organization, invited_by=owner, email="x@example.com")
    accepted, _token = await create_invitation(
        db_session, organization=organization, invited_by=owner, email="x@example.com", accepted=True
    )

    await InvitationRepository(db_session).delete_unaccepted_for_email(organization.id, "x@example.com")

    remaining_ids = (
        (await db_session.execute(select(Invitation.id).where(Invitation.organization_id == organization.id)))
        .scalars()
        .all()
    )
    assert remaining_ids == [accepted.id]
