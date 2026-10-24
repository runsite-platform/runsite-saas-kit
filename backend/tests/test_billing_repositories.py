from app.constants.enums import OrgRole, SubscriptionStatus
from app.repositories.billing_event_repository import BillingEventRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.usage_repository import UsageRepository
from tests.factories import add_member, create_organization, create_project, create_subscription, create_user


async def create_owned_organization(db_session, email: str = "owner@example.com"):
    owner = await create_user(db_session, email=email)
    return await create_organization(db_session, owner=owner)


async def test_blocking_subscription_covers_trialing_active_and_past_due(db_session) -> None:
    organization = await create_owned_organization(db_session)
    repository = SubscriptionRepository(db_session)
    assert await repository.has_blocking_subscription(organization.id) is False

    subscription = await create_subscription(db_session, organization=organization, status=SubscriptionStatus.EXPIRED)
    assert await repository.has_blocking_subscription(organization.id) is False

    expectations = {
        SubscriptionStatus.TRIALING: True,
        SubscriptionStatus.ACTIVE: True,
        SubscriptionStatus.PAST_DUE: True,
        SubscriptionStatus.CANCELED: False,
    }
    for status, expected in expectations.items():
        subscription.status = status
        await db_session.flush()
        assert await repository.has_blocking_subscription(organization.id) is expected


async def test_current_subscription_prefers_blocking_status(db_session) -> None:
    organization = await create_owned_organization(db_session)
    active = await create_subscription(db_session, organization=organization, status=SubscriptionStatus.ACTIVE)
    await create_subscription(db_session, organization=organization, status=SubscriptionStatus.EXPIRED)

    current = await SubscriptionRepository(db_session).get_current_for_organization(organization.id)

    assert current is not None
    assert current.id == active.id


async def test_plan_granting_subscription_ignores_past_due(db_session) -> None:
    organization = await create_owned_organization(db_session)
    await create_subscription(db_session, organization=organization, status=SubscriptionStatus.PAST_DUE)
    repository = SubscriptionRepository(db_session)

    assert await repository.get_plan_granting_for_organization(organization.id) is None

    trialing = await create_subscription(db_session, organization=organization, status=SubscriptionStatus.TRIALING)
    granting = await repository.get_plan_granting_for_organization(organization.id)
    assert granting is not None
    assert granting.id == trialing.id


async def test_subscription_lookup_by_provider_id_is_scoped_to_provider(db_session) -> None:
    organization = await create_owned_organization(db_session)
    subscription = await create_subscription(db_session, organization=organization, provider="stripe")
    repository = SubscriptionRepository(db_session)

    found = await repository.get_by_provider_id("stripe", subscription.provider_subscription_id)
    assert found is not None and found.id == subscription.id
    assert await repository.get_by_provider_id("creem", subscription.provider_subscription_id) is None


async def test_billing_event_insert_if_absent_is_idempotent(db_session) -> None:
    repository = BillingEventRepository(db_session)

    first = await repository.insert_if_absent(
        provider="stripe", event_id="evt_1", event_type="invoice.paid", payload={"id": "evt_1"}
    )
    second = await repository.insert_if_absent(
        provider="stripe", event_id="evt_1", event_type="invoice.paid", payload={"id": "evt_1", "retry": True}
    )
    other_provider = await repository.insert_if_absent(
        provider="creem", event_id="evt_1", event_type="checkout.completed", payload={}
    )

    assert (first, second, other_provider) == (True, False, True)
    stored = await repository.get_by_provider_event_id("stripe", "evt_1")
    assert stored is not None
    assert stored.payload == {"id": "evt_1"}
    locked = await repository.get_by_provider_event_id("stripe", "evt_1", for_update=True)
    assert locked is not None and locked.id == stored.id


async def test_payments_listed_for_one_organization_only(db_session) -> None:
    organization = await create_owned_organization(db_session)
    other_organization = await create_owned_organization(db_session, email="other@example.com")
    repository = PaymentRepository(db_session)
    assert await repository.list_for_organization(organization.id) == []
    assert await repository.list_for_organization(other_organization.id) == []
    assert await repository.get_by_provider_id("stripe", "in_missing") is None


async def test_usage_counts_members_projects_and_storage(db_session) -> None:
    owner = await create_user(db_session, email="usage-owner@example.com")
    organization = await create_organization(db_session, owner=owner)
    member = await create_user(db_session, email="usage-member@example.com")
    await add_member(db_session, organization=organization, user=member, role=OrgRole.MEMBER)
    await create_project(db_session, organization=organization, created_by=owner)

    usage = await UsageRepository(db_session).get_usage(organization.id)

    assert usage.members == 2
    assert usage.pending_invitations == 0
    assert usage.projects == 1
    assert usage.storage_bytes == 0
