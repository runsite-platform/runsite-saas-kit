from app.services.billing.plans import FEATURE_REQUIRED_PLAN, PLANS, get_plan


def test_free_plan_matches_spec() -> None:
    free_plan = PLANS["free"]
    assert free_plan.name == "Free"
    assert free_plan.price_monthly_cents == 0
    assert free_plan.trial_days == 0
    assert free_plan.limits.members == 3
    assert free_plan.limits.projects == 3
    assert free_plan.limits.storage_mb == 100
    assert free_plan.features == frozenset({"file_uploads"})


def test_pro_plan_matches_spec() -> None:
    pro_plan = PLANS["pro"]
    assert pro_plan.price_monthly_cents == 1900
    assert pro_plan.price_yearly_cents == 19000
    assert pro_plan.trial_days == 14
    assert pro_plan.limits.members == 10
    assert pro_plan.limits.projects == 100
    assert pro_plan.limits.storage_mb == 5000
    assert pro_plan.features == frozenset({"file_uploads", "analytics"})


def test_get_plan_returns_known_plan() -> None:
    assert get_plan("pro") is PLANS["pro"]


def test_get_plan_falls_back_to_free_for_unknown_id() -> None:
    assert get_plan("enterprise") is PLANS["free"]
    assert get_plan("") is PLANS["free"]


def test_every_required_plan_contains_its_feature() -> None:
    for feature, plan_id in FEATURE_REQUIRED_PLAN.items():
        assert feature in PLANS[plan_id].features
