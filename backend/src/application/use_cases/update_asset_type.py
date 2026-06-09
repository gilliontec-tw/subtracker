from domain.entities.asset_type import AssetType
from domain.exceptions import NotFoundException
from domain.repositories.asset_type_repository import AssetTypeRepository


class UpdateAssetTypeUseCase:
    def __init__(self, repo: AssetTypeRepository) -> None:
        self._repo = repo

    async def execute(self, asset_type_id: int, name: str) -> AssetType:
        entity = await self._repo.get_by_id(asset_type_id)
        if entity is None:
            raise NotFoundException()
        entity.name = name
        return await self._repo.save(entity)
