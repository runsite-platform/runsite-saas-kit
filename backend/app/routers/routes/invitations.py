from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, status

from app.schemas.invitations import (
    InvitationCreatedResponse,
    InvitationCreateRequest,
    InvitationPreviewResponse,
    InvitationResponse,
)
from app.schemas.organizations import OrganizationSummary
from app.services.invitation_service import InvitationService
from app.services.organization_service import user_display_name
from app.utils.dependencies import (
    AppSettings,
    CurrentUser,
    DbSession,
    EmailServiceDep,
    NotificationEmailQueueDep,
    OrgManagerMembership,
    VerifiedUser,
)

organization_invitations_router = APIRouter()
public_invitations_router = APIRouter()


@organization_invitations_router.get("")
async def list_invitations(
    membership: OrgManagerMembership, db: DbSession, settings: AppSettings
) -> list[InvitationResponse]:
    """List pending invitations of the organization."""
    return await InvitationService(db, settings).list_pending(membership.organization_id)


@organization_invitations_router.post("", status_code=status.HTTP_201_CREATED)
async def create_invitation(
    data: InvitationCreateRequest,
    background_tasks: BackgroundTasks,
    membership: OrgManagerMembership,
    inviter: VerifiedUser,
    db: DbSession,
    settings: AppSettings,
    email_service: EmailServiceDep,
) -> InvitationCreatedResponse:
    """Invite a user to the organization by email."""
    created_invitation = await InvitationService(db, settings).create_invitation(membership, inviter, data)
    background_tasks.add_task(
        email_service.send_invitation_email,
        email=created_invitation.invitation.email,
        organization_name=membership.organization.name,
        inviter_name=user_display_name(inviter),
        token=created_invitation.token,
    )
    return InvitationCreatedResponse(
        invitation=InvitationResponse.model_validate(created_invitation.invitation),
        invite_url=created_invitation.invite_url,
    )


@organization_invitations_router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    invitation_id: UUID, membership: OrgManagerMembership, db: DbSession, settings: AppSettings
) -> None:
    """Revoke a pending invitation."""
    await InvitationService(db, settings).revoke_invitation(membership.organization_id, invitation_id)


@public_invitations_router.get("/{token}")
async def get_invitation_preview(token: str, db: DbSession, settings: AppSettings) -> InvitationPreviewResponse:
    """Return public invitation details by token."""
    return await InvitationService(db, settings).get_preview(token)


@public_invitations_router.post("/{token}/accept")
async def accept_invitation(
    token: str,
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
    notification_emails: NotificationEmailQueueDep,
) -> OrganizationSummary:
    """Accept an invitation for the current user."""
    return await InvitationService(db, settings, notification_emails).accept_invitation(user, token)
