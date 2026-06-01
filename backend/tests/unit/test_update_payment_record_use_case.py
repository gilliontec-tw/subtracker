from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.update_payment_record import UpdatePaymentRecordUseCase
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
    uc = UpdatePaymentRecordUseCase(repo)
    with pytest.raises(NotFoundException):
        await uc.execute(payment_id=999, amount=Decimal("500.00"))


@pytest.mark.asyncio
async def test_applies_partial_updates_and_saves():
    repo = MagicMock()
    original = make_record()
    updated = make_record(amount=Decimal("999.00"), notes="edited")
    repo.get_by_id = AsyncMock(return_value=original)
    repo.save = AsyncMock(return_value=updated)
    uc = UpdatePaymentRecordUseCase(repo)
    result = await uc.execute(payment_id=10, amount=Decimal("999.00"), notes="edited")
    assert result.amount == Decimal("999.00")
    saved = repo.save.call_args[0][0]
    assert saved.amount == Decimal("999.00")
    assert saved.notes == "edited"


@pytest.mark.asyncio
async def test_unspecified_fields_are_unchanged():
    repo = MagicMock()
    original = make_record(currency="USD", notes="original")
    repo.get_by_id = AsyncMock(return_value=original)
    repo.save = AsyncMock(return_value=original)
    uc = UpdatePaymentRecordUseCase(repo)
    await uc.execute(payment_id=10, notes="changed")
    saved = repo.save.call_args[0][0]
    assert saved.currency == "USD"
