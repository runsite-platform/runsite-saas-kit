import json
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
import respx

from app.config.settings import Settings
from app.constants.enums import BillingInterval, PaymentStatus, SubscriptionStatus
from app.services.billing.plans import PLANS
from app.services.billing.providers.base import (
    BillingProviderError,
    PaymentSnapshot,
    SubscriptionSnapshot,
    WebhookSignatureError,
)
from app.services.billing.providers.creem_provider import CreemProvider
from tests.conftest import make_settings
from tests.factories import create_organization, create_user
from tests.fakes import TEST_CREEM_SETTINGS, creem_webhook_headers, load_webhook_body

CREEM_TEST_API_URL = TEST_CREEM_SETTINGS["CREEM_API_URL"]
CHECKOUT_URL = "https://checkout.creem.io/ch_RunsiteKit0001"
PORTAL_URL = "https://creem.io/my-orders/login/xyz"
PERIOD_END = datetime(2026, 11, 23, 10, 0, tzinfo=UTC)


@pytest.fixture
def settings() -> Settings:
    return make_settings(**TEST_CREEM_SETTINGS)


@pytest.fixture
def provider(settings) -> CreemProvider:
    return CreemProvider(settings)


def organization_stub(**overrides: object) -> SimpleNamespace:
    values = {"id": uuid4(), "slug": "acme", "billing_provider": None, "billing_customer_id": None}
    return SimpleNamespace(**{**values, **overrides})


def parse_fixture(provider: CreemProvider, name: str, organization_id=None):
    body = load_webhook_body("creem", name, organization_id=organization_id)
    return provider.parse_webhook(body, creem_webhook_headers(body))


async def test_create_checkout_posts_product_and_metadata(provider) -> None:
    organization = organization_stub()
    with respx.mock(assert_all_called=True) as respx_mock:
        route = respx_mock.post(f"{CREEM_TEST_API_URL}/v1/checkouts").mock(
            return_value=httpx.Response(200, json={"id": "ch_RunsiteKit0001", "checkout_url": CHECKOUT_URL})
        )

        url = await provider.create_checkout(
            organization,
            PLANS["pro"],
            BillingInterval.MONTHLY,
            "owner@example.com",
            "https://app.test/app/acme/billing?checkout=success",
            "https://app.test/app/acme/billing?checkout=canceled",
        )

    request = route.calls.last.request
    assert url == CHECKOUT_URL
    assert request.headers["x-api-key"] == "creem_test_api_key"
    assert json.loads(request.content) == {
        "product_id": "prod_pro_monthly_test",
        "success_url": "https://app.test/app/acme/billing?checkout=success",
        "customer": {"email": "owner@example.com"},
        "metadata": {"organization_id": str(organization.id), "plan_id": "pro", "interval": "monthly"},
    }


async def test_create_checkout_wraps_api_errors(provider) -> None:
    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.post(f"{CREEM_TEST_API_URL}/v1/checkouts").mock(side_effect=httpx.ConnectTimeout("timed out"))
        with pytest.raises(BillingProviderError, match="timed out"):
            await provider.create_checkout(
                organization_stub(),
                PLANS["pro"],
                BillingInterval.MONTHLY,
                "owner@example.com",
                "https://s",
                "https://c",
            )


async def test_portal_and_cancel_requests(provider) -> None:
    organization = organization_stub(billing_provider="creem", billing_customer_id="cust_RunsiteKit0001")
    subscription = SimpleNamespace(provider_subscription_id="sub_RunsiteKit0001")
    with respx.mock(assert_all_called=True) as respx_mock:
        portal_route = respx_mock.post(f"{CREEM_TEST_API_URL}/v1/customers/billing").mock(
            return_value=httpx.Response(200, json={"customer_portal_link": PORTAL_URL})
        )
        cancel_route = respx_mock.post(f"{CREEM_TEST_API_URL}/v1/subscriptions/sub_RunsiteKit0001/cancel").mock(
            return_value=httpx.Response(200, json={"id": "sub_RunsiteKit0001", "status": "scheduled_cancel"})
        )

        portal_url = await provider.create_portal_url(organization, "https://app.test/billing")
        await provider.cancel_subscription(subscription)
        await provider.cancel_subscription(subscription, at_period_end=False)

    assert portal_url == PORTAL_URL
    assert json.loads(portal_route.calls.last.request.content) == {"customer_id": "cust_RunsiteKit0001"}
    assert [json.loads(call.request.content) for call in cancel_route.calls] == [
        {"mode": "scheduled", "onExecute": "cancel"},
        {"mode": "immediate"},
    ]


def test_parse_webhook_rejects_bad_signatures(provider) -> None:
    body = load_webhook_body("creem", "checkout_completed")

    with pytest.raises(WebhookSignatureError):
        provider.parse_webhook(body, {})
    with pytest.raises(WebhookSignatureError):
        provider.parse_webhook(body, {"creem-signature": "f" * 64})
    with pytest.raises(WebhookSignatureError):
        provider.parse_webhook(body.replace(b"every-month", b"every-year"), creem_webhook_headers(body))


def test_checkout_completed_creates_the_subscription(provider) -> None:
    organization_id = uuid4()

    event = parse_fixture(provider, "checkout_completed", organization_id)

    assert event.event_id == "evt_RunsiteCheckoutDone01"
    assert event.event_type == "checkout.completed"
    assert event.kind == "subscription_created"
    assert event.organization_id == organization_id
    assert event.subscription == SubscriptionSnapshot(
        provider_subscription_id="sub_RunsiteKit0001",
        status=SubscriptionStatus.ACTIVE,
        customer_id="cust_RunsiteKit0001",
        price_reference="prod_pro_monthly_test",
        interval_hint=BillingInterval.MONTHLY,
        current_period_end=None,
        cancel_at_period_end=False,
        trial_ends_at=None,
    )


def test_subscription_paid_carries_subscription_and_payment(provider) -> None:
    organization_id = uuid4()

    event = parse_fixture(provider, "subscription_paid", organization_id)

    assert event.kind == "payment_succeeded"
    assert event.organization_id == organization_id
    assert event.subscription is not None
    assert event.subscription.status == SubscriptionStatus.ACTIVE
    assert event.subscription.current_period_end == PERIOD_END
    assert event.payment == PaymentSnapshot(
        provider_payment_id="tran_RunsiteKit0001",
        amount_cents=1900,
        currency="USD",
        status=PaymentStatus.SUCCEEDED,
        provider_subscription_id="sub_RunsiteKit0001",
        paid_at=datetime(2026, 10, 23, 10, 0, 5, tzinfo=UTC),
        invoice_url=None,
    )


def test_subscription_active_without_metadata_has_no_organization(provider) -> None:
    event = parse_fixture(provider, "subscription_active")

    assert event.kind == "subscription_created"
    assert event.organization_id is None
    assert event.subscription is not None
    assert event.subscription.customer_id == "cust_RunsiteKit0001"


def test_trialing_yearly_subscription(provider) -> None:
    event = parse_fixture(provider, "subscription_trialing")

    assert event.subscription is not None
    assert event.subscription.status == SubscriptionStatus.TRIALING
    assert event.subscription.price_reference == "prod_pro_yearly_test"
    assert event.subscription.interval_hint == BillingInterval.YEARLY
    assert event.subscription.trial_ends_at == datetime(2026, 11, 6, 10, 0, tzinfo=UTC)


def test_cancellation_events(provider) -> None:
    scheduled = parse_fixture(provider, "subscription_scheduled_cancel")
    canceled = parse_fixture(provider, "subscription_canceled")
    expired = parse_fixture(provider, "subscription_expired")

    assert scheduled.kind == "subscription_updated"
    assert scheduled.subscription is not None
    assert scheduled.subscription.status == SubscriptionStatus.ACTIVE
    assert scheduled.subscription.cancel_at_period_end is True
    assert canceled.kind == "subscription_canceled"
    assert canceled.subscription is not None
    assert canceled.subscription.status == SubscriptionStatus.CANCELED
    assert expired.kind == "subscription_canceled"
    assert expired.subscription is not None
    assert expired.subscription.status == SubscriptionStatus.EXPIRED


def test_unhandled_events_are_ignored(provider) -> None:
    body = json.dumps(
        {"id": "evt_refund", "eventType": "refund.created", "created_at": 1, "object": {"id": "ref_1"}}
    ).encode()

    event = provider.parse_webhook(body, creem_webhook_headers(body))

    assert event.kind == "ignored"
    assert event.event_id == "evt_refund"


async def test_webhook_route_rejects_a_bad_creem_signature(client) -> None:
    body = load_webhook_body("creem", "checkout_completed")

    response = await client.post(
        "/api/webhooks/billing/creem",
        content=body,
        headers={"Content-Type": "application/json", "creem-signature": "b" * 64},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_webhook"


async def test_webhook_route_applies_checkout_then_metadata_free_activation(client, db_session) -> None:
    owner = await create_user(db_session, email="creem-webhook@example.com")
    organization = await create_organization(db_session, owner=owner)
    checkout_body = load_webhook_body("creem", "checkout_completed", organization_id=organization.id)
    active_body = load_webhook_body("creem", "subscription_active")

    checkout = await client.post(
        "/api/webhooks/billing/creem", content=checkout_body, headers=creem_webhook_headers(checkout_body)
    )
    active = await client.post(
        "/api/webhooks/billing/creem", content=active_body, headers=creem_webhook_headers(active_body)
    )

    assert checkout.json() == {"status": "processed"}
    assert active.json() == {"status": "processed"}
    assert organization.plan_id == "pro"
    assert organization.billing_customer_id == "cust_RunsiteKit0001"
