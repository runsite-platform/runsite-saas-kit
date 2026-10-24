from app.config.settings import Settings
from app.services.billing.providers.base import PaymentProvider
from app.services.billing.providers.creem_provider import CreemProvider
from app.services.billing.providers.lemonsqueezy_provider import LemonSqueezyProvider
from app.services.billing.providers.stripe_provider import StripeProvider


def build_payment_provider(settings: Settings) -> PaymentProvider | None:
    """Return the configured payment provider, or None if billing is off."""
    if not settings.billing_enabled:
        return None
    match settings.BILLING_PROVIDER:
        case "stripe":
            return StripeProvider(settings)
        case "lemonsqueezy":
            return LemonSqueezyProvider(settings)
        case "creem":
            return CreemProvider(settings)
    return None
