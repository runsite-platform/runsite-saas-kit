import logging
from uuid import UUID

from fastapi_pagination import Page
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.constants.enums import AuthTokenKind, PlatformRole
from app.models import AuthToken, User
from app.repositories.admin_query_repository import AdminQueryRepository, OrganizationListRow
from app.schemas.admin import (
    AdminOrganizationDetail,
    AdminOrganizationMember,
    AdminOrganizationSummary,
    AdminPaymentInfo,
    AdminSubscriptionInfo,
    AdminUserDetail,
    AdminUserMembership,
    AdminUserSummary,
    ImpersonationResponse,
    PlanOverrideRequest,
)
from app.services.auth_service import EMAIL_VERIFY_TOKEN_LIFETIME
from app.services.billing.billing_service import BillingService
from app.services.billing.plans import PLANS
from app.utils.clock import Clock, utc_now
from app.utils.exceptions import BusinessError, not_found
from app.utils.security import create_access_token, generate_token, hash_token

logger = logging.getLogger(__name__)

IMPERSONATION_TOKEN_MINUTES = 30


def ensure_can_moderate(actor: User, target: User) -> None:
    """Raise if the actor may not block or unblock the target user."""
    if target.id == actor.id:
        raise BusinessError("forbidden", "You cannot block or unblock yourself", 403)
    if target.platform_role == PlatformRole.SUPERADMIN:
        raise BusinessError("forbidden", "Superadmins cannot be blocked or unblocked", 403)
    if target.platform_role == PlatformRole.ADMIN and actor.platform_role != PlatformRole.SUPERADMIN:
        raise BusinessError("forbidden", "Only a superadmin can block or unblock an admin", 403)


def organization_summary(row: OrganizationListRow) -> AdminOrganizationSummary:
    """Build an admin organization summary from a list row."""
    organization = row.organization
    return AdminOrganizationSummary(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        plan_id=organization.plan_id,
        plan_override_id=organization.plan_override_id,
        owner_email=row.owner_email,
        members_count=row.members_count,
        created_at=organization.created_at,
    )


class AdminService:
    """Service for platform admin user and organization management."""

    def __init__(self, db: AsyncSession, settings: Settings, clock: Clock = utc_now) -> None:
        self.db = db
        self.settings = settings
        self.clock = clock
        self.queries = AdminQueryRepository(db)

    async def list_users(self, *, search: str | None) -> Page:
        """Return a page of users matching the optional search."""
        return await self.queries.search_users(search=search.strip() if search else None)

    async def get_user_detail(self, user_id: UUID) -> AdminUserDetail:
        """Return a user's details with memberships and login methods."""
        user = await self._get_user(user_id)
        membership_rows = await self.queries.list_user_memberships(user.id)
        return AdminUserDetail(
            **AdminUserSummary.model_validate(user).model_dump(),
            has_password=user.password_hash is not None,
            google_linked=await self.queries.has_oauth_account(user.id),
            memberships=[
                AdminUserMembership(
                    organization_id=organization.id,
                    organization_name=organization.name,
                    organization_slug=organization.slug,
                    role=membership.role,
                    plan_id=organization.plan_id,
                )
                for membership, organization in membership_rows
            ],
        )

    async def block_user(self, actor: User, user_id: UUID) -> AdminUserSummary:
        """Block a user and revoke their refresh tokens."""
        target = await self._get_user(user_id)
        ensure_can_moderate(actor, target)
        target.is_blocked = True
        await self.queries.delete_refresh_tokens(target.id)
        await self.db.commit()
        logger.info("User %s blocked by %s", target.id, actor.id)
        return AdminUserSummary.model_validate(target)

    async def unblock_user(self, actor: User, user_id: UUID) -> AdminUserSummary:
        """Unblock a previously blocked user."""
        target = await self._get_user(user_id)
        ensure_can_moderate(actor, target)
        target.is_blocked = False
        await self.db.commit()
        logger.info("User %s unblocked by %s", target.id, actor.id)
        return AdminUserSummary.model_validate(target)

    async def create_verification_token(self, user_id: UUID) -> tuple[User, str | None]:
        """Create an email verification token, or None if already verified."""
        user = await self._get_user(user_id)
        if user.is_email_verified:
            return user, None
        raw_token = generate_token()
        self.db.add(
            AuthToken(
                user_id=user.id,
                kind=AuthTokenKind.EMAIL_VERIFY,
                token_hash=hash_token(raw_token),
                expires_at=self.clock() + EMAIL_VERIFY_TOKEN_LIFETIME,
            )
        )
        await self.db.commit()
        return user, raw_token

    async def set_admin_role(self, user_id: UUID, *, grant: bool) -> AdminUserSummary:
        """Grant or revoke the platform admin role for a user."""
        target = await self._get_user(user_id)
        if target.platform_role == PlatformRole.SUPERADMIN:
            raise BusinessError("forbidden", "Superadmin roles cannot be changed here", 403)
        target.platform_role = PlatformRole.ADMIN if grant else PlatformRole.USER
        await self.db.commit()
        return AdminUserSummary.model_validate(target)

    async def impersonate(self, actor: User, user_id: UUID) -> ImpersonationResponse:
        """Issue a short-lived access token to act as the target user."""
        target = await self._get_user(user_id)
        if target.platform_role == PlatformRole.SUPERADMIN:
            raise BusinessError("cannot_impersonate", "Superadmins cannot be impersonated", 403)
        if target.is_blocked:
            raise BusinessError("cannot_impersonate", "Blocked users cannot be impersonated", 403)
        access_token = create_access_token(
            target.id,
            secret=self.settings.JWT_SECRET,
            impersonated_by=actor.id,
            expires_minutes=IMPERSONATION_TOKEN_MINUTES,
        )
        logger.warning("Superadmin %s started impersonating user %s", actor.id, target.id)
        return ImpersonationResponse(access_token=access_token, expires_in=IMPERSONATION_TOKEN_MINUTES * 60)

    async def list_organizations(self, *, search: str | None, plan_id: str | None) -> Page:
        """Return a page of organizations filtered by search and plan."""
        return await self.queries.search_organizations(search=search.strip() if search else None, plan_id=plan_id)

    async def get_organization_detail(self, organization_id: UUID) -> AdminOrganizationDetail:
        """Return organization details with members, subscription and payments."""
        row = await self.queries.get_organization_row(organization_id)
        if row is None:
            raise not_found("Organization")
        organization = row.organization
        member_rows = await self.queries.list_organization_members(organization.id)
        subscription = await self.queries.get_latest_subscription(organization.id)
        payments = await self.queries.list_recent_payments(organization.id)
        return AdminOrganizationDetail(
            **organization_summary(row).model_dump(),
            plan_override_reason=organization.plan_override_reason,
            billing_provider=organization.billing_provider,
            members=[
                AdminOrganizationMember(
                    membership_id=membership.id,
                    user_id=user.id,
                    email=user.email,
                    full_name=user.full_name,
                    role=membership.role,
                )
                for membership, user in member_rows
            ],
            subscription=AdminSubscriptionInfo.model_validate(subscription) if subscription else None,
            payments=[AdminPaymentInfo.model_validate(payment) for payment in payments],
        )

    async def override_plan(
        self, actor: User, organization_id: UUID, request: PlanOverrideRequest, billing_service: BillingService
    ) -> AdminOrganizationDetail:
        """Set or clear an organization's plan override."""
        if request.plan_id is not None and request.plan_id not in PLANS:
            raise BusinessError("plan_unavailable", f"Unknown plan '{request.plan_id}'", 400)
        organization = await self.queries.get_organization(organization_id)
        if organization is None:
            raise not_found("Organization")
        await billing_service.set_plan_override(organization, request.plan_id, request.reason)
        logger.info("Plan override for organization %s set to %s by %s", organization.id, request.plan_id, actor.id)
        return await self.get_organization_detail(organization.id)

    async def _get_user(self, user_id: UUID) -> User:
        user = await self.queries.get_user(user_id)
        if user is None:
            raise not_found("User")
        return user
