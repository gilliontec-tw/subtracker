from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass
class PaymentRecord:
    subscription_id: int
    payment_date: date
    amount: Decimal
    currency: str
    source: str = "manual"
    notes: str | None = None
    id: int | None = None
    created_at: datetime | None = None
    created_by: int | None = None
    service_name: str | None = None  # populated by JOIN queries; not stored in DB
    department: str | None = None
    login_account: str | None = None
