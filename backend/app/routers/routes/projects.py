from uuid import UUID

from fastapi import APIRouter
from fastapi_pagination import Page

from app.models.enums import ProjectStatus
from app.schemas.projects import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService
from app.utils.dependencies import CurrentMembership, DbSession

router = APIRouter(prefix="/orgs/{org_id}/projects", tags=["projects"])


@router.get("")
async def list_projects(
    membership: CurrentMembership,
    session: DbSession,
    status: ProjectStatus | None = None,
) -> Page[ProjectResponse]:
    return await ProjectService(session).list_projects(membership.organization_id, status=status)


@router.post("", status_code=201)
async def create_project(data: ProjectCreate, membership: CurrentMembership, session: DbSession) -> ProjectResponse:
    project = await ProjectService(session).create_project(membership, data)
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}")
async def get_project(project_id: UUID, membership: CurrentMembership, session: DbSession) -> ProjectResponse:
    project = await ProjectService(session).get_project(membership.organization_id, project_id)
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}")
async def update_project(
    project_id: UUID, data: ProjectUpdate, membership: CurrentMembership, session: DbSession
) -> ProjectResponse:
    project = await ProjectService(session).update_project(membership.organization_id, project_id, data)
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: UUID, membership: CurrentMembership, session: DbSession) -> None:
    await ProjectService(session).delete_project(membership.organization_id, project_id)
