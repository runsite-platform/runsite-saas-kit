from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from fastapi_pagination import Page
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationKind
from app.models.notification import Notification
from app.models.user import User
from app.repositories.notification_repository import (
    NotificationEmailSettingRepository,
    NotificationReadFilter,
    NotificationRepository,
)
from app.schemas.notifications import NotificationEmailSettingItem, NotificationResponse
from app.utils.exceptions import not_found
from app.utils.security import utc_now

# Whether a kind is emailed when the user has not changed the setting. Add new kinds here and in NotificationKind.
EMAIL_ENABLED_BY_DEFAULT: dict[NotificationKind, bool] = {
    NotificationKind.WELCOME: False,
    NotificationKind.MEMBER_JOINED: True,
    NotificationKind.MEMBER_ROLE_CHANGED: True,
    NotificationKind.MEMBER_REMOVED: True,
    NotificationKind.OWNERSHIP_TRANSFERRED: True,
    NotificationKind.SYSTEM: True,
}


@dataclass(frozen=True)
class NotificationEmail:
    """Email to send for a notification."""

    to: str
    title: str
    body: str
    link: str | None


class NotificationEmailQueue(Protocol):
    """Queue that sends notification emails."""

    def enqueue(self, email: NotificationEmail) -> None:
        """Queue a notification email for sending."""
        ...


class NotificationService:
    """Creates in-app notifications and queues emails for them. `notify` does not commit; the caller does."""

    def __init__(self, db: AsyncSession, email_queue: NotificationEmailQueue | None = None) -> None:
        self.db = db
        self.email_queue = email_queue
        self.notifications = NotificationRepository(db)
        self.email_settings = NotificationEmailSettingRepository(db)

    async def notify(
        self,
        recipients: Iterable[User],
        *,
        kind: NotificationKind,
        title: str,
        body: str = "",
        link: str | None = None,
        organization_id: UUID | None = None,
    ) -> list[Notification]:
        """Create notifications for recipients and queue enabled emails."""
        unique_recipients = list({user.id: user for user in recipients if not user.is_blocked}.values())
        created_notifications = [
            Notification(
                user_id=user.id,
                organization_id=organization_id,
                kind=kind,
                title=title,
                body=body,
                link=link,
            )
            for user in unique_recipients
        ]
        self.db.add_all(created_notifications)
        await self.db.flush()

        if self.email_queue is not None and unique_recipients:
            email_settings = await self.email_settings.map_for_users([user.id for user in unique_recipients])
            for user in unique_recipients:
                if email_settings.get((user.id, kind), EMAIL_ENABLED_BY_DEFAULT[kind]):
                    self.email_queue.enqueue(NotificationEmail(to=user.email, title=title, body=body, link=link))
        return created_notifications

    async def list_notifications(self, user_id: UUID, *, read_filter: NotificationReadFilter) -> Page:
        """Return a page of the user's notifications."""
        return await self.notifications.list_for_user(user_id, read_filter=read_filter)

    async def unread_count(self, user_id: UUID) -> int:
        """Return the number of the user's unread notifications."""
        return await self.notifications.count_for_user(user_id, read_filter=NotificationReadFilter.UNREAD)

    async def set_read(self, user_id: UUID, notification_id: UUID, *, is_read: bool) -> NotificationResponse:
        """Mark a notification as read or unread."""
        notification = await self.notifications.get_for_user(user_id, notification_id)
        if notification is None:
            raise not_found("Notification")
        if is_read and notification.read_at is None:
            notification.read_at = utc_now()
        elif not is_read:
            notification.read_at = None
        await self.db.commit()
        await self.db.refresh(notification)
        return NotificationResponse.model_validate(notification)

    async def mark_all_read(self, user_id: UUID) -> None:
        """Mark all of the user's notifications as read."""
        await self.notifications.mark_all_read(user_id, utc_now())
        await self.db.commit()

    async def delete_notification(self, user_id: UUID, notification_id: UUID) -> None:
        """Delete one of the user's notifications."""
        notification = await self.notifications.get_for_user(user_id, notification_id)
        if notification is None:
            raise not_found("Notification")
        await self.notifications.delete(notification)
        await self.db.commit()

    async def delete_read(self, user_id: UUID) -> None:
        """Delete all of the user's read notifications."""
        await self.notifications.delete_read(user_id)
        await self.db.commit()

    async def get_email_settings(self, user_id: UUID) -> list[NotificationEmailSettingItem]:
        """Return the user's email setting for every notification kind."""
        stored_settings = await self.email_settings.map_for_users([user_id])
        return [
            NotificationEmailSettingItem(
                kind=kind, email_enabled=stored_settings.get((user_id, kind), default_email_enabled)
            )
            for kind, default_email_enabled in EMAIL_ENABLED_BY_DEFAULT.items()
        ]

    async def update_email_settings(
        self, user_id: UUID, settings: list[NotificationEmailSettingItem]
    ) -> list[NotificationEmailSettingItem]:
        """Save the user's email settings and return all of them."""
        for setting in settings:
            await self.email_settings.upsert(user_id, setting.kind, setting.email_enabled)
        await self.db.commit()
        return await self.get_email_settings(user_id)
