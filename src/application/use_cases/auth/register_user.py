from src.domain.entities.user import User
from src.domain.repositories.user_repository import UserRepository
from src.infrastructure.auth.hash_utils import hash_password


class RegisterUserUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    def execute(
        self,
        email: str,
        display_name: str,
        password: str,
        can_create: bool,
        can_update: bool,
        can_delete: bool,
    ) -> User:
        if not email.endswith("@gilliontec.com.tw"):
            raise ValueError("Email must end with @gilliontec.com.tw")
        if self._repo.get_by_email(email) is not None:
            raise ValueError("Email already registered")
        user = User(
            email=email,
            display_name=display_name,
            hashed_password=hash_password(password),
            role="user",
            can_create=can_create,
            can_update=can_update,
            can_delete=can_delete,
        )
        return self._repo.add(user)
