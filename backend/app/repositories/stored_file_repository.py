from uuid import UUID

from fastapi_pagination import Page
from sqlalchemy import func, select

from app.models.stored_file import StoredFile
from app.utils.repository import SQLAlchemyRepository


class StoredFileRepository(SQLAlchemyRepository[StoredFile]):
    model = StoredFile

    async def get_in_organization(self, organization_id: UUID, file_id: UUID) -> StoredFile | None:
        return await self.get_one(filter_params={"organization_id": organization_id, "id": file_id})

    async def list_for_organization(self, organization_id: UUID) -> Page:
        return await self.get_all(
            filter_params={"organization_id": organization_id},
            order_params={"created_at": "desc", "name": "asc"},
            pagination=True,
        )

    async def count_for_organization(self, organization_id: UUID) -> int:
        return await self.count_all(filter_params={"organization_id": organization_id})

    async def total_size_for_organization(self, organization_id: UUID) -> int:
        statement = select(func.coalesce(func.sum(self.model.size_bytes), 0)).where(
            self.model.organization_id == organization_id
        )
        return int(await self.db.scalar(statement) or 0)

    async def list_storage_keys(self, organization_id: UUID) -> list[str]:
        rows = await self.get_all("storage_key", filter_params={"organization_id": organization_id})
        return [row["storage_key"] for row in rows]
