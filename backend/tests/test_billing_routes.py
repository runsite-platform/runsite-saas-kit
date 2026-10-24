from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
import stripe

from app.config.settings import Settings
from app.constants.enums import OrgRole, PaymentStatus, SubscriptionStatus
from app.models import Payment
from app.services.billing.billing_service import BillingService
from app.services.billing.providers.stripe_provider import StripeProvider
from app.utils.dependencies import get_payment_provider
from tests.conftest import make_settings
from tests.factories import add_member, auth_headers, create_organization, create_subscription, create_user
from tests.fakes import FAKE_STRIPE_CHECKOUT_URL, FAKE_STRIPE_PORTAL_URL, TEST_STRIPE_SETTINGS, FakeStripeClient


@pytest.fixture
def settings() -> Settings:
    return make_settings(**TEST_STRIPE_SETTINGS)


@pytest.fixture
def fake_stripe_client() -> FakeStripeClient:
    return FakeStripeClient()


@pytest.fixture(autouse=True)
def stripe_provider(app, settings, fake_stripe_client) -> StripeProvider:
    provider = StripeProvider(settings, client=fake_stripe_client)
    app.dependency_overrides[get_payment_provider] = lambda: provider
    return provider


@pytest.fixture
async def team(db_session) -> SimpleNamespace:
    owner = await create_user(db_session, email="owner@example.com")
    organization = await create_organization(db_session, owner=owner, slug="acme")
    admin = await create_user(db_session, email="admin@example.com")
    member = await create_user(db_session, email="member@example.com")
    outsider = await create_user(db_session, email="outsider@example.com")
    await add_member(db_session, organization=organization, user=admin, role=OrgRole.ADMIN)
    await add_member(db_session, organization=organization, user=member, role=OrgRole.MEMBER)
    return SimpleNamespace(organization=organization, owner=owner, admin=admin, member=member, outsider=outsider)


def billing_path(team: SimpleNamespace, suffix: str = "") -> str:
    return f"/api/orgs/{team.organization.id}/billing{suffix}"


async def test_plans_are_public(client) -> None:
    response = await client.get("/api/plans")

    assert response.status_code == 200
    plans = {plan["id"]: plan for plan in response.json()}
    assert plans["free"]["available"] == {"monthly": True, "yearly": True}
    assert plans["free"]["features"] == ["file_uploads"]
    assert plans["pro"] == {
        "id": "pro",
        "name": "Pro",
        "price_monthly_cents": 1900,
        "price_yearly_cents": 19000,
        "trial_days": 14,
        "limits": {"members": 10, "projects": 100, "storage_mb": 5000},
        "features": ["analytics", "file_uploads"],
        "available": {"monthly": True, "yearly": True},
    }


async def test_overview_is_visible_to_every_member(client, settings, team) -> None:
    response = await client.get(billing_path(team), headers=await auth_headers(team.member, settings=settings))

    assert response.status_code == 200
    body = response.json()
    assert body["plan"]["id"] == "free"
    assert body["subscription"] is None
    assert body["plan_override"] is None
    assert body["usage"] == {"members": 3, "projects": 0, "storage_bytes": 0}
    assert body["billing_enabled"] is True
    assert body["provider"] == "stripe"


async def test_overview_is_hidden_from_outsiders(client, settings, team) -> None:
    response = await client.get(billing_path(team), headers=await auth_headers(team.outsider, settings=settings))

    assert response.status_code == 404


async def test_overview_reports_subscription_and_override(client, db_session, settings, team, stripe_provider) -> None:
    await create_subscription(db_session, organization=team.organization, status=SubscriptionStatus.TRIALING)
    service = BillingService(db_session, settings, stripe_provider)
    await service.set_plan_override(team.organization, "pro", "Launch partner")

    body = (await client.get(billing_path(team), headers=await auth_headers(team.owner, settings=settings))).json()

    assert body["plan"]["id"] == "pro"
    assert body["plan_override"] == {"plan_id": "pro", "reason": "Launch partner"}
    assert body["subscription"]["status"] == "trialing"
    assert body["subscription"]["provider"] == "stripe"
    assert body["subscription"]["cancel_at_period_end"] is False


async def test_owner_and_admin_can_start_checkout(client, settings, team, fake_stripe_client) -> None:
    for user in (team.owner, team.admin):
        response = await client.post(
            billing_path(team, "/checkout"),
            json={"plan_id": "pro", "interval": "monthly"},
            headers=await auth_headers(user, settings=settings),
        )
        assert response.status_code == 200
        assert response.json() == {"url": FAKE_STRIPE_CHECKOUT_URL}

    params = fake_stripe_client.create_checkout_session.calls[0][1]["params"]
    assert params["success_url"] == "http://testserver/app/acme/billing?checkout=success"
    assert params["cancel_url"] == "http://testserver/app/acme/billing?checkout=canceled"
    assert params["customer_email"] == "owner@example.com"
    assert params["client_reference_id"] == str(team.organization.id)


async def test_member_cannot_manage_billing_and_outsider_sees_nothing(client, settings, team) -> None:
    for suffix, payload in (
        ("/checkout", {"plan_id": "pro", "interval": "monthly"}),
        ("/portal", None),
        ("/cancel", None),
    ):
        member_response = await client.post(
            billing_path(team, suffix), json=payload, headers=await auth_headers(team.member, settings=settings)
        )
        outsider_response = await client.post(
            billing_path(team, suffix), json=payload, headers=await auth_headers(team.outsider, settings=settings)
        )
        assert member_response.status_code == 403, suffix
        assert member_response.json()["error"]["code"] == "forbidden"
        assert outsider_response.status_code == 404, suffix


async def test_checkout_requires_a_verified_email_when_enforced(client, db_session, settings) -> None:
    settings.REQUIRE_EMAIL_VERIFICATION = True
    owner = await create_user(db_session, email="unverified@example.com", is_email_verified=False)
    organization = await create_organization(db_session, owner=owner, slug="unverified")

    response = await client.post(
        f"/api/orgs/{organization.id}/billing/checkout",
        json={"plan_id": "pro", "interval": "monthly"},
        headers=await auth_headers(owner, settings=settings),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "email_not_verified"


@pytest.mark.parametrize(
    ("payload", "status_code", "error_code"),
    [
        ({"plan_id": "free", "interval": "monthly"}, 400, "plan_unavailable"),
        ({"plan_id": "enterprise", "interval": "yearly"}, 400, "plan_unavailable"),
        ({"plan_id": "pro", "interval": "weekly"}, 422, "validation_error"),
    ],
)
async def test_checkout_rejects_unavailable_plans(client, settings, team, payload, status_code, error_code) -> None:
    response = await client.post(
        billing_path(team, "/checkout"), json=payload, headers=await auth_headers(team.owner, settings=settings)
    )

    assert response.status_code == status_code
    if status_code == 400:
        assert response.json()["error"]["code"] == error_code


async def test_checkout_is_refused_while_a_subscription_exists(client, db_session, settings, team) -> None:
    await create_subscription(db_session, organization=team.organization, status=SubscriptionStatus.PAST_DUE)

    response = await client.post(
        billing_path(team, "/checkout"),
        json={"plan_id": "pro", "interval": "monthly"},
        headers=await auth_headers(team.owner, settings=settings),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "active_subscription"


async def test_provider_failure_is_a_502(client, settings, team, fake_stripe_client) -> None:
    fake_stripe_client.create_checkout_session.result = stripe.APIConnectionError("stripe unreachable")

    response = await client.post(
        billing_path(team, "/checkout"),
        json={"plan_id": "pro", "interval": "yearly"},
        headers=await auth_headers(team.owner, settings=settings),
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "billing_provider_error"


async def test_portal_needs_a_billing_account(client, db_session, settings, team, fake_stripe_client) -> None:
    missing = await client.post(
        billing_path(team, "/portal"), headers=await auth_headers(team.owner, settings=settings)
    )
    team.organization.billing_provider = "stripe"
    team.organization.billing_customer_id = "cus_portal"
    await db_session.flush()

    response = await client.post(
        billing_path(team, "/portal"), headers=await auth_headers(team.admin, settings=settings)
    )

    assert missing.status_code == 404
    assert response.status_code == 200
    assert response.json() == {"url": FAKE_STRIPE_PORTAL_URL}
    assert fake_stripe_client.create_portal_session.calls[0][1]["params"] == {
        "customer": "cus_portal",
        "return_url": "http://testserver/app/acme/billing",
    }


async def test_cancel_sets_cancel_at_period_end(client, db_session, settings, team, fake_stripe_client) -> None:
    missing = await client.post(
        billing_path(team, "/cancel"), headers=await auth_headers(team.owner, settings=settings)
    )
    subscription = await create_subscription(db_session, organization=team.organization)

    response = await client.post(
        billing_path(team, "/cancel"), headers=await auth_headers(team.owner, settings=settings)
    )

    assert missing.status_code == 404
    assert response.status_code == 200
    assert response.json()["subscription"]["cancel_at_period_end"] is True
    assert fake_stripe_client.update_subscription.calls == [
        ((subscription.provider_subscription_id,), {"params": {"cancel_at_period_end": True}})
    ]


async def test_payment_history_is_for_billing_managers(client, db_session, settings, team) -> None:
    db_session.add(
        Payment(
            organization_id=team.organization.id,
            provider="stripe",
            provider_payment_id="in_history",
            amount_cents=1900,
            currency="USD",
            status=PaymentStatus.SUCCEEDED,
            paid_at=datetime(2026, 11, 6, tzinfo=UTC),
            invoice_url="https://invoice.stripe.com/i/history",
        )
    )
    await db_session.flush()

    owner_response = await client.get(
        billing_path(team, "/payments"), headers=await auth_headers(team.owner, settings=settings)
    )
    member_response = await client.get(
        billing_path(team, "/payments"), headers=await auth_headers(team.member, settings=settings)
    )

    assert owner_response.status_code == 200
    payments = owner_response.json()
    assert len(payments) == 1
    assert payments[0]["amount_cents"] == 1900
    assert payments[0]["status"] == "succeeded"
    assert payments[0]["invoice_url"] == "https://invoice.stripe.com/i/history"
    assert member_response.status_code == 403
