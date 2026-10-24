import pytest

from app.constants.enums import SubscriptionStatus
from tests.factories import auth_headers, create_organization, create_subscription, create_user


@pytest.mark.parametrize(
    "blocking_status",
    [SubscriptionStatus.TRIALING, SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE],
)
async def test_delete_is_refused_while_a_subscription_blocks_it(client, db_session, settings, blocking_status) -> None:
    owner = await create_user(db_session, email="delete-owner@example.com")
    organization = await create_organization(db_session, owner=owner)
    await create_subscription(db_session, organization=organization, status=blocking_status)

    response = await client.delete(f"/api/orgs/{organization.id}", headers=await auth_headers(owner, settings=settings))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "active_subscription"


async def test_delete_succeeds_once_the_subscription_has_ended(client, db_session, settings) -> None:
    owner = await create_user(db_session, email="delete-owner-2@example.com")
    organization = await create_organization(db_session, owner=owner)
    subscription = await create_subscription(db_session, organization=organization, status=SubscriptionStatus.ACTIVE)
    organization_id = organization.id
    subscription.status = SubscriptionStatus.EXPIRED
    await db_session.flush()

    response = await client.delete(f"/api/orgs/{organization_id}", headers=await auth_headers(owner, settings=settings))

    assert response.status_code == 204
