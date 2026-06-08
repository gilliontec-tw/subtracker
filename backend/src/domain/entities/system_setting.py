from dataclasses import dataclass
from datetime import datetime


@dataclass
class SystemSetting:
    key: str
    value: str | None
    updated_at: datetime | None = None
