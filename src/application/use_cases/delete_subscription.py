from src.domain.repositories.subscription_repository import SubscriptionRepository


class DeleteSubscriptionUseCase:
    def __init__(self, repo: SubscriptionRepository) -> None:
        self._repo = repo

    def execute(self, subscription_id: int) -> None:
        self._repo.deactivate(subscription_id)
