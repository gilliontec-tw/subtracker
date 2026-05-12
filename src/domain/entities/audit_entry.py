from dataclasses import dataclass
from datetime import datetime


@dataclass
class AuditEntry:
    user_id: int
    user_email: str
    action: str        # "create" | "update" | "delete"
    target_type: str   # "subscription"
    target_id: int
    target_name: str
    changes: str | None = None
    id: int | None = None
    created_at: datetime | None = None
