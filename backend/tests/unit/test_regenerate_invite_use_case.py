from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.regenerate_invite import RegenerateInviteUseCase
from domain.exceptions import ForbiddenException, NotFoundException

from tests.unit.helpers import make_user


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def use_case(repo):
    return RegenerateInviteUseCase(repo)


@pytest.mark.asyncio
async def test_regenerates_token_for_active_user(use_case, repo):
    old_token = "old-token"
    user = make_user(id=5, invite_token=old_token)
    repo.get_by_id = AsyncMock(return_value=user)
    repo.save = AsyncMock(side_effect=lambda u: u)

    result = await use_case.execute(user_id=5)

    assert result.invite_token != old_token
    assert result.invite_token is not None
    assert result.invite_token_expires_at is not None
    repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_raises_not_found_if_user_missing(use_case, repo):
    repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundException):
        await use_case.execute(user_id=99)


@pytest.mark.asyncio
async def test_raises_forbidden_if_user_inactive(use_case, repo):
    user = make_user(is_active=False)
    repo.get_by_id = AsyncMock(return_value=user)

    with pytest.raises(ForbiddenException):
        await use_case.execute(user_id=1)
