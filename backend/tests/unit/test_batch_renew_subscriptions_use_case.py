from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.batch_renew_subscriptions import BatchRenewSubscriptionsUseCase
from domain.entities.subscription import Subscription


def make_subscription(**kwargs) -> Subscription:
    defaults = dict(
        id=1,
        service_name="GitHub",
        login_account="user@corp.com",
        expiry_date=date(2026, 1, 15),
        notification_emails=["user@corp.com"],
        notification_days=30,
        status="active",
        billing_cycle="monthly",
    )
    defaults.update(kwargs)
    return Subscription(**defaults)


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def audit_repo():
    return MagicMock()


@pytest.mark.asyncio
async def test_monthly_billing_cycle_advances_one_month(repo):
    sub = make_subscription(id=1, billing_cycle="monthly", expiry_date=date(2026, 1, 15))
    repo.get_by_id = AsyncMock(return_value=sub)
    repo.save = AsyncMock(side_effect=lambda e: e)

    uc = BatchRenewSubscriptionsUseCase(repo)
    result = await uc.execute(subscription_ids=[1])

    assert len(result["renewed"]) == 1
    assert result["renewed"][0].expiry_date == date(2026, 2, 15)
    assert result["skipped"] == []


@pytest.mark.asyncio
async def test_annual_billing_cycle_advances_one_year(repo):
    sub = make_subscription(id=2, billing_cycle="annual", expiry_date=date(2026, 6, 1))
    repo.get_by_id = AsyncMock(return_value=sub)
    repo.save = AsyncMock(side_effect=lambda e: e)

    uc = BatchRenewSubscriptionsUseCase(repo)
    result = await uc.execute(subscription_ids=[2])

    assert len(result["renewed"]) == 1
    assert result["renewed"][0].expiry_date == date(2027, 6, 1)


@pytest.mark.asyncio
async def test_quarterly_billing_cycle_advances_three_months(repo):
    sub = make_subscription(id=3, billing_cycle="quarterly", expiry_date=date(2026, 1, 1))
    repo.get_by_id = AsyncMock(return_value=sub)
    repo.save = AsyncMock(side_effect=lambda e: e)

    uc = BatchRenewSubscriptionsUseCase(repo)
    result = await uc.execute(subscription_ids=[3])

    assert result["renewed"][0].expiry_date == date(2026, 4, 1)


@pytest.mark.asyncio
async def test_semi_annual_billing_cycle_advances_six_months(repo):
    sub = make_subscription(id=4, billing_cycle="semi_annual", expiry_date=date(2026, 1, 1))
    repo.get_by_id = AsyncMock(return_value=sub)
    repo.save = AsyncMock(side_effect=lambda e: e)

    uc = BatchRenewSubscriptionsUseCase(repo)
    result = await uc.execute(subscription_ids=[4])

    assert result["renewed"][0].expiry_date == date(2026, 7, 1)


@pytest.mark.asyncio
async def test_biennial_billing_cycle_advances_two_years(repo):
    sub = make_subscription(id=5, billing_cycle="biennial", expiry_date=date(2026, 3, 10))
    repo.get_by_id = AsyncMock(return_value=sub)
    repo.save = AsyncMock(side_effect=lambda e: e)

    uc = BatchRenewSubscriptionsUseCase(repo)
    result = await uc.execute(subscription_ids=[5])

    assert result["renewed"][0].expiry_date == date(2028, 3, 10)


@pytest.mark.asyncio
async def test_missing_billing_cycle_returns_skipped(repo):
    sub = make_subscription(id=6, billing_cycle=None)
    repo.get_by_id = AsyncMock(return_value=sub)
    repo.save = AsyncMock()

    uc = BatchRenewSubscriptionsUseCase(repo)
    result = await uc.execute(subscription_ids=[6])

    assert result["renewed"] == []
    assert result["skipped"] == [{"id": 6, "reason": "missing_billing_cycle"}]
    repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_suspended_subscription_returns_skipped(repo):
    sub = make_subscription(id=8, status="suspended")
    repo.get_by_id = AsyncMock(return_value=sub)
    repo.save = AsyncMock()

    uc = BatchRenewSubscriptionsUseCase(repo)
    result = await uc.execute(subscription_ids=[8])

    assert result["renewed"] == []
    assert result["skipped"] == [{"id": 8, "reason": "not_active"}]
    repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_missing_id_returns_not_found_skipped(repo):
    repo.get_by_id = AsyncMock(return_value=None)
    repo.save = AsyncMock()

    uc = BatchRenewSubscriptionsUseCase(repo)
    result = await uc.execute(subscription_ids=[999])

    assert result["renewed"] == []
    assert result["skipped"] == [{"id": 999, "reason": "not_found"}]
    repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_audit_entry_written_per_renewed_subscription(repo, audit_repo):
    sub = make_subscription(id=1, billing_cycle="monthly", expiry_date=date(2026, 1, 15))
    repo.get_by_id = AsyncMock(return_value=sub)
    repo.save = AsyncMock(side_effect=lambda e: e)
    audit_repo.save = AsyncMock()

    uc = BatchRenewSubscriptionsUseCase(
        repo, audit_repo=audit_repo, actor_user_id=2, actor_email="admin@corp.com"
    )
    await uc.execute(subscription_ids=[1])

    audit_repo.save.assert_called_once()
    entry = audit_repo.save.call_args[0][0]
    assert entry.action == "renew"
    assert entry.resource_type == "subscription"
    assert entry.resource_id == 1
    assert entry.user_id == 2
    assert entry.details["user_email"] == "admin@corp.com"
    assert entry.details["service_name"] == "GitHub"
    changes = entry.details["changes"]
    assert len(changes) == 1
    assert changes[0]["field"] == "expiry_date"
    assert changes[0]["before"] == "2026-01-15"
    assert changes[0]["after"] == "2026-02-15"


@pytest.mark.asyncio
async def test_audit_not_called_for_skipped_subscriptions(repo, audit_repo):
    repo.get_by_id = AsyncMock(return_value=None)
    audit_repo.save = AsyncMock()

    uc = BatchRenewSubscriptionsUseCase(
        repo, audit_repo=audit_repo, actor_user_id=1, actor_email="a@corp.com"
    )
    await uc.execute(subscription_ids=[999])

    audit_repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_mixed_batch_returns_correct_renewed_and_skipped(repo):
    sub_active = make_subscription(id=1, billing_cycle="annual", expiry_date=date(2026, 6, 1))
    sub_suspended = make_subscription(id=2, status="suspended")
    sub_missing_cycle = make_subscription(id=3, billing_cycle=None)

    async def get_by_id(sub_id):
        return {1: sub_active, 2: sub_suspended, 3: sub_missing_cycle}.get(sub_id)

    repo.get_by_id = AsyncMock(side_effect=get_by_id)
    repo.save = AsyncMock(side_effect=lambda e: e)

    uc = BatchRenewSubscriptionsUseCase(repo)
    result = await uc.execute(subscription_ids=[1, 2, 3, 999])

    assert len(result["renewed"]) == 1
    assert result["renewed"][0].expiry_date == date(2027, 6, 1)
    assert len(result["skipped"]) == 3
    reasons = {s["id"]: s["reason"] for s in result["skipped"]}
    assert reasons[2] == "not_active"
    assert reasons[3] == "missing_billing_cycle"
    assert reasons[999] == "not_found"
