from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.models import BillingEvent
from app.utils.repository import SQLAlchemyRepository


class BillingEventRepository(SQLAlchemyRepository[BillingEvent]):
    model = BillingEvent

    async def insert_if_absent(self, *, provider: str, event_id: str, event_type: str, payload: dict[str, Any]) -> bool:
        statement = (
            insert(self.model)
            .values(provider=provider, event_id=event_id, event_type=event_type, payload=payload)
            .on_conflict_do_nothing(index_elements=["provider", "event_id"])
            .returning(self.model.id)
        )
        inserted_id = await self.db.scalar(statement)
        return inserted_id is not None

    async def get_by_provider_event_id(
        self, provider: str, event_id: str, *, for_update: bool = False
    ) -> BillingEvent | None:
        if not for_update:
            return await self.get_one(filter_params={"provider": provider, "event_id": event_id})
        statement = (
            select(self.model)
            .where(self.model.provider == provider, self.model.event_id == event_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return await self.db.scalar(statement)
