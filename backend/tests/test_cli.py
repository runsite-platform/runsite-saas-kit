import pytest
from sqlalchemy import func, select

from app.cli import (
    DEMO_ORGANIZATION_SLUG,
    DEMO_PROJECTS,
    CliError,
    SeedDemoResult,
    build_parser,
    create_superadmin,
    seed_demo,
)
from app.models import Membership, Organization, Project, User
from app.constants.enums import PlatformRole
from app.services.superadmin_service import SuperadminService, promote_superadmin_on_startup
from app.utils.security import verify_password
from tests.factories import create_user


def refuse_prompt() -> str:
    raise AssertionError("the password prompt must not be used")


async def test_promote_by_email_is_case_insensitive(db_session) -> None:
    user = await create_user(db_session, email="founder@example.com")

    promoted = await SuperadminService(db_session).promote_by_email("  FOUNDER@example.com ")
    missing = await SuperadminService(db_session).promote_by_email("nobody@example.com")

    assert promoted is user
    assert user.platform_role == PlatformRole.SUPERADMIN
    assert missing is None


async def test_startup_promotion_skips_an_empty_email() -> None:
    def refuse_session_maker() -> None:
        raise AssertionError("no session may be opened")

    await promote_superadmin_on_startup(refuse_session_maker, "   ")


async def test_create_superadmin_promotes_an_existing_user(db_session, settings) -> None:
    user = await create_user(db_session, email="existing@example.com")

    result = await create_superadmin(db_session, settings, email="EXISTING@example.com", password_prompt=refuse_prompt)

    assert result.created is False
    assert result.user_id == user.id
    assert user.platform_role == PlatformRole.SUPERADMIN


async def test_create_superadmin_creates_a_user_with_the_prompted_password(db_session, settings) -> None:
    result = await create_superadmin(
        db_session, settings, email="new-super@example.com", password_prompt=lambda: "long-password-1"
    )

    user = await db_session.get(User, result.user_id)
    assert result.created is True
    assert user is not None
    assert user.platform_role == PlatformRole.SUPERADMIN
    assert user.is_email_verified is True
    assert verify_password("long-password-1", user.password_hash)
    memberships = await db_session.scalar(
        select(func.count()).select_from(Membership).where(Membership.user_id == user.id)
    )
    assert memberships == 1


async def test_create_superadmin_prefers_the_password_option(db_session, settings) -> None:
    result = await create_superadmin(
        db_session, settings, email="option@example.com", password="option-password", password_prompt=refuse_prompt
    )

    assert result.created is True


@pytest.mark.parametrize(
    ("email", "password"),
    [("not-an-email", "long-password-1"), ("short@example.com", "short")],
)
async def test_create_superadmin_rejects_invalid_input(db_session, settings, email: str, password: str) -> None:
    with pytest.raises(CliError):
        await create_superadmin(db_session, settings, email=email, password=password, password_prompt=refuse_prompt)


async def test_seed_demo_is_idempotent(db_session) -> None:
    first_run = await seed_demo(db_session)
    second_run = await seed_demo(db_session)

    assert first_run == SeedDemoResult(
        user_created=True, organization_created=True, projects_created=len(DEMO_PROJECTS)
    )
    assert second_run == SeedDemoResult(user_created=False, organization_created=False, projects_created=0)
    organization = await db_session.scalar(select(Organization).where(Organization.slug == DEMO_ORGANIZATION_SLUG))
    project_count = await db_session.scalar(
        select(func.count()).select_from(Project).where(Project.organization_id == organization.id)
    )
    assert project_count == len(DEMO_PROJECTS) == 3


def test_parser_reads_both_commands() -> None:
    parser = build_parser()

    create_arguments = parser.parse_args(["create-superadmin", "--email", "a@example.com", "--password", "secret-pw"])
    seed_arguments = parser.parse_args(["seed-demo"])

    assert create_arguments.command == "create-superadmin"
    assert create_arguments.email == "a@example.com"
    assert create_arguments.password == "secret-pw"
    assert seed_arguments.command == "seed-demo"
    with pytest.raises(SystemExit):
        parser.parse_args([])
