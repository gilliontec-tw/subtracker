from domain.entities.subscription import Subscription
from domain.exceptions import NotFoundException
from domain.repositories.subscription_repository import SubscriptionRepository


class UpdateSubscriptionUseCase:
    def __init__(self, repo: SubscriptionRepository) -> None:
        self._repo = repo

    async def execute(self, subscription_id: int, **updates: object) -> Subscription:
        sub = await self._repo.get_by_id(subscription_id)
        if sub is None:
            raise NotFoundException()
        for field, value in updates.items():
            setattr(sub, field, value)
        return await self._repo.save(sub)
