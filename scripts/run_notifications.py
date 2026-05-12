r"""
Notification entry point — run daily at 08:00.

Windows Task Scheduler:
  Command:  python scripts\run_notifications.py
  Start in: <project root>

Linux crontab:
  0 8 * * * cd /opt/subtrack && python scripts/run_notifications.py
"""
import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Log to file so Task Scheduler errors are visible
log_path = Path(__file__).parent.parent / "logs" / "notifications.log"
log_path.parent.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

from src.infrastructure.database.session import SessionLocal
from src.infrastructure.database.sql_subscription_repository import SqlSubscriptionRepository
from src.infrastructure.email.smtp_email_sender import SmtpEmailSender
from src.application.use_cases.check_and_notify import CheckAndNotifyUseCase


def main():
    log.info("=== Notification run started ===")
    session = SessionLocal()
    try:
        repo = SqlSubscriptionRepository(session)
        email_sender = SmtpEmailSender()
        use_case = CheckAndNotifyUseCase(repo, email_sender)
        notified_ids = use_case.execute()
        log.info(f"Sent {len(notified_ids)} notification(s). IDs: {notified_ids}")
    except Exception as exc:
        log.exception(f"Notification run failed: {exc}")
        sys.exit(1)
    finally:
        session.close()
    log.info("=== Notification run finished ===")


if __name__ == "__main__":
    main()
