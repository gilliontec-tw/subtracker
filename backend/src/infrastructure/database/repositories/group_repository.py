from domain.entities.group import Group
from domain.exceptions import NotFoundException
from domain.repositories.group_repository import GroupRepository
from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import GroupModel, SubscriptionModel, UserGroupModel


def _to_entity(m: GroupModel) -> Group:
    return Group(id=m.id, name=m.name, created_at=m.created_at)


class SqlGroupRepository(GroupRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: int) -> Group | None:
        result = await self._session.execute(select(GroupModel).where(GroupModel.id == id))
        m = result.scalar_one_or_none()
        return _to_entity(m) if m else None

    async def get_by_name(self, name: str) -> Group | None:
        result = await self._session.execute(select(GroupModel).where(GroupModel.name == name))
        m = result.scalar_one_or_none()
        return _to_entity(m) if m else None

    async def list_all(self) -> list[Group]:
        result = await self._session.execute(select(GroupModel).order_by(GroupModel.name))
        return [_to_entity(m) for m in result.scalars().all()]

    async def save(self, entity: Group) -> Group:
        if entity.id is not None:
            result = await self._session.execute(
                select(GroupModel).where(GroupModel.id == entity.id)
            )
            m = result.scalar_one()
            m.name = entity.name
        else:
            m = GroupModel(name=entity.name)
            self._session.add(m)
        await self._session.commit()
        await self._session.refresh(m)
        return _to_entity(m)

    async def delete(self, id: int) -> None:
        result = await self._session.execute(select(GroupModel).where(GroupModel.id == id))
        m = result.scalar_one_or_none()
        if m is None:
            raise NotFoundException()
        await self._session.execute(
            sql_update(SubscriptionModel)
            .where(SubscriptionModel.group_id == id)
            .values(group_id=None)
        )
        await self._session.execute(sql_delete(UserGroupModel).where(UserGroupModel.group_id == id))
        await self._session.delete(m)
        await self._session.commit()

    async def get_group_ids_for_user(self, user_id: int) -> list[int]:
        result = await self._session.execute(
            select(UserGroupModel.group_id).where(UserGroupModel.user_id == user_id)
        )
        return [row[0] for row in result.all()]

    async def get_groups_for_user(self, user_id: int) -> list[Group]:
        result = await self._session.execute(
            select(GroupModel)
            .join(UserGroupModel, UserGroupModel.group_id == GroupModel.id)
            .where(UserGroupModel.user_id == user_id)
            .order_by(GroupModel.name)
        )
        return [_to_entity(m) for m in result.scalars().all()]

    async def get_groups_by_user_ids(self, user_ids: list[int]) -> dict[int, list[Group]]:
        if not user_ids:
            return {}
        result = await self._session.execute(
            select(UserGroupModel.user_id, GroupModel)
            .join(GroupModel, GroupModel.id == UserGroupModel.group_id)
            .where(UserGroupModel.user_id.in_(user_ids))
        )
        mapping: dict[int, list[Group]] = {uid: [] for uid in user_ids}
        for row in result.all():
            uid, group_m = row
            mapping[uid].append(_to_entity(group_m))
        return mapping

    async def get_member_user_ids(self, group_id: int) -> list[int]:
        result = await self._session.execute(
            select(UserGroupModel.user_id).where(UserGroupModel.group_id == group_id)
        )
        return [row[0] for row in result.all()]

    async def add_member(self, group_id: int, user_id: int) -> None:
        existing = await self._session.execute(
            select(UserGroupModel).where(
                UserGroupModel.group_id == group_id,
                UserGroupModel.user_id == user_id,
            )
        )
        if existing.scalar_one_or_none() is None:
            self._session.add(UserGroupModel(group_id=group_id, user_id=user_id))
            await self._session.commit()

    async def remove_member(self, group_id: int, user_id: int) -> None:
        await self._session.execute(
            sql_delete(UserGroupModel).where(
                UserGroupModel.group_id == group_id,
                UserGroupModel.user_id == user_id,
            )
        )
        await self._session.commit()
