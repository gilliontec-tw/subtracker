from abc import ABC, abstractmethod
from datetime import date

from domain.entities.audit_entry import AuditEntry


class AuditLogRepository(ABC):
    @abstractmethod
    async def save(self, entry: AuditEntry) -> None: ...

    @abstractmethod
    async def list_by_date_range(
        self, from_date: date, to_date: date, limit: int = 500
    ) -> list[AuditEntry]: ...
