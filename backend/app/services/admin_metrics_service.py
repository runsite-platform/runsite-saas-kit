from collections.abc import Iterable
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import BillingInterval, SubscriptionStatus
from app.repositories.admin_query_repository import AdminQueryRepository
from app.schemas.admin import PlatformMetricsResponse, TrialConversion
from app.schemas.overview import ChartRange
from app.services.billing.plans import get_plan
from app.services.daily_series import day_window_bounds, utc_day, zero_filled_daily_series
from app.utils.clock import Clock, utc_now

TRIAL_CONVERSION_WINDOW_DAYS = 90
CHURN_WINDOW_DAYS = 30
MONTHS_PER_YEAR = 12


def calculate_mrr_cents(active_subscription_counts: Iterable[tuple[str, str, int]]) -> int:
    monthly_cents = 0
    yearly_cents = 0
    for plan_id, interval, subscription_count in active_subscription_counts:
        plan = get_plan(plan_id)
        if interval == BillingInterval.YEARLY:
            yearly_cents += plan.price_yearly_cents * subscription_count
        else:
            monthly_cents += plan.price_monthly_cents * subscription_count
    return monthly_cents + round(yearly_cents / MONTHS_PER_YEAR)


def conversion_rate(converted: int, ended_trials: int) -> float | None:
    if ended_trials == 0:
        return None
    return round(converted / ended_trials, 4)


class AdminMetricsService:
    def __init__(self, session: AsyncSession, clock: Clock = utc_now) -> None:
        self.queries = AdminQueryRepository(session)
        self.clock = clock

    async def get_metrics(self, days: ChartRange) -> PlatformMetricsResponse:
        now = self.clock()
        series_length = int(days)
        status_counts = await self.queries.count_subscriptions_by_status()
        ended_trials, converted = await self.queries.count_ended_trials(
            starts_at=now - timedelta(days=TRIAL_CONVERSION_WINDOW_DAYS), ends_at=now
        )
        churned = await self.queries.count_churned_subscriptions(
            starts_at=now - timedelta(days=CHURN_WINDOW_DAYS), ends_at=now
        )
        end_day = utc_day(now)
        series_starts_at, series_ends_at = day_window_bounds(end_day, series_length)
        signups = await self.queries.count_signups_per_day(starts_at=series_starts_at, ends_at=series_ends_at)
        new_organizations = await self.queries.count_new_organizations_per_day(
            starts_at=series_starts_at, ends_at=series_ends_at
        )
        return PlatformMetricsResponse(
            mrr_cents=calculate_mrr_cents(await self.queries.count_active_subscriptions_by_plan()),
            active_subscriptions=status_counts.get(SubscriptionStatus.ACTIVE, 0),
            trialing_subscriptions=status_counts.get(SubscriptionStatus.TRIALING, 0),
            past_due_subscriptions=status_counts.get(SubscriptionStatus.PAST_DUE, 0),
            churned_last_30_days=churned,
            trial_conversion=TrialConversion(
                window_days=TRIAL_CONVERSION_WINDOW_DAYS,
                ended_trials=ended_trials,
                converted=converted,
                rate=conversion_rate(converted, ended_trials),
            ),
            total_users=await self.queries.count_users(),
            total_organizations=await self.queries.count_organizations(),
            days=series_length,
            signups_per_day=zero_filled_daily_series(signups, end_day=end_day, days=series_length),
            new_organizations_per_day=zero_filled_daily_series(new_organizations, end_day=end_day, days=series_length),
        )
