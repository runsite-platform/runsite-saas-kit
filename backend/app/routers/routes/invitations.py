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

organization_invitations_router = APIRouter(prefix="/orgs/{org_id}/invitations", tags=["invitations"])
public_invitations_router = APIRouter(prefix="/invitations", tags=["invitations"])


@organization_invitations_router.get("")
async def list_invitations(
    membership: OrgManagerMembership, session: DbSession, settings: AppSettings
) -> list[InvitationResponse]:
    return await InvitationService(session, settings).list_pending(membership.organization_id)


@organization_invitations_router.post("", status_code=status.HTTP_201_CREATED)
async def create_invitation(
    data: InvitationCreateRequest,
    background_tasks: BackgroundTasks,
    membership: OrgManagerMembership,
    inviter: VerifiedUser,
    session: DbSession,
    settings: AppSettings,
    email_service: EmailServiceDep,
) -> InvitationCreatedResponse:
    created_invitation = await InvitationService(session, settings).create_invitation(membership, inviter, data)
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
    invitation_id: UUID, membership: OrgManagerMembership, session: DbSession, settings: AppSettings
) -> None:
    await InvitationService(session, settings).revoke_invitation(membership.organization_id, invitation_id)


@public_invitations_router.get("/{token}")
async def get_invitation_preview(token: str, session: DbSession, settings: AppSettings) -> InvitationPreviewResponse:
    return await InvitationService(session, settings).get_preview(token)


@public_invitations_router.post("/{token}/accept")
async def accept_invitation(
    token: str,
    user: CurrentUser,
    session: DbSession,
    settings: AppSettings,
    notification_emails: NotificationEmailQueueDep,
) -> OrganizationSummary:
    return await InvitationService(session, settings, notification_emails).accept_invitation(user, token)
