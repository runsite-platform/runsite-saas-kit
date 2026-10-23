from datetime import datetime
from uuid import UUID

from fastapi_pagination import Page
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NotificationKind


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID | None
    kind: str
    title: str
    body: str
    link: str | None
    read_at: datetime | None
    created_at: datetime


class NotificationListResponse(Page[NotificationResponse]):
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class NotificationReadUpdate(BaseModel):
    is_read: bool


class NotificationEmailSettingItem(BaseModel):
    kind: NotificationKind
    email_enabled: bool


class NotificationSettingsResponse(BaseModel):
    email_delivery_available: bool
    settings: list[NotificationEmailSettingItem]


class NotificationSettingsUpdate(BaseModel):
    settings: list[NotificationEmailSettingItem] = Field(max_length=len(NotificationKind))
