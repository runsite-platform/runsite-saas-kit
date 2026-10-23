from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.user import User
from app.schemas.organizations import OrganizationSummary
from app.services.file_storage import presigned_url_or_none

if TYPE_CHECKING:
    from app.services.file_storage import ObjectStorage

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 72


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    avatar_url: str | None
    platform_role: str
    is_email_verified: bool
    has_password: bool
    google_linked: bool
    created_at: datetime

    @classmethod
    def from_user(
        cls, user: User, *, storage: "ObjectStorage | None" = None, google_linked: bool = False
    ) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=presigned_url_or_none(storage, user.avatar_key),
            platform_role=user.platform_role,
            is_email_verified=user.is_email_verified,
            has_password=user.password_hash is not None,
            google_linked=google_linked,
            created_at=user.created_at,
        )


class MeResponse(BaseModel):
    user: UserResponse
    organizations: list[OrganizationSummary]
    impersonated_by: UUID | None = None


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)


class ChangePasswordRequest(BaseModel):
    current_password: str | None = Field(default=None, max_length=PASSWORD_MAX_LENGTH)
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
