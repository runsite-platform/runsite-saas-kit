from typing import Any

import httpx

from app.services.billing.providers.base import BillingProviderError

PROVIDER_TIMEOUT_SECONDS = 30.0
ERROR_BODY_PREVIEW_LENGTH = 500


async def request_provider_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=PROVIDER_TIMEOUT_SECONDS) as http_client:
            response = await http_client.request(method, url, headers=headers, json=json_body)
    except httpx.HTTPError as error:
        raise BillingProviderError(f"{method} {url} failed: {error}") from error

    if response.status_code >= 400:
        preview = response.text[:ERROR_BODY_PREVIEW_LENGTH]
        raise BillingProviderError(f"{method} {url} returned {response.status_code}: {preview}")
    if not response.content:
        return {}
    try:
        body = response.json()
    except ValueError as error:
        raise BillingProviderError(f"{method} {url} returned a non-JSON body") from error
    return body if isinstance(body, dict) else {}
