from datetime import UTC, datetime

from domain.repositories.system_setting_repository import SystemSettingRepository
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import SystemSettingModel


class SqlSystemSettingRepository(SystemSettingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> str | None:
        result = await self._session.execute(
            select(SystemSettingModel.value).where(SystemSettingModel.key == key)
        )
        return result.scalar_one_or_none()

    async def set(self, key: str, value: str) -> None:
        stmt = (
            pg_insert(SystemSettingModel)
            .values(key=key, value=value, updated_at=datetime.now(UTC))
            .on_conflict_do_update(
                index_elements=["key"],
                set_={"value": value, "updated_at": datetime.now(UTC)},
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def get_all(self) -> dict[str, str]:
        result = await self._session.execute(
            select(SystemSettingModel.key, SystemSettingModel.value)
        )
        return {row.key: row.value for row in result.all() if row.value is not None}
