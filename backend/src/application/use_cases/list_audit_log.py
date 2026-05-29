from datetime import date

from domain.entities.audit_entry import AuditEntry
from domain.repositories.audit_log_repository import AuditLogRepository


class ListAuditLogUseCase:
    def __init__(self, repo: AuditLogRepository) -> None:
        self._repo = repo

    async def execute(self, from_date: date, to_date: date) -> list[AuditEntry]:
        return await self._repo.list_by_date_range(from_date, to_date)
