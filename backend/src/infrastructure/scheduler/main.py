"""Long-running scheduler container: fires CheckAndNotifyUseCase once per day."""

import asyncio
import logging
import signal
from datetime import date, datetime

from api.config import get_settings
from application.services.settings_service import SettingsService
from application.use_cases.check_and_notify import CheckAndNotifyUseCase

from infrastructure.database.repositories.subscription_repository import SqlSubscriptionRepository
from infrastructure.database.repositories.system_setting_repository import (
    SqlSystemSettingRepository,
)
from infrastructure.database.session import AsyncSessionFactory
from infrastructure.smtp.smtp_email_sender import SmtpEmailSender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

POLL_INTERVAL = 30

_shutdown = asyncio.Event()


def _handle_signal(sig: int, _frame: object) -> None:
    log.info("Received signal %s, shutting down…", signal.Signals(sig).name)
    _shutdown.set()


async def _read_schedule() -> tuple[int, int]:
    env = get_settings()
    async with AsyncSessionFactory() as session:
        svc = SettingsService(SqlSystemSettingRepository(session), env)
        hour = int(await svc.get("notification_cron_hour") or str(env.notification_cron_hour))
        minute = int(await svc.get("notification_cron_minute") or str(env.notification_cron_minute))
    return hour, minute


async def run_notifications() -> None:
    env = get_settings()
    async with AsyncSessionFactory() as session:
        svc = SettingsService(SqlSystemSettingRepository(session), env)
        smtp_config = await svc.get_smtp_config()
        sender = SmtpEmailSender(
            host=smtp_config.host,
            port=smtp_config.port,
            username=smtp_config.user,
            password=smtp_config.password,
            from_addr=smtp_config.from_addr,
            sender_name=smtp_config.sender_name,
        )
        repo = SqlSubscriptionRepository(session)
        use_case = CheckAndNotifyUseCase(repo, sender)
        sent = await use_case.execute()
    log.info("Notifications sent: %d", sent)


async def scheduler_loop(default_hour: int, default_minute: int) -> None:
    last_run_date: date | None = None
    log.info("Scheduler started — initial schedule %02d:%02d", default_hour, default_minute)

    while not _shutdown.is_set():
        try:
            target_hour, target_minute = await _read_schedule()
        except Exception:
            log.warning("Could not read schedule from DB, using defaults")
            target_hour, target_minute = default_hour, default_minute

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

    env = get_settings()
    asyncio.run(scheduler_loop(env.notification_cron_hour, env.notification_cron_minute))


if __name__ == "__main__":
    main()
