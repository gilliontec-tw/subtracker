from src.domain.entities.subscription import Subscription
from src.domain.repositories.subscription_repository import SubscriptionRepository


class ListSubscriptionsUseCase:
    def __init__(self, repo: SubscriptionRepository) -> None:
        self._repo = repo

    def execute(self) -> list[Subscription]:
        return self._repo.get_all_active()
