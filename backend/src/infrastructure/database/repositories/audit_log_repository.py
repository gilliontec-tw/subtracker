import json
from datetime import UTC, date, datetime, timedelta

from domain.entities.audit_entry import AuditEntry
from domain.repositories.audit_log_repository import AuditLogRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import AuditLogModel


def _to_entity(m: AuditLogModel) -> AuditEntry:
    return AuditEntry(
        id=m.id,
        user_id=m.user_id,
        action=m.action,
        resource_type=m.resource_type or "subscription",
        resource_id=m.resource_id or 0,
        details=json.loads(m.details) if m.details else {},
        created_at=m.created_at.replace(tzinfo=UTC) if m.created_at else None,
    )


class SqlAuditLogRepository(AuditLogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, entry: AuditEntry) -> None:
        model = AuditLogModel(
            user_id=entry.user_id,
            action=entry.action,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            details=json.dumps(entry.details),
        )
        self._session.add(model)
        await self._session.commit()

    async def list_by_date_range(
        self, from_date: date, to_date: date, limit: int = 500
    ) -> list[AuditEntry]:
        start = datetime(from_date.year, from_date.month, from_date.day, tzinfo=UTC)
        end = datetime(to_date.year, to_date.month, to_date.day, tzinfo=UTC) + timedelta(days=1)
        result = await self._session.execute(
            select(AuditLogModel)
            .where(
                AuditLogModel.created_at >= start,
                AuditLogModel.created_at < end,
            )
            .order_by(AuditLogModel.created_at.desc())
            .limit(limit)
        )
        return [_to_entity(m) for m in result.scalars().all()]
