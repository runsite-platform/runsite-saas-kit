from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import ProjectStatus
from app.models.stored_file import StoredFile
from tests.factories import create_organization, create_project, create_stored_file, create_user


async def test_project_defaults_to_active_status(db_session: AsyncSession) -> None:
    owner = await create_user(db_session, email="models-owner@example.com")
    organization = await create_organization(db_session, owner=owner)

    project = await create_project(db_session, organization=organization, created_by=owner, name="Website")
    await db_session.refresh(project)

    assert project.status == ProjectStatus.ACTIVE
    assert project.organization_id == organization.id
    assert project.created_by_id == owner.id
    assert project.description is None
    assert project.created_at is not None


async def test_stored_file_keeps_size_and_key(db_session: AsyncSession) -> None:
    owner = await create_user(db_session, email="models-files@example.com")
    organization = await create_organization(db_session, owner=owner)

    stored_file = await create_stored_file(
        db_session, organization=organization, uploaded_by=owner, name="report.pdf", size_bytes=2048
    )
    loaded = await db_session.get(StoredFile, stored_file.id)

    assert loaded is not None
    assert loaded.size_bytes == 2048
    assert loaded.storage_key.startswith(f"orgs/{organization.id}/files/")
    assert loaded.storage_key.endswith("-report.pdf")
