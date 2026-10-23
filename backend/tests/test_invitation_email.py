from app.config.settings import Settings
from app.services.email_service import EmailMessage, EmailService
from tests.fakes import InMemoryEmailSender


class FailingEmailSender:
    def __init__(self) -> None:
        self.attempts = 0

    async def send(self, message: EmailMessage) -> None:
        self.attempts += 1
        raise RuntimeError("email provider is down")


async def test_invitation_email_contains_link_and_escaped_names(settings: Settings) -> None:
    sender = InMemoryEmailSender()

    await EmailService(sender, settings).send_invitation_email(
        email="new.person@example.com", organization_name="Rocket <Labs>", inviter_name="Olivia", token="token-123"
    )

    assert len(sender.sent) == 1
    message = sender.sent[0]
    assert message.to == "new.person@example.com"
    assert "Olivia" in message.subject
    assert "http://testserver/invite/token-123" in message.text
    assert "http://testserver/invite/token-123" in message.html
    assert "Rocket <Labs>" in message.text
    assert "Rocket &lt;Labs&gt;" in message.html
    assert "<Labs>" not in message.html


async def test_invitation_email_failure_is_swallowed(settings: Settings) -> None:
    sender = FailingEmailSender()

    await EmailService(sender, settings).send_invitation_email(
        email="new.person@example.com", organization_name="Rocket Labs", inviter_name="Olivia", token="token-123"
    )

    assert sender.attempts == 1
