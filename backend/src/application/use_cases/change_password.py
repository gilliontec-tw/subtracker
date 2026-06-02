import bcrypt
from domain.entities.user import User
from domain.exceptions import ForbiddenException
from domain.repositories.user_repository import UserRepository


class ChangePasswordUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, user: User, current_password: str, new_password: str) -> None:
        if not bcrypt.checkpw(current_password.encode(), user.password_hash.encode()):
            raise ForbiddenException("目前密碼不正確")
        user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        await self._repo.save(user)
