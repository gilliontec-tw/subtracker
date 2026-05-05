r"""
Windows Task Scheduler entry point.
Schedule: daily at 08:00
Command: C:\Users\Gillion-ADM-015\AppData\Local\Programs\Python\Python311\python.exe C:\Users\Gillion-ADM-015\Desktop\Claude\saas-tracker\scripts\run_notifications.py
Start in: C:\Users\Gillion-ADM-015\Desktop\Claude\saas-tracker
"""
import sys
import os
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.infrastructure.database.session import SessionLocal
from src.infrastructure.database.sql_subscription_repository import SqlSubscriptionRepository
from src.infrastructure.email.smtp_email_sender import SmtpEmailSender
from src.application.use_cases.check_and_notify import CheckAndNotifyUseCase


def main():
    session = SessionLocal()
    try:
        repo = SqlSubscriptionRepository(session)
        email_sender = SmtpEmailSender()
        use_case = CheckAndNotifyUseCase(repo, email_sender)
        notified_ids = use_case.execute()
        print(f"[OK] Sent {len(notified_ids)} notification(s). IDs: {notified_ids}")
    except Exception as exc:
        print(f"[ERROR] Notification run failed: {exc}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
