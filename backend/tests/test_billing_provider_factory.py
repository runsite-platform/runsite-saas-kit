import pytest

from app.services.billing.providers.creem_provider import CreemProvider
from app.services.billing.providers.factory import build_payment_provider
from app.services.billing.providers.lemonsqueezy_provider import LemonSqueezyProvider
from app.services.billing.providers.stripe_provider import StripeProvider
from app.utils.dependencies import get_payment_provider
from tests.conftest import make_settings
from tests.fakes import TEST_CREEM_SETTINGS, TEST_LEMONSQUEEZY_SETTINGS, TEST_STRIPE_SETTINGS


@pytest.mark.parametrize(
    ("overrides", "expected_type"),
    [
        ({}, type(None)),
        ({"BILLING_PROVIDER": "paddle"}, type(None)),
        (TEST_STRIPE_SETTINGS, StripeProvider),
        (TEST_LEMONSQUEEZY_SETTINGS, LemonSqueezyProvider),
        (TEST_CREEM_SETTINGS, CreemProvider),
    ],
)
def test_build_payment_provider_matches_billing_provider(overrides, expected_type) -> None:
    provider = build_payment_provider(make_settings(**overrides))

    assert type(provider) is expected_type


def test_stripe_provider_builds_without_a_secret_key() -> None:
    provider = build_payment_provider(make_settings(BILLING_PROVIDER="stripe"))

    assert provider is not None
    assert provider.name == "stripe"


def test_dependency_returns_the_configured_provider(settings) -> None:
    assert get_payment_provider(settings) is None
    provider = get_payment_provider(make_settings(**TEST_CREEM_SETTINGS))
    assert provider is not None
    assert provider.name == "creem"
