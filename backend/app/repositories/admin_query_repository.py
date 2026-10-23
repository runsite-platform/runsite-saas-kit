from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import ColumnElement, Select, func, or_, select

from app.models import Membership, Organization, Payment, Subscription, User
from app.models.enums import AuthTokenKind, PlatformRole, SubscriptionStatus
from app.repositories.auth_token import AuthTokenRepository
from app.repositories.daily_counts import count_rows_per_day
from app.repositories.membership_repository import MembershipRepository
from app.repositories.oauth_account import OAuthAccountRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.utils.repository import SQLAlchemyRepository

LIKE_ESCAPE_CHARACTER = "\\"
CHURNED_STATUSES = (SubscriptionStatus.CANCELED, SubscriptionStatus.EXPIRED)


def contains_pattern(search: str) -> str:
    escaped_search = (
        search.replace(LIKE_ESCAPE_CHARACTER, LIKE_ESCAPE_CHARACTER * 2)
        .replace("%", LIKE_ESCAPE_CHARACTER + "%")
        .replace("_", LIKE_ESCAPE_CHARACTER + "_")
    )
    return f"%{escaped_search}%"


@dataclass(frozen=True)
class OrganizationListRow:
    organization: Organization
    members_count: int
    owner_email: str | None


class AdminQueryRepository(SQLAlchemyRepository[User]):
    model = User

    async def get_user(self, user_id: UUID) -> User | None:
        return await self.get_by_id(id=user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        return await self.db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))

    async def search_users(self, *, search: str | None) -> Page:
        filters: list[ColumnElement[bool]] = []
        if search:
            pattern = contains_pattern(search)
            filters.append(
                or_(
                    User.email.ilike(pattern, escape=LIKE_ESCAPE_CHARACTER),
                    User.full_name.ilike(pattern, escape=LIKE_ESCAPE_CHARACTER),
                )
            )
        return await self.get_all(
            filter_params={"and": filters},
            order_params={"created_at": "desc", "id": "asc"},
            pagination=True,
        )

    async def list_user_memberships(self, user_id: UUID) -> list[tuple[Membership, Organization]]:
        statement = (
            select(Membership, Organization)
            .join(Organization, Organization.id == Membership.organization_id)
            .where(Membership.user_id == user_id)
            .order_by(Organization.name)
        )
        result = await self.db.execute(statement)
        return [(membership, organization) for membership, organization in result.all()]

    async def has_oauth_account(self, user_id: UUID) -> bool:
        return await OAuthAccountRepository(self.db).exists(filter_params={"user_id": user_id})

    async def delete_refresh_tokens(self, user_id: UUID) -> None:
        await AuthTokenRepository(self.db).delete_for_user(user_id, AuthTokenKind.REFRESH)

    async def superadmin_exists(self) -> bool:
        return await self.exists(filter_params={"platform_role": PlatformRole.SUPERADMIN})

    async def get_organization(self, organization_id: UUID) -> Organization | None:
        return await OrganizationRepository(self.db).get_by_id(id=organization_id)

    @staticmethod
    def _members_count_expression() -> Any:
        return (
            select(func.count(Membership.id))
            .where(Membership.organization_id == Organization.id)
            .correlate(Organization)
            .scalar_subquery()
        )

    def _organization_rows_statement(self) -> Select[Any]:
        return select(
            Organization, self._members_count_expression().label("members_count"), User.email.label("owner_email")
        ).outerjoin(User, User.id == Organization.owner_id)

    async def search_organizations(self, *, search: str | None, plan_id: str | None) -> Page:
        filters: list[ColumnElement[bool]] = []
        if search:
            pattern = contains_pattern(search)
            filters.append(
                or_(
                    Organization.name.ilike(pattern, escape=LIKE_ESCAPE_CHARACTER),
                    Organization.slug.ilike(pattern, escape=LIKE_ESCAPE_CHARACTER),
                )
            )
        if plan_id:
            filters.append(Organization.plan_id == plan_id)
        statement = (
            select(
                Organization.id,
                Organization.name,
                Organization.slug,
                Organization.plan_id,
                Organization.plan_override_id,
                Organization.created_at,
                self._members_count_expression().label("members_count"),
                User.email.label("owner_email"),
            )
            .outerjoin(User, User.id == Organization.owner_id)
            .where(*filters)
            .order_by(Organization.created_at.desc(), Organization.id)
        )
        return await apaginate(self.db, statement)

    async def get_organization_row(self, organization_id: UUID) -> OrganizationListRow | None:
        result = await self.db.execute(self._organization_rows_statement().where(Organization.id == organization_id))
        row = result.first()
        if row is None:
            return None
        organization, members_count, owner_email = row
        return OrganizationListRow(organization=organization, members_count=int(members_count), owner_email=owner_email)

    async def list_organization_members(self, organization_id: UUID) -> list[tuple[Membership, User]]:
        return await MembershipRepository(self.db).list_with_users_for_organization(organization_id)

    async def get_latest_subscription(self, organization_id: UUID) -> Subscription | None:
        return await SubscriptionRepository(self.db).get_latest_for_organization(organization_id)

    async def list_recent_payments(self, organization_id: UUID) -> list[Payment]:
        return await PaymentRepository(self.db).list_recent_for_organization(organization_id)

    async def count_users(self) -> int:
        return await self.count_all()

    async def count_organizations(self) -> int:
        return await OrganizationRepository(self.db).count_all()

    async def count_subscriptions_by_status(self) -> dict[str, int]:
        result = await self.db.execute(select(Subscription.status, func.count()).group_by(Subscription.status))
        return {status: int(subscription_count) for status, subscription_count in result.all()}

    async def count_active_subscriptions_by_plan(self) -> list[tuple[str, str, int]]:
        result = await self.db.execute(
            select(Subscription.plan_id, Subscription.interval, func.count())
            .where(Subscription.status == SubscriptionStatus.ACTIVE)
            .group_by(Subscription.plan_id, Subscription.interval)
        )
        return [(plan_id, interval, int(subscription_count)) for plan_id, interval, subscription_count in result.all()]

    async def count_ended_trials(self, *, starts_at: datetime, ends_at: datetime) -> tuple[int, int]:
        statement = select(
            func.count(),
            func.count().filter(Subscription.status == SubscriptionStatus.ACTIVE),
        ).where(
            Subscription.trial_ends_at.is_not(None),
            Subscription.trial_ends_at >= starts_at,
            Subscription.trial_ends_at < ends_at,
            Subscription.status != SubscriptionStatus.TRIALING,
        )
        ended_trials, converted = (await self.db.execute(statement)).one()
        return int(ended_trials), int(converted)

    async def count_churned_subscriptions(self, *, starts_at: datetime, ends_at: datetime) -> int:
        return await SubscriptionRepository(self.db).count_all(
            filter_params={
                "status": ("in", CHURNED_STATUSES),
                "updated_at": ("between", starts_at, ends_at),
            }
        )

    async def count_signups_per_day(self, *, starts_at: datetime, ends_at: datetime) -> dict[date, int]:
        return await count_rows_per_day(self.db, User.created_at, starts_at=starts_at, ends_at=ends_at)

    async def count_new_organizations_per_day(self, *, starts_at: datetime, ends_at: datetime) -> dict[date, int]:
        return await count_rows_per_day(self.db, Organization.created_at, starts_at=starts_at, ends_at=ends_at)
