import uuid
from dataclasses import dataclass
from typing import Any

import pytest

from app.models.enums import PlatformRole
from tests.factories import auth_headers, create_organization, create_user

STAFF_ROLES = frozenset({PlatformRole.ADMIN, PlatformRole.SUPERADMIN})
SUPERADMIN_ONLY = frozenset({PlatformRole.SUPERADMIN})


@dataclass(frozen=True)
class AdminEndpoint:
    method: str
    path: str
    allowed_roles: frozenset[PlatformRole]
    json_body: dict[str, Any] | None = None


ADMIN_ENDPOINTS = (
    AdminEndpoint("GET", "/api/admin/users", STAFF_ROLES),
    AdminEndpoint("GET", "/api/admin/users/{user_id}", STAFF_ROLES),
    AdminEndpoint("POST", "/api/admin/users/{user_id}/block", STAFF_ROLES),
    AdminEndpoint("POST", "/api/admin/users/{user_id}/unblock", STAFF_ROLES),
    AdminEndpoint("POST", "/api/admin/users/{user_id}/resend-verification", STAFF_ROLES),
    AdminEndpoint("GET", "/api/admin/organizations", STAFF_ROLES),
    AdminEndpoint("GET", "/api/admin/organizations/{organization_id}", STAFF_ROLES),
    AdminEndpoint(
        "POST",
        "/api/admin/organizations/{organization_id}/plan-override",
        STAFF_ROLES,
        {"plan_id": "pro", "reason": "Partner deal"},
    ),
    AdminEndpoint("GET", "/api/admin/setup", STAFF_ROLES),
    AdminEndpoint("GET", "/api/admin/metrics", SUPERADMIN_ONLY),
    AdminEndpoint("POST", "/api/admin/users/{user_id}/grant-admin", SUPERADMIN_ONLY),
    AdminEndpoint("POST", "/api/admin/users/{user_id}/revoke-admin", SUPERADMIN_ONLY),
    AdminEndpoint("POST", "/api/admin/users/{user_id}/impersonate", SUPERADMIN_ONLY),
)


def endpoint_id(endpoint: AdminEndpoint) -> str:
    return f"{endpoint.method} {endpoint.path}"


@pytest.mark.parametrize("endpoint", ADMIN_ENDPOINTS, ids=endpoint_id)
@pytest.mark.parametrize("actor_role", list(PlatformRole), ids=str)
async def test_admin_permission_matrix(
    client, db_session, settings, email_outbox, endpoint: AdminEndpoint, actor_role: PlatformRole
) -> None:
    actor = await create_user(db_session, email="matrix-actor@example.com", platform_role=actor_role)
    target = await create_user(db_session, email="matrix-target@example.com", is_email_verified=False)
    organization = await create_organization(db_session, owner=target, slug="matrix-org")
    path = endpoint.path.format(user_id=target.id, organization_id=organization.id)

    response = await client.request(
        endpoint.method, path, json=endpoint.json_body, headers=await auth_headers(actor, settings=settings)
    )

    if actor_role in endpoint.allowed_roles:
        assert response.status_code == 200, response.text
    else:
        assert response.status_code == 403, response.text
        assert response.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize("endpoint", ADMIN_ENDPOINTS, ids=endpoint_id)
async def test_admin_endpoints_require_authentication(client, endpoint: AdminEndpoint) -> None:
    path = endpoint.path.format(user_id=uuid.uuid4(), organization_id=uuid.uuid4())

    response = await client.request(endpoint.method, path, json=endpoint.json_body)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


@pytest.mark.parametrize("endpoint", ADMIN_ENDPOINTS, ids=endpoint_id)
async def test_impersonated_superadmin_token_is_refused_everywhere(
    client, db_session, settings, endpoint: AdminEndpoint
) -> None:
    impersonated_superadmin_like = await create_user(
        db_session, email="matrix-impersonated@example.com", platform_role=PlatformRole.SUPERADMIN
    )
    path = endpoint.path.format(user_id=uuid.uuid4(), organization_id=uuid.uuid4())
    headers = await auth_headers(impersonated_superadmin_like, settings=settings, impersonated_by=uuid.uuid4())

    response = await client.request(endpoint.method, path, json=endpoint.json_body, headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
