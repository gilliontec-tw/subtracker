from abc import ABC, abstractmethod


class SystemSettingRepository(ABC):
    @abstractmethod
    async def get(self, key: str) -> str | None: ...

    @abstractmethod
    async def set(self, key: str, value: str) -> None: ...

    @abstractmethod
    async def get_all(self) -> dict[str, str]: ...
