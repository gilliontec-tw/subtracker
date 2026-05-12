from abc import ABC, abstractmethod
from src.domain.entities.user import User


class UserRepository(ABC):

    @abstractmethod
    def add(self, user: User) -> User:
        """Persist a new user; returns entity with assigned id."""
        ...

    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None: ...

    @abstractmethod
    def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    def get_all(self) -> list[User]:
        """Return all users including inactive, for admin management."""
        ...

    @abstractmethod
    def update(self, user: User) -> User:
        """Persist updated user; user.id must be set."""
        ...

    @abstractmethod
    def get_by_invite_token(self, token: str) -> User | None: ...

    @abstractmethod
    def delete(self, user_id: int) -> None: ...
