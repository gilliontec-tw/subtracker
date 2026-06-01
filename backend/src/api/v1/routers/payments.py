from datetime import date

from application.use_cases.create_payment_record import CreatePaymentRecordUseCase
from application.use_cases.delete_payment_record import DeletePaymentRecordUseCase
from application.use_cases.list_payment_records import ListPaymentRecordsUseCase
from application.use_cases.update_payment_record import UpdatePaymentRecordUseCase
from domain.entities.user import User
from fastapi import APIRouter, Depends, Query
from infrastructure.database.repositories.payment_record_repository import (
    SqlPaymentRecordRepository,
)
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
from api.v1.schemas.base import ApiResponse
from api.v1.schemas.payment_record import (
    PaymentRecordCreate,
    PaymentRecordResponse,
    PaymentRecordUpdate,
)

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


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
    current_user: User = Depends(require_can_create),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaymentRecordResponse]:
    sub_repo = SqlSubscriptionRepository(db)
    repo = SqlPaymentRecordRepository(db)
    use_case = CreatePaymentRecordUseCase(repo, sub_repo, actor_user_id=current_user.id)
    record = await use_case.execute(**body.model_dump())
    return ApiResponse.ok(data=PaymentRecordResponse(**vars(record)))


@router.put("/{id}", response_model=ApiResponse[PaymentRecordResponse])
async def update_payment(
    id: int,
    body: PaymentRecordUpdate,
    _: User = Depends(require_can_update),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaymentRecordResponse]:
    repo = SqlPaymentRecordRepository(db)
    use_case = UpdatePaymentRecordUseCase(repo)
    record = await use_case.execute(payment_id=id, **body.model_dump(exclude_unset=True))
    return ApiResponse.ok(data=PaymentRecordResponse(**vars(record)))


@router.delete("/{id}", response_model=ApiResponse[None])
async def delete_payment(
    id: int,
    _: User = Depends(require_can_delete),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    repo = SqlPaymentRecordRepository(db)
    use_case = DeletePaymentRecordUseCase(repo)
    await use_case.execute(payment_id=id)
    return ApiResponse.ok(message="付款紀錄已刪除")
