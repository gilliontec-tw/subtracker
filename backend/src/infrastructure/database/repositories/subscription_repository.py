import json
from datetime import UTC, date, datetime

from domain.entities.subscription import Subscription
from domain.exceptions import NotFoundException
from domain.repositories.subscription_repository import SubscriptionRepository
from sqlalchemy import func, or_, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import AssetTypeModel, GroupModel, SubscriptionModel


def _to_entity(
    m: SubscriptionModel,
    asset_type_name: str | None = None,
    group_name: str | None = None,
) -> Subscription:
    return Subscription(
        id=m.id,
        service_name=m.service_name,
        login_account=m.login_account,
        expiry_date=m.expiry_date,
        notification_emails=json.loads(m.notification_emails) if m.notification_emails else [],
        notification_days=m.notification_days if m.notification_days is not None else 30,
        cost=m.cost,
        currency=m.currency or "TWD",
        exchange_rate=m.exchange_rate,
        notes=m.notes,
        owner_name=m.owner_name,
        login_password=m.login_password,
        department=m.department,
        billing_cycle=m.billing_cycle,
        payment_account=m.payment_account,
        auto_renew=m.auto_renew or False,
        trial_end_date=m.trial_end_date,
        next_billing_date=m.next_billing_date,
        last_notified_date=m.last_notified_date,
        status=m.status or "active",
        asset_type_id=m.asset_type_id,
        asset_type_name=asset_type_name,
        group_id=m.group_id,
        group_name=group_name,
        deleted_at=m.deleted_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _with_joins(stmt):
    return (
        stmt.outerjoin(AssetTypeModel, SubscriptionModel.asset_type_id == AssetTypeModel.id)
        .outerjoin(GroupModel, SubscriptionModel.group_id == GroupModel.id)
        .add_columns(
            AssetTypeModel.name.label("asset_type_name"),
            GroupModel.name.label("group_name"),
        )
    )


class SqlSubscriptionRepository(SubscriptionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: int) -> Subscription | None:
        result = await self._session.execute(
            _with_joins(
                select(SubscriptionModel).where(
                    SubscriptionModel.id == id,
                    SubscriptionModel.deleted_at.is_(None),
                )
            )
        )
        row = result.one_or_none()
        return _to_entity(row[0], row[1], row[2]) if row else None

    async def list_all(self) -> list[Subscription]:
        result = await self._session.execute(
            _with_joins(
                select(SubscriptionModel)
                .where(SubscriptionModel.deleted_at.is_(None))
                .order_by(SubscriptionModel.expiry_date)
            )
        )
        return [_to_entity(row[0], row[1], row[2]) for row in result.all()]

    async def list_paginated(
        self,
        limit: int,
        offset: int,
        show_suspended: bool,
        group_ids: list[int] | None = None,
    ) -> tuple[list[Subscription], int]:
        if group_ids is not None and not group_ids:
            return [], 0

        base_filter = [SubscriptionModel.deleted_at.is_(None)]
        if not show_suspended:
            base_filter.append(SubscriptionModel.status != "suspended")
        if group_ids is not None:
            base_filter.append(SubscriptionModel.group_id.in_(group_ids))

        count_result = await self._session.execute(
            select(func.count()).select_from(SubscriptionModel).where(*base_filter)
        )
        total = count_result.scalar_one()

        data_result = await self._session.execute(
            _with_joins(
                select(SubscriptionModel)
                .where(*base_filter)
                .order_by(SubscriptionModel.expiry_date)
                .limit(limit)
                .offset(offset)
            )
        )
        items = [_to_entity(row[0], row[1], row[2]) for row in data_result.all()]
        return items, total

    async def save(self, entity: Subscription) -> Subscription:
        emails_json = json.dumps(entity.notification_emails)
        if entity.id is not None:
            result = await self._session.execute(
                select(SubscriptionModel).where(
                    SubscriptionModel.id == entity.id,
                    SubscriptionModel.deleted_at.is_(None),
                )
            )
            try:
                model = result.scalar_one()
            except NoResultFound:
                raise NotFoundException()
            model.service_name = entity.service_name
            model.login_account = entity.login_account
            model.expiry_date = entity.expiry_date
            model.notification_emails = emails_json
            model.notification_days = entity.notification_days
            model.cost = entity.cost
            model.currency = entity.currency
            model.exchange_rate = entity.exchange_rate
            model.notes = entity.notes
            model.owner_name = entity.owner_name
            model.login_password = entity.login_password
            model.department = entity.department
            model.billing_cycle = entity.billing_cycle
            model.payment_account = entity.payment_account
            model.auto_renew = entity.auto_renew
            model.trial_end_date = entity.trial_end_date
            model.next_billing_date = entity.next_billing_date
            model.last_notified_date = entity.last_notified_date
            model.status = entity.status
            model.asset_type_id = entity.asset_type_id
            model.group_id = entity.group_id
        else:
            model = SubscriptionModel(
                service_name=entity.service_name,
                login_account=entity.login_account,
                expiry_date=entity.expiry_date,
                notification_emails=emails_json,
                notification_days=entity.notification_days,
                cost=entity.cost,
                currency=entity.currency,
                exchange_rate=entity.exchange_rate,
                notes=entity.notes,
                owner_name=entity.owner_name,
                login_password=entity.login_password,
                department=entity.department,
                billing_cycle=entity.billing_cycle,
                payment_account=entity.payment_account,
                auto_renew=entity.auto_renew,
                trial_end_date=entity.trial_end_date,
                next_billing_date=entity.next_billing_date,
                last_notified_date=entity.last_notified_date,
                status=entity.status,
                asset_type_id=entity.asset_type_id,
                group_id=entity.group_id,
            )
            self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return await self.get_by_id(model.id) or _to_entity(model)

    async def delete(self, id: int) -> None:
        result = await self._session.execute(
            select(SubscriptionModel).where(
                SubscriptionModel.id == id,
                SubscriptionModel.deleted_at.is_(None),
            )
        )
        try:
            model = result.scalar_one()
        except NoResultFound:
            raise NotFoundException()
        model.deleted_at = datetime.now(UTC)
        await self._session.commit()

    async def list_due_for_notification(self, today: date) -> list[Subscription]:
        result = await self._session.execute(
            select(SubscriptionModel).where(
                SubscriptionModel.deleted_at.is_(None),
                SubscriptionModel.status == "active",
                SubscriptionModel.notification_emails.isnot(None),
                SubscriptionModel.notification_emails != "[]",
                SubscriptionModel.expiry_date >= today,
                or_(
                    SubscriptionModel.last_notified_date.is_(None),
                    SubscriptionModel.last_notified_date < today,
                ),
            )
        )
        candidates = [_to_entity(m) for m in result.scalars().all()]
        return [
            s
            for s in candidates
            if s.notification_days > 0
            and (s.expiry_date - today).days <= s.notification_days
            and s.notification_emails
        ]

    async def mark_notified(self, id: int, today: date) -> None:
        result = await self._session.execute(
            select(SubscriptionModel).where(
                SubscriptionModel.id == id,
                SubscriptionModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if model:
            model.last_notified_date = today
            await self._session.commit()
