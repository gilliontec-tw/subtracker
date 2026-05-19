"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-19

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("can_create", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("can_update", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("can_delete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("invite_token", sa.String(255), unique=True),
        sa.Column("invite_token_expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "saas_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_name", sa.String(255), nullable=False),
        sa.Column("login_account", sa.String(255)),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("notification_emails", sa.Text()),
        sa.Column("notification_days", sa.Integer(), server_default="30"),
        sa.Column("cost", sa.Numeric(10, 2)),
        sa.Column("currency", sa.String(10), server_default="TWD"),
        sa.Column("notes", sa.Text()),
        sa.Column("owner_name", sa.String(255)),
        sa.Column("category", sa.String(100)),
        sa.Column("department", sa.String(100)),
        sa.Column("billing_cycle", sa.String(20)),
        sa.Column("payment_account", sa.String(255)),
        sa.Column("auto_renew", sa.Boolean(), server_default="false"),
        sa.Column("trial_end_date", sa.Date()),
        sa.Column("next_billing_date", sa.Date()),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_saas_subscriptions_expiry_date", "saas_subscriptions", ["expiry_date"])
    op.create_index("ix_saas_subscriptions_status", "saas_subscriptions", ["status"])

    op.create_table(
        "payment_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "subscription_id",
            sa.Integer(),
            sa.ForeignKey("saas_subscriptions.id"),
            nullable=False,
        ),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="TWD"),
        sa.Column("source", sa.String(10), nullable=False, server_default="manual"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_payment_records_subscription_id", "payment_records", ["subscription_id"])
    op.create_index("ix_payment_records_payment_date", "payment_records", ["payment_date"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50)),
        sa.Column("resource_id", sa.Integer()),
        sa.Column("details", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("payment_records")
    op.drop_table("saas_subscriptions")
    op.drop_table("users")
