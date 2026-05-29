from datetime import datetime

from pydantic import BaseModel


class AuditLogChangeItem(BaseModel):
    field: str
    before: str
    after: str


class AuditLogResponse(BaseModel):
    id: int
    action: str
    resource_id: int
    user_email: str | None
    service_name: str | None
    changes: list[AuditLogChangeItem] | None
    created_at: datetime
