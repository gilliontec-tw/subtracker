from __future__ import annotations

import calendar
from datetime import date

from domain.entities.audit_entry import AuditEntry
from domain.entities.subscription import Subscription
from domain.repositories.audit_log_repository import AuditLogRepository
from domain.repositories.subscription_repository import SubscriptionRepository


def _add_cycle(d: date, cycle: str) -> date:
    """Return a new date advanced by the given billing cycle."""
    if cycle == "monthly":
        months = 1
    elif cycle == "quarterly":
        months = 3
    elif cycle == "semi_annual":
        months = 6
    elif cycle == "annual":
        months = 12
    elif cycle == "biennial":
        months = 24
    else:
        raise ValueError(f"Unknown billing cycle: {cycle}")

    total_months = d.month - 1 + months
    new_year = d.year + total_months // 12
    new_month = total_months % 12 + 1
    # Clamp day to the last valid day of the target month
    new_day = min(d.day, calendar.monthrange(new_year, new_month)[1])
    return date(new_year, new_month, new_day)


class BatchRenewSubscriptionsUseCase:
    def __init__(
        self,
        repo: SubscriptionRepository,
        audit_repo: AuditLogRepository | None = None,
        actor_user_id: int | None = None,
        actor_email: str | None = None,
    ) -> None:
        self._repo = repo
        self._audit_repo = audit_repo
        self._actor_user_id = actor_user_id
        self._actor_email = actor_email

    async def execute(self, subscription_ids: list[int]) -> dict:
        renewed: list[Subscription] = []
        skipped: list[dict] = []

        for sub_id in subscription_ids:
            sub = await self._repo.get_by_id(sub_id)

            if sub is None:
                skipped.append({"id": sub_id, "reason": "not_found"})
                continue

            if sub.status != "active":
                skipped.append({"id": sub_id, "reason": "not_active"})
                continue

            if sub.billing_cycle is None:
                skipped.append({"id": sub_id, "reason": "missing_billing_cycle"})
                continue

            old_expiry = sub.expiry_date
            new_expiry = _add_cycle(old_expiry, sub.billing_cycle)
            sub.expiry_date = new_expiry

            saved = await self._repo.save(sub)
            renewed.append(saved)

            if self._audit_repo is not None:
                await self._audit_repo.save(
                    AuditEntry(
                        user_id=self._actor_user_id,
                        action="renew",
                        resource_type="subscription",
                        resource_id=sub_id,
                        details={
                            "user_email": self._actor_email,
                            "service_name": sub.service_name,
                            "changes": [
                                {
                                    "field": "expiry_date",
                                    "before": str(old_expiry),
                                    "after": str(new_expiry),
                                }
                            ],
                        },
                    )
                )

        return {"renewed": renewed, "skipped": skipped}
