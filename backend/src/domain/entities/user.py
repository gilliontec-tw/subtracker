from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    email: str
    display_name: str
    password_hash: str
    role: str  # 'admin' | 'manager' | 'user'
    can_create: bool
    can_update: bool
    can_delete: bool
    is_active: bool
    id: int | None = None
    invite_token: str | None = None
    invite_token_expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
