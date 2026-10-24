from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import quote
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.constants.enums import NotificationKind, OrgRole
from app.models.invitation import Invitation
from app.models.membership import Membership
from app.models.user import User
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user import UserRepository
from app.schemas.invitations import InvitationCreateRequest, InvitationPreviewResponse, InvitationResponse
from app.schemas.organizations import OrganizationSummary
from app.services.notification_service import NotificationEmailQueue, NotificationService
from app.services.organization_service import user_display_name
from app.services.plan_limits import PlanLimitsService
from app.utils.exceptions import BusinessError, not_found
from app.utils.security import generate_token, hash_token, normalize_email, utc_now

INVITATION_LIFETIME = timedelta(days=7)


@dataclass(frozen=True)
class CreatedInvitation:
    """Newly created invitation with its raw token and invite URL."""

    invitation: Invitation
    token: str
    invite_url: str


def invalid_invitation_token() -> BusinessError:
    """Return the error for an invalid or expired invitation token."""
    return BusinessError("invalid_token", "This invitation link is invalid or has expired", status_code=400)


class InvitationService:
    """Service for organization invitations."""

    def __init__(
        self, db: AsyncSession, settings: Settings, notification_emails: NotificationEmailQueue | None = None
    ) -> None:
        self.db = db
        self.settings = settings
        self.notification_service = NotificationService(db, notification_emails)
        self.organization_repository = OrganizationRepository(db)
        self.membership_repository = MembershipRepository(db)
        self.invitation_repository = InvitationRepository(db)
        self.user_repository = UserRepository(db)

    def build_invite_url(self, token: str) -> str:
        """Return the frontend URL for accepting an invitation token."""
        return f"{self.settings.APP_URL}/invite/{quote(token)}"

    async def create_invitation(
        self, membership: Membership, inviter: User, data: InvitationCreateRequest
    ) -> CreatedInvitation:
        """Create an invitation, replacing any unaccepted one for the email."""
        organization = membership.organization
        email = normalize_email(data.email)
        if await self.membership_repository.get_by_email_in_organization(organization.id, email) is not None:
            raise BusinessError("already_member", "This person is already a member", status_code=409)
        await self.invitation_repository.delete_unaccepted_for_email(organization.id, email)
        await PlanLimitsService(self.db).ensure_can_add_member(organization)
        token = generate_token()
        invitation = await self.invitation_repository.add(
            Invitation(
                organization_id=organization.id,
                email=email,
                role=data.role,
                token_hash=hash_token(token),
                invited_by_id=inviter.id,
                expires_at=utc_now() + INVITATION_LIFETIME,
            )
        )
        await self.db.commit()
        return CreatedInvitation(invitation=invitation, token=token, invite_url=self.build_invite_url(token))

    async def list_pending(self, organization_id: UUID) -> list[InvitationResponse]:
        """Return the organization's pending, unexpired invitations."""
        invitations = await self.invitation_repository.list_pending_for_organization(organization_id, utc_now())
        return [InvitationResponse.model_validate(invitation) for invitation in invitations]

    async def revoke_invitation(self, organization_id: UUID, invitation_id: UUID) -> None:
        """Delete an unaccepted invitation from the organization."""
        invitation = await self.invitation_repository.get_in_organization(organization_id, invitation_id)
        if invitation is None or invitation.accepted_at is not None:
            raise not_found("Invitation")
        await self.invitation_repository.delete(invitation)
        await self.db.commit()

    async def get_preview(self, token: str) -> InvitationPreviewResponse:
        """Return public invitation details for the given token."""
        invitation = await self._get_unaccepted_invitation(token)
        organization = await self.organization_repository.get_by_id(id=invitation.organization_id)
        if organization is None:
            raise invalid_invitation_token()
        inviter = (
            await self.user_repository.get_by_id(id=invitation.invited_by_id) if invitation.invited_by_id else None
        )
        return InvitationPreviewResponse(
            organization_name=organization.name,
            inviter_name=user_display_name(inviter) if inviter else None,
            email=invitation.email,
            role=invitation.role,
            expired=invitation.expires_at <= utc_now(),
        )

    async def accept_invitation(self, user: User, token: str) -> OrganizationSummary:
        """Accept an invitation and add the user to the organization."""
        invitation = await self._get_unaccepted_invitation(token)
        now = utc_now()
        if invitation.expires_at <= now:
            raise invalid_invitation_token()
        if invitation.email != normalize_email(user.email):
            raise BusinessError(
                "invitation_email_mismatch",
                "This invitation was sent to a different email address",
                status_code=403,
            )
        organization = await self.organization_repository.get_by_id(id=invitation.organization_id)
        if organization is None:
            raise invalid_invitation_token()
        membership = await self.membership_repository.get_for_user(organization.id, user.id)
        if membership is None:
            membership = await self.membership_repository.add(
                Membership(organization=organization, user_id=user.id, role=invitation.role)
            )
            await self._notify_managers_about_new_member(organization.id, organization.name, organization.slug, user)
        invitation.accepted_at = now
        await self.db.commit()
        return OrganizationSummary.from_membership(membership)

    async def _notify_managers_about_new_member(
        self, organization_id: UUID, organization_name: str, organization_slug: str, new_member: User
    ) -> None:
        rows = await self.membership_repository.list_with_users_for_organization(organization_id)
        managers = [
            manager
            for membership, manager in rows
            if membership.role in (OrgRole.OWNER, OrgRole.ADMIN) and manager.id != new_member.id
        ]
        await self.notification_service.notify(
            managers,
            kind=NotificationKind.MEMBER_JOINED,
            title=f"{user_display_name(new_member)} joined {organization_name}",
            body=f"{new_member.email} accepted the invitation and is now a member.",
            link=f"/app/{organization_slug}/members",
            organization_id=organization_id,
        )

    async def _get_unaccepted_invitation(self, token: str) -> Invitation:
        invitation = await self.invitation_repository.get_by_token_hash(hash_token(token))
        if invitation is None or invitation.accepted_at is not None:
            raise invalid_invitation_token()
        return invitation
