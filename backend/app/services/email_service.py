import html
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING, Protocol
from urllib.parse import quote

import httpx

from app.config.settings import Settings
from app.models.user import User

if TYPE_CHECKING:
    from app.services.notification_service import NotificationEmail

EMAIL_LOGGER_NAME = "saaskit.email"
logger = logging.getLogger(EMAIL_LOGGER_NAME)

EMAIL_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "emails"
EMAIL_TIMEOUT_SECONDS = 60.0


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    html: str
    text: str


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None: ...


@lru_cache
def _load_template(file_name: str) -> Template:
    return Template((EMAIL_TEMPLATES_DIR / file_name).read_text(encoding="utf-8"))


def render_email_template(name: str, **values: str) -> tuple[str, str]:
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
        payload = {
            "from": self.settings.EMAIL_FROM,
            "to": [message.to],
            "subject": message.subject,
            "message": message.html,
            "text": message.text,
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as http_client:
            response = await http_client.post(
                self.settings.EMAIL_API_URL, headers={"Api-Key": self.settings.EMAIL_API_KEY}, json=payload
            )
        response.raise_for_status()


class LoggingEmailSender:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send(self, message: EmailMessage) -> None:
        logger.info("Email not sent (EMAIL_API_KEY is not set): %r to %s", message.subject, message.to)
        if self.settings.DEBUG:
            logger.info("Email text for %s:\n%s", message.to, message.text)


class EmailService:
    def __init__(self, sender: EmailSender, settings: Settings) -> None:
        self.sender = sender
        self.settings = settings

    async def send_verification_email(self, user: User, token: str) -> None:
        await self._send_template(
            "verify",
            to=user.email,
            subject=f"Confirm your email for {self.settings.BRAND_NAME}",
            link=f"{self.settings.APP_URL}/verify-email?token={quote(token)}",
        )

    async def send_password_reset_email(self, user: User, token: str) -> None:
        await self._send_template(
            "reset",
            to=user.email,
            subject=f"Reset your {self.settings.BRAND_NAME} password",
            link=f"{self.settings.APP_URL}/reset-password?token={quote(token)}",
        )

    async def send_invitation_email(self, *, email: str, organization_name: str, inviter_name: str, token: str) -> None:
        await self._send_template(
            "invitation",
            to=email,
            subject=f"{inviter_name} invited you to join {organization_name} on {self.settings.BRAND_NAME}",
            link=f"{self.settings.APP_URL}/invite/{quote(token)}",
            organization_name=organization_name,
            inviter_name=inviter_name,
        )

    async def send_notification_email(self, email: "NotificationEmail") -> None:
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
