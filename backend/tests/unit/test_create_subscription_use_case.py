from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.create_subscription import CreateSubscriptionUseCase
from domain.entities.subscription import Subscription


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def use_case(repo):
    return CreateSubscriptionUseCase(repo)


def _saved_entity(entity: Subscription) -> Subscription:
    entity.id = 1
    return entity


@pytest.mark.asyncio
async def test_saves_entity_and_returns_it(use_case, repo):
    repo.save = AsyncMock(side_effect=_saved_entity)
    result = await use_case.execute(
        service_name="GitHub",
        login_account="user@corp.com",
        expiry_date=date(2027, 1, 1),
        notification_emails=["admin@corp.com"],
        notification_days=30,
    )
    assert result.id == 1
    assert result.service_name == "GitHub"
    repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_default_currency_is_twd(use_case, repo):
    repo.save = AsyncMock(side_effect=_saved_entity)
    result = await use_case.execute(
        service_name="Slack",
        login_account="",
        expiry_date=date(2027, 6, 1),
        notification_emails=[],
        notification_days=30,
    )
    assert result.currency == "TWD"


@pytest.mark.asyncio
async def test_accepts_foreign_currency_with_exchange_rate(use_case, repo):
    repo.save = AsyncMock(side_effect=_saved_entity)
    result = await use_case.execute(
        service_name="AWS",
        login_account="aws@corp.com",
        expiry_date=date(2027, 6, 1),
        notification_emails=[],
        notification_days=14,
        cost=Decimal("100.00"),
        currency="USD",
        exchange_rate=Decimal("31.5"),
    )
    assert result.currency == "USD"
    assert result.exchange_rate == Decimal("31.5")


@pytest.mark.asyncio
async def test_entity_starts_with_no_id(use_case, repo):
    captured = []

    async def capture(entity):
        # Capture the id BEFORE it's modified by the side effect
        captured.append(entity.id)
        entity.id = 99
        return entity

    repo.save = AsyncMock(side_effect=capture)
    await use_case.execute(
        service_name="Notion",
        login_account="",
        expiry_date=date(2027, 1, 1),
        notification_emails=[],
        notification_days=30,
    )
    assert captured[0] is None
