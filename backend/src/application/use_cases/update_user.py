from domain.entities.user import User
from domain.exceptions import NotFoundException
from domain.repositories.user_repository import UserRepository


class UpdateUserUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, id: int, display_name: str, role: str) -> User:
        user = await self._repo.get_by_id(id)
        if user is None:
            raise NotFoundException(f"User {id} not found")

        is_admin = role == "admin"
        user.display_name = display_name
        user.role = role
        user.can_create = is_admin
        user.can_update = is_admin
        user.can_delete = is_admin
        return await self._repo.save(user)
