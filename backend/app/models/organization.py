import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    logo_key: Mapped[str | None] = mapped_column(String(512))
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    plan_id: Mapped[str] = mapped_column(String(32), default="free", server_default="free")
    billing_provider: Mapped[str | None] = mapped_column(String(32))
    billing_customer_id: Mapped[str | None] = mapped_column(String(255))
    plan_override_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    plan_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
