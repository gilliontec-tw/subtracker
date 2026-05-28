from domain.entities.user import User
from domain.exceptions import NotFoundException
from domain.repositories.user_repository import UserRepository


class ToggleUserStatusUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, id: int, is_active: bool) -> User:
        user = await self._repo.get_by_id(id)
        if user is None:
            raise NotFoundException(f"User {id} not found")
        user.is_active = is_active
        return await self._repo.save(user)
