from src.application.use_cases.delete_subscription import DeleteSubscriptionUseCase


def test_delete_calls_deactivate(mock_repo):
    uc = DeleteSubscriptionUseCase(mock_repo)
    uc.execute(1)
    mock_repo.deactivate.assert_called_once_with(1)
