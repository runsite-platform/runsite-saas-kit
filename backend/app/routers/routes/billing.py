from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.billing import (
    BillingOverviewResponse,
    CheckoutRequest,
    PaymentResponse,
    PlanResponse,
    RedirectUrlResponse,
)
from app.services.billing.billing_service import BillingService
from app.services.billing.providers.base import PaymentProvider
from app.utils.dependencies import (
    AppSettings,
    CurrentMembership,
    DbSession,
    OrgManagerMembership,
    VerifiedUser,
    get_payment_provider,
)

router = APIRouter(tags=["billing"])

ActivePaymentProvider = Annotated[PaymentProvider | None, Depends(get_payment_provider)]


@router.get("/plans")
async def list_plans(session: DbSession, settings: AppSettings, provider: ActivePaymentProvider) -> list[PlanResponse]:
    return BillingService(session, settings, provider).list_plans()


@router.get("/orgs/{org_id}/billing")
async def get_billing_overview(
    membership: CurrentMembership, session: DbSession, settings: AppSettings, provider: ActivePaymentProvider
) -> BillingOverviewResponse:
    return await BillingService(session, settings, provider).get_overview(membership.organization)


@router.get("/orgs/{org_id}/billing/payments")
async def list_payments(
    membership: OrgManagerMembership, session: DbSession, settings: AppSettings, provider: ActivePaymentProvider
) -> list[PaymentResponse]:
    return await BillingService(session, settings, provider).list_payments(membership.organization)


@router.post("/orgs/{org_id}/billing/checkout")
async def create_checkout(
    body: CheckoutRequest,
    user: VerifiedUser,
    membership: OrgManagerMembership,
    session: DbSession,
    settings: AppSettings,
    provider: ActivePaymentProvider,
) -> RedirectUrlResponse:
    service = BillingService(session, settings, provider)
    url = await service.create_checkout(membership.organization, user, body.plan_id, body.interval)
    return RedirectUrlResponse(url=url)


@router.post("/orgs/{org_id}/billing/portal")
async def create_portal_session(
    membership: OrgManagerMembership, session: DbSession, settings: AppSettings, provider: ActivePaymentProvider
) -> RedirectUrlResponse:
    url = await BillingService(session, settings, provider).create_portal_url(membership.organization)
    return RedirectUrlResponse(url=url)


@router.post("/orgs/{org_id}/billing/cancel")
async def cancel_subscription(
    membership: OrgManagerMembership, session: DbSession, settings: AppSettings, provider: ActivePaymentProvider
) -> BillingOverviewResponse:
    return await BillingService(session, settings, provider).cancel_subscription(membership.organization)
