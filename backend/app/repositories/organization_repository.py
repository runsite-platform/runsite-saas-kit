from uuid import UUID

from sqlalchemy import select

from app.models.membership import Membership
from app.models.organization import Organization
from app.utils.repository import SQLAlchemyRepository


class OrganizationRepository(SQLAlchemyRepository[Organization]):
    model = Organization

    async def slug_exists(self, slug: str) -> bool:
        return await self.exists(filter_params={"slug": slug})

    async def list_for_user(self, user_id: UUID) -> list[tuple[Organization, str]]:
        statement = (
            select(self.model, Membership.role)
            .join(Membership, Membership.organization_id == self.model.id)
            .where(Membership.user_id == user_id)
            .order_by(Membership.created_at, self.model.name)
        )
        result = await self.db.execute(statement)
        return [(organization, role) for organization, role in result.all()]
