from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.constants.enums import PlatformRole
from app.utils.security import decode_access_token, verify_password
from tests.conftest import make_settings
from tests.factories import auth_headers, create_user
from tests.fakes import InMemoryEmailSender


def test_make_settings_accepts_overrides_of_defaults() -> None:
    overridden = make_settings(EMAIL_API_KEY="key", GOOGLE_CLIENT_ID="client-id", REQUIRE_EMAIL_VERIFICATION=True)
    assert overridden.EMAIL_API_KEY == "key"
    assert overridden.GOOGLE_CLIENT_ID == "client-id"
    assert overridden.REQUIRE_EMAIL_VERIFICATION is True


async def test_create_user_defaults(db_session: AsyncSession) -> None:
    user = await create_user(db_session)
    assert user.id is not None
    assert user.email.endswith("@example.com")
    assert user.email == user.email.lower()
    assert user.platform_role == PlatformRole.USER
    assert user.is_email_verified is True
    assert user.password_hash is not None
    assert verify_password("password123", user.password_hash)


async def test_create_user_without_password(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="Google@Example.com", password=None)
    assert user.email == "google@example.com"
    assert user.password_hash is None


async def test_auth_headers_carry_valid_token(db_session: AsyncSession, settings: Settings) -> None:
    user = await create_user(db_session)
    headers = await auth_headers(user, settings=settings)
    scheme, token = headers["Authorization"].split(" ")
    assert scheme == "Bearer"
    assert decode_access_token(token, secret=settings.JWT_SECRET).user_id == user.id


def test_email_outbox_fixture_replaces_sender(email_outbox: InMemoryEmailSender) -> None:
    assert email_outbox.sent == []
