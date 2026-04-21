from abc import ABC, abstractmethod
from src.domain.entities.audit_entry import AuditEntry


class AuditLogRepository(ABC):

    @abstractmethod
    def add(self, entry: AuditEntry) -> AuditEntry: ...

    @abstractmethod
    def get_recent(self, limit: int = 100) -> list[AuditEntry]: ...
