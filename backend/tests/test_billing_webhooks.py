from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.config.settings import Settings
from app.models import BillingEvent, Payment, Subscription
from tests.conftest import make_settings
from tests.factories import create_organization, create_user
from tests.fakes import TEST_LEMONSQUEEZY_SETTINGS, lemonsqueezy_webhook_headers, load_webhook_body

WEBHOOK_URL = "/api/webhooks/billing/lemonsqueezy"


@pytest.fixture
def settings() -> Settings:
    return make_settings(**TEST_LEMONSQUEEZY_SETTINGS)


@pytest.fixture
async def organization(db_session):
    owner = await create_user(db_session, email="webhook-owner@example.com")
    return await create_organization(db_session, owner=owner)


async def count_rows(db_session, model) -> int:
    return (await db_session.execute(select(func.count()).select_from(model))).scalar_one()


async def post_fixture(client, name: str, organization_id=None, body: bytes | None = None):
    payload = body if body is not None else load_webhook_body("lemonsqueezy", name, organization_id=organization_id)
    return await client.post(WEBHOOK_URL, content=payload, headers=lemonsqueezy_webhook_headers(payload, name))


async def test_signed_event_is_recorded_and_applied(client, db_session, organization) -> None:
    response = await post_fixture(client, "subscription_created", organization.id)

    assert response.status_code == 200
    assert response.json() == {"status": "processed"}
    assert organization.plan_id == "pro"
    billing_event = (await db_session.execute(select(BillingEvent))).scalar_one()
    assert billing_event.provider == "lemonsqueezy"
    assert billing_event.event_type == "subscription_created"
    assert billing_event.payload["data"]["id"] == "4501"
    assert billing_event.processed_at is not None
    assert billing_event.error is None


async def test_duplicate_delivery_is_acknowledged_without_reapplying(client, db_session, organization) -> None:
    body = load_webhook_body("lemonsqueezy", "subscription_created", organization_id=organization.id)

    first = await post_fixture(client, "subscription_created", body=body)
    second = await post_fixture(client, "subscription_created", body=body)

    assert first.json() == {"status": "processed"}
    assert second.status_code == 200
    assert second.json() == {"status": "duplicate"}
    assert await count_rows(db_session, BillingEvent) == 1
    assert await count_rows(db_session, Subscription) == 1


async def test_bad_signature_is_rejected_before_recording(client, db_session) -> None:
    body = load_webhook_body("lemonsqueezy", "subscription_created")

    response = await client.post(
        WEBHOOK_URL,
        content=body,
        headers={"Content-Type": "application/json", "X-Event-Name": "subscription_created", "X-Signature": "0" * 64},
    )
    missing = await client.post(WEBHOOK_URL, content=body, headers={"Content-Type": "application/json"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_webhook"
    assert missing.status_code == 400
    assert await count_rows(db_session, BillingEvent) == 0


async def test_other_provider_path_is_not_found(client) -> None:
    body = load_webhook_body("lemonsqueezy", "subscription_created")

    response = await client.post("/api/webhooks/billing/stripe", content=body, headers={"Stripe-Signature": "t=1,v1=x"})

    assert response.status_code == 404


def with_payment_time(body: bytes, moment: datetime) -> bytes:
    return body.replace(b"2026-11-06T10:00:07.000000Z", moment.isoformat().encode())


async def test_old_event_for_a_foreign_subscription_is_acknowledged(client, db_session) -> None:
    foreign_body = with_payment_time(
        load_webhook_body("lemonsqueezy", "subscription_payment_success"), datetime.now(UTC) - timedelta(days=1)
    )

    response = await post_fixture(client, "subscription_payment_success", body=foreign_body)

    assert response.status_code == 200
    assert response.json() == {"status": "processed"}
    assert await count_rows(db_session, Payment) == 0


async def test_failed_event_stores_the_error_and_a_retry_reprocesses_it(client, db_session, organization) -> None:
    organization_id = organization.id
    payment_body = with_payment_time(
        load_webhook_body("lemonsqueezy", "subscription_payment_success"), datetime.now(UTC)
    )

    early = await post_fixture(client, "subscription_payment_success", body=payment_body)

    assert early.status_code == 500
    assert early.json() == {"status": "failed"}
    failed_event = (await db_session.execute(select(BillingEvent))).scalar_one()
    await db_session.refresh(failed_event)
    assert failed_event.processed_at is None
    assert "Cannot resolve the organization" in (failed_event.error or "")
    assert await count_rows(db_session, Payment) == 0

    created = await post_fixture(client, "subscription_created", organization_id)
    retried = await post_fixture(client, "subscription_payment_success", body=payment_body)

    assert created.json() == {"status": "processed"}
    assert retried.status_code == 200
    assert retried.json() == {"status": "processed"}
    await db_session.refresh(failed_event)
    assert failed_event.processed_at is not None
    assert failed_event.error is None
    payment = (await db_session.execute(select(Payment))).scalar_one()
    assert payment.organization_id == organization_id
    assert payment.amount_cents == 1900


async def test_expiry_returns_the_organization_to_free(client, db_session, organization) -> None:
    await post_fixture(client, "subscription_created", organization.id)
    await post_fixture(client, "subscription_cancelled", organization.id)
    assert organization.plan_id == "pro"

    response = await post_fixture(client, "subscription_expired", organization.id)

    assert response.json() == {"status": "processed"}
    await db_session.refresh(organization)
    assert organization.plan_id == "free"
