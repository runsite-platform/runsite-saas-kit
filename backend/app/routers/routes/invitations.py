from uuid import UUID

from fastapi import APIRouter, status

from app.emails.contents import InvitationEmailContent
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
    EmailQueueDep,
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
    membership: OrgManagerMembership,
    inviter: VerifiedUser,
    db: DbSession,
    settings: AppSettings,
    email_queue: EmailQueueDep,
) -> InvitationCreatedResponse:
    """Invite a user to the organization by email."""
    created_invitation = await InvitationService(db, settings).create_invitation(membership, inviter, data)
    email_queue.enqueue(
        created_invitation.invitation.email,
        InvitationEmailContent(
            link=created_invitation.invite_url,
            organization_name=membership.organization.name,
            inviter_name=user_display_name(inviter),
        ),
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
    email_queue: EmailQueueDep,
) -> OrganizationSummary:
    """Accept an invitation for the current user."""
    return await InvitationService(db, settings, email_queue).accept_invitation(user, token)
