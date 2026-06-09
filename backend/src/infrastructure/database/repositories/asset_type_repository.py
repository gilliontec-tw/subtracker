from domain.entities.asset_type import AssetType
from domain.exceptions import ConflictException, NotFoundException
from domain.repositories.asset_type_repository import AssetTypeRepository
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import AssetTypeModel, SubscriptionModel


def _to_entity(m: AssetTypeModel) -> AssetType:
    return AssetType(
        id=m.id,
        name=m.name,
        created_by=m.created_by,
        created_at=m.created_at,
    )


class SqlAssetTypeRepository(AssetTypeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[AssetType]:
        result = await self._session.execute(select(AssetTypeModel).order_by(AssetTypeModel.id))
        return [_to_entity(m) for m in result.scalars().all()]

    async def get_by_id(self, id: int) -> AssetType | None:
        result = await self._session.execute(select(AssetTypeModel).where(AssetTypeModel.id == id))
        m = result.scalar_one_or_none()
        return _to_entity(m) if m else None

    async def save(self, entity: AssetType) -> AssetType:
        if entity.id is not None:
            result = await self._session.execute(
                select(AssetTypeModel).where(AssetTypeModel.id == entity.id)
            )
            try:
                model = result.scalar_one()
            except NoResultFound:
                raise NotFoundException()
            model.name = entity.name
        else:
            model = AssetTypeModel(
                name=entity.name,
                created_by=entity.created_by,
            )
            self._session.add(model)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise ConflictException("此名稱已存在")
        await self._session.refresh(model)
        return _to_entity(model)

    async def delete(self, id: int) -> None:
        count_result = await self._session.execute(
            select(func.count())
            .select_from(SubscriptionModel)
            .where(
                SubscriptionModel.asset_type_id == id,
                SubscriptionModel.deleted_at.is_(None),
            )
        )
        if count_result.scalar_one() > 0:
            raise ConflictException("此類型尚有項目使用，無法刪除")
        result = await self._session.execute(select(AssetTypeModel).where(AssetTypeModel.id == id))
        try:
            model = result.scalar_one()
        except NoResultFound:
            raise NotFoundException()
        await self._session.delete(model)
        await self._session.commit()
