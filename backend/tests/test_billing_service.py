from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.config.settings import Settings
from app.constants.enums import BillingInterval, PaymentStatus, SubscriptionStatus
from app.models import Payment
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.billing.billing_service import BillingEventError, BillingService
from app.services.billing.providers.base import NormalizedEvent, PaymentSnapshot, SubscriptionSnapshot
from app.services.billing.providers.stripe_provider import StripeProvider
from app.utils.exceptions import BusinessError
from tests.conftest import make_settings
from tests.factories import create_organization, create_subscription, create_user
from tests.fakes import TEST_STRIPE_SETTINGS, FakeStripeClient

SUBSCRIPTION_ID = "sub_service_test"


@pytest.fixture
def settings() -> Settings:
    return make_settings(**TEST_STRIPE_SETTINGS)


@pytest.fixture
def billing_service(db_session, settings) -> BillingService:
    return BillingService(db_session, settings, StripeProvider(settings, client=FakeStripeClient()))


@pytest.fixture
async def organization(db_session):
    owner = await create_user(db_session, email="service-owner@example.com")
    return await create_organization(db_session, owner=owner)


def subscription_event(
    organization_id,
    status: SubscriptionStatus,
    *,
    event_id: str,
    price_reference: str | None = "price_pro_monthly_test",
    interval_hint: BillingInterval | None = None,
    occurred_at: datetime | None = None,
) -> NormalizedEvent:
    return NormalizedEvent(
        event_id=event_id,
        event_type="test.subscription",
        kind="subscription_updated",
        payload={},
        organization_id=organization_id,
        occurred_at=occurred_at,
        subscription=SubscriptionSnapshot(
            provider_subscription_id=SUBSCRIPTION_ID,
            status=status,
            customer_id="cus_service_test",
            price_reference=price_reference,
            interval_hint=interval_hint,
            current_period_end=datetime(2026, 12, 6, tzinfo=UTC),
        ),
    )


def payment_event(
    status: PaymentStatus, *, event_id: str, organization_id=None, occurred_at: datetime | None = None
) -> NormalizedEvent:
    return NormalizedEvent(
        event_id=event_id,
        event_type="test.payment",
        kind="payment_succeeded" if status == PaymentStatus.SUCCEEDED else "payment_failed",
        payload={},
        organization_id=organization_id,
        occurred_at=occurred_at,
        payment=PaymentSnapshot(
            provider_payment_id="in_service_test",
            amount_cents=1900,
            currency="USD",
            status=status,
            provider_subscription_id=SUBSCRIPTION_ID,
            paid_at=datetime(2026, 11, 6, tzinfo=UTC) if status == PaymentStatus.SUCCEEDED else None,
        ),
    )


async def test_status_transitions_recompute_the_plan(db_session, billing_service, organization) -> None:
    transitions = [
        (SubscriptionStatus.TRIALING, "pro", True),
        (SubscriptionStatus.ACTIVE, "pro", True),
        (SubscriptionStatus.PAST_DUE, "free", True),
        (SubscriptionStatus.CANCELED, "free", False),
        (SubscriptionStatus.EXPIRED, "free", False),
    ]
    for index, (status, expected_plan, expected_blocking) in enumerate(transitions):
        await billing_service.apply_event(subscription_event(organization.id, status, event_id=f"evt_{index}"))

        assert organization.plan_id == expected_plan, status
        assert await billing_service.has_blocking_subscription(organization.id) is expected_blocking, status

    subscriptions = await SubscriptionRepository(db_session).list_for_organization(organization.id)
    assert len(subscriptions) == 1
    assert subscriptions[0].status == SubscriptionStatus.EXPIRED
    assert subscriptions[0].plan_id == "pro"
    assert subscriptions[0].interval == BillingInterval.MONTHLY
    assert organization.billing_provider == "stripe"
    assert organization.billing_customer_id == "cus_service_test"


async def test_plan_comes_from_the_yearly_price(db_session, billing_service, organization) -> None:
    event = subscription_event(
        organization.id, SubscriptionStatus.ACTIVE, event_id="evt_yearly", price_reference="price_pro_yearly_test"
    )

    await billing_service.apply_event(event)

    subscription = await SubscriptionRepository(db_session).get_by_provider_id("stripe", SUBSCRIPTION_ID)
    assert subscription is not None
    assert subscription.interval == BillingInterval.YEARLY


async def test_unknown_price_never_grants_a_plan_to_a_new_subscription(
    db_session, billing_service, organization
) -> None:
    event = subscription_event(
        organization.id, SubscriptionStatus.ACTIVE, event_id="evt_cheap", price_reference="price_other_product"
    )

    assert await billing_service.apply_event(event) is None

    assert organization.plan_id == "free"
    assert await SubscriptionRepository(db_session).get_by_provider_id("stripe", SUBSCRIPTION_ID) is None


async def test_unknown_price_keeps_the_plan_of_a_known_subscription(billing_service, organization) -> None:
    await billing_service.apply_event(subscription_event(organization.id, SubscriptionStatus.ACTIVE, event_id="e1"))
    retired_price = subscription_event(
        organization.id, SubscriptionStatus.ACTIVE, event_id="e2", price_reference="price_retired"
    )

    await billing_service.apply_event(retired_price)

    assert organization.plan_id == "pro"


async def test_older_event_does_not_overwrite_a_newer_one(db_session, billing_service, organization) -> None:
    newer = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
    await billing_service.apply_event(
        subscription_event(organization.id, SubscriptionStatus.PAST_DUE, event_id="e_new", occurred_at=newer)
    )
    await billing_service.apply_event(
        subscription_event(
            organization.id, SubscriptionStatus.ACTIVE, event_id="e_old", occurred_at=newer - timedelta(minutes=5)
        )
    )

    subscription = await SubscriptionRepository(db_session).get_by_provider_id("stripe", SUBSCRIPTION_ID)
    assert subscription is not None
    assert subscription.status == SubscriptionStatus.PAST_DUE
    assert organization.plan_id == "free"


async def test_late_update_does_not_revive_a_canceled_subscription(db_session, billing_service, organization) -> None:
    canceled_at = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
    await billing_service.apply_event(
        subscription_event(organization.id, SubscriptionStatus.ACTIVE, event_id="e1", occurred_at=canceled_at)
    )
    await billing_service.apply_event(
        subscription_event(organization.id, SubscriptionStatus.CANCELED, event_id="e2", occurred_at=canceled_at)
    )
    await billing_service.apply_event(
        subscription_event(organization.id, SubscriptionStatus.ACTIVE, event_id="e3", occurred_at=canceled_at)
    )

    subscription = await SubscriptionRepository(db_session).get_by_provider_id("stripe", SUBSCRIPTION_ID)
    assert subscription is not None
    assert subscription.status == SubscriptionStatus.CANCELED
    assert organization.plan_id == "free"


async def test_newer_event_is_applied_and_remembered(db_session, billing_service, organization) -> None:
    first = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
    await billing_service.apply_event(
        subscription_event(organization.id, SubscriptionStatus.PAST_DUE, event_id="e1", occurred_at=first)
    )
    later = first + timedelta(hours=1)
    await billing_service.apply_event(
        subscription_event(organization.id, SubscriptionStatus.ACTIVE, event_id="e2", occurred_at=later)
    )

    subscription = await SubscriptionRepository(db_session).get_by_provider_id("stripe", SUBSCRIPTION_ID)
    assert subscription is not None
    assert subscription.status == SubscriptionStatus.ACTIVE
    assert subscription.provider_updated_at == later
    assert organization.plan_id == "pro"


async def test_payment_is_attributed_through_the_stored_subscription(db_session, billing_service, organization) -> None:
    await billing_service.apply_event(subscription_event(organization.id, SubscriptionStatus.ACTIVE, event_id="e1"))

    await billing_service.apply_event(payment_event(PaymentStatus.FAILED, event_id="e2"))
    await billing_service.apply_event(payment_event(PaymentStatus.SUCCEEDED, event_id="e3"))
    await billing_service.apply_event(payment_event(PaymentStatus.FAILED, event_id="e4-late-retry"))

    payments = (await db_session.execute(select(Payment))).scalars().all()
    assert len(payments) == 1
    assert payments[0].organization_id == organization.id
    assert payments[0].status == PaymentStatus.SUCCEEDED
    assert payments[0].paid_at == datetime(2026, 11, 6, tzinfo=UTC)


async def test_recent_event_for_unknown_organization_is_retried(billing_service) -> None:
    event = payment_event(PaymentStatus.SUCCEEDED, event_id="orphan", occurred_at=datetime.now(UTC))

    with pytest.raises(BillingEventError, match="organization"):
        await billing_service.apply_event(event)


async def test_old_event_for_unknown_organization_is_skipped(billing_service) -> None:
    event = payment_event(
        PaymentStatus.SUCCEEDED, event_id="foreign", occurred_at=datetime.now(UTC) - timedelta(hours=2)
    )

    assert await billing_service.apply_event(event) is None


async def test_ignored_events_change_nothing(billing_service, organization) -> None:
    event = NormalizedEvent(event_id="evt_ignored", event_type="ping", kind="ignored", payload={})

    assert await billing_service.apply_event(event) is None
    assert organization.plan_id == "free"


async def test_override_takes_precedence_over_subscription(db_session, billing_service, organization) -> None:
    await create_subscription(db_session, organization=organization, status=SubscriptionStatus.ACTIVE)
    assert await billing_service.recompute_plan(organization) == "pro"

    await billing_service.set_plan_override(organization, "free", "Downgraded for abuse review")
    assert organization.plan_id == "free"
    assert organization.plan_override_id == "free"
    assert organization.plan_override_reason == "Downgraded for abuse review"

    await billing_service.set_plan_override(organization, None, "Review finished")
    assert organization.plan_id == "pro"
    assert organization.plan_override_id is None


async def test_override_grants_a_plan_without_subscription(billing_service, organization) -> None:
    await billing_service.set_plan_override(organization, "pro", "Partner deal")

    assert organization.plan_id == "pro"


async def test_override_rejects_unknown_plans(billing_service, organization) -> None:
    with pytest.raises(BusinessError) as error_info:
        await billing_service.set_plan_override(organization, "enterprise", "Big customer")

    assert error_info.value.code == "plan_unavailable"
    assert organization.plan_override_id is None
