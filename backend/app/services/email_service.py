import html
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING, Any, Protocol
from urllib.parse import quote

import httpx

from app.config.settings import Settings
from app.emails.contents import EmailContent
from app.emails.renderer import DEFAULT_LOCALE, EmailRenderer
from app.models.user import User

if TYPE_CHECKING:
    from app.services.notification_service import NotificationEmail

EMAIL_LOGGER_NAME = "saaskit.email"
logger = logging.getLogger(EMAIL_LOGGER_NAME)

EMAIL_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "emails"
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


@lru_cache
def _load_template(file_name: str) -> Template:
    return Template((EMAIL_TEMPLATES_DIR / file_name).read_text(encoding="utf-8"))


def render_email_template(name: str, **values: str) -> tuple[str, str]:
    """Render the HTML and text bodies of a named email template."""
    escaped_values = {key: html.escape(value, quote=True) for key, value in values.items()}
    html_body = _load_template(f"{name}.html").substitute(escaped_values)
    text_body = _load_template(f"{name}.txt").substitute(values)
    return html_body, text_body


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
    """Service for sending transactional emails from templates."""

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

    async def send_verification_email(self, user: User, token: str) -> None:
        """Send the email address verification link."""
        await self._send_template(
            "verify",
            to=user.email,
            subject=f"Confirm your email for {self.settings.BRAND_NAME}",
            link=f"{self.settings.APP_URL}/verify-email?token={quote(token)}",
        )

    async def send_password_reset_email(self, user: User, token: str) -> None:
        """Send the password reset link."""
        await self._send_template(
            "reset",
            to=user.email,
            subject=f"Reset your {self.settings.BRAND_NAME} password",
            link=f"{self.settings.APP_URL}/reset-password?token={quote(token)}",
        )

    async def send_invitation_email(self, *, email: str, organization_name: str, inviter_name: str, token: str) -> None:
        """Send an organization invitation link."""
        await self._send_template(
            "invitation",
            to=email,
            subject=f"{inviter_name} invited you to join {organization_name} on {self.settings.BRAND_NAME}",
            link=f"{self.settings.APP_URL}/invite/{quote(token)}",
            organization_name=organization_name,
            inviter_name=inviter_name,
        )

    async def send_notification_email(self, email: "NotificationEmail") -> None:
        """Send a notification email."""
        await self._send_template(
            "notification",
            to=email.to,
            subject=email.title,
            title=email.title,
            body=email.body,
            link=f"{self.settings.APP_URL}{email.link or '/app'}",
            settings_link=f"{self.settings.APP_URL}/notifications",
        )

    async def _send_template(self, template_name: str, *, to: str, subject: str, **values: str) -> None:
        try:
            html_body, text_body = render_email_template(template_name, brand_name=self.settings.BRAND_NAME, **values)
            await self.sender.send(EmailMessage(to=to, subject=subject, html=html_body, text=text_body))
        except Exception:
            logger.exception("Failed to send email %r to %s", subject, to)
