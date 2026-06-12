from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    email: str
    display_name: str
    password_hash: str
    role: str  # 'admin' | 'user'
    is_active: bool
    id: int | None = None
    invite_token: str | None = None
    invite_token_expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def is_invite_valid(self) -> bool:
        from datetime import UTC, datetime

        if self.invite_token is None or self.invite_token_expires_at is None:
            return False
        return self.invite_token_expires_at > datetime.now(UTC).replace(tzinfo=None)
