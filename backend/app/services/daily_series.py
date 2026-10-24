from collections.abc import Mapping
from datetime import UTC, date, datetime, time, timedelta

from app.schemas.overview import DailyCount

MAX_SERIES_DAYS = 366


def _ensure_series_length(days: int) -> None:
    if not 1 <= days <= MAX_SERIES_DAYS:
        raise ValueError(f"days must be between 1 and {MAX_SERIES_DAYS}, got {days}")


def utc_day(moment: datetime) -> date:
    """Return the UTC calendar date of the given moment."""
    return moment.astimezone(UTC).date()


def window_start_day(end_day: date, days: int) -> date:
    """Return the first day of a window of days ending on end_day."""
    _ensure_series_length(days)
    return end_day - timedelta(days=days - 1)


def day_window_bounds(end_day: date, days: int) -> tuple[datetime, datetime]:
    """Return UTC datetime bounds covering the day window."""
    starts_at = datetime.combine(window_start_day(end_day, days), time.min, tzinfo=UTC)
    ends_at = datetime.combine(end_day + timedelta(days=1), time.min, tzinfo=UTC)
    return starts_at, ends_at


def zero_filled_daily_series(counts_by_day: Mapping[date, int], *, end_day: date, days: int) -> list[DailyCount]:
    """Return daily counts for the window with missing days set to zero."""
    start_day = window_start_day(end_day, days)
    series_days = [start_day + timedelta(days=offset) for offset in range(days)]
    return [DailyCount(day=series_day, count=counts_by_day.get(series_day, 0)) for series_day in series_days]
