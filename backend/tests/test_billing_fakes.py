import hashlib
import hmac
from uuid import uuid4

import stripe

from tests.fakes import (
    FAKE_STRIPE_CHECKOUT_URL,
    FakeStripeClient,
    hmac_sha256_hex,
    stripe_signature_header,
)


async def test_fake_stripe_client_records_calls_and_raises_configured_errors() -> None:
    client = FakeStripeClient()

    session = await client.v1.checkout.sessions.create_async(params={"mode": "subscription"})
    assert session.url == FAKE_STRIPE_CHECKOUT_URL
    assert client.create_checkout_session.calls == [((), {"params": {"mode": "subscription"}})]

    client.update_subscription.result = stripe.APIConnectionError("offline")
    try:
        await client.v1.subscriptions.update_async("sub_1", params={})
    except stripe.APIConnectionError as error:
        assert "offline" in str(error)
    else:
        raise AssertionError("expected APIConnectionError")


def test_stripe_signature_header_verifies_with_the_stripe_library() -> None:
    body = b'{"id": "evt_test", "object": "event", "type": "ping", "data": {"object": {}}}'
    header = stripe_signature_header(body, "whsec_unit")
    event = stripe.Webhook.construct_event(body, header, "whsec_unit")
    assert event.id == "evt_test"


def test_hmac_helper_matches_hashlib() -> None:
    body = str(uuid4()).encode()
    assert hmac_sha256_hex(body, "secret") == hmac.new(b"secret", body, hashlib.sha256).hexdigest()
