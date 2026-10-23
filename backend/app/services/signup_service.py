from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.models.enums import NotificationKind, PlatformRole
from app.models.user import User
from app.services.notification_service import NotificationService
from app.services.organization_service import OrganizationService
from app.utils.security import normalize_email


class SignupService:
    """Runs once for every new user. The caller commits."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def complete_signup(self, user: User) -> None:
        superadmin_email = normalize_email(self.settings.SUPERADMIN_EMAIL)
        if superadmin_email and user.email == superadmin_email:
            user.platform_role = PlatformRole.SUPERADMIN
        await self.session.flush()
        await OrganizationService(self.session).create_personal_organization(user)
        await NotificationService(self.session).notify(
            [user],
            kind=NotificationKind.WELCOME,
            title=f"Welcome to {self.settings.BRAND_NAME}",
            body="Your workspace is ready. Invite your team and create your first project.",
            link="/app",
        )
