import logging
from datetime import date

from src.domain.repositories.subscription_repository import SubscriptionRepository
from src.application.interfaces.email_sender import EmailSender

log = logging.getLogger(__name__)


class CheckAndNotifyUseCase:
    def __init__(self, repo: SubscriptionRepository, email_sender: EmailSender) -> None:
        self._repo = repo
        self._email_sender = email_sender

    def execute(self, today: date | None = None) -> list[int]:
        if today is None:
            today = date.today()

        subscriptions = self._repo.get_all_active()
        due_subs = [
            s for s in subscriptions
            if s.notifications_enabled and s.should_notify_today(today)
        ]

        if not due_subs:
            return []

        # 收集所有收件人（去重、保持順序）
        seen: set[str] = set()
        recipients: list[str] = []
        for sub in due_subs:
            for email in sub.notification_emails.split(","):
                email = email.strip()
                if email and email not in seen:
                    seen.add(email)
                    recipients.append(email)

        count = len(due_subs)
        subject = f"[提醒] 今日共有 {count} 筆訂閱即將到期，請確認續約"

        lines = []
        for i, sub in enumerate(due_subs, 1):
            lines.append(
                f"  {i}. {sub.service_name}\n"
                f"     登入帳號：{sub.login_account}\n"
                f"     到期日期：{sub.expiry_date.strftime('%Y/%m/%d')}\n"
                f"     提前通知：{sub.notification_days.value} 天前"
            )
        items_text = "\n\n".join(lines)

        body = (
            f"您好，\n\n"
            f"以下 {count} 筆 SaaS 訂閱即將到期，請確認是否需要續約：\n\n"
            f"{items_text}\n\n"
            f"請於到期前完成續約評估，並於系統中更新狀態。\n\n"
            f"此信為系統自動發送，請勿回覆。"
        )

        for recipient in recipients:
            try:
                self._email_sender.send(to=recipient, subject=subject, body=body)
            except Exception as exc:
                log.error("Failed to send notification email to %s: %s", recipient, exc)

        # Return IDs regardless of partial send failures; callers decide on retry policy.
        return [sub.id for sub in due_subs]
