from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.oauth_account import GOOGLE_PROVIDER
from app.models.user import User
from app.repositories.oauth_account import OAuthAccountRepository
from app.schemas.users import UserResponse
from app.utils.exceptions import BusinessError
from app.utils.security import hash_password, verify_password

if TYPE_CHECKING:
    from app.services.file_storage import ObjectStorage


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.oauth_accounts = OAuthAccountRepository(session)

    async def build_response(self, user: User, *, storage: "ObjectStorage | None" = None) -> UserResponse:
        google_linked = await self.oauth_accounts.has_provider(user.id, GOOGLE_PROVIDER)
        return UserResponse.from_user(user, storage=storage, google_linked=google_linked)

    async def update_profile(self, user: User, *, full_name: str) -> User:
        user.full_name = full_name.strip()
        await self.session.commit()
        return user

    async def change_password(self, user: User, *, current_password: str | None, new_password: str) -> None:
        if user.password_hash is not None and (
            not current_password or not verify_password(current_password, user.password_hash)
        ):
            raise BusinessError("invalid_credentials", "Current password is incorrect", status_code=400)
        user.password_hash = hash_password(new_password)
        await self.session.commit()
