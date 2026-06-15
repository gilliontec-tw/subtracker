from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.list_payment_records import ListPaymentRecordsUseCase
from domain.entities.payment_record import PaymentRecord


def make_record(**kwargs) -> PaymentRecord:
    defaults = dict(
        id=1,
        subscription_id=1,
        payment_date=date(2026, 5, 1),
        amount=Decimal("1200.00"),
        currency="TWD",
    )
    defaults.update(kwargs)
    return PaymentRecord(**defaults)


@pytest.mark.asyncio
async def test_subscription_id_path_calls_list_by_subscription():
    repo = MagicMock()
    repo.list_by_subscription = AsyncMock(return_value=[make_record()])
    uc = ListPaymentRecordsUseCase(repo)
    result = await uc.execute(subscription_id=1)
    repo.list_by_subscription.assert_called_once_with(1)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_date_range_path_calls_list_by_filters():
    repo = MagicMock()
    repo.list_by_filters = AsyncMock(return_value=[make_record()])
    uc = ListPaymentRecordsUseCase(repo)
    from_date = date(2026, 5, 1)
    to_date = date(2026, 5, 31)
    result = await uc.execute(from_date=from_date, to_date=to_date, service_name="GitHub")
    repo.list_by_filters.assert_called_once_with(from_date, to_date, "GitHub", None)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_no_params_calls_list_by_filters_with_none():
    repo = MagicMock()
    repo.list_by_filters = AsyncMock(return_value=[])
    uc = ListPaymentRecordsUseCase(repo)
    result = await uc.execute()
    repo.list_by_filters.assert_called_once_with(None, None, None, None)
    assert result == []
