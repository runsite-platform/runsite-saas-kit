from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class MemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    email: str
    full_name: str | None
    role: str
    joined_at: datetime


class MemberRoleUpdateRequest(BaseModel):
    role: Literal["admin", "member"]
