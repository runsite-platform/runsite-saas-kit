from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Organization
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.stored_file_repository import StoredFileRepository
from app.schemas.overview import ChartRange, OverviewChartsResponse, OverviewResponse
from app.services.billing.plans import get_plan
from app.services.daily_series import day_window_bounds, utc_day, zero_filled_daily_series
from app.utils.clock import Clock, utc_now

BYTES_PER_MEGABYTE = 1024 * 1024
ANALYTICS_FEATURE = "analytics"


class AnalyticsService:
    """Service for organization overview analytics."""

    def __init__(self, db: AsyncSession, clock: Clock = utc_now) -> None:
        self.analytics = AnalyticsRepository(db)
        self.projects = ProjectRepository(db)
        self.stored_files = StoredFileRepository(db)
        self.clock = clock

    async def get_overview(self, organization: Organization) -> OverviewResponse:
        """Return plan usage and limits for the organization."""
        plan = get_plan(organization.plan_id)
        return OverviewResponse(
            plan_id=plan.id,
            has_analytics=ANALYTICS_FEATURE in plan.features,
            projects_count=await self.projects.count_for_organization(organization.id),
            projects_limit=plan.limits.projects,
            members_count=await self.analytics.count_members(organization.id),
            members_limit=plan.limits.members,
            storage_used_bytes=await self.stored_files.total_size_for_organization(organization.id),
            storage_limit_bytes=plan.limits.storage_mb * BYTES_PER_MEGABYTE,
        )

    async def get_charts(self, organization_id: UUID, days: ChartRange) -> OverviewChartsResponse:
        """Return a zero-filled daily series of created projects."""
        series_length = int(days)
        end_day = utc_day(self.clock())
        starts_at, ends_at = day_window_bounds(end_day, series_length)
        counts_by_day = await self.analytics.count_projects_per_day(
            organization_id, starts_at=starts_at, ends_at=ends_at
        )
        return OverviewChartsResponse(
            days=series_length,
            projects_per_day=zero_filled_daily_series(counts_by_day, end_day=end_day, days=series_length),
        )
