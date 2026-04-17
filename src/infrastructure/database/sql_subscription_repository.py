from datetime import datetime
from sqlalchemy.orm import Session
from src.domain.entities.subscription import Subscription, NotificationDays
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
            responsible_person_email=model.responsible_person_email,
            notification_days=NotificationDays(model.notification_days),
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def add(self, subscription: Subscription) -> Subscription:
        model = SubscriptionModel(
            service_name=subscription.service_name,
            login_account=subscription.login_account,
            expiry_date=subscription.expiry_date,
            responsible_person_email=subscription.responsible_person_email,
            notification_days=subscription.notification_days.value,
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
        model.service_name = subscription.service_name
        model.login_account = subscription.login_account
        model.expiry_date = subscription.expiry_date
        model.responsible_person_email = subscription.responsible_person_email
        model.notification_days = subscription.notification_days.value
        model.updated_at = datetime.now()
        self._session.commit()
        self._session.refresh(model)
        return self._to_entity(model)

    def deactivate(self, subscription_id: int) -> None:
        model = self._session.get(SubscriptionModel, subscription_id)
        if model:
            model.is_active = False
            model.updated_at = datetime.now()
            self._session.commit()
