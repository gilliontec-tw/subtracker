from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.delete_payment_record import DeletePaymentRecordUseCase
from domain.entities.payment_record import PaymentRecord
from domain.exceptions import NotFoundException


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
async def test_raises_not_found_when_payment_missing():
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    uc = DeletePaymentRecordUseCase(repo)
    with pytest.raises(NotFoundException):
        await uc.execute(payment_id=999)


@pytest.mark.asyncio
async def test_calls_delete_with_correct_id():
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=make_record(id=10))
    repo.delete = AsyncMock()
    uc = DeletePaymentRecordUseCase(repo)
    await uc.execute(payment_id=10)
    repo.delete.assert_called_once_with(10)


@pytest.mark.asyncio
async def test_returns_none():
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=make_record())
    repo.delete = AsyncMock()
    uc = DeletePaymentRecordUseCase(repo)
    result = await uc.execute(payment_id=10)
    assert result is None
