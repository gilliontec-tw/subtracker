from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.add_user_to_group import AddUserToGroupUseCase
from application.use_cases.create_group import CreateGroupUseCase
from application.use_cases.delete_group import DeleteGroupUseCase
from application.use_cases.list_groups import ListGroupsUseCase
from application.use_cases.remove_user_from_group import RemoveUserFromGroupUseCase
from domain.entities.group import Group
from domain.exceptions import ConflictException, NotFoundException


def make_group(**kwargs) -> Group:
    defaults = dict(id=1, name="IT")
    defaults.update(kwargs)
    return Group(**defaults)


@pytest.fixture
def repo():
    return MagicMock()


# --- CreateGroupUseCase ---


@pytest.mark.asyncio
async def test_create_group_saves_and_returns(repo):
    repo.get_by_name = AsyncMock(return_value=None)
    repo.save = AsyncMock(side_effect=lambda g: Group(id=1, name=g.name))
    uc = CreateGroupUseCase(repo)
    result = await uc.execute(name="HR")
    assert result.name == "HR"
    repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_create_group_duplicate_raises(repo):
    repo.get_by_name = AsyncMock(return_value=make_group(name="HR"))
    uc = CreateGroupUseCase(repo)
    with pytest.raises(ConflictException):
        await uc.execute(name="HR")


# --- DeleteGroupUseCase ---


@pytest.mark.asyncio
async def test_delete_group_calls_repo(repo):
    repo.get_by_id = AsyncMock(return_value=make_group())
    repo.delete = AsyncMock()
    uc = DeleteGroupUseCase(repo)
    await uc.execute(group_id=1)
    repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_group_not_found_raises(repo):
    repo.get_by_id = AsyncMock(return_value=None)
    uc = DeleteGroupUseCase(repo)
    with pytest.raises(NotFoundException):
        await uc.execute(group_id=99)


# --- ListGroupsUseCase ---


@pytest.mark.asyncio
async def test_list_groups_returns_all(repo):
    groups = [make_group(id=1, name="HR"), make_group(id=2, name="IT")]
    repo.list_all = AsyncMock(return_value=groups)
    uc = ListGroupsUseCase(repo)
    result = await uc.execute()
    assert result == groups


# --- AddUserToGroupUseCase ---


@pytest.mark.asyncio
async def test_add_user_to_group(repo):
    repo.get_by_id = AsyncMock(return_value=make_group())
    repo.add_member = AsyncMock()
    uc = AddUserToGroupUseCase(repo)
    await uc.execute(group_id=1, user_id=5)
    repo.add_member.assert_called_once_with(1, 5)


@pytest.mark.asyncio
async def test_add_user_to_group_not_found_raises(repo):
    repo.get_by_id = AsyncMock(return_value=None)
    uc = AddUserToGroupUseCase(repo)
    with pytest.raises(NotFoundException):
        await uc.execute(group_id=99, user_id=5)


# --- RemoveUserFromGroupUseCase ---


@pytest.mark.asyncio
async def test_remove_user_from_group(repo):
    repo.get_by_id = AsyncMock(return_value=make_group())
    repo.remove_member = AsyncMock()
    uc = RemoveUserFromGroupUseCase(repo)
    await uc.execute(group_id=1, user_id=5)
    repo.remove_member.assert_called_once_with(1, 5)


@pytest.mark.asyncio
async def test_remove_user_from_group_not_found_raises(repo):
    repo.get_by_id = AsyncMock(return_value=None)
    uc = RemoveUserFromGroupUseCase(repo)
    with pytest.raises(NotFoundException):
        await uc.execute(group_id=99, user_id=5)
