import secrets
from datetime import datetime, timedelta
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
        can_create: bool,
        can_update: bool,
        can_delete: bool,
    ) -> User:
        if self._repo.get_by_email(email) is not None:
            raise ValueError("此 Email 已被使用")
        token = secrets.token_urlsafe(32)
        user = User(
            email=email,
            display_name=display_name,
            hashed_password=hash_password(secrets.token_hex(32)),  # unusable placeholder
            role="user",
            can_create=can_create,
            can_update=can_update,
            can_delete=can_delete,
            invite_token=token,
            invite_expires_at=datetime.now() + timedelta(hours=72),
        )
        return self._repo.add(user)
