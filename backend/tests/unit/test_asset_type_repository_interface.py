from unittest.mock import AsyncMock, MagicMock

import pytest
from domain.entities.asset_type import AssetType
from domain.repositories.asset_type_repository import AssetTypeRepository


@pytest.fixture
def repo():
    r = MagicMock(spec=AssetTypeRepository)
    r.list_all = AsyncMock(return_value=[AssetType(name="SaaS", id=1)])
    r.get_by_id = AsyncMock(return_value=AssetType(name="SaaS", id=1))
    r.save = AsyncMock(side_effect=lambda e: AssetType(name=e.name, id=1))
    r.delete = AsyncMock(return_value=None)
    return r


@pytest.mark.asyncio
async def test_list_all_returns_list(repo):
    result = await repo.list_all()
    assert isinstance(result, list)
    assert result[0].name == "SaaS"


@pytest.mark.asyncio
async def test_get_by_id_returns_entity(repo):
    result = await repo.get_by_id(1)
    assert result is not None
    assert result.id == 1


@pytest.mark.asyncio
async def test_save_returns_entity_with_id(repo):
    entity = AssetType(name="ERP")
    result = await repo.save(entity)
    assert result.id == 1


@pytest.mark.asyncio
async def test_delete_called(repo):
    await repo.delete(1)
    repo.delete.assert_called_once_with(1)
