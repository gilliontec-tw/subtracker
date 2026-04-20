from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class SubscriptionModel(Base):
    __tablename__ = "saas_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String(200), nullable=False)
    login_account = Column(String(200), nullable=False)
    expiry_date = Column(Date, nullable=False)
    notification_emails = Column(String(1000), nullable=False)  # 逗號分隔多個收件人
    notification_days = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    notes = Column(String(1000), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now)


class UserModel(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    email           = Column(String(200), nullable=False, unique=True)
    display_name    = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(String(20), nullable=False, default="user")
    can_create      = Column(Boolean, nullable=False, default=False)
    can_update      = Column(Boolean, nullable=False, default=False)
    can_delete      = Column(Boolean, nullable=False, default=False)
    is_active       = Column(Boolean, nullable=False, default=True)
    created_at      = Column(DateTime, nullable=False, default=datetime.now)
    last_login_at   = Column(DateTime, nullable=True)
