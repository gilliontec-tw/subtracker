from application.use_cases.add_user_to_group import AddUserToGroupUseCase
from application.use_cases.create_group import CreateGroupUseCase
from application.use_cases.delete_group import DeleteGroupUseCase
from application.use_cases.list_groups import ListGroupsUseCase
from application.use_cases.remove_user_from_group import RemoveUserFromGroupUseCase
from domain.exceptions import NotFoundException
from fastapi import APIRouter, Depends
from infrastructure.database.repositories.group_repository import SqlGroupRepository
from infrastructure.database.repositories.user_repository import SqlUserRepository
from infrastructure.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import require_admin
from api.v1.schemas.base import ApiResponse
from api.v1.schemas.group import (
    GroupBasicResponse,
    GroupCreate,
    GroupMemberAdd,
    GroupMemberResponse,
)

router = APIRouter(prefix="/api/v1/groups", tags=["groups"])


def _get_group_repo(db: AsyncSession = Depends(get_db)) -> SqlGroupRepository:
    return SqlGroupRepository(db)


@router.get("", response_model=ApiResponse[list[GroupBasicResponse]])
async def list_groups(
    _=Depends(require_admin),
    repo: SqlGroupRepository = Depends(_get_group_repo),
) -> ApiResponse[list[GroupBasicResponse]]:
    uc = ListGroupsUseCase(repo)
    groups = await uc.execute()
    return ApiResponse.ok(data=[GroupBasicResponse(id=g.id, name=g.name) for g in groups])


@router.post("", response_model=ApiResponse[GroupBasicResponse], status_code=201)
async def create_group(
    body: GroupCreate,
    _=Depends(require_admin),
    repo: SqlGroupRepository = Depends(_get_group_repo),
) -> ApiResponse[GroupBasicResponse]:
    uc = CreateGroupUseCase(repo)
    group = await uc.execute(name=body.name)
    return ApiResponse.ok(data=GroupBasicResponse(id=group.id, name=group.name))


@router.delete("/{group_id}", response_model=ApiResponse[None])
async def delete_group(
    group_id: int,
    _=Depends(require_admin),
    repo: SqlGroupRepository = Depends(_get_group_repo),
) -> ApiResponse[None]:
    uc = DeleteGroupUseCase(repo)
    await uc.execute(group_id=group_id)
    return ApiResponse.ok(message="群組已刪除")


@router.get("/{group_id}/members", response_model=ApiResponse[list[GroupMemberResponse]])
async def list_group_members(
    group_id: int,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[GroupMemberResponse]]:
    group_repo = SqlGroupRepository(db)
    user_repo = SqlUserRepository(db)
    group = await group_repo.get_by_id(group_id)
    if group is None:
        raise NotFoundException()
    user_ids = await group_repo.get_member_user_ids(group_id)
    users = await user_repo.get_users_by_ids(user_ids)
    members = [
        GroupMemberResponse(
            id=u.id,
            email=u.email,
            display_name=u.display_name,
            role=u.role,
            is_active=u.is_active,
        )
        for u in users
    ]
    return ApiResponse.ok(data=members)


@router.post("/{group_id}/members", response_model=ApiResponse[None], status_code=201)
async def add_group_member(
    group_id: int,
    body: GroupMemberAdd,
    _=Depends(require_admin),
    repo: SqlGroupRepository = Depends(_get_group_repo),
) -> ApiResponse[None]:
    uc = AddUserToGroupUseCase(repo)
    await uc.execute(group_id=group_id, user_id=body.user_id)
    return ApiResponse.ok(message="成員已加入")


@router.delete("/{group_id}/members/{user_id}", response_model=ApiResponse[None])
async def remove_group_member(
    group_id: int,
    user_id: int,
    _=Depends(require_admin),
    repo: SqlGroupRepository = Depends(_get_group_repo),
) -> ApiResponse[None]:
    uc = RemoveUserFromGroupUseCase(repo)
    await uc.execute(group_id=group_id, user_id=user_id)
    return ApiResponse.ok(message="成員已移除")
