from domain.repositories.asset_type_repository import AssetTypeRepository


class DeleteAssetTypeUseCase:
    def __init__(self, repo: AssetTypeRepository) -> None:
        self._repo = repo

    async def execute(self, asset_type_id: int) -> None:
        await self._repo.delete(asset_type_id)
