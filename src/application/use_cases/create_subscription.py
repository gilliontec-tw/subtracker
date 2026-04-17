from datetime import date
from src.domain.entities.subscription import Subscription, NotificationDays
from src.domain.repositories.subscription_repository import SubscriptionRepository


class CreateSubscriptionUseCase:
    def __init__(self, repo: SubscriptionRepository) -> None:
        self._repo = repo

    def execute(
        self,
        service_name: str,
        login_account: str,
        expiry_date: date,
        responsible_person_email: str,
        notification_days: NotificationDays,
    ) -> Subscription:
        entity = Subscription(
            service_name=service_name,
            login_account=login_account,
            expiry_date=expiry_date,
            responsible_person_email=responsible_person_email,
            notification_days=notification_days,
        )
        return self._repo.add(entity)
