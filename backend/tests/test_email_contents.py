import dataclasses

import pytest

from app.emails.contents import (
    EmailCategory,
    InvitationEmailContent,
    NotificationEmailContent,
    PasswordResetEmailContent,
    VerifyEmailContent,
)
from app.emails.links import AppLinks
from tests.conftest import make_settings


def test_subjects() -> None:
    assert VerifyEmailContent(link="x").subject("Acme") == "Confirm your email for Acme"
    assert PasswordResetEmailContent(link="x").subject("Acme") == "Reset your Acme password"
    invitation = InvitationEmailContent(link="x", organization_name="Rocket Labs", inviter_name="Olivia")
    assert invitation.subject("Acme") == "Olivia invited you to join Rocket Labs on Acme"
    assert NotificationEmailContent(title="Jo joined", body="").subject("Acme") == "Jo joined"


def test_categories_and_templates() -> None:
    assert VerifyEmailContent.category is EmailCategory.TRANSACTIONAL
    assert PasswordResetEmailContent.category is EmailCategory.TRANSACTIONAL
    assert InvitationEmailContent.category is EmailCategory.TRANSACTIONAL
    assert NotificationEmailContent.category is EmailCategory.NOTIFICATION
    assert [
        VerifyEmailContent.template_name,
        PasswordResetEmailContent.template_name,
        InvitationEmailContent.template_name,
        NotificationEmailContent.template_name,
    ] == ["verify", "reset", "invitation", "notification"]


def test_contents_are_frozen_and_class_attributes_are_not_fields() -> None:
    content = VerifyEmailContent(link="x")
    with pytest.raises(dataclasses.FrozenInstanceError):
        content.link = "y"  # type: ignore[misc]
    assert dataclasses.asdict(content) == {"link": "x"}


def test_notification_path_defaults_to_app() -> None:
    assert NotificationEmailContent(title="Hi", body="").path == "/app"


def test_app_links_match_frontend_routes_and_quote_tokens() -> None:
    links = AppLinks(make_settings(APP_URL="https://app.example.com"))
    assert links.verify_email("abc-123") == "https://app.example.com/verify-email?token=abc-123"
    assert links.reset_password("a b") == "https://app.example.com/reset-password?token=a%20b"
    assert links.invitation("a b") == "https://app.example.com/invite/a%20b"
