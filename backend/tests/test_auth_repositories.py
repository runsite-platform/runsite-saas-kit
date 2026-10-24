import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_token import AuthToken
from app.constants.enums import AuthTokenKind
from app.models.oauth_account import OAuthAccount
from app.models.user import User
from app.repositories.auth_token import AuthTokenRepository
from app.repositories.oauth_account import OAuthAccountRepository
from app.repositories.user import UserRepository
from app.utils.security import hash_token, utc_now


async def add_user(db_session: AsyncSession, email: str = "ann@example.com") -> User:
    return await UserRepository(db_session).add(User(email=email, full_name="Ann"))


async def add_refresh_token(db_session: AsyncSession, user: User, raw_token: str, family_id: uuid.UUID) -> AuthToken:
    token = AuthToken(
        user_id=user.id,
        kind=AuthTokenKind.REFRESH,
        token_hash=hash_token(raw_token),
        family_id=family_id,
        expires_at=utc_now() + timedelta(days=1),
        used_at=None,
    )
    return await AuthTokenRepository(db_session).add(token)


async def test_get_by_email_is_case_insensitive(db_session: AsyncSession) -> None:
    user = await add_user(db_session)
    found = await UserRepository(db_session).get_by_email("  ANN@example.com ")
    assert found is not None
    assert found.id == user.id


async def test_oauth_account_lookup(db_session: AsyncSession) -> None:
    user = await add_user(db_session)
    repository = OAuthAccountRepository(db_session)
    assert not await repository.has_provider(user.id, "google")
    await repository.add(OAuthAccount(user_id=user.id, provider="google", provider_account_id="sub-1"))
    found = await repository.get_by_provider_account("google", "sub-1")
    assert found is not None
    assert found.user_id == user.id
    assert await repository.has_provider(user.id, "google")


async def test_get_by_hash_filters_by_kind(db_session: AsyncSession) -> None:
    user = await add_user(db_session)
    await add_refresh_token(db_session, user, "raw-token", uuid.uuid4())
    repository = AuthTokenRepository(db_session)
    assert await repository.get_by_hash(hash_token("raw-token"), AuthTokenKind.REFRESH) is not None
    assert await repository.get_by_hash(hash_token("raw-token"), AuthTokenKind.PASSWORD_RESET) is None


async def test_revoke_family_marks_only_that_family(db_session: AsyncSession) -> None:
    user = await add_user(db_session)
    family_id = uuid.uuid4()
    first = await add_refresh_token(db_session, user, "first", family_id)
    second = await add_refresh_token(db_session, user, "second", family_id)
    other = await add_refresh_token(db_session, user, "other", uuid.uuid4())

    await AuthTokenRepository(db_session).revoke_family(family_id, utc_now())

    assert first.used_at is not None
    assert second.used_at is not None
    assert other.used_at is None


async def test_revoke_for_user_marks_every_token_of_kind(db_session: AsyncSession) -> None:
    user = await add_user(db_session)
    first = await add_refresh_token(db_session, user, "first", uuid.uuid4())
    second = await add_refresh_token(db_session, user, "second", uuid.uuid4())

    await AuthTokenRepository(db_session).revoke_for_user(user.id, AuthTokenKind.REFRESH, utc_now())

    assert first.used_at is not None
    assert second.used_at is not None
