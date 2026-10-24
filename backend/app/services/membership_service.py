from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import NotificationKind, OrgRole
from app.models.membership import Membership
from app.models.user import User
from app.repositories.membership_repository import MembershipRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user import UserRepository
from app.schemas.members import MemberResponse
from app.services.notification_service import NotificationEmailQueue, NotificationService
from app.utils.exceptions import BusinessError, forbidden, not_found

MANAGER_ROLES = (OrgRole.OWNER, OrgRole.ADMIN)


def build_member_response(membership: Membership, user: User) -> MemberResponse:
    """Build a member response from a membership and its user."""
    return MemberResponse(
        id=membership.id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        joined_at=membership.created_at,
    )


def owner_cannot_be_removed(message: str) -> BusinessError:
    """Return the error raised when an action targets the owner."""
    return BusinessError("owner_cannot_be_removed", message, status_code=400)


class MembershipService:
    """Service for organization members."""

    def __init__(self, db: AsyncSession, notification_emails: NotificationEmailQueue | None = None) -> None:
        self.db = db
        self.membership_repository = MembershipRepository(db)
        self.organization_repository = OrganizationRepository(db)
        self.notification_service = NotificationService(db, notification_emails)

    async def list_members(self, organization_id: UUID) -> list[MemberResponse]:
        """Return all members of the organization."""
        rows = await self.membership_repository.list_with_users_for_organization(organization_id)
        return [build_member_response(membership, user) for membership, user in rows]

    async def change_role(self, organization_id: UUID, membership_id: UUID, role: str) -> MemberResponse:
        """Change a non-owner member's role and notify them."""
        row = await self.membership_repository.get_with_user_in_organization(organization_id, membership_id)
        if row is None:
            raise not_found("Member")
        membership, user = row
        if membership.role == OrgRole.OWNER:
            raise owner_cannot_be_removed("The owner's role changes only through ownership transfer")
        role_changed = membership.role != role
        membership.role = role
        organization = await self.organization_repository.get_by_id(id=organization_id)
        if role_changed and organization is not None:
            await self.notification_service.notify(
                [user],
                kind=NotificationKind.MEMBER_ROLE_CHANGED,
                title=f"Your role in {organization.name} changed",
                body=f"You are now {role} of {organization.name}.",
                link=f"/app/{organization.slug}/members",
                organization_id=organization.id,
            )
        await self.db.commit()
        return build_member_response(membership, user)

    async def remove_member(self, actor_membership: Membership, membership_id: UUID) -> None:
        """Remove a member or let the actor leave the organization."""
        target_membership = await self.membership_repository.get_in_organization(
            actor_membership.organization_id, membership_id
        )
        if target_membership is None:
            raise not_found("Member")
        if target_membership.role == OrgRole.OWNER:
            raise owner_cannot_be_removed("The owner cannot be removed; transfer ownership first")
        is_leaving = target_membership.user_id == actor_membership.user_id
        if not is_leaving and actor_membership.role not in MANAGER_ROLES:
            raise forbidden()
        await self.membership_repository.delete(target_membership)
        if not is_leaving:
            await self._notify_removed_member(actor_membership.organization_id, target_membership.user_id)
        await self.db.commit()

    async def _notify_removed_member(self, organization_id: UUID, removed_user_id: UUID) -> None:
        organization = await self.organization_repository.get_by_id(id=organization_id)
        removed_user = await UserRepository(self.db).get_by_id(id=removed_user_id)
        if organization is None or removed_user is None:
            return
        await self.notification_service.notify(
            [removed_user],
            kind=NotificationKind.MEMBER_REMOVED,
            title=f"You were removed from {organization.name}",
            body=f"You no longer have access to {organization.name}.",
            link="/app",
        )
