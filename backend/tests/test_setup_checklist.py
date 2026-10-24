from app.constants.enums import PlatformRole
from app.services.setup_checklist_service import SetupChecklistService
from tests.conftest import make_settings
from tests.factories import auth_headers, create_user

STORAGE_SETTINGS = {
    "S3_ACCESS_KEY_ID": "access",
    "S3_SECRET_ACCESS_KEY": "secret",
    "S3_ENDPOINT_URL": "https://s3.runsite.test",
    "S3_BUCKET": "saaskit",
}


async def checklist_statuses(db_session, **setting_overrides: object) -> dict[str, str]:
    checklist = await SetupChecklistService(db_session, make_settings(**setting_overrides)).get_checklist()
    assert all(item.docs_url.startswith("https://docs.runsite.app/") for item in checklist.items)
    return {item.id: item.status for item in checklist.items}


async def test_nothing_configured(db_session) -> None:
    assert await checklist_statuses(db_session) == {
        "email_api_key": "missing",
        "sender_domain": "manual",
        "email_verification": "warning",
        "billing_provider": "missing",
        "billing_price_ids": "missing",
        "billing_webhook_secret": "missing",
        "google_oauth": "missing",
        "storage": "missing",
        "storage_delete_key": "missing",
        "superadmin": "missing",
    }


async def test_everything_configured_with_stripe(db_session) -> None:
    await create_user(db_session, email="setup-super@example.com", platform_role=PlatformRole.SUPERADMIN)

    statuses = await checklist_statuses(
        db_session,
        EMAIL_API_KEY="email-key",
        REQUIRE_EMAIL_VERIFICATION=True,
        BILLING_PROVIDER="stripe",
        STRIPE_SECRET_KEY="sk_test",
        STRIPE_WEBHOOK_SECRET="whsec_test",
        STRIPE_PRICE_PRO_MONTHLY="price_monthly",
        STRIPE_PRICE_PRO_YEARLY="price_yearly",
        GOOGLE_CLIENT_ID="google-id",
        GOOGLE_CLIENT_SECRET="google-secret",
        S3_DELETE_ACCESS_KEY_ID="delete-access",
        S3_DELETE_SECRET_ACCESS_KEY="delete-secret",
        **STORAGE_SETTINGS,
    )

    assert statuses.pop("sender_domain") == "manual"
    assert set(statuses.values()) == {"ok"}


async def test_partial_lemonsqueezy_and_storage_without_delete_key(db_session) -> None:
    statuses = await checklist_statuses(
        db_session,
        BILLING_PROVIDER="lemonsqueezy",
        LEMONSQUEEZY_API_KEY="ls-key",
        LEMONSQUEEZY_VARIANT_PRO_MONTHLY="111",
        **STORAGE_SETTINGS,
    )

    assert statuses["billing_provider"] == "warning"
    assert statuses["billing_price_ids"] == "warning"
    assert statuses["billing_webhook_secret"] == "missing"
    assert statuses["storage"] == "ok"
    assert statuses["storage_delete_key"] == "manual"


async def test_setup_endpoint_is_available_to_admins(client, db_session, settings) -> None:
    admin = await create_user(db_session, email="setup-admin@example.com", platform_role=PlatformRole.ADMIN)

    response = await client.get("/api/admin/setup", headers=await auth_headers(admin, settings=settings))

    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) == 10
    assert response.json()["items"][0] == {
        "id": "email_api_key",
        "status": "missing",
        "docs_url": "https://docs.runsite.app/saas-kit/setup/email",
    }
