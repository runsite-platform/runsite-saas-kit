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

router = APIRouter(prefix="/me/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    user: CurrentUser,
    session: DbSession,
    read_filter: Annotated[NotificationReadFilter, Query(alias="filter")] = NotificationReadFilter.ALL,
) -> NotificationListResponse:
    return await NotificationService(session).list_notifications(user.id, read_filter=read_filter)


@router.get("/unread-count")
async def get_unread_count(user: CurrentUser, session: DbSession) -> UnreadCountResponse:
    return UnreadCountResponse(unread_count=await NotificationService(session).unread_count(user.id))


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(user: CurrentUser, session: DbSession) -> None:
    await NotificationService(session).mark_all_read(user.id)


@router.delete("/read", status_code=status.HTTP_204_NO_CONTENT)
async def delete_read_notifications(user: CurrentUser, session: DbSession) -> None:
    await NotificationService(session).delete_read(user.id)


@router.get("/settings")
async def get_notification_settings(
    user: CurrentUser, session: DbSession, settings: AppSettings
) -> NotificationSettingsResponse:
    return NotificationSettingsResponse(
        email_delivery_available=settings.email_enabled,
        settings=await NotificationService(session).get_email_settings(user.id),
    )


@router.put("/settings")
async def update_notification_settings(
    data: NotificationSettingsUpdate, user: CurrentUser, session: DbSession, settings: AppSettings
) -> NotificationSettingsResponse:
    return NotificationSettingsResponse(
        email_delivery_available=settings.email_enabled,
        settings=await NotificationService(session).update_email_settings(user.id, data.settings),
    )


@router.patch("/{notification_id}")
async def update_notification(
    notification_id: UUID, data: NotificationReadUpdate, user: CurrentUser, session: DbSession
) -> NotificationResponse:
    return await NotificationService(session).set_read(user.id, notification_id, is_read=data.is_read)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(notification_id: UUID, user: CurrentUser, session: DbSession) -> None:
    await NotificationService(session).delete_notification(user.id, notification_id)
