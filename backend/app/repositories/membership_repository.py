from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import contains_eager, joinedload

from app.models.membership import Membership
from app.models.organization import Organization
from app.models.user import User
from app.utils.repository import SQLAlchemyRepository
from app.utils.security import normalize_email


class MembershipRepository(SQLAlchemyRepository[Membership]):
    model = Membership

    async def get_for_user(self, organization_id: UUID, user_id: UUID) -> Membership | None:
        statement = (
            select(self.model)
            .options(joinedload(self.model.organization))
            .where(self.model.organization_id == organization_id, self.model.user_id == user_id)
        )
        return await self.db.scalar(statement)

    async def get_in_organization(self, organization_id: UUID, membership_id: UUID) -> Membership | None:
        return await self.get_one(filter_params={"organization_id": organization_id, "id": membership_id})

    async def get_with_user_in_organization(
        self, organization_id: UUID, membership_id: UUID
    ) -> tuple[Membership, User] | None:
        statement = (
            select(self.model, User)
            .join(User, User.id == self.model.user_id)
            .where(self.model.organization_id == organization_id, self.model.id == membership_id)
        )
        row = (await self.db.execute(statement)).one_or_none()
        if row is None:
            return None
        membership, user = row
        return membership, user

    async def list_with_users_for_organization(self, organization_id: UUID) -> list[tuple[Membership, User]]:
        statement = (
            select(self.model, User)
            .join(User, User.id == self.model.user_id)
            .where(self.model.organization_id == organization_id)
            .order_by(self.model.created_at, User.email)
        )
        result = await self.db.execute(statement)
        return [(membership, user) for membership, user in result.all()]

    async def count_for_organization(self, organization_id: UUID) -> int:
        return await self.count_all(filter_params={"organization_id": organization_id})

    async def get_by_email_in_organization(self, organization_id: UUID, email: str) -> Membership | None:
        statement = (
            select(self.model)
            .join(User, User.id == self.model.user_id)
            .where(self.model.organization_id == organization_id, User.email == normalize_email(email))
        )
        return await self.db.scalar(statement)

    async def list_for_user_with_organizations(self, user_id: UUID) -> list[Membership]:
        statement = (
            select(self.model)
            .join(self.model.organization)
            .options(contains_eager(self.model.organization))
            .where(self.model.user_id == user_id)
            .order_by(self.model.created_at, Organization.name)
        )
        return list((await self.db.scalars(statement)).all())
