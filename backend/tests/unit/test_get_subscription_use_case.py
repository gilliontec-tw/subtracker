from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.get_subscription import GetSubscriptionUseCase
from domain.entities.subscription import Subscription
from domain.exceptions import NotFoundException


def make_subscription(**kwargs) -> Subscription:
    defaults = dict(
        service_name="TestSVC",
        login_account="user@test.com",
        expiry_date=date(2027, 1, 1),
        notification_emails=[],
        notification_days=30,
    )
    defaults.update(kwargs)
    return Subscription(**defaults)


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def use_case(repo):
    return GetSubscriptionUseCase(repo)


@pytest.mark.asyncio
async def test_raises_not_found_when_missing(use_case, repo):
    repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(NotFoundException):
        await use_case.execute(subscription_id=999)


@pytest.mark.asyncio
async def test_returns_subscription_when_found(use_case, repo):
    sub = make_subscription(id=1)
    repo.get_by_id = AsyncMock(return_value=sub)
    result = await use_case.execute(subscription_id=1)
    assert result == sub
    repo.get_by_id.assert_called_once_with(1)
