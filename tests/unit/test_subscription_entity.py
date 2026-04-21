from datetime import date, timedelta
from decimal import Decimal
import pytest
from src.domain.entities.subscription import Subscription, NotificationDays, SubscriptionStatus


def make_sub(expiry_date: date, notification_days: NotificationDays) -> Subscription:
    return Subscription(
        service_name="GitHub",
        login_account="it@company.com",
        expiry_date=expiry_date,
        notification_emails="alice@company.com",
        notification_days=notification_days,
    )


def test_should_notify_on_trigger_day():
    # expiry 2026-05-08, notify 7 days before → trigger on 2026-05-01
    sub = make_sub(date(2026, 5, 8), NotificationDays.SEVEN)
    assert sub.should_notify_today(date(2026, 5, 1)) is True


def test_should_not_notify_one_day_before_trigger():
    sub = make_sub(date(2026, 5, 8), NotificationDays.SEVEN)
    assert sub.should_notify_today(date(2026, 4, 30)) is False


def test_should_not_notify_one_day_after_trigger():
    sub = make_sub(date(2026, 5, 8), NotificationDays.SEVEN)
    assert sub.should_notify_today(date(2026, 5, 2)) is False


def test_should_not_notify_on_expiry_day_itself():
    sub = make_sub(date(2026, 5, 8), NotificationDays.SEVEN)
    assert sub.should_notify_today(date(2026, 5, 8)) is False


def test_all_threshold_values_trigger_correctly():
    thresholds = [
        (NotificationDays.THREE, 3),
        (NotificationDays.SEVEN, 7),
        (NotificationDays.FOURTEEN, 14),
        (NotificationDays.THIRTY, 30),
        (NotificationDays.NINETY, 90),
        (NotificationDays.ONE_TWENTY, 120),
    ]
    expiry = date(2026, 12, 31)
    for enum_val, days in thresholds:
        trigger = expiry - timedelta(days=days)
        sub = make_sub(expiry, enum_val)
        assert sub.should_notify_today(trigger) is True, f"Failed for {days} days"
        assert sub.should_notify_today(trigger - timedelta(days=1)) is False
        assert sub.should_notify_today(trigger + timedelta(days=1)) is False


def test_subscription_is_active_by_default():
    sub = make_sub(date(2026, 12, 31), NotificationDays.SEVEN)
    assert sub.is_active is True


def test_id_is_none_before_persistence():
    sub = make_sub(date(2026, 12, 31), NotificationDays.SEVEN)
    assert sub.id is None


def test_subscription_status_defaults_to_active():
    sub = make_sub(date(2026, 12, 31), NotificationDays.SEVEN)
    assert sub.status == SubscriptionStatus.ACTIVE


def test_subscription_cost_defaults_to_none():
    sub = make_sub(date(2026, 12, 31), NotificationDays.SEVEN)
    assert sub.cost is None
    assert sub.currency == "TWD"
