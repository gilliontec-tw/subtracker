from domain.entities.payment_record import PaymentRecord
from domain.exceptions import NotFoundException
from domain.repositories.payment_record_repository import PaymentRecordRepository


class UpdatePaymentRecordUseCase:
    def __init__(self, repo: PaymentRecordRepository) -> None:
        self._repo = repo

    async def execute(self, payment_id: int, **updates) -> PaymentRecord:
        record = await self._repo.get_by_id(payment_id)
        if record is None:
            raise NotFoundException()
        for field, value in updates.items():
            setattr(record, field, value)
        return await self._repo.save(record)
