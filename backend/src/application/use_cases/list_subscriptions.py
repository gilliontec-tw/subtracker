from domain.entities.subscription import Subscription
from domain.repositories.subscription_repository import SubscriptionRepository


class ListSubscriptionsUseCase:
    def __init__(self, repo: SubscriptionRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        limit: int,
        offset: int,
        show_suspended: bool,
        group_ids: list[int] | None = None,
    ) -> tuple[list[Subscription], int]:
        return await self._repo.list_paginated(
            limit=limit,
            offset=offset,
            show_suspended=show_suspended,
            group_ids=group_ids,
        )
