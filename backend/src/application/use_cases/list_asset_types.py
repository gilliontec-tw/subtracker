from domain.entities.asset_type import AssetType
from domain.repositories.asset_type_repository import AssetTypeRepository


class ListAssetTypesUseCase:
    def __init__(self, repo: AssetTypeRepository) -> None:
        self._repo = repo

    async def execute(self) -> list[AssetType]:
        return await self._repo.list_all()
