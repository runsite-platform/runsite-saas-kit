"""users and auth tokens

Revision ID: 8025f17e7b3c
Revises: 0001
Create Date: 2026-10-23 13:25:58.066031+00:00

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8025f17e7b3c"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=200), server_default="", nullable=False),
        sa.Column("avatar_key", sa.String(length=512), nullable=True),
        sa.Column("platform_role", sa.String(length=32), server_default="user", nullable=False),
        sa.Column("is_email_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_blocked", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk__users")),
        sa.UniqueConstraint("email", name=op.f("uq__users__email")),
    )
    op.create_table(
        "oauth_accounts",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_account_id", sa.String(length=255), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk__oauth_accounts__user_id__users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk__oauth_accounts")),
        sa.UniqueConstraint(
            "provider", "provider_account_id", name=op.f("uq__oauth_accounts__provider_provider_account_id")
        ),
    )
    op.create_index(op.f("ix__oauth_accounts__user_id"), "oauth_accounts", ["user_id"], unique=False)
    op.create_table(
        "auth_tokens",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk__auth_tokens__user_id__users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk__auth_tokens")),
    )
    op.create_index(op.f("ix__auth_tokens__user_id"), "auth_tokens", ["user_id"], unique=False)
    op.create_index(op.f("ix__auth_tokens__token_hash"), "auth_tokens", ["token_hash"], unique=False)
    op.create_index(op.f("ix__auth_tokens__family_id"), "auth_tokens", ["family_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix__auth_tokens__family_id"), table_name="auth_tokens")
    op.drop_index(op.f("ix__auth_tokens__token_hash"), table_name="auth_tokens")
    op.drop_index(op.f("ix__auth_tokens__user_id"), table_name="auth_tokens")
    op.drop_table("auth_tokens")
    op.drop_index(op.f("ix__oauth_accounts__user_id"), table_name="oauth_accounts")
    op.drop_table("oauth_accounts")
    op.drop_table("users")
