from collections.abc import Iterable
from uuid import UUID

from fastapi_pagination import Page
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import NotificationKind
from app.emails.contents import DEFAULT_NOTIFICATION_PATH, NotificationEmailContent
from app.models.notification import Notification
from app.models.user import User
from app.repositories.notification_repository import (
    NotificationEmailSettingRepository,
    NotificationReadFilter,
    NotificationRepository,
)
from app.schemas.notifications import NotificationEmailSettingItem, NotificationResponse
from app.services.email_service import EmailQueue
from app.services.notification_policy import NOTIFICATION_POLICIES, is_email_enabled, user_configurable_kinds
from app.utils.exceptions import BusinessError, not_found
from app.utils.security import utc_now


class NotificationService:
    """Creates in-app notifications and queues emails for them. `notify` does not commit; the caller does."""

    def __init__(self, db: AsyncSession, email_queue: EmailQueue | None = None) -> None:
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
            stored_settings = await self.email_settings.map_for_users([user.id for user in unique_recipients])
            email_content = NotificationEmailContent(title=title, body=body, path=link or DEFAULT_NOTIFICATION_PATH)
            for user in unique_recipients:
                if is_email_enabled(kind, stored_settings.get((user.id, kind))):
                    self.email_queue.enqueue(user.email, email_content)
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
        """Return the user's email setting for every kind they can turn off."""
        stored_settings = await self.email_settings.map_for_users([user_id])
        return [
            NotificationEmailSettingItem(
                kind=kind, email_enabled=is_email_enabled(kind, stored_settings.get((user_id, kind)))
            )
            for kind in user_configurable_kinds()
        ]

    async def update_email_settings(
        self, user_id: UUID, settings: list[NotificationEmailSettingItem]
    ) -> list[NotificationEmailSettingItem]:
        """Save the user's email settings and return all of them."""
        for setting in settings:
            if not NOTIFICATION_POLICIES[setting.kind].user_configurable:
                raise BusinessError("validation_error", f"{setting.kind} cannot be turned off", status_code=422)
        for setting in settings:
            await self.email_settings.upsert(user_id, setting.kind, setting.email_enabled)
        await self.db.commit()
        return await self.get_email_settings(user_id)
