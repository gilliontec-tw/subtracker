from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import UserModel


def _to_entity(m: UserModel) -> User:
    return User(
        id=m.id,
        email=m.email,
        display_name=m.display_name,
        password_hash=m.password_hash or "",
        role=m.role,
        can_create=m.can_create,
        can_update=m.can_update,
        can_delete=m.can_delete,
        is_active=m.is_active,
        invite_token=m.invite_token,
        invite_token_expires_at=m.invite_token_expires_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: int) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.id == id))
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.email == email))
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_invite_token(self, token: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.invite_token == token)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_all(self) -> list[User]:
        result = await self._session.execute(select(UserModel))
        return [_to_entity(m) for m in result.scalars().all()]

    async def save(self, entity: User) -> User:
        if entity.id is not None:
            result = await self._session.execute(select(UserModel).where(UserModel.id == entity.id))
            model = result.scalar_one()
            model.email = entity.email
            model.display_name = entity.display_name
            model.password_hash = entity.password_hash
            model.role = entity.role
            model.can_create = entity.can_create
            model.can_update = entity.can_update
            model.can_delete = entity.can_delete
            model.is_active = entity.is_active
            model.invite_token = entity.invite_token
            model.invite_token_expires_at = entity.invite_token_expires_at
        else:
            model = UserModel(
                email=entity.email,
                display_name=entity.display_name,
                password_hash=entity.password_hash,
                role=entity.role,
                can_create=entity.can_create,
                can_update=entity.can_update,
                can_delete=entity.can_delete,
                is_active=entity.is_active,
                invite_token=entity.invite_token,
                invite_token_expires_at=entity.invite_token_expires_at,
            )
            self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def delete(self, id: int) -> None:
        result = await self._session.execute(select(UserModel).where(UserModel.id == id))
        model = result.scalar_one()
        await self._session.delete(model)
        await self._session.commit()
