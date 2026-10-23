from datetime import date
from enum import IntEnum

from pydantic import BaseModel


class ChartRange(IntEnum):
    LAST_30_DAYS = 30
    LAST_90_DAYS = 90


class DailyCount(BaseModel):
    day: date
    count: int


class OverviewResponse(BaseModel):
    plan_id: str
    has_analytics: bool
    projects_count: int
    projects_limit: int
    members_count: int
    members_limit: int
    storage_used_bytes: int
    storage_limit_bytes: int


class OverviewChartsResponse(BaseModel):
    days: int
    projects_per_day: list[DailyCount]
