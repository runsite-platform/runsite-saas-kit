from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StoredFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    uploaded_by_id: UUID | None
    name: str
    size_bytes: int
    content_type: str
    created_at: datetime


class DownloadUrlResponse(BaseModel):
    url: str
