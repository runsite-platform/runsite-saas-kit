from collections.abc import Mapping
from typing import Any

from app.config.settings import Settings
from app.constants.enums import BillingInterval, PaymentStatus, SubscriptionStatus
from app.models import Organization, Subscription
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
    checkout_metadata,
    header_value,
    load_json_payload,
    parse_epoch_seconds_or_milliseconds,
    parse_interval,
    parse_iso_datetime,
    parse_organization_id,
    reference_id,
    verify_hmac_sha256_hex,
)
from app.services.billing.providers.http_client import request_provider_json

CREEM_SIGNATURE_HEADER = "creem-signature"
CHECKOUT_COMPLETED_EVENT = "checkout.completed"
SUBSCRIPTION_PAID_EVENT = "subscription.paid"
SCHEDULED_CANCEL_EVENT = "subscription.scheduled_cancel"
CREEM_STATUS_MAP: dict[str, SubscriptionStatus] = {
    "active": SubscriptionStatus.ACTIVE,
    "scheduled_cancel": SubscriptionStatus.ACTIVE,
    "trialing": SubscriptionStatus.TRIALING,
    "past_due": SubscriptionStatus.PAST_DUE,
    "unpaid": SubscriptionStatus.PAST_DUE,
    "paused": SubscriptionStatus.PAST_DUE,
    "canceled": SubscriptionStatus.CANCELED,
    "expired": SubscriptionStatus.EXPIRED,
}
EVENT_STATUS_OVERRIDES: dict[str, SubscriptionStatus] = {
    "subscription.canceled": SubscriptionStatus.CANCELED,
    "subscription.expired": SubscriptionStatus.EXPIRED,
}
CREEM_INTERVAL_MAP: dict[str, BillingInterval] = {
    "every-month": BillingInterval.MONTHLY,
    "every-year": BillingInterval.YEARLY,
}
SUBSCRIPTION_EVENT_KINDS: dict[str, EventKind] = {
    "subscription.active": "subscription_created",
    "subscription.trialing": "subscription_created",
    "subscription.update": "subscription_updated",
    "subscription.past_due": "subscription_updated",
    "subscription.unpaid": "subscription_updated",
    "subscription.paused": "subscription_updated",
    SCHEDULED_CANCEL_EVENT: "subscription_updated",
    "subscription.canceled": "subscription_canceled",
    "subscription.expired": "subscription_canceled",
}


class CreemProvider:
    """Creem payment provider."""

    name = "creem"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.provider_config = ProviderConfig(settings)

    def _url(self, path: str) -> str:
        return f"{self.settings.CREEM_API_URL.rstrip('/')}{path}"

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.settings.CREEM_API_KEY,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def create_checkout(
        self,
        organization: Organization,
        plan: Plan,
        interval: BillingInterval,
        customer_email: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create a Creem checkout and return its URL."""
        product_id = self.provider_config.price_reference(plan.id, interval)
        if product_id is None:
            raise BillingProviderError(f"No Creem product configured for {plan.id} ({interval})")
        body = {
            "product_id": product_id,
            "success_url": success_url,
            "customer": {"email": customer_email},
            "metadata": checkout_metadata(organization.id, plan.id, interval),
        }
        response = await request_provider_json(
            "POST", self._url("/v1/checkouts"), headers=self._headers(), json_body=body
        )
        checkout_url = response.get("checkout_url")
        if not checkout_url:
            raise BillingProviderError("Creem returned a checkout without checkout_url")
        return str(checkout_url)

    async def create_portal_url(self, organization: Organization, return_url: str) -> str:
        """Return the Creem customer portal URL."""
        response = await request_provider_json(
            "POST",
            self._url("/v1/customers/billing"),
            headers=self._headers(),
            json_body={"customer_id": organization.billing_customer_id},
        )
        portal_url = response.get("customer_portal_link")
        if not portal_url:
            raise BillingProviderError("Creem returned no customer_portal_link")
        return str(portal_url)

    async def cancel_subscription(self, subscription: Subscription, at_period_end: bool = True) -> None:
        """Cancel the Creem subscription immediately or at period end."""
        body = {"mode": "scheduled", "onExecute": "cancel"} if at_period_end else {"mode": "immediate"}
        await request_provider_json(
            "POST",
            self._url(f"/v1/subscriptions/{subscription.provider_subscription_id}/cancel"),
            headers=self._headers(),
            json_body=body,
        )

    def parse_webhook(self, raw_body: bytes, headers: Mapping[str, str]) -> NormalizedEvent:
        """Verify a Creem webhook signature and normalize the event."""
        verify_hmac_sha256_hex(
            raw_body, self.settings.CREEM_WEBHOOK_SECRET, header_value(headers, CREEM_SIGNATURE_HEADER)
        )
        return normalize_creem_event(load_json_payload(raw_body))


def normalize_creem_event(payload: dict[str, Any]) -> NormalizedEvent:
    """Convert a Creem event payload into a NormalizedEvent."""
    try:
        return _normalize(payload)
    except (KeyError, TypeError, ValueError) as error:
        raise WebhookPayloadError(f"Unexpected Creem payload: {error!r}") from error


def _normalize(payload: dict[str, Any]) -> NormalizedEvent:
    event_id = str(payload["id"])
    event_type = str(payload["eventType"])
    event_object = payload["object"]
    occurred_at = parse_epoch_seconds_or_milliseconds(payload.get("created_at"))
    ignored = NormalizedEvent(event_id=event_id, event_type=event_type, kind="ignored", payload=payload)

    if event_type == CHECKOUT_COMPLETED_EVENT:
        subscription_object = event_object.get("subscription")
        if not isinstance(subscription_object, dict):
            return ignored
        metadata = event_object.get("metadata") or subscription_object.get("metadata") or {}
        return NormalizedEvent(
            event_id=event_id,
            event_type=event_type,
            kind="subscription_created",
            payload=payload,
            organization_id=parse_organization_id(metadata.get(ORGANIZATION_METADATA_KEY)),
            occurred_at=occurred_at,
            subscription=_subscription_snapshot(
                subscription_object,
                event_type=event_type,
                metadata=metadata,
                product=event_object.get("product"),
                customer=event_object.get("customer"),
            ),
        )

    if event_type != SUBSCRIPTION_PAID_EVENT and event_type not in SUBSCRIPTION_EVENT_KINDS:
        return ignored

    metadata = event_object.get("metadata") or {}
    snapshot = _subscription_snapshot(event_object, event_type=event_type, metadata=metadata)
    organization_id = parse_organization_id(metadata.get(ORGANIZATION_METADATA_KEY))

    if event_type == SUBSCRIPTION_PAID_EVENT:
        payment = _payment_snapshot(event_object)
        return NormalizedEvent(
            event_id=event_id,
            event_type=event_type,
            kind="payment_succeeded" if payment is not None else "subscription_updated",
            payload=payload,
            organization_id=organization_id,
            occurred_at=occurred_at,
            subscription=snapshot,
            payment=payment,
        )

    kind = SUBSCRIPTION_EVENT_KINDS[event_type]
    if snapshot.status in ENDED_SUBSCRIPTION_STATUSES:
        kind = "subscription_canceled"
    return NormalizedEvent(
        event_id=event_id,
        event_type=event_type,
        kind=kind,
        payload=payload,
        organization_id=organization_id,
        occurred_at=occurred_at,
        subscription=snapshot,
    )


def _subscription_snapshot(
    subscription_object: dict[str, Any],
    *,
    event_type: str,
    metadata: dict[str, Any],
    product: object = None,
    customer: object = None,
) -> SubscriptionSnapshot:
    product_value = product if product is not None else subscription_object.get("product")
    product_details = product_value if isinstance(product_value, dict) else {}
    status_name = str(subscription_object.get("status") or "")
    status = EVENT_STATUS_OVERRIDES.get(event_type) or CREEM_STATUS_MAP.get(status_name, SubscriptionStatus.PAST_DUE)
    period_end = parse_iso_datetime(subscription_object.get("current_period_end_date"))
    return SubscriptionSnapshot(
        provider_subscription_id=str(subscription_object["id"]),
        status=status,
        customer_id=reference_id(customer if customer is not None else subscription_object.get("customer")),
        price_reference=reference_id(product_value),
        interval_hint=CREEM_INTERVAL_MAP.get(str(product_details.get("billing_period")))
        or parse_interval(metadata.get(INTERVAL_METADATA_KEY)),
        current_period_end=period_end,
        cancel_at_period_end=status_name == "scheduled_cancel" or event_type == SCHEDULED_CANCEL_EVENT,
        trial_ends_at=period_end if status == SubscriptionStatus.TRIALING else None,
    )


def _payment_snapshot(subscription_object: dict[str, Any]) -> PaymentSnapshot | None:
    transaction_id = subscription_object.get("last_transaction_id")
    if not transaction_id:
        return None
    product_value = subscription_object.get("product")
    product_details = product_value if isinstance(product_value, dict) else {}
    return PaymentSnapshot(
        provider_payment_id=str(transaction_id),
        amount_cents=int(product_details.get("price") or 0),
        currency=str(product_details.get("currency") or "USD").upper(),
        status=PaymentStatus.SUCCEEDED,
        provider_subscription_id=str(subscription_object["id"]),
        paid_at=parse_iso_datetime(subscription_object.get("last_transaction_date")),
        invoice_url=None,
    )
