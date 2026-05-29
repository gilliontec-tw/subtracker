from datetime import date
from decimal import Decimal

from domain.entities.payment_record import PaymentRecord
from domain.exceptions import NotFoundException
from domain.repositories.payment_record_repository import PaymentRecordRepository
from domain.repositories.subscription_repository import SubscriptionRepository


class CreatePaymentRecordUseCase:
    def __init__(
        self,
        repo: PaymentRecordRepository,
        sub_repo: SubscriptionRepository,
        actor_user_id: int | None = None,
    ) -> None:
        self._repo = repo
        self._sub_repo = sub_repo
        self._actor_user_id = actor_user_id

    async def execute(
        self,
        subscription_id: int,
        payment_date: date,
        amount: Decimal,
        currency: str = "TWD",
        notes: str | None = None,
    ) -> PaymentRecord:
        sub = await self._sub_repo.get_by_id(subscription_id)
        if sub is None:
            raise NotFoundException()
        record = PaymentRecord(
            subscription_id=subscription_id,
            payment_date=payment_date,
            amount=amount,
            currency=currency,
            source="manual",
            notes=notes,
            created_by=self._actor_user_id,
        )
        return await self._repo.save(record)
