from datetime import datetime

from domain.entities.user import User
from domain.exceptions import NotFoundException
from domain.repositories.user_repository import UserRepository


class ValidateInviteUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, token: str) -> User:
        user = await self._repo.get_by_invite_token(token)
        if user is None:
            raise NotFoundException("Invite token not found or expired")
        if user.invite_token_expires_at is None or user.invite_token_expires_at < datetime.utcnow():
            raise NotFoundException("Invite token not found or expired")
        return user
