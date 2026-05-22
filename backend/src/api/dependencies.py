from typing import Annotated

import jwt
from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import User
from domain.exceptions import ForbiddenException, NotAuthenticatedException
from infrastructure.auth.jwt_service import decode_access_token
from infrastructure.database.repositories.user_repository import SqlUserRepository
from infrastructure.database.session import get_db


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


async def require_manager(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in ("admin", "manager"):
        raise ForbiddenException()
    return current_user


async def require_can_create(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role in ("admin", "manager") or current_user.can_create:
        return current_user
    raise ForbiddenException()


async def require_can_update(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role in ("admin", "manager") or current_user.can_update:
        return current_user
    raise ForbiddenException()


async def require_can_delete(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role in ("admin", "manager") or current_user.can_delete:
        return current_user
    raise ForbiddenException()
