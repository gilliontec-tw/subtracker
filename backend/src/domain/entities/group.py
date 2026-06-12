from dataclasses import dataclass
from datetime import datetime


@dataclass
class Group:
    name: str
    id: int | None = None
    created_at: datetime | None = None
