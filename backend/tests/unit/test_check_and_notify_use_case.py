from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.check_and_notify import CheckAndNotifyUseCase
from domain.entities.subscription import Subscription

TODAY = date(2026, 5, 28)


def make_subscription(**kwargs) -> Subscription:
    defaults = dict(
        id=1,
        service_name="GitHub",
        login_account="user@corp.com",
        expiry_date=date(2026, 6, 5),
        notification_emails=["admin@corp.com"],
        notification_days=14,
        status="active",
    )
    defaults.update(kwargs)
    return Subscription(**defaults)


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def sender():
    return MagicMock()


@pytest.fixture
def use_case(repo, sender):
    return CheckAndNotifyUseCase(repo, sender)


@pytest.mark.asyncio
async def test_sends_one_email_per_recipient(use_case, repo, sender):
    sub = make_subscription()
    repo.list_due_for_notification = AsyncMock(return_value=[sub])
    repo.mark_notified = AsyncMock()
    sender.send = AsyncMock()

    count = await use_case.execute(today=TODAY)

    sender.send.assert_called_once()
    call_kwargs = sender.send.call_args[1]
    assert call_kwargs["to"] == ["admin@corp.com"]
    assert "GitHub" in call_kwargs["subject"]
    assert count == 1


@pytest.mark.asyncio
async def test_consolidates_multiple_subs_for_same_recipient(use_case, repo, sender):
    subs = [
        make_subscription(id=1, service_name="GitHub"),
        make_subscription(id=2, service_name="Slack"),
    ]
    repo.list_due_for_notification = AsyncMock(return_value=subs)
    repo.mark_notified = AsyncMock()
    sender.send = AsyncMock()

    count = await use_case.execute(today=TODAY)

    # Both subs go to admin@corp.com → only 1 email sent
    sender.send.assert_called_once()
    call_kwargs = sender.send.call_args[1]
    assert "2" in call_kwargs["subject"]
    assert "GitHub" in call_kwargs["body"]
    assert "Slack" in call_kwargs["body"]
    assert count == 1


@pytest.mark.asyncio
async def test_sends_separate_emails_for_different_recipients(use_case, repo, sender):
    sub1 = make_subscription(id=1, notification_emails=["a@corp.com"])
    sub2 = make_subscription(id=2, service_name="Slack", notification_emails=["b@corp.com"])
    repo.list_due_for_notification = AsyncMock(return_value=[sub1, sub2])
    repo.mark_notified = AsyncMock()
    sender.send = AsyncMock()

    count = await use_case.execute(today=TODAY)

    assert sender.send.call_count == 2
    assert count == 2


@pytest.mark.asyncio
async def test_marks_notified_after_send(use_case, repo, sender):
    sub = make_subscription()
    repo.list_due_for_notification = AsyncMock(return_value=[sub])
    repo.mark_notified = AsyncMock()
    sender.send = AsyncMock()

    await use_case.execute(today=TODAY)

    repo.mark_notified.assert_called_once_with(1, TODAY)


@pytest.mark.asyncio
async def test_marks_each_sub_notified_once_even_with_multiple_recipients(use_case, repo, sender):
    sub = make_subscription(id=1, notification_emails=["a@corp.com", "b@corp.com"])
    repo.list_due_for_notification = AsyncMock(return_value=[sub])
    repo.mark_notified = AsyncMock()
    sender.send = AsyncMock()

    await use_case.execute(today=TODAY)

    assert sender.send.call_count == 2
    repo.mark_notified.assert_called_once_with(1, TODAY)


@pytest.mark.asyncio
async def test_no_emails_when_nothing_due(use_case, repo, sender):
    repo.list_due_for_notification = AsyncMock(return_value=[])
    sender.send = AsyncMock()

    count = await use_case.execute(today=TODAY)

    sender.send.assert_not_called()
    assert count == 0


@pytest.mark.asyncio
async def test_uses_todays_date_when_not_provided(use_case, repo, sender):
    repo.list_due_for_notification = AsyncMock(return_value=[])
    sender.send = AsyncMock()

    await use_case.execute()

    called_today = repo.list_due_for_notification.call_args[0][0]
    assert called_today == date.today()


@pytest.mark.asyncio
async def test_subject_includes_days_remaining_single_sub(use_case, repo, sender):
    sub = make_subscription(expiry_date=date(2026, 6, 4))  # 7 days from TODAY
    repo.list_due_for_notification = AsyncMock(return_value=[sub])
    repo.mark_notified = AsyncMock()
    sender.send = AsyncMock()

    await use_case.execute(today=TODAY)

    call_kwargs = sender.send.call_args[1]
    assert "7" in call_kwargs["subject"]


@pytest.mark.asyncio
async def test_body_contains_service_and_expiry_info(use_case, repo, sender):
    sub = make_subscription()
    repo.list_due_for_notification = AsyncMock(return_value=[sub])
    repo.mark_notified = AsyncMock()
    sender.send = AsyncMock()

    await use_case.execute(today=TODAY)

    call_kwargs = sender.send.call_args[1]
    assert "GitHub" in call_kwargs["body"]
    assert "2026-06-05" in call_kwargs["body"]
