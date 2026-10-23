from datetime import UTC, date, datetime

import pytest

from app.models import Project
from app.repositories.daily_counts import count_rows_per_day
from app.services.daily_series import MAX_SERIES_DAYS, day_window_bounds, utc_day, zero_filled_daily_series
from tests.factories import create_organization, create_project, create_user


def test_zero_filled_series_covers_every_day_ending_on_end_day() -> None:
    counts_by_day = {date(2026, 3, 1): 4, date(2026, 2, 27): 1}

    series = zero_filled_daily_series(counts_by_day, end_day=date(2026, 3, 1), days=30)

    assert len(series) == 30
    assert series[0].day == date(2026, 1, 31)
    assert series[-1].day == date(2026, 3, 1)
    assert series[-1].count == 4
    assert {item.day: item.count for item in series}[date(2026, 2, 27)] == 1
    assert sum(item.count for item in series) == 5


def test_zero_filled_series_ignores_counts_outside_the_window() -> None:
    series = zero_filled_daily_series({date(2025, 1, 1): 9}, end_day=date(2026, 3, 1), days=90)

    assert len(series) == 90
    assert all(item.count == 0 for item in series)


@pytest.mark.parametrize("days", [0, -1, MAX_SERIES_DAYS + 1])
def test_zero_filled_series_rejects_out_of_range_lengths(days: int) -> None:
    with pytest.raises(ValueError):
        zero_filled_daily_series({}, end_day=date(2026, 3, 1), days=days)


def test_day_window_bounds_are_utc_midnights() -> None:
    starts_at, ends_at = day_window_bounds(date(2026, 3, 1), 30)

    assert starts_at == datetime(2026, 1, 31, tzinfo=UTC)
    assert ends_at == datetime(2026, 3, 2, tzinfo=UTC)


def test_utc_day_converts_aware_datetimes() -> None:
    assert utc_day(datetime.fromisoformat("2026-03-01T23:30:00-02:00")) == date(2026, 3, 2)


async def test_count_rows_per_day_groups_by_utc_day(db_session) -> None:
    owner = await create_user(db_session, email="daily-owner@example.com")
    organization = await create_organization(db_session, owner=owner, slug="daily-org")
    creation_times = [
        datetime(2026, 3, 1, 0, 30, tzinfo=UTC),
        datetime(2026, 3, 1, 23, 59, tzinfo=UTC),
        datetime(2026, 2, 28, 23, 59, tzinfo=UTC),
        datetime(2026, 3, 2, 0, 0, tzinfo=UTC),
    ]
    for index, created_at in enumerate(creation_times):
        project = await create_project(db_session, organization=organization, created_by=owner, name=f"Project {index}")
        project.created_at = created_at
    await db_session.flush()

    counts = await count_rows_per_day(
        db_session,
        Project.created_at,
        starts_at=datetime(2026, 2, 1, tzinfo=UTC),
        ends_at=datetime(2026, 3, 2, tzinfo=UTC),
        filters=(Project.organization_id == organization.id,),
    )

    assert counts == {date(2026, 3, 1): 2, date(2026, 2, 28): 1}
