"""Run from backend/ directory: python scripts/seed_admin.py"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from infrastructure.auth.password import hash_password
from infrastructure.database.models import Base, UserModel
from infrastructure.database.session import AsyncSessionFactory, engine
from sqlalchemy import select


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionFactory() as session:
        result = await session.execute(select(UserModel).where(UserModel.email == "admin@test.com"))
        existing = result.scalar_one_or_none()
        if existing:
            print("Admin already exists — skipping.")
            return

        admin = UserModel(
            email="admin@test.com",
            display_name="Admin",
            password_hash=hash_password("testpass123"),
            role="admin",
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        print("Admin created: admin@test.com / testpass123")


asyncio.run(main())
