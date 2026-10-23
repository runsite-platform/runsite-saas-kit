import pytest
from sqlalchemy import UniqueConstraint
from sqlalchemy.exc import IntegrityError

from app.config.db import Base
from app.models import BillingEvent, Organization, Payment, Subscription
from app.models.enums import BillingInterval, PaymentStatus, SubscriptionStatus
from tests.factories import create_organization, create_user


def unique_column_sets(table_name: str) -> set[tuple[str, ...]]:
    table = Base.metadata.tables[table_name]
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_billing_tables_declare_provider_unique_keys() -> None:
    assert ("provider", "provider_subscription_id") in unique_column_sets("subscriptions")
    assert ("provider", "provider_payment_id") in unique_column_sets("payments")
    assert ("provider", "event_id") in unique_column_sets("billing_events")


def test_organization_has_plan_override_columns() -> None:
    columns = Organization.__table__.columns
    assert columns["plan_override_id"].nullable
    assert columns["plan_override_reason"].nullable


async def test_duplicate_provider_subscription_id_is_rejected(db_session) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    db_session.add(
        Subscription(
            organization_id=organization.id,
            provider="stripe",
            provider_subscription_id="sub_duplicate",
            plan_id="pro",
            interval=BillingInterval.MONTHLY,
            status=SubscriptionStatus.ACTIVE,
        )
    )
    await db_session.flush()

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(
                Subscription(
                    organization_id=organization.id,
                    provider="stripe",
                    provider_subscription_id="sub_duplicate",
                    plan_id="pro",
                    interval=BillingInterval.MONTHLY,
                    status=SubscriptionStatus.ACTIVE,
                )
            )
            await db_session.flush()


async def test_payment_and_event_rows_persist(db_session) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    payment = Payment(
        organization_id=organization.id,
        provider="stripe",
        provider_payment_id="in_1",
        amount_cents=1900,
        currency="USD",
        status=PaymentStatus.SUCCEEDED,
    )
    event = BillingEvent(provider="stripe", event_id="evt_1", event_type="invoice.paid", payload={"id": "evt_1"})
    db_session.add_all([payment, event])
    await db_session.flush()

    assert payment.id is not None
    assert event.processed_at is None
    assert event.error is None
