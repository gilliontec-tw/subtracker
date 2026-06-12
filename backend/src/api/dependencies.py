from typing import Annotated

import jwt
from application.services.settings_service import SettingsService
from domain.entities.user import User
from domain.exceptions import ForbiddenException, NotAuthenticatedException
from fastapi import Cookie, Depends
from infrastructure.auth.jwt_service import decode_access_token
from infrastructure.database.repositories.system_setting_repository import (
    SqlSystemSettingRepository,
)
from infrastructure.database.repositories.user_repository import SqlUserRepository
from infrastructure.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession


async def get_current_user(
    access_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    if not access_token:
        raise NotAuthenticatedException()
    try:
        payload = decode_access_token(access_token)
    except jwt.PyJWTError:
        raise NotAuthenticatedException()
    user_id = int(payload["sub"])
    repo = SqlUserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise NotAuthenticatedException()
    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise ForbiddenException()
    return current_user


async def get_settings_service(db: AsyncSession = Depends(get_db)) -> SettingsService:
    from api.config import settings as env_settings

    repo = SqlSystemSettingRepository(db)
    return SettingsService(repo, env_settings)
