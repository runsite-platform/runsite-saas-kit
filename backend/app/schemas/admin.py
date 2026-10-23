from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.overview import DailyCount


class AdminUserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None
    platform_role: str
    is_email_verified: bool
    is_blocked: bool
    created_at: datetime
    last_login_at: datetime | None


class AdminUserMembership(BaseModel):
    organization_id: UUID
    organization_name: str
    organization_slug: str
    role: str
    plan_id: str


class AdminUserDetail(AdminUserSummary):
    has_password: bool
    google_linked: bool
    memberships: list[AdminUserMembership]


class ResendVerificationResponse(BaseModel):
    sent: bool


class ImpersonationResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AdminOrganizationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    plan_id: str
    plan_override_id: str | None
    owner_email: str | None
    members_count: int
    created_at: datetime


class AdminOrganizationMember(BaseModel):
    membership_id: UUID
    user_id: UUID
    email: str
    full_name: str | None
    role: str


class AdminSubscriptionInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    plan_id: str
    interval: str
    status: str
    current_period_end: datetime | None
    cancel_at_period_end: bool
    trial_ends_at: datetime | None
    created_at: datetime


class AdminPaymentInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    amount_cents: int
    currency: str
    status: str
    paid_at: datetime | None
    invoice_url: str | None


class AdminOrganizationDetail(AdminOrganizationSummary):
    plan_override_reason: str | None
    billing_provider: str | None
    members: list[AdminOrganizationMember]
    subscription: AdminSubscriptionInfo | None
    payments: list[AdminPaymentInfo]


class PlanOverrideRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    plan_id: str | None = Field(default=None, max_length=32)
    reason: str = Field(min_length=3, max_length=500)


class TrialConversion(BaseModel):
    window_days: int
    ended_trials: int = Field(description="Subscriptions whose trial ended in the window and that left trialing")
    converted: int = Field(
        description="Ended trials that are active now; a trial that converted and later churned is not counted"
    )
    rate: float | None


class PlatformMetricsResponse(BaseModel):
    currency: str = "usd"
    mrr_cents: int
    active_subscriptions: int
    trialing_subscriptions: int
    past_due_subscriptions: int
    churned_last_30_days: int
    trial_conversion: TrialConversion
    total_users: int
    total_organizations: int
    days: int
    signups_per_day: list[DailyCount]
    new_organizations_per_day: list[DailyCount]


class ChecklistStatus(StrEnum):
    OK = "ok"
    MISSING = "missing"
    WARNING = "warning"
    MANUAL = "manual"


class SetupChecklistItem(BaseModel):
    id: str
    status: ChecklistStatus
    docs_url: str


class SetupChecklistResponse(BaseModel):
    items: list[SetupChecklistItem]
