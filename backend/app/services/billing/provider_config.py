from app.config.settings import Settings
from app.constants.enums import BillingInterval
from app.services.billing.plans import PLANS, Plan

PRICE_REFERENCE_SETTINGS: dict[str, dict[tuple[str, BillingInterval], str]] = {
    "stripe": {
        ("pro", BillingInterval.MONTHLY): "STRIPE_PRICE_PRO_MONTHLY",
        ("pro", BillingInterval.YEARLY): "STRIPE_PRICE_PRO_YEARLY",
    },
    "lemonsqueezy": {
        ("pro", BillingInterval.MONTHLY): "LEMONSQUEEZY_VARIANT_PRO_MONTHLY",
        ("pro", BillingInterval.YEARLY): "LEMONSQUEEZY_VARIANT_PRO_YEARLY",
    },
    "creem": {
        ("pro", BillingInterval.MONTHLY): "CREEM_PRODUCT_PRO_MONTHLY",
        ("pro", BillingInterval.YEARLY): "CREEM_PRODUCT_PRO_YEARLY",
    },
}

CREDENTIAL_SETTINGS: dict[str, tuple[str, ...]] = {
    "stripe": ("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"),
    "lemonsqueezy": ("LEMONSQUEEZY_API_KEY", "LEMONSQUEEZY_STORE_ID", "LEMONSQUEEZY_WEBHOOK_SECRET"),
    "creem": ("CREEM_API_KEY", "CREEM_WEBHOOK_SECRET"),
}


def is_paid_plan(plan: Plan) -> bool:
    """Return whether the plan has a non-zero price."""
    return plan.price_monthly_cents > 0 or plan.price_yearly_cents > 0


def parse_billing_interval(value: BillingInterval | str) -> BillingInterval | None:
    """Parse a billing interval, returning None if it is invalid."""
    try:
        return BillingInterval(value)
    except ValueError:
        return None


class ProviderConfig:
    """Settings-backed configuration of the active billing provider."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.provider_name = settings.BILLING_PROVIDER if settings.billing_enabled else ""

    @property
    def has_credentials(self) -> bool:
        """Return whether all provider credentials are configured."""
        setting_names = CREDENTIAL_SETTINGS.get(self.provider_name, ())
        return bool(setting_names) and all(getattr(self.settings, name) for name in setting_names)

    def price_reference(self, plan_id: str, interval: BillingInterval | str) -> str | None:
        """Return the provider price id configured for a plan and interval."""
        billing_interval = parse_billing_interval(interval)
        if billing_interval is None:
            return None
        setting_name = PRICE_REFERENCE_SETTINGS.get(self.provider_name, {}).get((plan_id, billing_interval))
        if setting_name is None:
            return None
        return getattr(self.settings, setting_name) or None

    def resolve_price_reference(self, reference: str | None) -> tuple[str, BillingInterval] | None:
        """Return the plan and interval matching a provider price id."""
        if not reference:
            return None
        for (plan_id, interval), setting_name in PRICE_REFERENCE_SETTINGS.get(self.provider_name, {}).items():
            if getattr(self.settings, setting_name) == reference:
                return plan_id, interval
        return None

    def is_plan_available(self, plan_id: str, interval: BillingInterval | str) -> bool:
        """Return whether the plan can be purchased with this interval."""
        plan = PLANS.get(plan_id)
        if plan is None or parse_billing_interval(interval) is None:
            return False
        if not is_paid_plan(plan):
            return True
        return self.has_credentials and self.price_reference(plan_id, interval) is not None
