from uuid import UUID

from fastapi import APIRouter, status

from app.schemas.members import MemberResponse, MemberRoleUpdateRequest
from app.services.membership_service import MembershipService
from app.utils.dependencies import CurrentMembership, DbSession, EmailQueueDep, OrgManagerMembership

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
    email_queue: EmailQueueDep,
) -> MemberResponse:
    """Change the role of a member."""
    return await MembershipService(db, email_queue).change_role(membership.organization_id, membership_id, data.role)


@router.delete("/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    membership_id: UUID,
    membership: CurrentMembership,
    db: DbSession,
    email_queue: EmailQueueDep,
) -> None:
    """Remove a member from the organization."""
    await MembershipService(db, email_queue).remove_member(membership, membership_id)
