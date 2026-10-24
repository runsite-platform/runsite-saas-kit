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
    EmailQueueDep,
    OptionalObjectStorage,
    OrgManagerMembership,
    OrgOwnerMembership,
)

router = APIRouter()


@router.get("")
async def list_organizations(
    user: CurrentUser, db: DbSession, storage: OptionalObjectStorage
) -> list[OrganizationSummary]:
    """List organizations of the current user."""
    return await OrganizationService(db, storage=storage).list_summaries_for_user(user.id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreateRequest, user: CurrentUser, db: DbSession, storage: OptionalObjectStorage
) -> OrganizationSummary:
    """Create an organization owned by the current user."""
    return await OrganizationService(db, storage=storage).create_organization(user, data)


@router.get("/{org_id}")
async def get_organization(
    membership: CurrentMembership, db: DbSession, storage: OptionalObjectStorage
) -> OrganizationDetailResponse:
    """Return organization details."""
    return await OrganizationService(db, storage=storage).get_organization_detail(membership)


@router.patch("/{org_id}")
async def update_organization(
    data: OrganizationUpdateRequest,
    membership: OrgManagerMembership,
    db: DbSession,
    storage: OptionalObjectStorage,
) -> OrganizationDetailResponse:
    """Update the organization."""
    return await OrganizationService(db, storage=storage).update_organization(membership, data)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(membership: OrgOwnerMembership, db: DbSession, storage: OptionalObjectStorage) -> None:
    """Delete the organization."""
    await OrganizationService(db, storage=storage).delete_organization(membership)


@router.post("/{org_id}/transfer-ownership", status_code=status.HTTP_204_NO_CONTENT)
async def transfer_ownership(
    data: TransferOwnershipRequest,
    membership: OrgOwnerMembership,
    db: DbSession,
    email_queue: EmailQueueDep,
) -> None:
    """Transfer organization ownership to another member."""
    await OrganizationService(db).transfer_ownership(membership, data.membership_id, email_queue)
