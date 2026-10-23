from app.models.user import User
from app.utils.repository import SQLAlchemyRepository
from app.utils.security import normalize_email


class UserRepository(SQLAlchemyRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        return await self.get_one(filter_params={"email": normalize_email(email)})
