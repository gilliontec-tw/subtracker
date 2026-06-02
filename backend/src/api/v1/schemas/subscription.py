from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, field_validator

CurrencyType = Literal["TWD", "USD", "EUR", "JPY", "GBP", "CNY"]


class SubscriptionCreate(BaseModel):
    service_name: str
    expiry_date: date
    login_account: str = ""
    notification_emails: list[str] = []
    notification_days: int = 30
    cost: Decimal | None = None
    currency: CurrencyType = "TWD"
    exchange_rate: Decimal | None = None
    notes: str | None = None
    owner_name: str | None = None
    category: str | None = None
    department: str | None = None
    billing_cycle: str | None = None
    payment_account: str | None = None
    auto_renew: bool = False
    trial_end_date: date | None = None
    next_billing_date: date | None = None
    status: str = "active"


class SubscriptionUpdate(BaseModel):
    service_name: str | None = None
    expiry_date: date | None = None
    login_account: str | None = None
    notification_emails: list[str] | None = None
    notification_days: int | None = None
    cost: Decimal | None = None
    currency: CurrencyType | None = None
    exchange_rate: Decimal | None = None
    notes: str | None = None
    owner_name: str | None = None
    category: str | None = None
    department: str | None = None
    billing_cycle: str | None = None
    payment_account: str | None = None
    auto_renew: bool | None = None
    trial_end_date: date | None = None
    next_billing_date: date | None = None
    status: str | None = None


class SubscriptionResponse(BaseModel):
    id: int
    service_name: str
    login_account: str
    expiry_date: date
    notification_emails: list[str]
    notification_days: int
    cost: Decimal | None
    currency: str
    exchange_rate: Decimal | None
    notes: str | None
    owner_name: str | None
    category: str | None
    department: str | None
    billing_cycle: str | None
    payment_account: str | None
    auto_renew: bool
    trial_end_date: date | None
    next_billing_date: date | None
    status: str
    created_at: datetime | None
    updated_at: datetime | None


class BatchRenewRequest(BaseModel):
    subscription_ids: list[int]

    @field_validator("subscription_ids")
    @classmethod
    def validate_ids(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("subscription_ids must not be empty")
        if any(i <= 0 for i in v):
            raise ValueError("all subscription_ids must be positive integers")
        if len(v) != len(set(v)):
            raise ValueError("subscription_ids must not contain duplicates")
        return v


class BatchRenewSkipped(BaseModel):
    id: int
    reason: str  # "not_found" | "not_active" | "missing_billing_cycle"


class BatchRenewResponse(BaseModel):
    renewed: list[SubscriptionResponse]
    skipped: list[BatchRenewSkipped]
