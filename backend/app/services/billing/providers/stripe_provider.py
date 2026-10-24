from collections.abc import Mapping
from typing import Any

import stripe

from app.config.settings import Settings
from app.models import Organization, Subscription
from app.constants.enums import BillingInterval, PaymentStatus, SubscriptionStatus
from app.services.billing.plans import Plan
from app.services.billing.provider_config import ProviderConfig
from app.services.billing.providers.base import (
    ENDED_SUBSCRIPTION_STATUSES,
    INTERVAL_METADATA_KEY,
    ORGANIZATION_METADATA_KEY,
    BillingProviderError,
    EventKind,
    NormalizedEvent,
    PaymentSnapshot,
    SubscriptionSnapshot,
    WebhookPayloadError,
    WebhookSignatureError,
    checkout_metadata,
    header_value,
    load_json_payload,
    parse_interval,
    parse_organization_id,
    parse_unix_timestamp,
    reference_id,
)

STRIPE_SIGNATURE_HEADER = "stripe-signature"
STRIPE_STATUS_MAP: dict[str, SubscriptionStatus] = {
    "trialing": SubscriptionStatus.TRIALING,
    "active": SubscriptionStatus.ACTIVE,
    "past_due": SubscriptionStatus.PAST_DUE,
    "unpaid": SubscriptionStatus.PAST_DUE,
    "paused": SubscriptionStatus.PAST_DUE,
    "incomplete": SubscriptionStatus.PAST_DUE,
    "canceled": SubscriptionStatus.CANCELED,
    "incomplete_expired": SubscriptionStatus.EXPIRED,
}
STRIPE_INTERVAL_MAP: dict[str, BillingInterval] = {"month": BillingInterval.MONTHLY, "year": BillingInterval.YEARLY}
SUBSCRIPTION_EVENT_KINDS: dict[str, EventKind] = {
    "customer.subscription.created": "subscription_created",
    "customer.subscription.updated": "subscription_updated",
    "customer.subscription.deleted": "subscription_canceled",
}
INVOICE_EVENT_STATUSES: dict[str, PaymentStatus] = {
    "invoice.paid": PaymentStatus.SUCCEEDED,
    "invoice.payment_succeeded": PaymentStatus.SUCCEEDED,
    "invoice.payment_failed": PaymentStatus.FAILED,
}


class StripeProvider:
    """Stripe payment provider."""

    name = "stripe"

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.settings = settings
        self.provider_config = ProviderConfig(settings)
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = stripe.StripeClient(self.settings.STRIPE_SECRET_KEY)
        return self._client

    async def create_checkout(
        self,
        organization: Organization,
        plan: Plan,
        interval: BillingInterval,
        customer_email: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create a Stripe Checkout session and return its URL."""
        price_id = self.provider_config.price_reference(plan.id, interval)
        if price_id is None:
            raise BillingProviderError(f"No Stripe price configured for {plan.id} ({interval})")
        metadata = checkout_metadata(organization.id, plan.id, interval)
        subscription_data: dict[str, Any] = {"metadata": metadata}
        if plan.trial_days > 0:
            subscription_data["trial_period_days"] = plan.trial_days
        params: dict[str, Any] = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "client_reference_id": str(organization.id),
            "metadata": metadata,
            "subscription_data": subscription_data,
        }
        if organization.billing_provider == self.name and organization.billing_customer_id:
            params["customer"] = organization.billing_customer_id
        else:
            params["customer_email"] = customer_email
        try:
            checkout_session = await self._get_client().v1.checkout.sessions.create_async(params=params)
        except stripe.StripeError as error:
            raise BillingProviderError(f"Stripe checkout failed: {error}") from error
        if not checkout_session.url:
            raise BillingProviderError("Stripe returned a checkout session without a URL")
        return str(checkout_session.url)

    async def create_portal_url(self, organization: Organization, return_url: str) -> str:
        """Create a Stripe billing portal session and return its URL."""
        params = {"customer": organization.billing_customer_id, "return_url": return_url}
        try:
            portal_session = await self._get_client().v1.billing_portal.sessions.create_async(params=params)
        except stripe.StripeError as error:
            raise BillingProviderError(f"Stripe billing portal failed: {error}") from error
        return str(portal_session.url)

    async def cancel_subscription(self, subscription: Subscription, at_period_end: bool = True) -> None:
        """Cancel the Stripe subscription immediately or at period end."""
        try:
            subscriptions = self._get_client().v1.subscriptions
            if at_period_end:
                await subscriptions.update_async(
                    subscription.provider_subscription_id, params={"cancel_at_period_end": True}
                )
            else:
                await subscriptions.cancel_async(subscription.provider_subscription_id)
        except stripe.StripeError as error:
            raise BillingProviderError(f"Stripe cancellation failed: {error}") from error

    def parse_webhook(self, raw_body: bytes, headers: Mapping[str, str]) -> NormalizedEvent:
        """Verify a Stripe webhook signature and normalize the event."""
        signature = header_value(headers, STRIPE_SIGNATURE_HEADER)
        if not signature or not self.settings.STRIPE_WEBHOOK_SECRET:
            raise WebhookSignatureError("Missing Stripe signature or webhook secret")
        try:
            stripe.Webhook.construct_event(raw_body, signature, self.settings.STRIPE_WEBHOOK_SECRET)
        except stripe.SignatureVerificationError as error:
            raise WebhookSignatureError(str(error)) from error
        except ValueError as error:
            raise WebhookPayloadError("Stripe webhook body is not valid JSON") from error
        return normalize_stripe_event(load_json_payload(raw_body))


def normalize_stripe_event(payload: dict[str, Any]) -> NormalizedEvent:
    """Convert a Stripe event payload into a NormalizedEvent."""
    try:
        return _normalize(payload)
    except (KeyError, TypeError, ValueError, IndexError) as error:
        raise WebhookPayloadError(f"Unexpected Stripe payload: {error!r}") from error


def _normalize(payload: dict[str, Any]) -> NormalizedEvent:
    event_id = str(payload["id"])
    event_type = str(payload["type"])
    data_object = payload["data"]["object"]
    occurred_at = parse_unix_timestamp(payload.get("created"))

    if event_type in SUBSCRIPTION_EVENT_KINDS:
        snapshot = _subscription_snapshot(data_object)
        kind = SUBSCRIPTION_EVENT_KINDS[event_type]
        if snapshot.status in ENDED_SUBSCRIPTION_STATUSES:
            kind = "subscription_canceled"
        metadata = data_object.get("metadata") or {}
        return NormalizedEvent(
            event_id=event_id,
            event_type=event_type,
            kind=kind,
            payload=payload,
            organization_id=parse_organization_id(metadata.get(ORGANIZATION_METADATA_KEY)),
            occurred_at=occurred_at,
            subscription=snapshot,
        )

    if event_type in INVOICE_EVENT_STATUSES:
        status = INVOICE_EVENT_STATUSES[event_type]
        details = _invoice_subscription_details(data_object)
        metadata = details.get("metadata") or {}
        return NormalizedEvent(
            event_id=event_id,
            event_type=event_type,
            kind="payment_succeeded" if status == PaymentStatus.SUCCEEDED else "payment_failed",
            payload=payload,
            organization_id=parse_organization_id(metadata.get(ORGANIZATION_METADATA_KEY)),
            occurred_at=occurred_at,
            payment=_payment_snapshot(data_object, status, details),
        )

    return NormalizedEvent(event_id=event_id, event_type=event_type, kind="ignored", payload=payload)


def _subscription_snapshot(subscription_object: dict[str, Any]) -> SubscriptionSnapshot:
    items = (subscription_object.get("items") or {}).get("data") or []
    first_item = items[0] if items else {}
    price = first_item.get("price") or {}
    metadata = subscription_object.get("metadata") or {}
    period_end = first_item.get("current_period_end") or subscription_object.get("current_period_end")
    recurring_interval = (price.get("recurring") or {}).get("interval")
    return SubscriptionSnapshot(
        provider_subscription_id=str(subscription_object["id"]),
        status=STRIPE_STATUS_MAP.get(str(subscription_object["status"]), SubscriptionStatus.PAST_DUE),
        customer_id=reference_id(subscription_object.get("customer")),
        price_reference=reference_id(price.get("id")),
        interval_hint=STRIPE_INTERVAL_MAP.get(str(recurring_interval))
        or parse_interval(metadata.get(INTERVAL_METADATA_KEY)),
        current_period_end=parse_unix_timestamp(period_end),
        cancel_at_period_end=bool(subscription_object.get("cancel_at_period_end"))
        or subscription_object.get("cancel_at") is not None,
        trial_ends_at=parse_unix_timestamp(subscription_object.get("trial_end")),
    )


def _invoice_subscription_details(invoice: dict[str, Any]) -> dict[str, Any]:
    parent = invoice.get("parent") or {}
    details = parent.get("subscription_details") or invoice.get("subscription_details") or {}
    if not details.get("subscription") and invoice.get("subscription"):
        details = {**details, "subscription": invoice["subscription"]}
    return details


def _payment_snapshot(invoice: dict[str, Any], status: PaymentStatus, details: dict[str, Any]) -> PaymentSnapshot:
    succeeded = status == PaymentStatus.SUCCEEDED
    amount = invoice.get("amount_paid") if succeeded else invoice.get("amount_due")
    paid_at = (invoice.get("status_transitions") or {}).get("paid_at") if succeeded else None
    return PaymentSnapshot(
        provider_payment_id=str(invoice["id"]),
        amount_cents=int(amount or 0),
        currency=str(invoice.get("currency") or "usd").upper(),
        status=status,
        provider_subscription_id=reference_id(details.get("subscription")),
        paid_at=parse_unix_timestamp(paid_at),
        invoice_url=invoice.get("hosted_invoice_url"),
    )
