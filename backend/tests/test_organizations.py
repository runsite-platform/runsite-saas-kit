import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.models.enums import OrgRole
from app.repositories.membership_repository import MembershipRepository
from tests.factories import add_member, auth_headers, create_invitation, create_organization, create_user


async def test_create_organization_makes_caller_owner(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session)

    headers = await auth_headers(user, settings=settings)
    response = await client.post("/api/orgs", json={"name": "Rocket Labs"}, headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Rocket Labs"
    assert body["slug"] == "rocket-labs"
    assert body["role"] == "owner"
    assert body["plan_id"] == "free"
    assert body["logo_url"] is None
    membership = await MembershipRepository(db_session).get_for_user(uuid.UUID(body["id"]), user.id)
    assert membership is not None
    assert membership.role == OrgRole.OWNER
    assert membership.organization.owner_id == user.id


async def test_create_organization_adds_suffix_when_slug_is_taken(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    stranger = await create_user(db_session)
    await create_organization(db_session, owner=stranger, slug="rocket-labs")
    user = await create_user(db_session)

    headers = await auth_headers(user, settings=settings)
    response = await client.post("/api/orgs", json={"name": "Rocket Labs"}, headers=headers)

    assert response.status_code == 201
    assert response.json()["slug"] == "rocket-labs-2"


async def test_create_organization_rejects_blank_name(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session)
    response = await client.post("/api/orgs", json={"name": "   "}, headers=await auth_headers(user, settings=settings))
    assert response.status_code == 422


async def test_create_organization_requires_authentication(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/orgs", json={"name": "Anonymous"})
    assert response.status_code == 401


async def test_list_organizations_returns_only_user_memberships(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session)
    stranger = await create_user(db_session)
    own_organization = await create_organization(db_session, owner=user, name="Alpha")
    joined_organization = await create_organization(db_session, owner=stranger, name="Beta")
    await add_member(db_session, organization=joined_organization, user=user)
    await create_organization(db_session, owner=stranger, name="Gamma")

    response = await client.get("/api/orgs", headers=await auth_headers(user, settings=settings))

    assert response.status_code == 200
    roles_by_id = {item["id"]: item["role"] for item in response.json()}
    assert roles_by_id == {str(own_organization.id): "owner", str(joined_organization.id): "member"}


async def test_get_organization_returns_detail_with_usage(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    member = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner, name="Detail Co")
    await add_member(db_session, organization=organization, user=member)
    await create_invitation(db_session, organization=organization, invited_by=owner, email="pending@example.com")

    response = await client.get(f"/api/orgs/{organization.id}", headers=await auth_headers(member, settings=settings))

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Detail Co"
    assert body["role"] == "member"
    assert body["plan_id"] == "free"
    assert body["plan_name"] == "Free"
    assert body["owner_id"] == str(owner.id)
    assert body["member_count"] == 2
    assert body["pending_invitation_count"] == 1
    assert body["limits"] == {"members": 3, "projects": 3, "storage_mb": 100}


async def test_admin_renames_organization(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    admin = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner, name="Old Name", slug="old-name")
    await add_member(db_session, organization=organization, user=admin, role=OrgRole.ADMIN)

    response = await client.patch(
        f"/api/orgs/{organization.id}", json={"name": "New Name"}, headers=await auth_headers(admin, settings=settings)
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["slug"] == "old-name"


async def test_owner_changes_slug(client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner, slug="before")

    response = await client.patch(
        f"/api/orgs/{organization.id}",
        json={"slug": "after-change"},
        headers=await auth_headers(owner, settings=settings),
    )

    assert response.status_code == 200
    assert response.json()["slug"] == "after-change"


async def test_keeping_the_same_slug_is_allowed(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner, slug="same-slug")

    response = await client.patch(
        f"/api/orgs/{organization.id}",
        json={"name": "Same", "slug": "same-slug"},
        headers=await auth_headers(owner, settings=settings),
    )

    assert response.status_code == 200


async def test_changing_slug_to_taken_value_returns_409(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    stranger = await create_user(db_session)
    await create_organization(db_session, owner=stranger, slug="taken-address")
    organization = await create_organization(db_session, owner=owner, slug="mine")

    response = await client.patch(
        f"/api/orgs/{organization.id}",
        json={"slug": "taken-address"},
        headers=await auth_headers(owner, settings=settings),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "slug_taken"


async def test_invalid_slug_returns_422(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)

    for invalid_slug in ("Not Valid!", "-leading", "trailing-", "UPPER", "a" * 65):
        response = await client.patch(
            f"/api/orgs/{organization.id}",
            json={"slug": invalid_slug},
            headers=await auth_headers(owner, settings=settings),
        )
        assert response.status_code == 422, invalid_slug
