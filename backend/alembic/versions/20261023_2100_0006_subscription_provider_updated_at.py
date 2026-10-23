"""subscription provider_updated_at

Revision ID: 0006_subscription_updated_at
Revises: 0005_billing
Create Date: 2026-10-23 21:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_subscription_updated_at"
down_revision: str | Sequence[str] | None = "0005_billing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("provider_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("subscriptions", "provider_updated_at")
