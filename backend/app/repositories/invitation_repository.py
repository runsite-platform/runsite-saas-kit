from datetime import datetime
from typing import Any
from uuid import UUID

from app.models.invitation import Invitation
from app.utils.repository import SQLAlchemyRepository
from app.utils.security import normalize_email


def pending_invitation_filter(organization_id: UUID, now: datetime) -> dict[str, Any]:
    return {"organization_id": organization_id, "accepted_at": ("null",), "expires_at": ("gt", now)}


class InvitationRepository(SQLAlchemyRepository[Invitation]):
    model = Invitation

    async def get_by_token_hash(self, token_hash: str) -> Invitation | None:
        return await self.get_one(filter_params={"token_hash": token_hash})

    async def get_in_organization(self, organization_id: UUID, invitation_id: UUID) -> Invitation | None:
        return await self.get_one(filter_params={"organization_id": organization_id, "id": invitation_id})

    async def list_pending_for_organization(self, organization_id: UUID, now: datetime) -> list[Invitation]:
        invitations = await self.get_all(
            filter_params=pending_invitation_filter(organization_id, now),
            order_params={"created_at": "desc", "email": "asc"},
        )
        return list(invitations)

    async def count_pending_for_organization(self, organization_id: UUID, now: datetime) -> int:
        return await self.count_all(filter_params=pending_invitation_filter(organization_id, now))

    async def delete_unaccepted_for_email(self, organization_id: UUID, email: str) -> None:
        await self.delete_all(
            filter_params={
                "organization_id": organization_id,
                "email": normalize_email(email),
                "accepted_at": ("null",),
            }
        )
        await self.db.flush()
