from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.repositories.admin_query_repository import AdminQueryRepository
from app.schemas.admin import ChecklistStatus, SetupChecklistItem, SetupChecklistResponse

DOCS_BASE_URL = "https://docs.runsite.app"

DOCS_URLS = {
    "email_api_key": f"{DOCS_BASE_URL}/saas-kit/setup/email",
    "sender_domain": f"{DOCS_BASE_URL}/email/domains",
    "email_verification": f"{DOCS_BASE_URL}/saas-kit/setup/email#require-email-verification",
    "billing_provider": f"{DOCS_BASE_URL}/saas-kit/setup/billing",
    "billing_price_ids": f"{DOCS_BASE_URL}/saas-kit/setup/billing#price-ids",
    "billing_webhook_secret": f"{DOCS_BASE_URL}/saas-kit/setup/billing#webhooks",
    "google_oauth": f"{DOCS_BASE_URL}/saas-kit/setup/google-oauth",
    "storage": f"{DOCS_BASE_URL}/storage",
    "storage_delete_key": f"{DOCS_BASE_URL}/saas-kit/setup/storage#delete-key",
    "superadmin": f"{DOCS_BASE_URL}/saas-kit/setup/superadmin",
}


@dataclass(frozen=True)
class ProviderSettingNames:
    """Setting names required by a billing provider."""

    credentials: tuple[str, ...]
    price_ids: tuple[str, ...]
    webhook_secret: str


PROVIDER_SETTING_NAMES = {
    "stripe": ProviderSettingNames(
        credentials=("STRIPE_SECRET_KEY",),
        price_ids=("STRIPE_PRICE_PRO_MONTHLY", "STRIPE_PRICE_PRO_YEARLY"),
        webhook_secret="STRIPE_WEBHOOK_SECRET",
    ),
    "lemonsqueezy": ProviderSettingNames(
        credentials=("LEMONSQUEEZY_API_KEY", "LEMONSQUEEZY_STORE_ID"),
        price_ids=("LEMONSQUEEZY_VARIANT_PRO_MONTHLY", "LEMONSQUEEZY_VARIANT_PRO_YEARLY"),
        webhook_secret="LEMONSQUEEZY_WEBHOOK_SECRET",
    ),
    "creem": ProviderSettingNames(
        credentials=("CREEM_API_KEY",),
        price_ids=("CREEM_PRODUCT_PRO_MONTHLY", "CREEM_PRODUCT_PRO_YEARLY"),
        webhook_secret="CREEM_WEBHOOK_SECRET",
    ),
}


def ok_or(condition: bool, otherwise: ChecklistStatus = ChecklistStatus.MISSING) -> ChecklistStatus:
    """Return OK when the condition holds, otherwise the given status."""
    return ChecklistStatus.OK if condition else otherwise


def presence_status(settings: Settings, setting_names: tuple[str, ...]) -> ChecklistStatus:
    """Return OK, WARNING or MISSING based on which settings are set."""
    configured_count = sum(1 for setting_name in setting_names if getattr(settings, setting_name))
    if configured_count == len(setting_names):
        return ChecklistStatus.OK
    if configured_count == 0:
        return ChecklistStatus.MISSING
    return ChecklistStatus.WARNING


class SetupChecklistService:
    """Service for the admin setup checklist."""

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.queries = AdminQueryRepository(db)
        self.settings = settings

    async def get_checklist(self) -> SetupChecklistResponse:
        """Return the status of every setup checklist item."""
        settings = self.settings
        provider_settings = PROVIDER_SETTING_NAMES.get(settings.BILLING_PROVIDER) if settings.billing_enabled else None
        statuses = {
            "email_api_key": ok_or(settings.email_enabled),
            "sender_domain": ChecklistStatus.MANUAL,
            "email_verification": ok_or(settings.REQUIRE_EMAIL_VERIFICATION, ChecklistStatus.WARNING),
            "billing_provider": self._billing_provider_status(provider_settings),
            "billing_price_ids": (
                presence_status(settings, provider_settings.price_ids) if provider_settings else ChecklistStatus.MISSING
            ),
            "billing_webhook_secret": (
                presence_status(settings, (provider_settings.webhook_secret,))
                if provider_settings
                else ChecklistStatus.MISSING
            ),
            "google_oauth": ok_or(settings.google_login_enabled),
            "storage": ok_or(settings.storage_enabled),
            "storage_delete_key": self._storage_delete_status(),
            "superadmin": ok_or(await self.queries.superadmin_exists()),
        }
        return SetupChecklistResponse(
            items=[
                SetupChecklistItem(id=item_id, status=status, docs_url=DOCS_URLS[item_id])
                for item_id, status in statuses.items()
            ]
        )

    def _billing_provider_status(self, provider_settings: ProviderSettingNames | None) -> ChecklistStatus:
        if provider_settings is None:
            return ChecklistStatus.MISSING
        credentials_status = presence_status(self.settings, provider_settings.credentials)
        return ok_or(credentials_status == ChecklistStatus.OK, ChecklistStatus.WARNING)

    def _storage_delete_status(self) -> ChecklistStatus:
        if self.settings.storage_delete_enabled:
            return ChecklistStatus.OK
        if self.settings.storage_enabled:
            return ChecklistStatus.MANUAL
        return ChecklistStatus.MISSING
