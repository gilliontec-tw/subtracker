import bcrypt
from domain.exceptions import BadRequestException
from domain.repositories.user_repository import UserRepository


class DirectPasswordResetUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, email: str, new_password: str) -> None:
        user = await self._repo.get_by_email(email)
        if user is None or not user.is_active:
            raise BadRequestException("此帳號不存在")

        user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        await self._repo.save(user)
