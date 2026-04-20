from datetime import datetime
from src.domain.entities.user import User
from src.domain.repositories.user_repository import UserRepository
from src.infrastructure.auth.hash_utils import verify_password


class LoginUserUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    def execute(self, email: str, password: str) -> User:
        user = self._repo.get_by_email(email)
        if not user or not user.is_active:
            raise ValueError("Invalid credentials")
        if not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")
        user.last_login_at = datetime.now()
        self._repo.update(user)
        return user
