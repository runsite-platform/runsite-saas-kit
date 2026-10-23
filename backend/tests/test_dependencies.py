import uuid

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.utils.dependencies import get_access_claims, get_current_user, require_verified_email
from app.utils.exceptions import BusinessError
from app.utils.security import AccessTokenClaims, create_access_token
from tests.conftest import make_settings
from tests.factories import create_user


async def test_access_claims_require_credentials(settings: Settings) -> None:
    with pytest.raises(BusinessError) as error_info:
        await get_access_claims(settings, None)
    assert error_info.value.code == "not_authenticated"


async def test_access_claims_decode_bearer_token(settings: Settings) -> None:
    user_id = uuid.uuid4()
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=create_access_token(user_id, secret=settings.JWT_SECRET)
    )
    claims = await get_access_claims(settings, credentials)
    assert claims.user_id == user_id


async def test_current_user_missing_user_is_not_authenticated(db_session: AsyncSession) -> None:
    with pytest.raises(BusinessError) as error_info:
        await get_current_user(AccessTokenClaims(user_id=uuid.uuid4(), impersonated_by=None), db_session)
    assert error_info.value.status_code == 401


async def test_current_user_blocked(db_session: AsyncSession) -> None:
    user = await create_user(db_session, is_blocked=True)
    with pytest.raises(BusinessError) as error_info:
        await get_current_user(AccessTokenClaims(user_id=user.id, impersonated_by=None), db_session)
    assert error_info.value.code == "user_blocked"
    assert error_info.value.status_code == 403


async def test_current_user_returns_user(db_session: AsyncSession) -> None:
    user = await create_user(db_session)
    loaded = await get_current_user(AccessTokenClaims(user_id=user.id, impersonated_by=None), db_session)
    assert loaded.id == user.id


async def test_require_verified_email(db_session: AsyncSession) -> None:
    unverified = await create_user(db_session, is_email_verified=False)
    verified = await create_user(db_session, is_email_verified=True)
    strict_settings = make_settings(REQUIRE_EMAIL_VERIFICATION=True)
    relaxed_settings = make_settings(REQUIRE_EMAIL_VERIFICATION=False)

    with pytest.raises(BusinessError) as error_info:
        await require_verified_email(unverified, strict_settings)
    assert error_info.value.code == "email_not_verified"
    assert error_info.value.status_code == 403

    assert await require_verified_email(verified, strict_settings) is verified
    assert await require_verified_email(unverified, relaxed_settings) is unverified
