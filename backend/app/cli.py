"""Maintenance commands: python -m app.cli <command>."""

import argparse
import asyncio
import getpass
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.db import DatabaseManager
from app.config.settings import Settings, get_settings
from app.constants.enums import OrgRole, PlatformRole, ProjectStatus
from app.models import Membership, Organization, Project, User
from app.repositories.admin_query_repository import AdminQueryRepository
from app.services.signup_service import SignupService
from app.services.superadmin_service import SuperadminService
from app.utils.security import hash_password

MIN_PASSWORD_LENGTH = 8
DEMO_USER_EMAIL = "demo@example.com"
DEMO_USER_PASSWORD = "demo-password-123"
DEMO_USER_NAME = "Demo User"
DEMO_ORGANIZATION_NAME = "Demo Workspace"
DEMO_ORGANIZATION_SLUG = "demo"
DEMO_PROJECTS = (
    ("Website redesign", "Refresh the marketing site before the spring launch."),
    ("Mobile app", "First iOS and Android release."),
    ("Customer interviews", "Ten calls with early adopters."),
)


class CliError(Exception):
    pass


@dataclass(frozen=True)
class CreateSuperadminResult:
    user_id: UUID
    email: str
    created: bool


@dataclass(frozen=True)
class SeedDemoResult:
    user_created: bool
    organization_created: bool
    projects_created: int


def prompt_password() -> str:
    password = getpass.getpass("Password for the new superadmin: ")
    confirmation = getpass.getpass("Repeat the password: ")
    if password != confirmation:
        raise CliError("Passwords do not match")
    return password


async def create_superadmin(
    db: AsyncSession,
    settings: Settings,
    *,
    email: str,
    password: str | None = None,
    full_name: str = "Admin",
    password_prompt: Callable[[], str] = prompt_password,
) -> CreateSuperadminResult:
    normalized_email = email.strip().lower()
    if "@" not in normalized_email or normalized_email.startswith("@") or normalized_email.endswith("@"):
        raise CliError(f"'{email}' is not a valid email address")
    promoted_user = await SuperadminService(db).promote_by_email(normalized_email)
    if promoted_user is not None:
        return CreateSuperadminResult(user_id=promoted_user.id, email=promoted_user.email, created=False)
    resolved_password = password if password is not None else password_prompt()
    if len(resolved_password) < MIN_PASSWORD_LENGTH:
        raise CliError(f"The password must have at least {MIN_PASSWORD_LENGTH} characters")
    user = User(
        email=normalized_email,
        password_hash=hash_password(resolved_password),
        full_name=full_name,
        platform_role=PlatformRole.SUPERADMIN,
        is_email_verified=True,
        is_blocked=False,
    )
    db.add(user)
    await db.flush()
    await SignupService(db, settings).complete_signup(user)
    await db.commit()
    return CreateSuperadminResult(user_id=user.id, email=user.email, created=True)


async def seed_demo(db: AsyncSession) -> SeedDemoResult:
    user = await AdminQueryRepository(db).get_user_by_email(DEMO_USER_EMAIL)
    user_created = user is None
    if user is None:
        user = User(
            email=DEMO_USER_EMAIL,
            password_hash=hash_password(DEMO_USER_PASSWORD),
            full_name=DEMO_USER_NAME,
            platform_role=PlatformRole.USER,
            is_email_verified=True,
            is_blocked=False,
        )
        db.add(user)
        await db.flush()

    organization = await db.scalar(select(Organization).where(Organization.slug == DEMO_ORGANIZATION_SLUG))
    organization_created = organization is None
    if organization is None:
        organization = Organization(
            name=DEMO_ORGANIZATION_NAME, slug=DEMO_ORGANIZATION_SLUG, owner_id=user.id, plan_id="free"
        )
        db.add(organization)
        await db.flush()
        db.add(Membership(organization_id=organization.id, user_id=user.id, role=OrgRole.OWNER))

    existing_names = set(await db.scalars(select(Project.name).where(Project.organization_id == organization.id)))
    missing_projects = [(name, description) for name, description in DEMO_PROJECTS if name not in existing_names]
    for name, description in missing_projects:
        db.add(
            Project(
                organization_id=organization.id,
                name=name,
                description=description,
                status=ProjectStatus.ACTIVE,
                created_by_id=user.id,
            )
        )
    await db.commit()
    return SeedDemoResult(
        user_created=user_created, organization_created=organization_created, projects_created=len(missing_projects)
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="SaaS kit maintenance commands")
    subcommands = parser.add_subparsers(dest="command", required=True)
    create_command = subcommands.add_parser("create-superadmin", help="Promote or create a superadmin")
    create_command.add_argument("--email", required=True)
    create_command.add_argument("--password", help="Used only when the user does not exist yet; prompted otherwise")
    create_command.add_argument("--name", default="Admin", help="Full name for a new user")
    subcommands.add_parser("seed-demo", help="Create a demo user, organization and projects (idempotent)")
    return parser


async def run_command(arguments: argparse.Namespace, settings: Settings) -> int:
    DatabaseManager.setup(settings.DATABASE_URL)
    session_maker = DatabaseManager.session_maker
    if session_maker is None:
        raise CliError("The database is not configured")
    try:
        async with session_maker() as db:
            if arguments.command == "create-superadmin":
                result = await create_superadmin(
                    db, settings, email=arguments.email, password=arguments.password, full_name=arguments.name
                )
                action = "Created" if result.created else "Promoted"
                print(f"{action} superadmin {result.email}")
            else:
                seed_result = await seed_demo(db)
                print(
                    f"Demo data ready: user created={seed_result.user_created}, "
                    f"organization created={seed_result.organization_created}, "
                    f"projects created={seed_result.projects_created}. "
                    f"Log in as {DEMO_USER_EMAIL} / {DEMO_USER_PASSWORD}"
                )
    finally:
        await DatabaseManager.stop()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        return asyncio.run(run_command(arguments, get_settings()))
    except CliError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
