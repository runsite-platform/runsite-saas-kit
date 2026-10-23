import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.plan_limits import BYTES_PER_MEGABYTE, PlanLimitsService
from app.utils.exceptions import BusinessError
from tests.factories import create_organization, create_project, create_stored_file, create_user

FREE_STORAGE_BYTES = 100 * BYTES_PER_MEGABYTE


async def test_free_plan_allows_three_projects(db_session: AsyncSession) -> None:
    owner = await create_user(db_session, email="limits-projects@example.com")
    organization = await create_organization(db_session, owner=owner)
    service = PlanLimitsService(db_session)
    for project_number in range(2):
        await create_project(db_session, organization=organization, created_by=owner, name=f"P{project_number}")

    await service.ensure_can_add_project(organization)

    await create_project(db_session, organization=organization, created_by=owner, name="P2")
    with pytest.raises(BusinessError) as error_info:
        await service.ensure_can_add_project(organization)

    assert error_info.value.code == "plan_limit_reached"
    assert error_info.value.status_code == 402
    assert error_info.value.details == {"limit": "projects", "plan_id": "free"}


async def test_storage_limit_counts_existing_files(db_session: AsyncSession) -> None:
    owner = await create_user(db_session, email="limits-storage@example.com")
    organization = await create_organization(db_session, owner=owner)
    await create_stored_file(
        db_session, organization=organization, uploaded_by=owner, size_bytes=FREE_STORAGE_BYTES - 10
    )
    service = PlanLimitsService(db_session)

    await service.ensure_can_store(organization, 10)

    with pytest.raises(BusinessError) as error_info:
        await service.ensure_can_store(organization, 11)

    assert error_info.value.code == "plan_limit_reached"
    assert error_info.value.status_code == 402
    assert error_info.value.details == {"limit": "storage_mb", "plan_id": "free"}
