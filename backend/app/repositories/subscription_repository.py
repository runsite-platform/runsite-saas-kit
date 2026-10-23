from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import case, select

from app.models import Subscription
from app.models.subscription import BLOCKING_STATUSES, PLAN_GRANTING_STATUSES
from app.utils.repository import SQLAlchemyRepository

NEWEST_FIRST = {"created_at": "desc", "id": "desc"}


class SubscriptionRepository(SQLAlchemyRepository[Subscription]):
    model = Subscription

    async def get_by_provider_id(self, provider: str, provider_subscription_id: str) -> Subscription | None:
        return await self.get_one(
            filter_params={"provider": provider, "provider_subscription_id": provider_subscription_id}
        )

    async def list_for_organization(self, organization_id: UUID) -> Sequence[Subscription]:
        return await self.get_all(filter_params={"organization_id": organization_id}, order_params=NEWEST_FIRST)

    async def get_latest_for_organization(self, organization_id: UUID) -> Subscription | None:
        return await self.get_one(filter_params={"organization_id": organization_id}, order_params=NEWEST_FIRST)

    async def get_current_for_organization(self, organization_id: UUID) -> Subscription | None:
        blocking_first = case((self.model.status.in_(BLOCKING_STATUSES), 0), else_=1)
        statement = (
            select(self.model)
            .where(self.model.organization_id == organization_id)
            .order_by(blocking_first, self.model.created_at.desc(), self.model.id.desc())
            .limit(1)
        )
        return await self.db.scalar(statement)

    async def get_plan_granting_for_organization(self, organization_id: UUID) -> Subscription | None:
        return await self.get_one(
            filter_params={"organization_id": organization_id, "status": ("in", PLAN_GRANTING_STATUSES)},
            order_params=NEWEST_FIRST,
        )

    async def has_blocking_subscription(self, organization_id: UUID) -> bool:
        return await self.exists(
            filter_params={"organization_id": organization_id, "status": ("in", BLOCKING_STATUSES)}
        )
