from abc import ABC, abstractmethod

from domain.entities.asset_type import AssetType


class AssetTypeRepository(ABC):
    @abstractmethod
    async def list_all(self) -> list[AssetType]: ...

    @abstractmethod
    async def get_by_id(self, asset_type_id: int) -> AssetType | None: ...

    @abstractmethod
    async def save(self, entity: AssetType) -> AssetType: ...

    @abstractmethod
    async def delete(self, asset_type_id: int) -> None: ...
