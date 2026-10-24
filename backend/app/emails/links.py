from urllib.parse import quote

from app.config.settings import Settings


class AppLinks:
    """Frontend URLs that emails link to."""

    def __init__(self, settings: Settings) -> None:
        self.app_url = settings.APP_URL

    def verify_email(self, token: str) -> str:
        return f"{self.app_url}/verify-email?token={quote(token)}"

    def reset_password(self, token: str) -> str:
        return f"{self.app_url}/reset-password?token={quote(token)}"

    def invitation(self, token: str) -> str:
        return f"{self.app_url}/invite/{quote(token)}"
