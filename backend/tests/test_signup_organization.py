import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.models.enums import OrgRole
from app.repositories.organization_repository import OrganizationRepository
from app.services.signup_service import SignupService
from tests.factories import add_member, auth_headers, create_organization, create_user


async def test_register_creates_personal_organization(client: httpx.AsyncClient) -> None:
    register_response = await client.post(
        "/api/auth/register",
        json={"email": "jane@example.com", "password": "password123", "full_name": "Jane Doe"},
    )
    assert register_response.status_code in (200, 201), register_response.text
    access_token = register_response.json()["access_token"]

    me_response = await client.get("/api/me", headers={"Authorization": f"Bearer {access_token}"})

    assert me_response.status_code == 200
    organizations = me_response.json()["organizations"]
    assert len(organizations) == 1
    personal_organization = organizations[0]
    assert personal_organization["name"] == "Jane Doe's workspace"
    assert personal_organization["slug"] == "jane-doe"
    assert personal_organization["role"] == "owner"
    assert personal_organization["plan_id"] == "free"
    assert personal_organization["logo_url"] is None


async def test_personal_organization_falls_back_to_email_local_part(
    db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session, email="solo.founder@example.com", full_name="")

    await SignupService(db_session, settings).complete_signup(user)

    rows = await OrganizationRepository(db_session).list_for_user(user.id)
    assert [(organization.name, organization.slug, role) for organization, role in rows] == [
        ("solo.founder's workspace", "solo-founder", OrgRole.OWNER)
    ]


async def test_me_lists_every_organization_with_role(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session)
    stranger = await create_user(db_session)
    await create_organization(db_session, owner=user, name="Alpha")
    joined_organization = await create_organization(db_session, owner=stranger, name="Beta")
    await add_member(db_session, organization=joined_organization, user=user, role=OrgRole.ADMIN)

    response = await client.get("/api/me", headers=await auth_headers(user, settings=settings))

    assert response.status_code == 200
    roles_by_name = {item["name"]: item["role"] for item in response.json()["organizations"]}
    assert roles_by_name == {"Alpha": "owner", "Beta": "admin"}
