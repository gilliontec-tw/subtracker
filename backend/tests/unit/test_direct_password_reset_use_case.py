from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.direct_password_reset import DirectPasswordResetUseCase
from domain.exceptions import BadRequestException

from tests.unit.helpers import make_user


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def use_case(repo):
    return DirectPasswordResetUseCase(repo)


@pytest.mark.asyncio
async def test_raises_when_user_not_found(use_case, repo):
    repo.get_by_email = AsyncMock(return_value=None)

    with pytest.raises(BadRequestException) as exc_info:
        await use_case.execute("nobody@corp.com", "newpass123")

    assert "此帳號不存在" in exc_info.value.message


@pytest.mark.asyncio
async def test_raises_when_user_inactive(use_case, repo):
    repo.get_by_email = AsyncMock(return_value=make_user(is_active=False))

    with pytest.raises(BadRequestException) as exc_info:
        await use_case.execute("u@corp.com", "newpass123")

    assert "此帳號不存在" in exc_info.value.message


@pytest.mark.asyncio
async def test_updates_password_hash(use_case, repo):
    user = make_user(password_hash="old_hash")
    repo.get_by_email = AsyncMock(return_value=user)
    repo.save = AsyncMock(side_effect=lambda u: u)

    await use_case.execute("u@corp.com", "newpass123")

    saved = repo.save.call_args[0][0]
    assert saved.password_hash != "old_hash"
    assert saved.password_hash != ""


@pytest.mark.asyncio
async def test_does_not_change_other_fields(use_case, repo):
    user = make_user(display_name="Alice", role="admin")
    repo.get_by_email = AsyncMock(return_value=user)
    repo.save = AsyncMock(side_effect=lambda u: u)

    await use_case.execute("u@corp.com", "newpass123")

    saved = repo.save.call_args[0][0]
    assert saved.display_name == "Alice"
    assert saved.role == "admin"
