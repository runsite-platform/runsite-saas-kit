from fastapi import APIRouter, UploadFile

from app.schemas.media import AvatarResponse, LogoResponse
from app.services.media_service import MediaService
from app.utils.dependencies import CurrentUser, DbSession, OptionalObjectStorage, OrgManagerMembership

router = APIRouter()


@router.put("/me/avatar")
async def upload_avatar(
    file: UploadFile, user: CurrentUser, db: DbSession, storage: OptionalObjectStorage
) -> AvatarResponse:
    """Upload an avatar for the current user."""
    avatar_url = await MediaService(db, storage).set_user_avatar(user, file)
    return AvatarResponse(avatar_url=avatar_url)


@router.delete("/me/avatar", status_code=204)
async def remove_avatar(user: CurrentUser, db: DbSession, storage: OptionalObjectStorage) -> None:
    """Remove the current user avatar."""
    await MediaService(db, storage).remove_user_avatar(user)


@router.put("/orgs/{org_id}/logo")
async def upload_logo(
    file: UploadFile, membership: OrgManagerMembership, db: DbSession, storage: OptionalObjectStorage
) -> LogoResponse:
    """Upload the organization logo."""
    logo_url = await MediaService(db, storage).set_organization_logo(membership.organization, file)
    return LogoResponse(logo_url=logo_url)


@router.delete("/orgs/{org_id}/logo", status_code=204)
async def remove_logo(membership: OrgManagerMembership, db: DbSession, storage: OptionalObjectStorage) -> None:
    """Remove the organization logo."""
    await MediaService(db, storage).remove_organization_logo(membership.organization)
