import uuid
from collections.abc import AsyncIterator
from typing import Annotated

import httpx
import pytest
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.db import get_db_session
from app.config.settings import Settings, get_settings
from app.constants.enums import OrgRole
from app.models.membership import Membership
from app.utils.dependencies import CurrentMembership, require_feature, require_org_role
from app.utils.exceptions import BusinessError, business_error_handler
from tests.factories import add_member, auth_headers, create_organization, create_user


@pytest.fixture
async def gated_client(db_session: AsyncSession, settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    gated_app = FastAPI()
    gated_app.add_exception_handler(BusinessError, business_error_handler)

    async def override_db_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    gated_app.dependency_overrides[get_db_session] = override_db_session
    gated_app.dependency_overrides[get_settings] = lambda: settings

    @gated_app.get("/orgs/{org_id}/any-member")
    async def any_member(membership: CurrentMembership) -> dict[str, str]:
        return {"role": membership.role, "organization_name": membership.organization.name}

    @gated_app.get("/orgs/{org_id}/managers")
    async def managers_only(
        membership: Annotated[Membership, Depends(require_org_role(OrgRole.OWNER, OrgRole.ADMIN))],
    ) -> dict[str, str]:
        return {"role": membership.role}

    @gated_app.get("/orgs/{org_id}/analytics")
    async def analytics(membership: Annotated[Membership, Depends(require_feature("analytics"))]) -> dict[str, str]:
        return {"plan_id": membership.organization.plan_id}

    transport = httpx.ASGITransport(app=gated_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


async def test_member_gets_membership_with_organization(
    gated_client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner, name="Visible")

    headers = await auth_headers(owner, settings=settings)
    response = await gated_client.get(f"/orgs/{organization.id}/any-member", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"role": "owner", "organization_name": "Visible"}


async def test_non_member_gets_404_not_403(
    gated_client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    outsider = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)

    response = await gated_client.get(
        f"/orgs/{organization.id}/managers", headers=await auth_headers(outsider, settings=settings)
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_unknown_organization_gets_404(
    gated_client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session)
    headers = await auth_headers(user, settings=settings)
    response = await gated_client.get(f"/orgs/{uuid.uuid4()}/any-member", headers=headers)
    assert response.status_code == 404


async def test_anonymous_gets_401(gated_client: httpx.AsyncClient) -> None:
    response = await gated_client.get(f"/orgs/{uuid.uuid4()}/any-member")
    assert response.status_code == 401


async def test_member_role_is_forbidden_for_manager_route(
    gated_client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    member = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    await add_member(db_session, organization=organization, user=member)

    headers = await auth_headers(member, settings=settings)
    response = await gated_client.get(f"/orgs/{organization.id}/managers", headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_admin_passes_manager_route(
    gated_client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    admin = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    await add_member(db_session, organization=organization, user=admin, role=OrgRole.ADMIN)

    headers = await auth_headers(admin, settings=settings)
    response = await gated_client.get(f"/orgs/{organization.id}/managers", headers=headers)

    assert response.status_code == 200


async def test_feature_missing_from_plan_returns_402(
    gated_client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner, plan_id="free")

    headers = await auth_headers(owner, settings=settings)
    response = await gated_client.get(f"/orgs/{organization.id}/analytics", headers=headers)

    assert response.status_code == 402
    error = response.json()["error"]
    assert error["code"] == "plan_upgrade_required"
    assert error["details"] == {"feature": "analytics", "required_plan": "pro"}


async def test_feature_included_in_plan_passes(
    gated_client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner, plan_id="pro")

    headers = await auth_headers(owner, settings=settings)
    response = await gated_client.get(f"/orgs/{organization.id}/analytics", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"plan_id": "pro"}
