import uuid
from datetime import UTC, datetime, timedelta

from domain.entities.user import User
from domain.exceptions import ForbiddenException, NotFoundException
from domain.repositories.user_repository import UserRepository


class RegenerateInviteUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: int) -> User:
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundException("使用者不存在")
        if not user.is_active:
            raise ForbiddenException("無法為已停用的使用者重設連結")
        user.invite_token = str(uuid.uuid4())
        user.invite_token_expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)
        return await self._repo.save(user)
