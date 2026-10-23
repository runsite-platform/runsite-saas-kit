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

router = APIRouter(prefix="/admin/users", tags=["admin"])


@router.get("")
async def list_users(
    _: PlatformStaffUser,
    session: DbSession,
    settings: AppSettings,
    search: SearchQuery = None,
) -> Page[AdminUserSummary]:
    return await AdminService(session, settings).list_users(search=search)


@router.get("/{user_id}")
async def get_user(user_id: UUID, _: PlatformStaffUser, session: DbSession, settings: AppSettings) -> AdminUserDetail:
    return await AdminService(session, settings).get_user_detail(user_id)


@router.post("/{user_id}/block")
async def block_user(
    user_id: UUID, actor: PlatformStaffUser, session: DbSession, settings: AppSettings
) -> AdminUserSummary:
    return await AdminService(session, settings).block_user(actor, user_id)


@router.post("/{user_id}/unblock")
async def unblock_user(
    user_id: UUID, actor: PlatformStaffUser, session: DbSession, settings: AppSettings
) -> AdminUserSummary:
    return await AdminService(session, settings).unblock_user(actor, user_id)


@router.post("/{user_id}/resend-verification")
async def resend_verification(
    user_id: UUID,
    _: PlatformStaffUser,
    session: DbSession,
    settings: AppSettings,
    background_tasks: BackgroundTasks,
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> ResendVerificationResponse:
    user, raw_token = await AdminService(session, settings).create_verification_token(user_id)
    if raw_token is None:
        return ResendVerificationResponse(sent=False)
    background_tasks.add_task(email_service.send_verification_email, user, raw_token)
    return ResendVerificationResponse(sent=True)


@router.post("/{user_id}/grant-admin")
async def grant_admin(user_id: UUID, _: SuperadminUser, session: DbSession, settings: AppSettings) -> AdminUserSummary:
    return await AdminService(session, settings).set_admin_role(user_id, grant=True)


@router.post("/{user_id}/revoke-admin")
async def revoke_admin(user_id: UUID, _: SuperadminUser, session: DbSession, settings: AppSettings) -> AdminUserSummary:
    return await AdminService(session, settings).set_admin_role(user_id, grant=False)


@router.post("/{user_id}/impersonate")
async def impersonate_user(
    user_id: UUID, actor: SuperadminUser, session: DbSession, settings: AppSettings
) -> ImpersonationResponse:
    return await AdminService(session, settings).impersonate(actor, user_id)
