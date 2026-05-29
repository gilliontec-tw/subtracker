from datetime import date
from decimal import Decimal

from domain.entities.audit_entry import AuditEntry
from domain.entities.subscription import Subscription
from domain.repositories.audit_log_repository import AuditLogRepository
from domain.repositories.subscription_repository import SubscriptionRepository


class CreateSubscriptionUseCase:
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

    async def execute(
        self,
        service_name: str,
        login_account: str,
        expiry_date: date,
        notification_emails: list[str],
        notification_days: int,
        cost: Decimal | None = None,
        currency: str = "TWD",
        exchange_rate: Decimal | None = None,
        notes: str | None = None,
        owner_name: str | None = None,
        category: str | None = None,
        department: str | None = None,
        billing_cycle: str | None = None,
        payment_account: str | None = None,
        auto_renew: bool = False,
        trial_end_date: date | None = None,
        next_billing_date: date | None = None,
        status: str = "active",
    ) -> Subscription:
        entity = Subscription(
            service_name=service_name,
            login_account=login_account,
            expiry_date=expiry_date,
            notification_emails=notification_emails,
            notification_days=notification_days,
            cost=cost,
            currency=currency,
            exchange_rate=exchange_rate,
            notes=notes,
            owner_name=owner_name,
            category=category,
            department=department,
            billing_cycle=billing_cycle,
            payment_account=payment_account,
            auto_renew=auto_renew,
            trial_end_date=trial_end_date,
            next_billing_date=next_billing_date,
            status=status,
        )
        result = await self._repo.save(entity)
        if self._audit_repo is not None:
            await self._audit_repo.save(
                AuditEntry(
                    user_id=self._actor_user_id,
                    action="create",
                    resource_type="subscription",
                    resource_id=result.id,
                    details={
                        "user_email": self._actor_email,
                        "service_name": result.service_name,
                    },
                )
            )
        return result
