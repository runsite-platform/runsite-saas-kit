from uuid import UUID

from fastapi import APIRouter, status

from app.schemas.members import MemberResponse, MemberRoleUpdateRequest
from app.services.membership_service import MembershipService
from app.utils.dependencies import CurrentMembership, DbSession, NotificationEmailQueueDep, OrgManagerMembership

router = APIRouter()


@router.get("")
async def list_members(membership: CurrentMembership, db: DbSession) -> list[MemberResponse]:
    """List organization members."""
    return await MembershipService(db).list_members(membership.organization_id)


@router.patch("/{membership_id}")
async def change_member_role(
    membership_id: UUID,
    data: MemberRoleUpdateRequest,
    membership: OrgManagerMembership,
    db: DbSession,
    notification_emails: NotificationEmailQueueDep,
) -> MemberResponse:
    """Change the role of a member."""
    return await MembershipService(db, notification_emails).change_role(
        membership.organization_id, membership_id, data.role
    )


@router.delete("/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    membership_id: UUID,
    membership: CurrentMembership,
    db: DbSession,
    notification_emails: NotificationEmailQueueDep,
) -> None:
    """Remove a member from the organization."""
    await MembershipService(db, notification_emails).remove_member(membership, membership_id)
