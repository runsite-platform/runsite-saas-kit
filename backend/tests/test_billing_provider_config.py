import pytest

from app.constants.enums import BillingInterval
from app.services.billing.plans import PLANS
from app.services.billing.provider_config import ProviderConfig, is_paid_plan
from tests.conftest import make_settings
from tests.fakes import TEST_CREEM_SETTINGS, TEST_LEMONSQUEEZY_SETTINGS, TEST_STRIPE_SETTINGS


def test_free_plan_is_always_available_and_paid_plan_needs_a_provider(settings) -> None:
    config = ProviderConfig(settings)

    assert config.is_plan_available("free", BillingInterval.MONTHLY) is True
    assert config.is_plan_available("pro", BillingInterval.MONTHLY) is False
    assert config.price_reference("pro", BillingInterval.MONTHLY) is None


@pytest.mark.parametrize(
    ("overrides", "monthly_reference", "yearly_reference"),
    [
        (TEST_STRIPE_SETTINGS, "price_pro_monthly_test", "price_pro_yearly_test"),
        (TEST_LEMONSQUEEZY_SETTINGS, "101", "102"),
        (TEST_CREEM_SETTINGS, "prod_pro_monthly_test", "prod_pro_yearly_test"),
    ],
)
def test_each_provider_resolves_both_directions(overrides, monthly_reference, yearly_reference) -> None:
    config = ProviderConfig(make_settings(**overrides))

    assert config.price_reference("pro", BillingInterval.MONTHLY) == monthly_reference
    assert config.price_reference("pro", "yearly") == yearly_reference
    assert config.resolve_price_reference(yearly_reference) == ("pro", BillingInterval.YEARLY)
    assert config.resolve_price_reference(monthly_reference) == ("pro", BillingInterval.MONTHLY)
    assert config.resolve_price_reference("unknown") is None
    assert config.resolve_price_reference("") is None
    assert config.is_plan_available("pro", BillingInterval.MONTHLY) is True
    assert config.is_plan_available("pro", BillingInterval.YEARLY) is True


def test_missing_price_makes_only_that_interval_unavailable() -> None:
    config = ProviderConfig(make_settings(**{**TEST_STRIPE_SETTINGS, "STRIPE_PRICE_PRO_YEARLY": ""}))

    assert config.is_plan_available("pro", BillingInterval.MONTHLY) is True
    assert config.is_plan_available("pro", BillingInterval.YEARLY) is False
    assert config.resolve_price_reference("") is None


def test_missing_credentials_make_paid_plans_unavailable() -> None:
    config = ProviderConfig(make_settings(**{**TEST_LEMONSQUEEZY_SETTINGS, "LEMONSQUEEZY_STORE_ID": ""}))

    assert config.has_credentials is False
    assert config.is_plan_available("pro", BillingInterval.MONTHLY) is False


def test_unknown_plan_and_interval_are_unavailable() -> None:
    config = ProviderConfig(make_settings(**TEST_STRIPE_SETTINGS))

    assert config.is_plan_available("enterprise", BillingInterval.MONTHLY) is False
    assert config.is_plan_available("pro", "weekly") is False
    assert config.price_reference("pro", "weekly") is None


def test_is_paid_plan() -> None:
    assert is_paid_plan(PLANS["free"]) is False
    assert is_paid_plan(PLANS["pro"]) is True
