from datetime import date
from src.domain.entities.subscription import Subscription, NotificationDays
from src.application.use_cases.check_and_notify import CheckAndNotifyUseCase


def make_sub(expiry_date: date, notification_days: NotificationDays, sub_id: int = 1) -> Subscription:
    return Subscription(
        id=sub_id,
        service_name="TestSaaS",
        login_account="it@co.com",
        expiry_date=expiry_date,
        responsible_person_email="admin@co.com",
        notification_days=notification_days,
    )


def test_no_active_subscriptions_sends_no_emails(mock_repo, mock_email_sender):
    mock_repo.get_all_active.return_value = []
    uc = CheckAndNotifyUseCase(mock_repo, mock_email_sender)
    notified = uc.execute(today=date(2026, 5, 1))
    mock_email_sender.send.assert_not_called()
    assert notified == []


def test_subscription_not_due_today_sends_no_email(mock_repo, mock_email_sender):
    sub = make_sub(date(2026, 5, 8), NotificationDays.SEVEN)
    mock_repo.get_all_active.return_value = [sub]
    uc = CheckAndNotifyUseCase(mock_repo, mock_email_sender)
    notified = uc.execute(today=date(2026, 4, 30))  # one day before trigger
    mock_email_sender.send.assert_not_called()
    assert notified == []


def test_subscription_due_today_sends_one_email(mock_repo, mock_email_sender):
    sub = make_sub(date(2026, 5, 8), NotificationDays.SEVEN)
    mock_repo.get_all_active.return_value = [sub]
    uc = CheckAndNotifyUseCase(mock_repo, mock_email_sender)
    notified = uc.execute(today=date(2026, 5, 1))  # trigger day: 5/8 - 7 = 5/1
    mock_email_sender.send.assert_called_once_with(
        to="admin@co.com",
        subject="[提醒] TestSaaS 訂閱將於 2026-05-08 到期（提前 7 天通知）",
        body=mock_email_sender.send.call_args[1]["body"],
    )
    assert notified == [1]


def test_only_triggered_subscriptions_get_emails(mock_repo, mock_email_sender):
    today = date(2026, 5, 1)
    due = make_sub(date(2026, 5, 8), NotificationDays.SEVEN, sub_id=1)
    not_due = make_sub(date(2026, 6, 1), NotificationDays.SEVEN, sub_id=2)
    mock_repo.get_all_active.return_value = [due, not_due]
    uc = CheckAndNotifyUseCase(mock_repo, mock_email_sender)
    notified = uc.execute(today=today)
    assert mock_email_sender.send.call_count == 1
    assert notified == [1]


def test_email_failure_does_not_stop_remaining_notifications(mock_repo, mock_email_sender):
    today = date(2026, 5, 1)
    sub1 = make_sub(date(2026, 5, 8), NotificationDays.SEVEN, sub_id=1)
    sub2 = make_sub(date(2026, 5, 8), NotificationDays.SEVEN, sub_id=2)
    mock_repo.get_all_active.return_value = [sub1, sub2]
    mock_email_sender.send.side_effect = [Exception("SMTP error"), None]
    uc = CheckAndNotifyUseCase(mock_repo, mock_email_sender)
    notified = uc.execute(today=today)
    assert mock_email_sender.send.call_count == 2
    assert 2 in notified  # sub2 still notified despite sub1 failure
