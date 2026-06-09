from domain.entities.asset_type import AssetType
from domain.repositories.asset_type_repository import AssetTypeRepository


class CreateAssetTypeUseCase:
    def __init__(self, repo: AssetTypeRepository) -> None:
        self._repo = repo

    async def execute(self, name: str, created_by: int | None = None) -> AssetType:
        entity = AssetType(name=name, created_by=created_by)
        return await self._repo.save(entity)
