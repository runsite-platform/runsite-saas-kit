from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.repositories.notification_repository import NotificationReadFilter
from app.schemas.notifications import (
    NotificationListResponse,
    NotificationReadUpdate,
    NotificationResponse,
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    UnreadCountResponse,
)
from app.services.notification_service import NotificationService
from app.utils.dependencies import AppSettings, CurrentUser, DbSession

router = APIRouter()


@router.get("")
async def list_notifications(
    user: CurrentUser,
    db: DbSession,
    read_filter: Annotated[NotificationReadFilter, Query(alias="filter")] = NotificationReadFilter.ALL,
) -> NotificationListResponse:
    """List notifications of the current user."""
    return await NotificationService(db).list_notifications(user.id, read_filter=read_filter)


@router.get("/unread-count")
async def get_unread_count(user: CurrentUser, db: DbSession) -> UnreadCountResponse:
    """Return the number of unread notifications."""
    return UnreadCountResponse(unread_count=await NotificationService(db).unread_count(user.id))


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(user: CurrentUser, db: DbSession) -> None:
    """Mark all notifications as read."""
    await NotificationService(db).mark_all_read(user.id)


@router.delete("/read", status_code=status.HTTP_204_NO_CONTENT)
async def delete_read_notifications(user: CurrentUser, db: DbSession) -> None:
    """Delete all read notifications."""
    await NotificationService(db).delete_read(user.id)


@router.get("/settings")
async def get_notification_settings(
    user: CurrentUser, db: DbSession, settings: AppSettings
) -> NotificationSettingsResponse:
    """Return email notification settings."""
    return NotificationSettingsResponse(
        email_delivery_available=settings.email_enabled,
        settings=await NotificationService(db).get_email_settings(user.id),
    )


@router.put("/settings")
async def update_notification_settings(
    data: NotificationSettingsUpdate, user: CurrentUser, db: DbSession, settings: AppSettings
) -> NotificationSettingsResponse:
    """Update email notification settings."""
    return NotificationSettingsResponse(
        email_delivery_available=settings.email_enabled,
        settings=await NotificationService(db).update_email_settings(user.id, data.settings),
    )


@router.patch("/{notification_id}")
async def update_notification(
    notification_id: UUID, data: NotificationReadUpdate, user: CurrentUser, db: DbSession
) -> NotificationResponse:
    """Mark a notification as read or unread."""
    return await NotificationService(db).set_read(user.id, notification_id, is_read=data.is_read)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(notification_id: UUID, user: CurrentUser, db: DbSession) -> None:
    """Delete a notification."""
    await NotificationService(db).delete_notification(user.id, notification_id)
