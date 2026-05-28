from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

SUPPORTED_CURRENCIES = ("TWD", "USD", "EUR", "JPY", "GBP", "CNY")


@dataclass
class Subscription:
    service_name: str
    login_account: str
    expiry_date: date
    notification_emails: list[str]
    notification_days: int

    cost: Decimal | None = None
    currency: str = "TWD"
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
    last_notified_date: date | None = None
    status: str = "active"

    id: int | None = None
    deleted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
