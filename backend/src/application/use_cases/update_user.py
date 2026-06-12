from domain.entities.user import User
from domain.exceptions import LastAdminException, NotFoundException
from domain.repositories.user_repository import UserRepository


class UpdateUserUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, id: int, display_name: str, role: str) -> User:
        user = await self._repo.get_by_id(id)
        if user is None:
            raise NotFoundException(f"User {id} not found")

        if user.role == "admin" and role != "admin":
            all_users = await self._repo.list_all()
            admin_count = sum(1 for u in all_users if u.role == "admin")
            if admin_count <= 1:
                raise LastAdminException("Cannot demote the only admin")

        user.display_name = display_name
        user.role = role
        return await self._repo.save(user)
