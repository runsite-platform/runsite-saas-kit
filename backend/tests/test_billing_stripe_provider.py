import time
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
import stripe

from app.config.settings import Settings
from app.constants.enums import BillingInterval, PaymentStatus, SubscriptionStatus
from app.services.billing.plans import PLANS
from app.services.billing.providers.base import (
    BillingProviderError,
    PaymentSnapshot,
    SubscriptionSnapshot,
    WebhookPayloadError,
    WebhookSignatureError,
)
from app.services.billing.providers.stripe_provider import StripeProvider
from tests.conftest import make_settings
from tests.factories import create_organization, create_user
from tests.fakes import (
    FAKE_STRIPE_CHECKOUT_URL,
    FAKE_STRIPE_PORTAL_URL,
    TEST_STRIPE_SETTINGS,
    FakeStripeClient,
    load_webhook_body,
    stripe_signature_header,
    stripe_webhook_headers,
)

WEBHOOK_SECRET = TEST_STRIPE_SETTINGS["STRIPE_WEBHOOK_SECRET"]
TRIAL_END = datetime(2026, 11, 6, tzinfo=UTC)
FIRST_PERIOD_END = datetime(2026, 12, 6, tzinfo=UTC)


@pytest.fixture
def settings() -> Settings:
    return make_settings(**TEST_STRIPE_SETTINGS)


@pytest.fixture
def fake_stripe_client() -> FakeStripeClient:
    return FakeStripeClient()


@pytest.fixture
def provider(settings, fake_stripe_client) -> StripeProvider:
    return StripeProvider(settings, client=fake_stripe_client)


def organization_stub(**overrides: object) -> SimpleNamespace:
    values = {"id": uuid4(), "slug": "acme", "billing_provider": None, "billing_customer_id": None}
    return SimpleNamespace(**{**values, **overrides})


def parse_fixture(provider: StripeProvider, name: str, organization_id=None):
    body = load_webhook_body("stripe", name, organization_id=organization_id)
    return provider.parse_webhook(body, stripe_webhook_headers(body))


async def test_create_checkout_builds_a_subscription_session(provider, fake_stripe_client) -> None:
    organization = organization_stub()

    url = await provider.create_checkout(
        organization,
        PLANS["pro"],
        BillingInterval.MONTHLY,
        "owner@example.com",
        "https://app.test/app/acme/billing?checkout=success",
        "https://app.test/app/acme/billing?checkout=canceled",
    )

    metadata = {"organization_id": str(organization.id), "plan_id": "pro", "interval": "monthly"}
    assert url == FAKE_STRIPE_CHECKOUT_URL
    assert fake_stripe_client.create_checkout_session.calls == [
        (
            (),
            {
                "params": {
                    "mode": "subscription",
                    "line_items": [{"price": "price_pro_monthly_test", "quantity": 1}],
                    "success_url": "https://app.test/app/acme/billing?checkout=success",
                    "cancel_url": "https://app.test/app/acme/billing?checkout=canceled",
                    "client_reference_id": str(organization.id),
                    "metadata": metadata,
                    "subscription_data": {"metadata": metadata, "trial_period_days": 14},
                    "customer_email": "owner@example.com",
                }
            },
        )
    ]


async def test_create_checkout_reuses_the_known_customer(provider, fake_stripe_client) -> None:
    organization = organization_stub(billing_provider="stripe", billing_customer_id="cus_existing")

    await provider.create_checkout(
        organization, PLANS["pro"], BillingInterval.YEARLY, "owner@example.com", "https://s", "https://c"
    )

    params = fake_stripe_client.create_checkout_session.calls[0][1]["params"]
    assert params["customer"] == "cus_existing"
    assert "customer_email" not in params
    assert params["line_items"] == [{"price": "price_pro_yearly_test", "quantity": 1}]


async def test_create_checkout_wraps_stripe_errors(provider, fake_stripe_client) -> None:
    fake_stripe_client.create_checkout_session.result = stripe.APIConnectionError("network down")

    with pytest.raises(BillingProviderError, match="network down"):
        await provider.create_checkout(
            organization_stub(), PLANS["pro"], BillingInterval.MONTHLY, "owner@example.com", "https://s", "https://c"
        )


async def test_portal_and_cancel_call_stripe(provider, fake_stripe_client) -> None:
    organization = organization_stub(billing_provider="stripe", billing_customer_id="cus_existing")
    subscription = SimpleNamespace(provider_subscription_id="sub_123")

    portal_url = await provider.create_portal_url(organization, "https://app.test/app/acme/billing")
    await provider.cancel_subscription(subscription)
    await provider.cancel_subscription(subscription, at_period_end=False)

    assert portal_url == FAKE_STRIPE_PORTAL_URL
    assert fake_stripe_client.create_portal_session.calls == [
        ((), {"params": {"customer": "cus_existing", "return_url": "https://app.test/app/acme/billing"}})
    ]
    assert fake_stripe_client.update_subscription.calls == [(("sub_123",), {"params": {"cancel_at_period_end": True}})]
    assert fake_stripe_client.cancel_subscription.calls == [(("sub_123",), {})]


def test_parse_webhook_rejects_bad_signatures(provider) -> None:
    body = load_webhook_body("stripe", "customer_subscription_created")
    stale_header = stripe_signature_header(body, WEBHOOK_SECRET, timestamp=int(time.time()) - 3600)

    with pytest.raises(WebhookSignatureError):
        provider.parse_webhook(body, {})
    with pytest.raises(WebhookSignatureError):
        provider.parse_webhook(body, {"Stripe-Signature": stripe_signature_header(body, "whsec_wrong")})
    with pytest.raises(WebhookSignatureError):
        provider.parse_webhook(body, {"Stripe-Signature": stale_header})
    with pytest.raises(WebhookSignatureError):
        provider.parse_webhook(body.replace(b'"trialing"', b'"active"'), stripe_webhook_headers(body))


def test_subscription_created_is_normalised(provider) -> None:
    organization_id = uuid4()

    event = parse_fixture(provider, "customer_subscription_created", organization_id)

    assert event.event_id == "evt_1RunsiteSubCreated01"
    assert event.event_type == "customer.subscription.created"
    assert event.kind == "subscription_created"
    assert event.organization_id == organization_id
    assert event.payment is None
    assert event.subscription == SubscriptionSnapshot(
        provider_subscription_id="sub_1RunsiteKit0001",
        status=SubscriptionStatus.TRIALING,
        customer_id="cus_RunsiteKit0001",
        price_reference="price_pro_monthly_test",
        interval_hint=BillingInterval.MONTHLY,
        current_period_end=TRIAL_END,
        cancel_at_period_end=False,
        trial_ends_at=TRIAL_END,
    )


def test_subscription_updated_and_deleted_are_normalised(provider) -> None:
    updated = parse_fixture(provider, "customer_subscription_updated")
    deleted = parse_fixture(provider, "customer_subscription_deleted")

    assert updated.kind == "subscription_updated"
    assert updated.subscription is not None
    assert updated.subscription.status == SubscriptionStatus.ACTIVE
    assert updated.subscription.current_period_end == FIRST_PERIOD_END
    assert deleted.kind == "subscription_canceled"
    assert deleted.subscription is not None
    assert deleted.subscription.status == SubscriptionStatus.CANCELED
    assert deleted.subscription.cancel_at_period_end is True


def test_invoice_events_become_payments(provider) -> None:
    organization_id = uuid4()

    paid = parse_fixture(provider, "invoice_paid", organization_id)
    failed = parse_fixture(provider, "invoice_payment_failed", organization_id)

    assert paid.kind == "payment_succeeded"
    assert paid.organization_id == organization_id
    assert paid.subscription is None
    assert paid.payment == PaymentSnapshot(
        provider_payment_id="in_1RunsiteInvoice0001",
        amount_cents=1900,
        currency="USD",
        status=PaymentStatus.SUCCEEDED,
        provider_subscription_id="sub_1RunsiteKit0001",
        paid_at=datetime(2026, 11, 6, 0, 1, tzinfo=UTC),
        invoice_url="https://invoice.stripe.com/i/acct_test/test_runsite_kit_paid",
    )
    assert failed.kind == "payment_failed"
    assert failed.payment is not None
    assert failed.payment.status == PaymentStatus.FAILED
    assert failed.payment.amount_cents == 1900
    assert failed.payment.paid_at is None


def test_checkout_completed_is_ignored(provider) -> None:
    event = parse_fixture(provider, "checkout_session_completed")

    assert event.kind == "ignored"
    assert event.subscription is None
    assert event.payment is None


def test_unknown_subscription_status_never_grants_access(provider) -> None:
    body = load_webhook_body("stripe", "customer_subscription_created").replace(b'"trialing"', b'"brand_new_status"')

    event = provider.parse_webhook(body, stripe_webhook_headers(body))

    assert event.subscription is not None
    assert event.subscription.status == SubscriptionStatus.PAST_DUE


def test_signed_but_malformed_payload_is_rejected(provider) -> None:
    body = b'{"id": "evt_broken", "object": "event", "type": "customer.subscription.created", "data": {"object": {}}}'

    with pytest.raises(WebhookPayloadError):
        provider.parse_webhook(body, stripe_webhook_headers(body))


async def test_webhook_route_rejects_a_bad_stripe_signature(client) -> None:
    body = load_webhook_body("stripe", "customer_subscription_created")

    response = await client.post(
        "/api/webhooks/billing/stripe",
        content=body,
        headers={"Content-Type": "application/json", "Stripe-Signature": stripe_signature_header(body, "whsec_wrong")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_webhook"


async def test_webhook_route_applies_a_signed_stripe_event(client, db_session) -> None:
    owner = await create_user(db_session, email="stripe-webhook@example.com")
    organization = await create_organization(db_session, owner=owner)
    body = load_webhook_body("stripe", "customer_subscription_created", organization_id=organization.id)

    response = await client.post("/api/webhooks/billing/stripe", content=body, headers=stripe_webhook_headers(body))

    assert response.status_code == 200
    assert response.json() == {"status": "processed"}
    assert organization.plan_id == "pro"
    assert organization.billing_customer_id == "cus_RunsiteKit0001"
