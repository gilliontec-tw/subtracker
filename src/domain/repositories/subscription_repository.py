from abc import ABC, abstractmethod
from src.domain.entities.subscription import Subscription


class SubscriptionRepository(ABC):

    @abstractmethod
    def add(self, subscription: Subscription) -> Subscription:
        """Persist a new subscription; returns entity with assigned id."""
        ...

    @abstractmethod
    def get_by_id(self, subscription_id: int) -> Subscription | None:
        """Return None if not found."""
        ...

    @abstractmethod
    def get_all_active(self) -> list[Subscription]:
        """Return all subscriptions where is_active=True."""
        ...

    @abstractmethod
    def update(self, subscription: Subscription) -> Subscription:
        """Persist updated fields; subscription.id must be set."""
        ...

    @abstractmethod
    def deactivate(self, subscription_id: int) -> None:
        """Soft delete: set is_active=False. No-op if not found."""
        ...
