import uuid
from datetime import UTC, datetime, timedelta

import jwt
from api.config import get_settings

settings = get_settings()


def _now() -> datetime:
    return datetime.now(UTC)


def create_access_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": _now(),
        "exp": _now() + timedelta(minutes=settings.jwt_access_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_access_secret_key, algorithm="HS256")


def create_refresh_token(user_id: int) -> tuple[str, str]:
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "type": "refresh",
        "iat": _now(),
        "exp": _now() + timedelta(days=settings.jwt_refresh_expire_days),
    }
    token = jwt.encode(payload, settings.jwt_refresh_secret_key, algorithm="HS256")
    return token, jti


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_access_secret_key, algorithms=["HS256"])


def decode_refresh_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_refresh_secret_key, algorithms=["HS256"])
