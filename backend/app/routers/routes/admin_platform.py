from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.schemas.admin import PlatformMetricsResponse, SetupChecklistResponse
from app.schemas.overview import ChartRange
from app.services.admin_metrics_service import AdminMetricsService
from app.services.setup_checklist_service import SetupChecklistService
from app.utils.clock import Clock
from app.utils.dependencies import AppSettings, DbSession, PlatformStaffUser, SuperadminUser, get_clock

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics")
async def get_platform_metrics(
    _: SuperadminUser,
    session: DbSession,
    clock: Annotated[Clock, Depends(get_clock)],
    days: Annotated[ChartRange, Query()] = ChartRange.LAST_30_DAYS,
) -> PlatformMetricsResponse:
    return await AdminMetricsService(session, clock).get_metrics(days)


@router.get("/setup")
async def get_setup_checklist(
    _: PlatformStaffUser, session: DbSession, settings: AppSettings
) -> SetupChecklistResponse:
    return await SetupChecklistService(session, settings).get_checklist()
