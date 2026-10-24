import hashlib
import hmac
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
import respx

from app.constants.enums import BillingInterval
from app.services.billing.providers.base import (
    BillingProviderError,
    WebhookPayloadError,
    WebhookSignatureError,
    checkout_metadata,
    header_value,
    load_json_payload,
    parse_interval,
    parse_iso_datetime,
    parse_organization_id,
    parse_unix_timestamp,
    reference_id,
    verify_hmac_sha256_hex,
)
from app.services.billing.providers.http_client import request_provider_json

SECRET = "test-secret"
BODY = b'{"hello":"world"}'


def signature_for(body: bytes) -> str:
    return hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def test_hmac_verification_accepts_the_exact_body() -> None:
    verify_hmac_sha256_hex(BODY, SECRET, signature_for(BODY))


@pytest.mark.parametrize(
    ("secret", "signature"),
    [
        (SECRET, signature_for(b'{"hello":"world" }')),
        (SECRET, "0" * 64),
        (SECRET, None),
        (SECRET, ""),
        ("", signature_for(BODY)),
    ],
)
def test_hmac_verification_rejects_mismatches(secret, signature) -> None:
    with pytest.raises(WebhookSignatureError):
        verify_hmac_sha256_hex(BODY, secret, signature)


def test_datetime_parsers() -> None:
    assert parse_iso_datetime("2026-11-23T10:00:00.000000Z") == datetime(2026, 11, 23, 10, 0, tzinfo=UTC)
    assert parse_iso_datetime("2026-11-23T10:00:00.123Z") == datetime(2026, 11, 23, 10, 0, 0, 123000, tzinfo=UTC)
    assert parse_iso_datetime(None) is None
    assert parse_unix_timestamp(1792713600) == datetime(2026, 10, 23, tzinfo=UTC)
    assert parse_unix_timestamp(None) is None


def test_identifier_parsers() -> None:
    organization_id = UUID("6f1d2b1c-0d6e-4f3c-9a51-1d2a4f1e9b77")
    assert parse_organization_id(str(organization_id)) == organization_id
    assert parse_organization_id("not-a-uuid") is None
    assert parse_organization_id(None) is None
    assert parse_interval("yearly") == BillingInterval.YEARLY
    assert parse_interval("weekly") is None
    assert reference_id({"id": "cus_1"}) == "cus_1"
    assert reference_id("cus_2") == "cus_2"
    assert reference_id(42) == "42"
    assert reference_id(None) is None


def test_header_value_is_case_insensitive() -> None:
    headers = {"Content-Type": "application/json", "X-Signature": "abc"}
    assert header_value(headers, "x-signature") == "abc"
    assert header_value(headers, "creem-signature") is None


def test_checkout_metadata_is_string_only() -> None:
    organization_id = UUID("6f1d2b1c-0d6e-4f3c-9a51-1d2a4f1e9b77")
    assert checkout_metadata(organization_id, "pro", BillingInterval.YEARLY) == {
        "organization_id": str(organization_id),
        "plan_id": "pro",
        "interval": "yearly",
    }


def test_load_json_payload_rejects_non_objects() -> None:
    assert load_json_payload(b'{"id": 1}') == {"id": 1}
    with pytest.raises(WebhookPayloadError):
        load_json_payload(b"not json")
    with pytest.raises(WebhookPayloadError):
        load_json_payload(b"[1, 2]")


async def test_request_provider_json_returns_body_and_wraps_errors() -> None:
    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.post("https://provider.test/ok").mock(return_value=httpx.Response(200, json={"url": "x"}))
        respx_mock.delete("https://provider.test/empty").mock(return_value=httpx.Response(204))
        respx_mock.post("https://provider.test/fail").mock(return_value=httpx.Response(422, json={"error": "bad"}))
        respx_mock.get("https://provider.test/down").mock(side_effect=httpx.ConnectError("connection refused"))

        assert await request_provider_json("POST", "https://provider.test/ok", headers={}, json_body={}) == {"url": "x"}
        assert await request_provider_json("DELETE", "https://provider.test/empty", headers={}) == {}
        with pytest.raises(BillingProviderError, match="422"):
            await request_provider_json("POST", "https://provider.test/fail", headers={}, json_body={})
        with pytest.raises(BillingProviderError, match="connection refused"):
            await request_provider_json("GET", "https://provider.test/down", headers={})
