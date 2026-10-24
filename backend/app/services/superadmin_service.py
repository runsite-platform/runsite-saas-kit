import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import User
from app.constants.enums import PlatformRole
from app.repositories.admin_query_repository import AdminQueryRepository

logger = logging.getLogger(__name__)


class SuperadminService:
    """Service for granting the superadmin role."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.queries = AdminQueryRepository(db)

    async def promote_by_email(self, email: str) -> User | None:
        """Promote the user with the email to superadmin, if they exist."""
        user = await self.queries.get_user_by_email(email)
        if user is None:
            return None
        if user.platform_role != PlatformRole.SUPERADMIN:
            user.platform_role = PlatformRole.SUPERADMIN
            await self.db.commit()
            logger.info("User %s promoted to superadmin", user.id)
        return user


async def promote_superadmin_on_startup(session_maker: async_sessionmaker[AsyncSession], email: str) -> None:
    """Promote SUPERADMIN_EMAIL to superadmin at startup, logging errors."""
    if not email.strip():
        return
    try:
        async with session_maker() as db:
            promoted_user = await SuperadminService(db).promote_by_email(email)
    except Exception:
        logger.exception("Could not promote SUPERADMIN_EMAIL at startup")
        return
    if promoted_user is None:
        logger.info("SUPERADMIN_EMAIL has no account yet; it is promoted when that user registers")
