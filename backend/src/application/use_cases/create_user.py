import uuid
from datetime import UTC, datetime, timedelta

from domain.entities.user import User
from domain.exceptions import DuplicateEmailException
from domain.repositories.user_repository import UserRepository


class CreateUserUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, email: str, display_name: str, role: str) -> User:
        existing = await self._repo.get_by_email(email)
        if existing is not None:
            raise DuplicateEmailException(email)

        is_admin = role == "admin"
        token = str(uuid.uuid4())
        expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)

        user = User(
            email=email,
            display_name=display_name,
            password_hash="",
            role=role,
            can_create=is_admin,
            can_update=is_admin,
            can_delete=is_admin,
            is_active=True,
            invite_token=token,
            invite_token_expires_at=expires_at,
        )
        return await self._repo.save(user)
