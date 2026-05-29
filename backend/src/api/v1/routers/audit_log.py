from datetime import date

from application.use_cases.list_audit_log import ListAuditLogUseCase
from domain.entities.audit_entry import AuditEntry
from fastapi import APIRouter, Depends, Query
from infrastructure.database.repositories.audit_log_repository import SqlAuditLogRepository
from infrastructure.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import require_admin
from api.v1.schemas.audit_log import AuditLogChangeItem, AuditLogResponse
from api.v1.schemas.base import ApiResponse

router = APIRouter(prefix="/api/v1/audit-log", tags=["audit-log"])


def _to_response(entry: AuditEntry) -> AuditLogResponse:
    raw_changes = entry.details.get("changes")
    changes = [AuditLogChangeItem(**c) for c in raw_changes] if raw_changes else None
    return AuditLogResponse(
        id=entry.id,
        action=entry.action,
        resource_id=entry.resource_id,
        user_email=entry.details.get("user_email"),
        service_name=entry.details.get("service_name"),
        changes=changes,
        created_at=entry.created_at,
    )


@router.get("", response_model=ApiResponse[list[AuditLogResponse]])
async def list_audit_log(
    from_date: date = Query(...),
    to_date: date = Query(...),
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[AuditLogResponse]]:
    repo = SqlAuditLogRepository(db)
    use_case = ListAuditLogUseCase(repo)
    entries = await use_case.execute(from_date=from_date, to_date=to_date)
    return ApiResponse.ok(data=[_to_response(e) for e in entries])
