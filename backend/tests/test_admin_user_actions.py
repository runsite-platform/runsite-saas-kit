import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.constants.enums import AuthTokenKind, PlatformRole
from app.models import AuthToken
from app.utils.security import generate_token, hash_token
from tests.factories import auth_headers, create_user


async def count_refresh_tokens(db_session, user_id: uuid.UUID) -> int:
    statement = (
        select(func.count())
        .select_from(AuthToken)
        .where(AuthToken.user_id == user_id, AuthToken.kind == AuthTokenKind.REFRESH)
    )
    return int(await db_session.scalar(statement) or 0)


async def add_refresh_token(db_session, user_id: uuid.UUID) -> None:
    db_session.add(
        AuthToken(
            user_id=user_id,
            kind=AuthTokenKind.REFRESH,
            token_hash=hash_token(generate_token()),
            family_id=uuid.uuid4(),
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
    )
    await db_session.flush()


async def test_block_revokes_refresh_tokens_and_unblock_restores_access(client, db_session, settings) -> None:
    admin = await create_user(db_session, email="blocker@example.com", platform_role=PlatformRole.ADMIN)
    target = await create_user(db_session, email="blocked@example.com")
    await add_refresh_token(db_session, target.id)
    await add_refresh_token(db_session, target.id)
    admin_headers = await auth_headers(admin, settings=settings)
    target_headers = await auth_headers(target, settings=settings)

    block_response = await client.post(f"/api/admin/users/{target.id}/block", headers=admin_headers)
    blocked_me = await client.get("/api/me", headers=target_headers)

    assert block_response.status_code == 200, block_response.text
    assert block_response.json()["is_blocked"] is True
    assert await count_refresh_tokens(db_session, target.id) == 0
    assert blocked_me.status_code == 403
    assert blocked_me.json()["error"]["code"] == "user_blocked"

    unblock_response = await client.post(f"/api/admin/users/{target.id}/unblock", headers=admin_headers)
    unblocked_me = await client.get("/api/me", headers=target_headers)

    assert unblock_response.json()["is_blocked"] is False
    assert unblocked_me.status_code == 200


async def test_cannot_block_yourself(client, db_session, settings) -> None:
    admin = await create_user(db_session, email="self-block@example.com", platform_role=PlatformRole.ADMIN)

    headers = await auth_headers(admin, settings=settings)

    response = await client.post(f"/api/admin/users/{admin.id}/block", headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_cannot_block_a_superadmin(client, db_session, settings) -> None:
    superadmin = await create_user(db_session, email="super-a@example.com", platform_role=PlatformRole.SUPERADMIN)
    other_superadmin = await create_user(db_session, email="super-b@example.com", platform_role=PlatformRole.SUPERADMIN)

    response = await client.post(
        f"/api/admin/users/{other_superadmin.id}/block", headers=await auth_headers(superadmin, settings=settings)
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert other_superadmin.is_blocked is False


async def test_only_a_superadmin_can_block_an_admin(client, db_session, settings) -> None:
    admin = await create_user(db_session, email="admin-a@example.com", platform_role=PlatformRole.ADMIN)
    other_admin = await create_user(db_session, email="admin-b@example.com", platform_role=PlatformRole.ADMIN)
    superadmin = await create_user(db_session, email="super-c@example.com", platform_role=PlatformRole.SUPERADMIN)

    by_admin = await client.post(
        f"/api/admin/users/{other_admin.id}/block", headers=await auth_headers(admin, settings=settings)
    )
    by_superadmin = await client.post(
        f"/api/admin/users/{other_admin.id}/block", headers=await auth_headers(superadmin, settings=settings)
    )

    assert by_admin.status_code == 403
    assert by_superadmin.status_code == 200
    assert by_superadmin.json()["is_blocked"] is True


async def test_resend_verification_sends_only_to_unverified_users(client, db_session, settings, email_outbox) -> None:
    admin = await create_user(db_session, email="resender@example.com", platform_role=PlatformRole.ADMIN)
    unverified = await create_user(db_session, email="unverified@example.com", is_email_verified=False)
    verified = await create_user(db_session, email="verified@example.com", is_email_verified=True)
    headers = await auth_headers(admin, settings=settings)

    unverified_response = await client.post(f"/api/admin/users/{unverified.id}/resend-verification", headers=headers)
    verified_response = await client.post(f"/api/admin/users/{verified.id}/resend-verification", headers=headers)

    assert unverified_response.status_code == 200, unverified_response.text
    assert unverified_response.json() == {"sent": True}
    assert verified_response.json() == {"sent": False}
    assert [message.to for message in email_outbox.sent] == ["unverified@example.com"]
    assert "/verify-email?token=" in email_outbox.sent[0].text
