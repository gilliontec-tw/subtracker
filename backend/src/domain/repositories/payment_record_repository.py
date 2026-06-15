from abc import ABC, abstractmethod
from datetime import date

from domain.entities.payment_record import PaymentRecord


class PaymentRecordRepository(ABC):
    @abstractmethod
    async def save(self, record: PaymentRecord) -> PaymentRecord: ...

    @abstractmethod
    async def get_by_id(self, payment_id: int) -> PaymentRecord | None: ...

    @abstractmethod
    async def list_by_subscription(self, subscription_id: int) -> list[PaymentRecord]: ...

    @abstractmethod
    async def list_by_filters(
        self,
        from_date: date | None,
        to_date: date | None,
        service_name: str | None,
        group_ids: list[int] | None = None,
    ) -> list[PaymentRecord]: ...

    @abstractmethod
    async def delete(self, payment_id: int) -> None: ...
