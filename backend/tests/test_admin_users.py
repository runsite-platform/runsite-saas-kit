import uuid

from app.models import OAuthAccount
from app.constants.enums import PlatformRole
from tests.factories import auth_headers, create_organization, create_user


async def test_list_users_searches_email_and_name(client, db_session, settings) -> None:
    admin = await create_user(db_session, email="admin@example.com", full_name="Ada", platform_role=PlatformRole.ADMIN)
    await create_user(db_session, email="alice@example.com", full_name="Alice Smith")
    await create_user(db_session, email="bob@example.com", full_name="Bob Alison")
    await create_user(db_session, email="carol@example.com", full_name="Carol")

    response = await client.get(
        "/api/admin/users", params={"search": "ali"}, headers=await auth_headers(admin, settings=settings)
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert sorted(item["email"] for item in body["items"]) == ["alice@example.com", "bob@example.com"]
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["size"] == 50


async def test_list_users_paginates_and_caps_page_size(client, db_session, settings) -> None:
    admin = await create_user(db_session, email="pager@example.com", platform_role=PlatformRole.ADMIN)
    for index in range(4):
        await create_user(db_session, email=f"paged-{index}@example.com")
    headers = await auth_headers(admin, settings=settings)

    second_page = await client.get("/api/admin/users", params={"page": 2, "size": 2}, headers=headers)
    oversized = await client.get("/api/admin/users", params={"size": 101}, headers=headers)

    assert second_page.status_code == 200
    assert second_page.json()["total"] == 5
    assert len(second_page.json()["items"]) == 2
    assert second_page.json()["page"] == 2
    assert oversized.status_code == 422


async def test_search_treats_like_wildcards_literally(client, db_session, settings) -> None:
    admin = await create_user(db_session, email="wildcard@example.com", platform_role=PlatformRole.ADMIN)

    response = await client.get(
        "/api/admin/users", params={"search": "%"}, headers=await auth_headers(admin, settings=settings)
    )

    assert response.json()["total"] == 0


async def test_user_detail_lists_memberships_and_google_link(client, db_session, settings) -> None:
    admin = await create_user(db_session, email="detail-admin@example.com", platform_role=PlatformRole.ADMIN)
    member = await create_user(db_session, email="detail-member@example.com")
    organization = await create_organization(db_session, owner=member, name="Acme", slug="acme-detail")
    db_session.add(OAuthAccount(user_id=member.id, provider="google", provider_account_id="google-123"))
    await db_session.flush()

    response = await client.get(f"/api/admin/users/{member.id}", headers=await auth_headers(admin, settings=settings))

    assert response.status_code == 200, response.text
    detail = response.json()
    assert detail["email"] == "detail-member@example.com"
    assert detail["has_password"] is True
    assert detail["google_linked"] is True
    assert detail["is_blocked"] is False
    assert detail["memberships"] == [
        {
            "organization_id": str(organization.id),
            "organization_name": "Acme",
            "organization_slug": "acme-detail",
            "role": "owner",
            "plan_id": "free",
        }
    ]


async def test_user_detail_returns_404_for_unknown_user(client, db_session, settings) -> None:
    admin = await create_user(db_session, email="missing-admin@example.com", platform_role=PlatformRole.ADMIN)

    headers = await auth_headers(admin, settings=settings)

    response = await client.get(f"/api/admin/users/{uuid.uuid4()}", headers=headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
