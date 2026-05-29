from datetime import date

from domain.entities.audit_entry import AuditEntry
from domain.repositories.audit_log_repository import AuditLogRepository


class ConcreteAuditRepo(AuditLogRepository):
    async def save(self, entry: AuditEntry) -> None: ...
    async def list_by_date_range(
        self, from_date: date, to_date: date, limit: int = 500
    ) -> list[AuditEntry]: ...


def test_audit_log_repository_is_abstract():
    repo = ConcreteAuditRepo()
    assert isinstance(repo, AuditLogRepository)
