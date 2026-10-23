from fastapi import APIRouter, UploadFile

from app.schemas.media import AvatarResponse, LogoResponse
from app.services.media_service import MediaService
from app.utils.dependencies import CurrentUser, DbSession, OptionalObjectStorage, OrgManagerMembership

router = APIRouter(tags=["media"])


@router.put("/me/avatar")
async def upload_avatar(
    file: UploadFile, user: CurrentUser, session: DbSession, storage: OptionalObjectStorage
) -> AvatarResponse:
    avatar_url = await MediaService(session, storage).set_user_avatar(user, file)
    return AvatarResponse(avatar_url=avatar_url)


@router.delete("/me/avatar", status_code=204)
async def remove_avatar(user: CurrentUser, session: DbSession, storage: OptionalObjectStorage) -> None:
    await MediaService(session, storage).remove_user_avatar(user)


@router.put("/orgs/{org_id}/logo")
async def upload_logo(
    file: UploadFile, membership: OrgManagerMembership, session: DbSession, storage: OptionalObjectStorage
) -> LogoResponse:
    logo_url = await MediaService(session, storage).set_organization_logo(membership.organization, file)
    return LogoResponse(logo_url=logo_url)


@router.delete("/orgs/{org_id}/logo", status_code=204)
async def remove_logo(membership: OrgManagerMembership, session: DbSession, storage: OptionalObjectStorage) -> None:
    await MediaService(session, storage).remove_organization_logo(membership.organization)
