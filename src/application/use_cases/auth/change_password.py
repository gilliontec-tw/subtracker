from src.domain.repositories.user_repository import UserRepository
from src.infrastructure.auth.hash_utils import hash_password, verify_password


class ChangePasswordUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    def execute(self, user_id: int, current_password: str, new_password: str) -> None:
        user = self._repo.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")
        if not verify_password(current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")
        user.hashed_password = hash_password(new_password)
        self._repo.update(user)
