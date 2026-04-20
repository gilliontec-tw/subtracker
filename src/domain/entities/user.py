from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    email: str
    display_name: str
    hashed_password: str
    role: str           # "admin" | "user"
    can_create: bool
    can_update: bool
    can_delete: bool
    id: int | None = None
    is_active: bool = True
    created_at: datetime | None = None
    last_login_at: datetime | None = None
