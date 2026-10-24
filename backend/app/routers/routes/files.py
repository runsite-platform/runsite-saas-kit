from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile
from fastapi_pagination import Page

from app.models.membership import Membership
from app.schemas.files import DownloadUrlResponse, StoredFileResponse
from app.services.file_service import FileService
from app.utils.dependencies import CurrentMembership, DbSession, OptionalObjectStorage, require_feature

router = APIRouter()

FileUploadMembership = Annotated[Membership, Depends(require_feature("file_uploads"))]


@router.get("")
async def list_files(
    membership: CurrentMembership,
    db: DbSession,
    storage: OptionalObjectStorage,
) -> Page[StoredFileResponse]:
    """List organization files."""
    return await FileService(db, storage).list_files(membership.organization_id)


@router.post("", status_code=201)
async def upload_file(
    file: UploadFile, membership: FileUploadMembership, db: DbSession, storage: OptionalObjectStorage
) -> StoredFileResponse:
    """Upload a file to the organization storage."""
    stored_file = await FileService(db, storage).upload_file(membership, file)
    return StoredFileResponse.model_validate(stored_file)


@router.get("/{file_id}/download")
async def get_download_url(
    file_id: UUID, membership: CurrentMembership, db: DbSession, storage: OptionalObjectStorage
) -> DownloadUrlResponse:
    """Return a temporary download URL for a file."""
    url = await FileService(db, storage).get_download_url(membership.organization_id, file_id)
    return DownloadUrlResponse(url=url)


@router.delete("/{file_id}", status_code=204)
async def delete_file(
    file_id: UUID, membership: CurrentMembership, db: DbSession, storage: OptionalObjectStorage
) -> None:
    """Delete a file."""
    await FileService(db, storage).delete_file(membership, file_id)
