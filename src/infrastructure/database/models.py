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
    responsible_person_email = Column(String(200), nullable=False)
    notification_days = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now)
