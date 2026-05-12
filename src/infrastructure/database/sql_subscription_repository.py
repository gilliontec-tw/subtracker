import logging
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from src.domain.entities.subscription import Subscription, NotificationDays, SubscriptionStatus
from src.domain.repositories.subscription_repository import SubscriptionRepository
from src.infrastructure.database.models import SubscriptionModel
from src.infrastructure.auth.field_encrypt import encrypt as _enc, decrypt as _dec

log = logging.getLogger(__name__)


def _safe_notification_days(value: int) -> NotificationDays:
    """Convert a DB integer to NotificationDays; fall back to 30 for legacy/unknown values."""
    try:
        return NotificationDays(value)
    except ValueError:
        log.warning("Unknown notification_days value %r in DB; defaulting to 30", value)
        return NotificationDays.THIRTY


class SqlSubscriptionRepository(SubscriptionRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def _to_entity(self, model: SubscriptionModel) -> Subscription:
        # login_password 以 Fernet 密文儲存於 DB，在此解密後交給 domain 層（明文）
        raw_pw = _dec(model.login_password)
        if model.login_password is not None and raw_pw is None:
            # 解密失敗代表金鑰不符或資料損壞，記錄警告但不中斷讀取
            log.warning("subscription id=%s: login_password 解密失敗，可能金鑰已輪換或資料損壞", model.id)
        return Subscription(
            id=model.id,
            service_name=model.service_name,
            login_account=model.login_account,
            expiry_date=model.expiry_date,
            notification_emails=model.notification_emails,
            notification_days=_safe_notification_days(model.notification_days),
            is_active=model.is_active,
            status=SubscriptionStatus(model.status) if model.status else SubscriptionStatus.ACTIVE,
            cost=Decimal(str(model.cost)) if model.cost is not None else None,
            currency=model.currency or "TWD",
            notes=model.notes,
            user_name=model.user_name,
            category=model.category,
            department=model.department,
            billing_cycle=model.billing_cycle,
            payment_account=model.payment_account,
            auto_renew=bool(model.auto_renew),
            notifications_enabled=bool(model.notifications_enabled),
            login_password=raw_pw,  # 已解密的明文（或 None）
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
            user_name=subscription.user_name,
            category=subscription.category,
            department=subscription.department,
            billing_cycle=subscription.billing_cycle,
            payment_account=subscription.payment_account,
            auto_renew=subscription.auto_renew,
            notifications_enabled=subscription.notifications_enabled,
            login_password=_enc(subscription.login_password),  # 明文 → Fernet 密文
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
        model.user_name           = subscription.user_name
        model.category            = subscription.category
        model.department          = subscription.department
        model.billing_cycle       = subscription.billing_cycle
        model.payment_account     = subscription.payment_account
        model.auto_renew              = subscription.auto_renew
        model.notifications_enabled   = subscription.notifications_enabled
        model.login_password          = _enc(subscription.login_password)  # 明文 → Fernet 密文
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
