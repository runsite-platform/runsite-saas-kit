from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi_pagination import Page

from app.schemas.admin import (
    AdminUserDetail,
    AdminUserSummary,
    ImpersonationResponse,
    ResendVerificationResponse,
)
from app.services.admin_service import AdminService
from app.services.email_service import EmailService
from app.utils.dependencies import AppSettings, DbSession, PlatformStaffUser, SuperadminUser, get_email_service
from app.utils.pagination import SearchQuery

router = APIRouter()


@router.get("")
async def list_users(
    _: PlatformStaffUser,
    db: DbSession,
    settings: AppSettings,
    search: SearchQuery = None,
) -> Page[AdminUserSummary]:
    """List users for platform staff."""
    return await AdminService(db, settings).list_users(search=search)


@router.get("/{user_id}")
async def get_user(user_id: UUID, _: PlatformStaffUser, db: DbSession, settings: AppSettings) -> AdminUserDetail:
    """Return user details for platform staff."""
    return await AdminService(db, settings).get_user_detail(user_id)


@router.post("/{user_id}/block")
async def block_user(user_id: UUID, actor: PlatformStaffUser, db: DbSession, settings: AppSettings) -> AdminUserSummary:
    """Block a user."""
    return await AdminService(db, settings).block_user(actor, user_id)


@router.post("/{user_id}/unblock")
async def unblock_user(
    user_id: UUID, actor: PlatformStaffUser, db: DbSession, settings: AppSettings
) -> AdminUserSummary:
    """Unblock a user."""
    return await AdminService(db, settings).unblock_user(actor, user_id)


@router.post("/{user_id}/resend-verification")
async def resend_verification(
    user_id: UUID,
    _: PlatformStaffUser,
    db: DbSession,
    settings: AppSettings,
    background_tasks: BackgroundTasks,
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> ResendVerificationResponse:
    """Resend the email verification link to a user."""
    user, raw_token = await AdminService(db, settings).create_verification_token(user_id)
    if raw_token is None:
        return ResendVerificationResponse(sent=False)
    background_tasks.add_task(email_service.send_verification_email, user, raw_token)
    return ResendVerificationResponse(sent=True)


@router.post("/{user_id}/grant-admin")
async def grant_admin(user_id: UUID, _: SuperadminUser, db: DbSession, settings: AppSettings) -> AdminUserSummary:
    """Grant the platform admin role to a user."""
    return await AdminService(db, settings).set_admin_role(user_id, grant=True)


@router.post("/{user_id}/revoke-admin")
async def revoke_admin(user_id: UUID, _: SuperadminUser, db: DbSession, settings: AppSettings) -> AdminUserSummary:
    """Revoke the platform admin role from a user."""
    return await AdminService(db, settings).set_admin_role(user_id, grant=False)


@router.post("/{user_id}/impersonate")
async def impersonate_user(
    user_id: UUID, actor: SuperadminUser, db: DbSession, settings: AppSettings
) -> ImpersonationResponse:
    """Start a session as another user."""
    return await AdminService(db, settings).impersonate(actor, user_id)
