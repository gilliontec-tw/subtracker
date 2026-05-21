from datetime import date
from decimal import Decimal

from domain.entities.subscription import Subscription
from domain.repositories.subscription_repository import SubscriptionRepository


class CreateSubscriptionUseCase:
    def __init__(self, repo: SubscriptionRepository) -> None:
        self._repo = repo

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
        return await self._repo.save(entity)
