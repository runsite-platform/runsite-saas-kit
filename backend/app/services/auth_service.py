import uuid
from dataclasses import dataclass
from datetime import timedelta

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.models.auth_token import AuthToken
from app.constants.enums import AuthTokenKind
from app.models.user import User
from app.repositories.auth_token import AuthTokenRepository
from app.repositories.user import UserRepository
from app.services.email_service import EmailService
from app.services.signup_service import SignupService
from app.utils.exceptions import BusinessError
from app.utils.security import (
    create_access_token,
    generate_token,
    hash_password,
    hash_token,
    normalize_email,
    not_authenticated,
    utc_now,
    verify_password,
)

ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_LIFETIME = timedelta(days=30)
EMAIL_VERIFY_TOKEN_LIFETIME = timedelta(hours=24)
PASSWORD_RESET_TOKEN_LIFETIME = timedelta(hours=1)


@dataclass(frozen=True)
class IssuedSession:
    """Authenticated user with a fresh access and refresh token pair."""

    user: User
    access_token: str
    refresh_token: str


def invalid_credentials() -> BusinessError:
    """Return the error for a wrong email or password."""
    return BusinessError("invalid_credentials", "Invalid email or password", status_code=401)


def user_blocked() -> BusinessError:
    """Return the error for a blocked account."""
    return BusinessError("user_blocked", "This account is blocked", status_code=403)


def invalid_token() -> BusinessError:
    """Return the error for an invalid or expired link token."""
    return BusinessError("invalid_token", "This link is invalid or has expired", status_code=400)


class AuthService:
    """Service for password authentication and session management."""

    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        email_service: EmailService,
        background_tasks: BackgroundTasks,
    ) -> None:
        self.db = db
        self.settings = settings
        self.email_service = email_service
        self.background_tasks = background_tasks
        self.users = UserRepository(db)
        self.tokens = AuthTokenRepository(db)

    async def register(self, *, email: str, password: str, full_name: str) -> IssuedSession:
        """Create a user with a password and start a session."""
        normalized_email = normalize_email(email)
        if await self.users.get_by_email(normalized_email) is not None:
            raise BusinessError("email_taken", "An account with this email already exists", status_code=409)
        verification_required = self.settings.REQUIRE_EMAIL_VERIFICATION
        user = await self.users.add(
            User(
                email=normalized_email,
                password_hash=hash_password(password),
                full_name=full_name.strip(),
                is_email_verified=not verification_required,
            )
        )
        await SignupService(self.db, self.settings).complete_signup(user)
        if verification_required:
            await self._schedule_verification_email(user)
        return await self.start_session(user)

    async def login(self, *, email: str, password: str) -> IssuedSession:
        """Authenticate by email and password and start a session."""
        user = await self.users.get_by_email(email)
        if user is None or user.password_hash is None or not verify_password(password, user.password_hash):
            raise invalid_credentials()
        return await self.start_session(user)

    async def start_session(self, user: User) -> IssuedSession:
        """Record the login and issue a new session for the user."""
        if user.is_blocked:
            raise user_blocked()
        user.last_login_at = utc_now()
        issued = await self._issue_session(user, family_id=uuid.uuid4())
        await self.db.commit()
        return issued

    async def refresh(self, raw_token: str | None) -> IssuedSession:
        """Rotate a refresh token, revoking its family on reuse."""
        if not raw_token:
            raise not_authenticated()
        stored = await self.tokens.get_by_hash(hash_token(raw_token), AuthTokenKind.REFRESH)
        if stored is None:
            raise not_authenticated()
        now = utc_now()
        if stored.used_at is not None:
            if stored.family_id is not None:
                await self.tokens.revoke_family(stored.family_id, now)
            await self.db.commit()
            raise not_authenticated("Refresh token was already used")
        if stored.expires_at <= now:
            raise not_authenticated("Refresh token expired")
        user = await self.users.get_by_id(id=stored.user_id)
        if user is None:
            raise not_authenticated()
        if user.is_blocked:
            raise user_blocked()
        stored.used_at = now
        issued = await self._issue_session(user, family_id=stored.family_id or uuid.uuid4())
        await self.db.commit()
        return issued

    async def logout(self, raw_token: str | None) -> None:
        """Mark the given refresh token as used."""
        if not raw_token:
            return
        stored = await self.tokens.get_by_hash(hash_token(raw_token), AuthTokenKind.REFRESH)
        if stored is not None and stored.used_at is None:
            stored.used_at = utc_now()
            await self.db.commit()

    async def verify_email(self, raw_token: str) -> None:
        """Consume a verification token and mark the email verified."""
        user = await self._consume_single_use_token(raw_token, AuthTokenKind.EMAIL_VERIFY)
        user.is_email_verified = True
        await self.db.commit()

    async def resend_verification(self, email: str) -> None:
        """Send a new verification email if the user still needs one."""
        user = await self.users.get_by_email(email)
        if user is None or user.is_email_verified or user.is_blocked:
            return
        await self._schedule_verification_email(user)
        await self.db.commit()

    async def forgot_password(self, email: str) -> None:
        """Send a password reset email if the user exists and is active."""
        user = await self.users.get_by_email(email)
        if user is None or user.is_blocked:
            return
        token = await self._create_single_use_token(user, AuthTokenKind.PASSWORD_RESET, PASSWORD_RESET_TOKEN_LIFETIME)
        self.background_tasks.add_task(self.email_service.send_password_reset_email, user, token)
        await self.db.commit()

    async def reset_password(self, *, raw_token: str, new_password: str) -> None:
        """Consume a reset token, set the new password and revoke sessions."""
        user = await self._consume_single_use_token(raw_token, AuthTokenKind.PASSWORD_RESET)
        user.password_hash = hash_password(new_password)
        user.is_email_verified = True
        await self.tokens.revoke_for_user(user.id, AuthTokenKind.REFRESH, utc_now())
        await self.db.commit()

    async def _consume_single_use_token(self, raw_token: str, kind: AuthTokenKind) -> User:
        stored = await self.tokens.get_by_hash(hash_token(raw_token), kind)
        now = utc_now()
        if stored is None or stored.used_at is not None or stored.expires_at <= now:
            raise invalid_token()
        user = await self.users.get_by_id(id=stored.user_id)
        if user is None:
            raise invalid_token()
        stored.used_at = now
        return user

    async def _issue_session(self, user: User, *, family_id: uuid.UUID) -> IssuedSession:
        refresh_token = generate_token()
        await self.tokens.add(
            AuthToken(
                user_id=user.id,
                kind=AuthTokenKind.REFRESH,
                token_hash=hash_token(refresh_token),
                family_id=family_id,
                expires_at=utc_now() + REFRESH_TOKEN_LIFETIME,
            )
        )
        access_token = create_access_token(
            user.id, secret=self.settings.JWT_SECRET, expires_minutes=ACCESS_TOKEN_MINUTES
        )
        return IssuedSession(user=user, access_token=access_token, refresh_token=refresh_token)

    async def _create_single_use_token(self, user: User, kind: AuthTokenKind, lifetime: timedelta) -> str:
        raw_token = generate_token()
        await self.tokens.add(
            AuthToken(user_id=user.id, kind=kind, token_hash=hash_token(raw_token), expires_at=utc_now() + lifetime)
        )
        return raw_token

    async def _schedule_verification_email(self, user: User) -> None:
        token = await self._create_single_use_token(user, AuthTokenKind.EMAIL_VERIFY, EMAIL_VERIFY_TOKEN_LIFETIME)
        self.background_tasks.add_task(self.email_service.send_verification_email, user, token)
