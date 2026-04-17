from datetime import date
from src.domain.entities.subscription import NotificationDays
from src.domain.repositories.subscription_repository import SubscriptionRepository


class UpdateSubscriptionUseCase:
    def __init__(self, repo: SubscriptionRepository) -> None:
        self._repo = repo

    def execute(
        self,
        subscription_id: int,
        service_name: str,
        login_account: str,
        expiry_date: date,
        responsible_person_email: str,
        notification_days: NotificationDays,
    ):
        entity = self._repo.get_by_id(subscription_id)
        if entity is None:
            raise ValueError(f"Subscription {subscription_id} not found")
        entity.service_name = service_name
        entity.login_account = login_account
        entity.expiry_date = expiry_date
        entity.responsible_person_email = responsible_person_email
        entity.notification_days = notification_days
        return self._repo.update(entity)
