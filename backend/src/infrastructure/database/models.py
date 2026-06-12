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


class GroupModel(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("UserGroupModel", back_populates="group", cascade="all, delete-orphan")
    subscriptions = relationship("SubscriptionModel", back_populates="group", passive_deletes=True)


class UserGroupModel(Base):
    __tablename__ = "user_groups"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("GroupModel", back_populates="members")


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    password_hash = Column(String(255))
    role = Column(String(20), nullable=False, server_default="user")
    is_active = Column(Boolean, nullable=False, server_default="true")
    invite_token = Column(String(255), unique=True)
    invite_token_expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AssetTypeModel(Base):
    __tablename__ = "asset_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SubscriptionModel(Base):
    __tablename__ = "saas_subscriptions"

    id = Column(Integer, primary_key=True)
    service_name = Column(String(255), nullable=False)
    login_account = Column(String(255))
    expiry_date = Column(Date, nullable=False)
    notification_emails = Column(Text)
    notification_days = Column(Integer, server_default="30")
    cost = Column(Numeric(10, 2))
    currency = Column(String(10), server_default="TWD")
    exchange_rate = Column(Numeric(12, 6))
    notes = Column(Text)
    owner_name = Column(String(255))
    login_password = Column(String(255))
    department = Column(String(100))
    billing_cycle = Column(String(20))
    payment_account = Column(String(255))
    auto_renew = Column(Boolean, server_default="false")
    trial_end_date = Column(Date)
    next_billing_date = Column(Date)
    last_notified_date = Column(Date)
    status = Column(String(20), server_default="active")
    asset_type_id = Column(Integer, ForeignKey("asset_types.id"), nullable=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    payments = relationship("PaymentRecordModel", back_populates="subscription")
    group = relationship("GroupModel", back_populates="subscriptions")


class PaymentRecordModel(Base):
    __tablename__ = "payment_records"

    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("saas_subscriptions.id"), nullable=False)
    payment_date = Column(Date, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), nullable=False, server_default="TWD")
    source = Column(String(10), nullable=False, server_default="manual")
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
    details = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SystemSettingModel(Base):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
