from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page

from app.schemas.admin import AdminOrganizationDetail, AdminOrganizationSummary, PlanOverrideRequest
from app.services.admin_service import AdminService
from app.services.billing.billing_service import BillingService
from app.services.billing.providers.base import PaymentProvider
from app.utils.dependencies import AppSettings, DbSession, PlatformStaffUser, get_payment_provider
from app.utils.pagination import SearchQuery

router = APIRouter(prefix="/admin/organizations", tags=["admin"])

PlanFilterQuery = Annotated[str | None, Query(max_length=32)]


@router.get("")
async def list_organizations(
    _: PlatformStaffUser,
    session: DbSession,
    settings: AppSettings,
    search: SearchQuery = None,
    plan_id: PlanFilterQuery = None,
) -> Page[AdminOrganizationSummary]:
    return await AdminService(session, settings).list_organizations(search=search, plan_id=plan_id)


@router.get("/{organization_id}")
async def get_organization(
    organization_id: UUID, _: PlatformStaffUser, session: DbSession, settings: AppSettings
) -> AdminOrganizationDetail:
    return await AdminService(session, settings).get_organization_detail(organization_id)


@router.post("/{organization_id}/plan-override")
async def override_plan(
    organization_id: UUID,
    request: PlanOverrideRequest,
    actor: PlatformStaffUser,
    session: DbSession,
    settings: AppSettings,
    provider: Annotated[PaymentProvider | None, Depends(get_payment_provider)],
) -> AdminOrganizationDetail:
    billing_service = BillingService(session, settings, provider)
    return await AdminService(session, settings).override_plan(actor, organization_id, request, billing_service)
