import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.constants.enums import OrgRole
from app.models.invitation import Invitation
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.user import User
from tests.factories import add_member, auth_headers, create_invitation, create_organization, create_user


@dataclass
class OrganizationWorld:
    organization: Organization
    users_by_role: dict[str, User]
    target_membership: Membership
    invitation: Invitation


async def build_world(session: AsyncSession, name: str) -> OrganizationWorld:
    owner = await create_user(session)
    admin = await create_user(session)
    member = await create_user(session)
    target = await create_user(session)
    organization = await create_organization(session, owner=owner, name=name, plan_id="pro")
    await add_member(session, organization=organization, user=admin, role=OrgRole.ADMIN)
    await add_member(session, organization=organization, user=member, role=OrgRole.MEMBER)
    target_membership = await add_member(session, organization=organization, user=target, role=OrgRole.MEMBER)
    invitation, _token = await create_invitation(
        session, organization=organization, invited_by=owner, email=f"pending-{uuid.uuid4().hex[:8]}@example.com"
    )
    return OrganizationWorld(
        organization=organization,
        users_by_role={"owner": owner, "admin": admin, "member": member},
        target_membership=target_membership,
        invitation=invitation,
    )


@dataclass(frozen=True)
class RouteCase:
    name: str
    method: str
    path_template: str
    expected_status_by_role: dict[str, int]
    build_body: Callable[[OrganizationWorld], dict[str, Any]] | None = None

    def path_for(self, path_world: OrganizationWorld, id_world: OrganizationWorld) -> str:
        return self.path_template.format(
            org_id=path_world.organization.id,
            membership_id=id_world.target_membership.id,
            invitation_id=id_world.invitation.id,
        )

    def body_for(self, world: OrganizationWorld) -> dict[str, Any] | None:
        return self.build_body(world) if self.build_body else None


ROUTE_CASES = [
    RouteCase("get_organization", "GET", "/api/orgs/{org_id}", {"owner": 200, "admin": 200, "member": 200}),
    RouteCase(
        "rename_organization",
        "PATCH",
        "/api/orgs/{org_id}",
        {"owner": 200, "admin": 200, "member": 403},
        lambda world: {"name": "Renamed"},
    ),
    RouteCase("delete_organization", "DELETE", "/api/orgs/{org_id}", {"owner": 204, "admin": 403, "member": 403}),
    RouteCase(
        "transfer_ownership",
        "POST",
        "/api/orgs/{org_id}/transfer-ownership",
        {"owner": 204, "admin": 403, "member": 403},
        lambda world: {"membership_id": str(world.target_membership.id)},
    ),
    RouteCase("list_members", "GET", "/api/orgs/{org_id}/members", {"owner": 200, "admin": 200, "member": 200}),
    RouteCase(
        "change_member_role",
        "PATCH",
        "/api/orgs/{org_id}/members/{membership_id}",
        {"owner": 200, "admin": 200, "member": 403},
        lambda world: {"role": "admin"},
    ),
    RouteCase(
        "remove_member",
        "DELETE",
        "/api/orgs/{org_id}/members/{membership_id}",
        {"owner": 204, "admin": 204, "member": 403},
    ),
    RouteCase("list_invitations", "GET", "/api/orgs/{org_id}/invitations", {"owner": 200, "admin": 200, "member": 403}),
    RouteCase(
        "create_invitation",
        "POST",
        "/api/orgs/{org_id}/invitations",
        {"owner": 201, "admin": 201, "member": 403},
        lambda world: {"email": "fresh@example.com", "role": "member"},
    ),
    RouteCase(
        "revoke_invitation",
        "DELETE",
        "/api/orgs/{org_id}/invitations/{invitation_id}",
        {"owner": 204, "admin": 204, "member": 403},
    ),
]

CROSS_ID_CASES = [
    route_case
    for route_case in ROUTE_CASES
    if "{membership_id}" in route_case.path_template
    or "{invitation_id}" in route_case.path_template
    or route_case.name == "transfer_ownership"
]


def case_id(route_case: RouteCase) -> str:
    return route_case.name


@pytest.mark.parametrize("role", ["owner", "admin", "member"])
@pytest.mark.parametrize("route_case", ROUTE_CASES, ids=case_id)
async def test_role_matrix(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    email_outbox: Any,
    route_case: RouteCase,
    role: str,
) -> None:
    world = await build_world(db_session, "Matrix")

    response = await client.request(
        route_case.method,
        route_case.path_for(world, world),
        json=route_case.body_for(world),
        headers=await auth_headers(world.users_by_role[role], settings=settings),
    )

    assert response.status_code == route_case.expected_status_by_role[role], response.text
    if response.status_code == 403:
        assert response.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize("route_case", ROUTE_CASES, ids=case_id)
async def test_owner_of_another_organization_gets_404(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings, email_outbox: Any, route_case: RouteCase
) -> None:
    world_a = await build_world(db_session, "Alpha")
    world_b = await build_world(db_session, "Beta")

    response = await client.request(
        route_case.method,
        route_case.path_for(world_b, world_b),
        json=route_case.body_for(world_b),
        headers=await auth_headers(world_a.users_by_role["owner"], settings=settings),
    )

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("route_case", CROSS_ID_CASES, ids=case_id)
async def test_ids_from_another_organization_return_404(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings, email_outbox: Any, route_case: RouteCase
) -> None:
    world_a = await build_world(db_session, "Alpha")
    world_b = await build_world(db_session, "Beta")

    response = await client.request(
        route_case.method,
        route_case.path_for(world_a, world_b),
        json=route_case.body_for(world_b),
        headers=await auth_headers(world_a.users_by_role["owner"], settings=settings),
    )

    assert response.status_code == 404, response.text


@pytest.mark.parametrize("route_case", ROUTE_CASES, ids=case_id)
async def test_anonymous_gets_401(client: httpx.AsyncClient, db_session: AsyncSession, route_case: RouteCase) -> None:
    world = await build_world(db_session, "Anonymous")

    response = await client.request(
        route_case.method, route_case.path_for(world, world), json=route_case.body_for(world)
    )

    assert response.status_code == 401
