from datetime import date
from src.domain.entities.subscription import NotificationDays, Subscription, SubscriptionStatus
from src.application.use_cases.update_subscription import UpdateSubscriptionUseCase
import pytest


def test_update_calls_repo_update(mock_repo, sample_subscription):
    mock_repo.get_by_id.return_value = sample_subscription
    mock_repo.update.return_value = sample_subscription
    uc = UpdateSubscriptionUseCase(mock_repo)

    result = uc.execute(
        subscription_id=1,
        service_name="GitLab",
        login_account="it2@company.com",
        expiry_date=date(2027, 1, 1),
        notification_emails="bob@company.com",
        notification_days=NotificationDays.FOURTEEN,
        status=SubscriptionStatus.ACTIVE,
    )

    mock_repo.get_by_id.assert_called_once_with(1)
    updated: Subscription = mock_repo.update.call_args[0][0]
    assert updated.service_name == "GitLab"
    assert result is sample_subscription


def test_update_raises_if_not_found(mock_repo):
    mock_repo.get_by_id.return_value = None
    uc = UpdateSubscriptionUseCase(mock_repo)

    with pytest.raises(ValueError, match="not found"):
        uc.execute(
            subscription_id=999,
            service_name="X",
            login_account="x",
            expiry_date=date(2027, 1, 1),
            notification_emails="x@x.com",
            notification_days=NotificationDays.SEVEN,
            status=SubscriptionStatus.ACTIVE,
        )


def test_update_subscription_with_new_fields(mock_repo):
    existing = Subscription(
        id=5,
        service_name="Notion",
        login_account="team@co.com",
        expiry_date=date(2026, 9, 1),
        notification_emails="c@co.com",
        notification_days=NotificationDays.THIRTY,
        status=SubscriptionStatus.ACTIVE,
    )
    mock_repo.get_by_id.return_value = existing
    mock_repo.update.return_value = existing
    uc = UpdateSubscriptionUseCase(mock_repo)
    uc.execute(
        subscription_id=5,
        service_name="Notion",
        login_account="team@co.com",
        expiry_date=date(2026, 9, 1),
        notification_emails="c@co.com",
        notification_days=NotificationDays.THIRTY,
        status=SubscriptionStatus.ACTIVE,
        owner_name="林行政",
        category="生產力工具",
        department="全公司",
        billing_cycle="annual",
    )
    saved = mock_repo.update.call_args[0][0]
    assert saved.owner_name == "林行政"
    assert saved.category == "生產力工具"
    assert saved.department == "全公司"
    assert saved.billing_cycle == "annual"
