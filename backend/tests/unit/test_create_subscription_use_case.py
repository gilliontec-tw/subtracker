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


@pytest.mark.asyncio
async def test_writes_audit_entry_after_create(repo):
    repo.save = AsyncMock(side_effect=_saved_entity)
    audit_repo = MagicMock()
    audit_repo.save = AsyncMock()
    uc = CreateSubscriptionUseCase(
        repo, audit_repo=audit_repo, actor_user_id=1, actor_email="admin@corp.com"
    )
    await uc.execute(
        service_name="GitHub",
        login_account="user@corp.com",
        expiry_date=date(2027, 1, 1),
        notification_emails=[],
        notification_days=30,
    )
    audit_repo.save.assert_called_once()
    entry = audit_repo.save.call_args[0][0]
    assert entry.action == "create"
    assert entry.resource_type == "subscription"
    assert entry.details["service_name"] == "GitHub"
    assert entry.details["user_email"] == "admin@corp.com"
    assert entry.user_id == 1


@pytest.mark.asyncio
async def test_no_audit_entry_when_audit_repo_is_none(repo):
    repo.save = AsyncMock(side_effect=_saved_entity)
    uc = CreateSubscriptionUseCase(repo)  # no audit_repo
    result = await uc.execute(
        service_name="GitHub",
        login_account="",
        expiry_date=date(2027, 1, 1),
        notification_emails=[],
        notification_days=30,
    )
    assert result.service_name == "GitHub"  # no error raised
