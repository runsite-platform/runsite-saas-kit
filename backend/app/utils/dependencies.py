from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import BackgroundTasks, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.db import get_db_session
from app.config.settings import Settings, get_settings
from app.constants.enums import OrgRole, PlatformRole
from app.emails.contents import EmailContent
from app.models.membership import Membership
from app.models.user import User
from app.repositories.membership_repository import MembershipRepository
from app.repositories.user import UserRepository
from app.services.billing.plans import FEATURE_REQUIRED_PLAN, get_plan
from app.services.billing.providers.base import PaymentProvider
from app.services.billing.providers.factory import build_payment_provider
from app.services.email_service import EmailQueue, EmailSender, EmailService, LoggingEmailSender, RunsiteEmailSender
from app.services.file_storage import ObjectStorage, build_object_storage
from app.services.notification_service import NotificationEmail, NotificationEmailQueue
from app.utils.clock import Clock, utc_now
from app.utils.exceptions import BusinessError, forbidden, not_found
from app.utils.security import AccessTokenClaims, decode_access_token, not_authenticated

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def get_email_sender(settings: AppSettings) -> EmailSender:
    if settings.email_enabled:
        return RunsiteEmailSender(settings)
    return LoggingEmailSender(settings)


def get_email_service(settings: AppSettings, sender: Annotated[EmailSender, Depends(get_email_sender)]) -> EmailService:
    return EmailService(sender, settings)


EmailServiceDep = Annotated[EmailService, Depends(get_email_service)]


class BackgroundEmailQueue:
    """Sends emails after the response, so a slow email API never delays the request."""

    def __init__(self, background_tasks: BackgroundTasks, email_service: EmailService) -> None:
        self.background_tasks = background_tasks
        self.email_service = email_service

    def enqueue(self, to: str, content: EmailContent) -> None:
        self.background_tasks.add_task(self.email_service.send, to, content)


def get_email_queue(background_tasks: BackgroundTasks, email_service: EmailServiceDep) -> EmailQueue:
    return BackgroundEmailQueue(background_tasks, email_service)


EmailQueueDep = Annotated[EmailQueue, Depends(get_email_queue)]


class BackgroundNotificationEmailQueue:
    """Sends notification emails after the response, so a slow email API never delays the request."""

    def __init__(self, background_tasks: BackgroundTasks, email_service: EmailService) -> None:
        self.background_tasks = background_tasks
        self.email_service = email_service

    def enqueue(self, email: NotificationEmail) -> None:
        self.background_tasks.add_task(self.email_service.send_notification_email, email)


def get_notification_email_queue(
    background_tasks: BackgroundTasks, email_service: EmailServiceDep
) -> NotificationEmailQueue:
    return BackgroundNotificationEmailQueue(background_tasks, email_service)


NotificationEmailQueueDep = Annotated[NotificationEmailQueue, Depends(get_notification_email_queue)]

bearer_scheme = HTTPBearer(auto_error=False)


async def get_access_claims(
    settings: AppSettings,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> AccessTokenClaims:
    if credentials is None:
        raise not_authenticated()
    return decode_access_token(credentials.credentials, secret=settings.JWT_SECRET)


AccessClaims = Annotated[AccessTokenClaims, Depends(get_access_claims)]


async def get_current_user(claims: AccessClaims, db: DbSession) -> User:
    user = await UserRepository(db).get_by_id(id=claims.user_id)
    if user is None:
        raise not_authenticated()
    if user.is_blocked:
        raise BusinessError("user_blocked", "This account is blocked", status_code=403)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_verified_email(user: CurrentUser, settings: AppSettings) -> User:
    if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_email_verified:
        raise BusinessError("email_not_verified", "Verify your email address first", status_code=403)
    return user


VerifiedUser = Annotated[User, Depends(require_verified_email)]

MembershipDependency = Callable[..., Awaitable[Membership]]


async def get_current_membership(org_id: UUID, user: CurrentUser, db: DbSession) -> Membership:
    membership = await MembershipRepository(db).get_for_user(org_id, user.id)
    if membership is None:
        raise not_found("Organization")
    return membership


CurrentMembership = Annotated[Membership, Depends(get_current_membership)]


def require_org_role(*roles: OrgRole) -> MembershipDependency:
    allowed_roles = tuple(roles)

    async def check_org_role(membership: CurrentMembership) -> Membership:
        if membership.role not in allowed_roles:
            raise forbidden()
        return membership

    return check_org_role


def require_feature(feature: str) -> MembershipDependency:
    async def check_feature(membership: CurrentMembership) -> Membership:
        plan = get_plan(membership.organization.plan_id)
        if feature not in plan.features:
            raise BusinessError(
                "plan_upgrade_required",
                f"The {plan.name} plan does not include {feature}",
                status_code=402,
                details={"feature": feature, "required_plan": FEATURE_REQUIRED_PLAN.get(feature, "pro")},
            )
        return membership

    return check_feature


OrgManagerMembership = Annotated[Membership, Depends(require_org_role(OrgRole.OWNER, OrgRole.ADMIN))]
OrgOwnerMembership = Annotated[Membership, Depends(require_org_role(OrgRole.OWNER))]


def get_object_storage(settings: AppSettings) -> ObjectStorage | None:
    return build_object_storage(settings)


OptionalObjectStorage = Annotated[ObjectStorage | None, Depends(get_object_storage)]


def get_payment_provider(settings: AppSettings) -> PaymentProvider | None:
    return build_payment_provider(settings)


def get_clock() -> Clock:
    return utc_now


def require_platform_role(*roles: PlatformRole) -> Callable[..., Awaitable[User]]:
    allowed_roles = frozenset(roles)

    async def ensure_platform_role(claims: AccessClaims, user: CurrentUser) -> User:
        if claims.impersonated_by is not None:
            raise BusinessError("forbidden", "Platform admin is not available while impersonating", 403)
        if user.platform_role not in allowed_roles:
            raise BusinessError("forbidden", "You do not have permission to do this", 403)
        return user

    return ensure_platform_role


PlatformStaffUser = Annotated[User, Depends(require_platform_role(PlatformRole.ADMIN, PlatformRole.SUPERADMIN))]
SuperadminUser = Annotated[User, Depends(require_platform_role(PlatformRole.SUPERADMIN))]
