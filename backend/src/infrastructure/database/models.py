from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    password_hash = Column(String(255))
    role = Column(String(20), nullable=False, server_default="user")
    can_create = Column(Boolean, nullable=False, server_default="false")
    can_update = Column(Boolean, nullable=False, server_default="false")
    can_delete = Column(Boolean, nullable=False, server_default="false")
    is_active = Column(Boolean, nullable=False, server_default="true")
    invite_token = Column(String(255), unique=True)
    invite_token_expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SubscriptionModel(Base):
    __tablename__ = "saas_subscriptions"

    id = Column(Integer, primary_key=True)
    service_name = Column(String(255), nullable=False)
    login_account = Column(String(255))
    expiry_date = Column(Date, nullable=False)
    notification_emails = Column(Text)  # JSON-encoded list of email strings
    notification_days = Column(Integer, server_default="30")
    cost = Column(Numeric(10, 2))
    currency = Column(String(10), server_default="TWD")
    exchange_rate = Column(Numeric(12, 6))  # 1 foreign unit = ? TWD; NULL = not set
    notes = Column(Text)
    owner_name = Column(String(255))
    category = Column(String(100))
    department = Column(String(100))
    billing_cycle = Column(String(20))  # monthly|quarterly|semi_annual|annual|biennial
    payment_account = Column(String(255))
    auto_renew = Column(Boolean, server_default="false")
    trial_end_date = Column(Date)
    next_billing_date = Column(Date)
    last_notified_date = Column(Date)
    status = Column(String(20), server_default="active")  # active|suspended
    deleted_at = Column(DateTime(timezone=True))  # NULL = not deleted (soft delete)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    payments = relationship("PaymentRecordModel", back_populates="subscription")


class PaymentRecordModel(Base):
    __tablename__ = "payment_records"

    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("saas_subscriptions.id"), nullable=False)
    payment_date = Column(Date, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), nullable=False, server_default="TWD")
    source = Column(String(10), nullable=False, server_default="manual")  # auto|manual
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"))

    subscription = relationship("SubscriptionModel", back_populates="payments")


class AuditLogModel(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(Integer)
    details = Column(Text)  # JSON-encoded dict
    created_at = Column(DateTime(timezone=True), server_default=func.now())
