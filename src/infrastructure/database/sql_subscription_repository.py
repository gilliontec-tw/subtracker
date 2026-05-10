from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from src.domain.entities.subscription import Subscription, NotificationDays, SubscriptionStatus
from src.domain.repositories.subscription_repository import SubscriptionRepository
from src.infrastructure.database.models import SubscriptionModel


class SqlSubscriptionRepository(SubscriptionRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def _to_entity(self, model: SubscriptionModel) -> Subscription:
        return Subscription(
            id=model.id,
            service_name=model.service_name,
            login_account=model.login_account,
            expiry_date=model.expiry_date,
            notification_emails=model.notification_emails,
            notification_days=NotificationDays(model.notification_days),
            is_active=model.is_active,
            status=SubscriptionStatus(model.status) if model.status else SubscriptionStatus.ACTIVE,
            cost=Decimal(str(model.cost)) if model.cost is not None else None,
            currency=model.currency or "TWD",
            notes=model.notes,
            owner_name=model.owner_name,
            category=model.category,
            department=model.department,
            billing_cycle=model.billing_cycle,
            payment_account=model.payment_account,
            auto_renew=bool(model.auto_renew),
            trial_end_date=model.trial_end_date,
            next_billing_date=model.next_billing_date,
            notifications_enabled=bool(model.notifications_enabled),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def add(self, subscription: Subscription) -> Subscription:
        model = SubscriptionModel(
            service_name=subscription.service_name,
            login_account=subscription.login_account,
            expiry_date=subscription.expiry_date,
            notification_emails=subscription.notification_emails,
            notification_days=subscription.notification_days.value,
            status=subscription.status.value,
            cost=subscription.cost,
            currency=subscription.currency,
            notes=subscription.notes,
            owner_name=subscription.owner_name,
            category=subscription.category,
            department=subscription.department,
            billing_cycle=subscription.billing_cycle,
            payment_account=subscription.payment_account,
            auto_renew=subscription.auto_renew,
            trial_end_date=subscription.trial_end_date,
            next_billing_date=subscription.next_billing_date,
            notifications_enabled=subscription.notifications_enabled,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return self._to_entity(model)

    def get_by_id(self, subscription_id: int) -> Subscription | None:
        model = self._session.get(SubscriptionModel, subscription_id)
        return self._to_entity(model) if model else None

    def get_all_active(self) -> list[Subscription]:
        models = (
            self._session.query(SubscriptionModel)
            .filter(SubscriptionModel.is_active == True)
            .order_by(SubscriptionModel.expiry_date)
            .all()
        )
        return [self._to_entity(m) for m in models]

    def update(self, subscription: Subscription) -> Subscription:
        model = self._session.get(SubscriptionModel, subscription.id)
        if model is None:
            raise ValueError(f"Subscription {subscription.id} not found")
        model.service_name        = subscription.service_name
        model.login_account       = subscription.login_account
        model.expiry_date         = subscription.expiry_date
        model.notification_emails = subscription.notification_emails
        model.notification_days   = subscription.notification_days.value
        model.status              = subscription.status.value
        model.cost                = subscription.cost
        model.currency            = subscription.currency
        model.notes               = subscription.notes
        model.owner_name          = subscription.owner_name
        model.category            = subscription.category
        model.department          = subscription.department
        model.billing_cycle       = subscription.billing_cycle
        model.payment_account     = subscription.payment_account
        model.auto_renew              = subscription.auto_renew
        model.trial_end_date          = subscription.trial_end_date
        model.next_billing_date       = subscription.next_billing_date
        model.notifications_enabled   = subscription.notifications_enabled
        model.updated_at              = datetime.now(timezone.utc)
        self._session.commit()
        self._session.refresh(model)
        return self._to_entity(model)

    def deactivate(self, subscription_id: int) -> None:
        model = self._session.get(SubscriptionModel, subscription_id)
        if model:
            model.is_active  = False
            model.updated_at = datetime.now(timezone.utc)
            self._session.commit()
