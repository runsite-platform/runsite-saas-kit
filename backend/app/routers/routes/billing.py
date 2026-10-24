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

router = APIRouter()

ActivePaymentProvider = Annotated[PaymentProvider | None, Depends(get_payment_provider)]


@router.get("/plans")
async def list_plans(db: DbSession, settings: AppSettings, provider: ActivePaymentProvider) -> list[PlanResponse]:
    """List available billing plans."""
    return BillingService(db, settings, provider).list_plans()


@router.get("/orgs/{org_id}/billing")
async def get_billing_overview(
    membership: CurrentMembership, db: DbSession, settings: AppSettings, provider: ActivePaymentProvider
) -> BillingOverviewResponse:
    """Return the organization billing overview."""
    return await BillingService(db, settings, provider).get_overview(membership.organization)


@router.get("/orgs/{org_id}/billing/payments")
async def list_payments(
    membership: OrgManagerMembership, db: DbSession, settings: AppSettings, provider: ActivePaymentProvider
) -> list[PaymentResponse]:
    """List organization payments."""
    return await BillingService(db, settings, provider).list_payments(membership.organization)


@router.post("/orgs/{org_id}/billing/checkout")
async def create_checkout(
    body: CheckoutRequest,
    user: VerifiedUser,
    membership: OrgManagerMembership,
    db: DbSession,
    settings: AppSettings,
    provider: ActivePaymentProvider,
) -> RedirectUrlResponse:
    """Create a checkout session for a plan."""
    service = BillingService(db, settings, provider)
    url = await service.create_checkout(membership.organization, user, body.plan_id, body.interval)
    return RedirectUrlResponse(url=url)


@router.post("/orgs/{org_id}/billing/portal")
async def create_portal_session(
    membership: OrgManagerMembership, db: DbSession, settings: AppSettings, provider: ActivePaymentProvider
) -> RedirectUrlResponse:
    """Create a billing portal session URL."""
    url = await BillingService(db, settings, provider).create_portal_url(membership.organization)
    return RedirectUrlResponse(url=url)


@router.post("/orgs/{org_id}/billing/cancel")
async def cancel_subscription(
    membership: OrgManagerMembership, db: DbSession, settings: AppSettings, provider: ActivePaymentProvider
) -> BillingOverviewResponse:
    """Cancel the organization subscription."""
    return await BillingService(db, settings, provider).cancel_subscription(membership.organization)
