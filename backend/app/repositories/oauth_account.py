from uuid import UUID

from app.models.oauth_account import OAuthAccount
from app.utils.repository import SQLAlchemyRepository


class OAuthAccountRepository(SQLAlchemyRepository[OAuthAccount]):
    model = OAuthAccount

    async def get_by_provider_account(self, provider: str, provider_account_id: str) -> OAuthAccount | None:
        return await self.get_one(filter_params={"provider": provider, "provider_account_id": provider_account_id})

    async def has_provider(self, user_id: UUID, provider: str) -> bool:
        return await self.exists(filter_params={"user_id": user_id, "provider": provider})
