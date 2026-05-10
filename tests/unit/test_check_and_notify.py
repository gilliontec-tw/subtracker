from datetime import date
from src.domain.entities.subscription import Subscription, NotificationDays
from src.application.use_cases.check_and_notify import CheckAndNotifyUseCase


def make_sub(expiry_date: date, notification_days: NotificationDays, sub_id: int = 1,
             notifications_enabled: bool = True) -> Subscription:
    return Subscription(
        id=sub_id,
        service_name="TestSaaS",
        login_account="it@co.com",
        expiry_date=expiry_date,
        notification_emails="admin@co.com",
        notification_days=notification_days,
        notifications_enabled=notifications_enabled,
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


def test_subscription_due_today_sends_summary_email(mock_repo, mock_email_sender):
    # 單筆到期 → 彙總信主旨含「1 筆」
    sub = make_sub(date(2026, 5, 8), NotificationDays.SEVEN)
    mock_repo.get_all_active.return_value = [sub]
    uc = CheckAndNotifyUseCase(mock_repo, mock_email_sender)
    notified = uc.execute(today=date(2026, 5, 1))  # trigger day: 5/8 - 7 = 5/1
    assert mock_email_sender.send.call_count == 1
    call_kwargs = mock_email_sender.send.call_args[1]
    assert call_kwargs["to"] == "admin@co.com"
    assert "1 筆" in call_kwargs["subject"]
    assert "TestSaaS" in call_kwargs["body"]
    assert notified == [1]


def test_only_triggered_subscriptions_get_emails(mock_repo, mock_email_sender):
    # 只有 1 筆到期 → 只寄 1 封彙總信
    today = date(2026, 5, 1)
    due = make_sub(date(2026, 5, 8), NotificationDays.SEVEN, sub_id=1)
    not_due = make_sub(date(2026, 6, 1), NotificationDays.SEVEN, sub_id=2)
    mock_repo.get_all_active.return_value = [due, not_due]
    uc = CheckAndNotifyUseCase(mock_repo, mock_email_sender)
    notified = uc.execute(today=today)
    assert mock_email_sender.send.call_count == 1
    assert notified == [1]


def test_multiple_due_subscriptions_send_one_summary_email(mock_repo, mock_email_sender):
    # 多筆到期同一收件人 → 只寄 1 封彙總信，主旨含筆數，內文含所有服務名
    today = date(2026, 5, 1)
    sub1 = make_sub(date(2026, 5, 8), NotificationDays.SEVEN, sub_id=1)
    sub2 = Subscription(
        id=2,
        service_name="Slack",
        login_account="it@co.com",
        expiry_date=date(2026, 5, 8),
        notification_emails="admin@co.com",
        notification_days=NotificationDays.SEVEN,
    )
    mock_repo.get_all_active.return_value = [sub1, sub2]
    uc = CheckAndNotifyUseCase(mock_repo, mock_email_sender)
    notified = uc.execute(today=today)
    # 只寄 1 封（收件人相同，去重）
    assert mock_email_sender.send.call_count == 1
    call_kwargs = mock_email_sender.send.call_args[1]
    assert "2 筆" in call_kwargs["subject"]
    assert "TestSaaS" in call_kwargs["body"]
    assert "Slack" in call_kwargs["body"]
    assert notified == [1, 2]


def test_email_failure_returns_empty_notified(mock_repo, mock_email_sender):
    # 彙總信寄送失敗 → 回傳空列表
    today = date(2026, 5, 1)
    sub1 = make_sub(date(2026, 5, 8), NotificationDays.SEVEN, sub_id=1)
    mock_repo.get_all_active.return_value = [sub1]
    mock_email_sender.send.side_effect = Exception("SMTP error")
    uc = CheckAndNotifyUseCase(mock_repo, mock_email_sender)
    notified = uc.execute(today=today)
    assert notified == []


def test_disabled_subscription_is_skipped(mock_repo, mock_email_sender):
    # notifications_enabled=False → no email even when due today
    today = date(2026, 5, 1)
    sub = make_sub(date(2026, 5, 8), NotificationDays.SEVEN, notifications_enabled=False)
    mock_repo.get_all_active.return_value = [sub]
    uc = CheckAndNotifyUseCase(mock_repo, mock_email_sender)
    notified = uc.execute(today=today)
    mock_email_sender.send.assert_not_called()
    assert notified == []


def test_enabled_subscription_is_notified(mock_repo, mock_email_sender):
    # notifications_enabled=True (default) → sends email when due
    today = date(2026, 5, 1)
    sub = make_sub(date(2026, 5, 8), NotificationDays.SEVEN, notifications_enabled=True)
    mock_repo.get_all_active.return_value = [sub]
    uc = CheckAndNotifyUseCase(mock_repo, mock_email_sender)
    notified = uc.execute(today=today)
    assert mock_email_sender.send.call_count == 1
    assert notified == [1]
