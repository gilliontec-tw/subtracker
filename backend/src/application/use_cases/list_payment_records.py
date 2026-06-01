from datetime import date

from domain.entities.payment_record import PaymentRecord
from domain.repositories.payment_record_repository import PaymentRecordRepository


class ListPaymentRecordsUseCase:
    def __init__(self, repo: PaymentRecordRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        subscription_id: int | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        service_name: str | None = None,
    ) -> list[PaymentRecord]:
        if subscription_id is not None:
            return await self._repo.list_by_subscription(subscription_id)
        return await self._repo.list_by_filters(from_date, to_date, service_name)
