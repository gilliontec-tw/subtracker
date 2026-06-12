from domain.exceptions import NotFoundException
from domain.repositories.group_repository import GroupRepository


class DeleteGroupUseCase:
    def __init__(self, repo: GroupRepository) -> None:
        self._repo = repo

    async def execute(self, group_id: int) -> None:
        group = await self._repo.get_by_id(group_id)
        if group is None:
            raise NotFoundException()
        await self._repo.delete(group_id)
