from fastapi import APIRouter, status

from app.schemas.organizations import (
    OrganizationCreateRequest,
    OrganizationDetailResponse,
    OrganizationSummary,
    OrganizationUpdateRequest,
    TransferOwnershipRequest,
)
from app.services.organization_service import OrganizationService
from app.utils.dependencies import (
    CurrentMembership,
    CurrentUser,
    DbSession,
    NotificationEmailQueueDep,
    OptionalObjectStorage,
    OrgManagerMembership,
    OrgOwnerMembership,
)

router = APIRouter(prefix="/orgs", tags=["organizations"])


@router.get("")
async def list_organizations(
    user: CurrentUser, session: DbSession, storage: OptionalObjectStorage
) -> list[OrganizationSummary]:
    return await OrganizationService(session, storage=storage).list_summaries_for_user(user.id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreateRequest, user: CurrentUser, session: DbSession, storage: OptionalObjectStorage
) -> OrganizationSummary:
    return await OrganizationService(session, storage=storage).create_organization(user, data)


@router.get("/{org_id}")
async def get_organization(
    membership: CurrentMembership, session: DbSession, storage: OptionalObjectStorage
) -> OrganizationDetailResponse:
    return await OrganizationService(session, storage=storage).get_organization_detail(membership)


@router.patch("/{org_id}")
async def update_organization(
    data: OrganizationUpdateRequest,
    membership: OrgManagerMembership,
    session: DbSession,
    storage: OptionalObjectStorage,
) -> OrganizationDetailResponse:
    return await OrganizationService(session, storage=storage).update_organization(membership, data)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    membership: OrgOwnerMembership, session: DbSession, storage: OptionalObjectStorage
) -> None:
    await OrganizationService(session, storage=storage).delete_organization(membership)


@router.post("/{org_id}/transfer-ownership", status_code=status.HTTP_204_NO_CONTENT)
async def transfer_ownership(
    data: TransferOwnershipRequest,
    membership: OrgOwnerMembership,
    session: DbSession,
    notification_emails: NotificationEmailQueueDep,
) -> None:
    await OrganizationService(session).transfer_ownership(membership, data.membership_id, notification_emails)
