import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import User
from app.models.enums import PlatformRole
from app.repositories.admin_query_repository import AdminQueryRepository

logger = logging.getLogger(__name__)


class SuperadminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.queries = AdminQueryRepository(session)

    async def promote_by_email(self, email: str) -> User | None:
        user = await self.queries.get_user_by_email(email)
        if user is None:
            return None
        if user.platform_role != PlatformRole.SUPERADMIN:
            user.platform_role = PlatformRole.SUPERADMIN
            await self.session.commit()
            logger.info("User %s promoted to superadmin", user.id)
        return user


async def promote_superadmin_on_startup(session_maker: async_sessionmaker[AsyncSession], email: str) -> None:
    if not email.strip():
        return
    try:
        async with session_maker() as session:
            promoted_user = await SuperadminService(session).promote_by_email(email)
    except Exception:
        logger.exception("Could not promote SUPERADMIN_EMAIL at startup")
        return
    if promoted_user is None:
        logger.info("SUPERADMIN_EMAIL has no account yet; it is promoted when that user registers")
