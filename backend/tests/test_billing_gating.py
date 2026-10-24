from app.constants.enums import SubscriptionStatus
from app.services.billing.billing_service import BillingService
from tests.factories import auth_headers, create_organization, create_project, create_subscription, create_user


async def test_expired_subscription_returns_the_organization_to_free_limits(client, db_session, settings) -> None:
    owner = await create_user(db_session, email="gating-owner@example.com")
    organization = await create_organization(db_session, owner=owner)
    subscription = await create_subscription(db_session, organization=organization, status=SubscriptionStatus.ACTIVE)
    billing_service = BillingService(db_session, settings, None)
    assert await billing_service.recompute_plan(organization) == "pro"
    for index in range(4):
        await create_project(db_session, organization=organization, created_by=owner, name=f"Project {index}")
    headers = await auth_headers(owner, settings=settings)
    projects_path = f"/api/orgs/{organization.id}/projects"

    on_pro = await client.post(projects_path, json={"name": "Fifth on Pro"}, headers=headers)
    assert on_pro.status_code == 201

    subscription.status = SubscriptionStatus.EXPIRED
    assert await billing_service.recompute_plan(organization) == "free"

    on_free = await client.post(projects_path, json={"name": "Sixth on Free"}, headers=headers)
    listing = await client.get(projects_path, headers=headers)

    assert on_free.status_code == 402
    assert on_free.json()["error"]["code"] == "plan_limit_reached"
    assert on_free.json()["error"]["details"]["limit"] == "projects"
    assert listing.status_code == 200
    assert listing.json()["total"] == 5
