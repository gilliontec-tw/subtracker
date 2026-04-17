from src.application.use_cases.list_subscriptions import ListSubscriptionsUseCase


def test_list_delegates_to_repo(mock_repo, sample_subscription):
    mock_repo.get_all_active.return_value = [sample_subscription]
    uc = ListSubscriptionsUseCase(mock_repo)
    result = uc.execute()
    mock_repo.get_all_active.assert_called_once()
    assert result == [sample_subscription]
