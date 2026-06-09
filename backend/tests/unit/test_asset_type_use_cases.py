from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.create_asset_type import CreateAssetTypeUseCase
from application.use_cases.delete_asset_type import DeleteAssetTypeUseCase
from application.use_cases.list_asset_types import ListAssetTypesUseCase
from application.use_cases.update_asset_type import UpdateAssetTypeUseCase
from domain.entities.asset_type import AssetType
from domain.exceptions import ConflictException, NotFoundException


@pytest.fixture
def repo():
    return MagicMock()


@pytest.mark.asyncio
async def test_list_returns_all(repo):
    repo.list_all = AsyncMock(return_value=[AssetType(name="SaaS", id=1)])
    result = await ListAssetTypesUseCase(repo).execute()
    assert len(result) == 1
    assert result[0].name == "SaaS"


@pytest.mark.asyncio
async def test_create_saves_entity(repo):
    repo.save = AsyncMock(return_value=AssetType(name="ERP", id=2))
    result = await CreateAssetTypeUseCase(repo).execute(name="ERP", created_by=1)
    assert result.id == 2
    repo.save.assert_called_once()
    entity = repo.save.call_args[0][0]
    assert entity.name == "ERP"
    assert entity.created_by == 1


@pytest.mark.asyncio
async def test_update_saves_new_name(repo):
    repo.get_by_id = AsyncMock(return_value=AssetType(name="SaaS", id=1))
    repo.save = AsyncMock(return_value=AssetType(name="Cloud SaaS", id=1))
    result = await UpdateAssetTypeUseCase(repo).execute(asset_type_id=1, name="Cloud SaaS")
    assert result.name == "Cloud SaaS"
    entity = repo.save.call_args[0][0]
    assert entity.name == "Cloud SaaS"


@pytest.mark.asyncio
async def test_update_raises_not_found_when_missing(repo):
    repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(NotFoundException):
        await UpdateAssetTypeUseCase(repo).execute(asset_type_id=99, name="X")


@pytest.mark.asyncio
async def test_delete_delegates_to_repo(repo):
    repo.delete = AsyncMock(return_value=None)
    await DeleteAssetTypeUseCase(repo).execute(asset_type_id=1)
    repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_propagates_conflict(repo):
    repo.delete = AsyncMock(side_effect=ConflictException("此類型尚有項目使用，無法刪除"))
    with pytest.raises(ConflictException):
        await DeleteAssetTypeUseCase(repo).execute(asset_type_id=1)
