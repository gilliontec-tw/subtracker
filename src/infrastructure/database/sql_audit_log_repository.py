from sqlalchemy.orm import Session
from src.domain.entities.audit_entry import AuditEntry
from src.domain.repositories.audit_log_repository import AuditLogRepository
from src.infrastructure.database.models import AuditLogModel


class SqlAuditLogRepository(AuditLogRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def _to_entity(self, model: AuditLogModel) -> AuditEntry:
        return AuditEntry(
            id=model.id,
            user_id=model.user_id,
            user_email=model.user_email,
            action=model.action,
            target_type=model.target_type,
            target_id=model.target_id,
            target_name=model.target_name,
            created_at=model.created_at,
        )

    def add(self, entry: AuditEntry) -> AuditEntry:
        model = AuditLogModel(
            user_id=entry.user_id,
            user_email=entry.user_email,
            action=entry.action,
            target_type=entry.target_type,
            target_id=entry.target_id,
            target_name=entry.target_name,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return self._to_entity(model)

    def get_recent(self, limit: int = 100) -> list[AuditEntry]:
        models = (
            self._session.query(AuditLogModel)
            .order_by(AuditLogModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._to_entity(m) for m in models]
