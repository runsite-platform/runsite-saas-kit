import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from tests.conftest import make_settings
from tests.factories import auth_headers, create_organization, create_user


@pytest.fixture
def settings() -> Settings:
    return make_settings(REQUIRE_EMAIL_VERIFICATION=True)


async def test_unverified_user_cannot_invite(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session, is_email_verified=False)
    organization = await create_organization(db_session, owner=owner)

    response = await client.post(
        f"/api/orgs/{organization.id}/invitations",
        json={"email": "someone@example.com", "role": "member"},
        headers=await auth_headers(owner, settings=settings),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "email_not_verified"


async def test_verified_user_can_invite(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session, is_email_verified=True)
    organization = await create_organization(db_session, owner=owner)

    response = await client.post(
        f"/api/orgs/{organization.id}/invitations",
        json={"email": "someone@example.com", "role": "member"},
        headers=await auth_headers(owner, settings=settings),
    )

    assert response.status_code == 201
