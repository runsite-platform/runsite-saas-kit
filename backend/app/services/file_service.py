import uuid
from uuid import UUID

from fastapi import UploadFile
from fastapi_pagination import Page
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import OrgRole
from app.models.membership import Membership
from app.models.stored_file import StoredFile
from app.repositories.stored_file_repository import StoredFileRepository
from app.services.file_storage import ObjectStorage, delete_object_best_effort, require_storage
from app.services.plan_limits import PlanLimitsService
from app.utils.exceptions import BusinessError, not_found
from app.utils.uploads import display_file_name, read_upload_limited, safe_file_name

MAX_FILE_BYTES = 25 * 1024 * 1024
DEFAULT_CONTENT_TYPE = "application/octet-stream"


class FileService:
    def __init__(self, session: AsyncSession, storage: ObjectStorage | None) -> None:
        self.session = session
        self.storage = storage
        self.files = StoredFileRepository(session)
        self.plan_limits = PlanLimitsService(session)

    async def list_files(self, organization_id: UUID) -> Page:
        return await self.files.list_for_organization(organization_id)

    async def get_file(self, organization_id: UUID, file_id: UUID) -> StoredFile:
        stored_file = await self.files.get_in_organization(organization_id, file_id)
        if stored_file is None:
            raise not_found("File")
        return stored_file

    async def upload_file(self, membership: Membership, upload: UploadFile) -> StoredFile:
        storage = require_storage(self.storage)
        data = await read_upload_limited(upload, MAX_FILE_BYTES)
        await self.plan_limits.ensure_can_store(membership.organization, len(data))
        storage_key = f"orgs/{membership.organization_id}/files/{uuid.uuid4()}-{safe_file_name(upload.filename)}"
        content_type = upload.content_type or DEFAULT_CONTENT_TYPE
        await storage.put(storage_key, data, content_type)
        stored_file = StoredFile(
            organization_id=membership.organization_id,
            uploaded_by_id=membership.user_id,
            storage_key=storage_key,
            name=display_file_name(upload.filename),
            size_bytes=len(data),
            content_type=content_type,
        )
        await self.files.add(stored_file)
        await self.session.commit()
        await self.session.refresh(stored_file)
        return stored_file

    async def get_download_url(self, organization_id: UUID, file_id: UUID) -> str:
        stored_file = await self.get_file(organization_id, file_id)
        return require_storage(self.storage).presigned_get_url(stored_file.storage_key, download_name=stored_file.name)

    async def delete_file(self, membership: Membership, file_id: UUID) -> None:
        stored_file = await self.get_file(membership.organization_id, file_id)
        if membership.role == OrgRole.MEMBER and stored_file.uploaded_by_id != membership.user_id:
            raise BusinessError("forbidden", "Only owners and admins can delete files uploaded by others", 403)
        storage_key = stored_file.storage_key
        await self.files.delete(stored_file)
        await self.session.commit()
        if self.storage is not None:
            await delete_object_best_effort(self.storage, storage_key)
