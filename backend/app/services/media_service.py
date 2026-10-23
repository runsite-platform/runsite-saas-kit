from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.user import User
from app.services.file_storage import ObjectStorage, delete_object_best_effort, require_storage
from app.utils.exceptions import BusinessError
from app.utils.uploads import read_upload_limited

ALLOWED_IMAGE_CONTENT_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})
MAX_IMAGE_BYTES = 2 * 1024 * 1024


def avatar_storage_key(user_id: UUID) -> str:
    return f"users/{user_id}/avatar"


def logo_storage_key(organization_id: UUID) -> str:
    return f"orgs/{organization_id}/logo"


class MediaService:
    def __init__(self, session: AsyncSession, storage: ObjectStorage | None) -> None:
        self.session = session
        self.storage = storage

    async def set_user_avatar(self, user: User, upload: UploadFile) -> str:
        storage = require_storage(self.storage)
        storage_key = avatar_storage_key(user.id)
        await self._store_image(storage, storage_key, upload)
        user.avatar_key = storage_key
        await self.session.commit()
        return storage.presigned_get_url(storage_key)

    async def remove_user_avatar(self, user: User) -> None:
        storage_key = user.avatar_key
        user.avatar_key = None
        await self.session.commit()
        await self._delete_object(storage_key)

    async def set_organization_logo(self, organization: Organization, upload: UploadFile) -> str:
        storage = require_storage(self.storage)
        storage_key = logo_storage_key(organization.id)
        await self._store_image(storage, storage_key, upload)
        organization.logo_key = storage_key
        await self.session.commit()
        return storage.presigned_get_url(storage_key)

    async def remove_organization_logo(self, organization: Organization) -> None:
        storage_key = organization.logo_key
        organization.logo_key = None
        await self.session.commit()
        await self._delete_object(storage_key)

    async def _store_image(self, storage: ObjectStorage, storage_key: str, upload: UploadFile) -> None:
        content_type = (upload.content_type or "").lower()
        if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise BusinessError(
                "unsupported_file_type",
                "Use a PNG, JPEG or WebP image",
                415,
                details={"allowed": sorted(ALLOWED_IMAGE_CONTENT_TYPES)},
            )
        data = await read_upload_limited(upload, MAX_IMAGE_BYTES)
        await storage.put(storage_key, data, content_type)

    async def _delete_object(self, storage_key: str | None) -> None:
        if storage_key and self.storage is not None:
            await delete_object_best_effort(self.storage, storage_key)
