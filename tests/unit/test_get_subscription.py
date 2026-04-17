import pytest
from src.application.use_cases.get_subscription import GetSubscriptionUseCase


def test_get_returns_subscription(mock_repo, sample_subscription):
    mock_repo.get_by_id.return_value = sample_subscription
    uc = GetSubscriptionUseCase(mock_repo)
    result = uc.execute(1)
    assert result is sample_subscription


def test_get_raises_if_not_found(mock_repo):
    mock_repo.get_by_id.return_value = None
    uc = GetSubscriptionUseCase(mock_repo)
    with pytest.raises(ValueError, match="not found"):
        uc.execute(999)
