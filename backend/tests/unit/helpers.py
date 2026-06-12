from datetime import UTC, datetime, timedelta

from domain.entities.user import User


def make_user(**kwargs) -> User:
    defaults = dict(
        id=1,
        email="u@corp.com",
        display_name="User",
        password_hash="hash",
        role="user",
        is_active=True,
        invite_token="validtoken",
        invite_token_expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
    )
    defaults.update(kwargs)
    return User(**defaults)
