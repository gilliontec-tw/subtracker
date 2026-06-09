"""add asset_types table and asset_type_id to subscriptions

Revision ID: 005
Revises: 004
Create Date: 2026-06-09

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "asset_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "saas_subscriptions",
        sa.Column("asset_type_id", sa.Integer(), sa.ForeignKey("asset_types.id"), nullable=True),
    )
    op.execute("INSERT INTO asset_types (name) VALUES ('SaaS'), ('ERP'), ('網域')")


def downgrade() -> None:
    op.drop_column("saas_subscriptions", "asset_type_id")
    op.drop_table("asset_types")
