from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest
from fastapi import FastAPI

from app.models import StoredFile
from app.utils.dependencies import get_clock
from tests.factories import add_member, auth_headers, create_organization, create_project, create_user

FROZEN_NOW = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def frozen_clock(app: FastAPI) -> Iterator[None]:
    app.dependency_overrides[get_clock] = lambda: lambda: FROZEN_NOW
    yield
    app.dependency_overrides.pop(get_clock, None)


async def test_overview_returns_stat_cards_for_a_member_on_free(client, db_session, settings) -> None:
    owner = await create_user(db_session, email="overview-owner@example.com")
    member = await create_user(db_session, email="overview-member@example.com")
    organization = await create_organization(db_session, owner=owner, slug="overview-free", plan_id="free")
    await add_member(db_session, organization=organization, user=member)
    await create_project(db_session, organization=organization, created_by=owner, name="Alpha")
    await create_project(db_session, organization=organization, created_by=owner, name="Beta")
    for file_name, size_bytes in (("a.txt", 1500), ("b.txt", 500)):
        db_session.add(
            StoredFile(
                organization_id=organization.id,
                uploaded_by_id=owner.id,
                storage_key=f"orgs/{organization.id}/files/{file_name}",
                name=file_name,
                size_bytes=size_bytes,
                content_type="text/plain",
            )
        )
    await db_session.flush()

    response = await client.get(
        f"/api/orgs/{organization.id}/overview", headers=await auth_headers(member, settings=settings)
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "plan_id": "free",
        "has_analytics": False,
        "projects_count": 2,
        "projects_limit": 3,
        "members_count": 2,
        "members_limit": 3,
        "storage_used_bytes": 2000,
        "storage_limit_bytes": 100 * 1024 * 1024,
    }


async def test_overview_is_hidden_from_non_members(client, db_session, settings) -> None:
    owner = await create_user(db_session, email="hidden-owner@example.com")
    stranger = await create_user(db_session, email="stranger@example.com")
    organization = await create_organization(db_session, owner=owner, slug="hidden-org")

    response = await client.get(
        f"/api/orgs/{organization.id}/overview", headers=await auth_headers(stranger, settings=settings)
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_charts_require_the_analytics_feature(client, db_session, settings) -> None:
    owner = await create_user(db_session, email="charts-free@example.com")
    organization = await create_organization(db_session, owner=owner, slug="charts-free", plan_id="free")

    response = await client.get(
        f"/api/orgs/{organization.id}/overview/charts", headers=await auth_headers(owner, settings=settings)
    )

    assert response.status_code == 402
    error = response.json()["error"]
    assert error["code"] == "plan_upgrade_required"
    assert error["details"]["feature"] == "analytics"


async def test_charts_return_zero_filled_projects_per_day(client, db_session, settings, frozen_clock) -> None:
    owner = await create_user(db_session, email="charts-pro@example.com")
    organization = await create_organization(db_session, owner=owner, slug="charts-pro", plan_id="pro")
    for name, created_at in (
        ("Today one", datetime(2026, 3, 1, 9, 0, tzinfo=UTC)),
        ("Today two", datetime(2026, 3, 1, 10, 0, tzinfo=UTC)),
        ("Last week", datetime(2026, 2, 22, 10, 0, tzinfo=UTC)),
        ("Two months ago", datetime(2026, 1, 1, 10, 0, tzinfo=UTC)),
    ):
        project = await create_project(db_session, organization=organization, created_by=owner, name=name)
        project.created_at = created_at
    await db_session.flush()
    headers = await auth_headers(owner, settings=settings)

    month_response = await client.get(f"/api/orgs/{organization.id}/overview/charts", headers=headers)
    quarter_response = await client.get(
        f"/api/orgs/{organization.id}/overview/charts", params={"days": 90}, headers=headers
    )

    assert month_response.status_code == 200, month_response.text
    month = month_response.json()
    assert month["days"] == 30
    assert len(month["projects_per_day"]) == 30
    assert month["projects_per_day"][-1] == {"day": "2026-03-01", "count": 2}
    assert month["projects_per_day"][0]["day"] == str(date(2026, 1, 31))
    assert sum(point["count"] for point in month["projects_per_day"]) == 3
    quarter = quarter_response.json()
    assert len(quarter["projects_per_day"]) == 90
    assert sum(point["count"] for point in quarter["projects_per_day"]) == 4


async def test_charts_reject_unsupported_ranges(client, db_session, settings) -> None:
    owner = await create_user(db_session, email="charts-range@example.com")
    organization = await create_organization(db_session, owner=owner, slug="charts-range", plan_id="pro")

    response = await client.get(
        f"/api/orgs/{organization.id}/overview/charts",
        params={"days": 60},
        headers=await auth_headers(owner, settings=settings),
    )

    assert response.status_code == 422
