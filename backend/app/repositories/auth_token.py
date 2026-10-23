from datetime import datetime
from uuid import UUID

from app.models.auth_token import AuthToken
from app.models.enums import AuthTokenKind
from app.utils.repository import SQLAlchemyRepository


class AuthTokenRepository(SQLAlchemyRepository[AuthToken]):
    model = AuthToken

    async def get_by_hash(self, token_hash: str, kind: AuthTokenKind) -> AuthToken | None:
        return await self.get_one(filter_params={"token_hash": token_hash, "kind": kind})

    async def revoke_family(self, family_id: UUID, revoked_at: datetime) -> None:
        await self.update_all(
            values={"used_at": revoked_at},
            filter_params={"family_id": family_id, "used_at": ("null",)},
        )

    async def revoke_for_user(self, user_id: UUID, kind: AuthTokenKind, revoked_at: datetime) -> None:
        await self.update_all(
            values={"used_at": revoked_at},
            filter_params={"user_id": user_id, "kind": kind, "used_at": ("null",)},
        )

    async def delete_for_user(self, user_id: UUID, kind: AuthTokenKind) -> None:
        await self.delete_all(filter_params={"user_id": user_id, "kind": kind})
