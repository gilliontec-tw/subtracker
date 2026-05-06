import pytest
from unittest.mock import MagicMock
from src.application.use_cases.auth.register_user import RegisterUserUseCase
from src.domain.entities.user import User


@pytest.fixture
def repo():
    mock = MagicMock()
    mock.get_by_email.return_value = None
    mock.add.side_effect = lambda u: User(
        id=1,
        email=u.email,
        display_name=u.display_name,
        hashed_password=u.hashed_password,
        role=u.role,
        can_create=u.can_create,
        can_update=u.can_update,
        can_delete=u.can_delete,
    )
    return mock


def test_register_success(repo):
    result = RegisterUserUseCase(repo).execute(
        "alice@gilliontec.com.tw", "Alice",
        can_create=True, can_update=True, can_delete=False,
    )
    assert result.id == 1
    assert result.email == "alice@gilliontec.com.tw"
    assert result.role == "user"
    repo.add.assert_called_once()


def test_register_duplicate_email(repo):
    existing = User(
        id=1, email="alice@gilliontec.com.tw", display_name="Alice",
        hashed_password="x", role="user",
        can_create=False, can_update=False, can_delete=False,
    )
    repo.get_by_email.return_value = existing
    with pytest.raises(ValueError, match="已被使用"):
        RegisterUserUseCase(repo).execute(
            "alice@gilliontec.com.tw", "Alice2",
            can_create=False, can_update=False, can_delete=False,
        )
