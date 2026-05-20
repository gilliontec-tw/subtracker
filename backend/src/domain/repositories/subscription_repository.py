from abc import abstractmethod

from domain.entities.subscription import Subscription
from domain.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription, int]):
    @abstractmethod
    async def list_paginated(
        self,
        limit: int,
        offset: int,
        show_cancelled: bool,
    ) -> tuple[list[Subscription], int]: ...
