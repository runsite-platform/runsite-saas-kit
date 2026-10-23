import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PlatformRole
from app.models.oauth_account import GOOGLE_PROVIDER, OAuthAccount
from app.repositories.oauth_account import OAuthAccountRepository
from app.schemas.users import UserResponse
from app.services.signup_service import SignupService
from app.services.user_service import UserService
from app.utils.exceptions import BusinessError
from app.utils.security import verify_password
from tests.conftest import make_settings
from tests.factories import create_user


async def test_build_response_reflects_password_and_google_link(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="ann@example.com", full_name="Ann")
    service = UserService(db_session)

    response = await service.build_response(user)
    assert response.email == "ann@example.com"
    assert response.has_password is True
    assert response.google_linked is False
    assert response.avatar_url is None
    assert response.platform_role == "user"

    await OAuthAccountRepository(db_session).add(
        OAuthAccount(user_id=user.id, provider=GOOGLE_PROVIDER, provider_account_id="sub-1")
    )
    assert (await service.build_response(user)).google_linked is True


async def test_user_response_from_user_defaults(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="oauth@example.com", password=None)
    await db_session.refresh(user)
    response = UserResponse.from_user(user)
    assert response.id == user.id
    assert response.has_password is False
    assert response.google_linked is False
    assert response.avatar_url is None
    assert response.created_at == user.created_at


async def test_update_profile_strips_name(db_session: AsyncSession) -> None:
    user = await create_user(db_session)
    await UserService(db_session).update_profile(user, full_name="  New Name  ")
    assert user.full_name == "New Name"


async def test_change_password_requires_current_password(db_session: AsyncSession) -> None:
    user = await create_user(db_session, password="password123")
    service = UserService(db_session)
    with pytest.raises(BusinessError) as error_info:
        await service.change_password(user, current_password="wrong-password", new_password="newpassword1")
    assert error_info.value.code == "invalid_credentials"
    assert error_info.value.status_code == 400

    await service.change_password(user, current_password="password123", new_password="newpassword1")
    assert verify_password("newpassword1", user.password_hash or "")


async def test_oauth_only_user_sets_password_without_current(db_session: AsyncSession) -> None:
    user = await create_user(db_session, password=None)
    await UserService(db_session).change_password(user, current_password=None, new_password="newpassword1")
    assert verify_password("newpassword1", user.password_hash or "")


async def test_complete_signup_promotes_superadmin_case_insensitive(db_session: AsyncSession) -> None:
    settings = make_settings(SUPERADMIN_EMAIL=" Boss@Example.com ")
    boss = await create_user(db_session, email="boss@example.com")
    regular = await create_user(db_session, email="worker@example.com")

    await SignupService(db_session, settings).complete_signup(boss)
    await SignupService(db_session, settings).complete_signup(regular)

    assert boss.platform_role == PlatformRole.SUPERADMIN
    assert regular.platform_role == PlatformRole.USER


async def test_complete_signup_without_superadmin_setting(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="boss@example.com")
    await SignupService(db_session, make_settings(SUPERADMIN_EMAIL="")).complete_signup(user)
    assert user.platform_role == PlatformRole.USER
