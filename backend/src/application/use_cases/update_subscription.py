from domain.entities.audit_entry import AuditEntry
from domain.entities.subscription import Subscription
from domain.exceptions import NotFoundException
from domain.repositories.audit_log_repository import AuditLogRepository
from domain.repositories.subscription_repository import SubscriptionRepository


class UpdateSubscriptionUseCase:
    def __init__(
        self,
        repo: SubscriptionRepository,
        audit_repo: AuditLogRepository | None = None,
        actor_user_id: int | None = None,
        actor_email: str | None = None,
    ) -> None:
        self._repo = repo
        self._audit_repo = audit_repo
        self._actor_user_id = actor_user_id
        self._actor_email = actor_email

    async def execute(self, subscription_id: int, **updates: object) -> Subscription:
        sub = await self._repo.get_by_id(subscription_id)
        if sub is None:
            raise NotFoundException()
        old_values = {k: getattr(sub, k) for k in updates}
        for field, value in updates.items():
            setattr(sub, field, value)
        result = await self._repo.save(sub)
        if self._audit_repo is not None:
            changes = [
                {"field": k, "before": str(old_values[k]), "after": str(updates[k])}
                for k in updates
                if old_values[k] != updates[k]
            ]
            if changes:
                await self._audit_repo.save(
                    AuditEntry(
                        user_id=self._actor_user_id,
                        action="update",
                        resource_type="subscription",
                        resource_id=subscription_id,
                        details={
                            "user_email": self._actor_email,
                            "service_name": result.service_name,
                            "changes": changes,
                        },
                    )
                )
        return result
