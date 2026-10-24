from dataclasses import dataclass

FREE_PLAN_ID = "free"


@dataclass(frozen=True)
class Limits:
    """Resource limits of a plan."""

    members: int
    projects: int
    storage_mb: int


@dataclass(frozen=True)
class Plan:
    """Subscription plan with pricing, limits and features."""

    id: str
    name: str
    price_monthly_cents: int
    price_yearly_cents: int
    trial_days: int
    limits: Limits
    features: frozenset[str]


PLANS: dict[str, Plan] = {
    "free": Plan(
        id="free",
        name="Free",
        price_monthly_cents=0,
        price_yearly_cents=0,
        trial_days=0,
        limits=Limits(members=3, projects=3, storage_mb=100),
        features=frozenset({"file_uploads"}),
    ),
    "pro": Plan(
        id="pro",
        name="Pro",
        price_monthly_cents=1900,
        price_yearly_cents=19000,
        trial_days=14,
        limits=Limits(members=10, projects=100, storage_mb=5000),
        features=frozenset({"file_uploads", "analytics"}),
    ),
}

FEATURE_REQUIRED_PLAN: dict[str, str] = {"file_uploads": "free", "analytics": "pro"}


def get_plan(plan_id: str) -> Plan:
    """Return the plan by id, falling back to the free plan."""
    return PLANS.get(plan_id, PLANS[FREE_PLAN_ID])
