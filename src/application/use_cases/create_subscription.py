from datetime import date
from decimal import Decimal
from src.domain.entities.subscription import Subscription, NotificationDays, SubscriptionStatus
from src.domain.repositories.subscription_repository import SubscriptionRepository


class CreateSubscriptionUseCase:
    def __init__(self, repo: SubscriptionRepository) -> None:
        self._repo = repo

    def execute(
        self,
        service_name: str,
        login_account: str,
        expiry_date: date,
        notification_emails: str,
        notification_days: NotificationDays,
        status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
        cost: Decimal | None = None,
        currency: str = "TWD",
        notes: str | None = None,
        owner_name: str | None = None,
        category: str | None = None,
        department: str | None = None,
        billing_cycle: str | None = None,
    ) -> Subscription:
        entity = Subscription(
            service_name=service_name,
            login_account=login_account,
            expiry_date=expiry_date,
            notification_emails=notification_emails,
            notification_days=notification_days,
            status=status,
            cost=cost,
            currency=currency,
            notes=notes,
            owner_name=owner_name,
            category=category,
            department=department,
            billing_cycle=billing_cycle,
        )
        return self._repo.add(entity)
