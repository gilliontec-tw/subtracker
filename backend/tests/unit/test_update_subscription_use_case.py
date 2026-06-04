from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.update_subscription import UpdateSubscriptionUseCase
from domain.entities.subscription import Subscription
from domain.exceptions import NotFoundException


def make_subscription(**kwargs) -> Subscription:
    defaults = dict(
        id=1,
        service_name="OldName",
        login_account="old@corp.com",
        expiry_date=date(2027, 1, 1),
        notification_emails=["old@corp.com"],
        notification_days=30,
        notes="keep this",
        status="active",
    )
    defaults.update(kwargs)
    return Subscription(**defaults)


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def use_case(repo):
    return UpdateSubscriptionUseCase(repo)


@pytest.mark.asyncio
async def test_raises_not_found_for_missing_id(use_case, repo):
    repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(NotFoundException):
        await use_case.execute(subscription_id=999, service_name="New")


@pytest.mark.asyncio
async def test_updates_provided_fields(use_case, repo):
    original = make_subscription()
    repo.get_by_id = AsyncMock(return_value=original)
    repo.save = AsyncMock(side_effect=lambda e: e)
    result = await use_case.execute(subscription_id=1, service_name="NewName")
    assert result.service_name == "NewName"


@pytest.mark.asyncio
async def test_preserves_unprovided_fields(use_case, repo):
    original = make_subscription(notes="keep this")
    repo.get_by_id = AsyncMock(return_value=original)
    repo.save = AsyncMock(side_effect=lambda e: e)
    result = await use_case.execute(subscription_id=1, service_name="Updated")
    assert result.notes == "keep this"
    assert result.login_account == "old@corp.com"


@pytest.mark.asyncio
async def test_calls_save_with_updated_entity(use_case, repo):
    original = make_subscription()
    repo.get_by_id = AsyncMock(return_value=original)
    repo.save = AsyncMock(side_effect=lambda e: e)
    await use_case.execute(subscription_id=1, status="suspended")
    saved_entity = repo.save.call_args[0][0]
    assert saved_entity.status == "suspended"
    assert saved_entity.id == 1


@pytest.mark.asyncio
async def test_writes_audit_entry_with_diff_on_update():
    repo = MagicMock()
    audit_repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=make_subscription(expiry_date=date(2025, 1, 1)))
    repo.save = AsyncMock(side_effect=lambda e: e)
    audit_repo.save = AsyncMock()
    uc = UpdateSubscriptionUseCase(
        repo, audit_repo=audit_repo, actor_user_id=2, actor_email="editor@corp.com"
    )
    await uc.execute(subscription_id=1, expiry_date=date(2026, 1, 1))
    audit_repo.save.assert_called_once()
    entry = audit_repo.save.call_args[0][0]
    assert entry.action == "update"
    assert entry.user_id == 2
    assert len(entry.details["changes"]) == 1
    assert entry.details["changes"][0]["field"] == "expiry_date"
    assert "2025-01-01" in entry.details["changes"][0]["before"]
    assert "2026-01-01" in entry.details["changes"][0]["after"]


@pytest.mark.asyncio
async def test_no_audit_entry_when_value_unchanged():
    repo = MagicMock()
    audit_repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=make_subscription(service_name="GitHub"))
    repo.save = AsyncMock(side_effect=lambda e: e)
    audit_repo.save = AsyncMock()
    uc = UpdateSubscriptionUseCase(
        repo, audit_repo=audit_repo, actor_user_id=1, actor_email="a@corp.com"
    )
    await uc.execute(subscription_id=1, service_name="GitHub")  # same value
    audit_repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_no_audit_entry_when_audit_repo_is_none_update():
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=make_subscription())
    repo.save = AsyncMock(side_effect=lambda e: e)
    uc = UpdateSubscriptionUseCase(repo)
    result = await uc.execute(subscription_id=1, service_name="NewName")
    assert result.service_name == "NewName"  # no error raised
