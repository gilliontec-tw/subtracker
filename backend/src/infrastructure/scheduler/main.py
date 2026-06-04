"""Long-running scheduler container: fires CheckAndNotifyUseCase once per day."""

import asyncio
import logging
import os
import signal
from datetime import date

from api.config import get_settings
from application.use_cases.check_and_notify import CheckAndNotifyUseCase

from infrastructure.database.repositories.subscription_repository import (
    SqlSubscriptionRepository,
)
from infrastructure.database.session import AsyncSessionFactory
from infrastructure.smtp.smtp_email_sender import SmtpEmailSender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

POLL_INTERVAL = 30  # seconds between clock checks

_shutdown = asyncio.Event()


def _handle_signal(sig: int, _frame: object) -> None:
    log.info("Received signal %s, shutting down…", signal.Signals(sig).name)
    _shutdown.set()


async def run_notifications() -> None:
    settings = get_settings()
    sender = SmtpEmailSender(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        from_addr=settings.smtp_from,
    )
    async with AsyncSessionFactory() as session:
        repo = SqlSubscriptionRepository(session)
        use_case = CheckAndNotifyUseCase(repo, sender)
        sent = await use_case.execute()
    log.info("Notifications sent: %d", sent)


async def scheduler_loop(target_hour: int, target_minute: int) -> None:
    last_run_date: date | None = None

    log.info("Scheduler started — will run daily at %02d:%02d", target_hour, target_minute)

    while not _shutdown.is_set():
        from datetime import datetime

        now = datetime.now()
        today = now.date()

        if now.hour == target_hour and now.minute == target_minute and last_run_date != today:
            log.info("Triggering daily notification job")
            try:
                await run_notifications()
                last_run_date = today
            except Exception:
                log.exception("Notification job failed")

        try:
            await asyncio.wait_for(_shutdown.wait(), timeout=POLL_INTERVAL)
        except TimeoutError:
            pass


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    target_hour = int(os.environ.get("NOTIFICATION_CRON_HOUR", "8"))
    target_minute = int(os.environ.get("NOTIFICATION_CRON_MINUTE", "0"))

    asyncio.run(scheduler_loop(target_hour, target_minute))


if __name__ == "__main__":
    main()
