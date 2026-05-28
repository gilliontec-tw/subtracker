import sys
from collections import defaultdict
from datetime import date

from domain.entities.subscription import Subscription
from domain.repositories.subscription_repository import SubscriptionRepository

from application.interfaces.email_sender import EmailSender


def _format_sub_block(sub: Subscription, today: date) -> str:
    days = (sub.expiry_date - today).days
    cost_str = f"{sub.currency} {sub.cost}" if sub.cost else "—"
    return (
        f"服務名稱：{sub.service_name}\n"
        f"到期日：{sub.expiry_date}（{days} 天後）\n"
        f"負責人：{sub.owner_name or '—'}\n"
        f"部門：{sub.department or '—'}\n"
        f"費用：{cost_str}"
    )


def _format_email(subs: list[Subscription], today: date) -> tuple[str, str]:
    if len(subs) == 1:
        sub = subs[0]
        days = (sub.expiry_date - today).days
        subject = f"[SubTrack] {sub.service_name} 訂閱將於 {days} 天後到期"
    else:
        subject = f"[SubTrack] 您有 {len(subs)} 筆訂閱即將到期"

    separator = "─" * 30
    blocks = f"\n{separator}\n".join(_format_sub_block(s, today) for s in subs)
    body = (
        f"您好，\n\n"
        f"提醒您，以下 {len(subs)} 筆訂閱即將到期：\n\n"
        f"{separator}\n"
        f"{blocks}\n"
        f"{separator}\n\n"
        f"請確認是否需要續約。若已完成續約，請至 SubTrack 更新到期日，即可停止後續提醒。\n\n"
        f"此郵件由 SubTrack 自動發送，請勿回覆。"
    )
    return subject, body


class CheckAndNotifyUseCase:
    def __init__(self, repo: SubscriptionRepository, email_sender: EmailSender) -> None:
        self._repo = repo
        self._sender = email_sender

    async def execute(self, today: date | None = None) -> int:
        if today is None:
            today = date.today()
        due = await self._repo.list_due_for_notification(today)

        # Group subscriptions by recipient email
        by_recipient: dict[str, list[Subscription]] = defaultdict(list)
        for sub in due:
            if sub.id is None:
                continue
            for email in sub.notification_emails:
                by_recipient[email].append(sub)

        notified_ids: set[int] = set()
        emails_sent = 0

        for recipient, subs in by_recipient.items():
            try:
                subject, body = _format_email(subs, today)
                await self._sender.send(to=[recipient], subject=subject, body=body)
                for sub in subs:
                    if sub.id not in notified_ids:
                        await self._repo.mark_notified(sub.id, today)
                        notified_ids.add(sub.id)
                emails_sent += 1
            except Exception as exc:
                print(f"通知失敗（{recipient}）：{exc}", file=sys.stderr)

        return emails_sent
