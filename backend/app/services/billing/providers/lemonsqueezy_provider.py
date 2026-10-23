import hashlib
from collections.abc import Mapping
from typing import Any

from app.config.settings import Settings
from app.models import Organization, Subscription
from app.models.enums import BillingInterval, PaymentStatus, SubscriptionStatus
from app.services.billing.plans import Plan
from app.services.billing.provider_config import ProviderConfig
from app.services.billing.providers.base import (
    ENDED_SUBSCRIPTION_STATUSES,
    INTERVAL_METADATA_KEY,
    ORGANIZATION_SIGNATURE_KEY,
    BillingProviderError,
    EventKind,
    NormalizedEvent,
    PaymentSnapshot,
    SubscriptionSnapshot,
    WebhookPayloadError,
    checkout_metadata,
    header_value,
    load_json_payload,
    parse_interval,
    parse_iso_datetime,
    reference_id,
    sign_organization_id,
    verified_organization_id,
    verify_hmac_sha256_hex,
)
from app.services.billing.providers.http_client import request_provider_json

LEMONSQUEEZY_API_URL = "https://api.lemonsqueezy.com/v1"
JSON_API_MEDIA_TYPE = "application/vnd.api+json"
LEMONSQUEEZY_SIGNATURE_HEADER = "x-signature"
LEMONSQUEEZY_STATUS_MAP: dict[str, SubscriptionStatus] = {
    "on_trial": SubscriptionStatus.TRIALING,
    "active": SubscriptionStatus.ACTIVE,
    "cancelled": SubscriptionStatus.ACTIVE,
    "past_due": SubscriptionStatus.PAST_DUE,
    "unpaid": SubscriptionStatus.PAST_DUE,
    "paused": SubscriptionStatus.PAST_DUE,
    "expired": SubscriptionStatus.EXPIRED,
}
SUBSCRIPTION_EVENT_KINDS: dict[str, EventKind] = {
    "subscription_created": "subscription_created",
    "subscription_updated": "subscription_updated",
    "subscription_cancelled": "subscription_updated",
    "subscription_resumed": "subscription_updated",
    "subscription_paused": "subscription_updated",
    "subscription_unpaused": "subscription_updated",
    "subscription_expired": "subscription_canceled",
}
PAYMENT_EVENT_STATUSES: dict[str, PaymentStatus] = {
    "subscription_payment_success": PaymentStatus.SUCCEEDED,
    "subscription_payment_recovered": PaymentStatus.SUCCEEDED,
    "subscription_payment_failed": PaymentStatus.FAILED,
}
GRACE_PERIOD_STATUSES = ("cancelled", "expired")


class LemonSqueezyProvider:
    name = "lemonsqueezy"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.provider_config = ProviderConfig(settings)

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": JSON_API_MEDIA_TYPE,
            "Content-Type": JSON_API_MEDIA_TYPE,
            "Authorization": f"Bearer {self.settings.LEMONSQUEEZY_API_KEY}",
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
        variant_id = self.provider_config.price_reference(plan.id, interval)
        if variant_id is None:
            raise BillingProviderError(f"No Lemon Squeezy variant configured for {plan.id} ({interval})")
        document = {
            "data": {
                "type": "checkouts",
                "attributes": {
                    "checkout_data": {
                        "email": customer_email,
                        "custom": {
                            **checkout_metadata(organization.id, plan.id, interval),
                            ORGANIZATION_SIGNATURE_KEY: sign_organization_id(
                                organization.id, self.settings.LEMONSQUEEZY_WEBHOOK_SECRET
                            ),
                        },
                    },
                    "product_options": {"redirect_url": success_url},
                },
                "relationships": {
                    "store": {"data": {"type": "stores", "id": self.settings.LEMONSQUEEZY_STORE_ID}},
                    "variant": {"data": {"type": "variants", "id": variant_id}},
                },
            }
        }
        response = await request_provider_json(
            "POST", f"{LEMONSQUEEZY_API_URL}/checkouts", headers=self._headers(), json_body=document
        )
        checkout_url = ((response.get("data") or {}).get("attributes") or {}).get("url")
        if not checkout_url:
            raise BillingProviderError("Lemon Squeezy returned a checkout without a URL")
        return str(checkout_url)

    async def create_portal_url(self, organization: Organization, return_url: str) -> str:
        return await self._customer_portal_url(str(organization.billing_customer_id))

    async def _customer_portal_url(self, customer_id: str) -> str:
        response = await request_provider_json(
            "GET", f"{LEMONSQUEEZY_API_URL}/customers/{customer_id}", headers=self._headers()
        )
        attributes = (response.get("data") or {}).get("attributes") or {}
        portal_url = (attributes.get("urls") or {}).get("customer_portal")
        if not portal_url:
            raise BillingProviderError("Lemon Squeezy returned no customer portal URL")
        return str(portal_url)

    async def cancel_subscription(self, subscription: Subscription, at_period_end: bool = True) -> None:
        await request_provider_json(
            "DELETE",
            f"{LEMONSQUEEZY_API_URL}/subscriptions/{subscription.provider_subscription_id}",
            headers=self._headers(),
        )

    def parse_webhook(self, raw_body: bytes, headers: Mapping[str, str]) -> NormalizedEvent:
        verify_hmac_sha256_hex(
            raw_body,
            self.settings.LEMONSQUEEZY_WEBHOOK_SECRET,
            header_value(headers, LEMONSQUEEZY_SIGNATURE_HEADER),
        )
        return normalize_lemonsqueezy_event(
            load_json_payload(raw_body), raw_body, self.settings.LEMONSQUEEZY_WEBHOOK_SECRET
        )


def lemonsqueezy_event_id(event_name: str, raw_body: bytes) -> str:
    """Lemon Squeezy sends no event id; the signed body is identical across retries of one delivery."""
    return f"{event_name}:{hashlib.sha256(raw_body).hexdigest()}"


def normalize_lemonsqueezy_event(payload: dict[str, Any], raw_body: bytes, signing_secret: str) -> NormalizedEvent:
    try:
        return _normalize(payload, raw_body, signing_secret)
    except (KeyError, TypeError, ValueError) as error:
        raise WebhookPayloadError(f"Unexpected Lemon Squeezy payload: {error!r}") from error


def _normalize(payload: dict[str, Any], raw_body: bytes, signing_secret: str) -> NormalizedEvent:
    meta = payload["meta"]
    event_name = str(meta["event_name"])
    custom_data = meta.get("custom_data") or {}
    event_id = lemonsqueezy_event_id(event_name, raw_body)
    organization_id = verified_organization_id(custom_data, signing_secret)
    data = payload["data"]
    occurred_at = parse_iso_datetime((data.get("attributes") or {}).get("updated_at"))

    if event_name in SUBSCRIPTION_EVENT_KINDS:
        snapshot = _subscription_snapshot(data, custom_data)
        kind = SUBSCRIPTION_EVENT_KINDS[event_name]
        if snapshot.status in ENDED_SUBSCRIPTION_STATUSES:
            kind = "subscription_canceled"
        return NormalizedEvent(
            event_id=event_id,
            event_type=event_name,
            kind=kind,
            payload=payload,
            organization_id=organization_id,
            occurred_at=occurred_at,
            subscription=snapshot,
        )

    if event_name in PAYMENT_EVENT_STATUSES:
        status = PAYMENT_EVENT_STATUSES[event_name]
        return NormalizedEvent(
            event_id=event_id,
            event_type=event_name,
            kind="payment_succeeded" if status == PaymentStatus.SUCCEEDED else "payment_failed",
            payload=payload,
            organization_id=organization_id,
            occurred_at=occurred_at,
            payment=_payment_snapshot(data, status),
        )

    return NormalizedEvent(
        event_id=event_id, event_type=event_name, kind="ignored", payload=payload, organization_id=organization_id
    )


def _subscription_snapshot(data: dict[str, Any], custom_data: dict[str, Any]) -> SubscriptionSnapshot:
    attributes = data["attributes"]
    status_name = str(attributes["status"])
    period_end = attributes.get("ends_at") if status_name in GRACE_PERIOD_STATUSES else attributes.get("renews_at")
    return SubscriptionSnapshot(
        provider_subscription_id=str(data["id"]),
        status=LEMONSQUEEZY_STATUS_MAP.get(status_name, SubscriptionStatus.PAST_DUE),
        customer_id=reference_id(attributes.get("customer_id")),
        price_reference=reference_id(attributes.get("variant_id")),
        interval_hint=parse_interval(custom_data.get(INTERVAL_METADATA_KEY)),
        current_period_end=parse_iso_datetime(period_end),
        cancel_at_period_end=status_name == "cancelled" or bool(attributes.get("cancelled")),
        trial_ends_at=parse_iso_datetime(attributes.get("trial_ends_at")),
    )


def _payment_snapshot(data: dict[str, Any], status: PaymentStatus) -> PaymentSnapshot:
    attributes = data["attributes"]
    paid_at = attributes.get("updated_at") or attributes.get("created_at")
    return PaymentSnapshot(
        provider_payment_id=str(data["id"]),
        amount_cents=int(attributes.get("total") or 0),
        currency=str(attributes.get("currency") or "USD").upper(),
        status=status,
        provider_subscription_id=reference_id(attributes.get("subscription_id")),
        paid_at=parse_iso_datetime(paid_at) if status == PaymentStatus.SUCCEEDED else None,
        invoice_url=(attributes.get("urls") or {}).get("invoice_url"),
    )
