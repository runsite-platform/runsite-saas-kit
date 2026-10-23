"""organizations, memberships, invitations

Revision ID: 3c0a9e51b7d2
Revises: 8025f17e7b3c
Create Date: 2026-10-23 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3c0a9e51b7d2"
down_revision: str | Sequence[str] | None = "8025f17e7b3c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("logo_key", sa.String(length=512), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("plan_id", sa.String(length=32), server_default="free", nullable=False),
        sa.Column("billing_provider", sa.String(length=32), nullable=True),
        sa.Column("billing_customer_id", sa.String(length=255), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="fk__organizations__owner_id__users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk__organizations"),
    )
    op.create_index("ix__organizations__slug", "organizations", ["slug"], unique=True)
    op.create_index("ix__organizations__owner_id", "organizations", ["owner_id"], unique=False)

    op.create_table(
        "memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk__memberships__organization_id__organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk__memberships__user_id__users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk__memberships"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq__memberships__organization_id_user_id"),
    )
    op.create_index("ix__memberships__user_id", "memberships", ["user_id"], unique=False)

    op.create_table(
        "invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("invited_by_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk__invitations__organization_id__organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by_id"], ["users.id"], name="fk__invitations__invited_by_id__users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk__invitations"),
    )
    op.create_index("ix__invitations__token_hash", "invitations", ["token_hash"], unique=True)
    op.create_index("ix__invitations__organization_id_email", "invitations", ["organization_id", "email"], unique=False)


def downgrade() -> None:
    op.drop_index("ix__invitations__organization_id_email", table_name="invitations")
    op.drop_index("ix__invitations__token_hash", table_name="invitations")
    op.drop_table("invitations")
    op.drop_index("ix__memberships__user_id", table_name="memberships")
    op.drop_table("memberships")
    op.drop_index("ix__organizations__owner_id", table_name="organizations")
    op.drop_index("ix__organizations__slug", table_name="organizations")
    op.drop_table("organizations")
