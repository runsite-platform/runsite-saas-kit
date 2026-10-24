from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, false
from sqlalchemy.orm import Mapped, mapped_column

from app.config.db import Base
from app.constants.enums import PlatformRole
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(200), default="", server_default="")
    avatar_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    platform_role: Mapped[str] = mapped_column(
        String(32), default=PlatformRole.USER, server_default=PlatformRole.USER.value
    )
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
