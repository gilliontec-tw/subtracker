"""Run from backend/ directory: python scripts/run_notifications.py"""

import asyncio
import os
import sys
from pathlib import Path

# Set working directory to backend/ so .env is found when launched by Task Scheduler
os.chdir(Path(__file__).parent.parent)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.config import get_settings  # noqa: E402
from application.use_cases.check_and_notify import CheckAndNotifyUseCase  # noqa: E402
from infrastructure.database.repositories.subscription_repository import (  # noqa: E402
    SqlSubscriptionRepository,
)
from infrastructure.database.session import AsyncSessionFactory  # noqa: E402
from infrastructure.smtp.smtp_email_sender import SmtpEmailSender  # noqa: E402


async def main() -> None:
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
    print(f"通知已發送：{sent} 封")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"通知發送失敗：{e}", file=sys.stderr)
        sys.exit(1)
