from domain.exceptions import LastAdminException, NotFoundException
from domain.repositories.user_repository import UserRepository


class DeleteUserUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, id: int) -> None:
        user = await self._repo.get_by_id(id)
        if user is None:
            raise NotFoundException(f"User {id} not found")

        if user.role == "admin":
            all_users = await self._repo.list_all()
            admin_count = sum(1 for u in all_users if u.role == "admin")
            if admin_count <= 1:
                raise LastAdminException("Cannot delete the only admin")

        await self._repo.delete(id)
