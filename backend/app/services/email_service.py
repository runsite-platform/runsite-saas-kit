import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.config.settings import Settings
from app.emails.contents import EmailContent
from app.emails.renderer import DEFAULT_LOCALE, EmailRenderer

EMAIL_LOGGER_NAME = "saaskit.email"
logger = logging.getLogger(EMAIL_LOGGER_NAME)

EMAIL_TIMEOUT_SECONDS = 60.0


@dataclass(frozen=True)
class EmailMessage:
    """Rendered email ready to be sent."""

    to: str
    subject: str
    html: str
    text: str
    reply_to: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


class EmailSender(Protocol):
    """Protocol for email delivery backends."""

    async def send(self, message: EmailMessage) -> None:
        """Send the email message."""
        ...


class EmailQueue(Protocol):
    """Queue that sends emails outside the request."""

    def enqueue(self, to: str, content: EmailContent) -> None:
        """Queue an email for sending."""
        ...


class RunsiteEmailSender:
    """Sends through the Runsite email API. Never retries: a retried send could deliver twice."""

    def __init__(self, settings: Settings, timeout_seconds: float = EMAIL_TIMEOUT_SECONDS) -> None:
        self.settings = settings
        self.timeout_seconds = timeout_seconds

    async def send(self, message: EmailMessage) -> None:
        """Post the email to the Runsite email API."""
        payload: dict[str, Any] = {
            "from": self.settings.EMAIL_FROM,
            "to": [message.to],
            "subject": message.subject,
            "message": message.html,
            "text": message.text,
        }
        if message.reply_to:
            payload["reply_to"] = [message.reply_to]
        if message.headers:
            payload["headers"] = message.headers
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as http_client:
            response = await http_client.post(
                self.settings.EMAIL_API_URL, headers={"Api-Key": self.settings.EMAIL_API_KEY}, json=payload
            )
        response.raise_for_status()


class LoggingEmailSender:
    """Email sender that logs messages instead of sending them."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send(self, message: EmailMessage) -> None:
        """Log the email instead of sending it."""
        logger.info("Email not sent (EMAIL_API_KEY is not set): %r to %s", message.subject, message.to)
        if self.settings.DEBUG:
            logger.info("Email text for %s:\n%s", message.to, message.text)


class EmailService:
    """Renders email contents and sends them."""

    def __init__(self, sender: EmailSender, settings: Settings, renderer: EmailRenderer | None = None) -> None:
        self.sender = sender
        self.settings = settings
        self.renderer = renderer or EmailRenderer(settings)

    async def send(self, to: str, content: EmailContent, *, locale: str = DEFAULT_LOCALE) -> None:
        """Render and send an email. Never raises: failures are logged."""
        try:
            rendered = self.renderer.render(content, locale=locale)
            await self.sender.send(
                EmailMessage(
                    to=to,
                    subject=rendered.subject,
                    html=rendered.html,
                    text=rendered.text,
                    reply_to=self.settings.EMAIL_REPLY_TO or None,
                )
            )
        except Exception:
            logger.exception("Failed to send email %r (%s) to %s", content.template_name, content.category.value, to)
