from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import IntEnum, Enum


class NotificationDays(IntEnum):
    THREE = 3
    SEVEN = 7
    FOURTEEN = 14
    THIRTY = 30
    NINETY = 90
    ONE_TWENTY = 120


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    RENEWED = "renewed"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"


@dataclass
class Subscription:
    service_name: str
    login_account: str
    expiry_date: date
    notification_emails: str  # 逗號分隔，例如 "alice@co.com,bob@co.com"
    notification_days: NotificationDays
    id: int | None = None
    is_active: bool = True
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    cost: Decimal | None = None
    currency: str = "TWD"
    notes: str | None = None
    owner_name: str | None = None
    category: str | None = None
    department: str | None = None
    billing_cycle: str | None = None  # "monthly" | "annual" | None
    payment_account: str | None = None
    auto_renew: bool = False
    trial_end_date: date | None = None
    next_billing_date: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def should_notify_today(self, today: date) -> bool:
        trigger = self.expiry_date - timedelta(days=self.notification_days.value)
        return today == trigger

    def annual_cost(self) -> float:
        if self.cost is None:
            return 0.0
        multipliers = {
            "monthly":     12,
            "quarterly":   4,
            "semi_annual": 2,
            "annual":      1,
            "biennial":    0.5,
        }
        return float(self.cost) * multipliers.get(self.billing_cycle or "annual", 1)
