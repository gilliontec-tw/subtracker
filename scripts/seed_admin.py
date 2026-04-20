"""
Bootstrap the first admin account. Run ONCE after creating the users table.
Usage:  python scripts/seed_admin.py
Default credentials:  admin@gilliontec.com.tw  /  Admin@123!
Change the password immediately after first login.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from src.infrastructure.database.session import SessionLocal
from src.infrastructure.database.sql_user_repository import SqlUserRepository
from src.infrastructure.auth.hash_utils import hash_password
from src.domain.entities.user import User

session = SessionLocal()
repo = SqlUserRepository(session)

existing = repo.get_by_email("admin@gilliontec.com.tw")
if existing:
    print("Admin already exists — no changes made.")
else:
    admin = User(
        email="admin@gilliontec.com.tw",
        display_name="系統管理員",
        hashed_password=hash_password("Admin@123!"),
        role="admin",
        can_create=True,
        can_update=True,
        can_delete=True,
    )
    repo.add(admin)
    print("✅ Admin account created:")
    print("   Email:    admin@gilliontec.com.tw")
    print("   Password: Admin@123!")
    print("   ⚠️  Change this password immediately after first login!")

session.close()
