import json
import logging
from dataclasses import dataclass
from typing import ClassVar

import httpx
import pytest
import respx

from app.config.logger import LOGGER_NAME
from app.config.settings import Settings
from app.emails.contents import EmailCategory, PasswordResetEmailContent, VerifyEmailContent
from app.services.email_service import (
    EMAIL_LOGGER_NAME,
    EmailMessage,
    EmailService,
    LoggingEmailSender,
    RunsiteEmailSender,
)
from tests.conftest import make_settings

EMAIL_API_URL = "https://api.runsite.app/emails"


class RecordingSender:
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


@pytest.fixture
def email_settings() -> Settings:
    return make_settings(EMAIL_API_KEY="re_test_key", EMAIL_FROM="Acme <noreply@acme.test>", BRAND_NAME="Acme")


async def test_runsite_sender_posts_expected_request(email_settings: Settings) -> None:
    message = EmailMessage(to="ann@example.com", subject="Hello", html="<p>Hi</p>", text="Hi")
    with respx.mock(assert_all_called=True) as email_api:
        route = email_api.post(EMAIL_API_URL).mock(
            return_value=httpx.Response(200, json={"id": "4f1c2a40-0000-0000-0000-000000000000", "status": "sent"})
        )
        await RunsiteEmailSender(email_settings).send(message)

    request = route.calls.last.request
    assert request.headers["Api-Key"] == "re_test_key"
    assert json.loads(request.content) == {
        "from": "Acme <noreply@acme.test>",
        "to": ["ann@example.com"],
        "subject": "Hello",
        "message": "<p>Hi</p>",
        "text": "Hi",
    }


async def test_runsite_sender_raises_on_error_status(email_settings: Settings) -> None:
    message = EmailMessage(to="ann@example.com", subject="Hello", html="<p>Hi</p>", text="Hi")
    with respx.mock(assert_all_called=True) as email_api:
        email_api.post(EMAIL_API_URL).mock(return_value=httpx.Response(400, json={"detail": "sandbox"}))
        with pytest.raises(httpx.HTTPStatusError):
            await RunsiteEmailSender(email_settings).send(message)


async def test_email_service_swallows_sandbox_400_and_logs(
    email_settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    service = EmailService(RunsiteEmailSender(email_settings), email_settings)
    with respx.mock(assert_all_called=True) as email_api:
        route = email_api.post(EMAIL_API_URL).mock(
            return_value=httpx.Response(400, json={"detail": "Recipient is not verified in sandbox mode"})
        )
        email_logger = logging.getLogger(EMAIL_LOGGER_NAME)
        email_logger.addHandler(caplog.handler)
        try:
            await service.send("ann@example.com", VerifyEmailContent(link="http://testserver/verify-email?token=t"))
        finally:
            email_logger.removeHandler(caplog.handler)

    assert route.call_count == 1
    assert any("Failed to send email" in record.getMessage() for record in caplog.records)


async def test_logging_sender_does_not_raise(email_settings: Settings) -> None:
    message = EmailMessage(to="ann@example.com", subject="Hello", html="<p>Hi</p>", text="Hi")
    await LoggingEmailSender(email_settings).send(message)


async def test_runsite_sender_adds_reply_to_and_headers_when_set(email_settings: Settings) -> None:
    message = EmailMessage(
        to="ann@example.com",
        subject="Hello",
        html="<p>Hi</p>",
        text="Hi",
        reply_to="support@acme.test",
        headers={"X-Entity-Ref-ID": "42"},
    )
    with respx.mock(assert_all_called=True) as email_api:
        route = email_api.post(EMAIL_API_URL).mock(return_value=httpx.Response(200, json={"status": "sent"}))
        await RunsiteEmailSender(email_settings).send(message)

    payload = json.loads(route.calls.last.request.content)
    assert payload["reply_to"] == ["support@acme.test"]
    assert payload["headers"] == {"X-Entity-Ref-ID": "42"}


async def test_send_renders_verification_email(email_settings: Settings) -> None:
    sender = RecordingSender()
    link = "http://testserver/verify-email?token=token-123"

    await EmailService(sender, email_settings).send("ann@example.com", VerifyEmailContent(link=link))

    [message] = sender.sent
    assert message.to == "ann@example.com"
    assert message.subject == "Confirm your email for Acme"
    assert link in message.text
    assert f'href="{link}"' in message.html
    assert message.reply_to is None
    assert message.headers == {}


async def test_send_renders_password_reset_email(email_settings: Settings) -> None:
    sender = RecordingSender()
    link = "http://testserver/reset-password?token=reset-456"

    await EmailService(sender, email_settings).send("ann@example.com", PasswordResetEmailContent(link=link))

    [message] = sender.sent
    assert message.subject == "Reset your Acme password"
    assert link in message.text


async def test_send_uses_reply_to_setting() -> None:
    sender = RecordingSender()
    settings = make_settings(BRAND_NAME="Acme", EMAIL_REPLY_TO="support@acme.test")

    await EmailService(sender, settings).send("ann@example.com", VerifyEmailContent(link="http://testserver/v"))

    assert sender.sent[0].reply_to == "support@acme.test"


@dataclass(frozen=True)
class MissingTemplateContent:
    template_name: ClassVar[str] = "does-not-exist"
    category: ClassVar[EmailCategory] = EmailCategory.TRANSACTIONAL

    def subject(self, brand_name: str) -> str:
        return "Missing"


async def test_send_logs_render_errors_and_does_not_raise(
    email_settings: Settings, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    sender = RecordingSender()
    app_logger = logging.getLogger(LOGGER_NAME)
    monkeypatch.setattr(app_logger, "propagate", False)
    monkeypatch.setattr(app_logger, "handlers", [caplog.handler])

    await EmailService(sender, email_settings).send("ann@example.com", MissingTemplateContent())

    assert sender.sent == []
    [record] = [record for record in caplog.records if "Failed to send email" in record.getMessage()]
    assert "does-not-exist" in record.getMessage()
    assert "transactional" in record.getMessage()
    assert "ann@example.com" in record.getMessage()
