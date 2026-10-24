import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.constants.enums import BillingInterval, OrgRole, PlatformRole, ProjectStatus, SubscriptionStatus
from app.models.invitation import Invitation
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.project import Project
from app.models.stored_file import StoredFile
from app.models.subscription import Subscription
from app.models.user import User
from app.utils.security import create_access_token, generate_token, hash_password, hash_token, normalize_email, utc_now
from app.utils.slugs import slugify


async def create_user(
    session: AsyncSession,
    *,
    email: str | None = None,
    password: str | None = "password123",
    full_name: str = "Test User",
    platform_role: PlatformRole = PlatformRole.USER,
    is_email_verified: bool = True,
    is_blocked: bool = False,
) -> User:
    user = User(
        email=normalize_email(email or f"user-{uuid.uuid4().hex[:12]}@example.com"),
        password_hash=hash_password(password) if password is not None else None,
        full_name=full_name,
        platform_role=platform_role,
        is_email_verified=is_email_verified,
        is_blocked=is_blocked,
    )
    session.add(user)
    await session.flush()
    return user


async def auth_headers(user: User, *, settings: Settings, impersonated_by: UUID | None = None) -> dict[str, str]:
    token = create_access_token(user.id, secret=settings.JWT_SECRET, impersonated_by=impersonated_by)
    return {"Authorization": f"Bearer {token}"}


async def create_organization(
    session: AsyncSession,
    *,
    owner: User,
    name: str = "Acme",
    slug: str | None = None,
    plan_id: str = "free",
) -> Organization:
    organization = Organization(
        name=name,
        slug=slug or f"{slugify(name)}-{uuid.uuid4().hex[:8]}",
        owner_id=owner.id,
        plan_id=plan_id,
    )
    session.add(organization)
    await session.flush()
    session.add(Membership(organization_id=organization.id, user_id=owner.id, role=OrgRole.OWNER))
    await session.flush()
    return organization


async def add_member(
    session: AsyncSession, *, organization: Organization, user: User, role: OrgRole = OrgRole.MEMBER
) -> Membership:
    membership = Membership(organization_id=organization.id, user_id=user.id, role=role)
    session.add(membership)
    await session.flush()
    return membership


async def create_invitation(
    session: AsyncSession,
    *,
    organization: Organization,
    invited_by: User,
    email: str = "invitee@example.com",
    role: OrgRole = OrgRole.MEMBER,
    expires_in: timedelta = timedelta(days=7),
    accepted: bool = False,
) -> tuple[Invitation, str]:
    token = generate_token()
    now = utc_now()
    invitation = Invitation(
        organization_id=organization.id,
        email=normalize_email(email),
        role=role,
        token_hash=hash_token(token),
        invited_by_id=invited_by.id,
        expires_at=now + expires_in,
        accepted_at=now if accepted else None,
    )
    session.add(invitation)
    await session.flush()
    return invitation, token


async def create_project(
    session: AsyncSession,
    *,
    organization: Organization,
    created_by: User,
    name: str = "Project",
    status: ProjectStatus = ProjectStatus.ACTIVE,
) -> Project:
    project = Project(
        organization_id=organization.id,
        name=name,
        status=status,
        created_by_id=created_by.id,
    )
    session.add(project)
    await session.flush()
    return project


async def create_stored_file(
    session: AsyncSession,
    *,
    organization: Organization,
    uploaded_by: User,
    name: str = "file.txt",
    size_bytes: int = 10,
    content_type: str = "text/plain",
) -> StoredFile:
    stored_file = StoredFile(
        organization_id=organization.id,
        uploaded_by_id=uploaded_by.id,
        storage_key=f"orgs/{organization.id}/files/{uuid.uuid4()}-{name}",
        name=name,
        size_bytes=size_bytes,
        content_type=content_type,
    )
    session.add(stored_file)
    await session.flush()
    return stored_file


async def create_subscription(
    session: AsyncSession,
    *,
    organization: Organization,
    provider: str = "stripe",
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
    plan_id: str = "pro",
    interval: BillingInterval = BillingInterval.MONTHLY,
) -> Subscription:
    subscription = Subscription(
        organization_id=organization.id,
        provider=provider,
        provider_subscription_id=f"sub_{uuid4().hex}",
        plan_id=plan_id,
        interval=interval,
        status=status,
        current_period_end=datetime.now(UTC) + timedelta(days=30),
        cancel_at_period_end=False,
        trial_ends_at=None,
    )
    session.add(subscription)
    await session.flush()
    return subscription
