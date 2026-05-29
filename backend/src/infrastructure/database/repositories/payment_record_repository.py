from datetime import UTC, date

from domain.entities.payment_record import PaymentRecord
from domain.exceptions import NotFoundException
from domain.repositories.payment_record_repository import PaymentRecordRepository
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import PaymentRecordModel, SubscriptionModel


def _to_entity(m: PaymentRecordModel, service_name: str | None = None) -> PaymentRecord:
    return PaymentRecord(
        id=m.id,
        subscription_id=m.subscription_id,
        payment_date=m.payment_date,
        amount=m.amount,
        currency=m.currency or "TWD",
        source=m.source or "manual",
        notes=m.notes,
        created_at=m.created_at.replace(tzinfo=UTC) if m.created_at else None,
        created_by=m.created_by,
        service_name=service_name,
    )


class SqlPaymentRecordRepository(PaymentRecordRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _fetch_with_name(self, payment_id: int) -> PaymentRecord:
        result = await self._session.execute(
            select(PaymentRecordModel, SubscriptionModel.service_name)
            .join(
                SubscriptionModel,
                PaymentRecordModel.subscription_id == SubscriptionModel.id,
                isouter=True,
            )
            .where(PaymentRecordModel.id == payment_id)
        )
        try:
            row = result.one()
        except NoResultFound:
            raise NotFoundException()
        return _to_entity(row[0], row[1])

    async def save(self, record: PaymentRecord) -> PaymentRecord:
        if record.id is not None:
            result = await self._session.execute(
                select(PaymentRecordModel).where(PaymentRecordModel.id == record.id)
            )
            try:
                model = result.scalar_one()
            except NoResultFound:
                raise NotFoundException()
            model.payment_date = record.payment_date
            model.amount = record.amount
            model.currency = record.currency
            model.notes = record.notes
        else:
            model = PaymentRecordModel(
                subscription_id=record.subscription_id,
                payment_date=record.payment_date,
                amount=record.amount,
                currency=record.currency,
                source=record.source,
                notes=record.notes,
                created_by=record.created_by,
            )
            self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return await self._fetch_with_name(model.id)

    async def get_by_id(self, payment_id: int) -> PaymentRecord | None:
        try:
            return await self._fetch_with_name(payment_id)
        except NotFoundException:
            return None

    async def list_by_subscription(self, subscription_id: int) -> list[PaymentRecord]:
        result = await self._session.execute(
            select(PaymentRecordModel, SubscriptionModel.service_name)
            .join(
                SubscriptionModel,
                PaymentRecordModel.subscription_id == SubscriptionModel.id,
                isouter=True,
            )
            .where(PaymentRecordModel.subscription_id == subscription_id)
            .order_by(PaymentRecordModel.payment_date.desc())
        )
        return [_to_entity(row[0], row[1]) for row in result.all()]

    async def list_by_filters(
        self, from_date: date, to_date: date, service_name: str | None
    ) -> list[PaymentRecord]:
        filters = [
            PaymentRecordModel.payment_date >= from_date,
            PaymentRecordModel.payment_date <= to_date,
        ]
        if service_name:
            filters.append(SubscriptionModel.service_name.ilike(f"%{service_name}%"))
        result = await self._session.execute(
            select(PaymentRecordModel, SubscriptionModel.service_name)
            .join(
                SubscriptionModel,
                PaymentRecordModel.subscription_id == SubscriptionModel.id,
                isouter=True,
            )
            .where(*filters)
            .order_by(PaymentRecordModel.payment_date.desc())
            .limit(500)
        )
        return [_to_entity(row[0], row[1]) for row in result.all()]

    async def delete(self, payment_id: int) -> None:
        result = await self._session.execute(
            select(PaymentRecordModel).where(PaymentRecordModel.id == payment_id)
        )
        try:
            model = result.scalar_one()
        except NoResultFound:
            raise NotFoundException()
        await self._session.delete(model)
        await self._session.commit()
