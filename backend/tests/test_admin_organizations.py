import uuid
from datetime import UTC, datetime

from app.models import Payment
from app.models.enums import OrgRole, PaymentStatus, PlatformRole
from tests.factories import add_member, auth_headers, create_organization, create_subscription, create_user


async def test_list_organizations_filters_by_search_and_plan(client, db_session, settings) -> None:
    admin = await create_user(db_session, email="orgs-admin@example.com", platform_role=PlatformRole.ADMIN)
    owner = await create_user(db_session, email="orgs-owner@example.com")
    await create_organization(db_session, owner=owner, name="Acme Labs", slug="acme-labs", plan_id="pro")
    await create_organization(db_session, owner=owner, name="Acme Free", slug="acme-free", plan_id="free")
    await create_organization(db_session, owner=owner, name="Globex", slug="globex", plan_id="pro")
    headers = await auth_headers(admin, settings=settings)

    by_search = await client.get("/api/admin/organizations", params={"search": "acme"}, headers=headers)
    by_plan = await client.get("/api/admin/organizations", params={"search": "acme", "plan_id": "pro"}, headers=headers)

    assert by_search.status_code == 200, by_search.text
    assert sorted(item["slug"] for item in by_search.json()["items"]) == ["acme-free", "acme-labs"]
    assert by_plan.json()["total"] == 1
    item = by_plan.json()["items"][0]
    assert item["slug"] == "acme-labs"
    assert item["owner_email"] == "orgs-owner@example.com"
    assert item["members_count"] == 1
    assert item["plan_override_id"] is None


async def test_organization_detail_includes_members_subscription_and_payments(client, db_session, settings) -> None:
    admin = await create_user(db_session, email="org-detail-admin@example.com", platform_role=PlatformRole.ADMIN)
    owner = await create_user(db_session, email="org-detail-owner@example.com")
    teammate = await create_user(db_session, email="org-detail-teammate@example.com", full_name="Teammate")
    organization = await create_organization(db_session, owner=owner, name="Initech", slug="initech", plan_id="pro")
    await add_member(db_session, organization=organization, user=teammate, role=OrgRole.ADMIN)
    subscription = await create_subscription(db_session, organization=organization)
    db_session.add(
        Payment(
            organization_id=organization.id,
            provider="stripe",
            provider_payment_id="pi_test_1",
            amount_cents=1900,
            currency="usd",
            status=PaymentStatus.SUCCEEDED,
            paid_at=datetime(2026, 3, 1, tzinfo=UTC),
            invoice_url=None,
        )
    )
    await db_session.flush()

    response = await client.get(
        f"/api/admin/organizations/{organization.id}", headers=await auth_headers(admin, settings=settings)
    )

    assert response.status_code == 200, response.text
    detail = response.json()
    assert detail["members_count"] == 2
    assert [(member["email"], member["role"]) for member in detail["members"]] == [
        ("org-detail-owner@example.com", "owner"),
        ("org-detail-teammate@example.com", "admin"),
    ]
    assert detail["subscription"]["id"] == str(subscription.id)
    assert detail["subscription"]["status"] == "active"
    assert [payment["amount_cents"] for payment in detail["payments"]] == [1900]


async def test_organization_detail_returns_404_for_unknown_id(client, db_session, settings) -> None:
    admin = await create_user(db_session, email="org-404-admin@example.com", platform_role=PlatformRole.ADMIN)

    response = await client.get(
        f"/api/admin/organizations/{uuid.uuid4()}", headers=await auth_headers(admin, settings=settings)
    )

    assert response.status_code == 404


async def test_plan_override_sets_and_clears_the_effective_plan(client, db_session, settings) -> None:
    admin = await create_user(db_session, email="override-admin@example.com", platform_role=PlatformRole.ADMIN)
    owner = await create_user(db_session, email="override-owner@example.com")
    organization = await create_organization(db_session, owner=owner, slug="override-org", plan_id="free")
    headers = await auth_headers(admin, settings=settings)
    path = f"/api/admin/organizations/{organization.id}/plan-override"

    granted = await client.post(path, json={"plan_id": "pro", "reason": "Partner deal"}, headers=headers)

    assert granted.status_code == 200, granted.text
    assert granted.json()["plan_id"] == "pro"
    assert granted.json()["plan_override_id"] == "pro"
    assert granted.json()["plan_override_reason"] == "Partner deal"

    cleared = await client.post(path, json={"plan_id": None, "reason": "Deal ended"}, headers=headers)

    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["plan_id"] == "free"
    assert cleared.json()["plan_override_id"] is None


async def test_plan_override_validates_plan_and_reason(client, db_session, settings) -> None:
    admin = await create_user(db_session, email="override-admin-2@example.com", platform_role=PlatformRole.ADMIN)
    owner = await create_user(db_session, email="override-owner-2@example.com")
    organization = await create_organization(db_session, owner=owner, slug="override-org-2")
    headers = await auth_headers(admin, settings=settings)
    path = f"/api/admin/organizations/{organization.id}/plan-override"

    unknown_plan = await client.post(path, json={"plan_id": "enterprise", "reason": "Big customer"}, headers=headers)
    short_reason = await client.post(path, json={"plan_id": "pro", "reason": "  x "}, headers=headers)

    assert unknown_plan.status_code == 400
    assert unknown_plan.json()["error"]["code"] == "plan_unavailable"
    assert short_reason.status_code == 422
