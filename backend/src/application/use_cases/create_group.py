from domain.entities.group import Group
from domain.exceptions import ConflictException
from domain.repositories.group_repository import GroupRepository


class CreateGroupUseCase:
    def __init__(self, repo: GroupRepository) -> None:
        self._repo = repo

    async def execute(self, name: str) -> Group:
        existing = await self._repo.get_by_name(name)
        if existing is not None:
            raise ConflictException(f"群組 '{name}' 已存在")
        return await self._repo.save(Group(name=name))
