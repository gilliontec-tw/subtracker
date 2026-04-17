from datetime import date
from src.domain.repositories.subscription_repository import SubscriptionRepository
from src.application.interfaces.email_sender import EmailSender


class CheckAndNotifyUseCase:
    def __init__(self, repo: SubscriptionRepository, email_sender: EmailSender) -> None:
        self._repo = repo
        self._email_sender = email_sender

    def execute(self, today: date | None = None) -> list[int]:
        if today is None:
            today = date.today()

        subscriptions = self._repo.get_all_active()
        notified_ids: list[int] = []

        for sub in subscriptions:
            if not sub.should_notify_today(today):
                continue
            subject = (
                f"[提醒] {sub.service_name} 訂閱將於 {sub.expiry_date} 到期"
                f"（提前 {sub.notification_days.value} 天通知）"
            )
            body = (
                f"您好，\n\n"
                f"以下 SaaS 訂閱即將到期，請確認是否需要續約：\n\n"
                f"  服務名稱：{sub.service_name}\n"
                f"  登入帳號：{sub.login_account}\n"
                f"  到期日期：{sub.expiry_date}\n"
                f"  提前通知：{sub.notification_days.value} 天前\n\n"
                f"請於到期前完成續約評估，並於系統中更新狀態。\n\n"
                f"此信為系統自動發送，請勿回覆。"
            )
            try:
                self._email_sender.send(
                    to=sub.responsible_person_email,
                    subject=subject,
                    body=body,
                )
                notified_ids.append(sub.id)
            except Exception as exc:
                print(f"[ERROR] Failed to send email for subscription {sub.id}: {exc}")

        return notified_ids
