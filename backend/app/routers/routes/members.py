from uuid import UUID

from fastapi import APIRouter, status

from app.schemas.members import MemberResponse, MemberRoleUpdateRequest
from app.services.membership_service import MembershipService
from app.utils.dependencies import CurrentMembership, DbSession, NotificationEmailQueueDep, OrgManagerMembership

router = APIRouter(prefix="/orgs/{org_id}/members", tags=["members"])


@router.get("")
async def list_members(membership: CurrentMembership, session: DbSession) -> list[MemberResponse]:
    return await MembershipService(session).list_members(membership.organization_id)


@router.patch("/{membership_id}")
async def change_member_role(
    membership_id: UUID,
    data: MemberRoleUpdateRequest,
    membership: OrgManagerMembership,
    session: DbSession,
    notification_emails: NotificationEmailQueueDep,
) -> MemberResponse:
    return await MembershipService(session, notification_emails).change_role(
        membership.organization_id, membership_id, data.role
    )


@router.delete("/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    membership_id: UUID,
    membership: CurrentMembership,
    session: DbSession,
    notification_emails: NotificationEmailQueueDep,
) -> None:
    await MembershipService(session, notification_emails).remove_member(membership, membership_id)
