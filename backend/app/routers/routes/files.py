from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile
from fastapi_pagination import Page

from app.models.membership import Membership
from app.schemas.files import DownloadUrlResponse, StoredFileResponse
from app.services.file_service import FileService
from app.utils.dependencies import CurrentMembership, DbSession, OptionalObjectStorage, require_feature

router = APIRouter(prefix="/orgs/{org_id}/files", tags=["files"])

FileUploadMembership = Annotated[Membership, Depends(require_feature("file_uploads"))]


@router.get("")
async def list_files(
    membership: CurrentMembership,
    session: DbSession,
    storage: OptionalObjectStorage,
) -> Page[StoredFileResponse]:
    return await FileService(session, storage).list_files(membership.organization_id)


@router.post("", status_code=201)
async def upload_file(
    file: UploadFile, membership: FileUploadMembership, session: DbSession, storage: OptionalObjectStorage
) -> StoredFileResponse:
    stored_file = await FileService(session, storage).upload_file(membership, file)
    return StoredFileResponse.model_validate(stored_file)


@router.get("/{file_id}/download")
async def get_download_url(
    file_id: UUID, membership: CurrentMembership, session: DbSession, storage: OptionalObjectStorage
) -> DownloadUrlResponse:
    url = await FileService(session, storage).get_download_url(membership.organization_id, file_id)
    return DownloadUrlResponse(url=url)


@router.delete("/{file_id}", status_code=204)
async def delete_file(
    file_id: UUID, membership: CurrentMembership, session: DbSession, storage: OptionalObjectStorage
) -> None:
    await FileService(session, storage).delete_file(membership, file_id)
