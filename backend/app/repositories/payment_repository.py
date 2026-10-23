from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from app.models import Payment
from app.utils.repository import SQLAlchemyRepository

PAYMENT_HISTORY_LIMIT = 100
RECENT_PAYMENTS_LIMIT = 20


class PaymentRepository(SQLAlchemyRepository[Payment]):
    model = Payment

    async def get_by_provider_id(self, provider: str, provider_payment_id: str) -> Payment | None:
        return await self.get_one(filter_params={"provider": provider, "provider_payment_id": provider_payment_id})

    async def list_for_organization(self, organization_id: UUID) -> Sequence[Payment]:
        statement = (
            select(self.model)
            .where(self.model.organization_id == organization_id)
            .order_by(self.model.paid_at.desc().nulls_last(), self.model.created_at.desc(), self.model.id.desc())
            .limit(PAYMENT_HISTORY_LIMIT)
        )
        return (await self.db.scalars(statement)).all()

    async def list_recent_for_organization(self, organization_id: UUID) -> list[Payment]:
        statement = (
            select(self.model)
            .where(self.model.organization_id == organization_id)
            .order_by(self.model.created_at.desc(), self.model.id.desc())
            .limit(RECENT_PAYMENTS_LIMIT)
        )
        return list((await self.db.scalars(statement)).all())
