import shutil
from pathlib import Path

import pytest

from app.emails.contents import (
    EmailContent,
    InvitationEmailContent,
    NotificationEmailContent,
    PasswordResetEmailContent,
    VerifyEmailContent,
)
from app.emails.renderer import EMAIL_TEMPLATES_DIR, EmailRenderer
from tests.conftest import make_settings

APP_URL = "http://testserver"
ALL_CONTENTS: list[EmailContent] = [
    VerifyEmailContent(link=f"{APP_URL}/verify-email?token=verify-123"),
    PasswordResetEmailContent(link=f"{APP_URL}/reset-password?token=reset-123"),
    InvitationEmailContent(link=f"{APP_URL}/invite/invite-123", organization_name="Rocket Labs", inviter_name="Olivia"),
    NotificationEmailContent(title="Jo joined Rocket Labs", body="Say hello.", path="/app/rocket-labs/members"),
]


def build_renderer(templates_dir: Path = EMAIL_TEMPLATES_DIR) -> EmailRenderer:
    return EmailRenderer(make_settings(APP_URL=APP_URL, BRAND_NAME="Acme"), templates_dir=templates_dir)


def main_link(content: EmailContent) -> str:
    if isinstance(content, NotificationEmailContent):
        return f"{APP_URL}{content.path}"
    return content.link  # type: ignore[attr-defined]


@pytest.mark.parametrize("content", ALL_CONTENTS, ids=lambda content: content.template_name)
def test_every_email_renders_html_and_text(content: EmailContent) -> None:
    rendered = build_renderer().render(content)

    link = main_link(content)
    assert rendered.subject
    assert f'href="{link}"' in rendered.html
    assert link in rendered.text
    assert "<" not in rendered.text
    assert "font-size" not in rendered.text
    assert "Acme" in rendered.text
    assert rendered.html.startswith("<!doctype html>")


def test_fallback_link_and_preheader_stay_out_of_text() -> None:
    rendered = build_renderer().render(VerifyEmailContent(link=f"{APP_URL}/verify-email?token=verify-123"))

    assert "Or paste this link" in rendered.html
    assert "Or paste this link" not in rendered.text
    assert rendered.text.count(f"{APP_URL}/verify-email?token=verify-123") == 1


def test_notification_links_to_settings() -> None:
    rendered = build_renderer().render(NotificationEmailContent(title="Hi", body="Line one\nLine two"))

    assert f"Manage notifications: {APP_URL}/notifications" in rendered.text
    assert f"{APP_URL}/app" in rendered.text
    assert rendered.subject == "Hi"


def test_invitation_names_are_escaped_in_html() -> None:
    content = InvitationEmailContent(
        link=f"{APP_URL}/invite/invite-123", organization_name="Rocket <Labs>", inviter_name="<script>x</script>"
    )

    rendered = build_renderer().render(content)

    assert "<script>" not in rendered.html
    assert "&lt;script&gt;x&lt;/script&gt;" in rendered.html
    assert "Rocket &lt;Labs&gt;" in rendered.html
    assert "<script>x</script> invited you to join Rocket <Labs>." in rendered.text


def test_query_string_ampersand_is_escaped_in_html_and_plain_in_text() -> None:
    rendered = build_renderer().render(VerifyEmailContent(link=f"{APP_URL}/verify-email?token=a&next=b"))

    assert f"{APP_URL}/verify-email?token=a&amp;next=b" in rendered.html
    assert f"{APP_URL}/verify-email?token=a&next=b" in rendered.text


def test_base_template_is_used_when_locale_has_no_override() -> None:
    rendered = build_renderer().render(VerifyEmailContent(link="http://testserver/v"), locale="uk")

    assert '<html lang="uk">' in rendered.html
    assert "Confirm your email" in rendered.text


def test_locale_override_is_picked_up(tmp_path: Path) -> None:
    for template_name in ("layout.html", "components.html", "verify.html"):
        shutil.copy(EMAIL_TEMPLATES_DIR / template_name, tmp_path / template_name)
    (tmp_path / "verify.uk.html").write_text(
        '{% extends "layout.html" %}{% block content %}<p>UK_OVERRIDE {{ link }}</p>{% endblock %}',
        encoding="utf-8",
    )
    renderer = build_renderer(templates_dir=tmp_path)
    content = VerifyEmailContent(link="http://testserver/v")

    assert "UK_OVERRIDE http://testserver/v" in renderer.render(content, locale="uk").text
    assert "UK_OVERRIDE" not in renderer.render(content).text
