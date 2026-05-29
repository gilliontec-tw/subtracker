from dataclasses import dataclass
from datetime import datetime


@dataclass
class AuditEntry:
    user_id: int | None
    action: str  # "create" | "update" | "delete"
    resource_type: str  # "subscription"
    resource_id: int
    details: dict  # {"user_email": ..., "service_name": ..., "changes": [...]}
    id: int | None = None
    created_at: datetime | None = None
