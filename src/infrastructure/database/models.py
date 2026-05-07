from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class SubscriptionModel(Base):
    __tablename__ = "saas_subscriptions"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    service_name        = Column(String(200), nullable=False)
    login_account       = Column(String(200), nullable=False)
    expiry_date         = Column(Date, nullable=False)
    notification_emails = Column(String(1000), nullable=False)
    notification_days   = Column(Integer, nullable=False)
    is_active           = Column(Boolean, nullable=False, default=True)
    status              = Column(String(20), nullable=False, default="active")
    cost                = Column(Numeric(10, 2), nullable=True)
    currency            = Column(String(10), nullable=False, default="TWD")
    notes               = Column(String(1000), nullable=True)
    owner_name          = Column(String(100), nullable=True)
    category            = Column(String(100), nullable=True)
    department          = Column(String(100), nullable=True)
    billing_cycle       = Column(String(20), nullable=True)
    payment_account     = Column(String(100), nullable=True)
    auto_renew          = Column(Boolean,     nullable=False, default=False)
    trial_end_date      = Column(Date,        nullable=True)
    next_billing_date   = Column(Date,        nullable=True)
    icon_emoji          = Column(String(10),  nullable=True)
    login_password      = Column(String(500), nullable=True)
    created_at          = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at          = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc))


class UserModel(Base):
    __tablename__ = "users"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    email             = Column(String(200), nullable=False, unique=True)
    display_name      = Column(String(100), nullable=False)
    hashed_password   = Column(String(255), nullable=False)
    role              = Column(String(20), nullable=False, default="user")
    can_create        = Column(Boolean, nullable=False, default=False)
    can_update        = Column(Boolean, nullable=False, default=False)
    can_delete        = Column(Boolean, nullable=False, default=False)
    is_active         = Column(Boolean, nullable=False, default=True)
    created_at        = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_login_at     = Column(DateTime, nullable=True)
    invite_token      = Column(String(100), nullable=True)
    invite_expires_at = Column(DateTime, nullable=True)


class ConfigOptionModel(Base):
    __tablename__ = "config_options"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    type       = Column(String(50), nullable=False)    # "category" | "department"
    value      = Column(String(100), nullable=False)
    parent_id  = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class AuditLogModel(Base):
    __tablename__ = "audit_log"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(Integer, nullable=False)
    user_email  = Column(String(200), nullable=False)
    action      = Column(String(20), nullable=False)   # create | update | delete
    target_type = Column(String(50), nullable=False)   # subscription
    target_id   = Column(Integer, nullable=False)
    target_name = Column(String(200), nullable=False)
    created_at  = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
