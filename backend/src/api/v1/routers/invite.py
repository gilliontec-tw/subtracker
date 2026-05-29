from application.use_cases.accept_invite import AcceptInviteUseCase
from application.use_cases.validate_invite import ValidateInviteUseCase
from fastapi import APIRouter, Depends
from infrastructure.database.repositories.user_repository import SqlUserRepository
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from api.v1.schemas.base import ApiResponse
from api.v1.schemas.user import InviteAcceptRequest, InviteValidateResponse

router = APIRouter(prefix="/api/v1/invite", tags=["invite"])


@router.get("/{token}", response_model=ApiResponse[InviteValidateResponse])
async def validate_invite(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    repo = SqlUserRepository(db)
    use_case = ValidateInviteUseCase(repo)
    user = await use_case.execute(token)
    return ApiResponse.ok(data=InviteValidateResponse(email=user.email))


@router.post("/{token}", response_model=ApiResponse[None])
async def accept_invite(
    token: str,
    body: InviteAcceptRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = SqlUserRepository(db)
    use_case = AcceptInviteUseCase(repo)
    await use_case.execute(token=token, password=body.password)
    return ApiResponse.ok(message="密碼設定成功，請登入")
