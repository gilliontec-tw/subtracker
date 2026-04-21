import pytest
from unittest.mock import MagicMock
from src.application.use_cases.auth.change_password import ChangePasswordUseCase
from src.domain.entities.user import User
from src.infrastructure.auth.hash_utils import hash_password


@pytest.fixture
def repo():
    return MagicMock()


def _make_user(hashed_pw: str) -> User:
    return User(
        id=1,
        email="alice@gilliontec.com.tw",
        display_name="Alice",
        hashed_password=hashed_pw,
        role="user",
        can_create=False,
        can_update=False,
        can_delete=False,
    )


def test_change_password_success(repo):
    pw = hash_password("OldPass1!")
    repo.get_by_id.return_value = _make_user(pw)
    repo.update.side_effect = lambda u: u
    ChangePasswordUseCase(repo).execute(
        user_id=1,
        current_password="OldPass1!",
        new_password="NewPass2@",
    )
    repo.update.assert_called_once()
    saved_user = repo.update.call_args[0][0]
    assert saved_user.hashed_password != pw


def test_change_password_wrong_current(repo):
    pw = hash_password("OldPass1!")
    repo.get_by_id.return_value = _make_user(pw)
    with pytest.raises(ValueError, match="Current password"):
        ChangePasswordUseCase(repo).execute(
            user_id=1,
            current_password="WrongPass!",
            new_password="NewPass2@",
        )


def test_change_password_user_not_found(repo):
    repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="not found"):
        ChangePasswordUseCase(repo).execute(
            user_id=99,
            current_password="any",
            new_password="any2",
        )
