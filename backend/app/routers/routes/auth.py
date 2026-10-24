import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.schemas.auth import (
    EmailRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    StatusResponse,
    TokenRequest,
    TokenResponse,
)
from app.services.auth_service import REFRESH_TOKEN_LIFETIME, AuthService, IssuedSession
from app.services.file_storage import ObjectStorage
from app.services.google_oauth_service import (
    OAUTH_STATE_COOKIE_NAME,
    OAUTH_STATE_COOKIE_PATH,
    OAUTH_STATE_LIFETIME,
    GoogleOAuthError,
    GoogleOAuthService,
)
from app.services.user_service import UserService
from app.utils.dependencies import AppSettings, DbSession, EmailServiceDep, OptionalObjectStorage
from app.utils.exceptions import BusinessError
from app.utils.rate_limit import ClientIp, RateLimiterDep

router = APIRouter()
logger = logging.getLogger("saaskit.google_oauth")

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth"


def get_auth_service(
    db: DbSession, settings: AppSettings, email_service: EmailServiceDep, background_tasks: BackgroundTasks
) -> AuthService:
    """Build the auth service for the request."""
    return AuthService(db, settings, email_service, background_tasks)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def set_refresh_cookie(response: Response, refresh_token: str, settings: Settings) -> None:
    """Set the refresh token cookie."""
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=int(REFRESH_TOKEN_LIFETIME.total_seconds()),
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.is_secure_cookie,
        samesite="lax",
    )


def clear_refresh_cookie(response: Response, settings: Settings) -> None:
    """Clear the refresh token cookie."""
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.is_secure_cookie,
        samesite="lax",
    )


async def build_token_response(
    db: AsyncSession, issued: IssuedSession, *, storage: ObjectStorage | None = None
) -> TokenResponse:
    """Build a token response from an issued session."""
    user_response = await UserService(db).build_response(issued.user, storage=storage)
    return TokenResponse(access_token=issued.access_token, user=user_response)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    response: Response,
    db: DbSession,
    settings: AppSettings,
    auth_service: AuthServiceDep,
    rate_limiter: RateLimiterDep,
    request_ip: ClientIp,
    storage: OptionalObjectStorage,
) -> TokenResponse:
    """Register a new user and start a session."""
    rate_limiter.check("register", client_ip=request_ip, email=payload.email)
    issued = await auth_service.register(email=payload.email, password=payload.password, full_name=payload.full_name)
    set_refresh_cookie(response, issued.refresh_token, settings)
    return await build_token_response(db, issued, storage=storage)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db: DbSession,
    settings: AppSettings,
    auth_service: AuthServiceDep,
    rate_limiter: RateLimiterDep,
    request_ip: ClientIp,
    storage: OptionalObjectStorage,
) -> TokenResponse:
    """Log in with email and password."""
    rate_limiter.check("login", client_ip=request_ip, email=payload.email)
    issued = await auth_service.login(email=payload.email, password=payload.password)
    set_refresh_cookie(response, issued.refresh_token, settings)
    return await build_token_response(db, issued, storage=storage)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    db: DbSession,
    settings: AppSettings,
    auth_service: AuthServiceDep,
    storage: OptionalObjectStorage,
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> TokenResponse:
    """Rotate the refresh token and issue a new access token."""
    issued = await auth_service.refresh(refresh_token)
    set_refresh_cookie(response, issued.refresh_token, settings)
    return await build_token_response(db, issued, storage=storage)


@router.post("/logout", response_model=StatusResponse)
async def logout(
    response: Response,
    settings: AppSettings,
    auth_service: AuthServiceDep,
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> StatusResponse:
    """Log out and revoke the refresh token."""
    await auth_service.logout(refresh_token)
    clear_refresh_cookie(response, settings)
    return StatusResponse()


@router.post("/verify-email", response_model=StatusResponse)
async def verify_email(payload: TokenRequest, auth_service: AuthServiceDep) -> StatusResponse:
    """Verify the user email by token."""
    await auth_service.verify_email(payload.token)
    return StatusResponse()


@router.post("/resend-verification", response_model=StatusResponse)
async def resend_verification(
    payload: EmailRequest, auth_service: AuthServiceDep, rate_limiter: RateLimiterDep, request_ip: ClientIp
) -> StatusResponse:
    """Resend the email verification link."""
    rate_limiter.check("resend-verification", client_ip=request_ip, email=payload.email)
    await auth_service.resend_verification(payload.email)
    return StatusResponse()


@router.post("/forgot-password", response_model=StatusResponse)
async def forgot_password(
    payload: EmailRequest, auth_service: AuthServiceDep, rate_limiter: RateLimiterDep, request_ip: ClientIp
) -> StatusResponse:
    """Send a password reset link."""
    rate_limiter.check("forgot-password", client_ip=request_ip, email=payload.email)
    await auth_service.forgot_password(payload.email)
    return StatusResponse()


@router.post("/reset-password", response_model=StatusResponse)
async def reset_password(payload: ResetPasswordRequest, auth_service: AuthServiceDep) -> StatusResponse:
    """Reset the password by token."""
    await auth_service.reset_password(raw_token=payload.token, new_password=payload.password)
    return StatusResponse()


def clear_oauth_state_cookie(response: Response, settings: Settings) -> None:
    """Clear the OAuth state cookie."""
    response.delete_cookie(
        OAUTH_STATE_COOKIE_NAME,
        path=OAUTH_STATE_COOKIE_PATH,
        httponly=True,
        secure=settings.is_secure_cookie,
        samesite="lax",
    )


def login_error_redirect(settings: Settings, error_code: str) -> RedirectResponse:
    """Redirect to the login page with an error code."""
    response = RedirectResponse(f"{settings.APP_URL}/login?error={error_code}", status_code=status.HTTP_302_FOUND)
    clear_oauth_state_cookie(response, settings)
    return response


@router.get("/google/start")
async def google_start(db: DbSession, settings: AppSettings) -> RedirectResponse:
    """Redirect to Google OAuth consent screen."""
    google = GoogleOAuthService(db, settings)
    google.ensure_enabled()
    authorization_url, state_cookie = google.build_authorization()
    response = RedirectResponse(authorization_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        OAUTH_STATE_COOKIE_NAME,
        state_cookie,
        max_age=int(OAUTH_STATE_LIFETIME.total_seconds()),
        path=OAUTH_STATE_COOKIE_PATH,
        httponly=True,
        secure=settings.is_secure_cookie,
        samesite="lax",
    )
    return response


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    auth_service: AuthServiceDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Handle the Google OAuth callback and start a session."""
    google = GoogleOAuthService(db, settings)
    google.ensure_enabled()
    try:
        google.verify_state(state, request.cookies.get(OAUTH_STATE_COOKIE_NAME))
        if error or not code:
            raise GoogleOAuthError(f"Google returned no code (error={error})")
        profile = await google.fetch_profile(code)
        user = await google.resolve_user(profile)
        issued = await auth_service.start_session(user)
    except GoogleOAuthError:
        logger.warning("Google sign-in failed", exc_info=True)
        await db.rollback()
        return login_error_redirect(settings, "oauth_failed")
    except BusinessError as business_error:
        await db.rollback()
        return login_error_redirect(settings, business_error.code)
    response = RedirectResponse(f"{settings.APP_URL}/auth/callback", status_code=status.HTTP_302_FOUND)
    set_refresh_cookie(response, issued.refresh_token, settings)
    clear_oauth_state_cookie(response, settings)
    return response
