from application.use_cases.create_user import CreateUserUseCase
from application.use_cases.delete_user import DeleteUserUseCase
from application.use_cases.toggle_user_status import ToggleUserStatusUseCase
from application.use_cases.update_user import UpdateUserUseCase
from fastapi import APIRouter, Depends
from infrastructure.database.repositories.user_repository import SqlUserRepository
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, require_admin
from api.v1.schemas.base import ApiResponse
from api.v1.schemas.user import (
    CreateUserRequest,
    CreateUserResponse,
    UpdateUserRequest,
    UserListItemResponse,
    UserStatusRequest,
)

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _to_response(user) -> UserListItemResponse:
    return UserListItemResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
        created_at=str(user.created_at.date()) if user.created_at else None,
    )


@router.get("", response_model=ApiResponse[list[UserListItemResponse]])
async def list_users(
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = SqlUserRepository(db)
    users = await repo.list_all()
    return ApiResponse.ok(data=[_to_response(u) for u in users])


@router.post("", response_model=ApiResponse[CreateUserResponse])
async def create_user(
    body: CreateUserRequest,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = SqlUserRepository(db)
    use_case = CreateUserUseCase(repo)
    user = await use_case.execute(
        email=body.email,
        display_name=body.display_name,
        role=body.role,
    )
    return ApiResponse.ok(data=CreateUserResponse(id=user.id, invite_token=user.invite_token))


@router.patch("/{id}", response_model=ApiResponse[UserListItemResponse])
async def update_user(
    id: int,
    body: UpdateUserRequest,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = SqlUserRepository(db)
    use_case = UpdateUserUseCase(repo)
    user = await use_case.execute(id=id, display_name=body.display_name, role=body.role)
    return ApiResponse.ok(data=_to_response(user))


@router.patch("/{id}/status", response_model=ApiResponse[UserListItemResponse])
async def toggle_status(
    id: int,
    body: UserStatusRequest,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = SqlUserRepository(db)
    use_case = ToggleUserStatusUseCase(repo)
    user = await use_case.execute(id=id, is_active=body.is_active)
    return ApiResponse.ok(data=_to_response(user))


@router.delete("/{id}", response_model=ApiResponse[None])
async def delete_user(
    id: int,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = SqlUserRepository(db)
    use_case = DeleteUserUseCase(repo)
    await use_case.execute(id=id)
    return ApiResponse.ok()
