from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.models.enums import ProjectStatus
from tests.factories import add_member, auth_headers, create_organization, create_project, create_user


async def test_member_creates_reads_and_lists_projects(
    client: AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session, email="projects-owner@example.com")
    organization = await create_organization(db_session, owner=owner)
    member = await create_user(db_session, email="projects-member@example.com")
    await add_member(db_session, organization=organization, user=member)
    headers = await auth_headers(member, settings=settings)

    create_response = await client.post(
        f"/api/orgs/{organization.id}/projects",
        json={"name": "  Website  ", "description": "Landing page"},
        headers=headers,
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Website"
    assert created["description"] == "Landing page"
    assert created["status"] == "active"
    assert created["created_by_id"] == str(member.id)
    assert created["organization_id"] == str(organization.id)

    detail_response = await client.get(f"/api/orgs/{organization.id}/projects/{created['id']}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == created["id"]

    list_response = await client.get(f"/api/orgs/{organization.id}/projects", headers=headers)
    assert list_response.status_code == 200
    assert [project["name"] for project in list_response.json()["items"]] == ["Website"]


async def test_update_archive_and_filter_by_status(
    client: AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session, email="projects-archive@example.com")
    organization = await create_organization(db_session, owner=owner)
    kept = await create_project(db_session, organization=organization, created_by=owner, name="Kept")
    archived = await create_project(db_session, organization=organization, created_by=owner, name="Old")
    headers = await auth_headers(owner, settings=settings)

    rename_response = await client.patch(
        f"/api/orgs/{organization.id}/projects/{kept.id}",
        json={"name": "Kept renamed", "description": None},
        headers=headers,
    )
    archive_response = await client.patch(
        f"/api/orgs/{organization.id}/projects/{archived.id}", json={"status": "archived"}, headers=headers
    )

    assert rename_response.status_code == 200
    assert rename_response.json()["name"] == "Kept renamed"
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == ProjectStatus.ARCHIVED
    assert archive_response.json()["name"] == "Old"

    active_response = await client.get(
        f"/api/orgs/{organization.id}/projects", params={"status": "active"}, headers=headers
    )
    archived_response = await client.get(
        f"/api/orgs/{organization.id}/projects", params={"status": "archived"}, headers=headers
    )
    all_response = await client.get(f"/api/orgs/{organization.id}/projects", headers=headers)

    assert [project["name"] for project in active_response.json()["items"]] == ["Kept renamed"]
    assert [project["name"] for project in archived_response.json()["items"]] == ["Old"]
    assert sorted(project["name"] for project in all_response.json()["items"]) == ["Kept renamed", "Old"]


async def test_delete_project(client: AsyncClient, db_session: AsyncSession, settings: Settings) -> None:
    owner = await create_user(db_session, email="projects-delete@example.com")
    organization = await create_organization(db_session, owner=owner)
    project = await create_project(db_session, organization=organization, created_by=owner)
    headers = await auth_headers(owner, settings=settings)

    delete_response = await client.delete(f"/api/orgs/{organization.id}/projects/{project.id}", headers=headers)
    detail_response = await client.get(f"/api/orgs/{organization.id}/projects/{project.id}", headers=headers)

    assert delete_response.status_code == 204
    assert detail_response.status_code == 404
    assert detail_response.json()["error"]["code"] == "not_found"


async def test_project_validation(client: AsyncClient, db_session: AsyncSession, settings: Settings) -> None:
    owner = await create_user(db_session, email="projects-validation@example.com")
    organization = await create_organization(db_session, owner=owner)
    headers = await auth_headers(owner, settings=settings)

    empty_name = await client.post(f"/api/orgs/{organization.id}/projects", json={"name": "   "}, headers=headers)
    bad_status = await client.get(
        f"/api/orgs/{organization.id}/projects", params={"status": "deleted"}, headers=headers
    )
    huge_size = await client.get(f"/api/orgs/{organization.id}/projects", params={"size": 101}, headers=headers)

    assert empty_name.status_code == 422
    assert bad_status.status_code == 422
    assert huge_size.status_code == 422


async def test_free_plan_project_limit(client: AsyncClient, db_session: AsyncSession, settings: Settings) -> None:
    owner = await create_user(db_session, email="projects-limit@example.com")
    organization = await create_organization(db_session, owner=owner)
    for project_number in range(3):
        await create_project(db_session, organization=organization, created_by=owner, name=f"P{project_number}")

    headers = await auth_headers(owner, settings=settings)

    response = await client.post(f"/api/orgs/{organization.id}/projects", json={"name": "Fourth"}, headers=headers)

    assert response.status_code == 402
    error = response.json()["error"]
    assert error["code"] == "plan_limit_reached"
    assert error["details"] == {"limit": "projects", "plan_id": "free"}


async def test_other_organization_projects_are_hidden(
    client: AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner_a = await create_user(db_session, email="isolation-a@example.com")
    organization_a = await create_organization(db_session, owner=owner_a, name="A")
    project_a = await create_project(db_session, organization=organization_a, created_by=owner_a)
    owner_b = await create_user(db_session, email="isolation-b@example.com")
    organization_b = await create_organization(db_session, owner=owner_b, name="B")
    headers_b = await auth_headers(owner_b, settings=settings)

    responses = [
        await client.get(f"/api/orgs/{organization_a.id}/projects", headers=headers_b),
        await client.post(f"/api/orgs/{organization_a.id}/projects", json={"name": "X"}, headers=headers_b),
        await client.get(f"/api/orgs/{organization_a.id}/projects/{project_a.id}", headers=headers_b),
        await client.get(f"/api/orgs/{organization_b.id}/projects/{project_a.id}", headers=headers_b),
        await client.patch(
            f"/api/orgs/{organization_b.id}/projects/{project_a.id}", json={"name": "Stolen"}, headers=headers_b
        ),
        await client.delete(f"/api/orgs/{organization_b.id}/projects/{project_a.id}", headers=headers_b),
    ]

    assert [response.status_code for response in responses] == [404] * 6


async def test_projects_require_authentication(client: AsyncClient, db_session: AsyncSession) -> None:
    owner = await create_user(db_session, email="projects-anonymous@example.com")
    organization = await create_organization(db_session, owner=owner)

    response = await client.get(f"/api/orgs/{organization.id}/projects")

    assert response.status_code == 401
