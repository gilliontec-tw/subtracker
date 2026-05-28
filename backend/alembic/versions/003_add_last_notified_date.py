"""add last_notified_date to saas_subscriptions

Revision ID: 003
Revises: 002
Create Date: 2026-05-28

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "saas_subscriptions",
        sa.Column("last_notified_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("saas_subscriptions", "last_notified_date")
