import hashlib
import hmac
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from app.services.billing.providers.base import sign_organization_id
from app.services.email_service import EmailMessage


class InMemoryEmailSender:
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


class InMemoryObjectStorage:
    def __init__(self, *, can_delete: bool = True) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}
        self.deleted: list[str] = []
        self.can_delete = can_delete
        self.fail_deletes = False
        self.download_names: dict[str, str | None] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data
        self.content_types[key] = content_type

    async def delete(self, key: str) -> bool:
        if self.fail_deletes:
            raise ConnectionError("storage unreachable")
        if not self.can_delete:
            return False
        self.objects.pop(key, None)
        self.content_types.pop(key, None)
        self.deleted.append(key)
        return True

    def presigned_get_url(self, key: str, expires_seconds: int = 900, download_name: str | None = None) -> str:
        self.download_names[key] = download_name
        return f"https://storage.test/{key}"


TEST_STRIPE_SETTINGS: dict[str, str] = {
    "BILLING_PROVIDER": "stripe",
    "STRIPE_SECRET_KEY": "sk_test_runsite_kit",
    "STRIPE_WEBHOOK_SECRET": "whsec_test_runsite_kit",
    "STRIPE_PRICE_PRO_MONTHLY": "price_pro_monthly_test",
    "STRIPE_PRICE_PRO_YEARLY": "price_pro_yearly_test",
}
TEST_LEMONSQUEEZY_SETTINGS: dict[str, str] = {
    "BILLING_PROVIDER": "lemonsqueezy",
    "LEMONSQUEEZY_API_KEY": "ls_test_api_key",
    "LEMONSQUEEZY_STORE_ID": "9001",
    "LEMONSQUEEZY_WEBHOOK_SECRET": "ls_test_signing_secret",
    "LEMONSQUEEZY_VARIANT_PRO_MONTHLY": "101",
    "LEMONSQUEEZY_VARIANT_PRO_YEARLY": "102",
}
TEST_CREEM_SETTINGS: dict[str, str] = {
    "BILLING_PROVIDER": "creem",
    "CREEM_API_KEY": "creem_test_api_key",
    "CREEM_API_URL": "https://test-api.creem.io",
    "CREEM_WEBHOOK_SECRET": "creem_test_webhook_secret",
    "CREEM_PRODUCT_PRO_MONTHLY": "prod_pro_monthly_test",
    "CREEM_PRODUCT_PRO_YEARLY": "prod_pro_yearly_test",
}

FAKE_STRIPE_CHECKOUT_URL = "https://checkout.stripe.com/c/pay/cs_test_runsite_kit"
FAKE_STRIPE_PORTAL_URL = "https://billing.stripe.com/p/session/test_runsite_kit"
WEBHOOK_FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures" / "webhooks"
ORGANIZATION_ID_PLACEHOLDER = "__ORGANIZATION_ID__"
ORGANIZATION_SIGNATURE_PLACEHOLDER = "__ORGANIZATION_SIGNATURE__"


class RecordingAsyncMethod:
    def __init__(self, result: Any = None) -> None:
        self.result = result
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append((args, kwargs))
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


class FakeStripeClient:
    """Mimics the parts of `stripe.StripeClient` that `StripeProvider` calls."""

    def __init__(self) -> None:
        self.create_checkout_session = RecordingAsyncMethod(
            SimpleNamespace(id="cs_test_runsite_kit", url=FAKE_STRIPE_CHECKOUT_URL)
        )
        self.create_portal_session = RecordingAsyncMethod(SimpleNamespace(url=FAKE_STRIPE_PORTAL_URL))
        self.update_subscription = RecordingAsyncMethod(SimpleNamespace(id="sub_updated"))
        self.cancel_subscription = RecordingAsyncMethod(SimpleNamespace(id="sub_canceled"))
        self.v1 = SimpleNamespace(
            checkout=SimpleNamespace(sessions=SimpleNamespace(create_async=self.create_checkout_session)),
            billing_portal=SimpleNamespace(sessions=SimpleNamespace(create_async=self.create_portal_session)),
            subscriptions=SimpleNamespace(
                update_async=self.update_subscription,
                cancel_async=self.cancel_subscription,
            ),
        )


def load_webhook_body(provider: str, name: str, *, organization_id: UUID | None = None) -> bytes:
    template = (WEBHOOK_FIXTURES_DIRECTORY / provider / f"{name}.json").read_text(encoding="utf-8")
    resolved_organization_id = organization_id or uuid4()
    signature = sign_organization_id(
        resolved_organization_id, TEST_LEMONSQUEEZY_SETTINGS["LEMONSQUEEZY_WEBHOOK_SECRET"]
    )
    return (
        template.replace(ORGANIZATION_ID_PLACEHOLDER, str(resolved_organization_id))
        .replace(ORGANIZATION_SIGNATURE_PLACEHOLDER, signature)
        .encode()
    )


def hmac_sha256_hex(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def stripe_signature_header(body: bytes, secret: str, *, timestamp: int | None = None) -> str:
    signed_at = int(time.time()) if timestamp is None else timestamp
    digest = hmac.new(secret.encode(), f"{signed_at}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={signed_at},v1={digest}"


def stripe_webhook_headers(body: bytes) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Stripe-Signature": stripe_signature_header(body, TEST_STRIPE_SETTINGS["STRIPE_WEBHOOK_SECRET"]),
    }


def lemonsqueezy_webhook_headers(body: bytes, event_name: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Event-Name": event_name,
        "X-Signature": hmac_sha256_hex(body, TEST_LEMONSQUEEZY_SETTINGS["LEMONSQUEEZY_WEBHOOK_SECRET"]),
    }


def creem_webhook_headers(body: bytes) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "creem-signature": hmac_sha256_hex(body, TEST_CREEM_SETTINGS["CREEM_WEBHOOK_SECRET"]),
    }
