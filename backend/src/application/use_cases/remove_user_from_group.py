from domain.exceptions import NotFoundException
from domain.repositories.group_repository import GroupRepository


class RemoveUserFromGroupUseCase:
    def __init__(self, repo: GroupRepository) -> None:
        self._repo = repo

    async def execute(self, group_id: int, user_id: int) -> None:
        group = await self._repo.get_by_id(group_id)
        if group is None:
            raise NotFoundException()
        await self._repo.remove_member(group_id, user_id)
