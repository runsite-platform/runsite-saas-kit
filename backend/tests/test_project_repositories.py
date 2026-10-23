from fastapi_pagination import Params, set_params
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProjectStatus
from app.repositories.project_repository import ProjectRepository
from app.repositories.stored_file_repository import StoredFileRepository
from tests.factories import create_organization, create_project, create_stored_file, create_user


async def test_project_repository_scopes_by_organization(db_session: AsyncSession) -> None:
    first_owner = await create_user(db_session, email="repo-first@example.com")
    second_owner = await create_user(db_session, email="repo-second@example.com")
    first_organization = await create_organization(db_session, owner=first_owner, name="First")
    second_organization = await create_organization(db_session, owner=second_owner, name="Second")
    first_project = await create_project(db_session, organization=first_organization, created_by=first_owner)
    await create_project(
        db_session, organization=first_organization, created_by=first_owner, status=ProjectStatus.ARCHIVED
    )
    await create_project(db_session, organization=second_organization, created_by=second_owner)
    repository = ProjectRepository(db_session)

    assert await repository.get_in_organization(first_organization.id, first_project.id) is not None
    assert await repository.get_in_organization(second_organization.id, first_project.id) is None
    assert await repository.count_for_organization(first_organization.id) == 2
    with set_params(Params(page=1, size=50)):
        all_projects = await repository.list_for_organization(first_organization.id)
        active_projects = await repository.list_for_organization(first_organization.id, status=ProjectStatus.ACTIVE)
    assert all_projects.total == 2
    assert [project.id for project in active_projects.items] == [first_project.id]
    with set_params(Params(page=1, size=1)):
        first_page = await repository.list_for_organization(first_organization.id)
    assert len(first_page.items) == 1
    assert first_page.pages == 2


async def test_stored_file_repository_sums_sizes_and_lists_keys(db_session: AsyncSession) -> None:
    owner = await create_user(db_session, email="repo-files@example.com")
    organization = await create_organization(db_session, owner=owner)
    other_owner = await create_user(db_session, email="repo-files-other@example.com")
    other_organization = await create_organization(db_session, owner=other_owner, name="Other")
    first_file = await create_stored_file(db_session, organization=organization, uploaded_by=owner, size_bytes=100)
    second_file = await create_stored_file(db_session, organization=organization, uploaded_by=owner, size_bytes=250)
    await create_stored_file(db_session, organization=other_organization, uploaded_by=other_owner, size_bytes=999)
    repository = StoredFileRepository(db_session)

    assert await repository.total_size_for_organization(organization.id) == 350
    assert await repository.total_size_for_organization(other_organization.id) == 999
    assert sorted(await repository.list_storage_keys(organization.id)) == sorted(
        [first_file.storage_key, second_file.storage_key]
    )
    assert await repository.get_in_organization(other_organization.id, first_file.id) is None
    assert await repository.count_for_organization(organization.id) == 2


async def test_total_size_is_zero_without_files(db_session: AsyncSession) -> None:
    owner = await create_user(db_session, email="repo-empty@example.com")
    organization = await create_organization(db_session, owner=owner)

    assert await StoredFileRepository(db_session).total_size_for_organization(organization.id) == 0
