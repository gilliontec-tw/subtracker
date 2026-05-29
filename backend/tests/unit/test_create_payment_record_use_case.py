from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.create_payment_record import CreatePaymentRecordUseCase
from domain.entities.payment_record import PaymentRecord
from domain.entities.subscription import Subscription
from domain.exceptions import NotFoundException


def make_sub(**kwargs) -> Subscription:
    defaults = dict(
        id=1,
        service_name="GitHub",
        login_account="u@corp.com",
        expiry_date=date(2027, 1, 1),
        notification_emails=[],
        notification_days=30,
    )
    defaults.update(kwargs)
    return Subscription(**defaults)


def make_record(**kwargs) -> PaymentRecord:
    defaults = dict(
        id=10,
        subscription_id=1,
        payment_date=date(2026, 5, 1),
        amount=Decimal("1200.00"),
        currency="TWD",
    )
    defaults.update(kwargs)
    return PaymentRecord(**defaults)


@pytest.mark.asyncio
async def test_raises_not_found_when_subscription_missing():
    repo = MagicMock()
    sub_repo = MagicMock()
    sub_repo.get_by_id = AsyncMock(return_value=None)
    uc = CreatePaymentRecordUseCase(repo, sub_repo)
    with pytest.raises(NotFoundException):
        await uc.execute(
            subscription_id=999,
            payment_date=date(2026, 5, 1),
            amount=Decimal("1200.00"),
            currency="TWD",
        )


@pytest.mark.asyncio
async def test_saves_with_source_manual_and_returns_record():
    repo = MagicMock()
    sub_repo = MagicMock()
    sub_repo.get_by_id = AsyncMock(return_value=make_sub())
    repo.save = AsyncMock(return_value=make_record())
    uc = CreatePaymentRecordUseCase(repo, sub_repo, actor_user_id=1)
    result = await uc.execute(
        subscription_id=1,
        payment_date=date(2026, 5, 1),
        amount=Decimal("1200.00"),
        currency="TWD",
    )
    assert result.id == 10
    saved = repo.save.call_args[0][0]
    assert saved.source == "manual"
    assert saved.created_by == 1


@pytest.mark.asyncio
async def test_saves_with_notes():
    repo = MagicMock()
    sub_repo = MagicMock()
    sub_repo.get_by_id = AsyncMock(return_value=make_sub())
    repo.save = AsyncMock(return_value=make_record())
    uc = CreatePaymentRecordUseCase(repo, sub_repo)
    await uc.execute(
        subscription_id=1,
        payment_date=date(2026, 5, 1),
        amount=Decimal("1200.00"),
        currency="TWD",
        notes="年繳",
    )
    saved = repo.save.call_args[0][0]
    assert saved.notes == "年繳"
