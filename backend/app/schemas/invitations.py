from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.utils.security import normalize_email

InvitableRole = Literal["admin", "member"]


class InvitationCreateRequest(BaseModel):
    email: EmailStr
    role: InvitableRole = "member"

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return normalize_email(value)


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: str
    expires_at: datetime
    created_at: datetime


class InvitationCreatedResponse(BaseModel):
    invitation: InvitationResponse
    invite_url: str


class InvitationPreviewResponse(BaseModel):
    organization_name: str
    inviter_name: str | None
    email: str
    role: str
    expired: bool
