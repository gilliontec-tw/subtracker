from datetime import date

from domain.entities.subscription import Subscription
from domain.repositories.subscription_repository import SubscriptionRepository

from application.interfaces.email_sender import EmailSender


def _format_body(sub: Subscription, today: date) -> str:
    days = (sub.expiry_date - today).days
    cost_str = f"{sub.currency} {sub.cost}" if sub.cost else "—"
    return (
        f"您好，\n\n"
        f"提醒您，以下訂閱即將到期：\n\n"
        f"服務名稱：{sub.service_name}\n"
        f"到期日：{sub.expiry_date}（{days} 天後）\n"
        f"負責人：{sub.owner_name or '—'}\n"
        f"部門：{sub.department or '—'}\n"
        f"費用：{cost_str}\n\n"
        f"請確認是否需要續約。若已完成續約，請至 SubTrack 更新到期日，即可停止後續提醒。\n\n"
        f"此郵件由 SubTrack 自動發送，請勿回覆。"
    )


class CheckAndNotifyUseCase:
    def __init__(self, repo: SubscriptionRepository, email_sender: EmailSender) -> None:
        self._repo = repo
        self._sender = email_sender

    async def execute(self, today: date | None = None) -> int:
        if today is None:
            today = date.today()
        due = await self._repo.list_due_for_notification(today)
        sent = 0
        for sub in due:
            days = (sub.expiry_date - today).days
            subject = f"[SubTrack] {sub.service_name} 訂閱將於 {days} 天後到期"
            body = _format_body(sub, today)
            await self._sender.send(to=sub.notification_emails, subject=subject, body=body)
            await self._repo.mark_notified(sub.id, today)
            sent += 1
        return sent
