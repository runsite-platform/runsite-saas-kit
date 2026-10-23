from tests.factories import auth_headers, create_organization, create_user


async def test_paid_plans_are_unavailable_without_a_provider(client) -> None:
    plans = {plan["id"]: plan for plan in (await client.get("/api/plans")).json()}

    assert plans["free"]["available"] == {"monthly": True, "yearly": True}
    assert plans["pro"]["available"] == {"monthly": False, "yearly": False}


async def test_billing_actions_report_billing_disabled(client, db_session, settings) -> None:
    owner = await create_user(db_session, email="disabled-owner@example.com")
    organization = await create_organization(db_session, owner=owner)
    headers = await auth_headers(owner, settings=settings)
    base_path = f"/api/orgs/{organization.id}/billing"

    overview = await client.get(base_path, headers=headers)
    assert overview.status_code == 200
    assert overview.json()["billing_enabled"] is False
    assert overview.json()["provider"] is None

    for suffix, payload in (
        ("/checkout", {"plan_id": "pro", "interval": "monthly"}),
        ("/portal", None),
        ("/cancel", None),
    ):
        response = await client.post(f"{base_path}{suffix}", json=payload, headers=headers)
        assert response.status_code == 400, suffix
        assert response.json()["error"]["code"] == "billing_disabled"


async def test_webhooks_are_not_found_when_billing_is_disabled(client) -> None:
    for provider_name in ("stripe", "lemonsqueezy", "creem"):
        response = await client.post(f"/api/webhooks/billing/{provider_name}", content=b"{}")
        assert response.status_code == 404, provider_name
