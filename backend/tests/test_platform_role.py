import uuid

import pytest

from app.models.enums import PlatformRole
from app.utils.dependencies import require_platform_role
from app.utils.exceptions import BusinessError
from app.utils.security import AccessTokenClaims
from tests.factories import auth_headers, create_user


async def test_allowed_role_passes(db_session) -> None:
    admin = await create_user(db_session, email="role-admin@example.com", platform_role=PlatformRole.ADMIN)
    staff_dependency = require_platform_role(PlatformRole.ADMIN, PlatformRole.SUPERADMIN)

    resolved_user = await staff_dependency(claims=AccessTokenClaims(user_id=admin.id, impersonated_by=None), user=admin)

    assert resolved_user is admin


async def test_missing_role_is_forbidden(db_session) -> None:
    regular_user = await create_user(db_session, email="role-user@example.com")
    superadmin_dependency = require_platform_role(PlatformRole.SUPERADMIN)

    with pytest.raises(BusinessError) as raised:
        await superadmin_dependency(
            claims=AccessTokenClaims(user_id=regular_user.id, impersonated_by=None), user=regular_user
        )

    assert raised.value.code == "forbidden"
    assert raised.value.status_code == 403


async def test_impersonated_session_is_forbidden_even_for_staff_roles(db_session) -> None:
    impersonated_admin = await create_user(
        db_session, email="role-impersonated@example.com", platform_role=PlatformRole.ADMIN
    )
    staff_dependency = require_platform_role(PlatformRole.ADMIN, PlatformRole.SUPERADMIN)

    with pytest.raises(BusinessError) as raised:
        await staff_dependency(
            claims=AccessTokenClaims(user_id=impersonated_admin.id, impersonated_by=uuid.uuid4()),
            user=impersonated_admin,
        )

    assert raised.value.code == "forbidden"


async def test_me_reports_impersonator_from_claims(client, db_session, settings) -> None:
    superadmin = await create_user(db_session, email="me-super@example.com", platform_role=PlatformRole.SUPERADMIN)
    target = await create_user(db_session, email="me-target@example.com")

    impersonated = await client.get(
        "/api/me", headers=await auth_headers(target, settings=settings, impersonated_by=superadmin.id)
    )
    regular = await client.get("/api/me", headers=await auth_headers(target, settings=settings))

    assert impersonated.status_code == 200, impersonated.text
    assert impersonated.json()["user"]["id"] == str(target.id)
    assert impersonated.json()["impersonated_by"] == str(superadmin.id)
    assert regular.json()["impersonated_by"] is None
