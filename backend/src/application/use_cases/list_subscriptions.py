from domain.entities.subscription import Subscription
from domain.repositories.subscription_repository import SubscriptionRepository


class ListSubscriptionsUseCase:
    def __init__(self, repo: SubscriptionRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        limit: int,
        offset: int,
        show_cancelled: bool,
    ) -> tuple[list[Subscription], int]:
        return await self._repo.list_paginated(
            limit=limit,
            offset=offset,
            show_cancelled=show_cancelled,
        )
