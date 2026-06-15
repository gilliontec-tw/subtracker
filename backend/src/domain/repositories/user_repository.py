from abc import abstractmethod

from domain.entities.user import User
from domain.repositories.base import BaseRepository


class UserRepository(BaseRepository[User, int]):
    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def get_by_invite_token(self, token: str) -> User | None: ...

    @abstractmethod
    async def get_users_by_ids(self, user_ids: list[int]) -> list[User]: ...
