import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationKind, OrgRole
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.user import User
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.stored_file_repository import StoredFileRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user import UserRepository
from app.schemas.organizations import (
    OrganizationCreateRequest,
    OrganizationDetailResponse,
    OrganizationSummary,
    OrganizationUpdateRequest,
    PlanLimitsResponse,
)
from app.services.billing.plans import FREE_PLAN_ID, get_plan
from app.services.file_storage import ObjectStorage, delete_object_best_effort
from app.services.notification_service import NotificationEmailQueue, NotificationService
from app.utils.exceptions import BusinessError, not_found
from app.utils.security import utc_now
from app.utils.slugs import generate_unique_slug

logger = logging.getLogger(__name__)


def user_display_name(user: User) -> str:
    """Return the user's full name or the local part of their email."""
    full_name = (user.full_name or "").strip()
    return full_name or user.email.split("@", 1)[0]


def slug_taken() -> BusinessError:
    """Return the error for an organization slug that is already used."""
    return BusinessError("slug_taken", "This organization address is already taken", status_code=409)


class OrganizationService:
    """Service for organizations and their ownership."""

    def __init__(self, db: AsyncSession, *, storage: ObjectStorage | None = None) -> None:
        self.db = db
        self.storage = storage
        self.organization_repository = OrganizationRepository(db)
        self.membership_repository = MembershipRepository(db)
        self.invitation_repository = InvitationRepository(db)

    async def create_organization(self, user: User, data: OrganizationCreateRequest) -> OrganizationSummary:
        """Create an organization owned by the user."""
        owner_membership = await self._create_with_owner(user, name=data.name, slug_source=data.name)
        await self.db.commit()
        return OrganizationSummary.from_membership(owner_membership, storage=self.storage)

    async def create_personal_organization(self, user: User) -> Organization:
        """Called from SignupService without committing; the caller commits."""
        display_name = user_display_name(user)
        owner_membership = await self._create_with_owner(
            user, name=f"{display_name}'s workspace", slug_source=display_name
        )
        return owner_membership.organization

    async def list_summaries_for_user(self, user_id: UUID) -> list[OrganizationSummary]:
        """Return summaries of the organizations the user belongs to."""
        memberships = await self.membership_repository.list_for_user_with_organizations(user_id)
        return [OrganizationSummary.from_membership(membership, storage=self.storage) for membership in memberships]

    async def get_organization_detail(self, membership: Membership) -> OrganizationDetailResponse:
        """Return organization details with plan limits and counts."""
        organization = membership.organization
        plan = get_plan(organization.plan_id)
        member_count = await self.membership_repository.count_for_organization(organization.id)
        pending_invitation_count = await self.invitation_repository.count_pending_for_organization(
            organization.id, utc_now()
        )
        summary = OrganizationSummary.from_membership(membership, storage=self.storage)
        return OrganizationDetailResponse(
            **summary.model_dump(),
            plan_name=plan.name,
            owner_id=organization.owner_id,
            member_count=member_count,
            pending_invitation_count=pending_invitation_count,
            limits=PlanLimitsResponse(
                members=plan.limits.members, projects=plan.limits.projects, storage_mb=plan.limits.storage_mb
            ),
            created_at=organization.created_at,
        )

    async def update_organization(
        self, membership: Membership, data: OrganizationUpdateRequest
    ) -> OrganizationDetailResponse:
        """Update the organization name and slug."""
        organization = membership.organization
        if data.name is not None:
            organization.name = data.name
        if data.slug is not None and data.slug != organization.slug:
            if await self.organization_repository.slug_exists(data.slug):
                raise slug_taken()
            organization.slug = data.slug
        try:
            await self.db.flush()
        except IntegrityError as error:
            raise slug_taken() from error
        await self.db.commit()
        return await self.get_organization_detail(membership)

    async def delete_organization(self, membership: Membership) -> None:
        """Delete the organization and its stored objects."""
        organization = membership.organization
        await self._ensure_no_blocking_subscription(organization)
        await self._delete_organization_objects(organization)
        await self.organization_repository.delete(organization)
        await self.db.commit()

    async def transfer_ownership(
        self,
        owner_membership: Membership,
        target_membership_id: UUID,
        notification_emails: NotificationEmailQueue | None = None,
    ) -> None:
        """Transfer ownership to another member and notify them."""
        target_membership = await self.membership_repository.get_in_organization(
            owner_membership.organization_id, target_membership_id
        )
        if target_membership is None:
            raise not_found("Member")
        if target_membership.id == owner_membership.id:
            return
        owner_membership.role = OrgRole.ADMIN
        target_membership.role = OrgRole.OWNER
        organization = owner_membership.organization
        organization.owner_id = target_membership.user_id
        new_owner = await UserRepository(self.db).get_by_id(id=target_membership.user_id)
        if new_owner is not None:
            await NotificationService(self.db, notification_emails).notify(
                [new_owner],
                kind=NotificationKind.OWNERSHIP_TRANSFERRED,
                title=f"You are now the owner of {organization.name}",
                body="Ownership was transferred to you. You can now manage billing and delete the organization.",
                link=f"/app/{organization.slug}/settings",
                organization_id=organization.id,
            )
        await self.db.commit()

    async def _ensure_no_blocking_subscription(self, organization: Organization) -> None:
        if await SubscriptionRepository(self.db).has_blocking_subscription(organization.id):
            raise BusinessError(
                "active_subscription",
                "Cancel the subscription and wait for it to end before deleting this organization",
                status_code=409,
            )

    async def _delete_organization_objects(self, organization: Organization) -> None:
        storage_keys = await StoredFileRepository(self.db).list_storage_keys(organization.id)
        if organization.logo_key:
            storage_keys.append(organization.logo_key)
        if not storage_keys:
            return
        if self.storage is None:
            logger.warning(
                "Storage is not configured; %d objects of organization %s were left in the bucket",
                len(storage_keys),
                organization.id,
            )
            return
        for position, storage_key in enumerate(storage_keys):
            if not await delete_object_best_effort(self.storage, storage_key):
                logger.warning(
                    "%d objects of organization %s were left in the bucket",
                    len(storage_keys) - position,
                    organization.id,
                )
                return

    async def _create_with_owner(self, user: User, *, name: str, slug_source: str) -> Membership:
        if user.id is None:
            self.db.add(user)
            await self.db.flush()
        slug = await generate_unique_slug(slug_source, self.organization_repository.slug_exists)
        organization = await self.organization_repository.add(
            Organization(name=name, slug=slug, owner_id=user.id, plan_id=FREE_PLAN_ID)
        )
        return await self.membership_repository.add(
            Membership(organization=organization, user_id=user.id, role=OrgRole.OWNER)
        )
