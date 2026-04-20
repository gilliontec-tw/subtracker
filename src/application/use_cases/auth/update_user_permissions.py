from src.domain.entities.user import User
from src.domain.repositories.user_repository import UserRepository


class UpdateUserPermissionsUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    def execute(
        self,
        user_id: int,
        can_create: bool,
        can_update: bool,
        can_delete: bool,
        is_active: bool,
    ) -> User:
        user = self._repo.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")
        user.can_create = can_create
        user.can_update = can_update
        user.can_delete = can_delete
        user.is_active  = is_active
        return self._repo.update(user)
