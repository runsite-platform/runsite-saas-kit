import json
import logging

import httpx
import pytest
import respx

from app.config.settings import Settings
from app.models.user import User
from app.services.email_service import (
    EMAIL_LOGGER_NAME,
    EmailMessage,
    EmailService,
    LoggingEmailSender,
    RunsiteEmailSender,
    render_email_template,
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


def build_user() -> User:
    return User(email="ann@example.com", full_name="Ann")


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
            await service.send_verification_email(build_user(), "token-123")
        finally:
            email_logger.removeHandler(caplog.handler)

    assert route.call_count == 1
    assert any("Failed to send email" in record.getMessage() for record in caplog.records)


async def test_verification_email_contains_link(email_settings: Settings) -> None:
    sender = RecordingSender()
    await EmailService(sender, email_settings).send_verification_email(build_user(), "token-123")
    [message] = sender.sent
    assert message.to == "ann@example.com"
    assert "Acme" in message.subject
    assert "http://testserver/verify-email?token=token-123" in message.text
    assert "http://testserver/verify-email?token=token-123" in message.html


async def test_password_reset_email_contains_link(email_settings: Settings) -> None:
    sender = RecordingSender()
    await EmailService(sender, email_settings).send_password_reset_email(build_user(), "reset-456")
    [message] = sender.sent
    assert "http://testserver/reset-password?token=reset-456" in message.text


async def test_logging_sender_does_not_raise(email_settings: Settings) -> None:
    message = EmailMessage(to="ann@example.com", subject="Hello", html="<p>Hi</p>", text="Hi")
    await LoggingEmailSender(email_settings).send(message)


def test_render_escapes_html_values() -> None:
    html, text = render_email_template("verify", brand_name="<Acme>", link="http://x.test/?a=1&b=2")
    assert "&lt;Acme&gt;" in html
    assert "<Acme>" in text
    assert "http://x.test/?a=1&amp;b=2" in html
