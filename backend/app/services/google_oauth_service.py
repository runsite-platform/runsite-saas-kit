import secrets
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.constants.enums import AuthTokenKind
from app.models.oauth_account import GOOGLE_PROVIDER, OAuthAccount
from app.models.user import User
from app.repositories.auth_token import AuthTokenRepository
from app.repositories.oauth_account import OAuthAccountRepository
from app.repositories.user import UserRepository
from app.services.signup_service import SignupService
from app.utils.exceptions import BusinessError
from app.utils.security import JWT_ALGORITHM, generate_token, normalize_email, utc_now

GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_SCOPES = "openid email profile"
GOOGLE_HTTP_TIMEOUT_SECONDS = 15.0
OAUTH_STATE_COOKIE_NAME = "google_oauth_state"
OAUTH_STATE_COOKIE_PATH = "/api/auth/google"
OAUTH_STATE_LIFETIME = timedelta(minutes=10)
OAUTH_STATE_TOKEN_TYPE = "oauth_state"


class GoogleOAuthError(Exception):
    """Error raised when the Google OAuth flow fails."""

    pass


@dataclass(frozen=True)
class GoogleProfile:
    """Google account profile returned by the userinfo endpoint."""

    account_id: str
    email: str
    email_verified: bool
    full_name: str


class GoogleOAuthService:
    """Service for Google OAuth login."""

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.users = UserRepository(db)
        self.oauth_accounts = OAuthAccountRepository(db)

    @property
    def redirect_uri(self) -> str:
        """Return the OAuth callback URL."""
        return f"{self.settings.APP_URL}/api/auth/google/callback"

    def ensure_enabled(self) -> None:
        """Raise if Google login is not configured."""
        if not self.settings.google_login_enabled:
            raise BusinessError("google_login_disabled", "Google login is not configured", status_code=404)

    def build_authorization(self) -> tuple[str, str]:
        """Return the Google authorization URL and a signed state cookie."""
        state = generate_token()
        query = urlencode(
            {
                "client_id": self.settings.GOOGLE_CLIENT_ID,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "scope": GOOGLE_SCOPES,
                "state": state,
                "prompt": "select_account",
            }
        )
        state_cookie = jwt.encode(
            {"type": OAUTH_STATE_TOKEN_TYPE, "state": state, "exp": utc_now() + OAUTH_STATE_LIFETIME},
            self.settings.JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )
        return f"{GOOGLE_AUTHORIZATION_URL}?{query}", state_cookie

    def verify_state(self, state: str | None, state_cookie: str | None) -> None:
        """Raise if the OAuth state does not match the signed cookie."""
        if not state or not state_cookie:
            raise GoogleOAuthError("Missing OAuth state")
        try:
            payload = jwt.decode(state_cookie, self.settings.JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except JWTError as error:
            raise GoogleOAuthError("Invalid OAuth state cookie") from error
        expected_state = payload.get("state")
        if (
            payload.get("type") != OAUTH_STATE_TOKEN_TYPE
            or not isinstance(expected_state, str)
            or not secrets.compare_digest(expected_state.encode(), state.encode())
        ):
            raise GoogleOAuthError("OAuth state mismatch")

    async def fetch_profile(self, code: str) -> GoogleProfile:
        """Exchange the code for a token and return the Google profile."""
        try:
            async with httpx.AsyncClient(timeout=GOOGLE_HTTP_TIMEOUT_SECONDS) as http_client:
                token_response = await http_client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "code": code,
                        "client_id": self.settings.GOOGLE_CLIENT_ID,
                        "client_secret": self.settings.GOOGLE_CLIENT_SECRET,
                        "redirect_uri": self.redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )
                token_response.raise_for_status()
                google_access_token = token_response.json()["access_token"]
                userinfo_response = await http_client.get(
                    GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {google_access_token}"}
                )
                userinfo_response.raise_for_status()
                userinfo = userinfo_response.json()
        except (httpx.HTTPError, KeyError, ValueError) as error:
            raise GoogleOAuthError("Google token exchange failed") from error
        account_id = userinfo.get("sub")
        email = userinfo.get("email")
        if not isinstance(account_id, str) or not account_id or not isinstance(email, str) or not email:
            raise GoogleOAuthError("Google profile has no id or email")
        return GoogleProfile(
            account_id=account_id,
            email=normalize_email(email),
            email_verified=userinfo.get("email_verified") is True,
            full_name=str(userinfo.get("name") or ""),
        )

    async def resolve_user(self, profile: GoogleProfile) -> User:
        """Return the user for the Google profile, linking or creating one."""
        linked_account = await self.oauth_accounts.get_by_provider_account(GOOGLE_PROVIDER, profile.account_id)
        if linked_account is not None:
            linked_user = await self.users.get_by_id(id=linked_account.user_id)
            if linked_user is None:
                raise GoogleOAuthError("Linked user no longer exists")
            return linked_user
        if not profile.email_verified:
            raise GoogleOAuthError("Google email is not verified")
        user = await self.users.get_by_email(profile.email)
        if user is None:
            user = await self.users.add(
                User(email=profile.email, password_hash=None, full_name=profile.full_name, is_email_verified=True)
            )
            await SignupService(self.db, self.settings).complete_signup(user)
        else:
            await self._secure_unproven_account(user)
            user.is_email_verified = True
        await self.oauth_accounts.add(
            OAuthAccount(user_id=user.id, provider=GOOGLE_PROVIDER, provider_account_id=profile.account_id)
        )
        return user

    async def _secure_unproven_account(self, user: User) -> None:
        email_was_proven = self.settings.REQUIRE_EMAIL_VERIFICATION and user.is_email_verified
        if email_was_proven:
            return
        # Whoever registered this email never proved owning it, so drop their password and sessions
        user.password_hash = None
        await AuthTokenRepository(self.db).revoke_for_user(user.id, AuthTokenKind.REFRESH, utc_now())
