from domain.entities.subscription import Subscription
from domain.entities.user import User
from domain.exceptions import NotFoundException
from infrastructure.database.repositories.group_repository import SqlGroupRepository
from sqlalchemy.ext.asyncio import AsyncSession


async def get_user_group_ids(user: User, db: AsyncSession) -> list[int] | None:
    """Returns None for admin (no filter), list[int] for regular users (may be empty)."""
    if user.role == "admin":
        return None
    return await SqlGroupRepository(db).get_group_ids_for_user(user.id)


async def assert_subscription_access(
    sub: Subscription | None,
    current_user: User,
    db: AsyncSession,
) -> Subscription:
    """Raise NotFoundException if user cannot access this subscription. Returns sub."""
    if sub is None:
        raise NotFoundException()
    if current_user.role == "admin":
        return sub
    group_ids = await SqlGroupRepository(db).get_group_ids_for_user(current_user.id)
    if sub.group_id is None or sub.group_id not in group_ids:
        raise NotFoundException()
    return sub
