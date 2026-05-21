from domain.entities.subscription import Subscription
from domain.exceptions import NotFoundException
from domain.repositories.subscription_repository import SubscriptionRepository


class GetSubscriptionUseCase:
    def __init__(self, repo: SubscriptionRepository) -> None:
        self._repo = repo

    async def execute(self, subscription_id: int) -> Subscription:
        sub = await self._repo.get_by_id(subscription_id)
        if sub is None:
            raise NotFoundException()
        return sub
