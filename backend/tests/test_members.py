import uuid
from dataclasses import dataclass

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.models.enums import OrgRole
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.user import User
from app.repositories.membership_repository import MembershipRepository
from tests.factories import add_member, auth_headers, create_organization, create_user


@dataclass
class Team:
    organization: Organization
    owner: User
    admin: User
    member: User
    owner_membership: Membership
    admin_membership: Membership
    member_membership: Membership


async def build_team(session: AsyncSession) -> Team:
    owner = await create_user(session, full_name="Olivia Owner")
    admin = await create_user(session, full_name="Adam Admin")
    member = await create_user(session, full_name="Mia Member")
    organization = await create_organization(session, owner=owner, plan_id="pro")
    owner_membership = await MembershipRepository(session).get_for_user(organization.id, owner.id)
    assert owner_membership is not None
    admin_membership = await add_member(session, organization=organization, user=admin, role=OrgRole.ADMIN)
    member_membership = await add_member(session, organization=organization, user=member)
    return Team(organization, owner, admin, member, owner_membership, admin_membership, member_membership)


async def membership_exists(session: AsyncSession, membership_id: uuid.UUID) -> bool:
    count = await session.scalar(select(func.count()).select_from(Membership).where(Membership.id == membership_id))
    return count == 1


async def current_role(session: AsyncSession, membership_id: uuid.UUID) -> str | None:
    return await session.scalar(select(Membership.role).where(Membership.id == membership_id))


def members_url(team: Team, membership_id: uuid.UUID | None = None) -> str:
    base_url = f"/api/orgs/{team.organization.id}/members"
    return base_url if membership_id is None else f"{base_url}/{membership_id}"


async def test_member_lists_members_with_user_details(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    team = await build_team(db_session)

    response = await client.get(members_url(team), headers=await auth_headers(team.member, settings=settings))

    assert response.status_code == 200
    rows = {item["email"]: item for item in response.json()}
    assert set(rows) == {team.owner.email, team.admin.email, team.member.email}
    assert rows[team.owner.email]["role"] == "owner"
    assert rows[team.admin.email]["full_name"] == "Adam Admin"
    assert rows[team.member.email]["id"] == str(team.member_membership.id)
    assert rows[team.member.email]["user_id"] == str(team.member.id)
    assert "joined_at" in rows[team.member.email]


async def test_admin_promotes_member(client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings) -> None:
    team = await build_team(db_session)

    response = await client.patch(
        members_url(team, team.member_membership.id),
        json={"role": "admin"},
        headers=await auth_headers(team.admin, settings=settings),
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert await current_role(db_session, team.member_membership.id) == OrgRole.ADMIN


async def test_owner_demotes_admin(client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings) -> None:
    team = await build_team(db_session)

    response = await client.patch(
        members_url(team, team.admin_membership.id),
        json={"role": "member"},
        headers=await auth_headers(team.owner, settings=settings),
    )

    assert response.status_code == 200
    assert await current_role(db_session, team.admin_membership.id) == OrgRole.MEMBER


async def test_owner_role_cannot_be_changed(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    team = await build_team(db_session)

    response = await client.patch(
        members_url(team, team.owner_membership.id),
        json={"role": "member"},
        headers=await auth_headers(team.admin, settings=settings),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "owner_cannot_be_removed"
    assert await current_role(db_session, team.owner_membership.id) == OrgRole.OWNER


async def test_owner_role_cannot_be_assigned(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    team = await build_team(db_session)

    response = await client.patch(
        members_url(team, team.member_membership.id),
        json={"role": "owner"},
        headers=await auth_headers(team.owner, settings=settings),
    )

    assert response.status_code == 422


async def test_member_cannot_change_roles(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    team = await build_team(db_session)

    response = await client.patch(
        members_url(team, team.admin_membership.id),
        json={"role": "member"},
        headers=await auth_headers(team.member, settings=settings),
    )

    assert response.status_code == 403


async def test_changing_role_of_unknown_membership_returns_404(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    team = await build_team(db_session)

    response = await client.patch(
        members_url(team, uuid.uuid4()),
        json={"role": "admin"},
        headers=await auth_headers(team.owner, settings=settings),
    )

    assert response.status_code == 404


async def test_admin_removes_member(client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings) -> None:
    team = await build_team(db_session)

    response = await client.delete(
        members_url(team, team.member_membership.id), headers=await auth_headers(team.admin, settings=settings)
    )

    assert response.status_code == 204
    assert not await membership_exists(db_session, team.member_membership.id)


async def test_admin_removes_another_admin(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    team = await build_team(db_session)
    second_admin_membership = await add_member(
        db_session, organization=team.organization, user=await create_user(db_session), role=OrgRole.ADMIN
    )

    response = await client.delete(
        members_url(team, second_admin_membership.id), headers=await auth_headers(team.admin, settings=settings)
    )

    assert response.status_code == 204


async def test_owner_can_never_be_removed(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    team = await build_team(db_session)

    for actor in (team.owner, team.admin):
        response = await client.delete(
            members_url(team, team.owner_membership.id), headers=await auth_headers(actor, settings=settings)
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "owner_cannot_be_removed"
    assert await membership_exists(db_session, team.owner_membership.id)


async def test_member_leaves_organization(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    team = await build_team(db_session)

    response = await client.delete(
        members_url(team, team.member_membership.id), headers=await auth_headers(team.member, settings=settings)
    )

    assert response.status_code == 204
    assert not await membership_exists(db_session, team.member_membership.id)


async def test_member_cannot_remove_others(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    team = await build_team(db_session)

    response = await client.delete(
        members_url(team, team.admin_membership.id), headers=await auth_headers(team.member, settings=settings)
    )

    assert response.status_code == 403
    assert await membership_exists(db_session, team.admin_membership.id)
