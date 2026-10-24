from uuid import UUID

from fastapi import APIRouter
from fastapi_pagination import Page

from app.models.enums import ProjectStatus
from app.schemas.projects import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService
from app.utils.dependencies import CurrentMembership, DbSession

router = APIRouter()


@router.get("")
async def list_projects(
    membership: CurrentMembership,
    db: DbSession,
    status: ProjectStatus | None = None,
) -> Page[ProjectResponse]:
    """List organization projects."""
    return await ProjectService(db).list_projects(membership.organization_id, status=status)


@router.post("", status_code=201)
async def create_project(data: ProjectCreate, membership: CurrentMembership, db: DbSession) -> ProjectResponse:
    """Create a project in the organization."""
    project = await ProjectService(db).create_project(membership, data)
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}")
async def get_project(project_id: UUID, membership: CurrentMembership, db: DbSession) -> ProjectResponse:
    """Return a project by id."""
    project = await ProjectService(db).get_project(membership.organization_id, project_id)
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}")
async def update_project(
    project_id: UUID, data: ProjectUpdate, membership: CurrentMembership, db: DbSession
) -> ProjectResponse:
    """Update a project."""
    project = await ProjectService(db).update_project(membership.organization_id, project_id, data)
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: UUID, membership: CurrentMembership, db: DbSession) -> None:
    """Delete a project."""
    await ProjectService(db).delete_project(membership.organization_id, project_id)
