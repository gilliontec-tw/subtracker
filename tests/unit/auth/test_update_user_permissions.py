import pytest
from unittest.mock import MagicMock
from src.application.use_cases.auth.update_user_permissions import UpdateUserPermissionsUseCase
from src.domain.entities.user import User


@pytest.fixture
def repo():
    return MagicMock()


def _make_user() -> User:
    return User(
        id=2, email="bob@gilliontec.com.tw", display_name="Bob",
        hashed_password="x", role="user",
        can_create=False, can_update=False, can_delete=False,
    )


def test_update_permissions_success(repo):
    user = _make_user()
    repo.get_by_id.return_value = user
    repo.update.side_effect = lambda u: u
    result = UpdateUserPermissionsUseCase(repo).execute(
        user_id=2, can_create=True, can_update=True, can_delete=False, is_active=True,
    )
    assert result.can_create is True
    assert result.can_update is True
    assert result.can_delete is False


def test_update_permissions_user_not_found(repo):
    repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="not found"):
        UpdateUserPermissionsUseCase(repo).execute(
            user_id=99, can_create=True, can_update=True, can_delete=True, is_active=True,
        )
