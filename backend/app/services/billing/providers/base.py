import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import UUID

from app.constants.enums import BillingInterval, PaymentStatus, SubscriptionStatus
from app.models import Organization, Subscription
from app.services.billing.plans import Plan

EventKind = Literal[
    "subscription_created",
    "subscription_updated",
    "subscription_canceled",
    "payment_succeeded",
    "payment_failed",
    "ignored",
]

ORGANIZATION_METADATA_KEY = "organization_id"
ORGANIZATION_SIGNATURE_KEY = "organization_signature"
PLAN_METADATA_KEY = "plan_id"
INTERVAL_METADATA_KEY = "interval"
ENDED_SUBSCRIPTION_STATUSES: tuple[SubscriptionStatus, ...] = (SubscriptionStatus.CANCELED, SubscriptionStatus.EXPIRED)


class WebhookSignatureError(Exception):
    """Error raised when a webhook signature is missing or invalid."""

    pass


class WebhookPayloadError(ValueError):
    """Error raised when a webhook payload is malformed."""

    pass


class BillingProviderError(Exception):
    """Error raised when a payment provider request fails."""

    pass


@dataclass(frozen=True)
class SubscriptionSnapshot:
    """Provider-independent state of a subscription."""

    provider_subscription_id: str
    status: SubscriptionStatus
    customer_id: str | None = None
    price_reference: str | None = None
    interval_hint: BillingInterval | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    trial_ends_at: datetime | None = None


@dataclass(frozen=True)
class PaymentSnapshot:
    """Provider-independent state of a payment."""

    provider_payment_id: str
    amount_cents: int
    currency: str
    status: PaymentStatus
    provider_subscription_id: str | None = None
    paid_at: datetime | None = None
    invoice_url: str | None = None


@dataclass(frozen=True)
class NormalizedEvent:
    """Provider-independent billing webhook event."""

    event_id: str
    event_type: str
    kind: EventKind
    payload: dict[str, Any]
    organization_id: UUID | None = None
    occurred_at: datetime | None = None
    subscription: SubscriptionSnapshot | None = None
    payment: PaymentSnapshot | None = None


class PaymentProvider(Protocol):
    """Interface implemented by payment providers."""

    name: str

    async def create_checkout(
        self,
        organization: Organization,
        plan: Plan,
        interval: BillingInterval,
        customer_email: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create a checkout session and return its URL."""
        ...

    async def create_portal_url(self, organization: Organization, return_url: str) -> str:
        """Return the customer billing portal URL."""
        ...

    async def cancel_subscription(self, subscription: Subscription, at_period_end: bool = True) -> None:
        """Cancel the subscription immediately or at period end."""
        ...

    def parse_webhook(self, raw_body: bytes, headers: Mapping[str, str]) -> NormalizedEvent:
        """Verify a webhook request and return the normalized event."""
        ...


def checkout_metadata(organization_id: UUID, plan_id: str, interval: BillingInterval) -> dict[str, str]:
    """Return the metadata attached to a checkout."""
    return {
        ORGANIZATION_METADATA_KEY: str(organization_id),
        PLAN_METADATA_KEY: plan_id,
        INTERVAL_METADATA_KEY: str(interval),
    }


def sign_organization_id(organization_id: UUID, secret: str) -> str:
    """Return an HMAC-SHA256 signature of the organization id."""
    return hmac.new(secret.encode(), f"billing-organization:{organization_id}".encode(), hashlib.sha256).hexdigest()


def verified_organization_id(metadata: Mapping[str, Any], secret: str) -> UUID | None:
    """Metadata that buyers can edit (Lemon Squeezy custom data) is trusted only with our signature."""
    organization_id = parse_organization_id(metadata.get(ORGANIZATION_METADATA_KEY))
    signature = metadata.get(ORGANIZATION_SIGNATURE_KEY)
    if organization_id is None or not secret or not isinstance(signature, str):
        return None
    if not hmac.compare_digest(sign_organization_id(organization_id, secret), signature):
        return None
    return organization_id


def verify_hmac_sha256_hex(raw_body: bytes, secret: str, signature: str | None) -> None:
    """Raise WebhookSignatureError unless the HMAC-SHA256 signature matches."""
    if not secret or not signature:
        raise WebhookSignatureError("Missing webhook signature or signing secret")
    expected_signature = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_signature, signature.strip().lower()):
        raise WebhookSignatureError("Webhook signature does not match")


def load_json_payload(raw_body: bytes) -> dict[str, Any]:
    """Parse the webhook body as a JSON object."""
    try:
        payload = json.loads(raw_body)
    except ValueError as error:
        raise WebhookPayloadError("Webhook body is not valid JSON") from error
    if not isinstance(payload, dict):
        raise WebhookPayloadError("Webhook body must be a JSON object")
    return payload


def parse_organization_id(value: object) -> UUID | None:
    """Parse a UUID, returning None if it is missing or invalid."""
    if value is None:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


def parse_interval(value: object) -> BillingInterval | None:
    """Parse a billing interval, returning None if it is missing or invalid."""
    if not value:
        return None
    try:
        return BillingInterval(str(value))
    except ValueError:
        return None


def parse_iso_datetime(value: object) -> datetime | None:
    """Parse an ISO 8601 datetime, assuming UTC when naive."""
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def parse_unix_timestamp(value: object) -> datetime | None:
    """Convert a Unix timestamp in seconds to a UTC datetime."""
    if value is None:
        return None
    return datetime.fromtimestamp(int(str(value)), tz=UTC)


MILLISECOND_TIMESTAMP_THRESHOLD = 10**11


def parse_epoch_seconds_or_milliseconds(value: object) -> datetime | None:
    """Parse an epoch in seconds or milliseconds, or an ISO datetime."""
    if value is None or isinstance(value, bool):
        return None
    try:
        timestamp = int(str(value))
    except ValueError:
        return parse_iso_datetime(value)
    if timestamp > MILLISECOND_TIMESTAMP_THRESHOLD:
        return datetime.fromtimestamp(timestamp / 1000, tz=UTC)
    return datetime.fromtimestamp(timestamp, tz=UTC)


def header_value(headers: Mapping[str, str], name: str) -> str | None:
    """Return a header value by case-insensitive name."""
    lowered_name = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered_name:
            return value
    return None


def reference_id(value: object) -> str | None:
    """Return the id of a reference given as a value or an object with an id."""
    if value is None:
        return None
    if isinstance(value, Mapping):
        nested_id = value.get("id")
        return str(nested_id) if nested_id is not None else None
    return str(value)
