from abc import abstractmethod
from datetime import date

from domain.entities.subscription import Subscription
from domain.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription, int]):
    @abstractmethod
    async def list_paginated(
        self,
        limit: int,
        offset: int,
        show_suspended: bool,
    ) -> tuple[list[Subscription], int]: ...

    @abstractmethod
    async def list_due_for_notification(self, today: date) -> list[Subscription]: ...

    @abstractmethod
    async def mark_notified(self, id: int, today: date) -> None: ...
