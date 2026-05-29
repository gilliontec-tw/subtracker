from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.delete_subscription import DeleteSubscriptionUseCase
from domain.entities.subscription import Subscription
from domain.exceptions import NotFoundException


def make_subscription(**kwargs) -> Subscription:
    defaults = dict(
        id=1,
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
    return DeleteSubscriptionUseCase(repo)


@pytest.mark.asyncio
async def test_raises_not_found_when_missing(use_case, repo):
    repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(NotFoundException):
        await use_case.execute(subscription_id=999)


@pytest.mark.asyncio
async def test_calls_repo_delete_with_correct_id(use_case, repo):
    sub = make_subscription(id=42)
    repo.get_by_id = AsyncMock(return_value=sub)
    repo.delete = AsyncMock(return_value=None)
    await use_case.execute(subscription_id=42)
    repo.delete.assert_called_once_with(42)


@pytest.mark.asyncio
async def test_returns_none(use_case, repo):
    sub = make_subscription(id=1)
    repo.get_by_id = AsyncMock(return_value=sub)
    repo.delete = AsyncMock(return_value=None)
    result = await use_case.execute(subscription_id=1)
    assert result is None


@pytest.mark.asyncio
async def test_writes_audit_entry_on_delete():
    repo = MagicMock()
    audit_repo = MagicMock()
    sub = make_subscription(id=5, service_name="OldName", login_account="old@corp.com")
    repo.get_by_id = AsyncMock(return_value=sub)
    repo.delete = AsyncMock()
    audit_repo.save = AsyncMock()
    uc = DeleteSubscriptionUseCase(
        repo, audit_repo=audit_repo, actor_user_id=1, actor_email="admin@corp.com"
    )
    await uc.execute(subscription_id=5)
    audit_repo.save.assert_called_once()
    entry = audit_repo.save.call_args[0][0]
    assert entry.action == "delete"
    assert entry.resource_id == 5
    assert entry.details["service_name"] == "OldName"
    assert entry.details["user_email"] == "admin@corp.com"


@pytest.mark.asyncio
async def test_no_audit_entry_when_audit_repo_is_none_delete():
    repo = MagicMock()
    sub = make_subscription(id=5)
    repo.get_by_id = AsyncMock(return_value=sub)
    repo.delete = AsyncMock()
    uc = DeleteSubscriptionUseCase(repo)
    await uc.execute(subscription_id=5)  # no error raised
    repo.delete.assert_called_once_with(5)
