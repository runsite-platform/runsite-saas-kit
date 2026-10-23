import logging
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.models import Organization, Payment, Subscription, User
from app.models.enums import BillingInterval, PaymentStatus
from app.models.subscription import BLOCKING_STATUSES
from app.repositories.billing_event_repository import BillingEventRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.usage_repository import UsageRepository
from app.schemas.billing import (
    BillingOverviewResponse,
    PaymentResponse,
    PlanAvailabilityResponse,
    PlanLimitsResponse,
    PlanOverrideResponse,
    PlanResponse,
    SubscriptionSummaryResponse,
    UsageResponse,
)
from app.services.billing.plans import FREE_PLAN_ID, PLANS, Plan, get_plan
from app.services.billing.provider_config import ProviderConfig, is_paid_plan
from app.services.billing.providers.base import (
    ENDED_SUBSCRIPTION_STATUSES,
    BillingProviderError,
    NormalizedEvent,
    PaymentProvider,
    PaymentSnapshot,
    SubscriptionSnapshot,
)
from app.utils.exceptions import BusinessError, not_found

logger = logging.getLogger(__name__)

WebhookOutcome = Literal["processed", "duplicate", "failed"]
EVENT_ERROR_MAX_LENGTH = 2000


class BillingEventError(Exception):
    pass


class UnrelatedBillingEventError(BillingEventError):
    """The event is about a subscription this deployment did not create, so it is skipped."""


UNRESOLVED_EVENT_RETRY_WINDOW = timedelta(hours=1)


class BillingService:
    def __init__(self, session: AsyncSession, settings: Settings, provider: PaymentProvider | None) -> None:
        self.session = session
        self.settings = settings
        self.provider = provider
        self.provider_config = ProviderConfig(settings)
        self.subscriptions = SubscriptionRepository(session)
        self.payments = PaymentRepository(session)
        self.organizations = OrganizationRepository(session)
        self.billing_events = BillingEventRepository(session)

    def list_plans(self) -> list[PlanResponse]:
        return [self._plan_response(plan) for plan in PLANS.values()]

    async def get_overview(self, organization: Organization) -> BillingOverviewResponse:
        subscription = await self.subscriptions.get_current_for_organization(organization.id)
        usage = await UsageRepository(self.session).get_usage(organization.id)
        plan_override = None
        if organization.plan_override_id:
            plan_override = PlanOverrideResponse(
                plan_id=organization.plan_override_id, reason=organization.plan_override_reason
            )
        return BillingOverviewResponse(
            plan=self._plan_response(get_plan(organization.plan_id)),
            plan_override=plan_override,
            subscription=SubscriptionSummaryResponse.model_validate(subscription) if subscription else None,
            usage=UsageResponse(
                members=usage.members + usage.pending_invitations,
                projects=usage.projects,
                storage_bytes=usage.storage_bytes,
            ),
            billing_enabled=self.provider is not None,
            provider=self.provider.name if self.provider is not None else None,
        )

    async def list_payments(self, organization: Organization) -> list[PaymentResponse]:
        payments = await self.payments.list_for_organization(organization.id)
        return [PaymentResponse.model_validate(payment) for payment in payments]

    async def create_checkout(
        self, organization: Organization, user: User, plan_id: str, interval: BillingInterval
    ) -> str:
        provider = self._require_provider()
        plan = PLANS.get(plan_id)
        if plan is None or not is_paid_plan(plan) or not self.provider_config.is_plan_available(plan_id, interval):
            raise BusinessError("plan_unavailable", f"Plan '{plan_id}' ({interval}) is not available", status_code=400)
        if await self.subscriptions.has_blocking_subscription(organization.id):
            raise BusinessError(
                "active_subscription",
                "This organization already has a subscription; manage it in the billing portal",
                status_code=409,
            )
        billing_page_url = self._billing_page_url(organization)
        try:
            return await provider.create_checkout(
                organization,
                plan,
                interval,
                user.email,
                f"{billing_page_url}?checkout=success",
                f"{billing_page_url}?checkout=canceled",
            )
        except BillingProviderError as error:
            raise self._provider_failure(error) from error

    async def create_portal_url(self, organization: Organization) -> str:
        provider = self._require_provider()
        if organization.billing_provider != provider.name or not organization.billing_customer_id:
            raise not_found("Billing account")
        try:
            return await provider.create_portal_url(organization, self._billing_page_url(organization))
        except BillingProviderError as error:
            raise self._provider_failure(error) from error

    async def cancel_subscription(self, organization: Organization) -> BillingOverviewResponse:
        provider = self._require_provider()
        subscription = await self.subscriptions.get_current_for_organization(organization.id)
        if (
            subscription is None
            or subscription.provider != provider.name
            or subscription.status not in BLOCKING_STATUSES
        ):
            raise not_found("Subscription")
        try:
            await provider.cancel_subscription(subscription, at_period_end=True)
        except BillingProviderError as error:
            raise self._provider_failure(error) from error
        subscription.cancel_at_period_end = True
        await self.session.commit()
        return await self.get_overview(organization)

    async def recompute_plan(self, organization: Organization) -> str:
        override_plan_id = organization.plan_override_id
        if override_plan_id is not None and override_plan_id in PLANS:
            plan_id = override_plan_id
        else:
            granting = await self.subscriptions.get_plan_granting_for_organization(organization.id)
            plan_id = granting.plan_id if granting is not None and granting.plan_id in PLANS else FREE_PLAN_ID
        organization.plan_id = plan_id
        await self.session.flush()
        return plan_id

    async def set_plan_override(self, organization: Organization, plan_id: str | None, reason: str) -> None:
        if plan_id is not None and plan_id not in PLANS:
            raise BusinessError("plan_unavailable", f"Unknown plan '{plan_id}'", status_code=400)
        organization.plan_override_id = plan_id
        organization.plan_override_reason = reason
        await self.recompute_plan(organization)
        await self.session.commit()

    async def has_blocking_subscription(self, organization_id: UUID) -> bool:
        return await self.subscriptions.has_blocking_subscription(organization_id)

    async def process_webhook_event(self, event: NormalizedEvent) -> WebhookOutcome:
        provider_name = self._require_provider().name
        await self.billing_events.insert_if_absent(
            provider=provider_name, event_id=event.event_id, event_type=event.event_type, payload=event.payload
        )
        await self.session.commit()

        billing_event = await self.billing_events.get_by_provider_event_id(
            provider_name, event.event_id, for_update=True
        )
        if billing_event is None:
            raise BillingEventError(f"Billing event {event.event_id} vanished after insert")
        if billing_event.processed_at is not None:
            await self.session.commit()
            return "duplicate"

        try:
            await self.apply_event(event)
            billing_event.processed_at = datetime.now(UTC)
            billing_event.error = None
            await self.session.commit()
        except Exception as error:
            await self.session.rollback()
            logger.exception("Billing event %s/%s failed", provider_name, event.event_id)
            await self._record_event_error(provider_name, event.event_id, error)
            return "failed"
        return "processed"

    async def apply_event(self, event: NormalizedEvent) -> Organization | None:
        if event.kind == "ignored":
            return None
        provider_name = self._require_provider().name
        try:
            organization = await self._resolve_organization(provider_name, event)
            if event.subscription is not None:
                await self._upsert_subscription(provider_name, organization, event.subscription, event.occurred_at)
        except UnrelatedBillingEventError as error:
            logger.warning("Skipping billing event %s/%s: %s", provider_name, event.event_id, error)
            return None
        if event.payment is not None:
            await self._upsert_payment(provider_name, organization, event.payment)
        await self.recompute_plan(organization)
        return organization

    def _require_provider(self) -> PaymentProvider:
        if self.provider is None:
            raise BusinessError("billing_disabled", "Billing is not enabled on this deployment", status_code=400)
        return self.provider

    def _billing_page_url(self, organization: Organization) -> str:
        return f"{self.settings.APP_URL}/app/{organization.slug}/billing"

    @staticmethod
    def _provider_failure(error: BillingProviderError) -> BusinessError:
        logger.warning("Billing provider request failed: %s", error)
        return BusinessError(
            "billing_provider_error", "The payment provider could not complete the request", status_code=502
        )

    def _plan_response(self, plan: Plan) -> PlanResponse:
        return PlanResponse(
            id=plan.id,
            name=plan.name,
            price_monthly_cents=plan.price_monthly_cents,
            price_yearly_cents=plan.price_yearly_cents,
            trial_days=plan.trial_days,
            limits=PlanLimitsResponse(
                members=plan.limits.members, projects=plan.limits.projects, storage_mb=plan.limits.storage_mb
            ),
            features=sorted(plan.features),
            available=PlanAvailabilityResponse(
                monthly=self.provider_config.is_plan_available(plan.id, BillingInterval.MONTHLY),
                yearly=self.provider_config.is_plan_available(plan.id, BillingInterval.YEARLY),
            ),
        )

    async def _resolve_organization(self, provider_name: str, event: NormalizedEvent) -> Organization:
        if event.organization_id is not None:
            organization = await self.organizations.get_by_id(id=event.organization_id)
            if organization is not None:
                return organization
        candidate_subscription_ids = [
            subscription_id
            for subscription_id in (
                event.subscription.provider_subscription_id if event.subscription else None,
                event.payment.provider_subscription_id if event.payment else None,
            )
            if subscription_id
        ]
        for provider_subscription_id in candidate_subscription_ids:
            existing = await self.subscriptions.get_by_provider_id(provider_name, provider_subscription_id)
            if existing is not None:
                organization = await self.organizations.get_by_id(id=existing.organization_id)
                if organization is not None:
                    return organization
        message = f"Cannot resolve the organization for {provider_name} event {event.event_id}"
        # A brand-new subscription may arrive before the event that links it, so recent events are retried
        if event.occurred_at is not None and datetime.now(UTC) - event.occurred_at < UNRESOLVED_EVENT_RETRY_WINDOW:
            raise BillingEventError(message)
        raise UnrelatedBillingEventError(message)

    def _resolve_plan(
        self, snapshot: SubscriptionSnapshot, existing: Subscription | None
    ) -> tuple[str, BillingInterval]:
        resolved = self.provider_config.resolve_price_reference(snapshot.price_reference)
        if resolved is not None:
            return resolved
        if existing is None:
            raise UnrelatedBillingEventError(
                f"Price {snapshot.price_reference!r} of subscription {snapshot.provider_subscription_id} "
                "matches no configured plan"
            )
        return existing.plan_id, snapshot.interval_hint or BillingInterval(existing.interval)

    @staticmethod
    def _is_stale_snapshot(
        existing: Subscription, snapshot: SubscriptionSnapshot, occurred_at: datetime | None
    ) -> bool:
        if existing.status in ENDED_SUBSCRIPTION_STATUSES and snapshot.status not in ENDED_SUBSCRIPTION_STATUSES:
            return True
        last_applied_at = existing.provider_updated_at
        return occurred_at is not None and last_applied_at is not None and occurred_at < last_applied_at

    async def _upsert_subscription(
        self,
        provider_name: str,
        organization: Organization,
        snapshot: SubscriptionSnapshot,
        occurred_at: datetime | None,
    ) -> Subscription:
        existing = await self.subscriptions.get_by_provider_id(provider_name, snapshot.provider_subscription_id)
        if existing is not None and self._is_stale_snapshot(existing, snapshot, occurred_at):
            logger.info("Skipping an outdated update of subscription %s", snapshot.provider_subscription_id)
            return existing
        plan_id, interval = self._resolve_plan(snapshot, existing)
        subscription = existing or Subscription(
            organization_id=organization.id,
            provider=provider_name,
            provider_subscription_id=snapshot.provider_subscription_id,
        )
        subscription.plan_id = plan_id
        subscription.interval = interval
        subscription.status = snapshot.status
        subscription.cancel_at_period_end = snapshot.cancel_at_period_end
        if snapshot.current_period_end is not None:
            subscription.current_period_end = snapshot.current_period_end
        if snapshot.trial_ends_at is not None:
            subscription.trial_ends_at = snapshot.trial_ends_at
        if occurred_at is not None:
            subscription.provider_updated_at = occurred_at
        if existing is None:
            await self.subscriptions.add(subscription)
        if snapshot.customer_id:
            organization.billing_provider = provider_name
            organization.billing_customer_id = snapshot.customer_id
        await self.session.flush()
        return subscription

    async def _upsert_payment(
        self, provider_name: str, organization: Organization, snapshot: PaymentSnapshot
    ) -> Payment:
        existing = await self.payments.get_by_provider_id(provider_name, snapshot.provider_payment_id)
        payment = existing or Payment(
            organization_id=organization.id,
            provider=provider_name,
            provider_payment_id=snapshot.provider_payment_id,
        )
        is_late_failure = (
            existing is not None
            and existing.status == PaymentStatus.SUCCEEDED
            and snapshot.status == PaymentStatus.FAILED
        )
        if not is_late_failure:
            payment.status = snapshot.status
            payment.amount_cents = snapshot.amount_cents
            payment.currency = snapshot.currency
            if snapshot.paid_at is not None:
                payment.paid_at = snapshot.paid_at
            if snapshot.invoice_url:
                payment.invoice_url = snapshot.invoice_url
        if existing is None:
            await self.payments.add(payment)
        await self.session.flush()
        return payment

    async def _record_event_error(self, provider_name: str, event_id: str, error: Exception) -> None:
        billing_event = await self.billing_events.get_by_provider_event_id(provider_name, event_id)
        if billing_event is None:
            return
        billing_event.error = f"{type(error).__name__}: {error}"[:EVENT_ERROR_MAX_LENGTH]
        await self.session.commit()
