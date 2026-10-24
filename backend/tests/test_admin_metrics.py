from datetime import UTC, date, datetime, timedelta

from app.constants.enums import BillingInterval, PlatformRole, SubscriptionStatus
from app.models import Subscription, User
from app.schemas.admin import TrialConversion
from app.schemas.overview import ChartRange, DailyCount
from app.services.admin_metrics_service import AdminMetricsService, calculate_mrr_cents, conversion_rate
from app.utils.dependencies import get_clock
from tests.factories import auth_headers, create_organization, create_subscription, create_user

FROZEN_NOW = datetime(2026, 6, 30, 12, 0, tzinfo=UTC)


def test_mrr_adds_monthly_prices_and_yearly_prices_divided_by_twelve() -> None:
    assert calculate_mrr_cents([("pro", "monthly", 2), ("pro", "yearly", 1)]) == 2 * 1900 + round(19000 / 12)
    assert calculate_mrr_cents([("unknown-plan", "monthly", 3)]) == 0
    assert calculate_mrr_cents([]) == 0


def test_conversion_rate_handles_an_empty_window() -> None:
    assert conversion_rate(0, 0) is None
    assert conversion_rate(1, 2) == 0.5
    assert conversion_rate(2, 3) == 0.6667


async def seed_subscription(
    db_session,
    *,
    owner: User,
    slug: str,
    status: SubscriptionStatus,
    interval: BillingInterval = BillingInterval.MONTHLY,
    trial_ends_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> Subscription:
    organization = await create_organization(db_session, owner=owner, name=slug, slug=slug, plan_id="pro")
    subscription = await create_subscription(db_session, organization=organization, status=status, interval=interval)
    subscription.trial_ends_at = trial_ends_at
    if updated_at is not None:
        subscription.updated_at = updated_at
    await db_session.flush()
    return subscription


async def test_metrics_math_with_fixed_subscriptions(db_session) -> None:
    owner = await create_user(db_session, email="metrics-owner@example.com")
    await seed_subscription(
        db_session,
        owner=owner,
        slug="active-monthly",
        status=SubscriptionStatus.ACTIVE,
        trial_ends_at=FROZEN_NOW - timedelta(days=10),
    )
    await seed_subscription(
        db_session, owner=owner, slug="active-yearly", status=SubscriptionStatus.ACTIVE, interval=BillingInterval.YEARLY
    )
    await seed_subscription(
        db_session,
        owner=owner,
        slug="trialing",
        status=SubscriptionStatus.TRIALING,
        trial_ends_at=FROZEN_NOW + timedelta(days=5),
    )
    await seed_subscription(db_session, owner=owner, slug="past-due", status=SubscriptionStatus.PAST_DUE)
    await seed_subscription(
        db_session,
        owner=owner,
        slug="canceled-after-trial",
        status=SubscriptionStatus.CANCELED,
        trial_ends_at=FROZEN_NOW - timedelta(days=20),
        updated_at=FROZEN_NOW - timedelta(days=5),
    )
    await seed_subscription(
        db_session,
        owner=owner,
        slug="expired-long-ago",
        status=SubscriptionStatus.EXPIRED,
        trial_ends_at=FROZEN_NOW - timedelta(days=200),
        updated_at=FROZEN_NOW - timedelta(days=100),
    )
    await seed_subscription(
        db_session,
        owner=owner,
        slug="canceled-last-month",
        status=SubscriptionStatus.CANCELED,
        updated_at=FROZEN_NOW - timedelta(days=40),
    )

    metrics = await AdminMetricsService(db_session, clock=lambda: FROZEN_NOW).get_metrics(ChartRange.LAST_30_DAYS)

    assert metrics.mrr_cents == 1900 + round(19000 / 12)
    assert metrics.currency == "usd"
    assert metrics.active_subscriptions == 2
    assert metrics.trialing_subscriptions == 1
    assert metrics.past_due_subscriptions == 1
    assert metrics.trial_conversion == TrialConversion(window_days=90, ended_trials=2, converted=1, rate=0.5)
    assert metrics.churned_last_30_days == 1
    assert metrics.total_users == 1
    assert metrics.total_organizations == 7


async def test_signups_and_new_organizations_are_zero_filled(db_session) -> None:
    signup_times = (
        ("day-a@example.com", datetime(2026, 6, 30, 8, 0, tzinfo=UTC)),
        ("day-b@example.com", datetime(2026, 6, 30, 11, 0, tzinfo=UTC)),
        ("day-c@example.com", datetime(2026, 6, 28, 10, 0, tzinfo=UTC)),
        ("day-d@example.com", datetime(2026, 5, 1, 10, 0, tzinfo=UTC)),
    )
    created_users = []
    for email, created_at in signup_times:
        user = await create_user(db_session, email=email)
        user.created_at = created_at
        created_users.append(user)
    organization = await create_organization(db_session, owner=created_users[0], slug="day-org")
    organization.created_at = datetime(2026, 6, 29, 9, 0, tzinfo=UTC)
    await db_session.flush()
    service = AdminMetricsService(db_session, clock=lambda: FROZEN_NOW)

    month = await service.get_metrics(ChartRange.LAST_30_DAYS)
    quarter = await service.get_metrics(ChartRange.LAST_90_DAYS)

    assert month.days == 30
    assert len(month.signups_per_day) == 30
    assert month.signups_per_day[0].day == date(2026, 6, 1)
    assert month.signups_per_day[-1] == DailyCount(day=date(2026, 6, 30), count=2)
    signups_by_day = {point.day: point.count for point in month.signups_per_day}
    assert signups_by_day[date(2026, 6, 28)] == 1
    assert signups_by_day[date(2026, 6, 29)] == 0
    assert sum(signups_by_day.values()) == 3
    assert len(quarter.signups_per_day) == 90
    assert sum(point.count for point in quarter.signups_per_day) == 4
    new_organizations_by_day = {point.day: point.count for point in month.new_organizations_per_day}
    assert new_organizations_by_day[date(2026, 6, 29)] == 1
    assert sum(new_organizations_by_day.values()) == 1


async def test_metrics_endpoint_uses_the_injected_clock(app, client, db_session, settings) -> None:
    superadmin = await create_user(db_session, email="metrics-super@example.com", platform_role=PlatformRole.SUPERADMIN)
    app.dependency_overrides[get_clock] = lambda: lambda: FROZEN_NOW
    try:
        response = await client.get(
            "/api/admin/metrics", params={"days": 90}, headers=await auth_headers(superadmin, settings=settings)
        )
    finally:
        app.dependency_overrides.pop(get_clock, None)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["days"] == 90
    assert len(body["signups_per_day"]) == 90
    assert body["signups_per_day"][-1]["day"] == "2026-06-30"
    assert body["trial_conversion"]["rate"] is None
