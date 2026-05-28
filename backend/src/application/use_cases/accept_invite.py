import bcrypt
from domain.exceptions import NotFoundException
from domain.repositories.user_repository import UserRepository


class AcceptInviteUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, token: str, password: str) -> None:
        user = await self._repo.get_by_invite_token(token)
        if user is None or not user.is_invite_valid():
            raise NotFoundException("Invite token not found or expired")

        user.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user.invite_token = None
        user.invite_token_expires_at = None
        await self._repo.save(user)
