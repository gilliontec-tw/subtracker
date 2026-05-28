from domain.entities.user import User
from domain.exceptions import NotFoundException
from domain.repositories.user_repository import UserRepository


class ValidateInviteUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, token: str) -> User:
        user = await self._repo.get_by_invite_token(token)
        if user is None or not user.is_invite_valid():
            raise NotFoundException("Invite token not found or expired")
        return user
