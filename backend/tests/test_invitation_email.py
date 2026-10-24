from app.config.settings import Settings
from app.emails.contents import InvitationEmailContent
from app.services.email_service import EmailMessage, EmailService
from tests.fakes import InMemoryEmailSender

INVITE_LINK = "http://testserver/invite/token-123"


class FailingEmailSender:
    def __init__(self) -> None:
        self.attempts = 0

    async def send(self, message: EmailMessage) -> None:
        self.attempts += 1
        raise RuntimeError("email provider is down")


async def test_invitation_email_contains_link_and_escaped_names(settings: Settings) -> None:
    sender = InMemoryEmailSender()
    content = InvitationEmailContent(link=INVITE_LINK, organization_name="Rocket <Labs>", inviter_name="Olivia")

    await EmailService(sender, settings).send("new.person@example.com", content)

    [message] = sender.sent
    assert message.to == "new.person@example.com"
    assert "Olivia" in message.subject
    assert INVITE_LINK in message.text
    assert f'href="{INVITE_LINK}"' in message.html
    assert "Rocket <Labs>" in message.text
    assert "Rocket &lt;Labs&gt;" in message.html
    assert "<Labs>" not in message.html


async def test_invitation_email_failure_is_swallowed(settings: Settings) -> None:
    sender = FailingEmailSender()
    content = InvitationEmailContent(link=INVITE_LINK, organization_name="Rocket Labs", inviter_name="Olivia")

    await EmailService(sender, settings).send("new.person@example.com", content)

    assert sender.attempts == 1
