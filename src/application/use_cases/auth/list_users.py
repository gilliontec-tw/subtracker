from src.domain.entities.user import User
from src.domain.repositories.user_repository import UserRepository


class ListUsersUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    def execute(self) -> list[User]:
        return self._repo.get_all()
