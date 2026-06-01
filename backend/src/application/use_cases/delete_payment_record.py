from domain.exceptions import NotFoundException
from domain.repositories.payment_record_repository import PaymentRecordRepository


class DeletePaymentRecordUseCase:
    def __init__(self, repo: PaymentRecordRepository) -> None:
        self._repo = repo

    async def execute(self, payment_id: int) -> None:
        record = await self._repo.get_by_id(payment_id)
        if record is None:
            raise NotFoundException()
        await self._repo.delete(payment_id)
