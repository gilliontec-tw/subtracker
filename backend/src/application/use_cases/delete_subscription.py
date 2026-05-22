from domain.exceptions import NotFoundException
from domain.repositories.subscription_repository import SubscriptionRepository


class DeleteSubscriptionUseCase:
    def __init__(self, repo: SubscriptionRepository) -> None:
        self._repo = repo

    async def execute(self, subscription_id: int) -> None:
        sub = await self._repo.get_by_id(subscription_id)
        if sub is None:
            raise NotFoundException()
        await self._repo.delete(subscription_id)
