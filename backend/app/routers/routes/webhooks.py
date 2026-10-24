from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.schemas.billing import WebhookAcknowledgement
from app.services.billing.billing_service import BillingService
from app.services.billing.providers.base import PaymentProvider, WebhookPayloadError, WebhookSignatureError
from app.utils.dependencies import AppSettings, DbSession, get_payment_provider
from app.utils.exceptions import BusinessError, not_found

router = APIRouter()

ActivePaymentProvider = Annotated[PaymentProvider | None, Depends(get_payment_provider)]


@router.post(
    "/billing/{provider_name}",
    response_model=WebhookAcknowledgement,
    responses={500: {"model": WebhookAcknowledgement}},
)
async def receive_billing_webhook(
    provider_name: str,
    request: Request,
    db: DbSession,
    settings: AppSettings,
    provider: ActivePaymentProvider,
) -> JSONResponse:
    """Receive and process a payment provider webhook."""
    if provider is None or provider.name != provider_name:
        raise not_found("Billing provider")
    raw_body = await request.body()
    try:
        event = provider.parse_webhook(raw_body, request.headers)
    except (WebhookSignatureError, WebhookPayloadError) as error:
        raise BusinessError("invalid_webhook", str(error), status_code=400) from error

    outcome = await BillingService(db, settings, provider).process_webhook_event(event)
    status_code = 500 if outcome == "failed" else 200
    return JSONResponse({"status": outcome}, status_code=status_code)
