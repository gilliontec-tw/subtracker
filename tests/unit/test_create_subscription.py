from datetime import date
from src.domain.entities.subscription import NotificationDays, Subscription
from src.application.use_cases.create_subscription import CreateSubscriptionUseCase


def test_create_calls_repo_add_and_returns_entity(mock_repo, sample_subscription):
    mock_repo.add.return_value = sample_subscription
    uc = CreateSubscriptionUseCase(mock_repo)

    result = uc.execute(
        service_name="GitHub",
        login_account="it@company.com",
        expiry_date=date(2026, 12, 31),
        responsible_person_email="alice@company.com",
        notification_days=NotificationDays.SEVEN,
    )

    mock_repo.add.assert_called_once()
    added_entity: Subscription = mock_repo.add.call_args[0][0]
    assert added_entity.id is None  # not yet persisted when passed to repo
    assert added_entity.service_name == "GitHub"
    assert result is sample_subscription
