from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class PaymentRecordCreate(BaseModel):
    subscription_id: int
    payment_date: date
    amount: Decimal
    currency: str = "TWD"
    notes: str | None = None


class PaymentRecordUpdate(BaseModel):
    payment_date: date | None = None
    amount: Decimal | None = None
    currency: str | None = None
    notes: str | None = None


class PaymentRecordResponse(BaseModel):
    id: int
    subscription_id: int
    service_name: str | None = None
    department: str | None = None
    login_account: str | None = None
    payment_date: date
    amount: Decimal
    currency: str
    notes: str | None = None
    source: str
    created_at: datetime
