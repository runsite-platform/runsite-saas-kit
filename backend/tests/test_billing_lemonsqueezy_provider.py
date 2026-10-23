import json
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
import respx

from app.config.settings import Settings
from app.models.enums import BillingInterval, PaymentStatus, SubscriptionStatus
from app.services.billing.plans import PLANS
from app.services.billing.providers.base import (
    BillingProviderError,
    PaymentSnapshot,
    SubscriptionSnapshot,
    WebhookSignatureError,
    sign_organization_id,
)
from app.services.billing.providers.lemonsqueezy_provider import LEMONSQUEEZY_API_URL, LemonSqueezyProvider
from tests.conftest import make_settings
from tests.fakes import TEST_LEMONSQUEEZY_SETTINGS, lemonsqueezy_webhook_headers, load_webhook_body

CHECKOUT_URL = "https://acme.lemonsqueezy.com/checkout/custom/4f0b6c1e-0d2c-4a51-9c67-1d2a4f1e9b77"
PORTAL_URL = "https://acme.lemonsqueezy.com/billing?expires=1792800000&signature=fresh"


@pytest.fixture
def settings() -> Settings:
    return make_settings(**TEST_LEMONSQUEEZY_SETTINGS)


@pytest.fixture
def provider(settings) -> LemonSqueezyProvider:
    return LemonSqueezyProvider(settings)


def organization_stub(**overrides: object) -> SimpleNamespace:
    values = {"id": uuid4(), "slug": "acme", "billing_provider": None, "billing_customer_id": None}
    return SimpleNamespace(**{**values, **overrides})


def customer_document(portal_url: str | None) -> dict:
    return {"data": {"type": "customers", "id": "7001", "attributes": {"urls": {"customer_portal": portal_url}}}}


def parse_fixture(provider: LemonSqueezyProvider, name: str, organization_id=None):
    body = load_webhook_body("lemonsqueezy", name, organization_id=organization_id)
    return provider.parse_webhook(body, lemonsqueezy_webhook_headers(body, name))


async def test_create_checkout_posts_a_json_api_document(provider) -> None:
    organization = organization_stub()
    with respx.mock(assert_all_called=True) as respx_mock:
        route = respx_mock.post(f"{LEMONSQUEEZY_API_URL}/checkouts").mock(
            return_value=httpx.Response(
                201, json={"data": {"type": "checkouts", "id": "chk_1", "attributes": {"url": CHECKOUT_URL}}}
            )
        )

        url = await provider.create_checkout(
            organization,
            PLANS["pro"],
            BillingInterval.YEARLY,
            "owner@example.com",
            "https://app.test/app/acme/billing?checkout=success",
            "https://app.test/app/acme/billing?checkout=canceled",
        )

    request = route.calls.last.request
    assert url == CHECKOUT_URL
    assert request.headers["Authorization"] == "Bearer ls_test_api_key"
    assert request.headers["Accept"] == "application/vnd.api+json"
    assert request.headers["Content-Type"] == "application/vnd.api+json"
    assert json.loads(request.content) == {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "email": "owner@example.com",
                    "custom": {
                        "organization_id": str(organization.id),
                        "plan_id": "pro",
                        "interval": "yearly",
                        "organization_signature": sign_organization_id(organization.id, "ls_test_signing_secret"),
                    },
                },
                "product_options": {"redirect_url": "https://app.test/app/acme/billing?checkout=success"},
            },
            "relationships": {
                "store": {"data": {"type": "stores", "id": "9001"}},
                "variant": {"data": {"type": "variants", "id": "102"}},
            },
        }
    }


async def test_create_checkout_wraps_api_errors(provider) -> None:
    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.post(f"{LEMONSQUEEZY_API_URL}/checkouts").mock(
            return_value=httpx.Response(422, json={"errors": [{"detail": "variant not found"}]})
        )
        with pytest.raises(BillingProviderError, match="422"):
            await provider.create_checkout(
                organization_stub(),
                PLANS["pro"],
                BillingInterval.MONTHLY,
                "owner@example.com",
                "https://s",
                "https://c",
            )


async def test_portal_url_comes_from_the_customer_object(provider) -> None:
    organization = organization_stub(billing_provider="lemonsqueezy", billing_customer_id="7001")
    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get(f"{LEMONSQUEEZY_API_URL}/customers/7001").mock(
            return_value=httpx.Response(200, json=customer_document(PORTAL_URL))
        )
        assert await provider.create_portal_url(organization, "https://app.test/billing") == PORTAL_URL


async def test_portal_without_url_is_a_provider_error(provider) -> None:
    organization = organization_stub(billing_provider="lemonsqueezy", billing_customer_id="7001")
    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get(f"{LEMONSQUEEZY_API_URL}/customers/7001").mock(
            return_value=httpx.Response(200, json=customer_document(None))
        )
        with pytest.raises(BillingProviderError):
            await provider.create_portal_url(organization, "https://app.test/billing")


async def test_cancel_deletes_the_subscription(provider) -> None:
    subscription = SimpleNamespace(provider_subscription_id="4501")
    with respx.mock(assert_all_called=True) as respx_mock:
        route = respx_mock.delete(f"{LEMONSQUEEZY_API_URL}/subscriptions/4501").mock(
            return_value=httpx.Response(200, json={"data": {"type": "subscriptions", "id": "4501"}})
        )
        await provider.cancel_subscription(subscription)
        await provider.cancel_subscription(subscription, at_period_end=False)

    assert route.call_count == 2


def test_parse_webhook_rejects_bad_signatures(provider) -> None:
    body = load_webhook_body("lemonsqueezy", "subscription_created")

    with pytest.raises(WebhookSignatureError):
        provider.parse_webhook(body, {"Content-Type": "application/json"})
    with pytest.raises(WebhookSignatureError):
        provider.parse_webhook(body, {"X-Signature": "0" * 64})
    with pytest.raises(WebhookSignatureError):
        provider.parse_webhook(body + b" ", lemonsqueezy_webhook_headers(body, "subscription_created"))


def test_subscription_created_is_normalised(provider) -> None:
    organization_id = uuid4()

    event = parse_fixture(provider, "subscription_created", organization_id)
    same_event = parse_fixture(provider, "subscription_created", organization_id)

    assert event.event_id.startswith("subscription_created:")
    assert event.event_id == same_event.event_id
    assert event.event_type == "subscription_created"
    assert event.kind == "subscription_created"
    assert event.organization_id == organization_id
    assert event.subscription == SubscriptionSnapshot(
        provider_subscription_id="4501",
        status=SubscriptionStatus.TRIALING,
        customer_id="7001",
        price_reference="101",
        interval_hint=BillingInterval.MONTHLY,
        current_period_end=datetime(2026, 11, 6, 10, 0, tzinfo=UTC),
        cancel_at_period_end=False,
        trial_ends_at=datetime(2026, 11, 6, 10, 0, tzinfo=UTC),
    )


def test_unsigned_or_tampered_organization_id_is_not_trusted(provider) -> None:
    victim_organization_id = uuid4()
    body = load_webhook_body("lemonsqueezy", "subscription_created", organization_id=uuid4())
    payload = json.loads(body)
    payload["meta"]["custom_data"]["organization_id"] = str(victim_organization_id)
    tampered = json.dumps(payload).encode()
    del payload["meta"]["custom_data"]["organization_signature"]
    unsigned = json.dumps(payload).encode()

    for forged_body in (tampered, unsigned):
        event = provider.parse_webhook(forged_body, lemonsqueezy_webhook_headers(forged_body, "subscription_created"))
        assert event.organization_id is None


def test_cancelled_keeps_access_until_period_end_and_expired_ends_it(provider) -> None:
    updated = parse_fixture(provider, "subscription_updated")
    cancelled = parse_fixture(provider, "subscription_cancelled")
    expired = parse_fixture(provider, "subscription_expired")

    assert updated.kind == "subscription_updated"
    assert updated.subscription is not None
    assert updated.subscription.status == SubscriptionStatus.ACTIVE
    assert updated.subscription.current_period_end == datetime(2026, 12, 6, 10, 0, tzinfo=UTC)
    assert cancelled.kind == "subscription_updated"
    assert cancelled.subscription is not None
    assert cancelled.subscription.status == SubscriptionStatus.ACTIVE
    assert cancelled.subscription.cancel_at_period_end is True
    assert cancelled.subscription.current_period_end == datetime(2026, 12, 6, 10, 0, tzinfo=UTC)
    assert expired.kind == "subscription_canceled"
    assert expired.subscription is not None
    assert expired.subscription.status == SubscriptionStatus.EXPIRED


def test_invoice_events_become_payments_without_organization(provider) -> None:
    paid = parse_fixture(provider, "subscription_payment_success")
    failed = parse_fixture(provider, "subscription_payment_failed")

    assert paid.kind == "payment_succeeded"
    assert paid.organization_id is None
    assert paid.subscription is None
    assert paid.payment == PaymentSnapshot(
        provider_payment_id="9101",
        amount_cents=1900,
        currency="USD",
        status=PaymentStatus.SUCCEEDED,
        provider_subscription_id="4501",
        paid_at=datetime(2026, 11, 6, 10, 0, 7, tzinfo=UTC),
        invoice_url="https://app.lemonsqueezy.com/my-orders/0d6f3c1e/subscription-invoice/9101?signature=test",
    )
    assert failed.kind == "payment_failed"
    assert failed.payment is not None
    assert failed.payment.status == PaymentStatus.FAILED
    assert failed.payment.paid_at is None
    assert failed.payment.invoice_url is None


def test_unhandled_events_are_ignored(provider) -> None:
    body = json.dumps({"meta": {"event_name": "order_created"}, "data": {"type": "orders", "id": "1"}}).encode()

    event = provider.parse_webhook(body, lemonsqueezy_webhook_headers(body, "order_created"))

    assert event.kind == "ignored"
    assert event.event_type == "order_created"


async def test_webhook_route_rejects_a_bad_lemonsqueezy_signature(client) -> None:
    body = load_webhook_body("lemonsqueezy", "subscription_created")

    response = await client.post(
        "/api/webhooks/billing/lemonsqueezy",
        content=body,
        headers={"Content-Type": "application/json", "X-Signature": "a" * 64},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_webhook"
