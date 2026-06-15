from datetime import date

from application.use_cases.create_payment_record import CreatePaymentRecordUseCase
from application.use_cases.delete_payment_record import DeletePaymentRecordUseCase
from application.use_cases.list_payment_records import ListPaymentRecordsUseCase
from application.use_cases.update_payment_record import UpdatePaymentRecordUseCase
from domain.entities.user import User
from domain.exceptions import NotFoundException
from fastapi import APIRouter, Depends, Query
from infrastructure.database.repositories.group_repository import SqlGroupRepository
from infrastructure.database.repositories.payment_record_repository import (
    SqlPaymentRecordRepository,
)
from infrastructure.database.repositories.subscription_repository import (
    SqlSubscriptionRepository,
)
from infrastructure.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user
from api.v1.schemas.base import ApiResponse
from api.v1.schemas.payment_record import (
    PaymentRecordCreate,
    PaymentRecordResponse,
    PaymentRecordUpdate,
)

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


async def _assert_subscription_access(
    subscription_id: int, current_user: User, db: AsyncSession
) -> None:
    """Raises NotFoundException if the current user cannot access the subscription."""
    if current_user.role == "admin":
        return
    sub = await SqlSubscriptionRepository(db).get_by_id(subscription_id)
    if sub is None:
        raise NotFoundException()
    group_ids = await SqlGroupRepository(db).get_group_ids_for_user(current_user.id)
    if sub.group_id is None or sub.group_id not in group_ids:
        raise NotFoundException()


@router.get("", response_model=ApiResponse[list[PaymentRecordResponse]])
async def list_payments(
    subscription_id: int | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    service_name: str | None = Query(default=None),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[PaymentRecordResponse]]:
    repo = SqlPaymentRecordRepository(db)
    use_case = ListPaymentRecordsUseCase(repo)
    records = await use_case.execute(
        subscription_id=subscription_id,
        from_date=from_date,
        to_date=to_date,
        service_name=service_name,
    )
    return ApiResponse.ok(data=[PaymentRecordResponse(**vars(r)) for r in records])


@router.post("", response_model=ApiResponse[PaymentRecordResponse], status_code=201)
async def create_payment(
    body: PaymentRecordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaymentRecordResponse]:
    await _assert_subscription_access(body.subscription_id, current_user, db)
    sub_repo = SqlSubscriptionRepository(db)
    repo = SqlPaymentRecordRepository(db)
    use_case = CreatePaymentRecordUseCase(repo, sub_repo, actor_user_id=current_user.id)
    record = await use_case.execute(**body.model_dump())
    return ApiResponse.ok(data=PaymentRecordResponse(**vars(record)))


@router.put("/{id}", response_model=ApiResponse[PaymentRecordResponse])
async def update_payment(
    id: int,
    body: PaymentRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaymentRecordResponse]:
    repo = SqlPaymentRecordRepository(db)
    payment = await repo.get_by_id(id)
    if payment is None:
        raise NotFoundException()
    await _assert_subscription_access(payment.subscription_id, current_user, db)
    use_case = UpdatePaymentRecordUseCase(repo)
    record = await use_case.execute(payment_id=id, **body.model_dump(exclude_unset=True))
    return ApiResponse.ok(data=PaymentRecordResponse(**vars(record)))


@router.delete("/{id}", response_model=ApiResponse[None])
async def delete_payment(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    repo = SqlPaymentRecordRepository(db)
    payment = await repo.get_by_id(id)
    if payment is None:
        raise NotFoundException()
    await _assert_subscription_access(payment.subscription_id, current_user, db)
    use_case = DeletePaymentRecordUseCase(repo)
    await use_case.execute(payment_id=id)
    return ApiResponse.ok(message="付款紀錄已刪除")
