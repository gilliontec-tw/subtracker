"""add exchange_rate to saas_subscriptions

Revision ID: 002
Revises: 001
Create Date: 2026-05-20

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "saas_subscriptions",
        sa.Column("exchange_rate", sa.Numeric(12, 6)),
    )


def downgrade() -> None:
    op.drop_column("saas_subscriptions", "exchange_rate")
