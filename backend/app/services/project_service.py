from uuid import UUID

from fastapi_pagination import Page
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProjectStatus
from app.models.membership import Membership
from app.models.project import Project
from app.repositories.project_repository import ProjectRepository
from app.schemas.projects import ProjectCreate, ProjectUpdate
from app.services.plan_limits import PlanLimitsService
from app.utils.exceptions import not_found


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectRepository(session)
        self.plan_limits = PlanLimitsService(session)

    async def list_projects(self, organization_id: UUID, *, status: ProjectStatus | None = None) -> Page:
        return await self.projects.list_for_organization(organization_id, status=status)

    async def get_project(self, organization_id: UUID, project_id: UUID) -> Project:
        project = await self.projects.get_in_organization(organization_id, project_id)
        if project is None:
            raise not_found("Project")
        return project

    async def create_project(self, membership: Membership, data: ProjectCreate) -> Project:
        await self.plan_limits.ensure_can_add_project(membership.organization)
        project = Project(
            organization_id=membership.organization_id,
            name=data.name,
            description=data.description,
            status=ProjectStatus.ACTIVE,
            created_by_id=membership.user_id,
        )
        await self.projects.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def update_project(self, organization_id: UUID, project_id: UUID, data: ProjectUpdate) -> Project:
        project = await self.get_project(organization_id, project_id)
        changes = data.model_dump(exclude_unset=True)
        if changes.get("name") is not None:
            project.name = changes["name"]
        if "description" in changes:
            project.description = changes["description"]
        if changes.get("status") is not None:
            project.status = changes["status"]
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def delete_project(self, organization_id: UUID, project_id: UUID) -> None:
        project = await self.get_project(organization_id, project_id)
        await self.projects.delete(project)
        await self.session.commit()
