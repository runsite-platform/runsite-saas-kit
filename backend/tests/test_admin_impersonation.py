from jose import jwt

from app.models.enums import PlatformRole
from tests.factories import auth_headers, create_user


async def test_superadmin_grants_and_revokes_admin(client, db_session, settings) -> None:
    superadmin = await create_user(db_session, email="granter@example.com", platform_role=PlatformRole.SUPERADMIN)
    target = await create_user(db_session, email="promoted@example.com")
    headers = await auth_headers(superadmin, settings=settings)

    granted = await client.post(f"/api/admin/users/{target.id}/grant-admin", headers=headers)
    revoked = await client.post(f"/api/admin/users/{target.id}/revoke-admin", headers=headers)

    assert granted.status_code == 200, granted.text
    assert granted.json()["platform_role"] == "admin"
    assert revoked.json()["platform_role"] == "user"


async def test_superadmin_roles_cannot_be_changed(client, db_session, settings) -> None:
    superadmin = await create_user(db_session, email="granter-2@example.com", platform_role=PlatformRole.SUPERADMIN)
    other_superadmin = await create_user(
        db_session, email="other-super@example.com", platform_role=PlatformRole.SUPERADMIN
    )
    headers = await auth_headers(superadmin, settings=settings)

    revoke_other = await client.post(f"/api/admin/users/{other_superadmin.id}/revoke-admin", headers=headers)
    revoke_self = await client.post(f"/api/admin/users/{superadmin.id}/revoke-admin", headers=headers)

    assert revoke_other.status_code == 403
    assert revoke_self.status_code == 403
    assert other_superadmin.platform_role == PlatformRole.SUPERADMIN


async def test_impersonation_issues_a_short_access_token_without_refresh_cookie(client, db_session, settings) -> None:
    superadmin = await create_user(db_session, email="imp-super@example.com", platform_role=PlatformRole.SUPERADMIN)
    target = await create_user(db_session, email="imp-target@example.com")

    response = await client.post(
        f"/api/admin/users/{target.id}/impersonate", headers=await auth_headers(superadmin, settings=settings)
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 1800
    assert "refresh_token" not in response.cookies
    assert "set-cookie" not in response.headers
    claims = jwt.get_unverified_claims(body["access_token"])
    assert claims["sub"] == str(target.id)
    assert claims["imp"] == str(superadmin.id)
    assert claims["exp"] - claims["iat"] == 1800

    me_response = await client.get("/api/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me_response.json()["user"]["id"] == str(target.id)
    assert me_response.json()["impersonated_by"] == str(superadmin.id)


async def test_superadmins_cannot_be_impersonated(client, db_session, settings) -> None:
    superadmin = await create_user(db_session, email="imp-super-2@example.com", platform_role=PlatformRole.SUPERADMIN)
    other_superadmin = await create_user(
        db_session, email="imp-super-3@example.com", platform_role=PlatformRole.SUPERADMIN
    )
    headers = await auth_headers(superadmin, settings=settings)

    other_response = await client.post(f"/api/admin/users/{other_superadmin.id}/impersonate", headers=headers)
    self_response = await client.post(f"/api/admin/users/{superadmin.id}/impersonate", headers=headers)

    assert other_response.status_code == 403
    assert other_response.json()["error"]["code"] == "cannot_impersonate"
    assert self_response.json()["error"]["code"] == "cannot_impersonate"


async def test_blocked_users_cannot_be_impersonated(client, db_session, settings) -> None:
    superadmin = await create_user(db_session, email="imp-super-4@example.com", platform_role=PlatformRole.SUPERADMIN)
    blocked = await create_user(db_session, email="imp-blocked@example.com", is_blocked=True)

    response = await client.post(
        f"/api/admin/users/{blocked.id}/impersonate", headers=await auth_headers(superadmin, settings=settings)
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "cannot_impersonate"


async def test_admins_cannot_impersonate(client, db_session, settings) -> None:
    admin = await create_user(db_session, email="imp-admin@example.com", platform_role=PlatformRole.ADMIN)
    target = await create_user(db_session, email="imp-target-2@example.com")

    response = await client.post(
        f"/api/admin/users/{target.id}/impersonate", headers=await auth_headers(admin, settings=settings)
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_impersonated_session_cannot_use_the_admin_api(client, db_session, settings) -> None:
    superadmin = await create_user(db_session, email="imp-super-5@example.com", platform_role=PlatformRole.SUPERADMIN)
    impersonated_admin = await create_user(
        db_session, email="imp-admin-2@example.com", platform_role=PlatformRole.ADMIN
    )
    superadmin_headers = await auth_headers(superadmin, settings=settings)
    impersonation = await client.post(
        f"/api/admin/users/{impersonated_admin.id}/impersonate", headers=superadmin_headers
    )
    impersonated_headers = {"Authorization": f"Bearer {impersonation.json()['access_token']}"}

    users_response = await client.get("/api/admin/users", headers=impersonated_headers)
    setup_response = await client.get("/api/admin/setup", headers=impersonated_headers)

    assert users_response.status_code == 403
    assert users_response.json()["error"]["code"] == "forbidden"
    assert setup_response.status_code == 403
