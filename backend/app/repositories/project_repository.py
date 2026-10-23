from uuid import UUID

from fastapi_pagination import Page

from app.models.enums import ProjectStatus
from app.models.project import Project
from app.utils.repository import SQLAlchemyRepository


class ProjectRepository(SQLAlchemyRepository[Project]):
    model = Project

    async def get_in_organization(self, organization_id: UUID, project_id: UUID) -> Project | None:
        return await self.get_one(filter_params={"organization_id": organization_id, "id": project_id})

    async def list_for_organization(self, organization_id: UUID, *, status: ProjectStatus | None = None) -> Page:
        filter_params = {"organization_id": organization_id}
        if status is not None:
            filter_params["status"] = status
        return await self.get_all(
            filter_params=filter_params,
            order_params={"created_at": "desc", "name": "asc"},
            pagination=True,
        )

    async def count_for_organization(self, organization_id: UUID) -> int:
        return await self.count_all(filter_params={"organization_id": organization_id})
