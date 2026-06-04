from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.list_subscriptions import ListSubscriptionsUseCase
from domain.entities.subscription import Subscription


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
    return ListSubscriptionsUseCase(repo)


@pytest.mark.asyncio
async def test_passes_pagination_params_to_repo(use_case, repo):
    repo.list_paginated = AsyncMock(return_value=([], 0))
    await use_case.execute(limit=10, offset=20, show_suspended=False)
    repo.list_paginated.assert_called_once_with(limit=10, offset=20, show_suspended=False)


@pytest.mark.asyncio
async def test_passes_show_suspended_true(use_case, repo):
    repo.list_paginated = AsyncMock(return_value=([], 0))
    await use_case.execute(limit=50, offset=0, show_suspended=True)
    repo.list_paginated.assert_called_once_with(limit=50, offset=0, show_suspended=True)


@pytest.mark.asyncio
async def test_returns_items_and_total(use_case, repo):
    subs = [make_subscription(id=1), make_subscription(id=2)]
    repo.list_paginated = AsyncMock(return_value=(subs, 5))
    items, total = await use_case.execute(limit=50, offset=0, show_suspended=False)
    assert items == subs
    assert total == 5
