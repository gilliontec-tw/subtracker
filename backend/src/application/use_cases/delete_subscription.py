from domain.entities.audit_entry import AuditEntry
from domain.exceptions import NotFoundException
from domain.repositories.audit_log_repository import AuditLogRepository
from domain.repositories.subscription_repository import SubscriptionRepository


class DeleteSubscriptionUseCase:
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

    async def execute(self, subscription_id: int) -> None:
        sub = await self._repo.get_by_id(subscription_id)
        if sub is None:
            raise NotFoundException()
        await self._repo.delete(subscription_id)
        if self._audit_repo is not None:
            await self._audit_repo.save(
                AuditEntry(
                    user_id=self._actor_user_id,
                    action="delete",
                    resource_type="subscription",
                    resource_id=subscription_id,
                    details={
                        "user_email": self._actor_email,
                        "service_name": sub.service_name,
                    },
                )
            )
