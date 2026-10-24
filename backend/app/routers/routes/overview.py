from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.models import Membership
from app.schemas.overview import ChartRange, OverviewChartsResponse, OverviewResponse
from app.services.analytics_service import ANALYTICS_FEATURE, AnalyticsService
from app.utils.clock import Clock
from app.utils.dependencies import CurrentMembership, DbSession, get_clock, require_feature

router = APIRouter()


@router.get("")
async def get_overview(membership: CurrentMembership, db: DbSession) -> OverviewResponse:
    """Return the organization dashboard overview."""
    return await AnalyticsService(db).get_overview(membership.organization)


@router.get("/charts")
async def get_overview_charts(
    membership: Annotated[Membership, Depends(require_feature(ANALYTICS_FEATURE))],
    db: DbSession,
    clock: Annotated[Clock, Depends(get_clock)],
    days: Annotated[ChartRange, Query()] = ChartRange.LAST_30_DAYS,
) -> OverviewChartsResponse:
    """Return organization chart data for the given period."""
    return await AnalyticsService(db, clock).get_charts(membership.organization_id, days)
