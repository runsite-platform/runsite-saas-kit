import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.utils.exceptions import BusinessError

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
BCRYPT_ROUNDS = 12
BCRYPT_MAX_PASSWORD_BYTES = 72


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: UUID
    impersonated_by: UUID | None


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def not_authenticated(message: str = "Not authenticated") -> BusinessError:
    return BusinessError("not_authenticated", message, status_code=401)


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(_password_bytes(password), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_password_bytes(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    user_id: UUID, *, secret: str, impersonated_by: UUID | None = None, expires_minutes: int = 15
) -> str:
    issued_at = utc_now()
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=expires_minutes),
    }
    if impersonated_by is not None:
        claims["imp"] = str(impersonated_by)
    return jwt.encode(claims, secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, *, secret: str) -> AccessTokenClaims:
    try:
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
    except JWTError as error:
        raise not_authenticated("Invalid or expired access token") from error
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise not_authenticated("Invalid access token")
    try:
        user_id = UUID(str(payload["sub"]))
        impersonator_claim = payload.get("imp")
        impersonated_by = UUID(str(impersonator_claim)) if impersonator_claim else None
    except (KeyError, ValueError) as error:
        raise not_authenticated("Invalid access token") from error
    return AccessTokenClaims(user_id=user_id, impersonated_by=impersonated_by)
