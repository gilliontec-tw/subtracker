from application.use_cases.create_subscription import CreateSubscriptionUseCase
from application.use_cases.delete_subscription import DeleteSubscriptionUseCase
from application.use_cases.get_subscription import GetSubscriptionUseCase
from application.use_cases.list_subscriptions import ListSubscriptionsUseCase
from application.use_cases.update_subscription import UpdateSubscriptionUseCase
from domain.entities.user import User
from fastapi import APIRouter, Depends
from infrastructure.database.repositories.subscription_repository import (
    SqlSubscriptionRepository,
)
from infrastructure.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    get_current_user,
    require_can_create,
    require_can_delete,
    require_can_update,
)
from api.v1.schemas.base import ApiResponse, PaginationMeta
from api.v1.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionUpdate,
)

router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"])


def _get_repo(db: AsyncSession = Depends(get_db)) -> SqlSubscriptionRepository:
    return SqlSubscriptionRepository(db)


@router.get("/", response_model=ApiResponse[list[SubscriptionResponse]])
async def list_subscriptions(
    limit: int = 50,
    offset: int = 0,
    show_cancelled: bool = False,
    _: User = Depends(get_current_user),
    repo: SqlSubscriptionRepository = Depends(_get_repo),
) -> ApiResponse[list[SubscriptionResponse]]:
    use_case = ListSubscriptionsUseCase(repo)
    items, total = await use_case.execute(limit=limit, offset=offset, show_cancelled=show_cancelled)
    return ApiResponse.ok(
        data=[SubscriptionResponse(**vars(s)) for s in items],
        meta=PaginationMeta(total=total, limit=limit, offset=offset).model_dump(),
    )


@router.post("/", response_model=ApiResponse[SubscriptionResponse], status_code=201)
async def create_subscription(
    body: SubscriptionCreate,
    _: User = Depends(require_can_create),
    repo: SqlSubscriptionRepository = Depends(_get_repo),
) -> ApiResponse[SubscriptionResponse]:
    use_case = CreateSubscriptionUseCase(repo)
    sub = await use_case.execute(**body.model_dump())
    return ApiResponse.ok(data=SubscriptionResponse(**vars(sub)))


@router.get("/{id}", response_model=ApiResponse[SubscriptionResponse])
async def get_subscription(
    id: int,
    _: User = Depends(get_current_user),
    repo: SqlSubscriptionRepository = Depends(_get_repo),
) -> ApiResponse[SubscriptionResponse]:
    use_case = GetSubscriptionUseCase(repo)
    sub = await use_case.execute(subscription_id=id)
    return ApiResponse.ok(data=SubscriptionResponse(**vars(sub)))


@router.put("/{id}", response_model=ApiResponse[SubscriptionResponse])
async def update_subscription(
    id: int,
    body: SubscriptionUpdate,
    _: User = Depends(require_can_update),
    repo: SqlSubscriptionRepository = Depends(_get_repo),
) -> ApiResponse[SubscriptionResponse]:
    use_case = UpdateSubscriptionUseCase(repo)
    sub = await use_case.execute(subscription_id=id, **body.model_dump(exclude_unset=True))
    return ApiResponse.ok(data=SubscriptionResponse(**vars(sub)))


@router.delete("/{id}", response_model=ApiResponse[None])
async def delete_subscription(
    id: int,
    _: User = Depends(require_can_delete),
    repo: SqlSubscriptionRepository = Depends(_get_repo),
) -> ApiResponse[None]:
    use_case = DeleteSubscriptionUseCase(repo)
    await use_case.execute(subscription_id=id)
    return ApiResponse.ok(message="Subscription deleted")
