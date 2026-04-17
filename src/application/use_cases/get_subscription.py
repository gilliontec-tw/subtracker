from src.domain.entities.subscription import Subscription
from src.domain.repositories.subscription_repository import SubscriptionRepository


class GetSubscriptionUseCase:
    def __init__(self, repo: SubscriptionRepository) -> None:
        self._repo = repo

    def execute(self, subscription_id: int) -> Subscription:
        entity = self._repo.get_by_id(subscription_id)
        if entity is None:
            raise ValueError(f"Subscription {subscription_id} not found")
        return entity
