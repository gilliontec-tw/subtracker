from datetime import date
from decimal import Decimal

from domain.entities.subscription import SUPPORTED_CURRENCIES, Subscription


def make_subscription(**kwargs) -> Subscription:
    defaults = dict(
        service_name="GitHub",
        login_account="user@corp.com",
        expiry_date=date(2027, 1, 1),
        notification_emails=["admin@corp.com"],
        notification_days=30,
    )
    defaults.update(kwargs)
    return Subscription(**defaults)


def test_can_instantiate_with_required_fields():
    sub = make_subscription()
    assert sub.service_name == "GitHub"
    assert sub.expiry_date == date(2027, 1, 1)


def test_defaults():
    sub = make_subscription()
    assert sub.currency == "TWD"
    assert sub.auto_renew is False
    assert sub.status == "active"
    assert sub.id is None
    assert sub.cost is None
    assert sub.exchange_rate is None


def test_supported_currencies_contains_expected_values():
    assert "TWD" in SUPPORTED_CURRENCIES
    assert "USD" in SUPPORTED_CURRENCIES
    assert "EUR" in SUPPORTED_CURRENCIES
    assert "JPY" in SUPPORTED_CURRENCIES
    assert "GBP" in SUPPORTED_CURRENCIES
    assert "CNY" in SUPPORTED_CURRENCIES
    assert len(SUPPORTED_CURRENCIES) == 6


def test_optional_fields_accept_none():
    sub = make_subscription(cost=None, exchange_rate=None, notes=None, owner_name=None)
    assert sub.cost is None
    assert sub.exchange_rate is None


def test_accepts_decimal_cost_and_exchange_rate():
    sub = make_subscription(
        cost=Decimal("99.99"),
        currency="USD",
        exchange_rate=Decimal("31.500000"),
    )
    assert sub.cost == Decimal("99.99")
    assert sub.exchange_rate == Decimal("31.500000")


def test_last_notified_date_defaults_to_none():
    sub = make_subscription()
    assert sub.last_notified_date is None
