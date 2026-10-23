from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from fastapi_pagination import Page
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from app.models.notification import Notification, NotificationEmailSetting
from app.utils.repository import SQLAlchemyRepository


class NotificationReadFilter(StrEnum):
    ALL = "all"
    UNREAD = "unread"
    READ = "read"


def build_notification_filter(user_id: UUID, read_filter: NotificationReadFilter) -> dict[str, Any]:
    filter_params: dict[str, Any] = {"user_id": user_id}
    if read_filter == NotificationReadFilter.UNREAD:
        filter_params["read_at"] = ("null",)
    elif read_filter == NotificationReadFilter.READ:
        filter_params["read_at"] = ("!null",)
    return filter_params


class NotificationRepository(SQLAlchemyRepository[Notification]):
    model = Notification

    async def get_for_user(self, user_id: UUID, notification_id: UUID) -> Notification | None:
        return await self.get_one(filter_params={"user_id": user_id, "id": notification_id})

    async def list_for_user(self, user_id: UUID, *, read_filter: NotificationReadFilter) -> Page:
        unread_count = await self.count_for_user(user_id, read_filter=NotificationReadFilter.UNREAD)
        return await self.get_all(
            filter_params=build_notification_filter(user_id, read_filter),
            order_params={"created_at": "desc", "id": "desc"},
            pagination=True,
            additional_data={"unread_count": unread_count},
        )

    async def count_for_user(self, user_id: UUID, *, read_filter: NotificationReadFilter) -> int:
        return await self.count_all(filter_params=build_notification_filter(user_id, read_filter))

    async def mark_all_read(self, user_id: UUID, read_at: datetime) -> int:
        updated_notifications = await self.update_all(
            values={"read_at": read_at},
            filter_params={"user_id": user_id, "read_at": ("null",)},
        )
        return len(updated_notifications)

    async def delete_read(self, user_id: UUID) -> int:
        deleted_notifications = await self.delete_all(filter_params={"user_id": user_id, "read_at": ("!null",)})
        return len(deleted_notifications)


class NotificationEmailSettingRepository(SQLAlchemyRepository[NotificationEmailSetting]):
    model = NotificationEmailSetting

    async def map_for_users(self, user_ids: list[UUID]) -> dict[tuple[UUID, str], bool]:
        if not user_ids:
            return {}
        stored_settings = await self.get_all(filter_params={"user_id": ("in", user_ids)})
        return {(setting.user_id, setting.kind): setting.email_enabled for setting in stored_settings}

    async def upsert(self, user_id: UUID, kind: str, email_enabled: bool) -> None:
        statement = insert(self.model).values(user_id=user_id, kind=kind, email_enabled=email_enabled)
        statement = statement.on_conflict_do_update(
            index_elements=[self.model.user_id, self.model.kind],
            set_={"email_enabled": email_enabled, "updated_at": func.now()},
        )
        await self.db.execute(statement)
