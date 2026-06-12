"""add groups table, user_groups join, subscription group_id, remove can_* from users

Revision ID: 006
Revises: 005
Create Date: 2026-06-12

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create groups table
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # Create user_groups join table
    op.create_table(
        "user_groups",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id"), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # Add group_id to saas_subscriptions
    op.add_column(
        "saas_subscriptions",
        sa.Column("group_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_saas_subscriptions_group_id", "saas_subscriptions", "groups", ["group_id"], ["id"]
    )

    # Drop can_* columns from users
    op.drop_column("users", "can_create")
    op.drop_column("users", "can_update")
    op.drop_column("users", "can_delete")


def downgrade() -> None:
    # Restore can_* columns
    op.add_column(
        "users", sa.Column("can_delete", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column(
        "users", sa.Column("can_update", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column(
        "users", sa.Column("can_create", sa.Boolean(), nullable=False, server_default="false")
    )

    # Remove group_id from saas_subscriptions
    op.drop_constraint("fk_saas_subscriptions_group_id", "saas_subscriptions", type_="foreignkey")
    op.drop_column("saas_subscriptions", "group_id")

    # Drop tables
    op.drop_table("user_groups")
    op.drop_table("groups")
