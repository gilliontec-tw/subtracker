import pytest
from unittest.mock import MagicMock
from src.application.use_cases.auth.login_user import LoginUserUseCase
from src.domain.entities.user import User
from src.infrastructure.auth.hash_utils import hash_password


@pytest.fixture
def repo():
    return MagicMock()


def _make_user(hashed_pw: str, is_active: bool = True) -> User:
    return User(
        id=1,
        email="alice@gilliontec.com.tw",
        display_name="Alice",
        hashed_password=hashed_pw,
        role="user",
        can_create=False,
        can_update=False,
        can_delete=False,
        is_active=is_active,
    )


def test_login_success(repo):
    pw = hash_password("correct!")
    repo.get_by_email.return_value = _make_user(pw)
    result = LoginUserUseCase(repo).execute("alice@gilliontec.com.tw", "correct!")
    assert result.email == "alice@gilliontec.com.tw"


def test_login_wrong_password(repo):
    pw = hash_password("correct!")
    repo.get_by_email.return_value = _make_user(pw)
    with pytest.raises(ValueError, match="Invalid credentials"):
        LoginUserUseCase(repo).execute("alice@gilliontec.com.tw", "wrong!")


def test_login_user_not_found(repo):
    repo.get_by_email.return_value = None
    with pytest.raises(ValueError, match="Invalid credentials"):
        LoginUserUseCase(repo).execute("nobody@gilliontec.com.tw", "pw")


def test_login_inactive_user(repo):
    pw = hash_password("correct!")
    repo.get_by_email.return_value = _make_user(pw, is_active=False)
    with pytest.raises(ValueError, match="Invalid credentials"):
        LoginUserUseCase(repo).execute("alice@gilliontec.com.tw", "correct!")
