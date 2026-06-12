from abc import abstractmethod

from domain.entities.group import Group
from domain.repositories.base import BaseRepository


class GroupRepository(BaseRepository[Group, int]):
    @abstractmethod
    async def get_by_name(self, name: str) -> Group | None: ...

    @abstractmethod
    async def list_all(self) -> list[Group]: ...

    @abstractmethod
    async def get_group_ids_for_user(self, user_id: int) -> list[int]: ...

    @abstractmethod
    async def get_groups_for_user(self, user_id: int) -> list[Group]: ...

    @abstractmethod
    async def get_groups_by_user_ids(self, user_ids: list[int]) -> dict[int, list[Group]]: ...

    @abstractmethod
    async def get_member_user_ids(self, group_id: int) -> list[int]: ...

    @abstractmethod
    async def add_member(self, group_id: int, user_id: int) -> None: ...

    @abstractmethod
    async def remove_member(self, group_id: int, user_id: int) -> None: ...
