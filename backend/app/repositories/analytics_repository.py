from datetime import date, datetime
from uuid import UUID

from app.models import Project
from app.repositories.daily_counts import count_rows_per_day
from app.repositories.membership_repository import MembershipRepository
from app.utils.repository import SQLAlchemyRepository


class AnalyticsRepository(SQLAlchemyRepository[Project]):
    model = Project

    async def count_members(self, organization_id: UUID) -> int:
        return await MembershipRepository(self.db).count_for_organization(organization_id)

    async def count_projects_per_day(
        self, organization_id: UUID, *, starts_at: datetime, ends_at: datetime
    ) -> dict[date, int]:
        return await count_rows_per_day(
            self.db,
            self.model.created_at,
            starts_at=starts_at,
            ends_at=ends_at,
            filters=(self.model.organization_id == organization_id,),
        )
