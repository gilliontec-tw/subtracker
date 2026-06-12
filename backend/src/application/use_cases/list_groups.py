from domain.entities.group import Group
from domain.repositories.group_repository import GroupRepository


class ListGroupsUseCase:
    def __init__(self, repo: GroupRepository) -> None:
        self._repo = repo

    async def execute(self) -> list[Group]:
        return await self._repo.list_all()
