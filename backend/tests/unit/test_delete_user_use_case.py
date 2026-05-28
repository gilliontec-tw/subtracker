from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.delete_user import DeleteUserUseCase
from domain.exceptions import LastAdminException, NotFoundException

from tests.unit.helpers import make_user


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def use_case(repo):
    return DeleteUserUseCase(repo)


@pytest.mark.asyncio
async def test_raises_when_user_not_found(use_case, repo):
    repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundException):
        await use_case.execute(99)


@pytest.mark.asyncio
async def test_deletes_non_admin(use_case, repo):
    user = make_user(id=2, role="user")
    repo.get_by_id = AsyncMock(return_value=user)
    repo.delete = AsyncMock()

    await use_case.execute(2)

    repo.delete.assert_called_once_with(2)


@pytest.mark.asyncio
async def test_raises_when_deleting_last_admin(use_case, repo):
    admin = make_user(id=1, role="admin", can_create=True, can_update=True, can_delete=True)
    repo.get_by_id = AsyncMock(return_value=admin)
    repo.list_all = AsyncMock(return_value=[admin])

    with pytest.raises(LastAdminException):
        await use_case.execute(1)


@pytest.mark.asyncio
async def test_deletes_admin_when_another_admin_exists(use_case, repo):
    admin1 = make_user(id=1, role="admin", can_create=True, can_update=True, can_delete=True)
    admin2 = make_user(
        id=2, email="a2@corp.com", role="admin", can_create=True, can_update=True, can_delete=True
    )
    repo.get_by_id = AsyncMock(return_value=admin1)
    repo.list_all = AsyncMock(return_value=[admin1, admin2])
    repo.delete = AsyncMock()

    await use_case.execute(1)

    repo.delete.assert_called_once_with(1)
