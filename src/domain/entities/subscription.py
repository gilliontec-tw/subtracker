from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import IntEnum


class NotificationDays(IntEnum):
    THREE = 3
    SEVEN = 7
    FOURTEEN = 14
    THIRTY = 30
    NINETY = 90
    ONE_TWENTY = 120


@dataclass
class Subscription:
    service_name: str
    login_account: str
    expiry_date: date
    responsible_person_email: str
    notification_days: NotificationDays
    id: int | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def should_notify_today(self, today: date) -> bool:
        trigger = self.expiry_date - timedelta(days=self.notification_days.value)
        return today == trigger
