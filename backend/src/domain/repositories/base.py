from abc import ABC, abstractmethod


class BaseRepository[T, ID](ABC):
    @abstractmethod
    async def get_by_id(self, id: ID) -> T | None: ...

    @abstractmethod
    async def list_all(self) -> list[T]: ...

    @abstractmethod
    async def save(self, entity: T) -> T: ...

    @abstractmethod
    async def delete(self, id: ID) -> None: ...
