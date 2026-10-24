from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Protocol

DEFAULT_NOTIFICATION_PATH = "/app"


class EmailCategory(StrEnum):
    TRANSACTIONAL = "transactional"
    NOTIFICATION = "notification"


class EmailContent(Protocol):
    """Typed data of one email. Implementations are frozen dataclasses; their fields become template variables."""

    template_name: ClassVar[str]
    category: ClassVar[EmailCategory]

    def subject(self, brand_name: str) -> str: ...


@dataclass(frozen=True)
class VerifyEmailContent:
    template_name: ClassVar[str] = "verify"
    category: ClassVar[EmailCategory] = EmailCategory.TRANSACTIONAL

    link: str

    def subject(self, brand_name: str) -> str:
        return f"Confirm your email for {brand_name}"


@dataclass(frozen=True)
class PasswordResetEmailContent:
    template_name: ClassVar[str] = "reset"
    category: ClassVar[EmailCategory] = EmailCategory.TRANSACTIONAL

    link: str

    def subject(self, brand_name: str) -> str:
        return f"Reset your {brand_name} password"


@dataclass(frozen=True)
class InvitationEmailContent:
    template_name: ClassVar[str] = "invitation"
    category: ClassVar[EmailCategory] = EmailCategory.TRANSACTIONAL

    link: str
    organization_name: str
    inviter_name: str

    def subject(self, brand_name: str) -> str:
        return f"{self.inviter_name} invited you to join {self.organization_name} on {brand_name}"


@dataclass(frozen=True)
class NotificationEmailContent:
    """Notification email. `path` is relative to APP_URL."""

    template_name: ClassVar[str] = "notification"
    category: ClassVar[EmailCategory] = EmailCategory.NOTIFICATION

    title: str
    body: str
    path: str = DEFAULT_NOTIFICATION_PATH

    def subject(self, brand_name: str) -> str:
        return self.title
