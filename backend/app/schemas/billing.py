from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.constants.enums import BillingInterval


class PlanLimitsResponse(BaseModel):
    members: int
    projects: int
    storage_mb: int


class PlanAvailabilityResponse(BaseModel):
    monthly: bool
    yearly: bool


class PlanResponse(BaseModel):
    id: str
    name: str
    price_monthly_cents: int
    price_yearly_cents: int
    trial_days: int
    limits: PlanLimitsResponse
    features: list[str]
    available: PlanAvailabilityResponse


class SubscriptionSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    plan_id: str
    interval: str
    status: str
    current_period_end: datetime | None
    cancel_at_period_end: bool
    trial_ends_at: datetime | None


class PlanOverrideResponse(BaseModel):
    plan_id: str
    reason: str | None


class UsageResponse(BaseModel):
    members: int
    projects: int
    storage_bytes: int


class BillingOverviewResponse(BaseModel):
    plan: PlanResponse
    plan_override: PlanOverrideResponse | None
    subscription: SubscriptionSummaryResponse | None
    usage: UsageResponse
    billing_enabled: bool
    provider: str | None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    amount_cents: int
    currency: str
    status: str
    paid_at: datetime | None
    invoice_url: str | None
    created_at: datetime


class CheckoutRequest(BaseModel):
    plan_id: str = Field(min_length=1, max_length=32)
    interval: BillingInterval


class RedirectUrlResponse(BaseModel):
    url: str


class WebhookAcknowledgement(BaseModel):
    status: str
