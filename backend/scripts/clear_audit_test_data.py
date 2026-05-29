"""
One-time cleanup: delete all audit_log entries written by integration tests.
Run from backend/ with venv active: python scripts/clear_audit_test_data.py
"""

import asyncio

from api.config import get_settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        result = await conn.execute(text("DELETE FROM audit_log"))
        print(f"Deleted {result.rowcount} audit_log entries.")
    await engine.dispose()


asyncio.run(main())
